# Whip Clothing Tool

Whip Clothing Tool is a Windows **portable** desktop app to export GTA V clothing assets for **FiveM (WHIP)** workflows:

- Generate **preview images** with a fixed angle and lighting, transparent background, and selectable size/format.
- Export **model files** as **`.ydr` + `.ytd`** (plus collision files when the source actually contains them).
- **Automatically optimizes polygons** by about 30% with a decimation that respects UV, material and normal seams; skin weights, shaders, bounds and metadata are preserved.
- **Automatically optimizes textures** to 512 px before writing `.ytd` files, using the source compression and its mip chain (no re-encoding, colours and alpha preserved). The log reports the total MB saved.
- Support **vanilla** assets (GTA V Legacy RPFs), **addon packs** (loose `.ydd`/`.ytd` folders, scanned recursively), or **both**.
- Export every drawable/texture variant automatically, with output names generated from the source clothing name.
- Multi-language UI: **English, Italian, Spanish, French, German**.

The app is portable: there is no installer and no suggested GTA V path. You choose every input and the output root in the UI.

## Documentation (other languages)

- Italiano: [docs/i18n/README.it.md](docs/i18n/README.it.md)
- Español: [docs/i18n/README.es.md](docs/i18n/README.es.md)
- Français: [docs/i18n/README.fr.md](docs/i18n/README.fr.md)
- Deutsch: [docs/i18n/README.de.md](docs/i18n/README.de.md)

## Runtime requirements

- Windows 10/11 (64-bit)
- **Blender 4.2+/5.x** with the **Sollumz** add-on enabled
  - The app finds Blender on `PATH`, under the standard `Program Files/Blender Foundation` locations, or via the `WCT_BLENDER` environment variable pointing to `blender.exe`.
- GTA V Legacy installation only if you use the *Vanilla* or *Both* source mode

No system Python installation is required: the real export work runs inside Blender, which already provides `szio`, PyMateria and Sollumz.

## Quick start

1. Extract the portable ZIP anywhere. `whip_clothing_tool.exe` is at the **root** of the extracted folder (not inside a hidden build folder), with `core/` beside it.
2. Run `install-dependencies.ps1` once to install Blender and the Sollumz extension automatically:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1
   ```
   The script is idempotent: it detects an existing Blender, installs the latest Sollumz from its official GitHub release, enables it and verifies `szio`/`pymateria` inside Blender. Add `-Dev` to also install Node.js, Rust and the Visual Studio Build Tools if you want to rebuild the app.
3. Launch `whip_clothing_tool.exe` and choose your input/output folders in the UI.

If Blender is installed somewhere unusual, point the script at it with `-BlenderPath "C:\path\to\blender.exe"` or set `WCT_BLENDER` before launching the app.

## Speed and log noise

- **Parallel export.** The export runs several Blender processes at once (default: half of the CPU cores, 1 to 4). Set the environment variable `WCT_WORKERS` (1-8) to choose; `1` is the old single-process behaviour. The tasks of one source `.ydd` stay in one worker, the workers' manifests are merged into `export_manifest.json` and the `fxmanifest.lua` of each model resource is written from its `stream/` folder at the end. The very first export with a GTA V folder builds the archive index and uses one worker; the next ones are parallel. Output files and names are unchanged. Blender uses the GPU only for the preview renders, so the gain comes from the parallel processes.
- **Log.** Blender's `DDS image '' falling back to uncompressed` / `failed to load data` lines and `Image file "p_eyes_normal_012.dds" does not exist` (optional normal/specular maps the source model names but that are not in the texture file you export; also `givemechecker.dds`, a placeholder) are harmless. They are no longer shown line by line (the full text stays in `wct_export.log`); one summary line with the counts is shown at the end. A real failure is still an `error` line.

## Output layout

Choose one output root. The app splits it into:

```text
<output root>/
  models/whip_media_clothing_<male|female>/
    fxmanifest.lua
    stream/<model>.ydr
    stream/<model>.ytd
    stream/<model>.ytyp
    img/clothing/<gender>/<slot>/...
  previews/whip_media_clothing_<male|female>/img/clothing/<gender>/<slot>/
  export_manifest.json
  wct_export.log
