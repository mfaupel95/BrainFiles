# Woechentliche Selbstverbesserung von Spur 1. Laeuft NACH handel-wachen.ps1.
# Erzeugt nur einen Vorschlag in verbesserer/berichte/ - angewandt wird er
# erst per /ja im Dauerlauf (Handelsregeln: nicht heimlich eingesetzt).
$ErrorActionPreference = "Stop"
$env:MAXHIRN_ROUTINE = "1"
$wurzel = Split-Path -Parent $PSScriptRoot
. (Join-Path $wurzel 'Bus\Ereignis.ps1')                                # neu
$py = Join-Path $wurzel "Handel\verbesserer\.venv\Scripts\python.exe"
$lauf = Join-Path $wurzel "Handel\verbesserer\lauf.py"
$log = Join-Path $PSScriptRoot "logs\verbesserer-$(Get-Date -Format yyyy-MM-dd).log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$marke = Melde-Start -Wer 'routine/verbesserer' `
           -Log ('Agenten/Routinen/logs/verbesserer-' + (Get-Date -Format yyyy-MM-dd) + '.log') # neu
try {                                                                    # neu
  & $py $lauf --spur spur1 *>&1 | Tee-Object -FilePath $log
  Melde-Ende -Marke $marke -Code $LASTEXITCODE                          # neu
  exit $LASTEXITCODE
} catch {                                                                # neu
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  throw                                                                 # neu
}                                                                        # neu
