# Zweitkopie des unersetzlichen Teils nach O:\MaxHirn-Zweitkopie
#
# WARUM ES DIESE ZWEITE SICHERUNG GIBT
# G:, H: und I: sind dieselbe physische Platte (Disk 2, Seagate Portable,
# gemessen 23.08.2026 ueber Get-Partition/Get-Disk). Die Hauptsicherung auf G:
# haette durch eine zweite Kopie auf H: also nichts gewonnen - faellt Disk 2
# aus, waeren beide gleichzeitig weg. O: ist Disk 1 (WD NVMe, intern).
# Damit liegen Original (Disk 0), Sicherung (Disk 2) und Zweitkopie (Disk 1)
# auf drei verschiedenen Datentraegern.
#
# WAS SIE NICHT LEISTET
# Alle drei stecken im selben Rechner. Gegen einen erneuten Netzteilschaden,
# der 2026 schon mehrere Platten gleichzeitig getoetet hat, schuetzt sie nicht.
# Eine Kopie ausser Haus bleibt offen - siehe Wissen/Hardware.md.
#
# WAS MITKOMMT
# Alles ausser der Medienlast: Videos, Musik, Software und Posteingang bleiben
# draussen (zusammen 35,8 GB von 45 GB, gemessen 23.08.2026). Sie liegen
# weiterhin in der Hauptsicherung auf G:. Hier geht es um das, was sich nicht
# wiederbeschaffen laesst und schnell kopiert ist: Wissen, Skills, MCP-Server,
# Handel, Hermes, Routinen und Claude\Dokumente samt Bildern.
#
# Aufruf:  powershell -ExecutionPolicy Bypass -File sichern-zweitkopie.ps1

$ErrorActionPreference = 'Stop'
$quelle = $PSScriptRoot
$ziel   = 'O:\MaxHirn-Zweitkopie'

if (-not (Test-Path 'O:\')) {
  Write-Host 'O: ist nicht erreichbar - Zweitkopie uebersprungen.' -ForegroundColor Red
  exit 2
}

Write-Host '=== Zweitkopie nach O: ===' -ForegroundColor Cyan
$start = Get-Date

# Volle Pfade fuer die Medienordner: ein blosses /XD Software wuerde jeden
# gleichnamigen Unterordner irgendwo im Baum mit ausschliessen.
$ausserhalb = @(
  (Join-Path $quelle 'Claude\Videos'),
  (Join-Path $quelle 'Claude\Musik'),
  (Join-Path $quelle 'Claude\Software'),
  (Join-Path $quelle 'Claude\Posteingang'),
  (Join-Path $quelle 'GitHub')
)

robocopy $quelle $ziel /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL `
  /XD $ausserhalb .venv __pycache__ node_modules .git logs
$code = $LASTEXITCODE
$dauer = (Get-Date) - $start

Write-Host ("Dauer: {0:hh\:mm\:ss}" -f $dauer)
if ($code -lt 8) {
  Write-Host "robocopy-Code $code - erfolgreich." -ForegroundColor Green
} else {
  Write-Host "robocopy-Code $code - FEHLER." -ForegroundColor Red
  exit 1
}
