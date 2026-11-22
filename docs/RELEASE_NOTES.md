# Whip Clothing Tool — v0.2.1

Release notes in the languages supported by the app. English is the primary version.

---

## English

Whip Clothing Tool is a portable Windows app that exports GTA V clothing assets for FiveM / WHIP servers. The export pipeline is fully functional and produces real files, not just empty folders.

### What's new in 0.2.x

- **Parallel export (0.2.0).** Several Blender workers run at once (default: half the CPU cores, 1 to 4). Set `WCT_WORKERS` (1-8) to change it; `1` restores the old single-process behaviour. The tasks of one source `.ydd` stay in the same worker, the manifests are merged into `export_manifest.json` and each `fxmanifest.lua` is regenerated from its `stream/` folder at the end. The first run with a GTA V folder builds the archive index with a single worker. Output files and names are unchanged.
- **Quieter log (0.2.0).** Harmless Blender DDS warnings are still written to `wct_export.log`, but are no longer printed line by line in the app: one summary line with the counts appears at the end. Real errors are still shown as `error` lines.
- **Fewer `.ytyp` files (0.2.1).** GTA loads at most 3000 `.ytyp` files (the `MapTypesStore` pool); more crashes the game with `MapTypesStore Pool Full`. Archetypes are now packed into `wctchunk_*.ytyp` files (250 models each) and listed in `fxmanifest.lua`. Export all the categories you need in one run: each run rewrites these chunks from what it exported. Exports made by 0.1.x can be converted without exporting again: `blender --background --python core\merge_ytyps.py -- "<out>\models\whip_media_clothing_male\stream" "<out>\models\whip_media_clothing_female\stream"` (the originals are moved to `ytyp_single`).

### What it does

- **Previews** — transparent PNG/WebP (or opaque JPEG) renders with a fixed camera angle and lighting, so every item is visually consistent. Every texture variant uses its own `.ytd` colours.
- **Models** — exports `.ydr` + `.ytd` pairs, plus `.ybn` collision files when the source drawable actually contains collision bounds.
- **Polygon optimization** — meshes are decimated by about 30% while respecting UV, material and normal seams; skin weights, shaders, collision bounds and metadata are preserved. Meshes under 200 triangles are left untouched.
- **Automatic optimization** — textures are reduced to 512 px before writing `.ytd` files by dropping mip levels, without re-encoding; about 57% smaller texture files in testing, with colours and alpha unchanged. The saved MB are reported in the log.
- **Sources** — vanilla GTA V Legacy RPFs, loose add-on folders (scanned recursively), or both.
- **All variants** — every drawable and texture variation is exported automatically; names are generated from the source clothing file.
- **One output root** — the app creates `models/` and `previews/` underneath it, split by gender and slot.

### Usability

- Single screen with Models / Previews / Both mode and separate category pickers.
- Path validation for the GTA V folder and add-on packs, with a recursive `.ydd`/`.ytd` count.
- Remembers the chosen paths and all export settings between launches.
- Live progress bars and logs for both folder preparation and the Blender core, with auto-scroll and a completion badge.
- Interface available in **English, Italiano, Español, Français, Deutsch**.

### Requirements

- Windows 10/11 64-bit
- **Blender 4.2+ / 5.x** with the **Sollumz** add-on installed and enabled
- GTA V Legacy only if you use Vanilla or Both source mode

No system Python installation is required: the real work runs inside Blender, which already provides `szio`, PyMateria and Sollumz.

### Install and run

