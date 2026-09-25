---
id: 20260925-backtest-fundament
title: 'Handel — Backtest-Fundament (historische Daten)'
tags: [handel, backtest]
created: 2026-09-25
updated: 2026-09-25
related: ['[[Handel/Spuren-Uebersicht]]', '[[Handel/Kosten-und-Bedingungen]]', '[[Wissen/Handelsregeln]]']
summary: 'Wie die Spuren ueber 5,7 Jahre historische Daten nachgerechnet werden, was dabei herauskam und welche vier Fallen die Umsetzung aufgedeckt hat.'
---

# Backtest-Fundament

Quelle: `Agenten/Handel/historie.py`, `replay.py`, Spezifikation
`Agenten/Handel/docs/design/2026-09-24-backtest-fundament-design.md`,
Plan `docs/plans/2026-09-24-backtest-fundament.md`.

## Wozu

Die Spuren liefern im Betrieb etwa **eine Handelsrunde am Tag**. Auswertungen
rechnen ab `MIN_RUNDEN=8`; eine Zahl darunter ist ein Befund, keine Messung.
Der Backtest holt **historische** Runden dazu — fuer Kennzahlen (Trefferquote,
Erwartungswert, `f_max`) und fuer die Parametersuche.

> **Regel:** Backtest-Runden zaehlen **nicht** fuer die Freigabe-Bedingungen
> (50 Runden, netto positiv). Backtest-Journale liegen unter
> `Agenten/Handel/daten/backtest/` und sind aus der Freigaberechnung
> ausgeschlossen. Sie sind Messung, keine Live-Erfahrung.

## Die drei Einheiten

| Datei | Aufgabe |
|---|---|
| `historie.py` | Kerzen und Fundingsaetze von Binance holen und in `daten/historie/` ablegen |
| `replay.py` | eine Spur ueber die Historie fahren, ohne eine echte Datei anzufassen |
| `optimieren.py` | Parametersuche mit Walk-Forward (noch nicht gebaut) |

**Datenquelle ist Binance, nicht die Boerse der Spur.** Das ist ein bewusster
Proxy (BTC-USDC/OKX und BTCUSDT/Binance laufen ueber Arbitrage praktisch
gleich), aber jedes Ergebnis traegt `kerzenquelle: binance` — es wird nie als
OKX- oder Krakenkurs ausgegeben.

## Zwei Spurenfamilien

| Familie | Wie das Buch laeuft | Wie der Replay andockt |
|---|---|---|
| **A** | Buch im eigenen Modul (`lade_wachen`, `journal`, `pruefe_einstieg`, `pruefe_ausstiege`), Daten ueber eine `*_quelle`-Naht | Naht besetzen, `pruefe_*` je Schritt rufen |
| **B** | `spur_buch.zyklus(ordner, quelle, signal, …)` — `quelle` und `signal` kommen **als Argumente** | eigene `quelle` unterlegen, `zyklus` je Schritt rufen |

## Erste Zahlen (2026-09-25, 2021-01 bis 2026-09, Gebuehr 0,1 % je Seite)

| Spur | geschlossene Runden | auswertbar | Trefferquote | f_max/Runde | Summe |
|---|---|---|---|---|---|
| squeeze | 1088 | 759 | 51,0 % | +2,65 % | +61,9 % |
| wavetrend | 1506 | 1128 | 54,3 % | +3,18 % | +419,7 % |
| macd_mtf | 1209 | 774 | 53,2 % | +3,00 % | +299,9 % |
| supertrend | 854 | 854 | 49,8 % | +2,50 % | −6,9 % |

Zum Vergleich: die Live-Journale dieser Spuren trugen 8 bis 23 Runden.

`f_max` ist der Gebuehrensatz, ab dem die Runde die Nulllinie trifft — **kein
Gewinn**. Bei supertrend liegt `f_max` bei +2,50 %, die Summe aber bei −6,9 %:
`f_max` unterstellt, dass jeder Gewinner sein Ziel erreicht und jeder Verlierer
den Stop; die tatsaechliche Verteilung (viele kleine Ausstiege) liegt darunter.

## Sechs Fallen, die die Umsetzung aufgedeckt hat

1. **Ein Backtest-Journal braucht die Zeilen der SPUR.** Selbst gebaute
   Ausstiegszeilen sind wertlos: `kosten_wendepunkt.runden_aus_journal()` paart
   Einstieg ↔ Ausstieg je Instrument. Nur Ausstiegszeilen ergeben **0 Runden** —
   und das sieht wie ein Ergebnis aus. Richtig ist, die `journal()`-Aufrufe der
   Spur abzufangen und ihre eigenen Zeilen zu schreiben.
