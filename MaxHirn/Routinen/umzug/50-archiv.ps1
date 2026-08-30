# Phase 5 -- Claude/ heisst Archiv/.
#
# Der 45-GB-Ordner mit Vertraegen, Bescheiden und Fotos war nach einem Modell
# benannt, obwohl alle Modelle darauf zugreifen sollen. Genau diese
# Verwechslung war der Anlass fuer den ganzen Umbau.
#
# Billig ist das nur, weil der Suchindex relative Pfade speichert
# (files_meta.path = 'Bilder\-009.JPG', 9712 Eintraege) und index.py seine
# Wurzel aus der eigenen Lage ableitet. KEIN Reindex noetig -- wer trotzdem
# einen anstoesst, verliert Stunden ohne Gegenwert.
#
# Nicht angetastet wird das Wort "Claude", wo das Modell gemeint ist, und der
# Anwendungsordner %APPDATA%\Claude. Ersetzt wird nur 'Claude' als Pfadstueck.
#
#   .\50-archiv.ps1            Trockenlauf (zeigt Trefferzahlen)
#   .\50-archiv.ps1 -Echt      wirklich

param([switch]$Echt)
$DryRun = -not $Echt

. "$PSScriptRoot\gemeinsam.ps1"
$wurzel = Get-Wurzel
function P([string]$r) { Join-Path $wurzel $r }

Schritt "Wurzel: $wurzel"

# --- 1. Der Ordner selbst --------------------------------------------------
# Stufe 0: der Ordner wird als GANZES umbenannt, nichts darin einzeln angefasst.
$von  = P 'MaxHirn\Claude'
$nach = P 'MaxHirn\Archiv'
Schritt ''
if (Test-Path $nach) { Schritt 'Archiv\ besteht bereits.' 'ok' }
elseif (-not (Test-Path $von)) { Schritt 'Weder Claude\ noch Archiv\ gefunden.' 'fehler' }
elseif ($DryRun) { Schritt "[Probe] git mv MaxHirn/Claude MaxHirn/Archiv" }
else {
    $blocker = Get-Process | Where-Object { $_.Path -like "*BrainFiles\MaxHirn\Claude*" }
    if ($blocker) {
        $blocker | ForEach-Object { Schritt "  BLOCKIERT: $($_.Name) (PID $($_.Id))" 'fehler' }
        Bilanz 'abgebrochen - es laufen Programme aus Claude\.' -Erfolg:$false
        return
    }
    git -C $wurzel mv MaxHirn/Claude MaxHirn/Archiv 2>&1 | ForEach-Object { Schritt "  git: $_" }
    if (-not (Test-Path $nach)) {
        # git mv scheitert, wenn fast alles darin unversioniert ist - dann von Hand.
        Move-Item -LiteralPath $von -Destination $nach -Force
        Schritt 'per Move-Item umbenannt (git mv war nicht zustaendig).' 'ok'
    } else { Schritt 'umbenannt: MaxHirn\Claude -> MaxHirn\Archiv' 'ok' }
}

# --- 2. Die Verweise -------------------------------------------------------
# Zwei Regelgruppen, bewusst getrennt:
#   a) absolute Pfade  ...\MaxHirn\Claude  (auch JSON-verdoppelt)
#   b) relative Pfadstuecke  Claude/  und  Claude\
# Gruppe b traegt eine Sperre gegen %APPDATA%\Claude und $env:APPDATA\Claude --
# das ist der Anwendungsordner der Desktop-App und bleibt, wie er heisst.
# Die Worktrees zuerst, und zwar VOR den allgemeinen Regeln: sie sind in
# Phase 4 in die Werkstatt gewandert, nicht ins Archiv. Wer nur 'Claude ->
# Archiv' ersetzt, schreibt hier einen Pfad hin, den es nie gab.
$regeln = [ordered]@{
    'MaxHirn\\Claude\\Worktrees'                         = 'Werkstatt\Worktrees'
    'Claude/Worktrees'                                   = 'Werkstatt/Worktrees'
    'Claude\\Worktrees'                                  = 'Werkstatt\Worktrees'
    'MaxHirn\\\\Claude'                                  = 'MaxHirn\\Archiv'   # JSON
    'MaxHirn\\Claude'                                    = 'MaxHirn\Archiv'    # YAML, ps1, Text
    '(?<!APPDATA%\\)(?<!APPDATA\\)(?<!APPDATA%\\\\)(?<!APPDATA\\\\)Claude\\' = 'Archiv\'
    'Claude/'                                            = 'Archiv/'
}

