#Requires -RunAsAdministrator
<#
  docker-platten-kompaktieren.ps1 - monatliche Routine (seit 11.10.2026)

  Anlass: einmaliger Lauf am 11.10.2026 holte 14 GB auf O: zurueck (8,8 -> 22,7 GB
  frei); docker_data.vhdx war in Tagen von 27 auf 36 GB gewachsen. VHDX schrumpfen
  nie von selbst. Diese Routine kompaktiert NUR, wenn O: unter -SchwelleGB faellt.
  Ablauf wie der Einmal-Lauf: Container merken/stoppen, Docker+WSL aus,
  Optimize-VHD Full, Docker an, gemerkte Container wieder starten.
  Loescht keine Images/Volumes. Log: Werkstatt\Logs\docker-platten.log

  Einrichten (einmal, Admin): docker-platten-kompaktieren-einrichten.ps1
  Von Hand: powershell -NoProfile -ExecutionPolicy Bypass -File <dieses Skript> [-Testlauf] [-Erzwingen]
#>
param([switch]$Testlauf, [switch]$Erzwingen, [double]$SchwelleGB = 15)
$ErrorActionPreference = 'Continue'
$wurzel = Split-Path (Split-Path $PSScriptRoot)
$logDir = Join-Path $wurzel 'Werkstatt\Logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir 'docker-platten.log'
function L($t){ $z = "{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm'), $t; Write-Output $z; Add-Content -LiteralPath $log -Value $z -Encoding UTF8 }

$platten = 'O:\Modelle\DockerDesktopVMM\DockerDesktop.vhdx','O:\Modelle\DockerDesktopWSL\disk\docker_data.vhdx'
function GB($p){ [math]::Round((Get-Item -LiteralPath $p).Length/1GB,1) }
function Frei(){ [math]::Round((Get-PSDrive O).Free/1GB,1) }

foreach($p in $platten){ if(-not (Test-Path -LiteralPath $p)){ L "FEHLT $p"; exit 1 }; L ("VOR     {0} GB  {1}" -f (GB $p),$p) }
$frei = Frei
L "O: frei $frei GB (Schwelle $SchwelleGB GB)"
if($frei -ge $SchwelleGB -and -not $Erzwingen){ L 'genug Platz - nichts zu tun'; exit 0 }
if($Testlauf){ L 'Testlauf - wuerde jetzt kompaktieren, nichts geaendert'; exit 0 }

$merkDatei = Join-Path $logDir 'docker-platten-container.txt'
$laufend = @(docker ps --format '{{.Names}}' 2>$null)
$laufend | Set-Content -LiteralPath $merkDatei -Encoding UTF8
L ("{0} laufende Container gemerkt -> {1}" -f $laufend.Count,$merkDatei)
if($laufend.Count -gt 0){ docker stop $laufend 2>&1 | Out-Null }
Get-Process 'Docker Desktop','com.docker.backend' -ErrorAction SilentlyContinue | Stop-Process -Force
wsl --shutdown
Start-Sleep -Seconds 8
foreach($p in $platten){
  try { Optimize-VHD -Path $p -Mode Full -ErrorAction Stop; L ("NACH    {0} GB  {1}" -f (GB $p),$p) }
  catch { L "FEHLER  $p : $($_.Exception.Message)" }
}
L "O: frei nachher $(Frei) GB"
$d = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
if(Test-Path $d){ Start-Process $d; L 'Docker Desktop gestartet' }
for($i=0;$i -lt 36;$i++){ docker info 2>$null | Out-Null; if($LASTEXITCODE -eq 0){ break }; Start-Sleep -Seconds 5 }
if($LASTEXITCODE -ne 0){ L "Docker antwortet nicht - Container von Hand starten, Liste: $merkDatei"; exit 1 }
$fehler = 0
foreach($c in $laufend){ docker start $c 2>&1 | Out-Null; if($LASTEXITCODE -ne 0){ $fehler++; L "FEHLER Start $c" } }
L ("Fertig: {0} von {1} Container wieder gestartet" -f ($laufend.Count-$fehler),$laufend.Count)
if($fehler){ exit 1 }
