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

import io
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
from mathutils import Matrix, Quaternion, Vector

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


def extract_ytd_dds(ytd_path: Path, out_dir: Path) -> list[Path]:
    """Unpack the DDS textures of a .ytd so Blender can actually use them.

    Sollumz imports the dictionary but leaves clothing materials pointing at
    unresolved placeholders such as "zedra2.dds". Those placeholders are the
    reason every texture variant rendered with the same fallback colour.
    """
    if not ytd_path.is_file():
        return []
    try:
        from szio import try_load_asset
        asset, _ = try_load_asset(str(ytd_path), return_target=True)
    except Exception as exc:
        log("error", f"Cannot read texture file {ytd_path.name}: {exc}")
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for name, tex in (getattr(asset, "textures", {}) or {}).items():
        try:
            source = getattr(tex, "data", None)
            data = source.read_bytes() if hasattr(source, "read_bytes") else getattr(source, "data", b"")
            if not data or not data.startswith(b"DDS "):
                continue
            target = out_dir / f"{name}.dds"
            target.write_bytes(data)
            files.append(target)
        except Exception as exc:
            log("error", f"Cannot unpack texture {name}: {exc}")
    return files


def ytd_texture_names(path: Path) -> list[str]:
    """Return the real texture names stored inside a .ytd."""
    try:
        from szio import try_load_asset

        asset, _ = try_load_asset(str(path), return_target=True)
    except Exception:
        return []
    return [str(name) for name in (getattr(asset, "textures", {}) or {}).keys()]


def patch_diffuse_sampler(drawable, texture_name: str) -> None:
    """Bake the selected texture variation into the spawned prop's sampler."""
    group = getattr(drawable, "shader_group", None)
    if not group:
        return
    for shader in getattr(group, "shaders", []) or []:
        for param in getattr(shader, "parameters", []) or []:
            if str(getattr(param, "name", "")) == "diffusesampler":
                param.value = texture_name


def apply_diffuse_textures(dds_files: list[Path]) -> int:
    """Bind unpacked DDS files to the diffuse nodes Sollumz left unresolved."""
    if not dds_files:
        return 0

    loaded: dict[str, object] = {}
    for path in dds_files:
        try:
            # check_existing=False is critical: GTA variants often reuse the same
            # texture name with different pixels. Reusing a cached image would
            # make every preview look identical again.
            loaded[path.stem.lower()] = bpy.data.images.load(str(path), check_existing=False)
        except Exception as exc:
            log("error", f"Cannot load texture {path.name}: {exc}")
    if not loaded:
        return 0

    fallback = next(
        (img for name, img in loaded.items() if "diff" in name),
        next(iter(loaded.values())),
    )

    fixed = 0
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != "TEX_IMAGE":
                continue
            node_name = node.name.lower()
            if node_name != "diffusesampler" and not node_name.startswith("diffuse"):
                continue
            img = node.image
            if img is not None and img.has_data:
                continue
            key = img.name.lower() if img else ""
            while "." in key and key.rsplit(".", 1)[-1].isdigit():
                key = key.rsplit(".", 1)[0]
            if key.endswith(".dds"):
                key = key[:-4]
            node.image = loaded.get(key, fallback)
            fixed += 1
    if fixed:
        log("info", f"Applied {fixed} diffuse texture(s) to imported materials")
    return fixed


_OPT_YTD_CACHE: dict[tuple[str, int], bytes] = {}
_OPT_STATS = {"files": 0, "before": 0, "after": 0}


class _BytesDataSource:
    """Minimal DataSource compatible with szio's texture importer."""

    def __init__(self, data: bytes, name: str):
        self.data = data
        self.name = name

    def read_bytes(self) -> bytes:
        return self.data

    def open(self):
        return io.BytesIO(self.data)


