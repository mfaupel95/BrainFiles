# Startet die MoonDev-GUI (Schaltzentrale ueber moon-dev-ai-agents).
# Von der Aufgabenplanung/Startup beim Anmelden aufgerufen (+2 Min. Verzoegerung).
#
# WARUM: Die GUI ist die zentrale Steuerung fuer Boersen, Agenten und den
# RBI-Swarm. Nach jedem Neustart war sie weg und musste von Hand gestartet
# werden. Dieser Wrapper uebernimmt das.
#
# Laeuft schon eine MoonDev-GUI (auch eine von Hand gestartete), wird
# NICHTS gestartet: zwei Fenster zeigen dasselbe. Die Verzweigung steht im
# Protokoll.
#
# Gestartet wird pythonw.exe (fensterlos). Ein Fehler beim Aufbau landet in
# moongui-fehler.log.
#
# Hinweis PS 5.1: MainWindowTitle-Abfragen an fremde GUI-Prozesse koennen
# blockieren; deshalb wird der Fenstertitel nur EINMAL abgefragt und im
# Fehlerfall auf einen frischen pythonw-Prozess zurueckgegriffen.
#
# Erste Einrichtung / Neuaufsetzen:
# - Aufgabe (braucht einmalig Admin): moondev-gui-aufgabe.ps1
# - oder Startup-Verknuepfung: moondev-gui-autostart.vbs in den
#   Startup-Ordner des Benutzers (kein Admin).

$ErrorActionPreference = 'Stop'
$wurzel  = Split-Path $PSScriptRoot -Parent          # Agenten
$repos   = Join-Path (Split-Path $wurzel -Parent) 'Werkstatt'
$repo    = Join-Path $repos 'moon-dev-ai-agents'
$logs    = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$log       = Join-Path $logs 'moondev-gui-letzter-lauf.log'
$fehlerlog = Join-Path $logs 'moondev-gui-fehler.log'
$start     = Get-Date

# Bus-Anbindung: eine Routine ohne Meldung sieht im Journal wie ein
# ausgebliebener Lauf aus. Test test_anbindung_routinen verlangt Melde-Start,
# Melde-Ende an JEDEM Ausstieg und den Namen 'routine/moondev-gui'.
. (Join-Path $wurzel 'Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/moondev-gui' `
           -Log 'Agenten/Routinen/logs/moondev-gui-letzter-lauf.log'

function Schreib($text) {
    "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) $text" |
        Add-Content $log -Encoding UTF8
}

function Get-FensterPID {
    # Einmalige, schnelle Pruefung: laeuft schon eine MoonDev-GUI (auch von
    # Hand gestartet), wird nichts gestartet. MainWindowTitle kann in PS 5.1
    # blockieren, wenn der GUI-Thread gerade beschaeftigt ist.
    $p = Get-Process -Name python* -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -like '*MoonDev-GUI*' } |
        Select-Object -First 1
    if ($p) { return [int]$p.Id }
    return 0
}

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" |
    Set-Content $log -Encoding UTF8
try {
    $schon = Get-FensterPID
    if ($schon) {
        Schreib "Fenster laeuft schon (PID $schon), kein Start."
        "ENDE ok (nichts zu tun)" | Add-Content $log -Encoding UTF8
        Melde-Ende -Marke $marke -Code 0 -Text "laeuft bereits (PID $schon)"
        exit 0
    }

    if (-not (Test-Path $repo)) { throw "Repo fehlt: $repo" }
    $skript = Join-Path $repo 'moongui.py'
    if (-not (Test-Path $skript)) { throw "GUI fehlt: $skript" }
    $starter = Join-Path $repo '.venv\Scripts\pythonw.exe'
    if (-not (Test-Path $starter)) { throw "kein pythonw unter $starter" }

    Schreib "kein Fenster offen, starte $([IO.Path]::GetFileName($starter))"
    Remove-Item $fehlerlog -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $starter -ArgumentList $skript `
                  -WorkingDirectory $repo -PassThru `
                  -RedirectStandardError $fehlerlog | Out-Null

    # PID aus Start-Process ist der Launcher; pythonw startet als Kind.
    # Keine MainWindowTitle-Schleife (blockiert in PS 5.1), stattdessen kurz
    # warten und den Fenstertitel EINMAL pruefen.
    Start-Sleep -Seconds 3
    $pid_neu = Get-FensterPID
    if ($pid_neu) {
        Schreib "Fenster sichtbar (PID $pid_neu)."
        "ENDE ok (PID $pid_neu)" | Add-Content $log -Encoding UTF8
    } else {
        # Zweite Chance: Kindprozess von Start-Process lebt (pythonw)?
        $kind = Get-Process pythonw -ErrorAction SilentlyContinue |
            Where-Object { $_.StartTime -ge $start } |
            Select-Object -First 1
        if ($kind) {
            Schreib "pythonw laeuft (PID $($kind.Id)), Fenstertitel noch nicht sichtbar."
            "ENDE ok (PID $($kind.Id))" | Add-Content $log -Encoding UTF8
        } else {
            Schreib "Fenster nach 3 s nicht sichtbar, Fehlerlog pruefen."
            "ENDE FEHLER: Fenster nicht sichtbar" | Add-Content $log -Encoding UTF8
            Melde-Ende -Marke $marke -Code 1 -Text "Fenster nach 3 s nicht sichtbar"
            exit 1
        }
    }
} catch {
    Schreib "ENDE FEHLER: $_"
    "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
    Melde-Ende -Marke $marke -Code 1 -Text "$_"
    exit 1
}