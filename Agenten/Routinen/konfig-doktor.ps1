# konfig-doktor.ps1 - rein lesender Konfigurations-Doktor fuer BrainFiles.
# Spec: Werkstatt/spec-konfig-doktor-2026-10-04.md
# Aufruf: konfig-doktor.ps1 [-Modul <name>[,<name>]] [-Kurz] [-OhneExtern] [-PassThru]
#                           [-Wurzel <pfad>] [-BerichtOrdner <pfad>] [-ModulLimitSek 20]
# Exit: 0 = kein KRITISCH, 1 = mindestens ein KRITISCH, 2 = Doktor selbst defekt.
# Nur ASCII im Quelltext (Windows PowerShell 5.1 liest BOM-lose Dateien als ANSI).
[CmdletBinding()]
param(
    [string[]]$Modul = @(),
    [switch]$Kurz,
    [switch]$PassThru,
    [switch]$OhneExtern,
    [string]$Wurzel = '',
    [string]$BerichtOrdner = '',
    [int]$ModulLimitSek = 20
)
$ErrorActionPreference = 'Continue'
$WurzelExplizit = $PSBoundParameters.ContainsKey('Wurzel')
if (-not $Wurzel) { $Wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent }
$Wurzel = [System.IO.Path]::GetFullPath($Wurzel).TrimEnd('\', '/')
$script:Befunde = New-Object System.Collections.ArrayList

# ---------- Hilfen ----------
function Maske([string]$t) {
    if ($null -eq $t) { return '' }
    $t = $t -replace '(?i)(bearer\s+|(api[_-]?key|token|secret|password)\s*[:=]\s*)\S+', '${1}***'
    $t = $t -replace '(?i)\b(sk|pk|ghp|gho|xox[abp]|AKIA)[-_A-Za-z0-9]{12,}', '***'
    $t = $t -replace '(?=[A-Za-z0-9_\-]*\d)(?=[A-Za-z0-9_\-]*[A-Za-z])[A-Za-z0-9_\-]{40,}', '***'
    return $t
}

function Add-Befund {
    param(
        [string]$Id, [string]$Modul,
        [ValidateSet('KRITISCH', 'WARNUNG', 'HINWEIS', 'UNKLAR')][string]$Schwere,
        [string]$Titel, [string]$Beleg,
        [ValidateSet('gesichert', 'Vermutung')][string]$Status,
        [string]$Vorschlag
    )
    [void]$script:Befunde.Add([pscustomobject]@{
            id = $Id; modul = $Modul; schwere = $Schwere
            titel = (Maske $Titel); beleg = (Maske $Beleg); status = $Status; vorschlag = (Maske $Vorschlag)
        })
}

function Invoke-Extern {
    param(
        [string]$Datei, [string[]]$Argumente = @(), [int]$TimeoutSek = 20,
        [string[]]$EntferneEnv = @(), [hashtable]$SetzeEnv = @{}, [string]$Arbeitsordner = '',
        [switch]$StdinLeer
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Datei
    $psi.Arguments = (@($Argumente | ForEach-Object { if ($_ -eq '' -or $_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }) -join ' ')
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    if ($StdinLeer) { $psi.RedirectStandardInput = $true }
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    if ($Arbeitsordner) { $psi.WorkingDirectory = $Arbeitsordner }
    foreach ($e in $EntferneEnv) { [void]$psi.EnvironmentVariables.Remove($e) }
    foreach ($k in $SetzeEnv.Keys) { $psi.EnvironmentVariables[$k] = [string]$SetzeEnv[$k] }
    $p = [System.Diagnostics.Process]::Start($psi)
    if ($StdinLeer) { try { $p.StandardInput.Close() } catch { } }
    $so = $p.StandardOutput.ReadToEndAsync()
    $se = $p.StandardError.ReadToEndAsync()
    if (-not $p.WaitForExit($TimeoutSek * 1000)) {
        try { $p.Kill() } catch { }
        return [pscustomobject]@{ ExitCode = $null; Out = ''; Err = ''; TimedOut = $true }
    }
    $p.WaitForExit()
    return [pscustomobject]@{ ExitCode = $p.ExitCode; Out = $so.Result; Err = $se.Result; TimedOut = $false }
}

function Invoke-Modul {
    param([string]$Name, [string]$Fn)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try { & $Fn }
    catch {
        Add-Befund -Id "PRUEFUNG-FEHLGESCHLAGEN-$Name" -Modul $Name -Schwere 'UNKLAR' `
            -Titel "Pruefung '$Name' fehlgeschlagen" -Beleg ([string]$_.Exception.Message) -Status 'Vermutung' `
            -Vorschlag "Modul einzeln mit -Modul $Name aufrufen und Fehlertext pruefen"
    }
    $sw.Stop()
    if ($sw.Elapsed.TotalSeconds -gt $ModulLimitSek) {
        Add-Befund -Id "ZEITLIMIT-$Name" -Modul $Name -Schwere 'UNKLAR' `
            -Titel "Pruefung '$Name' ueberschreitet das Zeitlimit" `
            -Beleg ("{0:N1} s gemessen, Limit {1} s" -f $sw.Elapsed.TotalSeconds, $ModulLimitSek) -Status 'gesichert' `
            -Vorschlag 'Modul einzeln laufen lassen; Ursache der Langsamkeit klaeren'
    }
}

# ---------- Selbsttest-Module (nur fuer die Tests, nicht in der Standardliste) ----------
function Pruefe-SelbsttestFehler { throw 'absichtlicher Testfehler' }
function Pruefe-SelbsttestLangsam { Start-Sleep -Seconds 2 }
function Pruefe-SelbsttestKritisch {
    Add-Befund -Id 'TEST-KRITISCH' -Modul 'selbsttest-kritisch' -Schwere 'KRITISCH' -Titel 'Testbefund' `
        -Beleg 'Schluessel sk-abcdefghijklmnopqrstuvwxyz123456 im Text' -Status 'gesichert' -Vorschlag 'keiner'
}

# ---------- Modul 1: mcp-pfade ----------
# Loest $Pfad gegen genau EINE Basis auf (absolute Pfade ohne Basis). Rueckgabe: Pfad oder $null.
function Test-PfadAufgeloest([string]$Pfad, [string]$Basis) {
    if ([System.IO.Path]::IsPathRooted($Pfad)) {
        if (Test-Path -LiteralPath $Pfad) { return $Pfad } else { return $null }
    }
    $k = Join-Path $Basis $Pfad
    if (Test-Path -LiteralPath $k) { return $k }
    return $null
}

$script:SkriptEndung = '\.(js|mjs|cjs|py|ps1|cmd|bat|exe)$'

function Ist-PfadArg([string]$a, [string]$Cmd = '') {
    if (-not $a) { return $false }
    if ($a -match '^[-@]' -or $a -match '://') { return $false }
    # Paketbezeichner: github:user/repo, npm:x, git+ssh:... (mind. 2 Zeichen vor ':', also kein Laufwerk C:)
    if ($a -match '^[A-Za-z][A-Za-z0-9+.\-]+:') { return $false }
    # user/repo bzw. user/repo@1.2 bei Paketstartern (npx, uvx, ...) ist ein Paket, kein Pfad
    $leaf = ''
    if ($Cmd) { $leaf = [System.IO.Path]::GetFileNameWithoutExtension(($Cmd -split '[\\/]')[-1]).ToLowerInvariant() }
    if (@('npx', 'uvx', 'pnpx', 'bunx', 'pipx') -contains $leaf) {
        if ($a -match '^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+(@[^\\/]*)?$' -and $a -notmatch $script:SkriptEndung -and $a -notmatch '^\.') { return $false }
    }
    return ($a -match '[\\/]' -or $a -match '\.(js|mjs|cjs|py|ps1|cmd|bat|exe|json)$')
}

function Get-Eig($Objekt, [string]$Name) {
    $p = $Objekt.PSObject.Properties[$Name]
    if ($p) { return $p.Value }
    return $null
}

function Pruefe-McpPfade {
    $mf = Join-Path $Wurzel 'Agenten/MCP-Manifest.json'
    if (-not (Test-Path -LiteralPath $mf)) {
        Add-Befund -Id 'MCP-MANIFEST-FEHLT' -Modul 'mcp-pfade' -Schwere 'KRITISCH' -Titel 'MCP-Manifest fehlt' `
            -Beleg "Test-Path negativ: $mf" -Status 'gesichert' -Vorschlag 'Manifest aus git wiederherstellen; ohne Manifest sind die Server nicht pruefbar'
        return
    }
    $man = $null
    try { $man = Get-Content -LiteralPath $mf -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop }
    catch {
        Add-Befund -Id 'MCP-MANIFEST-DEFEKT' -Modul 'mcp-pfade' -Schwere 'KRITISCH' -Titel 'MCP-Manifest ist kein gueltiges JSON' `
            -Beleg "ConvertFrom-Json scheitert fuer $mf" -Status 'gesichert' -Vorschlag 'Manifest mit git diff gegen den letzten guten Stand vergleichen'
        return
    }
    $ausserhalb = New-Object System.Collections.ArrayList
    $wl = [System.IO.Path]::GetFullPath($Wurzel).TrimEnd('\', '/').ToLowerInvariant()
    foreach ($s in @($man.servers)) {
        if ($null -eq $s) { continue }
        $name = [string](Get-Eig $s 'name')
        if ((Get-Eig $s 'enabled') -eq $false) { continue }
        $cwd = $Wurzel
        $cwdRoh = [string](Get-Eig $s 'cwd')
        if ($cwdRoh) {
            if ([System.IO.Path]::IsPathRooted($cwdRoh)) { $cwd = $cwdRoh } else { $cwd = Join-Path $Wurzel $cwdRoh }
            if (-not (Test-Path -LiteralPath $cwd)) {
                Add-Befund -Id "MCP-CWD-FEHLT-$name" -Modul 'mcp-pfade' -Schwere 'KRITISCH' -Titel "Arbeitsverzeichnis von '$name' fehlt" `
                    -Beleg "cwd '$cwdRoh' aufgeloest zu $cwd, Test-Path negativ" -Status 'gesichert' -Vorschlag 'cwd im Manifest korrigieren oder Ordner wiederherstellen'
                continue
            }
        }
        $cmd = [string](Get-Eig $s 'command')
        $fehlend = New-Object System.Collections.ArrayList
        $optional = New-Object System.Collections.ArrayList
        $nurWurzel = New-Object System.Collections.ArrayList
        $aufgeloest = New-Object System.Collections.ArrayList
        # Kandidaten: Pfad, Herkunft, kritisch (command / positionales Skript) oder vermutlich optional
        $kand = New-Object System.Collections.ArrayList
        if ($cmd -and $cmd -match '[\\/]') { [void]$kand.Add([pscustomobject]@{ p = $cmd; her = 'command'; krit = $true }) }
        $argListe = @(@(Get-Eig $s 'args') | ForEach-Object { [string]$_ })
        for ($i = 0; $i -lt $argListe.Count; $i++) {
            $as = $argListe[$i]
            $nachFlag = ($i -gt 0 -and $argListe[$i - 1] -match '^--[A-Za-z]' -and $argListe[$i - 1] -notmatch '=')
            if ($as -match '^--[A-Za-z][^=]*=(.+)$') { $as = $Matches[1]; $nachFlag = $true }
            if (-not (Ist-PfadArg $as $cmd)) { continue }
            $krit = ((-not $nachFlag) -and ($as -match $script:SkriptEndung))
            [void]$kand.Add([pscustomobject]@{ p = $as; her = 'args'; krit = $krit })
        }
        foreach ($c in $kand) {
            $r = Test-PfadAufgeloest $c.p $cwd
            if ($r) { [void]$aufgeloest.Add($r); continue }
            if ($cwdRoh) {
                $rw = Test-PfadAufgeloest $c.p $Wurzel
                if ($rw) { [void]$aufgeloest.Add($rw); [void]$nurWurzel.Add("$($c.her): $($c.p)"); continue }
            }
            if ($c.krit) { [void]$fehlend.Add("$($c.her): $($c.p)") } else { [void]$optional.Add("$($c.her): $($c.p)") }
        }
        if ($cmd -and $cmd -notmatch '[\\/]') {
            if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
                Add-Befund -Id "MCP-COMMAND-NICHT-IM-PFAD-$name" -Modul 'mcp-pfade' -Schwere 'WARNUNG' -Titel "Command '$cmd' von '$name' nicht im PATH" `
                    -Beleg "Get-Command $cmd liefert nichts (in dieser Shell; Server-Start kann anderen PATH haben)" -Status 'Vermutung' `
                    -Vorschlag 'Programm installieren oder vollen Pfad ins Manifest schreiben'
            }
        }
        $geprueft = "cwd $cwd"
        if ($cwdRoh) { $geprueft = "cwd $cwd und Wurzel $Wurzel" }
        if ($fehlend.Count -gt 0) {
            Add-Befund -Id "MCP-PFAD-FEHLT-$name" -Modul 'mcp-pfade' -Schwere 'KRITISCH' -Titel "Server '$name': Pfad fehlt" `
                -Beleg ("Fehlend: " + ($fehlend -join '; ') + ". Geprueft gegen $geprueft; Test-Path negativ") -Status 'gesichert' `
                -Vorschlag 'Datei bauen/wiederherstellen oder Manifest-Eintrag korrigieren (Reparatur nur nach Freigabe)'
        }
        if ($optional.Count -gt 0) {
            Add-Befund -Id "MCP-PFAD-OPTIONAL-FEHLT-$name" -Modul 'mcp-pfade' -Schwere 'WARNUNG' -Titel "Server '$name': Datei hinter Flag oder Nicht-Skript-Argument fehlt" `
                -Beleg ("Fehlend: " + ($optional -join '; ') + ". Geprueft gegen $geprueft; Test-Path negativ") -Status 'Vermutung' `
                -Vorschlag 'Pruefen, ob die Datei optional ist oder vom Server selbst erzeugt wird; sonst Manifest korrigieren'
        }
        if ($nurWurzel.Count -gt 0) {
            Add-Befund -Id "MCP-PFAD-NUR-WURZEL-$name" -Modul 'mcp-pfade' -Schwere 'WARNUNG' -Titel "Server '$name': Pfad loest nur gegen die Wurzel auf, nicht gegen cwd" `
                -Beleg ("Betroffen: " + ($nurWurzel -join '; ') + ". Test-Path negativ unter cwd $cwd, positiv unter Wurzel $Wurzel") -Status 'gesichert' `
                -Vorschlag 'Der Server startet in cwd; Pfad im Manifest relativ zu cwd schreiben oder absolut machen'
        }
        $voll = (@($cmd) + $argListe) -join ' '
        if ($voll -match '(?i)(curl|wget|iwr|invoke-webrequest)[^|]*\|\s*(sh|bash|zsh|iex|invoke-expression)\b') {
            Add-Befund -Id "MCP-STARTER-AUFFAELLIG-$name" -Modul 'mcp-pfade' -Schwere 'WARNUNG' -Titel "Starter von '$name' holt Code aus dem Netz und fuehrt ihn aus" `
                -Beleg 'command/args enthalten Download-Pipe in eine Shell oder iex' -Status 'gesichert' -Vorschlag 'Skript lokal ablegen und pruefen; Entscheidung liegt bei Max'
        }
        foreach ($p in $aufgeloest) {
            $voll2 = [System.IO.Path]::GetFullPath($p).ToLowerInvariant()
            if (-not ($voll2 -eq $wl -or $voll2.StartsWith($wl + '\'))) { [void]$ausserhalb.Add("$name -> $p"); break }
        }
    }
    if ($ausserhalb.Count -gt 0) {
        Add-Befund -Id 'MCP-AUSSERHALB-WURZEL' -Modul 'mcp-pfade' -Schwere 'HINWEIS' -Titel "$($ausserhalb.Count) Server starten Programme ausserhalb der Wurzel" `
            -Beleg (($ausserhalb | Select-Object -First 8) -join '; ') -Status 'gesichert' -Vorschlag 'Nur zur Kenntnis: Pfade ausserhalb der Wurzel ueberleben einen Umzug auf die SSD nicht'
    }
    $sc = Join-Path $Wurzel 'Agenten/mcp-sync-check.ps1'
    if ((Test-Path -LiteralPath $sc) -and -not $OhneExtern) {
        $ps = (Get-Process -Id $PID).Path
        # Eigenes Limit unter dem Modul-Limit, damit der Befund noch vor dem Modul-Abbruch entsteht
        $to = [Math]::Max(5, $ModulLimitSek - 5)
        $r = Invoke-Extern -Datei $ps -Argumente @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $sc) -TimeoutSek $to
        if ($r.TimedOut) {
            Add-Befund -Id 'MCP-SYNC-ZEITLIMIT' -Modul 'mcp-pfade' -Schwere 'UNKLAR' -Titel 'mcp-sync-check.ps1 antwortet nicht im Zeitlimit' `
                -Beleg "Abbruch nach $to s" -Status 'gesichert' -Vorschlag 'Skript einzeln ausfuehren'
        }
        elseif ($r.ExitCode -ne 0) {
            $zeilen = @(([string]$r.Out + "`n" + [string]$r.Err) -split "`r?`n" | Where-Object { $_.Trim() })
            $tr = @($zeilen | Where-Object { $_ -match '^\s*(FEHLER|WARN)\b' } | Select-Object -First 3)
            if ($tr.Count -eq 0) { $tr = @($zeilen | Select-Object -First 3) }
            $zl = (@($tr | ForEach-Object { $_.Trim() }) -join ' / ')
            Add-Befund -Id 'MCP-SYNC-ABWEICHUNG' -Modul 'mcp-pfade' -Schwere 'HINWEIS' -Titel 'mcp-sync-check.ps1 meldet Abweichung' `
                -Beleg "Exit $($r.ExitCode): $zl" -Status 'gesichert' -Vorschlag 'Ausgabe des Skripts lesen; Abgleich Manifest und Client-Configs'
        }
    }
}

# ---------- Modul 2: hermes ----------
function Get-AblaufListe($Obj, [string]$Pfad, [int]$Tiefe, $Liste) {
    if ($null -eq $Obj -or $Tiefe -gt 5) { return }
    if ($Obj -is [System.Management.Automation.PSCustomObject]) {
        foreach ($p in $Obj.PSObject.Properties) {
            if ($p.Name -eq 'expires_at') { [void]$Liste.Add([pscustomobject]@{ Pfad = "$Pfad/expires_at"; Wert = $p.Value }) }
            else { Get-AblaufListe $p.Value "$Pfad/$($p.Name)" ($Tiefe + 1) $Liste }
        }
    }
    elseif ($Obj -is [System.Collections.IEnumerable] -and $Obj -isnot [string]) {
        $i = 0
        foreach ($e in $Obj) { Get-AblaufListe $e "$Pfad[$i]" ($Tiefe + 1) $Liste; $i++ }
    }
}

function ConvertTo-Zeit($Wert) {
    if ($null -eq $Wert) { return $null }
    if ($Wert -is [datetime]) { return $Wert.ToUniversalTime() }
    if ($Wert -is [string]) {
        if ([string]::IsNullOrWhiteSpace($Wert)) { return $null }
        $zahl = 0.0
        if ([double]::TryParse($Wert, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$zahl)) { $Wert = $zahl }
    }
    if ($Wert -is [ValueType] -and $Wert -isnot [bool]) {
        $n = [double]$Wert
        if ($n -le 0) { return $null }
        if ($n -gt 100000000000) { $n = $n / 1000 }
        return (New-Object DateTime 1970, 1, 1, 0, 0, 0, ([DateTimeKind]::Utc)).AddSeconds($n)
    }
    $d = [datetime]::MinValue
    $stil = [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal
    if ([datetime]::TryParse([string]$Wert, [System.Globalization.CultureInfo]::InvariantCulture, $stil, [ref]$d)) { return $d }
    return $null
}

function Pruefe-Hermes {
    if ($env:OS -ne 'Windows_NT') {
        Add-Befund -Id 'HERMES-NICHT-WINDOWS' -Modul 'hermes' -Schwere 'UNKLAR' -Titel 'Hermes-Pruefung uebersprungen (kein Windows)' `
            -Beleg 'Linux/Cloud-Checkout: Junctions und venvs fehlen' -Status 'gesichert' -Vorschlag 'Auf Max'' Rechner ausfuehren'
        return
    }
    $standard = Join-Path $Wurzel 'Agenten/Hermes'
    $heim = $standard
    $envHome = [string]$env:HERMES_HOME
    if (-not $WurzelExplizit -and $envHome) {
        if (-not [System.IO.Path]::IsPathRooted($envHome)) { $envHome = Join-Path $Wurzel $envHome }
        $a = [System.IO.Path]::GetFullPath($envHome).TrimEnd('\', '/')
        $heim = $a
        $b = [System.IO.Path]::GetFullPath($standard).TrimEnd('\', '/')
        if ($a -ne $b) {
            Add-Befund -Id 'HERMES-HOME-ABWEICHEND' -Modul 'hermes' -Schwere 'HINWEIS' -Titel 'HERMES_HOME zeigt nicht auf Agenten/Hermes' `
                -Beleg "HERMES_HOME=$envHome, erwartet $standard" -Status 'gesichert' -Vorschlag 'Pruefen, ob das gewollt ist (zweite Instanz?)'
        }
    }
    if (-not (Test-Path -LiteralPath $heim)) {
        Add-Befund -Id 'HERMES-ORDNER-FEHLT' -Modul 'hermes' -Schwere 'UNKLAR' -Titel 'Hermes-Ordner nicht vorhanden' `
            -Beleg "Test-Path negativ: $heim" -Status 'gesichert' -Vorschlag 'Bei frischem Checkout erwartbar; sonst Pfad/HERMES_HOME klaeren'
        return
    }
    $cfg = Join-Path $heim 'config.yaml'
    if (-not (Test-Path -LiteralPath $cfg)) {
        Add-Befund -Id 'HERMES-CONFIG-FEHLT' -Modul 'hermes' -Schwere 'KRITISCH' -Titel 'Hermes config.yaml fehlt' `
            -Beleg "Test-Path negativ: $cfg" -Status 'gesichert' -Vorschlag 'Aus der juengsten Altkopie (config.yaml.bak-*) wiederherstellen - nach Freigabe'
    }
    else {
        $gr = (Get-Item -LiteralPath $cfg).Length
        $baks = @(Get-ChildItem -LiteralPath $heim -File -Filter 'config.yaml.bak*' -ErrorAction SilentlyContinue)
        if ($baks.Count -gt 0) {
            $max = ($baks | Measure-Object -Property Length -Maximum).Maximum
            if ($gr -lt (0.5 * $max)) {
                Add-Befund -Id 'HERMES-CONFIG-GESCHRUMPFT' -Modul 'hermes' -Schwere 'UNKLAR' -Titel 'Hermes config.yaml ist deutlich kleiner als die groesste Altkopie' `
                    -Beleg ("config.yaml {0} KB, groesste Altkopie {1} KB" -f [math]::Round($gr / 1KB, 1), [math]::Round($max / 1KB, 1)) -Status 'Vermutung' `
                    -Vorschlag 'Max: Ist das Schrumpfen gewollt (Bereinigung) oder gingen Abschnitte verloren? Diff gegen die Altkopie zeigt es'
            }
        }
    }
    $auth = Join-Path $heim 'auth.json'
    $corrupt = @(Get-ChildItem -LiteralPath $heim -File -Filter '*.corrupt' -ErrorAction SilentlyContinue)
    if (Test-Path -LiteralPath $auth) {
        $json = $null
        $lesbar = $true
        try { $json = Get-Content -LiteralPath $auth -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop } catch { $lesbar = $false }
        if (-not $lesbar -or $null -eq $json) {
            Add-Befund -Id 'HERMES-AUTH-DEFEKT' -Modul 'hermes' -Schwere 'KRITISCH' -Titel 'auth.json ist kein gueltiges JSON' `
                -Beleg 'ConvertFrom-Json scheitert (Inhalt bewusst nicht ausgegeben)' -Status 'gesichert' -Vorschlag 'Neu anmelden oder aus Sicherung holen - nach Freigabe'
        }
        else {
            $liste = New-Object System.Collections.ArrayList
            Get-AblaufListe $json '' 0 $liste
            $jetzt = (Get-Date).ToUniversalTime()
            $abgelaufen = @()
            foreach ($e in $liste) {
                $t = ConvertTo-Zeit $e.Wert
                if ($t -and $t -lt $jetzt) { $abgelaufen += ("{0} (seit {1})" -f $e.Pfad, $t.ToString('yyyy-MM-dd')) }
            }
            if ($abgelaufen.Count -gt 0) {
                Add-Befund -Id 'HERMES-AUTH-ABGELAUFEN' -Modul 'hermes' -Schwere 'WARNUNG' -Titel "$($abgelaufen.Count) Anmeldung(en) in auth.json abgelaufen" `
                    -Beleg ($abgelaufen -join '; ') -Status 'Vermutung' -Vorschlag 'Ein Refresh-Token kann den Ablauf ausgleichen; Login im Hermes-Client erneuern, falls Aufrufe scheitern'
            }
        }
    }
    elseif (@($corrupt | Where-Object { $_.Name -like 'auth.json*' }).Count -gt 0) {
        Add-Befund -Id 'HERMES-AUTH-FEHLT' -Modul 'hermes' -Schwere 'KRITISCH' -Titel 'auth.json fehlt, nur eine .corrupt-Kopie liegt vor' `
            -Beleg 'Test-Path auth.json negativ; auth.json.corrupt vorhanden' -Status 'gesichert' -Vorschlag 'Neu anmelden - nach Freigabe'
    }
    else {
        Add-Befund -Id 'HERMES-AUTH-NICHT-ANGELEGT' -Modul 'hermes' -Schwere 'HINWEIS' -Titel 'auth.json fehlt (keine .corrupt-Kopie)' `
            -Beleg "Test-Path negativ: $auth" -Status 'gesichert' -Vorschlag 'Erwartbar, wenn nur API-Keys aus .env genutzt werden; sonst im Hermes-Client anmelden'
    }
    if ($corrupt.Count -gt 0) {
        $namen = @($corrupt | ForEach-Object { "{0} ({1})" -f $_.Name, $_.LastWriteTime.ToString('yyyy-MM-dd') })
        Add-Befund -Id 'HERMES-CORRUPT-RESTE' -Modul 'hermes' -Schwere 'HINWEIS' -Titel "$($corrupt.Count) .corrupt-Reste im Hermes-Ordner" `
            -Beleg ($namen -join '; ') -Status 'gesichert' -Vorschlag 'Ursache der Beschaedigung klaeren, danach aufraeumen (Teilprojekt B)'
    }
    $pro = Join-Path $heim 'profiles'
    if (Test-Path -LiteralPath $pro) {
        $ohne = @(Get-ChildItem -LiteralPath $pro -Directory -ErrorAction SilentlyContinue | Where-Object { -not (Test-Path -LiteralPath (Join-Path $_.FullName 'config.yaml')) })
        if ($ohne.Count -gt 0) {
            Add-Befund -Id 'HERMES-PROFILE-OHNE-CONFIG' -Modul 'hermes' -Schwere 'HINWEIS' -Titel "$($ohne.Count) Profil(e) ohne eigene config.yaml" `
                -Beleg (($ohne | Select-Object -First 10 | ForEach-Object { $_.Name }) -join ', ') -Status 'gesichert' `
                -Vorschlag 'Pruefen, ob das Profil die Hauptconfig erbt (empirisch, nicht annehmen)'
        }
    }
    $log = Join-Path $heim 'logs/errors.log'
    if (Test-Path -LiteralPath $log) {
        $zeilen = @(Get-Content -LiteralPath $log -Tail 200 -ErrorAction SilentlyContinue)
        $fz = @($zeilen | Where-Object { $_ -match '\bERROR\b|Traceback' })
        if ($fz.Count -gt 0) {
            $letzte = [string]$fz[-1]
            if ($letzte.Length -gt 160) { $letzte = $letzte.Substring(0, 160) }
            Add-Befund -Id 'HERMES-LOGFEHLER' -Modul 'hermes' -Schwere 'HINWEIS' -Titel "$($fz.Count) Fehlerzeilen in den letzten 200 Zeilen von errors.log" `
                -Beleg "Letzte: $letzte" -Status 'gesichert' -Vorschlag 'Log lesen, bevor spekuliert wird'
        }
    }
    if (-not $OhneExtern -and -not $Kurz) {
        $alle = @(Get-Command hermes -All -CommandType Application -ErrorAction SilentlyContinue)
        $hcPfad = $null
        $hc = @($alle | Where-Object { $_.Source -match '\.exe$' }) | Select-Object -First 1
        if ($hc) { $hcPfad = $hc.Source }
        else {
            $rf = Join-Path $heim 'bin\hermes.exe'
            if (Test-Path -LiteralPath $rf) { $hcPfad = $rf }
        }
        if (-not $hcPfad) {
            $andere = @($alle | Where-Object { $_.Source -notmatch '\.exe$' } | ForEach-Object { $_.Source })
            $bl = 'Keine hermes.exe im PATH und nicht unter <heim>\bin'
            if ($andere.Count -gt 0) { $bl += '; Nicht-.exe-Treffer: ' + ($andere -join ', ') }
            Add-Befund -Id 'HERMES-DOCTOR-NICHT-AUFRUFBAR' -Modul 'hermes' -Schwere 'UNKLAR' -Titel 'hermes.exe nicht gefunden, Selbstdiagnose uebersprungen' `
                -Beleg $bl -Status 'gesichert' -Vorschlag 'hermes doctor von Hand mit bereinigter Umgebung (PYTHONHOME/PYTHONPATH entfernt) ausfuehren'
        }
        else {
            $to = [Math]::Max(5, $ModulLimitSek - 5)
            $r = Invoke-Extern -Datei $hcPfad -Argumente @('doctor') -TimeoutSek $to -EntferneEnv @('PYTHONHOME', 'PYTHONPATH') -SetzeEnv @{ HERMES_HOME = $heim }
            if ($r.TimedOut) {
                Add-Befund -Id 'HERMES-DOCTOR-ZEITLIMIT' -Modul 'hermes' -Schwere 'UNKLAR' -Titel 'hermes doctor antwortet nicht im Zeitlimit' `
                    -Beleg "Abbruch nach $to s (Modul-Limit $ModulLimitSek s)" -Status 'gesichert' -Vorschlag 'hermes doctor von Hand ausfuehren'
            }
            else {
                $pz = @(($r.Out + "`n" + $r.Err) -split "`r?`n" | Where-Object { $_ -match '(?i)\[FAIL\]|\b(ERROR|FAILED|Fehler)\b' })
                if ($pz.Count -gt 0 -or $r.ExitCode -ne 0) {
                    $erste = @($pz | Select-Object -First 3 | ForEach-Object { if ($_.Length -gt 120) { $_.Substring(0, 120) } else { $_ } }) -join ' / '
                    Add-Befund -Id 'HERMES-DOCTOR' -Modul 'hermes' -Schwere 'HINWEIS' -Titel "hermes doctor: $($pz.Count) Problemzeile(n), Exit $($r.ExitCode)" `
                        -Beleg $erste -Status 'gesichert' -Vorschlag 'Ausgabe als Hypothese lesen, nicht als Befund (Meldungen koennen aus falschem Kontext stammen)'
                }
            }
        }
    }
}

# ---------- Modul 3: regelpaare ----------
function Get-NormalText([byte[]]$Bytes) {
    $t = [System.Text.Encoding]::UTF8.GetString($Bytes)
    $t = $t.TrimStart([char]0xFEFF)
    return ($t -replace "`r`n", "`n")
}

function Pruefe-Regelpaare {
    foreach ($rel in @('', 'MaxHirn', 'Werkstatt')) {
        $dir = $Wurzel
        $ort = 'Wurzel'
        if ($rel) { $dir = Join-Path $Wurzel $rel; $ort = $rel }
        $c = Join-Path $dir 'CLAUDE.md'
        $a = Join-Path $dir 'AGENTS.md'
        $hc = Test-Path -LiteralPath $c
        $ha = Test-Path -LiteralPath $a
        if (-not $hc -and -not $ha) {
            Add-Befund -Id "REGELPAAR-ORDNER-FEHLT-$ort" -Modul 'regelpaare' -Schwere 'UNKLAR' -Titel "Regelpaar in '$ort' nicht vorhanden" `
                -Beleg "Weder CLAUDE.md noch AGENTS.md unter $dir" -Status 'gesichert' -Vorschlag 'Bei frischem Checkout oder toter Junction erwartbar; sonst klaeren'
            continue
        }
        if ($hc -ne $ha) {
            $fehlt = 'AGENTS.md'
            if (-not $hc) { $fehlt = 'CLAUDE.md' }
            Add-Befund -Id "REGELPAAR-FEHLT-$ort" -Modul 'regelpaare' -Schwere 'WARNUNG' -Titel "Regelpaar '$ort': $fehlt fehlt" `
                -Beleg "Test-Path negativ fuer $fehlt unter $dir" -Status 'gesichert' -Vorschlag 'Partnerdatei aus der vorhandenen herstellen (Paar muss identisch bleiben) - nach Freigabe'
            continue
        }
        $bc = [System.IO.File]::ReadAllBytes($c)
        $ba = [System.IO.File]::ReadAllBytes($a)
        $gleichBytes = ($bc.Length -eq $ba.Length) -and ([Convert]::ToBase64String($bc) -ceq [Convert]::ToBase64String($ba))
        if ($gleichBytes) { continue }
        $tc = Get-NormalText $bc
        $ta = Get-NormalText $ba
        if ($tc -ceq $ta) {
            $crC = [regex]::Matches([System.Text.Encoding]::UTF8.GetString($bc), "`r`n").Count
            $crA = [regex]::Matches([System.Text.Encoding]::UTF8.GetString($ba), "`r`n").Count
            Add-Befund -Id "REGELPAAR-ZEILENENDE-$ort" -Modul 'regelpaare' -Schwere 'HINWEIS' -Titel "Regelpaar '$ort': nur Zeilenenden/BOM verschieden" `
                -Beleg "CLAUDE.md $($bc.Length) Bytes (CRLF $crC), AGENTS.md $($ba.Length) Bytes (CRLF $crA); Text nach Normalisierung gleich" -Status 'gesichert' `
                -Vorschlag 'Inhaltlich in Ordnung; AGENTS.md soll LF sein - nicht per Rewrite aendern (Hausregel)'
        }
        else {
            $zc = $tc -split "`n"
            $za = $ta -split "`n"
            $n = [Math]::Min($zc.Count, $za.Count)
            $erste = 0
            for ($i = 0; $i -lt $n; $i++) { if ($zc[$i] -cne $za[$i]) { $erste = $i + 1; break } }
            if ($erste -eq 0) { $erste = $n + 1 }
            Add-Befund -Id "REGELPAAR-INHALT-$ort" -Modul 'regelpaare' -Schwere 'WARNUNG' -Titel "Regelpaar '$ort': Inhalt weicht ab" `
                -Beleg "Erste Abweichung in Zeile $erste; CLAUDE.md $($zc.Count) Zeilen, AGENTS.md $($za.Count) Zeilen" -Status 'gesichert' `
                -Vorschlag 'Diff beider Dateien ansehen; die gepflegte Fassung in beide uebernehmen (gezielter Ersatz) - nach Freigabe'
        }
    }
}

# ---------- Modul 4: git-regeln ----------
function Get-Python {
    $venv = Join-Path $Wurzel 'Agenten/Handel/scanner/.venv/Scripts/python.exe'
    if (Test-Path -LiteralPath $venv) { return $venv }
    foreach ($n in 'python', 'python3') {
        $c = Get-Command $n -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($c -and $c.Source -notmatch 'WindowsApps') { return $c.Source }
    }
    return $null
}

# Restbudget des Moduls in ganzen Sekunden fuer den naechsten externen Aufruf (min. 1); 0 = erschoepft.
function Get-RestBudget([System.Diagnostics.Stopwatch]$Uhr) {
    $rest = $ModulLimitSek - $Uhr.Elapsed.TotalSeconds
    if ($rest -le 0) { return 0 }
    return [int][math]::Max(1, [math]::Floor($rest))
}

function Pruefe-GitRegeln {
    $uhr = [System.Diagnostics.Stopwatch]::StartNew()
    if (-not (Test-Path -LiteralPath (Join-Path $Wurzel '.git'))) {
        Add-Befund -Id 'GIT-KEIN-REPO' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Wurzel ist kein Git-Repository' `
            -Beleg "Test-Path negativ: $(Join-Path $Wurzel '.git')" -Status 'gesichert' -Vorschlag 'Nur zur Kenntnis (Test-Fixture oder Export)'
        return
    }
    $gc = Get-Command git -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $gc) {
        Add-Befund -Id 'GIT-FEHLT' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'git nicht im PATH' -Beleg 'Get-Command git liefert nichts' `
            -Status 'gesichert' -Vorschlag 'git installieren oder PATH pruefen'
        return
    }
    $git = $gc.Source
    # Alle git-Aufrufe mit --no-optional-locks: status darf den Index weder auffrischen noch sperren (rein lesend).

    # Zweige gegen die Zweigregel
    $t = Get-RestBudget $uhr
    if ($t -eq 0) {
        Add-Befund -Id 'GIT-ZWEIGE-NICHT-LESBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft' `
            -Beleg "Modul-Limit $ModulLimitSek s verbraucht; for-each-ref nicht gestartet" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
    }
    else { $r = Invoke-Extern -Datei $git -Argumente @('--no-optional-locks', '-C', $Wurzel, 'for-each-ref', '--format=%(refname)', 'refs/heads', 'refs/remotes') -TimeoutSek $t }
    if ($t -eq 0) { }
    elseif ($r.TimedOut -or $r.ExitCode -ne 0) {
        $e1 = (($r.Err -split "`r?`n") | Where-Object { $_.Trim() } | Select-Object -First 1)
        Add-Befund -Id 'GIT-ZWEIGE-NICHT-LESBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Zweige nicht lesbar' `
            -Beleg "TimedOut=$($r.TimedOut) Exit=$($r.ExitCode) $e1" -Status 'gesichert' -Vorschlag 'git for-each-ref von Hand ausfuehren'
    }
    else {
        $erlaubt = '^refs/heads/(master|zwischenstand)$|^refs/remotes/origin/(master|zwischenstand|HEAD)$'
        $fremd = @($r.Out -split "`r?`n" | Where-Object { $_ -and $_ -notmatch $erlaubt } | ForEach-Object { $_ -replace '^refs/(heads|remotes)/', '' })
        if ($fremd.Count -gt 0) {
            Add-Befund -Id 'GIT-ZWEIGE' -Modul 'git-regeln' -Schwere 'WARNUNG' -Titel "$($fremd.Count) Zweig(e) ausserhalb der Zweigregel (nur master, zwischenstand)" `
                -Beleg (($fremd | Select-Object -First 10) -join ', ') -Status 'gesichert' `
                -Vorschlag 'Offene PR-Zweige sind erlaubt (Ausnahme seit 29.09.2026); alle anderen auf master fuehren und loeschen - nur nach Freigabe'
        }
    }

    # ruhende, uncommittete Dateien
    $t = Get-RestBudget $uhr
    if ($t -eq 0) {
        Add-Befund -Id 'GIT-STATUS-NICHT-LESBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft' `
            -Beleg "Modul-Limit $ModulLimitSek s verbraucht; git status nicht gestartet" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
    }
    else { $s = Invoke-Extern -Datei $git -Argumente @('--no-optional-locks', '-c', 'core.quotepath=false', '-C', $Wurzel, 'status', '--porcelain') -TimeoutSek $t }
    if ($t -eq 0) { }
    elseif ($s.TimedOut -or $s.ExitCode -ne 0) {
        Add-Befund -Id 'GIT-STATUS-NICHT-LESBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'git status nicht lesbar oder zu langsam' `
            -Beleg "TimedOut=$($s.TimedOut) Exit=$($s.ExitCode)" -Status 'gesichert' -Vorschlag 'git status von Hand ausfuehren; Index-Sperre oder sehr grosser Arbeitsbaum?'
    }
    else {
        $jetzt = Get-Date
        $alt = New-Object System.Collections.ArrayList
        $zeilen = @($s.Out -split "`r?`n" | Where-Object { $_.Length -gt 3 })
        foreach ($z in ($zeilen | Select-Object -First 300)) {
            $p = $z.Substring(3)
            if ($p -match ' -> ') { $p = ($p -split ' -> ')[-1] }
            if ($p.Length -ge 2 -and $p.StartsWith('"') -and $p.EndsWith('"')) {
                $p = ($p.Substring(1, $p.Length - 2) -replace '\\"', '"') -replace '\\\\', '\'
            }
            $p = $p.TrimEnd('/')
            $it = Get-Item -LiteralPath (Join-Path $Wurzel $p) -Force -ErrorAction SilentlyContinue
            if ($it) {
                $tage = ($jetzt - $it.LastWriteTime).TotalDays
                if ($tage -ge 3) { [void]$alt.Add([pscustomobject]@{ Pfad = $p; Tage = [int]$tage }) }
            }
        }
        if ($alt.Count -gt 0) {
            $aelteste = @($alt | Sort-Object Tage -Descending | Select-Object -First 5)
            $schwere = 'HINWEIS'
            if ($aelteste[0].Tage -ge 7) { $schwere = 'WARNUNG' }
            Add-Befund -Id 'GIT-RUHEND' -Modul 'git-regeln' -Schwere $schwere -Titel "$($alt.Count) uncommittete Eintraege aelter als 3 Tage ($($zeilen.Count) insgesamt geaendert)" `
                -Beleg ('Aelteste: ' + (($aelteste | ForEach-Object { "$($_.Pfad) ($($_.Tage) d)" }) -join '; ')) -Status 'gesichert' `
                -Vorschlag 'Gehoert die Arbeit einer Sitzung? Dann committen (gezielt, nur eigene Dateien) - lange ungesicherte Arbeit war die Ursache gefuehlt verlorener Arbeit'
        }
    }

    # Besitz-Verstoesse
    $bpy = Join-Path $Wurzel 'Agenten/Werkzeuge/bereiche.py'
    if (-not (Test-Path -LiteralPath $bpy)) {
        Add-Befund -Id 'GIT-BESITZ-NICHT-PRUEFBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Besitzpruefung nicht moeglich' `
            -Beleg "Test-Path negativ: $bpy" -Status 'gesichert' -Vorschlag 'Nur zur Kenntnis (Fixture oder Export)'
        return
    }
    $py = Get-Python
    if (-not $py) {
        Add-Befund -Id 'GIT-BESITZ-NICHT-PRUEFBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Besitzpruefung nicht moeglich: kein Python' `
            -Beleg 'Weder venv noch python/python3 im PATH gefunden' -Status 'gesichert' -Vorschlag 'Python bereitstellen'
        return
    }
    $t = Get-RestBudget $uhr
    if ($t -eq 0) {
        Add-Befund -Id 'GIT-BESITZ-NICHT-PRUEFBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft' `
            -Beleg "Modul-Limit $ModulLimitSek s verbraucht; bereiche.py nicht gestartet" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
        return
    }
    # stdin leer schliessen: bereiche.py liest sonst bei Nicht-TTY Pfade von stdin (blockiert/fremde Daten)
    $b = Invoke-Extern -Datei $py -Argumente @($bpy, '--register') -TimeoutSek $t -Arbeitsordner $Wurzel -StdinLeer
    if ($b.TimedOut) {
        Add-Befund -Id 'GIT-BESITZ-NICHT-PRUEFBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Besitzpruefung im Zeitlimit nicht fertig' `
            -Beleg "Abbruch nach $t s" -Status 'gesichert' -Vorschlag 'bereiche.py --register von Hand ausfuehren'
    }
    elseif ($b.ExitCode -eq 1) {
        # --register ohne --aufrufer: Exit 1 heisst Register-Fehler (BEREICHE.json fehlt/ungueltig, Pfad fehlt, Doppeleintrag).
        # ID GIT-BESITZ bleibt stabil; belegt werden die FEHLER-Zeilen.
        $alle = @(($b.Out + "`n" + $b.Err) -split "`r?`n" | Where-Object { $_.Trim() })
        $ab = -1
        for ($i = 0; $i -lt $alle.Count; $i++) { if ($alle[$i] -match '^\s*FEHLER') { $ab = $i; break } }
        if ($ab -ge 0) { $zl = @($alle | Select-Object -Skip $ab -First 6) } else { $zl = @($alle | Select-Object -First 5) }
        Add-Befund -Id 'GIT-BESITZ' -Modul 'git-regeln' -Schwere 'WARNUNG' -Titel 'Bereichs-Register fehlerhaft (bereiche.py --register Exit 1)' `
            -Beleg (($zl | ForEach-Object { $_.Trim() }) -join ' / ') -Status 'gesichert' -Vorschlag 'Agenten/BEREICHE.json pruefen'
    }
    elseif ($b.ExitCode -ne 0) {
        Add-Befund -Id 'GIT-BESITZ-NICHT-PRUEFBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Besitzpruefung lieferte unerwarteten Exit-Code' `
            -Beleg "bereiche.py --register Exit $($b.ExitCode)" -Status 'gesichert' -Vorschlag 'Skript von Hand ausfuehren'
    }
}

# ---------- Modul 5: ballast (nur melden, nichts aufraeumen) ----------
function Get-Levenshtein([string]$a, [string]$b) {
    $la = $a.Length
    $lb = $b.Length
    if ($la -eq 0) { return $lb }
    if ($lb -eq 0) { return $la }
    $prev = 0..$lb
    for ($i = 1; $i -le $la; $i++) {
        $cur = New-Object int[] ($lb + 1)
        $cur[0] = $i
        for ($j = 1; $j -le $lb; $j++) {
            $kosten = 1
            if ($a[$i - 1] -ceq $b[$j - 1]) { $kosten = 0 }
            $cur[$j] = [Math]::Min([Math]::Min($cur[$j - 1] + 1, $prev[$j] + 1), $prev[$j - 1] + $kosten)
        }
        $prev = $cur
    }
    return $prev[$lb]
}

function Pruefe-Ballast {
    $ordner = @('', 'Agenten', 'Agenten/Routinen', 'Agenten/Hermes', 'Agenten/Bus', 'Agenten/Handel', 'Agenten/Werkzeuge')
    $alt = New-Object System.Collections.ArrayList
    $doppel = New-Object System.Collections.ArrayList
    $zwillinge = New-Object System.Collections.ArrayList
    $vermutAlt = 0
    $voll = $false
    foreach ($rel in $ordner) {
        $d = $Wurzel
        $anzeige = '.'
        if ($rel) { $d = Join-Path $Wurzel $rel; $anzeige = $rel }
        if (-not (Test-Path -LiteralPath $d)) { continue }
        $dateien = @(Get-ChildItem -LiteralPath $d -File -Force -ErrorAction SilentlyContinue)
        foreach ($f in $dateien) {
            if ($f.Name -match '(?i)\.(bak|orig|corrupt)($|[._-])') { [void]$alt.Add("$anzeige/$($f.Name)") }
            elseif ($f.Name -match '(?i)\.old($|[._-])|\.vor-') { [void]$alt.Add("$anzeige/$($f.Name)"); $vermutAlt++ }
            if ($f.Name -match '(?i)\.txt$') {
                $basis = $f.Name.Substring(0, $f.Name.Length - 4)
                if ($basis -and (Test-Path -LiteralPath (Join-Path $d $basis) -PathType Leaf)) { [void]$zwillinge.Add("$anzeige/$($f.Name)") }
            }
        }
        if ($voll) { continue }
        $skripte = @($dateien | Where-Object { $_.Extension -match '(?i)^\.(ps1|py|cmd)$' })
        for ($i = 0; $i -lt $skripte.Count -and -not $voll; $i++) {
            for ($j = $i + 1; $j -lt $skripte.Count; $j++) {
                if ($skripte[$i].Extension -ine $skripte[$j].Extension) { continue }
                $na = ($skripte[$i].BaseName.ToLowerInvariant() -replace '[-_ ]', '')
                $nb = ($skripte[$j].BaseName.ToLowerInvariant() -replace '[-_ ]', '')
                if ($na.Length -lt 8 -or $nb.Length -lt 8) { continue }
                # Levenshtein >= Laengendifferenz: dieser Vorfilter aendert kein Ergebnis, spart aber fast alle Aufrufe
                if ([Math]::Abs($na.Length - $nb.Length) -gt 2) { continue }
                if ((Get-Levenshtein $na $nb) -le 2) {
                    [void]$doppel.Add("$anzeige/$($skripte[$i].Name) ~ $($skripte[$j].Name)")
                    if ($doppel.Count -ge 20) { $voll = $true; break }
                }
            }
        }
    }
    $agenten = Join-Path $Wurzel 'Agenten'
    $zusatz = New-Object System.Collections.ArrayList
    if (Test-Path -LiteralPath $agenten) {
        foreach ($n in 'Werkstatt', 'Modelle', 'MaxHirn', 'Agenten') {
            $p = Join-Path $agenten $n
            if (Test-Path -LiteralPath $p) {
                $anz = @(Get-ChildItem -LiteralPath $p -File -Force -ErrorAction SilentlyContinue).Count
                [void]$zusatz.Add("Agenten/$n ($anz Dateien auf Ebene 1)")
            }
        }
    }
    if ($alt.Count -gt 0) {
        # .bak/.orig/.corrupt sind eindeutige Sicherungsendungen (gesichert); .old/.vor- koennen auch
        # gewollte Namen sein (z. B. Notiz "vor-umbau") - steckt ein solcher Treffer drin, nur Vermutung.
        $altStatus = 'gesichert'
        if ($vermutAlt -gt 0) { $altStatus = 'Vermutung' }
        $altBeleg = ($alt | Select-Object -First 12) -join '; '
        if ($alt.Count -gt 12) { $altBeleg += '; ...' }
        Add-Befund -Id 'BALLAST-ALTKOPIEN' -Modul 'ballast' -Schwere 'HINWEIS' -Titel "$($alt.Count) Altkopien (.bak/.orig/.corrupt/.old/.vor-; davon $vermutAlt unsicher)" `
            -Beleg $altBeleg -Status $altStatus -Vorschlag 'Aufraeumen ist Teilprojekt B; vorher Inhalt gegen die aktuelle Datei pruefen'
    }
    if ($doppel.Count -gt 0) {
        $dnAnzahl = "$($doppel.Count)"
        if ($voll) { $dnAnzahl = 'mindestens 20' }
        Add-Befund -Id 'BALLAST-DOPPELNAMEN' -Modul 'ballast' -Schwere 'HINWEIS' -Titel "$dnAnzahl Skriptpaar(e) mit fast gleichem Namen" `
            -Beleg ($doppel -join '; ') -Status 'Vermutung' -Vorschlag 'Pruefen, welches aufgerufen wird (Aufrufer suchen), dann das andere in Teilprojekt B entfernen'
    }
    if ($zwillinge.Count -gt 0) {
        Add-Befund -Id 'BALLAST-TXT-ZWILLINGE' -Modul 'ballast' -Schwere 'HINWEIS' -Titel "$($zwillinge.Count) .txt-Zwilling(e) von Dateien" `
            -Beleg ($zwillinge -join '; ') -Status 'Vermutung' -Vorschlag 'Ist die .txt eine Kopie (z. B. zum Anhaengen an eine Mail)? Dann in Teilprojekt B entfernen'
    }
    if ($zusatz.Count -gt 0) {
        Add-Befund -Id 'BALLAST-ZUSATZORDNER' -Modul 'ballast' -Schwere 'HINWEIS' -Titel 'Ordner unter Agenten/, die wie Wurzelordner heissen' `
            -Beleg ($zusatz -join '; ') -Status 'Vermutung' -Vorschlag 'Inhalt ansehen: gehoert er in die gleichnamige Wurzel? Zusammenfuehren in Teilprojekt B'
    }
}

# === MODULE (neue Pruefe-*-Funktionen oberhalb dieser Zeile einfuegen) ===

$ModulTabelle = [ordered]@{
    'mcp-pfade'  = 'Pruefe-McpPfade'
    'hermes'     = 'Pruefe-Hermes'
    'regelpaare' = 'Pruefe-Regelpaare'
    'git-regeln' = 'Pruefe-GitRegeln'
    'ballast'    = 'Pruefe-Ballast'
    'laufzeit'   = 'Pruefe-Laufzeit'
}
$VersteckteModule = @{
    'selbsttest-fehler'   = 'Pruefe-SelbsttestFehler'
    'selbsttest-langsam'  = 'Pruefe-SelbsttestLangsam'
    'selbsttest-kritisch' = 'Pruefe-SelbsttestKritisch'
}

function Zelle([string]$t) {
    if ($null -eq $t) { return '' }
    return (($t -replace '\|', '\|') -replace '\r?\n', ' ')
}

function Schreibe-Bericht {
    param($Sortiert, $Zaehler, [string]$Ordner)
    $datei = Join-Path $Ordner ('konfig-doktor-' + (Get-Date -Format 'yyyy-MM-dd') + '.md')
    $z = New-Object System.Text.StringBuilder
    [void]$z.AppendLine('# Konfig-Doktor ' + (Get-Date -Format 'yyyy-MM-dd HH:mm'))
    [void]$z.AppendLine('')
    [void]$z.AppendLine('Wurzel: `' + $Wurzel + '`. Rein lesender Lauf; Reparaturen nur nach Freigabe.')
    [void]$z.AppendLine('')
    [void]$z.AppendLine('## Zusammenfassung')
    [void]$z.AppendLine('')
    [void]$z.AppendLine('| Stufe | Anzahl |')
    [void]$z.AppendLine('|---|---|')
    foreach ($s in 'KRITISCH', 'WARNUNG', 'HINWEIS', 'UNKLAR') { [void]$z.AppendLine("| $s | $($Zaehler[$s]) |") }
    $nr = 0
    foreach ($s in 'KRITISCH', 'WARNUNG', 'HINWEIS') {
        $gruppe = @($Sortiert | Where-Object { $_.schwere -eq $s })
        if ($gruppe.Count -eq 0) { continue }
        [void]$z.AppendLine('')
        [void]$z.AppendLine("## $s ($($gruppe.Count))")
        [void]$z.AppendLine('')
        [void]$z.AppendLine('| # | Befund | Belegt durch | Status | Vorschlag |')
        [void]$z.AppendLine('|---|---|---|---|---|')
        foreach ($b in $gruppe) {
            $nr++
            [void]$z.AppendLine("| $nr | $(Zelle $b.titel) | $(Zelle $b.beleg) | $($b.status) | $(Zelle $b.vorschlag) |")
        }
    }
    $unklar = @($Sortiert | Where-Object { $_.schwere -eq 'UNKLAR' })
    if ($unklar.Count -gt 0) {
        [void]$z.AppendLine('')
        [void]$z.AppendLine("## Nicht pruefbar (UNKLAR) ($($unklar.Count))")
        [void]$z.AppendLine('')
        foreach ($b in $unklar) {
            [void]$z.AppendLine("- **$(Zelle $b.titel)** - $(Zelle $b.beleg). Zur Entscheidung fehlt: $(Zelle $b.vorschlag)")
        }
    }
    [System.IO.File]::WriteAllText($datei, $z.ToString(), (New-Object System.Text.UTF8Encoding($false)))
    return $datei
}

# === HAUPTLAUF ===
try {
    $gewaehlt = @($Modul)
    if ($gewaehlt.Count -eq 0) { $gewaehlt = @($ModulTabelle.Keys) }
    foreach ($m in $gewaehlt) {
        $fn = $null
        if ($ModulTabelle.Contains($m)) { $fn = $ModulTabelle[$m] }
        elseif ($VersteckteModule.ContainsKey($m)) { $fn = $VersteckteModule[$m] }
        if (-not $fn) { throw "Unbekanntes Modul: $m" }
        Invoke-Modul -Name $m -Fn $fn
    }

    $berichtZiel = $BerichtOrdner
    if (-not $berichtZiel) { $berichtZiel = Join-Path $Wurzel 'Werkstatt' }
    if (-not $Kurz -and -not (Test-Path -LiteralPath $berichtZiel)) {
        Add-Befund -Id 'BERICHT-ORDNER-FEHLT' -Modul 'doktor' -Schwere 'UNKLAR' -Titel 'Berichtsordner nicht erreichbar' `
            -Beleg "Test-Path negativ: $berichtZiel" -Status 'gesichert' -Vorschlag 'Junction Werkstatt/ pruefen (Modul laufzeit); Bericht wurde nicht geschrieben'
    }

    $rang = @{ KRITISCH = 0; WARNUNG = 1; HINWEIS = 2; UNKLAR = 3 }
    $modulRang = @{}
    $i = 0
    foreach ($k in $ModulTabelle.Keys) { $modulRang[$k] = $i; $i++ }
    $sortiert = @($script:Befunde | Sort-Object @{ Expression = { $rang[$_.schwere] } }, @{ Expression = { if ($modulRang.ContainsKey($_.modul)) { $modulRang[$_.modul] } else { 99 } } })
    $zaehler = @{}
    foreach ($s in 'KRITISCH', 'WARNUNG', 'HINWEIS', 'UNKLAR') { $zaehler[$s] = @($sortiert | Where-Object { $_.schwere -eq $s }).Count }

    $zeile = "konfig-doktor: KRITISCH $($zaehler['KRITISCH']) | WARNUNG $($zaehler['WARNUNG']) | HINWEIS $($zaehler['HINWEIS']) | UNKLAR $($zaehler['UNKLAR'])"
    if ($Kurz) {
        Write-Host $zeile
    }
    else {
        foreach ($s in 'KRITISCH', 'WARNUNG', 'HINWEIS', 'UNKLAR') { Write-Host ("{0,-8} {1}" -f $s, $zaehler[$s]) }
        if (Test-Path -LiteralPath $berichtZiel) {
            $pfad = Schreibe-Bericht -Sortiert $sortiert -Zaehler $zaehler -Ordner $berichtZiel
            Write-Host "Bericht: $pfad"
        }
    }
    if ($PassThru) { $sortiert }
    if ($zaehler['KRITISCH'] -gt 0) { exit 1 } else { exit 0 }
}
catch {
    Write-Host "konfig-doktor: Doktor selbst defekt - $($_.Exception.Message)"
    exit 2
}
