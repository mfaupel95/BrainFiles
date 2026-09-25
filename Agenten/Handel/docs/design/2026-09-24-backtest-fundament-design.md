# Backtest-Fundament für die Handels-Spuren — Design-Spezifikation

**Datum:** 2026-09-24
**Status:** Design genehmigt (Max, 2026-09-24), Spezifikation zur Prüfung
**Betrifft:** `Agenten/Handel` — neue Dateien `historie.py`, `replay.py`, `optimieren.py`,
`spur_opt.json`; Nachrüsten von Daten-Nähten in einzelnen Spuren

## Zweck

Die Spuren liefern wenige Runden: rund eine Handelsrunde je Spur und Tag. Damit
ist keine belastbare Aussage möglich — die Hausauswertung rechnet erst ab `MIN_RUNDEN=8`,
und `kosten_wendepunkt.py` sagt selbst, dass eine Zahl unter acht Runden ein
**Befund, keine Messung** ist. Ziel sind mehrere hundert Runden je Spur aus
historischen Daten, **zusätzlich** zu den Live-Daten.

Zwei Verwendungen, beide ausdrücklich gewünscht (Max, 2026-09-24):

1. **Messen** — Trefferquote, Erwartungswert, `f_max` je Spur auf großer Stichprobe.
2. **Optimieren** — Parametersuche je Spur mit In-Sample-/Out-of-Sample-Trennung.

**Nicht** gewünscht: historische Runden in die Freigabe-Bedingungen einrechnen.
Backtest-Runden bleiben strikt getrennt und zählen **nicht** für
„50 Runden" oder „netto positiv" aus `Wissen/Handelsregeln.md`.

## Ist-Stand (gemessen 2026-09-24)

Vorhanden und wiederverwendbar:

| Baustein | Was er schon tut | Grenze |
|---|---|---|
| `backtest_prognose.py` | fährt die **echten** Spurenmodule (squeeze, wavetrend, macd_mtf, supertrend) über den Pfad geladen, `SCHREIBEN=False`, `journal()` abgefangen | nur 4 Spuren, eigener Kerzenabruf |
| `bt_varianten_fast.py` | rechnet Indikatoren vor statt je Schritt — schnell | eigenes Kerzenformat |
| `bt_oos.py` | erste/zweite Hälfte als In-/Out-of-Sample | nur 7000 h, nur BTC |
| `backtest_urteile.py` | fährt gitter/orbk/nautilus mit den Werten aus deren `wachen.json`, schreibt `backtest_bestanden` | dreispurig, kein gemeinsames Journal |
| `spur_buch.zyklus(ordner, quelle, signal, modus, ereignis_name, ziel=None, zusatz_ausstieg=None, datenlage=None)` | nimmt `quelle` und `signal` **als Parameter** | — |
| `spur_buch.zeit_quelle`, `spur_buch.pfade(ordner)` | Uhr und alle drei Buchpfade aus EINER Wurzel | — |

**Die Naht existiert bereits.** Gemessen: 18 Spuren tragen
`kerzen_quelle` / `zeit_quelle` / `funding_quelle` / `quelle_override`
(`gitter`, `iv_waelle`, `macd_mtf`, `mosaic`, `orb`, `orbk`, `squeeze`,
`supertrend`, `wavetrend` sowie `moondev_*` in neun Spuren), und 11 Spuren
rufen `spur_buch.zyklus` auf (`iv_waelle`, `liq_wand`, `robinhood_radar`,
`trendwende_btc` und sieben `moondev_*`). Kein Modul-Patchen nötig: der Replay
reicht `quelle` und `signal` als Argumente durch.

Sonderfall `xperp`: **keine** stündliche Naht für den Perp-Zweig, aber
`tages_kerzen_quelle` für seine Aktien-/Rohstoffkerzen — dieser Zweig ist über
die vorhandenen `daten/*.csv` (yfinance, täglich) schon nachrechenbar.

Datenlage und Grenzen (gemessen, nicht geschätzt):

- **Binance public klines, kein Schlüssel:** BTCUSDT 1H hat Kerzen ab
  **2017-08-17** (`1502942400000`). **18.000 Kerzen** (2 Jahre 1H) in **10,4 s**.
