# Codex Remote Control starten (Windows).
#
# `codex remote-control` ist auf Windows nicht benutzbar: der Daemon-Lifecycle des
# app-servers ist Unix-only ("only supported on Unix platforms"). Der Weg, der auf
# Windows trägt, ist der Prozess selbst mit dem versteckten Schalter
# `--remote-control` plus einem lokalen WebSocket-Transport. Genau das startet
# dieses Skript, und es raeumt einen alten Restprozess vorher ab (zwei app-servers
# melden sich beim Relay als "409 Conflict / Remote app server already online").
#
# Aufruf:  powershell -File <dieses Skript>
# Log:     Agenten\Routinen\logs\codex-remote-control.log

$ErrorActionPreference = 'Continue'

$Hier = Split-Path -Parent $MyInvocation.MyCommand.Path
# Das Log gehoert in den Haus-Logordner der Routinen, nicht neben das Skript:
# Agenten/Werkzeuge/ traegt sonst einen zweiten logs/-Ordner nur fuer eine Datei.
$LogOrdner = Join-Path (Split-Path -Parent $Hier) 'Routinen\logs'
if (-not (Test-Path $LogOrdner)) { New-Item -ItemType Directory -Path $LogOrdner -Force | Out-Null }
$Log = Join-Path $LogOrdner 'codex-remote-control.log'

function Schreibe ($zeile) {
    $zeit = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Add-Content -Path $Log -Value "$zeit $zeile" -Encoding UTF8
}

# 1. Laeuft schon ein app-server mit --remote-control? Dann nichts tun.
$_marker = 'app-server --remote-control'
$vorhanden = @(Get-CimInstance Win32_Process -Filter "Name='codex.exe'" |
    Where-Object { $_.CommandLine -like "*$_marker*" })
if ($vorhanden.Count -gt 0) {
    Schreibe ("laeuft bereits: PID " + (($vorhanden | ForEach-Object { $_.ProcessId }) -join ', '))
    exit 0
}

# 2. codex.exe suchen: erst der verwaltete Pfad, dann der normale PATH.
$codex = Join-Path $env:LOCALAPPDATA 'Programs\OpenAI\Codex\bin\codex.exe'
if (-not (Test-Path $codex)) {
    $treffer = Get-Command codex.exe -ErrorAction SilentlyContinue
    if ($treffer) { $codex = $treffer.Source } else { Schreibe 'FEHLER: codex.exe nicht gefunden'; exit 1 }
}

# 3. Port 8766 muss frei sein (der WebSocket-Transport des app-servers).
$belegt = @(Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue)
if ($belegt.Count -gt 0) {
    Schreibe ("Port 8766 belegt durch PID " + (($belegt | ForEach-Object { $_.OwningProcess }) -join ', ') + ' - Abbruch')
    exit 1
}

# 4. Starten. stdout/stderr in die Logdatei, damit ein Fehler nicht im Fenster
#    der geplanten Aufgabe landet (die laeuft versteckt).
$args = @('app-server', '--remote-control', '--listen', 'ws://127.0.0.1:8766')
$p = Start-Process -FilePath $codex -ArgumentList $args -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogOrdner 'codex-app-server.out') `
    -RedirectStandardError (Join-Path $LogOrdner 'codex-app-server.err') -PassThru

# 5. Health-Check: /readyz muss antworten (lokaler HTTP-Zeuge, kein Fernzugriff).
$bereit = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $antwort = Invoke-WebRequest -Uri 'http://127.0.0.1:8766/readyz' -TimeoutSec 2 -UseBasicParsing
        if ($antwort.StatusCode -eq 200) { $bereit = $true; break }
    } catch { }
}

if ($bereit) {
    Schreibe "gestartet: PID $($p.Id), Port 8766 bereit"
    exit 0
}
Schreibe "gestartet: PID $($p.Id), aber /readyz antwortet nach 30 s nicht"
exit 1