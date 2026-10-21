<#
  fundus-suche.ps1 - Zugang zum Skill-Fundus (Documents/GitHub) UND zu den
  Skill-Klonen unter Werkstatt, ohne Token-Last.

  Zwei Quellen:
    Fundus:        %USERPROFILE%\Documents\GitHub  (alle Skill-Klone dort)
    Werkstatt:     Werkstatt (34 Repos mit SKILL.md, ~1022 Dateien)
  Wuerde man alle in die Hermes-Bibliothek legen, kostet das ~14.700 Tokens
  bei JEDER Anfrage. Dieses Skript haelt sie draussen und sucht nur auf
  Anforderung - in beiden Baeumen zugleich.

  Byte-identische Kopien (dieselbe Datei in mehreren Plugin-Pfaden oder in
  beiden Baeumen) werden je Baum auf einen Pfad zusammengefasst - sonst
  liefert jede Suche Dreifachtreffer. Skills, die in beiden Baeumen liegen,
  tragen in der Werkstatt-Ansicht den Vermerk "auch im Fundus".

  Aufruf:
    .\fundus-suche.ps1 -Begriff "excel"      # Treffer listen (beide Baeume)
    .\fundus-suche.ps1 -Begriff "excel" -Max 20
    .\fundus-suche.ps1 -MitKopien            # auch die doppelten Pfade zeigen
    .\fundus-suche.ps1 -Index                # beide Index-Dateien neu bauen
    .\fundus-suche.ps1                       # Uebersicht je Baum und Repo

  Hinweis: Schalter und Variablen muessen unterschiedlich heissen. PowerShell
  ist case-insensitiv - ein Schalter -Alle und eine Variable $alle sind dieselbe
  Variable, die Zuweisung ueberschreibt dann den Schalter.
#>
param(
  [string]$Begriff,
  [switch]$Index,
  [switch]$MitKopien,
  [int]$Max = 12
)
$ErrorActionPreference = 'Continue'

$stamm   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
# Fundus liegt seit 18.09.2026 unter Documents/GitHub (ausserhalb BrainFiles).
$fundus  = Join-Path $env:USERPROFILE 'Documents\GitHub'
$werkstatt = Join-Path $stamm 'Werkstatt'
$ziel    = Join-Path $stamm 'MaxHirn\Wissen\Fundus-Index.md'
$zielWk  = Join-Path $stamm 'MaxHirn\Wissen\Fundus-Index-Werkstatt.md'

# --- Fremd-Grenze (T-242(a), Entwurf 30.09.): die Liste ist die eine Quelle ---
# Der Fundus meldet je Baum, was Agenten\FREMD-Liste.json ueber ihn sagt, statt
# es hier zu wissen. Fehlt die Datei oder ihr Eintrag, sagt die Zeile genau das -
# die Suche selbst ist reine Lesung und laeuft weiter. PS-5.1-Fallen beachtet:
# Get-Content mit -Encoding UTF8, Zaehlen immer ueber @().
$fremdEintr = @()
$fremdJson = Join-Path $stamm 'Agenten\FREMD-Liste.json'
if (Test-Path $fremdJson) {
  try {
    $fremdObj = Get-Content $fremdJson -Raw -Encoding UTF8 | ConvertFrom-Json
    $fremdEintr = @($fremdObj.eintraege)
  } catch { $fremdEintr = @() }
}
function Get-FremdZeile($relPfad, $label) {
  if ($fremdEintr.Count -eq 0) {
    return ('Fremd-Grenze: {0} -> Liste nicht gelesen (Agenten\FREMD-Liste.json fehlt oder unlesbar)' -f $label)
  }
  $e = @($fremdEintr | Where-Object { $_.pfad -eq $relPfad })
  if ($e.Count -eq 0) {
    return ('Fremd-Grenze: {0} -> kein Eintrag in der Liste' -f $label)
  }
  $t = $e[0]
  $s = ('Fremd-Grenze: {0} -> fremd ({1}): {2}' -f $label, $t.art, $t.regel)
  $unter = @($fremdEintr | Where-Object { $_.pfad.StartsWith($relPfad + '/') -and $_.pfad -ne $relPfad }).Count
  if ($unter -gt 0) { $s += (' - dazu {0} Einzel-Eintraege unter diesem Baum' -f $unter) }
  return $s
}