- **Erster echter Abruf, gemessen 2026-09-25:** 3 Instrumente × (1H + 4H + 1D)
  = **194.628 Kerzen in 3 min 12 s** (≈ **1.000 Kerzen/s**), 12 MB auf Platte,
  Zeitraum **2021-01-01 bis 2026-09-25**. Daraus folgt für alle Instrumente:
  20 × (1H + 4H) ≈ **21 Minuten**, ~100 MB. Die frühere Schätzung „4 Minuten"
  war um den Faktor 5 zu optimistisch — die Abrufgeschwindigkeit hängt an der
  Netzlatenz je Seite (1000 Kerzen), nicht an der Kerzenzahl allein.
- **Funding-Historie** (`/fapi/v1/fundingRate`) frei ab **2020-08-01**.
- **Binance-Paar-Abdeckung: 19 von 20** geprüften Instrumenten. Fehlt: **MATIC**
  (heute POL) — für MATIC bleibt nur der lokale Altbestand.
- **OKX-OI-Historie ist nicht abrufbar** (`rubik/stat/contracts/open-interest-volume`
  → `50030 Illegal time range`) → `moondev_whale` ist nicht nachrechenbar.
- Bestehender Kerzenvorrat: `daten/backtest_kerzen/` (OKX, ~3000 Stundenkerzen =
  125 Tage), `kerzen_BTC-USDT_1H_8760.json` (1 Jahr BTC), `daten/*.csv`
  (yfinance, täglich, mehrere Jahre).

**Gebühren in `wachen.json` (gemessen):** 9 Spuren tragen sie schon —
`iv_waelle`, `liq_wand`, `swap`, `trendwende_btc`, `xperp` = `0.0005`;
`kraken`, `moondev_marktlage`, `mosaic` = `0.006`; `robinhood_radar` = `0.01`.
Die übrigen tragen **keine**. Der heutige Backtest nimmt deshalb pauschal
0,10 % je Seite — für Perp-Spuren der zwanzigfache Satz.

## Architektur

Drei Einheiten, jede mit einer Aufgabe. Keine kennt die Interna der anderen;
`replay.py` liest die Spuren, aber die Spuren wissen nichts vom Backtest.

### 1. Datenschicht — `Agenten/Handel/historie.py`

- **Quelle:** Binance public (Spot `/api/v3/klines`, Futures `/fapi/v1/fundingRate`).
  Kein Schlüssel, keine Kosten. Präzedenz im Haus: `nautilus/backtest.py` nutzt
  schon `BTCUSDT.BINANCE`.
- **Speicher:** `daten/historie/<symbol>_<takt>.json`, Reihen
  `[ts, o, h, l, c, v]`, aufsteigend, `ts` in Millisekunden — **dasselbe Format,
  das `backtest_prognose.kerzen_holen()` heute liefert**, damit die Kerzen ohne
  Adapter in jede Naht passen.
- **Zeitraum:** `2021-01-01` bis heute, Takte **1H** und **4H** (1D als Zugabe),
  Instrumente = Vereinigung der `instrumente` aus allen `wachen.json`.
  Fünf Jahre decken Bären-, Bullen- und Seitwärtsphasen.
- **Abrufregeln:** appendend (vorhandene Zeitstempel bleiben, nur Neues hinten
  an), Sperrdatei gegen zwei gleichzeitige Läufe, `daten/historie/_stand.json`
  mit Herkunft, Abrufzeit und Umfang je Reihe.
- **Mapping OKX→Binance** in EINER Tabelle (`BTC-USDC` → `BTCUSDT`,
  `BTC-USDT-SWAP` → `BTCUSDT`, `XBT/USD` → `BTCUSDT`). Ein unbekanntes Paar ist
  ein **harter Fehler**, kein stiller Ersatz (Hausregel).
- **Proxy-Wahrheit:** Binance-Kerzen sind nicht der OKX- oder Kraken-Kurs. Jedes
  Ergebnis trägt `kerzenquelle: binance`; es wird nie als Börsenkurs der Spur
  ausgegeben. Aktien und Rohstoffe (xperp) haben kein Binance-Paar und bleiben
  bei den Tageskerzen aus `daten/*.csv` — xperps Aktien-/Rohstoffzweig ist damit
  nur auf Tagesbasis nachrechenbar, nicht stündlich.

### 2. Replay-Kern — `Agenten/Handel/replay.py`

Der Kern liefert **nur Zeit und Daten**. Entscheiden tut die Spore.

