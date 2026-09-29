# Bonsai 2 27B (ternary, PrismML-Fork von llama.cpp) lokal starten.
#
# Zweck: das 27B-Modell als OpenAI-kompatiblen Dienst auf 127.0.0.1 bereitstellen,
# damit Hermes (Provider `bonsai`), Skripte und Bots es wie jedes andere Modell nutzen.
#
# Wichtig: dieses Modell laeuft NUR mit dem PrismML-Fork von llama.cpp (eigene
# Ternary-Kernels + Hadamard-Aktivierung). Ollama kann die Dateien nicht laden,
# ein upgestreamtes llama.cpp laedt sie ohne Warnung und liefert Unsinn.
#
# Auf DIESEM Rechner gemessen (RTX 3060 Ti 8 GB, 25.09.2026, PTQ1_0):
#   Kontext  8192, -ngl 99: 32 t/s Erzeugung, 666 t/s Prompt (1942 T in 2,9 s)
#   Kontext 16384, -ngl 99: 10 t/s Erzeugung,  44 t/s Prompt (VRAM randvoll, 177 MiB frei)
#   Kontext 65536, -ngl 99, -fa on: 12 t/s Erzeugung, 85 t/s Prompt
#       (VRAM 7.772/253 MiB - passt also, dicht). 65536 ist deshalb die VORGABE:
#       HERMES VERLANGT 64K, sonst lehnt es das Modell als Agent-Modell ab
#       ("Model bonsai has a context window of 8,192 tokens, which is below the
#       minimum 64,000 required by Hermes Agent"). Fuer reine Chat-Aufrufe
#       (Sprachmodell-Spuren, llm_lokal) ist 8192 schneller und reicht:
#       -Kontext 8192. Der grosse Kontext frisst den Speicher, den die
#       Prompt-Verarbeitung braucht.
#
# Der Dienst ist ein Schwergewicht und wird NICHT bei jedem Start gebraucht: vor dem
# Start werden Ollama-Modelle aus dem VRAM entladen (sie laufen danach wieder, notfalls
# auf der CPU). Mit -OllamaBehalten bleibt das aus.
#
# Beispiele:
#   .\bonsai-27b.ps1                      # Status (Prozess, Port, VRAM)
#   .\bonsai-27b.ps1 -Aktion start        # starten (Kontext 8192)
#   .\bonsai-27b.ps1 -Aktion test         # ein echter Aufruf gegen den Dienst
#   .\bonsai-27b.ps1 -Aktion stopp

param(
    [ValidateSet('start', 'stopp', 'status', 'test', 'log')]
    [string]$Aktion = 'status',
    [int]$Kontext = 65536,
    [int]$GpuLayers = 99,
    [int]$Port = 8081,
    [string]$Reasoning = 'medium',
    [switch]$OllamaBehalten
)

$ErrorActionPreference = 'Continue'

$Bin        = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'Modelle\llama-prism\bin'
$Modell     = Join-Path $PSScriptRoot '..\..\Modelle\GGUF\Ternary-Bonsai-2-27B-PTQ1_0.gguf'
$Protokoll  = Join-Path $env:LOCALAPPDATA 'Temp\bonsai-27b-server.log'

function Get-ServerProzesse {
    # Nur UNSEREN Fork-Server zaehlen: Hermes betreibt daneben einen eigenen
    # llama-server (upgestreamte Bauart, Port 18434) - der kann dieses Modell nicht laden.
    Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*llama-prism*' }
}

function Get-Vram {
    $v = (& nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader 2>$null)
    if ($v) { $v.Trim() } else { 'unbekannt' }
}

function Get-PortOffen {
    # Test-NetConnection kann in PS 5.1 minutenlang haengen (Netzwerk-Inventar) - direkter Verbindungsversuch.
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $ok = $c.ConnectAsync('127.0.0.1', $Port).Wait(1500)
        $c.Close()
        return $ok
    } catch { return $false }
}