$ziele = @()
$ziele += Get-ChildItem (P 'MaxHirn') -File -Filter '*.md'
$ziele += Get-ChildItem (P 'MaxHirn\Wissen') -File -Filter '*.md' -EA SilentlyContinue
$ziele += Get-ChildItem (P 'MaxHirn\.claude\skills') -Recurse -File -Include '*.md', '*.py' -EA SilentlyContinue
$ziele += Get-ChildItem (P 'MaxHirn\.agents\skills') -Recurse -File -Include '*.md' -EA SilentlyContinue
$ziele += Get-ChildItem (P 'MaxHirn\Archiv') -File -Filter '*.md' -EA SilentlyContinue
$ziele += Get-ChildItem (P 'MaxHirn\Archiv\ArchivSuche') -File -Include '*.py', '*.md', '*.bat' -EA SilentlyContinue
$ziele += Get-ChildItem (P 'Agenten') -File -Filter '*.ps1' -EA SilentlyContinue
$ziele += Get-ChildItem (P 'Agenten\Routinen') -File -Filter '*.ps1' -EA SilentlyContinue
foreach ($s in 'archiv', 'kraken', 'mail') {
    $ziele += Get-ChildItem (P "Agenten\MCP-Server\$s") -File -Include '*.py', '*.md' -EA SilentlyContinue
}
$ziele += Get-Item (P 'Agenten\Hermes\config.yaml') -EA SilentlyContinue
# claude_desktop_config.json steht bewusst NICHT in dieser Liste - siehe unten.

# Handkopien bleiben aussen vor: ihre Geschichte steht seit Phase 1 in Git.
# Zugaenge.md und Passwoerter-Quarantaene.md stehen in Stufe 0 der
# Schutzregeln: kein Agent ueberschreibt sie ohne ausdrueckliche Anordnung fuer
# genau diese Datei. Ihre Treffer werden nur gemeldet, nicht ersetzt - ein
# veralteter Pfad in einer Notiz ist der kleinere Schaden.
$stufe0 = @('Zugaenge.md', 'Passwoerter-Quarantaene.md')
$geschuetzt = $ziele | Where-Object { $_ -and $stufe0 -contains $_.Name }
$ziele = $ziele | Where-Object { $_ -and $_.Name -notlike '*.bak-*' -and $stufe0 -notcontains $_.Name } | Sort-Object FullName -Unique

