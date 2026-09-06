# Woechentliche Selbstverbesserung von Spur 1. Laeuft NACH handel-wachen.ps1.
# Erzeugt nur einen Vorschlag in verbesserer/berichte/ - angewandt wird er
# erst per /ja im Dauerlauf (Handelsregeln: nicht heimlich eingesetzt).
$ErrorActionPreference = "Stop"
$env:MAXHIRN_ROUTINE = "1"
$wurzel = Split-Path -Parent $PSScriptRoot
$py = Join-Path $wurzel "Handel\verbesserer\.venv\Scripts\python.exe"
$lauf = Join-Path $wurzel "Handel\verbesserer\lauf.py"
$log = Join-Path $PSScriptRoot "logs\verbesserer-$(Get-Date -Format yyyy-MM-dd).log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
& $py $lauf --spur spur1 *>&1 | Tee-Object -FilePath $log
exit $LASTEXITCODE
