# Gateway-Waechter: startet das Hermes-Gateway neu, wenn es nicht mehr laeuft.
#
# Vorsorge nach dem Ausfall am 16.09.2026 (Doppelstart durch den alten Task
# 'Hermes_Gateway' aus der Altanlage C:\Hermes; 13 Minuten Ausfall).
#
# Regel: Wenn kein Prozess mit 'tui_gateway' oder 'hermes_cli.main gateway'
# lebt UND Port 9900 nicht antwortet, wird der offizielle Launcher
# (Hermes_Gateway_2ef9d0b7.vbs) gestartet. Der eigene Doppelstart-Schutz
# des Gateways ("exiting to avoid double-running") faengt den Rest ab -
# dieser Waechter startet nur, wenn GAR KEIN Gateway da ist.
#
# FALLE (19.09.2026): Das Suchmuster hiese frueher 'hermes_cli.main gateway';
# der Gateway laeuft seit dem Hermes-Update aber als 'python.exe -m
# tui_gateway.entry'. Der Waechter fand ihn nie und startete alle ~16 min
# einen NEUEN Gateway, der den alten per --replace-Handoff verdraengte -
# der A2A-Dienst (Port 9900) fiel dabei ~90 s aus, und der SkillsBot
# scheiterte genau in diesen Fenstern. Prozessname UND Port pruefen, damit
# eine weitere Umbenennung nicht wieder blind neu startet.
#
# Registriert als Aufgabe 'MaxHirn-Gateway-Waechter': bei Anmeldung plus
# Wiederholung alle 2 Minuten, StartWhenAvailable, IgnoreNew (Muster:
# skillsbot-Waechter). Braucht keine Admin-Rechte.

$ErrorActionPreference = 'Continue'
$wurzel = Split-Path $PSScriptRoot -Parent
. (Join-Path $wurzel 'Bus\Ereignis.ps1')
$log = Join-Path $PSScriptRoot 'logs\gateway-waechter.log'
$marke = Melde-Start -Wer 'routine/gateway-waechter' `
           -Log 'Agenten/Routinen/logs/gateway-waechter.log'
# Pfad aus dem Skriptort ableiten, nicht verdrahten (Portabilitaet);
# $PSScriptRoot ist Agenten\Routinen
$vbs = Join-Path (Split-Path $PSScriptRoot -Parent) 'Hermes\gateway-service\Hermes_Gateway_2ef9d0b7.vbs'
$zeit = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')

$lebt = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { ($_.CommandLine -match 'tui_gateway' -or
                        $_.CommandLine -match 'hermes_cli\.main gateway') -and
                       $_.CommandLine -notmatch '--profile' }
if ($lebt) {
    Melde-Ende -Marke $marke -Code 0 -Text 'Gateway laeuft schon, kein Start'
    exit 0
}

# Zweite Wahrheit: Port 9900. Der Prozessname kann sich aendern (geschehen
# am 19.09.2026), ein offener A2A-Port ist die Sache selbst.
$port_offen = Test-NetConnection -ComputerName 127.0.0.1 -Port 9900 `
    -WarningAction SilentlyContinue -InformationLevel Quiet
if ($port_offen) {
    Melde-Ende -Marke $marke -Code 0 -Text 'Port 9900 antwortet, kein Start'
    exit 0
}

if (-not (Test-Path $vbs)) {
    "$zeit  FEHLER: Launcher fehlt ($vbs)" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 1 -Text "Launcher fehlt ($vbs)"
    exit 1
}

try {
    Start-Process wscript.exe -ArgumentList '//B', '//Nologo', $vbs -WindowStyle Hidden
    "$zeit  Gateway nicht gefunden - Neustart ausgeloest ($vbs)" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text 'Neustart ausgeloest'
} catch {
    "$zeit  FEHLER beim Gateway-Start: $($_.Exception.Message)" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 1 -Text $_.Exception.Message
    exit 1
}