def downsample_uncompressed_dds(data: bytes, max_size: int):
    """Downsample a mip-less uncompressed DDS by averaging 2x2 pixel blocks.

    Returns ``(bytes, width, height)`` or ``None`` for compressed/unknown
    formats, which cannot be resized safely without a full re-encode.
    """
    try:
        import numpy as np
        from szio.dds import DDS_HEADER, DdsFile, _format_layout, _mip_size

        dds = DdsFile.from_buffer(bytearray(data))
        block, bits = _format_layout(dds)
        if block is not None or not bits or bits % 8:
            return None
        bpp = bits // 8
        header_size = len(data) - len(dds.pixel_data)
        width, height = dds.width, dds.height
        pitch = (width * bits + 7) // 8
        pixels = np.frombuffer(bytes(dds.pixel_data), dtype=np.uint8)[: pitch * height]
        pixels = pixels.reshape(height, pitch)

        while (width > max_size or height > max_size) and width > 2 and height > 2:
            new_width, new_height = max(1, width // 2), max(1, height // 2)
            cut = pixels[: new_height * 2, : new_width * 2 * bpp]
            pixels = cut.reshape(new_height, 2, new_width, 2, bpp).mean(axis=(1, 3)).round().astype(np.uint8)
            width, height = new_width, new_height

        out = bytearray(data[:header_size]) + pixels.tobytes()
        header = DDS_HEADER.from_buffer(out, 4)
        header.dwWidth = width
        header.dwHeight = height
        header.dwMipMapCount = 1
        header.dwPitchOrLinearSize = _mip_size(width, height, None, bits)
        del header
        return bytes(out), width, height
    except Exception:
        return None


def optimized_ytd_bytes(source, max_size: int = 512) -> bytes:
    """Return a .ytd whose textures are at most ``max_size`` pixels wide/tall.

    First tries ``szio.dds.DdsFile.drop_mip()``, which discards the top mip and
    keeps the original compression and mip chain. For textures without mips it
    averages 2x2 blocks of uncompressed pixels. Neither path re-encodes with a
    different format, so colours and alpha stay intact.
    """
    raw = read_bytes(source)
    key = (source_string(source), int(max_size))
    cached = _OPT_YTD_CACHE.get(key)
    if cached is not None:
        return cached

    optimized = raw
    try:
        from szio import save_asset, try_load_asset
        from szio.dds import DdsFile
        from szio.gta5.assets import AssetFormat, AssetTarget, AssetVersion, SaveOptions

        asset, _ = try_load_asset(source, return_target=True)
        any_changed = False
        for tex in (getattr(asset, "textures", {}) or {}).values():
            try:
                data = bytearray(read_bytes(tex.data))
                dds = DdsFile.from_buffer(bytearray(data))
                width, height = dds.width, dds.height
                changed = False
                while width > max_size or height > max_size:
                    try:
                        mips = dds.complete_mip_count()
                    except Exception:
                        break
                    if mips <= 1:
                        resized = downsample_uncompressed_dds(bytes(data), max_size)
                        if resized:
                            data, width, height = resized
                            changed = True
                        break
                    data = bytearray(dds.drop_mip())
                    dds = DdsFile.from_buffer(bytearray(data))
                    width, height = dds.width, dds.height
                    changed = True
                if changed:
                    tex.data = _BytesDataSource(bytes(data), f"{tex.name}.dds")
                    tex.width = width
                    tex.height = height
                    any_changed = True
            except Exception:
                continue

        if any_changed:
            with tempfile.TemporaryDirectory() as tmp:
                save_asset(
                    asset,
                    [AssetTarget(AssetFormat.NATIVE, AssetVersion.GEN8)],
                    Path(tmp),
                    "wct_optimized",
                    SaveOptions(),
                )
                candidate = Path(tmp) / "wct_optimized.ytd"
                if candidate.is_file() and candidate.stat().st_size:
                    optimized = candidate.read_bytes()
    except Exception as exc:
        log("error", f"Cannot optimize texture {Path(str(source)).name}: {exc}")

    _OPT_YTD_CACHE[key] = optimized
    _OPT_STATS["files"] += 1
    _OPT_STATS["before"] += len(raw)
    _OPT_STATS["after"] += len(optimized)
    return optimized


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

    ytd_path = work_dir / f"{model_name}.ytd"
    dds_files = extract_ytd_dds(ytd_path, work_dir / f"{model_name}_textures")

    files = [{"name": f"{model_name}.ydr"}]
    if ytd_path.is_file():
        files.append({"name": f"{model_name}.ytd"})

    bpy.ops.sollumz.import_assets(
        directory=str(work_dir) + os.sep,
        files=files,
        use_custom_settings=True,
    )
    if mesh_bounds() is None:
        return False

    apply_diffuse_textures(dds_files)
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
# Polygon optimization
# ---------------------------------------------------------------------------

_POLY_STATS = {"meshes": 0, "before": 0, "after": 0}


def triangles_in(asset) -> int:
    total = 0
    for models in (getattr(asset, "models", None) or {}).values():
        for model in models:
            for geo in getattr(model, "geometries", None) or []:
                ib = getattr(geo, "index_buffer", None)
                if ib is not None:
                    total += len(ib) // 3
    return total


def add_temporary_skeleton(drawable) -> None:
    """Give a skinned drawable a minimal skeleton so Sollumz keeps skin weights."""
    ids = set()
    for models in (getattr(drawable, "models", None) or {}).values():
        for model in models:
            for geo in getattr(model, "geometries", None) or []:
                vb = getattr(geo, "vertex_buffer", None)
                if vb is not None and "BlendIndices" in (vb.dtype.names or []):
                    ids.update(int(x) for x in vb["BlendIndices"].ravel() if int(x) != 255)
    if not ids:
        return

    from szio.gta5.drawables import Skeleton, SkelBone, SkelBoneFlags

    real = sorted(ids)
    drawable.skeleton = Skeleton([
        SkelBone(
            name=f"bone_{i:03d}",
            tag=i,
            flags=SkelBoneFlags(0),
            position=Vector((0, 0, 0)),
            rotation=Quaternion((1, 0, 0, 0)),
            scale=Vector((1, 1, 1)),
            parent_index=-1 if i == real[0] else 0,
            translation_limit=None,
            rotation_limit=None,
        )
        for i in real
    ])


def optimize_polygons(drawable, ratio: float) -> None:
    """Decimate a drawable in place, preserving skin, UVs and shader indices.

    Sollumz is used for the actual collapse (its deleter respects UV/material
    seams), but only the resulting vertex/index buffers are copied back into
    the original szio asset. That keeps the original skeleton, bounds, shader
    group and other metadata untouched.
    """
    before = triangles_in(drawable)
    if ratio >= 1.0 or before < 200:
        return
    ensure_sollumz()
    original_skeleton = getattr(drawable, "skeleton", None)
    try:
        add_temporary_skeleton(drawable)
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            from szio import save_asset, try_load_asset
            from szio.gta5.assets import AssetFormat, AssetTarget, AssetVersion, SaveOptions

            targets = [AssetTarget(AssetFormat.NATIVE, AssetVersion.GEN8)]
            save_asset(drawable, targets, work, "wct_src", SaveOptions())
            clear_scene()
            bpy.ops.sollumz.import_assets(
                directory=str(work) + os.sep,
                files=[{"name": "wct_src.ydr"}],
                use_custom_settings=True,
            )
            meshes = [
                o for o in bpy.context.scene.objects
                if o.type == "MESH" and not is_collision(o)
            ]
            if not meshes:
                return
            for obj in meshes:
                mod = obj.modifiers.new("WCTOptimize", "DECIMATE")
                mod.ratio = ratio
                mod.delimit = {"NORMAL", "UV", "MATERIAL"}
                mod.use_collapse_triangulate = True
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=mod.name)

            bpy.ops.object.select_all(action="DESELECT")
            for obj in meshes:
                obj.select_set(True)
            out_dir = work / "out"
            out_dir.mkdir()
            bpy.ops.sollumz.export_assets(
                directory=str(out_dir) + os.sep,
                target_formats={"NATIVE"},
                target_versions={"GEN8"},
                limit_to_selected=True,
                use_custom_settings=True,
                direct_export=True,
                export_ytds=False,
                export_ymaps=False,
                export_ytyps=False,
            )
            products = sorted(out_dir.rglob("*.ydr"))
            if not products:
                return
            optimized, _ = try_load_asset(str(products[0]), return_target=True)

            def geometries_by_shader(asset):
                result = {}
                for models in (getattr(asset, "models", None) or {}).values():
                    for model in models:
                        for geo in getattr(model, "geometries", None) or []:
                            result.setdefault(getattr(geo, "shader_index", 0), []).append(geo)
                return result

            candidates = geometries_by_shader(optimized)
            for models in (getattr(drawable, "models", None) or {}).values():
                for model in models:
                    for geo in getattr(model, "geometries", None) or []:
                        pool = candidates.get(getattr(geo, "shader_index", 0)) or []
                        if not pool:
                            continue
                        new_geo = pool.pop(0)
                        new_vb = getattr(new_geo, "vertex_buffer", None)
                        old_vb = getattr(geo, "vertex_buffer", None)
                        if new_vb is None or old_vb is None:
                            continue
                        if set(new_vb.dtype.names or []) != set(old_vb.dtype.names or []):
                            continue
                        geo.vertex_buffer = new_vb
                        geo.index_buffer = new_geo.index_buffer
                        _POLY_STATS["meshes"] += 1
    except Exception as exc:
        log("error", f"Polygon optimization skipped: {exc}")
    finally:
        drawable.skeleton = original_skeleton
        after = triangles_in(drawable)
        _POLY_STATS["before"] += before
        _POLY_STATS["after"] += after
        clear_scene()


