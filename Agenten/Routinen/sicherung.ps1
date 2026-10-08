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

$ErrorActionPreference = 'Continue'
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
  $tmp = Join-Path $logs 'sicherung-lauf.tmp'
  # Erst das verschluesselte Secrets-Archiv erneuern, DANN kopieren: die
  # Sicherung schliesst die Klartextdateien aus (/XF *.env, auth.json,
  # OKX_API.env) und nimmt nur dieses Archiv mit. Scheitert die Archivierung,
  # laeuft die Sicherung trotzdem - die Klartextdateien sind dann aber NICHT
  # mitgesichert, und genau das muss im Protokoll stehen.
  $arch = Join-Path $wurzel 'Agenten\Hermes\scripts\secrets-archivieren.ps1'
  if (Test-Path $arch) {
    "--- Secrets-Archiv ---" | Add-Content $log -Encoding UTF8
    & powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File $arch *>> $log
    if ($LASTEXITCODE -ne 0) {
      "WARNUNG: Secrets-Archiv nicht erneuert (Code $LASTEXITCODE) - Klartextdateien sind ausgeschlossen und damit NICHT in dieser Sicherung." | Add-Content $log -Encoding UTF8
    }
  } else {
    "WARNUNG: secrets-archivieren.ps1 fehlt - Klartextdateien sind ausgeschlossen und damit NICHT in dieser Sicherung." | Add-Content $log -Encoding UTF8
  }
  & powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File (Join-Path $wurzel 'sichern.ps1') *> $tmp
  if (Test-Path $tmp) { Get-Content $tmp -Encoding UTF8 | Add-Content $log -Encoding UTF8; Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
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
