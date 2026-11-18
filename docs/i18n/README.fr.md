# Whip Clothing Tool

Whip Clothing Tool est une application de bureau Windows qui exporte des ressources **vêtements GTA V** pour les workflows **FiveM (WHIP)** :

- Génère des **aperçus** (même angle et même éclairage pour la cohérence) avec **fond transparent**, au **format** et à la **taille** choisis.
- Exporte des **modèles prop** pour les vêtements lâchés/lancés : produit **`.ydr` + `.ytd`** (et fichiers de collision optionnels si pris en charge) dans un **dossier que vous choisissez**.
- Prend en charge **vanilla uniquement**, **packs addon uniquement** ou **les deux**.
- Interface multilingue : **Anglais, Italien, Espagnol, Français, Allemand**.

> Application destinée à être **installée** (installateur). Aucun chemin WHIP codé en dur : vous choisissez toujours les dossiers dans l’app.

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
Windows 10/11 64 bits, GTA V Legacy pour le vanilla, Python 3.10+ et (selon le pipeline) Blender + Sollumz. L’installateur doit inclure ou guider l’installation.

## Collisions
Dépendent des `.ybn`/bounds. Si disponibles, à inclure dans la sortie ; sinon l’app avertit.

## Développement
Voir le `README.md` principal.