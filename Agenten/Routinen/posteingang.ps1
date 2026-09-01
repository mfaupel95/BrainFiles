# Geplantes Einsortieren des Posteingangs. Von der Aufgabenplanung aufgerufen.
#
# Das Skript sortiert nur, was es sicher zuordnen kann; alles andere bleibt
# liegen. Es ersetzt damit nicht das gezielte Einsortieren von Hand - der Lauf
# vom 23.08.2026 hat 9 von 303 Dateien zugeordnet und 67 liegen gelassen.
# Deshalb ist das Protokoll hier wichtiger als bei der Sicherung: Es zeigt,
# wie viel liegen bleibt.

$ErrorActionPreference = 'Stop'
# Zwei Ebenen ueber diesem Skript liegt die Wurzel BrainFiles\ (Agenten\Routinen\
# -> Agenten\ -> BrainFiles\). Das Archiv-Werkzeug liegt seit der Ordnertrennung
# vom 30.08.2026 unter MaxHirn\Archiv\ArchivSuche\ (hiess vorher Claude\).
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$suche  = Join-Path $wurzel 'MaxHirn\Archiv\ArchivSuche'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$log = Join-Path $logs 'posteingang-letzter-lauf.log'
$start = Get-Date

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
try {
  Push-Location $suche
  & (Join-Path $suche '.venv\Scripts\python.exe') (Join-Path $suche 'sort_inbox.py') *>&1 |
    Add-Content $log -Encoding UTF8
  Pop-Location
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  exit 1
}
