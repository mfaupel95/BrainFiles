# Phase 3 -- Alles, was laeuft, nach Agenten/ und alle Pfade nachziehen.
#
# ACHTUNG: Dieses Skript laesst sich NICHT aus einer laufenden Claude-Sitzung
# heraus ausfuehren. Gemessen am 30.08.2026 liefen 21 Prozesse aus
# MaxHirn\MCP-Server -- von Claude Desktop gestartete MCP-Server. Windows
# verweigert das Umbenennen eines Ordners, unter dem eine laufende .exe liegt.
# Erst Claude Desktop und Codex beenden, dann dieses Skript in einem normalen
# PowerShell-Fenster starten.
#
# Was hier ausser dem Verschieben passiert, und warum es passieren muss:
#
#   1. archiv_mcp.py rechnet den Vault aus der eigenen Lage aus (parents[2]).
#      Nach dem Umzug ergaebe das Agenten\ statt MaxHirn\ -- die Archivsuche
#      faende ihren Index nicht und wuerde das nur melden, wenn jemand hinsieht.
#   2. Sieben .venv enthalten editable installs: .pth-Dateien und ein
#      _finder.py mit absoluten Pfaden auf den alten Ort.
#   3. Zwei Server werden ueber ein .exe-Startprogramm aufgerufen, in dem der
#      absolute Pfad zu python.exe im Binaercode steht. Sie werden auf
#      python.exe -c "..." umgestellt, damit nichts neu gebaut werden muss.
#   4. Sechs geplante Aufgaben zeigen auf MaxHirn\Routinen bzw. MaxHirn\Handel.
#      Eine Aufgabe, die ins Leere laeuft, meldet trotzdem Erfolg.
#
#   .\30-agenten.ps1            Trockenlauf
#   .\30-agenten.ps1 -Echt      wirklich

param([switch]$Echt)
$DryRun = -not $Echt

. "$PSScriptRoot\gemeinsam.ps1"
$pfade  = Get-Pfade
$wurzel = Get-Wurzel
function P([string]$r) { Join-Path $wurzel $r }

$altBasis = (P 'MaxHirn\MCP-Server')
$neuBasis = (P 'Agenten\MCP-Server')

Schritt "Wurzel: $wurzel"

# --- 0. Blockierer ---------------------------------------------------------
$blocker = Get-Process | Where-Object { $_.Path -like "*BrainFiles\MaxHirn\MCP-Server*" -or $_.Path -like "*BrainFiles\MaxHirn\Hermes*" }
$claude  = Get-Process -Name 'Claude', 'codex' -ErrorAction SilentlyContinue
if ($blocker -or $claude) {
    Schritt 'Es laufen noch Programme, die den Umzug blockieren:' 'fehler'
    $blocker | Group-Object Name | ForEach-Object { Schritt "  $($_.Name): $($_.Count) Prozess(e) aus MaxHirn" 'fehler' }
    if ($claude) { Schritt "  Claude Desktop / Codex laeuft ($($claude.Count) Prozesse)" 'fehler' }
    Schritt ''
    Schritt 'Erst Claude Desktop und Codex beenden, dann dieses Skript neu starten.' 'warn'
    if (-not $DryRun) { Bilanz 'abgebrochen - Programme laufen noch.' -Erfolg:$false; return }
}

# --- 1. archiv_mcp.py: den Vault nicht mehr aus der Lage raten -------------
Schritt ''
$mcp = if (Test-Path (Join-Path $altBasis 'archiv\archiv_mcp.py')) { Join-Path $altBasis 'archiv\archiv_mcp.py' } else { Join-Path $neuBasis 'archiv\archiv_mcp.py' }
$altBlock = @'
VAULT = Path(__file__).resolve().parents[2]
ARCHIV = VAULT / "Claude"
'@
$neuBlock = @'
VAULT = Path(os.environ.get("MAXHIRN_VAULT") or (Path(__file__).resolve().parents[3] / "MaxHirn"))
ARCHIV = VAULT / "Archiv"
'@
if (Test-Path $mcp) {
    $inhalt = Get-Content -LiteralPath $mcp -Raw
    if ($inhalt -match 'parents\[2\]') {
        Sicherungskopie -Datei $mcp -DryRun:$DryRun | Out-Null
        if (-not $DryRun) {
            $neu = $inhalt.Replace($altBlock.Replace("`r`n","`n"), $neuBlock.Replace("`r`n","`n"))
            if ($neu -eq $inhalt) { $neu = $inhalt -replace 'VAULT = Path\(__file__\)\.resolve\(\)\.parents\[2\]', ($neuBlock -split "`n")[0] -replace 'ARCHIV = VAULT / "Claude"', 'ARCHIV = VAULT / "Archiv"' }
            if ($neu -notmatch '(?m)^import os$') { $neu = $neu -replace '(?m)^import sys$', "import os`nimport sys" }
            [System.IO.File]::WriteAllText($mcp, $neu, (New-Object System.Text.UTF8Encoding $false))
            Schritt 'archiv_mcp.py: VAULT ueber MAXHIRN_VAULT, ARCHIV auf "Archiv" umgestellt.' 'ok'
        } else { Schritt '[Probe] archiv_mcp.py wuerde umgestellt (parents[2] -> MAXHIRN_VAULT, Claude -> Archiv).' }
    } else { Schritt 'archiv_mcp.py ist bereits umgestellt.' 'ok' }
}

