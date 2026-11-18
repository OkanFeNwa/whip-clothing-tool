# Whip Clothing Tool

Whip Clothing Tool is a Windows **portable** desktop app to export GTA V clothing assets for **FiveM (WHIP)** workflows:

- Generate **preview images** with a fixed angle and lighting, transparent background, and selectable size/format.
- Export **model files** as **`.ydr` + `.ytd`** (plus collision files when the source actually contains them).
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

## Output layout

Choose one output root. The app splits it into:

```text
<output root>/
  models/whip_media_clothing_<male|female>/img/clothing/<gender>/<slot>/
  previews/whip_media_clothing_<male|female>/img/clothing/<gender>/<slot>/
  export_manifest.json
```

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
