<#
.SYNOPSIS
    Misst den Stand der Abschaltungen ohne Bluescreen (TASKS T-004).

.BESCHREIBUNG
    Fasst die Abfragen zusammen, die am 30.08.2026 zur Widerlegung der
    Standby-Hypothese gefuehrt haben. Nur lesend, keine Adminrechte noetig.

    Auswertung und Vorgeschichte: Wissen/Hardware.md, Abschnitt
    "Stromausfaelle ohne Bluescreen". Zahlen gehoeren dorthin, nicht hierher.

.BEISPIEL
    powershell -ExecutionPolicy Bypass -File Routinen\absturz-nachmessen.ps1
#>
param([int]$Tage = 30)

$ErrorActionPreference = 'Continue'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'Bus\Ereignis.ps1')      # neu
$marke = Melde-Start -Wer 'routine/absturz-nachmessen'                  # neu
try {                                                                    # neu

# Reichweite zuerst: ein abstuerzender Dienst kann das Protokoll so schnell
# ueberschreiben, dass eine Luecke faelschlich als Ruhe gelesen wird.
$aeltest = (Get-WinEvent -LogName System -Oldest -MaxEvents 1).TimeCreated
$start   = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
"Protokoll reicht zurueck bis : $aeltest"
"Letzter Systemstart          : $start  ({0:N1} h Laufzeit)" -f ((Get-Date) - $start).TotalHours
""

# Echte Absturzzeitpunkte stehen in 6008, nicht in 41: Ereignis 41 wird erst
# beim naechsten Hochfahren geschrieben und traegt dessen Zeitstempel.
"=== Unerwartetes Herunterfahren (Ereignis 6008) ==="
Get-WinEvent -FilterHashtable @{LogName='System';Id=6008;StartTime=(Get-Date).AddDays(-$Tage)} -EA SilentlyContinue |
    ForEach-Object { "  {0}" -f (($_.Message -replace "`r`n"," " -replace "\s+"," ")) }
""

# Felder ueber den NAMEN auslesen, nie ueber .Properties[n]: genau dort ist
# am 28.08.2026 "Checkpoint = 16" als "SleepInProgress = 16" verlesen worden.
"=== Kernel-Power 41 mit Fingerabdruck ==="
Get-WinEvent -FilterHashtable @{LogName='System';Id=41;StartTime=(Get-Date).AddDays(-$Tage)} -EA SilentlyContinue |
    Sort-Object TimeCreated | ForEach-Object {
        $x = [xml]$_.ToXml(); $d = @{}
        foreach ($e in $x.Event.EventData.Data) { $d[$e.Name] = $e.'#text' }
        "  {0} | Bugcheck={1} | Sleep={2} | Chk={3,-3} | SleepTrans={4} | PwrBtn={5}" -f `
            $_.TimeCreated.ToString('dd.MM HH:mm'), $d['BugcheckCode'], $d['SleepInProgress'],
            $d['Checkpoint'], $d['SystemSleepTransitionsToOn'], $d['PowerButtonTimestamp']
    }
""

# Ruhe beweist nur dann etwas, wenn die Bedingung ueberhaupt eingetreten ist.
$zyklen = @(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-Kernel-Power';Id=42;StartTime=(Get-Date).AddDays(-$Tage)} -EA SilentlyContinue)
"=== Standby-Zyklen (Kernel-Power 42): {0} in {1} Tagen ===" -f $zyklen.Count, $Tage
if ($zyklen.Count) { $zyklen | Sort-Object TimeCreated | Select-Object -Last 5 | ForEach-Object { "  $($_.TimeCreated)" } }
""

"=== Negativbefunde ==="
$whea = @(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-WHEA-Logger';StartTime=(Get-Date).AddDays(-$Tage)} -EA SilentlyContinue)
"  WHEA (CPU/RAM/PCIe)       : $($whea.Count) Ereignisse"
"  Plattenfehler 7 Tage      :"
Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='disk','Microsoft-Windows-Ntfs','volmgr';StartTime=(Get-Date).AddDays(-7)} -EA SilentlyContinue |
    Group-Object Id -NoElement | ForEach-Object { "     ID {0,-4} x{1}   (153 = E/A-Fehler, 140 = NTFS-Warnung, 98 = harmlos)" -f $_.Name, $_.Count }
$dump = if (Test-Path C:\Windows\MEMORY.DMP) { (Get-Item C:\Windows\MEMORY.DMP).LastWriteTime } else { 'keines' }
$mini = @(Get-ChildItem C:\Windows\Minidump -EA SilentlyContinue).Count
"  MEMORY.DMP                : $dump"
"  Minidumps                 : $mini"
$ws = Get-Service WSearch -EA SilentlyContinue
"  Windows Search            : $($ws.Status) / $($ws.StartType)"

Melde-Ende -Marke $marke -Code 0                                        # neu
} catch {                                                                # neu
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  throw                                                                 # neu
}                                                                        # neu