# --- 2. Verschieben (Routinen zuletzt: darin laeuft dieses Skript) ---------
Schritt ''
Schritt 'Verschieben:'
foreach ($m in $pfade.Agenten) {
    if ($m.Von -like '*Routinen') { continue }
    Verschiebe -Von (P $m.Von) -Nach (P $m.Nach) -DryRun:$DryRun
}

# --- 3. Editable installs in den .venv --------------------------------------
Schritt ''
$altText = 'MaxHirn\MCP-Server'
$neuText = 'Agenten\MCP-Server'
$basis = if (Test-Path $neuBasis) { $neuBasis } else { $altBasis }
$treffer = 0; $dateien = 0
foreach ($d in (Get-ChildItem $basis -Recurse -Force -File -Include '*.pth', '__editable__*.py' -EA SilentlyContinue)) {
    $n = Ersetze-InDatei -Datei $d.FullName -Ersetzungen @{
        [regex]::Escape('MaxHirn\\MCP-Server') = 'Agenten\\MCP-Server'
        [regex]::Escape($altText)              = $neuText
    } -DryRun:$DryRun
    if ($n -gt 0) { $treffer += $n; $dateien++; Schritt "  $n Pfad(e): $($d.Name)" 'ok' }
}
Schritt "editable installs: $treffer Pfade in $dateien Dateien"

# Was sich per Text nicht heilen laesst, wenigstens benennen.
$exeAlt = @(Get-ChildItem $basis -Recurse -Force -File -Filter '*.exe' -EA SilentlyContinue |
    Where-Object { $_.DirectoryName -like '*\.venv\Scripts' -and
        [System.Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($_.FullName)) -match 'MaxHirn\\MCP-Server' })
if ($exeAlt) {
    Schritt "$($exeAlt.Count) .exe-Startprogramme tragen den alten Pfad im Binaercode:" 'warn'
    $exeAlt | Select-Object -First 6 | ForEach-Object { Schritt "  $($_.Directory.Parent.Parent.Name)\$($_.Name)" 'warn' }
    Schritt '  -> die beiden benutzten (windows-mcp, blender-mcp) werden unten auf python -c umgestellt.' 'warn'
}

# --- 4. Die beiden Konfigurationen -----------------------------------------
Schritt ''
$desktop = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
$hermes  = P 'Agenten\Hermes\config.yaml'
if (-not (Test-Path $hermes)) { $hermes = P 'MaxHirn\Hermes\config.yaml' }

# 4a) Claude Desktop -- als JSON, damit die beiden Server sauber umgebaut werden
if (Test-Path $desktop) {
    Sicherungskopie -Datei $desktop -DryRun:$DryRun | Out-Null
    $roh = Get-Content -LiteralPath $desktop -Raw
    $roh = $roh.Replace('MaxHirn\\MCP-Server', 'Agenten\\MCP-Server')
    $cfg = $roh | ConvertFrom-Json
    $umbau = @{
        'windows-mcp' = @{ Ordner = 'ant.dir.cursortouch.windows-mcp'; Ruf = 'from windows_mcp.__main__ import main; main()' }
        'blender'     = @{ Ordner = 'ant.dir.gh.blender.blender-mcp' ; Ruf = 'from blmcp import main; main()' }
    }
    foreach ($name in $umbau.Keys) {
        $srv = $cfg.mcpServers.$name
        if ($srv -and $srv.command -like '*.exe' -and $srv.command -notlike '*python.exe') {
            $py = Join-Path $neuBasis "$($umbau[$name].Ordner)\.venv\Scripts\python.exe"
            $srv.command = $py
            $srv | Add-Member -NotePropertyName args -NotePropertyValue @('-c', $umbau[$name].Ruf) -Force
            Schritt "  $name -> python.exe -c (statt .exe-Startprogramm)" 'ok'
        }
    }
    if (-not $DryRun) {
        ($cfg | ConvertTo-Json -Depth 20) | Set-Content -LiteralPath $desktop -Encoding UTF8
        Schritt "claude_desktop_config.json neu geschrieben." 'ok'
    } else { Schritt '[Probe] claude_desktop_config.json wuerde neu geschrieben.' }
}

