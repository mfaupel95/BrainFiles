<#
.SYNOPSIS
    Teilt den Git-Arbeitsbaum in "ruhend" und "in Arbeit" auf.

.DESCRIPTION
    Vor jedem Commit im Mehrsitzungsbetrieb: Welche geaenderten Dateien darf
    ich anfassen? Die Schutzregeln setzen die Schwelle bei 10 Minuten
    Aenderungsalter - juengere Dateien koennen mitten in einem fremden
    Arbeitsschritt stehen und bleiben liegen.

    Das Skript aendert nichts. Es liest `git status --porcelain`, ergaenzt
    LastWriteTime und gibt zwei Gruppen aus, dazu eine fertige
    `git add`-Zeile fuer die ruhende Gruppe.

    Hintergrund: Wissen/Schutzregeln.md, Abschnitt "Mehrere Sitzungen".

.PARAMETER Minuten
    Ruhe-Schwelle in Minuten. Standard 10, entsprechend den Schutzregeln.

.EXAMPLE
    .\Routinen\arbeitsbaum-pruefen.ps1
#>
[CmdletBinding()]
param([int]$Minuten = 10)

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
git -C $wurzel rev-parse --show-toplevel >$null 2>&1
if ($LASTEXITCODE -ne 0) { Write-Output "Kein Git-Repository in $wurzel"; exit 1 }

$jetzt   = Get-Date
$ruhend  = @()
$inArbeit = @()
$ausgeschlossen = @()

function Test-EingebettetesGitRepo([string]$Pfad, [string]$Wurzel) {
    if (Test-Path -LiteralPath $Pfad -PathType Container) {
        $ordner = $Pfad
    } else {
        $ordner = Split-Path -Parent $Pfad
    }

    while ($ordner -and -not [string]::Equals($ordner, $Wurzel, [StringComparison]::OrdinalIgnoreCase)) {
        if (Test-Path -LiteralPath (Join-Path $ordner '.git')) { return $true }
        $naechster = Split-Path -Parent $ordner
        if ($naechster -eq $ordner) { break }
        $ordner = $naechster
    }
    return $false
}

foreach ($z in (git -C $wurzel status --porcelain)) {
    if ([string]::IsNullOrWhiteSpace($z)) { continue }
    $status = $z.Substring(0,2)
    $pfad   = $z.Substring(3).Trim('"')
    if ($pfad -match ' -> ') { $pfad = ($pfad -split ' -> ')[1] }   # Umbenennung
    $voll   = Join-Path $wurzel $pfad

    git -C $wurzel check-ignore --quiet --no-index -- $pfad 2>$null
    $ignoriert = $LASTEXITCODE -eq 0
    if ($ignoriert -or (Test-EingebettetesGitRepo $voll $wurzel)) {
        $ausgeschlossen += $pfad
        continue
    }

    if (Test-Path -LiteralPath $voll) {
        $lw    = (Get-Item -LiteralPath $voll).LastWriteTime
        $alter = [int]($jetzt - $lw).TotalMinutes
    } else {
        $lw = $null; $alter = 9999                                  # geloescht: ruht
    }

    $e = [pscustomobject]@{
        Status   = $status
        Pfad     = $pfad
        Geaendert= if ($lw) { $lw.ToString('HH:mm:ss') } else { 'geloescht' }
        AlterMin = $alter
    }
    if ($alter -ge $Minuten) { $ruhend += $e } else { $inArbeit += $e }
}

if (-not $ruhend -and -not $inArbeit) { Write-Output "Arbeitsbaum sauber."; exit 0 }

if ($ausgeschlossen) {
    Write-Output "=== AUSGESCHLOSSEN (ignoriert oder eingebettetes Git-Repo): $($ausgeschlossen.Count) ==="
    $ausgeschlossen | Sort-Object | ForEach-Object { Write-Output "    $_" }
    Write-Output ""
}

Write-Output "=== RUHEND (aelter als $Minuten Min) - darf gesichert werden: $($ruhend.Count) ==="
if ($ruhend) {
    $ruhend | Sort-Object AlterMin -Descending | Format-Table -AutoSize | Out-String -Width 200 | Write-Output
    $liste = ($ruhend | ForEach-Object { '"' + $_.Pfad + '"' }) -join ' '
    Write-Output "git add $liste"
}

Write-Output ""
Write-Output "=== IN ARBEIT (juenger als $Minuten Min): $($inArbeit.Count) ==="
Write-Output "Was die eigene Sitzung selbst geschrieben hat, gehoert trotzdem committet."
Write-Output "Liegen bleibt nur, was NICHT aus dieser Sitzung stammt."
if ($inArbeit) {
    $inArbeit | Sort-Object AlterMin | Format-Table -AutoSize | Out-String -Width 200 | Write-Output
}

Write-Output ""
Write-Output "Eigene Arbeit und fremde Arbeit in GETRENNTE Commits."
Write-Output "Fremd: git commit --author=`"Andere Sitzung <fremd@local>`" -m `"...`""
