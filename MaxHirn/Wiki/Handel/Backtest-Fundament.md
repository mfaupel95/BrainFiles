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

Quelle: `Agenten/Handel/historie_binance.py`, `replay.py`, Spezifikation
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
| `historie_binance.py` | Kerzen und Fundingsaetze von Binance holen und in `daten/historie/` ablegen |
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

## Erste Parametersuche (2026-09-25, 24 Monate, vier Halbjahres-Fenster)

Gesucht wurde ueber `pflicht_stop_prozent_min` und `ziel_r_vielfaches`; der
Deckel `pflicht_stop_prozent_max` flog raus (8 und 12 lieferten Runde fuer Runde
identische Zahlen - der ATR-Stop bleibt darunter, ein totes Rasterfeld).

**Kein Kandidat gewinnt alle vier Fenster** - bei beiden Spuren nicht. In JEDER
Spur ist eines der vier Halbjahre fuer JEDEN Parameter negativ (supertrend
F1/F3, squeeze F3). Das ist ein Marktregime, kein Parameterproblem.

Der eigentliche Befund ist eine **monotone Beziehung** (squeeze, netto je Runde):

| Stop-Breite | schlechtestes Fenster | bestes Fenster |
|---|---|---|
| 3 % | **−1,13 %** | +0,51 % |
| 5 % | −3,39 % | +2,57 % |
| 7 % | −5,04 % | +3,24 % |

