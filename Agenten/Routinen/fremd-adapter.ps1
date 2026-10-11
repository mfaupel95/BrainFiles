# Ein Lauf ueber alle Fremd-Adapter (adapter_lauf.py): neue Signale von nautilus/moon-dev/itb an den Bus.
# Das Tor (Handel\fremd_signale\wachen.json) entscheidet; der Lauf handelt nie. Kein --live.
# Aufgerufen von fremd-adapter-aufgabe.ps1 (NICHT registriert).
$ErrorActionPreference = 'Continue'
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$py     = Join-Path $wurzel 'Agenten\Handel\scanner\.venv\Scripts\python.exe'
$skript = Join-Path $wurzel 'Agenten\Bus\adapter_lauf.py'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'fremd-adapter-letzter-lauf.log'
"=== Lauf $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
if (-not ((Test-Path $py) -and (Test-Path $skript))) {
  "ENDE FEHLER: Python oder adapter_lauf.py fehlt" | Add-Content $log -Encoding UTF8
  exit 1
}
& $py $skript *>&1 | Add-Content $log -Encoding UTF8
$code = $LASTEXITCODE
"ENDE Code $code" | Add-Content $log -Encoding UTF8
exit $code
