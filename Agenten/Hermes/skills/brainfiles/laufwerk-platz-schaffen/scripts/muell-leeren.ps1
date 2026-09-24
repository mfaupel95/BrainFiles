# Inhalte von Muell-Ordnern leeren und vorher/nachher messen.
#
# Bewusst nur INHALTE loeschen, nie den Ordner selbst (Windows hält ihn
# offen). Dateien in Benutzung bleiben liegen - das ist kein Fehler.
#
# Aufruf:
#   powershell -NoProfile -ExecutionPolicy Bypass -File muell-leeren.ps1
# Test/anderer Ort:
#   powershell -NoProfile -ExecutionPolicy Bypass -File muell-leeren.ps1 -Ordner <pfad>
param(
  [string[]] $Ordner = @("$env:LOCALAPPDATA\CrashDumps", "$env:LOCALAPPDATA\Temp")
)
$ErrorActionPreference = 'Continue'
function Groesse([string] $p) {
  if (-not (Test-Path $p)) { return 0 }
  $s = (Get-ChildItem $p -Recurse -Force -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
  return [int][math]::Round($s / 1MB)
}
foreach ($p in $Ordner) {
  $vor = Groesse $p
  Get-ChildItem $p -Force -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
  }
  $nach = Groesse $p
  '{0}: {1} MB -> {2} MB' -f (Split-Path $p -Leaf), $vor, $nach
}
'FERTIG'
