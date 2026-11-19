#!/usr/bin/env python3
"""Run core/blender_export.py's model export without launching Blender/TAURI.

Only .ydr/.ytd/.ytyp output is needed for FiveM world drops; previews require
Blender and are deliberately not supported here. The worker imports Blender
modules at import time, so they are stubbed before loading it.

Usage
-----
    python scripts/run_export_headless.py job.json

``job.json`` is the same object the GUI sends to the worker, e.g.:

    {
      "outRoot": "E:/whip/output_addon",
      "sourceMode": "both",
      "gtavPath": "G:/Games/Epic Games/GTAV",
      "addonFolders": [
        "E:/whip/txData/WHIP_FB4EC1.base/resources/[clothing]/ef_clothes_props/stream",
        "..."
      ],
      "exportMode": "models",
      "modelCategories": ["props_p_head", "props_p_eyes"],
      "previewCategories": [],
      "maxTextureSize": 512,
      "polygonRatio": 0.7,
      "exportCollisions": false
    }

The RPF index in ``<outRoot>/.wct_cache/rpf_index.json`` is reused when its
``game`` matches ``gtavPath``; delete it to force a full re-index.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_export_headless.py <job.json>")
        return 2

    job_path = Path(sys.argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8-sig"))

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

    # Model-only export never touches Blender operators. Polygon decimation is
    # an optional fidelity/perf optimisation that DOES use Blender; the old
    # shipped drops were not decimated either, so skip it in headless runs to
    # preserve the original geometry exactly.
    module.ensure_sollumz = lambda: None
    module.optimize_polygons = lambda drawable, ratio: None

    module.export(job)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
