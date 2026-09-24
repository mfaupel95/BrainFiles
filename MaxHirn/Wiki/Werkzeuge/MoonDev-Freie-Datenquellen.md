# MoonDev-Agenten: freie Datenquellen statt api.moondev.com

`api.moondev.com:8000` antwortet nicht mehr (gemessen 24.09.2026, kein
HTTP-Status, nur Connect-Timeout). Drei Agenten hingen daran, weil sie ihre
Datenreihen über `src/agents/api.py` (`MoonDevAPI`) holen.

## Loesung

`src/agents/api_frei.py` stellt **dieselbe Klasse mit derselben Schnittstelle**
bereit — gleiche Methodennamen, gleiche DataFrame-Spalten — und holt die Daten
aus oeffentlichen Boersen-Endpunkten. Sie versucht ZUERST die echte
MoonDev-API und schaltet nur um, wenn der Host nicht antwortet. Rueckweg: den
Import in den drei Agenten wieder auf `src.agents.api` stellen.

| Reihe | freie Quelle | Messung 24.09.2026 |
|---|---|---|
| Funding | Binance `/fapi/v1/premiumIndex` | 910 Symbole in EINEM Aufruf |
| Open Interest | Binance `/fapi/v1/openInterest` + `markPrice` | 5 Symbole, BTC 8,09 Mrd USD |
| Liquidationen | OKX `/api/v5/public/liquidation-orders` (je `uly`) | 300 Zeilen (BTC/ETH/SOL) |
| Token-Adressen | — | oeffentlich moeglich, aber kein Agent liest sie |

`/fapi/v1/allForceOrders` (Binance) antwortet **404** — der Endpunkt ist weg.
Liquidationen kommen deshalb von OKX; `sz` ist dort in **Kontrakten**, der
USD-Wert braucht `ctVal` aus `/api/v5/public/instruments`.

## Was NICHT ersetzbar ist

`get_copybot_follow_list` und `get_recent_transactions` sind MoonDevs EIGENE
Kopierhandels-Datenbank. Dafuer gibt es keine oeffentliche Quelle. Beide geben
bewusst `None` zurueck (nicht einen leeren DataFrame): die Agenten pruefen auf
`None` und ueberspringen den Zyklus, statt mit Nullwerten zu rechnen.

## Nachweis (jeder Agent einmal gefahren)

- `whale_agent`: `✨ 5 Open-Interest-Zeilen (Binance, frei)`, BTC-OI 8,09 Mrd /
  ETH 6,11 Mrd / Total 14,21 Mrd USD.
- `liquidation_agent`: `✨ 300 Liquidationszeilen (OKX, frei)`, Fenster 1 h
  LONGS 28.249,61 USD (6 Ereignisse), 4 h LONGS 314.626,55 USD (96 Ereignisse).
- `funding_agent`: `✨ 910 Funding-Saetze (Binance, frei)`.

## Fallen beim Start

- Die Agenten verlangen `OPENAI_KEY` **und** `ANTHROPIC_KEY` in der Umgebung,
  schon im Konstruktor — ohne sie sterben sie vor dem ersten Datenabruf.
- Ohne `python -u` bleibt die Ausgabe im Puffer: ein mit `timeout` abgebrochener
  Lauf zeigt dann **leere** Logs, obwohl der Agent gearbeitet hat.
- Die LLM-Seite laeuft ueber die lokale Bruecke
  (`DEEPSEEK_BASE_URL`/`OPENAI_BASE_URL` = `http://127.0.0.1:11499/v1`), nicht
  gegen die toten Cloud-Schluessel (siehe `Ollama-Bruecke.md`).

`fundingarb_agent` nutzt `api.py` NICHT (eigene Datenwege) — bei den
„datenlosen" Agenten war er falsch mitgezaehlt.