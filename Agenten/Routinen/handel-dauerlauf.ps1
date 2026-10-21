# Startet den 24/7-Dauerlauf der Handelsspuren und haelt ihn am Leben.
# Von der Windows-Aufgabenplanung aufgerufen, Ausloeser "Bei Anmeldung" und
# zusaetzlich alle 30 Minuten (der zweite faengt einen Absturz auf, siehe
# unten).
#
# WICHTIG: Dieses Skript schaltet NICHTS scharf. dauerlauf.py laeuft ohne
# offenes Freigabefenster als Papierhandel, und ein Fenster oeffnet nur Max
# per Telegram - auf Anfrage, gedeckelt auf 24 Stunden. Aus einem Zeitplan
# heraus wird nie echtes Geld bewegt. Siehe Wissen/Handelsregeln.md, Punkt 3.
#
# Warum ein Waechter und kein Dienst: Die Kernel-Power-41-Abschaltungen aus
# Wissen/Hardware.md nehmen den Rechner ohne Vorwarnung mit. Ein Dienst waere
# danach zwar wieder da, aber die Aufgabenplanung ist das Werkzeug, das hier
# ohnehin schon alles andere startet - und sie ist sichtbar, wenn etwas
# klemmt. Der 30-Minuten-Ausloeser prueft nur, ob schon einer laeuft, und
# startet sonst neu; laeuft einer, endet das Skript sofort.
#
# RISIKOSTUFEN (-Risiko niedrig|mittel|hoch, seit 16.09.2026)
#   Der zweite Lauf derselben Spuren mit groesseren Betraegen - gedacht zum
#   DATENSAMMELN, nicht zum Handeln. Seine eigene Sperre heisst
#   dauerlauf.mittel.pid, sein Log dauerlauf.mittel.log; die Spuren schreiben
#   zustand.mittel.json und handelsjournal.mittel.csv und spiegeln die nach
#   Q:. Der Basislauf bleibt unberuehrt.
#
#   Warum eine EIGENE Sperre je Stufe: zwei Laeufe auf einer Sperrdatei
#   haetten sich gegenseitig "laeuft schon" gemeldet, und der zweite waere nie
#   gestartet.
#
#   Der Stufenlauf geht nie live und sendet nie nach Telegram (Begruendung in
#   Handel/dauerlauf.py). Ein zweiter Lauf kostet Rechenzeit und Netz: er ist
#   kein Ersatz fuer den Basislauf, sondern eine zweite Messreihe daneben.
#
# Aufruf:
#   .\handel-dauerlauf.ps1                 # Basis (Faktor 1.0)
#   .\handel-dauerlauf.ps1 -Risiko mittel  # zweiter Lauf, doppelte Betraege

param(
  [ValidateSet('niedrig', 'mittel', 'hoch')]
  [string]$Risiko = 'niedrig'
)

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$handel = Join-Path $wurzel 'Handel'
$py     = Join-Path $handel 'scanner\.venv\Scripts\python.exe'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

. (Join-Path $wurzel 'Bus\Ereignis.ps1')                                # neu

