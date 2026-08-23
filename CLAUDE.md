# KI-Betriebssystem

Dieser Ordner (`MaxHirn/`) ist zugleich Obsidian-Vault und Wurzel von Max'
persönlichem KI-Betriebssystem. Alle Pfade hier sind **relativ zu dieser Wurzel**,
damit das System später unverändert auf eine externe SSD umziehen kann.

## Aufbau

| Modul | Ort | Inhalt |
|---|---|---|
| **Wissen** | `Wissen/` | Wer Max ist, laufende Projekte, Werkzeuge |
| **Archiv** | `Claude/` | Dateiarchiv mit Volltextsuche (eigene `CLAUDE.md`), 42 GB |
| **Skills** | `.claude/skills/` | eigene, wiederverwendbare Fähigkeiten |
| **Verbindungen** | `Wissen/Verbindungen.md` | MCP-Server und ihr Anmeldestatus |
| **Zugänge** | `Wissen/Zugaenge.md` | API-Schlüssel und Tokens — **einzige** Ablage |
| **Schutzregeln** | `Wissen/Schutzregeln.md` | was nicht angefasst werden darf — **vor jedem Schreibzugriff lesen** |
| **Referenz** | `Referenz/` | Fremdmaterial: Anleitungen, Beispiele, Installationspakete |
| **Routinen** | `Wissen/Routinen.md` | zeitgesteuerte Abläufe (Beschreibung) |

### Werkzeuge und Programme

Diese Ordner standen bis 23.08.2026 in keiner Übersicht, obwohl vier davon
zum laufenden Betrieb gehören:

| Ort | Inhalt | Größe |
|---|---|---|
| `MCP-Server/` | die Serverprogramme selbst — von Claude **und** Hermes gestartet, siehe [Wissen/Verbindungen.md](Wissen/Verbindungen.md) | 1,8 GB |
| `Routinen/` | Wrapper für die geplanten Aufgaben plus deren Protokolle in `logs/` | klein |
| `Handel/` | DCA-Agent (`agent.py`), eigenes `.venv`, eigenes README | 171 MB |
| `Hermes/` | Daten des zweiten Agenten: Konfiguration, Gedächtnis, Sitzungen. Der **Programmcode** liegt außerhalb unter `C:\Hermes` — siehe [[Hermes]] | 61 MB |
| `GitHub/` | geklonte Fremd-Repos, aus Git reproduzierbar. **Von der Sicherung ausgenommen** | 415 MB |
| `Codex/`, `Coworking-Space/` | Ablagen einzelner Sitzungen, kein Bestandteil des Betriebs | 71 / 336 MB |

Einstieg für Menschen: [Dashboard.md](Dashboard.md)

## Reihenfolge bei jeder Anfrage

1. **`Wissen/` zuerst.** Dort steht der persönliche Kontext (Profil, Projekte,
   Vorlieben). Er beantwortet viele Fragen ohne jeden Werkzeugaufruf.
2. **Dann das Archiv.** Geht es um eigene Rechnungen, Verträge, Notizen, Fotos,
   Anleitungen? Dann `archiv`-Skill benutzen, nicht das Internet.
3. **Erst danach Internet** (WebSearch/WebFetch) — für allgemeines Weltwissen.

## Notizen im Vault

Neue Erkenntnisse, die dauerhaft gelten, gehören als Markdown-Datei nach `Wissen/`
(Skill `notiz`), nicht in eine Chat-Antwort. Verlinkung untereinander mit
`[[Dateiname]]`, damit Obsidian den Graphen aufbauen kann.

Kurzlebiges (Zwischenstände, Ausgaben eines einzelnen Laufs) gehört **nicht**
in den Vault.

## Portabilität

- Keine absoluten Pfade (`C:\Users\...`) in Skills, Notizen oder Skripten.
- Das Python-`.venv` unter `Claude/ArchivSuche/.venv` ist an seinen Pfad gebunden
  und muss nach einem Umzug einmal neu erzeugt werden — siehe
  [Wissen/Portabilitaet.md](Wissen/Portabilitaet.md).
