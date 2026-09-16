# Registriert die Aufgabe MaxHirn-Handelszentrale (Fenster "Handelszentrale").
#
# Einmalig bzw. nach jedem Neuaufsetzen des Rechners. ADMINISTRATOR NOETIG:
# die Aufgabenplanung laesst neue Aufgaben nur erhoeht anlegen ("Zugriff
# verweigert" sonst, geprueft am 13.09.2026). Die Aufgabe selbst laeuft
# danach als der angemeldete Benutzer (Interactive, Limited), damit das
# Fenster in der eigenen Sitzung erscheint - so wie MaxHirn-OmniRoute.
#
# Aufruf (erhoehte PowerShell):
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\handelszentrale-aufgabe.ps1
#
# Die Aufgabe ist KEINE geplante Routine im Sinne des Busses (sie meldet
# nicht selbst) - sie legt die Aufgabe an, die den Wrapper
# handelszentrale.ps1 aufruft. Ausloeser Anmeldung +2 Min,
# MultipleInstances IgnoreNew, StartWhenAvailable, damit ein verpasster
# Anmeldezeitpunkt nachgeholt wird.
#
# Ergebnis steht in logs/handelszentrale-aufgabe.log: der erhoehte Lauf hat
# kein Fenster, in dem man es lesen koennte.

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent          # Agenten
$wrapper = Join-Path $PSScriptRoot 'handelszentrale.ps1'
$aufgabe = 'MaxHirn-Handelszentrale'
$logs = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'handelszentrale-aufgabe.log'

function Schreib($text) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $text" |
    Add-Content $log -Encoding UTF8
}

# Startspur VOR jeder Pruefung: ein erhoeht gestartetes Skript, das gleich
# wieder zuklappt, ist sonst nicht mehr zu befragen - ein Klick auf "Ja" ohne
# Wirkung sieht dann wie ein Klick auf "Nein" aus.
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
  $text = "Aufgabe '{0}' eingerichtet: {1} (Ausloeser Anmeldung + {2})" -f `
            $aufgabe, $t.State, $trigger.Delay
  Schreib $text
  $text
} catch {
  Schreib "ENDE FEHLER: $_"
  "ENDE FEHLER: $_"
  exit 1
}
