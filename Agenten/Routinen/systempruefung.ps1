# Taegliche Systempruefung (morgens). Von der Aufgabenplanung aufgerufen.
#
# Zweck: nach dem Umzug des KI-Systems (Ordnertrennung 30.08.2026, Modelle als
# Junction auf O:) still gebrochene Dinge frueh sichtbar machen - tote Junctions,
# doppelte Ollama-Stores, absolute Pfade in Skripten, unaufloesbare MCP-Pfade,
# knapper Plattenplatz, fehlgeschlagene geplante Aufgaben.
#
# Zwei Ausgaben:
#   logs\systempruefung-JJJJ-MM-TT.log   - vollstaendiges Protokoll des Laufs
#   logs\systempruefung-letzter-lauf.md  - strukturierter Bericht, stabiler Name.
#     Gliederung: "Seit gestern neu" / "Selbst erledigt" / "Zu entscheiden" /
#     "Zur Kenntnis". Den liest der SessionStart-Hook und der tagesbriefing-Skill.
#
# Aufraeum-Politik (auf Wunsch, 02.09.2026): Eindeutig reproduzierbares raeumt
# die Pruefung selbst - verwaiste Ollama-Blob-Stores, deren Blobs restlos im
# aktiven Store liegen; tote Junctions ausserhalb von node_modules; .venv-Reste
# mit dem Namensteil "kaputt", neben denen ein funktionierendes .venv steht.
# Alles mit Ermessensspielraum wird nur gemeldet, mit fertigem Befehl.
#
# -NurPruefen schaltet die Aufraeum-Schritte ab (fuer gefahrlose Laeufe von Hand).
#
# Schnell bleiben: der 45-GB-Archivzweig unter MaxHirn\ und die vendorten
# Fremd-Baeume (node_modules, .venv, .pnpm, ant.dir.*, hermes-agent) werden beim
# Gehen uebersprungen. Gescannt wird der eigene Code unter Agenten\ und ein
# paar feste Orte. Ziel: unter einer Minute.

param([switch]$NurPruefen)

$ErrorActionPreference = 'Stop'
$wurzel  = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$agenten = Join-Path $wurzel 'Agenten'
$logs    = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$start    = Get-Date
$heute    = $start.ToString('yyyy-MM-dd')
$roh      = Join-Path $logs "systempruefung-$heute.log"
$bericht  = Join-Path $logs 'systempruefung-letzter-lauf.md'
$md_heute = Join-Path $logs "systempruefung-$heute.md"

$getan       = [System.Collections.Generic.List[string]]::new()
$entscheiden = [System.Collections.Generic.List[string]]::new()
$info        = [System.Collections.Generic.List[string]]::new()
$rohzeilen   = [System.Collections.Generic.List[string]]::new()

function Notiz($text)    { $rohzeilen.Add([string]$text); $rohzeilen | Set-Content $roh -Encoding UTF8; Write-Output $text }
# .Target ist mal string, mal string[] - je nach PowerShell-Fassung. Ohne diese
# Normalisierung indiziert $x.Target[0] bei einem string das erste Zeichen ("O").
function ZielVon($fi) { $t = $fi.Target; if ($t -is [System.Array]) { [string]$t[0] } else { [string]$t } }
function Getan($t)       { $getan.Add($t);       Notiz "  [erledigt]  $t" }
function Entscheiden($t) { $entscheiden.Add($t); Notiz "  [Entscheid] $t" }
function Info($t)        { $info.Add($t);        Notiz "  [Info]      $t" }

# Verzeichnisbaum ohne die dicken Fremd-Baeume. Gibt Ordner und Dateien getrennt
# zurueck; in uebersprungene Ordner wird nicht abgestiegen, sie selbst stehen
# aber in $dirs (fuer die Junction-Pruefung ihres eigenen Reparse-Punkts).
$ueberspringen = @('node_modules', '.venv', '.pnpm', '.git', '.hermes-runtime', '__pycache__', 'hermes-agent', '.obsidian')
function Gehe([string]$root) {
  $dirs  = [System.Collections.Generic.List[string]]::new()
  $files = [System.Collections.Generic.List[string]]::new()
  $stack = [System.Collections.Generic.Stack[string]]::new()
  $stack.Push($root)
  while ($stack.Count) {
    $d = $stack.Pop()
    try { $eintraege = [System.IO.Directory]::EnumerateFileSystemEntries($d) } catch { continue }
    foreach ($e in $eintraege) {
      $name = [System.IO.Path]::GetFileName($e)
      if ([System.IO.Directory]::Exists($e)) {
        $dirs.Add($e)
        if ($name -in $ueberspringen -or $name -like 'ant.dir.*' -or $name -like '*kaputt*') { continue }
        $stack.Push($e)
      } else {
        $files.Add($e)
      }
    }
  }
  [pscustomobject]@{ Dirs = $dirs; Files = $files }
}

