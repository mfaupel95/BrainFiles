# Stuendlicher Zwischenstand der Textebene. Von der Aufgabenplanung aufgerufen.
#
# Zweck: Git schuetzt nur, was committet ist. Zwischen dem Schreiben einer Datei
# und ihrem Commit ist die Arbeit nirgends gesichert - auch die Sicherung um
# 20:00 haelt dann nur den ueberschriebenen Stand. Bei mehreren gleichzeitigen
# Sitzungen (Claude-Chats, Hermes) ist dieses Fenster das eigentliche Risiko.
# Siehe Wissen/Schutzregeln.md, Abschnitt "Mehrere Sitzungen gleichzeitig".
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
$wurzel = Split-Path $PSScriptRoot -Parent
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'zwischenstand-letzter-lauf.log'
$start = Get-Date

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

  git add -A 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "git add fehlgeschlagen (Exitcode $LASTEXITCODE)" }

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
} catch {
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  Write-Output "ENDE FEHLER: $_"
  exit 1
} finally {
  Remove-Item Env:\GIT_INDEX_FILE -ErrorAction SilentlyContinue
}
