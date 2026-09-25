# OKX Trading-Bot-API (DCA/Grid) — Endpunkte, Felder, Rechnungen

Alles signiert gegen `OKX_BASE=https://eea.okx.com` (EEA-Konto; `www.okx.com`
antwortet bei diesen Schluesseln mit 50101). GET-Parameter in den PFAD, nicht in
`body`.

## Lesen

| Zweck | Aufruf |
|---|---|
| laufende DCA-Bots | `GET /api/v5/tradingBot/dca/orders?algoOrdType=contract_dca` |
| Stufen eines DCA | `GET /api/v5/tradingBot/dca/orders?algoId=<id>` |
| Munition/Position | `GET /api/v5/tradingBot/dca/position-details?algoId=<id>` |
| Rundenhistorie | `GET /api/v5/tradingBot/dca/cycle-list?algoId=<id>` |
| laufende Grids | `GET /api/v5/tradingBot/grid/orders-algo-pending?algoOrdType=contract_grid` |
| GESCHLOSSENE DCA-Bots | `GET /api/v5/tradingBot/dca/history-list?algoOrdType=contract_dca` |
| GESCHLOSSENE Grids | `GET /api/v5/tradingBot/grid/orders-algo-history?algoOrdType=contract_grid` |
| Details je Grid-Kennung (auch nach dem Stopp) | `GET /api/v5/tradingBot/grid/orders-algo-details?algoId=<id>&algoOrdType=contract_grid` |
| Instrumentregeln | `GET /api/v5/public/instruments?instType=SWAP&instId=<inst>` |
| Kontraktkerzen | `GET /api/v5/market/candles` (Spot-Paar fuer lange Reihen) |
| Kerzen weiter als ~12 Tage zurueck | `GET /api/v5/market/history-candles?instId=<inst>&bar=1H&after=<ts_ms>&limit=100` (rueckwaerts blaettern) |

Felder, auf die es ankommt: `algoId`, `instId`, `initPx` (Startkurs), `maxSafetyOrds`
(Stufen), `pxSteps` (Abstand als Anteil, z. B. `0.0075`), `slPx` (Stop, oft leer =
kein Stop), `tpPct`, `lever`, `liqPx`, `fillSafetyOrds` (verbrauchte Stufen),
`minPx`/`maxPx`/`gridNum`/`slTriggerPx` beim Grid, `minInvestment` (OKX-Mindest-
einsatz je Instrument), `tickSz`, `ctVal`, `maxLever`.

`position-details` traegt zusaetzlich `avgPx`, `notionalUsd`, `upl`, `tpPx`, `sz`,
`curCycleId` — daraus kommen die Zustandsrechnungen, ohne eine Order zu stellen.
`tpPct`/`slPct` fehlen dort oft; dann aus `tpPx`/`avgPx` bzw. `slPx`/`avgPx`
herleiten (Einstand = `avgPx`).

Kerzenzeilen sind LISTEN: `[ts, open, high, low, close, vol]` — Position 2/3/4
sind high/low/close.

algoOrdType-Werte: `contract_dca`, `spot_dca`, `recurring`, `contract_grid`,
`moon_grid`.

## Geschlossene Bots auswerten (Historie)

Die Historie-Antwort ist eine Liste je Bot mit `cTime`/`uTime` (ms), `state`,
`investment`, `lever`, `gridNum`/`maxSafetyOrds`, `minPx`/`maxPx`, `gridProfit`,
`totalPnl`, `arbitrageNum`, `fee`, `fundingFee`, `slTriggerPx`, `triggerParams`.
`/api/v5/tradingBot/dca/orders-algo-history` gibt es NICHT (HTTP 404) — der Weg
heisst `dca/history-list`. Die Antwort enthaelt eine begrenzte Zahl der juengsten
Eintraege (gemessen: 100); ob sich aeltere nachblaettern lassen, ist ungeprueft.

- **Der Richtungsgewinn steht NUR in der Detailantwort.** In der Liste sind
  `floatProfit`, `runPx` und `tradeNum` leer; wer das als 0 liest, haelt einen
  Richtungstreffer fuer ein Netz-Ergebnis. `grid/orders-algo-details` antwortet
auch fuer GESCHLOSSENE Kennungen — die Werte sind nach dem Stopp noch messbar.
- **`totalPnl = gridProfit + floatProfit`.** `fee` und `fundingFee` sind
  Ausweisposten und in den beiden Summanden bereits enthalten — nicht ein
  zweites Mal abziehen.
- **Wer gestoppt hat**, steht in `triggerParams[-1]`: `triggerType manual` (von
  Hand) oder `auto` mit `triggerPx`. `stopType 1` = Positionen am Markt
  geschlossen, `2` = stehen gelassen.
- **Lebensdauer** = `uTime - cTime`; fuer die Kursbewegung in diesem Fenster 1H-
  oder 4H-Kerzen ueber `market/history-candles` blaettern.
- **Kennung ohne Kontext zuordnen**: `dca/position-details?algoId=<id>` auf eine
  Grid-Kennung antwortet `OKX 50016: algoId and algoOrdType don't match` (und
  umgekehrt) — damit ist die Art bestimmbar, ohne sie zu raten.

## Schreiben (am LAUFENDEN Bot)

