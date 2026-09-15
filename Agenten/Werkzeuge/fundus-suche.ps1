<#
  fundus-suche.ps1 - Zugang zum Skill-Fundus (MaxHirn/skills) ohne Token-Last.

  Der Fundus sind geklonte Fremd-Repos mit ~238 SKILL.md (182 eindeutige Inhale).
  Wuerde man sie in die Hermes-Bibliothek legen, kostet das ~14.700 Tokens bei
  JEDER Anfrage. Dieses Skript haelt sie draussen und sucht nur auf Anforderung.

  Byte-identische Kopien (dieselbe Datei in mehreren Plugin-Pfaden) werden auf
  einen Pfad zusammengefasst - sonst liefert jede Suche Dreifachtreffer.

  Aufruf:
    .\fundus-suche.ps1 -Begriff "excel"      # Treffer listen
    .\fundus-suche.ps1 -Begriff "excel" -Max 20
    .\fundus-suche.ps1 -MitKopien            # auch die doppelten Pfade zeigen
    .\fundus-suche.ps1 -Index                # Wissen/Fundus-Index.md neu bauen
    .\fundus-suche.ps1                       # Uebersicht je Repo

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

$stamm  = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$fundus = Join-Path $stamm 'MaxHirn\skills'
$ziel   = Join-Path $stamm 'MaxHirn\Wissen\Fundus-Index.md'

if (-not (Test-Path $fundus)) { Write-Output "Fundus nicht gefunden: $fundus"; return }

function Get-SkillKopf($datei) {
  $t = Get-Content $datei.FullName -Raw -ErrorAction SilentlyContinue
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

$dateien = Get-ChildItem $fundus -Recurse -File -Filter 'SKILL.md' -ErrorAction SilentlyContinue
$skills = $dateien | ForEach-Object {
  $k = Get-SkillKopf $_
  [pscustomobject]@{
    Repo = ($_.FullName.Substring($fundus.Length + 1) -split '\\')[0]
    Name = $k.Name
    Desc = $k.Desc
    Pfad = $_.FullName.Substring($stamm.Length + 1)
    Hash = DateiHash $_.FullName
  }
}

# Gruppiert wird nach Hash, bei fehlendem Hash nach Pfad: ein nicht lesbarer
# Skill darf nicht mit allen anderen in einen Topf fallen (siehe DateiHash).
$eindeutig = $skills | Group-Object { if ($_.Hash) { $_.Hash } else { $_.Pfad } } | ForEach-Object { $_.Group | Sort-Object { $_.Pfad.Length } | Select-Object -First 1 } | Sort-Object Repo, Name
$doppelt = $skills.Count - $eindeutig.Count
$liste = if ($MitKopien) { $skills } else { $eindeutig }

if ($Index) {
  $zeilen = New-Object System.Collections.Generic.List[string]
  @('# Fundus-Index',
    '',
    'Erzeugt von `Agenten/Werkzeuge/fundus-suche.ps1 -Index`. Nicht von Hand pflegen.',
    '',
    ('Geklonte Fremd-Repos unter `MaxHirn/skills/`: **{0} eindeutige Skills** in {1} Repos ({2} Dateien, {3} byte-identische Kopien zusammengefasst).' -f $eindeutig.Count, ($eindeutig.Repo | Sort-Object -Unique).Count, $skills.Count, $doppelt),
    '',
    'Der Fundus ist **nicht** in der Hermes-Bibliothek geladen; Zugriff ueber das Skript.',
    '') | ForEach-Object { $zeilen.Add($_) }
  foreach ($repo in ($eindeutig.Repo | Sort-Object -Unique)) {
    $gruppe = $eindeutig | Where-Object { $_.Repo -eq $repo } | Sort-Object Name
    $zeilen.Add("## $repo ($($gruppe.Count))")
    $zeilen.Add('')
    foreach ($s in $gruppe) {
      $d = if ($s.Desc) { ' - ' + $s.Desc } else { '' }
      $zeilen.Add('- **' + $s.Name + '**' + $d)
      $zeilen.Add('  `' + $s.Pfad + '`')
    }
    $zeilen.Add('')
  }
  $text = ($zeilen -join "`n")
  [System.IO.File]::WriteAllText($ziel, $text, (New-Object System.Text.UTF8Encoding($false)))
  Write-Output ('Fundus-Index geschrieben: ' + $ziel)
  Write-Output ('Repos: ' + ($eindeutig.Repo | Sort-Object -Unique).Count + ' | eindeutige Skills: ' + $eindeutig.Count + ' | Dateien: ' + $skills.Count + ' | Zeichen: ' + $text.Length)
  return
}

if (-not $Begriff) {
  Write-Output ('Fundus-Vorrat: ' + $eindeutig.Count + ' eindeutige Skills in ' + ($eindeutig.Repo | Sort-Object -Unique).Count + ' Repos (' + $skills.Count + ' Dateien, ' + $doppelt + ' identische Kopien)')
  Write-Output ''
  $eindeutig | Group-Object Repo | Sort-Object Count -Descending | ForEach-Object {
    Write-Output ('  {0,-30} {1,4} Skills' -f $_.Name, $_.Count)
  }
  Write-Output ''
  Write-Output 'Suche:  .\fundus-suche.ps1 -Begriff "<wort>"'
  Write-Output 'Index:  .\fundus-suche.ps1 -Index   ->  MaxHirn\Wissen\Fundus-Index.md'
  return
}

$treffer = $liste | Where-Object {
  $_.Name -like "*$Begriff*" -or $_.Desc -like "*$Begriff*" -or $_.Pfad -like "*$Begriff*" -or $_.Repo -like "*$Begriff*"
} | Sort-Object Repo, Name

Write-Output ("{0} Treffer fuer '{1}' (von {2} eindeutigen Skills)" -f $treffer.Count, $Begriff, $eindeutig.Count)
if ($treffer.Count -eq 0) {
  Write-Output 'Kein Treffer. Andere Schreibweise versuchen oder MaxHirn\Wissen\Fundus-Index.md lesen.'
  return
}
$treffer | Select-Object -First $Max | ForEach-Object {
  Write-Output ("- {0} > {1}" -f $_.Repo, $_.Name)
  Write-Output ("  Pfad: {0}" -f $_.Pfad)
  if ($_.Desc) { Write-Output ("  Was:  {0}" -f $_.Desc) }
}
if ($treffer.Count -gt $Max) { Write-Output ("... und {0} weitere (mit -Max erhoehen)" -f ($treffer.Count - $Max)) }
