# Taeglicher Lauf der zweiten Spur (XPERP/OKX, gehebelt). Von der Windows-
# Aufgabenplanung aufgerufen.
#
# WICHTIG: Diese Routine handelt NUR AUF PAPIER. handeln.py laeuft hier ohne
# --live, und selbst mit --live blieben mehrere Sperren zu (wachen.json
# handel_erlaubt, Freigabe, Journal-Zweitziel). Scharfer Handel ist ein
# bewusster Schritt von Hand - aus einem Zeitplan heraus wird nie echtes
# Geld bewegt. Siehe Wissen/Handelsregeln.md und Wissen/Routinen.md.
#
# XPERP hat kein eigenes scan.py - handeln.py rechnet die Rangliste ueber
# auswahl.py/bot.py selbst (SCAN_ALTER_MINUTEN=120). Deshalb nur ein Aufruf.
#
# DEAKTIVIERT am 14.09.2026: die Aufgabe MaxHirn-XPERP-Spur2 ist abgeschaltet,
# weil die Spur laengst im Dauerlauf laeuft und dieser Aufruf ein zweiter
# Schreiber auf denselben Zustand war - am 14.09.2026 um 07:50 hat er einen
# Zyklus mit einem Ausstieg und drei Einstiegen gefahren, den der Dauerlauf
# nicht kannte. Die Datei bleibt liegen: faellt der Dauerlauf aus, ist sie der
# Notbetrieb (ein Aufruf, ein Zyklus). Die Sperre unten haelt sie ausserdem
# still, solange der Dauerlauf laeuft.
#
# Python kommt aus scanner\.venv - die zweite Spur braucht kein eigenes,
# weil okxf.py nur die Standardbibliothek benutzt.

$ErrorActionPreference = 'Stop'
# Sagt handeln.py, dass hier niemand am Bildschirm sitzt: kein
# Freigabefenster, kein scharfer Handel aus dem Zeitplan.
$env:MAXHIRN_ROUTINE = '1'
$wurzel = Split-Path $PSScriptRoot -Parent
$spur   = Join-Path $wurzel 'Handel\xperp'
$py     = Join-Path $wurzel 'Handel\scanner\.venv\Scripts\python.exe'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')                                # neu

$log   = Join-Path $logs 'xperp-handeln-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/xperp-handeln' `
           -Log 'Agenten/Routinen/logs/xperp-handeln-letzter-lauf.log'  # neu

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
  Push-Location $spur
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