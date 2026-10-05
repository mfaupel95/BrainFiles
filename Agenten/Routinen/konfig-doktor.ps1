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
        [string[]]$EntferneEnv = @(), [hashtable]$SetzeEnv = @{}, [string]$Arbeitsordner = ''
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Datei
    $psi.Arguments = (@($Argumente | ForEach-Object { if ($_ -eq '' -or $_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }) -join ' ')
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    if ($Arbeitsordner) { $psi.WorkingDirectory = $Arbeitsordner }
    foreach ($e in $EntferneEnv) { [void]$psi.EnvironmentVariables.Remove($e) }
    foreach ($k in $SetzeEnv.Keys) { $psi.EnvironmentVariables[$k] = [string]$SetzeEnv[$k] }
    $p = [System.Diagnostics.Process]::Start($psi)
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
