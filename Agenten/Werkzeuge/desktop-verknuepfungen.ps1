# Desktop-Verknuepfungen fuer die UI-Fenster dieses Rechners (30.09.2026).
#
# Aufruf (idempotent, ersetzt vorhandene Verknuepfungen gleichen Namens):
#   powershell -ExecutionPolicy Bypass -File Agenten\Werkzeuge\desktop-verknuepfungen.ps1
#
# WARUM ueber WScript.Shell und nicht per Hand: eine Verknuepfung braucht
# Target, ARGUMENTE und WorkingDirectory. Fehlt das Arbeitsverzeichnis, startet
# das Programm im falschen Ordner und findet seine Dateien nicht. Genau daran
# sind zwei Reste auf dem Desktop entstanden (Textdateien, deren NAME der ganze
# fehlgeschlagene Befehl war).
#
# KEINE UMLAUTE IN DIESER DATEI: PowerShell 5.1 liest eine .ps1 ohne BOM als
# ANSI. Ein "Verknuepfung" mit ue waere im Vergleich ein anderer Name, und ein
# Remove-Item mit -LiteralPath findet dann nichts - lautlos.
# Deshalb wird auch nach MUSTERN aufgeraeumt (Get-ChildItem -Filter), nicht
# ueber ausgeschriebene Namen.

$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$bf = 'C:\Users\faupe\Documents\BrainFiles'
$icon = "$env:SystemRoot\System32\imageres.dll,1"

# PowerShell hat $args als automatische Variable - ein Parameter dieses Namens
# laesst den Aufruf mit "System.Object[] kann nicht in string konvertiert
# werden" abbrechen.
function Neu($name, $ziel, $argumente, $wd, $iconPfad) {
  $pfad = Join-Path $desktop $name
  $s = $w.CreateShortcut($pfad)
  $s.TargetPath = $ziel
  $s.Arguments = $argumente
  $s.WorkingDirectory = $wd
  if ($iconPfad) { $s.IconLocation = $iconPfad }
  $s.Description = $name
  $s.Save()
  "angelegt: $name"
}

# 1) Handelszentrale - ueber den Wrapper: er hat den Doppelstart-Schutz
#    (Fenstertitel) und schreibt Aufbaufehler nach handelszentrale-fehler.log.
Neu 'Handelszentrale.lnk' `
    "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
    "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$bf\Agenten\Routinen\handelszentrale.ps1`"" `
    "$bf\Agenten\Routinen" $icon

# 2) Werkzeug-Zentrale (repos-zentrale) - eigenes venv, eigenes pythonw.
Neu 'Werkzeug-Zentrale.lnk' `
    "$bf\Agenten\Werkzeuge\repos-zentrale\.venv\Scripts\pythonw.exe" `
    "`"$bf\Agenten\Werkzeuge\repos-zentrale\repos_zentrale.py`"" `
    "$bf\Agenten\Werkzeuge\repos-zentrale" $icon

# 3) Freqtrade-Bots: drei Web-UIs auf 127.0.0.1 (nur lokal gebunden, Login
#    steht in freqtrade/user_data/config.json). Ein Klick oeffnet alle drei.
Neu 'Freqtrade-Bots.lnk' `
    "$env:SystemRoot\System32\cmd.exe" `
    '/c start "" http://127.0.0.1:8081/ & start "" http://127.0.0.1:8082/ & start "" http://127.0.0.1:8083/' `
    "$bf\Agenten\Handel\freqtrade" $icon

# 4) MoonDev-GUI: die vorhandene Verknuepfung zeigte richtig, trug aber einen
#    unbrauchbaren Namen; neu angelegt und die alte per Muster entfernt.
Neu 'MoonDev-GUI.lnk' `
    "$bf\Werkstatt\Repos\moon-dev-ai-agents\.venv\Scripts\pythonw.exe" `
    "`"$bf\Werkstatt\Repos\moon-dev-ai-agents\moongui.py`"" `
    "$bf\Werkstatt\Repos\moon-dev-ai-agents" $icon

# 5) Aufraeumen: Verknuepfungen auf DEAKTIVIERTE Ziele und Reste
#    fehlgeschlagener Verknuepfungen (Dateiname = der ganze Befehl).
foreach ($m in @('*MoonDev-GUI.vbs*', '*moongui.py*', '*CUsersfaupeDocuments*')) {
  Get-ChildItem -LiteralPath $desktop -Filter $m -File -ErrorAction SilentlyContinue |
    ForEach-Object {
      "entfernt: $($_.Name) ($($_.Length) Bytes)"
      Remove-Item -LiteralPath $_.FullName -Force
    }
}

# Gegenprobe: jede Verknuepfung auslesen UND pruefen, ob ihr Ziel existiert.
''
'--- Gegenprobe (Ziel-existiert muss True sein)'
foreach ($n in @('Handelszentrale.lnk', 'Werkzeug-Zentrale.lnk',
                 'Freqtrade-Bots.lnk', 'MoonDev-GUI.lnk')) {
  $p = Join-Path $desktop $n
  $s = $w.CreateShortcut($p)
  "{0,-22} Ziel-existiert={1}  wd={2}" -f $n, (Test-Path -LiteralPath $s.TargetPath), $s.WorkingDirectory
}