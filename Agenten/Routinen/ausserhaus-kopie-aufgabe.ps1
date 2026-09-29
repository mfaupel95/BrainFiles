# Legt die Aufgabe 'MaxHirn-Ausserhaus-Kopie' an: taeglich 21:30 (nach der
# Zweitkopie um 21:00), verstecktes Fenster, IgnoreNew, laeuft nach, wenn der
# Rechner zur Zeit war. Zeitlimit 6 Stunden - ein erstmaliger Vollaufbau der
# Kopie darf lange dauern, ein haengender Lauf soll aber nicht ewig stehen.
#
# Ist Q: nicht angesteckt, endet der Lauf nach Sekunden mit "uebersprungen"
# (kein Fehlschlag, keine Meldung).
#
# WARUM UEBER XML (gemessen 30.09.2026, um 00:5x):
# Register-ScheduledTask (Cmdlet) meldete 'Ready' samt naechstem Lauf, aber die
# Aufgabe war im NAECHSTEN Aufruf nicht mehr da - zweimal reproduziert. Ueber
# 'schtasks /create' angelegt, haelt sie. Und: Get-ScheduledTask -TaskName findet
# in dieser Umgebung auch VORHANDENE Aufgaben nicht (die Aufzaehlung
# Get-ScheduledTask | Where TaskName -like ... und 'schtasks /query' zeigen sie).
# Also anlegen per schtasks/XML und pruefen per schtasks/query.
#
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\ausserhaus-kopie-aufgabe.ps1

$ErrorActionPreference = 'Stop'
$name    = 'MaxHirn-Ausserhaus-Kopie'
$wrapper = Join-Path $PSScriptRoot 'ausserhaus-kopie.ps1'
if (-not (Test-Path $wrapper)) { throw "Wrapper fehlt: $wrapper" }

# Kein <UserId> im Principal: die Aufgabe laeuft als der angemeldete Benutzer,
# wie alle anderen MaxHirn-Aufgaben. <Hidden>true</Hidden> = kein Fenster.
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Erneuert taeglich die Ausser-Haus-Kopie auf Q:, wenn die SSD angesteckt ist; sonst uebersprungen (Exitcode 2 = kein Fehler). Wrapper: Agenten/Routinen/ausserhaus-kopie.ps1</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-09-30T21:30:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT6H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$wrapper"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$xmlPfad = Join-Path $env:TEMP 'maxhirn-ausserhaus-kopie.xml'
# schtasks verlangt die XML-Datei in Unicode (UTF-16LE).
[System.IO.File]::WriteAllText($xmlPfad, $xml, [System.Text.Encoding]::Unicode)

schtasks /create /tn $name /xml $xmlPfad /f | Out-Null
Remove-Item $xmlPfad -Force

# Pruefen mit dem Werkzeug, das hier verlaesslich ist: schtasks /query.
$q = schtasks /query /tn $name /v /fo list 2>&1
if ($LASTEXITCODE -ne 0) { throw "Anlegen fehlgeschlagen:`n$($q -join "`n")" }
($q | Where-Object { $_ -match 'Aufgabenname|Status|Anzahl|chste Laufzeit|Zuletzt' }) -join "`n"
Write-Output "Aktion: powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""$wrapper"""
