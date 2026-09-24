**Wer ist schuld: unser Code, der Schluessel oder die Boerse?**

Diagnose, wenn eine Live-Sperre oder ein Skript ploetzlich einen Zugangsfehler meldet
(Kraken Spot `EGeneral:Permission denied`, Kraken Futures `authenticationError`, OKX
`50119`/`50101`). Ziel: in wenigen Schritten entscheiden, welcher der drei Teile die
Ursache ist — und nur diesen anfassen. Reihenfolge einhalten, beim ersten klaren
Befund aufhoeren.

## 1. Privaten Aufruf NIE von Hand signieren

Kraken vergleicht die nonce gegen den HOECHSTEN Wert, den es je fuer diesen Schluessel
gesehen hat. Die Hausmodule holen die nonce aus dem gemeinsamen Pool
(`kraken/.kraken_nonce`), ein selbstgebauter Aufruf (`urllib` + HMAC, `time.time()*1000`)
liegt darunter — und Kraken antwortet dann NICHT mit einem nonce-Fehler, sondern mit
`EGeneral:Permission denied` bzw. `authenticationError`. Folge: die Handsonde "beweist"
einen kaputten Schluessel, waehrend die Spuren im selben Moment einwandfrei handeln.

Deshalb: Zugang immer ueber das Hausmodul pruefen (`kraken/kraken.py`:
`guthaben`, `_roh_privat`; `nautilus_kraken/kraken_futures.py`: `guthaben`, `_roh`).
Ein Ergebnis aus einem selbstsignierten Aufruf ist als Befund UNBRAUCHBAR, auch wenn
es plausibel aussieht.

## 2. Eine unabhaengige Umsetzung als Schiedsrichter

Bevor irgendwo "unser Code ist kaputt" steht: denselben Aufruf mit einem fremden
Programm fahren. Die offizielle kraken-cli kann Futures (`kraken futures accounts`,
`positions`, `open-orders`) und Spot; sie liest ihre Zugangsdaten aus eigenen
Umgebungsnamen (Futures: `KRAKEN_FUTURES_API_KEY`/`_SECRET` — Plural; Spot:
`KRAKEN_API_KEY`/`_SECRET`), die man fuer den Kindprozess aus den Hausnamen setzt,
ohne die Werte je auszugeben.

**Gemessen 25.09.2026 - die Namen unterscheiden sich in EINEM Buchstaben:**
gesetzt sind `KRAKEN_FUTURE_API_KEY`/`_SECRET` (Einzahl, 56/88 Zeichen; so liest
unser `nautilus_kraken/kraken_futures.py`), die Mehrzahl-Namen der kraken-cli
(`KRAKEN_FUTURES_API_KEY`/`_SECRET`) FEHLEN. Der Schiedsrichter kann also mit
unserer Umgebung gar nicht arbeiten: er meldet `Invalid key`, obwohl der Zugang
lebt. Wer ihn fahren will, setzt die Mehrzahl-Namen fuer den Kindprozess aus den
Hausnamen (Muster `Agenten/Werkzeuge/kraken.ps1`) - Werte nie ausgeben. Erst
DANACH ist sein Urteil ein Urteil.

- Beide Umsetzungen scheitern gleich → es ist NICHT die eigene Signatur. Weiter mit 4.
- Nur unsere scheitert → eigener Fehler; weiter im eigenen Code.

## 3. Erreichbarkeit und Uhr — billig und ohne Schluessel

- `https://api.kraken.com/0/public/SystemStatus` und `/0/public/Time`
- Futures-Ticker (`/derivatives/api/v3/tickers?symbol=PF_XBTUSD`) antwortet auch ohne
  Zugangsdaten — "Boerse erreichbar" ist damit in einem Aufruf belegt.
- Host-Uhr gegen die Boersenuhr stellen (`Get-Date` vs `/0/public/Time`, Differenz in
  Sekunden). Kraken vergleicht die nonce nicht gegen die Uhr, aber eine schiefe Uhr
  vergiftet jede spaetere Aussage (und `date` im Terminal-Werkzeug ist der Container,
  nicht der Rechner).

## 4. Ist der Schluessel unveraendert?

