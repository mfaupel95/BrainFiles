# Vollstaendige Kopie fuer ausserhalb des Hauses, Ziel Q:\MaxHirn-AusserHaus
#
# WOZU
# Hauptsicherung (G:, Disk 2) und Zweitkopie (O:, Disk 1) stecken beide im
# selben Rechner. Der Netzteilschaden von 2026 hat mehrere Platten
# GLEICHZEITIG getoetet - gegen genau diesen Fall hilft nur eine Kopie, die
# nicht angesteckt ist. Diese hier ist dafuer gedacht: kopieren, abmelden,
# ausser Haus bringen.
#
# ANDERS ALS DIE BEIDEN ANDEREN
# 1. Sie wird seit 29.09.2026 taeglich um 21:30 von der Aufgabe
#    'MaxHirn-Ausserhaus-Kopie' (Routinen/ausserhaus-kopie.ps1) erneuert,
#    SOLANGE die SSD angesteckt ist; sonst endet der Lauf nach Sekunden mit
#    Exitcode 2 (uebersprungen, kein Fehlschlag). Das eigentliche "ausser Haus"
#    bleibt Handarbeit: abmelden und die Platte woanders hinbringen - eine
#    Kopie, die dauerhaft am Rechner haengt, ist keine Kopie ausser Haus.
# 2. Sie nimmt ALLES mit (ausser dem aus Git Reproduzierbaren), nicht nur den
#    Kern - Platz ist genug.
#
# EXFAT
# Q: ist exFAT (SanDisk Portable SSD, Disk 3 - eine eigene physische Platte,
# nicht G:, J: oder O:). Deshalb /FFT: exFAT speichert Zeitstempel in 2-Sekunden-
# Schritten, NTFS in 100-Nanosekunden-Schritten. Ohne /FFT gilt jede Datei bei
# jedem Lauf als geaendert und es werden jedes Mal 45 GB neu geschrieben.
# /DCOPY:DAT entfaellt bewusst - exFAT kann Ordner-Zeitstempel nur begrenzt.
#
# Aufruf:  powershell -ExecutionPolicy Bypass -File sichern-ausser-haus.ps1
#          -NurPruefen  = nur zeigen, was zu tun waere (robocopy /L)

param([switch]$NurPruefen)

$ErrorActionPreference = 'Stop'
# Pflichtquelle vor jedem Schreibzugriff pruefen.
if (-not (Test-Path -LiteralPath 'O:\Archiv' -PathType Container)) {
  Write-Host 'ARCHIV_SOURCE_MISSING: O:\Archiv fehlt; keine Sicherung gestartet.' -ForegroundColor Red
  exit 2
}
# Eine Ebene ueber diesem Skript (Agenten\ -> BrainFiles\). Vorher $PSScriptRoot,
# das sicherte nach Phase 3 nur noch Agenten\.
$quelle = Split-Path $PSScriptRoot -Parent
$ziel   = 'Q:\MaxHirn-AusserHaus'

