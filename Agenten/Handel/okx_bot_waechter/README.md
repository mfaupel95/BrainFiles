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

## Die Leiter dimensionieren (Nachkauf-Barriere-Zonen)

`analyse.py` misst, ob die Leiter eines Bots zu seinem Instrument passt - und
rechnet die Zahlen fuer einen neuen. Gemessener Befund vom 23.09.2026 (alle fuenf
laufenden Bots, aus den eigenen Tageskerzen):

| Bot | Leiter tief | Kurs fiel seit Kauf | bis Liquidation | ATR/Tag | groesster Rueckgang 90 T |
|---|---|---|---|---|---|
| UNI | 7,92 % | -12,5 % | 5,5 % | 11,9 % | -25,4 % |
| ARB | 4,16 % | -12,0 % | 5,0 % | 13,2 % | -27,5 % |
| MON | 8,00 % | -12,1 % | 13,1 % | 8,6 % | -25,1 % |
| ZEC | 8,40 % | -10,0 % | 18,5 % | 10,6 % | -21,2 % (180 T: -46,2 %) |
| BCH | 7,98 % | -2,7 % | - | 9,0 % | -24,6 % (180 T: -45,8 %) |

**Das Schema war falsch, nicht die einzelne Zahl:** die Leitern reichten 4-8 %,
die Instrumente laufen 8-13 % pro TAG. Die Munition ist damit nach ein bis zwei
Tagen weg - kein Nachkauf mehr, und die Position laeuft ungebremst in die
Liquidation. Deshalb steht die Regel jetzt in ATR-Einheiten:

* **Tiefe** = max(3 x ATR, beobachteter Rueckgang 90/180/365 Tage, 10 %) - hoechstens 60 %
* **Abstand** je Stufe: mindestens 0,15 x ATR und 0,3 %, hoechstens 0,5 x ATR und 5 %,
  aber nie kleiner als 2,5 % - eine Stufe muss eine echte Bewegung sein
* **Hebel** so, dass die Liquidation 5 % UNTER dem Planboden liegt
* **Barriere**: der Planboden soll unter dem 90-Tage-Tief liegen. Liegt er darueber,
  sagt die Analyse es - die Leiter endet dann, bevor der Markt dort war

`vorschlag.py` rechnet die Tiefe seit 23.09.2026 so (`--tiefe auto`, Standard); ohne
Kerzen faellt es auf den festen Wert aus `wachen.json` zurueck, mit Hinweis. Der
Schalter `--tiefe 20` erzwingt eine feste Zahl.

```bash
# Was passt zu diesem Instrument? (Bericht ueber alle laufenden Bots)
../scanner/.venv/Scripts/python.exe analyse.py
# Nur der uebergeordnete Trend im Wochenchart (Quelle: Spot-Paar, nicht der Kontrakt)
../scanner/.venv/Scripts/python.exe analyse.py --woche
```

Der Wochenchart kommt bewusst vom **Spot**-Paar: die XPERP-Kontrakte sind zu jung
(7-26 Wochenkerzen), dort ist jede Trendaussage geraten.
## Parameter eines LAUFENDEN Bots aendern (anpassen.py)

Frage: lassen sich die Zahlen eines laufenden DCA-Bots umstellen, sodass es ab dem
naechsten Lauf greift? Antwort: ja - aber nicht alle Wege sind harmlos.

**Beweis, dass der Weg fuer dieses Konto existiert, ohne etwas zu aendern:** ein POST auf
`/api/v5/tradingBot/dca/amend-order-algo` mit einer algoId, die es nicht gibt, antwortet
`OKX 51291: The bot doesn't exist or has already stopped`. Damit ist belegt: der Endpunkt
gibt es, die Signatur stimmt, der Host passt - und der Bot wurde nicht beruehrt. Ein GET
darauf antwortet `OKX 3: Operation not supported` (falscher Weg).

Der Koerper traegt laut Doku ALLE Leiterparameter: `pxSteps`, `pxStepsMult`, `volMult`,
`tpPct`, `slPct`, `initOrdAmt`, `safetyOrdAmt`, `maxSafetyOrds`, `reserveFunds`.
Ein Amend schreibt also immer die ganze Leiter neu - auch Stop und Ziel. Deshalb gilt:
**was nicht ausdruecklich gewaehlt ist, bleibt wie es war.** `tpPct` wird, wenn der Bot es
nicht nennt, aus `tpPx / avgPx` hergeleitet (nicht mit 5 % angenommen).

Weitere Wege auf denselben Bot:

* `dca/margin/add` - Margin nachschiessen, drueckt die Liquidation nach unten,
* `dca/orders/manual-buy` - von Hand in den laufenden Zyklus kaufen.

### Was ein Amend NICHT kann

* Er aendert nicht, was schon gefuellt ist - die Position bleibt wie sie ist.
* Er schafft kein Geld: zusaetzliche Sicherungsstufen entstehen, koennen aber nicht
  fuellen, solange kein freies Guthaben da ist (die Warnung nennt Bedarf und Bestand).
* Er hebt die **Liquidation** nicht auf. Bei einer voll gefuellten Position ist das die
  bindende Wand, nicht die Leiter: liegt der Planboden unter `liqPx`, erreicht der Bot die
  tiefsten Stufen nie.

### Die Wand rechnen, statt sie zu schaetzen

Fuer eine isolierte Position gilt `Abstand(Einstand -> Liquidation) = Margin/Notional +
Rest`, wobei der Rest die Wartungsrate UND alles ist, was die Boerse sonst anrechnet
(z.B. einrealisierte Gewinne als Puffer). Margin, Notional und der Abstand sind bekannt -
der Rest faellt heraus (UNI-Bot 23.09.2026: 2,6 %) und wird NICHT angenommen. Ist er
gross (ueber 5 %, z.B. BCH 36,2 %), steckt mehr Margin in der Position als die
Leiterbetraege hergeben - die Zeile sagt es. Daraus folgt der
Margin-Bedarf: `(Zielabstand - heutiger Abstand) x Notional`.

### Aufruf

```
python anpassen.py                              # Bericht: alt gegen neu, je Bot
python anpassen.py --nur-schutz --sl-pct 0.21   # nur den Bueren-Stop setzen
python anpassen.py --stufen 20 --schritt 2.5    # Leiter tiefer legen
python anpassen.py --margin 50 --anwenden       # Margin nachschiessen
```

Gesendet wird nur mit `--anwenden` UND `anpassen_erlaubt=true` in `wachen.json` UND einer
ausdruecklichen Wahl; jede Aenderung landet in `bot_waechter_journal.jsonl`.
