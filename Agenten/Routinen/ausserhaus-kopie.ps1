# Erneuert die Ausser-Haus-Kopie auf Q:, sobald die SSD angesteckt ist.
# Von der Aufgabenplanung taeglich 21:30 aufgerufen (nach der Zweitkopie 21:00).
#
# WARUM ALS AUFGABE (T-182, Entscheidung Max am 29.09.2026)
# Vorher lief die Kopie nur von Hand - und wurde still 17 Tage alt, ohne dass es
# jemand merkte. Jetzt erneuert sie diese Aufgabe, sobald Q: haengt. Haengt die
# SSD nicht, tut sie NICHTS und meldet nichts: Exitcode 2 bedeutet
# "uebersprungen" und ist kein Fehlschlag (dieselbe Regel wie bei der
# Zweitkopie). Das WIRKLICHE "ausser Haus" bleibt Handarbeit - abmelden und die
# SSD woanders hinbringen.
#
# ZWEITE SICHERUNG: der Fristwaechter (Hermes-Cron ausserhaus-frist-wache)
# meldet weiterhin, wenn die juengste Spur im Ziel 14 Tage alt wird. Beides
# zusammen deckt beide Faelle ab - SSD selten angesteckt (Aufgabe greift, wenn
# sie da ist) und Aufgabe kaputt (Fristwaechter meldet).
#
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\ausserhaus-kopie.ps1
#   -NurPruefen = nur rechnen (robocopy /L), nichts schreiben

param([switch]$NurPruefen)

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')

$log = Join-Path $logs 'ausserhaus-kopie-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/ausserhaus-kopie' `
           -Log 'Agenten/Routinen/logs/ausserhaus-kopie-letzter-lauf.log'

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
try {
  # $argumente, nicht $args: $args ist in PowerShell automatisch belegt.
  $argumente = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                 (Join-Path $wurzel 'sichern-ausser-haus.ps1'))
  if ($NurPruefen) { $argumente += '-NurPruefen' }
  & powershell @argumente *>&1 | Add-Content $log -Encoding UTF8
  $code = $LASTEXITCODE
  $s = [int]((Get-Date) - $start).TotalSeconds
  if ($code -eq 2) {
    "ENDE uebersprungen - Q: nicht angesteckt oder Archiv fehlt (nach $s s)" |
      Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text 'uebersprungen: Q: nicht angesteckt'
  } elseif ($code -ne 0) {
    "ENDE FEHLER - Exitcode $code nach $s s" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code $code -Text "Exitcode $code"
    exit $code
  } else {
    "ENDE ok nach $s s" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0
  }
} catch {
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"
  exit 1
}
