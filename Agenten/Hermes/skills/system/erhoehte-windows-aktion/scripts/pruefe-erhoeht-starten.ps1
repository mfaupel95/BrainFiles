# Selbsttest des Wrappers - OHNE UAC und ohne Aenderung am System.
#
# Prueft drei Dinge: (1) der Wrapper parst unter PowerShell 5.1, (2) er benutzt keine
# Aufrufe, die es dort nicht gibt, (3) die Log-Mechanik haelt die Ausgabe UND den
# Exitcode des Zielskripts fest (genau das war einmal kaputt: Write-Host schreibt an
# die Host-Konsole des erhoehten Fensters und ist mit dem Fenster weg).
#
# Aufruf ueber das terminal-Werkzeug:
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/pruefe-erhoeht-starten.ps1

$ErrorActionPreference = 'Continue'
$wrapper = Join-Path $PSScriptRoot 'erhoeht-starten.ps1'
$probe   = Join-Path $env:TEMP ('erhoeht-probe-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $probe -Force | Out-Null
$ziel = Join-Path $probe 'ziel.ps1'
$log  = Join-Path $probe 'lauf.log'
$innen = Join-Path $probe 'innen.ps1'
$fehlerzahl = 0

Write-Host '--- 1) Syntax des Wrappers ---'
$fehler = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($wrapper, [ref]$null, [ref]$fehler)
if ($fehler) { $fehler | ForEach-Object { 'FEHLER: ' + $_.Message }; $fehlerzahl++ } else { 'SYNTAX OK' }

Write-Host '--- 2) Aufrufe, die es in PS 5.1 nicht gibt ---'
$text = Get-Content -LiteralPath $wrapper -Raw
foreach ($verbot in @('Split-Path -LeafBase', '-RedirectStandardOutput', 'reg query', 'Write-Host (''EXITCODE')) {
    if ($text -like "*$verbot*") { "TREFFER (pruefen): $verbot"; $fehlerzahl++ } else { "sauber: $verbot kommt nicht vor" }
}

Write-Host '--- 3) Log-Mechanik wie im Wrapper ---'
[System.IO.File]::WriteAllText($ziel, "Write-Host 'ZIEL LAEUFT'; Write-Error 'gewollter Fehler'; exit 7", (New-Object System.Text.UTF8Encoding($false)))
$innenText = @"
`$ErrorActionPreference = 'Continue'
`$log = '$log'
& '$ziel' *>&1 | Tee-Object -FilePath `$log
Add-Content -LiteralPath `$log -Value ('EXITCODE=' + `$LASTEXITCODE)
"@
[System.IO.File]::WriteAllText($innen, $innenText, (New-Object System.Text.UTF8Encoding($false)))
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $innen | Out-Null

Write-Host '--- 4) Was steht im Log? ---'
if (Test-Path -LiteralPath $log) {
    $inhalt = Get-Content -LiteralPath $log -Raw
    $hatZiel = $inhalt -match 'ZIEL LAEUFT'
    $hatFehl = $inhalt -match 'gewollter\s+Fehler'
    $hatCode = $inhalt -match 'EXITCODE=7'
    "Zielausgabe: $hatZiel | Fehlerstrom: $hatFehl | Exitcode: $hatCode"
    if (-not ($hatZiel -and $hatFehl -and $hatCode)) { 'MECHANIK UNVOLLSTAENDIG'; $fehlerzahl++ } else { 'MECHANIK OK' }
} else { 'KEIN LOG - Mechanik kaputt'; $fehlerzahl++ }

Remove-Item $probe -Recurse -Force -ErrorAction SilentlyContinue
if ($fehlerzahl -eq 0) { 'ERGEBNIS: bestanden' } else { "ERGEBNIS: $fehlerzahl Befund(e)" }
exit $fehlerzahl
