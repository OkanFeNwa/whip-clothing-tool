# Whip Clothing Tool

Whip Clothing Tool is a Windows **portable** desktop app to export GTA V clothing assets for **FiveM (WHIP)** workflows:

- Generate **preview images** with a fixed angle and lighting, transparent background, and selectable size/format.
- Export **model files** as **`.ydr` + `.ytd`** (plus collision files when the source actually contains them).
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

The executable is written to `src-tauri/target/release/whip_clothing_tool.exe`. Keep `core/blender_export.py` beside it in `target/release/core/` when copying the portable build elsewhere.

## Repository

Private repository intended for internal release.
