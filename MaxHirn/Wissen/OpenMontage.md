---
id: 20260917-openmontage
title: 'OpenMontage: Agentisches Videoproduktions-Framework'
tags: [ki-agenten, betrieb]
created: 2026-09-17
related: [20260916-repo-bots]
summary: 'Fork von calesthio/OpenMontage - 12 Produktionspipelines fuer KI-generierte
  Videos (Explainer, Dokumentar, Avatar, Screen-Demo), gesteuert von einem
  Coding-Agenten. Am 17.09.2026 lokal eingerichtet: 41 von 121 Werkzeugen laufen
  ohne einen einzigen API-Schluessel.'
updated: 2026-09-17
---

# OpenMontage: Agentisches Videoproduktions-Framework

## Was es ist

[OpenMontage](https://openmontage.video) ist kein fertiges Tool, sondern ein
**Framework fuer einen KI-Coding-Agenten** (Claude Code, Cursor, Copilot,
Codex): der Agent liest eine Pipeline-Definition (YAML), fuehrt sie ueber eine
**Werkzeug-Registry** aus (121 Werkzeuge: Bildgenerierung, Video, TTS, Musik,
Untertitel, Schnitt) und liefert am Ende eine gerenderte Videodatei. 517
Python-Dateien, 1.091 Markdown-Dateien (Skills + Pipeline-Anleitungen),
AGPL-3.0, 59.574 Sterne beim Original.

**12 Pipelines** (`pipeline_defs/*.yaml`): animierter Erklaerfilm,
Dokumentar-Montage (echtes Filmmaterial), Avatar-Sprecher,
Charakter-Animation, Cinematic, Clip-Factory, Hybrid, Lokalisierung/Dubbing,
Podcast-Repurposing, Screen-Demo, Talking-Head.

## Herkunft und Ablage

- Fork `mfaupel95/openmontage` ← `calesthio/OpenMontage` (Original: 59.574
  Sterne, AGPL-3.0, zuletzt gepusht 06.09.2026).
- Klon `Werkstatt/Repos/openmontage`, `origin`=Fork, `upstream`=Original,
  shallow (`git fetch --unshallow` vor einem Push in eigene Arbeit — siehe
  `repo-flotte`-Falle).
- Hermes-Bot `openmontage` (`--clone`, `terminal.backend local`,
  `terminal.cwd` im Klon) — gleicher getrimmter Skillstand wie die uebrige
  Flotte (31 geladen, 70 archiviert).

## Am 17.09.2026 eingerichtet und live gemessen

| Schritt | Ergebnis |
|---|---|
| `.venv` (Python 3.14) + `pip install -r requirements.txt` | ok |
| `remotion-composer` (Node, `npm install`) | 199 Pakete, 0 Fehler (3 Advisories, keine kritisch) |
| Werkzeug-Registry laden (`tools.tool_registry.registry.discover()`) | laeuft, 121 Werkzeuge erkannt |

**Capability-Check ohne einen einzigen API-Schluessel** (`.env` bewusst nicht
angelegt — keine Schluessel im Klartext im Fremd-Repo, siehe Schutzregeln):

```
Tools gesamt: 121 | verfuegbar: 41 (vor Piper-Fix: 37)
  video_post        9/9   analysis         7/13
  character_anim.   6/6   screen_capture   3/3
  subtitle          2/2   audio_processing 2/2
  video_generation  0/27  image_generation 0/17
  tts               0/11  music_generation 0/5
```

**Video- und Bildgenerierung bleiben bei 0** — die brauchen zwingend einen
bezahlten oder kostenlosen Cloud-Schluessel (fal.ai, Google, OpenAI, Runway
...). Das ist keine Fehlkonfiguration, das ist die Natur der Sache: es gibt
keinen lokalen Weg, ein Video oder ein Bild aus dem Nichts zu generieren, der
mit 8 GB VRAM sinnvoll laeuft.

## Die Piper-Falle (repo-flotte, bestaetigt)

`piper_tts` (das einzige TTS-Werkzeug ohne Cloud-Konto) meldete zuerst
`unavailable`, obwohl `pip install piper-tts` in der Repo-`.venv`
durchgelaufen war. Ursache: `tools/audio/piper_tts.py` prueft
`shutil.which("piper")` — das findet nur einen Befehl **auf dem PATH**, nicht
ein Paket in einer fremden venv. Fix: `uv tool install piper-tts` (landet in
`~/.local/bin`, das schon im Benutzer-PATH steht) — danach `piper_tts:
available`. Zusaetzlich `youtube_transcript_api` und `pygments` installiert
(`transcript_fetcher`, `code_snippet`) — leichte reine Python-Pakete, kein
GPU-Bedarf.

**Bewusst nicht installiert:** `torch`, `transformers`, `faster_whisper`,
`rembg`, `gfpgan`, `realesrgan` (Video-Verstehen, Untertitel-Transkription,
Hintergrund-Entfernung, Gesichts-/Bild-Hochskalierung) — mehrere GB Download
fuer Faehigkeiten, die auf der RTX 3060 Ti (8 GB VRAM) ohnehin nur eingeschraenkt
laufen. Bei Bedarf gezielt einzeln nachziehen.

## Kostenlose naechste Schritte (aus `docs/PROVIDERS.md`, Stufe 1+2)

1. **Pexels + Pixabay** (`PEXELS_API_KEY`, `PIXABAY_API_KEY`) — Stock-Fotos
   und -Videos, kostenlos, reicht fuer einfache Videos ohne KI-Bildgenerierung.
2. **Google API Key** (`GOOGLE_API_KEY`) — 700+ TTS-Stimmen, 1 Mio. Zeichen/
   Monat gratis, plus 300 $ Neukonto-Guthaben (deckt dann auch Imagen-Bilder).
3. **ElevenLabs** — Premium-TTS + Musik + SFX, 10.000 Zeichen/Monat gratis.

Schluessel gehoeren nach [[Zugaenge]], niemals in eine `.env` im Fremd-Repo-Baum
(diese liegt unter `Werkstatt/`, die keine Sicherung mitzieht).

## Aufruf

```powershell
cd Werkstatt\Repos\openmontage
.venv\Scripts\python.exe -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.support_envelope(), indent=2))"
```

Fuer den Agenten selbst: `AGENT_GUIDE.md` zuerst lesen (Pipeline-Auswahl,
Werkzeug-Registry, Freigabe-Checkpoints), dann `PROJECT_CONTEXT.md`. Kein
eigenes `skill --install` — siehe `skill-library-sync`, keine SKILL.md des
Fremd-Repos in die Haus-Bibliothek uebernehmen.

Verwandt: [[Repo-Bots]], `repo-flotte`-Skill (Fallen: PATH vs. venv,
Fremd-Repo-Software vs. reine Doku).
