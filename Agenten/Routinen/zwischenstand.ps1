# Stuendlicher Zwischenstand der Textebene. Von der Aufgabenplanung aufgerufen.
#
# Zweck: Git schuetzt nur, was committet ist. Zwischen dem Schreiben einer Datei
# und ihrem Commit ist die Arbeit nirgends gesichert. Bei mehreren gleichzeitigen
# Sitzungen (Claude-Chats, Hermes) kann eine Sitzung die uncommittete Arbeit
# einer anderen ueberschreiben - siehe Wissen/Schutzregeln.md, Abschnitt
# "Mehrere Sitzungen gleichzeitig". Dieser Lauf legt einmal am Tag einen lokalen
# Wiederherstellungspunkt der gesamten Textebene auf dem Branch "zwischenstand"
# an.
#
# Lief bis 02.09.2026 stuendlich, im Umfeld des System-Umzugs auf taeglich
# 20:00 reduziert, am 29.09.2026 wieder auf stuendlich gestellt - der Umzug
# ist abgeschlossen, der Grund fuer die Reduzierung entfaellt. Im schlimmsten
# Fall ist jetzt eine Stunde uncommitteter Arbeit ungesichert statt eines
# Tages - eigenes Committen nach jedem Arbeitsschritt bleibt trotzdem Pflicht.
#
# Das Skript kann per Konstruktion nichts kaputtmachen:
#   - Eigener Index ueber GIT_INDEX_FILE. Der normale Staging-Bereich bleibt
#     unberuehrt: eine Sitzung, die gerade selektiv "git add" gemacht hat,
#     verliert ihre Vormerkung nicht.
#   - Commit ueber "git commit-tree" auf den separaten Branch "zwischenstand".
#     HEAD, master und der Arbeitsbaum werden nie angefasst.
#   - Kein checkout, kein reset, kein stash, kein clean. Es wird ausschliesslich
#     geschrieben, nie verworfen.
#   - .gitignore ist eine Whitelist: Zugaenge.md, .env, .pfx, .kdbx usw. bleiben
#     auch hier draussen.
#
# Autor der Commits ist bewusst "Routine Zwischenstand", nicht Max und nicht ein
# Agent - die Historie soll nicht behaupten, jemand haette diese Arbeit getan.
#
# Eine Datei aus einem Zwischenstand zurueckholen:
#   git log --oneline zwischenstand
#   git checkout <commit> -- <pfad>
#
# Branch komplett aufraeumen (er waechst mit jedem Lauf):
#   git update-ref -d refs/heads/zwischenstand

param([switch]$Testlauf)

$ErrorActionPreference = 'Stop'
# Zwei Ebenen ueber diesem Skript liegt die Wurzel BrainFiles\ mit dem einzigen
# .git (Agenten\Routinen\ -> Agenten\ -> BrainFiles\). Seit der Ordnertrennung
# vom 30.08.2026 ist Agenten\ kein Git-Repository mehr - eine Ebene reichte bis
# dahin.
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
. (Join-Path $wurzel 'Agenten\Bus\Ereignis.ps1')                         # neu

