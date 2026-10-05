---
id: 20260830-ordnerstruktur
title: 'Ordnerstruktur'
tags: [betrieb, struktur]
created: 2026-08-30
updated: 2026-09-07
related: [20260830-schutzregeln, 20260830-verbindungen]
summary: 'Die vier Ordner unter BrainFiles, warum sie geteilt sind und welche fünf Fallen beim Verschieben brechen.'
---

# Ordnerstruktur

Seit dem **30.08.2026** ist `BrainFiles/` in vier Ordner geteilt. Vorher lag
alles in `MaxHirn/`: Obsidian-Vault, 45 GB persönliches Archiv, 51 GB
Modellgewichte, der Maschinenraum für 14 MCP-Server, die Daten eines zweiten
Agenten und Sitzungsreste — gewachsen, nicht entworfen.

## Die vier Ordner

| Ordner | Aufgabe | Größe | Sicherung |
|---|---|---|---|
| `MaxHirn/` | Wissen und persönliches Archiv, Obsidian-Vault | 45 GB | ja |
| `Modelle/` | Modellgewichte und Laufzeiten | 51 GB | **nein** |
| `Agenten/` | MCP-Server, Hermes, Handelsagent, Routinen, Sicherungsskripte | 4 GB | ja |
| `Werkstatt/` | gemeinsamer Arbeitsplatz aller Modelle | 1 GB | **nein** |

**Die tragende Regel: In `MaxHirn/` liegt nichts, was startet.** Sie ist der
Grund, warum auch `Routinen/` und die Sicherungsskripte nach `Agenten/`
gewandert sind, obwohl sie den Vault pflegen.

**Die eine Ausnahme:** `Archiv/ArchivSuche/` — Werkzeugcode (git-versioniert)
und der neu baubare Index bleiben auf `C:` beim Vault. Nur die Archivdaten
liegen auf `O:` (siehe nächster Abschnitt); `index.py` findet sie über die
Umgebungsvariable `ARCHIV_ROOT`, mit Rückfall auf die eigene Lage. Sie herauszureißen brächte Konfigurationspfade, wo heute keine
nötig sind.

## Archivdaten liegen auf O: — konfigbasiert (echter Umzug 07.09.2026)

