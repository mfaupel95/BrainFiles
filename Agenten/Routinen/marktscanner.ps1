# Taeglicher Marktscanner. Von der Windows-Aufgabenplanung aufgerufen.
#
# WICHTIG: Diese Routine handelt NUR AUF PAPIER. handeln.py laeuft hier ohne
# --live, und selbst mit --live blieben zwei weitere Sperren zu (Schluessel,
# wachen.json handel_erlaubt). Scharfer Handel ist ein bewusster Schritt von
# Hand - aus einem Zeitplan heraus wird nie echtes Geld bewegt. Siehe
# Wissen/Schutzregeln.md, Abschnitt "Marktscanner", und Wissen/Routinen.md.
#
# Zwei Schritte: erst scan.py (Rangliste -> berichte/), dann handeln.py
# --papier (Vorschlaege -> zustand.json, handelsjournal.csv).
#
# handeln.py setzt dabei die Bedingungen 2-4 aus Wissen/Schutzregeln.md um
# (Drawdown-Ratsche, Herzschlag-Notausstieg, Journal ausser Haus). Bedingung 5
# laeuft woechentlich getrennt in handel-wachen.ps1.

$ErrorActionPreference = 'Stop'
# Sagt handeln.py, dass hier niemand am Bildschirm sitzt: kein
# Freigabefenster, kein scharfer Handel aus dem Zeitplan.
$env:MAXHIRN_ROUTINE = '1'
$wurzel  = Split-Path $PSScriptRoot -Parent
$scanner = Join-Path $wurzel 'Handel\scanner'
$py      = Join-Path $scanner '.venv\Scripts\python.exe'
$logs    = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')                                # neu

$log   = Join-Path $logs 'marktscanner-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/marktscanner' `
           -Log 'Agenten/Routinen/logs/marktscanner-letzter-lauf.log'   # neu

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

if (-not (Test-Path $py)) {
  "ENDE FEHLER: kein Python unter $py - '.venv' im scanner-Ordner neu anlegen (py -3.13 -m venv .venv)" |
    Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "kein Python unter $py"        # neu
  exit 1
}

try {
  Push-Location $scanner
  & $py 'scan.py'              *>&1 | Add-Content $log -Encoding UTF8
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
