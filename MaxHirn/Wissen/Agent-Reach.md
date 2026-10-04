---
id: 20260916-agent-reach
title: 'Agent Reach: Internet-Zugang für Agenten'
tags: [ki-agenten, betrieb]
created: 2026-09-16
updated: 2026-09-16
related: [20260916-repo-bots]
summary: 'Fork von Panniantong/Agent-Reach als lesender Internet-Zugang (Twitter/X, Reddit, YouTube, GitHub, RSS, Web) ohne API-Schlüssel: Ablageort, Aufruf, Hermes-Profil.'
---

# Agent Reach: Internet-Zugang für Agenten (16.09.2026)

Geholt auf Max' Auftrag ("Github: Agent reach hinzufügen"). Es ist **kein**
Handelswerkzeug, sondern ein Zugang: Der Agent kann Twitter/X, Reddit, YouTube,
Bilibili, GitHub, RSS und beliebige Webseiten **lesen und durchsuchen**, ohne
API-Gebühren und ohne Schlüssel.

## Wo es liegt

| | |
|---|---|
| Repo | `Werkstatt/Repos/Agent-Reach` (2,2 MB, Python) |
| Herkunft | Fork `mfaupel95/Agent-Reach` von **`Panniantong/Agent-Reach`** (82.000 ★, MIT) |
| venv | `Werkstatt/Repos/Agent-Reach/.venv` (Requirements installiert, CLI vorhanden) |
| Bot | Hermes-Profil **`agent-reach`** mit `terminal.cwd` auf den Klon |
| Version | v1.5.0, laut `check-update` aktuell |

Aufruf (immer aus dem Repo-Ordner, sonst greift die venv nicht):

```powershell
cd Werkstatt/Repos/Agent-Reach
.\.venv\Scripts\agent-reach.exe doctor      # was geht gerade?
.\.venv\Scripts\agent-reach.exe setup       # geführte Einrichtung
.\.venv\Scripts\agent-reach.exe install     # Einzeiler mit Schaltern
```

## Was heute schon läuft (doctor, 5 von 16 Kanälen, 16.09.2026)

- **Beliebige Webseiten** über den Jina Reader (`https://r.jina.ai/<url>`) —
  geprüft: liefert Titel, Quelle und Text statt HTML.
- **RSS/Atom** — geprüft mit `feedparser` (tagesschau.de: 40 Einträge gelesen).
- **YouTube** (16.09.2026) — `yt-dlp 2026.08.19` liegt als uv-Werkzeug in
  `C:\Users\faupe\.local\bin\yt-dlp.exe` (dieser Ordner steht im Benutzer-PATH),
  dazu die JavaScript-Laufzeit in `C:\Users\faupe\.config\yt-dlp\config`
  (`--js-runtimes node`). Ohne diesen Eintrag meldet der Doctor „yt-dlp
  installiert, aber nicht einsatzbereit".
- **V2EX** (öffentliche API) und **Bilibili-Suche**.
- **GitHub** — das `gh`-CLI ist da und angemeldet (`doctor` verifiziert es nicht
  selbst, weil es dafür eine device-id schreiben müsste).

**Noch nicht freigeschaltet:** Twitter/X, Reddit, Facebook, Instagram,
小红书 (Xiaohongshu), 小宇宙-Podcasts, 雪球, LinkedIn, Boss直聘. Die
semantische Volltextsuche ist vorbereitet (`mcporter 0.13.13` und Exa sind
eingetragen, der Doctor prüft die Gegenstelle nicht), YouTube läuft seit
dem 16.09.2026. Freischalten geht über `agent-reach install` oder den Bot:
„installiere Reddit".

## Facebook und Instagram (16.09.2026)

Beide laufen ausschliesslich über **OpenCLI** (npm-Paket
`@jackwener/opencli` 1.8.7) und benutzen den **eigenen Chrome-Login** —
kein Cookie-Export, keine Zugangsdaten in Dateien.

Stand nach `install --env=auto --system --channels=facebook,instagram`:

| | |
|---|---|
| OpenCLI | installiert (`AppData\Roaming\npm\opencli`), Daemon läuft (Port 19825) |
| Browser-Extension | **nicht verbunden** — das ist der einzige fehlende Teil |
| Kanalstatus | `warn`: „opencli installiert, aber keine verbundene Browser-Extension" |

Die verbleibenden zwei Handgriffe gehen nur am Rechner:

1. Die Extension in Chrome/Edge installieren und aktiv lassen:
   https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk
2. In demselben Browser bei **facebook.com** und **instagram.com**
   angemeldet sein, dann einen `opencli`-Befehl laufen lassen — der Doctor
   schaltet den Kanal erst danach auf verfügbar.

**Zu bedenken:** die Extension handelt im Namen des angemeldeten Kontos; die
Doku von Agent Reach rät für solche Plattformen ausdrücklich zu einem
**Zweitkonto**. Gepostet wird nichts — die Kanäle lesen (Suche, Profil,
Feed, Gruppen).

## Was bewusst NICHT gemacht wurde

- **Kein Skill-Import.** `agent-reach skill --install` schreibt eine fremde
  SKILL.md in Agenten-Skill-Verzeichnisse. Für Hermes gilt `skill-library-sync`:
  aus fremden Bäumen wird nichts in die eigene Bibliothek übernommen - dieser
  Text ist die Hausfassung.
- **Keine Zugangsdaten hinterlegt.** Plattformen mit Anmeldung (Twitter, Reddit,
  Instagram ...) brauchen später Cookies oder Tokens. Die gehören nach
  `Wissen/Zugaenge.md`, nicht in eine `.env` im Fremd-Repo.

## Grenze

Das Werkzeug liest und sucht. Es postet nichts und handelt nicht. Der Nutzen für
Max liegt beim Research (Marktstimmung, Ankündigungen, Community-Reaktionen) —
und es ist der Weg, Inhalte von Plattformen zu lesen, die sonst eine teure API
oder einen Login verlangen.