# ---------------------------------------------------------------------------
# Archetype (.ytyp) generation — makes models spawnable with RequestModel
# ---------------------------------------------------------------------------

def drawable_bounds(drawable):
    """Return (bb_min, bb_max, bs_center, bs_radius) from all geometry vertices.

    Uses the actual vertex buffer positions across every LOD, so the archetype
    bounds match the exported .ydr even after polygon decimation.
    """
    import numpy as np

    positions = []
    for models in (getattr(drawable, "models", None) or {}).values():
        for model in models:
            for geo in getattr(model, "geometries", None) or []:
                vb = getattr(geo, "vertex_buffer", None)
                if vb is None or "Position" not in (vb.dtype.names or []):
                    continue
                pos = np.asarray(vb["Position"], dtype=np.float64)
                if pos.size:
                    positions.append(pos.reshape(-1, 3)[:, :3])
    if not positions:
        return None
    all_pos = np.vstack(positions)
    bb_min = all_pos.min(axis=0)
    bb_max = all_pos.max(axis=0)
    center = (bb_min + bb_max) / 2.0
    radius = float(np.linalg.norm(bb_max - bb_min) / 2.0)
    return bb_min, bb_max, center, radius


def build_archetype(base_name: str, drawable):
    """Create a BASE/DRAWABLE CBaseArchetypeDef for a static prop."""
    from szio.gta5.archetypes import Archetype, ArchetypeAssetType, ArchetypeType
    from szio.types import Vector

    bounds = drawable_bounds(drawable)
    if bounds is None:
        return None
    bb_min, bb_max, center, radius = bounds
    return Archetype(
        name=base_name,
        type=ArchetypeType.BASE,
        flags=32,  # static prop
        lod_dist=100.0,
        special_attribute=0,
        hd_texture_dist=5.0,
        texture_dictionary=base_name,
        clip_dictionary="",
        drawable_dictionary="",
        physics_dictionary="",
        bb_min=Vector([float(x) for x in bb_min]),
        bb_max=Vector([float(x) for x in bb_max]),
        bs_center=Vector([float(x) for x in center]),
        bs_radius=radius,
        asset_name=base_name,
        asset_type=ArchetypeAssetType.DRAWABLE,
        extensions=[],
    )


