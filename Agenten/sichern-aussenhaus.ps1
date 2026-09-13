# Monatliche Off-Site-Sicherung auf externe USB-SSD
#
# Zweck: Schutz gegen simultane Ausfälle aller drei lokalen Platten (C:, G:, O:).
# 
# Aufruf: powershell -ExecutionPolicy Bypass -File sichern-aussenhaus.ps1
#         -Laufwerk E  = kopiert nach E:\BrainFiles-Backup (statt D:)
#         -NurPruefen  = nur Prüfung ohne echte Kopie
#
# Sicherheitswerte:
# - MD5-Hashvergleich statt Dateizahl (filecount kann irreführen bei Duplikaten)
# - Trockenlauf vor Echtkopie (/L)
# - Keine /MIR (löscht nicht, behält alte Versionen bis zum USB-Platz reicht)
# - Atomare Übergabe (rename nach Erfolg)

param(
  [string]$Laufwerk = 'D',
  [switch]$NurPruefen
)

$ErrorActionPreference = 'Stop'
# Pflichtquelle vor Logs, Bereinigung oder Kopieren pruefen.
if (-not (Test-Path -LiteralPath 'O:\Archiv' -PathType Container)) {
  Write-Host 'ARCHIV_SOURCE_MISSING: O:\Archiv fehlt; keine Sicherung gestartet.' -ForegroundColor Red
  exit 2
}
$wurzel = Split-Path $PSScriptRoot -Parent
$zielroot = "${Laufwerk}:\"
$zielAktuell = Join-Path $zielroot "BrainFiles-Backup"
$zielTmp = Join-Path $zielroot "BrainFiles-Backup.tmp"
# Bestehende Teilkopie bereits vor Log-Ueberschreiben und Quellscan schuetzen.
if (Test-Path $zielTmp) {
  Write-Host 'PARTIAL_BACKUP_EXISTS: Teilkopie bleibt erhalten; zuerst Wiederaufnahme planen.' -ForegroundColor Red
  exit 2
}
$logs = Join-Path $PSScriptRoot 'Routinen\logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs "aussenhaus-letzter-lauf.log"

function Melde($msg, $farbe = 'White') {
  Write-Host $msg -ForegroundColor $farbe
  Add-Content $log -Value $msg -Encoding UTF8
}

"=== Lauf $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Set-Content $log -Encoding UTF8

Melde "=== Off-Site USB Backup ===" Cyan
Melde "Quelle: $wurzel"
Melde "Ziel:   $zielAktuell"
Melde "Laufwerk: ${Laufwerk}: (Verfügbarkeit prüfende...)"

# Laufwerksprüfung
if (-not (Test-Path $zielroot)) {
  Melde "FEHLER: Laufwerk ${Laufwerk}: existiert nicht oder ist nicht erreichbar." Red
  exit 2
}

$frei = (Get-PSDrive $Laufwerk -ErrorAction SilentlyContinue).Free
if (-not $frei) {
  Melde "FEHLER: Kann Speicherplatz auf ${Laufwerk}: nicht ermitteln." Red
  exit 2
}

$freiGB = [math]::Round($frei / 1GB, 1)
Melde "Verfügbar: $freiGB GB"

# Größenschätzung (MaxHirn + Agenten versioniert, Modelle/Werkstatt ausgeklammert)
# Mit Redundanz für geplante Aufgaben Logfiles:
$needed = 50  # GB - konservativ (MaxHirn 45 GB + Agenten 4 GB + Archiv-Duplikate)
if ($freiGB -lt $needed) {
  Melde "WARNUNG: Nur $freiGB GB verfügbar, aber $needed GB erwartet." Yellow
}

# Prüfung: Klartext-Zugangsdaten
Melde ""
Melde "=== Scan auf Klartext-Zugangsdaten ===" Cyan
& powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'sichern.ps1') -NurPruefen
if ($LASTEXITCODE -ne 0) {
  Melde "Zugangsdaten-Prüfung hat Fehler gemeldet - backup trotzdem fortgesetzt." Yellow
}

if ($NurPruefen) {
  Melde "NurPruefen=true - Stoppe hier." Green
  exit 0
}

# Trockenlauf
Melde ""
Melde "=== 1) Trockenlauf ===" Cyan
$start = Get-Date

if (Test-Path $zielTmp) {
  Melde "Vorhandene Teilkopie erkannt - Abbruch ohne Aenderung."
  Write-Host 'PARTIAL_BACKUP_EXISTS: Teilkopie bleibt erhalten; kein automatisches Loeschen.' -ForegroundColor Red
  exit 2
}

