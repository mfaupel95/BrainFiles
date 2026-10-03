# OKX-Fehler richtig lesen (und nicht dreimal senden)

Befund vom 20.09.2026, Spur `scanner`: Journal zeigte
`Verkauf AVAX-USDT fehlgeschlagen: HTTP Error 400: Bad Request`.
Daraus ist nicht ablesbar, was zu tun ist. Dahinter steckten ZWEI Fehler.

## 1. Orderfehler kommen mit HTTP 200

OKX lehnt eine Order fachlich ab, antwortet aber mit **HTTP 200** und
`code: "1"`. Die eigentliche Auskunft steht in `data[0].sMsg`/`sCode`:

```json
{"code":"1","msg":"All operations failed",
 "data":[{"sCode":"51020","sMsg":"Your order amount does not meet the minimum order amount."}]}
```

Wer nur das aeussere `msg` ausliest, schreibt "All operations failed" ins
Journal. Immer `data[0].sMsg` bevorzugen, `msg` nur als Rueckfall.

## 2. HTTP 4xx darf nicht als Transportfehler gelten

`_roh()` las die OKX-Auskunft nur bei 401/403 aus. Ein **400** fiel als
roher `HTTPError` durch und wurde von `_mit_wiederholung` fuer einen
Transportfehler gehalten - also **dreimal erneut gesendet**. Bei einer
Verkaufsorder ist jeder Versuch eine echte Order.

Regel: ALLE 4xx als fachlichen `OKXFehler` werfen (keine Wiederholung),
nur echte Transportfehler wiederholen.

## Gegenprobe (am echten Endpunkt, ohne Geld zu bewegen)

Eine Order mit zu kleiner Menge senden - OKX lehnt sie ab, es entsteht
keine Position:

```python
okx.markt_verkauf('AVAX-USDT', 0.001)
# vorher: HTTP Error 400: Bad Request
# jetzt:  OKX 51020: Your order amount does not meet the minimum order amount.
```

## 3. `50119`/`50101` heisst meist FALSCHER HOST, nicht toter Schluessel

Symptom: **jede** Order scheitert mit `OKX 50119: API key doesn't exist (HTTP
401)`, waehrend Leseaufrufe weiter funktionieren.

Mechanismus: ein Zugang besteht aus Schluessel **und** Host (`OKX_BASE`, EEA
`https://eea.okx.com` gegen global `www.okx.com`). Wird der Schluessel mit
Registry-Rueckfall gelesen (`_variable`), der Host aber nur aus der
Prozessumgebung (`_env`), dann findet ein Kindprozess ohne geerbte
Benutzervariablen den Schluessel - und signiert gegen den Vorgabe-Host. Der
Fehler sieht wie ein toter Schluessel aus, ist aber ein falscher Endpunkt.

**Regel: Schluessel und Host gehoeren zu EINEM Zugang - wer einen Teil mit
Rueckfall liest, liest jeden Teil so.** Und: ein `50119`/`50101`, das auf
JEDER Order steht, ist kein abgelaufener Schluessel.

Pruefen, **bevor** ein Schluessel getauscht wird:

```bash
env -u OKX_BASE python -c "import okx; print(okx._live_basis())"
# muss den EEA-Host nennen, sonst faellt der Kindprozess auf den globalen zurueck
```

Reihenfolge der Diagnose: erst Host, dann Kontoberechtigung, dann Schluessel.
Kontoberechtigung lesend: `/api/v5/account/config` signiert, Feld `perm`
(`read_only,trade`) und Feld `ip` (leer = keine IP-Sperre). **`okx._roh()` gibt
die DATA-LISTE zurueck, nicht das Antwort-Dict** - ein Probeaufruf mit `.get()`
faellt mit `AttributeError` um, obwohl der Abruf geklappt hat.

## 5. `51001` = unbekanntes Instrument — erst die Spur suchen, dann deuten

`51001` ("Instrument ID does not exist") heisst: die Anfrage trug eine
`instId`, die die Boerse nicht kennt. Typische Ursachen: ein **abgelaufener
Kontrakt** (Papier- und Live-Buecher behalten das Instrument, die Boerse kennt
es nicht mehr), ein fehlender Suffix (`-USDT`, `-SWAP`) oder ein Symbol der
falschen Boerse (Kraken `XBT/USD` an einem OKX-Endpunkt).

