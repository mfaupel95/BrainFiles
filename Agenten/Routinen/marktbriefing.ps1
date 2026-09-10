# Taeglicher Marktueberblick. Von der Windows-Aufgabenplanung aufgerufen.
#
# WICHTIG: Diese Routine LIEST NUR. Sie zieht die fertigen traderhub-Boards und
# laesst Claude daraus eine Wissensnotiz schreiben. Kein Handel, kein Versand,
# nichts wird scharfgeschaltet - aus einem Zeitplan heraus wird nie Geld bewegt.
# Siehe Wissen/Routinen.md und Wissen/Schutzregeln.md.
#
# Zwei Stufen, robust nach unten:
#   1. traderhub-Boards ziehen und als datierten Rohabzug ablegen. Deterministisch,
#      kein LLM, kein Login noetig. Diese Stufe muss gelingen.
#   2. "claude -p /marktbriefing" schreibt die Prosa-Notiz nach
#      Wissen/Marktlage-<Monat>-<Jahr>.md. Schlaegt sie fehl (kein Login, kein
#      Netz), bleibt der Rohabzug + ein Logeintrag "Notiz manuell nachziehen".

$ErrorActionPreference = 'Stop'
# Sagt nachgelagerten Werkzeugen, dass hier niemand am Bildschirm sitzt.
$env:MAXHIRN_ROUTINE = '1'

$brainfiles = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$vault      = Join-Path $brainfiles 'MaxHirn'
$logs       = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $brainfiles 'Agenten\Bus\Ereignis.ps1')                     # neu

$log    = Join-Path $logs 'marktbriefing-letzter-lauf.log'
$heute  = Get-Date -Format 'yyyy-MM-dd'
$daten  = Join-Path $logs "marktbriefing-daten-$heute.json"
$start  = Get-Date
$marke  = Melde-Start -Wer 'routine/marktbriefing' `
            -Log 'Agenten/Routinen/logs/marktbriefing-letzter-lauf.log' # neu

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

# --- Stufe 1: Rohabzug ------------------------------------------------------
$traderhub = (Get-Command traderhub -ErrorAction SilentlyContinue).Source
if (-not $traderhub) {
  "ENDE FEHLER: 'traderhub' nicht auf PATH - siehe .claude/skills/traderhub" |
    Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "traderhub nicht auf PATH"      # neu
  exit 1
}

try {
  $boards = [ordered]@{}
  foreach ($b in 'macro','movers') {
    $boards[$b] = (& $traderhub board get --board $b 2>&1 | Out-String)
  }
  $boards['rotation'] = (& $traderhub board rotation 2>&1 | Out-String)
  $abzug = [ordered]@{
    gezogen_am = $start.ToString('o')
    boards     = $boards
  }
  $abzug | ConvertTo-Json -Depth 8 | Set-Content $daten -Encoding UTF8
  "Stufe 1 ok: Rohabzug -> $daten" | Add-Content $log -Encoding UTF8
} catch {
  "ENDE FEHLER (Stufe 1): $_" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 1 -Text "Stufe 1: $_"                   # neu
  exit 1
}

# --- Stufe 2: Notiz per Claude -------------------------------------------------
$claude = (Get-Command claude -ErrorAction SilentlyContinue).Source
if (-not $claude) {
  "Stufe 2 uebersprungen: 'claude' nicht auf PATH. Notiz manuell nachziehen: /marktbriefing" |
    Add-Content $log -Encoding UTF8
  "ENDE ok (nur Stufe 1) nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0 -Text 'nur Stufe 1: kein claude auf PATH' # neu
  exit 0
}

$prompt = 'Fuehre den Skill /marktbriefing aus. Ziehe die Boards frisch, schreibe ' +
          'den heutigen Stand nach Wissen/Marktlage-<Monat>-<Jahr>.md (fortschreiben, ' +
          'nicht ueberschreiben), ziehe Wissen/INDEX.md nach falls die Monatsnotiz neu ' +
          'ist, und committe mit dem Skill sichern. Kein Handel, kein Versand.'

try {
  Push-Location $vault
  # --permission-mode acceptEdits: schreibt ohne Rueckfrage, aber nur Datei-Edits.
  & $claude -p $prompt --permission-mode acceptEdits *>&1 | Add-Content $log -Encoding UTF8
  $code = $LASTEXITCODE
  Pop-Location
  if ($code -ne 0) {
    "Stufe 2 FEHLER: claude Exitcode $code. Rohabzug liegt, Notiz manuell nachziehen: /marktbriefing" |
      Add-Content $log -Encoding UTF8
    "ENDE ok (nur Stufe 1) nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text "nur Stufe 1: claude Exitcode $code" # neu
    exit 0
  }
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0                                      # neu
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "Stufe 2 FEHLER: $_. Rohabzug liegt, Notiz manuell nachziehen: /marktbriefing" |
    Add-Content $log -Encoding UTF8
  "ENDE ok (nur Stufe 1) nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
  Melde-Ende -Marke $marke -Code 0 -Text "nur Stufe 1: $_"               # neu
  exit 0
}
