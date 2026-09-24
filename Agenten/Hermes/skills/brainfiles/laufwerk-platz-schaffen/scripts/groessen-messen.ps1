# Groessen unter einem Ordner messen - Windows, reparse-sicher.
#
# Warum PowerShell und nicht du: du folgt dem Selbst-Verweis
# %LOCALAPPDATA%\Anwendungsdaten (= Application Data) und druckt dann fast
# nichts mehr (die echten Unterordner fallen aus der Liste). Hier werden
# Reparse-Punkte explizit aussortiert und benannt.
#
# Aufruf (Hintergrund, Ausgabe in eine Datei - ein voller Lauf ueber Local +
# Roaming braucht Minuten, mehr als das Terminal-Zeitlimit):
#   powershell -NoProfile -ExecutionPolicy Bypass -File groessen-messen.ps1 \
#     -Wurzel $env:LOCALAPPDATA -Top 15 > <scratch>/groessen.txt
param(
  [string[]] $Wurzel = @($env:LOCALAPPDATA, $env:APPDATA),
  [int] $Top = 15
)
$ErrorActionPreference = 'Continue'
foreach ($w in $Wurzel) {
  if (-not (Test-Path $w)) { "=== $w  (fehlt)"; continue }
  "=== $w"
  $zeilen = @()
  foreach ($d in (Get-ChildItem $w -Force -Directory -ErrorAction SilentlyContinue)) {
    if ($d.Attributes -band [IO.FileAttributes]::ReparsePoint) {
      $zeilen += [pscustomobject]@{ MB = -1; Name = $d.Name + '  (VERWEIS, nicht gezaehlt)' }
    } else {
      $s = (Get-ChildItem $d.FullName -Recurse -Force -File -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum).Sum
      $zeilen += [pscustomobject]@{ MB = [int][math]::Round($s / 1MB); Name = $d.Name }
    }
  }
  $zeilen | Sort-Object MB -Descending | Select-Object -First $Top |
    ForEach-Object { '{0,8} MB  {1}' -f $_.MB, $_.Name }
}
'FERTIG'
