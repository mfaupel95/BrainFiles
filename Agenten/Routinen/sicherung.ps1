# Geplanter Sicherungslauf. Von der Windows-Aufgabenplanung aufgerufen.
#
# Der Wrapper existiert aus zwei Gruenden: Er haelt den Aufruf in der
# Aufgabenplanung kurz, und er schreibt die Ausgabe mit - eine geplante Aufgabe
# hat kein Fenster, in dem jemand mitliest. Bricht die Sicherung ab, steht der
# Grund im Protokoll statt nirgends.
#
# Pfade sind relativ zu diesem Skript ($PSScriptRoot), damit der Vault umziehen
# kann. Nur die Registrierung in der Aufgabenplanung enthaelt absolute Pfade und
# muss nach einem Umzug neu angelegt werden - siehe Wissen/Routinen.md.

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')                              # neu

$log = Join-Path $logs 'sicherung-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/sicherung' `
           -Log 'Agenten/Routinen/logs/sicherung-letzter-lauf.log'    # neu

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
try {
  & powershell -ExecutionPolicy Bypass -File (Join-Path $wurzel 'sichern.ps1') *>&1 |
    Add-Content $log -Encoding UTF8
  $code = $LASTEXITCODE
  $s = [int]((Get-Date) - $start).TotalSeconds
  if ($code -ne 0) {
    # Nicht auf Exceptions verlassen: robocopy wirft keine, es meldet ueber den
    # Exitcode. Ohne diese Pruefung stand im Protokoll "ENDE ok", waehrend die
    # Sicherung tatsaechlich fehlgeschlagen war (erlebt 23.08.2026, Code 11).
    "ENDE FEHLER - Exitcode $code nach $s s" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code $code -Text "Exitcode $code"       # neu
    exit $code
  }
  "ENDE ok nach $s s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0                                    # neu
} catch {
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                         # neu
  exit 1
}
