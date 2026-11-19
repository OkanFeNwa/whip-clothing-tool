#!/usr/bin/env python3
"""Regression check for the freemode-prop export rules.

Run with any Python 3.x (no Blender required):

    python scripts/verify_prop_export_rules.py E:/whip/output/.wct_cache/rpf_index.json
    python scripts/verify_prop_export_rules.py E:/whip/output/.wct_cache/rpf_index.json \
        "E:/whip/txData/WHIP_FB4EC1.base/resources/[clothing]"

It stubs the Blender-only modules, imports ``core/blender_export.py`` and
checks that build_tasks() still applies the rules that keep dropped hats/glasses
identical to the worn item:

  1. base props export ONLY texture variants 0-7 from the base RPF; DLC-added
     indices 8-25 are left to the registry's texture-0 fallback;
  2. every prop drawable keeps ranked .ydd alternatives, so a 4-vertex
     placeholder can be replaced by real geometry when one exists;
  3. the export key includes the ped collection, so two addon packs reusing
     the same local index do not overwrite each other;
  4. the exporter's collection token equals the token the client computes from
     GetPedCollectionNameFromProp (shared/slots.lua:collectionToken).

Pass addon ``stream/`` folders as extra arguments to check collection-aware
discovery as well.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path


def load_worker():
    # Blender modules are only needed at import time by the worker.
    for name in ("bpy", "mathutils", "addon_utils"):
        sys.modules.setdefault(name, types.ModuleType(name))
    mathutils = sys.modules["mathutils"]
    for name in ("Matrix", "Quaternion", "Vector"):
        setattr(mathutils, name, type(name, (), {}))

    worker = Path(__file__).resolve().parent.parent / "core" / "blender_export.py"
    spec = importlib.util.spec_from_file_location("wct_worker", str(worker))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build(module, index, ydds, ytds):
    return module.build_tasks(
        {
            "exportMode": "models",
            "modelCategories": ["props_p_head", "props_p_eyes"],
            "previewCategories": [],
        },
        ydds,
        ytds,
        Path("."),
    )


def check(label, tasks, module):
    failures: list[str] = []

    high_textures = sum(
        1
        for t in tasks
        if module.is_base_prop_source(t["ydd"])
        and t["part"] in ("p_head", "p_eyes")
        and any(tex["texIndex"] > 7 for tex in t["textures"])
    )
    print(f"[{label}] base-prop tasks with texture index > 7: {high_textures}")
    if high_textures:
        failures.append(f"{label}: base props must only export texture indices 0-7")

    base_textures = sum(
        1
        for t in tasks
        if module.is_base_prop_source(t["ydd"])
        and t["part"] in ("p_head", "p_eyes")
        and any(tex["texIndex"] <= 7 for tex in t["textures"])
    )
    print(f"[{label}] base-prop tasks with texture indices 0-7: {base_textures}")
    if base_textures == 0:
        failures.append(f"{label}: base texture variants (0-7) are being discarded")

    missing = [t for t in tasks if not t.get("yddAlternatives")]
    print(f"[{label}] tasks without .ydd alternatives: {len(missing)}")
    if missing:
        failures.append(f"{label}: some props have no ranked .ydd alternatives")

    eyes000 = [
        t for t in tasks
        if t["gender"] == "male" and t["part"] == "p_eyes" and t["draw"] == 0
    ]
    alt_count = len(eyes000[0]["yddAlternatives"]) if eyes000 else 0
    print(f"[{label}] male p_eyes #000 alternatives: {alt_count}")
    if alt_count < 2:
        failures.append(f"{label}: placeholder p_eyes_000.ydd has no DLC fallback candidate")

    bad_collection = [
        t for t in tasks if not isinstance(t.get("collection"), str) or not t["collection"]
    ]
    print(f"[{label}] tasks without a collection token: {len(bad_collection)}")
    if bad_collection:
        failures.append(f"{label}: some tasks have no collection token")

    # The exporter's model name is gender_slot_collection_draw[_di]_texture.
    # Colliding prefixes would silently overwrite one item with another.
    seen: dict[tuple, str] = {}
    collisions = 0
    for t in tasks:
        key = (t["gender"], t["slot"], t["collection"], t["draw"])
        for tex in t["textures"] or [None]:
            full = key + (tex["texIndex"] if tex else 0,)
            if full in seen:
                collisions += 1
            else:
                seen[full] = t["yddName"]
    print(f"[{label}] colliding model-name keys: {collisions}")
    if collisions:
        failures.append(f"{label}: two items map to the same model name")

    collections = sorted({t["collection"] for t in tasks})
    print(f"[{label}] collections: {len(collections)} -> {', '.join(collections[:12])}"
          + (" ..." if len(collections) > 12 else ""))
    return failures, collections


def runtime_token(name: str) -> str:
    """Mirror of ClothingWheel.collectionToken() in shared/slots.lua."""
    import re

    value = str(name or "").lower()
    if value == "" or "freemode_01" in value:
        return "np"
    value = re.sub(r"^mp_[mf]_", "", value)
    value = re.sub(r"^freemode_01_p_?", "", value)
    value = re.sub(r"^mp_[mf]_", "", value)
    value = re.sub(r"^p_", "", value)
    value = re.sub(r"[^a-z0-9]", "", value)
    return value or "np"


def check_runtime_tokens(module) -> list[str]:
    """The exporter must use the same token the client gets from game natives.

    Left side: collection name returned by GetPedCollectionNameFromProp.
    Right side: body/folder the exporter derives from an RPF or addon filename.
    A mismatch silently sends a drop to the generic model because the server
    cannot find the exported identity.
    """
    failures: list[str] = []
    cases = [
        ("mp_m_freemode_01", "mp_m_freemode_01_p"),
        ("mp_f_freemode_01", "mp_f_freemode_01_p"),
        ("mp_m_vinewood", "mp_m_freemode_01_p_mp_m_vinewood"),
        ("mp_f_gunrunning_01", "mp_f_freemode_01_p_mp_f_gunrunning_01"),
        ("mp_m_bikerdlc01", "mp_m_freemode_01_p_mp_m_bikerdlc_01"),
        ("mp_m_2023_01", "mp_m_freemode_01_p_mp_m_2023_01"),
        ("mp_m_npnew", "mp_m_freemode_01_p_mp_m_np_new"),
    ]
    for native, body in cases:
        want = runtime_token(native)
        got = module.collection_from_body(body)
        print(f"[token] {native:24} + {body:48} -> {got}")
        if got != want:
            failures.append(f"collection token mismatch: {body!r} -> {got}, runtime uses {want}")

    # Addon filenames use `body^part_draw.ydd`; the regex must strip at '^',
    # otherwise the part name leaks into the collection token.
    parsed = module.parse_source(
        "addon/stream/mp_m_freemode_01_p^p_head_044.ydd",
        "mp_m_freemode_01_p^p_head_044.ydd",
    )
    got = (parsed or {}).get("collection")
    print(f"[token] addon ^-filename -> {got}")
    if got != "np":
        failures.append(f"addon ^-filename token: {got!r}, expected 'np'")
    return failures


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: verify_prop_export_rules.py <rpf_index.json> [addon stream folder ...]")
        return 2

    index_path = Path(sys.argv[1])
    if not index_path.is_file():
        print(f"missing index: {index_path}")
        return 2

    module = load_worker()
    failures = check_runtime_tokens(module)
    index = json.loads(index_path.read_text(encoding="utf-8"))

    tasks = build(module, index, index["ydd"], index["ytd"])
    print(f"[base] tasks: {len(tasks)}")
    if not tasks:
        print("FAIL: build_tasks() returned no prop tasks")
        return 1
    base_failures, base_collections = check("base", tasks, module)
    failures.extend(base_failures)

    if len(sys.argv) > 2:
        addon_ydd, addon_ytd = module.scan_addons(sys.argv[2:])
        print(f"[addon] sources: {len(addon_ydd)} .ydd, {len(addon_ytd)} .ytd")
        combined = build(module, index, list(index["ydd"]) + addon_ydd,
                         list(index["ytd"]) + addon_ytd)
        print(f"[addon] tasks: {len(combined)}")
        addon_failures, addon_collections = check("addon", combined, module)
        failures.extend(addon_failures)
        if len(addon_collections) <= len(base_collections):
            failures.append("addon sources did not introduce any new collection token")
        else:
            new = sorted(set(addon_collections) - set(base_collections))
            print(f"[addon] new collections: {len(new)} -> {', '.join(new[:12])}"
                  + (" ..." if len(new) > 12 else ""))

    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1

    print(f"OK: {len(tasks)} base prop tasks, all export rules intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