function Get-SkillKopf($datei) {
  $t = Get-Content $datei.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
  if ($null -eq $t) { return @{ Name = $datei.Directory.Name; Desc = '' } }
  $kopf = if ($t.Length -gt 1500) { $t.Substring(0, 1500) } else { $t }
  $n = [regex]::Match($kopf, '(?m)^name:\s*"?([^"\r\n]+)')
  $d = [regex]::Match($kopf, '(?m)^description:\s*"?([^"\r\n]+)')
  $name = if ($n.Success) { $n.Groups[1].Value.Trim() } else { $datei.Directory.Name }
  $desc = if ($d.Success) { $d.Groups[1].Value.Trim().Trim('"') } else { '' }
  if ($desc -in @('', '|', '>', '|-', '>-')) {
    $b = [regex]::Match($kopf, '(?m)^description:\s*[|>]-?\s*\r?\n((?:[ \t]+\S[^\r\n]*\r?\n?)+)')
    if ($b.Success) { $desc = ($b.Groups[1].Value -replace '\s+', ' ').Trim() }
  }
  if ($desc.Length -gt 200) { $desc = $desc.Substring(0, 200) + '...' }
  return @{ Name = $name; Desc = $desc }
}

function DateiHash([string]$pfad) {
  # Get-FileHash FEHLT in dieser PowerShell 5.1 (CommandNotFoundException,
  # gemessen am 16.09.2026). Das war nicht nur ein Fehler, sondern eine falsche
  # Aussage: der Hash blieb leer, ALLE Skills landeten in EINER Gruppe und die
  # Suche meldete "0 Treffer von 0 eindeutigen Skills" - bei 182 Skills. Deshalb
  # MD5 ueber System.Security.Cryptography, dieselbe Reparatur wie in
  # systempruefung.ps1 Block 10. $null heisst "nicht lesbar"; der Aufrufer
  # nimmt dann den PFAD als Schluessel, damit kein Skill verschwindet.
  try {
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $strom = [System.IO.File]::OpenRead($pfad)
    try {
      return ([System.BitConverter]::ToString($md5.ComputeHash($strom)) -replace '-', '').ToLowerInvariant()
    } finally { $strom.Dispose(); $md5.Dispose() }
  } catch { return $null }
}

# ---------------------------------------------------------------- Sammeln
function Sammle([string]$quelle, [string]$wurzel) {
  if (-not (Test-Path $wurzel)) { return @() }
  Get-ChildItem $wurzel -Recurse -File -Filter 'SKILL.md' -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\node_modules\\' } | ForEach-Object {
    $k = Get-SkillKopf $_
    # Pfad RELATIV zur eigenen Wurzel (nicht zu $stamm): der Fundus liegt seit
    # 18.09.2026 ausserhalb BrainFiles - ein Substring auf $stamm schnitt
    # mitten in "C:\...\Documents\GitHub\" und verstaemmte jeden Pfad.
    $rel = $_.FullName.Substring($wurzel.Length + 1)
    $pfad = $rel
    [pscustomobject]@{
      Quelle = $quelle
      Repo   = ($rel -split '\\')[0]
      Name   = $k.Name
      Desc   = $k.Desc
      Pfad   = $pfad
      Hash   = DateiHash $_.FullName
    }
  }
}

# Gruppiert wird je Baum nach Hash, bei fehlendem Hash nach Pfad: ein nicht
# lesbarer Skill darf nicht mit allen anderen in einen Topf fallen.
function Eindeutig([object[]]$menge) {
  $menge | Group-Object { if ($_.Hash) { $_.Hash } else { $_.Pfad } } | ForEach-Object {
    $_.Group | Sort-Object { $_.Pfad.Length } | Select-Object -First 1
  } | Sort-Object Quelle, Repo, Name
}

