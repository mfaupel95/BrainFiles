---
name: skill-artifact-capabilities
description: Trockenlauf des Skills artifact-capabilities — Runtime-Capabilities für Artifact-Seiten (db, room, sample, user, artifact, assets, mcp, downloads, files, comments); Deklaration und Nutzungsmuster; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Artifact-Seiten mit serverseitigen Fähigkeiten ausstatten, die statisches HTML nicht kann.

**Wann nutzen:** Vor jeder Seite, die persistente Daten, Echtzeit-Kollaboration, KI-Abfragen oder Datei-Uploads braucht.

**Lauf:** 2026-10-22, trockenlauf.

**Deklaration:** `capabilities: {name: config}` im Artifact-Publish-Aufruf. Weglassen = bestehendes beibehalten; `{}` = alles löschen.

**Zugangsmuster (für alle Capabilities):**
```js
const ns = await claude.use("capabilityName");
if (!ns) { /* nicht verfügbar — UI verstecken */ return; }
```
`null` = nicht bereitgestellt, nicht erlaubt oder Ladefehler (alles gleich behandeln). Nie `window.claude.db` o.ä. lesen — nur `use()`.

**Die wichtigsten Capabilities:**

| Name | Deklaration | Wofür |
|---|---|---|
| `db` | `{db:{}, user:{}}` | Geteilte Daten außerhalb der Seite; Claude liest/schreibt; `onSnapshot` für Live-Updates |
| `artifact` | `{artifact:{}}` | Seite ist das Dokument — Polls, Listen, Boards; Viewer mit Schreibrecht publizieren neue Version |
| `room` | `{room:{}}` | Echtzeit-Präsenz und Events für alle die gerade die Seite offen haben; nichts wird gespeichert |
| `sample` | `{sample:{}}` | Claude aus der Seite heraus fragen; `await sample(prompt)` → `{text}` |
| `user` | `{user:{}}` | Wer schaut zu; `id()`, `me()`, `profiles(ids)` für Namen |
| `assets` | `{assets:{}}` | Datei-Upload in Asset-Store; nur Editors+ |
| `downloads` | `{downloads: true}` | Datei dem Viewer zum Speichern anbieten |
| `mcp` | `{mcp:{servers:[{server,tools}]}}` | Viewer-Konnektoren von der Seite aus aufrufen |
| `files` | `{files:{project:"chan_..."}}` | Claude-Code-Projektdateien lesen |
| `comments` | `{comments:{}}` | Kommentar-UI in die Seite einbauen |
| `permissions` | eingebaut, nie deklarieren | Berechtigungs-Status lesen/anfragen |

**Zustandsfrage — wo gehört was hin?**
- Per-Viewer-Komfort (Tab-Erinnerung, Entwurf): `localStorage`
- Seite IST das Dokument (Poll, Checkliste): `artifact` — ganzes Dokument neu generieren und publizieren
- Daten außerhalb (Claude liest/sät, viele Autoren, privat per User): `db`

**db — wichtigste Regeln:**
- Deklaration mit `user` zusammen: `{db:{}, user:{}}`
- Zugriffsregeln via `rules:[{path, read, write}]` — Levels: `view` < `interact` < `admin` < `owner`
- Private User-Daten unter `data/users/<id>/`
- Nie Standardwerte hardcoden — `write_db` nach Publish; leere DB behandeln
- `onSnapshot` einmal pro Query abonnieren, nie in Render-Funktion

**artifact — wichtigste Regeln:**
- Beim Publizieren: vollständiges HTML-Dokument mit Doctype; Zustand als Daten einbetten, nie DOM serialisieren
- Konflikt ist normal — kein Retry
- Read-only-Viewer: `not_granted`/`not_writer` → schreibgeschützte Ansicht zeigen

**sample — wichtigste Regeln:**
- `await sample(prompt)` — statuslos, immer Instruktionen+Daten mitschicken
- Erst nach User-Interaktion aufrufen (erste Call fragt Einwilligung)
- `not_granted` → verstecken; `rate_limited` → backoff; nie Schleife

**Verifikation nach Publish:** Ein funktionaler Pass — ein `ArtifactData list` jeder Collection; bei Zugriffs-Regeln auch mit niedrigerem `as_level` prüfen.
