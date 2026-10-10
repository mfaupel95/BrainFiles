#Requires -Version 5.1
# Wacht darauf dass claude --channels laeuft; startet es in einem neuen
# minimierten Fenster neu wenn der Prozess fehlt.
# Wird per Task Scheduler bei Anmeldung + alle 5 Minuten ausgefuehrt.

$laeuft = Get-WmiObject Win32_Process -Filter 'Name="claude.exe"' |
    Where-Object { $_.CommandLine -like '*--channels*' }

if ($laeuft) { exit 0 }

$befehl = 'claude --channels plugin:telegram@claude-plugins-official'
Start-Process powershell.exe `
    -ArgumentList '-NoExit', '-Command', $befehl `
    -WindowStyle Minimized
