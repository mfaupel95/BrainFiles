# Phase 4 -- Den gemeinsamen Arbeitsordner anlegen und fuellen.
#
# Werkstatt/ ist der Ort, an dem Claude, Codex und Hermes zusammenarbeiten,
# ohne im Vault zu wildern. Was hierher wandert, war schon vorher Arbeitsware:
# geklonte Fremd-Repos, Sitzungsablagen, Protokolle einzelner Laeufe.
#
#   .\40-werkstatt.ps1            Trockenlauf
#   .\40-werkstatt.ps1 -Echt      wirklich

param([switch]$Echt)
$DryRun = -not $Echt

. "$PSScriptRoot\gemeinsam.ps1"
$pfade  = Get-Pfade
$wurzel = Get-Wurzel
function P([string]$r) { Join-Path $wurzel $r }

Schritt "Wurzel: $wurzel"

# --- 0. Blockierer melden --------------------------------------------------
$quellen = $pfade.Werkstatt | ForEach-Object { (P $_.Von) }
$fremd = Get-Process | Where-Object { $p = $_.Path; $p -and ($quellen | Where-Object { $p -like "$_*" }) }
if ($fremd) {
    $fremd | ForEach-Object { Schritt "  BLOCKIERT: $($_.Name) (PID $($_.Id)) - $($_.Path)" 'fehler' }
    if (-not $DryRun) { Bilanz 'abgebrochen - es laufen Programme aus den Quellordnern.' -Erfolg:$false; return }
}

# --- 1. Verschieben --------------------------------------------------------
Schritt ''
Schritt 'Verschieben:'
foreach ($m in $pfade.Werkstatt) { Verschiebe -Von (P $m.Von) -Nach (P $m.Nach) -DryRun:$DryRun }

# --- 2. Neue Faecher -------------------------------------------------------
Schritt ''
foreach ($n in $pfade.WerkstattNeu) {
    if (-not (Test-Path (P $n))) {
        if ($DryRun) { Schritt "  [Probe] anlegen: $n" }
        else { New-Item -ItemType Directory -Path (P $n) -Force | Out-Null; Schritt "  angelegt: $n" 'ok' }
    } else { Schritt "  besteht: $n" 'ok' }
}

# --- 3. Die Spielregeln ----------------------------------------------------
# AGENTS.md liest Codex und Hermes, CLAUDE.md liest Claude. Gleicher Inhalt,
# zwei Namen - sonst gelten die Regeln nur fuer einen der drei.
$regeln = Join-Path $PSScriptRoot 'werkstatt-regeln.md'
foreach ($ziel in @('Werkstatt\AGENTS.md', 'Werkstatt\CLAUDE.md')) {
    if ($DryRun) { Schritt "  [Probe] Spielregeln -> $ziel" }
    else { Copy-Item -LiteralPath $regeln -Destination (P $ziel) -Force; Schritt "  geschrieben: $ziel" 'ok' }
}

# --- 4. Bilanz -------------------------------------------------------------
if (-not $DryRun) {
    $faecher = @(Get-ChildItem (P 'Werkstatt') -Directory | Select-Object -ExpandProperty Name)
    Schritt ''
    Schritt "Faecher: $($faecher -join ', ')"
    Bilanz "Werkstatt steht mit $($faecher.Count) Faechern und den Spielregeln in zwei Dateien."
} else { Bilanz 'Probe gelaufen - nichts veraendert.' }
Protokoll-Schreiben '40-werkstatt' | Out-Null
