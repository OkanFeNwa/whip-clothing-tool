import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { open } from "@tauri-apps/plugin-dialog";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import i18n from "./i18n";

type SourceMode = "vanilla" | "addon" | "both";
type ExportMode = "models" | "previews" | "both";
type LogLevel = "info" | "success" | "error";
type ProgressEvent =
  | { kind: "started" | "step"; message: string; current: number; total: number }
  | { kind: "core"; message: string; current: number; total: number }
  | { kind: "log"; level: LogLevel; message: string }
  | { kind: "finished"; message: string; ok: boolean };

const CATEGORY_OPTIONS = [
  "head", "berd", "hair", "uppr", "lowr", "feet", "teef", "accs", "task", "decl", "jbib",
  "props_p_head", "props_p_eyes", "props_p_ears", "props_p_rwrist", "props_p_lwrist"
] as const;
type CatId = (typeof CATEGORY_OPTIONS)[number];
type AddonFolder = { path: string; ydd: number; ytd: number };

type Settings = {
  sourceMode: SourceMode;
  gtavPath: string;
  addonFolders: AddonFolder[];
  outputRoot: string;
  imgSize: string;
  imgFormat: string;
  exportCollisions: boolean;
  exportMode: ExportMode;
  modelCategories: CatId[];
  previewCategories: CatId[];
};

const SETTINGS_KEY = "wct_settings";

function loadSettings(): Partial<Settings> {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    return raw ? JSON.parse(raw) as Partial<Settings> : {};
  } catch {
    return {};
  }
}

const saved = loadSettings();

