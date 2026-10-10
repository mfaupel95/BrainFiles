# Papier-Ausfuehrung der Fremd-Signale: ein Lauf von fremd_signale\handeln.py --papier.
# Ist das Tor zu (fremd_signale\wachen.json: fremd_signale_erlaubt != true), tut der Lauf nichts.
# Kein --live. Aufgerufen von der Aufgabe MaxHirn-Fremd-Papier (fremd-papier-aufgabe.ps1).
$ErrorActionPreference = 'Continue'
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$py     = Join-Path $wurzel 'Agenten\Handel\scanner\.venv\Scripts\python.exe'
$ordner = Join-Path $wurzel 'Agenten\Handel\fremd_signale'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'fremd-papier-letzter-lauf.log'
"=== Lauf $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
if (-not ((Test-Path $py) -and (Test-Path (Join-Path $ordner 'handeln.py')))) {
  "ENDE FEHLER: Python oder handeln.py fehlt" | Add-Content $log -Encoding UTF8
  exit 1
}
Push-Location $ordner
& $py 'handeln.py' '--papier' *>&1 | Add-Content $log -Encoding UTF8
$code = $LASTEXITCODE
Pop-Location
"ENDE Code $code" | Add-Content $log -Encoding UTF8
exit $code
