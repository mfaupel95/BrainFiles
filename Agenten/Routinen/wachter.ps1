# Registriert den Lotse-Wachter als geplanten Task (Wartungsmodus).

# Voraussetzungen (einmalig, von Max):
#   - SKILLSBOT_TOKEN, TELEGRAM_CHAT_ID, A2A_PEER_TOKENS als
#     Benutzervariablen (siehe Agenten/BUS/skillsbot.py --probe)
#   - pythonw.exe vorhanden (gilt für alle geplanten Tasks)

$ErrorActionPreference = 'Stop'
$hier = Split-Path $PSScriptRoot -Parent   # Agenten
$scripts = Join-Path $hier 'Hermes\scripts'
$python = (Get-Command pythonw.exe -CommandType Application -ErrorAction Stop |
    Select-Object -First 1).Source
$skript = Join-Path $scripts 'wachter.py'
$aufgabe = 'BrainFiles-Lotse-Waechter'

if (-not (Test-Path $skript)) {
    throw "Wachter fehlt: $skript"
}
if (-not (Test-Path $python)) {
    throw "Fensterloses Python fehlt: $python"
}

$aktion = New-ScheduledTaskAction -Execute $python `
    -Argument "`"$skript`" --probe" -WorkingDirectory $scripts
$trigger = (New-ScheduledTaskTrigger -AtLogOn)
$einstellungen = New-ScheduledTaskSettingsSet `
    -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $aufgabe -Action $aktion -Trigger $trigger `
    -Settings $einstellungen -Principal $principal -Force | Out-Null

Write-Host "Task '$aufgabe' registriert."
Write-Host "Start: Start-ScheduledTask -TaskName '$aufgabe'"
Write-Host "Status: Get-ScheduledTask -TaskName '$aufgabe' | Format-List"
