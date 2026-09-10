<#
    Raeumt die Benutzer-Umgebungsvariablen auf (HKCU\Environment).

    Hintergrund: Das PowerToys-Modul "Environment Variables" hat beim Speichern
    Sicherungskopien mit dem Suffix "_PowerToys_Max 2026" angelegt - teils
    doppelt geschachtelt - und dabei System-Variablen in die Benutzerebene
    kopiert. Stand 24.08.2026: 59 Benutzervariablen, davon 33 Duplikate.

    Zwei davon wirken sich aus:
      TEMP/TMP  zeigen auf C:\WINDOWS\TEMP statt auf den Benutzer-Temp.
      PATHEXT   ueberschreibt die System-Fassung und verliert dabei .PY/.PYW.

    Testlauf (aendert nichts):   .\umgebungsvariablen-aufraeumen.ps1
    Echter Lauf:                 .\umgebungsvariablen-aufraeumen.ps1 -Ausfuehren

    Zurueck geht es mit dem Registry-Export, den der echte Lauf vorher anlegt
    (Doppelklick auf die .reg-Datei), oder mit der Sicherung vom 24.08.2026:
    Hermes\.sicherung\HKCU-Environment.bak-20260824.reg
#>
param([switch]$Ausfuehren)

. (Join-Path (Split-Path $PSScriptRoot -Parent) 'Bus\Ereignis.ps1')      # neu
$marke = Melde-Start -Wer 'routine/umgebungsvariablen-aufraeumen'       # neu
try {                                                                    # neu

$Pfad = 'HKCU:\Environment'

# --- wirkungslose Kopien der System-Umgebung: weg ---------------------------
$SystemKopien = @(
    'windir','USERNAME','PROCESSOR_REVISION','PROCESSOR_LEVEL',
    'PROCESSOR_IDENTIFIER','PROCESSOR_ARCHITECTURE',
    'POWERSHELL_DISTRIBUTION_CHANNEL','OS','NUMBER_OF_PROCESSORS',
    'DriverData','ComSpec','asl.log',
    # PATHEXT: die System-Fassung enthaelt zusaetzlich .PY;.PYW. Weil PATHEXT
    # nicht zusammengesetzt, sondern ersetzt wird, kostet der Benutzereintrag
    # den direkten Aufruf von .py-Dateien.
    'PATHEXT'
)

# --- was bleiben muss -------------------------------------------------------
# ARCHIV_ROOT (seit 07.09.2026): Wurzel der Archivdaten auf O:\Archiv, von den
# Archivwerkzeugen gelesen. Gehoert zur Struktur wie OLLAMA_MODELS/HERMES_HOME.
$Behalten = @(
    'Path','OneDrive','ChocolateyLastPathUpdate','GIT_INSTALL_ROOT',
    'KRAKEN_API_KEY','KRAKEN_API_SECRET','OKX_API_KEY',
    'HERMES_GIT_BASH_PATH','HERMES_HOME','MNEMOVERSE_API_KEY','OLLAMA_MODELS',
    'ARCHIV_ROOT'
)

$u = Get-ItemProperty $Pfad
$alle = $u.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } |
        Select-Object -ExpandProperty Name

$duplikate = @($alle | Where-Object { $_ -match '_PowerToys_Max 2026' })
$kopien    = @($alle | Where-Object { $SystemKopien -contains $_ })

Write-Host ""
Write-Host "Benutzer-Umgebungsvariablen: $($alle.Count)" -ForegroundColor Cyan
Write-Host "  PowerToys-Duplikate zu loeschen : $($duplikate.Count)"
Write-Host "  System-Kopien zu loeschen       : $($kopien.Count)"
Write-Host "  zu korrigieren                  : TEMP, TMP"
Write-Host "  zu ergaenzen                    : OneDriveConsumer"
Write-Host "  unveraendert behalten           : $($Behalten.Count)"
Write-Host "  Endstand                        : $($Behalten.Count + 3)"
Write-Host ""

if (-not $Ausfuehren) {
    Write-Host "TESTLAUF - es wurde nichts geaendert." -ForegroundColor Yellow
    Write-Host "Zu loeschen:" -ForegroundColor Yellow
    ($duplikate + $kopien) | Sort-Object | ForEach-Object { "    $_" }
    Write-Host ""
    Write-Host "Echter Lauf: .\umgebungsvariablen-aufraeumen.ps1 -Ausfuehren"
    Melde-Ende -Marke $marke -Code 0 -Text 'Testlauf'                   # neu
    return
}

# --- Sicherung vor jedem Schreibzugriff ------------------------------------
$stempel = Get-Date -Format 'yyyyMMdd-HHmm'
$ziel = Join-Path $PSScriptRoot "..\Hermes\.sicherung\HKCU-Environment.vor-aufraeumen-$stempel.reg"
$ziel = [System.IO.Path]::GetFullPath($ziel)
reg export "HKCU\Environment" $ziel /y | Out-Null
if (-not (Test-Path $ziel)) { throw "Sicherung fehlgeschlagen - Abbruch, nichts geaendert." }
Write-Host "Sicherung: $ziel" -ForegroundColor Green

$geloescht = 0
foreach ($name in ($duplikate + $kopien)) {
    try {
        Remove-ItemProperty -Path $Pfad -Name $name -Force -ErrorAction Stop
        $geloescht++
    } catch {
        Write-Host "  konnte nicht geloescht werden: $name - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# --- TEMP/TMP auf den Windows-Standard zuruecksetzen ------------------------
foreach ($name in @('TEMP','TMP')) {
    Set-ItemProperty -Path $Pfad -Name $name -Value '%USERPROFILE%\AppData\Local\Temp' -Type ExpandString
}

# --- OneDriveConsumer wiederherstellen (existierte nur noch als Duplikat) ---
if (Test-Path "$env:USERPROFILE\OneDrive") {
    Set-ItemProperty -Path $Pfad -Name 'OneDriveConsumer' -Value "$env:USERPROFILE\OneDrive" -Type String
}

# --- Gegenprobe -------------------------------------------------------------
$nachher = (Get-ItemProperty $Pfad).PSObject.Properties |
           Where-Object { $_.Name -notlike 'PS*' }
Write-Host ""
Write-Host "Geloescht: $geloescht" -ForegroundColor Green
Write-Host "Verbleibend: $($nachher.Count)" -ForegroundColor Green
$nachher | Select-Object Name, Value | Format-Table -AutoSize -Wrap
Write-Host "Laufende Programme sehen die neuen Werte erst nach einer Neuanmeldung." -ForegroundColor Yellow

Melde-Ende -Marke $marke -Code 0                                        # neu
} catch {                                                                # neu
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  throw                                                                 # neu
}                                                                        # neu