function Get-Antwortet {
    try {
        $r = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/props" -f $Port) -TimeoutSec 5 -UseBasicParsing
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

function Show-Status {
    $p = @(Get-ServerProzesse)
    if ($p.Count -eq 0) { Write-Output 'bonsai-27b: laeuft NICHT' }
    else {
        foreach ($x in $p) { Write-Output ("bonsai-27b: PID {0} seit {1}" -f $x.ProcessId, $x.CreationDate) }
        Write-Output ("Dienst antwortet: {0}" -f $(if (Get-Antwortet) { 'ja' } else { 'nein' }))
    }
    $sp = Get-PortOffen
    Write-Output ("Port {0}: {1}" -f $Port, $(if ($sp) { 'offen' } else { 'zu' }))
    Write-Output ("VRAM belegt/frei: {0}" -f (Get-Vram))
    if (Test-Path $Modell) {
        Write-Output ("Modell: {0} ({1} GB)" -f (Resolve-Path $Modell), [math]::Round((Get-Item $Modell).Length / 1GB, 2))
    } else { Write-Output ("Modell FEHLT: {0}" -f $Modell) }
}

if ($Aktion -eq 'status') { Show-Status; return }

if ($Aktion -eq 'log') {
    if (Test-Path $Protokoll) { Get-Content $Protokoll -Tail 40 } else { Write-Output "kein Protokoll: $Protokoll" }
    return
}

if ($Aktion -eq 'stopp') {
    $p = @(Get-ServerProzesse)
    if ($p.Count -eq 0) { Write-Output 'bonsai-27b: nichts zu stoppen'; return }
    foreach ($x in $p) { Stop-Process -Id $x.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
    Write-Output ("bonsai-27b: gestoppt ({0} Prozess(e))" -f $p.Count)
    Show-Status
    return
}

if ($Aktion -eq 'test') {
    if (-not (Get-Antwortet)) { Write-Output 'bonsai-27b: Dienst antwortet nicht - erst starten'; return }
    # max_tokens grosszuegig: das Modell denkt, und das Denken zaehlt gegen das Limit.
    $koerper = @{
        model            = 'bonsai'
        messages         = @(@{ role = 'user'; content = 'Antworte in genau einem kurzen Satz: Hauptstadt von Frankreich?' })
        max_tokens       = 1024
        temperature      = 1.0
        top_p            = 0.95
        top_k            = 20
        min_p            = 0.05
        reasoning_effort = $Reasoning
    } | ConvertTo-Json -Depth 5
    $uhr = Measure-Command {
        $r = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/v1/chat/completions" -f $Port) -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($koerper))
    }
    Write-Output ("Antwort: {0}" -f ($r.choices[0].message.content).Trim())
    Write-Output ("Dauer: {0:N1} s | Prompt {1} T | Antwort {2} T" -f $uhr.TotalSeconds, $r.usage.prompt_tokens, $r.usage.completion_tokens)
    $t = $r.timings
    if ($t) { Write-Output ("Server-Timings: prompt {0:N1} t/s, decode {1:N1} t/s" -f $t.prompt_per_second, $t.predicted_per_second) }
    return
}

# ---- start ----
if (-not (Test-Path (Join-Path $Bin 'llama-server.exe'))) { Write-Output "FEHLT: $Bin\llama-server.exe"; exit 1 }
if (-not (Test-Path $Modell)) { Write-Output "FEHLT: $Modell"; exit 1 }
if (@(Get-ServerProzesse).Count -gt 0) { Write-Output 'bonsai-27b: laeuft schon'; Show-Status; return }

if (-not $OllamaBehalten) {
    # Ollama-Modelle aus dem VRAM entladen - sie werden beim naechsten Aufruf neu geladen.
    $geladen = @(& ollama ps 2>$null | Select-Object -Skip 1 | ForEach-Object { ($_ -split '\s+')[0] } | Where-Object { $_ })
    foreach ($m in $geladen) {
        & ollama stop $m 2>$null | Out-Null
        Write-Output ("VRAM freigegeben: ollama stop {0}" -f $m)
    }
    Start-Sleep -Seconds 2
}

# Die JSON-Argumente muessen fuer llama.cpp mit \" ankommen, sonst zerlegt der
# Windows-Argumentparser die Anfuehrungszeichen und der Server bricht beim Start ab.
$chatKargs = '{\"reasoning_effort\":\"' + $Reasoning + '\"}'
$argumente = @(
    '-m', $Modell,
    '--alias', 'bonsai',
    '--host', '127.0.0.1', '--port', "$Port",
    '-ngl', "$GpuLayers",
    '-c', "$Kontext",
    '-np', '1',
    '-fa', 'on',
    '--jinja',
    '--chat-template-kwargs', $chatKargs,
    '--temp', '1.0', '--top-p', '0.95', '--top-k', '20', '--min-p', '0.05'
)
Write-Output ("bonsai-27b: starte, Kontext {0}, Gpu-Layer {1}, Port {2}, Protokoll {3}" -f $Kontext, $GpuLayers, $Port, $Protokoll)
$proc = Start-Process -FilePath (Join-Path $Bin 'llama-server.exe') -ArgumentList $argumente `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput $Protokoll -RedirectStandardError "$Protokoll.fehler"
Start-Sleep -Seconds 2
Write-Output ("gestartet, PID {0} - Laden dauert 10-30 s" -f $proc.Id)
$ok = $false
foreach ($i in 1..12) {
    Start-Sleep -Seconds 5
    if (Get-Antwortet) { $ok = $true; break }
    if ($proc.HasExited) { Write-Output 'Prozess ist beendet - Protokoll:'; Get-Content "$Protokoll.fehler" -Tail 15 -ErrorAction SilentlyContinue; return }
}
Write-Output ("Dienst antwortet: {0}" -f $(if ($ok) { 'ja' } else { 'noch nicht' }))
Show-Status