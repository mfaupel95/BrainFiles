<#
.SYNOPSIS
    Fuehrt ein PowerShell-Skript ERHOEHT (UAC) aus und schreibt dessen Ausgabe mit.

.DESCRIPTION
    Ein erhoehtes Fenster schliesst sofort - die Ausgabe des Zielskripts ist sonst
    verloren, und ein stiller Abbruch sieht danach wie Erfolg aus. Dieser Wrapper
    laesst das Zielskript in eine Logdatei schreiben, startet es ueber
    Start-Process -Verb RunAs -Wait (Ausgabeumleitung ist mit RunAs NICHT moeglich,
    deshalb der Umweg) und gibt am Ende den Log-Schwanz auf der normalen Konsole aus.

    Der Exitcode des Starters sagt NUR, dass der UAC-Dialog bestaetigt wurde - das
    Ergebnis muss am ZIEL gemessen werden (Get-CimInstance / Registry / Dienst).

.EXAMPLE
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/erhoeht-starten.ps1 `
        -Skript C:/Users/faupe/Documents/BrainFiles/Agenten/Routinen/einmalig-beispiel.ps1 -Argumente '-Anlegen'
#>
param(
    [Parameter(Mandatory = $true)][string]$Skript,
    [string]$Argumente = '',
    [string]$Log
)

$ErrorActionPreference = 'Stop'

$Skript = (Resolve-Path -LiteralPath $Skript).Path
if (-not $Log) {
    # Achtung: den Schalter LeafBase von Split-Path gibt es erst ab PowerShell 6 -
    # unter 5.1 bricht der Aufruf ab. Deshalb der .NET-Weg.
    $name = [System.IO.Path]::GetFileNameWithoutExtension($Skript)
    $Log = Join-Path (Split-Path -Parent $Skript) ($name + '.log-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
}
if (Test-Path -LiteralPath $Log) { Remove-Item -LiteralPath $Log -Force }

# Inneres Skript: Ausgabe in ALLE Streams umleiten und mitschreiben.
$innen = Join-Path $env:TEMP ('erhoeht-innen-' + [guid]::NewGuid().ToString('N') + '.ps1')
$innenText = @"
`$ErrorActionPreference = 'Continue'
`$log = '$Log'
& '$Skript' $Argumente *>&1 | Tee-Object -FilePath `$log
# NICHT Write-Host: das schreibt an die Host-Konsole des erhoehten Fensters und ist
# mit dem Fenster weg. Alles, was den Lauf ueberleben soll, per Add-Content in die Datei.
Add-Content -LiteralPath `$log -Value ('EXITCODE=' + `$LASTEXITCODE)
"@
[System.IO.File]::WriteAllText($innen, $innenText, (New-Object System.Text.UTF8Encoding($false)))

Write-Host ('erhoeht starten: ' + $Skript + ' ' + $Argumente)
Write-Host ('Log: ' + $Log)
try {
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $innen
    )
} finally {
    Remove-Item -LiteralPath $innen -Force -ErrorAction SilentlyContinue
}

Write-Host '--- Log ---'
if (Test-Path -LiteralPath $Log) {
    Get-Content -LiteralPath $Log | Select-Object -Last 40
    Write-Host ('Logdatei: ' + $Log)
} else {
    Write-Host 'KEIN LOG entstanden - der Lauf wurde vermutlich am UAC-Dialog abgebrochen.'
}