Notiz "=== Systempruefung $($start.ToString('yyyy-MM-dd HH:mm:ss')) ==="
Notiz "Wurzel: $wurzel"
if ($NurPruefen) { Notiz "Modus: nur pruefen (keine Aufraeum-Schritte)" }

$baum = Gehe $agenten
Notiz "(Agenten-Baum: $($baum.Dirs.Count) Ordner, $($baum.Files.Count) Dateien gescannt)"

# ---------------------------------------------------------------------------
# 1) Git-Drift: uncommittete Arbeit im Vault, Alter des Zwischenstand-Zweigs
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 1) Git ---"
  $offen = @(git -C $wurzel status --porcelain 2>$null)
  if ($offen.Count -eq 0) {
    Info "Arbeitsbaum sauber."
  } else {
    $alt = 0
    foreach ($z in $offen) {
      $p = $z.Substring(3).Trim('"'); $voll = Join-Path $wurzel $p
      if (Test-Path -LiteralPath $voll) {
        if (((Get-Date) - (Get-Item -LiteralPath $voll).LastWriteTime).TotalMinutes -gt 60) { $alt++ }
      }
    }
    if ($alt -gt 0) { Entscheiden "$alt uncommittete Datei(en) aelter als 1 h im Arbeitsbaum - sichern-Skill oder eigener Commit (arbeitsbaum-pruefen.ps1 zeigt welche)." }
    else { Info "$($offen.Count) uncommittete Datei(en), alle juenger als 1 h - vermutlich in Arbeit, liegen lassen." }
  }
  $zw = git -C $wurzel rev-parse --verify --quiet refs/heads/zwischenstand 2>$null
  if ($zw) {
    $zdatum = git -C $wurzel log -1 --format=%cI zwischenstand 2>$null
    if ($zdatum) {
      $stunden = ((Get-Date) - [datetime]::Parse($zdatum)).TotalHours
      if ($stunden -gt 30) { Entscheiden ("Zwischenstand-Zweig ist {0:N0} h alt - laeuft MaxHirn-Zwischenstand noch? (logs\zwischenstand-letzter-lauf.log)" -f $stunden) }
      else { Info ("Zwischenstand-Zweig {0:N0} h alt - frisch." -f $stunden) }
    }
  }
} catch { Notiz "  ! Git-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 2) Tote Reparse-Punkte (Junction-Ziel existiert nicht mehr)
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 2) Tote Junctions ---"
  $reparse = [System.Collections.Generic.List[object]]::new()
  foreach ($d in $baum.Dirs) {
    $fi = Get-Item -LiteralPath $d -Force -EA SilentlyContinue
    if ($fi -and $fi.LinkType -and $fi.Target) { $reparse.Add($fi) }
  }
  $modelleJ = Get-Item -LiteralPath (Join-Path $wurzel 'Modelle') -Force -EA SilentlyContinue
  if ($modelleJ -and $modelleJ.LinkType) { $reparse.Add($modelleJ) }

  $tot = @($reparse | Where-Object { -not (Test-Path -LiteralPath (ZielVon $_)) })
  if ($tot.Count -eq 0) {
    Info "$($reparse.Count) Reparse-Punkte im eigenen Baum, alle Ziele erreichbar."
  }
  foreach ($j in $tot) {
    $rel = $j.FullName.Replace("$wurzel\", '')
    $ziel = ZielVon $j
    $inDeps = $j.FullName -match '\\(node_modules|\.pnpm|\.hermes-runtime)\\'
    if ($NurPruefen -or $inDeps) {
      Entscheiden "Tote Junction: $rel -> $ziel$(if ($inDeps) { ' (in vendorten Abhaengigkeiten - Ordner neu aufbauen oder loeschen)' })"
    } else {
      try { [System.IO.Directory]::Delete($j.FullName, $false); Getan "Tote Junction entfernt: $rel (zeigte auf $ziel)" }
      catch { Entscheiden "Tote Junction, Loeschen fehlgeschlagen ($_): $rel" }
    }
  }
  # Vendorte Fremd-Server, deren node_modules nach dem Umzug ins Leere zeigt:
  # nicht tief scannen, nur den ersten Eintrag als Stichprobe pruefen.
  foreach ($srvDir in (Get-ChildItem (Join-Path $agenten 'MCP-Server') -Directory -EA SilentlyContinue)) {
    $nm = Join-Path $srvDir.FullName 'node_modules'
    if (-not (Test-Path $nm)) { continue }
    $probe = Get-ChildItem $nm -Directory -Force -EA SilentlyContinue | Where-Object { $_.LinkType } | Select-Object -First 1
    if ($probe -and -not (Test-Path -LiteralPath (ZielVon $probe))) {
      Entscheiden "$($srvDir.Name): node_modules besteht aus toten Junctions (zeigen auf den alten MaxHirn-Pfad) - `pnpm install` im Ordner oder den Server loeschen, wenn ungenutzt."
    }
  }
} catch { Notiz "  ! Junction-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 3) Ollama: verwaiste Blob-/Manifest-Stores neben dem aktiven
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 3) Ollama-Stores ---"
  $aktiv = $env:OLLAMA_MODELS
  if (-not $aktiv) { $aktiv = [Environment]::GetEnvironmentVariable('OLLAMA_MODELS', 'User') }
  $modelleJunction = Join-Path $wurzel 'Modelle'
  $mj = Get-Item -LiteralPath $modelleJunction -Force -EA SilentlyContinue
  $modelleReal = if ($mj -and $mj.Target) { ZielVon $mj } else { $modelleJunction }

  if (-not $aktiv) {
    Info "OLLAMA_MODELS ist nicht gesetzt - Store-Pruefung uebersprungen."
  } elseif (-not (Test-Path $modelleReal)) {
    Entscheiden "Modelle-Junction zeigt auf fehlendes $modelleReal."
  } else {
    $aktivReal = $aktiv
    if ($aktiv.ToLower().StartsWith($modelleJunction.ToLower())) { $aktivReal = $modelleReal + $aktiv.Substring($modelleJunction.Length) }
    $aktivBlobs = Join-Path $aktivReal 'blobs'
    if (-not (Test-Path $aktivBlobs)) {
      Entscheiden "Aktiver Ollama-Store $aktivBlobs fehlt - OLLAMA_MODELS zeigt ins Leere."
    } else {
      $aktivNorm = [System.IO.Path]::GetFullPath($aktivReal).TrimEnd('\').ToLower()
      $aktivNamen = @{}
      Get-ChildItem $aktivBlobs -File -Force -EA SilentlyContinue | ForEach-Object { $aktivNamen[$_.Name] = $true }
      $blobDirs = Get-ChildItem $modelleReal -Recurse -Depth 3 -Force -Directory -EA SilentlyContinue -Filter 'blobs'
      $sonst = 0
      foreach ($bd in $blobDirs) {
        if ([System.IO.Path]::GetFullPath($bd.Parent.FullName).TrimEnd('\').ToLower() -eq $aktivNorm) { continue }
        $blobs = @(Get-ChildItem $bd.FullName -File -Force -EA SilentlyContinue)
        if ($blobs.Count -eq 0) { continue }
        $sonst++
        $fremd = @($blobs | Where-Object { -not $aktivNamen.ContainsKey($_.Name) })
        $gb = [math]::Round((($blobs | Measure-Object Length -Sum).Sum) / 1GB, 1)
        $storeDir = $bd.Parent.FullName
        $relStore = $storeDir.Replace($modelleReal, 'O:\Modelle')
        if ($fremd.Count -eq 0) {
          if ($NurPruefen) {
            Entscheiden "Verwaister Ollama-Store $relStore ($gb GB, $($blobs.Count) Blobs) - alle Blobs auch im aktiven Store. Loeschen: Remove-Item '$storeDir\blobs','$storeDir\manifests' -Recurse -Force"
          } else {
            try {
              Remove-Item -LiteralPath $bd.FullName -Recurse -Force
              $mani = Join-Path $storeDir 'manifests'
              if (Test-Path $mani) { Remove-Item -LiteralPath $mani -Recurse -Force }
              Getan "Verwaisten Ollama-Store geleert: $relStore\{blobs,manifests} ($gb GB, $($blobs.Count) doppelte Blobs)."
            } catch { Entscheiden "Verwaister Ollama-Store $relStore ($gb GB), Loeschen fehlgeschlagen: $_" }
          }
        } else {
          Entscheiden "Ollama-Store $relStore ($gb GB): $($fremd.Count) von $($blobs.Count) Blobs gibt es NUR hier - vor dem Loeschen pruefen (evtl. eigenes Modell)."
        }
      }
      if ($sonst -eq 0) { Info "Nur der aktive Ollama-Store vorhanden." }
    }
  }
} catch { Notiz "  ! Ollama-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 4) Kaputte / verwaiste .venv
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 4) Python-Umgebungen ---"
  $venvEltern = @($baum.Dirs | Where-Object { [System.IO.Path]::GetFileName($_) -like '*kaputt*' -and [System.IO.Path]::GetFileName($_) -like '*venv*' })
  foreach ($k in $venvEltern) {
    $rel = $k.Replace("$wurzel\", '')
    $hatEchtes = Test-Path (Join-Path (Split-Path $k -Parent) '.venv\Scripts\python.exe')
    if ($NurPruefen -or -not $hatEchtes) {
      Entscheiden "Venv-Rest '$rel'$(if (-not $hatEchtes) { ' (KEIN funktionierendes .venv daneben - vor dem Loeschen pruefen)' })"
    } else {
      try { Remove-Item -LiteralPath $k -Recurse -Force; Getan "Venv-Rest entfernt: $rel (funktionierendes .venv steht daneben)" }
      catch { Entscheiden "Venv-Rest '$rel', Loeschen fehlgeschlagen: $_" }
    }
  }
  # jedes .venv einmal: pyvenv.cfg -> home muss existieren
  $defekt = 0
  $venvDirs = @($baum.Dirs | Where-Object { [System.IO.Path]::GetFileName($_) -eq '.venv' })
  $venvDirs += (Join-Path $wurzel 'MaxHirn\Archiv\ArchivSuche\.venv')
  foreach ($v in ($venvDirs | Sort-Object -Unique)) {
    $cfg = Join-Path $v 'pyvenv.cfg'
    if (-not (Test-Path $cfg)) { continue }
    $venvHome = ((Get-Content $cfg | Where-Object { $_ -match '^home\s*=' }) -replace '^home\s*=\s*', '').Trim()
    if ($venvHome -and -not (Test-Path $venvHome)) {
      $defekt++
      Entscheiden "Venv zeigt auf fehlenden Python: $($v.Replace("$wurzel\", ''))\pyvenv.cfg -> home=$venvHome (neu erzeugen)."
    }
  }
  if ($venvEltern.Count -eq 0 -and $defekt -eq 0) { Info "$($venvDirs.Count) .venv geprueft, keine kaputt." }
} catch { Notiz "  ! Venv-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 5) Absolute Pfade und Umzugs-Altlasten in eigenem Code
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 5) Pfade in Skripten ---"
  $codeDateien = @()
  $codeDateien += $baum.Files
  $codeDateien += (Get-ChildItem -LiteralPath $wurzel -File -EA SilentlyContinue -Filter '*.ps1' | ForEach-Object FullName)
  $ci = Join-Path $wurzel 'MaxHirn\Archiv\ArchivSuche'
  if (Test-Path $ci) { $codeDateien += (Get-ChildItem -LiteralPath $ci -Recurse -File -EA SilentlyContinue | Where-Object { $_.FullName -notmatch '\\\.venv\\' } | ForEach-Object FullName) }
  $claudeDir = Join-Path $wurzel 'MaxHirn\.claude'
  if (Test-Path $claudeDir) { $codeDateien += (Get-ChildItem -LiteralPath $claudeDir -Recurse -File -EA SilentlyContinue | ForEach-Object FullName) }
  # EIN strenger Filter statt vielen -Include (die ohne -Recurse still ignoriert
  # werden und dann Binaerdateien wie .db mitnehmen): nur echte Skripte, nie .bak.
  $codeDateien = @($codeDateien | Where-Object { $_ -match '\.(ps1|py|psd1)$' -and $_ -notmatch '\.bak' } | Sort-Object -Unique)

  # Muster als Variablen, damit sie nicht selbst als Treffer im eigenen Skript
  # auftauchen. Routinen\umzug\ ist ausgenommen - das sind die eingefrorenen
  # Migrationsskripte, alte Pfade darin sind dort Absicht.
  $musterAbs = [regex]('C' + ':\\Users\\faupe')
  $musterAlt = [regex]('BrainFiles\\MaxHirn\\(MCP-Server|' + 'Claude)|\\' + 'Claude\\Worktrees')
  $absTreffer = @(); $altTreffer = @()
  foreach ($d in $codeDateien) {
    if ($d -match '\\umzug\\') { continue }
    foreach ($m in (Select-String -LiteralPath $d -Pattern $musterAbs -EA SilentlyContinue)) {
      $absTreffer += "$($d.Replace("$wurzel\", '')):$($m.LineNumber)"
    }
    foreach ($m in (Select-String -LiteralPath $d -Pattern $musterAlt -EA SilentlyContinue)) {
      $altTreffer += "$($d.Replace("$wurzel\", '')):$($m.LineNumber)"
    }
  }
  if ($absTreffer.Count -gt 0) { Entscheiden "Absoluter Benutzerpfad in $($absTreffer.Count) Codezeile(n) (Portabilitaet): $($absTreffer -join '; ')" }
  if ($altTreffer.Count -gt 0) { Entscheiden "Veralteter Pfad (vor dem Umzug) in $($altTreffer.Count) Zeile(n): $($altTreffer -join '; ')" }
  if ($absTreffer.Count -eq 0 -and $altTreffer.Count -eq 0) { Info "$($codeDateien.Count) Skripte geprueft, keine absoluten oder veralteten Pfade." }
} catch { Notiz "  ! Pfad-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 6) MCP-Server: command-Pfade in *.mcp.json muessen aufloesen
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 6) MCP-Konfiguration ---"
  $mcpDateien = @(
    (Join-Path $wurzel 'MaxHirn\.mcp.json'),
    (Join-Path $wurzel 'MaxHirn\Archiv\.mcp.json')
  ) + @($baum.Files | Where-Object { [System.IO.Path]::GetFileName($_) -eq '.mcp.json' })
  $mcpProblem = 0; $geprueft = 0
  foreach ($mfp in ($mcpDateien | Sort-Object -Unique)) {
    if (-not (Test-Path $mfp)) { continue }
    $geprueft++
    $dir = Split-Path $mfp -Parent
    try { $cfg = Get-Content $mfp -Raw | ConvertFrom-Json } catch { Entscheiden "MCP-Datei nicht lesbar: $($mfp.Replace("$wurzel\", ''))"; continue }
    if (-not $cfg.mcpServers) { continue }
    foreach ($srv in $cfg.mcpServers.PSObject.Properties) {
      $cmd = $srv.Value.command
      if (-not $cmd -or $cmd -match '^(npx|node|python|uvx|uv|cmd|powershell|pwsh)(\.exe)?$') { continue }
      $auf = if ([System.IO.Path]::IsPathRooted($cmd)) { $cmd } else { Join-Path $dir $cmd }
      if (-not (Test-Path $auf)) { $mcpProblem++; Entscheiden "MCP '$($srv.Name)' in $($mfp.Replace("$wurzel\", '')) zeigt auf fehlende Datei: $cmd" }
    }
  }
  if ($mcpProblem -eq 0) { Info "$geprueft .mcp.json geprueft, alle command-Pfade loesen auf." }
} catch { Notiz "  ! MCP-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 7) Plattenplatz
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 7) Plattenplatz ---"
  foreach ($bst in 'C', 'O', 'G') {
    $dv = Get-PSDrive -Name $bst -EA SilentlyContinue
    if (-not $dv) {
      if ($bst -eq 'G') { Entscheiden "Sicherungslaufwerk G: nicht angeschlossen - MaxHirn-Sicherung laeuft ins Leere." } else { Info "Laufwerk ${bst}: nicht vorhanden." }
      continue
    }
    $freiGb = [math]::Round($dv.Free / 1GB, 1)
    $schwelle = @{ C = 20; O = 40; G = 15 }[$bst]
    if ($freiGb -lt $schwelle) { Entscheiden "Laufwerk ${bst}: nur noch $freiGb GB frei (Schwelle $schwelle GB)." }
    else { Info "Laufwerk ${bst}: $freiGb GB frei." }
  }
} catch { Notiz "  ! Platz-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 8) Altlasten: .bak-Dateien, leere Geruest-Ordner, grosse ungeklaerte Bestaende
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 8) Altlasten ---"
  $baks = @($baum.Files | Where-Object { $_ -match '\.bak-' })
  $baks += @(Get-ChildItem -LiteralPath (Join-Path $wurzel 'MaxHirn') -Recurse -Force -File -EA SilentlyContinue -Filter '*.bak-*' |
    Where-Object { $_.FullName -notmatch '\\(node_modules|Referenz)\\' } | ForEach-Object FullName)
  $bakN = @($baks | Sort-Object -Unique).Count
  if ($bakN -ge 20) { Info "$bakN .bak-* Handkopien im Baum - Git versioniert jetzt; koennen gebuendelt weg (.gitignore schuetzt sie, git clean fasst sie nicht an)." }
  elseif ($bakN -gt 0) { Info "$bakN .bak-* Handkopien." }

  $mj2 = Get-Item -LiteralPath (Join-Path $wurzel 'Modelle') -Force -EA SilentlyContinue
  $mr = if ($mj2 -and $mj2.Target) { ZielVon $mj2 } else { $null }
  if ($mr -and (Test-Path $mr)) {
    # "leer?" ueber den lazy Enumerator - nicht rekursiv zaehlen (Ollama-Store!)
    $leer = Get-ChildItem $mr -Directory -Force -EA SilentlyContinue | Where-Object {
      -not ([System.IO.Directory]::EnumerateFileSystemEntries($_.FullName).GetEnumerator().MoveNext())
    }
    if ($leer) { Info "Leere Geruest-Ordner in O:\Modelle: $(($leer | ForEach-Object Name) -join ', ')." }
    $kimi = Join-Path $mr 'Kimi-K2.7-Code'
    if (Test-Path $kimi) {
      $kgb = [math]::Round((Get-ChildItem $kimi -Recurse -File -Force -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1GB, 1)
      Entscheiden "O:\Modelle\Kimi-K2.7-Code belegt $kgb GB - auschecken, behalten oder loeschen? (TASKS T-010)"
    }
  }
} catch { Notiz "  ! Altlasten-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 9) Geplante Aufgaben: fehlgeschlagene / deaktivierte MaxHirn-*-Laeufe
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 9) Geplante Aufgaben ---"
  $tasks = @(Get-ScheduledTask -TaskName 'MaxHirn-*' -EA SilentlyContinue)
  $schlecht = 0
  foreach ($t in $tasks) {
    $i = Get-ScheduledTaskInfo -TaskName $t.TaskName -TaskPath $t.TaskPath -EA SilentlyContinue
    if ($t.State -eq 'Disabled') { $schlecht++; Entscheiden "Aufgabe $($t.TaskName) ist deaktiviert." ; continue }
    # 267009 = laeuft gerade, 267011 = noch nie gelaufen; LastRunTime 1999-11-30
    # ist der "nie"-Platzhalter der Aufgabenplanung.
    $nieGelaufen = ($i.LastTaskResult -eq 267011) -or (-not $i.LastRunTime) -or ($i.LastRunTime.Year -lt 2000)
    if ($i -and $i.LastTaskResult -ne 0 -and $i.LastTaskResult -ne 267009 -and -not $nieGelaufen) {
      $schlecht++
      Entscheiden "Aufgabe $($t.TaskName): letzter Lauf $($i.LastRunTime) endete mit Code $($i.LastTaskResult)."
    }
    # Eine taegliche Aufgabe, die zwei Tage nicht gestartet ist, meldet keinen
    # Fehler - sie schweigt. Genau so ist die Hauptsicherung am 31.08. und
    # 01.09.2026 ausgefallen, ohne dass es jemandem aufgefallen waere: Code 1
    # vom 30.08. stand still im Bericht, der ausgebliebene Start nicht.
    if ($i -and -not $nieGelaufen -and $i.LastRunTime -lt (Get-Date).AddHours(-48)) {
      $schlecht++
      $herTage = [int]((Get-Date) - $i.LastRunTime).TotalDays
      Entscheiden "Aufgabe $($t.TaskName) ist seit $herTage Tagen nicht mehr gestartet (zuletzt $($i.LastRunTime)) - Trigger oder Aufgabenplanung pruefen."
    }
  }
  if ($schlecht -eq 0 -and $tasks.Count -gt 0) { Info "Alle $($tasks.Count) MaxHirn-Aufgaben zuletzt fehlerfrei." }
} catch { Notiz "  ! Aufgaben-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 10) Regelwerk: Doppeldateien, Skill-Form, updated-Pflicht
# ---------------------------------------------------------------------------
# Am 02.09.2026 fiel bei einer Durchsicht auf, dass Regeln, die niemand
# nachmisst, still verfallen: die CLAUDE.md/AGENTS.md-Paare waren
# auseinandergelaufen (Hermes kannte die Vektorsuche, Claude nicht), ein Skill
# lag in einer Form vor, in der er nie geladen wird, und die updated-Pflicht
# im Frontmatter wurde fast nirgends eingehalten. Diese drei Pruefungen kosten
# zusammen unter einer Sekunde.
try {
  Notiz "`n--- 10) Regelwerk ---"
  $regelfehler = 0

  # 10a) Die vier Doppeldateien muessen Zeichen fuer Zeichen gleich sein.
  $paare = @(
    @{ a = 'CLAUDE.md';                  b = 'AGENTS.md';                  ort = 'Wurzel'   },
    @{ a = 'MaxHirn\CLAUDE.md';          b = 'MaxHirn\AGENTS.md';          ort = 'MaxHirn'  },
    @{ a = 'MaxHirn\Archiv\CLAUDE.md';   b = 'MaxHirn\Archiv\AGENTS.md';   ort = 'Archiv'   },
    @{ a = 'Werkstatt\CLAUDE.md';        b = 'Werkstatt\AGENTS.md';        ort = 'Werkstatt'}
  )
  foreach ($p in $paare) {
    $pa = Join-Path $wurzel $p.a; $pb = Join-Path $wurzel $p.b
    if (-not (Test-Path $pa) -or -not (Test-Path $pb)) {
      $regelfehler++; Entscheiden "Regeldatei fehlt: $($p.a) oder $($p.b)."; continue
    }
    $ha = (Get-FileHash $pa -Algorithm SHA256).Hash
    $hb = (Get-FileHash $pb -Algorithm SHA256).Hash
    if ($ha -ne $hb) {
      $regelfehler++
      Entscheiden "Regelpaar $($p.ort): CLAUDE.md und AGENTS.md sind auseinandergelaufen - Claude und Hermes arbeiten nach verschiedenen Staenden. Vergleich: git diff --no-index `"$($p.a)`" `"$($p.b)`""
    }
  }

  # 10b) Skills muessen Ordner mit SKILL.md sein. Eine lose .md im skills-Ordner
  #      wird nie geladen - das Wissen darin ist vorhanden, aber unerreichbar.
  $skills = Join-Path $wurzel 'MaxHirn\.claude\skills'
  if (Test-Path $skills) {
    Get-ChildItem $skills -File -Filter *.md -EA SilentlyContinue | ForEach-Object {
      $regelfehler++
      Entscheiden "Skill $($_.Name) liegt lose in .claude\skills\ statt als Ordner mit SKILL.md - er wird in keiner Sitzung geladen."
    }
    Get-ChildItem $skills -Directory -EA SilentlyContinue | ForEach-Object {
      if (-not (Test-Path (Join-Path $_.FullName 'SKILL.md'))) {
        $regelfehler++
        Entscheiden "Skill-Ordner $($_.Name) hat keine SKILL.md - wird nicht geladen."
      }
    }
  }

  # 10c) updated-Pflicht: Wer eine Notiz aendert, setzt updated hoch.
  #      Als Entscheidung gemeldet wird nur, was gerade uncommittet im
  #      Arbeitsbaum liegt - da ist der Autor noch am Werk und kann es
  #      nachziehen. Heute bereits committete Notizen kommen nur als eine
  #      gebuendelte Info-Zeile: Der erste Lauf dieser Pruefung am 02.09.2026
  #      meldete 14 Notizen, weil ein einziger Pfad-Commit sie alle beruehrt
  #      hatte, ohne einen Inhalt zu aendern. Eine Pruefung, die so etwas als
  #      offenen Punkt fuehrt, wird nach zwei Tagen ueberlesen.
  Push-Location $wurzel
  try {
    $heuteISO = (Get-Date).ToString('yyyy-MM-dd')
    $ausnahmen = @('Zugaenge.md','Passwoerter-Quarantaene.md')

    function UpdatedWert($pfad) {
      $z = Select-String -Path $pfad -Pattern '^updated:' -EA SilentlyContinue | Select-Object -First 1
      if ($z) { ($z.Line -replace '^updated:\s*','').Trim(" '`"") } else { $null }
    }

    $offen = @(git status --porcelain -- MaxHirn/Wissen 2>$null |
               ForEach-Object { ($_ -replace '^.{3}','').Trim('"') } |
               Where-Object { $_ -like '*.md' })
    foreach ($rel in ($offen | Sort-Object -Unique)) {
      $f = Join-Path $wurzel $rel   # $rel traegt Vorwaerts-Slashes aus git; Join-Path und Test-Path kommen damit zurecht
      if (-not (Test-Path $f)) { continue }
      if ((Split-Path $f -Leaf) -in $ausnahmen) { continue }
      $wert = UpdatedWert $f
      if ($wert -and $wert -ne $heuteISO) {
        $regelfehler++
        Entscheiden "Notiz $rel ist geaendert und noch nicht committet, updated steht aber auf $wert - im Frontmatter nachziehen."
      }
    }

    $heuteCommit = @(git log --since=midnight --name-only --pretty=format: -- MaxHirn/Wissen 2>$null |
                     Where-Object { $_ -like '*.md' } | Sort-Object -Unique)
    $veraltet = @()
    foreach ($rel in $heuteCommit) {
      $f = Join-Path $wurzel $rel   # $rel traegt Vorwaerts-Slashes aus git; Join-Path und Test-Path kommen damit zurecht
      if (-not (Test-Path $f)) { continue }
      if ((Split-Path $f -Leaf) -in $ausnahmen) { continue }
      $wert = UpdatedWert $f
      if ($wert -and $wert -ne $heuteISO) { $veraltet += (Split-Path $f -Leaf) }
    }
    if ($veraltet.Count -gt 0) {
      Info "$($veraltet.Count) heute committete Notizen tragen ein aelteres updated: $($veraltet -join ', '). Bei reinen Pfad- oder Formalaenderungen ist das richtig so."
    }
  } finally { Pop-Location }

  if ($regelfehler -eq 0) { Info "Regelwerk in Ordnung: 4 Doppeldateien deckungsgleich, Skills vollstaendig, updated-Pflicht eingehalten." }
} catch { Notiz "  ! Regelwerk-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# Bericht schreiben
# ---------------------------------------------------------------------------
$vortag = Get-ChildItem $logs -Filter 'systempruefung-*.md' -EA SilentlyContinue |
  Where-Object { $_.Name -ne 'systempruefung-letzter-lauf.md' -and $_.BaseName -ne "systempruefung-$heute" } |
  Sort-Object Name | Select-Object -Last 1
$neuZeilen = [System.Collections.Generic.List[string]]::new()
if ($vortag) {
  $altText = Get-Content $vortag.FullName -Raw
  foreach ($e in $entscheiden) { if ($altText -notlike "*$e*") { $neuZeilen.Add($e) } }
} else {
  foreach ($e in $entscheiden) { $neuZeilen.Add($e) }
}

$sek = [int]((Get-Date) - $start).TotalSeconds
$md = [System.Collections.Generic.List[string]]::new()
$md.Add("# Systempruefung $heute")
$md.Add("")
$md.Add("_Lauf $($start.ToString('HH:mm')), Dauer $sek s. Vollprotokoll: ``Agenten\Routinen\logs\systempruefung-$heute.log``._")
$md.Add("")
if ($neuZeilen.Count -gt 0) {
  $md.Add("## Seit gestern neu")
  foreach ($z in $neuZeilen) { $md.Add("- $z") }
  $md.Add("")
}
$md.Add("## Selbst erledigt ($($getan.Count))")
if ($getan.Count -eq 0) { $md.Add("- nichts") } else { foreach ($z in $getan) { $md.Add("- $z") } }
$md.Add("")
$md.Add("## Zu entscheiden ($($entscheiden.Count))")
if ($entscheiden.Count -eq 0) { $md.Add("- nichts offen") } else { foreach ($z in $entscheiden) { $md.Add("- $z") } }
$md.Add("")
$md.Add("## Zur Kenntnis")
foreach ($z in $info) { $md.Add("- $z") }
$md.Add("")

$md | Set-Content $bericht -Encoding UTF8
$md | Set-Content $md_heute -Encoding UTF8

Get-ChildItem $logs -Filter 'systempruefung-*.*' -EA SilentlyContinue |
  Where-Object { $_.Name -ne 'systempruefung-letzter-lauf.md' -and $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item -Force -EA SilentlyContinue

Notiz "`nENDE ok - $($getan.Count) erledigt, $($entscheiden.Count) zu entscheiden, $($neuZeilen.Count) davon neu seit gestern (Dauer $sek s)"
exit 0
