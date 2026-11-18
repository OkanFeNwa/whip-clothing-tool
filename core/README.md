# Core scripts

## `forge.py`

Extracts GTA V clothing drawables from RPF archives (via `szio`/`PyMateria`) into FiveM-streamable `.ydr` + `.ytd` pairs.

This script is copied from the Whip workspace toolchain (`whip_clothingwheel/tools/model_forge/forge.py`) for packaging into the Whip Clothing Tool project.

### Usage (standalone)

```powershell
python forge.py --reindex --game "G:\Games\Epic Games\GTAV"
python forge.py --list --slot hat --game "G:\Games\Epic Games\GTAV"
python forge.py --slot hat --drawable 0 --texture 0 --out "C:\path\to\output"
```

### Notes

- Requires Python 3.10+ and dependencies such as `szio` and `pymateria` (index from Cfx wheel repo) as used by the original tool.
- The desktop app will call this script with user-selected paths (no hardcoded directories).
