use serde::Deserialize;
use serde::Serialize;
use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use tauri::{AppHandle, Emitter, Manager, Window};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ExportAssetsPayload {
    pub out_root: String,
    pub export_mode: String,
    pub model_categories: Vec<String>,
    pub preview_categories: Vec<String>,
    pub img_size: u32,
    pub img_format: String,
    pub gtav_path: Option<String>,
    pub addon_folders: Vec<String>,
    pub export_collisions: bool,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct JobPayload {
    pub out_root: String,
    pub export_mode: String,
    pub model_categories: Vec<String>,
    pub preview_categories: Vec<String>,
    pub img_size: u32,
    pub img_format: String,
    pub gtav_path: Option<String>,
    pub addon_folders: Vec<String>,
    pub export_collisions: bool,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase", tag = "kind")]
pub enum ProgressEvent {
    Started { message: String, total: u32 },
    Step { message: String, current: u32, total: u32 },
    Core { message: String, current: u32, total: u32 },
    Log { level: String, message: String },
    Finished { message: String, ok: bool },
}

#[derive(Debug, Deserialize)]
#[serde(tag = "kind")]
pub enum CoreEvent {
    // The Blender worker emits lowercase "kind" values. Renaming (not aliasing)
    // is required for internally-tagged enums to match them.
    #[serde(rename = "progress")]
    Progress { message: String, current: u32, total: u32 },
    #[serde(rename = "log")]
    Log { level: String, message: String },
    #[serde(rename = "done")]
    Done { ok: bool, message: String },
}

/// Blender's DDS cache prints these for every mip-less texture. They are
/// harmless (Sollumz falls back to uncompressed DDS and renders correctly),
/// but the word "failed" makes the export log look broken.
fn is_noisy_blender_warning(line: &str) -> bool {
    let lower = line.to_lowercase();
    (lower.contains("dds image") && lower.contains("failed to load data"))
        || (lower.contains("dds image") && lower.contains("falling back to uncompressed"))
}

fn category_to_folder(cat: &str) -> Option<&'static str> {
    match cat {
        "head" => Some("00_head"), "berd" => Some("01_masks"), "hair" => Some("02_hair"),
        "uppr" => Some("03_arms_gloves"), "lowr" => Some("04_pants"), "feet" => Some("06_shoes"),
        "teef" => Some("07_teeth"), "accs" => Some("05_bags"), "task" => Some("08_undershirts"),
        "decl" => Some("10_decals"), "jbib" => Some("11_tops"),
        "props_p_head" => Some("p0_hats"), "props_p_eyes" => Some("p1_glasses"),
        "props_p_ears" => Some("p2_ears"), "props_p_rwrist" => Some("p6_watches"),
        "props_p_lwrist" => Some("p7_bracelets"), _ => None,
    }
}

fn count_clothing_recursive(path: &PathBuf) -> (usize, usize) {
    fn walk(dir: &PathBuf, ydd: &mut usize, ytd: &mut usize) {
        if let Ok(entries) = fs::read_dir(dir) {
            for e in entries.flatten() {
                let p = e.path();
                if p.is_dir() { walk(&p, ydd, ytd); }
                else if p.is_file() {
                    if let Some(ext) = p.extension().and_then(|s| s.to_str()) {
                        match ext.to_ascii_lowercase().as_str() {
                            "ydd" => *ydd += 1,
                            "ytd" => *ytd += 1,
                            _ => {}
                        }
                    }
                }
            }
        }
    }
    let mut ydd = 0usize;
    let mut ytd = 0usize;
    walk(path, &mut ydd, &mut ytd);
    (ydd, ytd)
}

#[cfg(test)]
mod tests {
    use super::CoreEvent;

    #[test]
    fn parses_worker_events_lowercase() {
        let log: CoreEvent = serde_json::from_str(
            r#"{"kind":"log","level":"info","message":"hello"}"#,
        ).expect("log event");
        assert!(matches!(log, CoreEvent::Log { .. }));

        let done: CoreEvent = serde_json::from_str(
            r#"{"kind":"done","ok":true,"message":"ok"}"#,
        ).expect("done event");
        assert!(matches!(done, CoreEvent::Done { ok: true, .. }));
    }
}

#[tauri::command]
fn validate_gtav(path: String) -> bool {
    let p = PathBuf::from(&path);
    p.is_dir() && p.join("GTA5.exe").is_file() && p.join("update").join("x64").is_dir()
}

#[tauri::command]
fn validate_addon(path: String) -> (usize, usize) {
    count_clothing_recursive(&PathBuf::from(&path))
}

fn find_blender() -> Option<PathBuf> {
    // Explicit override first: useful for portable bundles or non-standard installs.
    for key in ["WCT_BLENDER", "BLENDER_EXE"] {
        if let Ok(value) = env::var(key) {
            let candidate = PathBuf::from(value);
            if candidate.is_file() {
                return Some(candidate);
            }
        }
    }

    if let Some(path_var) = env::var_os("PATH") {
        for dir in env::split_paths(&path_var) {
            let candidate = dir.join("blender.exe");
            if candidate.is_file() {
                return Some(candidate);
            }
        }
    }

    let mut roots = Vec::new();
    for key in ["ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"] {
        if let Some(value) = env::var_os(key) {
            roots.push(PathBuf::from(value));
        }
    }
    for root in roots {
        let base = root.join("Blender Foundation");
        if let Ok(entries) = fs::read_dir(base) {
            for entry in entries.flatten() {
                let candidate = entry.path().join("blender.exe");
                if candidate.is_file() {
                    return Some(candidate);
                }
            }
        }
    }
    None
}

fn write_job_file(job: &JobPayload) -> Result<PathBuf, String> {
    let json = serde_json::to_string(job).map_err(|e| e.to_string())?;
    let path = env::temp_dir().join(format!("wct-job-{}.json", std::process::id()));
    fs::write(&path, json).map_err(|e| format!("Cannot write core job file: {}", e))?;
    Ok(path)
}

fn emit(window: &Window, ev: ProgressEvent) {
    let _ = window.emit("wct://progress", ev);
}

#[tauri::command]
async fn export_assets(app: AppHandle, window: Window, payload: ExportAssetsPayload) -> Result<String, String> {
    if payload.out_root.trim().is_empty() {
        return Err("Output root is required.".into());
    }

    let root = PathBuf::from(&payload.out_root);
    fs::create_dir_all(&root).map_err(|e| format!("Cannot create output root: {}", e))?;

    let models_dir = root.join("models");
    let previews_dir = root.join("previews");
    let do_models = matches!(payload.export_mode.as_str(), "models" | "both");
    let do_previews = matches!(payload.export_mode.as_str(), "previews" | "both");

    let mut dirs: Vec<(String, PathBuf)> = Vec::new();
    if do_models {
        for c in &payload.model_categories {
            if let Some(folder) = category_to_folder(c) {
                for gender in ["male", "female"] {
                    dirs.push((
                        format!("model / {} / {}", c, gender),
                        models_dir.join(format!("whip_media_clothing_{}", gender))
                            .join("img").join("clothing").join(gender).join(folder),
                    ));
                }
            }
        }
    }
    if do_previews {
        for c in &payload.preview_categories {
            if let Some(folder) = category_to_folder(c) {
                for gender in ["male", "female"] {
                    dirs.push((
                        format!("preview / {} / {}", c, gender),
                        previews_dir.join(format!("whip_media_clothing_{}", gender))
                            .join("img").join("clothing").join(gender).join(folder),
                    ));
                }
            }
        }
    }
    if dirs.is_empty() {
        return Err("No valid categories selected.".into());
    }

    // Phase 1: shell preparation progress.
    let total_prep = dirs.len() as u32;
    emit(&window, ProgressEvent::Started { message: "Preparing output folders".into(), total: total_prep });
    for (i, (label, target)) in dirs.iter().enumerate() {
        let current = i as u32 + 1;
        emit(&window, ProgressEvent::Step { message: label.clone(), current, total: total_prep });
        if let Err(e) = fs::create_dir_all(target) {
            let msg = format!("FAILED: {} -> {}", target.display(), e);
            emit(&window, ProgressEvent::Log { level: "error".into(), message: msg.clone() });
            emit(&window, ProgressEvent::Finished { message: msg.clone(), ok: false });
            return Err(msg);
        }
        emit(&window, ProgressEvent::Log { level: "success".into(), message: format!("Ready: {}", target.display()) });
    }
    emit(&window, ProgressEvent::Finished { message: "Output folders ready. Starting core export…".into(), ok: true });

    // Phase 2: real core work runs inside Blender (Sollumz + szio are already there).
    let blender = find_blender().ok_or_else(|| {
        "Blender was not found. Install Blender and Sollumz, or set WCT_BLENDER to blender.exe."
            .to_string()
    })?;

    // Look next to the running executable first. This keeps the portable
    // build working from any folder (including the project root) without
    // depending on compile-time paths or Tauri's bundled resource layout.
    let script_name = "blender_export.py";
    let core_script = std::env::current_exe().ok()
        .and_then(|p| p.parent().map(|d| d.join("core").join(script_name)))
        .filter(|p| p.is_file())
        .or_else(|| {
            app.path().resource_dir().ok()
                .map(|p| p.join("core").join(script_name))
                .filter(|p| p.is_file())
        })
        .or_else(|| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .map(|p| p.join("core").join(script_name))
                .filter(|p| p.is_file())
        })
        .ok_or_else(|| format!("{} not found next to the executable", script_name))?;

    let job = JobPayload {
        out_root: payload.out_root.clone(),
        export_mode: payload.export_mode.clone(),
        model_categories: payload.model_categories.clone(),
        preview_categories: payload.preview_categories.clone(),
        img_size: payload.img_size,
        img_format: payload.img_format.clone(),
        gtav_path: payload.gtav_path.clone(),
        addon_folders: payload.addon_folders.clone(),
        export_collisions: payload.export_collisions,
    };
    let job_file = write_job_file(&job)?;

    // Persist the full export log next to the outputs so it can be inspected
    // after the app is closed. Both stdout (worker events) and stderr (Blender
    // diagnostics) are appended here.
    let log_path = PathBuf::from(&payload.out_root).join("wct_export.log");
    let log_file = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
        .ok()
        .map(Mutex::new)
        .map(Arc::new);
    if let Some(writer) = &log_file {
        if let Ok(mut f) = writer.lock() {
            let _ = writeln!(f, "\n===== export started =====");
        }
    }

    emit(&window, ProgressEvent::Started { message: "Starting Blender core process".into(), total: 1 });

    let mut command = Command::new(&blender);
    command
        .arg("--background")
        .arg("--python")
        .arg(&core_script)
        .arg("--")
        .arg(&job_file)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let mut child = command.spawn()
        .map_err(|e| format!("Failed to start Blender core: {}", e))?;

    let stderr = child.stderr.take().ok_or_else(|| "No stderr from Blender core".to_string())?;
    let stderr_window = window.clone();
    let stderr_log = log_file.clone();
    let stderr_thread = thread::spawn(move || {
        for line in BufReader::new(stderr).lines().flatten() {
            let line = line.trim();
            if line.is_empty() { continue; }
            if let Some(writer) = &stderr_log {
                if let Ok(mut f) = writer.lock() { let _ = writeln!(f, "[blender] {}", line); }
            }
            if is_noisy_blender_warning(line) { continue; }
            let lower = line.to_lowercase();
            // Blender prints non-fatal texture-cache warnings as ERROR; keep them
            // visible but do not paint the whole log red. Real failures come from
            // the worker's JSON "error" events.
            let level = if lower.contains("traceback") || lower.contains("python error") { "error" } else { "info" };
            emit(&stderr_window, ProgressEvent::Log { level: level.into(), message: line.to_string() });
        }
    });

    let stdout = child.stdout.take().ok_or_else(|| "No stdout from Blender core".to_string())?;
    let mut final_message = String::new();
    let mut core_ok = false;
    for line in BufReader::new(stdout).lines().flatten() {
        let original = line.trim();
        if original.is_empty() { continue; }
        if let Some(writer) = &log_file {
            if let Ok(mut f) = writer.lock() { let _ = writeln!(f, "{}", original); }
        }
        let line = original.strip_prefix("WCT_JSON:").unwrap_or(original);
        match serde_json::from_str::<CoreEvent>(line) {
            Ok(CoreEvent::Progress { message, current, total }) => {
                emit(&window, ProgressEvent::Core { message, current, total });
            }
            Ok(CoreEvent::Log { level, message }) => {
                emit(&window, ProgressEvent::Log { level: level.clone(), message: message.clone() });
                if level == "error" { final_message = message; }
            }
            Ok(CoreEvent::Done { ok, message }) => {
                core_ok = ok;
                final_message = message;
            }
            Err(_) => {
                emit(&window, ProgressEvent::Log { level: "info".into(), message: original.to_string() });
            }
        }
    }

    let status = child.wait().map_err(|e| e.to_string())?;
    let _ = stderr_thread.join();
    let _ = fs::remove_file(&job_file);

    let log_note = format!("Export log saved to {}", log_path.display());
    if let Some(writer) = &log_file {
        if let Ok(mut f) = writer.lock() {
            let _ = writeln!(f, "===== export finished: {} =====", final_message);
        }
    }
    emit(&window, ProgressEvent::Log { level: "info".into(), message: log_note.clone() });

    if !status.success() || !core_ok {
        let err = if final_message.is_empty() { format!("Core exited with status {}", status) } else { final_message };
        emit(&window, ProgressEvent::Finished { message: err.clone(), ok: false });
        return Err(err);
    }

    let finished = format!("{} {}", final_message, log_note);
    emit(&window, ProgressEvent::Finished { message: finished.clone(), ok: true });
    Ok(finished)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .invoke_handler(tauri::generate_handler![validate_gtav, validate_addon, export_assets])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
