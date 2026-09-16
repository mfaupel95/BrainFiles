# Registriert den Bus als Aufgabe 'bei Systemstart'.
#
# Register-ScheduledTask statt schtasks, weil schtasks kein 'Starten, sobald
# moeglich' setzt - siehe Wissen/Routinen.md. Einmal von Hand als
# Administrator ausfuehren; danach startet der Bus mit dem Rechner.
#
# Dies ist die einzige Stelle im ganzen Modul, die einen absoluten Pfad
# erzeugt - und sie erzeugt ihn zur Laufzeit aus $PSScriptRoot. Nach einem
# Umzug des Vaults muss dieses Skript einmal neu laufen.

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$busPy  = Join-Path $wurzel 'Bus\bus.py'
# pythonw statt python: der Bus braucht kein Konsolenfenster (die Prints
# sind Status, das Journal geht auf die Platte). Unter python.exe wuerde
# bei jedem Start ein Fenster aufploppen (gemessen 16.09.2026).
$python = (Get-Command python).Source
$python = if (Test-Path ($python -replace 'python\.exe$','pythonw.exe')) { $python -replace 'python\.exe$','pythonw.exe' } else { $python }

$aktion  = New-ScheduledTaskAction -Execute $python -Argument "`"$busPy`"" `
             -WorkingDirectory (Split-Path $busPy -Parent)
$ausloes = New-ScheduledTaskTrigger -AtStartup
$einst   = New-ScheduledTaskSettingsSet -StartWhenAvailable `
             -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) `
             -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName 'BrainFiles-Bus' -Action $aktion `
  -Trigger $ausloes -Settings $einst -RunLevel Highest -Force

Write-Output "Aufgabe 'BrainFiles-Bus' registriert: $busPy"