- **Anschluss:** Spore über den Pfad laden (`importlib`, Muster
  `backtest_prognose.lade()`), ihre `signal()`-Funktion nehmen und
  `spur_buch.zyklus(backtest_ordner, historische_quelle, signal, "papier", …)`
  aufrufen. Für die vier Indikator-Spuren mit eigenem `lauf()` stattdessen die
  Nähte `kerzen_quelle` und `zeit_quelle` setzen — beide Wege sind vorhanden,
  keiner braucht eine Änderung an der Spore.
- **Buch umbiegen:** je Lauf ein eigener Ordner `daten/backtest/<spur>/` mit
  Kopie der `wachen.json`, eigener `zustand.json`, eigenem `handelsjournal.csv`.
  Der Replay schreibt **nie** in `<spur>/handelsjournal.csv`, `<spur>/zustand.json`
  oder `Q:\Handel_Journal\…`. Ein Test nach dem Modulwächter-Muster beweist das.
- **Takt:** je Kerze ein Zyklus. `--genau` ruft die Spore je Schritt auf;
  `--schnell` rechnet Indikatoren vor (Begründung des Verfahrens steht in
  `bt_varianten_fast.py`) und ist nur erlaubt, wo das Signal ausschließlich von
  Werten am aktuellen Index abhängt. Standard ist `--genau`.
- **Kosten wahr:** Gebühr je Spur aus ihrer `wachen.json` (`gebuehr_taker`);
  fehlt sie, gilt der Satz der Börse der Spur — OKX Spot `0.001`, OKX Perps
  `0.0005`, Kraken `0.006`. Ein pauschaler 0,10-%-Default entfällt. Ausgewiesen
  wird immer brutto **und** netto. Funding wird bei Perp-Spuren berechnet.
- **Kennzahlen:** EINE Funktion für Backtest und Betrieb (aufbauend auf
  `kosten_wendepunkt.py` und der Rundenrechnung aus `auswertung_alle.py`) — zwei
  Umsetzungen wären zwei Wahrheiten. Ausgabe je Spur: Runden, Trefferquote,
  Brutto/Netto je Runde, `f_max`, längster Rücklauf, Verteilung über Instrumente.
- **In/Out-of-Sample:** Aufteilung wie `bt_oos.py` (Fenster wählbar, Standard
  70/30 auf der Zeitachse) — beide Hälften werden getrennt ausgewiesen.
- **Live ist aus:** kein `--live`-Weg im Replay-Modul, `SCHREIBEN=False`,
  Order- und Kontofunktionen durch Attrappen ersetzt.

### 3. Optimierer — `Agenten/Handel/optimieren.py`

- **Suchtabelle je Spur** in `spur_opt.json`: Parameter, Bereiche, Mindestzahl
  Runden je Fenster. Der Code kennt keine Zahlen (Hausregel: Zahlen gehören in
  JSON, nicht in den Code).
- **Walk-Forward:** Suchfenster → **ungesehenes** Prüffenster → rollierend, wie
  beim Gitter (`suche_gitter.py`, `regime_gitter.py`).
- **Vorfilter:** `f_max` und Mindestrundenzahl. Unter acht Runden wird nicht
  optimiert, sondern berichtet.
- **Urteil:** Ein Kandidat überlebt nur, wenn er im Prüffenster **und** im
  rollierenden Mittel besser ist. „Kein Hebel" ist ein vollwertiges Ergebnis —
  der Gitter-Befund vom 15.09.2026 (42 Kombinationen spannen 0,17–2,23 %) zeigt,
  dass das der Normalfall ist.
- **Schreibt nie** in `wachen.json`. Ausgabe: Vorschlagsdatei
  `daten/backtest/<spur>/optimierung.json`. Die Übernahme entscheidet Max —
  Muster: `backtest_urteile.py` schreibt nur Urteilsfelder, nie Strategiewerte.

## Nicht nachrechenbar (Vermerk statt geschätzter Zahl)

Diese Spuren bekommen im Bericht `backtest: nicht nachrechenbar` mit Grund:

