# Taegliche Datensortierung (morgens, nach der Systempruefung). Von der
# Aufgabenplanung aufgerufen.
#
# Zweck: BrainFiles organisch sauber halten, ohne den 44-GB-Archivzweig unter
# MaxHirn\Archiv jemals anzufassen (auf Wunsch, 05.09.2026 dauerhaft tabu).
#
# Zwei Kategorien, zwei Politiken (gleiche Linie wie systempruefung.ps1,
# Abschnitt "Aufraeum-Politik"):
#   1) .bak-Dateien       - eindeutig reproduzierbar -> raeumt sich selbst weg,
#                           landet in <Bereich>\_Backups, Originalpfad bleibt
#                           im Dateinamen erkennbar (\ -> __). Nichts geloescht.
#   2) lose Schluesseldateien (*.pem, *.ppk, id_rsa*, id_ed25519*) ausserhalb
#      von ~/.ssh - Ermessensspielraum (koennte eine bewusst dort abgelegte
#      Testdatei sein) -> wird NUR gemeldet, mit fertigem Verschiebe-Befehl.
#      Referenzsuche in Agenten+MaxHirn (ohne Archiv) davor, damit ein Fund,
#      der irgendwo im Klartext referenziert wird, nicht kommentarlos vorgeschlagen
#      wird.
#
# Ausgaben (gleiches Muster wie systempruefung.ps1):
#   logs\datensortierung-JJJJ-MM-TT.log   - vollstaendiges Protokoll
#   logs\datensortierung-letzter-lauf.md  - strukturierter Bericht, stabiler Name
#     Gliederung: "Seit gestern neu" / "Selbst erledigt" / "Zu entscheiden" /
#     "Zur Kenntnis". Gedacht fuer denselben SessionStart-Hook wie die
#     Systempruefung (datensortierung-hook.ps1).
#
# -NurPruefen schaltet Schritt 1 (das Verschieben der .bak-Dateien) ab, fuer
# gefahrlose Laeufe von Hand. Schritt 2 verschiebt ohnehin nie automatisch.

param([switch]$NurPruefen)

$ErrorActionPreference = 'Stop'
$wurzel  = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$agenten = Join-Path $wurzel 'Agenten'
$maxhirn = Join-Path $wurzel 'MaxHirn'
$sshDir  = Join-Path $env:USERPROFILE '.ssh'
$logs     = Join-Path $PSScriptRoot 'logs'
$waechter = Join-Path $PSScriptRoot 'safe-file-ops.ps1'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $agenten 'Bus\Ereignis.ps1')                                # neu
$marke = Melde-Start -Wer 'routine/datensortierung' `
           -Log 'Agenten/Routinen/logs/datensortierung-letzter-lauf.md' # neu
try {                                                                    # neu

$start    = Get-Date
$heute    = $start.ToString('yyyy-MM-dd')
$roh      = Join-Path $logs "datensortierung-$heute.log"
$bericht  = Join-Path $logs 'datensortierung-letzter-lauf.md'
$md_heute = Join-Path $logs "datensortierung-$heute.md"

$getan       = [System.Collections.Generic.List[string]]::new()
$entscheiden = [System.Collections.Generic.List[string]]::new()
$info        = [System.Collections.Generic.List[string]]::new()
$rohzeilen   = [System.Collections.Generic.List[string]]::new()

function Notiz($text)    { $rohzeilen.Add([string]$text); $rohzeilen | Set-Content $roh -Encoding UTF8; Write-Output $text }
function Getan($t)       { $getan.Add($t);       Notiz "  [erledigt]  $t" }
function Entscheiden($t) { $entscheiden.Add($t); Notiz "  [Entscheid] $t" }
function Info($t)        { $info.Add($t);        Notiz "  [Info]      $t" }

# Verzeichnisbaum ohne Archiv, ohne bereits konsolidierte _Backups, ohne die
# dicken Fremd-Baeume - gleiche Liste wie systempruefung.ps1, ergaenzt um
# Archiv und _Backups.
$ueberspringen = @('node_modules', '.venv', '.pnpm', '.git', '.hermes-runtime', '__pycache__', 'hermes-agent', '.obsidian', 'Archiv', '_Backups')
function Gehe([string]$root) {
  $files = [System.Collections.Generic.List[string]]::new()
  $stack = [System.Collections.Generic.Stack[string]]::new()
  $stack.Push($root)
  while ($stack.Count) {
    $d = $stack.Pop()
    try { $eintraege = [System.IO.Directory]::EnumerateFileSystemEntries($d) } catch { continue }
    foreach ($e in $eintraege) {
      $name = [System.IO.Path]::GetFileName($e)
      if ([System.IO.Directory]::Exists($e)) {
        if ($name -in $ueberspringen -or $name -like 'ant.dir.*') { continue }
        $stack.Push($e)
      } else {
        $files.Add($e)
      }
    }
  }
  $files
}

Notiz "=== Datensortierung $($start.ToString('yyyy-MM-dd HH:mm:ss')) ==="
if ($NurPruefen) { Notiz "Modus: nur pruefen (kein Verschieben von .bak-Dateien)" }

$bereiche = @(
  @{ Name = 'Agenten'; Root = $agenten },
  @{ Name = 'MaxHirn'; Root = $maxhirn }
)

# --- Vorschaltung: zwei getrennte Zusicherungen ----------------------------
# 1) Das Archiv selbst (O:\Archiv, Stufe 0) darf nie in eine Massenoperation
#    geraten. Der Waechter bestaetigt das vor jedem Lauf.
# 2) MaxHirn\Archiv ist laut Schutzregeln Stufe 2 - dieser Zweig wird hier
#    allein durch die Ausschlussliste ferngehalten (Wunsch 05.09.2026). Faellt
#    'Archiv' aus der Liste, laeuft das Skript durch den ganzen Zweig, ohne
#    dass eine Stufe es aufhaelt. Deshalb wird die Liste geprueft.
$null = & powershell -ExecutionPolicy Bypass -NoProfile -File $waechter `
          -Pfad 'O:\Archiv' -Aktion massenhaft_loeschen -Erwartet ABBRUCH -Stille
