---
name: hermes-kompression-reparatur
description: "Fix Hermes compression when auxiliary models fail."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Hermes, Kompression, Auxiliary, Diagnose, Config]
    related_skills: [hermes-agent, hermes-doctor, hermes-maintenance]
---

# Hermes Kontext-Kompression reparieren (Auxiliary-Modell-Ausfall)

Diagnostiziert und repariert eine gebrochene Hermes-Kontext-Kompression: Sessions
wachsen unkomprimiert auf 190k+ Tokens, weil das Auxiliary-Kompressionsmodell
nicht ladbar/aufloesbar ist. Es AENDERT NICHTS am Code des Checkouts - nur die
Config (`auxiliary.compression` und Verwandte) ueber `hermes config set`. Stellt
KEINE notwendige Modellkosten-Abwaegung her: es waehlt das zuverlaessigste
verfuegbare Modell (Standard: das Hauptmodell) und dokumentiert die Alternativen.

## When to Use

- Logs zeigen `Pre-API compression made insufficient progress: X -> X`
- Logs zeigen `Failed to generate context summary: ... 404 ... not found`
- `Context is over the compression threshold ... compression is currently blocked`
- Sessions wachsen ohne sichtbare Kompression auf sehr hohe Token-Zahlen
- Nach einem Hermes-Update (Migration) ist die Kompression ploetzlich tot
- suspect: `auxiliary.compression` zeigt auf ein lokales GGUF / einen toten Server

## Prerequisites

- Hermes-Checkout unter `Agenten/Hermes/` (Windows, `bin/hermes.exe`).
- Vor JEDEM `hermes.exe`-Aufruf `PYTHONHOME` und `PYTHONPATH` entfernen
  (`env -u PYTHONHOME -u PYTHONPATH ...`) - uv-venv-Falle, sonst
  `Fatal Python error: init_import_site`.
- Der Hauptprovider `nous` muss angemeldet sein (`hermes doctor` ->
  "Nous Portal auth (logged in)").
- Heimverzeichmis der Config: `Agenten/Hermes/config.yaml` (Wahrheit).

## How to Run

    cd Agenten/Hermes && env -u PYTHONHOME -u PYTHONPATH ./bin/hermes.exe config check

Die Reparatur ist eine Reihe von `hermes config set`-Befehlen (nie Hands-Edit der
config.yaml - ein falscher Indent korrumpiert den Live-Gateway).

## Quick Reference

- Diagnose-Logs: `logs/errors.log`, `logs/gateway-stdio.log` (grep auf
  `compress|summary|404|cooldown|64,000`)
- Aktueller Zustand: `awk '/^auxiliary:/,/^display:/' config.yaml`
- Config pruefen: `hermes config check` (Exit 0 = sauber)
- Setzen: `hermes config set <pfad> <wert>`
- Kein Hot-Reload: wirkt erst ab naechster Session / Gateway-Neustart.

## Procedure

1. **Symptom bestaetigen** - in `logs/errors.log` und `logs/gateway-stdio.log`
   nach dem 404/insufficient-progress-Muster suchen:

   `search_files(pattern="Failed to generate context summary|insufficient progress", path="Agenten/Hermes/logs")`

   Kernzeile: `Model 'X' not found. The requested model does not exist in our
   configuration or OpenRouter catalog` - das ist der 404-Nachweis.

2. **Ursache lokalisieren** - den Compressions-/Auxiliary-Block ansehen:

   `awk '/^auxiliary:/,/^display:/' config.yaml`

   Verdaechtig: `auxiliary.compression.provider: llamacpp` (oder ein fremder
   Provider) mit einem lokalen GGUF-Modellnamen. Hermes loest Auxiliary-Modelle
   ueber den Nous/OpenRouter-Katalog auf (`agent/auxiliary_client.py`,
   Nous-spezifischer Self-Heal in `_ladder_nous_rungs`), NICHT ueber einen
   lokalen llama-server - ein GGUF-Name dort ergibt 404.

