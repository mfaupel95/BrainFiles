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

## Verifikation nach der Reparatur

- Der Pruefer belegt nur, dass das **Serverprogramm existiert** — nicht, dass ein Agent
  es starten kann. Nach jeder Reparatur den echten Start belegen:
  `hermes -p <profil> mcp test <name>` (rc 0 + Werkzeugliste).
- Claude-Seite: der Eintrag muss das Schreiben **ueberleben**. Nach dem Schreiben die
  mtime der Claude-Config gegen die eigene Schreibzeit halten — bleibt sie stehen, hat
  die App nicht aus ihrem Speicher zurueckgeschrieben. Endgueltig belegt es erst ein
  Neustart der App (der Server steht dann unter den Connectors).
- Eintrag byte-genau einsetzen: Anker auf das Blockende (`    }` + `  },` + naechster
  Top-Level-Schluessel), das Komma am Vorgaenger nicht vergessen, in eine Temp-Datei
  schreiben, `json.load` validieren, dann `os.replace`; Diff gegen die Sicherung zeigen.
  Nur `command`/`args` noetig — die uebrigen Eintraege der Datei fuehren kein `cwd`.

## Fallstricke (belegt 10./11.09.2026)
- ZWEI Claude-Config-Pfade: der Pruefer liest seit 14.10.2026 den MSIX-Container ZUERST und faellt nur auf den klassischen Pfad `%APPDATA%\Claude\claude_desktop_config.json` durch; liegt eine zweite Datei daneben, warnt er. Vorher war die Reihenfolge umgekehrt: eine verwaiste klassische Datei blendete den Pruefer aus und erzeugte falsche "fehlt bei Claude"-Fehler fuer alle Server, die nur im Container stehen (14.10.2026: 7 falsche Fehler, echte Container-Config hatte alle). Bei unerwarteten Claude-Fehlern also immer pruefen, WELCHE Datei der Pruefer laut seiner Ausgabe liest, und die mtimes beider Dateien vergleichen; die aktive ist die im Container (wird bei App-Nutzung staendig neu geschrieben).
- `hermes mcp add` ist discovery-first und fragt interaktiv `Enable all N tools? [Y/n/select]:`. In einer nicht-interaktiven Shell bricht das mit "Cancelled" ab, obwohl der Server erreichbar ist — `echo y | hermes -p <profil> mcp add ...` voranstellen. `--args` muss die letzte Option sein.
- Profil-Ziel: `hermes -p default` schreibt in die WURZEL-Config `Agenten\Hermes\config.yaml` (Profil `default` = Agenten\Hermes). Ohne `-p` schreibt der Befehl in das eigene Profil. Der Pruefer bewertet nur die Wurzel-Config.
- Manifest-Stempel: der Pruefer vergleicht die mtime der Configs mit der mtime des Manifests. Nach jeder verifizierten Reparatur das Manifest ZULETZT anfassen (`touch`), sonst warnt er dauerhaft "Konfiguration neuer als Manifest".
- cwd ist bei `hermes mcp add` nicht setzbar (kein `--cwd`). Fuer Server, die ihr Arbeitsverzeichnis aus einer eigenen Variablen oder `~` ziehen (z. B. ziplime: `ZIPLIME_MCP_HOME` bzw. `~/.ziplime/mcp`), ist das ohne Wirkung — vorher in der Serverquelle pruefen.
- BEIDE Apps (Claude Desktop UND Hermes) ueberschreiben ihre Konfiguration aus eigenem Speicher. Server-Eintraege koennen still verschwinden (mcp-memory geschah so in beiden Configs). Deshalb regelmaessig pruefen; Config-Zeitstempel > Manifest-Zeitstempel = Alarm.
- Claude-Config nur bei geschlossener App aendern, sonst ueberschreibt die laufende App sie aus ihrem Speicher.
- Hermes config.yaml nicht manuell editieren — Hermes-Kommandos/Framework-Konventionen nutzen.
- Reparatur an Stufe-1-Dateien (Agenten/*.ps1): erst `.bak-JJJJMMTT` kopieren, dann aendern, dann echten Lauf zeigen.
- Windows PowerShell 5.1 parst UTF-8 ohne BOM falsch (Parserfehler bei Umlauten/Sonderzeichen). Nach dem Schreiben BOM setzen: `[IO.File]::WriteAllText($p, [IO.File]::ReadAllText($p), (New-Object Text.UTF8Encoding($true)))`
- Serververzeichnisse: `Agenten\MCP-Server\<name>`; Python-Server laufen mit `.venv\Scripts\python.exe <name>_mcp.py` — das Skript liegt in der Wurzel des Serverordners, NICHT in `.venv\Scripts` (dort liegt nur `mcp.exe`).
- Hermes-Sandbox-Terminal (Docker) kann bei `proxy.enabled` + fehlendem iron-proxy tot sein: dann alles ueber windows-mcp (`mcp__windows_mcp__PowerShell`/`FileSystem`) auf dem Host machen.
