# Building Whip Clothing Tool (Windows)

## Prerequisites

- **Node.js** (LTS) + npm
- **Rust** (stable) + Cargo (required for Tauri). Install from https://rustup.rs and ensure `cargo` is on PATH.
- **Visual Studio Build Tools** (C++ workload) if required by Tauri on Windows.
- **Python 3.10+** (for `core/forge.py`). The installer should bundle Python or guide the user to install it.

## Install JS dependencies

```powershell
cd E:\whip\tools\whip-clothing-tool
npm install
```

## Run in development

```powershell
npm run tauri:dev
```

## Build installer

```powershell
npm run tauri:build
```

Tauri outputs installers under `src-tauri/target/release/bundle/` (NSIS/MSI depending on configuration).

## Bundling notes (important)

- **No hardcoded paths**: users select GTA V Legacy, addon folders, and output folders in the app.
- **Ship `core/forge.py`** with the app resources if you call it from the bundled app (configure Tauri `resources` in `tauri.conf.json` when wiring the final pipeline).
- **Python runtime**: prefer an installer that either (a) bundles an embeddable Python + dependencies, or (b) runs a first-run setup that installs requirements. Document this in the final installer UX.
- **Blender/Sollumz**: optional for some workflows; the app should detect presence and show instructions/download links. Do not assume paths.

## Icon placeholders

Replace files in `src-tauri/icons/` with real app icons before release.
