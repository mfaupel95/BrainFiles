# Woechentlicher Wachen-Abgleich des Marktscanners. Von der Windows-
# Aufgabenplanung aufgerufen (Bedingung 5 aus Wissen/Schutzregeln.md,
# Abschnitt "Damit der Automat unbeaufsichtigt laufen darf").
#
# Ruft handeln.py --wachen: zeigt die Bedingungen 2-5 als Momentaufnahme,
# spiegelt Journal + Zustand nach journal_zweitziel (Bedingung 4) und
# schliesst handel_erlaubt, wenn der rollierende Erwartungswert negativ ist
# (Bedingung 5) oder der Kill-Switch erreicht ist (Bedingung 2).
#
# Loest KEINE Order aus und legt handel_erlaubt NIE auf true - der Schalter
# geht hier nur von true nach false. Scharfschalten bleibt ein Schritt von
# Hand. Siehe Wissen/Routinen.md.

$ErrorActionPreference = 'Stop'
# Sagt handeln.py, dass hier niemand am Bildschirm sitzt: kein
# Freigabefenster, kein scharfer Handel aus dem Zeitplan.
$env:MAXHIRN_ROUTINE = '1'
$wurzel  = Split-Path $PSScriptRoot -Parent
$scanner = Join-Path $wurzel 'Handel\scanner'
$py      = Join-Path $scanner '.venv\Scripts\python.exe'
$logs    = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$log   = Join-Path $logs 'handel-wachen-letzter-lauf.log'
$start = Get-Date

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

if (-not (Test-Path $py)) {
  "ENDE FEHLER: kein Python unter $py - '.venv' im scanner-Ordner neu anlegen (py -3.13 -m venv .venv)" |
    Add-Content $log -Encoding UTF8
  exit 1
}

try {
  Push-Location $scanner
  & $py 'handeln.py' '--wachen' *>&1 | Add-Content $log -Encoding UTF8
  Pop-Location
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  exit 1
}
