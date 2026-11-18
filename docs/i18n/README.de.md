# Whip Clothing Tool

Whip Clothing Tool ist eine Windows-Desktop-App zum Exportieren von **GTA-V-Kleidungs-Assets** für **FiveM (WHIP)**-Workflows:

- Erzeugt **Vorschau-Bilder** (gleicher Blickwinkel und gleiche Beleuchtung für Konsistenz) mit **transparentem Hintergrund**, in wählbarem **Format** und **Größe**.
- Exportiert **Prop-Modelle** für fallende/geworfene Kleidung: erzeugt **`.ydr` + `.ytd`** (und optional Kollisionsdateien, falls unterstützt) in einem von Ihnen gewählten **Ausgabeordner**.
- **Optimiert Polygone automatisch** um etwa 30 % durch eine Dezimation, die UV-, Material- und Normalen-Nähte berücksichtigt. Skin-Gewichte, Shader, Bounds und Metadaten bleiben erhalten.
- **Optimiert Texturen automatisch** auf 512 px, bevor die `.ytd` geschrieben werden. Dabei bleiben Originalkompression und Mip-Kette erhalten (kein Re-Encoding, Farben und Alpha unverändert). Das Protokoll meldet die eingesparten MB.
- Unterstützt **nur Vanilla**, **nur Addon-Packs** oder **beides**.
- Mehrsprachige Oberfläche: **Englisch, Italienisch, Spanisch, Französisch, Deutsch**.

> Die App ist **portabel**: kein Installer und kein vorgeschlagener GTA-/WHIP-Pfad. Sie wählen Ein-/Ausgabe immer in der App.

## Dokumentation

- English: [../../README.md](../../README.md)
- Italiano: [README.it.md](README.it.md)
- Español: [README.es.md](README.es.md)
- Français: [README.fr.md](README.fr.md)

## Funktionen

### Vorschau-Bilder
- Render mit **festem Winkel und fester Beleuchtung** für alle Items.
- **Transparenter Hintergrund**.
- Wahl: Quelle (Vanilla / Addon / Beide), **Ausgabeordner**, **Größe** (manuell), **Format** (Auswahl).

### Prop-Modelle
- Exportiert `.ydr` + `.ytd` in den gewählten Ordner.
- Kollisionsdaten optional, je nach Pipeline.
- Keine fest codierten Pfade: immer über Dateiauswahl.

## Voraussetzungen
Windows 10/11 64-Bit, Blender 4.2+/5.x mit aktiviertem Sollumz, GTA V Legacy nur für die Vanilla-Quelle. Es ist kein System-Python nötig: die eigentliche Arbeit läuft in Blender.

## Automatische Installation der Abhängigkeiten
ZIP entpacken: `whip_clothing_tool.exe` liegt im **Stammverzeichnis** des Ordners, neben `core/`.
Einmal ausführen:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1
```

Das Script erkennt Blender, installiert die neueste Sollumz-Erweiterung aus dem offiziellen GitHub-Release, aktiviert sie und prüft `szio`/`pymateria` in Blender. Mit `-Dev` werden zusätzlich Node.js, Rust und die Visual Studio Build Tools zum Neubauen installiert.

## Spawnbare Modelle
Jedes Modell in `stream/` ist ein normalisiertes statisches Objekt (`normal_spec.sps`, Color 1 `#FF8000`, Color 2 `#000000`) mit einem binären GEN8-`.ytyp` und einem `DLC_ITYP_REQUEST`-Eintrag im erzeugten `fxmanifest.lua`. Die Dateien unter `img/clothing/` behalten die ursprünglichen Ped-Shader für das WHIP-Kleidungssystem. Props stammen immer aus der Basisdatei `streamedpedprops.rpf/mp_[mf]_freemode_01_p/`, nie aus dem ersten DLC-Pack mit demselben Namen. Alle Texturvarianten, die der Ped tragen kann, werden exportiert: Basis `a`–`h` (0–7) plus die DLC-Varianten `i`–`z` (8–25) desselben Drawables, sodass hohe Indizes nicht mehr auf den `prop_cap_01`-Fallback zurückfallen. Der echte Texturname wird in den `diffusesampler` des Objekts geschrieben. Einige Basis-`.ydd` sind 4-Vertre-Platzhalter (zum Beispiel `p_eyes_000.ydd`): In diesem Fall verwendet das Werkzeug automatisch das erste DLC mit echter Geometrie und vermerkt dies im Feld `source` des Manifests.

Kopiere `models/whip_media_clothing_<Geschlecht>/` nach `resources/` und starte es in der `server.cfg`. **Nach dem Hinzufügen oder Ersetzen von Dateien in `stream/` muss jeder Client die Verbindung vollständig trennen und neu verbinden**: `refresh` + `restart` aktualisieren bereits heruntergeladene Dateien nicht. Falls `RequestModel` nach einer sauberen Wiederverbindung weiterhin scheitert, verwendet die App `prop_cap_01` als letzten Ausweg.

## Export-Protokoll
Die App schreibt die gesamte Ausgabe in `<output root>/wct_export.log`. Harmlose Blender-DDS-Warnungen bleiben in der Datei, werden aber in der Oberfläche ausgeblendet.

## Kollisionen
Hängen von `.ybn`/Bounds ab. Falls verfügbar, in den Ausgabeordner aufnehmen; sonst warnt die App.

## Entwicklung
Siehe Haupt-`README.md`.