# 4b) Hermes -- als Text, YAML bleibt so, wie Hermes es geschrieben hat
if (Test-Path $hermes) {
    Sicherungskopie -Datei $hermes -DryRun:$DryRun | Out-Null
    $n = Ersetze-InDatei -Datei $hermes -Ersetzungen @{
        [regex]::Escape('MaxHirn\MCP-Server') = 'Agenten\MCP-Server'
        '(?m)^(\s+)command: .*\\ant\.dir\.cursortouch\.windows-mcp\\\.venv\\Scripts\\windows-mcp\.exe\s*$' =
            ('${1}args:' + "`n" + '${1}  - -c' + "`n" + '${1}  - ''from windows_mcp.__main__ import main; main()''' + "`n" +
             '${1}command: ' + (Join-Path $neuBasis 'ant.dir.cursortouch.windows-mcp\.venv\Scripts\python.exe'))
        '(?m)^(\s+)command: .*\\ant\.dir\.gh\.blender\.blender-mcp\\\.venv\\Scripts\\blender-mcp\.exe\s*$' =
            ('${1}args:' + "`n" + '${1}  - -c' + "`n" + '${1}  - ''from blmcp import main; main()''' + "`n" +
             '${1}command: ' + (Join-Path $neuBasis 'ant.dir.gh.blender.blender-mcp\.venv\Scripts\python.exe'))
    } -DryRun:$DryRun
    Schritt "config.yaml: $n Stelle(n) geaendert." 'ok'
}

# --- 5. HERMES_HOME --------------------------------------------------------
Schritt ''
$hh = P 'Agenten\Hermes'
$ist = [Environment]::GetEnvironmentVariable('HERMES_HOME', 'User')
Schritt "HERMES_HOME bisher: $ist"
if (-not $DryRun -and $ist -ne $hh) {
    [Environment]::SetEnvironmentVariable('HERMES_HOME', $hh, 'User')
    Schritt "HERMES_HOME kuenftig: $hh" 'ok'
}

# --- 6. Geplante Aufgaben --------------------------------------------------
Schritt ''
$aufgaben = 0
$altPfad = 'MaxHirn\\(Routinen|Handel)'
function Neu-Pfad([string]$s) {
    $s -replace 'MaxHirn\\Routinen', 'Agenten\Routinen' -replace 'MaxHirn\\Handel', 'Agenten\Handel'
}
foreach ($t in (Get-ScheduledTask -ErrorAction SilentlyContinue)) {
    # Nur Aufgaben anfassen, die den alten Pfad in Argumenten oder
    # Arbeitsverzeichnis tragen. Alle anderen unberuehrt lassen.
    $betroffen = @($t.Actions | Where-Object {
        $_.Arguments -match $altPfad -or $_.WorkingDirectory -match $altPfad
    })
    if (-not $betroffen) { continue }

    $aufgaben++
    Schritt "  Aufgabe '$($t.TaskName)' zeigt auf den alten Pfad"

    # COM-Handler-Aktionen (ohne .Execute) unveraendert durchreichen, sonst
    # Exec-Aktion neu bauen und -Argument/-WorkingDirectory nur setzen, wenn
    # gefuellt -- New-ScheduledTaskAction lehnt leere Werte ab.
    $neuAktionen = foreach ($a in $t.Actions) {
        if ([string]::IsNullOrEmpty($a.Execute)) { $a; continue }
        $nta = @{ Execute = $a.Execute }
        $arg = Neu-Pfad $a.Arguments
        if (-not [string]::IsNullOrEmpty($arg)) { $nta.Argument = $arg }
        $wd = Neu-Pfad $a.WorkingDirectory
        if (-not [string]::IsNullOrEmpty($wd)) { $nta.WorkingDirectory = $wd }
        New-ScheduledTaskAction @nta
    }

    if (-not $DryRun) {
        Set-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath -Action $neuAktionen | Out-Null
        Schritt "    umgehaengt" 'ok'
    }
}
Schritt "geplante Aufgaben betroffen: $aufgaben"

# --- 7. Routinen zuletzt ---------------------------------------------------
# Ab hier gilt $PSScriptRoot nicht mehr, deshalb vorher das Protokoll schreiben.
Schritt ''
Protokoll-Schreiben '30-agenten' | Out-Null
$rout = $pfade.Agenten | Where-Object { $_.Von -like '*Routinen' }
Verschiebe -Von (P $rout.Von) -Nach (P $rout.Nach) -DryRun:$DryRun

if ($DryRun) { Bilanz 'Probe gelaufen - nichts veraendert.' }
else {
    $ziele = @('Agenten\MCP-Server', 'Agenten\Hermes', 'Agenten\Handel', 'Agenten\Routinen') | Where-Object { Test-Path (P $_) }
    Bilanz "$($ziele.Count) von 4 Zielordnern stehen; $treffer venv-Pfade, $aufgaben Aufgaben umgehaengt." -Erfolg:($ziele.Count -eq 4)
}
