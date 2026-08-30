# Der Rest des Umbaus -- laeuft NICHT aus einer Claude-Sitzung heraus.
#
# Warum getrennt: Claude Desktop startet 21 MCP-Server-Prozesse aus
# MaxHirn\MCP-Server. Windows verweigert das Umbenennen eines Ordners, unter
# dem eine laufende .exe liegt. Eine Sitzung kann sich nicht selbst umziehen.
#
# SO WIRD ES BENUTZT
#   1. Claude Desktop beenden (ganz -- auch das Symbol im Infobereich).
#   2. Codex beenden, falls offen.
#   3. Ein normales PowerShell-Fenster oeffnen und starten:
#
#        & "$env:USERPROFILE\Documents\BrainFiles\MaxHirn\Routinen\umzug\UMZUG-OFFLINE.ps1" -Echt
#
#   4. Danach Claude Desktop wieder starten. Die Server melden sich aus dem
#      neuen Ordner.
#
# Ohne -Echt laufen alle vier Schritte als Trockenlauf: nichts wird veraendert,
# aber jede Zahl steht schon da.

param([switch]$Echt)

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
if ((Split-Path $wurzel -Leaf) -ne 'BrainFiles') { $wurzel = "$env:USERPROFILE\Documents\BrainFiles" }

function Titel($t) {
    Write-Host ''
    Write-Host ('=' * 72) -ForegroundColor Cyan
    Write-Host "  $t" -ForegroundColor Cyan
    Write-Host ('=' * 72) -ForegroundColor Cyan
}

# --- Vorbedingung ----------------------------------------------------------
$laeuft = Get-Process -Name 'Claude', 'codex' -ErrorAction SilentlyContinue
$ausVault = Get-Process | Where-Object { $_.Path -like "$wurzel\MaxHirn\MCP-Server*" }
if ($laeuft -or $ausVault) {
    Write-Host ''
    Write-Host 'ABBRUCH: es laufen noch Programme aus dem Umzugsgebiet.' -ForegroundColor Red
    if ($laeuft)   { Write-Host "  Claude Desktop / Codex: $($laeuft.Count) Prozesse" -ForegroundColor Red }
    if ($ausVault) { Write-Host "  MCP-Server aus MaxHirn: $($ausVault.Count) Prozesse" -ForegroundColor Red }
    Write-Host ''
    Write-Host 'Erst beide Programme beenden, dann dieses Skript erneut starten.' -ForegroundColor Yellow
    return
}

# --- Die vier Schritte -----------------------------------------------------
# Nach Schritt 3 liegt der Ordner an neuer Stelle - die Pfade werden deshalb
# jedes Mal frisch bestimmt statt einmal am Anfang.
function Skript($name) {
    foreach ($k in @("$wurzel\Agenten\Routinen\umzug\$name", "$wurzel\MaxHirn\Routinen\umzug\$name")) {
        if (Test-Path $k) { return $k }
    }
    throw "Skript $name nicht gefunden."
}

Titel 'Phase 3 -- Agenten: MCP-Server, Hermes, Handel, Routinen'
& (Skript '30-agenten.ps1') -Echt:$Echt

Titel 'Phase 5 -- Claude/ heisst Archiv/'
& (Skript '50-archiv.ps1') -Echt:$Echt

Titel 'Phase 8 -- Sicherung auf die neue Struktur'
& (Skript '80-sicherung.ps1') -Echt:$Echt

Titel 'Phase 9 -- Pruefung'
& (Skript '90-pruefen.ps1')

Write-Host ''
Write-Host 'Fertig. Jetzt Claude Desktop wieder starten.' -ForegroundColor Green
Write-Host 'Was rot geblieben ist, gehoert in die naechste Sitzung.' -ForegroundColor Yellow
Write-Host ''
Write-Host 'Die Sicherung ist noch NICHT bestaetigt - sie zaehlt erst nach einem' -ForegroundColor Yellow
Write-Host 'echten Lauf:  & "<Agenten>\Routinen\umzug\80-sicherung.ps1" -Echt -Lauf' -ForegroundColor Yellow