function CategoryPicker({
  selected, onChange, title, hint, t
}: {
  selected: CatId[]; onChange: (next: CatId[]) => void; title: string; hint: string;
  t: (k: string) => string;
}) {
  function toggle(id: CatId) {
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  }
  return (
    <div className="cat-block">
      <div className="cat-head">
        <h3>{title}</h3>
        <div className="cat-actions">
          <button type="button" className="btn btn-mini" onClick={() => onChange([...CATEGORY_OPTIONS])}>{t("categories.all")}</button>
          <button type="button" className="btn btn-mini" onClick={() => onChange([])}>{t("categories.none")}</button>
        </div>
      </div>
      <div className="hint" style={{ marginBottom: 10 }}>{hint}</div>
      <div className="category-grid">
        {CATEGORY_OPTIONS.map((c) => {
          const checked = selected.includes(c);
          return (
            <label key={c} className={`check-card${checked ? " checked" : ""}`}>
              <input type="checkbox" checked={checked} onChange={() => toggle(c)} />
              <span className="check-box" aria-hidden="true"><span className="check-mark">✓</span></span>
              <span className="check-label">{t(`categories.items.${c}`)}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

export default function App() {
  const { t } = useTranslation();
  const [sourceMode, setSourceMode] = useState<SourceMode>(saved.sourceMode ?? "both");
  const [gtavPath, setGtavPath] = useState(saved.gtavPath ?? "");
  const [gtavValid, setGtavValid] = useState<boolean | null>(null);
  const [addonFolders, setAddonFolders] = useState<AddonFolder[]>(
    Array.isArray(saved.addonFolders) ? saved.addonFolders : []
  );
  const [outputRoot, setOutputRoot] = useState(saved.outputRoot ?? "");
  const [imgSize, setImgSize] = useState(saved.imgSize ?? "256");
  const [imgFormat, setImgFormat] = useState(saved.imgFormat ?? "png");
  const [exportCollisions, setExportCollisions] = useState(saved.exportCollisions ?? true);
  const [exportMode, setExportMode] = useState<ExportMode>(saved.exportMode ?? "both");
  const [modelCategories, setModelCategories] = useState<CatId[]>(
    Array.isArray(saved.modelCategories) ? saved.modelCategories : ["props_p_head"]
  );
  const [previewCategories, setPreviewCategories] = useState<CatId[]>(
    Array.isArray(saved.previewCategories) ? saved.previewCategories : ["props_p_head"]
  );
  const [busy, setBusy] = useState(false);
  const [prep, setPrep] = useState<{ current: number; total: number; message: string }>({ current: 0, total: 0, message: "" });
  const [core, setCore] = useState<{ current: number; total: number; message: string }>({ current: 0, total: 0, message: "" });
  const [logs, setLogs] = useState<{ level: LogLevel; message: string }[]>([]);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    listen<ProgressEvent>("wct://progress", (e) => {
      const p = e.payload;
      if (p.kind === "started") {
        setPrep({ current: 0, total: p.total, message: p.message });
      } else if (p.kind === "step") {
        setPrep({ current: p.current, total: p.total, message: p.message });
      } else if (p.kind === "core") {
        setCore({ current: p.current, total: p.total, message: p.message });
      } else if (p.kind === "log") {
        setLogs((prev) => [...prev, { level: p.level, message: p.message }]);
      } else if (p.kind === "finished") {
        setLogs((prev) => [...prev, { level: p.ok ? "success" : "error", message: p.message }]);
      }
    }).then((fn) => { unlisten = fn; });
    return () => { unlisten?.(); };
  }, []);

  // Persist every user choice so the next launch reopens with the same setup.
  useEffect(() => {
    const settings: Settings = {
      sourceMode, gtavPath, addonFolders, outputRoot, imgSize, imgFormat,
      exportCollisions, exportMode, modelCategories, previewCategories
    };
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch { /* ignore */ }
  }, [sourceMode, gtavPath, addonFolders, outputRoot, imgSize, imgFormat,
      exportCollisions, exportMode, modelCategories, previewCategories]);

  // Re-check saved folders on startup: paths may have moved or been deleted.
  useEffect(() => {
    if (saved.gtavPath) void validateGtav(saved.gtavPath);
    const paths = Array.isArray(saved.addonFolders) ? saved.addonFolders.map((f) => f.path) : [];
    if (paths.length === 0) return;
    void Promise.all(paths.map(async (path): Promise<AddonFolder> => {
      try {
        const [ydd, ytd] = await invoke<[number, number]>("validate_addon", { path });
        return { path, ydd, ytd };
      } catch {
        return { path, ydd: 0, ytd: 0 };
      }
    })).then(setAddonFolders);
  }, []);

  async function validateGtav(path: string) {
    setGtavPath(path);
    if (!path.trim()) { setGtavValid(null); return; }
    try { setGtavValid(await invoke<boolean>("validate_gtav", { path })); }
    catch { setGtavValid(false); }
  }

  async function addAddonFolder() {
    const selected = await open({ directory: true, multiple: false });
    if (typeof selected !== "string" || addonFolders.some((f) => f.path === selected)) return;
    try {
      const [ydd, ytd] = await invoke<[number, number]>("validate_addon", { path: selected });
      setAddonFolders((prev) => [...prev, { path: selected, ydd, ytd }]);
    } catch {
      setAddonFolders((prev) => [...prev, { path: selected, ydd: 0, ytd: 0 }]);
    }
  }

  async function pickDirectory(setter: (v: string) => void) {
    const selected = await open({ directory: true, multiple: false });
    if (typeof selected === "string") setter(selected);
  }

  function changeLang(lng: string) {
    void i18n.changeLanguage(lng);
    try { localStorage.setItem("wct_lang", lng); } catch { /* ignore */ }
  }

  const prepPct = useMemo(() => prep.total ? Math.min(100, Math.round(prep.current / prep.total * 100)) : 0, [prep]);
  const corePct = useMemo(() => core.total ? Math.min(100, Math.round(core.current / core.total * 100)) : 0, [core]);

  async function runExport() {
    if (!outputRoot.trim()) { setLogs((p) => [...p, { level: "error", message: t("status.pickOutput") }]); return; }
    const cats = exportMode === "models" ? modelCategories : exportMode === "previews" ? previewCategories : [...new Set([...modelCategories, ...previewCategories])];
    if (cats.length === 0) { setLogs((p) => [...p, { level: "error", message: t("status.pickCategories") }]); return; }
    setBusy(true);
    setLogs([]);
    setPrep({ current: 0, total: 0, message: "" });
    setCore({ current: 0, total: 0, message: "" });
    try {
      const res = await invoke<string>("export_assets", {
        payload: {
          outRoot: outputRoot,
          exportMode,
          modelCategories,
          previewCategories,
          imgSize: Number(imgSize),
          imgFormat,
          gtavPath: sourceMode === "addon" ? null : gtavPath,
          addonFolders: addonFolders.map((f) => f.path),
          exportCollisions
        }
      });
      setLogs((p) => [...p, { level: "success", message: res }]);
    } catch (e) {
      setLogs((p) => [...p, { level: "error", message: String(e) }]);
    } finally { setBusy(false); }
  }

  return (
    <div className="app">
      <header>
        <div><h1>{t("app.title")}</h1><p className="subtitle">{t("app.subtitle")}</p></div>
        <div className="lang-select">
          <label htmlFor="lang">{t("language.label")}</label>
          <select id="lang" value={i18n.resolvedLanguage || "en"} onChange={(e) => changeLang(e.target.value)}>
            <option value="en">English</option><option value="it">Italiano</option><option value="es">Español</option><option value="fr">Français</option><option value="de">Deutsch</option>
          </select>
        </div>
      </header>

      <section className="card">
        <h2>{t("source.label")}</h2>
        <div className="field">
          <div className="radio-group" role="radiogroup" aria-label={t("source.label")}>
            {(["vanilla", "addon", "both"] as SourceMode[]).map((m) => (
              <label key={m}><input type="radio" name="source" checked={sourceMode === m} onChange={() => setSourceMode(m)} />{t(`source.${m}`)}</label>
            ))}
          </div>
        </div>
        {(sourceMode === "vanilla" || sourceMode === "both") && (
          <div className="field">
            <label>{t("paths.gtavLegacy")}</label>
            <div className="row">
              <input type="text" value={gtavPath} onChange={(e) => setGtavPath(e.target.value)} onBlur={(e) => void validateGtav(e.target.value)} placeholder="" />
              <button type="button" className="btn" onClick={async () => { const p = await open({ directory: true, multiple: false }); if (typeof p === "string") await validateGtav(p); }}>{t("paths.browse")}</button>
            </div>
            <div className="hint">{t("paths.gtavLegacyHint")}</div>
            {gtavValid !== null && (
              <div className={`badge ${gtavValid ? "ok" : "bad"}`}>
                {gtavValid ? t("validation.gtavOk") : t("validation.gtavBad")}
              </div>
            )}
          </div>
        )}
        {(sourceMode === "addon" || sourceMode === "both") && (
          <div className="field">
            <label>{t("paths.addonFolders")}</label>
            <button type="button" className="btn" onClick={() => void addAddonFolder()}>{t("paths.addFolder")}</button>
            <div className="hint">{t("paths.addonFoldersHint")}</div>
            {addonFolders.length > 0 && (
              <div className="chips">
                {addonFolders.map((f) => (
                  <span className="chip" key={f.path}>
                    {f.path}
                    <span className={`chip-count ${f.ydd + f.ytd > 0 ? "ok" : "bad"}`}>
                      {f.ydd + f.ytd > 0 ? t("validation.addonFound", { count: f.ydd + f.ytd, ydd: f.ydd, ytd: f.ytd }) : t("validation.addonEmpty")}
                    </span>
                    <button type="button" aria-label={t("paths.remove")} onClick={() => setAddonFolders((prev) => prev.filter((x) => x.path !== f.path))}>×</button>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <h2>{t("export.title")}</h2>
        <div className="field">
          <label>{t("paths.outputRoot")}</label>
          <div className="row">
            <input type="text" value={outputRoot} onChange={(e) => setOutputRoot(e.target.value)} readOnly />
            <button type="button" className="btn" onClick={() => void pickDirectory(setOutputRoot)}>{t("paths.browse")}</button>
          </div>
          <div className="hint">{t("paths.outputRootHint")}</div>
        </div>

        <div className="field">
          <label>{t("export.mode")}</label>
          <div className="segmented" role="radiogroup" aria-label={t("export.mode")}>
            {(["models", "previews", "both"] as ExportMode[]).map((m) => (
              <button key={m} type="button" className={`seg${exportMode === m ? " active" : ""}`} onClick={() => setExportMode(m)}>{t(`export.${m}`)}</button>
            ))}
          </div>
        </div>

        {(exportMode === "models" || exportMode === "both") && (
          <CategoryPicker title={t("categories.modelsLabel")} hint={t("categories.hint")} selected={modelCategories} onChange={setModelCategories} t={t} />
        )}
        {(exportMode === "previews" || exportMode === "both") && (
          <CategoryPicker title={t("categories.previewsLabel")} hint={t("categories.hint")} selected={previewCategories} onChange={setPreviewCategories} t={t} />
        )}

        {(exportMode === "previews" || exportMode === "both") && (
          <div className="grid two" style={{ marginTop: 12 }}>
            <div className="field">
              <label htmlFor="imgSize">{t("previews.size")}</label>
              <input id="imgSize" type="number" min={64} max={4096} value={imgSize} onChange={(e) => setImgSize(e.target.value)} />
              <div className="hint">{t("previews.sizeHint")}</div>
            </div>
            <div className="field">
              <label htmlFor="imgFormat">{t("previews.format")}</label>
              <select id="imgFormat" value={imgFormat} onChange={(e) => setImgFormat(e.target.value)}>
                <option value="png">PNG</option><option value="webp">WebP</option><option value="jpeg">JPEG</option>
              </select>
              <div className="hint">{t("previews.transparentNote")}</div>
            </div>
          </div>
        )}

        {(exportMode === "models" || exportMode === "both") && (
          <div className="field checkbox-row" style={{ marginTop: 8 }}>
            <input id="coll" type="checkbox" checked={exportCollisions} onChange={(e) => setExportCollisions(e.target.checked)} />
            <div><label htmlFor="coll" style={{ marginBottom: 2 }}>{t("collisions.label")}</label><div className="hint">{t("collisions.hint")}</div></div>
          </div>
        )}

        <div className="field" style={{ marginTop: 12 }}>
          <div className="progress-head"><span>{t("progress.preparing") || prep.message || t("progress.idle")}</span><span>{prep.current}/{prep.total || 0}</span></div>
          <div className="progress-track"><div className="progress-fill" style={{ width: `${prepPct}%` }} /></div>
        </div>
        <div className="field">
          <div className="progress-head"><span>{t("progress.core")}: {core.message || t("progress.idle")}</span><span>{core.current}/{core.total || 0}</span></div>
          <div className="progress-track"><div className="progress-fill core" style={{ width: `${corePct}%` }} /></div>
        </div>

        <div className="field">
          <div className="log-head"><h3>{t("log.title")}</h3><button type="button" className="btn btn-mini" onClick={() => setLogs([])}>{t("log.clear")}</button></div>
          <div className="log-box">
            {logs.length === 0 ? <div className="hint">{t("log.empty")}</div> : logs.map((l, i) => (
              <div key={i} className={`log-line ${l.level}`}><span className="log-tag">{t(`log.${l.level}`)}</span>{l.message}</div>
            ))}
          </div>
        </div>

        <div className="field">
          <button type="button" className="btn primary btn-lg" disabled={busy} onClick={() => void runExport()}>
            {busy ? t("export.running") : t("export.run")}
          </button>
        </div>
      </section>

      <footer><div>{t("footer.docs")}: <code>README.md</code>, <code>docs/i18n/</code></div></footer>
    </div>
  );
}
