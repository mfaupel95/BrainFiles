# konfig-doktor.test.ps1 - Tests fuer konfig-doktor.ps1 (Hausstil wie Bus-Tests, kein Framework).
# Aufruf: powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1
# Endet mit "konfig-doktor bestanden". Nur ASCII im Quelltext.
$ErrorActionPreference = 'Continue'
$Doktor = Join-Path (Split-Path $PSScriptRoot -Parent) 'konfig-doktor.ps1'
$Ps = (Get-Process -Id $PID).Path
$script:Fehler = 0
$script:Aufraeumen = New-Object System.Collections.ArrayList

function Pruefe([string]$Name, [bool]$Bedingung, [string]$Detail = '') {
    if ($Bedingung) { Write-Host "  ok     $Name" }
    else { Write-Host "  FEHLT  $Name $Detail"; $script:Fehler++ }
}
function Neue-Wurzel {
    $p = Join-Path ([IO.Path]::GetTempPath()) ('konfig doktor test ' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $p | Out-Null
    [void]$script:Aufraeumen.Add($p)
    return $p
}
function Schreibe([string]$Pfad, [string]$Inhalt) {
    $d = Split-Path $Pfad -Parent
    if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    [IO.File]::WriteAllText($Pfad, $Inhalt, (New-Object System.Text.UTF8Encoding($false)))
}
function Lauf([string]$Wurzel, [string[]]$Module, [hashtable]$Extra = @{}) {
    $a = @{ Wurzel = $Wurzel; Modul = $Module; PassThru = $true; Kurz = $true; OhneExtern = $true }
    foreach ($k in $Extra.Keys) { $a[$k] = $Extra[$k] }
    return @(& $Doktor @a)
}
function Lauf-Kind([string[]]$Argumente) {
    $o = & $Ps -NoProfile -ExecutionPolicy Bypass -File $Doktor @Argumente 2>&1 | Out-String
    return [pscustomobject]@{ Exit = $LASTEXITCODE; Out = $o }
}
function Hat($Befunde, [string]$Id) { return (@($Befunde | Where-Object { $_.id -eq $Id }).Count -gt 0) }
function Schwere-Von($Befunde, [string]$Id) { return (@($Befunde | Where-Object { $_.id -eq $Id }) | Select-Object -First 1).schwere }

Write-Host '--- Geruest ---'
$fx = Neue-Wurzel
$r = Lauf $fx @('selbsttest-fehler')
Pruefe 'Modulfehler wird isoliert (UNKLAR)' ((Hat $r 'PRUEFUNG-FEHLGESCHLAGEN-selbsttest-fehler') -and ((Schwere-Von $r 'PRUEFUNG-FEHLGESCHLAGEN-selbsttest-fehler') -eq 'UNKLAR'))
$r = Lauf $fx @('selbsttest-langsam') @{ ModulLimitSek = 1 }
Pruefe 'Zeitlimit ergibt UNKLAR' ((Hat $r 'ZEITLIMIT-selbsttest-langsam') -and ((Schwere-Von $r 'ZEITLIMIT-selbsttest-langsam') -eq 'UNKLAR'))
$r = Lauf $fx @('selbsttest-fehler', 'selbsttest-kritisch')
Pruefe 'Fehler in Modul A stoppt Modul B nicht' ((Hat $r 'TEST-KRITISCH') -and (Hat $r 'PRUEFUNG-FEHLGESCHLAGEN-selbsttest-fehler'))
Pruefe 'KRITISCH steht vor UNKLAR' ($r[0].schwere -eq 'KRITISCH')
$b = $r | Where-Object { $_.id -eq 'TEST-KRITISCH' }
Pruefe 'Maske entfernt Schluessel aus Beleg' (($b.beleg -notmatch 'sk-abcdefghijklmnopqrstuvwxyz123456') -and ($b.beleg -match '\*\*\*'))

$k = Lauf-Kind @('-Wurzel', $fx, '-Modul', 'selbsttest-kritisch', '-BerichtOrdner', $fx)
Pruefe 'Exit 1 bei KRITISCH' ($k.Exit -eq 1) "Exit=$($k.Exit)"
$bericht = Join-Path $fx ('konfig-doktor-' + (Get-Date -Format 'yyyy-MM-dd') + '.md')
Pruefe 'Bericht wird geschrieben' (Test-Path -LiteralPath $bericht)
$bt = ''
if (Test-Path -LiteralPath $bericht) { $bt = [IO.File]::ReadAllText($bericht) }
Pruefe 'Bericht hat Stufen-Abschnitt' ($bt -match '## KRITISCH \(1\)')
Pruefe 'Bericht ohne Schluessel' (($bt -notmatch 'sk-abcdefghijklmnopqrstuvwxyz123456') -and ($bt -match '\*\*\*'))
$fx2 = Neue-Wurzel
$k = Lauf-Kind @('-Wurzel', $fx2, '-Modul', 'selbsttest-kritisch', '-Kurz')
Pruefe 'Kurz: Zaehlzeile' ($k.Out -match 'konfig-doktor: KRITISCH 1 \| WARNUNG 0 \| HINWEIS 0 \| UNKLAR 0')
Pruefe 'Kurz: kein Bericht' (-not (Test-Path -LiteralPath (Join-Path $fx2 'Werkstatt')) -and @(Get-ChildItem -LiteralPath $fx2 -Filter 'konfig-doktor-*.md').Count -eq 0)
$k = Lauf-Kind @('-Wurzel', $fx2, '-Modul', 'selbsttest-fehler', '-Kurz')
Pruefe 'Exit 0 ohne KRITISCH' ($k.Exit -eq 0) "Exit=$($k.Exit)"
$k = Lauf-Kind @('-Wurzel', $fx2, '-Modul', 'gibt-es-nicht', '-Kurz')
Pruefe 'Exit 2 bei unbekanntem Modul' ($k.Exit -eq 2) "Exit=$($k.Exit)"

# === ENDE (neue Testabschnitte oberhalb dieser Zeile einfuegen) ===
foreach ($p in $script:Aufraeumen) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue }
if ($script:Fehler -gt 0) { Write-Host "konfig-doktor FEHLGESCHLAGEN: $($script:Fehler) Pruefung(en)"; exit 1 }
Write-Host 'konfig-doktor bestanden'
