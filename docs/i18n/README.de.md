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

## Kollisionen
Hängen von `.ybn`/Bounds ab. Falls verfügbar, in den Ausgabeordner aufnehmen; sonst warnt die App.

## Entwicklung
Siehe Haupt-`README.md`.