# Dateinamen-Zusatz der Stufe. Der Basislauf behaelt seine Namen (''), sonst
# wuerde jede geplante Aufgabe und jede Auswertung ploetzlich woanders suchen.
$suffix = if ($Risiko -eq 'niedrig') { '' } else { '.' + $Risiko }
$name   = 'handel-dauerlauf-letzter-lauf' + $suffix + '.log'
$log    = Join-Path $logs $name
$sperre = Join-Path $handel ('dauerlauf' + $suffix + '.pid')
# Meldet nur den Start-Vorgang selbst (dieses Skript startet und beendet sich
# sofort); der Dauerlauf laeuft danach als eigener Hintergrundprozess weiter
# und ist nicht Teil dieser Bus-Meldung.
$marke = Melde-Start -Wer ('routine/handel-dauerlauf' + $suffix) `
           -Log ('Agenten/Routinen/logs/' + $name)                     # neu

function Schreib($text) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $text" | Add-Content $log -Encoding UTF8
}

# Laeuft schon einer? Zwei Dauerlaeufe auf demselben Telegram-Token nehmen
# sich gegenseitig die Nachrichten weg - Telegram antwortet dem zweiten
# Abrufer mit 409. Deshalb hier abfangen und nicht erst dort. Geprueft wird
# die Sperre DIESER Stufe: der Basislauf und der Stufenlauf duerfen und sollen
# gleichzeitig laufen, sie schreiben in verschiedene Dateien.
# Die Sperrdatei traegt seit 29.09.2026 zwei Felder: "<PID> <Startzeit>". Das
# erste Feld ist weiterhin die nackte Nummer, damit eine Datei aus einem
# aelteren Lauf lesbar bleibt. Die Startzeit ist noetig, weil Windows PIDs
# wiederverwendet: traegt irgendein fremder Python-Prozess nach einem Neustart
# die alte Nummer, meldete diese Pruefung sonst fuer immer "laeuft bereits" -
# und der Waechter startete nie wieder. Im Zweifel wird gestartet; dauerlauf.py
# prueft die Sperre seit demselben Tag selbst und beendet sich, wenn er
# danebenlaeuft (sperre.py).
if (Test-Path $sperre) {
  # @() ist Pflicht: bei nur EINEM Feld gaebe die Pipeline einen String
  # zurueck, und $felder[0] waere dann dessen erstes ZEICHEN.
  $felder = @(((Get-Content $sperre -Raw -ErrorAction SilentlyContinue) -split '\s+') |
              Where-Object { $_ })
  $pid_alt = $felder[0]
  $lebt = Get-Process -Id $pid_alt -ErrorAction SilentlyContinue
  $passt = $true
  if ($lebt -and $felder.Count -gt 1) {
    try {
      $soll = [double]::Parse($felder[1], [Globalization.CultureInfo]::InvariantCulture)
      $ist = ([DateTimeOffset]$lebt.StartTime).ToUnixTimeMilliseconds() / 1000.0
      $passt = [Math]::Abs($ist - $soll) -le 2.0
    } catch { $passt = $true }   # unlesbare Zeit: wie frueher entscheiden
  }
  if ($lebt -and $passt -and $lebt.ProcessName -like 'python*') {
    Schreib "laeuft bereits (PID $pid_alt, Stufe $Risiko) - nichts zu tun"
    Melde-Ende -Marke $marke -Code 0 -Text 'laeuft bereits'                # neu
    exit 0
  }
  if ($lebt -and -not $passt) {
    Schreib "verwaiste Sperre (PID $pid_alt lebt, aber mit anderer Startzeit - Nummer wiederverwendet) - wird ersetzt"
  } else {
    Schreib "verwaiste Sperre (PID $pid_alt lebt nicht mehr) - wird ersetzt"
  }
  Remove-Item $sperre -Force -ErrorAction SilentlyContinue
}

# Spawn-Schutz (12.10.2026): liegen schon viele Handel-Python-Prozesse herum,
# startet kein weiterer Lauf. Mit dem Baum-Stopp in dauerlauf.py kommen Waisen
# nicht mehr vor; diese Grenze faengt einen Rueckfall ab, bevor er den
# Commit-Speicher aufbraucht.
$handelProzesse = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
                    Where-Object { $_.CommandLine -and $_.CommandLine.Contains('Handel\scanner\.venv\') }).Count
if ($handelProzesse -gt 40) {
  Schreib "ABBRUCH: $handelProzesse Handel-Python-Prozesse aktiv (Grenze 40) - kein Start"
  Melde-Ende -Marke $marke -Code 1 -Text "Spawn-Schutz: $handelProzesse Prozesse"
  exit 1
}

if (-not (Test-Path $py)) {
  Schreib "ENDE FEHLER: kein Python unter $py - '.venv' im scanner-Ordner neu anlegen (py -3.13 -m venv .venv)"
  Melde-Ende -Marke $marke -Code 1 -Text "kein Python unter $py"           # neu
  exit 1
}

Schreib "Start (Stufe $Risiko)"
# Umleitung seit 30.09.2026: ohne sie stirbt der Dauerlauf UNSICHTBAR. Am
# 30.09.2026 starben alle drei Stufen binnen Minuten mit Rueckgabe 143 (SIGTERM)
# und ohne eine einzige Zeile im eigenen Log - der Sterbegrund lag nur im
# verworfenen stderr des Kindes (T-193).
$kindlog = Join-Path $logs ('dauerlauf' + $suffix + '-kind.log')
$kinderr = Join-Path $logs ('dauerlauf' + $suffix + '-kind.err.log')
$p = Start-Process -FilePath $py `
                   -ArgumentList 'dauerlauf.py','--takt','15','--risiko',$Risiko `
                   -WorkingDirectory $handel `
                   -RedirectStandardOutput $kindlog `
                   -RedirectStandardError $kinderr `
                   -WindowStyle Hidden -PassThru
$p.Id | Set-Content $sperre -Encoding ASCII
Schreib "gestartet als PID $($p.Id), Takt 15 min, Stufe $Risiko"
Melde-Ende -Marke $marke -Code 0 -Text "gestartet als PID $($p.Id)"        # neu
exit 0
