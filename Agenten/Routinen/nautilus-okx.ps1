# Nautilus-Signalgeber (Ensemble-Donchian, 4H-Kerzen BTC-USDC, Vola-skaliert; Auswertung 13.10.2026 Variante H2) mit echten OKX-Kerzen (nautilus_okx_lauf.py): schreibt neue EMA-Kreuzungen nach
# Werkstatt\nautilus_intents.jsonl; adapter_lauf.py meldet sie an den Bus. Handelt nie. Kein --live.
# Aufgerufen von nautilus-okx-aufgabe.ps1 (NICHT registriert).
$ErrorActionPreference = 'Continue'
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$py     = Join-Path $wurzel 'Werkstatt\nautilus-venv\Scripts\python.exe'
$skript = Join-Path $wurzel 'Agenten\Bus\nautilus_okx_lauf.py'
if (-not (Test-Path $py)) { $py = 'O:\Werkstatt\nautilus-venv\Scripts\python.exe' }
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'nautilus-okx-letzter-lauf.log'
"=== Lauf $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
if (-not ((Test-Path $py) -and (Test-Path $skript))) {
  "ENDE FEHLER: nautilus-venv oder nautilus_okx_lauf.py fehlt" | Add-Content $log -Encoding UTF8
  exit 1
}
& $py $skript --instrument BTC-USDC --bar 4H --strategie ensemble 2>&1 | Where-Object { $_ -notmatch 'INFO\]|Pandas4Warning|e\.run' } | Add-Content $log -Encoding UTF8
$code = $LASTEXITCODE
"ENDE Code $code" | Add-Content $log -Encoding UTF8
exit $code
