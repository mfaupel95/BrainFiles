# Merkmale fuer die Marktprognose — Design (Entwurf zur Abnahme)

Stand: 01.10.2026 · Auftrag Max: „aus den neuen Handelsstrategien in moondev und
MaxHirn/Wiki/Handel nach diesem Vorbild weitere Indikatoren zur Marktprognose entwickeln".
Vorbild: `Agenten/Handel/prognose_berichte/Stanni.csv` (Spalten `Tor;Wert;Erklärung`).

## 1. Das Vorbild wird zur Bauform

`Stanni.csv` ist keine Liste von Zahlen, sondern eine **Tabelle mit Begruendung**: je Tor
ein Wert UND die Herkunft dieses Werts („WEIT (24.09.2026): 55 -> 70 …", „Gemessen am
13.09.2026 ueber 31 Maerkte (1D): LONG Median 57,5 …"). Genau das fehlt den Indikatorwerten
im Haus: `omniquant/prognose.json` traegt schon `_hoechst_rsi`-Vermerke, die vier
Prognose-Spuren tragen ihre Schwellen dagegen als **Konstanten im Code** (offener Task T-097).

**Bauform:** Jedes neue Merkmal bekommt eine Tor-Tabelle in diesem Format — maschinenlesbar
als JSON, zusaetzlich als CSV mit `Tor;Wert;Erklärung`. Ein Wert ohne Messung, die ihn
traegt, kommt nicht in die Tabelle.

## 2. Befund: woher die Ideen kommen — und was sie wert sind

**moondev (RBI-Bibliothek, `Werkstatt/Repos/moon-dev-ai-agents/src/data/rbi`)**, selbst
gezaehlt am 01.10.2026: **4003 Backtest-Dateien, 804 eindeutige Strategienamen**, dazu
4482 Zeilen `ideas.txt` und 4671 Zeilen `strategy_ideas.csv`. Haufigkeit der Familien im
Namensbestand:

| Familie | Dateien | im Haus gebaut? |
|---|---|---|
| Breakout | 135 | teils (orb/orbk, donchian) |
| Volatility | 124 | nein (kein ATR-Regime) |
| Band / Bollinger | 111 | ja (`klassik_bollinger`) |
| Squeeze | 104 | ja (`squeeze`) |
| **Divergenz** | 94 | **nein** |
| Momentum | 75 | teils (`moondev_topmovers`, `_signalwelle`) |
| Reversal | 66 | teils (`klassik_rsi`) |
| **Volume** | 63 | **nein** (CVD nur in `xperp`) |
| RSI | 48 | ja (`klassik_rsi`, `_rsi2`) |
| Liquidity | 33 | teils (`liq_wand`) |
| **VWAP** | 21 | **nein** |
| Fractal | 20 | nein |
| Channel / Keltner | 24 | nur innerhalb `squeeze` |
| Stochastik | 16 | nein |
| ADX | 7 | nein (nur in der Fremddatei `backtest_archiv_strategie.py`) |

**Wert dieser Quelle: Steinbruch, kein Beleg.** Am 25.09.2026 selbst nachgemessen
(`MaxHirn/Wiki/Werkzeuge/MoonDev-GUI-und-RBI.md`): die dokumentierten Zahlen reproduzieren
sich nicht, die „funktionierenden" Strategien liefern **−95 bis −97 %** gegen
**Buy & Hold +128 %**, und die mit „Sharpe 2,14" laeuft nicht einmal
(`RuntimeError: Indicator "swing_lows(L,12)"`). Ein Modell, das Strategie, Backtest und
Ergebnisbericht schreibt, hat nichts gemessen. **Uebernommen werden deshalb nur NAMEN und
RECHENREGELN, nie eine Zahl.**

**Wiki/Handel** liefert die Haltung und die Werkzeuge: `nautilus-rust-Quant-Ebene.md`
(EvidenceGate: erst ab t ≥ 2,0 handeln), `Strategie-Kennzahlen.md` (t-Statistik nach
`strategie_metrics.py`; heute hat **nur der scanner t = 15,3**, alles andere liegt bei
t < 2), `Kosten-und-Bedingungen.md` (f_max je Runde).

## 3. Die Luecke, belegt

Suche ueber `Agenten/Handel/**/*.py` (ohne Fremdmaterial): `adx`, `vwap`, `stoch`,
`obv`, `cci`, `mfi`, `cmf`, `ichimoku`, `fibonacci`, `divergen` kommen im eigenen Code
**nicht** vor. Treffer nur in Fremd-Beispieldateien (`freqtrade/user_data/strategies/
SampleStrategy.py`, `backtest_archiv_strategie.py` = Harvard-`BB_Squeeze_ADX`) und in zwei
Kommentarzeilen.

## 4. Sechs Merkmale (Vorschlag, in dieser Reihenfolge)

| Nr | Merkmal | Warum (Quelle) | Messbar aus |
|---|---|---|---|
| 1 | **ADX(14)/DI** — Regime-Tor „Trend oder Seitwaerts" | moondev Breakout 135 + Squeeze 104; Harvard `BB_Squeeze_ADX` bestaetigt den Trend mit ADX > 25 | Binance 1H/4H (2017 ff.) |
| 2 | **ATR-Perzentil(14/200)** — Volatilitaetsregime | moondev Volatility 124; `gitter` verliert in ruhigen, gewinnt in bewegten Fenstern | dito |
| 3 | **VWAP + Abstand zum VWAP** | moondev VWAP 21, „VolumeWeightedBreakout" | dito (Volumen ist da) |
| 4 | **Volumenfluss** (OBV-Steigung, Volumen-Verhaeltnis) | moondev Volume 63 | dito |
| 5 | **Divergenz Preis ↔ RSI/MACD** (Swing-Paarung) | moondev Divergenz 94 — die zweithaeufigste Familie | dito |
| 6 | **Multi-Timeframe-Ausrichtung** (4H/1H/15m Score) | moondev Fractal/Adaptive; im Haus nur `macd_mtf` fuer MACD | dito |

Spaeter moeglich: Stochastik %K/%D (16), Fibonacci-Zone, Liquiditaets-Gaps (33).
**Nicht** gebaut: Ichimoku (zu gross), ML-Modelle, neue Datenquellen.

## 5. Wie gemessen wird — das Herz des Entwurfs

Ein Merkmal ist hier **kein Signal, sondern ein Tor**: es wird als **Filter auf
bestehenden Runden** geprueft, nicht als eigene Spur.

- **Grundlage:** `daten/historie/` (Binance 1H ab 2017; BTC/ETH/SOL liegen, weitere
  Instrumente per `historie_binance.py`), gefahren ueber `replay.py` (Familien A/B) und
  die vorhandenen Journale unter `daten/backtest/<spur>/`.
- **Verfahren wie `filter_studie.py`:** Zeit-Halbierung — eine Regel muss in **beiden**
  Haelften positiv sein, sonst „verworfen". Dazu Trefferquote, Erwartung, t-Statistik
  (`strategie_metrics.py`), `f_max` (`kosten_wendepunkt.py`), Kosten 0,1 % je Seite.
- **Das Raster liefert den Wert:** jede Schwelle wird als Raster gefahren (z. B. ADX
  15/20/25/30, ATR-Perzentil 20/40/60/80), damit der Wert in der Tor-Tabelle aus einer
  Messung kommt und nicht aus dem Bauch.
- **Ein verworfenes Merkmal wird mit Zahl dokumentiert.** Das ist das Ergebnis, nicht ein
  Fehlschlag — und die ehrliche Haelfte der Arbeit.

## 6. Was entsteht (Bauform)

| Datei | Aufgabe |
|---|---|
| `Agenten/Handel/merkmal.py` | reine Funktionen ueber Kerzen, **nur Standardbibliothek** (wie `ti_indikatoren.py`); Rueckgabe je Merkmal Wert + Rohwerte |
| `Agenten/Handel/merkmale/*.json` | je Merkmal eine Tor-Tabelle im Vorbild (Tor, Wert, Erklaerung) |
| `Agenten/Handel/merkmale_tabelle.py` | schreibt daraus die CSV im Format des Vorbilds |
| `Agenten/Handel/merkmale_studie.py` | die Filterstudie, schreibt `merkmale_studie_ergebnis.json` |
| `tests/test_merkmale.py`, `tests/test_merkmale_studie.py` | Rechenregeln, Grenzfaelle (zu wenig Kerzen -> `None`, nie still 0), Halbierungsregel |

Kein `pandas`, kein `talib` in `merkmal.py`: die Spuren laufen in `scanner/.venv` ohne
diese Pakete (gemessen 01.10.2026: nur `Agenten/Handel/.venv` traegt numpy/pandas).

## 7. Was NICHT gebaut wird

- **Keine neue Einzelspur je Indikator.** 39 Spuren genuegen; eine Spur kostet Buchhaltung,
  Runden, Spiegelung und Dauerlauf-Zeit — und gemessen hat bisher nur EIN scanner t > 2.
- **Keine Uebernahme fremder Dateien oder Zahlen** aus moondev (Hausregel
  `skill-library-sync`; Zahlen sind Prosa, siehe § 2).
- **Nichts schreibt in eine `wachen.json`** — die Studie schreibt nach `daten/` und in
  Tests. Tore werden erst nach dem Urteil gesetzt, mit Max' Abnahme.
- Kein Live-Bezug, kein Orderweg, keine neue Datenquelle.

## 8. Reihenfolge

1. Diese Spezifikation abnehmen.
2. `merkmal.py` + Tests (Rechenregeln, Gegenprobe).
3. `merkmale_studie.py` + Halbierungsregel.
4. Lauf ueber die Historie; Urteil je Merkmal **und** je Schwelle.
5. Tor-Tabellen im Stanni-Format — nur fuer die Ueberlebenden.
6. Erst danach (eigener Auftrag): Verdrahtung als zusaetzliche Tore in `omniquant` oder als
   Spur. Nach jedem Schritt ist ein Abbruch moeglich.

## 9. Offene Entscheidung

Sechs Merkmale wie in § 4, in dieser Reihenfolge? Empfehlung: ja — die drei Familien mit
der groessten Luecke (Volatility, Divergenz, Volume/VWAP) sind zuerst dran, und der
Zuschnitt erlaubt den Abbruch nach jedem Merkmal.
