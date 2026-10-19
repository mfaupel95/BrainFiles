# Startet den Moon-Dev-Agent (new_or_top_agent) aus dem Repo-Klon als
# Dauerlaeufer: stuendlicher Analysezyklus, Urteil vom LOKALEN Ollama
# (qwen35-8k), Marktdaten ueber die oeffentliche CoinGecko-API - kein
# bezahlter Schluessel noetig. Von der Aufgabenplanung bei Anmeldung
# aufgerufen (+2 Minuten Verzoegerung).
#
# Nur EINE Instanz: laeuft schon ein Agent (auch ein von Hand gestarteter),
# wird nichts gestartet - zwei Instanzen wuerden zweimal dieselben CSVs
# schreiben. Die Verzweigung steht im Protokoll.
#
# Die Schluessel (OLLAMA_MODEL, OLLAMA_BASE_URL) kommen aus der .env des
# Repos, nicht aus dem Wrapper - der Wrapper traegt keine Geheimnisse.
#
# Erst-Einrichtung / Neuaufsetzen (Administrator nicht noetig):
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\moondev-agent-aufgabe.ps1

$ErrorActionPreference = 'Stop'
$wurzel     = Split-Path $PSScriptRoot -Parent            # Agenten
$brainfiles = Split-Path $wurzel -Parent                  # BrainFiles
$repo       = Join-Path $brainfiles 'Werkstatt\moon-dev-ai-agents'
$logs       = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')

$log        = Join-Path $logs 'moondev-agent-letzter-lauf.log'
$agentlog   = Join-Path $logs 'moondev-new_or_top.log'
$fehlerlog  = Join-Path $logs 'moondev-new_or_top.err.log'
$start      = Get-Date
$marke      = Melde-Start -Wer 'routine/moondev-agent' `
              -Log 'Agenten/Routinen/logs/moondev-agent-letzter-lauf.log'

function Schreib($text) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $text" |
    Add-Content $log -Encoding UTF8
}

function Get-AgentProzess {
  # CommandLine statt PID-Datei: so wird auch ein von Hand gestarteter
  # Agent erkannt, und ein Neustart der Sitzung hinterlaesst keine Sperre.
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*new_or_top_agent*' } |
    Select-Object -First 1
}

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" |
  Set-Content $log -Encoding UTF8
try {
  $schon = Get-AgentProzess
  if ($schon) {
    Schreib "Agent laeuft schon (PID $($schon.ProcessId)) - kein Start."
    'ENDE ok (nichts zu tun)' | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text "laeuft bereits (PID $($schon.ProcessId))"
    exit 0
  }

  $envDatei = Join-Path $repo '.env'
  if (-not (Test-Path $envDatei)) { throw "fehlt: $envDatei" }
  foreach ($z in (Get-Content $envDatei -Encoding UTF8)) {
    if ($z -match '^OLLAMA_MODEL=')      { $env:OLLAMA_MODEL    = $z.Substring(13).Trim() }
    elseif ($z -match '^OLLAMA_BASE_URL=') { $env:OLLAMA_BASE_URL = $z.Substring(15).Trim() }
  }
  if (-not $env:OLLAMA_MODEL) { throw 'OLLAMA_MODEL fehlt in der .env des Repos' }

  $python = Join-Path $repo '.venv\Scripts\python.exe'
  if (-not (Test-Path $python)) { throw "kein venv: $python" }

  Schreib "kein Agent da - starte (Modell $env:OLLAMA_MODEL) aus $repo"
  # Emojis im Agent-Output brauchen UTF-8; ohne das bricht Windows-Python
  # unter der cp1252-Codepage beim ersten Emoji-print ab (UnicodeEncodeError).
  $env:PYTHONIOENCODING = 'utf-8'
  Remove-Item $agentlog, $fehlerlog -Force -ErrorAction SilentlyContinue
  $p = Start-Process -FilePath $python `
                     -ArgumentList '-m','src.agents.new_or_top_agent' `
                     -WorkingDirectory $repo -PassThru `
                     -RedirectStandardOutput $agentlog `
                     -RedirectStandardError $fehlerlog

  $pid_neu = 0
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    $gefunden = Get-AgentProzess
    if ($gefunden) { $pid_neu = [int]$gefunden.ProcessId; break }
    if ($p.HasExited) { break }
  }

  if ($pid_neu) {
    Schreib "Agent laeuft (PID $pid_neu) nach $([int]((Get-Date) - $start).TotalSeconds) s"
    'ENDE ok' | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text "Agent PID $pid_neu"
  } else {
    $grund = 'kein Agent-Prozess nach 30 s'
    if ($p.HasExited) { $grund = "Prozess endete mit Code $($p.ExitCode)" }
    if (Test-Path $fehlerlog) {
      $zeilen = (Get-Content $fehlerlog -Tail 5 -ErrorAction SilentlyContinue) -join ' | '
      if ($zeilen) { $grund = "$grund - $zeilen" }
    }
    throw $grund
  }
} catch {
  Schreib "ENDE FEHLER: $_"
  Melde-Ende -Marke $marke -Code 1 -Text "$_"
  exit 1
}