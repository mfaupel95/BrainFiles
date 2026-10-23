# jev-trader-hl-livetest-start.ps1 - Live-Test des Jev-Traders auf Hyperliquid TESTNET.
# Sicherheitskette, JEDER Punkt bricht ab BEVOR etwas startet:
#   1) HL_TESTNET=true ist zwingend (nie Mainnet aus diesem Weg)
#   2) DRY_RUN=false ist zwingend (sonst waere es nur die Trocken-Kopie)
#   3) Wallet braucht USDC auf HL-Testnet (Faucet), sonst scheitert jede Order
#   4) Einzelinstanz: kein zweiter Live-Test-Prozess
# Start NUR auf ausdrueckliches Wort von Max (Live nur auf Befehl).
# Anker: Agenten/Routinen -> BrainFiles-Wurzel.
$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot '..\Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/jev-trader-hl-livetest-start'
$Wurzel = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # BrainFiles
$Bun    = 'C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\tools\bun\bun.exe'
$WT     = Join-Path $Wurzel 'Werkstatt\jev-trader-hl-livetest'
$EnvLive = Join-Path $WT '.env.live'
$EnvAktiv = Join-Path $WT '.env'
$PidFile = Join-Path (Join-Path $Wurzel 'Agenten\Hermes\cache') 'jev-trader-hl.pid'
$OutLog  = Join-Path (Join-Path $Wurzel 'Agenten\Routinen\logs') 'jev-trader-hl.out.log'

# [1]+[2] Env lesen (nur Werte der Nicht-Geheimnisse)
$envWerte = @{}
foreach ($z in (Get-Content -LiteralPath $EnvLive)) {
  if ($z -match '^\s*([A-Z_0-9]+)\s*=\s*(.*)$') { $envWerte[$matches[1]] = $matches[2] }
}
if ($envWerte['HL_TESTNET'] -ne 'true') { Write-Output "ABBRUCH: HL_TESTNET ist nicht 'true' - dieser Weg geht NUR aufs Testnet."; Melde-Ende -Marke $marke -Code 1 -Text 'HL_TESTNET nicht true'; exit 1 }
if ($envWerte['DRY_RUN'] -ne 'false') { Write-Output "ABBRUCH: DRY_RUN ist nicht 'false' - waere nur ein Trockenlauf."; Melde-Ende -Marke $marke -Code 1 -Text 'DRY_RUN nicht false'; exit 1 }
if ($envWerte['ENGINE'] -ne 'hyperliquid') { Write-Output "ABBRUCH: ENGINE ist nicht 'hyperliquid'."; Melde-Ende -Marke $marke -Code 1 -Text 'ENGINE nicht hyperliquid'; exit 1 }

# [3] Wallet-Guthaben auf HL-Testnet
$probe = & $Bun --env-file=$EnvLive run (Join-Path $WT 'hl_guthaben.ts') 2>$null
$g = $probe | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $null -eq $g -or $g.accountValue -le 0) {
  Write-Output "ABBRUCH: Wallet $($g.user) hat $($g.accountValue) USDC auf HL-Testnet (Faucet noetig: https://app.hyperliquid-testnet.xyz)."
  Melde-Ende -Marke $marke -Code 1 -Text 'Wallet ohne Guthaben'
  exit 1
}

# [4] Einzelinstanz
$laeuft = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^bun' -and $_.CommandLine -match 'jev-trader-hl-livetest' }
if ($laeuft) { Write-Output "Live-Test laeuft schon (PID $($laeuft.ProcessId))"; Melde-Ende -Marke $marke -Code 0 -Text 'laeuft bereits'; exit 0 }

# Start: .env.live wird zu .env (bun laedt sie automatisch aus dem CWD)
Move-Item -LiteralPath $EnvLive -Destination $EnvAktiv -Force
$p = Start-Process -FilePath $Bun -ArgumentList 'run','src/index.ts' `
  -WorkingDirectory $WT -WindowStyle Hidden `
  -RedirectStandardOutput $OutLog -RedirectStandardError (Join-Path (Join-Path $Wurzel 'Agenten\Routinen\logs') 'jev-trader-hl.err.log') -PassThru
"$($p.Id) $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')" | Out-File -Encoding ascii $PidFile -Force
Write-Output "Jev-Trader HL-Live-Test gestartet (PID $($p.Id)) - PORT $($envWerte['PORT']), Coin $($envWerte['HL_COIN']), Hebel $($envWerte['HL_LEVERAGE'])x"
Melde-Ende -Marke $marke -Code 0 -Text "gestartet PID $($p.Id)"