def write_ytyp(directory: Path, base_name: str, drawable, save_asset, targets) -> bool:
    """Write one binary GEN8 .ytyp containing a single archetype for base_name."""
    from szio.gta5.archetypes import AssetMapTypes
    from szio.gta5.assets import SaveOptions

    archetype = build_archetype(base_name, drawable)
    if archetype is None:
        return False
    asset = AssetMapTypes(name=base_name, archetypes=[archetype])
    save_asset(asset, targets, directory, base_name, SaveOptions())
    return (directory / f"{base_name}.ytyp").is_file()


_STATIC_SHADER_NAME = "normal_spec"
_STATIC_SHADER_PRESET = "normal_spec.sps"


def normalize_static_prop(drawable) -> int:
    """Convert a ped-clothing drawable into a plain static-prop drawable.

    The exported .ydr already has no skeleton/skin weights, but it still uses
    ped shaders and ped vertex colours. Those are valid for the clothing system
    but can prevent FiveM from treating the asset as a normal object. This
    function rewrites the shader group to ``normal_spec.sps`` and resets the
    vertex colours, without touching geometry or UVs.

    Returns the number of shaders that were converted.
    """
    import numpy as np
    from szio.gta5.drawables import RenderBucket, ShaderParameter
    from szio.types import Vector

    drawable.skeleton = None
    for models in (getattr(drawable, "models", None) or {}).values():
        for model in models:
            model.has_skin = False
            model.matrix_count = 0
            model.bone_index = 0
            for geo in getattr(model, "geometries", None) or []:
                vb = getattr(geo, "vertex_buffer", None)
                if vb is None:
                    continue
                names = list(vb.dtype.names or [])
                drop = [n for n in ("BlendWeights", "BlendIndices") if n in names]
                keep = [n for n in names if n not in drop]
                if drop:
                    new = np.empty(len(vb), dtype=[(n, vb.dtype[n]) for n in keep])
                    for n in keep:
                        new[n] = vb[n]
                    vb = new
                    geo.vertex_buffer = vb
                if "Colour0" in (vb.dtype.names or []):
                    vb["Colour0"] = np.array([255, 128, 0, 255], dtype=vb["Colour0"].dtype)
                if "Colour1" in (vb.dtype.names or []):
                    vb["Colour1"] = 0

    shader_group = getattr(drawable, "shader_group", None)
    if shader_group is None or not shader_group.shaders:
        return 0

    for shader in shader_group.shaders:
        old = {str(p.name).lower(): p.value for p in shader.parameters}
        diffuse = str(old.get("diffusesampler", "") or "")
        bump = str(old.get("bumpsampler", "") or diffuse)
        spec = str(old.get("specsampler", "") or diffuse)
        shader.name = _STATIC_SHADER_NAME
        shader.preset_filename = _STATIC_SHADER_PRESET
        shader.render_bucket = RenderBucket.OPAQUE
        shader.parameters = [
            ShaderParameter("diffusesampler", diffuse),
            ShaderParameter("bumpsampler", bump),
            ShaderParameter("specsampler", spec),
            ShaderParameter("hardalphablend", Vector((1.0, 0.0, 0.0, 0.0))),
            ShaderParameter("usetessellation", Vector((0.0, 0.0, 0.0, 0.0))),
            ShaderParameter("wetnessmultiplier", Vector((1.0, 0.0, 0.0, 0.0))),
            ShaderParameter("bumpiness", Vector((1.0, 0.0, 0.0, 0.0))),
            ShaderParameter("specmapintmask", Vector((1.0, 0.0, 0.0, 0.0))),
            ShaderParameter("specularintensitymult", Vector((1.0, 0.0, 0.0, 0.0))),
            ShaderParameter("specularfalloffmult", Vector((100.0, 0.0, 0.0, 0.0))),
            ShaderParameter("specularfresnel", Vector((0.75, 0.0, 0.0, 0.0))),
        ]
    return len(shader_group.shaders)


