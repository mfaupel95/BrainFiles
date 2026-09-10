# Taeglicher Lauf der dritten Spur (Kraken, Spot, EUR). Von der Windows-
# Aufgabenplanung aufgerufen.
#
# WICHTIG: Diese Routine handelt NUR AUF PAPIER. handeln.py laeuft hier ohne
# --live, und selbst mit --live blieben mehrere Sperren zu (wachen.json
# handel_erlaubt, Freigabe, Journal-Zweitziel, Guthaben). Scharfer Handel ist
# ein bewusster Schritt von Hand - aus einem Zeitplan heraus wird nie echtes
# Geld bewegt. Siehe Wissen/Handelsregeln.md und Wissen/Routinen.md.
#
# Zwei Schritte: erst scan.py (Rangliste -> berichte/), dann handeln.py
# --papier (Vorschlaege -> zustand.json, handelsjournal.csv).
#
# Python kommt aus scanner\.venv - die dritte Spur braucht kein eigenes,
# weil kraken.py nur die Standardbibliothek benutzt.

$ErrorActionPreference = 'Stop'
# Sagt handeln.py, dass hier niemand am Bildschirm sitzt: kein
# Freigabefenster, kein scharfer Handel aus dem Zeitplan.
$env:MAXHIRN_ROUTINE = '1'
$wurzel = Split-Path $PSScriptRoot -Parent
$spur   = Join-Path $wurzel 'Handel\kraken'
$py     = Join-Path $wurzel 'Handel\scanner\.venv\Scripts\python.exe'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')                                # neu

$log   = Join-Path $logs 'kraken-scanner-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/kraken-scanner' `
           -Log 'Agenten/Routinen/logs/kraken-scanner-letzter-lauf.log' # neu

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

if (-not (Test-Path $py)) {
  "ENDE FEHLER: kein Python unter $py - '.venv' im scanner-Ordner neu anlegen (py -3.13 -m venv .venv)" |
    Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "kein Python unter $py"        # neu
  exit 1
}

try {
  Push-Location $spur
  & $py 'scan.py'               *>&1 | Add-Content $log -Encoding UTF8
  & $py 'handeln.py' '--papier' *>&1 | Add-Content $log -Encoding UTF8
  Pop-Location
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0                                      # neu
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  exit 1
}
