---
titel: Puter self-hosted (Internet-Computer)
aktualisiert: 2026-10-10
tags: [werkzeug, docker, selfhosting, fremd]
---

# Puter self-hosted — der Open-Source-"Internet-Computer"

Der Fork-Klon von [HeyPuter/puter] ("The Open-Source Internet Computer" - ein
Web-Desktop/Personal-Cloud-OS, MIT) als `mfaupel95/puter` (origin),
`upstream` = `HeyPuter/puter`, liegt seit **10.10.2026** in
`Werkstatt/puter` (vorher an der BrainFiles-Wurzel, umgezogen, T-380).
Dazu gehoert der laufende `docker compose`-Stack in
`Werkstatt/puter/puter-selfhosted/`.

## Was laeuft (gemessen 10.10., 6 Container, alle up)

| Container | Bild | Port |
|---|---|---|
| puter-caddy | caddy:2.11-alpine | **0.0.0.0:80** (HTTP) |
| puter | ghcr.io/heyputer/puter:main | 4100 intern |
| puter-s3 | rustfs/rustfs (S3-Objektstore) | 9000-9001 intern |
| puter-mariadb | mariadb:11 | 3306 intern |
| puter-dynamo | amazon/dynamodb-local | 8000 intern |
| puter-valkey | valkey/valkey:8-alpine | 6379 intern |

Compose-Datei: `Werkstatt/puter/puter-selfhosted/docker-compose.yml`
(Services valkey, mariadb, dynamo, s3, s3-init, ollama, ollama-init, puter,
puter-smtp, caddy; Ollama-Baustein mit Volume `./puter/data/ollama`). Alle
Container laufen mit `restart: unless-stopped` - sie ueberleben Neustarts von
selbst. puter und caddy haengen per `depends_on: service_healthy` an mariadb.

## Umzug 10.10.2026: Machen und Fallen

**Umziehen heisst: `docker compose down`, Ordner verschieben, `up -d` vom
NEUEN Ort.** Die laufenden Container mounten weiter den alten (dann leeren)
Pfad - erst `down`, sonst zeigen `/etc/puter` und `/var/puter` ins Leere.

FALLE (gemessen 10.10.): nach dem Umzug meldete mariadb `unhealthy` mit
`Access denied for user root (using password: NO)`, obwohl die Env stimmte.
Ursache: `.my-healthcheck.cnf` im mariadb-Datadir war **world-writable (777)**
geworden (Umzug/Windows-Seite) - MariaDB IGNORIERT world-writable Config-Dateien
und der Healthcheck verlor damit sein Passwort. Fix im laufenden Container:
`chmod 600 /var/lib/mysql/.my-healthcheck.cnf` (danach wird er healthy).
Kontrolle: `mariadb --defaults-extra-file=/var/lib/mysql/.my-healthcheck.cnf -e
"SELECT 1"` muss 1 liefern.

ZWEITE FALLE: `docker compose -f <pfad>` aus einer ANDEREN cwd laedt die `.env`
des Projekts nicht - leere/Default-Passwoerter. Also immer aus
`puter-selfhosted/` starten.

## Zugangsdaten - nicht anfassen

Unter `puter-selfhosted/` liegen `.env` und `puter/config/config.json` (Stufe 0
nach Schutzregeln). Beide werden **nicht gelesen** und hier nicht wiedergegeben.
Hinweis: das Erst-Boot-Log des puter-Containers zeigt ein generiertes Passwort
im Klartext (`docker logs puter`) - Zugang zum Stack, Wert nie ausgeben.
