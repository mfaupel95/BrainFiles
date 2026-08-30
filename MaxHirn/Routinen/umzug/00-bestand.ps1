# Phase 0 -- Bestand aufnehmen und pruefen, ob der Umzug losgehen darf.
#
# Erzeugt die Beweisliste, gegen die Phase 9 am Ende zaehlt. Ohne diese Zahl
# ist "es ist nichts verlorengegangen" eine Behauptung, keine Pruefung.
#
#   .\00-bestand.ps1            Bestand aufnehmen
#   .\00-bestand.ps1 -Nachher   dasselbe, aber als Vergleichslauf am Ende

param([switch]$Nachher)

. "$PSScriptRoot\gemeinsam.ps1"
$pfade  = Get-Pfade
$wurzel = Get-Wurzel
$marke  = if ($Nachher) { 'nachher' } else { 'vorher' }

Schritt "Wurzel: $wurzel"
Schritt ''

# --- 1. Laufende Programme -------------------------------------------------
# Ein offener Prozess haelt Dateien und schreibt mitten im Umzug zurueck.
$laufen = @()
foreach ($name in $pfade.Prozesse) {
    $p = Get-Process -Name $name -ErrorAction SilentlyContinue
    if ($p) { $laufen += "$name ($($p.Count)x, PID $($p.Id -join ', '))" }
}
if ($laufen) {
    Schritt 'LAUFEN NOCH -- vor Phase 1 beenden:' 'warn'
    $laufen | ForEach-Object { Schritt "  - $_" 'warn' }
} else {
    Schritt 'Kein blockierendes Programm laeuft.' 'ok'
}
Schritt ''

# --- 2. Bestand ------------------------------------------------------------
$logs = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs -Force | Out-Null }
$liste = Join-Path $logs "bestand-$marke.txt"

$gesamt = 0
$zeilen = New-Object System.Collections.Generic.List[string]

foreach ($ordner in (Get-ChildItem $wurzel -Force -Directory | Sort-Object Name)) {
    $dateien = Get-ChildItem $ordner.FullName -Recurse -File -Force -ErrorAction SilentlyContinue
    $n = ($dateien | Measure-Object).Count
    $gesamt += $n
    Schritt ("{0,10:N0} Dateien  {1}" -f $n, $ordner.Name)
    foreach ($d in $dateien) { $zeilen.Add($d.FullName.Substring($wurzel.Length + 1)) }
}
$lose = Get-ChildItem $wurzel -Force -File
$gesamt += $lose.Count
foreach ($d in $lose) { $zeilen.Add($d.Name) }
Schritt ("{0,10:N0} Dateien  (lose in der Wurzel)" -f $lose.Count)

$zeilen | Sort-Object | Set-Content -LiteralPath $liste -Encoding UTF8

# --- 3. Bilanz -------------------------------------------------------------
$vorher = Join-Path $logs 'bestand-vorher.txt'
if ($Nachher -and (Test-Path $vorher)) {
    $a = Get-Content $vorher
    $b = Get-Content $liste
    $fehlen = (Compare-Object $a $b | Where-Object SideIndicator -eq '<=').Count
    Bilanz "$('{0:N0}' -f $gesamt) Dateien, $fehlen ohne Entsprechung im Vorher-Stand." -Erfolg:($fehlen -eq 0)
} else {
    Bilanz "$('{0:N0}' -f $gesamt) Dateien erfasst -> $liste$(if ($laufen) { '  ACHTUNG: ' + $laufen.Count + ' Programm(e) laufen noch.' })" -Erfolg:(-not $laufen)
}
Protokoll-Schreiben "00-bestand-$marke" | Out-Null
