---
id: 20260830-index
title: 'Wissen — Index'
tags: [betrieb]
created: 2026-08-30
updated: 2026-08-30
related: []
summary: 'Einstiegspunkt für Agenten: vollständiges Verzeichnis aller Notizen in Wissen/ mit Zweck und Pfad.'
---

# Wissen — Index

Verbindliches Verzeichnis aller Notizen in `Wissen/`. Diese Datei ist die
Wahrheit darüber, **welche** Notizen es gibt; [[Dashboard]] bleibt die
kuratierte Startseite für Menschen und zeigt bewusst nur einen Teil.

## Für Agenten: so wird gelesen

1. Erst diesen Index lesen, dann anhand der Beschreibungen **1–3 Notizen**
   gezielt öffnen. Nicht den ganzen Ordner einlesen.
2. Was hier steht, wird nicht neu erhoben. Eine Zahl aus einer Notiz wird
   zitiert, nicht nachgemessen.
3. Beim Zitieren die `id` aus dem Frontmatter angeben, nicht den Dateinamen.

## Für Agenten: so wird gepflegt

- Neue dauerhafte Erkenntnis → **neue Notiz** mit vollständigem Frontmatter
  (`id`, `title`, `tags`, `created`, `updated`, `related`, `summary`).
- Bestehendes Thema geändert → Notiz **an Ort und Stelle** ändern und
  `updated` hochsetzen. Keine zweite Notiz zum selben Thema.
- Jedes Anlegen, Umbenennen oder Löschen einer Notiz **muss im selben
  Arbeitsschritt** hier in der Registry nachgezogen werden.
- `id` ist dauerhaft: `JJJJMMTT-slug`, wird nie geändert und nie wiederverwendet.
  Der Dateiname darf sich ändern, die `id` nicht.
- Nur Schlagwörter aus der Liste unten verwenden. Ein neues Schlagwort wird
  **erst hier eingetragen**, dann benutzt.
- Querverweise als `[[Dateiname]]` setzen und die Gegenstelle in `related`
  (dort mit `id`) spiegeln.

## Schlagwörter (kontrolliert)

`archiv`, `betrieb`, `finanzen`, `handel`, `hardware`, `holz`, `ki-agenten`,
`mcp`, `profil`, `sicherheit`, `steuern`, `system`

## Registry

Format: `` `id` — **Titel** — `Pfad` — wofür.``

### Betrieb und Agenten

- `20260830-verbindungen` — **Verbindungen** — `Wissen/Verbindungen.md` — Welche Dienste und MCP-Server erreichbar sind und welche davon authentifiziert.
- `20260830-werkzeuge` — **Werkzeuge** — `Wissen/Werkzeuge.md` — Welche Werkzeuge tatsächlich abgerufen werden, gemessen an den bisherigen Sitzungen.
- `20260830-hermes` — **Hermes Agent** — `Wissen/Hermes.md` — Einrichtung, Ablageorte und Fallstricke des Hermes-Agenten neben Claude.
- `20260831-python-versionen` — **Python-Versionen** — `Wissen/Python-Versionen.md` — Installierte Python-Versionen und venv-Konfigurationen nach dem Upgrade auf 3.13.
- `20260830-routinen` — **Routinen** — `Wissen/Routinen.md` — Welche Abläufe ohne Aufforderung laufen, mit Zeitplan und Protokollort.
- `20260830-wiederholbare-aufgaben` — **Wiederholbare Aufgaben** — `Wissen/Wiederholbare-Aufgaben.md` — Welche Arbeit sich wiederholt hat und welche Skills daraus entstanden sind.
- `20260830-portabilitaet` — **Portabilität** — `Wissen/Portabilitaet.md` — Was beim Umzug des gesamten Systems auf eine externe SSD zu beachten ist.
- `20260830-ordnerstruktur` — **Ordnerstruktur** — `Wissen/Ordnerstruktur.md` — Die vier Ordner unter `BrainFiles/`, warum sie geteilt sind und welche fünf Fallen beim Verschieben still brechen.
- `20260830-fristen` — **Fristen** — `Wissen/Fristen.md` — Alle laufenden Termine mit Konsequenz, ISO-datiert, gepflegt vom Skill `frist`.

