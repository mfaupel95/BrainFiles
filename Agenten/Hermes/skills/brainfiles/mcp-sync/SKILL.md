---
name: mcp-sync
category: brainfiles
description: Use when Claude/Hermes MCP drift. Checks MCP-Manifest.
---

# MCP-Sync (Claude Desktop <-> Hermes)

## Wahrheit
`Agenten\MCP-Manifest.json` (Wurzel: BrainFiles) ist die einzige Wahrheit fuer die MCP-Server. Feld `agent`: `beide` (Standard), `hermes` oder `claude`, wenn nur ein Agent den Server traegt.

## Dateien
- Manifest: `Agenten\MCP-Manifest.json` (ist GITIGNORED — Sicherung `.bak-JJJJMMTT` ist der einzige Rueckweg)
- Pruefer: `Agenten\mcp-sync-check.ps1` (muss UTF-8 MIT BOM sein, sonst Parserfehler unter Windows PowerShell 5.1; Text ASCII-sicher halten)
- Claude-Config: MSIX-Container `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude_desktop_config.json` (NICHT `%APPDATA%\Claude`)
- Hermes-Config: `Agenten\Hermes\config.yaml`, Block `mcp_servers:`, Serverschluessel mit exakt 2 Leerzeichen Einzug und ohne Wert
- Eingebunden in `Agenten\Routinen\systempruefung.ps1` (Abschnitt 0), Aufgabe `MaxHirn-Systempruefung`

## Lauf
```
powershell -ExecutionPolicy Bypass -File Agenten\mcp-sync-check.ps1
```
Exit 0 = in Sync, 1 = Fehler. Fehler: Server im Manifest aktiv, aber bei einem Agenten fehlend; Programm/Verzeichnis fehlt. Warnung: Konfiguration neuer als Manifest (= stille App-Ueberschreibung), Server in Agenten-Config aber nicht im Manifest.

## Was der Pruefer NICHT sieht (Exit 0 ist kein Beweis fuer Gleichheit)
- **Er vergleicht nur NAMEN, keine Argumente.** `args`, `cwd` und `env` koennen in Manifest, Hermes-Config und Claude-Config auseinanderlaufen, und der Pruefer meldet trotzdem ALLES IN ORDNUNG. Belegter Fall: derselbe Pfad wurde an zwei Orten korrigiert, die Claude-Config behielt den alten, inzwischen GELOESCHTEN Ordner - weder Fehler noch Warnung. Nach jeder Pfadkorrektur alle drei Orte angleichen und die `args` gegeneinander lesen (per Skript ueber beide Dateien, nicht mit dem Auge).
- **Eintraege mit `enabled: false` verschwinden aus BEIDEN Namenslisten.** `HoleHermesNamen` streicht sie, und der Abgleich gegen das Manifest laeuft nur ueber diese gefilterte Liste. Ein Server, der in der Hermes-Config steht und im Manifest GANZ fehlt, taucht deshalb nie als Warnung auf - auch nicht als 'im Manifest deaktiviert, laeuft aber'. Vor dem Urteil 'in Sync' die ROHLISTE des `mcp_servers:`-Blocks (Schluessel mit 2 Leerzeichen Einzug) gegen das Manifest halten.
- Geprueft wird nur, was als `cwd`-relativ erkennbar ist; absolute `command`-Pfade (z.B. eine `.exe` unter `O:\...`) werden nicht auf Existenz geprueft. Bei 'ALLES IN ORDNUNG' und trotzdem totem Server: den Pfad selbst testen.

