<#
anker-pruefen.ps1 - prueft den Hermes-Anker (Arbeitsverzeichnis), ohne eine Sitzung zu starten.

Warum: eine interaktive Hermes-Sitzung (CLI und TUI) uebernimmt das Startverzeichnis der
Shell. `terminal.cwd` aus Agenten\Hermes\config.yaml gilt dort NICHT - es gilt fuer Gateway,
Cron und entfernte Backends. Den interaktiven Anker setzt deshalb eine Funktion `hermes` im
PowerShell-Profil (Documents\PowerShell\Microsoft.PowerShell_profile.ps1).

Dieses Skript beweist, dass die ECHTE Profilfunktion wirkt: es legt eine Attrappe
`hermes.exe` an (eine Kopie von cmd.exe), haengt ihr Verzeichnis VORNE in den PATH, laedt das
Profil und ruft `hermes /c cd` auf - das Kind meldet damit sein Arbeitsverzeichnis.

Aufruf:    pwsh -NoProfile -File Agenten/Werkzeuge/anker-pruefen.ps1
Rueckgabe: 0 = alle Erwartungen erfuellt, 1 = Abweichung.
#>

$ErrorActionPreference = 'Continue'
$BrainFiles = 'C:\Users\faupe\Documents\BrainFiles'
$Anker = Join-Path $BrainFiles 'Agenten\Hermes'
$fehler = 0

function Pruefe([string]$Name, [string]$Ist, [string]$Soll) {
    $ok = ($Ist.TrimEnd('\') -ieq $Soll.TrimEnd('\'))
    if (-not $ok) { $script:fehler++ }
    '{0,-34} {1,-10} {2}' -f $Name, $(if ($ok) { 'ok' } else { 'ABWEICHUNG' }), $Ist
    if (-not $ok) { '{0,-34} {1,-10} {2}' -f '', 'erwartet', $Soll }
}

# --- Attrappe statt hermes.exe -------------------------------------------------
$attrappe = Join-Path $env:TEMP 'anker-pruefen-bin'
New-Item -ItemType Directory -Force -Path $attrappe | Out-Null
Copy-Item -LiteralPath (Join-Path $env:SystemRoot 'System32\cmd.exe') `
          -Destination (Join-Path $attrappe 'hermes.exe') -Force
$env:Path = "$attrappe;$env:Path"

# --- das echte Profil laden ----------------------------------------------------
. $PROFILE

'Profil     : ' + $PROFILE
'hermes ist : ' + (Get-Command hermes -ErrorAction SilentlyContinue).CommandType
''
if ((Get-Command hermes -ErrorAction SilentlyContinue).CommandType -ne 'Function') {
    'FEHLER: die Profilfunktion hermes fehlt - der Anker wirkt nicht.'
    exit 1
}

$start = (Get-Location).Path
Pruefe 'hermes (Vorgabe)'        (hermes /c cd) $Anker
Pruefe 'hermes -Hier'            (hermes -Hier /c cd) $start
Pruefe 'hermes -p gibtsnicht'    (hermes -p gibtsnicht /c cd) $Anker

# Ein echtes Bot-Profil: Erwartung unabhaengig aus dessen config.yaml gelesen.
$bot = Get-ChildItem -Directory (Join-Path $Anker 'profiles') -ErrorAction SilentlyContinue |
       Where-Object { Test-Path (Join-Path $_.FullName 'config.yaml') } |
       Sort-Object Name | Select-Object -First 1
if ($bot) {
    $soll = $null
    $imTerminal = $false
    foreach ($zeile in (Get-Content -LiteralPath (Join-Path $bot.FullName 'config.yaml'))) {
        if ($zeile -match '^terminal:') { $imTerminal = $true; continue }
        if ($imTerminal) {
            if ($zeile -match '^\S') { break }
            if ($zeile -match '^\s+cwd:\s*(.+?)\s*$') { $soll = $matches[1].Trim("'").Trim('"'); break }
        }
    }
    if ($soll -and (Test-Path -LiteralPath $soll)) {
        Pruefe "hermes -p $($bot.Name)" (hermes -p $bot.Name /c cd) $soll
    } else {
        '{0,-34} {1,-10} {2}' -f "hermes -p $($bot.Name)", 'uebersprungen', 'kein terminal.cwd im Profil'
    }
}

Pruefe 'Shell-cwd danach'        (Get-Location).Path $start
''
if ($fehler -eq 0) { 'Anker in Ordnung.'; exit 0 }
"$fehler Abweichung(en)."; exit 1