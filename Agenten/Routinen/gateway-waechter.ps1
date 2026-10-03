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
# KORREKTUR (29.09.2026): "Port 9900 ist die Wahrheit" gilt nicht mehr. Seit
# dem Update vom 29.09.2026 lauscht der Gateway auf einem Named Pipe
# (\\.\pipe\hermes-gateway-*) und bedient Webhooks auf 8644; TCP 9900 bleibt
# zu, waehrend der Dienst gesund laeuft. Folge: dieser Waechter startete den
# Gateway im 2-Minuten-Takt neu - 128 Zeilen "Neustart ausgeloest" allein am
# 29.09.2026, jeder Neustart reisst die laufenden Verbindungen mit.
# Geprueft wird jetzt die BEDINGUNG, nicht ihr frueherer Nebeneffekt: laeuft
# ein Prozess 'hermes_cli.main gateway run' (ohne --profile) UND antwortet er
# (Pipe ODER Port)? Prueffrage fuer jede Wache: prueft sie die Sache - oder
# eine Adresse, die die Sache einmal begleitet hat? Siehe Wiki
# [[Lektionen/Wahrheit-pruefen]] 8 und 10.
#
# Registriert als Aufgabe 'MaxHirn-Gateway-Waechter': bei Anmeldung plus
# Wiederholung alle 2 Minuten, StartWhenAvailable, IgnoreNew (Muster:
# skillsbot-Waechter). Braucht keine Admin-Rechte.

$ErrorActionPreference = 'Continue'
$wurzel = Split-Path $PSScriptRoot -Parent
. (Join-Path $wurzel 'Bus\Ereignis.ps1')
$log = Join-Path $PSScriptRoot 'logs\gateway-waechter.log'
$merker = Join-Path $PSScriptRoot 'logs\gateway-waechter.merker'
$marke = Melde-Start -Wer 'routine/gateway-waechter' `
           -Log 'Agenten/Routinen/logs/gateway-waechter.log'
# Pfad aus dem Skriptort ableiten, nicht verdrahten (Portabilitaet);
# $PSScriptRoot ist Agenten\Routinen
$vbs = Join-Path (Split-Path $PSScriptRoot -Parent) 'Hermes\gateway-service\Hermes_Gateway_2ef9d0b7.vbs'
$zeit = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')

# ---------------------------------------------------------------------------
# 1. Laeuft der Gateway-Prozess? Das ist die Bedingung.
# ---------------------------------------------------------------------------
# BEFUND/FIX 29.09.2026: Die Erkennung hing an der Kommandozeile EINES
# Starters ('hermes_cli.main gateway'). Seit dem Update gibt es ZWEI Formen:
# der Launcher startet '-m hermes_cli.main gateway run', der Update-Weg
# ('hermes gateway run --replace') startet eine runpy-Form, in der zwischen
# 'hermes_cli.main' und 'gateway run' noch ', run_name=...' steht. Das alte
# Muster traf die runpy-Form NICHT: der Waechter sah 0 Prozesse und startete
# den Gateway im 2-Minuten-Takt neu (148 Neustarts und 19 'exited UNCLEANLY'
# am 29.09.2026, jede Runde reisst die Verbindungen mit). Kanonisch ist die
# Identitaet aus gateway_state.json (pid + Zustand = running, so schreibt es
# der Gateway selbst); die Kommandozeile bleibt Rueckfall fuer Altbestaende.
# FALLE (30.09.2026, 2,5 h unbemerkter Ausfall): Das Muster
# 'run_module\(''hermes_cli\.main''' traf JEDEN runpy-Start des Hauptmoduls -
# auch den DASHBOARD-Prozess ('... main.py', 'dashboard', ...). Solange der
# Dashboard lief, hielt der Waechter ihn fuer den Gateway und startete nichts.
# Das Muster fordert jetzt den Unterbefehl 'gateway' und schliesst 'dashboard'
# aus. Zweite Sperre: die Frische von gateway_state.json - der Gateway
# schreibt seinen Herzschlag selbst; ein alter Stand heisst tot, auch wenn
# irgendein Prozess noch laeuft.
$state_datei = Join-Path (Split-Path $PSScriptRoot -Parent) 'Hermes\gateway_state.json'
$gw = @()
$state_frisch = $false
if (Test-Path $state_datei) {
    try {
        $st = (Get-Content $state_datei -Raw -Encoding UTF8 | ConvertFrom-Json)
        if ($st.updated_at) {
            $st_alter = [int]((Get-Date).ToUniversalTime() - ([datetime]$st.updated_at).ToUniversalTime()).TotalSeconds
            # 1800 s, nicht 600: der Gateway schreibt seinen Stand gemessen nur alle
# ~7 min (16:05:13 -> 16:12:36). Mit 600 s galt ein gesunder, aber gerade
# schreibtraeger Gateway als tot und der Waechter startete einen zweiten.
            $state_frisch = ($st_alter -ge 0 -and $st_alter -lt 1800)
        }
        if ($state_frisch -and $st.pid -and $st.gateway_state -eq 'running') {
            $pr = Get-Process -Id $st.pid -ErrorAction SilentlyContinue
            if ($pr -and $pr.ProcessName -in @('python','pythonw')) {
                $gw = @(Get-CimInstance Win32_Process -Filter "ProcessId=$($st.pid)")
            }
        }
    } catch { $gw = @() }
}
if (-not $gw) {
    # Rueckfall ueber die Kommandozeile: der Unterbefehl MUSS 'gateway' sein.
    # Zwei Startformen: '-m hermes_cli.main gateway run' (Launcher) und
    # "runpy.run_module('hermes_cli.main', ...)" mit sys.argv ['main.py','gateway','run'].
    $gw = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='pythonw.exe'" -ErrorAction SilentlyContinue |
            Where-Object {
                $c = $_.CommandLine
                if (-not $c) { return $false }
                if ($c -match '--profile') { return $false }
                if ($c -match 'hermes_cli\.main gateway run') { return $true }
                if ($c -match 'run_module\(''hermes_cli\.main''' -and $c -match "'gateway'" -and $c -notmatch "'dashboard'") { return $true }
                return $false
            })
}

if (-not $gw) {
    if (-not (Test-Path $vbs)) {
        "$zeit  FEHLER: Launcher fehlt ($vbs)" | Add-Content $log -Encoding UTF8
        Melde-Ende -Marke $marke -Code 1 -Text "Launcher fehlt ($vbs)"
        exit 1
    }
    try {
        Start-Process wscript.exe -ArgumentList '//B', '//Nologo', $vbs -WindowStyle Hidden
        "$zeit  kein Gateway-Prozess - Neustart ausgeloest ($vbs)" | Add-Content $log -Encoding UTF8
        Melde-Ende -Marke $marke -Code 0 -Text 'Neustart ausgeloest (kein Prozess)'
    } catch {
        "$zeit  FEHLER beim Gateway-Start: $($_.Exception.Message)" | Add-Content $log -Encoding UTF8
        Melde-Ende -Marke $marke -Code 1 -Text $_.Exception.Message
        exit 1
    }
    exit 0
}

# Frisch gestartet = Boot, nicht nachstossen (sonst --replace-Churn wie am 19.09.).
$start = ($gw | Sort-Object CreationDate | Select-Object -First 1).CreationDate
$alter = [int]((Get-Date) - $start).TotalSeconds
if ($alter -lt 120) {
    Melde-Ende -Marke $marke -Code 0 -Text "Gateway-Prozess bootet ($alter s), kein Start"
    exit 0
}

# ---------------------------------------------------------------------------
# 2. Antwortet er? Control-Pipe (neue Bauart) oder Port (alte Bauart).
# ---------------------------------------------------------------------------
$pipe_da = $false
try {
    $pipe_da = @([System.IO.Directory]::GetFiles('\\.\pipe\') |
                 Where-Object { $_ -match 'hermes-gateway' }).Count -gt 0
} catch {
    $pipe_da = $false          # Pipe-Namensraum nicht lesbar: der Port entscheidet
}
$port_offen = Test-NetConnection -ComputerName 127.0.0.1 -Port 9900 `
    -WarningAction SilentlyContinue -InformationLevel Quiet

