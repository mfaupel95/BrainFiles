# Kraken: Invalid nonce, Temporary lockout und der falsche Variablenname

Stand 22.09.2026. Reihenfolge der Pruefung, damit nicht stundenlang die
falsche Ursache gejagt wird.

Verwandt: `references/boersen-schluessel-diagnose.md` — die Zuordnung „unser
Code, der Schluessel oder die Boerse?" samt der Falle, einen PRIVATEN Aufruf von
Hand zu signieren: ein selbstgebauter Aufruf liegt unter dem nonce-Peak und
bekommt `EGeneral:Permission denied` bzw. `authenticationError` — der Fehlertext
klingt dann nach fehlenden Rechten, obwohl der Schluessel in Ordnung ist.

## Erst den Kontostatus, dann den nonce

`EAPI:Invalid nonce` und `EGeneral:Temporary lockout` sehen im Log
aehnlich aus, haben aber nichts miteinander zu tun. Eine Serie
fehlgeschlagener Privataufrufe fuehrt zur **Sperre des Schluessels**.
Danach wird JEDER nonce abgelehnt - auch ein korrekter.

Deshalb: bei wiederholten nonce-Fehlern zuerst pruefen, ob ueberhaupt
noch etwas durchgeht. Ist die Antwort `Temporary lockout`, ist jede
weitere Sonde schaedlich (sie verlaengert die Sperre) und jede Messung
wertlos (sie misst die Sperre, nicht den nonce).

## Nicht sondieren, sondern warten

Sweeps ueber Zeitfenster (`srv-600s` bis `srv+10000s`) beweisen nichts,
solange die Sperre steht, und jeder Treffer wuerde den serverseitigen
nonce-Peak weiter hochtreiben. Richtig ist eine Wache, die **genau
einen** Abruf pro Stunde macht und nur den Uebergang meldet
(`Agenten/Hermes/scripts/kraken-lockout-wache.py`).

## nonce-Regeln, die bleiben

- Ein Schluessel, mehrere Programme: nur mit **gemeinsamem** persistentem
  nonce-Zaehler (`Agenten/Handel/kraken/nonce_pool.py`, O_EXCL-Sperrdatei).
  Zwei Prozesse mit eigener Wallclock ueberholen sich sonst gegenseitig.
- Monotone Wallclock ist die bewaehrte Basis. Ein "Drift-Abzug" gegen die
  Kraken-Serverzeit klingt richtig, senkt den nonce aber unter den bereits
  gespeicherten Peak - danach geht gar nichts mehr.
- **Die EINHEIT ist die groesste, die ein Programm auf demselben Schluessel
  benutzt.** Kraken merkt sich den HOECHSTEN Wert je Schluessel: signiert ein
  zweites Werkzeug in Nanosekunden (~1,78e18), waehrend die Hausseite
  Mikrosekunden (~1,77e12) sendet, ist danach JEDE Hausabfrage rund tausendfach
  zu klein — `EAPI:Invalid nonce` fuer alle Hausspuren, ausgeloest von einem
  fremden Programm, das einmal gelaufen ist. Fix ist die Angleichung der Einheit
  (`monotone_nonce()` auf Nanosekunden), nicht Abwarten. Vor dem Einbinden eines
  zweiten Werkzeugs auf denselben Schluessel dessen Einheit an einer signierten
  Ausgabe MESSEN, nicht annehmen.
