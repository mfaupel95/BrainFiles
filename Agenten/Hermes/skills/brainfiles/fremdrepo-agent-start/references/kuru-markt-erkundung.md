# Kuru (Monad) Markt-Erkundung — jev-trader Multi-Markt

Fuer den JEV-Trading-Bot (`O:/Werkstatt 2/JEV/jev-trader`, Fork mfaupel95/jev-trader)
andere Paare vorbereiten: welche Maerkte Kuru auf Monad fuehrt, wie man den
Margin-Account findet, und wie die Groessen je Markt zu setzen sind.

## Aktive Maerkte auflisten

`curl https://api.kuru.io/api/v1/markets` liefert ALLE Maerkte (auch inaktive).
Aktiv = `ticksize > 0` UND `minsize > 0`. Stand 14.10.2026: genau 4 aktive,
alle gegen USDC (0x754704Bc…):

| Markt | OrderBook-Adresse | minOrder (aus API minsize) |
|---|---|---|
| MON-USDC | 0x065C9d28E428A0db40191a54d33d5b7c71a9C394 | 200 MON |
| WETH-USDC | 0xa6afd386135b7d41a6c40c525abc4a1019b0d132 | 0.002 WETH |
| cbBTC-USDC | 0x40c49f171202f91ff5d2fae34c22dd2bfdd22af0 | 0.000125 cbBTC |
| XAUt0-USDC | 0x851145eaefdc37956b08da829fa31722199f3f07 | 0.002 XAUt0 |

Token-Symbole sind NICHT ueber `/api/v1/token/<addr>` aufloesbar (leer) — die
Adressen gegen die Discover-Seite oder bekannte Adressen mappen.

## Margin-Account: EINER fuer alle Maerkte

Alle Kuru-Maerkte settle gegen DENSELBEN MarginAccount. Finden: Storage-Slot 73
(0x49) des OrderBook-Proxys per `eth_getStorageAt`:
`eth_getStorageAt(<orderbook>, "0x49", "latest")` → die letzten 20 Bytes sind
die MarginAccount-Adresse. Gemessen: 0x2A68ba1833cDf93fa9Da1EEbd7F46242aD8E90c5
fuer alle 4 Maerkte — kein Extra-Setup je Paar.

## Markt-Parameter und Groessen

`Kuru.ParamFetcher.getMarketParams(provider, marketAddr)` liefert base/quote
Decimals, price/sizePrecision, tickSize. `minSize` ist on-chain 0 — die echte
Mindestgroesse steht in der API (`minsize`).

WICHTIG: Die Ordergroesse ist in BASIS-Asset-Einheiten kodiert (via
sizePrecision), NICHT in MON — die Config-Namen `tradeSizeMon`/`maxPositionMon`
sind fuer Nicht-MON-Maerkte irrefuehrend, die Werte sind trotzdem Basis-Einheiten
(WETH/cbBTC/XAUt0). Fuer Dry-Run-Tests ueber der Mindestgroesse und passend zur
Bankroll waehlen (z.B. WETH 0.01, cbBTC 0.0005, XAUt0 0.02).

## Multi-Markt-Code

Der Bot war hart auf MON-USDC verdrahtet. Parametrisiert: `MARKET_LABEL` +
`BASE_SYMBOL` env (Default MON-USDC/MON), die Modell-Prompt-Strings in
`src/model.ts` als Template-Literale, `state.market` in `src/trader.ts` aus
`config.marketLabel`. Launcher `run-market.sh <mon|weth|cbbtc|xaut0> [port]`
setzt MARKET/MARKET_LABEL/BASE_SYMBOL/MARGIN_ACCOUNT/TRADE_SIZE/MAX_POSITION/
MARGIN/BANKROLL. Alle Maerkte teilen `data/events.jsonl` — immer nur eins zur
Zeit laufen lassen, oder die zweite Instanz aus einem separaten cwd starten.

## Verifikation

Dry-Run gegen einen anderen Markt: `bun run src/index.ts` mit den env-Vars aus
einem Temp-cwd, ~40 s laufen lassen — die Logzeile muss den neuen Marktpreis
zeigen (WETH ~2506 USDC, nicht MON ~0.024) und Sim-Orders in den neuen
Basis-Einheiten posten. `bun test` gruen halten.
