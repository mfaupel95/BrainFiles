# Findet Optimierungen im Betrieb: welche Routine lahmt, welche Leiche steht
# herum, welcher Prozess waechst. Von der Aufgabenplanung aufgerufen
# (MaxHirn-Optimierungen-Finden, montags 09:45).
#
# Warum es diese Routine gibt: Am 16.09.2026 wurde die Sicherung um 20:00 von
# aussen beendet (0xC000013A) - im Protokoll stand danach nur die Kopfzeile,
# die Ende-Zeile fehlte. Der Bus konnte das nicht melden, weil das
# Ende-Ereignis nie geschrieben wurde; die Systempruefung sah den Lauf als
# "fehlerfrei" an, weil ein von-aussen-beendeter Lauf fuer sie kein Fehler ist.
# Genau diese Luecke schliesst die Pruefung: sie liest die Protokolle der
# anderen Routinen nach und meldet, was angefangen und nicht zu Ende gelaufen
# ist.
#
# Die Arbeit steckt in Agenten\Hermes\scripts\optimierungen-finden.py (nur
# lesend, leere Ausgabe = kein Befund = keine Meldung). Dieser Wrapper
# schreibt das Protokoll und gibt den Befund ueber den Bus weiter.
#
# Pfade sind relativ zu $PSScriptRoot, damit der Vault umziehen kann.

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent                # Agenten
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')                              # neu

$log  = Join-Path $logs 'optimierungen-finden-letzter-lauf.log'
$py   = Join-Path $wurzel 'Hermes\scripts\optimierungen-finden.py'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/optimierungen-finden' `
           -Log 'Agenten/Routinen/logs/optimierungen-finden-letzter-lauf.log'   # neu

# Interpreter: zuerst der der Hermes-Anlage im Vault (zieht mit um), sonst die
# Anlagen-Python. Nur Standardbibliothek - es genuegt jede 3.10+.
$python = @(
  (Join-Path $wurzel 'Hermes\hermes-agent\venv\Scripts\python.exe'),
  (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe')
) | Where-Object { Test-Path $_ } | Select-Object -First 1

# Die Kopfzeile ist kein Schmuck: die Routine liest die Protokolle der anderen
# Routinen nach genau diesem Muster ('=== Lauf ...' bis 'ENDE ...'). Ohne
# beides wuerde sie sich selbst als abgebrochenen Lauf melden.
"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8
try {
  if (-not $python) { throw "Kein Python gefunden (Hermes-venv und Python313 fehlen)." }
  if (-not (Test-Path $py)) { throw "Skript fehlt: $py" }

  $ausgabe = @(& $python $py 2>&1 | ForEach-Object { $_.ToString() })
  $code    = $LASTEXITCODE
  $text    = ($ausgabe -join "`r`n").Trim()
  if ($text) { $text | Add-Content $log -Encoding UTF8 }
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8

  # Ein Befund ist kein Fehler: die Pruefung hat gearbeitet und etwas
  # gefunden. Deshalb als Hinweis (wird immer gemeldet) und nicht als
  # Fehlercode - der wuerde jede Woche wie ein kaputter Lauf aussehen.
  if ($text -and $code -eq 0) {
    Melde-Hinweis -Wer 'routine/optimierungen-finden' -Text $text
  }
  # Melde-Ende zuletzt: der Zyklus im Journal soll alles umfassen, und der
  # Anbindungstest verlangt die Meldung unmittelbar vor dem Ausstieg.
  Melde-Ende -Marke $marke -Code $code                                # neu
  exit $code
} catch {
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                          # neu
  throw
}
