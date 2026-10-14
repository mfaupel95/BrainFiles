# jev-trader-start.ps1 — Start/Waechter des Jev-Trader-Live-Bots (Monad, Kuru MON-USDC).
# Anker: Agenten/Routinen -> BrainFiles-Wurzel, Bot-Ordner: Werkstatt/jev-trader.
# Einzelinstanz: startet nur, wenn kein bun-Prozess mit src/index.ts laeuft, sonst Exit 0.
# Aufruffrequenz: geplante Aufgabe MaxHirn-Jev-Trader (Logon + alle 15 min, IgnoreNew).
$ErrorActionPreference = 'Continue'
$Wurzel  = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # BrainFiles
$BotDir  = Join-Path $Wurzel 'Werkstatt\jev-trader'
$Bun     = 'C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\tools\bun\bun.exe'
$PidFile = Join-Path (Join-Path $Wurzel 'Agenten\Hermes\cache') 'jev-trader.pid'
$LogDir  = Join-Path $Wurzel 'Agenten\Routinen\logs'
$OutLog  = Join-Path $LogDir 'jev-trader.out.log'
$ErrLog  = Join-Path $LogDir 'jev-trader.err.log'

# Bereits laufend? Dann nichts tun (Doppelorder-Risiko vermeiden).
$laeuft = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^bun' -and $_.CommandLine -match 'src/index.ts' }
if ($laeuft) {
  Write-Output "jev-trader laeuft schon (PID $($laeuft.ProcessId))"
  exit 0
}

if (-not (Test-Path -LiteralPath $Bun)) { Write-Output "bun fehlt: $Bun"; exit 2 }
if (-not (Test-Path -LiteralPath $BotDir)) { Write-Output "Bot-Ordner fehlt: $BotDir"; exit 2 }

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$p = Start-Process -FilePath $Bun -ArgumentList 'run','src/index.ts' `
  -WorkingDirectory $BotDir -WindowStyle Hidden `
  -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog -PassThru
"$($p.Id) $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')" | Out-File -Encoding ascii $PidFile -Force
Write-Output "jev-trader gestartet (PID $($p.Id))"