def write_fxmanifest(out_root: Path, model_names: list[str]) -> None:
    """Write a resource fxmanifest registering every generated .ytyp."""
    lines = [
        "fx_version 'cerulean'",
        "game 'gta5'",
        "this_is_a_map 'yes'",
        "",
    ]
    for name in sorted(set(model_names)):
        lines.append(f"data_file 'DLC_ITYP_REQUEST' 'stream/{name}.ytyp'")
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "fxmanifest.lua").write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def source_preference(src, item: dict | None = None) -> tuple:
    """Rank sources so the file the ped actually wears wins over duplicates.

    For freemode props (``p_head``, ``p_eyes``, ...) the drawable index is the
    number in the filename and the ped uses the base file from
    ``streamedpedprops.rpf/mp_[mf]_freemode_01_p/p_<part>_NNN.ydd``.
    Themed DLC packs and loose add-ons often ship a file with the same name but
    a completely different model (e.g. a Christmas helmet instead of the base
    hat). Those must never win over the base source.
    """
    value = source_string(src).lower()
    item = item or {}
    part = str(item.get("part", "")).lower()
    body = str(item.get("body", "")).lower()
    is_prop = part.startswith("p_") or "/p_head_" in value or "/p_eyes_" in value

    if is_prop:
        if (
            "streamedpedprops.rpf" in value
            and ("/mp_m_freemode_01_p/" in value or "/mp_f_freemode_01_p/" in value)
        ):
            return (0, value)  # canonical base prop
        if ".rpf/" not in value and body in ("mp_m_freemode_01_p", "mp_f_freemode_01_p"):
            return (1, value)  # loose copy of the base prop
        if "mppatches_p.rpf" in value:
            return (2, value)  # patch variant, not what the ped wears
        return (3, value)  # themed DLC variants (only used when base is absent)

    if ".rpf/" not in value:
        return (0, value)  # loose add-on clothing file
    if "/mp_m_freemode_01/" in value or "/mp_f_freemode_01/" in value:
        return (1, value)
    if "x64w.rpf" in value or "x64v.rpf" in value:
        return (2, value)
    return (3, value)


