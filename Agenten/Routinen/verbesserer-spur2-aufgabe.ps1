# Registriert die Aufgabe MaxHirn-Verbesserer-Spur2 (woechentlicher Lauf der
# XPERP-Optimierungsschleife, Routine verbesserer-spur2.ps1).
#
# Einmalig bzw. nach jedem Neuaufsetzen des Rechners. ADMINISTRATOR NOETIG:
# die Aufgabenplanung laesst neue Aufgaben nur erhoeht anlegen (siehe
# handelszentrale-aufgabe.ps1). Die Aufgabe selbst laeuft danach als der
# angemeldete Benutzer (Interactive, Limited).
#
# Aufruf (erhoehte PowerShell, aus der Repo-Wurzel):
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\verbesserer-spur2-aufgabe.ps1
#
# Zeitpunkt: sonntags 04:00, NACH dem Wachen-Abgleich (handel-wachen.ps1) und
# getrennt von Spur 1. Der Lauf erzeugt nur einen Vorschlag in
# verbesserer\berichte\ - angewandt wird er erst per /ja im Dauerlauf.
# StartWhenAvailable holt einen verpassten Lauf nach, MultipleInstances
# IgnoreNew verhindert zwei Laeufe gleichzeitig, das Zeitlimit ist grosszuegig
# (gemessen: ein Lauf rund 7 Minuten, mit Kerzenabruf laenger).
#
# Ergebnis steht in logs\verbesserer-spur2-aufgabe.log: der erhoehte Lauf hat
# kein Fenster, in dem man es lesen koennte.

$ErrorActionPreference = 'Stop'
$wrapper = Join-Path $PSScriptRoot 'verbesserer-spur2.ps1'
$aufgabe = 'MaxHirn-Verbesserer-Spur2'
$logs = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'verbesserer-spur2-aufgabe.log'

function Schreib($text) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $text" |
    Add-Content $log -Encoding UTF8
}

$binAdmin = ([Security.Principal.WindowsPrincipal] `
  [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Schreib ("gestartet als {0}, erhoeht: {1}" -f $env:USERNAME, $binAdmin)
if (-not $binAdmin) {
  Schreib "ABBRUCH: nicht erhoeht - Register-ScheduledTask wird abgelehnt."
  "ABBRUCH: bitte in einer erhoehten PowerShell starten."
  exit 1
}

try {
  if (-not (Test-Path $wrapper)) { throw "Wrapper fehlt: $wrapper" }

  $aktion = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "{0}"' -f $wrapper)

  $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '04:00'

  $einstellungen = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

  $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType Interactive -RunLevel Limited

  Register-ScheduledTask -TaskName $aufgabe -Action $aktion -Trigger $trigger `
    -Settings $einstellungen -Principal $principal -Force | Out-Null

  $t = Get-ScheduledTask -TaskName $aufgabe
  $info = Get-ScheduledTaskInfo -TaskName $aufgabe
  $text = "Aufgabe '{0}' eingerichtet: {1}, naechster Lauf {2}" -f `
            $aufgabe, $t.State, $info.NextRunTime
  Schreib $text
  $text
} catch {
  Schreib "ENDE FEHLER: $_"
  "ENDE FEHLER: $_"
  exit 1
}