| Spur(en) | Grund |
|---|---|
| `moondev_whale` | OKX-OI-Historie antwortet `50030 Illegal time range` |
| `moondev_liquidation`, `liq_wand` | keine frei abrufbare Liquidationshistorie |
| `moondev_sentiment` | die RSS-Titel von damals sind nicht archiviert |
| `iv_wand`, `iv_waelle` | Strike-OI-Historie (Deribit) nicht abrufbar, nur Live-Bestand |
| `nautilus`, `nautilus_kraken`, `nautilus_kraken_futures` | Einstiege hängen an Quote-Ticks, die es nur live gibt |
| `kopier`, `kopier1zu1` | Solana-Onchain-Historie nur wenige Tage |
| `robinhood_radar` | fremde SQLite hält nur den Sammelzeitraum |
| `xperp` Perp-Zweig (Krypto) | keine stündliche Naht; der Aktien-/Rohstoff-Zweig dagegen ist über `tages_kerzen_quelle` und `daten/*.csv` schon nachrechenbar |

## Kern-Spuren (zweites Teilprojekt, nicht hier)

`scanner`, `xperp`, `swap`, `kraken` haben **keine** Kerzen-Naht für ihren
stündlichen Betriebsweg: sie rufen `okx.kerzen()` direkt, lesen Kontostand und
Ranglisten. Sie brauchen einen eigenen Umbau, Live-Pfad vollständig draußen.
Ausnahme innerhalb dieses Punkts: `xperps` Tageszweig (`tages_kerzen_quelle`)
ist schon bedienbar. Eigener Design-Zyklus.

## Reihenfolge und Nachweise

1. `historie.py` + Mapping. **Nachweis:** `_stand.json` nennt Umfang je Reihe,
   Abrufzeit im Log, Stichprobe stimmt gegen einen Direktabruf.
2. `replay.py` auf **drei** Spuren: `squeeze` (eigene Nähte), `moondev_funding`
   (Binance-Funding), `trendwende_btc` (`spur_buch`).
3. **Gegenprobe:** `squeeze` muss auf denselben Kerzen dieselben Runden liefern
   wie `backtest_prognose.py --spur squeeze`. Weicht der Kern ab, lügt er.
4. Alle übrigen nachrechenbaren Spuren, dann `optimieren.py`.
5. Kern-Spuren (eigenes Teilprojekt).
6. Eine Zeile je Spur in `auswertung_alle.py`: `Backtest N Runden / live M Runden`,
   nicht nachrechenbare Spuren mit Grund. **Kein Cron** — kein Dauerprozess.

## Trennung von Live

- Backtest-Journale liegen unter `daten/backtest/` und sind aus der Freigabe-
  Rechnung ausgeschlossen.
- `daten/historie/` und `daten/backtest/` gehen **nicht** in die Ausser-Haus-Kopie
  nach `Q:\Handel_Journal` (Bedingung 4 betrifft den Betrieb, nicht den Backtest).
- `.gitignore`: `historie.py`, `replay.py`, `optimieren.py`, `spur_opt.json` und
  die Design-/Plan-Dokumente werden freigegeben; `daten/historie/*.json` und
  `daten/backtest/` bleiben gesperrt (reproduzierbar, groß). Gegenprobe nach der
  Anlage: `git check-ignore -v` **und** `git ls-files` auf die gesperrten Pfade.

## Abnahmekriterien

1. `python historie.py --stand` nennt je Reihe Instrument, Takt, Zeitraum, Anzahl.
2. `python replay.py --spur squeeze --genau` liefert dieselben Runden wie
   `backtest_prognose.py --spur squeeze` auf denselben Kerzen.
3. Kein Backtest-Lauf verändert eine echte Datei: Nachweis über Vergleiche von
   Dateiliste und Größen der betroffenen Spurenordner vor/nach dem Lauf.
4. `spiegelstand.py` meldet nach einem Backtest-Lauf weiter 32/32 byte-gleich.
5. Alle bestehenden Suiten bleiben grün (Handel, Bus Ende-zu-Ende).
6. `optimieren.py` für eine Spur zeigt Walk-Forward-Ergebnisse; Kandidaten ohne
   Prüffenster-Vorteil werden als „kein Hebel" ausgewiesen.

## Nicht in dieser Spezifikation

- Umbau der vier Kern-Spuren (eigenes Teilprojekt, eigener Zyklus).
- Beschaffung kostenpflichtiger Historien (Deribit-Options-OI, Onchain-Nachkauf).
- Änderung an `Wissen/Handelsregeln.md` — die Freigabe-Bedingungen bleiben,
  wie sie sind.
- Ersatz des Live-Betriebs durch Backtest-Ergebnisse.