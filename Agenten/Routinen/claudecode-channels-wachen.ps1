#Requires -Version 5.1
# Wacht darauf dass claude --channels laeuft; startet es in einem neuen
# minimierten Fenster neu wenn der Prozess fehlt.
# Wird per Task Scheduler bei Anmeldung + alle 5 Minuten ausgefuehrt.

. (Join-Path $PSScriptRoot '..\Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/claudecode-channels-wachen'
$laeuft = Get-WmiObject Win32_Process -Filter 'Name="claude.exe"' |
    Where-Object { $_.CommandLine -like '*--channels*' }

if ($laeuft) { Melde-Ende -Marke $marke -Code 0 -Text 'laeuft bereits'; exit 0 }

$befehl = 'claude --channels plugin:telegram@claude-plugins-official'
Start-Process powershell.exe `
    -ArgumentList '-NoExit', '-Command', $befehl `
    -WindowStyle Minimized
Melde-Ende -Marke $marke -Code 0 -Text 'gestartet'
