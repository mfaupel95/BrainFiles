# llm_stunde

Papierspur auf 1H-Kerzen, BTC/ETH/SOL-USDT-SWAP, nur Long. Drei Indikator-Kandidaten, je in zwei Armen:

| Variante | Kandidat (Einstieg long) | Ausstieg |
|---|---|---|
| `ema1h` | EMA33 kreuzt über EMA135 | Gegenkreuz |
| `st1h` | SuperTrend (ATR10 × 3,0) wechselt auf long | Wechsel auf short |
| `rsi1h` | RSI14 kreuzt über 30, Schluss über EMA200 | RSI14 über 55 |

- **R-Arm:** Einstieg, sobald der Kandidat steht.
- **L-Arm:** Einstieg nur bei `BUY` mit Konfidenz ≥ 70 % vom lokalen Modell (`phi4-mini` über die Brücke, Port 11499). Ausfall heißt kein Einstieg.

Stop: fest 2,5 % (Hausstandard von `klassik_ema`, innerhalb 1,5 bis 5 %). Kein festes Ziel. Ausstiege sind in beiden Armen regelbasiert. Jeder Strang schreibt nach `laeufe/<variante>-<arm>/`, das LLM-Protokoll nach `llm_entscheide.jsonl`.

Parameter stammen aus Hausläufen (`ema_cross_h1.py`, `klassik_*`) und sind nicht neu gefittet. Die Spur ist Papier: `handel_erlaubt` bleibt `false`, `--live` wird verweigert.

Aufruf: `python handeln.py --vorschau | --papier | --wachen`

Plan und Begründung: `Werkstatt/Projekte/plan-llm-stunde-1h-2026-10-12.md`.
