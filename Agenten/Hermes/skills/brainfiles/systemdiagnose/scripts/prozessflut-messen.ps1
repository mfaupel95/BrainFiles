<#
  prozessflut-messen.ps1 - Prozessflut je Gruppe messen, Erzeuger zeigen und
  auf Wunsch den Ueberschuss beenden.

  TROCKENLAUF IST DIE VORGABE. Beendet wird nur mit -Anwenden.

  Aufruf ueber das terminal-Werkzeug:
    powershell -NoProfile -File <skill>\scripts\prozessflut-messen.ps1
    powershell -NoProfile -File <skill>\scripts\prozessflut-messen.ps1 -Muster 'MCP-Server' -Proben 5
    powershell -NoProfile -File <skill>\scripts\prozessflut-messen.ps1 -Anwenden

  Hausregel: Handels-Dauerlauf, MoonDev-Agenten, Gateway, SkillsBot werden
  nie beendet - auch wenn sie ins Muster fallen.
#>
param(
  [string]$Muster    = 'MCP-Server',
  [int]$JeGruppe     = 3,
  [int]$Proben       = 3,
  [int]$TaktSekunden = 10,
  [switch]$Anwenden
)

$ErrorActionPreference = 'Continue'
$geschuetzt = 'dauerlauf|moondev|gateway|skillsbot|handelszentrale|repos-zentrale'

function Get-Kennzahlen {
  $os = Get-CimInstance Win32_OperatingSystem
  $pf = 0
  foreach ($p in @(Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue)) { $pf += $p.CurrentUsage }
  [pscustomobject]@{
    Zeit       = (Get-Date).ToString('HH:mm:ss')
    Python     = @(Get-Process python, pythonw -ErrorAction SilentlyContinue).Count
    Node       = @(Get-Process node -ErrorAction SilentlyContinue).Count
    CommitFrei = [math]::Round($os.FreeVirtualMemory / 1MB, 1)
    RamFrei    = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
    PagefileMB = $pf
  }
}

function Get-Gruppe($cmd) {
  if (-not $cmd) { return '(ohne Kommandozeile)' }
  $m = [regex]::Match($cmd, [regex]::Escape($Muster) + '\\[^\\]+')
  if ($m.Success -and $m.Value) { return $m.Value }
  if ($cmd.Length -gt 60) { return $cmd.Substring(0, 60) }
  return $cmd
}

Write-Output ("Prozessflut-Messung  Muster='{0}'  JeGruppe={1}  Anwenden={2}" -f $Muster, $JeGruppe, [bool]$Anwenden)
for ($i = 1; $i -le $Proben; $i++) {
  $k = Get-Kennzahlen
  Write-Output ("{0}  python={1,4}  node={2,4}  Commit frei={3,6} GB  RAM frei={4,6} GB  Pagefile={5} MB" -f `
      $k.Zeit, $k.Python, $k.Node, $k.CommitFrei, $k.RamFrei, $k.PagefileMB)
  if ($i -lt $Proben) { Start-Sleep -Seconds $TaktSekunden }
}

$kinder = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match $Muster })
if ($kinder.Count -eq 0) { Write-Output "Keine Prozesse mit Muster '$Muster' gefunden."; return }

$gruppen = @($kinder | Group-Object { Get-Gruppe $_.CommandLine })
Write-Output ''
Write-Output 'Gruppen (groesste zuerst):'
foreach ($g in ($gruppen | Sort-Object Count -Descending)) {
  $marke = ''
  if ($g.Count -gt $JeGruppe) { $marke = '   <-- UEBERZAEHLIG' }
  Write-Output ('{0,4} x  {1}{2}' -f $g.Count, $g.Name, $marke)
}

Write-Output ''
Write-Output 'Erzeuger (Eltern der gefundenen Prozesse):'
foreach ($e in ($kinder | Group-Object ParentProcessId | Sort-Object Count -Descending | Select-Object -First 6)) {
  $pp = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $e.Name) -ErrorAction SilentlyContinue
  if (-not $pp) { Write-Output ('{0,4} x  PID {1}  (nicht mehr vorhanden)' -f $e.Count, $e.Name); continue }
  $c = $pp.CommandLine
  if (-not $c) { $c = '(ohne Kommandozeile)' }
  if ($c.Length -gt 100) { $c = $c.Substring(0, 100) }
  Write-Output ('{0,4} x  PID {1}  {2}  {3}' -f $e.Count, $e.Name, $pp.Name, $c)
}

$ueber = @()
foreach ($g in $gruppen) {
  if ($g.Count -le $JeGruppe) { continue }
  $nach = @($g.Group | Sort-Object CreationDate -Descending)
  foreach ($p in @($nach | Select-Object -Skip $JeGruppe)) {
    if ($p.ProcessId -eq $PID) { continue }
    if ($p.CommandLine -and ($p.CommandLine -match $geschuetzt)) { continue }
    $ueber += $p
  }
}

Write-Output ''
Write-Output ('Ueberschuss: {0} Prozess(e)' -f $ueber.Count)
if (-not $Anwenden) {
  Write-Output 'Trockenlauf - nichts beendet. Zum Beenden -Anwenden anhaengen.'
  return
}
foreach ($p in $ueber) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 8
$k = Get-Kennzahlen
Write-Output ('Nach dem Beenden: python={0}  node={1}  Commit frei={2} GB' -f $k.Python, $k.Node, $k.CommitFrei)
