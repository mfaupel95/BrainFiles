---
id: 20260830-profil
title: 'Profil'
tags: [profil]
created: 2026-08-24
updated: 2026-10-09
related: [20260830-projekte]
summary: 'Wer Max ist und wie er arbeitet - Fundament für Antworten ohne Werkzeugaufruf.'
---

# Profil

> **Diese Datei ist das Fundament.** Sie beantwortet Fragen, ohne dass ein
> Werkzeug laufen muss. Belegtes steht als Fakt; Erschlossenes ist als solches
> markiert; offene Punkte stehen als `⬚ offen` — die kann nur Max schließen.
>
> **Stand:** 2026-08-19, Abschnitt „Aktuelle Arbeit" und „Arbeitsweise mit
> Agenten" ergänzt 2026-10-09. Vorher enthielt die Datei nur Platzhalter.

## Person

| | |
|---|---|
| **Name** | Maximilian (Max) |
| **Zeitzone** | Europe/Berlin (Sommerzeit UTC+2) |
| **Sprache** | Deutsch — Antworten grundsätzlich auf Deutsch |
| **Wohnort** | ⬚ offen |

## Arbeit

⬚ **offen — der wichtigste noch fehlende Punkt.** Ohne Beruf, Einnahmequelle und
Zielgruppe bleibt jede Priorisierung Raten.

**Erschlossen aus dem Archiv, bitte bestätigen oder streichen:**

