# Prophet-Signal Spur

**Quelle:** CryptoPredictions-Papier (Sharif University 2023)

## Modell

Facebook Prophet war im Paper das beste Modell für Crypto-Preisvorhersagen:
- **Accuracy:** 0.71 (vs. ARIMA 0.72, aber MAE/RMSE viel besser)
- **MAE:** 83 USD (vs. ARIMA 1009, SARIMAX 1119, XGBoost 796, LSTM/GRU/RF ~1000)
- **RMSE:** 116 (vs. ARIMA 1163, SARIMAX 1391)
- **MAPE%:** 0.40 (vs. ARIMA 4.47, SARIMAX 5.48)

Prophet nutzt additive Zerlegung: `y = Trend + Saisonalität + Rauschen`

## Diese Spur

**Nicht** die Python-Prophet-Bibliothek (NumPy-Kompatibilität im Scanner-venv), sondern eine Nachbildung:

1. **Trend:** EMA30 der Schlusse (exponentiell geglätteter 30-Perioden-Durchschnitt)
2. **Saisonalität:** (Schluss - Trend) / Trend über 7-Tages-Zyklen
3. **Signal:** Long wenn EMA steigt + Saisonalität erkannt, Short wenn EMA fällt

**Einstieg:**
- Long: Trend nach oben (EMA > EMA[-1] um >0,1%) UND Saisonalität-Stärke > 0,2
- Short: Trend nach unten (EMA < EMA[-1] um >0,1%) UND Saisonalität-Stärke > 0,2

**Ausstieg:**
- Gegensignal: Trend-Umkehr (von Long -> Short oder Short -> Long)

## Parameter

- `trend_n: 30` — EMA-Periode (Tage)
- `saison_min: 0.2` — Mindeststärke der Saisonalität (0..1)
- `kerzen_zeitrahmen: "4H"` — 4-Stunden-Kerzen
- `kerzen_anzahl: 400` — letzte 400 Kerzen laden (~67 Tage)
- `mindest_kerzen: 60` — Signal erst ab 60 Kerzen (10 Tagen)

Instrument: BTC/ETH/SOL-USDT-SWAP, je 2 offene Plätze, Risiko 5 USD pro Position (10 USD Buchrisiko).

## Status

- **Papier:** Baseline gebaut, erste Tests nächster Zyklus
- **Live:** Nicht verfügbar (kein Live-Zweig, Prognosemodell)
- **Reifegrad:** Neu, CryptoPredictions-Paper dokumentiert, noch keine echten Handelsdaten

## Testen

```bash
cd Agenten/Handel/prophet_signal
python handeln.py --vorschau    # Zeigt das Signal ohne zu schreiben
python handeln.py --papier      # Schreib ins Papierbuch
python handeln.py --wachen      # Zeigt den Wachenstatus
```

## Vergleich mit klassik-Spuren

| Aspekt | prophet_signal | klassik_* |
|--------|---|---|
| **Modell** | Trend + Saisonalität | Technische Indikatoren (SMA, EMA, RSI, ...) |
| **Komplexität** | Additive Zerlegung | Einfache Kreuzungen |
| **Datenbasis** | CryptoPredictions-Paper | Pine-Vorlagen + Haus-Regeln |
| **Reifegrad** | Neu (02.10.2026) | Bewährt (seit 30.09.2026) |

Das Paper zeigt Prophet als stark, also erste Papierevaluierung zur Baseline.
