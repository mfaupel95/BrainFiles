# OKX-Bot-Waechter (Future DCA, Future Grid)

Werkzeug `Agenten/Handel/okx_bot_waechter/`, gebaut 23.09.2026 auf Zuruf:
*„stoppen wenn die aus dem letzten kaufbaren Limit rauslaufen, um einen
Stop-Loss quasi zu imitieren, und auch neue vorschlagen und bauen können."*

## Das Problem in einem Satz

Future-DCA- und Future-Grid-Bots **kaufen nach, solange der Kurs faellt**. Ist
die letzte Stufe gefuellt (bzw. die untere Netzkante erreicht), hoert das auf:
der Bot haelt nur noch und laeuft ungebremst in die **Liquidation**. Keiner
dieser Bots hatte einen boersenseitigen Stop (`slPx` leer bei allen fuenf).

## Was er tut

| Befehl | Wirkung |
|---|---|
| `waechter.py` | Bericht ueber alle laufenden Bots, rein lesend |
| `waechter.py --anwenden` | stoppt die Bots in einer Stopp-Lage (`stop_erlaubt=true` noetig) |
| `vorschlag.py --art dca\|grid --inst <id> --budget <n>` | rechnet einen neuen Bot, schreibt `vorschlaege/*.json` |
| `bauen.py <vorschlag.json> --anwenden` | legt ihn an (`bauen_erlaubt=true` noetig) |

Lagen: `OK` / `KNAPP` / `AUSGELAUFEN` / `NOTFALL` / `WARNUNG`.
`AUSGELAUFEN` = Kurs unter der letzten kaufbaren Grenze. `NOTFALL` = dieselbe
Lage mit Liquidation naeher als `liq_notfall_prozent`, **oder** ein gesundes
Buch, das unter `liq_notfall_prozent` an die Liquidation kommt.

Cron: `okx-bot-wache` (alle 30 min, no_agent, `Agenten/Hermes/scripts/okx-bot-wache.py`) -
meldet nur Neues (Lagewechsel, sonst hoechstens alle 6 h), leere Ausgabe = nichts.

## Die Messung, auf der alles steht

* **Letzte kaufbare Grenze** = tiefste Kauforder aus `/tradingBot/dca/orders`
  (cycleId aus `cycle-list`), gegen die Planrechnung geprueft:
  `initPx * (1 - maxSafetyOrds * pxSteps)` — beim echten UNI-Bot ergab beides
  denselben Wert 9.613 (gemessen, nicht angenommen).
* **Munition** = `maxSafetyOrds - fillSafetyOrds` aus `dca/position-details`.
  `0` heisst: der Bot kann nicht mehr nachkaufen.
* **Liquidation** = `liqPx` (DCA: position-details, Grid: orders-algo-pending).
* Grid: untere Kante `minPx` (Long/Neutral) bzw. obere `maxPx` (Short).

## Erster Befund (23.09.2026, echter Aufruf)

| Bot | Kurs | Grenze | Munition | bis Liq | PnL | Lage |
|---|---|---|---|---|---|---|
| UNI | 9.236 | 9.613 | 0/11 | 5,6 % | −50,9 % | NOTFALL |
| ARB | 0,22548 | 0,23816 | 0/8 | 5,0 % | −44,1 % | NOTFALL |
| MON | 0,02424 | 0,02498 | 0/10 | 13,1 % | −22,6 % | AUSGELAUFEN |
| ZEC | 1525,0 | 1538,3 | 0/6 | 18,3 % | +2,7 % | AUSGELAUFEN |
| BCH | 349,6 | 321,2 | 13/14 | — | +71,5 % | OK |

Alle fuenf ohne `slPx`. Zwei stehen 5 % vor der Liquidation. **Gestoppt wurde
nichts** — `stop_erlaubt` steht auf `false`, das ist die Entscheidung von Max.

## Ein neuer Bot bringt seinen Stop mit

`vorschlag.py` legt die **tiefste Stufe auf den geplanten Boden**
(`dca_fallraum_prozent`, hart begrenzt durch das Tagestief) und setzt genau
dorthin den Stop: DCA `slPct` (Modus `market`), Grid `slTriggerPx = minPx`.
Beispielrechnung (UNI, 100 USDC): 12 Stufen, 1,25 % Abstand, letzte Stufe
7,819, Stop 8,11 % unter dem mittleren Einstieg, Hebel 7 so, dass die
Liquidation 5 % **unter** dem Planboden liegt.

Der Vorschlag beschoenigt nicht: Boden ueber dem Kurs = Fehler; Einsatz unter
dem OKX-Mindestinvestment (Grid: 534,42 bei diesem Bereich) = Warnung und
`bauen.py` verweigert.

## Fallen, die im Code stehen

* `POST /tradingBot/grid/stop-order-algo` will den Koerper als **Liste**,
  `dca/stop` als Objekt.
