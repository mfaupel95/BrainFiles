# trendwende_btc — BTC short, sobald der Trend auf 1H dreht

Auftrag Max, 21.09.2026: *„Baue einen Agenten, der BTCUSD xperp short setzt,
sobald der Trend wendet."*

## Die Regel (eine, nachrechenbar)

| Schritt | Was gilt |
|---|---|
| Daten | BTC-Kerzen **1H**, 400 Stück, OKX öffentlich (`scanner/okx.kerzen`) |
| Trend | `supertrend(k, n=10, faktor=3.0)` aus `xperp/indikatoren.py` — dieselbe Quelle wie die Spur `supertrend` |
| **Wende** | Richtung wechselt von **+1 auf −1** auf der letzten **abgeschlossenen** Kerze. Nur der *Wechsel* zählt — sonst stünde die Spur jede Kerze wieder short |
| Filter | Schlusskurs **unter der EMA200**: eine Wende gegen einen intakten Aufwärtstrend ist meist ein Rücksetzer |
| Einstieg | **short**, Stop und Ziel aus `spur_buch` (Stop 4 %, Ziel 2R) |

Gemessen am 21.09.2026 22:1x: BTC 86.664 USD, EMA200 79.909 USD, SuperTrend
**+1** → kein Signal. In den letzten 200 Kerzen drehte der Trend **3×** nach
unten — die Spur hat also Gelegenheiten, ohne im Minutentakt zu feuern.

## Buch und Grenzen

- **Papier.** Kein Live-Zweig; `--live` verweigert mit Grund. Der Haken
  `freigabe.erfuellt` bleibt **false** (Handelsregeln Punkt 3: scharf schalten
  von Hand).
- Buch, Ratsche (`drawdown_halbierung_usd 5.00` = 1,0 × Buchrisiko), Vorfilter
  und Spiegelung kommen aus **`Handel/spur_buch.py`** — eine Buchhaltung für
  alle Buch-Spuren.
- Risiko 5 USD je Position, **1 Platz** (es gibt nur ein Instrument),
  Stop 4 %, Ziel 2R, Kill-Schwelle 20 USD.
- Bedingung 4: Journal und Zustand nach `Q:\Handel_Journal\trendwende_btc`.

## Aufruf

```bash
cd Agenten/Handel/trendwende_btc
../scanner/.venv/Scripts/python.exe handeln.py --vorschau   # rechnen, nichts schreiben
../scanner/.venv/Scripts/python.exe handeln.py --papier     # Papierzyklus
../scanner/.venv/Scripts/python.exe handeln.py --wachen     # Wachenstand
cd tests && ../../scanner/.venv/Scripts/python.exe -m unittest test_signal
```

## Was noch fehlt (bewusst)

1. **Zweiter Ausstieg über das Signal:** steht die Regel auf „short, wenn der
   Trend dreht", gehört als Ausstieg auch der Rückdreh dazu. Heute beenden nur
   Stop, Ziel und die Frist. Kommt nach den ersten gemessenen Runden — vorher
   wäre es eine Regel ohne Zahlen.
2. **Kein Live-Pfad** (wie `supertrend`): `handel_erlaubt` ist wirkungslos,
   solange kein Orderaufruf existiert. Wer sie live nimmt, braucht zuerst einen
   Orderweg und die Sperrenkette — Muster in `handel-spuren/references/`.
