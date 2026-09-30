# omnitrade — Haus-Spur auf den Rust-Laeufen

**Was sie tut:** liest die Statusdateien der Rust-Laeufe in
`Werkstatt/omnitrade/status/` und spiegelt deren **Position** in ein eigenes
Buch. Der Rust-Lauf entscheidet (das `.omni`-Skript), diese Spur fuehrt aus —
im Live-Zweig ueber den Haus-Orderweg auf Kraken.

Angelegt am 30.09.2026 (Auftrag Max: „nur noch omnitrade auf kraken handel
erlaubt"). Die Sperrseite dieses Auftrags war schnell umgesetzt, die
Freigabeseite fehlte: `omnitrade-exchange/src/` kennt nur `binance` und `okx`,
`omnitrade-cli/src/commands/live.rs:33` weist jedes andere `--exchange` ab —
danach handelte niemand mehr auf Kraken. Weg B ist der kleinere: **kein
Kraken-Adapter in Rust** (zweiter Schluessel, zweiter Nonce-Zaehler), sondern
der erprobte Spot-Weg `Handel/kraken/kraken.py` mit Preisrundung je Paar,
Stop-Logik und Freigabebeleg.

## Aufruf

```
cd Agenten/Handel/omnitrade
../scanner/.venv/Scripts/python.exe handeln.py --vorschau
```

`--vorschau` rechnet und schreibt nichts, `--papier` bucht, `--live` laeuft
ueber die Sperrenkette des gemeinsamen Kerns (`spur_buch.sperren_live`),
`--wachen` zeigt die Grenzen.

## Die Regel

| Was | Woher | Wann |
|---|---|---|
| Einstieg long | `net_quantity > 0` **und** Lauf laeuft wirklich | Statusdatei frisch **und** PID lebt |
| Ausstieg `omnitrade flat` | Lauf meldet keine Position mehr | `net_quantity 0` bei `running`/`stopped` |
| Notausstieg | `stop_prozent` 8 % | immer (Boersen-Stop im Live-Zweig) |

- **Gespiegelt wird der Zustand, nicht die Orderliste.** `recent_orders` ist ein
  Ringpuffer mit hoechstens 20 Eintraegen (`MAX_ORDERS` in `status.rs`); wer
  daraus Ereignisse nachzaehlt, verliert bei einem Ausfall alles dazwischen.
- **`state: running` ist kein Beweis.** Nach einem harten Ende bleibt die Datei
  mit einer toten PID auf `running` stehen (30.09.2026 lag
  `live_adx_macd_BTCUSDC.json` zwei Stunden so herum). Der Einstieg verlangt
  deshalb zwei Zeugen; der Ausstieg greift auch bei `stopped` (die CLI verkauft
  beim Beenden), nie bei `starting`/`error`.
- **Kein Short.** omnitrade handelt nur long; eine Short-Seite waere eine zweite
  Strategie neben der bestellten.

## Dateien

| Datei | Zweck |
|---|---|
| `lesen.py` | Statusdateien lesen, Symbol zerlegen, zwei Zeugen — rein lesend, wirft nie |
| `handeln.py` | Quelle, Signal, Ausstiegsgrund, Boersenbindung; ruft `spur_buch.zyklus` |
| `wachen.json` | die Grenzen (einzige Quelle der Zahlen) |
| `tests/test_omnitrade.py` | ohne Netz, mit Attrappen-Statusordner |

## Stand

Papier, `handel_erlaubt=false`. Der Live-Weg ist verdrahtet und in der Vorschau
sichtbar gesperrt; bindend waere ohnehin das Guthaben (Kraken-Konto ~25 USDC,
Tor 60). Der Nachweis der Kette steht in `tests/` (Einstieg, Halten, Ausstieg,
Leiche, toter Lauf) — im Betrieb bucht die Spur, sobald ein Rust-Lauf eine
Position haelt.