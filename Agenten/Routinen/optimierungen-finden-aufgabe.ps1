# Registriert die Aufgabe MaxHirn-Optimierungen-Finden (montags 09:45).
#
# Einmalig bzw. nach jedem Neuaufsetzen des Rechners. Fuer neue Aufgaben in
# der Aufgabenplanung ist in der Regel eine erhoehte PowerShell noetig
# ("Zugriff verweigert" sonst, siehe handelszentrale-aufgabe.ps1). Die
# Aufgabe selbst laeuft danach als der angemeldete Benutzer (Interactive,
# Limited) - so wie die uebrigen MaxHirn-Routinen.
#
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\optimierungen-finden-aufgabe.ps1
#
# StartWhenAvailable ist gesetzt: die Kernel-Power-41-Abschaltungen (siehe
# Wissen\Hardware.md) lassen einen verpassten Montagstermin sonst ersatzlos
# ausfallen.
#
# Ergebnis steht in logs/optimierungen-finden-aufgabe.log - ein erhoeht
# gestartetes Skript hat kein Fenster, in dem man es lesen koennte.

$ErrorActionPreference = 'Stop'
$wrapper = Join-Path $PSScriptRoot 'optimierungen-finden.ps1'
$aufgabe = 'MaxHirn-Optimierungen-Finden'
$logs = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'optimierungen-finden-aufgabe.log'

function Schreib($text) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $text" | Add-Content $log -Encoding UTF8
}

$binAdmin = ([Security.Principal.WindowsPrincipal] `
  [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Schreib ("gestartet als {0}, erhoeht: {1}" -f $env:USERNAME, $binAdmin)

try {
  if (-not (Test-Path $wrapper)) { throw "Wrapper fehlt: $wrapper" }

  $aktion = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "{0}"' -f $wrapper)

  $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9:45am

  $einstellungen = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

  $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType Interactive -RunLevel Limited

  Register-ScheduledTask -TaskName $aufgabe -Action $aktion -Trigger $trigger `
    -Settings $einstellungen -Principal $principal -Force | Out-Null

  $t = Get-ScheduledTask -TaskName $aufgabe
  $text = "Aufgabe '{0}' eingerichtet: State={1}, montags 09:45, StartWhenAvailable" -f `
            $aufgabe, $t.State
  Schreib $text
  $text
} catch {
  Schreib "ENDE FEHLER: $_"
  "ENDE FEHLER: $_"
  exit 1
}
