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
# Geklonte Fremdbaeume pfadgenau, nicht ueber den blanken Namen: ein Muster
# 'skills' oder 'codex' ohne Pfad traefe auch .claude\skills\ - also genau das
# von Hand geschriebene Textmaterial, das die Pruefung sehen SOLL.
# Gemessen 12.09.2026: Von 246 Treffern kamen 170 aus MaxHirn\skills, 46 aus
# Agenten\Hermes\hermes-agent, 19 aus CLIProxyAPI und 4 aus codex - alles
# Quellcode, dessen DATEINAME 'credentials' oder 'api_key' enthaelt. Uebrig
# blieben 18, und darunter standen die echten: 14 Hermes-Profil-.env,
# eine alte Kopie der Schluesselablage und ein llama.cpp-Schluessel.
$ausnahmen = '(?i)\.(env\.template|env\.example)$|\\(GitHub|Modelle|Werkstatt|\.venv|__pycache__|node_modules|\.git)\\|\\(MaxHirn\\skills|MaxHirn\\CLIProxyAPI|MaxHirn\\codex|Agenten\\Hermes\\hermes-agent)\\'

# Bereits bewertete Fundstellen. Sie bleiben in der Liste, werden aber getrennt
# ausgegeben - sonst geht ein NEUER Fund zwischen den immer gleichen unter.
# Zugaenge.md ist laut CLAUDE.md die einzige Ablage fuer Schluessel und damit
# ein gewollter Treffer; Hermes\.env enthaelt nur auskommentierte Vorlagenzeilen
# (geprueft 23.08.2026). Passwoerter-Quarantaene.md ist eine Checkliste mit
# Dienstnamen, ohne eine einzige Zugangsangabe - sie faellt nur ins Muster,
# weil "Passwoerter" darin vorkommt.
# OKX_API.env stand hier als offener Punkt: die Datei lag im Archiv-Posteingang
# und wurde von Lauf 2 (O:\Archiv) mitkopiert, ohne dass die Zugangsdaten-Pruefung
# sie sehen konnte - die laeuft nur ueber $quelle. Seit 12.09.2026 liegt sie
# unter %USERPROFILE%\.zugangsdaten\ und damit ausserhalb beider Quellen.
#
# Bewusst Pfadenden statt Regex: ein Backslash im Muster muesste doppelt
# geschrieben werden, und genau daran ist die erste Fassung gescheitert
# ("Unbekannte Escape-Zeichenfolge \H"). EndsWith braucht kein Escaping.
$bekannt = @(
  '\Wissen\Zugaenge.md',
  '\Wissen\Passwoerter-Quarantaene.md',
  '\Hermes\.env',
  # OKX_API.env lag bis 12.09.2026 im Archiv-Posteingang und wurde dort von
  # Lauf 2 mitkopiert, ohne dass diese Pruefung sie sehen konnte - sie laeuft nur
  # ueber $quelle. Seit dem 12.09.2026 liegt die Datei neben der Schluesselablage,
  # damit hier sichtbar und bewertet, und alle Streukopien sind entfernt.
  '\Wissen\OKX_API.env',
  # Schluessel der lokalen llama.cpp-Laufzeit, nur auf diesem Rechner gueltig.
  '\runtimes\llamacpp\.api_key',
  # Schutzkopie der Notizen vom 30.08.2026. Passwoerter-Quarantaene.md ist laut
  # eigener Beschreibung eine Checkliste mit Dienstnamen und ohne eine einzige
  # Zugangsangabe; sie faellt nur ins Muster, weil "Passwoerter" darin vorkommt.
  '\Archiv\.sicherung-wissen-20260830\Passwoerter-Quarantaene.md',
  # Kostenloser AcoustID-Schluessel fuer die Musik-Erkennung. Das Werkzeug liest
  # ihn nicht aus dieser Datei, sondern aus --acoustid-key oder der
  # Umgebungsvariable ACOUSTID_KEY; die Datei ist die Ablage des Werts.
  '\Archiv\ArchivSuche\acoustid_key.txt'
)

