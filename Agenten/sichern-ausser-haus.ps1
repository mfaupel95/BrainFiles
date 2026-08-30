# Vollstaendige Kopie fuer ausserhalb des Hauses, Ziel E:\MaxHirn-AusserHaus
#
# WOZU
# Hauptsicherung (G:, Disk 2) und Zweitkopie (O:, Disk 1) stecken beide im
# selben Rechner. Der Netzteilschaden von 2026 hat mehrere Platten
# GLEICHZEITIG getoetet - gegen genau diesen Fall hilft nur eine Kopie, die
# nicht angesteckt ist. Diese hier ist dafuer gedacht: kopieren, abmelden,
# ausser Haus bringen.
#
# ANDERS ALS DIE BEIDEN ANDEREN
# 1. Sie laeuft NICHT als geplante Aufgabe. Eine Kopie, die dauerhaft am
#    Rechner haengt, ist keine Kopie ausser Haus. Aufruf von Hand, wenn die
#    SSD angesteckt ist.
# 2. Sie nimmt ALLES mit (ausser dem aus Git Reproduzierbaren), nicht nur den
#    Kern - Platz ist genug.
#
# EXFAT
# E: ist exFAT. Deshalb /FFT: exFAT speichert Zeitstempel in 2-Sekunden-
# Schritten, NTFS in 100-Nanosekunden-Schritten. Ohne /FFT gilt jede Datei bei
# jedem Lauf als geaendert und es werden jedes Mal 45 GB neu geschrieben.
# /DCOPY:DAT entfaellt bewusst - exFAT kann Ordner-Zeitstempel nur begrenzt.
#
# Aufruf:  powershell -ExecutionPolicy Bypass -File sichern-ausser-haus.ps1
#          -NurPruefen  = nur zeigen, was zu tun waere (robocopy /L)

param([switch]$NurPruefen)

$ErrorActionPreference = 'Stop'
$quelle = $PSScriptRoot
$ziel   = 'E:\MaxHirn-AusserHaus'

if (-not (Test-Path 'E:\')) {
  Write-Host 'E: ist nicht angesteckt - nichts zu tun.' -ForegroundColor Yellow
  exit 2
}

$vol = Get-Volume -DriveLetter E
Write-Host "Ziel: $ziel  ($($vol.FileSystemLabel), $($vol.FileSystem), frei $([math]::Round($vol.SizeRemaining/1GB,1)) GB)" -ForegroundColor Cyan

$modus = if ($NurPruefen) { '/L' } else { '' }
$start = Get-Date

robocopy $quelle $ziel /E /XJ /FFT /R:1 /W:1 /MT:16 /NP /NFL /NDL $modus `
  /XD GitHub .venv __pycache__ node_modules .git logs
$code = $LASTEXITCODE
$dauer = (Get-Date) - $start

Write-Host ("Dauer: {0:hh\:mm\:ss}" -f $dauer)
if ($code -lt 8) {
  Write-Host "robocopy-Code $code - erfolgreich." -ForegroundColor Green
} else {
  Write-Host "robocopy-Code $code - FEHLER." -ForegroundColor Red
  exit 1
}

if ($NurPruefen) { return }

Write-Host ''
Write-Host 'DANACH:' -ForegroundColor Yellow
Write-Host '  1. "Hardware sicher entfernen", bevor die SSD abgezogen wird.'
Write-Host '  2. Die SSD gehoert ausser Haus - nicht im selben Raum wie der Rechner.'
Write-Host '  3. Sie enthaelt Klartext-Zugangsdaten (Wissen\Zugaenge.md,'
Write-Host '     OKX_API.env). Ohne BitLocker To Go liest die jeder, der sie findet.'
