# Startet den Nautilus-Quoten-Container (nautilus-demo) nach Rechnerstart.
#
# Docker Desktop startet bei Anmeldung (Autostart-Eintrag in HKCU\Run) und
# der Container hat --restart unless-stopped - der Normalfall ist also
# abgedeckt. Diese Aufgabe faengt den Restfall ab: Docker Desktop laeuft,
# aber der Container ist nicht hochgekommen (z.B. weil Docker beim ersten
# Start noch nicht bereit war). Idempotent: laeuft der Container schon,
# passiert nichts.
#
# Geplante Aufgabe: MaxHirn-Nautilus-Docker (Anmeldung + 2 Min, versteckt,
# IgnoreNew). Log: Agenten\Routinen\logs\nautilus-docker-start.log

$ErrorActionPreference = 'Continue'   # stderr von docker zaehlt sonst als Fehler
$log = Join-Path $PSScriptRoot 'logs\nautilus-docker-start.log'
$ts  = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

function Log($m) { "$ts $m" | Out-File -FilePath $log -Append -Encoding utf8 }

# Bus-Anbindung: jede Routine meldet Start und Ende (test_anbindung_routinen).
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/nautilus-docker-start'

# 1) Warten, bis der Docker-Daemon erreichbar ist (max. 120 s).
$bereit = $false
for ($i = 0; $i -lt 24; $i++) {
  docker info *> $null
  if ($LASTEXITCODE -eq 0) { $bereit = $true; break }
  Start-Sleep -Seconds 5
}
if (-not $bereit) {
  Log "Docker-Daemon nach 120 s nicht erreichbar - Container nicht gestartet."
  Melde-Ende -Marke $marke -Code 0 -Text "Docker-Daemon nach 120 s nicht erreichbar"
  exit 0
}

# 2) Container-Status pruefen und ggf. starten.
$c = docker ps -a --filter "name=nautilus-demo" --format "{{.Names}}|{{.Status}}" 2>$null
if (-not $c) {
  Log "Container nautilus-demo existiert nicht - Image bauen und starten."
  docker build -t nautilus-demo-node:1.231.0 (Join-Path $PSScriptRoot '..\Handel\nautilus') *> $null
  docker run -d --name nautilus-demo --restart unless-stopped `
    -e OKX_API_KEY=dummy-node-key `
    -e OKX_API_SECRET=dummy-node-secret `
    -e OKX_API_PASSPHRASE=dummy-node-pass `
    nautilus-demo-node:1.231.0 *> $null
  Log "Container neu erstellt und gestartet."
} elseif ($c -match 'Exited|Dead|Created') {
  docker start nautilus-demo *> $null
  Log "Container war '$c' - neu gestartet."
} else {
  Log "Container laeuft bereits: $c"
}
Melde-Ende -Marke $marke -Code 0
exit 0