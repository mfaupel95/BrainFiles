<#
.SYNOPSIS
    Holt Windows Terminal aus dem festverdrahteten Fokusmodus (Stand 02.09.2026).

.DESCRIPTION
    Symptom: Das Terminal-Fenster (PowerShell 7.6.5 laeuft darin) laesst sich
    weder verschieben noch in der Groesse aendern, und die Einstellungen sind
    per Maus nicht erreichbar. Ursache ist der Fokusmodus, der Titel- und
    Tab-Leiste ausblendet. Er steht an zwei Stellen:

    1. settings.json  -> "launchMode": "focus" wird auf "default" gesetzt.
    2. state.json     -> in allen persistedWindowLayouts wird
                         "launchMode": "focus" auf "default" gesetzt.
                         Die Split-Pane-Layouts selbst bleiben erhalten.

    ("initialPosition": "," in settings.json bleibt unangetastet - das ist
    gueltige Terminal-Syntax fuer "beide Koordinaten automatisch".)

    Beide Dateien werden vorher nach <name>.bak-20260902 gesichert.
    Kein Adminrecht noetig (nur AppData des Benutzers).

    WICHTIG: Windows Terminal vor dem Lauf vollstaendig schliessen, sonst
    schreibt es state.json beim Beenden erneut mit "focus".

.PARAMETER Testlauf
    Zeigt nur an, was geschehen wuerde. Aendert nichts.

.PARAMETER Rueckgaengig
    Stellt settings.json und state.json aus den .bak-20260902-Sicherungen
    wieder her.

.EXAMPLE
    Rechtsklick auf die Datei > "Mit PowerShell ausfuehren"
    oder in einer PowerShell:
        .\einmalig-20260902-terminal-fokusmodus.ps1 -Testlauf
        .\einmalig-20260902-terminal-fokusmodus.ps1
        .\einmalig-20260902-terminal-fokusmodus.ps1 -Rueckgaengig
#>

[CmdletBinding()]
param(
    [switch]$Testlauf,
    [switch]$Rueckgaengig
)

$ErrorActionPreference = 'Stop'

$localState = Join-Path $env:LOCALAPPDATA `
    'Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState'
$settings = Join-Path $localState 'settings.json'
$state    = Join-Path $localState 'state.json'
$suffix   = '.bak-20260902'

function Test-TerminalLaeuft {
    $null -ne (Get-Process -Name 'WindowsTerminal' -ErrorAction SilentlyContinue)
}

# ------------------------------------------------------------ Rueckgaengig
if ($Rueckgaengig) {
    foreach ($ziel in @($settings, $state)) {
        $bak = "$ziel$suffix"
        if (-not (Test-Path $bak)) {
            Write-Host "Keine Sicherung: $bak - uebersprungen." -ForegroundColor Yellow
            continue
        }
        if ($Testlauf) {
            Write-Host "WUERDE zuruecksetzen: $bak -> $ziel"
        }
        else {
            Copy-Item $bak $ziel -Force
            Write-Host "Zurueckgesetzt: $ziel" -ForegroundColor Green
        }
    }
    return
}

# ------------------------------------------------------------ Vorpruefung
if (Test-TerminalLaeuft) {
    Write-Host "Windows Terminal laeuft noch. Bitte ALLE Terminal-Fenster" -ForegroundColor Red
    Write-Host "schliessen (auch das hier - Skript per Rechtsklick starten)," -ForegroundColor Red
    Write-Host "sonst wird state.json beim Beenden erneut ueberschrieben." -ForegroundColor Red
    if (-not $Testlauf) { return }
}

foreach ($ziel in @($settings, $state)) {
    if (-not (Test-Path $ziel)) { throw "Nicht gefunden: $ziel" }
}

# ------------------------------------------------------------ Sicherung
if (-not $Testlauf) {
    foreach ($ziel in @($settings, $state)) {
        Copy-Item $ziel "$ziel$suffix" -Force
        Write-Host "Gesichert: $ziel$suffix" -ForegroundColor DarkGray
    }
}

# ------------------------------------------------------------ settings.json
$s = Get-Content $settings -Raw
$sNeu = $s -replace '"launchMode"\s*:\s*"focus"', '"launchMode": "default"'

if ($sNeu -eq $s) {
    Write-Host "settings.json: kein 'launchMode: focus' gefunden - nichts zu aendern." -ForegroundColor Yellow
}
elseif ($Testlauf) {
    Write-Host 'settings.json WUERDE geaendert: "launchMode": "focus" -> "launchMode": "default"' -ForegroundColor Cyan
}
else {
    # Gegenpruefung: bleibt es gueltiges JSON?
    $null = $sNeu | ConvertFrom-Json
    Set-Content $settings $sNeu -NoNewline -Encoding UTF8
    Write-Host "settings.json geaendert." -ForegroundColor Green
}

# ------------------------------------------------------------ state.json
$t = Get-Content $state -Raw
$tNeu = $t -replace '"launchMode"\s*:\s*"focus"', '"launchMode" : "default"'

$anzahl = ([regex]::Matches($t, '"launchMode"\s*:\s*"focus"')).Count

if ($anzahl -eq 0) {
    Write-Host "state.json: kein 'focus' in den Layouts - nichts zu aendern." -ForegroundColor Yellow
}
elseif ($Testlauf) {
    Write-Host "state.json WUERDE geaendert: $anzahl x 'focus' -> 'default' in persistedWindowLayouts." -ForegroundColor Cyan
}
else {
    $null = $tNeu | ConvertFrom-Json
    Set-Content $state $tNeu -NoNewline -Encoding UTF8
    Write-Host "state.json geaendert ($anzahl Layouts)." -ForegroundColor Green
}

Write-Host ""
Write-Host "Fertig. Windows Terminal neu starten - Titel- und Tab-Leiste sind zurueck." -ForegroundColor Green
Write-Host "Fokusmodus bei Bedarf weiterhin per Strg+Umschalt+P > 'Fokusmodus umschalten'." -ForegroundColor DarkGray
