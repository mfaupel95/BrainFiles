# Auth-Sitzung eines Bot-Profils an die Wurzel koppeln (Symlink auf <HERMES_HOME>\auth.json).
#
# WARUM: Ein Profil ohne eigene auth.json ist eine Insel - es hat keine
# Modell-Anmeldung. Statt die Sitzung des Startprofils zu KOPIEREN (dieselbe
# Refresh-Kennung in vielen Dateien, eine Rotation entwertet die anderen),
# verweist das Profil per Symlink auf EINEN Store. Genau dafuer hat Hermes die
# Sperre und die "Peer hat rotiert, uebernimm seinen Token"-Logik
# (hermes_cli/auth.py::_nous_shared_store_lock); ein Symlink auf den Root-Store
# wird ausdruecklich als "kein Klon" behandelt (auth_oauth_grants.py:66).
#
# Symlinks brauchen auf Windows Adminrechte -> dieses Skript erhoeht starten.
#
#   powershell -NoProfile -File auth-verknuepfen.ps1              # Trockenlauf
#   powershell -NoProfile -File auth-verknuepfen.ps1 -Anwenden    # schreiben
#   powershell -NoProfile -File auth-verknuepfen.ps1 -Zuruecknehmen
param(
    [switch]$Anwenden,
    [switch]$Zuruecknehmen,
    [string]$Protokoll = ''
)

$ErrorActionPreference = 'Continue'
if ($Protokoll) { Start-Transcript -Path $Protokoll -Force | Out-Null }
$home_ = Split-Path $PSScriptRoot -Parent   # Agenten\Hermes (kein absoluter Benutzerpfad)
$root  = Join-Path $home_ 'auth.json'
$profDir = Join-Path $home_ 'profiles'

if (-not (Test-Path $root)) { Write-Output "Root-auth.json fehlt: $root"; exit 1 }

$angelegt = @(); $entfernt = @(); $uebersprungen = @()

foreach ($p in Get-ChildItem $profDir -Directory | Sort-Object Name) {
    if ($p.Name.StartsWith('.')) { continue }   # .deleted/.sicherung sind keine Profile
    $ziel = Join-Path $p.FullName 'auth.json'
    $item = Get-Item $ziel -Force -ErrorAction SilentlyContinue

    if ($Zuruecknehmen) {
        if ($item -and $item.LinkType -eq 'SymbolicLink') {
            $t = @($item.Target)[0]
            if ($t -eq $root) { Remove-Item $ziel -Force; $entfernt += $p.Name }
            else { $uebersprungen += "$($p.Name): zeigt woandershin ($t)" }
        }
        continue
    }

    if ($item -and $item.LinkType -eq 'SymbolicLink') {
        $t = @($item.Target)[0]
        if ($t -eq $root) { $uebersprungen += "$($p.Name): schon verknuepft"; continue }
        $uebersprungen += "$($p.Name): Symlink auf anderes Ziel - nicht angefasst"; continue
    }
    if ($item) {
        # eigene auth.json: eigene Anmeldung, bleibt unberuehrt
        $groesse = (Get-Item $ziel).Length
        $uebersprungen += "$($p.Name): eigene auth.json ($groesse B) - nicht angefasst"
        continue
    }

    if (-not $Anwenden) { $angelegt += $p.Name; continue }
    try {
        New-Item -ItemType SymbolicLink -Path $ziel -Target $root -ErrorAction Stop | Out-Null
        $angelegt += $p.Name
    } catch {
        $uebersprungen += "$($p.Name): FEHLER $($_.Exception.Message)"
    }
}

if ($Zuruecknehmen) {
    Write-Output ("Zurueckgenommen: " + ($(if ($entfernt) { $entfernt -join ', ' } else { 'nichts' })))
} elseif ($Anwenden) {
    Write-Output ("Angelegt: " + $angelegt.Count)
    $angelegt | ForEach-Object { Write-Output "  + $_" }
} else {
    Write-Output ("Waere anzulegen: " + $angelegt.Count)
    $angelegt | ForEach-Object { Write-Output "  + $_" }
    Write-Output "Trockenlauf - schreiben mit -Anwenden (erhoehte Shell)."
}
Write-Output ("Uebersprungen: " + $uebersprungen.Count)
$uebersprungen | ForEach-Object { Write-Output "  - $_" }

# Gegenprobe: jeder verknuepfte Store muss auf denselben Root zeigen
$verweise = @()
foreach ($p in Get-ChildItem $profDir -Directory) {
    $ziel = Join-Path $p.FullName 'auth.json'
    $i = Get-Item $ziel -Force -ErrorAction SilentlyContinue
    if (-not $i) { continue }
    if ($i.LinkType -eq 'SymbolicLink') {
        $t = @($i.Target)[0]
        $ok = 'NEIN'
        try { if ((Get-Item $ziel).Target -eq $root) { $ok = 'ja' } } catch { $ok = 'FEHLER' }
        $verweise += "$($p.Name) -> $t [$ok]"
    }
}
Write-Output "--- Verweise ---"
$verweise | ForEach-Object { Write-Output $_ }
if ($Protokoll) { Stop-Transcript | Out-Null }