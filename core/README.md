# Core scripts

## `blender_export.py`

The real export worker used by the desktop app. It runs inside Blender:

```powershell
blender --background --python blender_export.py -- job.json
```

It scans loose add-on folders and/or vanilla RPF archives, converts every drawable/texture variant into WHIP-compatible `.ydr` + `.ytd` files, optionally writes `.ybn` collisions, renders transparent previews with fixed lighting/camera, and emits NDJSON progress events on stdout.

Blender provides the required modules (`szio`, PyMateria, Sollumz). No system Python packages are needed.

## `forge.py`

Original standalone RPF extraction helper kept for debugging. It has no built-in game path: pass `--game` or set `WCT_GTAV_PATH`.

```powershell
python forge.py --reindex --game "<your GTA V Legacy folder>"
python forge.py --list --slot hat --game "<your GTA V Legacy folder>"
```

## `export_core.py`

Optional dependency-free CLI bridge that finds Blender and runs `blender_export.py`. The Tauri app calls Blender directly and does not need this script at runtime.
