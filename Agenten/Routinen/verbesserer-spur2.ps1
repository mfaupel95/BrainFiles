# Woechentliche Selbstverbesserung von Spur 2 (XPERP). Laeuft NACH
# handel-wachen.ps1 und getrennt von verbesserer.ps1 (Spur 1): der erste Lauf
# rechnet 20-35 Minuten (Merkmals-Cache). Erzeugt nur einen Vorschlag in
# verbesserer/berichte/ - angewandt wird er erst per /ja im Dauerlauf.
$ErrorActionPreference = "Stop"
$env:MAXHIRN_ROUTINE = "1"
$wurzel = Split-Path -Parent $PSScriptRoot
. (Join-Path $wurzel 'Bus\Ereignis.ps1')
$py = Join-Path $wurzel "Handel\verbesserer\.venv\Scripts\python.exe"
$lauf = Join-Path $wurzel "Handel\verbesserer\xperp_lauf.py"
$log = Join-Path $PSScriptRoot "logs\verbesserer-spur2-$(Get-Date -Format yyyy-MM-dd).log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$marke = Melde-Start -Wer 'routine/verbesserer-spur2' `
           -Log ('Agenten/Routinen/logs/verbesserer-spur2-' + (Get-Date -Format yyyy-MM-dd) + '.log')
try {
  & $py $lauf *>&1 | Tee-Object -FilePath $log
  Melde-Ende -Marke $marke -Code $LASTEXITCODE
  exit $LASTEXITCODE
} catch {
  Melde-Ende -Marke $marke -Code 1 -Text "$_"
  throw
}