if (-not (Test-Path 'Q:\')) {
  Write-Host 'Q: ist nicht angesteckt - nichts zu tun.' -ForegroundColor Yellow
  exit 2
}

$vol = Get-Volume -DriveLetter Q
Write-Host "Ziel: $ziel  ($($vol.FileSystemLabel), $($vol.FileSystem), frei $([math]::Round($vol.SizeRemaining/1GB,1)) GB)" -ForegroundColor Cyan

$modus = if ($NurPruefen) { '/L' } else { '' }
$start = Get-Date

# Zwei Pfade sind im Betrieb fluechtig und ergaben am 30.09.2026 robocopy-Code 11:
# `Agenten\Hermes\cache` - Wegwerfbereich: uv-Bau-Cache (die .whl ist waehrend
#               eines Baus GESPERRT, E5), die Scratch-Ablage (TMPDIR, wird nach
#               24 h geleert) und ein Browser-Profil, dessen `Network\Cookies`
#               ein LAUFENDER Prozess haelt (E32) - dazu ein Rest des
#               abgebrochenen Update-Versuchs (.previous-python-*, E3: Pfad
#               nicht gefunden, ~150 Dateien). Alles wiederherstellbar bzw.
#               wandert taeglich durch; in eine Sicherung gehoert es nicht.
# `cron\output` - Cron-Berichte; sie entstehen und verschwinden WAEHREND des
#               Laufs (E2, Datei nicht gefunden). Berichte, keine Daten.
$fluechtig = @(
  (Join-Path $quelle 'Agenten\Hermes\cache'),
  (Join-Path $quelle 'Agenten\Hermes\cron\output'),
  # 21.10.2026: Chrome-Profil, `Network\Cookies` haelt ein LAUFENDER Prozess (E32, Code 11 am 19./20.10.)
  (Join-Path $quelle 'Agenten\Hermes\browser-profile')
)
# 21.10.2026: `.leases`-Marker laufender Hermes-Prozesse (E2, Code 11 am 21.10. 21:59) - nach NAMEN
# ausgeschlossen wie in sichern.ps1/sichern-zweitkopie.ps1, darum unten in /XD ergaenzt.

# Derselbe gesperrte Waisen-Rest wie in sichern.ps1 (03.10.2026):
# state-snapshots\.20260930-204617-pre-update.48588.partial ist leer und
# GESPERRT (icacls schlaegt selbst fehl). Der Lauf vom 02.10.2026 21:37
# endete mit FEHLER 6 / Code 11 bei 0 fehlenden Dateien. Wildcards sind in
# /XD verboten ('Ungueltiger Parameter #11', Code 16, ohne Kopieren), also
# wird der Pfad aufgeloest.
$waisen = @()
# 21.10.2026: zusaetzlich `profiles\*\cache\terminal` - die hermes-snap-*.sh entstehen und
# verschwinden im Betrieb (E2, Code 11 am 20.10.). Wildcard darum hier aufgeloest, nicht in /XD.
foreach ($muster in @('Agenten\Hermes\state-snapshots\.*.partial',
                      'Agenten\Hermes\profiles\*\cache\terminal')) {
  $waisen += @(Get-ChildItem -Path (Join-Path $quelle $muster) -Directory `
                 -Force -ErrorAction SilentlyContinue |
               ForEach-Object { $_.FullName })
}
if ($waisen.Count -gt 0) {
  Write-Host ("Gesperrte Update-Reste ausgeschlossen: {0}" -f $waisen.Count)
}

robocopy $quelle $ziel /E /XJ /FFT /R:1 /W:1 /MT:16 /NP /NFL /NDL $modus `
  /XD Modelle Werkstatt .venv __pycache__ node_modules .projectatlas .git logs pending_messages terminal-output shared_metrics .leases $fluechtig $waisen /XF *.pid *.db-shm *.db-wal 'Zugaenge.md' *.env auth.json OKX_API.env nous_auth.json   # 08.10.2026: Klartext-Zugangsdaten raus - sie liegen verschluesselt in Agenten\Hermes\secrets\secrets-<datum>.7z (secrets-archivieren.ps1, AES-256). Zugaenge.md war hier als EINZIGES Skript noch nicht ausgeschlossen. *.pid sind fluechtige Sperrdateien (skillsbot.pid haelt der Bus); *.db-shm/*.db-wal sind die Begleitdateien einer LAUFENDEN SQLite-Datenbank (Agenten\Hermes\shared-state.db) - sie entstehen und verschwinden im Betrieb und eine Rohkopie waere ohnehin kein gueltiger Datenbankstand. robocopy meldete fuer beide Klassen Code 11; dasselbe gilt fuer die zwei Pfade in $fluechtig. $waisen = gesperrte Update-Reste als aufgeloeste Vollpfade
$code = $LASTEXITCODE

# Die Archivdaten liegen seit dem 07.09.2026 auf O:\Archiv, nicht mehr unter
# $quelle. Ohne diesen zweiten Lauf fehlt der Ausser-Haus-Kopie das komplette
# 45-GB-Archiv - genau das, wofuer diese Sicherung gedacht ist.
if (Test-Path 'O:\Archiv') {
  robocopy 'O:\Archiv' (Join-Path $ziel 'MaxHirn\Archiv') /E /XJ /FFT /R:1 /W:1 /MT:16 /NP /NFL /NDL $modus
  if ($LASTEXITCODE -gt $code) { $code = $LASTEXITCODE }
} else {
  Write-Host 'O:\Archiv nicht erreichbar - der Archivteil FEHLT in dieser Kopie.' -ForegroundColor Red
  if ($code -lt 8) { $code = 8 }
}

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
Write-Host '     Wissen\OKX_API.env). Ohne BitLocker To Go liest die jeder, der sie findet.'
