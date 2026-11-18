# Whip Clothing Tool

Whip Clothing Tool è un’app desktop per Windows che esporta asset **abbigliamento GTA V** per **FiveM (WHIP)**:

- Genera **anteprime** (stessa angolazione e stessa illuminazione per coerenza) con **sfondo trasparente**, in **formato** e **dimensione** scelti.
- Esporta **modelli prop** per vestiti che cadono/vengono lanciati: produce **`.ydr` + `.ytd`** (e file di collisione opzionali, se supportati) in una **cartella scelta da te**.
- Supporta **solo vanilla**, **solo pack addon**, o **entrambi**.
- Interfaccia in più lingue: **Italiano, Inglese, Spagnolo, Francese, Tedesco**.

> L’app è **portable**: nessun installer e nessun percorso GTA/WHIP suggerito. Scegli sempre input/output nell’app.

## Documentazione

- English: [../../README.md](../../README.md)
- Español: [README.es.md](README.es.md)
- Français: [README.fr.md](README.fr.md)
- Deutsch: [README.de.md](README.de.md)

## Cosa fa

### Anteprime
- Render con **angolazione e luce fisse** (stesse per tutti i capi).
- **Sfondo trasparente**.
- Puoi scegliere: sorgente (Vanilla / Addon / Entrambi), **cartella di output**, **dimensione** (inserita a mano), **formato** (selettore: es. PNG, WebP; JPEG solo senza trasparenza).

### Modelli prop
- Esporta `.ydr` + `.ytd` in una cartella scelta.
- Eventuale export collisioni se supportato dal flusso scelto (vedi README principale).
- Niente percorsi hardcoded: tutto via esplora risorse.

## Requisiti
Windows 10/11 64-bit, Blender 4.2+/5.x con Sollumz abilitato, GTA V Legacy solo per la sorgente Vanilla. Non serve Python di sistema: il lavoro reale gira dentro Blender.

## Installazione automatica delle dipendenze
Estrai lo zip: `whip_clothing_tool.exe` è nella **root** della cartella, accanto a `core/`.
Esegui una volta:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1
```

Lo script rileva Blender, installa l'ultima estensione Sollumz dal release ufficiale di GitHub, la abilita e verifica `szio`/`pymateria` dentro Blender. Con `-Dev` installa anche Node.js, Rust e i Visual Studio Build Tools per ricompilare l'app.

## Collisioni
Dipendono da `.ybn`/bounds nel modello. Se esportabili, includili nella cartella di output; altrimenti l’app avvisa (oggetto potrebbe comportarsi male in game).

## Sviluppo
Vedi `README.md` principale.