# Phase 8 -- Die Sicherungsskripte auf die neue Struktur stellen.
#
# Bisher war die Quelle MaxHirn\ und die 51 GB Modelle liefen jede Nacht mit
# nach G: -- obwohl Schutzregeln.md sie selbst als "neu herunterladbar" fuehrt.
# Kuenftig ist die Quelle BrainFiles\ (damit auch Agenten und Werkstatt
# gesichert sind) und Modelle\ steht in der Ausschlussliste.
#
# Stufe-1-Regel der Schutzregeln: erst .bak anlegen, dann aendern, dann EINMAL
# echt laufen lassen und die Ausgabe zeigen. Eine Aenderung an einem
# Sicherungsskript gilt erst als erledigt, wenn ein Lauf sie bestaetigt hat --
# genau hier hat sichern.ps1 am 23.08.2026 "ENDE ok" gemeldet, waehrend
# robocopy mit Code 11 gescheitert war.
#
#   .\80-sicherung.ps1            Trockenlauf
#   .\80-sicherung.ps1 -Echt      aendern
#   .\80-sicherung.ps1 -Echt -Lauf  aendern und sichern.ps1 einmal ausfuehren

param([switch]$Echt, [switch]$Lauf)
$DryRun = -not $Echt

. "$PSScriptRoot\gemeinsam.ps1"
$wurzel = Get-Wurzel
function P([string]$r) { Join-Path $wurzel $r }

Schritt "Wurzel: $wurzel"

$skripte = @('Agenten\sichern.ps1', 'Agenten\sichern-zweitkopie.ps1', 'Agenten\sichern-ausser-haus.ps1')
$alteQuelle = 'C:\Users\faupe\Documents\BrainFiles\MaxHirn'
$neueQuelle = $wurzel

$gesamt = 0
foreach ($s in $skripte) {
    $datei = P $s
    if (-not (Test-Path $datei)) { Schritt "FEHLT: $s" 'warn'; continue }
    Sicherungskopie -Datei $datei -DryRun:$DryRun | Out-Null
    $n = Ersetze-InDatei -Datei $datei -Ersetzungen @{
        # Die Quelle eine Ebene hoeher.
        [regex]::Escape("'$alteQuelle'") = "'$neueQuelle'"
        # Modelle in die Ausschlussliste von robocopy. GitHub steht dort noch
        # aus alter Zeit - der Ordner heisst jetzt Werkstatt\Repos.
        '/XD GitHub'                     = '/XD Modelle Repos Sitzungen Worktrees'
    } -DryRun:$DryRun
    $gesamt += $n
    Schritt ("  {0,3} Stelle(n): {1}" -f $n, $s) 'ok'
}

# Gegenprobe: steht in den Skripten noch der alte Stamm?
Schritt ''
foreach ($s in $skripte) {
    $datei = P $s
    if (-not (Test-Path $datei)) { continue }
    $roh = Get-Content -LiteralPath $datei -Raw
    $alt = ([regex]::Matches($roh, [regex]::Escape('BrainFiles\MaxHirn'))).Count
    if ($alt -gt 0) { Schritt "  $s traegt noch $alt mal BrainFiles\MaxHirn - von Hand pruefen." 'warn' }
}

# --- Der eine echte Lauf ---------------------------------------------------
if ($Lauf -and -not $DryRun) {
    Schritt ''
    Schritt 'sichern.ps1 laeuft jetzt einmal echt. Das dauert.' 'warn'
    & (P 'Agenten\sichern.ps1') 2>&1 | ForEach-Object { Schritt "  $_" }
    Bilanz "Skripte angepasst ($gesamt Stellen) und sichern.ps1 einmal gelaufen - Ausgabe oben lesen."
} elseif ($DryRun) {
    Bilanz "Probe: $gesamt Stellen wuerden geaendert. Danach mit -Echt -Lauf einmal wirklich sichern."
} else {
    Bilanz "$gesamt Stellen geaendert. NOCH NICHT BESTAETIGT - erst ein echter Lauf zaehlt (-Echt -Lauf)." -Erfolg:$false
}
Protokoll-Schreiben '80-sicherung' | Out-Null
