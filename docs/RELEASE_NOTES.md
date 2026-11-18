# Whip Clothing Tool — v0.1.0

Release notes in the languages supported by the app. English is the primary version.

---

## English

Whip Clothing Tool is a portable Windows app that exports GTA V clothing assets for FiveM / WHIP servers. This is the first public build: the export pipeline is fully functional and produces real files, not just empty folders.

### What it does

- **Previews** — transparent PNG/WebP (or opaque JPEG) renders with a fixed camera angle and lighting, so every item is visually consistent. Every texture variant uses its own `.ytd` colours.
- **Models** — exports `.ydr` + `.ytd` pairs, plus `.ybn` collision files when the source drawable actually contains collision bounds.
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

1. Download `whip-clothing-tool-v0.1.0-portable-win64.zip` and extract it anywhere. `whip_clothing_tool.exe` is at the **root** of the extracted folder, beside `core/`.
2. Run `install-dependencies.ps1` once to install Blender and Sollumz automatically (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Add `-Dev` to also install Node.js, Rust and the Visual Studio Build Tools.
3. Run `whip_clothing_tool.exe`. There is no app installer.
4. Pick the output root and the source folders, choose the categories, then press **Export**.

If Blender is not on `PATH`, set the `WCT_BLENDER` environment variable to your `blender.exe`.

### Output layout

```text
<output root>/
  models/whip_media_clothing_<male|female>/img/clothing/<gender>/<slot>/
  previews/whip_media_clothing_<male|female>/img/clothing/<gender>/<slot>/
  export_manifest.json
```

### Notes

- The first vanilla run builds an RPF index inside `<output root>/.wct_cache/`; it can take a few minutes, later runs reuse the cache.
- Collisions are only written when the source contains real bounds; no placeholder collision is invented.
- JPEG does not support transparency. Use PNG or WebP for transparent previews.
- All input/output paths are selected in the app. The build contains no game, server or user paths.

---

## Italiano

Whip Clothing Tool è un’app portable per Windows che esporta asset di abbigliamento GTA V per server FiveM / WHIP. Questa è la prima build pubblica: la pipeline di export è completa e genera file reali, non solo cartelle vuote.

### Cosa fa

- **Anteprime**: PNG/WebP trasparenti (o JPEG opaco) con angolazione e illuminazione fisse, così ogni capo è coerente. Ogni variante texture usa i colori del proprio `.ytd`.
- **Modelli**: esporta coppie `.ydr` + `.ytd` e file di collisione `.ybn` solo quando il modello sorgente contiene bounds reali.
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

1. Scarica `whip-clothing-tool-v0.1.0-portable-win64.zip` ed estrailo dove vuoi. `whip_clothing_tool.exe` è nella **root** della cartella estratta, accanto a `core/`.
2. Esegui una volta `install-dependencies.ps1` per installare Blender e Sollumz automaticamente (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Aggiungi `-Dev` per installare anche Node.js, Rust e i Visual Studio Build Tools.
3. Avvia `whip_clothing_tool.exe`. Non c’è installer per l’app.
4. Scegli output root e cartelle sorgente, seleziona le categorie e premi **Export**.

Se Blender non è in `PATH`, imposta la variabile d’ambiente `WCT_BLENDER` con il percorso di `blender.exe`.

### Note

- La prima esecuzione vanilla crea l’indice RPF in `<output root>/.wct_cache/`; può volerci qualche minuto, poi viene riutilizzato.
- Le collisioni vengono scritte solo se la sorgente contiene bounds reali.
- JPEG non supporta la trasparenza: usa PNG o WebP.
- Tutti i percorsi si scelgono nell’app: la build non contiene percorsi di gioco, server o utente.

---

## Español

Whip Clothing Tool es una aplicación portable para Windows que exporta recursos de ropa de GTA V para servidores FiveM / WHIP. Esta es la primera compilación pública: el proceso de exportación es completo y genera archivos reales, no solo carpetas vacías.

### Qué hace

- **Vistas previas**: PNG/WebP transparentes (o JPEG opaco) con ángulo e iluminación fijos, para que todas las prendas sean coherentes. Cada variante de textura usa los colores de su `.ytd`.
- **Modelos**: exporta pares `.ydr` + `.ytd` y archivos de colisión `.ybn` solo cuando el modelo de origen contiene bounds reales.
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

1. Descarga `whip-clothing-tool-v0.1.0-portable-win64.zip` y extráelo donde quieras. `whip_clothing_tool.exe` está en la **raíz** de la carpeta extraída, junto a `core/`.
2. Ejecuta una vez `install-dependencies.ps1` para instalar Blender y Sollumz automáticamente (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Añade `-Dev` para instalar también Node.js, Rust y Visual Studio Build Tools.
3. Ejecuta `whip_clothing_tool.exe`. No hay instalador de la app.
4. Elige la carpeta de salida y las fuentes, selecciona las categorías y pulsa **Export**.

Si Blender no está en `PATH`, define la variable de entorno `WCT_BLENDER` con la ruta a `blender.exe`.

### Notas

- La primera ejecución con fuente vanilla crea el índice RPF en `<output root>/.wct_cache/`; puede tardar unos minutos, después se reutiliza.
- Las colisiones solo se escriben si la fuente contiene bounds reales.
- JPEG no admite transparencia: usa PNG o WebP.
- Todas las rutas se eligen en la app: la compilación no contiene rutas de juego, servidor ni usuario.

---

## Français

Whip Clothing Tool est une application portable Windows qui exporte des ressources de vêtements GTA V pour les serveurs FiveM / WHIP. C’est la première version publique : le pipeline d’export est complet et produit de vrais fichiers, pas seulement des dossiers vides.

### Fonctionnalités

- **Aperçus** : PNG/WebP transparents (ou JPEG opaque) avec angle et éclairage fixes, pour que chaque vêtement soit cohérent. Chaque variante de texture utilise les couleurs de son propre `.ytd`.
- **Modèles** : exporte des paires `.ydr` + `.ytd`, ainsi que des fichiers de collision `.ybn` uniquement lorsque le modèle source contient de vrais bounds.
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

1. Téléchargez `whip-clothing-tool-v0.1.0-portable-win64.zip` et extrayez-le où vous voulez. `whip_clothing_tool.exe` est à la **racine** du dossier extrait, à côté de `core/`.
2. Exécutez une fois `install-dependencies.ps1` pour installer Blender et Sollumz automatiquement (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Ajoutez `-Dev` pour installer aussi Node.js, Rust et les Visual Studio Build Tools.
3. Lancez `whip_clothing_tool.exe`. Il n’y a pas d’installateur pour l’application.
4. Choisissez le dossier de sortie et les sources, sélectionnez les catégories, puis cliquez sur **Export**.

Si Blender n’est pas dans `PATH`, définissez la variable d’environnement `WCT_BLENDER` avec le chemin vers `blender.exe`.

### Remarques

- Le premier passage avec la source vanilla crée l’index RPF dans `<output root>/.wct_cache/` ; cela peut prendre quelques minutes, les passages suivants réutilisent le cache.
- Les collisions ne sont écrites que si la source contient de vrais bounds.
- JPEG ne gère pas la transparence : utilisez PNG ou WebP.
- Tous les chemins sont choisis dans l’app : la compilation ne contient aucun chemin de jeu, de serveur ou d’utilisateur.

---

## Deutsch

Whip Clothing Tool ist eine portable Windows-App, die GTA-V-Kleidungs-Assets für FiveM-/WHIP-Server exportiert. Dies ist der erste öffentliche Build: Die Export-Pipeline ist vollständig und erzeugt echte Dateien statt leerer Ordner.

### Funktionen

- **Vorschauen** : transparente PNG/WebP-Bilder (oder deckendes JPEG) mit festem Blickwinkel und fester Beleuchtung, damit alle Items konsistent aussehen. Jede Texturvariante verwendet die Farben ihrer eigenen `.ytd`.
- **Modelle** : exportiert `.ydr` + `.ytd`-Paare und `.ybn`-Kollisionsdateien nur dann, wenn das Quellmodell echte Bounds enthält.
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

1. Lade `whip-clothing-tool-v0.1.0-portable-win64.zip` herunter und entpacke es beliebig. `whip_clothing_tool.exe` liegt im **Stammverzeichnis** des entpackten Ordners, neben `core/`.
2. Führe einmal `install-dependencies.ps1` aus, um Blender und Sollumz automatisch zu installieren (`powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1`). Mit `-Dev` werden zusätzlich Node.js, Rust und die Visual Studio Build Tools installiert.
3. Starte `whip_clothing_tool.exe`. Es gibt keinen Installer für die App.
4. Wähle Ausgabeordner und Quellen, markiere die Kategorien und klicke auf **Export**.

Falls Blender nicht in `PATH` liegt, setze die Umgebungsvariable `WCT_BLENDER` auf den Pfad von `blender.exe`.

### Hinweise

- Der erste Lauf mit Vanilla-Quelle erstellt den RPF-Index in `<output root>/.wct_cache/`; das kann einige Minuten dauern, danach wird der Cache genutzt.
- Kollisionen werden nur geschrieben, wenn die Quelle echte Bounds enthält.
- JPEG unterstützt keine Transparenz: für transparente Vorschauen PNG oder WebP verwenden.
- Alle Pfade werden in der App gewählt: der Build enthält keine Spiel-, Server- oder Benutzerpfade.