def is_base_prop_source(src) -> bool:
    """True for the canonical freemode prop folder inside streamedpedprops.rpf."""
    value = source_string(src).lower()
    return (
        "streamedpedprops.rpf" in value
        and ("/mp_m_freemode_01_p/" in value or "/mp_f_freemode_01_p/" in value)
    )


def dedupe_sources(items: list[dict], key_fn, label: str) -> list[dict]:
    best: dict[tuple, tuple[tuple, dict]] = {}
    for item in items:
        key = key_fn(item)
        rank = source_preference(item["source"], item)
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

        # For drawables that come from the canonical base prop file, the ped
        # only uses texture variants a-h (indices 0-7) from that same folder.
        # Higher indices exist only in unrelated DLC packs and used to put
        # Christmas colours on the base hat. The wheel registry falls back to
        # texture 0, so those variants are deliberately not exported.
        if (
            item["part"] in ("p_head", "p_eyes")
            and item["collection"] == "np"
            and is_base_prop_source(item["source"])
        ):
            textures = [
                t for t in textures
                if t["texIndex"] <= 7 and is_base_prop_source(t["source"])
            ]

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

def patch_szio_skeleton_loader() -> None:
    """Make szio tolerate addon drawables with broken bone references.

    Several third-party .ydd packs contain a ``None`` entry in a bone's
    children. szio's ``_add_bone`` dereferences it unconditionally, so the
    whole drawable fails to load before any model or preview can be produced.
    Skipping only the invalid bones keeps the rest of the skeleton intact.
    """
    try:
        from szio.gta5.native.adapters import drawable as adapter
        if not callable(getattr(adapter, "_load_skeleton_native", None)):
            return
        if getattr(adapter, "_wct_skeleton_patched", False):
            return

        Vector = adapter.Vector
        Quaternion = adapter.Quaternion
        SkelBone = adapter.SkelBone
        SkelBoneFlags = adapter.SkelBoneFlags
        SkelBoneTranslationLimit = adapter.SkelBoneTranslationLimit
        SkelBoneRotationLimit = adapter.SkelBoneRotationLimit
        Skeleton = adapter.Skeleton
        pm = adapter.pm
    except Exception as exc:
        log("error", f"Could not patch szio skeleton loader: {exc}")
        return

    def translation_limit(limit):
        if limit is None:
            return None
        try:
            return SkelBoneTranslationLimit(Vector(limit.min), Vector(limit.max))
        except Exception:
            return None

    def rotation_limit(limit):
        if limit is None:
            return None
        try:
            assert limit.num_control_points == 1
            assert limit.degrees_of_freedom == pm.BoneJointDofs.JOINT_3_DOF
            assert limit.use_euler_angles
            p0, p1 = limit.control_points[:2]
            return SkelBoneRotationLimit(
                Vector((p0.max_swing, p0.min_twist, p0.max_twist)),
                Vector((p1.max_swing, p1.min_twist, p1.max_twist)),
            )
        except Exception:
            return None

    def robust_load_skeleton(d):
        bones = []

        def add_bone(b, parent_index):
            if b is None:
                return
            try:
                px, py, pz, _ = b.default_translation
                rx, ry, rz, rw = b.default_rotation
                sx, sy, sz, _ = b.default_scale
            except Exception:
                return
            index = len(bones)
            bones.append(SkelBone(
                name=b.name,
                tag=b.id,
                flags=SkelBoneFlags(b.degrees_of_freedom),
                position=Vector((px, py, pz)),
                rotation=Quaternion((rw, rx, ry, rz)),
                scale=Vector((sx, sy, sz)),
                parent_index=parent_index,
                translation_limit=translation_limit(b.translation_limit),
                rotation_limit=rotation_limit(b.rotation_limit),
            ))
            for child in b.children or []:
                if child is not None:
                    add_bone(child, index)

        try:
            if d.skeleton is not None and d.skeleton.root_bone is not None:
                add_bone(d.skeleton.root_bone, -1)
        except Exception as exc:
            log("error", f"Skeleton partially skipped: {exc}")
        return Skeleton(bones) if bones else None

    adapter._load_skeleton_native = robust_load_skeleton
    adapter._wct_skeleton_patched = True
    log("info", "Patched szio skeleton loader for invalid addon bones")


