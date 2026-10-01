# Taeglicher Papier-Test der Scanner-Varianten v0 gegen v4 (nur Papier, kein Geld).
# Holt frische OKX-Tageskerzen, schliesst offene Papierpositionen (Stop/Ziel),
# traegt neue Signale ein. Zustand: Werkstatt/scanner-varianten/papier_pos.json,
# Log: papier_log.csv. Auswertung nach ca. 30 Runden je Variante.
$ErrorActionPreference = 'Continue'
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$py     = Join-Path $wurzel 'Agenten\Handel\.venv\Scripts\python.exe'
$ordner = Join-Path $wurzel 'Werkstatt\scanner-varianten'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'scanner-papier-letzter-lauf.log'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/scanner-papier' -Log 'Agenten/Routinen/logs/scanner-papier-letzter-lauf.log'
"=== Lauf $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
if (-not ((Test-Path $py) -and (Test-Path $ordner))) {
  "ENDE FEHLER: Python oder Ordner fehlt" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text 'Python oder Ordner fehlt'
  exit 1
}
Push-Location $ordner
& $py 'papier.py' *>&1 | Add-Content $log -Encoding UTF8
$code = $LASTEXITCODE
Pop-Location
"ENDE Code $code" | Add-Content $log -Encoding UTF8
Melde-Ende -Marke $marke -Code $code
exit $code
