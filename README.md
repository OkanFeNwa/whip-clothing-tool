# Whip Clothing Tool

Whip Clothing Tool is a Windows desktop app to export **GTA V clothing** assets for **FiveM (WHIP)** workflows:

- Generate **preview images** (same camera angle and lighting for consistency) with **transparent background**, in selectable **format** and **size**.
- Export **prop models** for dropping/throwing clothing items in-game: produces **`.ydr` + `.ytd`** (and optional collision files where applicable) into an **output folder you choose**.
- Supports **vanilla** assets (from GTA V Legacy RPFs), **addon packs** (folders containing clothing `.ydd`/`.ytd`), or **both**.
- Multi-language UI: **English, Italian, Spanish, French, German**.

> This tool is designed to be **installed** (installer-based). It does **not** assume any hardcoded WHIP server paths: you always pick input/output folders in the UI.

## Documentation (other languages)

- Italiano: [docs/i18n/README.it.md](docs/i18n/README.it.md)
- Español: [docs/i18n/README.es.md](docs/i18n/README.es.md)
- Français: [docs/i18n/README.fr.md](docs/i18n/README.fr.md)
- Deutsch: [docs/i18n/README.de.md](docs/i18n/README.de.md)

## What this tool does

### 1) Preview images (shop / clothing previews)
- Exports preview renders of clothing items with a **fixed angle and fixed lighting** (consistency-first).
- Background is **transparent**.
- You choose:
  - **Source mode**: `Vanilla only`, `Addon packs only`, or `Both`
  - **Output folder** (browse)
  - **Image size** (manual input, e.g. `256`, `512`, ...)
  - **Image format** (selector), typically `PNG` and/or `WebP` (and `JPEG` only if transparency is not required)
- For addon packs, the tool can read pack folders you select and infer output naming compatible with WHIP naming conventions where possible.

### 2) Prop models (for dropped/thrown clothing)
- Exports model files suitable for FiveM streaming: primarily **`.ydr` + `.ytd`** into a folder you choose.
- Optional: export **collision** data if the pipeline supports it for the selected asset type (see [Collisions](#collisions)).
- You choose output folders and paths manually (no hardcoded server directories).

## Key principles (important)

- **No hardcoded paths.** Every input/output location is selected in the app (file browser).
- **Installer distribution.** The project is meant to be built into an installer (MSI/NSIS) via Tauri bundling.
- **Include dependencies in the installer when feasible.** If the app needs external runtimes/tools, the installer/build pipeline should bundle or auto-install them (see [Prerequisites and bundled components](#prerequisites-and-bundled-components)).
- **Fast and lightweight app code.** Heavy work is delegated to external tools (Python, Blender) invoked as needed.

## Requirements (runtime)

Depending on the tasks you run, the app may require some components. The installer should include or guide installation of missing pieces:

- **Windows 10/11 (64-bit)**
- **GTA V Legacy** installation (required for vanilla RPF extraction)
- **Python 3.10+** (recommended) with packages used by the included core scripts (installed automatically by the installer/setup step when possible)
- **Blender 4.2+ / 5.x** (recommended) with **Sollumz** (required for certain render/export pipelines)
- Optional: GPU drivers up to date (for Blender rendering)

> If a required component is missing, the app should show a clear message and, when possible, offer to install/configure it.

## Collisions

FiveM object collisions depend on how the model is set up (often a `.ybn`/collision bounds). Whip’s behavior for throwable/dropped objects should be followed:

- If your pipeline can generate or attach valid collisions, enable export/copy of collision files into the output folder.
- If collisions are not available for a given asset, the tool should warn you (the item may behave incorrectly in-game).

The exact collision export path depends on the selected export method (RPF extraction vs Blender/Sollumz workflow). The UI will expose options when supported.

## Project structure (high level)

```
whip-clothing-tool/
  src-tauri/        # Tauri (Rust) desktop shell + commands
  src/              # Web UI (i18n, settings, job runners)
  core/             # Python/core scripts (model extraction, helpers)
  scripts/          # Build helpers, bundling notes
  docs/i18n/        # Translated documentation
  assets/           # Icons, templates
```

## Development

### Prerequisites (build machine)

- Node.js (LTS) + npm
- Rust (stable) + Cargo
- Python 3.10+
- (Optional) Blender + Sollumz for preview rendering pipelines

### Run in dev (once scaffold is complete)

```bash
npm install
npm run tauri dev
```

### Build installer (Windows)

```bash
npm run tauri build
```

The output installer will be produced by Tauri’s bundler (e.g. NSIS/MSI depending on configuration).

## Repository

This repository is intended to be published as a **private GitHub repository** (you can make it public later). Keep secrets out of git; use local config files ignored by `.gitignore`.

## License

TBD (add a `LICENSE` file before public release).