if ($pipe_da -or $port_offen) {
    Melde-Ende -Marke $marke -Code 0 `
        -Text ("Gateway laeuft (Pipe: $pipe_da, Port 9900: $port_offen), kein Start")
    exit 0
}

# ---------------------------------------------------------------------------
# 3. Prozess da, antwortet aber nicht = haengender Start. Hoechstens EIN
#    Neustart je 30 Minuten - sonst entsteht genau die Schleife, die dieser
#    Umbau am 29.09.2026 beendet hat.
# ---------------------------------------------------------------------------
$letzter = 0
if (Test-Path $merker) {
    $roh = (Get-Content $merker -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($roh -match '^\d+$') { $letzter = [int]$roh }
}
$jetzt_s = [int]((Get-Date) - (Get-Date '1970-01-01')).TotalSeconds
if (($jetzt_s - $letzter) -lt 1800) {
    Melde-Ende -Marke $marke -Code 0 `
        -Text "Gateway-Prozess $alter s alt, antwortet nicht - Neustart unterdrueckt (letzter vor <30 min)"
    exit 0
}

try {
    Start-Process wscript.exe -ArgumentList '//B', '//Nologo', $vbs -WindowStyle Hidden
    $jetzt_s | Set-Content $merker -Encoding UTF8
    "$zeit  Gateway-Prozess $alter s alt ohne Antwort - Neustart ausgeloest ($vbs)" |
        Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 0 -Text 'Neustart ausgeloest (haengender Prozess)'
} catch {
    "$zeit  FEHLER beim Gateway-Start: $($_.Exception.Message)" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 1 -Text $_.Exception.Message
    exit 1
}