Ein Schluessel, der vor zwanzig Minuten noch geantwortet hat und jetzt fuer JEDE nonce
abgelehnt wird, wurde meist auf der Boersenseite geaendert (geloescht, deaktiviert,
Rechte oder IP-Beschraenkung). Belegen statt vermuten: in der
PowerShell-History (`ConsoleHost_history.txt`) steht die letzte `setx`-Zeile, also der
Wert, mit dem es funktioniert hat. Die Registry-Werte dagegen HASHEN (oder nur die
Laenge vergleichen) und das Ergebnis ausgeben: gleich oder anders, nie der Wert.

Gemessenes Muster: Werte identisch, Uhr sauber, Boerse online, jeder
Genauigkeitsgrad der nonce abgelehnt → die Ursache liegt beim Konto/Schluessel und ist
die EINE Sache, die der Nutzer im Portal erledigen muss. Dann NICHT am eigenen
funktionierenden Orderweg "reparieren".

## 5. Nonce und Format systematisch ausschliessen

Wer die nonce in Verdacht hat, geht die Groessenordnungen durch — je ein Aufruf mit dem
Wert aus Millisekunden, Mikrosekunden, Nanosekunden und zwei klar zu grossen Zahlen
(z. B. 1,8e18 und 9e18). Wird JEDER Wert abgelehnt, ist die nonce erwiesen unschuldig;
dann nicht weiter in dieser Richtung suchen (der Verdacht auf einen "vergifteten"
Zaehler ist nur richtig, wenn ein hoeherer Wert ploetzlich durchgeht).

## 6. Nachweis ohne Klartext — und die PowerShell-Falle

- Nur die EXISTENZ und Laenge messen: `[Environment]::GetEnvironmentVariable('NAME','User')`
  und davon `Length` oder einen Hash ausgeben. `reg query HKCU\Environment` und
  `Get-ItemProperty HKCU:\Environment` geben die WERTE im Klartext aus — Passphrasen
  landen damit im Sitzungsprotokoll. (HKCU loest in einer MCP-PowerShell ausserdem auf
  einen anderen Benutzerkontext auf; massgeblich ist `GetEnvironmentVariable`.)
- **Nie eine PowerShell-Hilfsfunktion mit EINEM Buchstaben benennen.** `function H`
  kollidiert mit dem Alias `h` (= `Get-History`); der Aufruf scheitert und PowerShell
  schreibt den uebergebenen WERT in die Fehlermeldung — aus einer Hash-Pruefung wird so
eine Klartextausgabe aller Schluessel. Mehrbuchstabige Namen (`Get-HashWert`).
- Rechte statt Vermutungen: OKX beantwortet `/api/v5/account/config` mit dem Feld `perm`
  und dem Feld `ip`; OKX unterscheidet ausserdem den falschen Host (50101/50119) vom
  toten Schluessel. Kraken Spot und Kraken Futures sind getrennte Dienste mit getrennten
  Schluesselpaaren — der Spot-Schluessel oeffnet den Futures-Host nie.

## 7. Eine Fehlermeldung darf keinen anderen Namen nennen als der Code liest

- `kraken/kraken.py` warf `KRAKEN_API_KEY / KRAKEN_API_SECRET fehlen`, waehrend
  die Zeilen darueber `KRAKEN_SPOT_API_KEY`/`KRAKEN_SPOT_API_SECRET` lesen. Wer
  daraufhin den genannten Namen setzt, aendert nichts - und wer ihn prueft,
  findet ihn womoeglich vor und sucht den Fehler beim Schluessel. Beide Namen
  existieren in `HKCU\Environment`, aber nur das SPOT-Paar oeffnet den Spot-Host
  (das generische Paar antwortet `EAPI:Invalid key`).
- Regel: die Fehlermeldung nennt die Variable, die der Code AUCH liest. Bei
  jedem Zugangsfehler zuerst diese Zuordnung pruefen (Programm -> Name), statt
  den Wert zu verdaechtigen.
## Merksatz

Ein Fehlertext ist kein Befund. Erst die unabhaengige Umsetzung entscheidet, ob unser
Code oder der Zugang die Ursache ist; nur letzterer ist eine Nutzeraktion.
