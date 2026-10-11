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
