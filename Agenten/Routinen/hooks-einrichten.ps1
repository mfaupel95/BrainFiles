# Schaltet den Pre-commit-Hook des Besitz-Registers fuer DIESEN Klon ein.
#
# Setzt core.hooksPath auf .githooks (nur lokal, kein Administrator noetig,
# rueckgaengig mit: git config --unset core.hooksPath). Der Hook
# (.githooks\pre-commit) ruft Agenten\Werkzeuge\bereiche.py --staged.
#
# Wirkung: wer sich per Umgebungsvariable BRAINFILES_BEREICH=handel|bot|wissen
# ausweist, kann nicht in Bereiche eines anderen Besitzers committen. Ohne die
# Variable wird nichts blockiert (Max von Hand, Routinen).
#
# Aufruf:  powershell -ExecutionPolicy Bypass -File Agenten\Routinen\hooks-einrichten.ps1
# Die Variable selbst setzt dieses Skript NICHT: sie gehoert in den Start der
# jeweiligen Sitzung (Handels-, Bot-, Wissens-Sitzung), nicht global in den
# Benutzer - sonst waere jeder Commit dieses Benutzers an einen Bereich gebunden.

$ErrorActionPreference = 'Continue'
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent   # Repo-Wurzel
$hook = Join-Path $wurzel '.githooks\pre-commit'

if (-not (Test-Path $hook)) {
  "FEHLER: $hook fehlt - Stand mit dem Hook holen (git pull)."
  exit 1
}

git -C $wurzel config core.hooksPath .githooks
if ($LASTEXITCODE -ne 0) { "FEHLER: git config fehlgeschlagen."; exit 1 }

$ist = git -C $wurzel config --get core.hooksPath
"core.hooksPath = $ist"
"Hook aktiv fuer: $wurzel"
"Naechster Schritt: in der Sitzung BRAINFILES_BEREICH setzen, z. B. `$env:BRAINFILES_BEREICH = 'handel'"
exit 0
