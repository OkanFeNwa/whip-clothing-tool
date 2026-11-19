# Whip Clothing Tool

Whip Clothing Tool est une application de bureau Windows qui exporte des ressources **vêtements GTA V** pour les workflows **FiveM (WHIP)** :

- Génère des **aperçus** (même angle et même éclairage pour la cohérence) avec **fond transparent**, au **format** et à la **taille** choisis.
- Exporte des **modèles prop** pour les vêtements lâchés/lancés : produit **`.ydr` + `.ytd`** (et fichiers de collision optionnels si pris en charge) dans un **dossier que vous choisissez**.
- **Optimise automatiquement les polygones** d’environ 30 % avec une décimation qui respecte les coutures UV, matériau et normales ; poids du squelette, shaders, limites et métadonnées sont préservés.
- **Optimise automatiquement les textures** à 512 px avant d’écrire les `.ytd`, en conservant la compression et la chaîne de mips d’origine (aucun réencodage : couleurs et alpha préservés). Le journal indique les MB économisés.
- Prend en charge **vanilla uniquement**, **packs addon uniquement** ou **les deux**.
- Interface multilingue : **Anglais, Italien, Espagnol, Français, Allemand**.

> L’application est **portable** : aucun installateur et aucun chemin GTA/WHIP suggéré. Vous choisissez toujours les dossiers dans l’app.

## Documentation

- English: [../../README.md](../../README.md)
- Italiano: [README.it.md](README.it.md)
- Español: [README.es.md](README.es.md)
- Deutsch: [README.de.md](README.de.md)

## Fonctionnalités

### Aperçus
- Rendu avec **angle et éclairage fixes** pour tous les articles.
- **Fond transparent**.
- Choix : source (Vanilla / Addon / Les deux), **dossier de sortie**, **taille** (saisie manuelle), **format** (sélecteur).

### Modèles prop
- Exporte `.ydr` + `.ytd` dans le dossier choisi.
- Collisions optionnelles selon le pipeline.
- Pas de chemins codés : sélection via l’explorateur.

## Prérequis
Windows 10/11 64 bits, Blender 4.2+/5.x avec Sollumz activé, GTA V Legacy uniquement pour la source Vanilla. Aucun Python système requis : le travail réel s’exécute dans Blender.

## Installation automatique des dépendances
Extrayez le ZIP : `whip_clothing_tool.exe` est à la **racine** du dossier, à côté de `core/`.
Exécutez une fois :

```powershell
powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1
```

Le script détecte Blender, installe la dernière extension Sollumz depuis la version officielle GitHub, l’active et vérifie `szio`/`pymateria` dans Blender. Avec `-Dev`, il installe aussi Node.js, Rust et les Visual Studio Build Tools pour recompiler l’application.

## Modèles instanciables
Chaque modèle dans `stream/` est un objet statique normalisé (`normal_spec.sps`, Color 1 `#FF8000`, Color 2 `#000000`) avec un `.ytyp` binaire GEN8 et une ligne `DLC_ITYP_REQUEST` dans le `fxmanifest.lua` généré. Les fichiers sous `img/clothing/` gardent les shaders ped d’origine pour le système de vêtements WHIP. Les props proviennent toujours du fichier de base `streamedpedprops.rpf/mp_[mf]_freemode_01_p/`, jamais de la première DLC portant le même nom. Seules les textures de base `a`–`h` (indices 0–7) sont exportées ; les autres utilisent le repli texture 0 du registre. Le vrai nom de texture est écrit dans le `diffusesampler` de l'objet. Certains `.ydd` de base sont des placeholders de 4 sommets (par exemple `p_eyes_000.ydd`) : dans ce cas l'outil utilise automatiquement le premier DLC avec une géométrie réelle et l'indique dans le champ `source` du manifeste.

Copiez `models/whip_media_clothing_<genre>/` dans `resources/` et démarrez-le dans `server.cfg`. **Après avoir ajouté ou remplacé des fichiers dans `stream/`, chaque client doit se reconnecter entièrement** : `refresh` + `restart` ne mettent pas à jour les fichiers déjà téléchargés. Si `RequestModel` échoue encore après une reconnexion propre, l’application utilise `prop_cap_01` en dernier recours.

## Journal d’export
L’application écrit toute la sortie dans `<output root>/wct_export.log`. Les avertissements DDS non fatals de Blender restent dans le fichier mais sont masqués dans l’interface.

## Collisions
Dépendent des `.ybn`/bounds. Si disponibles, à inclure dans la sortie ; sinon l’app avertit.

## Développement
Voir le `README.md` principal.