def export(job: dict) -> None:
    out_root = Path(job.get("outRoot", ""))
    if not str(out_root):
        raise RuntimeError("Output root is required")
    out_root.mkdir(parents=True, exist_ok=True)

    ensure_sollumz()
    patch_szio_skeleton_loader()
    _OPT_YTD_CACHE.clear()
    _OPT_STATS.update(files=0, before=0, after=0)
    _POLY_STATS.update(meshes=0, before=0, after=0)
    max_tex_size = int(job.get("maxTextureSize", 512) or 512)
    try:
        polygon_ratio = max(0.3, min(1.0, float(job.get("polygonRatio", 0.7) or 0.7)))
    except (TypeError, ValueError):
        polygon_ratio = 0.7
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
    exported_ytyps = 0
    failed = 0
    stream_names: dict[Path, set[str]] = {}

    try:
        from szio import VPath  # used only to restore cache entries if needed

        asset_cache: dict[str, object] = {}
        for index, task in enumerate(tasks, 1):
            label = f"{task['gender']} {task['part']} #{task['draw']:03d} / {task['slot']}"
            try:
                cache_key = source_string(task["ydd"])
                asset = asset_cache.get(cache_key)
                if asset is None:
                    loaded = try_load_asset(task["ydd"], return_target=True)
                    if not loaded:
                        raise RuntimeError(f"Cannot load {task['yddName']}")
                    asset, _ = loaded
                    if polygon_ratio < 1.0:
                        for _, source_drawable in (asset.drawables or {}).items():
                            optimize_polygons(source_drawable, polygon_ratio)
                    asset_cache[cache_key] = asset
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
                                    (work / f"{base_name}.ytd").write_bytes(
                                        optimized_ytd_bytes(tex["source"], max_tex_size)
                                    )
                                except Exception as exc:
                                    log("error", f"Cannot prepare texture {tex['name']}: {exc}")
                                    (work / f"{base_name}.ytd").write_bytes(read_bytes(tex["source"]))

                            if job.get("exportCollisions", False):
                                bounds = getattr(drawable, "bounds", None) or []
                                for bi, bound in enumerate(bounds):
                                    bname = base_name if len(bounds) == 1 else f"{base_name}_{bi}"
                                    try:
                                        save_asset(bound, targets, work, bname, SaveOptions())
                                    except Exception as exc:
                                        log("error", f"Collision export failed for {base_name}: {exc}")

                            ytyp_ok = False
                            if task["kind"] == "models":
                                try:
                                    ytyp_ok = write_ytyp(
                                        work, base_name, drawable, save_asset, targets
                                    )
                                except Exception as exc:
                                    log("error", f"Archetype export failed for {base_name}: {exc}")

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
                                for ext in (".ydr", ".ytd", ".ybn", ".ytyp"):
                                    for f in work.glob(f"*{ext}"):
                                        shutil.copy2(f, target_dir / f.name)
                                if (target_dir / f"{base_name}.ydr").is_file():
                                    exported_models += 1
                                    if ytyp_ok and (target_dir / f"{base_name}.ytyp").is_file():
                                        exported_ytyps += 1
                                    row["outputs"] = [
                                        source_string(p) for p in sorted(target_dir.glob(f"{base_name}.*"))
                                    ]
                                else:
                                    failed += 1
                                    log("error", f"Model file was not produced: {base_name}.ydr")

                                if ytyp_ok and (target_dir / f"{base_name}.ytyp").is_file():
                                    resource_root = target_dir.parents[3]
                                    stream_dir = resource_root / "stream"
                                    stream_dir.mkdir(parents=True, exist_ok=True)
                                    spawn_dir = work / "spawn"
                                    spawn_dir.mkdir(exist_ok=True)
                                    try:
                                        import copy

                                        spawn_drawable = copy.deepcopy(drawable)
                                        normalize_static_prop(spawn_drawable)
                                        names = ytd_texture_names(work / f"{base_name}.ytd")
                                        texture_name = next(
                                            (n for n in names if "_diff_" in n.lower()),
                                            names[0] if len(names) == 1 else None,
                                        )
                                        if texture_name:
                                            patch_diffuse_sampler(spawn_drawable, texture_name)
                                        save_asset(
                                            spawn_drawable, targets, spawn_dir,
                                            base_name, SaveOptions()
                                        )
                                        shutil.copy2(
                                            spawn_dir / f"{base_name}.ydr",
                                            stream_dir / f"{base_name}.ydr",
                                        )
                                    except Exception as exc:
                                        log(
                                            "error",
                                            f"Static prop conversion failed for {base_name}: {exc}",
                                        )
                                        shutil.copy2(
                                            work / f"{base_name}.ydr",
                                            stream_dir / f"{base_name}.ydr",
                                        )
                                    for ext in (".ytd", ".ytyp"):
                                        for f in work.glob(f"*{ext}"):
                                            shutil.copy2(f, stream_dir / f.name)
                                    stream_names.setdefault(resource_root, set()).add(base_name)
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

        for resource_root, names in sorted(stream_names.items()):
            write_fxmanifest(resource_root, list(names))
            log(
                "success",
                f"Spawnable resource ready: {resource_root} "
                f"({len(names)} archetype(s), fxmanifest + stream/)",
            )

        if _OPT_STATS["files"]:
            before_mb = _OPT_STATS["before"] / 1_000_000
            after_mb = _OPT_STATS["after"] / 1_000_000
            log(
                "success",
                f"Optimized {_OPT_STATS['files']} texture(s): "
                f"{before_mb:.1f} MB -> {after_mb:.1f} MB",
            )

        if _POLY_STATS["meshes"]:
            log(
                "success",
                f"Optimized {_POLY_STATS['meshes']} mesh(es): "
                f"{_POLY_STATS['before']} -> {_POLY_STATS['after']} triangles",
            )

        message = (
            f"Core completed: {exported_models} model(s), {exported_ytyps} archetype(s), "
            f"{exported_previews} preview(s), {failed} failed."
        )
        if _POLY_STATS["meshes"]:
            message += (
                f" Polygons: {_POLY_STATS['before']} -> {_POLY_STATS['after']}."
            )
        if _OPT_STATS["files"]:
            message += (
                f" Textures: {_OPT_STATS['before'] / 1_000_000:.1f} MB -> "
                f"{_OPT_STATS['after'] / 1_000_000:.1f} MB."
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
