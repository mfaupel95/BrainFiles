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

# Bus-Anbindung (Hausmuster): jede geplante Routine meldet Start und Ende.
# Nur beim Lauf gegen das eigene Repo: eine Fixture-Wurzel (Tests) hat keinen Bus,
# und ohne Melde-Ende ging der Exit-Code verloren (immer 0). Stubs statt Journal-Eintraegen.
$eigeneWurzel = [System.IO.Path]::GetFullPath((Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)).TrimEnd('\', '/')
$ereignis = Join-Path $Wurzel 'Agenten\Bus\Ereignis.ps1'
if (($Wurzel -ieq $eigeneWurzel) -and (Test-Path -LiteralPath $ereignis)) { . $ereignis }
else {
    function Melde-Start { param($Wer, $Log) return $null }
    function Melde-Ende { param($Marke, $Code, $Text) }
}
$marke = Melde-Start -Wer 'routine/konfig-doktor' `
           -Log 'Agenten/Routinen/logs/konfig-doktor-letzter-lauf.md'

# ---------- Hilfen ----------
function Maske([string]$t) {
    if ($null -eq $t) { return '' }
    # auch JSON-/YAML-Form: "api_key": "wert" (Schluessel in Anfuehrungszeichen, Wert mit Leerzeichen)
    $t = $t -replace '(?i)((bearer|basic)\s+|(api[_-]?key|token|secret|password)["'']?\s*[:=]\s*)("[^"]*"|''[^'']*''|\S+)', '${1}***'
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
    $uhr = [System.Diagnostics.Stopwatch]::StartNew()
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
        $to = [Math]::Max(1, [Math]::Min($ModulLimitSek - 5, (Get-RestBudget $uhr) - 2))
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
    $uhr = [System.Diagnostics.Stopwatch]::StartNew()
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
            $unlesbar = @()
            foreach ($e in $liste) {
                # "Infinity"/"NaN"/Riesenwerte: AddSeconds wirft - einzeln abfangen statt Modulabsturz
                $t = $null
                try { $t = ConvertTo-Zeit $e.Wert } catch { $unlesbar += $e.Pfad; continue }
                if ($t -and $t -lt $jetzt) { $abgelaufen += ("{0} (seit {1})" -f $e.Pfad, $t.ToString('yyyy-MM-dd')) }
            }
            if ($unlesbar.Count -gt 0) {
                Add-Befund -Id 'HERMES-AUTH-ABLAUF-UNLESBAR' -Modul 'hermes' -Schwere 'UNKLAR' -Titel "$($unlesbar.Count) expires_at-Wert(e) in auth.json nicht als Zeit lesbar" `
                    -Beleg ('Pfade (Werte bewusst nicht ausgegeben): ' + ($unlesbar -join '; ')) -Status 'Vermutung' `
                    -Vorschlag 'Ablauf von Hand im Hermes-Client pruefen (Wert ausserhalb des Datumsbereichs, z. B. Infinity/NaN)'
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
            # Timeout nie ueber dem Restbudget des Moduls (auch bei -ModulLimitSek <= 5)
            $rest = Get-RestBudget $uhr
            $to = [Math]::Min([Math]::Max(5, $ModulLimitSek - 5), [Math]::Max(1, $rest - 1))
            $r = $null
            if ($rest -gt 0) { $r = Invoke-Extern -Datei $hcPfad -Argumente @('doctor') -TimeoutSek $to -EntferneEnv @('PYTHONHOME', 'PYTHONPATH') -SetzeEnv @{ HERMES_HOME = $heim } }
            if ($null -eq $r) {
                Add-Befund -Id 'HERMES-DOCTOR-ZEITLIMIT' -Modul 'hermes' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft, hermes doctor nicht gestartet' `
                    -Beleg "Modul-Limit $ModulLimitSek s verbraucht" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
            }
            elseif ($r.TimedOut) {
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
    return (($t -replace "`r`n", "`n") -replace "`r", "`n")
}

