# Herzschlag-Wache: meldet stille Spuren (Handel\herzschlag_wache.py).
# Von der Aufgabe MaxHirn-Herzschlag-Wache alle 10 Minuten aufgerufen.

$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot '..\Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/herzschlag-wache' -Log 'Agenten/Routinen/logs/herzschlag-wache-letzter-lauf.log'
$wurzel = Split-Path $PSScriptRoot -Parent
$handel = Join-Path $wurzel 'Handel'
$py = Join-Path $handel 'scanner\.venv\Scripts\python.exe'
$logs = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'herzschlag-wache-letzter-lauf.log'
"=== Lauf $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

if (-not (Test-Path $py)) {
  "ENDE FEHLER: kein Python unter $py" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text 'Python fehlt'
  exit 1
}

Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue
Push-Location $handel
& $py 'herzschlag_wache.py' *>&1 | Add-Content $log -Encoding UTF8
$code = $LASTEXITCODE
Pop-Location
"ENDE Exitcode $code (1 = mindestens eine Spur still)" | Add-Content $log -Encoding UTF8
Melde-Ende -Marke $marke -Code 0 -Text "Code $code"
exit 0
