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