* Bei GET gehoeren die Parameter in den **Pfad** (`_roh(body=...)` schickt
  einen Request-Body - fuer POST).
* `/public/instruments` verlangt `instType`; die Kennung sagt, welcher Markt
  gemeint ist (FUTURES bei `-USD_UM_XPERP-<Datum>`, SWAP bei `-USDT-SWAP`).
* Grid-Vorschlag: die OKX-KI-Kanten koennen **enger** sein als der beobachtete
  30-Tage-Bereich; der Plan zieht sie auf die weitere Spanne und deckelt die
  Stufenzahl (`grid_num_max`).
* `stopType 1` schliesst die Positionen am Markt, `2` laesst sie stehen - der
  Waechter hat 1 als Vorgabe, weil ein Stop ohne Schliessung kein Stop ist.

## Das Schema der Nachkauf-Leitern (Analyse 23.09.2026)

`analyse.py` misst je Bot, ob die Leiter zum Instrument passt. Ergebnis: **die
Leitern reichten 4-8 %, die Instrumente laufen 8-13 % pro Tag.** Kein Einzelfall,
ein Konstruktionsfehler - die Munition ist nach ein bis zwei Tagen weg.

| Bot | Leiter | Rueckgang seit Kauf | bis Liq | ATR/Tag | 90-T-Rueckgang |
|---|---|---|---|---|---|
| UNI | 7,92 % | -12,5 % | 5,5 % | 11,9 % | -25,4 % |
| ARB | 4,16 % | -12,0 % | 5,0 % | 13,2 % | -27,5 % |
| MON | 8,00 % | -12,1 % | 13,1 % | 8,6 % | -25,1 % |
| ZEC | 8,40 % | -10,0 % | 18,5 % | 10,6 % | -21,2 % |
| BCH | 7,98 % | -2,7 % | - | 9,0 % | -24,6 % |

Regel (in `analyse.py`, Vorgabe fuer neue Bots): Tiefe = max(3 x ATR, beobachteter
Rueckgang, 10 %); Abstand je Stufe 0,15-0,5 x ATR, aber mindestens 2,5 %; Hebel so,
dass die Liquidation 5 % unter dem Planboden liegt; Planboden moeglichst unter dem
90-Tage-Tief. `vorschlag.py --tiefe auto` rechnet das jetzt so.

Wochenchart: die Kontrakte sind zu jung (7-26 Wochenkerzen) - die Trendaussage kommt
vom SPOT-Paar (`analyse.py --woche`).

## Entscheidung Max zum Stoppen (23.09.2026)

UNI und ARB werden **nicht** gestoppt: der uebergeordnete Trend im Wochenchart ist
aufwaerts (UNI 2,25x ueber dem 30-Wochen-Durchschnitt, der steigt; ARB 2,0x - beide
allerdings 51 % bzw. 90 % unter ihrem Wochenhoch), Max erwartet die Rueckkehr und ein
Laufen ins Plus. Festgehalten als `bots: {"<algoId>": {"scharf": false, "vermerk":
"Entscheidung Max ..."}}` in `wachen.json` - damit kippt die Entscheidung nicht bei
der naechsten Freigabe still um. `stop_erlaubt` bleibt `false`.
## Laufende Bots umstellen (anpassen.py, 23.09.2026)

Der Amend-Weg fuer einen laufenden DCA ist belegt: `POST /api/v5/tradingBot/dca/amend-order-algo`
mit allen Leiterparametern. Beweis ohne Wirkung: eine unbekannte algoId antwortet
`OKX 51291 The bot doesn't exist or has already stopped` - Endpunkt, Signatur und Host sind
damit geprueft, ohne einen Bot anzufassen. Ein GET darauf: `OKX 3 Operation not supported`.

Die zwei ehrlichen Grenzen: neue Sicherungsstufen brauchen freies Guthaben (am 23.09.2026
waren es 0,03 USDC), und die bindende Wand einer voll gefuellten Position ist die
Liquidation, nicht die Leiter. Margin-Bedarf = `(Zielabstand - heutiger Abstand) x Notional`,
Wartungsrate als Rest gemessen.

## Das Schema der Grids (Analyse 25.09.2026)

Gemessen an ALLEN 62 geschlossenen Grids des Kontos: `grid/orders-algo-history`
fuer die Liste, `grid/orders-algo-details` je Kennung fuer `floatProfit`, und
1H-Kerzen ueber `market/history-candles` fuer die Kursbewegung waehrend der
Lebensdauer (die normale `market/candles`-Abfrage reicht nur ~12 Tage zurueck und
haette bei den August-Bots still das falsche Fenster geliefert).

Summe ueber 62 Grids (Investment 7.072,87 USDC):

| Groesse | Summe |
|---|---|
| Netzgewinn (`gridProfit`) | **+305,64** |
| Richtungsgewinn (`floatProfit`) | **-392,99** |
| Gebuehren + Funding | -45,64 |
| **Ergebnis** | **-77,01 (-1,09 % des Einsatzes)** |

