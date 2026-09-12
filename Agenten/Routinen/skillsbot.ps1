# Registriert den SkillsBot (Telegram <-> A2A) als geplanten Task.
#
# Voraussetzungen (einmalig, von Max):
#   - Bot bei @BotFather anlegen, setx SKILLSBOT_TOKEN <token>
#   - setx TELEGRAM_CHAT_ID <id> (gleiche ID wie beim melder)
#   - python skillsbot.py --probe  muss Exit 0 liefern
#
# Aufruf (Administrator noetig):
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\skillsbot.ps1

$ErrorActionPreference = 'Stop'
$hier = Split-Path $PSScriptRoot -Parent   # Agenten
$bus = Join-Path $hier 'Bus'
$python = (Get-Command pythonw.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$skript = Join-Path $bus 'skillsbot.py'
$aufgabe = 'BrainFiles-SkillsBot'

if (-not (Test-Path $skript)) {
  throw "SkillsBot fehlt: $skript"
}
if (-not (Test-Path $python)) {
  throw "Fensterloses Python fehlt: $python"
}

$aktion = New-ScheduledTaskAction -Execute $python -Argument "`"$skript`"" `
                                  -WorkingDirectory $bus
$trigger = @(
  (New-ScheduledTaskTrigger -AtLogOn),
  (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Minutes 2))
)
$einstellungen = New-ScheduledTaskSettingsSet -RestartCount 99 `
  -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) `
  -MultipleInstances IgnoreNew -StartWhenAvailable `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
  -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $aufgabe -Action $aktion -Trigger $trigger `
  -Settings $einstellungen -Principal $principal -Force | Out-Null

Write-Host "Task '$aufgabe' registriert."
Write-Host "Start: Start-ScheduledTask -TaskName '$aufgabe'"
