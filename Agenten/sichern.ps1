# Sicherung des Vaults nach G:\MaxHirn-Sicherung
#
# Ablauf: Klartext-Zugangsdaten protokollieren, dann kopieren.
# Kopiert nur Neues und Geaendertes, loescht nichts (kein /MIR).
#
# Ausschluesse: GitHub, .venv, __pycache__, node_modules, .git
# Gemessen 19.08.2026: Diese Ordner sind 119.095 der 188.214 Dateien (63 %),
# aber nur 2,2 der 43,9 GB (5 %). Der Durchsatz haengt an der Dateizahl, nicht
# an der Datenmenge (93 GB in 188.000 Dateien -> 3,3 MB/s; eine einzelne Datei
# von 48,83 GB -> 102 MB/s). Alles Ausgeschlossene ist aus Git bzw. pip
# reproduzierbar.
#
# Aufruf:  powershell -ExecutionPolicy Bypass -File sichern.ps1
#          -NurPruefen  = nur die Zugangsdaten-Pruefung, nicht kopieren

param([switch]$NurPruefen)

$ErrorActionPreference = 'Stop'
$quelle = 'C:\Users\faupe\Documents\BrainFiles'
$ziel   = 'G:\MaxHirn-Sicherung'

# Praezise Muster. Die frueheren breiten Muster ('passw', 'secret', 'key')
# lieferten hunderte Fehltreffer - Guitar-Pro-Tabs mit "Secret" im Songtitel,
# Blender-Doku ueber "Keying". Ein Pruefbefehl, dessen Ergebnis man durchblaettern
# muss, wird nicht benutzt.
$namensmuster = @(
  '(?i)^.*passwoer?t.*$', '(?i)^.*passwords?\.(csv|txt|htm|html|json)$',
  '(?i)^(firefox|chrome|edge|brave)\.csv$',
  '(?i)^.*zugangsdaten.*$', '(?i)^.*credentials.*$', '(?i)^zugaenge\.md$',
  '(?i)^.*api[_-]?key.*$', '(?i)^.*[_-]key\.(txt|json|env)$',
  '(?i)^\.env$', '(?i)^.*\.env$',
  '(?i)^id_(rsa|dsa|ecdsa|ed25519)$', '(?i)^ssh_host_.*_key$',
  '(?i)^(passwd|shadow|smbpasswd|secrets\.tdb)$'
)
$ausnahmen = '(?i)\.(env\.template|env\.example)$|\\(GitHub|\.venv|__pycache__|node_modules|\.git)\\'

# Bereits bewertete Fundstellen. Sie bleiben in der Liste, werden aber getrennt
# ausgegeben - sonst geht ein NEUER Fund zwischen den immer gleichen unter.
# Zugaenge.md ist laut CLAUDE.md die einzige Ablage fuer Schluessel und damit
# ein gewollter Treffer; Hermes\.env enthaelt nur auskommentierte Vorlagenzeilen
# (geprueft 23.08.2026). Passwoerter-Quarantaene.md ist eine Checkliste mit
# Dienstnamen, ohne eine einzige Zugangsangabe - sie faellt nur ins Muster,
# weil "Passwoerter" darin vorkommt.
# OKX_API.env steht bewusst NICHT hier - offener Punkt.
#
# Bewusst Pfadenden statt Regex: ein Backslash im Muster muesste doppelt
# geschrieben werden, und genau daran ist die erste Fassung gescheitert
# ("Unbekannte Escape-Zeichenfolge \H"). EndsWith braucht kein Escaping.
$bekannt = @(
  '\Wissen\Zugaenge.md',
  '\Wissen\Passwoerter-Quarantaene.md',
  '\Hermes\.env'
)

Write-Host '=== 1) Pruefung auf Klartext-Zugangsdaten ===' -ForegroundColor Cyan
$treffer = Get-ChildItem $quelle -Recurse -File -Force -ErrorAction SilentlyContinue |
  Where-Object {
    $n = $_.Name
    $_.FullName -notmatch $ausnahmen -and ($namensmuster | Where-Object { $n -match $_ })
  }

function Ist-Bekannt($pfad) {
  foreach ($b in $bekannt) { if ($pfad.EndsWith($b, 'OrdinalIgnoreCase')) { return $true } }
  return $false
}
$altbekannt = @($treffer | Where-Object { Ist-Bekannt $_.FullName })
$offen      = @($treffer | Where-Object { -not (Ist-Bekannt $_.FullName) })

if ($altbekannt) {
  Write-Host "$($altbekannt.Count) bereits bewertet (bewusst so): $(($altbekannt | ForEach-Object { $_.Name }) -join ', ')" -ForegroundColor DarkGray
}

if ($offen) {
  $offen | Select-Object @{n='KB';e={[math]::Round($_.Length/1KB,1)}},
                         @{n='Pfad';e={$_.FullName.Replace($quelle,'')}} |
    Format-Table -AutoSize
  Write-Host "$($offen.Count) noch nicht bewertet - jede einzeln ansehen." -ForegroundColor Yellow
  Write-Host 'Verschluesselt (.kdbx, .pfx) ist unproblematisch. Nur Klartext ist das Problem.'
} else {
  Write-Host 'Nichts Neues.' -ForegroundColor Green
}

if ($NurPruefen) { return }

Write-Host ''
Write-Host '=== 2) Sicherung ===' -ForegroundColor Cyan
$start = Get-Date
# 'logs' ist ausgeschlossen, weil der geplante Lauf (Routinen\sicherung.ps1)
# waehrend der Sicherung in sein eigenes Protokoll schreibt. robocopy kann die
# offene Datei nicht kopieren und beendet mit Code 11 - gemessen 23.08.2026.
robocopy $quelle $ziel /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL `
  /XD Modelle Repos Sitzungen Worktrees .venv __pycache__ node_modules .git logs
$code = $LASTEXITCODE
$dauer = (Get-Date) - $start

Write-Host ("Dauer: {0:hh\:mm\:ss}" -f $dauer)
if ($code -lt 8) {
  Write-Host "robocopy-Code $code - erfolgreich." -ForegroundColor Green
} else {
  Write-Host "robocopy-Code $code - FEHLER." -ForegroundColor Red
  Write-Host ''
  Write-Host 'Hinweis: Quelle und Ziel weichen planmaessig ab. Ohne /MIR behaelt die'
  Write-Host 'Sicherung Dateien, die in der Quelle geloescht wurden - z. B.'
  Write-Host 'Claude\Posteingang\Maximilianbackup0924 (48,8 GB).'
  # Fehler muss nach aussen sichtbar sein: ohne eigenen Exitcode meldet die
  # Aufgabenplanung einen misslungenen Lauf als Erfolg.
  exit 1
}

Write-Host ''
Write-Host 'Hinweis: Quelle und Ziel weichen planmaessig ab. Ohne /MIR behaelt die'
Write-Host 'Sicherung Dateien, die in der Quelle geloescht wurden - z. B.'
Write-Host 'Claude\Posteingang\Maximilianbackup0924 (48,8 GB).'
