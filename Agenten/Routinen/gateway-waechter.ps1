# Gateway-Waechter: startet das Hermes-Gateway neu, wenn es nicht mehr laeuft.
#
# Vorsorge nach dem Ausfall am 16.09.2026 (Doppelstart durch den alten Task
# 'Hermes_Gateway' aus der Altanlage C:\Hermes; 13 Minuten Ausfall).
#
# Regel: Port 9900 ist die Wahrheit. Der A2A-Gateway bindet 9900; ist der
# Port offen, laeuft der Dienst - unabhaengig vom Prozessnamen. Ist er zu,
# wird der offizielle Launcher (Hermes_Gateway_2ef9d0b7.vbs) gestartet.
# Der eigene Doppelstart-Schutz des Gateways ("exiting to avoid
# double-running") faengt den Rest ab - dieser Waechter startet nur, wenn
# GAR KEIN Gateway da ist.
#
# FALLE (19.09.2026, zweifach): Das Suchmuster 'tui_gateway' hat das
# TUI/Desktop-JSON-RPC-Backend ('python.exe -m tui_gateway.entry') fuer den
# A2A-Gateway gehalten. Diese Backends lauschen NICHT auf 9900; als der echte
# Gateway (dann 'hermes_cli.main gateway run') ausfiel, meldete der Waechter
# weiter "laeuft schon" und der Ausfall blieb ~13 h unerkannt. Vorher matchte
# 'hermes_cli.main gateway' zu eng und startete alle ~16 min neu (--replace-
# Handoff, 90 s Ausfall je Mal). EINDEUTIG: Nur ein Prozess mit
# 'hermes_cli.main gateway' ist der A2A-Gateway; 'tui_gateway' allein zaehlt
# nie. Port 9900 pruefen, Prozessname nur als Boot-/Stuck-Entscheidung.
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

# Erste Wahrheit: Port 9900. Ein offener A2A-Port ist die Sache selbst,
# der Prozessname kann sich jederzeit aendern (zweimal am 19.09.2026 geschehen).
$port_offen = Test-NetConnection -ComputerName 127.0.0.1 -Port 9900 `
    -WarningAction SilentlyContinue -InformationLevel Quiet
if ($port_offen) {
    Melde-Ende -Marke $marke -Code 0 -Text 'Port 9900 antwortet, kein Start'
    exit 0
}

# Port zu, aber vielleicht noch am Binden. Nur ein Prozess mit
# 'hermes_cli.main gateway' ist der A2A-Gateway - 'tui_gateway.entry' ist das
# TUI/Desktop-JSON-RPC-Backend und zaehlt NIE (lauscht nicht auf 9900).
$gw = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
      Where-Object { $_.CommandLine -match 'hermes_cli\.main gateway' -and
                     $_.CommandLine -notmatch '--profile' }
if ($gw) {
    # Frisch gestartet = Boot, nicht nachstossen (sonst --replace-Churn wie
    # am 19.09.). Ein alter, haengender Prozess faellt durch und wird neu
    # gestartet.
    $alter = ((Get-Date) - $gw[0].CreationDate).TotalSeconds
    if ($alter -lt 120) {
        Melde-Ende -Marke $marke -Code 0 -Text 'Gateway-Prozess bootet (Port noch nicht offen), kein Start'
        exit 0
    }
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