Schritt ''
Schritt "Verweise in $($ziele.Count) Dateien:"
$gesamt = 0; $geaendert = 0
foreach ($z in $ziele) {
    $n = Ersetze-InDatei -Datei $z.FullName -Ersetzungen $regeln -DryRun:$DryRun
    if ($n -gt 0) {
        $gesamt += $n; $geaendert++
        Schritt ("  {0,3}  {1}" -f $n, $z.FullName.Replace("$wurzel\", ''))
    }
}

# --- 2b. claude_desktop_config.json: nur die Einstellungen, nie die Vermerke --
#
# In dieser Datei stehen zweierlei Pfade:
#   - funktionale Einstellungen (pdf-vault, coworkUserFilesPath, Worktrees)
#   - Berechtigungsvermerke frueherer Sitzungen (remoteSessionFolderGrants,
#     remoteFolderConsentMemory, epitaxy-perm-mode-acks)
#
# Die zweite Sorte wird NICHT umgeschrieben. Ein Vermerk auf einen Pfad, den es
# nicht mehr gibt, gewaehrt nichts - das ist der harmlose Ausgang. Wuerde man
# ihn mitziehen, waere eine Freigabe auf den neuen Ort ausgedehnt, ohne dass
# Max sie je erteilt hat. Deshalb hier gezielte Schluessel statt Textersetzung.
$desktop = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
if (Test-Path $desktop) {
    Sicherungskopie -Datei $desktop -DryRun:$DryRun | Out-Null
    $cfg = Get-Content -LiteralPath $desktop -Raw | ConvertFrom-Json
    $altArchiv = (P 'MaxHirn\Claude')
    $neuArchiv = (P 'MaxHirn\Archiv')
    $neuTrees  = (P 'Werkstatt\Worktrees')
    $k = 0

    if ($cfg.mcpServers.'pdf-vault' -and $cfg.mcpServers.'pdf-vault'.args -contains $altArchiv) {
        $cfg.mcpServers.'pdf-vault'.args = @($cfg.mcpServers.'pdf-vault'.args | ForEach-Object { if ($_ -eq $altArchiv) { $neuArchiv } else { $_ } })
        $k++; Schritt '  pdf-vault: Archivpfad nachgezogen' 'ok'
    }
    if ($cfg.coworkUserFilesPath -eq $altArchiv) { $cfg.coworkUserFilesPath = $neuArchiv; $k++; Schritt '  coworkUserFilesPath nachgezogen' 'ok' }
    # Worktrees liegen seit Phase 4 in der Werkstatt, nicht mehr im Archiv.
    if ($cfg.preferences.chillingSlothLocation.customPath -like "$altArchiv\Worktrees*") {
        $cfg.preferences.chillingSlothLocation.customPath = $neuTrees
        $k++; Schritt '  Worktree-Ort auf Werkstatt\Worktrees gesetzt' 'ok'
    }
    if (-not $DryRun -and $k -gt 0) {
        ($cfg | ConvertTo-Json -Depth 30) | Set-Content -LiteralPath $desktop -Encoding UTF8
    }
    Schritt "claude_desktop_config.json: $k Einstellung(en); Berechtigungsvermerke unangetastet." 'ok'
}

# --- 3. Gegenprobe ---------------------------------------------------------
# Uebrig bleiben duerfen nur '.claude/' (klein) und der Anwendungsordner.
Schritt ''
foreach ($g in $geschuetzt) {
    $roh = Get-Content -LiteralPath $g.FullName -Raw -EA SilentlyContinue
    $n = if ($roh) { ([regex]::Matches($roh, 'Claude[/\\]')).Count } else { 0 }
    if ($n -gt 0) { Schritt "STUFE 0, von Hand: $n Verweis(e) in $($g.Name) -- nicht automatisch geaendert." 'warn' }
}

$rest = @()
# Im Trockenlauf waeren alle Treffer noch da - die Gegenprobe ergaebe nur
# Rauschen. Sie zaehlt erst nach einem echten Lauf.
foreach ($z in $(if ($DryRun) { @() } else { $ziele })) {
    $inhalt = Get-Content -LiteralPath $z.FullName -Raw -EA SilentlyContinue
    if (-not $inhalt) { continue }
    foreach ($m in [regex]::Matches($inhalt, '.{0,14}Claude[/\\].{0,14}')) {
        if ($m.Value -notmatch 'APPDATA') { $rest += "$($z.Name): $($m.Value -replace '\s+',' ')" }
    }
}
if ($rest) {
    Schritt "Gegenprobe: $($rest.Count) Resttreffer -- pruefen:" 'warn'
    $rest | Select-Object -First 12 | ForEach-Object { Schritt "  $_" 'warn' }
} else { Schritt 'Gegenprobe: kein Resttreffer ausser dem Anwendungsordner.' 'ok' }

if ($DryRun) { Bilanz "Probe: $gesamt Stellen in $geaendert Dateien wuerden geaendert." }
else { Bilanz "$gesamt Stellen in $geaendert Dateien geaendert; $($rest.Count) Resttreffer." -Erfolg:($rest.Count -eq 0) }
Protokoll-Schreiben '50-archiv' | Out-Null