```

The files under `img/clothing/` keep the original ped shaders for the WHIP clothing system. The files under `stream/` are normalised static props (`normal_spec.sps`, `Color 1 = #FF8000`, `Color 2 = #000000`) with a binary GEN8 `.ytyp` archetype each, so they can be spawned with `RequestModel()` / `CreateObject()`.

### Source selection for props

Freemode props are resolved from the **base** file the ped actually wears, not from the first DLC with a matching name:

- `streamedpedprops.rpf/mp_m_freemode_01_p/p_head_NNN.ydd` (male) or `mp_f_freemode_01_p/p_head_NNN.ydd` (female)
- glasses use `p_eyes_NNN.ydd` in the same folder
- the three-digit number is the drawable index; each prop `.ydd` has a single entry (index 0)
- textures `a`–`h` map to indices 0–7 and come from `p_head_diff_NNN_<letter>.ytd` in the same base folder (`p_eyes_diff_...` for glasses)
- texture indices above 7 are **not** exported for base drawables: those variants do not exist in the base folder, and the wheel registry falls back to texture 0 for them. There is no in-game evidence that a ped wears them, so this remains the default.
- the real texture name from the selected `.ytd` is baked into the spawned prop's `diffusesampler`, so a dropped prop shows the same colours as the worn item

DLC variants with the same filename are only used for drawable indices that do not exist in the base set. This prevents exporting a themed helmet in place of the base hat.

Some base prop files are **4-vertex placeholders** rather than real models (for example `p_eyes_000.ydd` in the base RPF, while DLC packs carry the actual glasses). During export the worker detects such placeholders and automatically falls back to the next-ranked DLC source with real geometry. If every candidate is a stub, the best one is exported instead of failing. The manifest's `source` field records the file actually used.

You can verify these rules against your RPF cache after any tool update:

```powershell
python scripts/verify_prop_export_rules.py E:/whip/output/.wct_cache/rpf_index.json
```

## Spawning the exported models

Copy each `models/whip_media_clothing_<gender>/` folder into your FiveM server's `resources/` folder and start it in `server.cfg`. The generated `fxmanifest.lua` contains `this_is_a_map 'yes'` and one `data_file 'DLC_ITYP_REQUEST' 'stream/<model>.ytyp'` line per model — do not remove them.

```lua
-- example client usage
local model = `male_p0_np_005_00`
RequestModel(model)
while not HasModelLoaded(model) do Wait(0) end
local obj = CreateObject(model, x, y, z, true, true)
SetModelAsNoLongerNeeded(model)
```

**After adding or replacing files in `stream/`, every client must fully reconnect to the server.** A resource `refresh` + `restart` is not enough — FiveM clients keep the previously downloaded files in their cache until they reconnect. If `RequestModel` still fails after a clean reconnect and the archetype is registered, the tool falls back to the `prop_cap_01` model.

## Export log

Every export appends its full worker output to `<output root>/wct_export.log`. Non-fatal Blender DDS cache warnings (`failed to load data from file` / `falling back to uncompressed`) are kept in the file but hidden in the app, because all textures still render correctly.

## Collisions

If a source drawable contains collision bounds and **Export collisions** is enabled, the worker writes matching `.ybn` files next to the `.ydr`/`.ytd` pair. If the source has no bounds, no collision file is invented.

## Project structure

```text
whip-clothing-tool/
  src-tauri/        # Tauri (Rust) shell, folder validation, Blender process launcher
  src/              # React UI with EN/IT/ES/FR/DE translations
  core/             # Blender export worker + optional standalone helpers
  docs/i18n/        # Translated documentation
```

## Development

```bash
npm install
npm run tauri dev
```

## Build (portable Windows exe)

```bash
npm run tauri build
```

The executable is first written to `src-tauri/target/release/whip_clothing_tool.exe`; the packaging step then copies it to the project root as `whip_clothing_tool.exe`, next to `core/`. Always keep `core/blender_export.py` beside the exe when copying the portable build elsewhere.

## Repository

Private repository intended for internal release.
