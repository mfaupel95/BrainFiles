# Backtest-Optimierung der Prognose-Spuren — macd_mtf & squeeze, Long-Seite

**Datum:** 21.09.2026 · **Durchgangsware** (Werkstatt)
**Treiber:** `Agenten/Handel/bt_varianten_fast.py` (Indikatoren einmal je Instrument
vorrechnen, Einstiegs-/Ausstiegslogik aus `<spur>/handeln.py` über den Pfad),
`bt_oos.py` (Halbierung in H1/H2). **Rein lesend:** keine `wachen.json`, keine
Live-Datei, kein Scharfschalten — `SCHREIBEN=False`, Journal abgefangen.

**Massstab:** Langlauf 7000 h, **nur Long**, netto **0,10 %/Seite** (OKX Spot Taker).
Ausgangspunkt (verifiziert): macd_mtf-long **+2,28 %/R** (62 R, 48,4 %, +141,18,
dd −63,51), squeeze-long **+1,57 %/R** (60 R, 45,0 %, +94,09, dd −67,15).

---

## 1. Ausgangspunkt verifiziert

Die reproduzierte Baseline stimmt mit dem Stand vom 21.09.2026 überein:

| Spur | Runden | Quote | netto/R | Summe | max. Rücklauf |
|---|---|---|---|---|---|
| macd_mtf long | 62 | 48,4 % | **+2,277 %** | +141,18 | −63,51 |
| squeeze long | 60 | 45,0 % | **+1,568 %** | +94,09 | −67,15 |

(Zahlen identisch zum dokumentierten Stand; der schnelle Treiber rechnet die
Indikator-Arrays einmal je Instrument und liest je Schritt nur am aktuellen
Index — mathematisch identisch zur schrittweisen Neuberechnung, weil Fenster
und Aggregation beide bei Index 0 starten.)

## 2. Getestete Varianten — Ergebnisse (7000 h, long, netto 0,10 %/Seite)

### macd_mtf — Indikator-Varianten

| Variante | Runden | Quote | netto/R | Summe | max. Rücklauf |
|---|---|---|---|---|---|
| **BASE** (Stand) | 62 | 48,4 % | +2,277 % | +141,18 | −63,51 |
| **hist1+4** (Histogramm muss auch im 4er steigen) | 54 | **51,9 %** | **+2,787 %** | **+150,50** | **−54,82** |
| fakt(1,4,8) | 81 | 37,0 % | +0,117 % | +9,49 | −171,39 |
| fakt(1,2,4) | 82 | 35,4 % | +0,034 % | +2,80 | −137,28 |
| macd(5,35,5) | 63 | 41,3 % | +1,006 % | +63,36 | −103,76 |
| macd(8,21,5) | 70 | 38,6 % | +0,517 % | +36,22 | −121,35 |

### macd_mtf — Parameter-Varianten (Stop/Ziel auf BASE-Signal)

| Variante | Runden | Quote | netto/R | Summe | max. Rücklauf |
|---|---|---|---|---|---|
| BASE | 62 | 48,4 % | +2,277 % | +141,18 | −63,51 |
| ziel R=3 | 46 | 41,3 % | +3,382 % | +155,56 | −61,29 |
| ziel R=1,5 | 93 | 51,6 % | +1,453 % | +135,16 | −65,59 |
| stop min4 | 91 | 48,4 % | +1,693 % | +154,05 | −76,49 |
| stop max15 | 62 | 48,4 % | +2,277 % | +141,18 | −63,51 |
| stop 3–15 | 127 | 44,9 % | +0,868 % | +110,23 | −78,70 |

### squeeze — Indikator-Varianten

| Variante | Runden | Quote | netto/R | Summe | max. Rücklauf |
|---|---|---|---|---|---|
| **BASE** (Stand) | 60 | 45,0 % | +1,568 % | +94,09 | −67,15 |
| **laenge30** (Squeeze-Fenster 20→30) | 44 | **50,0 %** | **+2,531 %** | **+111,38** | **−64,31** |
| laenge15 | 76 | 39,5 % | +0,538 % | +40,87 | −121,38 |
| kc1.8 | 77 | 37,7 % | +0,277 % | +21,37 | −124,70 |
| kc1.2 | 48 | 47,9 % | +2,076 % | +99,65 | −77,18 |
| mom>0.05 | 61 | 44,3 % | +1,476 % | +90,02 | −69,57 |

### squeeze — Parameter-Varianten (Stop/Ziel auf BASE-Signal)