`C:` war auf 4,8 GB frei. Die Archivdaten `Archiv/{Bilder,Dokumente,Musik,
Videos,Software,Posteingang}` — zusammen 44 GB, 64.745 Dateien — liegen physisch
auf `O:\Archiv\`. Bis zum 06.09.2026 waren das Junctions im Vault; seit dem
07.09.2026 sind die Junctions weg und alle Werkzeuge finden die Daten über die
**Umgebungsvariable `ARCHIV_ROOT`** (`O:\Archiv`, wie `OLLAMA_MODELS` gesetzt).

Was auf `C:` beim Vault bleibt: `ArchivSuche/` (Werkzeugcode, git-versioniert),
der Volltextindex `archiv_index.db` (neu baubar) und die Steuerdateien im Archiv
(`CLAUDE.md`, `README.md`, `TASKS.md`, `BESCHAEDIGTE_*.md` …).

**Was der echte Umzug geändert hat:**
- `index.py`, `server.py`: `ROOT` aus `ARCHIV_ROOT`, Rückfall auf die eigene
  Lage. `sort_inbox.py` erbt über `index.ROOT`. Kein Reindex — `index.py`
  gegengeprüft: 9712 Einträge, 0 verändert, 0 entfernt (relative Pfade).
- `archiv_mcp.py`, `mailversand.py`: Datenwurzel (`ARCHIV` ← `ARCHIV_ROOT`) von
  der Indexwurzel (`INDEX_DIR`/`DB_PATH`, weiter auf `C:`) getrennt.
- `vektor_index.py`, `vektor_suche.py`, `search_cli.py`: unverändert (nur DB).
- `sichern.ps1` / `sichern-zweitkopie.ps1`: kein Junction-Sonderfall mehr, der
  zweite robocopy-Lauf `O:\Archiv` → `G:` bzw. Dokumente+Bilder → `J:` bleibt.

**Sicherung bleibt vollständig:** Drei-Platten-Netz unverändert — Original `O:`,
Sicherung `G:`, Zweitkopie `J:`.

## Was die Teilung bringt

Sie ist keine Kosmetik — vorher ließ sich nichts pro Bereich entscheiden:

- **51 GB weniger je Sicherungslauf.** `Modelle/` steht jetzt in der
  Ausschlussliste von `sichern.ps1`. Dass Modelle neu herunterladbar sind,
  stand schon vorher in [[Schutzregeln]] — der Sicherungslauf wusste es nur nicht.
- **Ein Git-Repository über die ganze Struktur.** Die Wurzel liegt in
  `BrainFiles/`, versioniert ist weiterhin nur die Textebene über eine
  Whitelist. Beim Hochziehen wurden 115 Dateien als Umbenennung übernommen,
  0 Löschungen — `git log --follow` reicht über den Umbau hinweg.
- **Ein Ort zum Schreiben für alle Modelle.** `Werkstatt/` mit eigenen
  Spielregeln (`Werkstatt/AGENTS.md`): hier liegt nie ein Original.

## Der Ordner „Claude“ heißt jetzt `Archiv/`

Die 45 GB Verträge, Bescheide und Fotos waren nach einem Modell benannt, obwohl
alle Modelle darauf zugreifen sollen. Genau diese Verwechslung war der Anlass
für den Umbau.

Billig war die Umbenennung nur wegen einer gemessenen Eigenschaft:
**der Suchindex speichert relative Pfade.** `files_meta.path` enthält
`Bilder\-009.JPG`, nicht den vollen Pfad; 9712 Einträge. Ein Reindex war deshalb
**nicht nötig** — wer trotzdem einen anstößt, verliert Stunden ohne Gegenwert.

## Fünf Fallen beim Verschieben

Alle fünf sind gemessen worden, nicht vermutet. Jede bricht **still** — das ist
das Gefährliche daran.

1. **Server, die ihren Ort ausrechnen.** `archiv_mcp.py` bestimmte den Vault mit
   `Path(__file__).resolve().parents[2]`. Nach dem Umzug ergab das `Agenten/`
   statt `MaxHirn/`. Jetzt über die Variable `MAXHIRN_VAULT` mit Rückfall auf
   `parents[3] / "MaxHirn"`.
2. **Zwei Konfigurationen, dieselben ~30 Pfade.**
   `%APPDATA%\Claude\claude_desktop_config.json` und `Agenten/Hermes/config.yaml`
   müssen **gemeinsam** geändert werden, sonst laufen Claude und Hermes
   auseinander. Siehe [[Verbindungen]].
3. **`.venv` überlebt den Umzug nur halb.** Editable installs (`.pth`-Dateien,
   `__editable___*_finder.py`) und die `.exe`-Startprogramme unter
   `Scripts\` tragen absolute Pfade **im Inneren**. Geprüft: in
   `windows-mcp.exe` und `blender-mcp.exe` steht der Pfad zu `python.exe` im
   Binärcode. Beide laufen jetzt über `python.exe -c "from … import main; main()"`,
   damit nichts neu gebaut werden muss. Server, die über
   `python.exe` + Skriptpfad gestartet werden, überstehen den Umzug unbeschädigt.
4. **Laufende Prozesse blockieren.** Windows benennt keinen Ordner um, unter dem
   eine laufende `.exe` liegt. Gemessen am 30.08.2026: 21 Prozesse aus
   `MaxHirn\MCP-Server` (von Claude Desktop gestartet) und 2 aus
   `Modelle\Ollama`. **Eine Claude-Sitzung kann sich nicht selbst umziehen** —
   dafür gibt es `Agenten/Routinen/umzug/UMZUG-OFFLINE.ps1`.
5. **Geplante Aufgaben melden Erfolg, auch wenn sie ins Leere laufen.** Sechs
   Aufgaben zeigten auf `MaxHirn\Routinen` bzw. `MaxHirn\Handel`. Prüfbefehl:
   `Get-ScheduledTask | ? { $_.Actions.Execute -match 'MaxHirn' }`.

## Was nicht mitgewandert ist, und warum

- **Berechtigungsvermerke.** In `claude_desktop_config.json` stehen neben den
  Einstellungen auch `remoteSessionFolderGrants` und
  `epitaxy-perm-mode-acks` früherer Sitzungen. Sie wurden **nicht**
  umgeschrieben. Ein Vermerk auf einen Pfad, den es nicht mehr gibt, gewährt
  nichts — mitgezogen wäre er eine Freigabe auf den neuen Ort, die niemand
  erteilt hat.
- **Die Ablagen im Benutzerordner.** Entscheidung vom 30.08.2026: `~/.claude`,
  `~/.codex` und `%APPDATA%\Claude` bleiben, wo die Programme sie suchen. Was
  dort liegt und was es kostet, steht in [[KI-Ablagen-im-Benutzerordner]].
- **`C:\Hermes`** (Programmcode, 121.112 Dateien, eigener Git-Klon). Aus Git
  reproduzierbar und über `HERMES_HOME` sauber von seinen Daten getrennt.

## Umgebungsvariablen, die zur Struktur gehören

| Variable | Wert | Falle |
|---|---|---|
| `OLLAMA_MODELS` | `Modelle\Ollama\Store` | Ollama erwartet den Ordner, der `blobs` **und** `manifests` nebeneinander enthält. Zeigte bis 30.08.2026 auf `Modelle\Ollama\models` mit einem einzigen Blob, während der echte Store mit 16,9 GB danebenlag. |
| `HERMES_HOME` | `Agenten\Hermes` | trennt die Daten des Agenten vom Programmcode unter `C:\Hermes` |
| `MAXHIRN_VAULT` | optional | überschreibt die Vault-Erkennung von `archiv_mcp.py` / `mailversand.py` (Werkzeug + Index) |
| `ARCHIV_ROOT` | `O:\Archiv` | wo die Archivdaten liegen. Unset → Rückfall auf `…\MaxHirn\Archiv` (nur sinnvoll, wenn die Daten dort wieder danebenliegen). Von `index.py`, `server.py`, `sort_inbox.py`, `archiv_mcp.py`, `mailversand.py` gelesen. Nach dem Setzen sehen laufende Prozesse (Claude Desktop, Hermes) sie erst nach Neustart. |

## Wie der Umbau gemacht wurde

Skriptgetrieben, in `Agenten/Routinen/umzug/`: `00-bestand`, `10-git-wurzel`,
`20-modelle`, `30-agenten`, `40-werkstatt`, `50-archiv`, `70-benutzerordner`,
`80-sicherung`, `90-pruefen`. Alle mit Trockenlauf als Voreinstellung,
idempotent, mit einer Bilanzzeile am Ende. `pfade.psd1` hält die Tabelle
alt→neu.

Der Grund für Skripte statt Einzelbearbeitung war nicht Eleganz, sondern Kosten:
90 Textstellen in 22 Dateien einzeln zu lesen und zu ändern hätte ein
Vielfaches an Tokens gekostet, ohne dass dabei Nachdenken nötig gewesen wäre.
Das Verfahren steht im Skill `umzug`.

## Laufwerksregel (seit 05.10.2026)

- **C:** System, Programme, Repo-Textebene.
- **O:** Daten: `Modelle`, `Werkstatt`, `Archiv`, `Wiki` (Junction), `MaxHirn-Zweitkopie`
  (Sicherungsziel), dazu die alten Bestände `Documents` und `iTunes` (bleiben bewusst).
- **G:/J:** Sicherung. **Q:/H:** Musik.
- In `O:\` entsteht direkt nichts Neues außer diesen Ordnern. Systemgebundenes
  (`WindowsApps`, `WpSystem`, `XBOX Games`, `MapData`, `Program Files`) nicht anfassen.
- Leere Reste `iCloudDrive` und `Mary Ann` wurden am 05.10.2026 entfernt. `O:\faupe`
  (nur `Documents\desktop.ini`) ist für Werkzeuge als Systempfad gesperrt und muss von
  Hand im Explorer gelöscht werden.

Verwandt: [[Schutzregeln]], [[Portabilitaet]], [[Verbindungen]],
[[KI-Ablagen-im-Benutzerordner]], [[Hermes]]
