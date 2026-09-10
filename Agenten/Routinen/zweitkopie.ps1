# Geplante Zweitkopie nach O:. Von der Aufgabenplanung aufgerufen.
#
# Laeuft um 21:00, also nach der Hauptsicherung um 20:00. Beide gleichzeitig
# waere unnoetig: sie lesen denselben Baum.
#
# Exitcode 2 bedeutet "O: nicht erreichbar" und ist kein Fehler im Sinne der
# Aufgabenplanung - er wird protokolliert, aber nicht als Fehlschlag gemeldet,
# damit ein abgemeldetes Laufwerk keinen roten Alarm ausloest.

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')                                # neu

$log = Join-Path $logs 'zweitkopie-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/zweitkopie' `
           -Log 'Agenten/Routinen/logs/zweitkopie-letzter-lauf.log'     # neu

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
try {
  & powershell -ExecutionPolicy Bypass -File (Join-Path $wurzel 'sichern-zweitkopie.ps1') *>&1 |
    Add-Content $log -Encoding UTF8
  $code = $LASTEXITCODE
  $s = [int]((Get-Date) - $start).TotalSeconds
  if ($code -eq 2) {
    "ENDE uebersprungen - O: nicht erreichbar (nach $s s)" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text 'uebersprungen: O: nicht erreichbar' # neu
  } elseif ($code -ne 0) {
    "ENDE FEHLER - Exitcode $code nach $s s" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code $code -Text "Exitcode $code"         # neu
    exit $code
  } else {
    "ENDE ok nach $s s" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0                                    # neu
  }
} catch {
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  exit 1
}
