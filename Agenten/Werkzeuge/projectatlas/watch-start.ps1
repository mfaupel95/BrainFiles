# ProjectAtlas-Watcher starten (idempotent).
#
# Was er tut: Er beobachtet EIN Repository und zieht dessen Atlas nach, wenn
# sich Dateien aendern (gemessen 15.09.2026: eine neue Datei war nach 40 s im
# Index). Ohne ihn veraltet die Karte still - sie ist nur so aktuell wie der
# letzte Scan.
#
# Aufruf:
#   powershell -File Agenten\Werkzeuge\projectatlas\watch-start.ps1
#   powershell -File Agenten\Werkzeuge\projectatlas\watch-start.ps1 -Repo "O:\Werkstatt\omnitrade"
#
# Laeuft schon einer, tut das Skript nichts und sagt es (Exit 0) - so kann es
# bei jeder Anmeldung laufen, ohne Doppelprozesse zu erzeugen.
#
# FALLE (gemessen, kostete zwei Timeouts): `Start-Process -RedirectStandardOutput`
# blockiert den Aufrufer, bis der Kindprozess ENDET - bei einem Dauerprozess
# also nie. Deshalb startet hier `cmd.exe /c ... > log 2>&1`: die Umleitung
# macht die Shell, `Start-Process` kehrt sofort zurueck. Die PID wird danach
# aus dem Delta der projectatlas-Prozesse gelesen.
#
# Warum eine PID-Datei und nicht `projectatlas watch-status`: watch-status
# meldet auch bei laufendem Watcher `active: false` - es beschreibt einen
# Refresh-Durchgang, nicht den Prozess. Und die Pruefung ueber
# Win32_Process/CommandLine braucht bei diesem Prozessbaum Minuten.
#
# Warum nicht aus einer Agentensitzung heraus: der Watcher ist ein
# Dauerprozess, ein Kindprozess der Sitzung stirbt mit ihr. Im Dauerbetrieb
# haelt ihn der Hermes-Cron `atlas-watcher` (alle 15 Min, scripts/atlas-watcher.py).
param(
    [string]$Repo = 'O:\Werkstatt\omnitrade'
)
$ErrorActionPreference = 'Continue'
$Hier = Split-Path -Parent $MyInvocation.MyCommand.Path
$Exe = Join-Path $Hier 'bin\projectatlas.exe'
$Log = Join-Path $Hier 'logs'
New-Item -ItemType Directory -Force -Path $Log | Out-Null

$Name = Split-Path -Leaf $Repo
$PidDatei = Join-Path $Log "watch-$Name.pid"

if (-not (Test-Path $Exe)) { Write-Output "FEHLER: $Exe fehlt"; exit 2 }
if (-not (Test-Path (Join-Path $Repo '.projectatlas'))) {
    Write-Output "FEHLER: $Repo ist nicht kartiert (kein .projectatlas) - erst init"
    exit 2
}

# Laeuft schon einer? Der Eintrag in der PID-Datei zaehlt, wenn der Prozess
# MIT DEM RICHTIGEN NAMEN lebt. Die Namenspruefung ist keine Feinheit:
# Windows vergibt PIDs neu, und eine besetzte PID sieht genau so aus wie
# ein gesunder Watcher (03.10.2026 gemessen: PID 69928 war ein toter
# Watcher, die PID war inzwischen an svchost.exe vergeben). Der Waechter hat
# daraufhin bei jedem Lauf neu gestartet - 18 haengende Prozesse.
if (Test-Path $PidDatei) {
    $alt = (Get-Content $PidDatei -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($alt) {
        $p = Get-Process -Id $alt -ErrorAction SilentlyContinue
        if ($p -and $p.ProcessName -eq 'projectatlas') {
            Write-Output "laeuft schon: PID $alt auf $Repo"
            exit 0
        }
        $wer = if ($p) { " - inzwischen " + $p.ProcessName } else { "" }
        Write-Output ("PID-Datei war verwaist (" + $alt + $wer + ") - starte neu")
    }
}

$vorher = @(Get-Process projectatlas -ErrorAction SilentlyContinue |
            ForEach-Object { $_.Id })

# Der Start laeuft ueber eine .cmd: `Start-Process -RedirectStandardOutput`
# blockiert bei einem Dauerprozess (der Aufrufer wartet auf das Ende des
# Kindes), und ein direktes cmd-Kommando mit Umleitung scheiterte still.
# Die .cmd macht die Umleitung selbst und kehrt sofort zurueck.
$CmdDatei = Join-Path $Hier ("watch-{0}.cmd" -f $Name)
if (-not (Test-Path $CmdDatei)) {
    Write-Output "FEHLER: Starter fehlt: $CmdDatei (eine .cmd je Repo)"
    exit 2
}
Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', $CmdDatei) -WindowStyle Hidden
Start-Sleep -Seconds 8

$neu = @(Get-Process projectatlas -ErrorAction SilentlyContinue |
         Where-Object { $vorher -notcontains $_.Id })
if ($neu.Count -eq 0) {
    Write-Output ("FEHLER: Watcher kam nicht hoch - Log ansehen: " +
                  (Join-Path $Log ("watch-$Name.log")))
    exit 1
}
$pid_ = ($neu | Sort-Object StartTime -Descending | Select-Object -First 1).Id
Set-Content -Path $PidDatei -Value $pid_ -Encoding ascii
Write-Output "gestartet: PID $pid_ auf $Repo"
Write-Output "Log: $(Join-Path $Log ("watch-$Name.log"))"
if ($neu.Count -gt 1) {
    Write-Output ("HINWEIS: " + $neu.Count + " neue projectatlas-Prozesse - PIDs " + (($neu | ForEach-Object { $_.Id }) -join ', '))
}
exit 0
