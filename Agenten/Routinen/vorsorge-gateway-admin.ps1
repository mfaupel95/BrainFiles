# Vorsorge nach dem Gateway-Ausfall am 16.09.2026 - in einer ADMIN-PowerShell ausfuehren.
# (Rechtsklick auf PowerShell -> Als Administrator ausfuehren, dann diesen Befehl:)
#   powershell -ExecutionPolicy Bypass -File ".\vorsorge-gateway-admin.ps1"   (im Ordner Agenten\Routinen)

$ErrorActionPreference = 'Continue'

# 1) Alten Gateway-Task deaktivieren (zeigte auf die Altanlage C:\Hermes und
#    startete am 16.09. um 10:34 einen zweiten Gateway -> 13 Minuten Ausfall).
#    Der zugehoerige VBS ist bereits entschaerft; der Task selbst muss trotzdem
#    aus dem Verkehr, damit kein Restrisiko bleibt.
Disable-ScheduledTask -TaskName 'Hermes_Gateway' -ErrorAction SilentlyContinue | Out-Null
'1) alter Task Hermes_Gateway: ' + (Get-ScheduledTask -TaskName 'Hermes_Gateway').State

# 2) Gateway-Waechter registrieren: prueft alle 2 Minuten, ob ein Gateway lebt,
#    und startet es ueber den offiziellen Launcher neu, wenn nicht. Muster:
#    skillsbot-Waechter (Anmeldung + Wiederholung, StartWhenAvailable, IgnoreNew).
$sk = Join-Path $PSScriptRoot 'gateway-waechter.ps1'
if (-not (Test-Path $sk)) { Write-Error ('Waechter-Skript fehlt: ' + $sk); exit 1 }
$aktion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $sk + '"')
$t1 = New-ScheduledTaskTrigger -AtLogOn
$t2 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
     -RepetitionInterval (New-TimeSpan -Minutes 2) `
     -RepetitionDuration (New-TimeSpan -Days 3650)
$einst = New-ScheduledTaskSettingsSet -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'MaxHirn-Gateway-Waechter' -Action $aktion `
    -Trigger $t1,$t2 -Settings $einst `
    -Description 'Startet das Hermes-Gateway neu, wenn es nicht laeuft (alle 2 min).' | Out-Null
'2) Waechter MaxHirn-Gateway-Waechter: ' + (Get-ScheduledTask -TaskName 'MaxHirn-Gateway-Waechter').State

# 3) Bus-Task auf pythonw umstellen: der Bus laeuft als python.exe und zeigt
#    bei jedem Start ein Konsolenfenster (gemessen 16.09.2026). Das Journal
#    geht auf die Platte, die Prints sind Status - pythonw reicht, genau wie
#    beim SkillsBot. bus.ps1 (Registrierung) ist bereits umgestellt.
$py = (Get-Command python).Source -replace 'python\.exe$', 'pythonw.exe'
$busPy = Join-Path (Split-Path $PSScriptRoot -Parent) 'Bus\bus.py'
$akt = New-ScheduledTaskAction -Execute $py -Argument ('"' + $busPy + '"') `
    -WorkingDirectory (Split-Path $busPy -Parent)
Set-ScheduledTask -TaskName 'BrainFiles-Bus' -Action $akt | Out-Null
'3) Bus-Task laeuft jetzt unter: ' + (Get-ScheduledTask -TaskName 'BrainFiles-Bus').Actions[0].Execute
'fertig.'
