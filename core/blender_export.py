#!/usr/bin/env python3
"""blender_export.py - real model/preview export worker for Whip Clothing Tool.

Runs inside Blender (which already has Sollumz + szio/PyMateria available):

    blender --background --python blender_export.py -- <job.json>

Reads the JSON job written by the Tauri app, scans loose add-on folders and/or
vanilla GTA RPF archives, converts every drawable/texture variant into
WHIP-compatible .ydr/.ytd files, renders transparent previews, and emits
NDJSON progress events prefixed with ``WCT_JSON:`` on stdout.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import sys
import tempfile
import traceback
from pathlib import Path, PurePosixPath

import bpy
from mathutils import Matrix, Vector

try:
    import addon_utils  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - Blender always ships this
    addon_utils = None


# ---------------------------------------------------------------------------
# Event bridge
# ---------------------------------------------------------------------------

PREFIX = "WCT_JSON:"


def emit(kind: str, **data) -> None:
    payload = {"kind": kind, **data}
    print(PREFIX + json.dumps(payload, ensure_ascii=False), flush=True)


def log(level: str, message: str) -> None:
    emit("log", level=level, message=message)


def progress(message: str, current: int, total: int) -> None:
    emit("progress", message=message, current=current, total=total)


def done(ok: bool, message: str) -> None:
    emit("done", ok=ok, message=message)


# ---------------------------------------------------------------------------
# Sollumz / Blender setup
# ---------------------------------------------------------------------------

_SOLLUMZ_MODULES = [
    "bl_ext.user_default.sollumz",
    "bl_ext.blender_org.sollumz",
    "bl_ext.blender_org.sollumz_dev",
    "SollumzPlugin",
]


def ensure_sollumz() -> None:
    try:
        bpy.ops.sollumz.import_assets  # type: ignore[attr-defined]
        return
    except Exception:
        pass
    if addon_utils is None:
        raise RuntimeError("Sollumz add-on is not available in this Blender installation")
    for module in _SOLLUMZ_MODULES:
        try:
            addon_utils.enable(module, default_set=False)
            bpy.ops.sollumz.import_assets  # type: ignore[attr-defined]
            log("success", f"Enabled Sollumz: {module}")
            return
        except Exception:
            continue
    raise RuntimeError(
        "Sollumz is required. Install and enable it in Blender, then run the export again."
    )


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    for img in list(bpy.data.images):
        if img.users == 0:
            bpy.data.images.remove(img)


def eevee_engine() -> str:
    try:
        ids = {i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    except Exception:
        ids = set()
    return "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in ids else "BLENDER_EEVEE"


def setup_render(size: int, image_format: str) -> None:
    scene = bpy.context.scene
    scene.render.engine = eevee_engine()
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    fmt = image_format.upper()
    scene.render.image_settings.file_format = "JPEG" if fmt == "JPEG" else fmt
    scene.render.image_settings.quality = 92
    scene.render.image_settings.color_mode = "RGB" if fmt == "JPEG" else "RGBA"
    scene.render.use_simplify = True
    scene.render.simplify_subdivision = 0
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 1
    scene.view_settings.view_transform = "Standard"
    scene.use_nodes = fmt == "JPEG"
    if fmt == "JPEG":
        tree = scene.node_tree
        tree.nodes.clear()
        layers = tree.nodes.new("CompositorNodeRLayers")
        white = tree.nodes.new("CompositorNodeRGB")
        white.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        over = tree.nodes.new("CompositorNodeAlphaOver")
        composite = tree.nodes.new("CompositorNodeComposite")
        tree.links.new(white.outputs[0], over.inputs[1])
        tree.links.new(layers.outputs["Image"], over.inputs[2])
        tree.links.new(over.outputs[0], composite.inputs[0])


def setup_lighting() -> None:
    world = bpy.data.worlds.get("WCTWorld") or bpy.data.worlds.new("WCTWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is None:
        bg = world.node_tree.nodes.new("ShaderNodeBackground")
        out = world.node_tree.nodes.get("World Output") or world.node_tree.nodes.new("ShaderNodeOutputWorld")
        world.node_tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs[0].default_value = (0.55, 0.57, 0.6, 1.0)
    bg.inputs[1].default_value = 0.35

    def area(name: str, loc, energy: float, color) -> None:
        data = bpy.data.lights.new(name, type="AREA")
        data.energy = energy
        data.color = color
        if hasattr(data, "size"):
            data.size = 3.0
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    area("WCT_Key", (2.5, -2.5, 3.5), 190, (1.0, 0.96, 0.9))
    area("WCT_Fill", (-3.0, -1.5, 2.0), 85, (0.85, 0.92, 1.0))
    area("WCT_Rim", (0.0, 3.0, 4.0), 120, (1.0, 1.0, 1.0))


def is_collision(obj) -> bool:
    return str(getattr(obj, "sollum_type", "")).startswith("sollumz_bound")


def hide_collisions() -> None:
    for obj in bpy.data.objects:
        if is_collision(obj):
            obj.hide_render = True


def fix_alpha_modes() -> None:
    for mat in bpy.data.materials:
        if hasattr(mat, "blend_method") and mat.blend_method in {"BLEND", "HASHED"}:
            try:
                mat.blend_method = "CLIP"
                mat.alpha_threshold = 0.01
            except Exception:
                pass
        if not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != "BSDF_PRINCIPLED":
                continue
            alpha = node.inputs.get("Alpha")
            if alpha is None:
                continue
            if alpha.is_linked:
                for link in list(mat.node_tree.links):
                    if link.to_socket == alpha:
                        mat.node_tree.links.remove(link)
            try:
                alpha.default_value = 1.0
            except Exception:
                pass


def mesh_bounds():
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not is_collision(o)]
    if not meshes:
        return None
    mn = Vector((float("inf"),) * 3)
    mx = Vector((float("-inf"),) * 3)
    for obj in meshes:
        for corner in obj.bound_box:
            p = obj.matrix_world @ Vector(corner)
            for i in range(3):
                mn[i] = min(mn[i], p[i])
                mx[i] = max(mx[i], p[i])
    return mn, mx


HEAD_PROP_RE = re.compile(r"(?:^|[_^])p_(?:head|eyes|ears|mouth)_\d", re.I)
BAG_RE = re.compile(r"(?:^|[_^])hand_\d", re.I)
SHOE_RE = re.compile(r"(?:^|[_^])feet_\d", re.I)


def apply_orientation(source_name: str) -> None:
    if HEAD_PROP_RE.search(source_name):
        rot = Matrix.Rotation(math.radians(180), 4, "Z") @ Matrix.Rotation(math.radians(-90), 4, "Y")
    elif BAG_RE.search(source_name):
        rot = Matrix.Rotation(math.radians(180), 4, "Z")
    elif SHOE_RE.search(source_name):
        rot = Matrix.Rotation(math.radians(90), 4, "Z")
    else:
        return
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.matrix_world = rot @ obj.matrix_world
    bpy.context.view_layer.update()


def frame_camera(cam) -> None:
    bounds = mesh_bounds()
    if bounds is None:
        return
    mn, mx = bounds
    center = (mn + mx) / 2
    size = mx - mn
    az = math.radians(35.0)
    el = math.radians(20.0)
    visible_w = abs(size.x * math.cos(az)) + abs(size.y * math.sin(az))
    depth = abs(size.x * math.sin(az)) + abs(size.y * math.cos(az))
    visible_h = size.z * math.cos(el) + depth * math.sin(el)
    cam.data.ortho_scale = max(visible_w, visible_h, 0.001) * 1.22
    distance = max(size.x, size.y, size.z, 1.0) * 3.0
    offset = Vector((
        math.sin(az) * math.cos(el),
        -math.cos(az) * math.cos(el),
        math.sin(el),
    )) * distance
    cam.location = center + offset
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()


def render_preview(work_dir: Path, model_name: str, output: Path, job: dict, source_name: str) -> bool:
    clear_scene()
    ensure_sollumz()
    files = [{"name": f"{model_name}.ydr"}]
    if (work_dir / f"{model_name}.ytd").is_file():
        files.append({"name": f"{model_name}.ytd"})

    bpy.ops.sollumz.import_assets(
        directory=str(work_dir) + os.sep,
        files=files,
        use_custom_settings=True,
    )
    if mesh_bounds() is None:
        return False

    fix_alpha_modes()
    hide_collisions()
    apply_orientation(source_name)

    cam_data = bpy.data.cameras.new("WCTCamera")
    cam_data.type = "ORTHO"
    cam_data.clip_start = 0.01
    cam_data.clip_end = 1000
    cam = bpy.data.objects.new("WCTCamera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    setup_lighting()
    frame_camera(cam)

    setup_render(int(job.get("imgSize", 256)), str(job.get("imgFormat", "png")))
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    return output.is_file()


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------

YDD_RE = re.compile(
    r"^(?:(?P<body>mp_[mf]_[a-z0-9_]+)\^)?"
    r"(?P<part>[a-z0-9]+(?:_[a-z0-9]+)*)_(?P<draw>\d{1,3})"
    r"(?:_(?P<variant>[a-z0-9]+))?(?:_\d+)?$",
    re.I,
)
YTD_RE = re.compile(
    r"^(?:(?P<body>mp_[mf]_[a-z0-9_]+)\^)?"
    r"(?P<part>[a-z0-9]+(?:_[a-z0-9]+)*)_diff[_-](?P<draw>\d{1,3})"
    r"[_-](?P<tex>[a-z0-9]+)(?:[_-].*)?$",
    re.I,
)
BODY_IN_PATH_RE = re.compile(r"mp_[mf]_[a-z0-9_]+", re.I)


def body_from_source(src, name: str) -> str:
    prefix_match = re.match(r"^(mp_[mf]_[a-z0-9_]+)\^", name, re.I)
    if prefix_match:
        return prefix_match.group(1)
    hit = BODY_IN_PATH_RE.search(str(src).replace("\\", "/"))
    return hit.group(0) if hit else ""


def collection_from_body(body: str) -> str:
    if not body or "freemode_01" in body.lower():
        return "np"
    return body.lower().split("_")[-1]


def gender_from_body(body: str, src) -> str:
    low = f"{body} {src}".lower().replace("\\", "/")
    return "female" if "mp_f_" in low or "mp_f_freemode" in low else "male"


def parse_source(src, name: str, is_ytd: bool = False) -> dict | None:
    stem = Path(name).stem
    regex = YTD_RE if is_ytd else YDD_RE
    match = regex.match(stem)
    if not match:
        return None
    body = match.group("body") or body_from_source(src, name)
    part = match.group("part").lower()
    draw = int(match.group("draw"))
    if is_ytd:
        tex = match.group("tex").lower()
        tex_index = int(tex) if tex.isdigit() else max(0, ord(tex[0]) - 97) if tex else 0
    else:
        tex = None
        tex_index = 0
    return {
        "source": src,
        "name": name,
        "body": body,
        "collection": collection_from_body(body),
        "gender": gender_from_body(body, src),
        "part": part,
        "draw": draw,
        "tex": tex,
        "texIndex": tex_index,
    }


def source_string(src) -> str:
    return str(src).replace("\\", "/")


def read_bytes(src) -> bytes:
    if hasattr(src, "read_bytes"):
        return src.read_bytes()
    return Path(src).read_bytes()


def scan_addons(folders: list[str]) -> tuple[list, list]:
    ydds: list = []
    ytds: list = []
    for folder in folders:
        path = Path(folder)
        if not path.exists():
            log("error", f"Addon path not found: {path}")
            continue
        files = path.rglob("*") if path.is_dir() else [path]
        for item in files:
            if not (item.is_file() or hasattr(item, "is_file") and item.is_file()):
                continue
            ext = item.suffix.lower() if hasattr(item, "suffix") else Path(str(item)).suffix.lower()
            if ext == ".ydd":
                ydds.append(item)
            elif ext == ".ytd":
                ytds.append(item)
    return ydds, ytds


def scan_vanilla(game_path: str, cache_file: Path) -> tuple[list, list]:
    from szio import VPath  # imported lazily so Blender starts faster

    game = str(game_path).replace("\\", "/").rstrip("/")
    game_dir = VPath(game)
    cached = None
    if cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            cached = None
    if not cached or str(cached.get("game", "")).lower() != game.lower():
        log("info", f"Indexing vanilla RPF archives in {game} (first run only)")
        entries: dict[str, list[str]] = {"ydd": [], "ytd": []}
        rpfs = list(game_dir.rglob("*.rpf"))
        log("info", f"Found {len(rpfs)} RPF archives")
        for idx, rpf in enumerate(rpfs, 1):
            full = str(rpf)
            rel = full[len(game) + 1:] if full.lower().startswith(game.lower()) else full
            try:
                archive = VPath(game, rel)
                for entry in archive.rglob("*"):
                    low = str(entry).lower()
                    if low.endswith(".ydd"):
                        entries["ydd"].append(str(entry))
                    elif low.endswith(".ytd"):
                        entries["ytd"].append(str(entry))
            except Exception as exc:
                log("error", f"Skipped RPF {rel}: {exc}")
            if idx % 20 == 0 or idx == len(rpfs):
                progress(f"Indexing RPF {idx}/{len(rpfs)}", idx, len(rpfs))
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"game": game, **entries}, indent=1), encoding="utf-8")
        cached = {"game": game, **entries}
        log("success", f"Indexed {len(entries['ydd'])} .ydd and {len(entries['ytd'])} .ytd files")
    else:
        log("success", "Using cached vanilla RPF index")

    def restore(rel: str):
        return VPath(game, rel[len(game) + 1:] if rel.lower().startswith(game.lower()) else rel)

    return [restore(p) for p in cached.get("ydd", [])], [restore(p) for p in cached.get("ytd", [])]


# ---------------------------------------------------------------------------
# Category / task planning
# ---------------------------------------------------------------------------

CATEGORIES = {
    "head": ("00_head", "0", ["head"]),
    "berd": ("01_masks", "1", ["berd"]),
    "hair": ("02_hair", "2", ["hair"]),
    "uppr": ("03_arms_gloves", "3", ["uppr", "hand"]),
    "lowr": ("04_pants", "4", ["lowr"]),
    "accs": ("05_bags", "5", ["accs", "hand"]),
    "feet": ("06_shoes", "6", ["feet"]),
    "teef": ("07_teeth", "7", ["teef"]),
    "task": ("08_undershirts", "8", ["task"]),
    "decl": ("10_decals", "10", ["decl"]),
    "jbib": ("11_tops", "11", ["jbib"]),
    "props_p_head": ("p0_hats", "p0", ["p_head"]),
    "props_p_eyes": ("p1_glasses", "p1", ["p_eyes"]),
    "props_p_ears": ("p2_ears", "p2", ["p_ears"]),
    "props_p_rwrist": ("p6_watches", "p6", ["p_rwrist"]),
    "props_p_lwrist": ("p7_bracelets", "p7", ["p_lwrist"]),
}


def categories_for_part(part: str, model_cats: list[str], preview_cats: list[str], mode: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for cat in dict.fromkeys(model_cats + preview_cats):
        meta = CATEGORIES.get(cat)
        if not meta or part not in meta[2]:
            continue
        if mode in ("models", "both") and cat in model_cats:
            result.append((cat, "models"))
        if mode in ("previews", "both") and cat in preview_cats:
            result.append((cat, "previews"))
    return result


def source_preference(src) -> tuple:
    """Rank sources so one canonical file wins over DLC duplicates."""
    value = source_string(src).lower()
    if ".rpf/" not in value:
        return (0, value)  # loose add-on file
    if "/mp_m_freemode_01_p/" in value or "/mp_f_freemode_01_p/" in value:
        return (1, value)  # base freemode props from the patch DLC
    if "x64w.rpf" in value or "x64v.rpf" in value:
        return (2, value)
    return (3, value)  # themed DLC variants


def dedupe_sources(items: list[dict], key_fn, label: str) -> list[dict]:
    best: dict[tuple, tuple[tuple, dict]] = {}
    for item in items:
        key = key_fn(item)
        rank = source_preference(item["source"])
        if key not in best or rank < best[key][0]:
            best[key] = (rank, item)
    if len(best) != len(items):
        log("info", f"Deduplicated {label}: {len(items)} -> {len(best)} unique item(s)")
    return [entry[1] for entry in best.values()]


def build_tasks(job: dict, ydds: list, ytds: list, out_root: Path) -> list[dict]:
    parsed_ydd = [p for src in ydds if (p := parse_source(src, Path(str(src)).name))]
    parsed_ytd = [p for src in ytds if (p := parse_source(src, Path(str(src)).name, True))]

    parsed_ydd = dedupe_sources(
        parsed_ydd, lambda p: (p["gender"], p["part"], p["draw"]), "drawable files"
    )
    parsed_ytd = dedupe_sources(
        parsed_ytd,
        lambda p: (p["gender"], p["part"], p["draw"], p["texIndex"]),
        "texture files",
    )

    ytd_by_key: dict[tuple, list[dict]] = {}
    for tex in parsed_ytd:
        key = (tex["gender"], tex["part"], tex["draw"], tex["collection"])
        ytd_by_key.setdefault(key, []).append(tex)
        ytd_by_key.setdefault((tex["gender"], tex["part"], tex["draw"], "*"), []).append(tex)

    mode = job.get("exportMode", "both")
    model_cats = job.get("modelCategories", []) or []
    preview_cats = job.get("previewCategories", []) or []
    tasks: list[dict] = []

    for item in parsed_ydd:
        pairs = categories_for_part(item["part"], model_cats, preview_cats, mode)
        if not pairs:
            continue
        textures = ytd_by_key.get(
            (item["gender"], item["part"], item["draw"], item["collection"]), []
        ) or ytd_by_key.get((item["gender"], item["part"], item["draw"], "*"), [])
        textures = sorted(textures, key=lambda t: (t["texIndex"], t["name"])) or [None]
        for cat, kind in pairs:
            folder, slot, _ = CATEGORIES[cat]
            for tex in textures:
                tasks.append({
                    "category": cat,
                    "kind": kind,
                    "gender": item["gender"],
                    "collection": item["collection"],
                    "part": item["part"],
                    "draw": item["draw"],
                    "slotFolder": folder,
                    "slot": slot,
                    "ydd": item["source"],
                    "yddName": item["name"],
                    "textures": [tex] if tex else [],
                    "modelDir": out_root / "models" / f"whip_media_clothing_{item['gender']}" / "img" / "clothing" / item["gender"] / folder,
                    "previewDir": out_root / "previews" / f"whip_media_clothing_{item['gender']}" / "img" / "clothing" / item["gender"] / folder,
                })
    return tasks


# ---------------------------------------------------------------------------
# Main export
# ---------------------------------------------------------------------------

def export(job: dict) -> None:
    out_root = Path(job.get("outRoot", ""))
    if not str(out_root):
        raise RuntimeError("Output root is required")
    out_root.mkdir(parents=True, exist_ok=True)

    ensure_sollumz()
    from szio import save_asset, try_load_asset
    from szio.gta5.assets import AssetFormat, AssetTarget, AssetVersion, SaveOptions

    targets = [AssetTarget(AssetFormat.NATIVE, AssetVersion.GEN8)]
    addon_folders = job.get("addonFolders", []) or []
    vanilla = job.get("gtavPath")
    addon_ydd, addon_ytd = scan_addons(addon_folders)
    vanilla_ydd, vanilla_ytd = ([], [])
    if vanilla:
        vanilla_ydd, vanilla_ytd = scan_vanilla(str(vanilla), out_root / ".wct_cache" / "rpf_index.json")

    ydds = addon_ydd + vanilla_ydd
    ytds = addon_ytd + vanilla_ytd
    log("info", f"Sources: {len(ydds)} drawable container(s), {len(ytds)} texture file(s)")
    if not ydds:
        raise RuntimeError("No .ydd files found in the selected sources")

    tasks = build_tasks(job, ydds, ytds, out_root)
    if not tasks:
        raise RuntimeError("No source drawables matched the selected categories")

    log("success", f"Planned {len(tasks)} drawable/texture variant(s)")
    progress("Starting core export", 0, len(tasks))

    work_root = out_root / ".wct_work"
    work_root.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    exported_models = 0
    exported_previews = 0
    failed = 0

    try:
        from szio import VPath  # used only to restore cache entries if needed

        for index, task in enumerate(tasks, 1):
            label = f"{task['gender']} {task['part']} #{task['draw']:03d} / {task['slot']}"
            try:
                loaded = try_load_asset(task["ydd"], return_target=True)
                if not loaded:
                    raise RuntimeError(f"Cannot load {task['yddName']}")
                asset, _ = loaded
                drawables = list((asset.drawables or {}).items())
                if not drawables:
                    raise RuntimeError(f"No drawables in {task['yddName']}")
                multi = len(drawables) > 1

                for di, (_, drawable) in enumerate(drawables):
                    for tex in task["textures"] or [None]:
                        tex_index = tex["texIndex"] if tex else 0
                        suffix = f"_{di:02d}" if multi else ""
                        base_name = (
                            f"{task['gender']}_{task['slot']}_{task['collection']}_"
                            f"{task['draw']:03d}{suffix}_{tex_index:02d}"
                        )
                        with tempfile.TemporaryDirectory(dir=work_root) as tmp:
                            work = Path(tmp)
                            save_asset(drawable, targets, work, base_name, SaveOptions())

                            if tex:
                                try:
                                    (work / f"{base_name}.ytd").write_bytes(read_bytes(tex["source"]))
                                except Exception as exc:
                                    log("error", f"Cannot copy texture {tex['name']}: {exc}")

                            if job.get("exportCollisions", False):
                                bounds = getattr(drawable, "bounds", None) or []
                                for bi, bound in enumerate(bounds):
                                    bname = base_name if len(bounds) == 1 else f"{base_name}_{bi}"
                                    try:
                                        save_asset(bound, targets, work, bname, SaveOptions())
                                    except Exception as exc:
                                        log("error", f"Collision export failed for {base_name}: {exc}")

                            row = {
                                "category": task["category"],
                                "kind": task["kind"],
                                "source": source_string(task["ydd"]),
                                "texture": tex["name"] if tex else None,
                                "name": base_name,
                            }
                            if task["kind"] == "models":
                                target_dir = task["modelDir"]
                                target_dir.mkdir(parents=True, exist_ok=True)
                                for ext in (".ydr", ".ytd", ".ybn"):
                                    for f in work.glob(f"*{ext}"):
                                        shutil.copy2(f, target_dir / f.name)
                                if (target_dir / f"{base_name}.ydr").is_file():
                                    exported_models += 1
                                    row["outputs"] = [
                                        source_string(p) for p in sorted(target_dir.glob(f"{base_name}.*"))
                                    ]
                                else:
                                    failed += 1
                                    log("error", f"Model file was not produced: {base_name}.ydr")
                            else:
                                target_dir = task["previewDir"]
                                ext = str(job.get("imgFormat", "png")).lower()
                                if ext == "jpeg":
                                    ext = "jpg"
                                out_file = target_dir / f"{base_name}.{ext}"
                                try:
                                    ok = render_preview(
                                        work, base_name, out_file, job, task["yddName"]
                                    )
                                except Exception as exc:
                                    ok = False
                                    log("error", f"Render failed for {base_name}: {exc}")
                                if ok:
                                    exported_previews += 1
                                    row["outputs"] = [source_string(out_file)]
                                else:
                                    failed += 1
                                    log("error", f"Preview was not produced: {out_file.name}")
                            manifest.append(row)
            except Exception as exc:
                failed += 1
                log("error", f"Export failed for {label}: {exc}")
                traceback.print_exc(file=sys.stderr)

            progress(f"core: {label}", index, len(tasks))

        manifest_path = out_root / "export_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log("success", f"Manifest written: {manifest_path}")

        message = (
            f"Core completed: {exported_models} model(s), {exported_previews} preview(s), "
            f"{failed} failed."
        )
        done(failed == 0, message)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        done(False, "No job file was supplied")
        return 1
    try:
        job = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        export(job)
        return 0
    except Exception as exc:
        log("error", f"{type(exc).__name__}: {exc}")
        traceback.print_exc(file=sys.stderr)
        done(False, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
