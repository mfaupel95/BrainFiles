# Registriert die Aufgabe MaxHirn-Herzschlag-Wache (alle 10 Minuten).
#
# Einmalig bzw. nach jedem Neuaufsetzen des Rechners. ADMINISTRATOR NOETIG:
# die Aufgabenplanung laesst neue Aufgaben nur erhoeht anlegen. Die Aufgabe
# selbst laeuft danach als der angemeldete Benutzer (Interactive, Limited).
#
# Aufruf (erhoehte PowerShell):
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\herzschlag-wache-aufgabe.ps1
#
# Ausloeser: Anmeldung +3 Min, danach alle 10 Minuten. MultipleInstances
# IgnoreNew, StartWhenAvailable. Wichtig: die Wache faellt mit diesem Rechner
# aus - ein Beobachter auf anderer Hardware ersetzt sie nicht.
# Ergebnis steht in logs\herzschlag-wache-aufgabe.log.

$ErrorActionPreference = 'Stop'
$wrapper = Join-Path $PSScriptRoot 'herzschlag-wache.ps1'
$aufgabe = 'MaxHirn-Herzschlag-Wache'
$logs = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'herzschlag-wache-aufgabe.log'

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

  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(3) `
    -RepetitionInterval (New-TimeSpan -Minutes 10)

  $einstellungen = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

  $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType Interactive -RunLevel Limited

  Register-ScheduledTask -TaskName $aufgabe -Action $aktion -Trigger $trigger `
    -Settings $einstellungen -Principal $principal -Force | Out-Null

  $t = Get-ScheduledTask -TaskName $aufgabe
  $text = "Aufgabe '{0}' eingerichtet: {1} (alle 10 Minuten)" -f $aufgabe, $t.State
  Schreib $text
  $text
} catch {
  Schreib "ENDE FEHLER: $_"
  "ENDE FEHLER: $_"
  exit 1
}