2. **Ein rollierendes Fenster, kein wachsender Praefix.** Im Betrieb fordert
   jede Spur eine feste `kerzen_anzahl` an; sie sieht nie die ganze Geschichte.
   Ein Praefix ist ausserdem O(n²): 900 Schritte ueber 1.200 Kerzen = 20 s,
   hochgerechnet auf 50.223 Kerzen ≈ 16 Stunden. Das Fenster muss die
   `mindest_kerzen` der Spur respektieren — **sonst meldet die Spur still
   „0 Runden"** (gemessen: macd_mtf braucht ~560 Basiskerzen fuer seinen
   16er-Rahmen, mit Fenster 400 kam kein Handel zustande, mit 640 dann 1209).
3. **Drei Dinge muessen waehrend des Laufs stillgelegt werden:** `ereignis.lauf`
   (jeder Zyklus oeffnet eine Bus-Meldung — ueber 50.000 Schritte eine Flut im
   Bus-Journal und Telegram-Nachrichten aus einem Backtest), `spur_buch.spiegeln`
   (Bedingung 4 spiegelt nach Q:) und die Risikostufe (sonst entstehen
   `.mittel`-Dateien). Alles im `finally` zurueckstellen.
4. **Die Uhr der Spur muss gesetzt werden — auch bei Familie A.** `squeeze`,
   `wavetrend`, `macd_mtf` und `supertrend` haben dieselbe Naht wie Familie B
   (`zeit_quelle` + `_jetzt()`); wer sie nicht setzt, bekommt ein Journal mit
   der **Wanduhr des Laufs**. Gemessen: ein 6-Monats-Lauf schrieb alle 48 Zeilen
   mit der Uhrzeit des Laufs, und die Fensterteilung des Optimierers fand darauf
   **nichts** — alle 18 Kandidaten meldeten „0 Runden", was wie ein ehrliches
   „kein Hebel" aussieht und keines war. Zusätzlich schreibt der Replay zu jeder
   Zeile `_kerzen_ts`; die Fensterteilung benutzt diesen Stempel und fällt nur
   notfalls auf `zeit` zurück.
5. **Ein zu kurzer Zeitraum ist eine Rechnung, kein Fehler.** 6 Monate im
   4H-Takt sind 1092 Kerzen; für 2 Fenster à 600 sind 1200 nötig. Der
   Optimierer hebt den Zeitraum an **und meldet es** — still eine andere Zahl
   zu rechnen wäre schlimmer als der Abbruch.
6. **Import-Reihenfolge:** `spur_buch` legt beim Import den Bus-Ordner in
   `sys.path`; ein alphabetisch vorgezogenes `import ereignis` faellt mit
   `ModuleNotFoundError` um, obwohl das Modul existiert.

## Offen

- **T-095:** `runden_aus_journal` paart je **Instrument**, nicht je Position —
  bei gleichzeitigen Positionen im selben Instrument gehen bis zu 30 % der
  Runden verloren (1088 gegen 759 bei squeeze).
- **T-096:** per-Spur-Historienquellen fuer die Feed-Spuren
  (`moondev_funding` kann als erste, dort liegt der Fundingsatz frei vor).
- Nicht nachrechenbar und mit Grund vermerkt: `moondev_whale`, `-liquidation`,
  `-sentiment`, `liq_wand`, `iv_wand`, `iv_waelle`, `robinhood_radar`,
  `kopier`, `kopier1zu1`, die Nautilus-Arme — sowie `scanner`, `xperp` (Perp),
  `swap`, `kraken`, weil sie keine Kerzen-Naht haben (T-091).

## Einen Lauf starten

```bash
cd Agenten/Handel
python historie.py --stand                       # was liegt an Daten
python historie.py --auffuellen --instrumente BTC-USDC,ETH-USDC,SOL-USDC --takte 1H,4H
python replay.py --spur squeeze --lauf ganz      # ganze Historie
python replay.py --spur squeeze --gegenprobe     # Kern gegen backtest_prognose pruefen
```

`--gegenprobe` ist das Tor: `squeeze` muss ueber den neuen Kern **dieselben
Runden** liefern wie das seit 21.09.2026 im Betrieb laufende
`backtest_prognose.py`. Liefert er sie nicht, ist der Kern falsch — nicht der
alte Rechner.
