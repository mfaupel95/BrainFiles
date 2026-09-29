# Legt die Aufgabe 'MaxHirn-Ollama' an: Anmeldung + 15 Sekunden, verstecktes
# Fenster, IgnoreNew. Die REGISTRIERUNG braucht Administrator (Elevation);
# der Betrieb danach laeuft als angemeldeter Benutzer.
#
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\ollama-start-aufgabe.ps1

$ErrorActionPreference = 'Stop'
$name    = 'MaxHirn-Ollama'
$wrapper = Join-Path $PSScriptRoot 'ollama-start.ps1'
if (-not (Test-Path $wrapper)) { throw "Wrapper fehlt: $wrapper" }

$aktion   = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument (
  '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $wrapper + '"'
)
$trigger  = New-ScheduledTaskTrigger -AtLogOn
$trigger.Delay = 'PT15S'
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
                                         -StartWhenAvailable
$task = New-ScheduledTask -Action $aktion -Trigger $trigger -Settings $settings `
  -Description 'Startet Ollama (ollama serve) nach der Anmeldung - die lokale Modell-Laufzeit fuer alle LLM-Urteile. Wrapper: Agenten/Routinen/ollama-start.ps1'

Register-ScheduledTask -TaskName $name -InputObject $task -Force | Out-Null
Get-ScheduledTask -TaskName $name |
  Select-Object TaskName, State | Format-Table -AutoSize
Write-Output "Aufgabe '$name' angelegt."