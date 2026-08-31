# Gemeinsame Bausteine der Umzugsskripte.
#
# Wird von jedem 00-..90-Skript mit  . "$PSScriptRoot\gemeinsam.ps1"  geladen.
# Enthaelt bewusst keine absoluten Pfade: die Wurzel wird aus der eigenen Lage
# hochgelaufen, damit die Skripte in Phase 3 selbst mitwandern koennen und
# danach unveraendert weiterlaufen.

$ErrorActionPreference = 'Stop'

function Get-Wurzel {
    # Laeuft von hier aus nach oben, bis ein Ordner 'BrainFiles' heisst.
    $p = $PSScriptRoot
    while ($p -and (Split-Path $p -Leaf) -ne 'BrainFiles') {
        $eltern = Split-Path $p -Parent
        if ($eltern -eq $p) { throw "Keine Wurzel 'BrainFiles' oberhalb von $PSScriptRoot gefunden." }
        $p = $eltern
    }
    return $p
}

function Get-Pfade {
    Import-PowerShellDataFile (Join-Path $PSScriptRoot 'pfade.psd1')
}

$script:Protokoll = @()

function Schritt {
    # Eine Zeile ins Protokoll und auf den Bildschirm.
    param([string]$Text, [string]$Art = 'info')
    $farbe = switch ($Art) { 'ok' {'Green'} 'warn' {'Yellow'} 'fehler' {'Red'} default {'Gray'} }
    Write-Host $Text -ForegroundColor $farbe
    $script:Protokoll += $Text
}

function Verschiebe {
    # Idempotent: liegt die Quelle nicht mehr da, das Ziel aber schon, gilt der
    # Schritt als erledigt. Ein zweiter Lauf aendert dann nichts.
    param(
        [Parameter(Mandatory)][string]$Von,
        [Parameter(Mandatory)][string]$Nach,
        [switch]$DryRun
    )
    $vonDa  = Test-Path $Von
    $nachDa = Test-Path $Nach

    if (-not $vonDa -and $nachDa) { Schritt "  uebersprungen (schon dort): $Nach" 'ok'; return }
    if (-not $vonDa)              { Schritt "  FEHLT: $Von" 'warn'; return }
    if ($nachDa) {
        Schritt "  KOLLISION: $Nach existiert bereits, Quelle bleibt liegen." 'fehler'
        return
    }

    $zielEltern = Split-Path $Nach -Parent
    if ($DryRun) {
        Schritt "  [Probe] $Von  ->  $Nach"
    } else {
        if (-not (Test-Path $zielEltern)) { New-Item -ItemType Directory -Path $zielEltern -Force | Out-Null }
        # -Force: .git und andere versteckte Ordner weigern sich sonst.
        Move-Item -LiteralPath $Von -Destination $Nach -Force
        Schritt "  verschoben: $(Split-Path $Von -Leaf)  ->  $Nach" 'ok'
    }
}

function Sicherungskopie {
    # .bak-JJJJMMTT nach Stufe-1-Regel der Schutzregeln.
    param([Parameter(Mandatory)][string]$Datei, [switch]$DryRun)
    if (-not (Test-Path $Datei)) { Schritt "  FEHLT (keine Sicherung noetig): $Datei" 'warn'; return $null }
    $bak = "$Datei.bak-$(Get-Date -Format 'yyyyMMdd')"
    if (Test-Path $bak) { Schritt "  Sicherung besteht schon: $(Split-Path $bak -Leaf)" 'ok'; return $bak }
    if ($DryRun) { Schritt "  [Probe] Sicherung -> $(Split-Path $bak -Leaf)" }
    else { Copy-Item -LiteralPath $Datei -Destination $bak; Schritt "  Sicherung: $(Split-Path $bak -Leaf)" 'ok' }
    return $bak
}

function Ersetze-InDatei {
    # Gezielte Textersetzung. Gibt die Trefferzahl zurueck, damit die Bilanz
    # eine Zahl nennen kann statt "erledigt".
    param(
        [Parameter(Mandatory)][string]$Datei,
        [Parameter(Mandatory)][hashtable]$Ersetzungen,   # Muster (Regex) -> Ersatz
        [switch]$DryRun
    )
    if (-not (Test-Path $Datei)) { return 0 }
    $inhalt = Get-Content -LiteralPath $Datei -Raw -Encoding UTF8
    if ($null -eq $inhalt) { return 0 }   # leere Datei
    $neu = $inhalt
    $treffer = 0
    foreach ($muster in $Ersetzungen.Keys) {
        $m = [regex]::Matches($neu, $muster)
        if ($m.Count -gt 0) {
            $treffer += $m.Count
            $neu = [regex]::Replace($neu, $muster, $Ersetzungen[$muster])
        }
    }
    if ($treffer -gt 0 -and -not $DryRun) {
        # Ohne BOM schreiben - Obsidian und git sind sonst unnoetig unruhig.
        [System.IO.File]::WriteAllText($Datei, $neu, (New-Object System.Text.UTF8Encoding $false))
    }
    return $treffer
}

function Bilanz {
    # Eine Zeile, die der Mensch (und das Modell) liest. Nichts sonst.
    param([Parameter(Mandatory)][string]$Text, [switch]$Erfolg = $true)
    Write-Host ''
    Write-Host "BILANZ: $Text" -ForegroundColor ($(if ($Erfolg) {'Green'} else {'Red'}))
}

function Protokoll-Schreiben {
    param([Parameter(Mandatory)][string]$Name)
    $ordner = Join-Path $PSScriptRoot 'logs'
    if (-not (Test-Path $ordner)) { New-Item -ItemType Directory -Path $ordner -Force | Out-Null }
    $datei = Join-Path $ordner "$Name-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
    $script:Protokoll | Set-Content -LiteralPath $datei -Encoding UTF8
    return $datei
}
