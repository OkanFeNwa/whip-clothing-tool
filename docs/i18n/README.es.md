# Whip Clothing Tool

Whip Clothing Tool es una aplicación de escritorio para Windows que exporta recursos de **ropa de GTA V** para flujos de trabajo de **FiveM (WHIP)**:

- Genera **vistas previas** (mismo ángulo y misma iluminación para coherencia) con **fondo transparente**, en **formato** y **tamaño** seleccionables.
- Exporta **modelos prop** para ropa que cae/se lanza: genera **`.ydr` + `.ytd`** (y archivos de colisión opcionales si se soportan) en una **carpeta elegida por ti**.
- Soporta **solo vanilla**, **solo packs addon** o **ambos**.
- Interfaz en varios idiomas: **Inglés, Italiano, Español, Francés, Alemán**.

> App pensada para **instalarse** (instalador). Sin rutas fijas de WHIP: siempre eliges entrada/salida en la app.

## Documentación

- English: [../../README.md](../../README.md)
- Italiano: [README.it.md](README.it.md)
- Français: [README.fr.md](README.fr.md)
- Deutsch: [README.de.md](README.de.md)

## Qué hace

### Vistas previas
- Render con **ángulo e iluminación fijos** para todos los elementos.
- **Fondo transparente**.
- Eliges: fuente (Vanilla / Addon / Ambos), **carpeta de salida**, **tamaño** (manual), **formato** (selector).

### Modelos prop
- Exporta `.ydr` + `.ytd` a la carpeta elegida.
- Colisiones opcionales si el flujo lo permite.
- Sin rutas codificadas: siempre con el explorador de archivos.

## Requisitos
Windows 10/11 64-bit, GTA V Legacy para vanilla, Python 3.10+ y (según pipeline) Blender + Sollumz. El instalador debe incluir o guiar la instalación.

## Colisiones
Dependen de `.ybn`/bounds. Si están disponibles, inclúyelas en la salida; si no, la app lo avisará.

## Desarrollo
Ver `README.md` principal.