# Stuendliche Ausstiegspruefung des Papier-Tests (OKX-1H-Kerzen): Stop/Ziel offener Positionen binnen Stunden.
$ErrorActionPreference = 'Continue'
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$py     = Join-Path $wurzel 'Agenten\Handel\.venv\Scripts\python.exe'
$ordner = Join-Path $wurzel 'Werkstatt\scanner-varianten'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'scanner-papier-stunde-letzter-lauf.log'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/scanner-papier-stunde' -Log 'Agenten/Routinen/logs/scanner-papier-stunde-letzter-lauf.log'
"=== Lauf $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
if (-not ((Test-Path $py) -and (Test-Path $ordner))) {
  "ENDE FEHLER: Python oder Ordner fehlt" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text 'Python oder Ordner fehlt'
  exit 1
}
Push-Location $ordner
& $py 'papier_stunde.py' *>&1 | Add-Content $log -Encoding UTF8
$code = $LASTEXITCODE
Pop-Location
"ENDE Code $code" | Add-Content $log -Encoding UTF8
Melde-Ende -Marke $marke -Code $code
exit $code
