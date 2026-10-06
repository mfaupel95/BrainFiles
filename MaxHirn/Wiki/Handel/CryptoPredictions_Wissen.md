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
- **Bestätigt 13.09.2026 (Max):** Das Freivolumen gilt für **alle Paare** und ist
  an das Abo gebunden. Daraus folgt eine neue, **nicht-marktliche**
  Abhängigkeit: Fällt das Abo weg, kehrt die 0,80-%-Runde zurück — jede Spur,
  deren Rechnung auf 0 % Gebühr gebaut wurde (`orbk`), muss dann neu bewertet
  werden. Das ist ein Kostenschalter außerhalb des Marktes und gehört in jede
  Live-Betrachtung als eigenes Risiko, nicht nur als Fußnote.

## Eigene Kursdaten: Qualitaet und Grid-Messungen (13.09.2026)

**Unmoegliche Kerze in `daten/BTC-USD.csv`.** Die letzte Zeile (2026-08-10) hat
ein Close UNTER dem Tagestief (`o=64848.91 h=65278.34 l=63992.34 c=63854.66`).
Jede Auswertung dieser Reihe muss die Zeile verwerfen und die Zahl der
tatsaechlich gerechneten Kerzen ausweisen; der Nautilus-`BarDataWrangler`
bricht daran ab. 4345 von 4346 Zeilen sind brauchbar.

**Zwei lokale Kursreihen fuer Backtests:**
- `kerzen_BTC-USDT_1H_8760.json` - 8800 Stundenkerzen (2025-08-23..2026-08-24),
  Liste `[ts_ms, open, high, low, close]`, KEIN Volumen (Platzhalter setzen).
  Kurs fiel im Zeitraum von 116.447 auf 79.240 (-32 %).
- `daten/<SYMBOL>.csv` - Tageskerzen ab 2014 (BTC-USD 4346 Zeilen),
  Spalten `Datum,Open,High,Low,Close`, kein Volumen.

**Was ein Grid in diesen Reihen wirklich tut** (Nautilus-Backtest,
`nautilus/backtest_grid.py`, Aufruf und Zahlen im README dort):

| Marktlage | Grid | Schlichtes Halten |
|---|---|---|
| BTC 1H, -32 % Absturz (12 Stufen) | -17,70 % | -31,95 % |
| BTC Tages, 12 Jahre (10 Stufen) | +19,9 % | +14.079 % |
| 3 Seitwaerts-Fenster (je 10 Stufen) | +3,2 / +5,5 / +14,3 % | +0,02 / +0,11 / +0,29 % |

Daraus die belastbaren Saetze: Ein Grid verliert weniger als Halten, wenn der
Markt faellt, und gewinnt, wenn er seitwaerts laeuft - in einem Trend nach oben
ist es ein Bremsklotz mit Gebuehren. Und: **doppelt so viele Stufen verdienten
in allen drei Seitwaerts-Fenstern die HAELFTE** (Gebuehren wachsen mit der
Frequenz: 131 Fills = 147 USDT = 1,5 % des Einsatzes). Der Stufenabstand muss
ueber den Gebuehren beider Seiten liegen, sonst verliert das Grid unabhaengig
vom Kurs.
Die Zyklen allein sind keine Aussage: im Absturz verdienten die 12 Zyklen
+1.022 USDT, der liegengebliebene Bestand kostete -2.762 USDT.

## Ablehnungen protokollieren, nicht nur Buchungen (14.09.2026)

**Der Befund.** Aus 107 geschlossenen Runden des Spiegel-Buchs war nur noch
abzuleiten, in welchem Band das Nachahmen getragen hat (daraus kam die
Obergrenze der Marktkapitalisierung: unter 1 Mio Ø +16,5 %, darueber Ø -12 bis
-22 %). Was NICHT ableitbar war: wie viele Kandidaten an welchem Tor haengen
blieben. Ein volles Buch und ein zu strenges Tor sahen im Journal gleich aus -
beide erzeugen nur "keine neue Kopie". Genau diese Verwechslung haette den
naechsten Schluss falsch gemacht (an der Marktkapitalisierung drehen, waehrend
das Buch seit Stunden voll war).

**Die Regel.** Ein Papierbuch schreibt neben das Journal ein
Ablehnungsprotokoll: je Zyklus die Lage (wie viele Signale kamen mit, woran
scheiterten sie - reine Rechnung ueber alle Signale) UND die Entscheidung (was
das Buch mit den bewerteten Kandidaten tat, inklusive Platzmangel). Ein
Einzelkandidat wird nur dann mit Kennung protokolliert, wenn er bis zur
teuersten Pruefung gekommen ist (Risiko-Scan) - der Rest steht als Zahl je
Grund, sonst waere das Protokoll bei 700 Signalen je Zyklus unlesbar.

**Warum eine eigene Datei.** Die Leser des Journals zaehlen Zeilen als
Buchungen (`bilanz()` rechnet jede Nicht-`eroeffnen`-Zeile als Runde,
`buchauswertung` je Aktion). Eine Ablehnung waere dort eine erfundene Runde und
wuerde die Bilanz faelschen. Das Protokoll liegt daneben, geht wie das Journal
mit nach `journal_zweitziel` und wird von `spiegelstand.py` byte-genau
mitgeprueft (`ZUSATZ`).

**Zwei Fallen, beide teuer.** (1) Dasselbe Signal steht Stunden im Feed - ohne
Sperre je (Transaktion, Grund) traegt das Protokoll denselben Kandidaten alle
15 Minuten erneut ein und die Zaehlung ist ein Vielfaches der Wahrheit. (2) Die
Zaehlung darf keine ZWEITE Fassung derselben Grenze sein: die billigen Tore
(Alter, Marktkapitalisierung, doppelte Kopie) stehen in `spiegel._vorpruefung`
einmal und werden von Buch und Zaehlung gemeinsam benutzt; ein Test haelt fest,
dass ein billiges Tor keinen Abruf kostet.

**Lesen.** `spiegel.py --ablehnungen [--stunden N]` zeigt Lage, Entscheidung und
Einzelfaelle und stellt am Ende beide Seiten gegen: `kaufbar = bewertet + nicht
mehr erreicht`. Geht die Zeile nicht auf, ist ein Zweig im Zyklus nicht
gezaehlt - "Achtung" ist dann die ehrliche Ausgabe, nicht eine gerundete Zahl.
