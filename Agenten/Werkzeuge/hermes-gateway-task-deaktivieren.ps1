# Deaktiviert den abgeloesten Task 'Hermes_Gateway' (Start aus der Altanlage
# C:\Hermes). Laeuft nur mit Adminrechten durch: der Task liegt auf der Platte
# und darf aus einer normalen Sitzung nicht geaendert werden ("Zugriff
# verweigert", auch per schtasks).
#
# Aufruf (aus einer NICHT erhoehten Sitzung startet der UAC-Dialog):
#   Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile',
#     '-ExecutionPolicy','Bypass','-File','<dieser Pfad>'
#
# Ergebnis steht in %TEMP%\hermes-gateway-task.log.
$log = Join-Path $env:TEMP 'hermes-gateway-task.log'
function Schreib($t) { "$((Get-Date).ToString('HH:mm:ss'))  $t" | Add-Content $log -Encoding UTF8 }
$ErrorActionPreference = 'Continue'
Set-Content -Path $log -Value '' -Encoding UTF8

$erhoeht = (New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent())
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Schreib "Start (erhoeht: $erhoeht)"

try {
    Disable-ScheduledTask -TaskName 'Hermes_Gateway' -ErrorAction Stop | Out-Null
    Schreib "deaktiviert"
} catch {
    Schreib "FEHLER deaktivieren: $($_.Exception.Message)"
}

$t = Get-ScheduledTask -TaskName 'Hermes_Gateway' -ErrorAction SilentlyContinue
Schreib ("Zustand Hermes_Gateway: " + $(if ($t) { $t.State } else { 'nicht gefunden' }))
$g = Get-ScheduledTask -TaskName 'Hermes_Gateway_2ef9d0b7' -ErrorAction SilentlyContinue
Schreib ("Zustand Hermes_Gateway_2ef9d0b7 (muss Ready bleiben): " + $(if ($g) { $g.State } else { 'nicht gefunden' }))
Schreib "Ende"
