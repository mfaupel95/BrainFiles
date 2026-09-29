# Faehrt alle Testsammlungen im Handel-Baum und meldet, wenn eine Spur
# schlechter dasteht als beim letzten bestaetigten Stand.
#
# Warum es diese Routine gibt: bis zum 29.09.2026 hat NIEMAND die Tests
# regelmaessig gefahren. Es lag zwar ein GitHub-Workflow im Baum, der war aber
# toter Text - am falschen Ort, nicht versioniert, auf Zweignamen, die es hier
# nicht gibt, und jeder Schritt auf "continue-on-error". Er konnte gar nicht
# rot werden. Er wurde am selben Tag entfernt; diese Datei ist sein Ersatz.
#
# Die eigentliche Arbeit macht Handel/testlauf.py. Hier steht nur, was
# drumherum noetig ist: Log, Bus-Meldung, Exit-Code.
#
# NACHTS fahren. Die Sammlung im Wurzelverzeichnis braucht allein ueber fuenf
# Minuten, der ganze Lauf deutlich laenger - tagsueber nimmt er dem Dauerlauf
# die Rechenzeit weg.
#
# Rot wird der Lauf nur bei einer VERSCHLECHTERUNG gegenueber
# Handel/testlauf_basis.json, nicht bei absoluter Roete. Sonst waere er ab dem
# ersten Tag dauerrot und damit wertlos. Wer eine Spur repariert hat, zieht die
# Basislinie nach:  python testlauf.py --basis-schreiben
#
# Aufruf:
#   .\handel-tests.ps1

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$handel = Join-Path $wurzel 'Handel'
$py     = Join-Path $handel '.venv\Scripts\python.exe'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')

$name = 'handel-tests-letzter-lauf.log'
$log  = Join-Path $logs $name
$marke = Melde-Start -Wer 'routine/handel-tests' `
           -Log ('Agenten/Routinen/logs/' + $name)

function Schreib($text) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $text" | Add-Content $log -Encoding UTF8
}

# Das Log traegt immer nur den LETZTEN Lauf. Eine Testausgabe ueber 34 Spuren
# ist lang; wuerde angehaengt, waere die Datei nach einem Monat unlesbar und
# im Quellbaum stuende wieder ein Log ohne Rotation (siehe BEFUND-hygiene).
Set-Content $log -Value '' -Encoding UTF8

if (-not (Test-Path $py)) {
  Schreib "ENDE FEHLER: kein Python unter $py"
  Melde-Ende -Marke $marke -Code 1 -Text "kein Python unter $py"
  exit 1
}

Schreib 'Start'
# 2>&1 fuehrt stderr in die Pipeline. Mit ErrorActionPreference='Stop' waere
# das ein Abbruch - deshalb hier auf Continue, der Exit-Code entscheidet.
$ErrorActionPreference = 'Continue'
$ausgabe = & $py (Join-Path $handel 'testlauf.py') 2>&1
$code = $LASTEXITCODE
$ErrorActionPreference = 'Stop'

$ausgabe | Out-String | Add-Content $log -Encoding UTF8

if ($code -eq 0) {
  Schreib 'ENDE OK: kein Rueckschritt gegenueber der Basislinie'
  Melde-Ende -Marke $marke -Code 0 -Text 'kein Rueckschritt'
  exit 0
}

# Die SCHLECHTER-Zeilen in die Bus-Meldung heben: wer die Warnung liest, soll
# nicht erst das Log oeffnen muessen, um zu sehen, welche Spur gekippt ist.
$schlecht = @($ausgabe | Select-String -Pattern '^SCHLECHTER' |
              ForEach-Object { $_.ToString().Trim() })
$text = if ($schlecht) { $schlecht -join '; ' } else { "Lauf endete mit Code $code" }
Schreib "ENDE FEHLER: $text"
Melde-Ende -Marke $marke -Code $code -Text $text
exit $code
