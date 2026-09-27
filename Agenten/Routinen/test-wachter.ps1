# Lotse-Wachter — Testlauf (Scope: lesend, kein Eingriff)

$ErrorActionPreference = 'Stop'
$hier = Split-Path $PSScriptRoot -Parent
$scripts = Join-Path $hier 'Hermes\scripts'
$python = (Get-Command pythonw.exe -CommandType Application -ErrorAction Stop |
    Select-Object -First 1).Source
$skript = Join-Path $scripts 'wachter.py'

if (-not (Test-Path $skript)) {
    throw "Skript fehlt: $skript"
}

Write-Host "Starte Wachter-Test..."
& $python $skript --probe
Write-Host "Exit-Code: $LASTEXITCODE"
