# MoonDev-Spuren auf historischen Daten — Design

**Datum:** 2026-09-26 · **Status:** freigegeben (Max, 26.09.2026)
**Vorgaenger:** `2026-09-24-backtest-fundament-design.md` (Kern: `historie_binance.py`,
`replay.py`, `optimieren.py`)
**Self-Review:** 26.09.2026 — Platzhalter: keine. Vier Mehrdeutigkeiten
inline behoben: Vorgabe von `top` (Wachen-Zahl der Spur, nicht „alles"),
erster Tag einer Reihe ohne Vortagesschliessung, Familie C als neu
gekennzeichnet, HYPE faellt aus dem Lauf (kuerzeste Reihe wuerde den
Zeitraum auf vier Monate kappen).
**Nachfreigabe Max:** 26.09.2026 — `moondev_signalwelle` soll die
1H-Kerzen der Top 40 bekommen und ist damit die vierte nachrechenbare Spur;
ihr kleineres Universum (40 statt 250) steht als Grenze 6 in Abschnitt 6.

## 1. Zweck

Die MoonDev-Spuren sind Papierbuecher auf Signalen geklonter Fremd-Bots. Ihr
Problem ist nicht die Regel, sondern die Stichprobe: jede von ihnen hat seit
dem 16.09.2026 **ein- bis zweistellig viele** geschlossene Runden. Eine
Trefferquote aus acht Runden ist ein Befund, keine Messung
(`buchauswertung.MIN_AUSSTIEGE`, `auswertung_alle.MIN_RUNDEN` = 8).

Dieses Design macht **vier** dieser Spuren auf 2021–2026 nachrechenbar und
vervielfacht damit ihre Stichprobe um Groessenordnungen. Es baut auf dem
bestehenden Kern auf und aendert ihn nicht.

**Abgrenzung (unveraendert gueltig):** Runden aus historischen Daten sind eine
Messung, keine Live-Erfahrung. Sie fuellen **keine** Freigabe-Bedingung
(Wissen/Handelsregeln.md, Bedingung 1) und werden in `auswertung_alle.py` in
der eigenen Sektion „Backtest (historisch)" gefuehrt, nie zu Live-Runden
addiert.

**Nicht Ziel:** eine Nachbildung der Spuren, eine zweite Gebuehrenrechnung,
eine Aenderung an laufenden Spuren, an `wachen.json`-Werten oder am Q:-Ziel.

## 2. Was schon steht

| Teil | Stand |
|---|---|
| `historie_binance.py` | Binance-Kerzen, oeffentlich und schluesselfrei; BTC/ETH/SOL in 1H/4H/1D seit 2021 (12 MB, 50.223 Stundenkerzen je Instrument) |
| `replay.py` | Kern: Familie A (eigenes Buch) und Familie B (`spur_buch.zyklus`); Kerzenuhr, rollierendes Fenster, Gebuehr je Spur, Journal in Hausform, Gegenprobe |
| `optimieren.py` | Walk-Forward-Suche mit Status-quo-Vergleich, Mindestrunden, toten Feldern |
| `auswertung_alle.py` | eigene Sektion „Backtest (historisch)" mit immer genanntem Grund |
| nachgerechnet | squeeze, wavetrend, macd_mtf, supertrend (759–1128 Runden statt 8–23) |

## 3. Die zwei Datenwege

Gemessen am 26.09.2026, alle Endpunkte oeffentlich und ohne Schluessel.

### 3.1 Marktquerschnitt (taeglich)

* Quelle: `https://api.binance.com/api/v3/klines` (1D) fuer die liquidesten
  USDT-Spot-Paare; die Rangliste kommt aus `/api/v3/ticker/24hr`
  (`quoteVolume`) gegen `/api/v3/exchangeInfo` (`status=TRADING`).
* Menge: Binance hat **496** USDT-Spot-Paare. Vorgabe **300** Symbole.
  Gemessen: 10 Symbole × 1D seit 2021 = 20.775 Kerzen in 26 s →
  **~13 min, ~70 MB** fuer 300.
* Ablage: `daten/historie/feed/<SYMBOL>_1D.json` — **eigener Ordner und
  eigenes Namensschema**. Grund: `daten/historie/BTCUSDT_1D.json` gibt es
  bereits (2.094 Kerzen aus `historie_binance.py`), und beide Kerzenformen sind
  **nicht** austauschbar (siehe 3.3).
* Felder je Kerze: `[ts_ms, o, h, l, c, volumen_quote]` — das
  **Quote**-Volumen in USD (Binance-Feld 7).

### 3.2 Funding (achtstuendlich)

* Quelle: `https://fapi.binance.com/fapi/v1/fundingRate`, paginiert
  (1.000 Eintraege je Aufruf, ~7 Aufrufe fuer 5,7 Jahre).
* Gegenstand: die `instrumente` der Funding-Spur (BTC, ETH, SOL, HYPE, FIL,
  ZEC). Gemessen: **fuenf von sechs ab 2021-01-01**, HYPE erst ab 2025-05-30
  (neues Listing).

  **HYPE faellt aus dem Lauf, mit genanntem Grund.** Der Kern fuehrt den Walk
  ueber die *kuerzeste* Reihe (`laenge = min(len(k))`) — mit HYPE liefe der
  ganze Funding-Backtest vom 30.05.2025 an, also ueber vier Monate. Das waere
  wieder ein Befund statt einer Messung. HYPE wird als
  `symbole_zu_kurz: ["HYPE"]` im Stand gefuehrt und spaeter eigens gerechnet,
  wenn genug Zeitraum da ist — nicht stillschweigend als Nullsatz gerechnet.
* Ablage: `daten/historie/feed/funding_<SYM>.json`, aufsteigend
  `[[ts_ms, rate], ...]`. Ein Funding-Satz gilt ab seinem Zeitstempel bis zum
  naechsten — die Spur sieht immer den letzten Satz **davor** (kein Blick in
  die Zukunft).

### 3.3 Stundendaten fuer die Signalwelle

* Gegenstand: die **Top 40** nach dem Volumen (dieselbe Rangliste wie 3.1).
* Quelle: `/api/v3/klines` mit `interval=1h`, seit 2021 paginiert (1.000 je
  Aufruf, ~50 Aufrufe je Symbol). Gemessen: ~1.000 Kerzen/s → **~33 min,
  ~250 MB** (40 × 50.223 Stundenkerzen).
* Ablage: `daten/historie/feed/<SYMBOL>_1H.json`, Kerzenform wie 3.1.
* Grund: `moondev_signalwelle` entscheidet auf `aenderung_1h`; aus
  Tageskerzen laesst sich eine Stundenbewegung nicht ehrlich bilden.
* **Der Schritt dieser Spur ist eine Stunde**, nicht ein Tag. Ihre uebrigen
  Groessen kommen aus derselben Reihe: `aenderung_24h` = Schluss gegen
  Schluss vor 24 Kerzen, `volumen_24h` = Summe der Quote-Volumina der letzten
  24 Kerzen.

### 3.4 Warum die Kerzenform nicht gemischt wird

`historie_binance.py` speichert als sechstes Feld das **Basis**-Volumen (gemessen:
01.01.2021 = 54.182,93 BTC). Die Movers-Spur prueft ihr Volumen aber gegen
`mindest_volumen_usd` (2e7 = **20 Mio USD**) — mit Basisvolumen waere die
Schwelle um den Faktor Kurs verfehlt und die Spur haette nie gehandelt. Die
Feed-Kerze traegt deshalb das Quote-Volumen und liegt in einem eigenen Ordner,
den `historie_binance.lade()` nicht findet.

## 4. Der Marktquerschnitt (Tafel)

`moondev_historie.tafel(ts_ms, top=None)` liefert je Handelstag eine Liste von
dicts mit **genau den Feldern, die `quelle()` der Spuren von CoinGecko holt**:

| Feld | Herkunft |
|---|---|
| `symbol` | Symbol ohne Quote-Anteil (`BTCUSDT` → `BTC`) |
| `kurs` | Schlusskurs der Tageskerze |
| `aenderung_24h` | `(c_t / c_{t-1} − 1) · 100` |
| `volumen_24h` | Quote-Volumen in USD (Binance-Feld 7), unveraendert |
| `rang` | Platz **nach dem Volumen dieses Tages** (siehe 4.1) |

Der **erste Tag** einer Reihe hat keine Vortagesschliessung und damit keine
`aenderung_24h`: er erscheint nicht in der Tafel (kein geschaetzter Wert, kein
`null` in einem Feld, das die Regel als Zahl liest).

Fuer die Signalwelle gibt es dieselbe Tafel **auf Stundenbasis**
(`tafel_stunde(ts_ms, top=None)`) mit `aenderung_1h` anstelle von `rang` —
dieselben vier Felder, die ihre `quelle()` von CoinGecko holt
(`aenderung_1h`, `aenderung_24h`, `volumen_24h`, `kurs`).

Dazu `breite(ts_ms, top=None)`: der Anteil der Symbole mit
`aenderung_24h > 0` unter den Top `top` nach dem Volumen dieses Tages — die
Zahl, die `moondev_marktlage` als `breite` liest.

`top=None` heisst **nicht** „alles", sondern **die Zahl der Spur**: die
`anzahl_coins` aus ihrer `wachen.json` (Topmovers 250, Marktlage 100),
hoechstens so viele, wie geladen sind. Eine Vorgabe „alles" waere eine zweite
Auslegung derselben Zahl und wuerde die Spur breiter rechnen, als sie im
Betrieb sieht.

### 4.1 Der Rang wird je Tag gebildet, nicht einmal festgelegt

Gemessen am 26.09.2026: von den **40 liquidesten** USDT-Paaren haben nur
**20** Daten ab Januar 2021 — die heute liquidesten Paare sind ueberwiegend
neu (2023 und spaeter). Eine einmal festgelegte Rangliste waere fuer 2021
halb leer und wuerde die Gegenwart in die Vergangenheit tragen.

Deshalb entsteht der Rang **je Tag aus dem Volumen dieses Tages**, berechnet
aus den Kerzen selbst. Die Reihenfolge ist damit zeitrichtig; die Auswahl der
*ueberhaupt geladenen* Symbole bleibt es nicht (siehe 6.1).

## 5. Anschluss an die Spuren

Anschlussstellen sind die **Nahten, die die Spuren im Betrieb schon haben** —
keine Nachbildung, kein Patch der Regel:

| Spur | Familie | Naht | Schritt | Gebuehr je Seite |
|---|---|---|---|---|
| `moondev_topmovers` | B | `quelle(w)` → Tafel | 1 Tag | 0,05 % (`okx_perp`) |
| `moondev_marktlage` | B | `quelle(w)` → Tafel + `breite` | 1 Tag | 0,60 % (`kraken`, eigener `gebuehr_taker`) |
| `moondev_signalwelle` | B | `quelle(w)` → Stundentafel | 1 Stunde | 0,05 % (`okx_perp`) |
| `moondev_funding` | C | `funding_quelle(sym)` + `zeit_quelle()` | 8 h | 0,05 % (`okx_perp`) |

* **Familie B** laeuft ueber `spur_buch.zyklus(ordner, quelle, signal, ...)` —
  `quelle` und `signal` sind Parameter, der Kern schiebt die historische
  Quelle unter. Die Uhr kommt aus dem bestehenden Kern (`zeit_quelle` der
  Kerze, nicht die Wanduhr).
* **Familie C** ist in DIESEM Design neu (`moondev_funding`): eine Spur mit
  eigenem `lauf(modus)` und eigenen Nahtnamen, die weder `spur_buch.zyklus`
  noch `pruefe_einstieg`-Form von Familie A benutzt. Sie hat ein `lauf(modus)` mit
  `hole_kurse(w)` → `funding_holen(sym)` → `funding_quelle`. Genau diese
  Modulvariable wird gesetzt; `schuetze()` legt `SCHREIBEN`, `journal`,
  `schreibe_zustand`, `spiegeln` und die Dateikonstanten um. Die Rueckgabe
  muss tragen, was `pruefe_einstieg` liest: `funding_rate` und `mark_price`.
  `zeit_quelle` ist vorhanden und wird auf die Funding-Zeit gesetzt.
* Die Gebuehr kommt aus `replay.gebuehr_fuer()` (Wert der Spur, sonst
  Boersensatz) — **kein** pauschaler Ersatz.

Der Quellen-Adapter liefert genau die Dict-Form, die die jeweilige `quelle()`
zurueckgibt: `(daten, kurse, fehler)`. Ein Adapter mit falschen Feldern liesse
die Spur **still** ohne Signal laufen und erzeugte eine Zahl, die wie ein
Messwert aussieht — deshalb prueft ein Test je Spur, dass der Adapter genau
die Felder liefert, die `signal()` bzw. `pruefe_einstieg()` liest.

## 6. Ehrliche Grenzen (werden mitgeliefert, nicht verschwiegen)

1. **Ueberlebende.** Nur Symbole, die heute noch auf Binance handelbar sind,
   werden geladen. Paare, die vor 2026 delistet wurden, fehlen — die Breite
   ist dadurch **eher zu hoch** (nur Ueberlebende zaehlen), die Movers-Auswahl
   eher zu sauber. Das ist der wichtigste Vorbehalt dieser Zahlen und steht
   als Vermerk in jeder Tafel-Antwort.
2. **Rang nach Volumen statt Marktkapitalisierung.** Eine freie
   Marktkapital-Historie gibt es nicht (CoinGecko `/coins/{id}/market_chart`
   liefert fuer freie Konten nur 365 Tage). Gleiche Absicht, anderer Filter,
   ausgewiesen als `rang_groesse: "quote_volumen"`.
3. **Ein Tag ist ein Schritt.** Im Betrieb entscheidet die Spur alle 15
   Minuten, im Backtest einmal je Tagesschluss. Einstieg und Ausstieg liegen
   damit groeber; die Haltedauer ist eine Untergrenze, nicht das Betriebsmass.
4. **Binance-Kerzen sind ein Ersatz.** Sie sind nie ein OKX- oder
   Kraken-Preis; die Herkunft steht als `kerzenquelle: binance` im Journal und
   in jeder Ausgabe.
5. **Backtest-Runden fuellen keine Freigabe-Bedingung.** Unveraendert.
6. **Die Signalwelle sieht 40 Symbole statt 250.** Ihre `wachen.json` setzt
   `anzahl_coins: 250`; die Stundendaten decken die Top 40 ab. Eine
   1h-Bewegung von +3 % ist bei kleinen Coins haeufiger als bei den
   liquidesten — der Backtest findet also **weniger** Signale als die Regel
   im Betrieb, nie mehr. Die Abweichung wird als
   `universum: "top40_nach_volumen"` ausgewiesen; wer mehr will, laesst 1H
   fuer weitere Symbole nachladen (je 100 Symbole ~80 min, ~600 MB).

## 7. Was nicht nachrechenbar ist

In `replay.NICHT_NACHRECHENBAR` mit Grund gefuehrt; `lauf_b` verweigert diese
Spuren, statt zu raten. `auswertung_alle.py` nennt den Grund in der
Backtest-Zeile.

| Spur | Grund |
|---|---|
| `moondev_sniper` | pump.fun-Neulaunches mit Alter in Minuten — nur live vorhanden |
| `moondev_listingarb` | Marktkapitalisierung fehlt frei (die Binance-Paarliste waere baubar) |
| `moondev_whale` | OKX-OI-Historie verweigert (`50030 Illegal time range`) |
| `moondev_liquidation` | keine freie Liquidationshistorie |
| `moondev_sentiment` | RSS-Titel werden nicht archiviert |
| `iv_wand`, `iv_waelle` | Deribit-Strike-OI-Historie |
| Nautilus-Arme | Quote-Feeds |
| `kopier`, `kopier1zu1`, `robinhood_radar` | Onchain-Historie nur wenige Tage |

## 8. Nachweis

1. `tests/test_moondev_historie.py` — Tafel-Felder, Rang je Tag, Breite,
   Funding-Vorwaertsschnitt (kein Blick in die Zukunft), Lueckenmeldung,
   ausgewiesener Survivorship-Vermerk.
2. `tests/test_replay_feed.py` — je Spur ein Test, dass der Adapter die
   Felder liefert, die ihre Entscheidung liest; `NichtsAusserhalbTest` (kein
   Schreibzugriff ausserhalb `daten/`); die Kerzenuhr schlaegt die Wanduhr.
3. **Gegenprobe an einem echten Abzug:** ein einmal aufgezeichneter
   CoinGecko-Abzug (`daten/historie/coingecko_probe.json`) wird gegen die
   Tafel desselben Tages gehalten — die Zahlen muessen in der
   Groessenordnung uebereinstimmen (Abweichung dokumentiert, nicht
   weggerechnet). Ein Adapter, den niemand gegen die Wirklichkeit gehalten
   hat, ist eine Behauptung.
4. `auswertung_alle.py --spur moondev_topmovers` nennt Runden, Trefferquote
   und Zeitraum; `spiegelstand.py` bleibt unberuehrt (der Backtest schreibt
   nur unter `daten/backtest/`).
5. Die laufenden Spuren, jede `wachen.json`, das Q:-Ziel und
   `daten.bak-20260919` bleiben unangetastet.

## 9. Aufwand und Reihenfolge

| Schritt | Aufwand |
|---|---|
| `moondev_historie.py` + Tests | ~2 h, davon 13 min Abruf (300 Symbole 1D) und ~15 min Funding |
| Stundendaten Top 40 (in derselben Datenschicht) | ~33 min Abruf, ~250 MB |
| Adapter `moondev_topmovers` + Tests | ~1 h |
| Adapter `moondev_marktlage` + Tests | ~1 h |
| Adapter `moondev_signalwelle` + Tests (Stundenschritt) | ~1 h |
| Familie C `moondev_funding` + Tests | ~1,5 h |
| Gegenprobe, Auswertungszeile, Wiki, Aufgabe T-096 schliessen | ~1 h |

Reihenfolge: erst die Datenschicht und ihre Pruefung (ein Signal, das nie
entsteht, sieht wie ein Messwert aus), dann je Spur ein Adapter mit Test,
zuletzt die Gegenprobe gegen den echten Abzug.