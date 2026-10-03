# Registriert MaxHirn-Scanner-Papier-Stunde (stuendlich ab :05). ADMINISTRATOR NOETIG.
# Aufruf (erhoehte PowerShell): powershell -ExecutionPolicy Bypass -File Agenten\Routinen\scanner-papier-stunde-aufgabe.ps1
$ErrorActionPreference = 'Stop'
$wrapper = Join-Path $PSScriptRoot 'scanner-papier-stunde.ps1'
$aktion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "{0}"' -f $wrapper)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date '00:05') -RepetitionInterval (New-TimeSpan -Hours 1)
$einst = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$prin = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'MaxHirn-Scanner-Papier-Stunde' -Action $aktion -Trigger $trigger -Settings $einst -Principal $prin -Force | Out-Null
"Aufgabe eingerichtet: " + (Get-ScheduledTask -TaskName 'MaxHirn-Scanner-Papier-Stunde').State
