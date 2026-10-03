# Einmalig 30.09.2026: C: entlastet (34 -> 69 GB frei). Protokoll und Rueckweg.
# Aufruf: -Rueckgaengig [-Testlauf]  holt huggingface und docker-models wieder auf C:.
# Hermes.alt-20260916 liegt in Werkstatt/Ausgemustert/c-entlasten-20260930 (von Hand zurueckkopieren).
# Deinstalliert: Store-Apps Cinebench, PictureGuide (neu ueber den Store).
param([switch]$Rueckgaengig, [switch]$Testlauf)
$ErrorActionPreference = 'Continue'
$ziele = @(
  @{ C = "$env:USERPROFILE\.cache\huggingface"; O = 'O:\Modelle\_von-c\huggingface' },
  @{ C = "$env:USERPROFILE\.docker\models";     O = 'O:\Modelle\_von-c\docker-models' }
)
if (-not $Rueckgaengig) { $ziele | % { "{0} -> {1} ({2})" -f $_.C, $_.O, (Get-Item $_.C -ea 0).LinkType }; return }
foreach ($z in $ziele) {
  if ((Get-Item $z.C -ea 0).LinkType -ne 'Junction') { "uebersprungen (keine Junction): $($z.C)"; continue }
  if ($Testlauf) { "wuerde zurueckholen: $($z.O) -> $($z.C)"; continue }
  (Get-Item $z.C).Delete()
  robocopy $z.O $z.C /E /MOVE /SL /R:1 /W:1 /NP /NFL /NDL /NJH | Out-Null
  "zurueck: $($z.C) (Exit $LASTEXITCODE)"
}