function Pruefe-Regelpaare {
    foreach ($rel in @('', 'MaxHirn', 'Werkstatt')) {
        $dir = $Wurzel
        $ort = 'Wurzel'
        if ($rel) { $dir = Join-Path $Wurzel $rel; $ort = $rel }
        $c = Join-Path $dir 'CLAUDE.md'
        $a = Join-Path $dir 'AGENTS.md'
        $hc = Test-Path -LiteralPath $c -PathType Leaf
        $ha = Test-Path -LiteralPath $a -PathType Leaf
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
            $crC = [regex]::Matches([System.Text.Encoding]::UTF8.GetString($bc), "`r").Count
            $crA = [regex]::Matches([System.Text.Encoding]::UTF8.GetString($ba), "`r").Count
            $bomC = ($bc.Length -ge 3 -and $bc[0] -eq 0xEF -and $bc[1] -eq 0xBB -and $bc[2] -eq 0xBF)
            $bomA = ($ba.Length -ge 3 -and $ba[0] -eq 0xEF -and $ba[1] -eq 0xBB -and $ba[2] -eq 0xBF)
            # betroffen ist, wer CR/BOM traegt (Ziel: LF ohne BOM); tragen beide etwas, beide nennen
            $betroffen = @()
            if ($crC -gt 0 -or $bomC) { $betroffen += 'CLAUDE.md' }
            if ($crA -gt 0 -or $bomA) { $betroffen += 'AGENTS.md' }
            if ($betroffen.Count -eq 0) { $betroffen = @('CLAUDE.md', 'AGENTS.md') }
            Add-Befund -Id "REGELPAAR-ZEILENENDE-$ort" -Modul 'regelpaare' -Schwere 'HINWEIS' -Titel "Regelpaar '$ort': nur Zeilenenden/BOM verschieden" `
                -Beleg "CLAUDE.md $($bc.Length) Bytes (CR $crC, BOM $bomC), AGENTS.md $($ba.Length) Bytes (CR $crA, BOM $bomA); Text nach Normalisierung gleich" -Status 'gesichert' `
                -Vorschlag ("Inhaltlich in Ordnung; abweichend: " + ($betroffen -join ' und ') + " - Zeilenende/BOM angleichen, nicht per Rewrite aendern (Hausregel)")
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
    else { $r = Invoke-Extern -Datei $git -Argumente @('--no-optional-locks', '-C', $Wurzel, 'for-each-ref', '--merged', 'master', '--format=%(refname) %(objectname)', 'refs/heads') -TimeoutSek $t }
    if ($t -eq 0) { }
    elseif ($r.TimedOut -or $r.ExitCode -ne 0) {
        $e1 = (($r.Err -split "`r?`n") | Where-Object { $_.Trim() } | Select-Object -First 1)
        Add-Befund -Id 'GIT-ZWEIGE-NICHT-LESBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Zweige nicht lesbar' `
            -Beleg "TimedOut=$($r.TimedOut) Exit=$($r.ExitCode) $e1" -Status 'gesichert' -Vorschlag 'git for-each-ref von Hand ausfuehren'
    }
    else {
        # Zweigregel seit 08.10.2026: jeder Agent arbeitet auf eigenem Zweig - offene Zweige sind erlaubt.
        # Befund nur fuer Zweige, die schon vollstaendig in master stecken (Merge erledigt, Aufraeumen faellig).
        # Ein frisch abgezweigter Zweig ohne eigenen Commit (gleiche Spitze wie master) zaehlt nicht.
        $zeilen = @($r.Out -split "`r?`n" | Where-Object { $_ })
        $mSpitze = ''
        foreach ($z in $zeilen) { if ($z -match '^refs/heads/master (\S+)$') { $mSpitze = $Matches[1] } }
        $fertig = @($zeilen | Where-Object { $_ -notmatch '^refs/heads/(master|zwischenstand) ' } | Where-Object { ($_ -split ' ')[1] -ne $mSpitze } | ForEach-Object { ($_ -split ' ')[0] -replace '^refs/heads/', '' })
        if ($fertig.Count -gt 0) {
            Add-Befund -Id 'GIT-ZWEIGE' -Modul 'git-regeln' -Schwere 'HINWEIS' -Titel "$($fertig.Count) Zweig(e) bereits in master gemergt" `
                -Beleg (($fertig | Select-Object -First 10) -join ', ') -Status 'gesichert' `
                -Vorschlag 'Zweigregel: nach dem Merge Zweig und Arbeitsbaum loeschen (git branch -d, git worktree remove) - nur nach Freigabe'
        }
    }

    # ruhende, uncommittete Dateien
    $t = Get-RestBudget $uhr
    if ($t -eq 0) {
        Add-Befund -Id 'GIT-STATUS-NICHT-LESBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft' `
            -Beleg "Modul-Limit $ModulLimitSek s verbraucht; git status nicht gestartet" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
    }
    else { $s = Invoke-Extern -Datei $git -Argumente @('--no-optional-locks', '-c', 'core.quotepath=false', '-C', $Wurzel, 'status', '--porcelain', '-z') -TimeoutSek $t }
    if ($t -eq 0) { }
    elseif ($s.TimedOut -or $s.ExitCode -ne 0) {
        Add-Befund -Id 'GIT-STATUS-NICHT-LESBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'git status nicht lesbar oder zu langsam' `
            -Beleg "TimedOut=$($s.TimedOut) Exit=$($s.ExitCode)" -Status 'gesichert' -Vorschlag 'git status von Hand ausfuehren; Index-Sperre oder sehr grosser Arbeitsbaum?'
    }
    else {
        $jetzt = Get-Date
        $alt = New-Object System.Collections.ArrayList
        # -z: Eintraege NUL-getrennt, Pfade unquotiert; bei Umbenennung/Kopie (R/C) folgt der Quellpfad
        # als eigenes Feld und wird uebersprungen - der Zielname zaehlt.
        $felder = @($s.Out -split "`0")
        $zeilen = New-Object System.Collections.ArrayList
        for ($i = 0; $i -lt $felder.Count; $i++) {
            $f = $felder[$i]
            if ($f.Length -le 3) { continue }
            if ($f.Substring(0, 2) -match '[RC]') { $i++ }
            [void]$zeilen.Add($f.Substring(3))
        }
        foreach ($p in ($zeilen | Select-Object -First 300)) {
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
        $altTitel = "$($alt.Count) Altkopien (.bak/.orig/.corrupt/.old/.vor-)"
        if ($vermutAlt -gt 0) { $altTitel = "$($alt.Count) Altkopien (.bak/.orig/.corrupt/.old/.vor-; davon $vermutAlt unsicher)" }
        Add-Befund -Id 'BALLAST-ALTKOPIEN' -Modul 'ballast' -Schwere 'HINWEIS' -Titel $altTitel `
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

# ---------- Modul 6: laufzeit ----------
# Rein lesend. plattenplatz-pruefen.ps1 -OhneOrdner liest nur (Get-PSDrive/CIM). Docker/WSL nur ohne -OhneExtern.
function Pruefe-Laufzeit {
    $uhr = [System.Diagnostics.Stopwatch]::StartNew()
    if ($env:OS -ne 'Windows_NT') {
        Add-Befund -Id 'LAUFZEIT-NICHT-WINDOWS' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'Laufzeitpruefung uebersprungen (kein Windows)' `
            -Beleg 'Linux/Cloud-Checkout: Junctions, Laufwerke, Docker/WSL nicht vergleichbar' -Status 'gesichert' -Vorschlag 'Auf Max'' Rechner ausfuehren'
        return
    }
    foreach ($n in 'Modelle', 'Werkstatt') {
        $p = Join-Path $Wurzel $n
        $item = Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
        $link = 'kein Link'
        if ($item -and $item.LinkType) { $link = "$($item.LinkType) -> $(@($item.Target) -join ',')" }
        if (-not (Test-Path -LiteralPath $p)) {
            Add-Befund -Id "LAUFZEIT-JUNCTION-$n" -Modul 'laufzeit' -Schwere 'KRITISCH' -Titel "$n/ fehlt oder das Junction-Ziel ist nicht erreichbar" `
                -Beleg "Test-Path negativ fuer $p ($link)" -Status 'gesichert' -Vorschlag 'Laufwerk O: pruefen (angeschlossen?), danach Junction neu setzen - nach Freigabe'
            continue
        }
        try { Get-ChildItem -LiteralPath $p -Force -ErrorAction Stop | Select-Object -First 1 | Out-Null }
        catch {
            Add-Befund -Id "LAUFZEIT-JUNCTION-$n" -Modul 'laufzeit' -Schwere 'KRITISCH' -Titel "$n/ ist nicht lesbar" `
                -Beleg "Get-ChildItem scheitert fuer $p ($link)" -Status 'gesichert' -Vorschlag 'Berechtigungen und Laufwerk pruefen'
        }
    }
    $pp = Join-Path $Wurzel 'Agenten/Routinen/plattenplatz-pruefen.ps1'
    $t = Get-RestBudget $uhr
    if (-not (Test-Path -LiteralPath $pp)) {
        Add-Befund -Id 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'plattenplatz-pruefen.ps1 nicht vorhanden' `
            -Beleg "Test-Path negativ: $pp" -Status 'gesichert' -Vorschlag 'Skript wiederherstellen (git)'
    }
    elseif ($t -eq 0) {
        Add-Befund -Id 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft' `
            -Beleg "Modul-Limit $ModulLimitSek s verbraucht; plattenplatz-pruefen.ps1 nicht gestartet" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
    }
    else {
        $ps = (Get-Process -Id $PID).Path
        $r = Invoke-Extern -Datei $ps -Argumente @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $pp, '-OhneOrdner') -TimeoutSek $t -StdinLeer
        if ($r.TimedOut) {
            Add-Befund -Id 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'plattenplatz-pruefen.ps1 antwortet nicht im Zeitlimit' `
                -Beleg "Abbruch nach $t s" -Status 'gesichert' -Vorschlag 'Skript einzeln ausfuehren'
        }
        else {
            $n = 0
            foreach ($z in ($r.Out -split "`r?`n")) {
                if ($z -notmatch '^\s*WARN\b') { continue }
                $n++
                $schwere = 'WARNUNG'
                if ($z -match '^\s*WARN\s+Commit\b') { $schwere = 'KRITISCH' }
                Add-Befund -Id "LAUFZEIT-PLATZ-$n" -Modul 'laufzeit' -Schwere $schwere -Titel ('Platz/Commit: ' + $z.Trim()) `
                    -Beleg "plattenplatz-pruefen.ps1 -OhneOrdner, Ausgabezeile: $($z.Trim())" -Status 'gesichert' `
                    -Vorschlag 'Platz schaffen bzw. Commit-Reserve pruefen (Auslagerungsdatei, Docker/WSL-Speicher); Aufraeumen nur nach Freigabe'
            }
            # Kein stilles Gruen: Ausgabe muss vollstaendig sein und zum Exitcode passen.
            $gruende = New-Object System.Collections.Generic.List[string]
            if ($r.ExitCode -ne 0 -and $r.ExitCode -ne 1) { $gruende.Add("Exit $($r.ExitCode) (erwartet 0 oder 1)") }
            elseif ($r.ExitCode -eq 1 -and $n -eq 0) { $gruende.Add('Exit 1 ohne WARN-Zeile') }
            if ($r.Out -match '(?m)^\s*INFO\s+Commit:\s*nicht lesbar') { $gruende.Add('Commit-Reserve nicht lesbar (INFO Commit: nicht lesbar)') }
            elseif ($r.Out -notmatch '(?m)^\s*(WARN|INFO)\s+Commit\b') { $gruende.Add('keine Commit-Zeile in der Ausgabe') }
            if ($gruende.Count -gt 0) {
                $err = (([string]$r.Err) -replace '\s+', ' ').Trim()
                if ($err.Length -gt 200) { $err = $err.Substring(0, 200) + '...' }
                if (-not $err) { $err = 'leer' }
                Add-Befund -Id 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'Plattenplatz/Commit-Reserve nicht belegbar' `
                    -Beleg ('plattenplatz-pruefen.ps1 -OhneOrdner: ' + ($gruende -join '; ') + "; Exit $($r.ExitCode); stderr: $err") -Status 'gesichert' `
                    -Vorschlag 'plattenplatz-pruefen.ps1 einzeln ausfuehren; Commit-Reserve notfalls im Task-Manager (Leistung, Arbeitsspeicher, Zugesichert) ablesen'
            }
        }
    }
    if (-not $OhneExtern) {
        $d = Get-Command docker -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($d) {
            $t = [math]::Min(10, (Get-RestBudget $uhr))
            if ($t -eq 0) {
                Add-Befund -Id 'LAUFZEIT-DOCKER' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft' `
                    -Beleg "Modul-Limit $ModulLimitSek s verbraucht; docker info nicht gestartet" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
            }
            else {
                $r = Invoke-Extern -Datei $d.Source -Argumente @('info', '--format', '{{.ServerVersion}}') -TimeoutSek $t -StdinLeer
                if ($r.TimedOut -and $t -lt 10) {
                    Add-Befund -Id 'LAUFZEIT-DOCKER' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft' `
                        -Beleg "docker info nach $t s (Restbudget, regulaer 10 s) abgebrochen" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
                }
                elseif ($r.TimedOut) {
                    Add-Befund -Id 'LAUFZEIT-DOCKER' -Modul 'laufzeit' -Schwere 'WARNUNG' -Titel "Docker antwortet nicht binnen $t s" `
                        -Beleg "docker info: Zeitlimit $t s ueberschritten" -Status 'gesichert' `
                        -Vorschlag 'Ein haengendes Docker kann MCP-Server im Kreis neu starten lassen (Spawn-Sturm, siehe Wiki). Docker Desktop neu starten ist Max'' Entscheidung; der Doktor startet nichts'
                }
                elseif ($r.ExitCode -ne 0) {
                    Add-Befund -Id 'LAUFZEIT-DOCKER' -Modul 'laufzeit' -Schwere 'HINWEIS' -Titel 'Docker-Daemon laeuft nicht' `
                        -Beleg "docker info Exit $($r.ExitCode)" -Status 'gesichert' -Vorschlag 'Nur relevant, wenn MCP_DOCKER gebraucht wird'
                }
            }
        }
        $w = Get-Command wsl.exe -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($w) {
            $t = [math]::Min(10, (Get-RestBudget $uhr))
            if ($t -eq 0) {
                Add-Befund -Id 'LAUFZEIT-WSL' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft' `
                    -Beleg "Modul-Limit $ModulLimitSek s verbraucht; wsl --status nicht gestartet" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
            }
            else {
                $r = Invoke-Extern -Datei $w.Source -Argumente @('--status') -TimeoutSek $t -StdinLeer
                if ($r.TimedOut -and $t -lt 10) {
                    Add-Befund -Id 'LAUFZEIT-WSL' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'Zeitbudget erschoepft' `
                        -Beleg "wsl --status nach $t s (Restbudget, regulaer 10 s) abgebrochen" -Status 'gesichert' -Vorschlag 'Mit hoeherem -ModulLimitSek erneut pruefen'
                }
                elseif ($r.TimedOut) {
                    Add-Befund -Id 'LAUFZEIT-WSL' -Modul 'laufzeit' -Schwere 'WARNUNG' -Titel "WSL antwortet nicht binnen $t s" `
                        -Beleg 'wsl --status: Zeitlimit' -Status 'gesichert' -Vorschlag 'Entscheidung ueber Neustart liegt bei Max'
                }
                elseif ($r.ExitCode -ne 0) {
                    Add-Befund -Id 'LAUFZEIT-WSL' -Modul 'laufzeit' -Schwere 'HINWEIS' -Titel 'wsl --status meldet Fehler' `
                        -Beleg "wsl --status Exit $($r.ExitCode)" -Status 'gesichert' -Vorschlag 'Nur relevant, wenn WSL gebraucht wird'
                }
            }
        }
    }
}

# ---------- Modul 7: wurzel (Regel "Wurzel bleibt leer", seit 11.10.2026) ----------
# Erlaubt: die vier Hauptordner, Regeldateien, README, .cmd-Aufrufer, Git-Dateien
# und Konfigurationsordner (.claude, .githooks, ...). Alles andere wird gemeldet;
# bekannte Ablagefehler (Plaene, npm, venv, Dumps, Schluessel) als WARNUNG.
$WurzelErlaubt = @('MaxHirn', 'Modelle', 'Agenten', 'Werkstatt', 'AGENTS.md', 'CLAUDE.md', 'README.md',
    '.gitattributes', '.gitignore')
$WurzelVerboten = @(
    @{ Muster = '^(docs|memory|plans|specs)$'; Grund = 'Plaene/Specs/Handover (superpowers legt docs/superpowers/ an) - gehoeren nach Werkstatt/Projekte bzw. Werkstatt/Austausch' },
    @{ Muster = '^(node_modules|package(-lock)?\.json|pnpm-lock\.yaml|yarn\.lock)$'; Grund = 'npm-Reste (kein npm install in der Wurzel)' },
    @{ Muster = '^(\.?venv|__pycache__)$'; Grund = 'Python-Umgebung/Cache' },
    @{ Muster = '^\.env(\..*)?$|\.(pem|key|p12|pfx)$'; Grund = 'Zugangsdaten/Schluessel - einzige Ablage ist MaxHirn/Wissen/Zugaenge.md' },
    @{ Muster = '^docker-compose.*\.ya?ml$|^compose\.ya?ml$'; Grund = 'Compose-Datei (ein docker compose up startet hier ungeprueft Container)' },
    @{ Muster = '\.(bak|orig|old)($|[._-])'; Grund = 'Sicherungskopie (Stand steht in git)' },
    @{ Muster = '^(handover|report)\b|\.(dmp|log)$'; Grund = 'Sitzungs-/Absturzrest' }
)

function Pruefe-Wurzel {
    $warn = New-Object System.Collections.ArrayList
    $hinw = New-Object System.Collections.ArrayList
    $grund = @{}
    $jetzt = Get-Date
    foreach ($e in @(Get-ChildItem -LiteralPath $Wurzel -Force -ErrorAction SilentlyContinue)) {
        $n = $e.Name
        if ($WurzelErlaubt -contains $n) { continue }
        if (-not $e.PSIsContainer -and $e.Extension -ieq '.cmd') { continue }
        # Konfigurationsordner (.git, .claude, .githooks, .worktrees, Plugin-Ordner) - nicht .venv
        if ($e.PSIsContainer -and $n.StartsWith('.') -and $n -ine '.venv') { continue }
        $tage = [int][Math]::Floor(($jetzt - $e.LastWriteTime).TotalDays)
        $art = 'Datei'
        if ($e.PSIsContainer) { $art = 'Ordner' }
        $eintrag = "$n ($art, $tage Tage alt)"
        $treffer = $null
        foreach ($v in $WurzelVerboten) { if ($n -match $v.Muster) { $treffer = $v.Grund; break } }
        if ($treffer) { [void]$warn.Add($eintrag); $grund[$treffer] = $true }
        else { [void]$hinw.Add($eintrag) }
    }
    if ($warn.Count -gt 0) {
        Add-Befund -Id 'WURZEL-ABLAGEFEHLER' -Modul 'wurzel' -Schwere 'WARNUNG' -Titel "$($warn.Count) Ablagefehler in der Wurzel" `
            -Beleg (($warn -join '; ') + ' | Art: ' + (@($grund.Keys) -join '; ')) -Status 'gesichert' `
            -Vorschlag 'Regel "Wurzel bleibt leer" (CLAUDE.md): nach Werkstatt/ verschieben bzw. loeschen - nach Freigabe, Dateien juenger als 10 min liegen lassen'
    }
    if ($hinw.Count -gt 0) {
        Add-Befund -Id 'WURZEL-UNBEKANNT' -Modul 'wurzel' -Schwere 'HINWEIS' -Titel "$($hinw.Count) unbekannte Eintraege in der Wurzel" `
            -Beleg ($hinw -join '; ') -Status 'Vermutung' `
            -Vorschlag 'Gehoert es in einen der vier Hauptordner? Sonst nach Werkstatt/ - oder in die Erlaubt-Liste von Modul wurzel aufnehmen'
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
    'wurzel'     = 'Pruefe-Wurzel'
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
    if ($zaehler['KRITISCH'] -gt 0) {
        Melde-Ende -Marke $marke -Code 1 -Text "KRITISCH $($zaehler['KRITISCH'])"
        exit 1
    } else {
        Melde-Ende -Marke $marke -Code 0 -Text "ok (KRITISCH 0)"
        exit 0
    }
}
catch {
    Write-Host "konfig-doktor: Doktor selbst defekt - $($_.Exception.Message)"
    Melde-Ende -Marke $marke -Code 2 -Text "Doktor selbst defekt: $($_.Exception.Message)"
    exit 2
}
