# Geplantes Einsortieren des Posteingangs. Von der Aufgabenplanung aufgerufen.
#
# Das Skript sortiert nur, was es sicher zuordnen kann; alles andere bleibt
# liegen. Es ersetzt damit nicht das gezielte Einsortieren von Hand - der Lauf
# vom 23.08.2026 hat 9 von 303 Dateien zugeordnet und 67 liegen gelassen.
# Deshalb ist das Protokoll hier wichtiger als bei der Sicherung: Es zeigt,
# wie viel liegen bleibt.

param([switch]$NurPruefen)

$ErrorActionPreference = 'Stop'
# Zwei Ebenen ueber diesem Skript liegt die Wurzel BrainFiles\ (Agenten\Routinen\
# -> Agenten\ -> BrainFiles\). Das Archiv-Werkzeug liegt seit der Ordnertrennung
# vom 30.08.2026 unter MaxHirn\Archiv\ArchivSuche\ (hiess vorher Claude\).
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$suche  = Join-Path $wurzel 'MaxHirn\Archiv\ArchivSuche'
$logs     = Join-Path $PSScriptRoot 'logs'
$waechter = Join-Path $PSScriptRoot 'safe-file-ops.ps1'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Agenten\Bus\Ereignis.ps1')                         # neu

$log = Join-Path $logs 'posteingang-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/posteingang' `
           -Log 'Agenten/Routinen/logs/posteingang-letzter-lauf.log'    # neu

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
# --- Vorschaltung: scharfer Waechter, sonst kein automatischer Lauf ---------
# Der Posteingang ist Stufe 0: unsortierte Originale ohne Zweitquelle. Dieses
# Skript verschiebt daraus - das ist gewolltes Sortieren und bleibt erlaubt.
# Es darf aber nie anfangen zu loeschen. Vor jedem Lauf wird deshalb geprueft,
# dass der Waechter genau das noch verbietet. Ist die Zusicherung hinfaellig
# (Regel geaendert, Pfad verschoben), bricht der Lauf ab, statt still Schaden
# anzurichten (angeordnet 12.09.2026).
$inbox = 'O:\Archiv\Posteingang'
$tor = & powershell -ExecutionPolicy Bypass -NoProfile -File $waechter `
         -Pfad $inbox -Aktion massenhaft_loeschen -Erwartet ABBRUCH -Stille
if ($LASTEXITCODE -ne 0) {
  "ENDE FEHLER: Schutzpruefung fuer '$inbox' nicht bestanden (Exitcode $LASTEXITCODE)." | Add-Content $log -Encoding UTF8
  $tor | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text 'Waechtertor offen'
  exit 1
}
"Vorschaltung ok: '$inbox' ist gegen Massenloeschen gesperrt." | Add-Content $log -Encoding UTF8
try {
  if ($NurPruefen) {
    'Modus: nur pruefen (sort_inbox.py wird nicht gestartet).' | Add-Content $log -Encoding UTF8
  } else {
    Push-Location $suche
    & (Join-Path $suche '.venv\Scripts\python.exe') (Join-Path $suche 'sort_inbox.py') *>&1 |
      Add-Content $log -Encoding UTF8
    Pop-Location
  }
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0                                      # neu
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  exit 1
}