3. **Frueheren, laufenden Zustand aus Git holen** (falls Update zuruecksetzte):

   `git log --oneline -5 -- config.yaml` dann
   `git show <commit>^:config.yaml | grep -A8 "^auxiliary:"`

   Memory dokumentiert oft den letzten funktionierenden Wert.

4. **Kompressionsmodell auf das Hauptmodell umstellen** (zuverlaessigster Kanal):

   `env -u PYTHONHOME -u PYTHONPATH ./bin/hermes.exe config set auxiliary.compression.provider nous`
   `env -u PYTHONHOME -u PYTHONPATH ./bin/hermes.exe config set auxiliary.compression.model <hauptmodell>`

   Hauptmodell aus `model.default` + `model.provider` in config.yaml nehmen
   (z.B. `deepseek/deepseek-v4-flash-0731`, 786k Kontext). Gleiche
   Fehlerklasse betrifft auch `auxiliary.mcp` (MCP-Kompression) -
   konsistent umstellen.

5. **Schwelle pruefen/setzen** - ein Update-Migrationsschritt setzt
   `compression.threshold` gern auf 0.6-0.75 zurueck. Der dokumentierte Wert
   fuer fruehes Greifen (vor dem effektiven 200k-Fenster kleinerer
   Kompressionsmodelle) war 0.19:

   `env -u PYTHONHOME -u PYTHONPATH ./bin/hermes.exe config set compression.threshold 0.19`

6. **Andere Auxiliary-Pfade pruefen** - `auxiliary.skills_hub` kann auf ein
   Modell zeigen, das gar nicht als Hauptmodell ladbar ist (z.B. ein
   CLIP-Projektor wie `gemma-4-E4B-it-mmproj-BF16`: Log-
   `CLIP cannot be used as main model`). Auf `nous` + ein Flash-Modell stellen.

7. **Verifizieren** - siehe Verification.

## Pitfalls

- **Free-Routen ueber den OmniRoute-Router sind NICHT zuverlaessig**: Ein
  Router/Proxy kann Modelle auf `opencode` und andere Anbieter routen, die dann
  403 (`OpenCode free tier can only be used from within OpenCode`) oder 502
  (Timeout) liefern. `auto/coding:free`, `auto/best-free` scheiterten.
- **Lokales Ollama reicht meist nicht**: Modelle unter 64k Kontext lehnt Hermes
  ab (`below the minimum 64,000 required by Hermes Agent`). Kleine lokale
  Modelle (1.7B-35B mit 8k) sind unbrauchbar fuer Kompression.
- **Lokaler llama-server (Port 18434) ist instabil** (crasht, VRAM, "Invalid
  API Key" nach Neustart) - nicht als Kompressions-Endpoint verlassen.
- **curl gegen llama/OmniRoute ohne API-Key wirft 401**, das ist KEIN Beweis
  dass der Server tot ist - erst mit Key aus `.env`
  (`HERMES_CUSTOM_127_0_0_1_20128_API_KEY`) testen.
- **Windows-Mess-Pitfalls im `terminal`**: PowerShell-Inline mit `$` wird von
  bash verschluckt - als `.ps1` schreiben und `powershell -File` ausfuehren.
  `du`/`df` sind auf MSYS fuer grosse Baeume zu langsam/Timeout - PowerShell
  `Get-ChildItem -Recurse -File | Measure-Object Length -Sum` nutzen.
  `netstat`-Optionen sind auf Windows anders - `Get-NetTCPConnection -State
  Listen` verwenden.
- **Auxiliary-Modell = Hauptmodell** ist die sichere Wahl: gleicher Provider,
  nachweislich laufend, gross genug (>= 64k, idealerweise 786k).
- **Config-Neustart**: wirkt ab naechster Session/Gateway-Neustart.

## Verification

    env -u PYTHONHOME -u PYTHONPATH ./bin/hermes.exe config check && \
      awk '/^auxiliary:/,/^display:/' Agenten/Hermes/config.yaml

Erfolg: `config check` Exit 0 und `auxiliary.compression` zeigt auf `nous` +
Hauptmodell (kein `llamacpp`/GGUF-Name mehr). Der 404 in `logs/errors.log`
erscheint ab der naechsten Session nicht mehr.