- **Das Symptom auf der Spur-Seite ist kein nonce-Text.** Es kommt als
  Guthaben-Tor herein („Guthaben nicht abrufbar"), als gescheiterte Live-Sperre
  oder als stumm bleibender Live-Zweig. Wer nur nach `Invalid nonce` grept, findet
  die Ursache nicht — die betroffene Spur fragt ihren Kontostand ab und deutet die
  Ausnahme als fehlendes Guthaben.
- **Auch bei richtiger Einheit und streng monotonen EIGENEN Werten kann
  `EAPI:Invalid nonce` kommen.** Kraken vergleicht gegen den HOECHSTEN je Schluessel
  gesehenen Wert. Ein Werkzeug, das den gemeinsamen Pool NICHT benutzt (die
  kraken-cli), hebt ihn einmal hoch - danach liegt jeder Pool-Wert darunter, bis die
  Uhr den fremden Wert eingeholt hat, und ein Wiederholversuch mit DEMSELBEN Wert
  hilft nicht. Fix: den gemeinsamen Zaehler in der DATEI vorwaerts schieben
  (`nonce_pool.vorwaerts(sekunden)`; ohne das Schreiben waere der naechste normale
  Aufruf wieder zu niedrig) und mit dem vorgeschobenen Wert bis zu dreimal
  wiederholen (`kraken._roh_privat`). Erkennungszeichen: derselbe Aufruf gelingt eine
  Minute spaeter ohne Codeaenderung, und ein Schreibvorgang scheitert, waehrend der
  Leseaufruf Sekunden vorher durchging.
- Alte Prozesse halten ihren Code im Speicher. Ein nonce-Fix wirkt erst,
  wenn ALLE Sender neu gestartet sind (Dauerlaeufe, MCP-Server, Gateway).

## `EAPI:Invalid key`: erst den VARIABLENNAMEN pruefen, dann den Schluessel

**Die Regel: meldet ein Programm `Invalid key`, waehrend eine andere Anwendung
auf DEMSELBEN Rechner mit derselben Boerse nachweislich arbeitet, ist fast
immer der gelesene VARIABLENNAME falsch — nicht der Schluessel.**

Gemessen am 22.09.2026: die Benutzerumgebung traegt ZWEI Kraken-Paare.

| Variablen | wer liest sie | Zustand |
|---|---|---|
| `KRAKEN_SPOT_API_KEY` / `KRAKEN_SPOT_API_SECRET` | `Handel/kraken/kraken.py`, `MCP-Server/kraken/kraken_mcp.py` | gilt |
| `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` | die kraken-cli (und jedes Fremdwerkzeug mit "generischem" Namen) | von Kraken abgelehnt |

Pruefweg (keine Werte ausgeben):

```powershell
([Environment]::GetEnvironmentVariable('KRAKEN_SPOT_API_KEY','User')).Length
([Environment]::GetEnvironmentVariable('KRAKEN_API_KEY','User')).Length
```

Beide vorhanden und `HKCU\Environment`, aber nur eines authentifiziert. Der
Gegenbeweis kommt vom eigenen Client: `kraken.guthaben('ZEUR')` liefert eine
Zahl (also gilt dieser Satz), waehrend das Fremdwerkzeug 401-artig scheitert.
Erst DANN ist der Schluessel verdaechtig.

Zwei Nachbarn dieser Falle, beide billig zu pruefen: `Get-ItemProperty
HKCU:\Environment` loest in manchen Sitzungen einen anderen Benutzerkontext auf
(immer `[Environment]::GetEnvironmentVariable(name,'User')` benutzen), und ein
gewachsener Schluesselname (`KRAKEN_API_KEY_BILLING` o. ae.) sieht aus wie eine
Variante, ist aber ein anderer Zugang.

### kraken-cli als zweiter Kraken-Weg

Die offizielle `krakenfx/kraken-cli` (Rust, Einzelprogramm) liest die
generischen Namen und scheitert damit an diesem Konto. Es gibt **keine
Windows-Binaries** (nur macOS/Linux, Anleitung sagt "use WSL") — mit
vorhandenem Rust baut sie trotzdem nativ:

```powershell
cd Werkstatt\kraken-cli
cargo build --release --bin kraken     # Ergebnis: target\release\kraken.exe
```

Aufruf ueber den Haus-Wrapper `Agenten/Werkzeuge/kraken.ps1`: er setzt
`KRAKEN_API_KEY`/`KRAKEN_API_SECRET` aus den SPOT-Variablen (Werte bleiben im
Prozess) und reicht `$args` durch. Der Wrapper hat **keinen `param`-Block und
kein `[CmdletBinding()]`** — sonst deutet PowerShell den CLI-Schalter `-o` als
eigenen Parameter (`-OutVariable`/`-OutBuffer`) und bricht mit "Parametername o
ist nicht eindeutig" ab.

Nutzen fuer die Spuren, ohne Orderrecht: `ticker`/`ohlc`/`orderbook` (oeffentlich),
`balance`/`open-orders`/`ledger` (lesend), und der **eigene Papiermodus** mit
Livekursen und einstellbarer Gebuehr:

```powershell
.\kraken.ps1 workspace create sandbox --capital 10000 --mode paper --fee-rate 0.006 -o json
$env:KRAKEN_WORKSPACE='sandbox'
.\kraken.ps1 paper buy BTCUSD 0.01 -o json
```

`--fee-rate 0.006` ist der gemessene Haus-Satz; ohne ihn rechnet die CLI mit
0,26 %. `record`/`session`/`replay` legen Marktdaten lokal ab (DuckDB/JSONL) —
eine Rate-Limit-freie Quelle fuer Backtests. Der **eingebaute MCP der CLI** wird
bewusst nicht eingebunden: zwei Wege auf einem Schluessel erzeugen zwei
Meinungen darueber, was erlaubt ist.

## Nach dem Ende der Sperre: erst messen, dann urteilen

Die Sperre laeuft von selbst ab (Minuten bis Stunden), **ohne dass am Code
etwas geaendert wird**. Der erste erfolgreiche Leseaufruf danach ist deshalb
der Beweis, dass nonce-Pool und Schluessel in Ordnung waren - nicht der Beweis,
dass eine Reparatur gewirkt hat.

- Solange die Sperre steht, ist "der nonce-Code ist kaputt" **unbewiesen**:
die Sperre lehnt jeden nonce ab. Eine neue Schluessel-Empfehlung ist eine
  Absicherung, kein belegter Befund - im Bericht so benennen.
- Nach dem Ende der Sperre den **ersten Leseaufruf** als Beleg nehmen
  (`guthaben()` liefert eine Zahl statt einer Ausnahme).
- **Die Sperre war ein versteckter Blocker der Spuren.** Ein Guthaben-Tor
  ("nur X frei, noetig Y") kann waehrend der Sperre gar nicht anders antworten.
  Nach dem Ende der Sperre `handeln.py --vorschau` erneut laufen lassen: faellt
  "Live waere gesperrt durch: nichts", ist die Spur ohne Code-Aenderung frei -
  und der naechste Zyklus handelt. Nie einen Blocker aus der Sperrzeit
  weitererzaehlen.
- Eine Wache auf einen solchen Zustand ist nach dessen Ende entbehrlich; sie
  abzuraeumen ist Teil des Abschlusses. Der Merker, dass mehr als EIN Abruf je
  Stunde die Sperre verlaengert, bleibt gueltig.
