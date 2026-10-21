# Start des omnitrade2-Live-Laufs (XPERP, echtes Geld). Parameter stehen in
# lauf.json - EINE Quelle: nachziehen.py zieht dort von 1 auf 19 Kontrakte hoch.
#
# Freigaben sind Prozess-Env und gelten nur fuer diesen Lauf. Ohne
# OMNITRADE_MAINNET_APPROVED/OMNITRADE_PERP_MAINNET_APPROVED + --confirm-real-money
# verweigert die Engine den Mainnet-Start (siehe FAQ in der README des Repos).
$ErrorActionPreference = "Stop"
$hier = Split-Path -Parent $MyInvocation.MyCommand.Path
$wurzel = Resolve-Path (Join-Path $hier "..\..\..")
$wt = Join-Path $wurzel "Werkstatt\omnitrade-pr"
$out = Join-Path $wurzel "Agenten\Hermes\cache\omnitrade2"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$lauf = Get-Content (Join-Path $hier "lauf.json") -Raw | ConvertFrom-Json
$statusFile = Join-Path $out "sol-xperp-status.json"
$logFile = Join-Path $out "sol-xperp.log"
$errFile = Join-Path $out "sol-xperp-err.log"
$cli = Join-Path $wt "target\release\omnitrade-cli.exe"

if (-not (Test-Path $cli)) { Write-Output "Binary fehlt: $cli"; exit 5 }

# Doppelstart-Sperre: kein zweiter Lauf auf demselben Instrument.
$existing = Get-CimInstance Win32_Process -Filter "Name='omnitrade-cli.exe'" |
    Where-Object { $_.CommandLine -like "*$($lauf.inst)*" }
if ($existing) {
    Write-Output "Laeuft schon (PID $($existing.ProcessId)): kein zweiter Start."
    exit 2
}

# Not-Aus (fail closed)
$kill = Join-Path $env:TEMP "omnitrade.kill"
if (Test-Path $kill) { Write-Output "Not-Aus gesetzt ($kill): Start abgebrochen."; exit 3 }

$env:OKX_REGION = "eea"
$env:OMNITRADE_MAINNET_APPROVED = "1"
$env:OMNITRADE_PERP_MAINNET_APPROVED = "1"
$env:RUST_LOG = "info"

foreach ($n in @("OKX_API_KEY", "OKX_API_SECRET", "OKX_PASSPHRASE")) {
    $v = [Environment]::GetEnvironmentVariable($n, "User")
    if ([string]::IsNullOrEmpty($v)) { Write-Output "Zugang $n fehlt: Abbruch."; exit 4 }
}

$args = @(
    "live",
    "--exchange", "okx",
    "--network", $lauf.netz,
    "--symbol", $lauf.inst,
    "--script", (Join-Path $wt $lauf.strategie),
    "--interval", $lauf.interval,
    "--quantity", ([string]$lauf.quantity),
    "--initial-capital", ([string]$lauf.initial_capital),
    "--max-notional-usd", ([string]$lauf.max_notional_usd),
    "--confirm-real-money",
    "--allow-shorts",
    "--status-file", $statusFile
)

$p = Start-Process -FilePath $cli -ArgumentList $args -WorkingDirectory $wt `
    -RedirectStandardOutput $logFile -RedirectStandardError $errFile `
    -WindowStyle Hidden -PassThru
Write-Output ("GESTARTET PID {0} phase={1} quantity={2} inst={3}" -f $p.Id, $lauf.phase, $lauf.quantity, $lauf.inst)
Write-Output "Status: $statusFile"