### System und Hardware

- `20260830-hardware` — **Hardware** — `Wissen/Hardware.md` — Laufwerke des Arbeitsrechners, Plattendiagnose und der ungeklärte Stromausfall.
- `20260830-hardware-checkliste-d5` — **Hardware-Checkliste D5** — `Wissen/Hardware-Checkliste-D5.md` — Schrittfolge zur Eingrenzung des D5-RAM-Fehlers und der Kernel-Power-41-Abschaltungen.
- `20260830-benutzerprofil` — **Benutzerprofil** — `Wissen/Benutzerprofil.md` — Was im Windows-Benutzerprofil liegt, was davon zum Betrieb gehört und was Altlast ist.
- `20260830-ki-ablagen-benutzerordner` — **KI-Ablagen im Benutzerordner** — `Wissen/KI-Ablagen-im-Benutzerordner.md` — Welche KI-Daten außerhalb von `BrainFiles/` liegen, warum sie dort bleiben und was bei einem Neuaufsetzen verlorenginge.
- `20260830-miniaturansichten` — **Miniaturansichten** — `Wissen/Miniaturansichten.md` — Warum der Explorer keine Vorschaubilder mehr zeigte und was dagegen geholfen hat.

### Sicherheit

- `20260830-schutzregeln` — **Schutzregeln** — `Wissen/Schutzregeln.md` — Welche Dateien in `MaxHirn/` ein Agent nicht anfassen darf und warum.
- `20260830-zugaenge` — **Zugänge** — `Wissen/Zugaenge.md` — Zentrale und einzige Ablage aller API-Schlüssel und Tokens. **Geschützt: nur auf ausdrückliche Anweisung ändern, kein Frontmatter.**
- `20260830-passwoerter-quarantaene` — **Passwörter-Quarantäne** — `Wissen/Passwoerter-Quarantaene.md` — Arbeitsliste der Dienste aus dem Firefox-Export, deren Passwörter noch zu ändern sind.

### Steuern und Geld

- `20260830-steuerunterlagen` — **Steuerunterlagen** — `Wissen/Steuerunterlagen.md` — Steuernummern, veranlagte Jahre, Bescheide und laufende Verfahren.
- `20260830-belege-einspruch-2024` — **Belege zum Einspruch ESt 2024** — `Wissen/Belege-Einspruch-2024.md` — Welche Nachweise gesammelt sind und was bis 30.09.2026 noch fehlt.
- `20260830-handelsbots` — **Handelsbots auf OKX** — `Wissen/Handelsbots.md` — Gemessene Ergebnisse der DCA-Bots und welche Stellschraube tatsächlich wirkt.
- `20260831-marktscanner` — **Marktscanner OKX** — `Wissen/Marktscanner.md` — Täglicher Krypto-Scanner mit begrenztem Selbsthandel: Entscheidung, Grenzen, Scharfschalt-Weg, Stand.
- `20260830-marktlage-august-2026` — **Marktlage August 2026** — `Wissen/Marktlage-August-2026.md` — Geprüfter Marktstand samt Bewertung der zugrunde liegenden Quelle.

### Person und Fachliches

- `20260830-profil` — **Profil** — `Wissen/Profil.md` — Wer Max ist und wie er arbeitet; Fundament für Antworten ohne Werkzeugaufruf.
- `20260830-projekte` — **Projekte** — `Wissen/Projekte.md` — Was gerade läuft, ein Abschnitt je Projekt.
- `20260830-fachkunde-holztechnik` — **Fachkunde Holztechnik** — `Wissen/Fachkunde-Holztechnik.md` — Inhalt und Ablage des Lehrwerks im Archiv.

### Verfahren

- `20260830-pdf-scans-lesen` — **Gescannte PDFs lesen** — `Wissen/PDF-Scans-lesen.md` — Wie PDFs ohne Textebene per OCR auswertbar gemacht werden.
