use serde::Deserialize;
use serde::Serialize;
use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
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
    pub worker_index: u32,
    pub worker_count: u32,
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

/// State shared by the worker threads of one export.
struct Shared {
    progress: Mutex<Vec<(u32, u32)>>,
    done: Mutex<Vec<(bool, String)>>,
    last_error: Mutex<String>,
    missing_maps: AtomicUsize,
    missing_other: AtomicUsize,
}

/// A Blender line that is not worth showing: it is counted and left to the log file. Returns true when it was one.
/// Blender prints these on stdout as well as stderr, so both streams ask.
fn note_noise(line: &str, shared: &Shared) -> bool {
    if is_noisy_blender_warning(line) {
        return true;
    }
    let lower = line.to_lowercase();
    if lower.contains("image file") && lower.contains("does not exist") {
        if lower.contains("_normal_") || lower.contains("_spec_") {
            shared.missing_maps.fetch_add(1, Ordering::Relaxed);
        } else {
            shared.missing_other.fetch_add(1, Ordering::Relaxed);
        }
        return true;
    }
    false
}

/// With several workers: joins their manifests into export_manifest.json and writes the fxmanifest of each model
/// resource from its stream folder. Returns how many resources got one.
fn merge_outputs(root: &PathBuf) -> Result<usize, String> {
    let mut parts: Vec<PathBuf> = Vec::new();
    if let Ok(rd) = fs::read_dir(root) {
        for e in rd.flatten() {
            let p = e.path();
            let name = p.file_name().and_then(|s| s.to_str()).unwrap_or("").to_string();
            if name.starts_with("export_manifest.part") && name.ends_with(".json") {
                parts.push(p);
            }
        }
    }
    parts.sort();
    let mut rows: Vec<serde_json::Value> = Vec::new();
    for p in &parts {
        let text = fs::read_to_string(p).map_err(|e| format!("{}: {}", p.display(), e))?;
        let value: serde_json::Value = serde_json::from_str(&text).map_err(|e| format!("{}: {}", p.display(), e))?;
        if let Some(list) = value.as_array() {
            rows.extend(list.iter().cloned());
        }
    }
    rows.sort_by_key(|r| {
        (
            r.get("name").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            r.get("kind").and_then(|v| v.as_str()).unwrap_or("").to_string(),
        )
    });
    let merged = serde_json::to_string_pretty(&rows).map_err(|e| e.to_string())?;
    fs::write(root.join("export_manifest.json"), merged).map_err(|e| e.to_string())?;
    for p in &parts {
        let _ = fs::remove_file(p);
    }

    let mut written = 0usize;
    if let Ok(rd) = fs::read_dir(root.join("models")) {
        for e in rd.flatten() {
            let resource = e.path();
            let stream = resource.join("stream");
            if !stream.is_dir() {
                continue;
            }
            let mut names: Vec<String> = Vec::new();
            if let Ok(files) = fs::read_dir(&stream) {
                for f in files.flatten() {
                    let fp = f.path();
                    if fp.extension().and_then(|s| s.to_str()) == Some("ytyp") {
                        if let Some(stem) = fp.file_stem().and_then(|s| s.to_str()) {
                            names.push(stem.to_string());
                        }
                    }
                }
            }
            names.sort();
            let mut text = String::from("fx_version 'cerulean'\ngame 'gta5'\nthis_is_a_map 'yes'\n\n");
            for n in &names {
                text.push_str(&format!("data_file 'DLC_ITYP_REQUEST' 'stream/{}.ytyp'\n", n));
            }
            fs::write(resource.join("fxmanifest.lua"), text).map_err(|e| e.to_string())?;
            written += 1;
        }
    }
    Ok(written)
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

fn write_job_file(job: &JobPayload, worker: u32) -> Result<PathBuf, String> {
    let json = serde_json::to_string(job).map_err(|e| e.to_string())?;
    let path = env::temp_dir().join(format!("wct-job-{}-{}.json", std::process::id(), worker));
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

    // How many Blender processes share the work. WCT_WORKERS overrides; default is half the cores (1 to 4).
    // The first run with GTA V builds the archive index, which only one worker may do (they would write the same file).
    let cache_ready = root.join(".wct_cache").join("rpf_index.json").is_file();
    let needs_index = payload.gtav_path.as_deref().map(|p| !p.trim().is_empty()).unwrap_or(false);
    let mut workers: u32 = env::var("WCT_WORKERS")
        .ok()
        .and_then(|v| v.trim().parse::<u32>().ok())
        .unwrap_or_else(|| {
            let cores = thread::available_parallelism().map(|n| n.get() as u32).unwrap_or(2);
            (cores / 2).clamp(1, 4)
        })
        .clamp(1, 8);
    if needs_index && !cache_ready && workers > 1 {
        workers = 1;
        emit(&window, ProgressEvent::Log {
            level: "info".into(),
            message: "First export with GTA V: building the archive index with one worker. The next exports run in parallel.".into(),
        });
    }

    // Chunked .ytyp files of an earlier export would double up with this run's: start clean.
    if let Ok(rd) = fs::read_dir(&models_dir) {
        for e in rd.flatten() {
            if let Ok(files) = fs::read_dir(e.path().join("stream")) {
                for f in files.flatten() {
                    let fp = f.path();
                    let n = fp.file_name().and_then(|s| s.to_str()).unwrap_or("");
                    if n.starts_with("wctchunk_") && n.ends_with(".ytyp") {
                        let _ = fs::remove_file(&fp);
                    }
                }
            }
        }
    }

    let mut job_files: Vec<PathBuf> = Vec::new();
    for i in 0..workers {
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
            worker_index: i,
            worker_count: workers,
        };
        job_files.push(write_job_file(&job, i)?);
    }

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
            let _ = writeln!(f, "\n===== export started ({} worker(s)) =====", workers);
        }
    }

    emit(&window, ProgressEvent::Started { message: format!("Starting {} Blender core process(es)", workers), total: 1 });

    let shared = Arc::new(Shared {
        progress: Mutex::new(vec![(0, 0); workers as usize]),
        done: Mutex::new(Vec::new()),
        last_error: Mutex::new(String::new()),
        missing_maps: AtomicUsize::new(0),
        missing_other: AtomicUsize::new(0),
    });

    let mut children: Vec<Child> = Vec::new();
    let mut threads: Vec<thread::JoinHandle<()>> = Vec::new();
    for (i, job_file) in job_files.iter().enumerate() {
        let mut command = Command::new(&blender);
        command
            .arg("--background")
            .arg("--python")
            .arg(&core_script)
            .arg("--")
            .arg(job_file)
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
        let stdout = child.stdout.take().ok_or_else(|| "No stdout from Blender core".to_string())?;

        let (w1, l1, s1) = (window.clone(), log_file.clone(), shared.clone());
        threads.push(thread::spawn(move || {
            for line in BufReader::new(stderr).lines().flatten() {
                let line = line.trim();
                if line.is_empty() { continue; }
                if let Some(writer) = &l1 {
                    if let Ok(mut f) = writer.lock() { let _ = writeln!(f, "[blender] {}", line); }
                }
                if note_noise(line, &s1) { continue; }
                let lower = line.to_lowercase();
                // Blender prints non-fatal warnings as ERROR; keep what is left visible but do not paint
                // the whole log red. Real failures come from the worker's JSON "error" events.
                let level = if lower.contains("traceback") || lower.contains("python error") { "error" } else { "info" };
                emit(&w1, ProgressEvent::Log { level: level.into(), message: line.to_string() });
            }
        }));

        let (w2, l2, s2) = (window.clone(), log_file.clone(), shared.clone());
        threads.push(thread::spawn(move || {
            for line in BufReader::new(stdout).lines().flatten() {
                let original = line.trim();
                if original.is_empty() { continue; }
                if let Some(writer) = &l2 {
                    if let Ok(mut f) = writer.lock() { let _ = writeln!(f, "{}", original); }
                }
                let json = original.strip_prefix("WCT_JSON:").unwrap_or(original);
                match serde_json::from_str::<CoreEvent>(json) {
                    Ok(CoreEvent::Progress { message, current, total }) => {
                        let (cur, tot) = match s2.progress.lock() {
                            Ok(mut p) => {
                                p[i] = (current, total);
                                (p.iter().map(|x| x.0).sum::<u32>(), p.iter().map(|x| x.1).sum::<u32>())
                            }
                            Err(_) => (current, total),
                        };
                        emit(&w2, ProgressEvent::Core { message, current: cur, total: tot });
                    }
                    Ok(CoreEvent::Log { level, message }) => {
                        emit(&w2, ProgressEvent::Log { level: level.clone(), message: message.clone() });
                        if level == "error" {
                            if let Ok(mut e) = s2.last_error.lock() { *e = message; }
                        }
                    }
                    Ok(CoreEvent::Done { ok, message }) => {
                        if let Ok(mut d) = s2.done.lock() { d.push((ok, message)); }
                    }
                    Err(_) => {
                        // Blender's own log lines come through stdout too.
                        if !note_noise(original, &s2) {
                            emit(&w2, ProgressEvent::Log { level: "info".into(), message: original.to_string() });
                        }
                    }
                }
            }
        }));
        children.push(child);
    }

    let mut all_exited_ok = true;
    let mut last_status = String::new();
    for child in children.iter_mut() {
        match child.wait() {
            Ok(status) => {
                if !status.success() { all_exited_ok = false; last_status = format!("Core exited with status {}", status); }
            }
            Err(e) => { all_exited_ok = false; last_status = e.to_string(); }
        }
    }
    for t in threads { let _ = t.join(); }
    for f in &job_files { let _ = fs::remove_file(f); }

    let missing_maps = shared.missing_maps.load(Ordering::Relaxed);
    let missing_other = shared.missing_other.load(Ordering::Relaxed);
    if missing_maps > 0 || missing_other > 0 {
        emit(&window, ProgressEvent::Log {
            level: "info".into(),
            message: format!(
                "Blender could not find {} optional normal/specular map(s) and {} placeholder texture(s) referenced by the source models. \
                 This is harmless: the prop models are rebuilt with the diffuse texture only, and previews just lack some shine. \
                 (The individual lines are in wct_export.log.)",
                missing_maps, missing_other
            ),
        });
    }

    let done = shared.done.lock().map(|d| d.clone()).unwrap_or_default();
    let core_ok = all_exited_ok && done.len() == workers as usize && done.iter().all(|d| d.0);
    let mut final_message = if done.len() == 1 {
        done[0].1.clone()
    } else {
        done.iter().map(|d| d.1.clone()).collect::<Vec<_>>().join(" | ")
    };

    if core_ok && workers > 1 {
        match merge_outputs(&root) {
            Ok(n) => emit(&window, ProgressEvent::Log { level: "success".into(), message: format!("Merged {} worker manifests, fxmanifest written for {} model resource(s)", workers, n) }),
            Err(e) => {
                let err = format!("Could not merge the workers' results: {}", e);
                emit(&window, ProgressEvent::Log { level: "error".into(), message: err.clone() });
                emit(&window, ProgressEvent::Finished { message: err.clone(), ok: false });
                return Err(err);
            }
        }
    }

    let log_note = format!("Export log saved to {}", log_path.display());
    if let Some(writer) = &log_file {
        if let Ok(mut f) = writer.lock() {
            let _ = writeln!(f, "===== export finished: {} =====", final_message);
        }
    }
    emit(&window, ProgressEvent::Log { level: "info".into(), message: log_note.clone() });

    if !core_ok {
        if final_message.is_empty() || done.iter().all(|d| d.0) {
            final_message = shared.last_error.lock().map(|e| e.clone()).unwrap_or_default();
        }
        let err = if !final_message.is_empty() { final_message } else if !last_status.is_empty() { last_status } else { "Core did not finish".to_string() };
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
