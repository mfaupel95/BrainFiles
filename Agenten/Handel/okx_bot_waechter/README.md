# OKX-Bot-Waechter

Waechter ueber die **echten OKX-Bots** (Future DCA = `contract_dca`,
Future Grid = `contract_grid`). Er beantwortet eine Frage:

> Laeuft ein Bot aus seiner **letzten kaufbaren Grenze** heraus - und wenn ja,
> stoppt ihn jemand?

Beide Botarten haben denselben blinden Fleck: sie kaufen nach, solange der Kurs
faellt. Ist die letzte Stufe gefuellt, hoert das auf - der Bot haelt dann nur
noch und laeuft ungebremst in die **Liquidation**. Genau dort setzt der
Waechter an (Nachbildung eines Stop-Loss). Zusaetzlich kann er **neue Bots
vorschlagen und bauen**, bei denen der Stop schon eingebaut ist.

## Die vier Befehle

```bash
cd Agenten/Handel/okx_bot_waechter

# 1. Bericht: Lage aller laufenden Bots (rein lesend, stoppt nichts)
../scanner/.venv/Scripts/python.exe waechter.py

# 2. Scharf: stoppt die Bots, die aus ihrer letzten Kaufgrenze gelaufen sind
#    (braucht stop_erlaubt=true in wachen.json)
../scanner/.venv/Scripts/python.exe waechter.py --anwenden

# 3. Vorschlag rechnen (schreibt nur eine JSON-Datei nach vorschlaege/)
../scanner/.venv/Scripts/python.exe vorschlag.py --art dca --inst UNI-USD_UM_XPERP-310718 --budget 100
../scanner/.venv/Scripts/python.exe vorschlag.py --art grid --inst BTC-USD_UM_XPERP-310404 --budget 600

# 4. Vorschlag bauen (braucht bauen_erlaubt=true in wachen.json)
../scanner/.venv/Scripts/python.exe bauen.py vorschlaege/<datei>.json --anwenden
```

Tests (ohne Netz, ohne echte Dateien):

```bash
cd Agenten/Handel/okx_bot_waechter/tests
../../scanner/.venv/Scripts/python.exe -m unittest test_okx_bot_waechter
```

## Woher die Zahlen kommen (alles gemessen, nicht geraten)

| Groesse | Quelle |
|---|---|
| laufende Bots | `GET /api/v5/tradingBot/dca/ongoing-list`, `.../grid/orders-algo-pending` |
| Ist der Bot voll investiert? | `.../dca/position-details` -> `fillSafetyOrds` gegen `maxSafetyOrds` |
| **Letzte kaufbare Grenze** | tiefste Kauforder aus `.../dca/orders` (cycleId aus `.../dca/cycle-list`) - gegen die Planrechnung `initPx * (1 - n*pxSteps)` geprueft |
| Liquidation | `.../dca/position-details` -> `liqPx`; Grid: `orders-algo-pending` -> `liqPx` |
| Boersenseitiger Stop? | `slPx` (DCA) / `slTriggerPx` (Grid) - leer heisst: **keiner** |
| Grid-Bereich | `minPx` / `maxPx` (untere Kante = letzte kaufbare Grenze eines Long-Netzes) |
| Vorschlag Grid | `GET /api/v5/tradingBot/grid/ai-param` + eigene Kerzen (30 Tage) |
| Anlegen | `POST .../dca/create`, `POST .../grid/order-algo` |
| Stoppen | `POST .../dca/stop` (`stopType` 1 = Positionen am Markt schliessen, 2 = behalten), `POST .../grid/stop-order-algo` (Koerper ist eine **Liste**) |

## Lage (das Vokabular der Meldung)

| Lage | Bedeutung | Handlung |
|---|---|---|
| `OK` | im Plan, Nachkauf moeglich | keine |
| `KNAPP` | unter der letzten Kaufgrenze oder Munition alle, aber noch innerhalb der Reserve | beobachten |
| `AUSGELAUFEN` | Kurs unter der letzten Kaufgrenze - **kein Nachkauf mehr** | Stop-Kandidat |
| `NOTFALL` | wie AUSGELAUFEN **oder** naeher als `liq_notfall_prozent` an der Liquidation | Stop |
| `WARNUNG` | naeher als `liq_warnung_prozent` an der Liquidation | beobachten |

Ein `OK`-Bot mit leerem `slPx` traegt trotzdem einen Grund: *kein
boersenseitiger Stop gesetzt*. Das ist kein Fehler, sondern die Feststellung,
dass der Bot keinen eigenen Schutz hat - der Waechter ist dann der einzige.

## Die Tore

In `wachen.json`:

* `stop_erlaubt: false` - ohne diesen Haken stoppt `--anwenden` **nichts**
  (es zeigt nur `GESPERRT ...`). Je Bot ausnehmbar: `bots: {"<algoId>": {"scharf": false}}`.
* `bauen_erlaubt: false` - ohne diesen Haken legt `bauen.py --anwenden` nichts an.
* `startgeld_max_usd: 300` - Deckel fuer einen neuen Bot; `--deckel-aus` hebt ihn
  bewusst auf.

Beides steht bewusst auf `false`. Die Sperre ist der Normalzustand, nicht die
Ausnahme - wie bei der Freigabekette der Spuren.

## Warum ein neuer Bot seinen Stop schon mitbringt

`vorschlag.py` rechnet einen Plan, dessen **tiefste Stufe** auf dem geplanten
Boden liegt (`dca_fallraum_prozent`, hart begrenzt durch das Tagestief), und
setzt genau dorthin `slPct` (DCA) bzw. `slTriggerPx = minPx` (Grid). Der neue
Bot braucht damit keinen Waechter, um zu wissen, wann Schluss ist - der
Waechter ist fuer die Bots da, die es nicht wissen.

Der Vorschlag lehnt einen Plan ab, statt ihn zu beschönigen:

* Boden ueber dem Kurs -> Fehler,
* Einsatz unter dem OKX-Mindestinvestment -> Warnung, `bauen.py` verweigert,
* Kurs schon ausserhalb des Netzes -> Warnung,
* Hebel so gewaehlt, dass die Liquidation **unter** dem Planboden liegt.

## Grenzen

* Der Waechter **stoppt**, er verkauft nicht von sich aus weiter: `stopType 1`
  schliesst die Positionen am Markt (das ist die Nachbildung des Stop-Loss,
  `stopType 2` laesst sie stehen).
* Er sieht nur Bots, die auf diesem Konto laufen, und nur die Arten
  `contract_dca` / `contract_grid` (Spot-DCA, Moon-Grid und Recurring sind
  nicht verdrahtet - gleiche Endpunkte, andere Felder).
* Stoppen ist **echt**: es bewegt Geld. Darum zwei Tore und ein Protokoll
  (`bot_waechter_journal.jsonl`, nicht versioniert).
* Der Waechter ist kein Ersatz fuer einen boersenseitigen Stop: ein leeres
  `slPx` heisst, dass niemand schuetzt, solange der Waechter nicht laeuft.