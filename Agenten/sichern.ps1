# Sicherung des Vaults nach G:\MaxHirn-Sicherung
#
# Ablauf: Klartext-Zugangsdaten protokollieren, dann kopieren.
# Kopiert nur Neues und Geaendertes, loescht nichts (kein /MIR).
#
# Ausschluesse: Modelle (huggingface-reproduzierbar), Werkstatt (Durchgangsware),
# .venv, __pycache__, node_modules, .git, logs
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
# Pflichtquelle vor Scan, Prozessbeendigung oder Kopieren pruefen.
if (-not (Test-Path -LiteralPath 'O:\Archiv' -PathType Container)) {
  Write-Host 'ARCHIV_SOURCE_MISSING: O:\Archiv fehlt; keine Sicherung gestartet.' -ForegroundColor Red
  exit 2
}
# Dieses Skript liegt in Agenten\; eine Ebene hoeher ist die Wurzel BrainFiles\.
# Relativ statt absolut, damit ein Umzug den Sicherungslauf nicht bricht.
$quelle = Split-Path $PSScriptRoot -Parent
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
# Modelle und Werkstatt mit ausgeklammert: seit die Quelle BrainFiles\ ist,
# liefe die Pruefung sonst durch 51 GB Modellgewichte (huggingface-Caches mit
# *api_key*, *.env im Namen) - am 31.08.2026 waren das 193 Fehltreffer.
$ausnahmen = '(?i)\.(env\.template|env\.example)$|\\(GitHub|Modelle|Werkstatt|\.venv|__pycache__|node_modules|\.git)\\'

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
Write-Host '=== 2) Claude Desktop beenden ===' -ForegroundColor Cyan
$claude_proc = Get-Process claude -ErrorAction SilentlyContinue
if ($claude_proc) {
  Write-Host "Claude läuft (PID $($claude_proc.Id)), beende vor Sicherung..."
  $claude_proc | Stop-Process -Force -ErrorAction SilentlyContinue
  $timeout = 30
  $start_wait = Get-Date
  while ((Get-Process claude -ErrorAction SilentlyContinue) -and ((Get-Date) - $start_wait).TotalSeconds -lt $timeout) {
    Start-Sleep -Milliseconds 500
  }
  if (Get-Process claude -ErrorAction SilentlyContinue) {
    Write-Host "WARNUNG: Claude beendet sich nicht (Timeout $timeout s). Sicherung trotzdem versucht." -ForegroundColor Yellow
  } else {
    Write-Host "Claude Desktop beendet. Fahre mit Sicherung fort." -ForegroundColor Green
  }
} else {
  Write-Host "Claude nicht aktiv - Sicherung kann starten." -ForegroundColor Green
}

Write-Host ''
Write-Host '=== 3) Sicherung ===' -ForegroundColor Cyan
$start = Get-Date
# 'logs' ist ausgeschlossen, weil der geplante Lauf (Routinen\sicherung.ps1)
# waehrend der Sicherung in sein eigenes Protokoll schreibt. robocopy kann die
# offene Datei nicht kopieren und beendet mit Code 11 - gemessen 23.08.2026.
# /XJ ueberspringt Junctions: BrainFiles\Modelle zeigt auf O:\Modelle, und der
# Vault selbst kann in einem Worktree gespiegelt sein. Das Archiv ist hier keine
# Junction mehr (echter Umzug 07.09.2026) - unter $quelle liegt davon nichts.
robocopy $quelle $ziel /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL `
  /XD Modelle Werkstatt .venv __pycache__ node_modules .git logs pending_messages terminal-output shared_metrics
$code = $LASTEXITCODE

# Zweiter Lauf: die Archivdaten (Bilder/Dokumente/Musik/Videos/Software/
# Posteingang) liegen seit dem echten Umzug (07.09.2026) physisch auf O:\Archiv
# und damit ausserhalb von $quelle. Dieser Lauf zieht sie nach G:, damit die
# Hauptsicherung inhaltlich vollstaendig bleibt (Drei-Platten-Netz).
$archivQuelle = 'O:\Archiv'
$archivZiel   = Join-Path $ziel 'MaxHirn\Archiv'
if (Test-Path $archivQuelle) {
  robocopy $archivQuelle $archivZiel /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL
  if ($LASTEXITCODE -gt $code) { $code = $LASTEXITCODE }
} else {
  Write-Host 'O:\Archiv nicht erreichbar - Archivteil der Sicherung uebersprungen.' -ForegroundColor Red
  if ($code -lt 8) { $code = 8 }
}
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
  Write-Host ''
  Write-Host 'Fehlercode 3221225786 (STATUS_CONFLICT_WITH_LOCK) = Claude Desktop war noch offen'
  Write-Host 'und blockierte Dateien. Sicherungsskript beendet Claude jetzt automatisch.'
  # Fehler muss nach aussen sichtbar sein: ohne eigenen Exitcode meldet die
  # Aufgabenplanung einen misslungenen Lauf als Erfolg.
  exit 1
}

Write-Host ''
Write-Host 'Hinweis: Quelle und Ziel weichen planmaessig ab. Ohne /MIR behaelt die'
Write-Host 'Sicherung Dateien, die in der Quelle geloescht wurden - z. B.'
Write-Host 'Claude\Posteingang\Maximilianbackup0924 (48,8 GB).'
