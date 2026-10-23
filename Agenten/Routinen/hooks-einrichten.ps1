# Schaltet den Pre-commit-Hook des Besitz-Registers fuer diesen Klon ein.
$ErrorActionPreference = 'Continue'
$wurzel = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $PSScriptRoot '..\Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/hooks-einrichten'
$hook = Join-Path $wurzel '.githooks\pre-commit'

if (-not (Test-Path $hook)) {
  "FEHLER: $hook fehlt - Stand mit dem Hook holen (git pull)."
  Melde-Ende -Marke $marke -Code 1 -Text 'Hook fehlt'
  exit 1
}

git -C $wurzel config core.hooksPath .githooks
if ($LASTEXITCODE -ne 0) {
  "FEHLER: git config fehlgeschlagen."
  Melde-Ende -Marke $marke -Code 1 -Text 'git config fehlgeschlagen'
  exit 1
}

$ist = git -C $wurzel config --get core.hooksPath
"core.hooksPath = $ist"
"Hook aktiv fuer: $wurzel"
"Naechster Schritt: in der Sitzung BRAINFILES_BEREICH setzen, z. B. `$env:BRAINFILES_BEREICH = 'handel'"
Melde-Ende -Marke $marke -Code 0 -Text 'Hook aktiviert'
exit 0
