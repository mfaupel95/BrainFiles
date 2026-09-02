<#
.SYNOPSIS
    Entfernt zwei defekte Command-Palette-Erweiterungen (Stand 02.09.2026).

.DESCRIPTION
    Aus dem PowerToys-Report vom 02.09.2026: zwei Fremd-Erweiterungen der
    Command Palette (CmdPal) werfen bei jedem Start Fehler und sollen weg.

      1. 23610AlickolliSoftware.Aria2ExtensionforCommandPal
         Log: "Failed to start extension ... after 34 ms:
         System.ArgumentException: You forgot to start the extension."
      2. JiriPolasek.ColorsforCommandPalette
         Log: FileNotFoundException fuer LocalState\favorites.json und
         history.json.

    Es wird nur das jeweils benannte Paket per Remove-AppxPackage fuer den
    aktuellen Benutzer entfernt. Keine Adminrechte noetig. Andere Erweiterungen
    desselben Herausgebers (JiriPolasek: QR Codes, Unit Converter, Errors)
    bleiben unberuehrt - sie haben eigene PackageFullNames.

    Nicht betroffen: Microsoft.CommandPalette selbst und PowerToys.

.PARAMETER Testlauf
    Zeigt nur an, was entfernt wuerde. Aendert nichts.

.NOTES
    Rueckgaengig: beide Erweiterungen sind Store-Apps und lassen sich jederzeit
    neu installieren -
      winget install "23610AlickolliSoftware.Aria2ExtensionforCommandPal"
      winget install "JiriPolasek.ColorsforCommandPalette"
    oder ueber den Microsoft Store ("... for Command Palette" suchen).

    Hintergrund: Wissen/Hardware.md, Abschnitt "Monitore und PowerToys
    PowerDisplay" (derselbe Report). Offener Punkt zum zweiten Monitor:
    Archiv/TASKS.md, T-023.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\einmalig-20260902-cmdpal-erweiterungen-entfernen.ps1 -Testlauf
    powershell -ExecutionPolicy Bypass -File .\einmalig-20260902-cmdpal-erweiterungen-entfernen.ps1
#>

[CmdletBinding()]
param(
    [switch]$Testlauf
)

$ErrorActionPreference = 'Stop'

$ziele = @(
    '23610AlickolliSoftware.Aria2ExtensionforCommandPal',
    'JiriPolasek.ColorsforCommandPalette'
)

$entfernt = 0
foreach ($name in $ziele) {
    $pkg = Get-AppxPackage -Name $name -ErrorAction SilentlyContinue
    if (-not $pkg) {
        Write-Host "nicht installiert : $name" -ForegroundColor DarkGray
        continue
    }
    foreach ($p in $pkg) {
        if ($Testlauf) {
            Write-Host ("wuerde entfernen : {0}  ({1})" -f $p.Name, $p.PackageFullName) -ForegroundColor Yellow
            continue
        }
        Write-Host ("entferne         : {0}  ({1})" -f $p.Name, $p.PackageFullName)
        Remove-AppxPackage -Package $p.PackageFullName
        $weg = Get-AppxPackage -Name $name -ErrorAction SilentlyContinue
        if ($weg) {
            Write-Host "  -> noch vorhanden, Entfernen fehlgeschlagen" -ForegroundColor Red
        } else {
            Write-Host "  -> entfernt" -ForegroundColor Green
            $entfernt++
        }
    }
}

if ($Testlauf) {
    Write-Host "`nTestlauf - nichts geaendert." -ForegroundColor Cyan
} else {
    Write-Host ("`nFertig. {0} Paket(e) entfernt." -f $entfernt) -ForegroundColor Cyan
    Write-Host "Command Palette neu starten (oder PowerToys), damit die Liste stimmt."
}
