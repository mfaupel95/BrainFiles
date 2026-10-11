# Herzschlag-Wache: meldet stille Spuren (Handel\herzschlag_wache.py).
# Von der Aufgabe MaxHirn-Herzschlag-Wache alle 10 Minuten aufgerufen
# (einrichten: herzschlag-wache-aufgabe.ps1).
#
# Rein lesend bis auf die Merkdatei Handel\cache\herzschlag-wache.json: das
# Skript meldet nur den WECHSEL (Spur still / wieder lebendig) ueber den Bus.
# Es stellt keine Order und aendert keine Spur. Exitcode 1 des Skripts heisst
# "mindestens eine Spur still" und ist KEIN Fehler dieses Wrappers - deshalb
# meldet er hier weder Start noch Ende an den Bus (alle 10 Minuten waere das
# Rauschen), sondern schreibt nur das Log.

$ErrorActionPreference = 'Continue'
$wurzel = Split-Path $PSScriptRoot -Parent                 # Agenten
$handel = Join-Path $wurzel 'Handel'
$py     = Join-Path $handel 'scanner\.venv\Scripts\python.exe'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'herzschlag-wache-letzter-lauf.log'

"=== Lauf $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

if (-not (Test-Path $py)) {
  "ENDE FEHLER: kein Python unter $py" | Add-Content $log -Encoding UTF8
  exit 1
}

# Aus einer Sitzung, die durch den MCP-Supervisor laeuft, startet Python nur
# ohne PYTHONHOME/PYTHONPATH (siehe CLAUDE.md, Abschnitt Fallen).
Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue

Push-Location $handel
& $py 'herzschlag_wache.py' *>&1 | Add-Content $log -Encoding UTF8
$code = $LASTEXITCODE
Pop-Location
"ENDE Exitcode $code (1 = mindestens eine Spur still)" | Add-Content $log -Encoding UTF8
exit 0