$fundusSkills    = @(Sammle 'fundus' $fundus)
$werkstattSkills = @(Sammle 'werkstatt' $werkstatt)

$fundusHashes = @{}
foreach ($s in $fundusSkills) { if ($s.Hash) { $fundusHashes[$s.Hash] = $true } }

$eindeutigFundus    = @(Eindeutig $fundusSkills)
$eindeutigWerkstatt = @($werkstattSkills | Group-Object { if ($_.Hash) { $_.Hash } else { $_.Pfad } } | ForEach-Object {
  $g = $_.Group | Sort-Object { $_.Pfad.Length } | Select-Object -First 1
  $g | Add-Member -NotePropertyName Beide -NotePropertyValue ($g.Hash -and $fundusHashes.ContainsKey($g.Hash)) -PassThru
} | Sort-Object Repo, Name)

$doppeltF = $fundusSkills.Count - $eindeutigFundus.Count
$doppeltW = $werkstattSkills.Count - $eindeutigWerkstatt.Count

function Schreib-Index([string]$datei, [string]$titel, [object[]]$eintraege, [int]$dateien, [int]$kopien) {
  $zeilen = New-Object System.Collections.Generic.List[string]
  # Titelzeile VOR dem Array bauen: in "@(\"# \" + $titel, ...)" gewinnt das
  # Komma gegen das Plus (PS-Vorrang) und der ganze Kopf wird EIN String
  # (gemessen 16.09.2026: Kopf stand in einer Zeile).
  $titelzeile = "# " + $titel
  @($titelzeile,
    '',
    'Erzeugt von `Agenten/Werkzeuge/fundus-suche.ps1 -Index`. Nicht von Hand pflegen.',
    '',
    ('Geklonte Fremd-Repos: **{0} eindeutige Skills** in {1} Repos ({2} Dateien, {3} byte-identische Kopien zusammengefasst).' -f $eintraege.Count, ($eintraege.Repo | Sort-Object -Unique).Count, $dateien, $kopien),
    '',
    'Nicht in der Hermes-Bibliothek geladen; Zugriff ueber `Agenten/Werkzeuge/fundus-suche.ps1 -Begriff "<wort>"`.',
    '') | ForEach-Object { $zeilen.Add($_) }
  foreach ($repo in ($eintraege.Repo | Sort-Object -Unique)) {
    # @() erzwingt ein Array: .Count auf einem Einzelobjekt aus der Pipeline
    # ist in PowerShell 5.1 LEER (gemessen 16.09.2026) - ohne @() wuerde
    # jedes 1-Skill-Repo als "(0)" oder "()" ausgewiesen.
    $gruppe = @($eintraege | Where-Object { $_.Repo -eq $repo } | Sort-Object Name)
    $zeilen.Add("## $repo ($($gruppe.Count))")
    $zeilen.Add('')
    foreach ($s in $gruppe) {
      $d = if ($s.Desc) { ' - ' + $s.Desc } else { '' }
      $merk = if ($s.Beide) { ' *(auch im Fundus)*' } else { '' }
      $zeilen.Add('- **' + $s.Name + '**' + $merk + $d)
      $zeilen.Add('  `' + $s.Pfad + '`')
    }
    $zeilen.Add('')
  }
  $text = ($zeilen -join "`n")
  [System.IO.File]::WriteAllText($datei, $text, (New-Object System.Text.UTF8Encoding($false)))
  Write-Output ('Index geschrieben: ' + $datei)
  Write-Output ('  Repos: ' + ($eintraege.Repo | Sort-Object -Unique).Count + ' | eindeutige Skills: ' + $eintraege.Count + ' | Dateien: ' + $dateien + ' | Zeichen: ' + $text.Length)
}

