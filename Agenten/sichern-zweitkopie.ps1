# Zweitkopie des unersetzlichen Teils nach J:\MaxHirn-Zweitkopie
#
# WARUM ES DIESE ZWEITE SICHERUNG GIBT
# G:, H: und I: sind dieselbe physische Platte (Disk 2, Seagate Portable,
# gemessen 23.08.2026 ueber Get-Partition/Get-Disk). Die Hauptsicherung auf G:
# haette durch eine zweite Kopie auf H: also nichts gewonnen - faellt Disk 2
# aus, waeren beide gleichzeitig weg. J: ist die externe Sicherungsplatte.
# Damit liegen Original, Sicherung (Disk 2) und Zweitkopie auf getrennten
# Datentraegern.
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
$ziel   = 'J:\MaxHirn-Zweitkopie'

if (-not (Test-Path 'J:\')) {
  Write-Host 'J: ist nicht erreichbar - Zweitkopie uebersprungen.' -ForegroundColor Red
  exit 2
}

Write-Host '=== Zweitkopie nach J: ===' -ForegroundColor Cyan
$start = Get-Date

# Volle Pfade fuer die Medienordner: ein blosses /XD Software wuerde jeden
# gleichnamigen Unterordner irgendwo im Baum mit ausschliessen. Seit dem echten
# Umzug (07.09.2026) liegen diese Ordner ohnehin auf O:\Archiv und nicht mehr
# unter $quelle; die Liste bleibt als Absicherung stehen. Der unersetzliche
# Archivteil (Dokumente + Bilder) kommt ueber den zweiten Lauf.
$ausserhalb = @(
  (Join-Path $quelle 'MaxHirn\Archiv\Videos'),
  (Join-Path $quelle 'MaxHirn\Archiv\Musik'),
  (Join-Path $quelle 'MaxHirn\Archiv\Software'),
  (Join-Path $quelle 'MaxHirn\Archiv\Posteingang')
)

robocopy $quelle $ziel /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL `
  /XD $ausserhalb Modelle Werkstatt .venv __pycache__ node_modules .git logs pending_messages terminal-output shared_metrics
$code = $LASTEXITCODE

# Zweiter Lauf: der unersetzliche Archivteil liegt seit dem echten Umzug
# (07.09.2026) physisch auf O:\Archiv, ausserhalb von $quelle. Nach J: kommt
# wie bisher nur Dokumente + Bilder - Videos, Musik, Software, Posteingang
# bleiben draussen (Medienlast, weiterhin nur in der Hauptsicherung auf G:).
$archivQuelle = 'O:\Archiv'
$archivZiel   = Join-Path $ziel 'MaxHirn\Archiv'
if (Test-Path $archivQuelle) {
  foreach ($ordner in 'Dokumente','Bilder') {
    robocopy (Join-Path $archivQuelle $ordner) (Join-Path $archivZiel $ordner) `
      /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL
    if ($LASTEXITCODE -gt $code) { $code = $LASTEXITCODE }
  }
} else {
  Write-Host 'O:\Archiv nicht erreichbar - Archivteil der Zweitkopie uebersprungen.' -ForegroundColor Red
  if ($code -lt 4) { $code = 4 }
}

$dauer = (Get-Date) - $start

Write-Host ("Dauer: {0:hh\:mm\:ss}" -f $dauer)
if ($code -lt 8) {
  Write-Host "robocopy-Code $code - erfolgreich." -ForegroundColor Green
} else {
  Write-Host "robocopy-Code $code - FEHLER." -ForegroundColor Red
  exit 1
}
