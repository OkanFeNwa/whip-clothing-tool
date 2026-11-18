# Whip Clothing Tool

Whip Clothing Tool es una aplicación de escritorio para Windows que exporta recursos de **ropa de GTA V** para flujos de trabajo de **FiveM (WHIP)**:

- Genera **vistas previas** (mismo ángulo y misma iluminación para coherencia) con **fondo transparente**, en **formato** y **tamaño** seleccionables.
- Exporta **modelos prop** para ropa que cae/se lanza: genera **`.ydr` + `.ytd`** (y archivos de colisión opcionales si se soportan) en una **carpeta elegida por ti**.
- Soporta **solo vanilla**, **solo packs addon** o **ambos**.
- Interfaz en varios idiomas: **Inglés, Italiano, Español, Francés, Alemán**.

> La app es **portátil**: sin instalador y sin ruta de GTA/WHIP sugerida. Siempre eliges entrada/salida en la app.

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
Windows 10/11 64-bit, Blender 4.2+/5.x con Sollumz habilitado, GTA V Legacy solo para la fuente Vanilla. No se necesita Python del sistema: el trabajo real se ejecuta dentro de Blender.

## Instalación automática de dependencias
Extrae el ZIP: `whip_clothing_tool.exe` está en la **raíz** de la carpeta, junto a `core/`.
Ejecuta una vez:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1
```

El script detecta Blender, instala la última extensión de Sollumz desde el release oficial de GitHub, la habilita y verifica `szio`/`pymateria` dentro de Blender. Con `-Dev` instala también Node.js, Rust y Visual Studio Build Tools para recompilar la app.

## Colisiones
Dependen de `.ybn`/bounds. Si están disponibles, inclúyelas en la salida; si no, la app lo avisará.

## Desarrollo
Ver `README.md` principal.