if ($LASTEXITCODE -ne 0) {
  Notiz "  ! Vorschaltung: 'O:\Archiv' ist nicht mehr gesperrt (Exitcode $LASTEXITCODE) - Lauf abgebrochen."
  Melde-Ende -Marke $marke -Code 1 -Text 'Waechtertor offen'
  exit 1
}
if ('Archiv' -notin $ueberspringen) {
  Notiz "  ! Vorschaltung: 'Archiv' fehlt in der Ausschlussliste - Lauf abgebrochen."
  Melde-Ende -Marke $marke -Code 1 -Text 'Archiv nicht mehr ausgeschlossen'
  exit 1
}
Notiz 'Vorschaltung ok: O:\Archiv gesperrt, Archiv-Zweig ausgeschlossen.'

# ---------------------------------------------------------------------------
# 1) .bak-Dateien konsolidieren
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 1) .bak-Dateien ---"
  $verschobenGesamt = 0
  foreach ($b in $bereiche) {
    $dateien = Gehe $b.Root
    $baks = @($dateien | Where-Object { ([System.IO.Path]::GetFileName($_)) -imatch '\.bak($|[-_.])' })
    if ($baks.Count -eq 0) { continue }
    $backupsDir = Join-Path $b.Root '_Backups'
    if (-not (Test-Path $backupsDir)) { New-Item -ItemType Directory -Path $backupsDir | Out-Null }
    foreach ($f in $baks) {
      $rel = $f.Substring($b.Root.Length).TrimStart('\')
      $flatName = $rel -replace '[\\/]', '__'
      $destPath = Join-Path $backupsDir $flatName
      if (Test-Path $destPath) {
        $i = 1
        $base = [System.IO.Path]::GetFileNameWithoutExtension($flatName)
        $ext = [System.IO.Path]::GetExtension($flatName)
        do { $destPath = Join-Path $backupsDir "$base`_$i$ext"; $i++ } while (Test-Path $destPath)
      }
      # Waechter: Stufe 0 und Schluesseldateien werden nicht angefasst, auch
      # wenn der Name nach .bak aussieht. Der Fund steht dann im Bericht.
      $null = & powershell -ExecutionPolicy Bypass -NoProfile -File $waechter `
                -Pfad $f -Aktion verschieben -Stille
      if ($LASTEXITCODE -eq 1) {
        Entscheiden "$($b.Name): .bak-Datei $rel liegt in Stufe 0 - nicht verschoben."
      } elseif ($NurPruefen) {
        Entscheiden "$($b.Name): .bak-Datei $rel wuerde nach _Backups verschoben."
      } else {
        try { Move-Item -LiteralPath $f -Destination $destPath; Getan "$($b.Name): $rel -> _Backups\$(Split-Path $destPath -Leaf)"; $verschobenGesamt++ }
        catch { Entscheiden "$($b.Name): $rel konnte nicht nach _Backups verschoben werden: $_" }
      }
    }
  }
  if ($verschobenGesamt -eq 0 -and -not $NurPruefen) { Info "Keine neuen .bak-Dateien gefunden." }
} catch { Notiz "  ! .bak-Konsolidierung abgebrochen: $_" }

# ---------------------------------------------------------------------------
# 2) Lose Schluesseldateien ausserhalb ~/.ssh melden (nicht automatisch verschieben)
# ---------------------------------------------------------------------------
try {
  Notiz "`n--- 2) Lose Schluesseldateien ---"
  $musterName = '\.(pem|ppk)$|^id_rsa|^id_ed25519'
  # Erst sammeln, dann EINMAL suchen. Bis 30.09.2026 lief die Referenzsuche je
  # Kandidat und holte sich die Dateiliste jedes Mal neu per
  # Get-ChildItem -Recurse -File - OHNE die Ueberspringen-Liste, also inklusive
  # node_modules, .venv und hermes-agent. Mit fuenf Zertifikaten stand der Lauf
  # nach 43 Minuten noch in diesem Block; die Aufgabe wurde beim Neustart mit
  # 267014 abgebrochen. Jetzt: eine Namensliste, ein Suchlauf, dieselbe Auskunft.
  $kandidaten = [System.Collections.Generic.List[object]]::new()
  foreach ($b in $bereiche) {
    foreach ($f in (Gehe $b.Root)) {
      if ([System.IO.Path]::GetFileName($f) -imatch $musterName) {
        # Eine CA-Buendelsammlung in einer Umgebung ist kein loser Schluessel:
        # certifi/botocore-cacert.pem in site-packages oder in einer .venv-Kopie
        # wurde bis 30.09.2026 als Fund gemeldet (jedes Mal mit >100
        # Referenzen) und war der Ausloeser der langsamen Suche. Echte
        # Schluesseldateien im Arbeitsbaum bleiben gemeldet.
        # Dieselbe Kategorie taucht noch an drei weiteren, staendigen Orten auf
        # (30.09.2026, 16 tagtaeglich wiederkehrende Treffer): das gebuendelte
        # Git-Toolchain-OpenSSL (inkl. seiner .previous-git-*-Leiche nach einem
        # abgebrochenen Update), der uv-Paketcache (ohnehin fluechtig, siehe
        # sichern-ausser-haus.ps1) und die Test-Fixtures im fremden codex-rs-Repo.
        if ($f -match '\\site-packages\\|\\\.?venv[^\\]*\\|\\tools\\\.?previous-git-[^\\]*\\|\\tools\\git-[^\\]*\\|\\cache\\uv\\archive-v0\\|\\codex-rs\\http-client\\tests\\fixtures\\') { continue }
        $kandidaten.Add([PSCustomObject]@{ Bereich = $b.Name; Root = $b.Root; Pfad = $f })
      }
    }
  }
  if ($kandidaten.Count -eq 0) {
    Info "Keine losen Schluesseldateien ausserhalb ~/.ssh gefunden."
  } else {
    $namen  = @($kandidaten | ForEach-Object { [System.IO.Path]::GetFileName($_.Pfad) } | Sort-Object -Unique)
    $muster = ($namen | ForEach-Object { [regex]::Escape($_) }) -join '|'
    $selbst = @($kandidaten | ForEach-Object { $_.Pfad })
    $treffer = @{}
    foreach ($n in $namen) { $treffer[$n] = 0 }

    # Alle Kandidaten-Dateien in EINEM Suchlauf durchsuchen (in Bloecken, damit
    # die Kommandozeile nicht ueberlaeuft).
    # Nur Dateien, in denen ein Dateiname ueberhaupt vorkommen kann, und nie in
    # Kopien einer Umgebung. Agenten+MaxHirn haben 156.000 Dateien (nach der
    # Ueberspringen-Liste), allein durch .venv.bak-* und site-packages. Ohne
    # diese zwei Filter oeffnet die Suche jede einzelne davon - der Lauf vom
    # 30.09.2026 stand nach ueber 20 Minuten noch in diesem Block.
    $textEndungen = @('.py','.ps1','.psd1','.md','.json','.jsonl','.csv','.txt',
                      '.cfg','.ini','.toml','.yaml','.yml','.env','.sh','.cmd',
                      '.bat','.js','.ts','.tsx','.jsx','.html','.css','.xml',
                      '.conf','.properties')
    $uebersprungen = '\\\.?venv[^\\]*\\|\\site-packages\\|\\dist-info\\|\\node_modules\\'
    $zuSuchen = [System.Collections.Generic.List[string]]::new()
    foreach ($b2 in $bereiche) {
      foreach ($datei in (Gehe $b2.Root)) {
        if ($selbst -contains $datei) { continue }
        if ($datei -match $uebersprungen) { continue }
        if ($textEndungen -notcontains [System.IO.Path]::GetExtension($datei).ToLower()) { continue }
        try { if ([System.IO.FileInfo]::new($datei).Length -ge 2MB) { continue } } catch { continue }
        $zuSuchen.Add($datei)
      }
    }
    $block = 200
    for ($i = 0; $i -lt $zuSuchen.Count; $i += $block) {
      $ende = [Math]::Min($i + $block, $zuSuchen.Count) - 1
      $stueck = $zuSuchen[$i..$ende]
      foreach ($m in (Select-String -LiteralPath $stueck -Pattern $muster -EA SilentlyContinue)) {
        foreach ($n in $namen) {
          if ($m.Line -match [regex]::Escape($n)) { $treffer[$n]++ }
        }
      }
    }

    foreach ($k in $kandidaten) {
      $name = [System.IO.Path]::GetFileName($k.Pfad)
      $rel  = $k.Pfad.Substring($k.Root.Length).TrimStart('\')
      $ziel = Join-Path $sshDir $name
      if ($treffer[$name] -gt 0) {
        Entscheiden "$($k.Bereich): Schluesseldatei $rel ist an $($treffer[$name]) Stelle(n) referenziert - vor dem Verschieben pruefen, welche."
      } else {
        Entscheiden "$($k.Bereich): lose Schluesseldatei $rel gefunden, keine Referenzen gefunden. Verschieben: Move-Item '$($k.Pfad)' '$ziel'"
      }
    }
  }
} catch { Notiz "  ! Schluessel-Suche abgebrochen: $_" }

# ---------------------------------------------------------------------------
# Bericht schreiben (gleiche Form wie systempruefung.ps1)
# ---------------------------------------------------------------------------
$vortag = Get-ChildItem $logs -Filter 'datensortierung-*.md' -EA SilentlyContinue |
  Where-Object { $_.Name -ne 'datensortierung-letzter-lauf.md' -and $_.BaseName -ne "datensortierung-$heute" } |
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
$md.Add("# Datensortierung $heute")
$md.Add("")
$md.Add("_Lauf $($start.ToString('HH:mm')), Dauer $sek s. Vollprotokoll: ``Agenten\Routinen\logs\datensortierung-$heute.log``._")
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

# Loeschen nur auf freien Pfaden: erst fragen, dann raeumen. Ist der
# Protokollordner nicht als Stufe 2 bestaetigt, bleiben die alten Dateien liegen.
$null = & powershell -ExecutionPolicy Bypass -NoProfile -File $waechter `
          -Pfad $logs -Aktion loeschen -Erwartet ERLAUBT -Stille
if ($LASTEXITCODE -eq 0) {
  Get-ChildItem $logs -Filter 'datensortierung-*.*' -EA SilentlyContinue |
    Where-Object { $_.Name -ne 'datensortierung-letzter-lauf.md' -and $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item -Force -EA SilentlyContinue
} else {
  Notiz "  ! Protokollaufraeumen uebersprungen: '$logs' ist nicht als frei bestaetigt (Exitcode $LASTEXITCODE)."
}

Notiz "`nENDE ok - $($getan.Count) erledigt, $($entscheiden.Count) zu entscheiden, $($neuZeilen.Count) davon neu seit gestern (Dauer $sek s)"
Melde-Ende -Marke $marke -Code 0                                        # neu
exit 0

} catch {                                                                # neu
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  throw                                                                 # neu
}                                                                        # neu