Die Stop-Breite steuert nicht den Gewinn, sondern wie tief das schlechte Fenster
schneidet. Die Frage ist damit keine Optimierungsfrage mehr ("welcher Parameter
ist der beste?"), sondern eine Risikofrage ("welches Profil will ich?") - und
die entscheidet Max, nicht der Optimierer.

**Vier Fehler des Optimierers, alle am 2026-09-25 gefunden und mit Tests
festgenagelt** (jeder haette eine falsche Empfehlung erzeugt):

1. Vergleich **brutto** statt netto → empfiehlt die Einstellung mit den meisten
   Runden, weil jede Runde 2 x Gebuehr kostet.
2. Vergleich gegen die **eigene Suchhaelfte** statt gegen die heutige Einstellung
   → mass den Regimewechsel zwischen den Haelften und liess **18 von 18**
   Kandidaten durch (supertrend) bzw. 14 von 18 (squeeze).
3. Mindestrundenzahl **8** war zu lasch (bei ~0,5 % Vorsprung und ~5 % Streuung
   braucht es Groessenordnung 100) → jetzt 30 plus Mindestvorsprung 0,10 %.
4. Bei mehreren Fenstern war **"erstes gegen letztes"** willkuerlich → jetzt muss
   ein Kandidat JEDES auswertbare Fenster gewinnen (`urteil_walkforward`).

**Merksatz:** Ein Backtest liefert erst dann eine Zahl, wenn Uhr, Fensterteilung,
Vergleichsmass und Gebuehr nachgerechnet sind. Alle vier waren in dieser Sitzung
zuerst falsch - und jede Fassung sah wie ein Ergebnis aus.

## Feed-Spuren: echte Laeufe ueber 2021-2026 (2026-09-29)

Die vier Feed-Spuren entscheiden ueber einen MARKTQUERSCHNITT, nicht ueber eine
Kerzenreihe. `replay.lauf_feed()` faehrt sie deshalb ueber den Querschnitt: ein
Schritt ist ein ZEITPUNKT, kein Instrument. Die Daten kommen aus
`moondev_historie.py` (Ablage `daten/historie/feed/`), nicht von CoinGecko -
die Feldnamen uebersetzt ein Adapter, und `tests/test_replay_feed.py` prueft
sie gegen den QUELLTEXT der Spur: wer die Spur umbaut, soll einen roten Test
bekommen statt einen stillen Nullauf.

| Spur | Takt | Runden | Treffer | Stop/Ziel | netto je Runde | Schritte | Universum |
|---|---|---|---|---|---|---|---|
| moondev_topmovers | 1D | 55 | 60 % | 8 %/12 % | +9.40 % | 2098 | 300 |
| moondev_marktlage | 1D | 5 | 60 % | 6 %/9 % | -1.12 % | 2098 | 300 |
| moondev_signalwelle | 1H | 62 | 34 % | 7 %/10,5 % | -1.83 % | 21628 | 41 |
| moondev_funding | 8h | 23 | 74 % | 6 %/9 % | +5.99 % | 7829 | 6 Instrumente |

ROH, ohne Deutung, mit drei Vorbehalten, die dazugehoeren:

- **moondev_funding ist abgebrochen**: `kill_ausgeloest = true`, die eigene
  Ratsche hat den Lauf beendet. Die 23 Runden decken NICHT den ganzen Zeitraum
  - die Zahl ist ein Anfang, kein Ergebnis.
- **Die Signalwelle rechnet auf einem kleineren Universum als im Betrieb**
  (Top 41 mit 1H-Kerzen gegen 250 Coins live). 62 Runden sind damit nicht mit
  dem Betrieb vergleichbar.
- **Die Marktbreite ist nach oben verzerrt**: nur Ueberlebende. Ein 2023
  delistetes Paar fehlt, und wer fehlt, kann nicht unter seiner EMA200 liegen.
  "Breite 100 %" heisst hier "von den HEUTE noch gehandelten Paaren standen
  alle darueber".

### Nicht nachrechenbar (mit Grund)

| Spur | Grund |
|---|---|
| moondev_sniper | pump.fun-Neulaunches mit Alter in Minuten - nur live |
| moondev_listingarb | Marktkapitalisierung frei nicht historisch abrufbar |
| moondev_whale | OKX-OI-Historie antwortet 50030 Illegal time range |
| moondev_liquidation | keine freie Liquidationshistorie |
| moondev_sentiment | RSS-Titel werden nicht archiviert |

Die Gruende stehen im Code (`replay.NICHT_NACHRECHENBAR`) und werden im Bericht
genannt - ein leeres Feld waere nicht zu deuten. Ein Lauf ueber eine nicht
nachrechenbare Spur bricht mit RuntimeError ab, statt zu raten.

### Die Gegenprobe

`GegenprobeTest` haelt den Adapter gegen die Wirklichkeit: die Preise, die die
Spuren sich im Betrieb SELBST geholt haben (ihre echten Journals, Quelle
CoinGecko) gegen die Binance-Tageskerze desselben Tages. 40 Preise verglichen,
groesste Abweichung 13,5 % - zwei Boersen sind zwei Preise, geprueft wird die
Groessenordnung (Toleranz 25 %), nicht die Stelle hinter dem Komma.

Ein frischer CoinGecko-Abzug ist von diesem Rechner nicht zu bekommen (HTTP 403
von Cloudflare); der Test benennt das als SKIP statt still zu bestehen.
`daten_probe_coingecko.py` zeichnet ihn auf, wenn das Netz mitspielt.

### Lehre: ein Test, der den Quelltext liest, muss ihn PARSEN

Zweimal an einem Tag zugeschlagen: ein Test suchte `lade_wachen` bzw.
`import ereignis` per Textsuche im Quelltext und fand den Namen zuerst im
DOCSTRING/KOMMENTAR, der ihn begruendet - beide Male meldete er falsch. Der
Importcheck parst jetzt mit `ast` und prueft die Reihenfolge der echten
Importknoten.

### Drei Fehler, die die echten Laeufe aufgedeckt haben

1. `main()` rechnete die Fensterbreite ueber `lade_wachen()` VOR den neuen
   Zweigen; das gibt es nur bei Familie A - beide Feed-Laeufe starben mit
   AttributeError, bevor ein Schritt gerechnet war.
2. `gebuehr_fuer()` holte die Wachen ebenso; die Kostenrechnung haengt jetzt an
   keiner Spurenfamilie (`wachen_von()` liest die DATEI).
3. `lauf_feed` importierte `ereignis` vor `spur_buch`; spur_buch legt beim
   Import Agenten/Bus auf den Suchpfad - andersherum faellt der Import um.

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
python historie_binance.py --stand                       # was liegt an Daten
python historie_binance.py --auffuellen --instrumente BTC-USDC,ETH-USDC,SOL-USDC --takte 1H,4H
python replay.py --spur squeeze --lauf ganz      # ganze Historie
python replay.py --spur squeeze --gegenprobe     # Kern gegen backtest_prognose pruefen
```

Die Feed-Spuren brauchen eigene Daten und einen eigenen Weg:

```bash
cd Agenten/Handel
python moondev_historie.py --universum 300 --takt 1D     # Top 300, Tageskerzen
python moondev_historie.py --stunden 40 --takt 1H        # Top 40 + Funding-Instrumente, stuendlich
python moondev_historie.py --funding spur                # Funding der Spur-Instrumente
python moondev_historie.py --stand
python replay.py --spur moondev_topmovers  --feed --lauf ganz --takt 1D
python replay.py --spur moondev_marktlage  --feed --lauf ganz --takt 1D
python replay.py --spur moondev_signalwelle --feed --lauf ganz --takt 1H
python replay.py --spur moondev_funding    --familie-c --lauf ganz
```

Nicht abrufbare Symbole (Binance fuehrt zwei USDT-Paare mit chinesischen Namen,
`urllib` kann solche Adressen nicht kodieren und der Fehler reisst den ganzen
Abruf ab) fliegen aus dem Universum und werden im Stand als `verworfen`
GENANNT - nie still weggelassen.

`--gegenprobe` ist das Tor: `squeeze` muss ueber den neuen Kern **dieselben
Runden** liefern wie das seit 21.09.2026 im Betrieb laufende
`backtest_prognose.py`. Liefert er sie nicht, ist der Kern falsch — nicht der
alte Rechner.
