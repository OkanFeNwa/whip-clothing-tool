# Building Whip Clothing Tool (Windows)

## Prerequisites

- **Node.js** (LTS) + npm
- **Rust** (stable) + Cargo (required for Tauri). Install from https://rustup.rs and ensure `cargo` is on PATH.
- **Visual Studio Build Tools** (C++ workload) if required by Tauri on Windows.

Blender + Sollumz are required at **runtime**, not at build time.

## Install JS dependencies

```powershell
npm install
```

## Run in development

```powershell
npm run tauri dev
```

## Build portable exe

```powershell
npm run tauri build
```

Tauri is configured with `bundle.active = false`, so the output is a standalone executable:

```text
src-tauri/target/release/whip_clothing_tool.exe
src-tauri/target/release/core/blender_export.py
```

Copy the `core/` folder next to the exe when distributing the portable build.

## Runtime discovery

The app looks for Blender in this order:

1. `WCT_BLENDER` / `BLENDER_EXE` environment variable
2. `blender.exe` on `PATH`
3. Standard Blender Foundation folders under `Program Files`, `Program Files (x86)` and `LOCALAPPDATA`

No game path, server path or user path is baked into the app.

## No hardcoded paths

Users select the GTA V Legacy folder, add-on folders and output root in the UI. Do not add machine-specific defaults to the source or documentation.
