# Woechentlicher Wachen-Abgleich der automatischen Spuren. Von der Windows-
# Aufgabenplanung aufgerufen (Bedingung 5 aus Wissen/Handelsregeln.md,
# Abschnitt "Damit der Automat unbeaufsichtigt laufen darf").
#
# Zwei Spuren, nacheinander, jede mit ihrer eigenen wachen.json:
#   Spur 1  Handel\scanner  (OKX, USD)
#   Spur 3  Handel\kraken   (Kraken, EUR)
# Spur 2 (XPERP) hat keinen Live-Pfad und damit nichts abzugleichen.
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

. (Join-Path $wurzel 'Bus\Ereignis.ps1')                                # neu

$log   = Join-Path $logs 'handel-wachen-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/handel-wachen' `
           -Log 'Agenten/Routinen/logs/handel-wachen-letzter-lauf.log'  # neu

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

if (-not (Test-Path $py)) {
  "ENDE FEHLER: kein Python unter $py - '.venv' im scanner-Ordner neu anlegen (py -3.13 -m venv .venv)" |
    Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "kein Python unter $py"        # neu
  exit 1
}

try {
  Push-Location $scanner
  & $py 'handeln.py' '--wachen' *>&1 | Add-Content $log -Encoding UTF8
  Pop-Location

  $kraken = Join-Path $wurzel 'Handel\kraken'
  if (Test-Path (Join-Path $kraken 'handeln.py')) {
    "" | Add-Content $log -Encoding UTF8
    Push-Location $kraken
    & $py 'handeln.py' '--wachen' *>&1 | Add-Content $log -Encoding UTF8
    Pop-Location
  }
  # Backtest-Urteile der Spuren mit eigenem Motor (gitter, orbk, nautilus):
  # faehrt die drei Motoren mit den Werten der jeweiligen Spur und schreibt in
  # deren wachen.json NUR die drei Felder backtest_bestanden / backtest_urteil /
  # backtest_geprueft_am. handel_erlaubt und freigabe.erfuellt bleiben unberuehrt;
  # scharf schaltet weiterhin nur ein Schritt von Hand.
  "" | Add-Content $log -Encoding UTF8
  Push-Location (Join-Path $wurzel 'Handel')
  & $py 'backtest_urteile.py' *>&1 | Add-Content $log -Encoding UTF8
  Pop-Location
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0                                      # neu
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  exit 1
}