Die Mechanik verdient also zuverlaessig, die Richtung verliert mehr. 30 Gewinner
gegen 28 Verlierer, mittlere Lebensdauer **1,3 Tage**. Entscheidend ist die
Marktrichtung waehrend der Lebensdauer: lief sie in Richtung des Grids, waren
**82 %** der Laeufe Gewinner (Summe +392,51); lief sie dagegen, **21 %**
(Summe -469,52). Hebel, Netzzahl und Bandbreite trennen NICHT (Gewinner im
Mittel 7,0x / 62 Netze / 32 % Band gegen Verlierer 5,8x / 75 Netze / 45 % Band).

### Die zwei genannten Kennungen

| algoId | Instrument | Laufzeit | Markt | Netzgewinn | Richtung | Ergebnis |
|---|---|---|---|---|---|---|
| `3850683993419132928` | PUMP long | 1,42 T | **+25,6 %** | 4,56 | 104,97 | **+109,53 (93,2 %)** |
| `3936916024150462464` | ZEC long | 3,95 T | +5,7 % | 35,28 | 11,48 | **+46,76 (30,6 %)** |

Zwei verschiedene Mechanismen, beide erfolgreich - und beide IM PLUS gestoppt
worden, keiner lief aus:

* **PUMP:** 96 % des Gewinns kam aus dem RICHTUNGSgewinn, das Netz lieferte 4 %.
  Hebel 10, Band 0,0035-0,005 (42,9 %), der Markt lief 25,6 % hoch - ein
  gehebelter Long im Netzkostuem. Automatisch gestoppt bei 0,00388
  (`slTriggerPx` 0,00345, `triggerType auto`).
* **ZEC:** 75 % aus dem Netz - 92 Arbitrage-Runden in einem 17,2 %-Band, der
  Kurs schwankte vier Tage zwischen -6,1 % und +10,5 %, ohne auszubrechen. Von
  Hand gestoppt, **ohne Stop** (`slTriggerPx` leer).

### Die Regel, die daraus folgt

Ein Long-Grid ist ein **gehebelter Long mit Mean-Reversion-Overlay**. Es gibt
zwei Wege zum Gewinn (Richtung oder Oszillation) und **einen** Weg zum grossen
Verlust: laufen lassen, waehrend der Markt gegen die Position geht. Der groesste
Einzelverlust der Serie - BICO 10.-12.08.2026, 1,66 Tage, Markt -19,3 % - war
**-304,33 USDC, viermal der Gewinn aller 62 Grids zusammen**.

Daraus drei Regeln:

1. `slTriggerPx = minPx` **immer** setzen. `vorschlag.py` tut das schon; von Hand
   angelegt fehlte der Stop (ZEC 19.09. und das laufende Grid, T-077).
2. Kein neues Long-Grid gegen einen fallenden Wochenchart - die gemessene
   Trefferquote dort ist 21 %.
3. Das Band aus dem ATR, nicht aus dem Bauch: im Erfolgsfall fuellte sich das
   Netz wegen der BEWEGUNG, nicht wegen der Enge.

Nachpruefbar mit `Agenten/Handel/okx_bot_waechter/grid_historie.py` (T-076,
08.10.2026: die Wegwerfsonde ist als Leser in den Waechter uebernommen - je Grid
Seite, Laufzeit, Netzgewinn, Richtungsgewinn, Stop ja/nein, Marktbewegung;
`waechter.py --historie` haengt die Summen an den Bericht).

## Eine laufende Contract-DCA nimmt keinen Stop an (25.09.2026)

Gemessen an acht laufenden Future-DCA-Bots: `dca/amend-order-algo` weist JEDEN
Amend mit `51291: The bot doesn't exist or has already stopped` ab - auch mit
korrektem Koerper (alle Felder wie in der Doku) und laufendem Bot. Der Grund steht
in der Doku-Ueberschrift: der Endpunkt heisst **"Amend SPOT dca basic param"**, ist
also nur fuer SPOT-DCA. Fuer `algoOrdType: contract_dca` gibt es keinen Amend.

Ein Stop auf die POSITION geht ebenfalls nicht: `/api/v5/account/positions` liefert
fuer dieses Konto **0 Eintraege** (auch mit `instType=FUTURES`/`SWAP`); abgefragt mit
dem Bot-Instrument kommt eine Zeile mit `pos=0`. Die Bots halten ihre Marge intern,
es liegt keine Position zum Absichern draussen.

**Das einzige Schutzmittel ist deshalb `dca/stop`** - den Bot anhalten, was die
Position zum Markt schliesst (Tor `stop_erlaubt` in der `wachen.json`).
Anders als beim Grid: dort gibt es `grid/amend-order-algo` (der ZEC-Grid-Stop 1354
liess sich damit setzen, `sCode 0`).
