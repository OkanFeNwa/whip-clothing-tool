# Whip Clothing Tool

Whip Clothing Tool ist eine Windows-Desktop-App zum Exportieren von **GTA-V-Kleidungs-Assets** für **FiveM (WHIP)**-Workflows:

- Erzeugt **Vorschau-Bilder** (gleicher Blickwinkel und gleiche Beleuchtung für Konsistenz) mit **transparentem Hintergrund**, in wählbarem **Format** und **Größe**.
- Exportiert **Prop-Modelle** für fallende/geworfene Kleidung: erzeugt **`.ydr` + `.ytd`** (und optional Kollisionsdateien, falls unterstützt) in einem von Ihnen gewählten **Ausgabeordner**.
- Unterstützt **nur Vanilla**, **nur Addon-Packs** oder **beides**.
- Mehrsprachige Oberfläche: **Englisch, Italienisch, Spanisch, Französisch, Deutsch**.

> Die App ist für eine **Installation** (Installer) gedacht. Keine fest codierten WHIP-Pfade: Sie wählen Ein-/Ausgabe immer in der App.

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
Windows 10/11 64-bit, GTA V Legacy für Vanilla, Python 3.10+ und je nach Pipeline Blender + Sollumz. Der Installer sollte fehlende Komponenten einbinden oder anleiten.

## Kollisionen
Hängen von `.ybn`/Bounds ab. Falls verfügbar, in den Ausgabeordner aufnehmen; sonst warnt die App.

## Entwicklung
Siehe Haupt-`README.md`.