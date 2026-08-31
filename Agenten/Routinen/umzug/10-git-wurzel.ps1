# Phase 1 -- Die Git-Wurzel von MaxHirn/ nach BrainFiles/ hochziehen.
#
# Zuerst von allen Phasen, damit jeder spaetere Move als Umbenennung in der
# Historie steht statt als "geloescht + neu angelegt". Nach diesem Schritt
# lautet der Pfad jeder bisher versionierten Datei  MaxHirn/<alt>  -- eine
# reine Praefix-Verschiebung, deshalb laesst sich das Staging Datei fuer Datei
# ausrechnen und muss nicht geraten werden.
#
# Schutzregel 1: kein 'git add -A', kein 'git add .'. Jede Datei wird namentlich
# hinzugefuegt; die Loeschungen der alten Pfade holt 'git add -u', das
# ausschliesslich bereits versionierte Dateien anfasst.
#
#   .\10-git-wurzel.ps1            Trockenlauf
#   .\10-git-wurzel.ps1 -Echt      wirklich

param([switch]$Echt)
$DryRun = -not $Echt

. "$PSScriptRoot\gemeinsam.ps1"
$wurzel  = Get-Wurzel
$vault   = Join-Path $wurzel 'MaxHirn'

Schritt "Wurzel: $wurzel"
Schritt ''

# --- 0. Vorbedingungen -----------------------------------------------------
# Der Schritt ist zweigeteilt (Ordner verschieben / Staging), und ein
# abgebrochener erster Teil darf den zweiten nicht blockieren. Massgeblich ist
# daher nicht, wo .git liegt, sondern ob die neue .gitignore schon steht.
if (-not (Test-Path (Join-Path $vault '.git')) -and -not (Test-Path (Join-Path $wurzel '.git'))) {
    throw "Weder $vault\.git noch $wurzel\.git gefunden."
}
$repoWurzel = git -C $wurzel rev-parse --show-toplevel
Schritt "Repo-Wurzel laut Git: $repoWurzel"

# Die Sauberkeitspruefung ergibt nur VOR dem Verschieben einen Sinn. Danach
# meldet Git zwangslaeufig 117 Loeschungen und ebenso viele Unbekannte - das
# ist der Umzug selbst, nicht fremde Arbeit.
# Massgeblich ist, was Git selbst als Wurzel meldet - nicht, ob noch eine leere
# .git-Huelle im alten Ordner steht.
$vorDemMove = ($repoWurzel -replace '/','\') -ieq $vault
$offen = if ($vorDemMove) { @(git -C $wurzel status --porcelain) } else { @() }
if (-not $vorDemMove) { Schritt '.git liegt bereits oben - Sauberkeitspruefung entfaellt.' 'warn' }
if ($offen) {
    Schritt 'Der Arbeitsbaum ist nicht sauber. Nach Schutzregel 1 erst sichern:' 'fehler'
    $offen | ForEach-Object { Schritt "  $_" 'fehler' }
    Bilanz 'abgebrochen - uncommittete Aenderungen im Arbeitsbaum.' -Erfolg:$false
    return
}
# Die Liste der versionierten Dateien stammt aus dem Index und traegt noch die
# alten, MaxHirn-relativen Pfade - genau die brauchen wir zum Umrechnen.
$dateien = @(git -C $wurzel ls-files)
Schritt "$($dateien.Count) versionierte Dateien im Index (alte Pfade)."

if ($DryRun) {
    Schritt ''
    Schritt '[Probe] .git, .gitignore, .gitattributes -> BrainFiles\'
    Schritt "[Probe] .gitignore wird durch gitignore-neu.txt ersetzt (Whitelist mit MaxHirn/-Praefix)"
    Schritt "[Probe] $($dateien.Count) Dateien wuerden namentlich als MaxHirn\<alt> hinzugefuegt"
    Bilanz "Probe in Ordnung: $($dateien.Count) Umbenennungen vorbereitet."
    return
}

# --- 1. Die drei Steuerdateien hoch ----------------------------------------
if ((Test-Path (Join-Path $vault '.git')) -and
    -not (Get-ChildItem (Join-Path $vault '.git') -Recurse -Force -EA SilentlyContinue)) {
    # Move-Item laesst bei versteckten Ordnern gern die leere Huelle stehen.
    Remove-Item -LiteralPath (Join-Path $vault '.git') -Force -Recurse
    Schritt 'leere .git-Huelle in MaxHirn entfernt' 'ok'
}
Verschiebe -Von (Join-Path $vault '.git')           -Nach (Join-Path $wurzel '.git')
Verschiebe -Von (Join-Path $vault '.gitattributes') -Nach (Join-Path $wurzel '.gitattributes')
if (Test-Path (Join-Path $vault '.gitignore')) { Remove-Item -LiteralPath (Join-Path $vault '.gitignore') -Force }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'gitignore-neu.txt') -Destination (Join-Path $wurzel '.gitignore')
Schritt 'neue .gitignore (Whitelist mit MaxHirn/-Praefix) gesetzt' 'ok'

# --- 2. Staging: Loeschungen und neue Pfade, beides namentlich --------------
Push-Location $wurzel
try {
    # -u fasst ausschliesslich bereits versionierte Dateien an. Es kann nichts
    # Fremdes einsammeln - genau das trennt es von 'git add -A'.
    git add -u -- . 2>&1 | Out-Null

    $zugefuegt = 0
    foreach ($d in $dateien) {
        $neu = "MaxHirn/$d"
        if (Test-Path (Join-Path $wurzel $neu)) {
            git add --force -- $neu 2>&1 | Out-Null
            $zugefuegt++
        } else {
            Schritt "  fehlt am neuen Ort: $neu" 'warn'
        }
    }
    Schritt "$zugefuegt Dateien namentlich hinzugefuegt" 'ok'

    # --- 3. Gegenprobe: nur Umbenennungen, keine Loeschung ------------------
    $status = git diff --cached -M --name-status
    $r = ($status | Where-Object { $_ -match '^R' }).Count
    $d = ($status | Where-Object { $_ -match '^D' }).Count
    $a = ($status | Where-Object { $_ -match '^A' }).Count
    Schritt ''
    Schritt "vorgemerkt: $r Umbenennungen, $a Neuzugaenge, $d Loeschungen"
    $unversioniert = (git status --porcelain | Where-Object { $_ -match '^\?\?' }).Count
    Schritt "unversioniert sichtbar (sollte klein sein): $unversioniert"

    Bilanz "$r Umbenennungen, $d Loeschungen, $a Neuzugaenge -- bereit zum Commit." -Erfolg:($d -eq 0)
} finally { Pop-Location }

Protokoll-Schreiben '10-git-wurzel' | Out-Null
