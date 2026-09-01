<#
.SYNOPSIS
    Drei Eingriffe gegen die Abstuerze ohne Bluescreen (Stand 28.08.2026).

.DESCRIPTION
    1. Entfernt g:\pagefile.sys aus PagingFiles. G: ist die Seagate Portable
       (USB); eine Auslagerungsdatei gehoert dort nicht hin. C: und O: bleiben.
       Wirkt erst nach einem Neustart.
    2. Setzt den Dienst WSearch auf Deaktiviert. Er stuerzt seit 24.08. rund
       1.200-mal taeglich ab und ueberschreibt dabei das Systemprotokoll.
    3. Schaltet den S3-Standby im Netzbetrieb ab (Zeitwert 0 = nie).
       Vorheriger Wert: 2700 Sekunden = 45 Minuten.

    Jeder Schritt meldet, was er tut, und prueft danach das Ergebnis.
    Hintergrund: Wissen/Hardware.md, Abschnitt "Stromausfaelle ohne Bluescreen".
    Offene Punkte: Archiv/TASKS.md, T-002 bis T-004.

.PARAMETER Rueckgaengig
    Stellt alle drei Aenderungen auf den Stand vom 28.08.2026 zurueck.

.PARAMETER Testlauf
    Zeigt nur an, was geschehen wuerde. Aendert nichts.

.PARAMETER StandbyBehalten
    Laesst Schritt 3 aus. Empfohlen fuer den ersten Durchgang: Nur wenn der
    Standby weiter benutzt wird, zeigt sich, ob Schritt 1 die Abstuerze
    wirklich behoben hat. Schaltet man den Standby gleich mit ab, faellt die
    Bedingung weg, unter der sie auftreten - dann bleibt ungeklaert, welcher
    der beiden Eingriffe gewirkt hat.

.EXAMPLE
    Rechtsklick auf die Datei > "Mit PowerShell ausfuehren"
    oder in einer Administrator-PowerShell:
        .\einmalig-20260828-absturzbehebung.ps1 -Testlauf
        .\einmalig-20260828-absturzbehebung.ps1 -StandbyBehalten
        .\einmalig-20260828-absturzbehebung.ps1
        .\einmalig-20260828-absturzbehebung.ps1 -Rueckgaengig
#>

[CmdletBinding()]
param(
    [switch]$Rueckgaengig,
    [switch]$Testlauf,
    [switch]$StandbyBehalten
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------- Erhoehung
$istAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $istAdmin) {
    Write-Host "Adminrechte noetig - starte neu mit Rechteerhoehung ..." -ForegroundColor Yellow
    $argumente = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-NoExit', '-File', "`"$PSCommandPath`""
    )
    if ($Rueckgaengig)     { $argumente += '-Rueckgaengig' }
    if ($Testlauf)         { $argumente += '-Testlauf' }
    if ($StandbyBehalten)  { $argumente += '-StandbyBehalten' }
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $argumente
    return
}

$MM = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management'
$SICHERUNG = Join-Path $PSScriptRoot 'sicherungen\MemoryManagement-20260828.reg'

function Schritt($nummer, $text) {
    Write-Host ""
    Write-Host "=== $nummer) $text ===" -ForegroundColor Cyan
}

Write-Host ""
if ($Testlauf) {
    Write-Host "TESTLAUF - es wird nichts geaendert." -ForegroundColor Yellow
}
if ($Rueckgaengig) {
    Write-Host "RUECKGAENGIG - Stand vom 28.08.2026 wird wiederhergestellt." -ForegroundColor Yellow
}

# ------------------------------------------------- 1) Auslagerungsdatei g:
Schritt 1 'Auslagerungsdatei auf der USB-Platte'

$vorher = (Get-ItemProperty -Path $MM -Name PagingFiles).PagingFiles
Write-Host "Jetzt eingetragen:"
$vorher | ForEach-Object { Write-Host "    $_" }

if ($Rueckgaengig) {
    $ziel = @(
        'c:\pagefile.sys 0 0'
        'g:\pagefile.sys 4096 16384'
        'o:\pagefile.sys 4096 16384'
    )
} else {
    $ziel = @($vorher | Where-Object { $_ -notmatch '^\s*g:' })
}

