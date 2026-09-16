# Gateway-Waechter: startet das Hermes-Gateway neu, wenn es nicht mehr laeuft.
#
# Vorsorge nach dem Ausfall am 16.09.2026 (Doppelstart durch den alten Task
# 'Hermes_Gateway' aus der Altanlage C:\Hermes; 13 Minuten Ausfall).
#
# Regel: Wenn kein Prozess mit 'hermes_cli.main gateway' lebt, wird der
# offizielle Launcher (Hermes_Gateway_2ef9d0b7.vbs) gestartet. Der eigene
# Doppelstart-Schutz des Gateways ("exiting to avoid double-running") faengt
# den Rest ab - dieser Waechter startet nur, wenn GAR KEIN Gateway da ist.
#
# Registriert als Aufgabe 'MaxHirn-Gateway-Waechter': bei Anmeldung plus
# Wiederholung alle 2 Minuten, StartWhenAvailable, IgnoreNew (Muster:
# skillsbot-Waechter). Braucht keine Admin-Rechte.

$ErrorActionPreference = 'Continue'
$log = Join-Path $PSScriptRoot 'logs\gateway-waechter.log'
# Pfad aus dem Skriptort ableiten, nicht verdrahten (Portabilitaet);
# $PSScriptRoot ist Agenten\Routinen
$vbs = Join-Path (Split-Path $PSScriptRoot -Parent) 'Hermes\gateway-service\Hermes_Gateway_2ef9d0b7.vbs'
$zeit = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')

$lebt = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'hermes_cli\.main gateway' }
if ($lebt) {
    exit 0
}

if (-not (Test-Path $vbs)) {
    "$zeit  FEHLER: Launcher fehlt ($vbs)" | Add-Content $log -Encoding UTF8
    exit 1
}

try {
    Start-Process wscript.exe -ArgumentList '//B', '//Nologo', $vbs -WindowStyle Hidden
    "$zeit  Gateway nicht gefunden - Neustart ausgeloest ($vbs)" | Add-Content $log -Encoding UTF8
} catch {
    "$zeit  FEHLER beim Gateway-Start: $($_.Exception.Message)" | Add-Content $log -Encoding UTF8
    exit 1
}
