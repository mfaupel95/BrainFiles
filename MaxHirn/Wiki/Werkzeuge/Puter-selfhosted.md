---
titel: Puter self-hosted (Internet-Computer)
aktualisiert: 2026-10-08
tags: [werkzeug, docker, selfhosting, fremd]
---

# Puter self-hosted — der Open-Source-„Internet-Computer“

**Stand 08.10.2026 (gemessen):** Eine andere Sitzung hat [HeyPuter/puter]
(„The Open-Source Internet Computer" — ein Web-Desktop/Personal-Cloud-OS, MIT)
als Fork `mfaupel95/puter` (origin), `upstream` = `HeyPuter/puter`, an die
**BrainFiles-Wurzel** geklont — nicht nach `Werkstatt/Repos`, wo Fremd-Repos
nach Hausregel liegen. Dazu gehört ein laufender `docker compose`-Stack
(`puter/puter-selfhosted/`, 170 MB), der **bereits gestartet ist**.

## Was läuft (gemessen 08.10., 6 Container, alle healthy)

| Container | Bild | Port |
|---|---|---|
| puter-caddy | caddy:2.11-alpine | **0.0.0.0:80** (HTTP) |
| puter | ghcr.io/heyputer/puter:main | 4100 intern |
| puter-s3 | rustfs/rustfs (S3-Objektstore) | 9000-9001 intern |
| puter-mariadb | mariadb:11 | 3306 intern |
| puter-dynamo | amazon/dynamodb-local | 8000 intern |
| puter-valkey | valkey/valkey:8-alpine | 6379 intern |

Compose-Datei: `puter/puter-selfhosted/docker-compose.yml` (Services valkey,
mariadb, dynamo, s3, s3-init, ollama, ollama-init, puter, puter-smtp, caddy;
Ollama-Baustein mit Volume `./puter/data/ollama`). Alle Container laufen mit
`restart: unless-stopped` — sie überleben Neustarts von selbst.

## Zugangsdaten — nicht anfassen

Unter `puter/puter-selfhosted/` liegen `.env` und `puter/config/config.json`
(Stufe 0 nach Schutzregeln). Beide wurden **nicht gelesen** und werden hier
nicht wiedergegeben — der Stack kann Schlüssel enthalten.

## Hausregel-Abweichung

Der Klon liegt an der BrainFiles-Wurzel statt in `Werkstatt/Repos` und ist
**untracked** (`git status` zeigt `?? puter/`). Er wird von der Whitelist
nicht abgedeckt — ein `git add -A` würde ihn als eingebettetes Repo anfassen.
Deshalb: nur eigene Pfade stagen. Umzug nach `Werkstatt/Repos` ist offen
(siehe Entscheidung unten).

## Offene Entscheidung (Max)

- Klon nach `Werkstatt/Repos/puter` verschieben und als Repo-Bot/profil
  anbinden (Hausmuster), oder Stack wieder abbauen?
- Läuft der Dienst dauerhaft (Port 80, Autostart über Docker), ist das ein
  Betriebsfakt, der hierher gehört.