# Trockenlauf: quelle, archiv-daten
Melde "Quelle..."
robocopy $wurzel $zielTmp /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL /L `
  /XD Modelle Werkstatt .venv __pycache__ node_modules .projectatlas .git logs pending_messages terminal-output shared_metrics
$codeQuelle = $LASTEXITCODE

$archivQuelle = 'O:\Archiv'
$archivZielTmp = Join-Path $zielTmp 'MaxHirn\Archiv'
if (Test-Path $archivQuelle) {
  Melde "Archiv..."
  robocopy $archivQuelle $archivZielTmp /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL /L
  $codeArchiv = $LASTEXITCODE
} else {
  Melde "Archiv nicht erreichbar - übersprungen." Yellow
  $codeArchiv = 8
}

$codeMax = [math]::Max($codeQuelle, $codeArchiv)
if ($codeMax -ge 8) {
  Melde "Trockenlauf-Fehler (Code $codeMax) - Echtkopie abgebrochen." Red
  exit 1
}

Melde "Trockenlauf OK - fahre mit Echtkopie fort." Green

# Echtkopie (erstellt .tmp, dann rename)
Melde ""
Melde "=== 2) Echtkopie ===" Cyan

if (Test-Path $zielTmp) {
  Write-Host 'PARTIAL_BACKUP_EXISTS: Teilkopie bleibt erhalten; kein automatisches Loeschen.' -ForegroundColor Red
  exit 2
}

$start = Get-Date
Melde "Quelle..."
robocopy $wurzel $zielTmp /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL `
  /XD Modelle Werkstatt .venv __pycache__ node_modules .projectatlas .git logs pending_messages terminal-output shared_metrics
$codeQuelle = $LASTEXITCODE

if (Test-Path $archivQuelle) {
  Melde "Archiv..."
  robocopy $archivQuelle $archivZielTmp /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL
  $codeArchiv = $LASTEXITCODE
} else {
  Melde "Archiv nicht erreichbar." Yellow
  $codeArchiv = 8
}

$codeMax = [math]::Max($codeQuelle, $codeArchiv)
$dauer = (Get-Date) - $start

if ($codeMax -ge 8) {
  Melde "Echtkopie-Fehler (Code $codeMax) - $zielTmp bleibt erhalten für Debugging." Red
  exit 1
}

# Atomare Übergabe: rename .tmp zu aktuell
Melde ""
Melde "=== 3) Atomare Uebergabe ===" Cyan
if (Test-Path $zielAktuell) {
  $archivAlt = Join-Path $zielroot ("BrainFiles-Backup.alt-" + (Get-Date -Format yyyyMMdd-HHmm))
  Melde "Vorherige Backup zu $archivAlt umbenennen..."
  Rename-Item $zielAktuell $archivAlt -Force
}

Rename-Item $zielTmp $zielAktuell -Force
Melde "Fertig - neues Backup ist live unter $zielAktuell" Green

# Verifizierung: MD5-Hashes spot-check
Melde ""
Melde "=== 4) Verifizierung (Spot-Check) ===" Cyan
$sample = 5  # prüfe 5 Dateien randomisiert
$quelldateien = @(Get-ChildItem $wurzel -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
  $_.FullName -notmatch '(Modelle|Werkstatt|\.venv|__pycache__|node_modules|\.git|logs)' 
} | Get-Random -Count $sample)

$ok = 0
foreach ($f in $quelldateien) {
  $relPath = $f.FullName.Replace($wurzel, '').TrimStart('\')
  $zielF = Join-Path $zielAktuell $relPath
  
  if (Test-Path $zielF) {
    $h1 = (Get-FileHash $f.FullName -Algorithm MD5).Hash
    $h2 = (Get-FileHash $zielF -Algorithm MD5).Hash
    if ($h1 -eq $h2) {
      $ok++
      Melde "  OK: $relPath" Green
    } else {
      Melde "  FAIL: $relPath - Hashes unterscheiden sich!" Red
      exit 1
    }
  } else {
    Melde "  FAIL: $relPath - nicht im Ziel!" Red
    exit 1
  }
}

Melde "$ok/$sample Dateien verifiziert."

# Zusammenfassung
Melde ""
Melde "=== ERFOLG ===" Green
Melde ("Dauer: {0:hh\:mm\:ss}" -f $dauer)
Melde "Ziel: $zielAktuell"
Melde "Alte Versionen: unter $zielroot als .alt-YYYYMMDD-HHMM"
Melde ""
Melde "Naechste USB-Sicherung: in 4 Wochen. Vor Abziehen: Hardware sicher entfernen"
Melde ""