## Drift aufloesen: 'beide' gegen die Wirklichkeit
Sagt das Manifest `agent: beide` und der Server fehlt bei einem Agenten, gibt es ZWEI richtige Ausgaenge - die Wahl muss belegt werden, nicht geraten:
1. **Eintragen** (Manifest gilt): nur bei GESCHLOSSENER Claude-Desktop-App. Laeuft sie, ist jede Aenderung an `claude_desktop_config.json` beim naechsten Schreibvorgang der App weg. Ob sie laeuft: `tasklist | grep -i claude.exe` (bash) bzw. `Get-Process Claude` (PowerShell); die MSIX-App startet viele Prozesse, einer genuegt als Beweis.
2. **Manifest auf die Realitaet ziehen**: war der Server nie im anderen Agenten (Claude-Config UND `~/.claude.json` lesen - Claude Code fuehrt seine Server dort getrennt) und gehoert er zur Arbeit des tragenden Agenten, `agent` auf `hermes` oder `claude` setzen. Dabei PFLICHT: Grund DATIERT in die `description` schreiben und den Rueckweg mitnennen (Feld zurueck auf `beide`, Eintrag bei geschlossener App nachtragen) - sonst liest die naechste Sitzung die Umstellung als Versehen.
Ein Server, den ein Katalog/`hermes mcp add` eingetragen hat, ist damit noch nicht Teil der Wahrheit: erst Manifest, dann Config - oder Config-Eintrag wieder entfernen.