# Bewertete KLASSEN als Muster statt als Endung, getrennt von $bekannt: eine
# Klasse soll nicht jeden einzelnen neuen Fund verschlucken. Ein .env irgendwo
# sonst im Baum faellt weiterhin auf.
# Hermes legt je Profil eine eigene Zugangsdatei an (12 Stueck, je 27 KB) und
# sichert bei einem Update den alten Stand mit. Beides sind laufende
# Zugangsdaten des Agenten, keine vergessenen Reste. Bewusst so entschieden am
# 12.09.2026: sie bleiben in der Sicherung, damit ein Wiederaufbau die Profile
# nicht ohne Schluessel dastehen laesst. Hingenommen wird dafuer, dass sie auf
# den Sicherungsdatentraegern im Klartext liegen.
$bekanntMuster = @(
  '\\Agenten\\Hermes\\profiles\\[^\\]+\\.env$',
  '\\Agenten\\Hermes\\state-snapshots\\[^\\]+\\.env$'
)

Write-Host '=== 1) Pruefung auf Klartext-Zugangsdaten ===' -ForegroundColor Cyan
$treffer = Get-ChildItem $quelle -Recurse -File -Force -ErrorAction SilentlyContinue |
  Where-Object {
    $n = $_.Name
    $_.FullName -notmatch $ausnahmen -and ($namensmuster | Where-Object { $n -match $_ })
  }

