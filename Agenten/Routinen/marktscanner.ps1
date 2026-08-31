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

$ErrorActionPreference = 'Stop'
$wurzel  = Split-Path $PSScriptRoot -Parent
$scanner = Join-Path $wurzel 'Handel\scanner'
$py      = Join-Path $scanner '.venv\Scripts\python.exe'
$logs    = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$log   = Join-Path $logs 'marktscanner-letzter-lauf.log'
$start = Get-Date

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

if (-not (Test-Path $py)) {
  "ENDE FEHLER: kein Python unter $py - '.venv' im scanner-Ordner neu anlegen (py -3.13 -m venv .venv)" |
    Add-Content $log -Encoding UTF8
  exit 1
}

try {
  Push-Location $scanner
  & $py 'scan.py'              *>&1 | Add-Content $log -Encoding UTF8
  & $py 'handeln.py' '--papier' *>&1 | Add-Content $log -Encoding UTF8
  Pop-Location
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  exit 1
}