## Fallstricke (belegt 10./11.09.2026)
- BEIDE Apps (Claude Desktop UND Hermes) ueberschreiben ihre Konfiguration aus eigenem Speicher. Server-Eintraege koennen still verschwinden (mcp-memory geschah so in beiden Configs). Deshalb regelmaessig pruefen; Config-Zeitstempel > Manifest-Zeitstempel = Alarm.
- Claude-Config nur bei geschlossener App aendern, sonst ueberschreibt die laufende App sie aus ihrem Speicher.
- Hermes config.yaml nicht manuell editieren — Hermes-Kommandos/Framework-Konventionen nutzen.
- Reparatur an Stufe-1-Dateien (Agenten/*.ps1): erst `.bak-JJJJMMTT` kopieren, dann aendern, dann echten Lauf zeigen.
- Windows PowerShell 5.1 parst UTF-8 ohne BOM falsch (Parserfehler bei Umlauten/Sonderzeichen). Nach dem Schreiben BOM setzen: `[IO.File]::WriteAllText($p, [IO.File]::ReadAllText($p), (New-Object Text.UTF8Encoding($true)))`
- Serververzeichnisse: `Agenten\MCP-Server\<name>`; Python-Server laufen mit `.venv\Scripts\python.exe <name>_mcp.py` — das Skript liegt in der Wurzel des Serverordners, NICHT in `.venv\Scripts` (dort liegt nur `mcp.exe`).
- Hermes-Sandbox-Terminal (Docker) kann bei `proxy.enabled` + fehlendem iron-proxy tot sein: dann alles ueber windows-mcp (`mcp__windows_mcp__PowerShell`/`FileSystem`) auf dem Host machen.
- **Manifest-Aenderung**: Datei ist gitignored, also vorher `Agenten\MCP-Manifest.json.bak-JJJJMMTT` daneben legen. Danach das Feld `updated` auf das heutige Datum setzen - das Manifest ist dann juenger als beide Configs und die Zeitstempel-Warnungen verstummen von selbst (sie sagen nur 'Config neuer als Manifest', nicht 'Config falsch').
- **Manifest byte-sauber editieren**: die Datei ist LF mit 2 Leerzeichen Einzug; per Zeilenindex ersetzen und `json.loads` VOR dem Schreiben pruefen, statt sie ueber `json.dump` neu zu formatieren (sonst Ganzdatei-Diff). Gegenprobe: `git diff --numstat` zeigt 2 rein / 2 raus.
- Warnung 'Server in Agenten-Config, aber NICHT im Manifest' wird NICHT durch einen Eintrag unter `disabled` gestillt - der Pruefer meldet den Namen dann zusaetzlich als 'im Manifest deaktiviert, laeuft aber bei einem Agenten'. Sauberer Weg fuer Kandidaten (belegt mit robinhood am 16.09.2026): Server per `hermes mcp remove <name>` aus der Config entfernen (bereinigt auch OAuth-Tokens) und den Kandidaten mit Grund in `disabled` dokumentieren (Santiment-Muster). Die Zeitstempel-Warnung 'Konfiguration neuer als Manifest' verschwindet von selbst, wenn das Manifest nach den Configs geschrieben wurde.
- ToolUniverse schreibt bei jedem Start ohne API-Schluessel eine eigene `.env.template` in sein ARBEITSVERZEICHNIS (`generate_env_template` in `execute_function.py`, relativer Pfad, nicht abschaltbar). Fehlt `cwd` im Serverblock, ist das die Sitzungswurzel — so landeten Kopien in der Repo-Wurzel, in MaxHirn/, MaxHirn/Archiv/, Agenten/Hermes/ und Agenten/Bus/ (drei davon sogar committet). Deshalb: `cwd` fuer JEDEN stdio-Server setzen, auch wenn das Manifest es schon nennt. Hermes liest den Schluessel beim Start (`tools/mcp_tool_transport.py`, `StdioServerParameters(..., cwd=config.get("cwd"))`), Claude Desktop kennt ihn nicht. Nachweis: Serverdatei loeschen, `hermes mcp test <name>` aus einem FREMDEN Ordner starten, danach pruefen, wo die Datei auftaucht.
- Eine `.env.template` ist nie ein Dokument, sondern ein Nebenprodukt — eine Freigabe `!**/*.env.template` in .gitignore nimmt nur Servermuell in den Verlauf auf (am 16.09.2026 zurueckgenommen). Grundsatzregel `*` deckt sie ab.
- `hermes config set` schreibt die GANZE config.yaml neu und wirft dabei den auskommentierten Vorlagenblock am Dateiende weg (~39 Zeilen Kommentar, kein Wertverlust), ebenso kann eine parallel laufende Sitzung gleichzeitig andere Werte darin aendern. Vor jedem `config set`: `.bak-JJJJMMTT` kopieren, danach `git diff` lesen und fremde Hunks mit `git add -p` uncommittet liegen lassen.
- **Der Pruefer vergleicht nur NAMEN, keine Argumente** (belegt 21.10.2026): pdf-vault stand in beiden Agenten, uebergab bei Claude aber `MaxHirn\Claude` - den Ordner gibt es seit dem Umzug nicht mehr -, waehrend Manifest und Hermes `MaxHirn\Referenz\Claude_prompts` nutzten. Ergebnis: Exit 0, obwohl der Server bei Claude ins Leere zeigte. Vor jedem 'in Sync' zusaetzlich command/args/env je Server vergleichen; relative Manifest-Argumente dabei gegen `cwd` aufloesen, sonst meldet der Vergleich jeden relativen Eintrag als abweichend (falscher Alarm).
- **Eine editable-Installation bricht beim Ordner-Umzug STILL** (belegt 21.10.2026): `Werkstatt/ziplime/.venv/.../ziplime.pth` zeigte auf `O:\Werkstatt\Repos\ziplime`, das es seit dem 14.10.2026 nicht mehr gibt. Der Server startete nur, solange sein eigener Ordner zufaellig das Arbeitsverzeichnis war; aus einem fremden Ordner: `No module named 'ziplime'` - und `cwd` in der Wachen half nur deshalb. Bei einem Python-Server, der nicht hochkommt, also zuerst `*.pth` und `__editable__*.pth` im venv gegen die Wirklichkeit pruefen (`pip show <paket>` nennt die 'Editable project location'); Reparatur ist der Pfad in der .pth (Sicherung daneben), Beleg `import <paket>` aus einem fremden Ordner.
- **Einen Server-Start ohne Client pruefen**: stdio-Handshake mit genau command+args aus der Config - `initialize`, `notifications/initialized`, `tools/list` - und im Kind `PYTHONPATH`/`PYTHONHOME` entfernen, sonst zieht es die Pakete des Aufrufer-venv und scheitert an fremdem pydantic (sieht wie ein Serverfehler aus, ist Umgebungsvererbung). So belegt man die Werkzeugzahl ohne Claude oder Hermes zu starten (pdf-vault 9, ziplime 14 am 21.10.2026).
- **Claude Desktop beenden und neu starten**: `CloseMainWindow()` wirkt nicht (alle Prozesse melden `MainWindowHandle 0`). `Stop-Process -Force` auf die Prozesse mit `Path -like '*WindowsApps*'` beendet nur die App - die vielen `claude.exe` aus `~/.local/bin` sind die Claude-Code-CLI und muessen bleiben. Start per `Start-Process 'shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude'`. Danach die mtime der Config pruefen: steht sie noch auf dem eigenen Schreibzeitpunkt, hat die App nichts aus ihrem Speicher zurueckgeschrieben.