function Ist-Bekannt($pfad) {
  foreach ($b in $bekannt) { if ($pfad.EndsWith($b, 'OrdinalIgnoreCase')) { return $true } }
  foreach ($m in $bekanntMuster) { if ($pfad -match $m) { return $true } }
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
# Seit 29.09.2026 pfadgenau ausgeschlossen, zusammen rund 14 GB: Hermes\models
# und Hermes\runtimes (GGUF-Gewichte und Laufzeiten, gehoeren nach Modelle\),
# Handel\nautilus-rust\target (Rust-Build-Cache, cargo baut ihn neu) und
# _Backups (Notfallkopien von state.db; das Original geht mit).
# Waisen-Reste abgebrochener Updates. NUR der gesperrte .partial-Ordner wird
# ausgeschlossen: leer, aber GESPERRT (icacls schlaegt selbst fehl, Remove-Item
# 'Access denied'). robocopy versuchte zweimal, brach nach 1 s Wartezeit ab und
# beendete den Lauf mit FEHLER 5 / Code 11, obwohl 0 Nutzdateien fehlten. Ein
# gesperrter Bau-Rest gehoert nicht in die Sicherung: er ist nicht kopierbar
# und nicht wiederherstellbar.
# NICHT ausgeschlossen: tools\.previous-python-* (346 MB) und die
# MCP-Server\*.venv.bak-20260918 (~45 MB je). Sie sind NICHT gesperrt, werden
# sauber kopiert und liegen als Reserve neben dem funktionierenden Original -
# ihr Ausschluss waere eine stillschweigende Datenverlagerung, keine Fehlerbehebung.
# WICHTIG - Wildcards sind in /XD nicht erlaubt: robocopy wertet
# '...\*.partial' als Ordnernamen, meldet 'Ungueltiger Parameter #11' und
# endet mit Code 16, OHNE zu kopieren (gemessen 03.10.2026). Deshalb wird
# der Pfad hier aufgeloest und als Liste uebergeben.
$waisen = @()
foreach ($muster in @('Agenten\Hermes\state-snapshots\.*.partial')) {
  $waisen += @(Get-ChildItem -Path (Join-Path $quelle $muster) -Directory `
                 -Force -ErrorAction SilentlyContinue |
               ForEach-Object { $_.FullName })
}
if ($waisen.Count -gt 0) {
  Write-Host ("Gesperrte Update-Reste ausgeschlossen: {0}" -f $waisen.Count)
}

robocopy $quelle $ziel /E /XJ /R:1 /W:1 /MT:16 /NP /NFL /NDL `
  /XD Modelle Werkstatt .venv __pycache__ node_modules .projectatlas .git logs pending_messages terminal-output shared_metrics browser-profile .leases (Join-Path $quelle 'Agenten\Hermes\cache') (Join-Path $quelle 'Agenten\Hermes\cron\output') (Join-Path $quelle 'Agenten\Hermes\models') (Join-Path $quelle 'Agenten\Hermes\runtimes') (Join-Path $quelle 'Agenten\Handel\nautilus-rust\target') (Join-Path $quelle 'Agenten\_Backups') (Join-Path $quelle 'MaxHirn\_zu_loeschen') $waisen `
  /XF *.pid *.db-shm *.db-wal *.lock 'Zugaenge.md' *.env auth.json OKX_API.env nous_auth.json   # 08.10.2026: Klartext-Zugangsdaten ausgeschlossen - sie liegen stattdessen verschluesselt in Agenten\Hermes\secrets\secrets-<datum>.7z (erzeugt von secrets-archivieren.ps1, AES-256 mit -mhe=on). Betroffen: 57 Profil-.env (Hermes legt je Profil eine an), auth.json (credential_pool mit access_token/refresh_token/agent_key) und die Schluesselablagen. Keine der Sicherungsplatten hat BitLocker; die Profil-.env waren bis 12.09.2026 bewusst zum Wiederaufbau drin, ab 08.10.2026 kommen sie aus dem Archiv. *.env ist absichtlich breit (jede .env im Baum) und trifft .env.template NICHT - gemessen 08.10.2026 mit robocopy /L. Seit 07.10.2026 auch *.db-shm/*.db-wal/*.lock und .leases (XD): SQLite-Nebendateien und Lock-/Lease-Marker laufender Hermes-Prozesse verschwinden zwischen Auflisten und Kopieren (FEHLER 2, Code 11, Exitcode 1 am 06.10.2026, keine Nutzdatei fehlte). *.pid sind fluechtige Sperrdateien (skillsbot.pid haelt den Bus); robocopy kann sie nicht lesen und meldet sonst Code 11. Agenten\Hermes\cache ist Wegwerf- und Probebereich (transiente Test-Klone, Wache-Zustaende): Entstehen und Vergehen waehrend des Laufs und liessen robocopy 21.09.2026 mit Code 11 und Exitcode 1 enden, obwohl keine Nutzdatei fehlte. Agenten\Hermes\cron\output ist derselbe Fall (Cron-Ausgaben, alle 6 min neu, alte werden weggeraeumt - gemessen 22.09.2026, 838 Dateien). $waisen traegt die gesperrten Update-Reste als AUFGELOESTE Vollpfade (siehe oben). 'Zugaenge.md' ist seit 07.10.2026 ausgeschlossen: die Datei ist die einzige Schluesselablage (CLAUDE.md) und lag nach jedem Lauf im Klartext auf G:. Der git-Remote (private GitHub, seit 07.10.2026) traegt den Text-Layer nicht, also gibt es keine ausser-Haus-Kopie dieser Datei mehr - robocopy /XF nach Dateiname ist absichtlich breit (jede Zugaenge.md im Baum), weil die Quelle nur diese eine legitime Stelle hat.
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
  Write-Host 'Hinweis zu Fehlercode 3221225786 (0xC0000409, STATUS_STACK_BUFFER_OVERRUN):'
  Write-Host 'das ist ein genereller Fail-Fast-Code, KEIN Beleg fuer eine Datei-Sperre durch'
  Write-Host 'Claude Desktop. Ursache am 29./30.09.2026 war Commit-Erschoepfung durch einen'
  Write-Host 'MCP-Server-Spawn-Sturm (Docker/WSL haengt) - siehe'
  Write-Host 'MaxHirn\Wiki\Betrieb\Systemleistung-2026-09-29.md, Abschnitt 9/10.'
  # Fehler muss nach aussen sichtbar sein: ohne eigenen Exitcode meldet die
  # Aufgabenplanung einen misslungenen Lauf als Erfolg.
  exit 1
}

Write-Host ''
Write-Host 'Hinweis: Quelle und Ziel weichen planmaessig ab. Ohne /MIR behaelt die'
Write-Host 'Sicherung Dateien, die in der Quelle geloescht wurden - z. B.'
Write-Host 'Claude\Posteingang\Maximilianbackup0924 (48,8 GB).'
