<#
.SYNOPSIS
    Zieht ruhende Fremdarbeit beendeter Sitzungen in die Hauptarbeit (master).

.DESCRIPTION
    Hintergrund- und Parallel-Sitzungen (Subagenten, Bots, Desktop-, CLI- und
    Telegram-Sitzungen) schreiben in DENSELBEN Arbeitsbaum, committen ihre
    Arbeit aber oft nicht. Sie steht dann als fremde Aenderung ('M' / '??') im
    Baum - als Fremdarbeiter, der nie in die Hauptarbeit kommt, und der bei
    jedem 'git status' wie offene Arbeit aussieht.

    Der Zwischenstand (zwischenstand.ps1, 20:00) SICHERT diese Arbeit auf dem
    Branch 'zwischenstand' - dort bleibt sie aber liegen. Dieses Skript holt
    sie ein zweites Mal ab und schiebt sie in EINEM Commit auf master, mit dem
    Autor "Andere Sitzung <fremd@local>". Damit ist sichtbar, dass es eine
    Uebernahme ist und keine eigene Arbeit.

    Es kann per Konstruktion nichts kaputtmachen:
      - Eigener Index ueber GIT_INDEX_FILE (.git\fremdarbeit.index). Der normale
        Staging-Bereich bleibt unberuehrt: eine Sitzung, die gerade selektiv
        'git add' gemacht hat, verliert ihre Vormerkung nicht.
      - Kein checkout, kein reset, kein stash, kein clean, kein merge.
      - 'git update-ref' mit Alt-Wert: hat eine andere Sitzung master inzwischen
        bewegt, schlaegt der Schreibvorgang fehl, statt ihre Commits zu
        ueberschreiben.
      - Nur was RUHT (Standard 30 Minuten ohne Aenderung) wird angefasst. Was
        eine laufende Sitzung gerade schreibt, bleibt liegen - die Schwelle ist
        dieselbe wie in den Schutzregeln (Wissen/Schutzregeln.md) und in
        arbeitsbaum-pruefen.ps1.
      - .gitignore ist eine Whitelist: Zugaenge.md, .env, .pfx, .kdbx bleiben
        auch hier draussen.
      - Liegt bereits eine Git-Sperre im Index (eine andere Sitzung committet
        gerade), wird der Lauf uebersprungen statt gewartet.

    Der Arbeitsbaum wird nie veraendert - nur der Verlauf waechst.

.PARAMETER Minuten
    Ruhe-Schwelle in Minuten. Standard 30.

.PARAMETER Testlauf
    Zeigt nur, was uebernommen wuerde. Schreibt nichts.

.PARAMETER NichtPushen
    Kein 'git push origin master' nach dem Commit.

.EXAMPLE
    .\Routinen\fremdarbeit-einziehen.ps1 -Testlauf
    .\Routinen\fremdarbeit-einziehen.ps1
#>
[CmdletBinding()]
param(
    [int]$Minuten = 30,
    [switch]$Testlauf,
    [switch]$NichtPushen
)

# git schreibt Warnungen nach stderr; unter 'Stop' macht schon eine solche
# Warnung den Lauf zunichte (NativeCommandError). Fehler werden deshalb
# ausdruecklich ueber $LASTEXITCODE geprueft.
$ErrorActionPreference = 'Continue'

$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
. (Join-Path $wurzel 'Agenten\Bus\Ereignis.ps1')

