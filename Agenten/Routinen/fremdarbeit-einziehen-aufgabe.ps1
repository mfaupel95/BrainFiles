# Registriert die Aufgabe MaxHirn-Fremdarbeit-Einziehen in der
# Windows-Aufgabenplanung. Einmalig auszufuehren; danach ist die Aufgabe
# eingerichtet (erneutes Ausfuehren legt sie neu an).
#
# Vorlage ist die XML der bestehenden Aufgabe MaxHirn-Zwischenstand: gleiche
# Einstellungen (versteckt ueber -WindowStyle Hidden in der Aktion,
# StartWhenAvailable, IgnoreNew), nur andere Zeit und anderes Skript.
#
# 20:40 liegt NACH dem Zwischenstand (20:00): der sichert die uncommittete
# Arbeit erst auf den Branch "zwischenstand", diese Aufgabe holt dieselbe
# Arbeit ein zweites Mal ab und schreibt sie nach master.
#
# Kein Melde-Start/Melde-Ende: dies ist ein Registrierer, kein periodischer
# Lauf (dieselbe Bauart wie handelszentrale-aufgabe.ps1).
$ErrorActionPreference = 'Stop'
$neu = 'MaxHirn-Fremdarbeit-Einziehen'
$vorlage = 'MaxHirn-Zwischenstand'
$skript = Join-Path $PSScriptRoot 'fremdarbeit-einziehen.ps1'

if (-not (Test-Path $skript)) { throw "Skript fehlt: $skript" }

$xml = Export-ScheduledTask -TaskName $vorlage
$xml = $xml -replace [regex]::Escape((Get-ScheduledTask -TaskName $vorlage).Actions[0].Arguments), `
      ('-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "{0}"' -f $skript)
$xml = $xml -replace '<StartBoundary>[^<]+</StartBoundary>', '<StartBoundary>2026-09-21T20:40:00</StartBoundary>'

if (Get-ScheduledTask -TaskName $neu -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $neu -Confirm:$false
}
Register-ScheduledTask -TaskName $neu -Xml $xml -Force | Out-Null

$t = Get-ScheduledTask -TaskName $neu
$i = Get-ScheduledTaskInfo -TaskName $neu
Write-Output ("Aufgabe   : {0}  Zustand {1}" -f $t.TaskName, $t.State)
Write-Output ("Aktion    : {0} {1}" -f $t.Actions[0].Execute, $t.Actions[0].Arguments)
Write-Output ("Trigger   : {0}  naechster Lauf {1}" -f $t.Triggers[0].StartBoundary, $i.NextRunTime)
Write-Output ("Einstell. : StartWhenAvailable={0} MultipleInstances={1}" -f `
    $t.Settings.StartWhenAvailable, $t.Settings.MultipleInstances)
