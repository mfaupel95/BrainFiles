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
$logs    = Join-Path $PSScriptRoot 'logs'
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
      if ($NurPruefen) {
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
  $funde = 0
  foreach ($b in $bereiche) {
    $dateien = Gehe $b.Root
    $kandidaten = @($dateien | Where-Object { ([System.IO.Path]::GetFileName($_)) -imatch $musterName })
    foreach ($f in $kandidaten) {
      $funde++
      $rel = $f.Substring($b.Root.Length).TrimStart('\')
      $name = [System.IO.Path]::GetFileName($f)
      # Referenzsuche: taucht der Dateiname irgendwo im eigenen Code auf?
      $refs = @()
      foreach ($b2 in $bereiche) {
        $refs += @(Get-ChildItem -LiteralPath $b2.Root -Recurse -File -EA SilentlyContinue |
          Where-Object { $_.FullName -notmatch '\\(node_modules|\.git|\.venv|__pycache__|\.obsidian|Archiv|_Backups)\\' -and $_.Length -lt 2MB -and $_.FullName -ne $f } |
          Select-String -Pattern ([regex]::Escape($name)) -EA SilentlyContinue)
      }
      $ziel = Join-Path $sshDir $name
      if ($refs.Count -gt 0) {
        Entscheiden "$($b.Name): Schluesseldatei $rel ist an $($refs.Count) Stelle(n) referenziert - vor dem Verschieben pruefen, welche."
      } else {
        Entscheiden "$($b.Name): lose Schluesseldatei $rel gefunden, keine Referenzen gefunden. Verschieben: Move-Item '$f' '$ziel'"
      }
    }
  }
  if ($funde -eq 0) { Info "Keine losen Schluesseldateien ausserhalb ~/.ssh gefunden." }
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

Get-ChildItem $logs -Filter 'datensortierung-*.*' -EA SilentlyContinue |
  Where-Object { $_.Name -ne 'datensortierung-letzter-lauf.md' -and $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item -Force -EA SilentlyContinue

Notiz "`nENDE ok - $($getan.Count) erledigt, $($entscheiden.Count) zu entscheiden, $($neuZeilen.Count) davon neu seit gestern (Dauer $sek s)"
Melde-Ende -Marke $marke -Code 0                                        # neu
exit 0

} catch {                                                                # neu
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  throw                                                                 # neu
}                                                                        # neu
