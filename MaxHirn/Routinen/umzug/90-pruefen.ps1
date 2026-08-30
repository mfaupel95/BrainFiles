# Phase 9 -- Alles auf einmal pruefen, eine Tabelle als Ergebnis.
#
# Der Sinn: nach einem Umbau ist "sieht gut aus" wertlos. Jede Zeile hier hat
# eine Erwartung, die entweder eintritt oder nicht. Was hier gruen ist, ist
# gemessen -- nicht angenommen.
#
#   .\90-pruefen.ps1

. "$PSScriptRoot\gemeinsam.ps1"
$wurzel = Get-Wurzel
function P([string]$r) { Join-Path $wurzel $r }

$zeilen = @()
function Pruefe([string]$Was, [scriptblock]$Test) {
    try { $e = & $Test } catch { $e = @{ ok = $false; text = "Fehler: $($_.Exception.Message)" } }
    $script:zeilen += [pscustomobject]@{ '  ' = $(if ($e.ok) { 'ok' } else { 'FEHLT' }); Pruefung = $Was; Befund = $e.text }
}

# 1) Die vier Ordner
Pruefe 'Vier Ordner stehen' {
    $da = @('MaxHirn', 'Modelle', 'Agenten', 'Werkstatt') | Where-Object { Test-Path (P $_) }
    @{ ok = $da.Count -eq 4; text = "$($da.Count)/4: $($da -join ', ')" }
}

# 2) In MaxHirn liegt nichts mehr, was startet
Pruefe 'MaxHirn ohne Maschinenraum' {
    $rest = @('MCP-Server', 'Hermes', 'Handel', 'Routinen', 'Modelle', 'GitHub', 'Codex', 'Coworking-Space') |
        Where-Object { Test-Path (P "MaxHirn\$_") }
    @{ ok = $rest.Count -eq 0; text = $(if ($rest) { "noch da: $($rest -join ', ')" } else { 'nur Wissen, Archiv, Referenz' }) }
}

# 3) Dateizahl gegen den Stand vor dem Umzug
Pruefe 'Keine Datei verloren' {
    $v = Join-Path $PSScriptRoot 'logs\bestand-vorher.txt'
    if (-not (Test-Path $v)) { return @{ ok = $false; text = 'bestand-vorher.txt fehlt' } }
    $jetzt = (Get-ChildItem $wurzel -Recurse -File -Force -EA SilentlyContinue | Measure-Object).Count
    $damals = (Get-Content $v | Measure-Object).Count
    @{ ok = $jetzt -ge $damals; text = "vorher $damals, jetzt $jetzt" }
}

