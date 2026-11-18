# Whip Clothing Tool

Whip Clothing Tool es una aplicación de escritorio para Windows que exporta recursos de **ropa de GTA V** para flujos de trabajo de **FiveM (WHIP)**:

- Genera **vistas previas** (mismo ángulo y misma iluminación para coherencia) con **fondo transparente**, en **formato** y **tamaño** seleccionables.
- Exporta **modelos prop** para ropa que cae/se lanza: genera **`.ydr` + `.ytd`** (y archivos de colisión opcionales si se soportan) en una **carpeta elegida por ti**.
- **Optimiza los polígonos automáticamente** alrededor de un 30 % con una decimación que respeta las costuras de UV, material y normales; se conservan pesos del esqueleto, shaders, límites y metadatos.
- **Optimiza las texturas automáticamente** a 512 px antes de escribir los `.ytd`, conservando la compresión y la cadena de mips originales (sin recodificar: colores y alpha intactos). El registro indica los MB ahorrados.
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

## Modelos generables
Cada modelo en `stream/` es un objeto estático normalizado (`normal_spec.sps`, Color 1 `#FF8000`, Color 2 `#000000`) con un `.ytyp` binario GEN8 y una línea `DLC_ITYP_REQUEST` en el `fxmanifest.lua` generado. Los archivos en `img/clothing/` conservan los shaders ped originales para el sistema de ropa de WHIP. Los props se toman siempre del archivo base `streamedpedprops.rpf/mp_[mf]_freemode_01_p/`, no de la primera DLC con el mismo nombre. Se exportan todas las variantes de textura que el ped puede llevar: base `a`–`h` (0–7) más las variantes DLC `i`–`z` (8–25) del mismo drawable, así que los índices altos ya no caen en el fallback `prop_cap_01`. El nombre real de la textura se escribe en el `diffusesampler` del objeto. Algunos `.ydd` base son placeholders de 4 vértices (por ejemplo `p_eyes_000.ydd`): en ese caso la herramienta usa automáticamente el primer DLC con geometría real y lo indica en el campo `source` del manifiesto.

Copia `models/whip_media_clothing_<género>/` en `resources/` y arráncalo en `server.cfg`. **Después de añadir o reemplazar archivos en `stream/`, todos los clientes deben reconectarse por completo**: `refresh` + `restart` no actualizan los archivos ya descargados. Si `RequestModel` sigue fallando tras una reconexión limpia, la app usa `prop_cap_01` como último recurso.

## Registro de exportación
La app escribe toda la salida en `<output root>/wct_export.log`. Las advertencias DDS no fatales de Blender se conservan en el archivo pero se ocultan en la interfaz.

## Colisiones
Dependen de `.ybn`/bounds. Si están disponibles, inclúyelas en la salida; si no, la app lo avisará.

## Desarrollo
Ver `README.md` principal.