**Bevor der Code gedeutet oder die gemeldete Spur repariert wird, ihn in DER
Spur suchen, die ihn angeblich schreibt:**

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel
grep -rn '51001' xperp/ nautilus_kraken/ | head -20
```

Ein leerer Treffer ist der Befund: diese Spur erzeugt den Code nicht. Gemessen
trat `51001` ausschliesslich in `xperp` auf (abgelaufener Kontrakt
`CL-USD_UM_XPERP-310509` ueber `okxf.letzter_kurs_mit_fallback`), waehrend die
nautilus-Arme die Zahl nirgends enthielten - ihnen wurde sie trotzdem
zugeschrieben. Und die Trefferzahl sagt nichts: derselbe Zahlenwert steht
harmlos in Modell-Metadaten und Kennungen, also die **Fundstelle** lesen, nie
bloss zaehlen. Ein `grep -r` ueber ganz `Agenten/` laeuft in den Timeout -
imner je Spur/Ordner suchen.

## Falle beim Nachstellen

OKX antwortet ohne `User-Agent` mit **HTTP 403 (Cloudflare 1010)**. Wer
ein Wegwerfskript baut und `okx.HEADERS` vergisst, misst seinen eigenen
Fehler und haelt ihn fuer einen Schluesselfehler.

## 4. Storno einer Algo-Order: `50014` = instId fehlt, `51400` = erledigt

Befund 23.09.2026, Spur `scanner`: jede Runde
`offener Stop 3940642343922589696 bleibt liegen: OKX 50014: Parameter instId
can not be empty`, und `zustand.json` trug **23 Kopien** desselben Stops.

Zwei Fehler auf einmal:

* `cancel-algos` braucht **`instId`**. Ohne sie: `50014`, der Stop laesst sich
  **nie** abbestellen. Gemessen am EEA-Host mit einer Attrappen-Kennung:
  `{"algoId": FAKE}` -> `50014`; `{"algoId": FAKE, "instId": "ZEC-USDC"}` ->
  `51400 Order cancellation failed as the order has been filled, canceled or
  does not exist`.
* **`51400` heisst erledigt, nicht Fehler.** Wer es als Fehler behandelt,
  laesst den Merker fuer immer liegen und meldet jede Runde dasselbe. Ein
  Stop, den es nicht mehr gibt, ist kein offener Stop.

Regel: `stop_stornieren(algo_id, inst)` - Instrument IMMER mitgeben;
`51400` still als erledigt werten; fehlt einem Alteintrag das Instrument,
lesend nachholen (`stop_inst`, `state`/`instId` aus `order-algo`).

Der zweite Fehler war der Merker selbst: `z["offene_stops"].append(...)` ohne
Dedupe. Wuchs bei jedem weiteren Ausstiegsversuch, denn solange der Verkauf
zusatzlich scheiterte (falscher Host, `50119`), blieb die Position im Buch und
der naechste Zyklus merkte denselben Stop erneut.

**Merksatz: ein Merker, der nur beim Erfolg faellt, braucht einen Dedupe - und
eine Antwort, die "gibt es nicht mehr" bedeutet, ist kein Fehler.**

Nachweis/Bestandsaufraeumer: `Agenten/Handel/scanner/stops_bereinigen.py`
(Vorschau Standard, `--anwenden`, `--stornieren` fuer Waisenstops);
Tester `scanner/tests/test_okx_stornieren.py`; Gegenprobe
`zustand.json` (23 -> 0, Buch gegen Boerse 5/5 ueber
`/api/v5/trade/orders-algo-pending?ordType=conditional`).

## 6. `50103` aus einer UNGESIGNETEN Abfrage — sieht wie ein fehlender Schluessel aus

`OKX 50103: OK-ACCESS-KEY can not be empty` heisst: die Anfrage ging OHNE Signatur
raus. Beim Sondieren vergisst man das leicht, denn `_roh(pfad)` signiert NICHT —
der Schalter muss ausdruecklich mit: `_roh('/api/v5/account/positions',
signiert=True)`. Ohne ihn liest man einen Schluesselfehler, wo keiner ist, und
"repariert" die Schluessel einer Spur, die gesund ist.

**Regel: bevor ein Schluessel verdaechtigt wird, pruefen, ob die Sonde ueberhaupt
signiert hat.** Lesende Kontodaten (`account/positions`, `account/balance`,
`trade/orders-algo-pending`) brauchen `signiert=True`, oeffentliche Marktdaten
(`market/*`, `public/*`) nicht. GET-Parameter gehoeren in den PFAD (so wie oben),
`body=` ist fuer POST.

Alle conditional Stops eines Kontos liegen in EINEM Aufruf
(`orders-algo-pending?ordType=conditional`): je Zeile `algoId`, `instId`, `sz`,
`slTriggerPx`, `tdMode`, `side`, `reduceOnly`. Das ist die Quelle fuer die Frage
"welche Schutz-Orders liegen am Markt, und deckt jede eine Position?" — und
`reduceOnly: true` ist der Grund, warum eine Order groesser als ihre Position
dort harmlos ist (siehe SKILL.md, "Waisen").

## 7. `50124` = falscher MARKT-NAMENSRAUM, nicht fehlende Berechtigung

Befund 25.09.2026, Spur `swap`: `Eroeffnen XAU-USDT-SWAP fehlgeschlagen:
OKX 50124: This API Key does not have trading permission for the market`.

Der Schluessel war in Ordnung: `/api/v5/account/config` meldete
`perm: read_only,trade`, `acctLv: 2`. Der Fehler kam vom NAMEN des Marktes. Auf
diesem EEA-Konto ist der Markt nur unter dem **XPERP-Kontrakt** handelbar
(`instType=FUTURES`, `instId` `XAU-USD_UM_XPERP-310502`), nicht unter dem
gleichnamigen gewoehnlichen Perpetual (`instType=SWAP`, `XAU-USDT-SWAP`). Der
oeffentliche Instrumentenabruf listet BEIDE - sichtbar heisst nicht handelbar.

Zeugen (beide lesend, ohne Order):

```python
okxf.instrumente(okxf.ROHSTOFF)          # liefert nur die XPERP-Kontrakte
okxf.swap_instrument("XAU-USDT-SWAP")    # liefert den gewoehnlichen Perpetual
okxf._roh("/api/v5/account/positions?instType=SWAP", signiert=True)     # []
okxf._roh("/api/v5/account/positions?instType=FUTURES", signiert=True)  # die echten
okxf._roh("/api/v5/trade/orders-history-archive?instType=FUTURES"
          "&instId=XAU-USD_UM_XPERP-310502", signiert=True)             # gefuellt
```

**Regel: erst den Namensraum, dann die Rechte.** Ein `50124` bei einem Markt,
der oeffentlich gelistet ist, heisst: die Spur handelt die falsche Kennung
desselben Marktes. Gegenprobe ist die ORDERHISTORIE des vermuteten Zwillings
(`instType` passend waehlen - der XPERP-Kontrakt ist `FUTURES`, nicht `SWAP`,
sonst kommt `51015 Instrument ID doesn't match instrument type`) und die
Positionsliste je `instType`. Nie eine Testorder zur Diagnose.

Umsetzung im Haus: `swap/kandidaten.handels_kontrakte()` liefert je Basiswert
den XPERP-Zwilling (EINE Abfrage), die Reihen des Vorrats tragen ihn als
`handels_instr`/`handels_instId`, `handeln.anlauf()` nimmt ihn; eine Reihe ohne
Zwilling faellt aus der Liste statt in einen Fehler zu laufen.

## 8. Eine Sperre muss sagen, WELCHE Boerse gefragt wurde

Befund 25.09.2026, Spur `mosaic` (zwei Boersen in der wachen.json): Der
Sperrgrund lautete `nur 0.71 EUR frei, noetig 60.00`. Max las das als OKX -
dort liegen USDC, und die Zahl stand ohne Namen da. Gefragt war Kraken (EUR);
OKX hatte ebenfalls kein Geld (0,15 USDC frei). Die Meldung war richtig und
trotzdem irrefuehrend.

**Regel: der Grund nennt die Boerse UND ihre Waehrung** (`kraken: nur 0.71 EUR
frei, noetig 60.00 - dazu okx: nur 0.15 USDC frei, noetig 60.00`). Bei mehreren
Boersen in der Liste gehoeren die uebrigen Gruende daneben, sonst sieht eine
geprueft-leere Boerse wie eine ungeprueft uebersprungene aus.
`mosaic/handeln.live_sperren()` macht das seit dem 25.09.2026; Test in
`mosaic/tests/test_boersenwahl.py`.

## 9. `51291` am Amend-Weg = die Bot-ART passt nicht — vor jedem Stop klaeren, WAS man stoppen will

Symptom: `POST /api/v5/tradingBot/dca/amend-order-algo` weist einen laufenden Bot
mit `OKX 51291: The bot doesn't exist or has already stopped` ab — auch mit
vollstaendigem Koerper (alle Felder der Doku) und obwohl `dca/ongoing-list` und
`dca/position-details` denselben Bot als `running` zeigen. Das liest sich wie eine
tote Kennung und ist keine.

Mechanismus: bei Bots ist die **Doku-Ueberschrift** die Auskunft.
`dca/amend-order-algo` heisst dort **"Amend SPOT dca basic param"** und ist nur
fuer SPOT-DCA. Fuer `algoOrdType: contract_dca` gibt es keinen Amend; OKX sucht
eine SPOT-DCA mit dieser Kennung, findet keine und meldet "existiert nicht".
GRID-Bots haben dagegen `grid/amend-order-algo` (das naheliegende
`grid/amend-algo` antwortet HTTP 404) — damit liess sich ein Schutzstop setzen
(`sCode: 0`, danach gegenlesen: `slTriggerPx` steht).

Regel: **vor jedem Bot-Amend die Bot-ART und die Ueberschrift des Endpunkts
pruefen.** SPOT-DCA, Contract-DCA und Grid sind drei verschiedene Wege; ein
51291 auf einen nachweislich laufenden Bot heisst "falscher Weg", nicht "Bot
weg".

Damit bleibt als Schutz fuer eine Contract-DCA nur der Bot selbst (`dca/stop`,
Tor `stop_erlaubt`) - und ein Stop auf die POSITION geht aus zwei Gruenden nicht:

* **Der Bot-Name traegt eine Lieferkennung, die Position nicht.** Bot:
  `LTC-USD_UM_XPERP-310404`, Position: `LTC-USD_UM_XPERP`. Wer mit dem Bot-Namen
  sucht, findet nie eine Position; mit dem Bot-Namen abgefragt kommt eine Zeile
  mit `pos=0` zurueck.
* **Ein Bot haelt seine Marge intern.** `/api/v5/account/positions` liefert fuer
dieses Konto 0 Eintraege - auch mit `instType=FUTURES`. Draussen liegt also
  nichts, was eine bedingte `order-algo` mit `reduceOnly` schuetzen koennte.

Werkzeuge, die daraus entstanden sind: `okx_bot_waechter/grid_schutz.py` (Grid:
Stop = Kurs − 1,5 × ATR, gedeckelt unter den Bandboden und ueber die Liquidation)
und `okx_bot_waechter/positions_schutz.py` (Position; **ueberspringt still, wenn
keine Position sichtbar ist** - genau der Fall oben, und das ist der Befund, nicht
ein Fehler).

## 10. `51155` = Compliance-Sperre des Kontos, nicht Rechte und nicht Menge

Symptom: `OKX 51155: You can't trade this pair or borrow this crypto due to local
compliance restrictions.` bei einem Instrument, das oeffentlich GELISTET ist,
dessen Paar existiert und dessen Menge weit ueber `minSz` liegt.

Mechanismus: das EEA-Konto schliesst einzelne Instrumente aus, obwohl
`/api/v5/public/instruments` sie fuehrt. Der Fehler kommt **vor** jeder
Mengenpruefung - ein `validate`-Lauf scheitert identisch. Betroffen sind die
**gestakten Formen**: `BETH` (Beacon-ETH) und `OKSOL` (OKX-Staked-SOL) haben auf
diesem Konto **nur ein USDT-Paar** (`BETH-USDT`, `OKSOL-USDT`) und kein
USDC-Paar - und auch das USDT-Paar ist gesperrt.

**Regel: die Handelbarkeit eines Instruments ist nur am ORDERWEG zu erfahren,
nicht am Instrumentenabruf.** `status=live` in `public/instruments` heisst
"gelistet", nicht "handelbar" - dieselbe Familie wie `50124` (Abschnitt 7:
falscher Markt-Namensraum) und `51001` (Abschnitt 5: unbekanntes Instrument).
Ein `validate`-Lauf vor dem echten Verkauf ist die einzige billige Probe.

Umgang im Bestand: solche Posten gehoeren als "compliance-gesperrt" in den
Bericht - nicht in einen zweiten Versuch, nicht in eine Paarsuche. Der Kontowert
bleibt in `eqUsd` sichtbar, einsetzbar ist er nicht; `availBal` bleibt voll, was
den Posten harmlos aussehen laesst.

## 11. Ein Transportfehler wird wiederholt - und die Meldung muss das sagen

```
OKX-Transportfehler 1/6: <urlopen error [WinError 10054] Eine vorhandene
Verbindung wurde vom Remotehost geschlossen>
```

Diese Zeile liest sich wie ein Ausfall und ist eine **Warnung**: der Wiederholer
(`_mit_wiederholung` in `scanner/okx.py`, `xperp/okxf.py`, `mosaic/okx_spot.py`,
`kraken/kraken.py`) versucht es bis `MAX_FEHLER = 6` mit wachsender Pause
(`1.5 * fehler` Sekunden) - erst der SECHSTE Fehlschlag ist ein Fehler. Wer sie
deutet statt prueft, sucht einen Defekt, den es nicht gibt.

**Regel: eine Meldung aus einem Wrapper spricht die Wiederholung aus**
(`... - wird wiederholt, kein Ausfall`). Sie geht auf `stderr`, wird also nicht
vom Dauerlauf gefiltert - aber Max liest sie, und eine Zeile, die wie ein
Ausfall klingt, kostet Vertrauen. Der Praefix bleibt gleich, damit bestehende
Suchen weiter treffen.

Pruefen, in dieser Reihenfolge (beide Messungen sind billig):

```python
okx._roh('/api/v5/account/config', signiert=True)   # antwortet? (hier 0,2 s, perm read_only,trade)
```

```bash
grep -c Transportfehler Agenten/Handel/dauerlauf.log          # im EIGENEN Log: 0
grep -rc Transportfehler Agenten/Routinen/logs/               # Rand-Logs: einzelne Zeilen
grep -n 'TIMEOUT\|Traceback' Agenten/Handel/dauerlauf.log     # kein Befund = Zyklus lief durch
```

Mechanismus: `WinError 10054` ist ein zurueckgesetztes TCP-Socket. Es traf am
selben Tag **OKX UND Kraken gleichzeitig** (Handelszentrale-Fehlerlog) - also ein
lokaler Netz-/Verbindungsmoment, keine Boersensperre. Verteilt ueber zwei Tage:
7 Vorkommen in den Rand-Logs, NULL im Dauerlauf-Log, und der Zyklus davor/danach
lief mit allen Spuren `ok`. Kein Grund fuer eine neue Sonde und keiner fuer eine
Wache.

Zwei Anschluesse, die zusammengehoeren:

* **Fachliche Fehler werden NICHT wiederholt** (Abschnitt 2): `OKXFehler` geht
direkt raus, sonst geht eine abgelehnte Order mehrfach an die Boerse.
* **Eine im Reset verlorene ANTWORT ist keine verlorene Order.** Der naechste
  Zyklus holt den Zustand von der Boerse (`boersenstops`, `wartende_auftraege`,
  Buchabgleich), deshalb ist ein Transportfehler auf dem Orderweg kein Grund fuer
  einen Handgriff von Hand.

Test: `tests/test_transport_wiederholung.py` (zwei Fehlversuche dann Antwort,
sechs dann Ausnahme, fachlicher Fehler nur EIN Versuch, und alle vier Meldungen
nennen die Wiederholung).