if (@(Compare-Object $vorher $ziel -SyncWindow 0).Count -eq 0) {
    Write-Host "Bereits im Sollzustand - nichts zu tun." -ForegroundColor Green
} elseif ($Testlauf) {
    Write-Host "Wuerde setzen auf:" -ForegroundColor Yellow
    $ziel | ForEach-Object { Write-Host "    $_" }
} else {
    Set-ItemProperty -Path $MM -Name PagingFiles -Value $ziel -Type MultiString
    $nachher = (Get-ItemProperty -Path $MM -Name PagingFiles).PagingFiles
    Write-Host "Jetzt gesetzt:" -ForegroundColor Green
    $nachher | ForEach-Object { Write-Host "    $_" }
    if ($nachher -match '^\s*g:') {
        Write-Host "ACHTUNG: g: steht immer noch drin!" -ForegroundColor Red
    }
    Write-Host "Wirkt erst nach einem Neustart." -ForegroundColor Yellow
    Write-Host "Zuruecksetzen notfalls mit:  reg import `"$SICHERUNG`""
}

# ------------------------------------------------------- 2) Windows Search
Schritt 2 'Windows Search (WSearch)'

$dienst = Get-Service WSearch -ErrorAction SilentlyContinue
if (-not $dienst) {
    Write-Host "Dienst WSearch nicht vorhanden - uebersprungen." -ForegroundColor Yellow
} else {
    $startArt = (Get-CimInstance Win32_Service -Filter "Name='WSearch'").StartMode
    Write-Host "Jetzt: StartMode=$startArt, Status=$($dienst.Status)"

    $zielArt = if ($Rueckgaengig) { 'Automatic' } else { 'Disabled' }

    if ($Testlauf) {
        Write-Host "Wuerde StartupType auf $zielArt setzen." -ForegroundColor Yellow
    } else {
        Set-Service WSearch -StartupType $zielArt
        if (-not $Rueckgaengig) {
            try { Stop-Service WSearch -Force -ErrorAction Stop } catch { }
        }
        $neu = (Get-CimInstance Win32_Service -Filter "Name='WSearch'").StartMode
        Write-Host "Jetzt: StartMode=$neu" -ForegroundColor Green
    }
}

# --------------------------------------------------------------- 3) Standby
Schritt 3 'S3-Standby im Netzbetrieb'

if ($StandbyBehalten -and -not $Rueckgaengig) {
    Write-Host "Uebersprungen (-StandbyBehalten)." -ForegroundColor Yellow
    Write-Host "Der Standby bleibt aktiv - nur so zeigt sich, ob Schritt 1"
    Write-Host "die Abstuerze wirklich behoben hat."
    Write-Host ""
    Write-Host "=== Fertig ===" -ForegroundColor Cyan
    Write-Host "Schritt 1 wirkt erst nach einem Neustart."
    Write-Host "Danach pruefen, ob auf G: noch eine pagefile.sys liegt:"
    Write-Host "    Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize"
    Write-Host ""
    return
}

$schema = ((powercfg /getactivescheme) |
    Select-String -Pattern '([0-9a-fA-F-]{36})').Matches[0].Value
$abfrage = powercfg /query $schema SUB_SLEEP STANDBYIDLE | Out-String
$hex = ([regex]'Index der aktuellen Wechselstromeinstellung:\s*(0x[0-9a-fA-F]+)'
    ).Match($abfrage).Groups[1].Value
$sekunden = if ($hex) { [Convert]::ToInt32($hex, 16) } else { -1 }
Write-Host ("Jetzt: {0} Sekunden ({1})" -f $sekunden,
    $(if ($sekunden -eq 0) { 'nie' } else { "$([math]::Round($sekunden/60)) Minuten" }))

$zielMinuten = if ($Rueckgaengig) { 45 } else { 0 }

if ($Testlauf) {
    Write-Host "Wuerde standby-timeout-ac auf $zielMinuten setzen." -ForegroundColor Yellow
} else {
    powercfg /change standby-timeout-ac $zielMinuten | Out-Null
    $abfrage2 = powercfg /query $schema SUB_SLEEP STANDBYIDLE | Out-String
    $hex2 = ([regex]'Index der aktuellen Wechselstromeinstellung:\s*(0x[0-9a-fA-F]+)'
        ).Match($abfrage2).Groups[1].Value
    $sek2 = if ($hex2) { [Convert]::ToInt32($hex2, 16) } else { -1 }
    Write-Host ("Jetzt: {0} Sekunden ({1})" -f $sek2,
        $(if ($sek2 -eq 0) { 'nie' } else { "$([math]::Round($sek2/60)) Minuten" })
    ) -ForegroundColor Green
}

# ------------------------------------------------------------------ Abschluss
Write-Host ""
Write-Host "=== Fertig ===" -ForegroundColor Cyan
if (-not $Testlauf -and -not $Rueckgaengig) {
    Write-Host "Schritt 1 wirkt erst nach einem Neustart."
    Write-Host "Danach pruefen, ob auf G: noch eine pagefile.sys liegt:"
    Write-Host "    Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize"
    Write-Host ""
    Write-Host "Beobachten: Bleiben die Kernel-Power-41-Ereignisse jetzt aus?"
    Write-Host "    Get-WinEvent -FilterHashtable @{LogName='System'; Id=41} -MaxEvents 5 |"
    Write-Host "      Select-Object TimeCreated"
}
Write-Host ""