| Zweck | Aufruf | Koerper |
|---|---|---|
| Leiter/Stop/Ziel umstellen | `POST /api/v5/tradingBot/dca/amend-order-algo` | ALLE Felder: `algoId`, `pxSteps`, `pxStepsMult`, `volMult`, `tpPct`, `slPct`, `initOrdAmt`, `safetyOrdAmt`, `maxSafetyOrds`, `reserveFunds`, `triggerParams` |
| Margin nachschiessen | `POST /api/v5/tradingBot/dca/margin/add` | `algoId`, `amt` |
| von Hand nachkaufen | `POST /api/v5/tradingBot/dca/orders/manual-buy` | `algoId`, `algoOrdType`, `price`, `amt` |
| Grid-Kanten/Netz | `POST /api/v5/tradingBot/grid/amend-algo-basic-param` | `minPx`, `maxPx`, `gridNum`, TP/SL |
| Grid-Stufen/Stop | `POST /api/v5/tradingBot/grid/amend-order-algo` | `gridNum`, TP/SL/Trigger |

Es gibt keinen Teil-Amend: wer die Leiter anfasst, schreibt auch Stop und Ziel
neu. Deshalb jedes nicht gewaehlte Feld aus dem Ist-Zustand uebernehmen und
`triggerParams` (`triggerAction: start`, `triggerStrategy: instant`) mitschicken.

**Gefahrlos pruefen, dass der Weg existiert** (bevor der erste echte Aufruf laeuft):

```
POST amend-order-algo mit algoId "1"  -> OKX 51291: The bot doesn't exist or has already stopped
GET  amend-order-algo                 -> OKX 3: Operation not supported
```

Der Fachfehler beweist Endpunkt, Signatur und Host; geaendert wurde nichts, weil
es den Bot nicht gibt. Ein 404/„not found“ haette das Gegenteil bedeutet.

## Die zwei Rechnungen

**Letzte kaufbare Grenze** (doppelt bestimmen, gegenseitige Kontrolle):

```
Grenze = initPx * (1 - maxSafetyOrds * pxSteps)      # Planrechnung
Grenze = tiefste Kauforder aus dca/orders?algoId=…   # gelebte Wahrheit
Tiefe_prozent = maxSafetyOrds * pxSteps * 100
Munition      = maxSafetyOrds - fillSafetyOrds
```

**Deckung gegen das Instrument** (die eigentliche Frage):

```
ATR14(Tag)  = Mittel der Tagesranges (high-low)/close, in Prozent
Ziel_Tiefe  = max(3 * ATR14, groesster Rueckgang 90/180/365 T, 10 %), max 60 %
Abstand     = 0,15-0,5 * ATR14, mindestens 2,5 %, hoechstens 5 %
Stufen_noetig = Ziel_Tiefe / Abstand_min
Hebel       <= so, dass liqPx mindestens 5 % unter dem Planboden liegt
```

**Wand einer gefuellten Position** (entscheidet, ob eine Umstellung wirkt):

```
Abstand(Einstand -> Liquidation) = Margin/Notional + Rest
Margin           = initOrdAmt + fillSafetyOrds * safetyOrdAmt   # Leiterbetraege
Rest             = Abstand - Margin/Notional                    # MESSEN, nicht annehmen
Margin_Bedarf    = (Zielabstand - Abstand) * Notional
Bedarf_Stufen    = (maxSafetyOrds_neu - fillSafetyOrds) * safetyOrdAmt   # gegen freies Guthaben
```

## Beispiel (nachgerechnet, DCA auf einem Alt-Kontrakt)

Ist-Zustand: `initPx` 9,613 · `maxSafetyOrds` 11 · `pxSteps` 0,0075 -> Tiefe
7,92 %, `fillSafetyOrds` 11 -> **Munition 0/11**; ATR14 11,9 %/Tag, 90-Tage-
Rueckgang −25,4 % -> die Leiter war nach rund einem Tag leer.

Vorschlag mit `--tiefe auto` (Budget 100, 12 Stufen à 2,98 %): Planboden 5,868
(35,8 % unter dem Startkurs), Hebel 3, Liquidation 5,003, `slPct` 21,81 %.
Warnungen: 20 Stufen waeren fuer 3 x ATR noetig; der Planboden liegt noch ueber
dem 90-Tage-Tief 3,168.

Umstellung desselben gefuellten Bots auf 20 Stufen à 2,5 % (Planboden 50 % unter
dem Einstand): Abstand zur Liquidation 12,33 % (Rest 2,6 %), 9 neue Stufen
brauchen 30,2 USDC, fuer die volle Tiefe fehlen 163,9 USDC Margin. Freies Guthaben
0,03 -> die neuen Stufen entstehen, koennen aber nicht fuellen. Genau so gehoert
die Antwort formuliert.

Grid: `minPx`/`maxPx` sind die Kanten, `slTriggerPx = minPx` ist der eingebaute
Stop, `minInvestment` des Instruments entscheidet ueber die Machbarkeit.

## Antwortformen

- `grid/stop-order-algo` → Liste
- `dca/stop` → Objekt, `stopType 1` schliesst die Positionen am Markt
- Unbekannte Kennung = harter Fehler (`ValueError`), nie ein Ersatzinstrument
