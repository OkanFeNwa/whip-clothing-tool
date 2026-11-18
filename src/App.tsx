import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { open } from "@tauri-apps/plugin-dialog";
import i18n from "./i18n";

type SourceMode = "vanilla" | "addon" | "both";

export default function App() {
  const { t } = useTranslation();
  const [sourceMode, setSourceMode] = useState<SourceMode>("vanilla");
  const [gtavPath, setGtavPath] = useState("");
  const [addonFolders, setAddonFolders] = useState<string[]>([]);
  const [outPreviews, setOutPreviews] = useState("");
  const [outModels, setOutModels] = useState("");
  const [imgSize, setImgSize] = useState("256");
  const [imgFormat, setImgFormat] = useState("png");
  const [exportCollisions, setExportCollisions] = useState(true);
  const [slot, setSlot] = useState("hat");
  const [drawable, setDrawable] = useState("0");
  const [texture, setTexture] = useState("0");
  const [modelName, setModelName] = useState("");

  const statusMessage = useMemo(() => {
    if (sourceMode !== "addon" && !gtavPath.trim()) return t("status.missingGtav");
    return t("status.ready");
  }, [sourceMode, gtavPath, t]);

  async function pickDirectory(setter: (v: string) => void) {
    const selected = await open({ directory: true, multiple: false });
    if (typeof selected === "string") setter(selected);
  }

  async function addAddonFolder() {
    const selected = await open({ directory: true, multiple: false });
    if (typeof selected === "string" && !addonFolders.includes(selected)) {
      setAddonFolders((prev) => [...prev, selected]);
    }
  }

  function changeLang(lng: string) {
    void i18n.changeLanguage(lng);
    try {
      localStorage.setItem("wct_lang", lng);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="app">
      <header>
        <div>
          <h1>{t("app.title")}</h1>
          <p className="subtitle">{t("app.subtitle")}</p>
        </div>
        <div className="lang-select">
          <label htmlFor="lang">{t("language.label")}</label>
          <select
            id="lang"
            value={i18n.resolvedLanguage || "en"}
            onChange={(e) => changeLang(e.target.value)}
          >
            <option value="en">English</option>
            <option value="it">Italiano</option>
            <option value="es">Español</option>
            <option value="fr">Français</option>
            <option value="de">Deutsch</option>
          </select>
        </div>
      </header>

      <div className="grid two">
        <section className="card">
          <h2>{t("source.label")}</h2>
          <div className="field">
            <div className="radio-group" role="radiogroup" aria-label={t("source.label")}>
              {(["vanilla", "addon", "both"] as SourceMode[]).map((m) => (
                <label key={m}>
                  <input
                    type="radio"
                    name="source"
                    checked={sourceMode === m}
                    onChange={() => setSourceMode(m)}
                  />
                  {t(`source.${m}`)}
                </label>
              ))}
            </div>
          </div>

          {(sourceMode === "vanilla" || sourceMode === "both") && (
            <div className="field">
              <label>{t("paths.gtavLegacy")}</label>
              <div className="row">
                <input
                  type="text"
                  value={gtavPath}
                  onChange={(e) => setGtavPath(e.target.value)}
                  placeholder="G:\Games\Epic Games\GTAV"
                />
                <button type="button" className="btn" onClick={() => void pickDirectory(setGtavPath)}>
                  {t("paths.browse")}
                </button>
              </div>
              <div className="hint">{t("paths.gtavLegacyHint")}</div>
            </div>
          )}

          {(sourceMode === "addon" || sourceMode === "both") && (
            <div className="field">
              <label>{t("paths.addonFolders")}</label>
              <button type="button" className="btn" onClick={() => void addAddonFolder()}>
                {t("paths.addFolder")}
              </button>
              <div className="hint">{t("paths.addonFoldersHint")}</div>
              {addonFolders.length > 0 && (
                <div className="chips">
                  {addonFolders.map((f) => (
                    <span className="chip" key={f}>
                      {f}
                      <button
                        type="button"
                        aria-label={t("paths.remove")}
                        onClick={() => setAddonFolders((prev) => prev.filter((x) => x !== f))}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        <section className="card">
          <h2>{t("previews.title")}</h2>
          <div className="field">
            <label>{t("paths.outputPreviews")}</label>
            <div className="row">
              <input
                type="text"
                value={outPreviews}
                onChange={(e) => setOutPreviews(e.target.value)}
                readOnly
              />
              <button type="button" className="btn" onClick={() => void pickDirectory(setOutPreviews)}>
                {t("paths.browse")}
              </button>
            </div>
          </div>
          <div className="field">
            <label htmlFor="imgSize">{t("previews.size")}</label>
            <input
              id="imgSize"
              type="number"
              min={64}
              max={4096}
              value={imgSize}
              onChange={(e) => setImgSize(e.target.value)}
            />
            <div className="hint">{t("previews.sizeHint")}</div>
          </div>
          <div className="field">
            <label htmlFor="imgFormat">{t("previews.format")}</label>
            <select id="imgFormat" value={imgFormat} onChange={(e) => setImgFormat(e.target.value)}>
              <option value="png">PNG</option>
              <option value="webp">WebP</option>
              <option value="jpeg">JPEG</option>
            </select>
            <div className="hint">{t("previews.transparentNote")}</div>
          </div>
          <div className="field">
            <button type="button" className="btn primary" disabled title={t("previews.run")}>
              {t("previews.run")}
            </button>
          </div>
        </section>
      </div>

      <section className="card" style={{ marginTop: 20 }}>
        <h2>{t("models.title")}</h2>
        <p className="hint" style={{ marginTop: 0 }}>{t("models.note")}</p>
        <div className="field">
          <label>{t("paths.outputModels")}</label>
          <div className="row">
            <input
              type="text"
              value={outModels}
              onChange={(e) => setOutModels(e.target.value)}
              readOnly
            />
            <button type="button" className="btn" onClick={() => void pickDirectory(setOutModels)}>
              {t("paths.browse")}
            </button>
          </div>
        </div>
        <div className="field checkbox-row">
          <input
            id="coll"
            type="checkbox"
            checked={exportCollisions}
            onChange={(e) => setExportCollisions(e.target.checked)}
          />
          <div>
            <label htmlFor="coll" style={{ marginBottom: 2 }}>{t("collisions.label")}</label>
            <div className="hint">{t("collisions.hint")}</div>
          </div>
        </div>
        <div className="grid two" style={{ marginTop: 12 }}>
          <div className="field">
            <label htmlFor="slot">{t("models.slot")}</label>
            <input id="slot" type="text" value={slot} onChange={(e) => setSlot(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="modelName">{t("models.modelName")}</label>
            <input
              id="modelName"
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="cw_my_item"
            />
          </div>
          <div className="field">
            <label htmlFor="drawable">{t("models.drawable")}</label>
            <input
              id="drawable"
              type="number"
              value={drawable}
              onChange={(e) => setDrawable(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="texture">{t("models.texture")}</label>
            <input
              id="texture"
              type="number"
              value={texture}
              onChange={(e) => setTexture(e.target.value)}
            />
          </div>
        </div>
        <div className="field">
          <button type="button" className="btn primary" disabled title={t("models.run")}>
            {t("models.run")}
          </button>
        </div>
      </section>

      <div className="status">{statusMessage}</div>

      <footer>
        <div>
          {t("footer.docs")}: <code>README.md</code>, <code>docs/i18n/</code>
        </div>
        <div style={{ marginTop: 6 }}>{t("footer.repoNote")}</div>
      </footer>
    </div>
  );
}
