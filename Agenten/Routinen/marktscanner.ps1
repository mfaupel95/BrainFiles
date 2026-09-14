# Taeglicher Marktscanner. Von der Windows-Aufgabenplanung aufgerufen.
#
# WICHTIG: Diese Routine handelt NUR AUF PAPIER. handeln.py laeuft hier ohne
# --live, und selbst mit --live blieben zwei weitere Sperren zu (Schluessel,
# wachen.json handel_erlaubt). Scharfer Handel ist ein bewusster Schritt von
# Hand - aus einem Zeitplan heraus wird nie echtes Geld bewegt. Siehe
# Wissen/Schutzregeln.md, Abschnitt "Marktscanner", und Wissen/Routinen.md.
#
# EIN Schritt: scan.py rechnet die Rangliste nach berichte/. Gehandelt wird
# hier NICHT mehr (14.09.2026): handeln.py laeuft im Dauerlauf, alle 15 Minuten
# - mit denselben Bedingungen 2-4 aus Wissen/Schutzregeln.md (Drawdown-Ratsche,
# Herzschlag-Notausstieg, Journal ausser Haus). Bedingung 5 laeuft woechentlich
# getrennt in handel-wachen.ps1. Zwei Schreiber auf denselben Zustand waren der
# Fehler bei xperp (Aufgabe MaxHirn-XPERP-Spur2, am 14.09.2026 geloescht); die
# Sperre unten haelt diesen Aufruf still, solange der Dauerlauf laeuft.

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

# Sperre gegen den Doppellauf: laeuft der Dauerlauf, schreibt dieser Aufruf
# auf denselben Zustand wie jener. Dann nur melden und aussteigen.
$pidDatei = Join-Path $wurzel 'Handel\dauerlauf.pid'
if (Test-Path $pidDatei) {
  $dl = (Get-Content $pidDatei -Raw).Trim()
  if ($dl -match '^[0-9]+$' -and (Get-Process -Id ([int]$dl) -ErrorAction SilentlyContinue)) {
    "ENDE uebersprungen: der Dauerlauf fuehrt die Spur (PID $dl) - ein zweiter Schreiber auf denselben Zustand ist nicht noetig." |
      Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text "uebersprungen, Dauerlauf laeuft"
    exit 0
  }
}

try {
  Push-Location $scanner
  & $py 'scan.py'              *>&1 | Add-Content $log -Encoding UTF8
  Pop-Location
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0                                      # neu
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  exit 1
}
