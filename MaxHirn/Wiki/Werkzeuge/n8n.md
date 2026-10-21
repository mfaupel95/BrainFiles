# n8n (lokal, Docker)

Seit 11.10.2026: n8n 2.42.6 als Docker-Container `n8n` (n8nio/n8n:latest), nur auf
`127.0.0.1:5678` gebunden (`-p 127.0.0.1:5678:5678`), `--restart unless-stopped`.

## Zugang

- UI: http://localhost:5678
- Owner-Konto: `max@faupel.local` — Passwort steht in `MaxHirn/Wissen/Zugaenge.md`
  (Abschnitt n8n). Nie in Chat/Log ausgeben.
- Daten: `Agenten/Hermes/cache/n8n-data` (n8n-DB, Workflows, Credentials) — wird mit
  Agenten/ mitgesichert, ist NICHT git-versioniert (cache-Regel).

## Erster Workflow: Eingangskorb

`POST http://127.0.0.1:5678/webhook/eingang` mit JSON-Body → haengt eine Zeile
(ISO-Zeitstempel + JSON) an `notizen.jsonl` im Eingangsordner.

- Im Container: `/data/eingang/notizen.jsonl`
- Auf dem Host: `Agenten/Hermes/cache/n8n-eingang/notizen.jsonl`
- Workflow-Name: "Eingangskorb (Webhook zu Datei)", id 991001 (Root-id im Import-JSON noetig)

## Workflows hinzufuegen (headless, ohne UI-Klick)

1. Workflow-JSON nach `Agenten/Hermes/cache/n8n-eingang/` legen (Root-Feld `"id"` setzen!)
2. Import: `docker exec n8n n8n import:workflow --input="/data/eingang/<datei>.json"`
3. Aktivieren (+ Neustart, weil CLI-Aenderungen erst nach Restart wirken):
   `docker exec n8n n8n update:workflow --id=<id> --active=true && docker restart n8n`

## Wache

`Agenten/Hermes/scripts/n8n-wache.py` + Hermes-Cron `n8n-wache` (id b198bd6aab97,
alle 15 min, no_agent, Telegram). Watchdog-Muster: leere Ausgabe = nichts senden.
- UI kaputt + Container tot → `docker start n8n` (heilt, meldet)
- UI kaputt + Container laeuft → `docker restart n8n` (haengende Port-Weiterleitung,
  stateful im Volume, kein Verlust) — meldet
- Heilversuch hoechstens alle 6 h (Merkdatei `Agenten/Hermes/cache/n8n-wache.json`),
  Erholung wird immer gemeldet

## Fallen

- **Code-Knoten**: `fs` ist in der Sandbox gesperrt — der Container laeuft mit
  `NODE_FUNCTION_ALLOW_BUILTIN=fs`. Ohne dieses Env: "Module 'fs' is disallowed".
- **Import**: n8n 2.x verlangt eine Root-`"id"` im Workflow-JSON (sonst
  `SQLITE_CONSTRAINT: NOT NULL constraint failed: workflow_entity.id`).
- **Aktivierung**: `update:workflow --active=true` schreibt nur die DB — der Webhook
  antwortet erst nach `docker restart n8n` (Log: "Changes will not take effect if n8n is running").
- Zugangsdaten im Container liegen im Volume (n8n-data) — Container loeschen/neu bauen
  verliert nichts.