$log = Join-Path $logs 'zwischenstand-letzter-lauf.log'
$start = Get-Date
$marke = Melde-Start -Wer 'routine/zwischenstand' `
           -Log 'Agenten/Routinen/logs/zwischenstand-letzter-lauf.log'  # neu

function Schreib($text) {
  $text | Add-Content $log -Encoding UTF8
  Write-Output $text
}

"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

try {
  Set-Location $wurzel
  if (-not (Test-Path (Join-Path $wurzel '.git'))) { throw "kein Git-Repository in $wurzel" }

  # Eigener Index - der normale Staging-Bereich bleibt unangetastet
  $eigenerIndex = Join-Path $wurzel '.git\zwischenstand.index'
  if (Test-Path $eigenerIndex) { Remove-Item $eigenerIndex -Force }
  $env:GIT_INDEX_FILE = $eigenerIndex

  # git schreibt Warnungen nach stderr (CRLF-Umwandlung, "adding embedded git
  # repository" bei einem Fremd-Repo im Baum). Unter $ErrorActionPreference=Stop
  # macht schon eine solche Warnung den Lauf zunichte. Fuer den einen git-Aufruf
  # daher auf Continue schalten und die Ausgabe in eine Variable fangen; echte
  # Fehler bleiben ueber den Exitcode sichtbar.
  $eap = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  # Der Index ist hier FRISCH (GIT_INDEX_FILE zeigt auf eine neu angelegte
  # Datei). Ohne den folgenden Schritt kennt er den versionierten Bestand
  # nicht - und git add -A nimmt dann jeden Pfad NICHT auf, den .gitignore
  # verdeckt, obwohl er in master liegt (z.B. Agenten/Hermes/config.yaml,
  # Agenten/Bus/.gitignore). Am 30.09.2026 fehlten so 338 Dateien im
  # Zwischenstand, waehrend der Lauf 'ENDE ok' meldete. read-tree legt den
  # committeten Baum in den Index; danach ergaenzt add -A nur noch Neues.
  # Gegenprobe: git diff --name-status master zwischenstand darf keine
  # D-Ausgaben mehr zeigen.
  git read-tree HEAD
  if ($LASTEXITCODE -ne 0) { throw "git read-tree fehlgeschlagen (Exitcode $LASTEXITCODE)" }

  $addAusgabe = git add -A 2>&1
  $ErrorActionPreference = $eap
  if ($LASTEXITCODE -ne 0) { throw "git add fehlgeschlagen (Exitcode $LASTEXITCODE): $addAusgabe" }

  $baum = (git write-tree).Trim()
  if (-not $baum) { throw "git write-tree lieferte nichts" }

  # Elter: bisheriger Zwischenstand, sonst der aktuelle HEAD
  $elter = (git rev-parse --verify --quiet refs/heads/zwischenstand)
  if (-not $elter) { $elter = (git rev-parse HEAD) }
  $elter = "$elter".Trim()

  # Nichts zu tun, wenn der Baum sich seit dem letzten Zwischenstand nicht
  # unterscheidet. Spart leere Commits bei jeder stillen Stunde.
  $elternBaum = (git rev-parse "$elter^{tree}").Trim()
  if ($baum -eq $elternBaum) {
    Schreib "ENDE unveraendert - kein Zwischenstand noetig"
    Remove-Item $eigenerIndex -Force -ErrorAction SilentlyContinue
    Melde-Ende -Marke $marke -Code 0 -Text 'unveraendert'                # neu
    exit 0
  }

  $abweichend = (git status --porcelain | Measure-Object -Line).Lines
  $nachricht  = "Zwischenstand $($start.ToString('yyyy-MM-dd HH:mm')) - $abweichend Datei(en) abweichend von master"

  if ($Testlauf) {
    Schreib "TESTLAUF - es wuerde committet werden:"
    Schreib "  Nachricht : $nachricht"
    Schreib "  Baum      : $baum"
    Schreib "  Elter     : $elter"
    Schreib "  Betroffen :"
    git status --porcelain | ForEach-Object { Schreib "    $_" }
    Remove-Item $eigenerIndex -Force -ErrorAction SilentlyContinue
    Melde-Ende -Marke $marke -Code 0 -Text 'Testlauf'                    # neu
    exit 0
  }

  $env:GIT_AUTHOR_NAME     = 'Routine Zwischenstand'
  $env:GIT_AUTHOR_EMAIL    = 'routine@localhost'
  $env:GIT_COMMITTER_NAME  = 'Routine Zwischenstand'
  $env:GIT_COMMITTER_EMAIL = 'routine@localhost'

  $neu = (git commit-tree $baum -p $elter -m $nachricht).Trim()
  if (-not $neu) { throw "git commit-tree lieferte nichts" }

  git update-ref refs/heads/zwischenstand $neu
  if ($LASTEXITCODE -ne 0) { throw "git update-ref fehlgeschlagen (Exitcode $LASTEXITCODE)" }

  Remove-Item $eigenerIndex -Force -ErrorAction SilentlyContinue

  $s = [int]((Get-Date) - $start).TotalSeconds
  Schreib "ENDE ok - $($neu.Substring(0,7)) mit $abweichend abweichenden Datei(en) nach $s s"
  Melde-Ende -Marke $marke -Code 0                                       # neu
} catch {
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Write-Output "ENDE FEHLER: $_"
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                            # neu
  exit 1
} finally {
  Remove-Item Env:\GIT_INDEX_FILE -ErrorAction SilentlyContinue
}