| Variante | Runden | Quote | netto/R | Summe | max. Rücklauf |
|---|---|---|---|---|---|
| BASE | 60 | 45,0 % | +1,568 % | +94,09 | −67,15 |
| ziel R=3 | 43 | 30,2 % | +0,617 % | +26,51 | −67,84 |
| ziel R=1,5 | 64 | 50,0 % | +1,082 % | +69,22 | −73,20 |
| stop min4 | 71 | 46,5 % | +1,390 % | +98,69 | −65,86 |
| stop max15 | 60 | 45,0 % | +1,568 % | +94,09 | −67,15 |
| stop 3–15 | 98 | 40,8 % | +0,621 % | +60,88 | −85,36 |

## 3. OOS-Stabilität (Halbierung 7000 h → H1 0–3500, H2 3500–7000)

| Spur / Variante | H1 netto/R | H1 Quote | H2 netto/R | H2 Quote |
|---|---|---|---|---|
| macd BASE | +1,047 % | 40,0 % | +1,783 % | 47,8 % |
| macd **hist1+4** | **+1,693 %** | **46,2 %** | **+2,590 %** | **52,6 %** |
| squeeze BASE | +1,611 % | 46,2 % | +3,293 % | 52,6 % |
| squeeze **laenge30** | **+4,704 %** | **63,6 %** | **+3,380 %** | **54,5 %** |

`hist1+4` schlägt BASE auf **beiden** Hälften (netto/R und Quote). `laenge30`
schlägt BASE auf beiden Hälften im netto/R und in der Quote, fällt aber auf H2
bei der Runden-Zahl stark ab (11 statt 19) — Summe H2 +37,18 vs. +62,56. Der
Vorsprung pro Runde ist stabil, die Runden-Zahl dünner.

## 4. Befund und Empfehlung

**Was trägt:** Die einzige robuste, messbare Verbesserung ist **macd_mtf
`hist1+4`** — das Histogramm muss zusätzlich zum 1er auch im 4er-Zeitrahmen
steigen. Es hebt Quote (48,4→51,9 %), netto/R (+2,28→+2,79 %), Summe
(+141→+150) und senkt den Rücklauf (−63,5→−54,8), und das auf beiden
Hälften (OOS). Das ist eine Bestätigungs-Bedingung am selben Indikator, kein
neuer Parameter — kein Overfit-Risiko im Sinne der Hausmethodik.

**Was NICHT trägt:**
- **Parameter-Suche ist ein Fehlgriff.** `ziel R=3` zeigt auf macd zwar +3,38 %/R,
  aber bei nur 46 Runden und 41 % Quote; `ziel R=1,5` und `stop min4` erhöhen
  die Runden-Zahl, ohne den Vorsprung pro Runde zu halten. `stop max15` ist
  wirkungslos (identisch zu BASE). Kein Parameter-Knopf hebt den Stand robust.
- **Faktor-/MACD-Varianten verschlechtern** die Long-Seite durchweg (mehr
  Runden, niedrigere Quote, tieferer Rücklauf).
- **squeeze `laenge30`** verbessert netto/R und Quote auf beiden Hälften, aber
  bei deutlich weniger Runden (44 vs. 60; H2 nur 11) — der Vorsprung ist
  dünner belegt und nicht als klare Empfehlung zu vertreten.

**Empfehlung (eine):** Die Optimierung setzt an der **macd_mtf-Long-Seite mit
der `hist1+4`-Bedingung** an (Histogramm-Anstieg im 1er UND 4er-Zeitrahmen als
Einstiegsfilter). Es ist die einzige Variante, die den Stand auf dem vollen
7000-h-Langlauf und in beiden OOS-Hälften übertrifft. Für squeeze gibt es
**keine** Variante, die als klare Verbesserung zu empfehlen wäre — `laenge30`
ist vielversprechend, aber zu dünn belegt; dort bleibt der Stand die bessere
Wahl, bis mehr Historie (oder ein OOS auf anderem Datenfenster) den Vorsprung
verdichtet.

## 5. Nachweis

```bash
cd Agenten/Handel
python bt_varianten_fast.py --json bt_varianten_fast.json   # Varianten, 7000 h long
python bt_oos.py                                             # Halbierung H1/H2
```
Skripte und `bt_varianten_fast.json` liegen in `Agenten/Handel/` (Durchgangsware,
nicht versioniert). Keine Spur-, `wachen.json`- oder Live-Datei wurde
geschrieben oder verändert.