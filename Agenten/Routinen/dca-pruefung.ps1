# Geplante DCA-Faelligkeitspruefung. Von der Aufgabenplanung aufgerufen.
#
# WICHTIG: Diese Routine loest nichts aus. `agent.py check` meldet nur, ob eine
# Rate faellig ist. Quote holen, vorlegen und ausfuehren bleibt ein bewusster
# Schritt von Hand - aus einem Zeitplan heraus wird nie gehandelt.
#
# `check` schweigt, wenn nichts ansteht. Das Protokoll enthaelt dann nur die
# Kopfzeile; eine Routine, die taeglich "nichts zu tun" meldet, wird ignoriert.

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$handel = Join-Path $wurzel 'Handel'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$log = Join-Path $logs 'dca-letzter-lauf.log'
$start = Get-Date

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
try {
  Push-Location $handel
  & (Join-Path $handel '.venv\Scripts\python.exe') (Join-Path $handel 'agent.py') check *>&1 |
    Add-Content $log -Encoding UTF8
  Pop-Location
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  exit 1
}
