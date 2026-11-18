import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import it from "./locales/it.json";
import es from "./locales/es.json";
import fr from "./locales/fr.json";
import de from "./locales/de.json";

const stored = typeof localStorage !== "undefined" ? localStorage.getItem("wct_lang") : null;

void i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      it: { translation: it },
      es: { translation: es },
      fr: { translation: fr },
      de: { translation: de }
    },
    lng: stored || "en",
    fallbackLng: "en",
    interpolation: { escapeValue: false }
  });

export default i18n;
