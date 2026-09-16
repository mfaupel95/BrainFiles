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

## Fallstricke (belegt 10./11.09.2026)
- BEIDE Apps (Claude Desktop UND Hermes) ueberschreiben ihre Konfiguration aus eigenem Speicher. Server-Eintraege koennen still verschwinden (mcp-memory geschah so in beiden Configs). Deshalb regelmaessig pruefen; Config-Zeitstempel > Manifest-Zeitstempel = Alarm.
- Claude-Config nur bei geschlossener App aendern, sonst ueberschreibt die laufende App sie aus ihrem Speicher.
- Hermes config.yaml nicht manuell editieren — Hermes-Kommandos/Framework-Konventionen nutzen.
- Reparatur an Stufe-1-Dateien (Agenten/*.ps1): erst `.bak-JJJJMMTT` kopieren, dann aendern, dann echten Lauf zeigen.
- Windows PowerShell 5.1 parst UTF-8 ohne BOM falsch (Parserfehler bei Umlauten/Sonderzeichen). Nach dem Schreiben BOM setzen: `[IO.File]::WriteAllText($p, [IO.File]::ReadAllText($p), (New-Object Text.UTF8Encoding($true)))`
- Serververzeichnisse: `Agenten\MCP-Server\<name>`; Python-Server laufen mit `.venv\Scripts\python.exe <name>_mcp.py` — das Skript liegt in der Wurzel des Serverordners, NICHT in `.venv\Scripts` (dort liegt nur `mcp.exe`).
- Hermes-Sandbox-Terminal (Docker) kann bei `proxy.enabled` + fehlendem iron-proxy tot sein: dann alles ueber windows-mcp (`mcp__windows_mcp__PowerShell`/`FileSystem`) auf dem Host machen.
- Warnung 'Server in Agenten-Config, aber NICHT im Manifest' wird NICHT durch einen Eintrag unter `disabled` gestillt - der Pruefer meldet den Namen dann zusaetzlich als 'im Manifest deaktiviert, laeuft aber bei einem Agenten'. Sauberer Weg fuer Kandidaten (belegt mit robinhood am 16.09.2026): Server per `hermes mcp remove <name>` aus der Config entfernen (bereinigt auch OAuth-Tokens) und den Kandidaten mit Grund in `disabled` dokumentieren (Santiment-Muster). Die Zeitstempel-Warnung 'Konfiguration neuer als Manifest' verschwindet von selbst, wenn das Manifest nach den Configs geschrieben wurde.
- ToolUniverse schreibt bei jedem Start ohne API-Schluessel eine eigene `.env.template` in sein ARBEITSVERZEICHNIS (`generate_env_template` in `execute_function.py`, relativer Pfad, nicht abschaltbar). Fehlt `cwd` im Serverblock, ist das die Sitzungswurzel — so landeten Kopien in der Repo-Wurzel, in MaxHirn/, MaxHirn/Archiv/, Agenten/Hermes/ und Agenten/Bus/ (drei davon sogar committet). Deshalb: `cwd` fuer JEDEN stdio-Server setzen, auch wenn das Manifest es schon nennt. Hermes liest den Schluessel beim Start (`tools/mcp_tool_transport.py`, `StdioServerParameters(..., cwd=config.get("cwd"))`), Claude Desktop kennt ihn nicht. Nachweis: Serverdatei loeschen, `hermes mcp test <name>` aus einem FREMDEN Ordner starten, danach pruefen, wo die Datei auftaucht.
- Eine `.env.template` ist nie ein Dokument, sondern ein Nebenprodukt — eine Freigabe `!**/*.env.template` in .gitignore nimmt nur Servermuell in den Verlauf auf (am 16.09.2026 zurueckgenommen). Grundsatzregel `*` deckt sie ab.
- `hermes config set` schreibt die GANZE config.yaml neu und wirft dabei den auskommentierten Vorlagenblock am Dateiende weg (~39 Zeilen Kommentar, kein Wertverlust), ebenso kann eine parallel laufende Sitzung gleichzeitig andere Werte darin aendern. Vor jedem `config set`: `.bak-JJJJMMTT` kopieren, danach `git diff` lesen und fremde Hunks mit `git add -p` uncommittet liegen lassen.
