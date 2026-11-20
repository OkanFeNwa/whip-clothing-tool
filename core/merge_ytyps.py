#!/usr/bin/env python3
"""merge_ytyps.py - turns the one-.ytyp-per-model files of an OLD export into a few big .ytyp files (no re-export needed).

GTA loads at most 3000 .ytyp files (MapTypesStore pool); thousands of single-model files crash the game with
"MapTypesStore Pool Full". Exports made by v0.2.1 and later already write big files; this script fixes the older ones.

Runs inside Blender (needs Sollumz):

    blender --background --python merge_ytyps.py -- "<...>\\models\\whip_media_clothing_male\\stream" "<...>\\whip_media_clothing_female\\stream"

For each stream folder: reads every per-model .ytyp, writes wctchunk_*.ytyp (250 archetypes each), moves the per-model files to
<resource>/ytyp_single (not streamed, kept in case something goes wrong) and rewrites the resource's fxmanifest.lua.
"""
from __future__ import annotations

import shutil
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_export as be  # noqa: E402  (its export worker only runs when it is the main script)


def merge(stream: Path) -> int:
    from szio import save_asset, try_load_asset
    from szio.gta5.assets import AssetFormat, AssetTarget, AssetVersion

    targets = [AssetTarget(AssetFormat.NATIVE, AssetVersion.GEN8)]
    singles = sorted(f for f in stream.glob("*.ytyp") if not f.name.startswith(be.YTYP_CHUNK_PREFIX))
    if not singles:
        print(f"[merge] {stream}: no per-model .ytyp files, nothing to do")
        return 0

    archetypes = []
    for f in singles:
        loaded = try_load_asset(f, return_target=True)
        if not loaded:
            raise RuntimeError(
                f"This Blender/Sollumz cannot read {f.name}. Re-export with Whip Clothing Tool 0.2.1 or later instead "
                f"(it writes the big .ytyp files directly)."
            )
        asset, _ = loaded
        found = list(getattr(asset, "archetypes", None) or [])
        if not found:
            raise RuntimeError(f"{f.name} holds no archetype")
        archetypes.extend(found)

    for old in stream.glob(be.YTYP_CHUNK_PREFIX + "*.ytyp"):
        old.unlink()
    count = be.write_ytyp_chunks(stream, stream.parent.name, archetypes, save_asset, targets, 0)
    if not count:
        raise RuntimeError("No .ytyp file was written")

    backup = stream.parent / "ytyp_single"
    backup.mkdir(exist_ok=True)
    for f in singles:
        shutil.move(str(f), str(backup / f.name))
    be.write_fxmanifest(stream.parent, [])
    print(f"[merge] {stream.parent.name}: {len(archetypes)} archetype(s) -> {count} .ytyp file(s); originals in {backup}")
    return count


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        print("[merge] usage: blender --background --python merge_ytyps.py -- <stream folder> [...]")
        return 1
    try:
        be.ensure_sollumz()
        for a in args:
            merge(Path(a))
        print("[merge] done")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[merge] FAILED: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
