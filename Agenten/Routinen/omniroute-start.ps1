# Startet den OmniRoute-Router, falls er nicht laeuft.
# Von der Aufgabenplanung bei der Anmeldung aufgerufen.
#
# WARUM: Ohne laufenden Router faellt der Hermes-Provider omniroute aus.
# Jede Agenten-Delegation scheitert dann mit "Connection error" bzw.
# HTTP 401 - genau das war nach jedem Neustart des Rechners der Zustand.
# Die Deaktivierung der alten Autostart-Eintraege (09.09.2026) bleibt damit
# bestehen: gestartet wird nur ueber diesen einen, protokollierten Weg.
#
# Ist der Port schon belegt, wird NICHT gestartet. An einem laufenden Router
# haengen offene Agenten-Sitzungen, und zwei Instanzen teilen sich dieselbe
# Speicherdatei (~/.omniroute/storage.sqlite).

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$brain  = Split-Path $wurzel -Parent
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')

$log   = Join-Path $logs 'omniroute-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/omniroute-start' `
           -Log 'Agenten/Routinen/logs/omniroute-letzter-lauf.log'

$port    = 20128
$starter = Join-Path $brain 'Werkstatt\Projekte\OmniRoute\omniroute-quell-produktion.ps1'

function Test-PortOffen($p) {
  $c = New-Object Net.Sockets.TcpClient
  try {
    $c.Connect('127.0.0.1', $p)
    $c.Close()
    return $true
  } catch {
    return $false
  }
}

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
try {
  if (Test-PortOffen $port) {
    "Port $port ist belegt - der Router laeuft schon, kein Start." |
      Add-Content $log -Encoding UTF8
    "ENDE ok (nichts zu tun) nach $([int]((Get-Date) - $start).TotalSeconds) s" |
      Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0
    exit 0
  }

  if (-not (Test-Path $starter)) { throw "Startskript fehlt: $starter" }
  "Port $port ist frei - starte den Router ueber das Quell-Produktion-Skript." |
    Add-Content $log -Encoding UTF8

  # Losgeloest starten, NICHT mit Pipe: das Startskript startet einen
  # DAUERprozess. Haengt der Aufrufer an dessen Ausgabestrom, kehrt er nie
  # zurueck - die Aufgabe bleibt "Running", dieses Protokoll ist in der
  # Zwischenzeit gesperrt ("Device or resource busy"), und wer die Aufgabe
  # beendet, reisst den Router mit. Genau das war am 16.09.2026: Start 10:35,
  # ^C um 10:39, danach 5,5 Stunden kein Router - unbemerkt.
  # Eigene Konsole (kein -NoNewWindow) = eigener Prozessbaum.
  $argumente = @('-ExecutionPolicy','Bypass','-NoProfile','-File', ('"' + $starter + '"'))
  Start-Process -FilePath 'powershell.exe' -ArgumentList $argumente -WindowStyle Hidden | Out-Null

  # Selbst auf den Port warten - der erste Start baut notfalls erst (next build).
  $frist = 600
  $warte = Get-Date
  while (-not (Test-PortOffen $port)) {
    if (((Get-Date) - $warte).TotalSeconds -gt $frist) {
      "Router kam binnen $frist s nicht hoch. Letzte Zeilen der Startprotokolle:" |
        Add-Content $log -Encoding UTF8
      $proto = Join-Path $env:USERPROFILE '.omniroute\logs\quell-produktion'
      Get-ChildItem $proto -Filter 'start-*.log*' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime | Select-Object -Last 2 |
        ForEach-Object { Get-Content $_.FullName -Tail 12 | Add-Content $log -Encoding UTF8 }
      throw "Router kam auf Port $port nicht hoch"
    }
    Start-Sleep -Seconds 3
  }

  "Router laeuft auf Port $port." | Add-Content $log -Encoding UTF8
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0
} catch {
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"
  exit 1
}