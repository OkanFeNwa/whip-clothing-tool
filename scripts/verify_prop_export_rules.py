#!/usr/bin/env python3
"""Regression check for the freemode-prop export rules.

Run with any Python 3.x (no Blender required):

    python scripts/verify_prop_export_rules.py E:/whip/output/.wct_cache/rpf_index.json

It stubs the Blender-only modules, imports ``core/blender_export.py`` and
checks that build_tasks() still applies the two rules that keep dropped
hats/glasses identical to the worn item:

  1. base props export every wearable texture variant (0-25), including the
     DLC-added ones for the same drawable;
  2. every prop drawable keeps ranked .ydd alternatives, so a 4-vertex
     placeholder can be replaced by real geometry when one exists.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_prop_export_rules.py <path-to-rpf_index.json>")
        return 2

    index_path = Path(sys.argv[1])
    if not index_path.is_file():
        print(f"missing index: {index_path}")
        return 2

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

    index = json.loads(index_path.read_text(encoding="utf-8"))
    tasks = module.build_tasks(
        {
            "exportMode": "models",
            "modelCategories": ["props_p_head", "props_p_eyes"],
            "previewCategories": [],
        },
        index["ydd"],
        index["ytd"],
        Path("."),
    )

    failures: list[str] = []

    if not tasks:
        failures.append("build_tasks() returned no prop tasks")

    high_textures = sum(
        1
        for t in tasks
        if module.is_base_prop_source(t["ydd"])
        and t["part"] in ("p_head", "p_eyes")
        and any(tex["texIndex"] > 7 for tex in t["textures"])
    )
    print(f"base-prop tasks with texture index > 7: {high_textures}")
    if high_textures == 0:
        failures.append("DLC texture variants (8-25) are being discarded")

    missing_alternatives = [
        t for t in tasks if "yddAlternatives" not in t or not t["yddAlternatives"]
    ]
    print(f"tasks without .ydd alternatives: {len(missing_alternatives)}")
    if missing_alternatives:
        failures.append("some props have no ranked .ydd alternatives")

    eyes000 = [
        t
        for t in tasks
        if t["gender"] == "male" and t["part"] == "p_eyes" and t["draw"] == 0
    ]
    alt_count = len(eyes000[0]["yddAlternatives"]) if eyes000 else 0
    print(f"male p_eyes #000 alternatives: {alt_count}")
    if alt_count < 2:
        failures.append("placeholder p_eyes_000.ydd has no DLC fallback candidate")

    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1

    print(f"OK: {len(tasks)} prop tasks, all export rules intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
