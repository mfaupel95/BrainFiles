# Taegliche Systempruefung (morgens). Von der Aufgabenplanung aufgerufen.
#
# Zweck: nach dem Umzug des KI-Systems (Ordnertrennung 30.08.2026, Modelle als
# Junction auf O:) still gebrochene Dinge frueh sichtbar machen - tote Junctions,
# doppelte Ollama-Stores, absolute Pfade in Skripten, unaufloesbare MCP-Pfade,
# MCP-Konfigurations-Drift (Claude/Hermes), knapper Plattenplatz, fehlgeschlagene
# geplante Aufgaben.
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

. (Join-Path $agenten 'Bus\Ereignis.ps1')                                # neu
$marke = Melde-Start -Wer 'routine/systempruefung' `
           -Log 'Agenten/Routinen/logs/systempruefung-letzter-lauf.md'  # neu
try {                                                                    # neu

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
# Get-FileHash fehlt in dieser PowerShell (5.1.26100.9444: Get-Command
# Get-FileHash liefert nichts). Ein Pruefblock, der daran abbricht, sieht im
# Bericht wie ein Lauf aus, der nichts gefunden hat - der Regelwerk-Block 10
# lief so seit seiner Einfuehrung nie. Deshalb ueber .NET rechnen.
function DateiHash($pfad) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try { [BitConverter]::ToString($sha.ComputeHash([System.IO.File]::ReadAllBytes($pfad))) }
  finally { $sha.Dispose() }
}
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
# 0) MCP-Konfiguration: Claude und Hermes in Sync?
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 0) MCP-Sync (Claude + Hermes) ---"
  & powershell -ExecutionPolicy Bypass -File (Join-Path $agenten 'mcp-sync-check.ps1') -Streng 2>$null
  if ($LASTEXITCODE -eq 0) { Info "MCP-Server sind in Sync." }
  else { Entscheiden "MCP-Konfiguration-Drift erkannt - mcp-sync-check.ps1 laufen lassen." }
} catch { Notiz "  ! MCP-Pruefung: $_" }

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
      # Stores, die bewusst hier liegen und deren Blobs es nur hier gibt - sonst
      # meldet der Block sie JEDEN Tag als Entscheiden, und ein Dauerfehlalarm
      # deckt echte Neufunde zu. Nur der NAME steht hier, nie eine Loeschung:
      # ein Store, der nicht in dieser Liste steht, wird weiter gemeldet.
      $gewolltStores = @{
        'models--convaiinnovations--laya-multilingual' = 'laya-Modell (NandhaKishorM/laya), 21.09.2026 geladen - Entscheidung Max'
        'hub'                                          = 'laya-Blob (615 MB) liegt in hub/blobs - derselbe Modellbestand'
      }
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
          $storeName = Split-Path $storeDir -Leaf
          if ($gewolltStores.ContainsKey($storeName)) {
            Info "Ollama-Store $relStore ($gb GB): $($fremd.Count) von $($blobs.Count) Blobs nur hier - gewollt ($($gewolltStores[$storeName]))."
          } else {
            Entscheiden "Ollama-Store $relStore ($gb GB): $($fremd.Count) von $($blobs.Count) Blobs gibt es NUR hier - vor dem Loeschen pruefen (evtl. eigenes Modell)."
          }
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
  # auftauchen. Zwei Orte sind ausgenommen, beide aus Absicht:
  #   Routinen\umzug\   - eingefrorene Migrationsskripte
  #   Hermes\cache\     - Wegwerf- und Probenskripte (nicht versioniert, dort
  #                      ist ein fester Pfad erlaubt). Ohne diese Ausnahme
  #                      meldete der Block jeden Tag dieselben 14 Cache-Dateien
  #                      als Portabilitaetsproblem - ein Dauerfehlalarm deckt
  #                      die echten Funde zu.
  #   Hermes\tmp\ und Hermes\.sicherung\ - dasselbe: Wegwerf bzw. Altkopien,
  #                      beide nicht versioniert (22.09.2026, 11 der 37 Zeilen).
  #   profiles\<bot>\cache\ - der Wegwerf-Ordner JE BOT, dieselbe Sorte wie
  #                      Hermes\cache\. Am 30.09.2026 meldete der Block zwei
  #                      Probenskripte aus profiles\agent-trade-kit\cache\scratch.
  $ausgenommen = @('\\umzug\\', '\\Hermes\\cache\\', '\\Hermes\\tmp\\', '\\Hermes\\.sicherung\\', '\\profiles\\[^\\]+\\cache\\')
  $musterAbs = [regex]('C' + ':\\Users\\faupe')
  $musterAlt = [regex]('BrainFiles\\MaxHirn\\(MCP-Server|' + 'Claude)|\\' + 'Claude\\Worktrees')
  $absTreffer = @(); $altTreffer = @()
  foreach ($d in $codeDateien) {
    if (@($ausgenommen | Where-Object { $d -match $_ }).Count -gt 0) { continue }
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
  $mcpProblem = 0; $geprueft = 0; $fremdAusgelassen = 0
  foreach ($mfp in ($mcpDateien | Sort-Object -Unique)) {
    # Fremd-Repos bringen ihre EIGENE .mcp.json mit (claude-plugins-official,
    # financial-services): dort gilt die Umgebung des Herstellers (bun/node),
    # nicht dieser Rechner. Gemeldet wurden daraus 8 Entscheiden-Zeilen je
    # Lauf - nichts davon ist hier behebbar, ohne ein Fremd-Repo zu verbiegen.
    if ($mfp -match '\\skills\\|\\plugins\\') { $fremdAusgelassen++; continue }
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
  if ($fremdAusgelassen -gt 0) { Info "$fremdAusgelassen .mcp.json in Fremd-Baeumen (skills/, plugins/) ausgelassen - dort gilt die Umgebung des Herstellers." }
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

# 7b) Plattenplatz vertieft: Commit-Reserve und Wachstumsordner (Vorfall 30.09., T-228).
# Schnell zuerst; die Ordnermessung (~75 s) nur, wenn eine Warnung vorliegt.
try {
  $pp = Join-Path $PSScriptRoot 'plattenplatz-pruefen.ps1'
  $ppAus = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $pp -OhneOrdner)
  if ($LASTEXITCODE -ne 0) { $ppAus = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $pp) }
  foreach ($z in $ppAus) {
    if ($z -like 'WARN *') { Entscheiden $z.Substring(5) }
    elseif ($z -like 'INFO Commit*' -or $z -like 'INFO Gross*') { Info $z.Substring(5) }
  }
} catch { Notiz "  ! Platzpruefung (vertieft) abgebrochen: $_" }

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
  # Gewollt deaktivierte Aufgaben: sie werden nicht als Entscheiden gemeldet,
  # nur als Info. Eintrag + Grund. (MoonDev-Agent: ersetzt durch den
  # MoonDev-Dauerlauf, kein Doppelstart.)
  $gewolltDeaktiviert = @{
    'MaxHirn-MoonDev-Agent' = 'ersetzt durch MaxHirn-MoonDev-Dauerlauf'
  }
  # Waechter-Aufgaben, die NIE deaktiviert sein duerfen: ein deaktivierter
  # Waechter ist schutzloser Betrieb. Am 12.10.2026 war der Gateway-Waechter
  # deaktiviert worden; der Gateway-Ausfall am 13.10. (18:13-23:06, Code 75,
  # Liveness-Watchdog) blieb deshalb 5 h unbemerkt. Diese Aufgaben aktiviert
  # die Pruefung selbst wieder (schtasks /Change /ENABLE, keine Admin-Rechte)
  # und meldet es als erledigt.
  $kritischeWaechter = @(
    'MaxHirn-Gateway-Waechter',
    # Live-Spuren brauchen ein Netz: am 12./13.10.2026 waren Basis-Dauerlauf und
    # sein Waechter deaktiviert, die Live-Positionen liefen ohne Ueberwachung.
    # Ein Neustart des Dauerlaufs umgeht KEINE Handels-Gates (handel_erlaubt,
    # Freigabefenster, Kill) - er stellt nur die Ueberwachung wieder her.
    # Mittel-Waechter bewusst NICHT hier: Mittel-Stufe ist dokumentiert abgeschaltet.
    'MaxHirn-Handel-Dauerlauf',
    'MaxHirn-Handel-Dauerlauf-Waechter'
  )
  $schlecht = 0
  foreach ($t in $tasks) {
    $i = Get-ScheduledTaskInfo -TaskName $t.TaskName -TaskPath $t.TaskPath -EA SilentlyContinue
    if ($t.State -eq 'Disabled') {
      if ($gewolltDeaktiviert.ContainsKey($t.TaskName)) {
        Info "Aufgabe $($t.TaskName) ist deaktiviert (gewollt: $($gewolltDeaktiviert[$t.TaskName]))."
      } elseif ($t.TaskName -in $kritischeWaechter) {
        # Deaktivieren stoppt die Neustart-Serie - aber dann laeuft der
        # Gateway ohne Netz. Aktivieren ist immer richtig: ein Waechter wird
        # nicht fuer spaeter deaktiviert, die Ursache gehoert behoben.
        $altEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        try {
          $r = & schtasks /Change /TN $t.TaskName /ENABLE 2>&1
          if ($LASTEXITCODE -eq 0) {
            Getan "Kritischer Waechter $($t.TaskName) war deaktiviert - wieder aktiviert (schtasks /Change /ENABLE)."
          } else {
            $schlecht++; Entscheiden "Kritischer Waechter $($t.TaskName) ist deaktiviert und liess sich nicht aktivieren: $($r -join ' ')"
          }
        } catch {
          $schlecht++; Entscheiden "Kritischer Waechter $($t.TaskName) ist deaktiviert, Aktivierung fehlgeschlagen: $_"
        } finally { $ErrorActionPreference = $altEAP }
      } else {
        $schlecht++; Entscheiden "Aufgabe $($t.TaskName) ist deaktiviert."
      }
      continue
    }
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
    # Erwarteten Abstand aus dem EIGENEN Trigger ableiten. Eine pauschale
    # 48-Stunden-Grenze meldete die beiden Wochenaufgaben (Handel-Wachen,
    # Verbesserer) jeden Tag als "seit 6 Tagen nicht mehr gestartet", obwohl
    # sie planmaessig sonntags laufen. Ein Dauerfehlalarm deckt die echten
    # Funde zu - das ist schlimmer als keine Pruefung.
    $abstandStd = 48
    foreach ($tr in $t.Triggers) {
      switch ($tr.CimClass.CimClassName) {
        'MSFT_TaskWeeklyTrigger' {
          $wochen = if ($tr.WeeksInterval) { [int]$tr.WeeksInterval } else { 1 }
          # eine Woche Luft: verpasste Startfenster holt StartWhenAvailable nach
          $abstandStd = 7 * 24 * $wochen + 24
        }
        'MSFT_TaskMonthlyTrigger'      { $abstandStd = 31 * 24 + 24 }
        'MSFT_TaskMonthlyDOWTrigger'   { $abstandStd = 31 * 24 + 24 }
        # Start bei Hochfahren/Anmeldung hat kein Zeitraster zum Messen.
        'MSFT_TaskBootTrigger'         { $abstandStd = 0 }
        'MSFT_TaskLogonTrigger'        { $abstandStd = 0 }
      }
    }
    if ($i -and -not $nieGelaufen -and $abstandStd -gt 0 -and $i.LastRunTime -lt (Get-Date).AddHours(-$abstandStd)) {
      $schlecht++
      $herTage = [int]((Get-Date) - $i.LastRunTime).TotalDays
      Entscheiden "Aufgabe $($t.TaskName) ist seit $herTage Tagen nicht mehr gestartet (zuletzt $($i.LastRunTime), erwarteter Abstand $abstandStd h) - Trigger oder Aufgabenplanung pruefen."
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
    $ha = DateiHash $pa
    $hb = DateiHash $pb
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
# 11) Handelsspuren: Kopie ausser Haus (Bedingung 4)
# ---------------------------------------------------------------------------
# Ein `journal_zweitziel` in wachen.json ist eine Absicht - kopiert wird erst im
# Zyklus. Am 13.09.2026 hatte nur ein Teil der Spuren wirklich eine Kopie
# ausser Haus, und eine ueberschriebene Kopie (USB-Aussetzer, oder ein Testlauf,
# der seinen Temp-Zustand mitspiegelt) sieht in keinem Bericht wie ein Fehler
# aus. Verglichen wird deshalb BYTE-GENAU gegen die Originale.
# Die Rechnung steht in Agenten\Handel\spiegelstand.py (Rueckgabecode und
# Spalten stehen im Modul: 0 = jede Spur im Dauerlauf byte-gleich). Dieselbe
# Funktion liefert die Zeile im Tagesbericht.
try {
  Notiz "`n--- 11) Journal ausser Haus (Bedingung 4) ---"
  $spiegelSkript = Join-Path $agenten 'Handel\spiegelstand.py'
  $handelPy = Join-Path $agenten 'Handel\scanner\.venv\Scripts\python.exe'
  if (-not (Test-Path $handelPy)) { $handelPy = (Get-Command python -EA SilentlyContinue).Source }
  if (-not (Test-Path $spiegelSkript)) {
    Entscheiden "Pruefskript fuer Bedingung 4 fehlt: Agenten\Handel\spiegelstand.py"
  } elseif (-not $handelPy -or -not (Test-Path $handelPy)) {
    Info "Journal-Spiegelung nicht geprueft - kein Python gefunden."
  } else {
    $aus = @(& $handelPy $spiegelSkript --stunden 2 2>&1)
    $code = $LASTEXITCODE
    foreach ($z in $aus) { Notiz "  $z" }
    # Nur echte Zeilen der Tabelle: nicht eingerueckt und nicht als "ausserhalb
    # des Dauerlaufs" gekennzeichnet (orb/kraken sind kein Fehler).
    $abweichend = @($aus | Where-Object {
        $_ -match 'ABWEICHUNG|Ziel fehlt|kein Ziel' -and $_ -notmatch '^\s' -and $_ -notmatch 'nicht in dauerlauf'
      } | ForEach-Object { ($_ -split '\s+')[0] } | Sort-Object -Unique)
    $alt = @($aus | Where-Object { $_ -match 'Hinweis: Herzschlag' })
    if ($code -eq 0) { Info "Bedingung 4: jede Spur im Dauerlauf byte-gleich mit Q:." }
    elseif ($abweichend.Count -gt 0) {
      Entscheiden "Bedingung 4: Kopie ausser Haus nicht in Ordnung bei $($abweichend -join ', ') - Befehl: python $spiegelSkript"
    } else {
      Entscheiden "Bedingung 4: Pruefung meldete Code $code ohne benennbare Spur - Vollprotokoll ansehen."
    }
    if ($alt.Count -gt 0) { Entscheiden "Herzschlag ueber 2 h alt: $(($alt | ForEach-Object { $_.Trim() }) -join ' | ')" }
  }
} catch { Notiz "  ! Spiegelungs-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 11b) Handelsspuren: passt die Herzschlag-Grenze zur Handelserlaubnis?
# ---------------------------------------------------------------------------
# Bedingung 3 schliesst alle offenen Positionen, wenn der letzte gesunde Lauf
# aelter ist als herzschlag_max_minuten. Der Waechter startet einen toten
# Dauerlauf alle 30 Minuten neu, ein Zyklus dauert 1-2 Minuten - eine Stoerung
# heilt also nach hoechstens rund 32 Minuten von selbst. Regel (14.09., am
# 13.10.2026 wiedereingesetzt nach Ruecknahme der 19.09.-"180 fuer alle"-Regel):
# 180 Minuten fuer Papier-Spuren, 45 Minuten fuer Spuren mit Handelserlaubnis
# (Live) - Live haelt keine offene Marktposition laenger als 45 Minuten
# ungesichert. Diese Pruefung haelt sie fest - ohne sie verfaellt die Regel wie
# die gewachsenen Zahlen davor (30/45/90/180/2880).
try {
  Notiz "`n--- 11b) Handel: Herzschlag-Regel ---"
  $handelsSpuren = @(Get-ChildItem (Join-Path $wurzel 'Agenten\Handel') -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName 'wachen.json') })
  # Ein WERKZEUG traegt kein 'handel_erlaubt' - es haelt nie eine Position, die
  # ein Herzschlag schliessen koennte. Es wird gezaehlt, aber nicht geprueft:
  # `okx_bot_waechter` (Bot-Berater, fuehrt kein Buch) meldete sonst jeden Tag
  # "Herzschlag 0 min statt 180", ohne dass die Zahl etwas bedeutet - und eine
  # taegliche Zeile ohne Bedeutung ist der Anfang, an dem man echte Warnungen
  # ueberliest (29.09.2026).
  $werkzeuge = @()
  $spuren = @()
  foreach ($hs in $handelsSpuren) {
    $wj = Get-Content (Join-Path $hs.FullName 'wachen.json') -Raw | ConvertFrom-Json
    if ($null -eq $wj.PSObject.Properties['handel_erlaubt']) { $werkzeuge += $hs.Name }
    else { $spuren += $hs }
  }
  $regelkonform = 0
  foreach ($hs in $spuren) {
    $wj = Get-Content (Join-Path $hs.FullName 'wachen.json') -Raw | ConvertFrom-Json
    $hm = [int]$wj.herzschlag_max_minuten
    $erlaubt = ($wj.handel_erlaubt -eq $true)
    # Regel 13.10.2026: 45 fuer Spuren mit Handelserlaubnis (Live), 180 fuer Papier.
    $soll = if ($erlaubt) { 45 } else { 180 }
    if ($hm -ne $soll) {
      $art = if ($erlaubt) { 'Spuren mit Handelserlaubnis (Live)' } else { 'Papier-Spuren' }
      Entscheiden "Handel/$($hs.Name): Herzschlag $hm min statt $soll - Regel 13.10.2026: $soll min fuer $art. Ableitung und Folge stehen im Feld _herzschlag_regel dieser wachen.json."
    } else {
      $regelkonform++
    }
  }
  $werkzeugText = if ($werkzeuge.Count -gt 0) { " - ausgenommen als Werkzeug ohne Handelsbuch: $(($werkzeuge | Sort-Object) -join ', ')" } else { "" }
  Info "$regelkonform von $($spuren.Count) Handels-Spuren folgen der Herzschlag-Regel (180 fuer alle, Papier UND Live)$werkzeugText."
} catch { Notiz "  ! Herzschlag-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 12) Handelsspuren: laeuft der Dauerlauf, und dreht er sich noch?
# ---------------------------------------------------------------------------
# Der Dauerlauf ist der einzige Schreiber der Handelsdateien. Faellt er aus,
# stehen alle Spuren still - und es meldet sich nichts, weil sein Zweck ist,
# sich zu melden, wenn er laeuft. Zwei Fragen: laeuft der Prozess, und wie alt
# ist der letzte Zyklus? Die Bus-Zeitstempel sind UTC ("zeit"), die Grenze
# richtet sich nach dem Takt (15 min, hier 45 min Luft).
try {
  Notiz "`n--- 12) Handel: Dauerlauf ---"
  $dl = @(Get-CimInstance Win32_Process -EA SilentlyContinue |
          Where-Object { $_.CommandLine -match 'dauerlauf\.py' })
  $journal = Join-Path $agenten ("Bus\journal\{0}.jsonl" -f (Get-Date).ToString('yyyy-MM-dd'))
  $letzte = $null
  if (Test-Path $journal) {
    $zeilen = @(Get-Content -LiteralPath $journal -Tail 500 -EA SilentlyContinue |
                Where-Object { $_ -match '"wer":\s*"handel/' })
    foreach ($z in $zeilen) {
      if ($z -match '"zeit":\s*"([^"]+)"') {
        $t = [datetime]::Parse($matches[1]).ToUniversalTime()
        if (-not $letzte -or $t -gt $letzte) { $letzte = $t }
      }
    }
  }
  $alterMin = if ($letzte) { [int](([datetime]::UtcNow) - $letzte).TotalMinutes } else { $null }
  # Alter des laufenden Prozesses: nach einem Neustart ist der erste Zyklus
  # noch nicht im Journal, und "kein Ereignis heute" waere dann ein Fehlalarm.
  $seitMin = $null
  if ($dl.Count -gt 0) {
    $frueh = ($dl | Sort-Object CreationDate | Select-Object -First 1).CreationDate
    if ($frueh) { $seitMin = [int]((Get-Date) - $frueh).TotalMinutes }
  }
  if ($dl.Count -eq 0) {
    $zusatz = if ($null -ne $alterMin) { " seit $alterMin min kein Zyklus" } else { "" }
    Entscheiden "Handels-Dauerlauf laeuft nicht (kein dauerlauf.py-Prozess)$zusatz - starten: Agenten\Routinen\handel-dauerlauf.ps1"
  } elseif ($null -ne $seitMin -and $seitMin -le 15) {
    Info "Handels-Dauerlauf laeuft seit $seitMin min - der erste Zyklus steht noch aus."
  } elseif ($null -eq $alterMin) {
    Entscheiden "Dauerlauf laeuft, aber im Bus-Journal von heute steht kein Handels-Ereignis - laeuft er, aber ohne Bus-Anbindung?"
  } elseif ($alterMin -gt 45) {
    Entscheiden "Handels-Dauerlauf laeuft, letzter Zyklus aber vor $alterMin min (Takt 15 min, Grenze 45) - haengt ein Lauf, oder laeuft ein zweiter daneben?"
  } else {
    Info "Handels-Dauerlauf laeuft, letzter Zyklus vor $alterMin min ($($dl.Count) Prozesse der venv-Kette)."
  }
} catch { Notiz "  ! Dauerlauf-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 13) Arbeitszweig: eine Linie (master), und ist sie veroeffentlicht?
# ---------------------------------------------------------------------------
# CLAUDE.md, Abschnitt "Zweige" (08.10.2026): Agenten arbeiten auf eigenen Zweigen in
# eigenen Arbeitsbaeumen (.worktrees/); der HAUPTBAUM bleibt auf master. Zweimal
# ist daneben einer entstanden (telegram-bus 16.09., berichtsschicht
# 17./18.09.) - beide Male lagen Commits herum, die master nicht hatte und die
# GitHub nicht kannte. Nicht der Zweig ist der Fehler, sondern dass es
# niemandem auffiel: Block 1 ueberspringt den Zweig, Block 8 die .bak-Dateien.
try {
  Notiz "`n--- 13) Git: Arbeitszweig und Veroeffentlichung ---"
  $zweig = (git -C $wurzel rev-parse --abbrev-ref HEAD 2>$null)
  if (-not $zweig) {
    Entscheiden "Arbeitszweig nicht lesbar (git rev-parse lieferte nichts) - ist $wurzel noch ein Repo?"
  } elseif ($zweig -ne 'master') {
    Entscheiden "Arbeitszweig ist '$zweig', nicht master - zusammenfuehren: 'git branch -f master $zweig' (wenn master ein Vorfahre ist), sonst 'git merge $zweig'."
  } else {
    Info "Arbeitszweig ist master."
  }
  # origin/master muss lokal bekannt sein, sonst ist "ist alles veroeffentlicht?"
  # nicht messbar - und ein stiller Fehlalarm waere die Folge.
  $fern = git -C $wurzel rev-parse --verify --quiet refs/remotes/origin/master 2>$null
  if (-not $fern) {
    Entscheiden "origin/master ist lokal nicht bekannt - 'git fetch origin' laufen lassen, sonst ist die Frage 'alles veroeffentlicht?' nicht messbar."
  } else {
    $vor = @(git -C $wurzel rev-list origin/master..HEAD 2>$null)
    if ($vor.Count -gt 0) {
      $aeltester = (git -C $wurzel rev-list --max-count=1 --reverse origin/master..HEAD 2>$null)
      Entscheiden "$($vor.Count) Commit(s) sind nicht auf origin/master (aeltester $aeltester) - 'git push origin $zweig' faellig."
    } else {
      Info "Keine unveroeffentlichten Commits gegenueber origin/master."
    }
    if ($zweig -and $zweig -ne 'master') {
      $hinter = @(git -C $wurzel rev-list HEAD..master 2>$null)
      if ($hinter.Count -gt 0) {
        Entscheiden "master hat $($hinter.Count) Commit(s), die im Arbeitszweig '$zweig' fehlen - der Baum zeigt nicht die integrierte Linie."
      }
    }
  }
} catch { Notiz "  ! Zweig-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 14) Docker: laeuft der Nautilus-Quoten-Container, und liefert er Quotes?
# ---------------------------------------------------------------------------
# Der OKX-Demo-Quoten-Node laeuft seit 19.09.2026 als Container
# (nautilus-demo, --restart unless-stopped). Er ist der sichtbare
# Quotenstrom; die Dauerlauf-Spur zyklisiert unabhaengig davon. Zwei Fragen:
# laeuft der Container, und sind die Logs frisch (Quote-Zeilen je Tick)?
# docker ps/logs sind langsam (~1-2 s) - nur einmal aufrufen.
#
# JEDER Docker-Aufruf laeuft mit Zeitgrenze: ist die Engine tot, wartet der
# Client unbegrenzt auf die Pipe. Am 19.-22.09.2026 war Docker Desktop aus -
# Block 14 war jedes Mal die letzte Zeile im Protokoll, der Lauf wurde von
# aussen gekillt (267014) und der Bericht danach gar nicht mehr geschrieben.
# Ohne Antwort in der Frist kommt $null zurueck, nie ein Haenger.
function DockerMitFrist {
  param([int]$Sekunden = 20, [string[]]$Argumente)
  try {
    $si = New-Object System.Diagnostics.ProcessStartInfo
    $si.FileName = 'docker'
    $si.Arguments = (($Argumente | ForEach-Object {
      if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
    }) -join ' ')
    $si.RedirectStandardOutput = $true
    $si.RedirectStandardError  = $true
    $si.UseShellExecute = $false
    $si.CreateNoWindow  = $true
    $p = [System.Diagnostics.Process]::Start($si)
    $tOut = $p.StandardOutput.ReadToEndAsync()
    $tErr = $p.StandardError.ReadToEndAsync()
    if (-not $p.WaitForExit($Sekunden * 1000)) {
      try { $p.Kill() } catch { }
      return $null
    }
    $text = $tOut.GetAwaiter().GetResult()
    @($text -split "`r?`n" | Where-Object { $_ -ne '' })
  } catch { return $null }
}
try {
  Notiz "`n--- 14) Docker: Nautilus-Quoten-Container ---"
  $cZeilen = DockerMitFrist 20 @('ps', '--filter', 'name=nautilus-demo', '--format', '{{.Names}}|{{.Status}}')
  if ($null -eq $cZeilen) {
    Entscheiden "Docker-Engine antwortet nicht (Frist 20 s) - Container nautilus-demo ungeprueft. Ist die Engine wieder da: 'docker start nautilus-demo' und Block 14 erneut laufen lassen."
  } elseif (-not $cZeilen) {
    Entscheiden "Docker-Container nautilus-demo laeuft nicht (docker ps leer) - starten: 'docker start nautilus-demo' oder 'docker run -d --name nautilus-demo --restart unless-stopped -e OKX_API_KEY=dummy-node-key -e OKX_API_SECRET=dummy-node-secret -e OKX_API_PASSPHRASE=dummy-node-pass nautilus-demo-node:1.231.0'"
  } else {
    $status = ((@($cZeilen)[0]) -split '\|')[1]
    if ($status -match 'Restarting|Exited|Dead') {
      Entscheiden "Docker-Container nautilus-demo ist '$status' - Logs pruefen: 'docker logs --tail 20 nautilus-demo', dann 'docker start nautilus-demo'."
    } else {
      # Quote-Frische: letzte Log-Zeile mit Quote-Zeitstempel (UTC).
      # Zwei Fallen: (1) docker logs liefert ANSI-Escape-Sequenzen
      # (\x1b[...m) - vor dem Match entfernen, sonst beginnt die Zeile nicht
      # mit der Ziffer; (2) [datetimeoffset]::Parse(...AssumeUniversal) statt
      # [datetime]::ParseExact, das speichert als Local und verfaelscht die
      # Differenz um die Zeitzone.
      $logroh = DockerMitFrist 25 @('logs', '--tail', '200', 'nautilus-demo')
      $logzeilen = @()
      if ($logroh) {
        $logzeilen = @($logroh | ForEach-Object { $_ -replace "\x1b\[[0-9;]*m", "" })
      }
      $letzteQuote = $logzeilen | Where-Object { $_ -match 'Quote BTC-USDT-SWAP' } |
        Select-Object -Last 1
      if ($letzteQuote -and $letzteQuote -match '^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})') {
        $t = [datetimeoffset]::Parse($matches[1] + 'Z',
          [System.Globalization.CultureInfo]::InvariantCulture,
          [System.Globalization.DateTimeStyles]::AssumeUniversal)
        $alterMin = [int](([datetimeoffset]::UtcNow) - $t).TotalMinutes
        if ($alterMin -gt 5) {
          Entscheiden "Docker-Container nautilus-demo laeuft ($status), letzte Quote aber vor $alterMin min - haengt der Feed? 'docker logs --tail 20 nautilus-demo'."
        } else {
          Info "Docker-Container nautilus-demo laeuft ($status), letzte Quote vor $alterMin min."
        }
      } else {
        Info "Docker-Container nautilus-demo laeuft ($status), aber keine Quote-Zeile in den letzten 200 Logzeilen - Feed pruefen: 'docker logs --tail 20 nautilus-demo'."
      }
    }
  }
} catch { Notiz "  ! Docker-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 15) Fremd-Grenze: die eine Quelle (Agenten/FREMD-Liste.json) auf sich selbst
# pruefen. fremd.py --pruefen meldet Befunde zur Liste selbst (fehlender Ordner,
# leere Felder, Ueberschneidung mit eigenen Wurzeln, Dopplung) - leer bzw.
# "gesund:" heisst in Ordnung. Angeschlossen nach Entwurf 30.09., T-242(b).
try {
  Notiz "`n--- 15) Fremd-Grenze ---"
  $fremdSkript = Join-Path $agenten 'Werkzeuge\fremd.py'
  $fremdPy = Join-Path $agenten 'Handel\scanner\.venv\Scripts\python.exe'
  if (-not (Test-Path $fremdPy)) { $fremdPy = (Get-Command python -EA SilentlyContinue).Source }
  if (-not (Test-Path $fremdSkript)) {
    Entscheiden "Fremd-Grenze nicht geprueft: Agenten\Werkzeuge\fremd.py fehlt."
  } elseif (-not $fremdPy -or -not (Test-Path $fremdPy)) {
    Info "Fremd-Grenze nicht geprueft - kein Python gefunden."
  } else {
    $fAus = @(& $fremdPy $fremdSkript --pruefen 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -ne '' })
    $gesund = @($fAus | Where-Object { $_ -match '^gesund: (\d+) Eintraege' })
    if ($gesund.Count -gt 0) {
      $n = ($gesund[0] -replace '^gesund: ', '' -replace ' Eintraege.*$', '')
      Info "Fremd-Grenze gesund: $n Eintraege (Liste = eine Quelle fuer Zentrale, Bestand und fundus-suche)."
    } else {
      foreach ($fz in $fAus) { Entscheiden "Fremd-Grenze: $fz" }
    }
  }
} catch { Notiz "  ! Fremd-Grenze-Pruefung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 16) Konfig-Doktor: rein lesend, hier nur die Zaehlzeile (-Kurz). Den vollen
# Bericht schreibt konfig-doktor.ps1 ohne -Kurz nach Werkstatt\.
# Exit 0 = nichts KRITISCH, 1 = mind. ein KRITISCH, 2 = Doktor selbst defekt.
try {
  Notiz "`n--- 16) Konfig-Doktor ---"
  $doktor = Join-Path $PSScriptRoot 'konfig-doktor.ps1'
  if (-not (Test-Path -LiteralPath $doktor)) {
    Entscheiden "Konfig-Doktor nicht geprueft: Agenten\Routinen\konfig-doktor.ps1 fehlt."
  } else {
    # Continue: unter 'Stop' wirft schon eine stderr-Zeile des Kindes (NativeCommandError)
    $altEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $dAus = (& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $doktor -Kurz 2>&1 | Out-String).Trim(); $dCode = $LASTEXITCODE }
    finally { $ErrorActionPreference = $altEAP }
    if ($dCode -eq 2) { Entscheiden "Konfig-Doktor selbst defekt: $dAus" }
    elseif ($dCode -eq 1) { Entscheiden "$dAus - Bericht: konfig-doktor.ps1 ohne -Kurz laufen lassen." }
    else { Info $dAus }
  }
} catch { Notiz "  ! Konfig-Doktor abgebrochen: $_" }

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

# Alte Protokolle erst nach 30 Tagen weg. Bei -NurPruefen passiert hier
# nichts: der Schalter verspricht oben "keine Aufraeum-Schritte", und ein
# Aufraeumschritt, der trotzdem loescht, ist genau die Falle, die man einem
# Prueflauf nicht ansieht.
if (-not $NurPruefen) {
  Get-ChildItem $logs -Filter 'systempruefung-*.*' -EA SilentlyContinue |
    Where-Object { $_.Name -ne 'systempruefung-letzter-lauf.md' -and $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item -Force -EA SilentlyContinue
}

Notiz "`nENDE ok - $($getan.Count) erledigt, $($entscheiden.Count) zu entscheiden, $($neuZeilen.Count) davon neu seit gestern (Dauer $sek s)"
Melde-Ende -Marke $marke -Code 0                                        # neu
exit 0

} catch {                                                                # neu
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  throw                                                                 # neu
}                                                                        # neu