1. Download `whip-clothing-tool-v0.2.1-portable-win64.zip` and extract it anywhere. `whip_clothing_tool.exe` is at the **root** of the extracted folder, beside `core/`.
2. Run `install-dependencies.ps1` once to install Blender and Sollumz automatically (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Add `-Dev` to also install Node.js, Rust and the Visual Studio Build Tools.
3. Run `whip_clothing_tool.exe`. There is no app installer.
4. Pick the output root and the source folders, choose the categories, then press **Export**.

If Blender is not on `PATH`, set the `WCT_BLENDER` environment variable to your `blender.exe`.

### Output layout

```text
<output root>/
  models/whip_media_clothing_<male|female>/
    fxmanifest.lua
    stream/<model>.ydr / .ytd, wctchunk_*.ytyp
    img/clothing/<gender>/<slot>/...
  previews/whip_media_clothing_<male|female>/img/clothing/<gender>/<slot>/
  export_manifest.json
  wct_export.log
```

### Spawnable models

Each model in `stream/` is a normalised static prop (`normal_spec.sps`, `Color 1 = #FF8000`, `Color 2 = #000000`) with a binary GEN8 `.ytyp` archetype (flags 32, lodDist 100, hdTextureDist 5, bounds from the real vertices). The generated `fxmanifest.lua` contains `this_is_a_map 'yes'` and one `data_file 'DLC_ITYP_REQUEST' 'stream/wctchunk_*.ytyp'` line per chunk (250 models each). Copy the resource into `resources/` and start it in `server.cfg`.

**After adding or replacing files in `stream/`, every client must fully reconnect** — `refresh` + `restart` does not update files already cached by the client. If `RequestModel` still fails after a clean reconnect, the tool falls back to `prop_cap_01`.

### Notes

- The first vanilla run builds an RPF index inside `<output root>/.wct_cache/`; it can take a few minutes, later runs reuse the cache.
- Collisions are only written when the source contains real bounds; no placeholder collision is invented.
- JPEG does not support transparency. Use PNG or WebP for transparent previews.
- Props are taken from the base `streamedpedprops.rpf/mp_[mf]_freemode_01_p/` files the ped actually wears. DLC packs with the same filename are ignored unless the drawable does not exist in the base set — this fixes exporting a themed helmet instead of the base hat. Only base texture variants `a`–`h` (indices 0–7) are exported; higher indices are left to the registry's texture-0 fallback. The real `.ytd` texture name is baked into the spawned prop's `diffusesampler`.
- The full export log is appended to `<output root>/wct_export.log`. Harmless Blender DDS cache warnings are recorded there but hidden in the app.
- All input/output paths are selected in the app. The build contains no game, server or user paths.

---

## Italiano

Whip Clothing Tool è un’app portable per Windows che esporta asset di abbigliamento GTA V per server FiveM / WHIP. La pipeline di export è completa e genera file reali, non solo cartelle vuote.

### Novità di 0.2.x

- **Export parallelo (0.2.0).** Gira più worker Blender in contemporanea (default: metà dei core CPU, da 1 a 4). La variabile d’ambiente `WCT_WORKERS` (1-8) permette di cambiarlo; `1` ripristina il vecchio comportamento a processo singolo. I task di uno stesso `.ydd` restano nello stesso worker, i manifest vengono uniti in `export_manifest.json` e ogni `fxmanifest.lua` viene riscritto dalla propria cartella `stream/` alla fine. La prima esecuzione con una cartella GTA V crea l’indice degli archivi con un solo worker. File e nomi esportati non cambiano.
- **Log meno rumoroso (0.2.0).** I warning DDS non fatali di Blender restano in `wct_export.log` ma non vengono più stampati riga per riga nell’app: alla fine compare una riga di riepilogo con i conteggi. I veri errori sono ancora mostrati come righe `error`.
- **Meno file `.ytyp` (0.2.1).** GTA carica al massimo 3000 file `.ytyp` (il pool `MapTypesStore`); di più il gioco crasha con `MapTypesStore Pool Full`. Gli archetype ora vengono scritti in file `wctchunk_*.ytyp` (250 modelli ciascuno) e elencati nell'`fxmanifest.lua`. Esporta in una sola esecuzione tutte le categorie che ti servono: ogni export riscrive questi chunk in base a ciò che ha generato. Gli export di 0.1.x si convertono senza riesportare: `blender --background --python core\merge_ytyps.py -- "<out>\models\whip_media_clothing_male\stream" "<out>\models\whip_media_clothing_female\stream"` (gli originali vengono spostati in `ytyp_single`).

### Cosa fa

- **Anteprime**: PNG/WebP trasparenti (o JPEG opaco) con angolazione e illuminazione fisse, così ogni capo è coerente. Ogni variante texture usa i colori del proprio `.ytd`.
- **Modelli**: esporta coppie `.ydr` + `.ytd` e file di collisione `.ybn` solo quando il modello sorgente contiene bounds reali.
- **Ottimizzazione poligoni**: le mesh vengono decimate di circa il 30% rispettando le cuciture UV, materiale e normali; pesi dello scheletro, shader, bounds di collisione e metadati restano intatti. Le mesh sotto 200 triangoli non vengono toccate.
- **Ottimizzazione automatica**: le texture vengono ridotte a 512 px prima di scrivere i `.ytd`, eliminando livelli mip senza ricomprimere; nei test i file texture sono circa il 57% più piccoli, con colori e alpha invariati. I MB risparmiati sono riportati nel log.
- **Sorgenti**: RPF di GTA V Legacy, cartelle addon sciolte (scansione ricorsiva), oppure entrambi.
- **Tutte le varianti**: ogni drawable e ogni variazione texture viene esportata automaticamente; i nomi derivano dal file sorgente.
- **Un’unica cartella di output**: l’app crea `models/` e `previews/`, divisi per genere e slot.

### Usabilità

- Schermata unica con modalità Models / Previews / Both e selettori di categorie separati.
- Validazione della cartella GTA V e dei pack addon, con conteggio ricorsivo di `.ydd`/`.ytd`.
- Ricorda percorsi e impostazioni tra un avvio e l’altro.
- Barre di avanzamento e log in tempo reale per preparazione e export Blender, con auto-scroll e indicatore di fine.
- Interfaccia in **Inglese, Italiano, Español, Français, Deutsch**.

### Requisiti

- Windows 10/11 64-bit
- **Blender 4.2+ / 5.x** con add-on **Sollumz** installato e abilitato
- GTA V Legacy solo se usi la sorgente Vanilla o Both

Non serve Python di sistema: il lavoro reale gira dentro Blender, che fornisce già `szio`, PyMateria e Sollumz.

### Installazione e avvio

1. Scarica `whip-clothing-tool-v0.2.1-portable-win64.zip` ed estrailo dove vuoi. `whip_clothing_tool.exe` è nella **root** della cartella estratta, accanto a `core/`.
2. Esegui una volta `install-dependencies.ps1` per installare Blender e Sollumz automaticamente (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Aggiungi `-Dev` per installare anche Node.js, Rust e i Visual Studio Build Tools.
3. Avvia `whip_clothing_tool.exe`. Non c’è installer per l’app.
4. Scegli output root e cartelle sorgente, seleziona le categorie e premi **Export**.

Se Blender non è in `PATH`, imposta la variabile d’ambiente `WCT_BLENDER` con il percorso di `blender.exe`.

### Modelli spawnabili

Ogni modello in `stream/` è un prop statico normalizzato (`normal_spec.sps`, Color 1 `#FF8000`, Color 2 `#000000`) con un archetype `.ytyp` binario GEN8 (flags 32, lodDist 100, hdTextureDist 5, bounds dai vertici reali). L'`fxmanifest.lua` generato contiene `this_is_a_map 'yes'` e una riga `data_file 'DLC_ITYP_REQUEST' 'stream/wctchunk_*.ytyp'` per ogni chunk (250 modelli ciascuno). Copia la resource in `resources/` e avviala in `server.cfg`.

**Dopo aver aggiunto o sostituito file in `stream/`, ogni client deve riconnettersi completamente**: `refresh` + `restart` non aggiornano i file già scaricati. Se `RequestModel` fallisce ancora dopo una riconnessione pulita, l'app usa `prop_cap_01` come ultima risorsa.

### Note

- La prima esecuzione vanilla crea l’indice RPF in `<output root>/.wct_cache/`; può volerci qualche minuto, poi viene riutilizzato.
- Le collisioni vengono scritte solo se la sorgente contiene bounds reali.
- JPEG non supporta la trasparenza: usa PNG o WebP.
- I prop vengono presi dai file base `streamedpedprops.rpf/mp_[mf]_freemode_01_p/` che il ped indossa davvero. Le DLC con lo stesso nome vengono ignorate salvo quando il drawable non esiste nel set base: così non esce più un casco tematico al posto del cappello base. Vengono esportate solo le varianti texture base `a`–`h` (indici 0–7); gli indici superiori usano il fallback texture 0 del registry. Il nome reale della texture nel `.ytd` viene scritto nel `diffusesampler` del prop spawnato.
- Il log completo viene scritto in `<output root>/wct_export.log`; i warning DDS non fatali di Blender sono nel file ma nascosti nell’app.
- Tutti i percorsi si scelgono nell’app: la build non contiene percorsi di gioco, server o utente.

---

## Español

Whip Clothing Tool es una aplicación portable para Windows que exporta recursos de ropa de GTA V para servidores FiveM / WHIP. El proceso de exportación es completo y genera archivos reales, no solo carpetas vacías.

### Novedades de 0.2.x

- **Exportación paralela (0.2.0).** Se ejecutan varios workers de Blender a la vez (por defecto, la mitad de los núcleos de CPU, entre 1 y 4). La variable de entorno `WCT_WORKERS` (1-8) permite cambiarlo; `1` restaura el comportamiento antiguo de un solo proceso. Las tareas de un mismo `.ydd` permanecen en el mismo worker, los manifiestos se unen en `export_manifest.json` y cada `fxmanifest.lua` se regenera desde su carpeta `stream/` al final. La primera ejecución con una carpeta de GTA V crea el índice de archivos con un solo worker. Los archivos y nombres exportados no cambian.
- **Registro menos ruidoso (0.2.0).** Las advertencias DDS inofensivas de Blender siguen escribiéndose en `wct_export.log`, pero ya no se imprimen línea por línea en la app: al final aparece una línea de resumen con los recuentos. Los errores reales se siguen mostrando como líneas `error`.
- **Menos archivos `.ytyp` (0.2.1).** GTA carga como máximo 3000 archivos `.ytyp` (el pool `MapTypesStore`); más hacen que el juego se cierre con `MapTypesStore Pool Full`. Los arquetipos ahora se escriben en archivos `wctchunk_*.ytyp` (250 modelos cada uno) y se enumeran en `fxmanifest.lua`. Exporta en una sola ejecución todas las categorías que necesites: cada exportación reescribe estos chunks con lo que ha generado. Las exportaciones de 0.1.x se pueden convertir sin volver a exportar: `blender --background --python core\merge_ytyps.py -- "<out>\models\whip_media_clothing_male\stream" "<out>\models\whip_media_clothing_female\stream"` (los originales se mueven a `ytyp_single`).

### Qué hace

- **Vistas previas**: PNG/WebP transparentes (o JPEG opaco) con ángulo e iluminación fijos, para que todas las prendas sean coherentes. Cada variante de textura usa los colores de su `.ytd`.
- **Modelos**: exporta pares `.ydr` + `.ytd` y archivos de colisión `.ybn` solo cuando el modelo de origen contiene bounds reales.
- **Optimización de polígonos**: las mallas se reducen alrededor de un 30 % respetando las costuras de UV, material y normales; se conservan pesos del esqueleto, shaders, límites de colisión y metadatos. Las mallas de menos de 200 triángulos no se modifican.
- **Optimización automática**: las texturas se reducen a 512 px antes de escribir los `.ytd`, eliminando niveles mip sin recodificar; en las pruebas los archivos de textura son un 57 % más pequeños, con colores y alpha intactos. Los MB ahorrados se muestran en el registro.
- **Fuentes**: RPF de GTA V Legacy, carpetas addon sueltas (escaneo recursivo) o ambas.
- **Todas las variantes**: exporta automáticamente cada drawable y cada variación de textura; los nombres se generan desde el archivo de origen.
- **Una sola carpeta de salida**: la app crea `models/` y `previews/`, separados por género y slot.

### Usabilidad

- Una sola pantalla con modo Models / Previews / Both y selectores de categorías independientes.
- Validación de la carpeta de GTA V y de los packs addon, con conteo recursivo de `.ydd`/`.ytd`.
- Recuerda las rutas y todas las opciones entre ejecuciones.
- Barras de progreso y registros en tiempo real tanto para la preparación como para el export con Blender, con desplazamiento automático e indicador de finalización.
- Interfaz en **English, Italiano, Español, Français, Deutsch**.

### Requisitos

- Windows 10/11 de 64 bits
- **Blender 4.2+ / 5.x** con el complemento **Sollumz** instalado y activado
- GTA V Legacy solo si usas la fuente Vanilla o Both

No se necesita Python del sistema: el trabajo real se ejecuta dentro de Blender, que ya incluye `szio`, PyMateria y Sollumz.

### Instalación y uso

1. Descarga `whip-clothing-tool-v0.2.1-portable-win64.zip` y extráelo donde quieras. `whip_clothing_tool.exe` está en la **raíz** de la carpeta extraída, junto a `core/`.
2. Ejecuta una vez `install-dependencies.ps1` para instalar Blender y Sollumz automáticamente (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Añade `-Dev` para instalar también Node.js, Rust y Visual Studio Build Tools.
3. Ejecuta `whip_clothing_tool.exe`. No hay instalador de la app.
4. Elige la carpeta de salida y las fuentes, selecciona las categorías y pulsa **Export**.

Si Blender no está en `PATH`, define la variable de entorno `WCT_BLENDER` con la ruta a `blender.exe`.

### Modelos instanciables

Cada modelo en `stream/` es un objeto estático normalizado (`normal_spec.sps`, Color 1 `#FF8000`, Color 2 `#000000`) con un arquetipo `.ytyp` binario GEN8 (flags 32, lodDist 100, hdTextureDist 5, bounds de los vértices reales). El `fxmanifest.lua` generado contiene `this_is_a_map 'yes'` y una línea `data_file 'DLC_ITYP_REQUEST' 'stream/wctchunk_*.ytyp'` por chunk (250 modelos cada uno). Copia el resource en `resources/` y arráncalo en `server.cfg`.

**Después de añadir o reemplazar archivos en `stream/`, todos los clientes deben reconectarse por completo**: `refresh` + `restart` no actualizan los archivos ya descargados. Si `RequestModel` sigue fallando tras una reconexión limpia, la app usa `prop_cap_01` como último recurso.

### Notas

- La primera ejecución con fuente vanilla crea el índice RPF en `<output root>/.wct_cache/`; puede tardar unos minutos, después se reutiliza.
- Las colisiones solo se escriben si la fuente contiene bounds reales.
- JPEG no admite transparencia: usa PNG o WebP.
- Los props se toman de los archivos base `streamedpedprops.rpf/mp_[mf]_freemode_01_p/` que el ped usa realmente. Las DLC con el mismo nombre se ignoran salvo que el drawable no exista en el conjunto base: así no se exporta un casco temático en lugar del sombrero base. Solo se exportan las variantes de textura base `a`–`h` (índices 0–7); los índices superiores usan el fallback de textura 0 del registro. El nombre real de la textura del `.ytd` se escribe en el `diffusesampler` del objeto generado.
- El registro completo se guarda en `<output root>/wct_export.log`; las advertencias DDS no fatales de Blender quedan en el archivo pero se ocultan en la app.
- Todas las rutas se eligen en la app: la compilación no contiene rutas de juego, servidor ni usuario.

---

## Français

Whip Clothing Tool est une application portable Windows qui exporte des ressources de vêtements GTA V pour les serveurs FiveM / WHIP. Le pipeline d’export est complet et produit de vrais fichiers, pas seulement des dossiers vides.

### Nouveautés de 0.2.x

- **Export parallèle (0.2.0).** Plusieurs workers Blender tournent en même temps (par défaut : la moitié des cœurs CPU, entre 1 et 4). La variable d’environnement `WCT_WORKERS` (1-8) permet de le modifier ; `1` restaure l’ancien comportement en un seul processus. Les tâches d’un même `.ydd` restent dans le même worker, les manifests sont fusionnés dans `export_manifest.json` et chaque `fxmanifest.lua` est régénéré depuis son dossier `stream/` à la fin. Le premier passage avec un dossier GTA V construit l’index des archives avec un seul worker. Les fichiers et les noms exportés ne changent pas.
- **Journal moins bruyant (0.2.0).** Les avertissements DDS sans gravité de Blender restent dans `wct_export.log`, mais ne sont plus affichés ligne par ligne dans l’app : une ligne récapitulative avec les comptes apparaît à la fin. Les vraies erreurs sont toujours affichées comme lignes `error`.
- **Moins de fichiers `.ytyp` (0.2.1).** GTA charge au maximum 3000 fichiers `.ytyp` (le pool `MapTypesStore`) ; au-delà, le jeu plante avec `MapTypesStore Pool Full`. Les archétypes sont désormais écrits dans des fichiers `wctchunk_*.ytyp` (250 modèles chacun) et listés dans `fxmanifest.lua`. Exportez en une seule fois toutes les catégories dont vous avez besoin : chaque export réécrit ces fichiers à partir de ce qu’il a généré. Les exports de 0.1.x peuvent être convertis sans réexporter : `blender --background --python core\merge_ytyps.py -- "<out>\models\whip_media_clothing_male\stream" "<out>\models\whip_media_clothing_female\stream"` (les originaux sont déplacés vers `ytyp_single`).

### Fonctionnalités

- **Aperçus** : PNG/WebP transparents (ou JPEG opaque) avec angle et éclairage fixes, pour que chaque vêtement soit cohérent. Chaque variante de texture utilise les couleurs de son propre `.ytd`.
- **Modèles** : exporte des paires `.ydr` + `.ytd`, ainsi que des fichiers de collision `.ybn` uniquement lorsque le modèle source contient de vrais bounds.
- **Optimisation des polygones** : les maillages sont décimés d’environ 30 % en respectant les coutures UV, matériau et normales ; poids du squelette, shaders, limites de collision et métadonnées sont conservés. Les maillages de moins de 200 triangles ne sont pas modifiés.
- **Optimisation automatique** : les textures sont réduites à 512 px avant l’écriture des `.ytd` en supprimant des niveaux de mip sans réencodage ; lors des tests, les fichiers de texture sont environ 57 % plus petits, avec des couleurs et un alpha inchangés. Les MB économisés sont indiqués dans le journal.
- **Sources** : RPF de GTA V Legacy, dossiers addon isolés (analyse récursive), ou les deux.
- **Toutes les variantes** : chaque drawable et chaque variation de texture est exportée automatiquement ; les noms sont générés depuis le fichier source.
- **Un seul dossier de sortie** : l’app crée `models/` et `previews/`, répartis par genre et par slot.

### Ergonomie

- Un seul écran avec mode Models / Previews / Both et des sélecteurs de catégories séparés.
- Validation du dossier GTA V et des packs addon, avec comptage récursif des `.ydd`/`.ytd`.
- Mémorise les chemins et tous les réglages entre deux lancements.
- Barres de progression et journaux en temps réel pour la préparation et l’export Blender, avec défilement automatique et indicateur de fin.
- Interface en **English, Italiano, Español, Français, Deutsch**.

### Prérequis

- Windows 10/11 64 bits
- **Blender 4.2+ / 5.x** avec l’extension **Sollumz** installée et activée
- GTA V Legacy uniquement pour la source Vanilla ou Both

Aucun Python système requis : le travail réel s’exécute dans Blender, qui fournit déjà `szio`, PyMateria et Sollumz.

### Installation et utilisation

1. Téléchargez `whip-clothing-tool-v0.2.1-portable-win64.zip` et extrayez-le où vous voulez. `whip_clothing_tool.exe` est à la **racine** du dossier extrait, à côté de `core/`.
2. Exécutez une fois `install-dependencies.ps1` pour installer Blender et Sollumz automatiquement (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Ajoutez `-Dev` pour installer aussi Node.js, Rust et les Visual Studio Build Tools.
3. Lancez `whip_clothing_tool.exe`. Il n’y a pas d’installateur pour l’application.
4. Choisissez le dossier de sortie et les sources, sélectionnez les catégories, puis cliquez sur **Export**.

Si Blender n’est pas dans `PATH`, définissez la variable d’environnement `WCT_BLENDER` avec le chemin vers `blender.exe`.

### Modèles instanciables

Chaque modèle dans `stream/` est un objet statique normalisé (`normal_spec.sps`, Color 1 `#FF8000`, Color 2 `#000000`) avec un archétype `.ytyp` binaire GEN8 (flags 32, lodDist 100, hdTextureDist 5, bounds issus des vrais sommets). Le `fxmanifest.lua` généré contient `this_is_a_map 'yes'` et une ligne `data_file 'DLC_ITYP_REQUEST' 'stream/wctchunk_*.ytyp'` par bloc de 250 modèles. Copiez la ressource dans `resources/` et démarrez-la dans `server.cfg`.

**Après avoir ajouté ou remplacé des fichiers dans `stream/`, chaque client doit se reconnecter entièrement** : `refresh` + `restart` ne mettent pas à jour les fichiers déjà téléchargés. Si `RequestModel` échoue encore après une reconnexion propre, l’application utilise `prop_cap_01` en dernier recours.

### Remarques

- Le premier passage avec la source vanilla crée l’index RPF dans `<output root>/.wct_cache/` ; cela peut prendre quelques minutes, les passages suivants réutilisent le cache.
- Les collisions ne sont écrites que si la source contient de vrais bounds.
- JPEG ne gère pas la transparence : utilisez PNG ou WebP.
- Les props proviennent des fichiers de base `streamedpedprops.rpf/mp_[mf]_freemode_01_p/` que le ped porte réellement. Les DLC portant le même nom sont ignorées sauf si le drawable n’existe pas dans le jeu de base : plus de casque thématique à la place du chapeau de base. Seules les variantes de texture de base `a`–`h` (indices 0–7) sont exportées ; les indices supérieurs utilisent le repli texture 0 du registre. Le vrai nom de texture du `.ytd` est écrit dans le `diffusesampler` de l’objet instancié.
- Le journal complet est écrit dans `<output root>/wct_export.log` ; les avertissements DDS non fatals de Blender y sont conservés mais masqués dans l’app.
- Tous les chemins sont choisis dans l’app : la compilation ne contient aucun chemin de jeu, de serveur ou d’utilisateur.

---

## Deutsch

Whip Clothing Tool ist eine portable Windows-App, die GTA-V-Kleidungs-Assets für FiveM-/WHIP-Server exportiert. Die Export-Pipeline ist vollständig und erzeugt echte Dateien statt leerer Ordner.

### Neuigkeiten in 0.2.x

- **Paralleler Export (0.2.0).** Mehrere Blender-Worker laufen gleichzeitig (standardmäßig die Hälfte der CPU-Kerne, 1 bis 4). Mit der Umgebungsvariable `WCT_WORKERS` (1-8) lässt sich das ändern; `1` stellt das alte Verhalten mit einem einzelnen Prozess wieder her. Die Aufgaben einer `.ydd` bleiben im selben Worker, die Manifeste werden zu `export_manifest.json` zusammengeführt und jede `fxmanifest.lua` wird am Ende aus ihrem `stream/`-Ordner neu geschrieben. Der erste Lauf mit einem GTA-V-Ordner erstellt den Archivindex mit einem einzelnen Worker. Ausgabedateien und -namen bleiben unverändert.
- **Leiseres Protokoll (0.2.0).** Harmlose Blender-DDS-Warnungen stehen weiterhin in `wct_export.log`, werden aber nicht mehr Zeile für Zeile in der App angezeigt: am Ende erscheint eine Zusammenfassungszeile mit den Zahlen. Echte Fehler werden weiterhin als `error`-Zeilen angezeigt.
- **Weniger `.ytyp`-Dateien (0.2.1).** GTA lädt höchstens 3000 `.ytyp`-Dateien (den `MapTypesStore`-Pool); mehr lässt das Spiel mit `MapTypesStore Pool Full` abstürzen. Die Archetypen werden jetzt in `wctchunk_*.ytyp`-Dateien (je 250 Modelle) geschrieben und in `fxmanifest.lua` aufgeführt. Exportiere alle benötigten Kategorien in einem Lauf: jeder Lauf schreibt diese Blöcke aus dem, was er exportiert hat, neu. Exporte aus 0.1.x lassen sich ohne erneuten Export konvertieren: `blender --background --python core\merge_ytyps.py -- "<out>\models\whip_media_clothing_male\stream" "<out>\models\whip_media_clothing_female\stream"` (die Originale werden nach `ytyp_single` verschoben).

### Funktionen

- **Vorschauen** : transparente PNG/WebP-Bilder (oder deckendes JPEG) mit festem Blickwinkel und fester Beleuchtung, damit alle Items konsistent aussehen. Jede Texturvariante verwendet die Farben ihrer eigenen `.ytd`.
- **Modelle** : exportiert `.ydr` + `.ytd`-Paare und `.ybn`-Kollisionsdateien nur dann, wenn das Quellmodell echte Bounds enthält.
- **Polygon-Optimierung** : Meshes werden um etwa 30 % dezimiert, wobei UV-, Material- und Normalen-Nähte beachtet werden. Skin-Gewichte, Shader, Kollisionsgrenzen und Metadaten bleiben erhalten. Meshes unter 200 Dreiecken bleiben unverändert.
- **Automatische Optimierung** : Texturen werden vor dem Schreiben der `.ytd` auf 512 px reduziert, indem Mip-Ebenen ohne Re-Encoding entfernt werden. Im Test waren die Texturdateien etwa 57 % kleiner, Farben und Alpha unverändert. Die eingesparten MB werden im Protokoll gemeldet.
- **Quellen** : Vanilla-GTA-V-Legacy-RPFs, lose Addon-Ordner (rekursive Suche) oder beides.
- **Alle Varianten** : jeder Drawable und jede Texturvariante wird automatisch exportiert; die Namen werden aus der Quelldatei erzeugt.
- **Ein Ausgabeordner** : die App erstellt `models/` und `previews/`, unterteilt nach Geschlecht und Slot.

### Bedienung

- Ein einzelner Bildschirm mit den Modi Models / Previews / Both und getrennten Kategorie-Auswahlen.
- Validierung des GTA-V-Ordners und der Addon-Packs mit rekursiver Zählung von `.ydd`/`.ytd`.
- Merkt sich Pfade und alle Exporteinstellungen zwischen zwei Starts.
- Echtzeit-Fortschrittsbalken und Logs für Vorbereitung und Blender-Export, mit automatischem Scrollen und Fertig-Anzeige.
- Oberfläche auf **English, Italiano, Español, Français, Deutsch**.

### Voraussetzungen

- Windows 10/11 (64-Bit)
- **Blender 4.2+ / 5.x** mit installiertem und aktiviertem Add-on **Sollumz**
- GTA V Legacy nur für die Quelle Vanilla oder Both

Es ist kein System-Python nötig: die eigentliche Arbeit läuft in Blender, das `szio`, PyMateria und Sollumz bereits mitbringt.

### Installation und Start

1. Lade `whip-clothing-tool-v0.2.1-portable-win64.zip` herunter und entpacke es beliebig. `whip_clothing_tool.exe` liegt im **Stammverzeichnis** des entpackten Ordners, neben `core/`.
2. Führe einmal `install-dependencies.ps1` aus, um Blender und Sollumz automatisch zu installieren (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Mit `-Dev` werden zusätzlich Node.js, Rust und die Visual Studio Build Tools installiert.
3. Starte `whip_clothing_tool.exe`. Es gibt keinen Installer für die App.
4. Wähle Ausgabeordner und Quellen, markiere die Kategorien und klicke auf **Export**.

Falls Blender nicht in `PATH` liegt, setze die Umgebungsvariable `WCT_BLENDER` auf den Pfad von `blender.exe`.

### Spawnbare Modelle

Jedes Modell in `stream/` ist ein normalisiertes statisches Objekt (`normal_spec.sps`, Color 1 `#FF8000`, Color 2 `#000000`) mit einem binären GEN8-`.ytyp`-Archetyp (flags 32, lodDist 100, hdTextureDist 5, Bounds aus den echten Vertizes). Das erzeugte `fxmanifest.lua` enthält `this_is_a_map 'yes'` und eine `data_file 'DLC_ITYP_REQUEST' 'stream/wctchunk_*.ytyp'`-Zeile pro Block (je 250 Modelle). Kopiere die Ressource nach `resources/` und starte sie in der `server.cfg`.

**Nach dem Hinzufügen oder Ersetzen von Dateien in `stream/` muss jeder Client die Verbindung vollständig trennen und neu verbinden**: `refresh` + `restart` aktualisieren bereits heruntergeladene Dateien nicht. Falls `RequestModel` nach einer sauberen Wiederverbindung weiterhin scheitert, verwendet die App `prop_cap_01` als letzten Ausweg.

### Hinweise

- Der erste Lauf mit Vanilla-Quelle erstellt den RPF-Index in `<output root>/.wct_cache/`; das kann einige Minuten dauern, danach wird der Cache genutzt.
- Kollisionen werden nur geschrieben, wenn die Quelle echte Bounds enthält.
- JPEG unterstützt keine Transparenz: für transparente Vorschauen PNG oder WebP verwenden.
- Props stammen aus den Basisdateien `streamedpedprops.rpf/mp_[mf]_freemode_01_p/`, die der Ped tatsächlich trägt. DLC-Dateien mit demselben Namen werden ignoriert, es sei denn, der Drawable existiert nicht im Basis-Set — so wird kein Themen-Helm statt der Basismütze exportiert. Es werden nur die Basis-Texturvarianten `a`–`h` (Indizes 0–7) exportiert; höhere Indizes nutzen den Textur-0-Fallback der Registry. Der echte Texturname aus dem `.ytd` wird in den `diffusesampler` des gespawnten Objekts geschrieben.
- Das vollständige Export-Protokoll liegt in `<output root>/wct_export.log`; harmlose Blender-DDS-Warnungen stehen in der Datei, werden aber in der App ausgeblendet.
- Alle Pfade werden in der App gewählt: der Build enthält keine Spiel-, Server- oder Benutzerpfade.
