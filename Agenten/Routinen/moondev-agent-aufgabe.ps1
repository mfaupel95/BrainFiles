# Legt die Aufgabe 'MaxHirn-MoonDev-Agent' an: Anmeldung + 2 Minuten,
# verstecktes Fenster, unbegrenzte Laufzeit (sonst beendet die
# Aufgabenplanung den Dauerlaeufer nach 72 h), IgnoreNew (keine doppelte
# Instanz, auch nicht bei mehrfachem Logon). Kein Administrator noetig:
# die Aufgabe laeuft als angemeldeter Benutzer.
#
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\moondev-agent-aufgabe.ps1

$ErrorActionPreference = 'Stop'
$name    = 'MaxHirn-MoonDev-Agent'
$wrapper = Join-Path $PSScriptRoot 'moondev-agent.ps1'
if (-not (Test-Path $wrapper)) { throw "Wrapper fehlt: $wrapper" }

$aktion   = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument (
  '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $wrapper + '"'
)
$trigger  = New-ScheduledTaskTrigger -AtLogOn
$trigger.Delay = 'PT2M'
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
                                         -ExecutionTimeLimit ([TimeSpan]::Zero) `
                                         -StartWhenAvailable
$task = New-ScheduledTask -Action $aktion -Trigger $trigger -Settings $settings `
  -Description 'Moon-Dev-Agent (src/agents/new_or_top_agent) als Dauerlaeufer: stuendlicher Analysezyklus, Urteil vom lokalen Ollama, oeffentliche CoinGecko-API. Wrapper: Agenten/Routinen/moondev-agent.ps1'

Register-ScheduledTask -TaskName $name -InputObject $task -Force | Out-Null
Get-ScheduledTask -TaskName $name |
  Select-Object TaskName, State | Format-Table -AutoSize
Write-Output "Aufgabe '$name' angelegt. Start: Start-ScheduledTask -TaskName '$name'"