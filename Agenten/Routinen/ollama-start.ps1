# Startet Ollama (ollama serve) - die lokale Modell-Laufzeit, an der alle
# LLM-Urteile haengen (Moon-Dev-Agenten, LLM-Spuren). Von der Aufgabenplanung
# bei der Anmeldung aufgerufen (+2 Minuten Verzoegerung).
#
# WARUM: Ollama hat keinen Windows-Dienst (gemessen 16.09.2026: kein
# ollama-Process, kein Service-Eintrag, Port 11434 zu, nachdem die
# Start-Sitzung endete). Ohne Ollama liefern alle LLM-Aufrufe leeren Content
# und die Agenten fallen still auf "DO NOTHING" zurueck.
#
# Laeuft schon ein Ollama (auch ein von Hand gestartetes), wird NICHTS
# gestartet - zwei Server auf demselben Port schliessen sich aus; die
# Verzweigung steht im Protokoll.
#
# Erst-Einrichtung / Neuaufsetzen der Aufgabe (Administrator noetig fuer die
# Registrierung, nicht fuer den Betrieb):
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\ollama-start-aufgabe.ps1

$ErrorActionPreference = 'Stop'
$wurzel   = Split-Path $PSScriptRoot -Parent            # Agenten
$logs     = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')

$log   = Join-Path $logs 'ollama-start-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/ollama-start' `
         -Log 'Agenten/Routinen/logs/ollama-start-letzter-lauf.log'

function Schreib($text) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $text" |
    Add-Content $log -Encoding UTF8
}

function PortOffen($port) {
  try {
    return [bool](Test-NetConnection 127.0.0.1 -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue)
  } catch { return $false }
}

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" |
  Set-Content $log -Encoding UTF8
try {
  if (PortOffen 11434) {
    Schreib "Ollama laeuft schon (Port 11434 offen) - kein Start."
    'ENDE ok (nichts zu tun)' | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text 'laeuft bereits'
    exit 0
  }

  $ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
  if (-not (Test-Path $ollama)) { throw "ollama.exe fehlt: $ollama" }

  Schreib "kein Ollama da - starte $ollama serve"
  $p = Start-Process -FilePath $ollama -ArgumentList 'serve' `
                     -WindowStyle Hidden -PassThru

  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (PortOffen 11434) { break }
    if ($p.HasExited) { break }
  }

  if (PortOffen 11434) {
    Schreib "Ollama antwortet (Port 11434) nach $([int]((Get-Date) - $start).TotalSeconds) s"
    'ENDE ok' | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text 'Port 11434 offen'
  } else {
    $grund = 'Port 11434 nicht offen nach 30 s'
    if ($p.HasExited) { $grund = "Prozess endete mit Code $($p.ExitCode)" }
    throw $grund
  }
} catch {
  Schreib "ENDE FEHLER: $_"
  Melde-Ende -Marke $marke -Code 1 -Text "$_"
  exit 1
}