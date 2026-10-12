#Requires -RunAsAdministrator
# Registriert die Aufgabe "MaxHirn-Docker-Platten": alle 4 Wochen sonntags 04:00, mit hoechsten Rechten
# (Optimize-VHD braucht Admin). Laeuft nur bei angemeldetem Max, weil Docker Desktop eine Sitzung braucht.
$skript = Join-Path $PSScriptRoot 'docker-platten-kompaktieren.ps1'
$aktion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$skript`""
$ausloeser = New-ScheduledTaskTrigger -Weekly -WeeksInterval 4 -DaysOfWeek Sunday -At 4am
$prinzipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$einst = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName 'MaxHirn-Docker-Platten' -Action $aktion -Trigger $ausloeser -Principal $prinzipal -Settings $einst -Force | Out-Null
Write-Output 'Aufgabe MaxHirn-Docker-Platten registriert (alle 4 Wochen, Sonntag 04:00).'