$log = Join-Path $logs 'fremdarbeit-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/fremdarbeit-einziehen' `
           -Log 'Agenten/Routinen/logs/fremdarbeit-letzter-lauf.log'

function Schreib($text) {
    $text | Add-Content $log -Encoding UTF8
    Write-Output $text
}

function Test-EingebettetesGitRepo([string]$Pfad, [string]$Wurzel) {
    # In einem eingebetteten Repo fuehrt ein anderes .git die Versionierung
    # (Werkstatt, Agenten/Handel/nautilus, Fremd-Klone in skills/).
    if (Test-Path -LiteralPath $Pfad -PathType Container) {
        $ordner = $Pfad
    } else {
        $ordner = Split-Path -Parent $Pfad
    }
    while ($ordner -and -not [string]::Equals($ordner, $Wurzel, [StringComparison]::OrdinalIgnoreCase)) {
        if (Test-Path -LiteralPath (Join-Path $ordner '.git')) { return $true }
        $naechster = Split-Path -Parent $ordner
        if ($naechster -eq $ordner) { break }
        $ordner = $naechster
    }
    return $false
}

function IndexMitWiederholung([string[]]$argumente, [int]$versuche = 12) {
    # Schreibt in den ECHTEN Index (.git\index) und weicht dabei der Sperre
    # einer anderen Sitzung aus, statt den Lauf abzubrechen.
    for ($i = 1; $i -le $versuche; $i++) {
        $aus = & git @argumente 2>&1
        if ($LASTEXITCODE -eq 0) { return $true }
        if ($i -eq $versuche) { Schreib "    Indexzugriff scheiterte: $aus"; return $false }
        Start-Sleep -Seconds 5
    }
    return $false
}

function Test-Rueckschritt([string]$Pfad) {
    # (T-218) STALE-CHECK: ist der Arbeitsbaum-Stand dieser Datei ein RUECKSCHRITT
    # gegenueber der letzten committeten Aenderung? Am 30.09.2026 hat die Routine eine
    # im Baum liegende ALT-Version des Gateway-Launchers uebernommen und damit eine
    # Reparatur vom Vortag stillschweigend aufgehoben. Eine ruhende Datei, deren Inhalt
    # einem FRUEHEREN Commit dieser Datei entspricht (waehrend HEAD neuer ist), ist nicht
    # 'Fremdarbeit in Arbeit', sondern ein Rueckfall - der wird NICHT uebernommen,
    # sondern uebersprungen und gemeldet.
    try {
        $kopfBlob = (& git ls-tree HEAD -- $Pfad 2>$null)
    } catch { return $false }
    if (-not $kopfBlob) { return $false }        # HEAD kennt die Datei nicht -> kein Rueckschritt
    $kopfTeile = $kopfBlob -split '\s+'
    if ($kopfTeile.Count -lt 3) { return $false }
    $kopf = $kopfTeile[2]
    $wt = (& git hash-object -- $Pfad 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $wt) { return $false }
    $wt = $wt.Trim()
    if ($wt -eq $kopf) { return $false }         # identisch mit HEAD => kein 'M', egal
    $historie = (& git log --format=%H -- $Pfad 2>$null)
    $headSha = (git rev-parse HEAD 2>$null).Trim()
    foreach ($c in ($historie -split "`n")) {
        $c = $c.Trim()
        if (-not $c -or $c -eq $headSha) { continue }
        $alt = (& git ls-tree $c -- $Pfad 2>$null)
        if ($alt) {
            $t = $alt -split '\s+'
            if ($t.Count -ge 3 -and $t[2] -eq $wt) { return $true }
        }
    }
    return $false
}

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) (Schwelle $Minuten Min) ===" | Set-Content $log -Encoding UTF8

