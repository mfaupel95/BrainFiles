# Startet den 24/7-Dauerlauf der Handelsspuren und haelt ihn am Leben.
# Von der Windows-Aufgabenplanung aufgerufen, Ausloeser "Bei Anmeldung" und
# zusaetzlich alle 30 Minuten (der zweite faengt einen Absturz auf, siehe
# unten).
#
# WICHTIG: Dieses Skript schaltet NICHTS scharf. dauerlauf.py laeuft ohne
# offenes Freigabefenster als Papierhandel, und ein Fenster oeffnet nur Max
# per Telegram - auf Anfrage, gedeckelt auf 24 Stunden. Aus einem Zeitplan
# heraus wird nie echtes Geld bewegt. Siehe Wissen/Handelsregeln.md, Punkt 3.
#
# Warum ein Waechter und kein Dienst: Die Kernel-Power-41-Abschaltungen aus
# Wissen/Hardware.md nehmen den Rechner ohne Vorwarnung mit. Ein Dienst waere
# danach zwar wieder da, aber die Aufgabenplanung ist das Werkzeug, das hier
# ohnehin schon alles andere startet - und sie ist sichtbar, wenn etwas
# klemmt. Der 30-Minuten-Ausloeser prueft nur, ob schon einer laeuft, und
# startet sonst neu; laeuft einer, endet das Skript sofort.

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$handel = Join-Path $wurzel 'Handel'
$py     = Join-Path $handel 'scanner\.venv\Scripts\python.exe'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$log = Join-Path $logs 'handel-dauerlauf-letzter-lauf.log'
$sperre = Join-Path $handel 'dauerlauf.pid'

function Schreib($text) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $text" | Add-Content $log -Encoding UTF8
}

# Laeuft schon einer? Zwei Dauerlaeufe auf demselben Telegram-Token nehmen
# sich gegenseitig die Nachrichten weg - Telegram antwortet dem zweiten
# Abrufer mit 409. Deshalb hier abfangen und nicht erst dort.
if (Test-Path $sperre) {
  $pid_alt = Get-Content $sperre -ErrorAction SilentlyContinue
  $lebt = Get-Process -Id $pid_alt -ErrorAction SilentlyContinue
  if ($lebt -and $lebt.ProcessName -like 'python*') {
    Schreib "laeuft bereits (PID $pid_alt) - nichts zu tun"
    exit 0
  }
  Schreib "verwaiste Sperre (PID $pid_alt lebt nicht mehr) - wird ersetzt"
  Remove-Item $sperre -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path $py)) {
  Schreib "ENDE FEHLER: kein Python unter $py - '.venv' im scanner-Ordner neu anlegen (py -3.13 -m venv .venv)"
  exit 1
}

Schreib "Start"
$p = Start-Process -FilePath $py `
                   -ArgumentList 'dauerlauf.py','--takt','15' `
                   -WorkingDirectory $handel `
                   -WindowStyle Hidden -PassThru
$p.Id | Set-Content $sperre -Encoding ASCII
Schreib "gestartet als PID $($p.Id), Takt 15 min"
exit 0
