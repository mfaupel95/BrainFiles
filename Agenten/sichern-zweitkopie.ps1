# Zweitkopie des unersetzlichen Teils nach O:\MaxHirn-Zweitkopie
#
# WARUM ES DIESE ZWEITE SICHERUNG GIBT
# G:, H: und I: sind dieselbe physische Platte (Disk 2, Seagate Portable,
# gemessen 23.08.2026 ueber Get-Partition/Get-Disk). Die Hauptsicherung auf G:
# haette durch eine zweite Kopie auf H: also nichts gewonnen - faellt Disk 2
# aus, waeren beide gleichzeitig weg.
#
# ZIEL SEIT 29.09.2026: O: (Disk 1, WDC NVMe) statt J:.
# Grund: J: (Disk 4, WD My Book) wird seit dem 28.09. wiederholt als
# schreibgeschuetzt eingebunden (NTFS-Event 98, zuletzt 29.09. 21:06), hat 479
# unkorrigierte Lesefehler und ist so langsam, dass ein rekursives Auflisten
# 300 s ueberschreitet. Die Laeufe vom 28.09. (Code 1) und 29.09. (0xC000013A)
# brachen ab. G: waere die falsche Wahl - G:, H: und I: sind dieselbe Platte
# (Disk 2) wie die Hauptsicherung.
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
# Pflichtquelle vor jedem Schreibzugriff pruefen.
if (-not (Test-Path -LiteralPath 'O:\Archiv' -PathType Container)) {
  Write-Host 'ARCHIV_SOURCE_MISSING: O:\Archiv fehlt; keine Sicherung gestartet.' -ForegroundColor Red
  exit 2
}
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
# gleichnamigen Unterordner irgendwo im Baum mit ausschliessen. Seit dem echten
# Umzug (07.09.2026) liegen diese Ordner ohnehin auf O:\Archiv und nicht mehr
# unter $quelle; die Liste bleibt als Absicherung stehen. Der unersetzliche
# Archivteil (Dokumente + Bilder) kommt ueber den zweiten Lauf.
$ausserhalb = @(
  (Join-Path $quelle 'MaxHirn\Archiv\Videos'),
  (Join-Path $quelle 'MaxHirn\Archiv\Musik'),
  (Join-Path $quelle 'MaxHirn\Archiv\Software'),
  (Join-Path $quelle 'MaxHirn\Archiv\Posteingang'),
  # HERMES-CACHE: hier liegt der uv-Build-Cache, dessen editable-Wheel ein
  # laufender Hermes-/uv-Prozess sperrt. Ein blosses /XD cache wuerde jeden
  # gleichnamigen Ordner mit ausschliessen, darum der volle Pfad. Folge ohne
  # Ausschluss: robocopy FEHLER 5 auf hermes_agent-0.0.0-0.editable-py3-none-any.whl,
  # robocopy-Code 11 und Exitcode 1 (Lauf 28.09.2026 21:02) - die Aufgabe
  # MaxHirn-Zweitkopie stand deshalb taeglich auf Code 1, ohne dass eine Datei
  # fehlte (2936 uebersprungen, 0 Fehler im Zaehler). Der Cache ist neu baubar
  # und gehoert nicht in eine Sicherung; die Dateien des Hermes-Baums
  # (config.yaml, profiles, skills, SOUL.md) werden weiter mitgesichert.
  (Join-Path $quelle 'Agenten\Hermes\cache'),
  # 08.10.2026 angeglichen an sichern.ps1: Zweitkopie-Agenten\ hatte 49 GB statt
  # ~4 GB und O: lief voll (Lauf 07.10. 21:00: FEHLER 112, kein Speicherplatz).
  # Neu herunterladbar bzw. neu baubar, nicht unersetzlich.
  (Join-Path $quelle 'Agenten\Hermes\cron\output'),
  (Join-Path $quelle 'Agenten\Hermes\models'),
  (Join-Path $quelle 'Agenten\Hermes\runtimes'),
  (Join-Path $quelle 'Agenten\Handel\nautilus-rust\target'),
  (Join-Path $quelle 'Agenten\_Backups'),
  (Join-Path $quelle 'MaxHirn\_zu_loeschen')
)

# Derselbe gesperrte Waisen-Rest wie in sichern.ps1 (03.10.2026):
# state-snapshots\.20260930-204617-pre-update.48588.partial ist leer und
# gesperrt (icacls schlaegt selbst fehl). robocopy meldete beim Lauf vom
# 02.10.2026 FEHLER 5 auf dem ZIELverzeichnis O: (der Ordner war schon
# dorthin kopiert worden und ist dort ebenso gesperrt) und endete mit
# Code 11 - bei 0 fehlenden Dateien. Wildcards sind in /XD verboten
# ('Ungueltiger Parameter #11', Code 16, ohne Kopieren), darum aufgeloest.
$waisen = @()
# 21.10.2026: zusaetzlich `profiles\*\cache\terminal` - die hermes-snap-*.sh(.tmp.*) entstehen und
# verschwinden im Betrieb (E2, Code 11 am 21.10. 21:00). Gleiche Loesung wie in sichern-ausser-haus.ps1.
foreach ($muster in @('Agenten\Hermes\state-snapshots\.*.partial',
                      'Agenten\Hermes\profiles\*\cache\terminal')) {
  $waisen += @(Get-ChildItem -Path (Join-Path $quelle $muster) -Directory `
                 -Force -ErrorAction SilentlyContinue |
               ForEach-Object { $_.FullName })
}
if ($waisen.Count -gt 0) {
  Write-Host ("Gesperrte Update-Reste ausgeschlossen: {0}" -f $waisen.Count)
}

robocopy $quelle $ziel /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL `
  /XD $ausserhalb Modelle Werkstatt .venv __pycache__ node_modules .projectatlas .git logs pending_messages terminal-output shared_metrics browser-profile .leases $waisen `
  /XF *.pid *.db-wal *.db-shm *.lock 'Zugaenge.md' *.env auth.json OKX_API.env nous_auth.json   # 08.10.2026: Klartext-Zugangsdaten raus - sie liegen verschluesselt in Agenten\Hermes\secrets\secrets-<datum>.7z (secrets-archivieren.ps1). fluechtige Dateien (Sperrdateien, SQLite-WAL/-SHM): robocopy kann sie nicht lesen und meldet sonst Code 11, obwohl nichts fehlt (skillsbot.pid haelt den Bus); robocopy kann sie nicht lesen und meldet sonst Code 11. $waisen = gesperrte Update-Reste als aufgeloeste Vollpfade. 'Zugaenge.md' ist seit 07.10.2026 ausgeschlossen (derselbe Grund wie in sichern.ps1): die Schluesselablage lag nach jedem Lauf im Klartext auf O:.
$code = $LASTEXITCODE

# Zweiter Lauf: der unersetzliche Archivteil liegt seit dem echten Umzug
# (07.09.2026) physisch auf O:\Archiv, ausserhalb von $quelle. Nach O: kommt
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
