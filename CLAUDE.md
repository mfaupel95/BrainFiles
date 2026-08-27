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
| `Codex/` | **keine Sitzungsablage** — die fünf Datumsordner sind leer. Die 71 MB sind vier CSV-Protokolle einer Dublettenlöschung `Mary Ann` (O: gegen G:, 06.08.2026) | 71 MB |
| `Coworking-Space/` | Ablagen einzelner Sitzungen, kein Bestandteil des Betriebs | 336 MB |

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

**Das geschieht ungefragt, nicht als Angebot.** Wenn am Ende einer Aufgabe ein
Ergebnis steht, das in einem Monat noch gilt — eine Messung, eine Entscheidung
mit Begründung, eine Falle, die Zeit gekostet hat —, wird es abgelegt und die
Ablage in einem Satz gemeldet. Nicht „ich könnte das als Notiz ablegen“.
Gefragt wird nur im Zweifelsfall, ob etwas überhaupt dauerhaft gilt.
Ausgewertete Zahlen brauchen dabei das Skript, mit dem sie entstanden sind —
sonst ist die Notiz beim nächsten Mal nicht nachrechenbar (Beispiel:
[[Handelsbots]] und `Handel/dca_auswertung.py`).

Kurzlebiges (Zwischenstände, Ausgaben eines einzelnen Laufs) gehört **nicht**
in den Vault.

## Mehrere Sitzungen gleichzeitig

Max hat mehrere Chats offen, dazu Hermes — alle schreiben in denselben Vault.
**Git schützt nur, was committet ist**, alles davor kann eine andere Sitzung
vernichten. Deshalb:

- **Verwerfen ist verboten, Sichern ist Pflicht.** Fremdes im Arbeitsbaum nicht
  liegen lassen, sondern in einem **eigenen, getrennten Commit** sichern, mit
  `git commit --author="Andere Sitzung <fremd@local>"` — nie vermischt mit
  eigener Arbeit. Den echten Namen nur eintragen, wenn der Urheber wirklich
  feststeht (etwa `"Hermes <hermes@local>"`); **nicht raten**, das macht die
  Historie genauso falsch wie die Ich-Form. `git add <pfad>` namentlich, nie
  `git add -A`, `git add .` oder `git commit -a`. Liegen lassen, was in den
  letzten **10 Minuten** geschrieben wurde (`(Get-Item <pfad>).LastWriteTime`)
  — älter gilt als ruhend.
- **Nie verwerfen:** `git reset --hard`, `checkout -- <datei>`, `restore`,
  `stash`, `clean` löschen die uncommittete Arbeit anderer Sitzungen
  unwiederbringlich. Nur auf ausdrückliche Anweisung, vorher ansagen.
- **Eigenes zügig committen**, nach jedem Arbeitsschritt.
- **`index.py`, `sort_inbox.py`, `sichern.ps1`, `zweitkopie.ps1` nie doppelt
  starten.**

Vollständig: [Wissen/Schutzregeln.md](Wissen/Schutzregeln.md)

## Portabilität

- Keine absoluten Pfade (`C:\Users\...`) in Skills, Notizen oder Skripten.
- Das Python-`.venv` unter `Claude/ArchivSuche/.venv` ist an seinen Pfad gebunden
  und muss nach einem Umzug einmal neu erzeugt werden — siehe
  [Wissen/Portabilitaet.md](Wissen/Portabilitaet.md).
