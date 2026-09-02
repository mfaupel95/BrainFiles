# Kurzfassung der Systempruefung fuer den SessionStart-Hook von Claude Code.
#
# Gibt nichts aus, wenn es nichts zu sagen gibt - ein Hook, der jeden
# Sitzungsstart mit "alles ok" zumuellt, wird abgeschaltet. Ausgegeben wird nur,
# wenn der Bericht von heute ist UND mindestens ein Punkt zu entscheiden bleibt.
#
# Eingebunden ueber MaxHirn/.claude/settings.local.json -> hooks.SessionStart.

$ErrorActionPreference = 'SilentlyContinue'
$bericht = Join-Path $PSScriptRoot 'logs\systempruefung-letzter-lauf.md'
if (-not (Test-Path $bericht)) { exit 0 }

$zeilen = Get-Content $bericht -Encoding UTF8
$datumZeile = $zeilen | Where-Object { $_ -match '^# Systempruefung (\d{4}-\d{2}-\d{2})' } | Select-Object -First 1
if (-not $datumZeile) { exit 0 }
$null = $datumZeile -match '(\d{4}-\d{2}-\d{2})'
$berichtsdatum = $Matches[1]
$heute = (Get-Date).ToString('yyyy-MM-dd')

$alter = if ($berichtsdatum -eq $heute) { 'von heute' } else { "vom $berichtsdatum (heute noch kein Lauf)" }

# Abschnitte "Seit gestern neu" und "Zu entscheiden" herausschneiden
$aus = [System.Collections.Generic.List[string]]::new()
$imBlock = $false
foreach ($z in $zeilen) {
  if ($z -match '^## (Seit gestern neu|Zu entscheiden)') { $imBlock = $true; $aus.Add(''); $aus.Add($z); continue }
  if ($z -match '^## ') { $imBlock = $false; continue }
  if ($imBlock -and $z.Trim()) { $aus.Add($z) }
}

$zuEntscheiden = ($zeilen | Where-Object { $_ -match '^## Zu entscheiden \((\d+)\)' })
$anzahl = 0
if ($zuEntscheiden -and ($zuEntscheiden -match '\((\d+)\)')) { $anzahl = [int]$Matches[1] }
if ($anzahl -eq 0) { exit 0 }

Write-Output "Systempruefung $alter - $anzahl Punkt(e) zu entscheiden. Voller Bericht: Agenten\Routinen\logs\systempruefung-letzter-lauf.md"
$aus | ForEach-Object { Write-Output $_ }
exit 0