if ($Index) {
  # Fundus-Index.md bleibt unveraendert im Format (rueckwaertskompatibel).
  Schreib-Index $ziel 'Fundus-Index' $eindeutigFundus $fundusSkills.Count $doppeltF
  # Werkstatt-Index ist die zweite Uebersicht, mit Ueberlappungs-Vermerk.
  Schreib-Index $zielWk 'Fundus-Index - Werkstatt' $eindeutigWerkstatt $werkstattSkills.Count $doppeltW
  $ueberlapp = @($eindeutigWerkstatt | Where-Object { $_.Beide }).Count
  Write-Output ('Ueberlappung: ' + $ueberlapp + ' Werkstatt-Skills liegen byte-identisch auch im Fundus')
  Write-Output (Get-FremdZeile 'Werkstatt' 'Werkstatt')
  return
}

if (-not $Begriff) {
  Write-Output ('Fundus:        ' + $eindeutigFundus.Count + ' eindeutige Skills in ' + ($eindeutigFundus.Repo | Sort-Object -Unique).Count + ' Repos (' + $fundusSkills.Count + ' Dateien, ' + $doppeltF + ' identische Kopien)')
  Write-Output ('Werkstatt: ' + $eindeutigWerkstatt.Count + ' eindeutige Skills in ' + ($eindeutigWerkstatt.Repo | Sort-Object -Unique).Count + ' Repos (' + $werkstattSkills.Count + ' Dateien, ' + $doppeltW + ' identische Kopien, ' + @($eindeutigWerkstatt | Where-Object { $_.Beide }).Count + ' auch im Fundus)')
  Write-Output (Get-FremdZeile 'Werkstatt' 'Werkstatt')
  Write-Output ('Fremd-Grenze: Fundus (Documents\GitHub) -> ausserhalb von BrainFiles, von der Liste nicht erfasst; Inhalt: geklonte Fremd-Repos')
  Write-Output ''
  Write-Output 'Fundus:'
  $eindeutigFundus | Group-Object Repo | Sort-Object Count -Descending | ForEach-Object {
    Write-Output ('  {0,-30} {1,4} Skills' -f $_.Name, $_.Count)
  }
  Write-Output ''
  Write-Output 'Werkstatt:'
  $eindeutigWerkstatt | Group-Object Repo | Sort-Object Count -Descending | ForEach-Object {
    Write-Output ('  {0,-30} {1,4} Skills   ({2} auch im Fundus)' -f $_.Name, $_.Count, @($_.Group | Where-Object { $_.Beide }).Count)
  }
  Write-Output ''
  Write-Output 'Suche:  .\fundus-suche.ps1 -Begriff "<wort>"   (durchsucht beide Baeume)'
  Write-Output 'Index:  .\fundus-suche.ps1 -Index   ->  MaxHirn\Wissen\Fundus-Index.md + Fundus-Index-Werkstatt.md'
  return
}

$liste = @($eindeutigFundus) + @($eindeutigWerkstatt)
$treffer = @($liste | Where-Object {
  $_.Name -like "*$Begriff*" -or $_.Desc -like "*$Begriff*" -or $_.Pfad -like "*$Begriff*" -or $_.Repo -like "*$Begriff*"
} | Sort-Object Quelle, Repo, Name)

Write-Output ("{0} Treffer fuer '{1}' (Fundus {2} + Werkstatt {3} eindeutige Skills)" -f $treffer.Count, $Begriff, $eindeutigFundus.Count, $eindeutigWerkstatt.Count)
if ($treffer.Count -eq 0) {
  Write-Output 'Kein Treffer. Andere Schreibweise versuchen oder die Index-Dateien unter MaxHirn\Wissen\ lesen.'
  return
}
$treffer | Select-Object -First $Max | ForEach-Object {
  $q = if ($_.Quelle -eq 'fundus') { 'Fundus  ' } else { 'Werkstatt' }
  $m = if ($_.Beide) { '  [auch im Fundus]' } else { '' }
  Write-Output ("- {0} > {1} > {2}{3}" -f $q, $_.Repo, $_.Name, $m)
  Write-Output ("  Pfad: {0}" -f $_.Pfad)
  if ($_.Desc) { Write-Output ("  Was:  {0}" -f $_.Desc) }
}
if ($treffer.Count -gt $Max) { Write-Output ("... und {0} weitere (mit -Max erhoehen)" -f ($treffer.Count - $Max)) }
