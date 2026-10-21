#Requires -RunAsAdministrator
<#
  einmalig-20261011-docker-platten-kompaktieren.ps1

  Anlass: O: hat nur noch ~12 GB frei, die beiden Docker-Platten belegen dort 60 GB
  (DockerDesktop.vhdx 32 GB, docker_data.vhdx 27 GB). Sie schrumpfen nie von selbst.
  Das Skript beendet Docker/WSL, kompaktiert beide VHDX und startet Docker wieder.
  Es loescht keine Docker-Daten (Images, Volumes bleiben); nur ungenutzte Bloecke werden frei.

  Aufruf (Admin-Konsole):
    powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\einmalig-20261011-docker-platten-kompaktieren.ps1
  Mit -Testlauf werden nur Pfade und Groessen gezeigt.
#>
param([switch]$Testlauf)
$ErrorActionPreference = 'Continue'
$platten = 'O:\Modelle\DockerDesktopVMM\DockerDesktop.vhdx','O:\Modelle\DockerDesktopWSL\disk\docker_data.vhdx'
function GB($p){ [math]::Round((Get-Item -LiteralPath $p).Length/1GB,1) }
foreach($p in $platten){ if(-not (Test-Path -LiteralPath $p)){ Write-Output "FEHLT $p"; exit 1 } ; Write-Output ("VOR     {0} GB  {1}" -f (GB $p),$p) }
Write-Output ("O: frei vorher {0} GB" -f [math]::Round((Get-PSDrive O).Free/1GB,1))
if($Testlauf){ Write-Output 'Testlauf - nichts geaendert.'; exit 0 }
# Laufende Container merken, damit sie nach dem Neustart wieder hochkommen (Freqtrade-Bots u. a.)
$merkDatei = Join-Path $PSScriptRoot 'einmalig-20261011-container-liste.txt'
$laufend = @(docker ps --format '{{.Names}}' 2>$null)
$laufend | Set-Content -LiteralPath $merkDatei -Encoding UTF8
Write-Output ("Gemerkt: {0} laufende Container -> {1}" -f $laufend.Count,$merkDatei)
if($laufend.Count -gt 0){ docker stop $laufend 2>&1 | Out-Null }
Get-Process 'Docker Desktop','com.docker.backend' -ErrorAction SilentlyContinue | Stop-Process -Force
wsl --shutdown
Start-Sleep -Seconds 8
foreach($p in $platten){
  try { Optimize-VHD -Path $p -Mode Full -ErrorAction Stop; Write-Output ("NACH    {0} GB  {1}" -f (GB $p),$p) }
  catch { Write-Output "FEHLER  $p : $($_.Exception.Message)" }
}
Write-Output ("O: frei nachher {0} GB" -f [math]::Round((Get-PSDrive O).Free/1GB,1))
$d = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
if(Test-Path $d){ Start-Process $d; Write-Output 'Docker Desktop gestartet.' }
for($i=0;$i -lt 36;$i++){ docker info 2>$null | Out-Null; if($LASTEXITCODE -eq 0){ break }; Start-Sleep -Seconds 5 }
if($LASTEXITCODE -ne 0){ Write-Output "Docker antwortet nicht - Container von Hand starten, Liste: $merkDatei"; exit 1 }
foreach($c in $laufend){ docker start $c 2>&1 | Out-Null; Write-Output ("{0}  {1}" -f $(if($LASTEXITCODE -eq 0){'START  '}else{'FEHLER '}),$c) }
Write-Output ('Fertig: {0} Container wieder gestartet.' -f $laufend.Count)
