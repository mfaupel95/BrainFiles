# Oeffentliche Ersatz-Endpoints fuer Pro-gesperrte Datenquellen

Erfahrungen mit den Moon-Dev-Agenten (CoinGecko): Premium-Endpoints lehnen
free-Calls mit 10005 ab — auch auf `api.coingecko.com`, nicht nur auf
`pro-api.coingecko.com`.

| Pro-only (gesperrt) | Oeffentlicher Ersatz | Semantik-Verschiebung |
|---|---|---|
| `GET /coins/top_gainers_losers` | `GET /coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&price_change_percentage=24h`, dann im df filtern (`> 0`) + absteigend sortieren | Gewinner-Subset der Top-100 nach Marktkapitalisierung, keine 24h-Volumen-Rangliste |
| `GET /coins/list/new` | `GET /coins/markets?order=market_cap_asc&per_page=100` | „neue Coins" oeffentlich nicht verfuegbar — kleinste Marketcaps als Kandidaten; Verschiebung ausweisen |

Regeln:
- Spalten: markets liefert `current_price`, `total_volume`,
  `price_change_percentage_24h_in_currency` (nur mit Param
  `price_change_percentage=24h`), `symbol` klein — vor der Analyse auf die
  Namen umbenennen, die der Agent erwartet.
- Kopf: User-Agent setzen (nackte urllib wird 403; `requests` meist ok —
  ein Kopf schadet nie). `x-cg-pro-api-key`-Header nur setzen, wenn ein Key
  existiert.
- Rate: free praktisch ~5-10 Calls/min (429 ab ~6 Calls in 30 s gemessen),
  10.000 Calls/Monat. Ein Zyklus mit 6 Analysen (~14 Calls) braucht DELAY
  ~12 s + einen 15-s-Retry je 429er. Pro-Key (`COINGECKO_API_KEY`) hebt
  Limit und Kopf-Limits auf — dann head-Grenzen und DELAY zuruecknehmen.
- 429 ist ein behandeltes Fehlerbild: get_coin_data-aehnliche Funktionen
  geben {} zurueck und die Schleife springt weiter — Agent ueberlebt,
  einzelne Analysen fehlen. Das gehoert in den Bericht („x von y analysiert").