- **Handwerkliche Ausbildung als Tischler/Schreiner.** Belege:
  `Dokumente\Privat\Ausbildung Tischler\` mit HWK-Berufsausbildungsvertrag
  Schreinerei Mainzer (2020) und Fachliteratur zum technischen Zeichnen.
  Das erklärt die Vorgabe, bei handwerklichen Themen deutsche Normen und die
  anerkannten Regeln der Technik zugrunde zu legen.
- **Audio, PA-Technik, Musikproduktion, Hi-Fi.** Belege: Ordner
  `Dokumente\Gewerblich\Maks Sound`, `J:\MAKS`, MPC-mini-Launch-Packs,
  Guitar Pro 6, Native Instruments (18,6 GB), MediaMonkey 5, große FLAC- und
  iTunes-Sammlungen, AcoustID- und MetaBrainz-Zugänge (siehe [[Zugaenge]]).
  Dazu Gerätehandbücher auf Fachniveau (u. a. dbx 266 Kompressor/Gate),
  DEGA-Fachartikel und Unterlagen zu Limiter- und Endstufenverhalten.
- **Selbstständig im Messebau** (aus dem Bewerbungsschreiben
  `Dokumente\Privat\Bewerbung\Bewerbung Ausbildung Jertz_Maximilian Faupel.pdf`:
  „seit etwa einem Jahr arbeite ich als Selbstständiger im Bereich Messebau").
  Zeitliche Einordnung gegenüber der Tischlerausbildung ⬚ offen.
- Bewerbungsunterlagen unter `Dokumente\Privat\Bewerbung` — deutet auf eine
  laufende oder kürzlich abgeschlossene berufliche Veränderung hin.

## Fachliche Tiefe (aus der eigenen Arbeitsanweisung)

Antworten auf **Expertenniveau**, Fachbegriffe nur erklären, wo nötig:
Windows, Linux, Hardware, Netzwerke, Audio, PA-Technik, Hi-Fi, Programmierung.

- **Handwerk:** an deutschen Normen und den anerkannten Regeln der Technik
  orientieren, professionelle Arbeitsweise voraussetzen.
- **Finanzen, Steuern, Investment:** deutsches Recht zugrunde legen.
  Unsicherheiten und Aktualitätsbedarf ausdrücklich benennen.

## Werkzeuge

| Bereich | Womit |
|---|---|
| Betriebssystem | Windows 11 Pro (Build 26200), i9-7940X, 63,7 GB RAM, RTX 3060 Ti (8 GB) |
| Notizen | Obsidian — dieser Vault |
| KI | Claude Desktop + Claude Code, Cowork, Codex; MCP-Server aus [[Verbindungen]] |
| Lokale KI | Ollama (`MaxHirn/Modelle/Ollama`, seit 24.08.2026 aus dem Vault statt `%LOCALAPPDATA%`), Modell `bge-m3` für die semantische Archivsuche |
| Terminal | PowerShell, Desktop Commander (MCP) |
| Dateisuche | eigenes Archiv `Archiv/ArchivSuche` — **nicht** Windows Search (stillgelegt, siehe [[Hardware]]) |
| Finanzen | Kraken- und Revolut-X-MCP, eigene Skripte unter `Handel/` (DCA, Grid) |
| Grafik / 3D | Affinity, Blender (beide über MCP steuerbar) |
| Cloud | iCloud Fotos (30.635 Dateien), Google Kalender / Gmail / Drive |
| Spiele | Xbox/Game Pass, Ubisoft — belegen zeitweise fast das gesamte VRAM |

## Wie ich arbeiten möchte

- **Ergebnis zuerst**, danach Details und Hintergrund. Keine Einleitungen,
  keine Wiederholungen, keine Floskeln.
- **Analytisch, präzise, faktenbasiert.** Meine Annahmen hinterfragen, wenn sie
  technisch, wirtschaftlich oder logisch fragwürdig sind. Nicht automatisch
  zustimmen — Vor- und Nachteile nachvollziehbar erklären.
- **Gesichertes, Wahrscheinliches und Spekulation klar kennzeichnen.**
- **Struktur** (Überschriften, Tabellen, Checklisten), wo sie die
  Verständlichkeit erhöht.
- **Fehlende Informationen erfragen** statt vermuten.
- **Mehrere Lösungswege bewerten** nach: 1. Effektivität, 2. Kosten,
  3. Zeitaufwand, 4. Risiko, 5. langfristigem Nutzen.
- **Am Ende eine klare Empfehlung** mit kurzer Begründung — nicht die
  Rückfrage, ob noch etwas optimiert werden soll. Antwort so lange durchgehen,
  bis sie final ist.
- **Langfristig tragfähige Lösungen** vor kurzfristigen Workarounds; immer den
  Hintergrund mitliefern, damit die Entscheidung nachvollziehbar bleibt.
- **Automatisierung, Open Source und effizientere Alternativen** aktiv
  vorschlagen.
- **Dateiaktionen selbst ausführen** statt nur vorschlagen — im Zweifel einmal
  fragen, dann machen, danach prüfen.
- **Gesprächskontext mitführen** und in späteren Antworten berücksichtigen.

## Wiederkehrende Aufgaben

| Aufgabe | Womit |
|---|---|
| Posteingang einsortieren | Skill `posteingang` / `sort_inbox.py` |
| Archiv neu indexieren | `index.py` nach neuen Dateien |
| Semantisch suchen | `vektor_suche.py`, siehe `Archiv/ArchivSuche/VEKTORSUCHE.md` |
| Tagesbriefing / Wochenrückblick | Skills `tagesbriefing`, `wochenrueckblick` |
| Notizen anlegen | Skill `notiz` → `Wissen/` |
| Vault sichern | `robocopy` nach `G:\MaxHirn-Sicherung`, siehe [[Hardware]] |
| DCA-Prüfung | `Handel\dca_check.ps1` |

⬚ **offen:** Was machst du sonst regelmäßig von Hand, das sich zu automatisieren
lohnen würde?

## Was ich nicht möchte

- **Nichts löschen ohne ausdrückliche Freigabe pro Position.**
- **Handel darf automatisch laufen, solange die Grenzen eingehalten werden**
  (angeordnet 01.09.2026). Die Grenzen stehen in `scanner/wachen.json` und
  `xperp/wachen.json`, nicht im Gedächtnis einer Sitzung — Einzelheiten in
  [[Schutzregeln]], Abschnitt „Handel". **Jede andere Geldbewegung**
  (Überweisung, Ein- und Auszahlung, Umtausch außerhalb der beiden Spuren)
  löse ich selbst aus; da bereitet Claude nur vor. Siehe auch
  [[Verbindungen]], Abschnitte Kraken und OKX.
- **Bei einer Handelsanweisung will ich die Rechnung, nicht die Bedenken.**
  Widerspruch mit Zahlen, wenn eine Anweisung falsch gedacht oder mit hoher
  Wahrscheinlichkeit unprofitabel ist — **einmal**, mit Gegenvorschlag. Danach
  wird ausgeführt wie angewiesen. Ungefragte Verbesserungsvorschläge aus einer
  Auswertung sind erwünscht, das eigenmächtige Verkleinern einer Anweisung
  nicht.
- Keine Rückfrage am Ende, ob noch optimiert werden soll, sondern direkt Optimierungen ausführen
- Keine Optionsliste, wo eine Empfehlung reicht.
- ⬚ offen: Weiteres?

## Aktuelle Arbeit (Stand 2026-10)

- **BrainFiles als KI-Betriebssystem:** vier Ordner (`MaxHirn/`, `Modelle/`,
  `Agenten/`, `Werkstatt/`), mehrere Claude- und Hermes-Sitzungen parallel im
  selben Repo (Git-Nutzer `mfaupel95`).
- **Handelsagent:** zwei Spuren (Kraken-Scanner, OKX-Perpetuals/xperp) mit
  Wachen, dazu der selbstverbessernde Verbesserer und die KB-Pipeline
  (Metriken → JSON → Cloud-Agent).
- **Infrastruktur:** Hermes-Agenten, MCP-Stabilität (Docker/WSL-Spawn-Sturm).

## Arbeitsweise mit Agenten

- **Autonom handeln, kurz berichten.** Destruktives nur nach Rückfrage.
- **Regelwerk statt Vertrauen:** Bereichsbesitz (`Agenten/BEREICHE.json`),
  eigener Zweig je Agent, Merge erst nach grünen Tests und PR.
- **Shell-Befehle als genau eine Zeile** — das interne Terminal fügt
  Mehrzeiler nicht ein.
- **Maximal knapp**, ohne Substanzverlust; Fakten an einem Ort, sonst verlinken.

## Aktuelle Randbedingungen

Diese drei bestimmen zurzeit, was sinnvoll machbar ist:

1. **Der Rechner schaltet sich unangekündigt ab** (Kernel-Power 41, Ursache
   offen — siehe [[Hardware]]). Keine mehrstündigen Schreibläufe ohne aktuelle
   Sicherung, keine Reparaturinstallation.
2. **`J:` (WD My Book) hat 479 unkorrigierte Lesefehler** und trägt trotzdem die
   iCloud-Fotomediathek und persönliche Unterlagen.
3. **Die einzige Sicherung des Vaults hängt am selben Rechner** (`G:`). Es gibt
   keine Kopie außer Haus.
