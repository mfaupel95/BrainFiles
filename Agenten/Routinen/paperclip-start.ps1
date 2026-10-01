# Paperclip-Instanz starten (paperclipai run)
#
# Hausmuster: laeuft schon -> nichts tun, sonst starten und ins Log schreiben.
#
# ZWEI FALLEN, die hier bewusst behandelt werden:
#  1) ARBEITSVERZEICHNIS: Der Server laedt beim Start eine .env aus dem
#     ARBEITSVERZEICHNIS. In C:\Users\faupe liegt eine .env mit ANTHROPIC_API_KEY
#     (Max' Console-Schluessel ohne Guthaben). Wird der Server dort gestartet,
#     erbt jede Sonde und jeder Agent diese Variable, Claude Code nimmt dann
#     API-Key-Auth statt des Abo-Tokens und der Umgebungstest scheitert mit
#     "Claude hello probe failed. Exit code 1." Deshalb startet er hier in
#     %USERPROFILE%\.paperclip.
#  2) ANTHROPIC_* wird zusaetzlich aus der eigenen Umgebung entfernt, damit
#     nichts durchgereicht wird.

$ErrorActionPreference = 'Continue'
$logDir = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir 'paperclip-start.log'
$stempel = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

function Melden($text) { Add-Content -Path $log -Value "[$stempel] $text" -Encoding UTF8 }

# Laeuft schon?
$belegt = $false
try {
    $t = Test-NetConnection -ComputerName 127.0.0.1 -Port 3100 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($t) { $belegt = $true }
} catch { }

if ($belegt) {
    Melden 'Port 3100 belegt - Paperclip laeuft schon, kein Start.'
    exit 0
}

$arbeit = Join-Path $env:USERPROFILE '.paperclip'
if (-not (Test-Path $arbeit)) {
    Melden "Arbeitsverzeichnis fehlt: $arbeit - erst 'paperclipai onboard' fahren."
    exit 2
}

$cmd = Join-Path $env:USERPROFILE '.local\npm\paperclipai.cmd'
if (-not (Test-Path $cmd)) {
    Melden "paperclipai nicht gefunden: $cmd"
    exit 3
}

Remove-Item Env:ANTHROPIC_API_KEY, Env:ANTHROPIC_AUTH_TOKEN -ErrorAction SilentlyContinue

Melden "Start: $cmd run (Arbeitsverzeichnis $arbeit)"
# Die Ausgabe wird INNERHALB des cmd-Aufrufs umgeleitet. Mit -RedirectStandardOutput
# haelt der Start-Prozess die Handles des Kindes offen und der Aufrufer wartet ewig.
$out = Join-Path $logDir 'paperclip-stdout.log'
$err = Join-Path $logDir 'paperclip-stderr.log'
$zeile = "`"$cmd`" run >> `"$out`" 2>> `"$err`""
Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $zeile -WorkingDirectory $arbeit -WindowStyle Hidden

# Auf die Antwort warten (der erste Start braucht bis ~3 Minuten, spaeter ~40 s)
for ($i = 1; $i -le 60; $i++) {
    Start-Sleep -Seconds 5
    try {
        $r = Invoke-WebRequest -Uri 'http://127.0.0.1:3100/' -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) { Melden "Paperclip antwortet (HTTP 200) nach $($i * 5) s."; exit 0 }
    } catch { }
}
Melden 'Paperclip antwortet nach 300 s nicht - Logs unter Agenten\Routinen\logs\paperclip-*.log pruefen.'
exit 1