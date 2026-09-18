# Registriert die Aufgabe MaxHirn-MoonDev-GUI (Fenster "MoonDev-GUI").
#
# Einmalig bzw. nach jedem Neuaufsetzen des Rechners. Die Registrierung
# BRAUCHT Erhoehung: ohne sie endet Register-ScheduledTask mit
# "Zugriff verweigert" - passiert am 17.09.2026 um 00:51, der Beleg steht
# in logs/moondev-gui-aufgabe.log. Ein nicht erhoehtes Konto kann das
# nicht umgehen (dieselbe Falle wie bei jeder Register-ScheduledTask-
# Aufgabe im Haus).
# Der Task laeuft danach im eigenen Benutzerkontext (Session-User,
# Interactive, Limited), wie bei der Handelszentrale.
# Solange der Task fehlt, startet der Wrapper ueber die
# Startup-Verknuepfung MoonDev-GUI.vbs - dieser Weg braucht kein Admin.
#
# Aufruf:
# powershell -ExecutionPolicy Bypass -File Agenten\Routinen\moondev-gui-aufgabe.ps1
#
# Diese Datei meldet nicht an den Bus - nur ihr Wrapper moondev-gui.ps1
# tut das (Melde-Start/Melde-Ende als 'routine/moondev-gui').
# Ausloeser Anmeldung +2 Min,
# MultipleInstances IgnoreNew, StartWhenAvailable.
#
# Ergebnis steht logs/moondev-gui-aufgabe.log.

$ErrorActionPreference = 'Stop'
$wurzel  = Split-Path $PSScriptRoot -Parent          # Agenten
$wrapper = Join-Path $PSScriptRoot 'moondev-gui.ps1'
$aufgabe = 'MaxHirn-MoonDev-GUI'
$logs    = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'moondev-gui-aufgabe.log'

function Schreib($text) {
    "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) $text" |
        Add-Content $log -Encoding UTF8
}

Schreib "gestartet als $env:USERNAME"
try {
    if (-not (Test-Path $wrapper)) { throw "Wrapper fehlt: $wrapper" }

    $aktion = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument ('-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "{0}"' -f $wrapper)

    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $trigger.Delay = 'PT2M'

    $einstellungen = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
        -LogonType Interactive -RunLevel Limited

    Register-ScheduledTask -TaskName $aufgabe -Action $aktion -Trigger $trigger `
        -Settings $einstellungen -Principal $principal -Force | Out-Null

    $t = Get-ScheduledTask -TaskName $aufgabe
    $text = "Aufgabe '{0}' eingerichtet: {1} (Ausloeser Anmeldung {2})" -f `
        $aufgabe, $t.State, $trigger.Delay
    Schreib $text
    $text
} catch {
    Schreib "ENDE FEHLER: $_"
    "ENDE FEHLER: $_"
    exit 1
}