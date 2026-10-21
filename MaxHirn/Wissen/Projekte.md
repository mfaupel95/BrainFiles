---
id: 20260830-projekte
title: 'Projekte'
tags: [profil, betrieb]
created: 2026-08-24
updated: 2026-10-13
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

### Windows-Profilstruktur (Teilprojekt B)

- **Ziel:** Die Windows-Profilebene für eine spätere Linux-/WSL-Nutzung ordnen;
  `BrainFiles/` selbst bleibt unverändert. WSL als Hauptumgebung und eine
  vollständige Linux-Migration sind spätere, getrennte Teilprojekte.
- **Festgelegt:** Dotfolder pragmatisch behandeln — nur Anwendungen verschieben,
  die XDG, Umgebungsvariablen oder `--config-dir` nativ unterstützen; übrige
  Speicherorte dokumentieren, keine erzwungenen Symlinks.
- **Stand (2026-10-13):** User-PATH bereinigt: fünf bestätigte tote und zwei
  fehlerhafte Einträge entfernt; 29 Einträge verbleiben. Volta und Python 3.13
  bleiben die maßgeblichen Interpreter. Direkte Node.js-Installation unter
  `Program Files` nur dokumentieren, nicht deinstallieren; `.local\\Python\\bin`
  unverändert lassen. Eine erste Bestandsaufnahme fand rund 80 Dotfolder/-dateien.
- **Offen:** Bestandsaufnahme und Entscheidungsmatrix für Dotfolder/XDG erstellen.
  `.claude.json`-Backups und -Temp-Dateien sowie drei als archiviert markierte
  Hermes-Verzeichnisse sollten sofort bereinigt werden. Die Hermes-Verzeichnisse
  sind jedoch ungeklärt: direkte Abfrage ergab im ersten Ordner nur zwei Dateien,
  während rekursive Messungen für alle drei jeweils rund 237 GB und 3,54 Mio.
  Elemente meldeten. Nichts davon löschen, bevor Ursache und tatsächlicher Inhalt
  nachvollziehbar verifiziert sind. Die jüngsten Detailabfragen konnten wegen
  vorübergehender Nichtverfügbarkeit des Ausführungsdienstes nicht abgeschlossen
  werden.
- **Stand (2026-10-21), Umzug nativ ausgeführt:** matplotlib, kube und Rust
  (`.cargo` + `.rustup` nach `.config\`) umgezogen und verifiziert; Umgebungsvariablen
  gesetzt, Rust-PATH-Eintrag angepasst. Zurückgestellt: `.docker` (6,9 GB Modelle, nur
  Client-Konfiguration per `DOCKER_CONFIG` abdeckbar), `.bun` (nicht im PATH, laufende
  Prozesse), `aws`/`azure` (leer, CLIs nicht installiert), `dotnet`, `git`/`npm`
  (Entscheidung ausstehend). Protokoll: `Werkstatt/Protokolle/2026-10-21-profil-umzug.txt`.
- **Offen:** `.dotnet\tools` steht wieder im User-PATH und ist tot; Herkunft unklar.
  Entscheidung über `.docker`-Aufteilung und git/npm ausstehend.
- **Nächste Schritte:** Entscheidungen oben einholen, dann alte Ordner (`.matplotlib`,
  `.kube`, `.cargo`, `.rustup`) vom Nutzer entfernen lassen, sobald die Verifikation
  bestätigt ist.

### Digitales Archiv

- **Ziel:** Alle eigenen Dateien (Bilder, Videos, Musik, Dokumente) durchsuchbar
  an einem Ort.
- **Stand:** Läuft. Volltextsuche mit OCR unter `Archiv/ArchivSuche/`,
  Posteingang-Sortierung automatisiert.
- **Offen:** Restliche PDFs im Posteingang, die sich nicht sicher zuordnen ließen.

### Jev Trader

- **Ziel:** Demo-Trading-Bot (`O:\Werkstatt 2\JEV\jev-trader`): Jev (TypeSafe-AI-Modell)
  entscheidet pro Monad-Block (~300 ms) "buy" oder "sell" für MON-USDC, aus
  Orderbuch- und Taker-Flow-Daten von Kurus On-Chain-Orderbuch. Backend (Bun)
  platziert je Block eine Post-only-Limitorder; Next.js-Dashboard zeigt den
  Feed live per SSE. `MODEL=mock` ist nur eine Heuristik zum Infrastrukturtest,
  `MODEL=jev` nutzt das echte Modell. `DRY_RUN=true`/fehlender `PRIVATE_KEY`
  verhindert echte Trades; Positions- und Margin-Limits begrenzen den Einsatz.
- **Stand (2026-10-13):** Lokal lauffähig, Skill `.claude/skills/run-jev-trader/`
  angelegt und end-to-end verifiziert (Backend-Smoke-Test + Playwright-Screenshot
  des Dashboards). Dry-Run-Papiertest mit `mock` lief fehlerfrei. `TYPESAFE_AI_API_KEY`
  als Windows-Benutzervariable gesetzt (Eintrag in [[Zugaenge]]) und in die
  Projekt-`.env` übernommen, damit der nächste Papiertest mit dem echten
  Jev-Modell laufen kann.
- **Einsatzgrenzen:** Eng an Markt und Venue gebunden — Code und Modell-Prompt
  sind fest auf MON-USDC/Kuru/Monad zugeschnitten, kein generisches
  Trading-Framework. Ein anderes Paar oder eine andere Chain braucht
  Codeänderungen, kein reines Config-Flag.
- **Nächste Schritte:** Papiertest mit echtem Jev-Modell (weiterhin `DRY_RUN=true`)
  laufen lassen und auswerten; danach ein zweites Kuru-Marktpaar für einen
  weiteren Test auswählen.

## Erledigt

