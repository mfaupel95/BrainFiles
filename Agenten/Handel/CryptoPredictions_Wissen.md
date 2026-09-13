# Wissen über CryptoPredictions Toolkit

## Überblick
CryptoPredictions ist ein Open-Source-Toolkit zur Vorhersage in Python. Implementiert von Amirhossein Alimohammadi und Ahmad Nosratbakhsh, ermöglicht es Benutzern, Vorhersagen basierend auf historischen Daten zu treffen und dabei verschiedene Modellierungsansätze zu verwenden.

## Hauptbestandteile des Toolkits

### Hydra Configurations
- **configs**: Hauptverzeichnis für Konfigurationsdateien, die verschiedene Aspekte des Toolkits steuern.
- **modularer Aufbau**, der eine klare Struktur in Bezug auf Datensätze, Modelle, Optimierer, Scheduler und Visualisierungen aufweist.

### Wichtige Dateien
- **main.yaml**: Hauptkonfigurationsdatei für das Datenmodul.
- **modelfiles**: Beinhaltet spezifische Modellparameter für verschiedene Algorithmen, wie z.B. LSTM, GRU.
- **optimizers**: Bezieht sich auf die Konfiguration von Optimierungsalgorithmen (z.B. Adam, SGD).
- **dataset_loader**: Konfigurationsdateien für das Laden verschiedener Datensätze (z.B. Bitmex, CoinMarket).

### Module und Funktionalitäten
- **vorschlag.py**: Erzeugt Vorschläge basierend auf historischen Daten und Marktanalysen.
- **lauf.py**: Orchestriert die verschiedenen Teile des Toolkits und führt die Hauptlogik aus.
- **digest.py**: Führt wöchentliche Analysen durch und generiert Berichte.

### Nutzung
Das Toolkit erfordert eine Konfiguration über YAML-Dateien und ist darauf ausgelegt, mit verschiedenen Datensätzen und Modellen zu arbeiten, während es beständig aktualisiert und optimiert wird.

## Vermerk im Handelsverzeichnis
Wissen über die Funktionsweise und Implementierung von CryptoPredictions sollte im Handelsverzeichnis vermerkt werden, um den Informationsaustausch und das Lernen zu erleichtern.

## Historische Marktdaten für Krypto (Stand 13.09.2026)

Übersicht über bezugsfähige Quellen für historische OHLCV-Daten und was davon
bereits lokal liegt. Reihenfolge nach Eignung für die hiesige Umgebung (lokaler
Cache, Börsen-Kerzen, dann Datensätze).

### Bereits lokal vorhanden

| Datei | Inhalt | Quelle |
|---|---|---|
| `Handel/daten/*.csv` | Tages-OHLCV je Ticker, `Datum,Open,High,Low,Close` | yfinance (`kursdaten.py`, Cache max. 12 h alt) |
| `Handel/kerzen_BTC-USDT_1H_8760.json` | 8.800 Stundenkerzen BTC-USDT, 23.08.2025–24.08.2026, je Kerze `[ts_ms, open, high, low, close]` | OKX-Format (Zeitstempel in Millisekunden) |

### Börsen-APIs (authentisch, kostenlos, ohne Login)

- **OKX `GET /api/v5/market/history-candles`** — historische Kerzen; Limit je
  Abruf 100, für ältere Daten paginiert über `after`/`before`. Für SWAP-Reihen
  `instId` voll angeben (z. B. `BTC-USDT-SWAP`). Es gibt zusätzlich eine
  Download-Seite für historische Marktdaten (Candlestick ab Juli 2023).
- **Binance `GET /api/v3/klines`** (Spot) bzw. `/fapi/v1/klines` (USDT-M
  Futures) — bis zu 1.000 Kerzen je Abruf, paginiert über `startTime`/`endTime`.
  Vollständige Archivdumps (monatlich, alle Intervalle) im öffentlichen
  Repository `binance/binance-public-data` auf GitHub.
- **Kraken** — OHLCVT-CSVs je Paar und Intervall (1 bis 1440 Minuten) als ZIP
  zum Download, ab Marktstart des Paares. Lücken = Intervalle ohne Trades.

### Datenportale und Datensätze

- **CryptoDataDownload** (`cryptodatadownload.com`) — kostenlose OHLCV-CSVs
  seit 2017, täglich/stündlich/1-Minute, ohne Login und ohne Rate-Limit;
  Deckung über mehrere Börsen (Binance, Bitstamp, Gemini, Bitfinex, …),
  Aktualisierung täglich 00:00 UTC. Für das CryptoPredictions-Datenmodul
  (`dataset_loader`) direkt als CSV verarbeitbar.
- **CryptoDatum** (`cryptodatum.io`) — OHLCV-CSV/Excel, mehr als 200 Paare.
- **Kaggle** — z. B. „BITCOIN Historical Datasets 2018–2026 (Binance API)"
  (15-Minuten-Kerzen, ~45 MB); daneben viele ältere Datensätze mit
  unterschiedlicher Aktualität und Qualität — vor Nutzung prüfen, bis wann
  die Daten reichen und ob Zeitstempel konsistent sind.

### Empfehlung

Für Vorhersage- und Backtest-Zwecke im Handel: **Börsen-APIs (OKX/Binance)
bevorzugen** — authentische Kerzen, kein Datenanbieter-Risiko, Intervalle frei
wählbar. `CryptoDataDownload` als CSV-Ergänzung für lange Historien, wo die
Börsen-API paginieren müsste. Kaggle-Datensätze nur für einmalige Analysen,
nicht als laufende Datenquelle (veralten und sind oft unvollständig).

## Kraken Pro: Gebührenfreivolumen (Stand 13.09.2026)

Max führt das Kraken-Pro-Abo. Danach ist das Handelsvolumen **bis 10.000 EUR im
Monat gebührenfrei**; darüber gilt die gemessene Staffel vom 02.09.2026 (Taker
0,40 %, Maker 0,25 %). Der **Spread bleibt immer** — er ist die Kostenposition,
die auch das Abo nicht aufhebt.

Was das für die Spuren bedeutet:

- **kraken (Spur 3, stillgelegt):** Die Stilllegung vom 03.09.2026 beruht nicht
  auf der Gebühr allein — ohne sie gerechnet blieb der beste Wert bei **−0,57 %
  je Runde** (720 Tageskerzen, 8 Paare). Das Abo macht die Spur also **nicht**
  tragfähig; sie bleibt zu, bis ein Signal auch ohne Gebühr über null kommt.
- **orbk (Papier):** Sein Buch rechnet im OANDA-Modell (SPEC.md) **ohne
  Kommission** — nur Spread + Slippage. Für Kraken-Spot wäre das ein
  Modellfehler; innerhalb der 10.000 EUR ist es durch das Abo gedeckt. Darüber
  ist die Rechnung zu optimistisch.
- **Frequenzdeckel (bestätigt 13.09.2026):** Das Freivolumen zählt auf das
  **Handelsvolumen** — Kauf und Verkauf zusammen. Eine Runde zählt damit
  doppelt: 10.000 EUR sind bei 50 EUR Einsatz rund **100 Runden im Monat**
  (etwa 3 am Tag), bei 10 EUR rund 500. Minuten- oder Sekundenhandel sprengt
  dieses Budget in Tagen. Wer das Freivolumen als Vorteil nutzt, nutzt es für
  **mehr Runden aus demselben Signal**, nicht für höhere Frequenz.
- **Offen** (vor einem Live-Gedanken in der App prüfen): für welche Paare das
  Freivolumen gilt und ob es an das Abo-Modell gebunden bleibt.
