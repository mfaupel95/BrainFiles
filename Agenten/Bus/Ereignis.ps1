# Erzeugerseite fuer die Routinen. Wird mit Punkt eingebunden:
#
#   . (Join-Path $wurzel 'Bus\Ereignis.ps1')
#   $marke = Melde-Start -Wer 'routine/sicherung' -Log $relativerLogPfad
#   ... eigentliche Arbeit ...
#   Melde-Ende -Marke $marke -Code $code
#
# Die Regel ueber allen anderen: ein toter Bus darf niemals einen Lauf
# abbrechen. Deshalb steht in jeder Funktion ein try/catch um alles, und
# $ErrorActionPreference wird waehrenddessen auf 'Continue' gesetzt - sonst
# reisst ein 'Stop' aus dem aufrufenden Skript den Melder mit hinein.
#
# Pfade sind relativ zu diesem Skript. BUS_JOURNAL und BUS_PORT gibt es nur
# fuer den Test.

$BusWurzel = $PSScriptRoot

function Get-BusPort {
  if ($env:BUS_PORT) { return [int]$env:BUS_PORT }
  try {
    return [int]((Get-Content (Join-Path $BusWurzel 'bus.json') -Raw |
                  ConvertFrom-Json).port)
  } catch { return 0 }
}

function Get-BusJournal {
  if ($env:BUS_JOURNAL) { return $env:BUS_JOURNAL }
  return (Join-Path $BusWurzel 'journal')
}

function Send-BusEreignis {
  param([hashtable]$Ereignis)
  $alt = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $roh  = $Ereignis | ConvertTo-Json -Compress -Depth 4
    $port = Get-BusPort
    if ($port -gt 0) {
      try {
        # -ErrorAction Stop: macht den Cmdlet-Fehler terminierend, sonst
        # greift dieses catch gar nicht (siehe Kommentar unten).
        Invoke-RestMethod -Uri "http://127.0.0.1:$port/ereignis" -Method Post `
          -Body $roh -ContentType 'application/json' -TimeoutSec 1 -ErrorAction Stop | Out-Null
        return
      } catch { }
    }
    try {
      # Auch hier -ErrorAction Stop noetig: $ErrorActionPreference = 'Continue'
      # (oben) schuetzt nur den *Aufrufer* vor einem 'Stop', der aus diesem
      # Skript herausreisst. Ohne -ErrorAction Stop an den Cmdlets selbst
      # waeren ihre Fehler nicht-terminierend - sie wuerden nur ausgegeben
      # (stderr) statt das catch auszuloesen, und genau das soll hier
      # verhindert werden.
      $ordner = Get-BusJournal
      if (-not (Test-Path $ordner)) {
        New-Item -ItemType Directory -Path $ordner -Force -ErrorAction Stop | Out-Null
      }
      $datei = Join-Path $ordner ((Get-Date).ToString('yyyy-MM-dd') + '.jsonl')
      Add-Content -Path $datei -Value $roh -Encoding UTF8 -ErrorAction Stop
    } catch { }
  } catch { } finally { $ErrorActionPreference = $alt }
}

function New-BusEreignis {
  param([string]$Wer, [string]$Was, $Code, $Dauer, [string]$Text, $Log)
  return @{
    id      = [guid]::NewGuid().ToString('N')
    zeit    = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
    wer     = $Wer
    was     = $Was
    code    = $Code
    dauer_s = $Dauer
    text    = $Text
    log     = $Log
  }
}

function Melde-Start {
  # $Log bewusst ohne [string]-Typangabe: sonst macht PowerShell ein
  # fehlendes -Log zu "" statt $null, und journal.py-seitige Leser
  # (Teilprojekt 2) muessten "" und null als denselben Fall behandeln.
  param([Parameter(Mandatory)][string]$Wer, $Log = $null)
  Send-BusEreignis (New-BusEreignis -Wer $Wer -Was 'start' -Code $null `
                    -Dauer $null -Text '' -Log $Log)
  return [pscustomobject]@{ Wer = $Wer; Start = Get-Date; Log = $Log }
}

function Melde-Ende {
  param([Parameter(Mandatory)]$Marke, [int]$Code = 0, [string]$Text = '')
  $s = [int]((Get-Date) - $Marke.Start).TotalSeconds
  Send-BusEreignis (New-BusEreignis -Wer $Marke.Wer -Was 'ende' -Code $Code `
                    -Dauer $s -Text $Text -Log $Marke.Log)
}

function Melde-Hinweis {
  param([Parameter(Mandatory)][string]$Wer,
        [Parameter(Mandatory)][string]$Text)
  Send-BusEreignis (New-BusEreignis -Wer $Wer -Was 'hinweis' -Code $null `
                    -Dauer $null -Text $Text -Log $null)
}
