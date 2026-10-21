# Equity und Waehrung: das Konto entscheidet, nicht das Symbol

Erfahrung vom 21.10.2026 am omnitrade2-Live-Loop (SOL-USD_UM_XPERP-310404, OKX EWR).

## Der Befund

Nach dem WebSocket-Reconnect konnte der Lauf keinen einzigen Auftrag absetzen:

```
Risk guard rejection: drawdown violation: current 4.688.672,01 % exceeds limit 10.00 %
orders_placed 1 · orders_rejected 3 · state running
```

Die Zahl schwankte mit dem unrealisierten PnL (4.688.672 / 3.907.226 / 4.376.093) und
nicht mit dem Kontostand — der erste Hinweis darauf, dass die Equity falsch gerechnet war.

## Die Ursache

`pair_equity(account, base, quote, price)` nimmt die Quote **des Symbols** und sucht sie
im Kontostand. Bei XPERP heisst die Quote `USD`; das Konto fuehrt aber **USDC**. Auch das
Instrument selbst meldet `settleCcy: USD` — erst `/api/v5/account/config` nennt die
Wahrheit: `settleCcy: USDC`.

Ohne Bestand faellt die Equity auf den uPnL zusammen. Der Guard merkt sich den hoechsten
Wert als Peak; war der PnL einmal positiv (Peak ≈ 0,00) und danach negativ, wird

```
drawdown = (peak - equity) / peak * 100
```

zum Millionenprozent-Wert. Folge: **jeder** Auftrag wird abgelehnt, waehrend der Status
gesund aussieht (`state: running`, `orders_placed: 1`).

## Die Regel

1. Fuer Equity, Margin und Groessenregeln die **Abrechnungswaehrung des Kontos** nehmen
   (`/account/config` → `settleCcy`). Nicht die des Instruments, nicht die Quote des
   Symbols. Reihenfolge im Code: Quote → Kontowaehrung → Instrument-Waehrung, und die
   erste Waehrung mit Bestand gewinnt (`live_loop::risk::bewertungs_waehrung`).
2. Ergibt eine Rechnung **0**, ist zuerst die Waehrung zu pruefen, dann die Daten.
3. Der Guard steigt bei `peak <= 0` frueh aus (`guard.rs`). Ein Test, der die Waehrung
   prueft, braucht deshalb einen **positiven Peak vor dem Verlust** — sonst beweist er
   nichts (eigener Fehlversuch: der erste Test war mit `peak = 0` immer gruen).

## Die zweite Lehre desselben Laufs

Das Buch zaehlte Auftraege selbst (`net_quantity`) und erfuhr nie, dass die Position an
der Boerse geschlossen wurde: Buch `-0.1 SOL`, Boerse `pos = 0`. Seit dem Fix liest der
Loop die Position **je Kerze** ueber `position_snapshot`; scheitert der Abruf, bleibt der
alte Wert stehen und es wird gewarnt (nie stillschweigend auf 0).

## Belege

- `Werkstatt/omnitrade-pr`, Commits `669484f` (Equity + Buch) und `abf54a6` (Kontowaehrung
  vor Instrument-Waehrung), Branch `hermes/okx-reconnect-20261021`.
- Tests: `equity_nimmt_die_abrechnungswaehrung_wenn_die_quote_fehlt`,
  `xperp_auftrag_wird_nicht_am_erfundenen_drawdown_abgelehnt`,
  `buch_uebernimmt_die_boersenposition_ohne_eigenen_auftrag`;
  Gegenproben: Regel aus → rot, Waehrung nicht durchgereicht → 1 statt 2 Auftraege.
- Laufender Nachweis im Log: `SOL-USD_UM_XPERP-310404: Equity-Bewertung in USDC`.

Siehe auch [[Boersen-und-Schluessel]] und [[Dauerlauf-Tode]].
