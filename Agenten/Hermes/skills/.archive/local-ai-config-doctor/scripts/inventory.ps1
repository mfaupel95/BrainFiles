# Bestandsaufnahme fuer ein lokal installiertes KI-Werkzeug.
#
# Aufruf:
#   powershell -NoProfile -ExecutionPolicy Bypass -File inventory.ps1 -Name hermes
#   powershell -NoProfile -ExecutionPolicy Bypass -File inventory.ps1 -Name claude -Depth 4
#
# Gibt aus: Prozesse, Dateitreffer, Config-Verzeichnisse, Umgebungsvariablen
# (User + Machine) und - falls -EnvFile angegeben - die Schluesselnamen einer
# .env samt Wertlaenge. Werte werden NIE ausgegeben.
#
# Alles ist read-only. Fehler werden unterdrueckt, damit ein gesperrter
# Unterordner den Lauf nicht abbricht.

param(
    [Parameter(Mandatory = $true)][string]$Name,
    [int]$Depth = 3,
    [string]$EnvFile = ''
)

$ErrorActionPreference = 'SilentlyContinue'
$home_dir = $env:USERPROFILE

function Section($t) { Write-Output ''; Write-Output ('=== ' + $t + ' ===') }

Section 'PROZESSE'
$procs = Get-Process | Where-Object { $_.ProcessName -like ('*' + $Name + '*') }
if ($procs) {
    $procs | Select-Object ProcessName, Id, @{N = 'Pfad'; E = { $_.Path } } | Format-Table -AutoSize
} else {
    Write-Output ('Kein laufender Prozess mit Namensbestandteil "' + $Name + '"')
}

Section ('DATEITREFFER (Tiefe ' + $Depth + ')')
Get-ChildItem -Path $home_dir -Filter ('*' + $Name + '*') -Recurse -Depth $Depth |
    Select-Object -First 40 |
    Select-Object @{N = 'Typ'; E = { if ($_.PSIsContainer) { 'DIR' } else { 'FILE' } } },
                  LastWriteTime, Length, FullName |
    Format-Table -AutoSize

Section 'CONFIG-VERZEICHNISSE'
$roots = @(
    (Join-Path $env:APPDATA      $Name),
    (Join-Path $env:LOCALAPPDATA $Name),
    (Join-Path $home_dir ('.' + $Name)),
    (Join-Path $home_dir (Join-Path '.config' $Name))
)
foreach ($r in $roots) {
    if (Test-Path $r) {
        Write-Output ('--- ' + $r)
        Get-ChildItem $r -Force |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 25 LastWriteTime, Length, Name |
            Format-Table -AutoSize
    } else {
        Write-Output ('(nicht vorhanden) ' + $r)
    }
}

Section 'UMGEBUNGSVARIABLEN'
foreach ($scope in @('User', 'Machine')) {
    $vars = [Environment]::GetEnvironmentVariables($scope).GetEnumerator() |
        Where-Object { $_.Name -like ('*' + $Name + '*') -or $_.Value -like ('*' + $Name + '*') }
    if ($vars) {
        Write-Output ('--- Scope ' + $scope)
        $vars | Select-Object Name, Value | Format-Table -AutoSize
    } else {
        Write-Output ('Scope ' + $scope + ': keine Treffer')
    }
}
Write-Output '--- Im AKTUELLEN Prozess sichtbar (kann abweichen!)'
Get-ChildItem Env: | Where-Object { $_.Name -like ('*' + $Name + '*') } |
    Select-Object Name, Value | Format-Table -AutoSize

if ($EnvFile -and (Test-Path $EnvFile)) {
    Section 'ENV-DATEI (Werte maskiert)'
    Get-Content $EnvFile | ForEach-Object {
        $l = $_.Trim()
        if ($l -match '^\s*#' -or $l -eq '') { return }
        if ($l -notmatch '^[A-Za-z_][A-Za-z0-9_]*=') { return }
        $p = $l -split '=', 2
        $len = 0
        if ($p[1]) { $len = $p[1].Trim().Trim('"').Length }
        Write-Output ($p[0] + ' -> Laenge ' + $len)
    }
}

Section 'FERTIG'
Write-Output 'Naechster Schritt: effektive Instanz bestimmen (Home-Variable, aktives Profil),'
Write-Output 'erst danach die Selbstpruefung des Werkzeugs ausfuehren.'
