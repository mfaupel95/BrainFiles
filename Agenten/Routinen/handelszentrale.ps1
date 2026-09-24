# Startet die Handelszentrale - die lesende Ansicht ueber alle Handelsspuren.
# Von der Aufgabenplanung bei der Anmeldung aufgerufen (+2 Minuten Verzoegerung).
#
# WARUM: Nach jedem Neustart war das Fenster weg. Positionen, Stops und der
# Stand des Dauerlaufs waren dann nur ueber Telegram oder den Tagesbericht zu
# sehen. Die Ansicht liest ausschliesslich - sie schaltet nichts scharf, kennt
# keinen Orderpfad und schreibt keine Spurdatei; der Dauerlauf bleibt der
# einzige Schreiber (Beleg: Agenten/Handel/tests/test_handelszentrale_rein_lesend.py).
#
# Laeuft schon eine Handelszentrale (auch eine von Hand gestartete), wird
# NICHTS gestartet: zwei Fenster zeigen dasselbe, und das zweite laesst sich
# spaeter nicht mehr von einem Dienst unterscheiden. Die Verzweigung steht im
# Protokoll - ein "nichts zu tun" ohne Zeile sieht wie ein stummer Abbruch aus.
#
# Gestartet wird python.exe mit verstecktem Fenster (-WindowStyle Hidden).
# Das ist der dokumentierte Fix gegen aufblitzende Konsolenfenster: nur ein
# Elternprozess MIT eigener Konsole (python.exe statt pythonw.exe) vererbt sie
# als eine versteckte Konsole an alle Kinder (powershell, onchainos ...), statt
# dass jedes Kind sein eigenes sichtbares anlegt (Hermes main.ts:2986). Ein
# Fehler beim Aufbau landet weiter in handelszentrale-fehler.log.
#
# Nachweis ist der FENSTERTITEL des Kindes, nicht die PID des Starters: ein
# venv-Start ist ein Paar aus Launcher und Interpreter.
#
# Erste Einrichtung / Neuaufsetzen der Aufgabe (Administrator nicht noetig):
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\handelszentrale-aufgabe.ps1

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent          # Agenten
$handel = Join-Path $wurzel 'Handel'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')

$log       = Join-Path $logs 'handelszentrale-letzter-lauf.log'
$fehlerlog = Join-Path $logs 'handelszentrale-fehler.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/handelszentrale' `
           -Log 'Agenten/Routinen/logs/handelszentrale-letzter-lauf.log'

$titel   = 'Handelszentrale'
$skript  = Join-Path $handel 'handelszentrale.py'
$pythonw = Join-Path $handel 'scanner\.venv\Scripts\pythonw.exe'
$python  = Join-Path $handel 'scanner\.venv\Scripts\python.exe'

function Schreib($text) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $text" |
    Add-Content $log -Encoding UTF8
}

function Get-FensterPID {
  # Fenstertitel statt PID-Datei: so wird auch ein von Hand gestartetes
  # Fenster erkannt, und ein Neustart der Sitzung hinterlaesst keine Sperre.
  $p = Get-Process -Name python* -ErrorAction SilentlyContinue |
       Where-Object { $_.MainWindowTitle -like "*$titel*" } |
       Select-Object -First 1
  if ($p) { return [int]$p.Id }
  return 0
}

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" |
  Set-Content $log -Encoding UTF8
try {
  $schon = Get-FensterPID
  if ($schon) {
    Schreib "Fenster laeuft schon (PID $schon) - kein Start."
    "ENDE ok (nichts zu tun)" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text "laeuft bereits (PID $schon)"
    exit 0
  }

  if (-not (Test-Path $skript)) { throw "Fenster fehlt: $skript" }
  $starter = $python
    if (-not (Test-Path $starter)) { $starter = $pythonw }
    if (-not (Test-Path $starter)) { throw "kein Python unter $python" }

  Schreib "kein Fenster offen - starte $([IO.Path]::GetFileName($starter))"
  Remove-Item $fehlerlog -Force -ErrorAction SilentlyContinue
  $p = Start-Process -FilePath $starter -ArgumentList $skript `
                       -WorkingDirectory $handel -WindowStyle Hidden -PassThru `
                       -RedirectStandardError $fehlerlog

  $pid_neu = 0
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    $pid_neu = Get-FensterPID
    if ($pid_neu) { break }
    if ($p.HasExited) { break }
  }

  if ($pid_neu) {
    Schreib "Fenster offen (PID $pid_neu) nach $([int]((Get-Date) - $start).TotalSeconds) s"
    "ENDE ok" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text "Fenster PID $pid_neu"
  } else {
    $grund = "kein Fenstertitel nach 30 s"
    if ($p.HasExited) { $grund = "Prozess endete mit Code $($p.ExitCode)" }
    if (Test-Path $fehlerlog) {
      $zeilen = (Get-Content $fehlerlog -Tail 5 -ErrorAction SilentlyContinue) -join " | "
      if ($zeilen) { $grund = "$grund - $zeilen" }
    }
    throw $grund
  }
} catch {
  Schreib "ENDE FEHLER: $_"
  Melde-Ende -Marke $marke -Code 1 -Text "$_"
  exit 1
}