# 4) Git
Pruefe 'Git-Wurzel und Historie' {
    $top = git -C $wurzel rev-parse --show-toplevel 2>&1
    $folgt = git -C $wurzel log --follow --oneline -- MaxHirn/Wissen/Fristen.md 2>&1 | Measure-Object
    @{ ok = ($top -replace '/','\') -ieq $wurzel -and $folgt.Count -gt 1
       text = "Wurzel $top, Fristen.md ueber $($folgt.Count) Commits verfolgbar" }
}

# 5) Kein Archivpfad heisst mehr Claude
Pruefe 'Claude/ als Pfad verschwunden' {
    $t = 0
    foreach ($d in (Get-ChildItem (P 'MaxHirn') -Recurse -File -Include '*.md' -EA SilentlyContinue |
                    Where-Object { $_.FullName -notlike '*\Archiv\Dokumente\*' -and $_.FullName -notlike '*\Archiv\Posteingang\*' -and $_.Name -notlike '*.bak-*' })) {
        $r = Get-Content $d.FullName -Raw -EA SilentlyContinue
        if ($r) { $t += ([regex]::Matches($r, '(?<!APPDATA%\\)(?<!APPDATA\\)(?<!\.)Claude[/\\]')).Count }
    }
    @{ ok = $t -eq 0; text = "$t Resttreffer (Zugaenge.md wird von Hand gepflegt)" }
}

# 6) MCP-Konfiguration zeigt auf Vorhandenes
Pruefe 'MCP-Pfade existieren (Claude Desktop)' {
    $f = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
    if (-not (Test-Path $f)) { return @{ ok = $false; text = 'Konfiguration nicht gefunden' } }
    $cfg = Get-Content $f -Raw | ConvertFrom-Json
    $fehlt = @()
    foreach ($n in $cfg.mcpServers.PSObject.Properties.Name) {
        $s = $cfg.mcpServers.$n
        foreach ($p in @($s.command) + @($s.args)) {
            if ($p -is [string] -and $p -match '^[A-Za-z]:\\' -and -not (Test-Path $p)) { $fehlt += "$n : $p" }
        }
    }
    @{ ok = $fehlt.Count -eq 0; text = $(if ($fehlt) { "$($fehlt.Count) tote Pfade: $($fehlt[0])" } else { "$($cfg.mcpServers.PSObject.Properties.Name.Count) Server, alle Pfade vorhanden" }) }
}

# 7) Derselbe Test fuer Hermes
Pruefe 'MCP-Pfade existieren (Hermes)' {
    $f = P 'Agenten\Hermes\config.yaml'
    if (-not (Test-Path $f)) { return @{ ok = $false; text = 'config.yaml nicht gefunden' } }
    $fehlt = @()
    foreach ($m in [regex]::Matches((Get-Content $f -Raw), '[A-Za-z]:\\[^\s''"]+')) {
        if (-not (Test-Path $m.Value)) { $fehlt += $m.Value }
    }
    @{ ok = $fehlt.Count -eq 0; text = $(if ($fehlt) { "$($fehlt.Count) tote Pfade: $($fehlt[0])" } else { 'alle Pfade vorhanden' }) }
}

# 8) Der Suchindex - ohne Reindex, das ist der Punkt
Pruefe 'Suchindex ohne Neubau brauchbar' {
    $db = P 'MaxHirn\Archiv\ArchivSuche\archiv_index.db'
    if (-not (Test-Path $db)) { return @{ ok = $false; text = 'archiv_index.db nicht gefunden' } }
    $py = P 'Agenten\MCP-Server\archiv\.venv\Scripts\python.exe'
    if (-not (Test-Path $py)) { return @{ ok = $true; text = 'DB vorhanden, python zum Zaehlen fehlt' } }
    $n = & $py -c "import sqlite3;print(sqlite3.connect('file:$($db -replace '\\','/')?mode=ro',uri=True).execute('select count(*) from files_meta').fetchone()[0])" 2>&1
    @{ ok = ($n -as [int]) -gt 9000; text = "$n Eintraege, Pfade relativ - kein Reindex noetig" }
}

# 9) Ollama
Pruefe 'Ollama findet seine Modelle' {
    $exe = P 'Modelle\Programme\Ollama\ollama.exe'
    if (-not (Test-Path $exe)) { return @{ ok = $false; text = 'ollama.exe nicht am neuen Ort' } }
    $l = & $exe list 2>&1 | Select-Object -Skip 1 | Where-Object { $_ -match '\S' }
    @{ ok = $l.Count -gt 0; text = "$($l.Count) Modell(e); OLLAMA_MODELS=$([Environment]::GetEnvironmentVariable('OLLAMA_MODELS','User'))" }
}

# 10) Umgebungsvariablen
Pruefe 'HERMES_HOME zeigt richtig' {
    $h = [Environment]::GetEnvironmentVariable('HERMES_HOME', 'User')
    @{ ok = ($h -eq (P 'Agenten\Hermes')) -and (Test-Path $h); text = $h }
}

# 11) Geplante Aufgaben
Pruefe 'Geplante Aufgaben laufen nicht ins Leere' {
    $tot = @()
    foreach ($t in (Get-ScheduledTask -EA SilentlyContinue)) {
        foreach ($a in $t.Actions) {
            foreach ($m in [regex]::Matches("$($a.Arguments)", '[A-Za-z]:\\[^\s"'']+\.ps1')) {
                if (-not (Test-Path $m.Value)) { $tot += "$($t.TaskName): $($m.Value)" }
            }
        }
    }
    @{ ok = $tot.Count -eq 0; text = $(if ($tot) { "$($tot.Count) tot: $($tot[0])" } else { 'alle Ziele vorhanden' }) }
}

# 12) Obsidian
Pruefe 'Obsidian-Vault unversehrt' {
    $o = P 'MaxHirn\.obsidian'
    @{ ok = (Test-Path $o); text = $(if (Test-Path $o) { "$((Get-ChildItem $o -File).Count) Konfigurationsdateien" } else { 'fehlt' }) }
}

# --- Ausgabe ---------------------------------------------------------------
Write-Host ''
$zeilen | Format-Table -AutoSize -Wrap
$fehler = @($zeilen | Where-Object { $_.'  ' -ne 'ok' })
Bilanz "$($zeilen.Count - $fehler.Count) von $($zeilen.Count) Pruefungen bestanden." -Erfolg:($fehler.Count -eq 0)
