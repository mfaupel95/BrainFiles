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
# Handel, Hermes, Routinen und Archiv\Dokumente samt Bildern.
#
# Aufruf:  powershell -ExecutionPolicy Bypass -File sichern-zweitkopie.ps1

$ErrorActionPreference = 'Stop'
# Eine Ebene ueber diesem Skript: seit Phase 3 liegt es in Agenten\, die Quelle
# ist aber die Wurzel BrainFiles\ (Wissen, Skills, MCP-Server, Handel, Hermes,
# Routinen). Vorher stand hier $PSScriptRoot - das sicherte nach dem Umzug nur
# noch Agenten\.
$quelle = Split-Path $PSScriptRoot -Parent
$ziel   = 'O:\MaxHirn-Zweitkopie'

if (-not (Test-Path 'O:\')) {
  Write-Host 'O: ist nicht erreichbar - Zweitkopie uebersprungen.' -ForegroundColor Red
  exit 2
}

Write-Host '=== Zweitkopie nach O: ===' -ForegroundColor Cyan
$start = Get-Date

# Volle Pfade fuer die Medienordner: ein blosses /XD Software wuerde jeden
# gleichnamigen Unterordner irgendwo im Baum mit ausschliessen. Der Archivordner
# heisst seit der Ordnertrennung vom 30.08.2026 Archiv\ (vorher Claude\).
$ausserhalb = @(
  (Join-Path $quelle 'MaxHirn\Archiv\Videos'),
  (Join-Path $quelle 'MaxHirn\Archiv\Musik'),
  (Join-Path $quelle 'MaxHirn\Archiv\Software'),
  (Join-Path $quelle 'MaxHirn\Archiv\Posteingang')
)

robocopy $quelle $ziel /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL `
  /XD $ausserhalb Modelle Werkstatt .venv __pycache__ node_modules .git logs pending_messages terminal-output shared_metrics
$code = $LASTEXITCODE
$dauer = (Get-Date) - $start

Write-Host ("Dauer: {0:hh\:mm\:ss}" -f $dauer)
if ($code -lt 8) {
  Write-Host "robocopy-Code $code - erfolgreich." -ForegroundColor Green
} else {
  Write-Host "robocopy-Code $code - FEHLER." -ForegroundColor Red
  exit 1
}