try {
    Set-Location $wurzel
    if (-not (Test-Path (Join-Path $wurzel '.git'))) { throw "kein Git-Repository in $wurzel" }

    $zweig = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($zweig -ne 'master') {
        Schreib "ENDE uebersprungen - Arbeitszweig ist '$zweig', nicht master"
        Melde-Ende -Marke $marke -Code 0 -Text "uebersprungen: Zweig $zweig"
        exit 0
    }

    $sperre = Join-Path $wurzel '.git\index.lock'
    if (Test-Path $sperre) {
        Schreib "ENDE uebersprungen - .git\index.lock liegt vor (andere Sitzung committet gerade)"
        Melde-Ende -Marke $marke -Code 0 -Text 'uebersprungen: Git-Sperre aktiv'
        exit 0
    }

    # --- Nachtrag: Phantomeintraege frueherer Uebernahmen -------------------
    # Beim Bau des eigenen Index bleibt der normale Index unberuehrt; fuer eine
    # NEU aufgenommene Datei fehlt ihm danach der Eintrag. 'git status' zeigt
    # sie dann gleichzeitig als geloescht (Index gegen HEAD) und als ungetrackt
    # - und ein 'git commit' einer anderen Sitzung OHNE Pfadangabe (es
    # committet den ganzen Index) wuerde sie wieder aus master loeschen. Diese
    # Reparatur holt genau die Pfade der letzten eigenen Uebernahme-Commits
    # nach: nachweisbare Herkunft, kein Raten, idempotent.
    $meinePfaede = @(& git log -5 --author=fremd@local --name-only --format= 2>$null |
                     Where-Object { $_ -and $_.Trim() } |
                     ForEach-Object { $_.Trim() } |
                     Select-Object -Unique)
    $nachgezogen = 0
    foreach ($pfad in $meinePfaede) {
        if ((& git ls-files -s -- $pfad 2>$null)) { continue }        # Index kennt den Pfad
        $kopfZeile = (& git ls-tree HEAD -- $pfad 2>$null)
        if (-not $kopfZeile) { continue }                            # HEAD kennt ihn auch nicht
        $teile = ($kopfZeile -split '\s+')
        if (IndexMitWiederholung @('update-index', '--add', '--cacheinfo', "$($teile[0]),$($teile[2]),$pfad")) { $nachgezogen++ }
    }
    if ($nachgezogen -gt 0) { Schreib "    Nachtrag: $nachgezogen Phantomeintrag/-eintraege aus frueheren Uebernahmen geradegezogen" }

    $jetzt  = Get-Date
    $ruhend = @()
    $inArbeit = @()

    foreach ($z in (git status --porcelain -uall)) {
        if ([string]::IsNullOrWhiteSpace($z)) { continue }
        $status = $z.Substring(0, 2)
        $pfad   = $z.Substring(3).Trim('"')
        if ($pfad -match ' -> ') { $pfad = ($pfad -split ' -> ')[1] }
        $voll = Join-Path $wurzel $pfad

        if (Test-EingebettetesGitRepo $voll $wurzel) { continue }

        if (Test-Path -LiteralPath $voll) {
            $alter = [int]($jetzt - (Get-Item -LiteralPath $voll).LastWriteTime).TotalMinutes
        } else {
            # Eine geloeschte Datei hat keine eigene Zeit mehr. Sie wie eine
            # ruhende Datei zu behandeln war falsch: eine Sitzung, die gerade
            # aufraeumt, haette ihre Loeschung sofort uebernommen bekommen.
            # Ersatzwahrheit ist der ORDNER - Windows schreibt beim Loeschen
            # dessen Zeit fort. Ist er frisch, ruht die Loeschung nicht.
            $ordner = Split-Path -Parent $voll
            if ($ordner -and (Test-Path -LiteralPath $ordner)) {
                $alter = [int]($jetzt - (Get-Item -LiteralPath $ordner).LastWriteTime).TotalMinutes
            } else {
                $alter = 9999
            }
        }

        if ($alter -ge $Minuten) { $ruhend += $pfad } else { $inArbeit += $pfad }
    }

    # --- T-218: Rueckschritt-Pfade aussortieren ---------------------------
    # Eine Datei, deren Arbeitsbaum-Stand ein RUECKSCHRITT gegenueber dem letzten
    # committeten Stand ist (Inhalt == aelterer Commit, HEAD neuer), ist keine
    # Fremdarbeit in Arbeit, sondern ein Rueckfall. Sie wird NICHT uebernommen,
    # sondern uebersprungen und gemeldet - sonst hebt der Lauf stillschweigend
    # eine Reparatur auf (gemessen 30.09.2026 am Gateway-Launcher).
    $rueckschritt = @()
    $neuRuhend = @()
    foreach ($pfad in $ruhend) {
        if (Test-Rueckschritt $pfad) { $rueckschritt += $pfad } else { $neuRuhend += $pfad }
    }
    $ruhend = $neuRuhend
    if ($rueckschritt) {
        Schreib "UEBERSPRUNGEN (Rueckschritt gegen HEAD, nicht uebernommen):"
        $rueckschritt | Sort-Object | ForEach-Object { Schreib "    $_" }
    }

    if (-not $ruhend) {
        Schreib "ENDE nichts zu uebernehmen - keine ruhende Fremdarbeit ($($inArbeit.Count) Datei(en) in Arbeit)"
        Melde-Ende -Marke $marke -Code 0 -Text 'nichts zu uebernehmen'
        exit 0
    }

    if ($Testlauf) {
        Schreib "TESTLAUF - es wuerde uebernommen ($($ruhend.Count)):"
        $ruhend | Sort-Object | ForEach-Object { Schreib "    $_" }
        Schreib "IN ARBEIT - bleibt liegen ($($inArbeit.Count)):"
        $inArbeit | Sort-Object | ForEach-Object { Schreib "    $_" }
        Melde-Ende -Marke $marke -Code 0 -Text "Testlauf: $($ruhend.Count) uebernehmbar"
        exit 0
    }

    $tip = (git rev-parse HEAD).Trim()
    if (-not $tip) { throw 'git rev-parse HEAD lieferte nichts' }

    $eigenerIndex = Join-Path $wurzel '.git\fremdarbeit.index'
    if (Test-Path $eigenerIndex) { Remove-Item $eigenerIndex -Force }
    $env:GIT_INDEX_FILE = $eigenerIndex

    git read-tree $tip
    if ($LASTEXITCODE -ne 0) { throw "git read-tree fehlgeschlagen (Exitcode $LASTEXITCODE)" }

    # Viele ruhende Pfade (z.B. 2044 Profil-Skill-Dateien) sprengen die
    # Windows-Kommandozeile (32k, WinError 206 'Dateiname zu lang', gemessen
    # 11.10.2026 01:20). Pfade stattdessen NUL-getrennt aus einer Datei lesen
    # (git add --pathspec-from-file, git >= 2.25).
    $pfadDatei = Join-Path $wurzel '.git\fremdarbeit-pfade.txt'
    [System.IO.File]::WriteAllText($pfadDatei, ($ruhend -join "`0"), (New-Object System.Text.UTF8Encoding($false)))
    git add --pathspec-from-file=$pfadDatei --pathspec-file-nul
    if ($LASTEXITCODE -ne 0) { throw "git add fehlgeschlagen (Exitcode $LASTEXITCODE)" }
    Remove-Item $pfadDatei -Force -ErrorAction SilentlyContinue

    # --- SYNTAX-TOR (11.10.2026) ------------------------------------------
    # Der Sweep committet rohen Code ("nicht von Hand geprueft"). Am 11.10.2026
    # brachte er zwei Defekte nach master, die die Handel-Suite rot machten
    # (getattr mit 4 Argumenten -> TypeError in leitstand_nautilus.status();
    # zweite Kraken-Node-Klasse gegen den read-only-Kontrakt). Syntaxfehler war
    # das nicht - deshalb prueft das Tor mehr als py_compile: Syntax UND
    # Argumentzahl bekannter Builtins.
    #
    # Nur bei .py im uebernommenen Satz. Befund in einer uebernommenen Datei =
    # Lauf abgebrochen, nichts committet, Arbeit bleibt im Baum liegen.
    # Der volle Testlauf laeuft hier absichtlich NICHT (~12 min, sprengt den
    # 30-Minuten-Takt) - den faehrt der Cron `syntax-tor-wache` separat.
    $pyUebernommen = @($ruhend | Where-Object { $_ -like '*.py' })
    if ($pyUebernommen.Count -gt 0) {
        $torSkript = Join-Path $wurzel 'Agenten\Hermes\scripts\syntax-tor-wache.py'
        $torPy = Join-Path $wurzel 'Agenten\Handel\scanner\.venv\Scripts\python.exe'
        if ((Test-Path $torSkript) -and (Test-Path $torPy)) {
            $torAus = (& $torPy $torSkript --nur-syntax 2>&1 | Out-String)
            $torCode = $LASTEXITCODE
            $torTreffer = @()
            foreach ($p in $pyUebernommen) {
                $muster = [regex]::Escape($p.Replace('/', '\'))
                foreach ($z in ($torAus -split "`n")) {
                    if ($z -match $muster) { $torTreffer += $z.Trim() }
                }
            }
            if ($torTreffer.Count -gt 0) {
                Schreib "ENDE abgebrochen - SYNTAX-TOR: $($torTreffer.Count) Befund(e) in uebernommenen Dateien"
                $torTreffer | ForEach-Object { Schreib "    $_" }
                Schreib "    Nichts committet - die Arbeit bleibt im Baum liegen."
                Schreib "    Volle Pruefung: Agenten\Hermes\scripts\syntax-tor-wache.py"
                Melde-Ende -Marke $marke -Code 0 -Text "Syntax-Tor: $($torTreffer.Count) Befund(e), nichts committet"
                exit 0
            }
            Schreib "    Syntax-Tor: $($pyUebernommen.Count) .py-Datei(en) geprueft, sauber"
        } else {
            Schreib "    WARNUNG Syntax-Tor nicht verfuegbar (Skript oder venv fehlt) - ohne Pruefung"
        }
    }

    $baum = (git write-tree).Trim()
    if (-not $baum) { throw 'git write-tree lieferte nichts' }

    # @() erzwingen: bei genau einem Pfad liefert die Pipeline sonst ein
    # Einzelobjekt ohne .Count (PS-5.1-Falle).
    $liste = @($ruhend | Sort-Object | ForEach-Object { '  - ' + $_ })
    if ($liste.Count -gt 40) {
        $weitere = $liste.Count - 40
        $liste = $liste[0..39] + @("  ... und $weitere weitere")
    }
    $nachricht = @(
        "Fremdarbeit uebernommen: $($ruhend.Count) ruhende Datei(en) beendeter Sitzungen"
        ""
        "Herkunft: Aenderungen, die nicht aus einer eigenen Sitzung stammen und"
        "laenger als $Minuten Minuten unberuehrt im Arbeitsbaum lagen. Automatisch"
        "uebernommen von der Routine fremdarbeit-einziehen - nicht von Hand geprueft."
        ""
        "Pfade:"
        $liste
    ) -join "`n"
    $msgDatei = Join-Path $wurzel '.git\fremdarbeit-msg.txt'
    # Ohne BOM: 'Set-Content -Encoding UTF8' schreibt unter PS 5.1 ein BOM, und
    # das landete als unsichtbares Zeichen in der Commit-Betreffzeile.
    [System.IO.File]::WriteAllText($msgDatei, $nachricht, (New-Object System.Text.UTF8Encoding($false)))

    $env:GIT_AUTHOR_NAME     = 'Andere Sitzung'
    $env:GIT_AUTHOR_EMAIL    = 'fremd@local'
    $env:GIT_COMMITTER_NAME  = 'Routine Fremdarbeit'
    $env:GIT_COMMITTER_EMAIL = 'routine@localhost'

    $neu = (git commit-tree $baum -p $tip -F $msgDatei).Trim()
    if (-not $neu) { throw 'git commit-tree lieferte nichts' }

    # Atomar: nur wenn master noch auf $tip steht. Sonst hat eine andere
    # Sitzung inzwischen committet und ihr Commit bleibt unangetastet.
    git update-ref refs/heads/master $neu $tip
    if ($LASTEXITCODE -ne 0) {
        Schreib "ENDE abgebrochen - master wurde waehrend des Laufs bewegt (update-ref verweigert), nichts geaendert"
        Melde-Ende -Marke $marke -Code 0 -Text 'master zwischenzeitlich bewegt'
        exit 0
    }

    # --- Phantomeintraege im ECHTEN Index geradeziehen ---------------------
    # Der eigene Index hat nur die uebernommenen Pfade angefasst; der normale
    # Index weiss von dem neuen Commit nichts. Fuer eine NEU aufgenommene Datei
    # fehlt ihm der Eintrag: 'git status' zeigt sie dann gleichzeitig als
    # geloescht (Index gegen HEAD) und als ungetrackt - und ein 'git commit'
    # einer anderen Sitzung OHNE Pfadangabe (es committet den ganzen Index)
    # wuerde sie wieder aus master loeschen. Hier wird je uebernommenem Pfad
    # der echte Index an HEAD angeglichen, und zwar nur dann, wenn dort noch
    # der ALTE Stand steht: eine frische Vormerkung einer anderen Sitzung
    # bleibt unangetastet.
    Remove-Item Env:\GIT_INDEX_FILE -ErrorAction SilentlyContinue

    $phantome = 0
    foreach ($pfad in $ruhend) {
        $indexZeile = (& git ls-files -s -- $pfad 2>$null)
        $altZeile   = (& git ls-tree $tip -- $pfad 2>$null)
        $neuZeile   = (& git ls-tree $neu -- $pfad 2>$null)
        $idxBlob = if ($indexZeile) { ($indexZeile -split '\s+')[1] } else { $null }
        $altBlob = if ($altZeile)   { ($altZeile   -split '\s+')[2] } else { $null }
        $neuBlob = if ($neuZeile)   { ($neuZeile   -split '\s+')[2] } else { $null }

        # Nur anfassen, wenn der Index seit dem Uebernahme-Commit unveraendert
        # ist (er steht noch auf dem Stand von $tip). Hat eine andere Sitzung
        # dort inzwischen selbst etwas vorgemerkt, ist IHRE Fassung juenger und
        # bleibt stehen.
        if ($idxBlob -ne $altBlob) { continue }

        if ($neuBlob) {
            if ($neuBlob -ne $idxBlob) {
                $mode = ($neuZeile -split '\s+')[0]
                if (IndexMitWiederholung @('update-index', '--add', '--cacheinfo', "$mode,$neuBlob,$pfad")) { $phantome++ }
            }
        } elseif ($idxBlob) {
            if (IndexMitWiederholung @('update-index', '--force-remove', '--', $pfad)) { $phantome++ }
        }
    }
    if ($phantome -gt 0) {
        Schreib "    Index geradegezogen: $phantome Phantomeintrag/-eintraege entfernt"
        $indexRest = (& git diff --cached --name-only 2>$null)
        if ($indexRest) { Schreib "    (fremd vorgemerkt bleibt: $((@($indexRest) -join ', ')))" }
    }

    Remove-Item $eigenerIndex -Force -ErrorAction SilentlyContinue
    Remove-Item $msgDatei -Force -ErrorAction SilentlyContinue

    $push = 'nicht gepusht'
    if (-not $NichtPushen) {
        # Der Rechner traegt einen GITHUB_TOKEN als Benutzervariable (93 Zeichen,
        # scope-arm: er darf in dieses Repo nicht schreiben). Git bevorzugt ihn
        # gegenueber dem verwalteten Zugang im Credential-Manager, deshalb endete
        # dieser Push mit "remote: Write access to repository not granted - 403"
        # (Lauf 28.09.2026 20:40), waehrend derselbe Push von Hand lief - dort
        # ist die Variable nicht gesetzt. Gemessen 29.09.2026: Push MIT dem
        # Registry-Token = exit 128/403, ohne ihn = erfolgreich. Darum hier nur
        # fuer diesen einen Aufruf raeumen; die Variable selbst bleibt stehen
        # (was sie sonst traegt, entscheidet Max - nicht diese Routine).
        $env:GITHUB_TOKEN = $null
        $env:GH_TOKEN = $null
        $pushAus = git push origin master 2>&1
        if ($LASTEXITCODE -eq 0) { $push = 'gepusht' } else { $push = "Push fehlgeschlagen: $pushAus" }
    }

    $s = [int]((Get-Date) - $start).TotalSeconds
    Schreib "ENDE ok - $($neu.Substring(0,7)) mit $($ruhend.Count) uebernommenen Datei(en), $push, $s s"
    Melde-Ende -Marke $marke -Code 0 -Text "$($ruhend.Count) Fremdarbeit-Datei(en) uebernommen ($push)"
} catch {
    "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
    Write-Output "ENDE FEHLER: $_"
    Melde-Ende -Marke $marke -Code 1 -Text "$_"
    exit 1
} finally {
    Remove-Item Env:\GIT_INDEX_FILE -ErrorAction SilentlyContinue
    Remove-Item Env:\GIT_AUTHOR_NAME -ErrorAction SilentlyContinue
    Remove-Item Env:\GIT_AUTHOR_EMAIL -ErrorAction SilentlyContinue
    Remove-Item Env:\GIT_COMMITTER_NAME -ErrorAction SilentlyContinue
    Remove-Item Env:\GIT_COMMITTER_EMAIL -ErrorAction SilentlyContinue
}
