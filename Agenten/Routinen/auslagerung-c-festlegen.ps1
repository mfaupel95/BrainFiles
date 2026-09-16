# auslagerung-c-festlegen.ps1
# Einmalige Admin-Aktion vom 16.09.2026 (Systemdiagnose):
#   - C:-Auslagerungsdatei von "systemverwaltet" (40 GB belegt, ~200 MB benutzt)
#     auf feste 8192 MB setzen -> ~32 GB C: frei
#   - Ruhezustand ausschalten (powercfg /h off loescht hiberfil.sys sofort,
#     12,7 GB) -- nur wenn Max Hibernate nicht nutzt (vereinbart)
#   - O:-Pagefile-Eintrag (4096/16384) bleibt unangetastet
# Wirkt voll erst nach Neustart (neue Auslagerungsgroesse greift beim naechsten Boot).
$ErrorActionPreference = 'Stop'

$logDir = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir 'auslagerung-festlegen.log'
function Log($m) {
    $line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $m
    Add-Content -Path $log -Value $line -Encoding UTF8
    Write-Output $line
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Log "Start (Admin: $isAdmin)"
if (-not $isAdmin) { Log 'ABBruch: nicht als Administrator gestartet.'; exit 1 }

$freiVorher = [math]::Round((Get-PSDrive C).Free/1GB, 2)
Log "C: frei vorher: $freiVorher GB (pagefile.sys + hiberfil.sys existieren, s. Diagnose)"

# 1) Ruhezustand aus (loescht C:\hiberfil.sys sofort, kein Neustart noetig)
powercfg /h off | Out-Null
if ($LASTEXITCODE -eq 0) { Log 'powercfg /h off: OK' } else { Log "powercfg /h off: Exit-Code $LASTEXITCODE" }
if (Test-Path 'C:\hiberfil.sys') { Log 'WARNUNG: hiberfil.sys existiert noch (evtl. von anderem Prozess gesperrt)' }
else { Log 'hiberfil.sys: entfernt' }

# 2) PagingFiles: C:-Zeile auf fest 8192/8192, alle anderen Zeilen (O:) behalten
$key = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management'
$aktuell = (Get-ItemProperty -Path $key -Name 'PagingFiles' -ErrorAction SilentlyContinue).PagingFiles
if (-not $aktuell) { $aktuell = @() }
elseif ($aktuell -is [string]) { $aktuell = @($aktuell) }
Log ('PagingFiles aktuell : ' + ($aktuell -join ' | '))

$neu = @()
foreach ($zeile in $aktuell) {
    if ($zeile -match '^C:\\pagefile\.sys') { $neu += 'C:\pagefile.sys 8192 8192' }
    else { $neu += $zeile }
}
if (-not ($neu -contains 'C:\pagefile.sys 8192 8192')) { $neu += 'C:\pagefile.sys 8192 8192' }
Set-ItemProperty -Path $key -Name 'PagingFiles' -Value $neu -Type MultiString

$geprueft = (Get-ItemProperty -Path $key -Name 'PagingFiles').PagingFiles
if ($geprueft -is [string]) { $geprueft = @($geprueft) }
Log ('PagingFiles gesetzt  : ' + ($geprueft -join ' | '))

$freiNachher = [math]::Round((Get-PSDrive C).Free/1GB, 2)
$diff = [math]::Round($freiNachher - $freiVorher, 2)
Log "C: frei nachher: $freiNachher GB (Differenz: $diff GB, kommt vom hiberfil-Loeschvorgang)"
Log 'FERTIG. Neustart noetig: erst beim naechsten Boot gilt die 8-GB-Auslagerung, C: hat dann ~32 GB mehr.'