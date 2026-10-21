# n8n lokal (Docker) — konkrete Rezepte

Stand 11.10.2026: n8n 2.42.6 als Container `n8n` (n8nio/n8n:latest), nur
`127.0.0.1:5678`, `--restart unless-stopped`. Daten in
`Agenten/Hermes/cache/n8n-data` (Volume), Eingangskorb-Mount
`cache/n8n-eingang` -> `/data/eingang`. Owner `max@faupel.local`, Passwort in
`Wissen/Zugaenge.md` (nie ausgeben). Doku: `MaxHirn/Wiki/Werkzeuge/n8n.md`.

## Container starten

```bash
docker run -d --name n8n --restart unless-stopped \
  -p 127.0.0.1:5678:5678 \
  -v "C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/cache/n8n-data:/home/node/.n8n" \
  -v "C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/cache/n8n-eingang:/data/eingang" \
  -e GENERIC_TIMEZONE=Europe/Berlin -e TZ=Europe/Berlin \
  -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_SECURE_COOKIE=false \
  -e NODE_FUNCTION_ALLOW_BUILTIN=fs \
  n8nio/n8n:latest
```

`NODE_FUNCTION_ALLOW_BUILTIN=fs` ist PFLICHT, wenn ein Code-Knoten Dateien
schreiben soll — ohne es: `Module 'fs' is disallowed` (Sandbox blockt
Node-Core-Module).

## Owner-Konto (erster Start)

Neuere n8n ignoriert `N8N_USER_MANAGEMENT_DISABLED` und zeigt den Setup-Flow
(`showSetupOnFirstLoad: true`). Owner headless anlegen:

```bash
curl -s -X POST http://127.0.0.1:5678/rest/owner/setup \
  -H 'Content-Type: application/json' \
  --data '{"firstName":"Max","lastName":"Faupel","email":"max@faupel.local","password":"<generiert>"}'
```

- E-Mail muss eine gueltige TLD haben — `max@localhost` wird mit 400
  `Invalid email` abgewiesen; `max@faupel.local` geht.
- Passwort generieren (`secrets.token_urlsafe(18)`), NIE in Chat/Log ausgeben,
  in `Wissen/Zugaenge.md` haengen (Muster ai4trade/neu_anlegen.py).

## Workflow headless importieren + aktivieren

1. Workflow-JSON nach `Agenten/Hermes/cache/n8n-eingang/` legen. **Root-Feld
   `"id"` setzen** — n8n 2.x verlangt es, sonst
   `SQLITE_CONSTRAINT: NOT NULL constraint failed: workflow_entity.id`.
2. Import:
   `docker exec n8n n8n import:workflow --input="/data/eingang/<datei>.json"`
3. Aktivieren + Neustart (CLI-Aenderungen wirken erst nach Restart):
   `docker exec n8n n8n update:workflow --id=<id> --active=true && docker restart n8n`
   Ohne den Restart antwortet der Webhook mit `Cannot POST /webhook/<pfad>`.

## Workflow-Schema (Webhook -> Code-Knoten)

- Webhook-Node: `type: n8n-nodes-base.webhook`, `typeVersion: 2`, `path`,
  `responseMode: onReceived`.
- Code-Node: `type: n8n-nodes-base.code`, `typeVersion: 2`. Der Request-Body
  liegt direkt in `$input.first().json` (kein `.body`-Feld bei
  `Content-Type: application/json`). Datei schreiben mit `fs.appendFileSync`
  auf den gemounteten Pfad (`/data/eingang/...`).
- Verbindung: `connections: { "<Webhook>": { "main": [[{node, type: "main", index: 0}]] } }`.

## Wache

`Agenten/Hermes/scripts/n8n-wache.py` + Hermes-Cron `n8n-wache`
(id b198bd6aab97, alle 15 min, no_agent, Telegram). Watchdog-Muster: leere
Ausgabe = nichts senden. UI kaputt + Container tot -> `docker start n8n`
(heilt, meldet); UI kaputt + Container laeuft -> Meldung, kein Neustart
(max 1x/6h, Merkdatei `cache/n8n-wache.json`).

## Fallen

- **Code-Knoten-Sandbox**: `fs` gesperrt ohne `NODE_FUNCTION_ALLOW_BUILTIN=fs`.
- **Import braucht Root-`id`** (siehe oben).
- **Aktivierung braucht Restart** (siehe oben).
- **Zugangsdaten**: liegen im Volume (n8n-data) — Container loeschen/neu bauen
  verliert nichts, aber auch nicht die Credentials.
