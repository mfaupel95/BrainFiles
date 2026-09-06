---
id: 20260830-ordnerstruktur
title: 'Ordnerstruktur'
tags: [betrieb, struktur]
created: 2026-08-30
updated: 2026-09-06
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

**Die eine Ausnahme:** `Archiv/ArchivSuche/` bleibt im Archiv. `index.py`
leitet die zu indexierende Wurzel aus der eigenen Lage ab
(`Path(__file__).parent.parent`), und die Datenbank gehört neben die Daten, die
sie beschreibt. Sie herauszureißen brächte Konfigurationspfade, wo heute keine
nötig sind.

## Archiv-Unterordner liegen physisch auf O: (seit 06.09.2026)

`C:` war auf 23,5 GB frei. Deshalb sind `Archiv/{Bilder,Dokumente,Musik,Videos,
Software,Posteingang}` — zusammen 44 GB — nach `O:\Archiv\` kopiert; an alter
Stelle steht je eine **Junction**, genau wie `Modelle/` → `O:\Modelle`. Der Vault
sieht die Pfade unverändert, `index.py` (relative Pfade, 9712 Einträge
unverändert) und der `archiv`-MCP laufen ohne Anpassung weiter. `ArchivSuche/`
und die Steuerdateien im Archiv bleiben real auf `C:`.

**Warum Junction und nicht echter Umzug:** die Junction ist in Minuten gesetzt
und reversibel. Der saubere Weg — Archiv ganz aus dem Vault, `MAXHIRN_VAULT` +
Wurzelerkennung + Sicherungsskripte + `archiv_mcp.py` konfigbasiert — ist als
eigener Auftrag offen (Skill `umzug`).

**Sicherung bleibt vollständig:** `sichern.ps1` (`/XJ` überspringt Junctions)
zieht `O:\Archiv` in einem zweiten Lauf nach `G:`, `sichern-zweitkopie.ps1`
Dokumente + Bilder nach `J:`. Drei-Platten-Netz unverändert: Original `O:`,
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
| `MAXHIRN_VAULT` | optional | überschreibt die Vault-Erkennung von `archiv_mcp.py` |

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

Verwandt: [[Schutzregeln]], [[Portabilitaet]], [[Verbindungen]],
[[KI-Ablagen-im-Benutzerordner]], [[Hermes]]
