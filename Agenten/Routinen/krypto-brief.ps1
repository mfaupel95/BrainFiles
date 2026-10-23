# krypto-brief.ps1 -- Taegliches Krypto-Briefing (Smart-Money-Format).
# Von der Windows-Aufgabenplanung aufgerufen. Holt Marktdaten, rendert das
# Briefing und sendet es an den eigenen BotFather-Chat.
#
# Drei Stufen, robust nach unten (Hausmuster marktbriefing.ps1):
#   1. fetch.py             -> datiertes JSON nach Werkstatt/KryptoBrief/daten/
#   2. render_briefing.py   -> Briefing-Klartext aus dem neuesten JSON
#   3. send_telegram.py     -> an KRYPTO_BRIEF_CHAT_ID (BotFather-Chat)
#
# Fehler sind nie tot-ausfallen: eine tote Datenquelle loggt nur, ein alter
# Rohabzug greift weiter; schlaegt das Senden fehl, steht der Text im Log.
# KEIN Handel, KEIN Scharfschalten -- der Bot liest und informiert nur.

$ErrorActionPreference = 'Continue'   # stderr von git/etc. bricht nicht ab.
. (Join-Path $PSScriptRoot '..\Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/krypto-brief' -Log 'Agenten/Routinen/logs/krypto-brief-letzter-lauf.log'

$brainfiles = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$logs   = Join-Path $PSScriptRoot 'logs'
$log    = Join-Path $logs 'krypto-brief-letzter-lauf.log'
$start  = Get-Date
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

$python = Join-Path $brainfiles 'Agenten\Handel\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
  "ENDE FEHLER: python fehlt: $python" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text 'Python fehlt'
  exit 1
}

$entry = Join-Path $brainfiles 'Agenten\KryptoBrief\krypto-brief.py'
& $python $entry *>> $log
$code = $LASTEXITCODE
if ($code -eq 0) {
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
} else {
  "ENDE FEHLER code=$code nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
}
Melde-Ende -Marke $marke -Code $code -Text "Code $code"
exit $code
