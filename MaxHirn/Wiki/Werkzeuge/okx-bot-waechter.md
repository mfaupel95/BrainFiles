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