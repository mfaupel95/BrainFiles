---
id: 20260830-projekte
title: 'Projekte'
tags: [profil, betrieb]
created: 2026-08-24
updated: 2026-09-03
related: [20260830-profil]
summary: 'Was gerade läuft, ein Abschnitt je Projekt, Erledigtes bleibt unten stehen.'
---

# Projekte

Was gerade läuft. Ein Abschnitt je Projekt. Abgeschlossenes nach unten unter
„Erledigt" schieben statt löschen — der Kontext bleibt so erhalten.

## Aktiv

### KI-Betriebssystem

- **Ziel:** Ein persönliches Betriebssystem nach dem Muster
  „Wissen / Verbindungen / Skills / Routinen", bedienbar durch **mehrere**
  Agenten auf derselben Wissens- und Werkzeugschicht.
- **Stand (2026-08-19):** Grundgerüst steht. [[Profil]] ist befüllt.
  `BrainFiles/` enthält nur noch `MaxHirn/` — `Claude_prompts` und `KI Futter`
  liegen jetzt unter `Referenz/`, damit der SSD-Umzug vollständig ist.
  Zugangsdaten zentral in [[Zugaenge]]. Sicherung über `sichern.ps1` mit
  Ausschlüssen (Tageslauf unter einer Minute statt Stunden).
- **Stand (2026-08-23):** [[Hermes]] als zweiter Agent eingebunden — Daten in
  `MaxHirn/Hermes/`, Code in `C:\Hermes`, alle 11 MCP-Server und die 11 eigenen
  Skills übernommen, Schreib-Sandbox auf den Vault begrenzt. Gemeinsame Regeln
  für beide Agenten in `AGENTS.md`. **Läuft noch nicht** — der Anthropic-Token
  fehlt (`claude setup-token`).
- **Nächste Schritte:** Hermes-Token setzen (siehe [[Hermes]]), Verbindungen
  authentifizieren (siehe [[Verbindungen]]), Routinen einplanen (siehe
  [[Routinen]]), offene Punkte im [[Dashboard]].
- **Blockiert durch:** die ungeklärten Stromausfälle (siehe [[Hardware]]) —
  nichts Langlaufendes, bis das steht.

### Lokale KI

- **Ziel:** Suche und Auswertung eigener Daten, ohne dass sie den Rechner
  verlassen. Wachstum über Index und Notizen, **nicht** über Training —
  ein Modell lernt beim Benutzen nichts dazu.
- **Stand (2026-08-19):** Stufe 1 läuft. Semantische Archivsuche lokal über
  Ollama + `bge-m3`, 1.076 Dateien / 11.965 Abschnitte, eigener Vektorindex
  neben dem Volltextindex. Beschreibung in `Archiv/ArchivSuche/VEKTORSUCHE.md`.
- **Seit 24.08.2026:** Ollama läuft aus `MaxHirn/Modelle/Ollama` statt aus
  `%LOCALAPPDATA%` — portabel und bewusst als gemeinsamer Ort für Stufe 1 und
  Stufe 2 angelegt, nicht als Unterordner von ArchivSuche oder Hermes.
  Modelldaten liegen über `OLLAMA_MODELS` ebenfalls dort
  (`MaxHirn/Modelle/Ollama/models`), nicht mehr unter `%USERPROFILE%\.ollama`.
- **Wichtig zur Einordnung:** Ein Cloud-Modell mit lokaler Suche schützt die
  Daten *nicht* — der lokal gefundene Kontext wird mitgesendet. Schutz entsteht
  nur dort, wo die Inferenz läuft.
- **Offen:** Stufe 2 — lokales Sprachmodell über dieselbe Ollama-Laufzeit für
  alles mit Personenbezug. Grenze ist der VRAM: 8 GB reichen für 7–8B in Q4/Q5,
  12–14B nur knapp. Vorher festlegen, welche Ordner schützenswert sind.

### Digitales Archiv

- **Ziel:** Alle eigenen Dateien (Bilder, Videos, Musik, Dokumente) durchsuchbar
  an einem Ort.
- **Stand:** Läuft. Volltextsuche mit OCR unter `Archiv/ArchivSuche/`,
  Posteingang-Sortierung automatisiert.
- **Offen:** Restliche PDFs im Posteingang, die sich nicht sicher zuordnen ließen.

## Erledigt

