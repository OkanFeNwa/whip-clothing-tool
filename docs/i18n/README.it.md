# Whip Clothing Tool

Whip Clothing Tool è un’app desktop per Windows che esporta asset **abbigliamento GTA V** per **FiveM (WHIP)**:

- Genera **anteprime** (stessa angolazione e stessa illuminazione per coerenza) con **sfondo trasparente**, in **formato** e **dimensione** scelti.
- Esporta **modelli prop** per vestiti che cadono/vengono lanciati: produce **`.ydr` + `.ytd`** (e file di collisione opzionali, se supportati) in una **cartella scelta da te**.
- **Ottimizza automaticamente i poligoni** di circa il 30% con decimazione che rispetta le cuciture UV, materiale e normali; pesi dello scheletro, shader, bounds e metadati restano intatti.
- **Ottimizza automaticamente le texture** a 512 px prima di scrivere i `.ytd`, mantenendo compressione e mip originali (nessuna ricompressione: colori e alpha intatti). Il log mostra i MB risparmiati.
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

## Modelli spawnabili
Ogni modello in `stream/` è un prop statico normalizzato (`normal_spec.sps`, Color 1 `#FF8000`, Color 2 `#000000`) con un `.ytyp` binario GEN8 e una voce `DLC_ITYP_REQUEST` nell'`fxmanifest.lua` generato. I file sotto `img/clothing/` mantengono gli shader ped originali per il sistema abbigliamento WHIP. I prop vengono sempre presi dal file base `streamedpedprops.rpf/mp_[mf]_freemode_01_p/`, non dalla prima DLC omonima. Solo le texture base `a`–`h` (indici 0–7) vengono esportate; gli altri usano il fallback texture 0 del registry. Il nome reale della texture viene scritto nel `diffusesampler` del prop. Alcuni `.ydd` base sono placeholder da 4 vertici (per esempio `p_eyes_000.ydd`): in quel caso il tool usa automaticamente la prima DLC con geometria reale e lo indica nel campo `source` del manifest.

Copia `models/whip_media_clothing_<genere>/` in `resources/` e avviala in `server.cfg`. **Dopo aver aggiunto o sostituito file in `stream/`, ogni client deve riconnettersi completamente**: `refresh` + `restart` non aggiornano i file già scaricati. Se `RequestModel` fallisce ancora dopo una riconnessione pulita, l'app usa come ultima risorsa `prop_cap_01`.

## Log di export
L'app scrive tutto l'output in `<output root>/wct_export.log`. I warning DDS non fatali di Blender restano nel file ma sono nascosti nell'interfaccia.

## Collisioni
Dipendono da `.ybn`/bounds nel modello. Se esportabili, includili nella cartella di output; altrimenti l’app avvisa (oggetto potrebbe comportarsi male in game).

## Sviluppo
Vedi `README.md` principale.