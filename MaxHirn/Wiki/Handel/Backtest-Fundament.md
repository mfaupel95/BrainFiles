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
| moondev_signalwelle | 1H | 62 | 34 % | 7 %/10,5 % | -1.83 % | 50337 | 41 |
| moondev_funding | 8h | 23 | 74 % | 6 %/9 % | +5.99 % | 6369 | 6 Instrumente |

**Die Schrittzahl haengt an `--mindest-symbole`** (ab wie vielen Reihen ein
Zeitpunkt als Schritt zaehlt): die Signalwelle liefert mit der strengen Vorgabe
30 genau 21.628 Schritte, mit 20 genau 50.337 - und in BEIDEN Laeufen dieselben
62 Runden. Die duennen Zeitpunkte bringen also kein Signal; wer zwei Laeufe
vergleicht, muss diese Zahl mitlesen, sonst sieht der Unterschied wie ein
Datenfehler aus.

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

### Die Gegenprobe: dieselbe Tageskerze auf zwei Boersen

Ein Adapter, den niemand gegen die Wirklichkeit gehalten hat, ist eine
Behauptung. `historie_probe.py --okx` holt deshalb die Schlusskurse der groessten
50 Paare von OKX, und `GegenprobeTest` haelt sie gegen die eigene Tafel:
**50 Paare, derselbe Zeitpunkt, alle innerhalb 5 %.**

Zwei Fehlversuche auf dem Weg dahin - beide waren Fehler des VERGLEICHS, nicht
der Daten, und beide haetten fast eine falsche Aussage ergeben:

1. Erst wurden Binances Tageskerze und OKX' Ticker "jetzt" verglichen. Vier
   Symbole lagen 10-11 % auseinander (CELO/BERA/ONE/HBAR). Kein
   Boersenunterschied: die Kerze war der Stand des ABRUF-Zeitpunkts am Morgen,
   der Ticker der Stand am Abend. Der Vergleich prueft die Uhr, nicht die Daten.
2. Dann Binance-Tageskerze gegen OKX-Tageskerze: **0 von 50** trafen sich. OKX'
   Tageskerze beginnt um 00:00 **UTC+8**, Binances um 00:00 UTC - dieselbe Zahl
   "1D" bedeutet dort eine andere Tagesgrenze.

Jetzt wird derselbe ZEITPUNKT verglichen: der Schluss der letzten
abgeschlossenen Binance-Tageskerze gegen die OKX-Stunde, die auf dieser Grenze
endet. Die letzte, noch laufende Tageskerze ist ausdruecklich ausgenommen - ihr
"Schluss" ist der Stand des Abrufs.

CoinGecko, die Quelle der Spuren im Betrieb, ist von diesem Rechner nicht mehr
zu bekommen (HTTP 403 von Cloudflare, gemessen am 29.09.2026); der Test benennt
das als SKIP statt still zu bestehen. `daten_probe_coingecko.py` zeichnet einen
Abzug auf, wenn das Netz mitspielt. Eine zweite Boerse leistet dasselbe.

### Lehre: ein Test, der den Quelltext liest, muss ihn PARSEN

Zweimal an einem Tag zugeschlagen: ein Test suchte `lade_wachen` bzw.
`import ereignis` per Textsuche im Quelltext und fand den Namen zuerst im
DOCSTRING/KOMMENTAR, der ihn begruendet - beide Male meldete er falsch. Der
Importcheck parst jetzt mit `ast` und prueft die Reihenfolge der echten
Importknoten.

### Der Kill-Schalter ist eine Sackgasse (2026-09-29)

Der Funding-Lauf endete nach **sechs Tagen** - `kill_ausgeloest = true`. Die
Ursache ist keine Einstellung, sondern der Bauart nach ein Fehler:

`spur_buch.zyklus` kehrt bei gesetztem `kill` SOFORT zurueck und leert die
Positionen (Zeile 571). Der Kill rechnet aber auf der KAPITALKURVE (Ruecklauf
vom Hoechststand). Zurueckkommen kann die Kurve nur durch neue Trades - und
genau die sperrt der Kill. **Ein einmal ausgeloester Kill geht nie wieder auf**,
in keinem Buch, das ueber `spur_buch` laeuft.

Im Lauf war das Buch zum Kill-Zeitpunkt im PLUS; der Kill feuerte auf den
Ruecklauf vom eigenen Hoechststand, nicht auf einen Verlust. Fuer den Betrieb
heisst das: eine Feed-Spur, die einmal 45 USD vom Hoch zurueckfaellt, handelt
danach fuer immer nicht mehr - bis jemand den Deckel von Hand hebt (bei xperp
am 21.09.2026 genau so passiert).

Fuer die Messung ueber den ganzen Zeitraum laeuft die Spur deshalb ein zweites
Mal mit erhoehtem Deckel - in der **Kopie** der Wachen
(`--setzen kill_switch_gesamt_usd=1000000`, Lauf `ohnekill`), nie an der echten
Wachen. Was gesetzt wurde, steht als `_backtest_gesetzt` in der Kopie.

### Offen nach diesem Durchgang

- Der Kill-Schalter geht nie wieder auf (oben) - Entscheidung Max, ob
  `spur_buch` nach einer Frist selbst wieder freigibt.
- ~~Ausstiege zum Kerzenschluss rechnen die Gewinner zu gut~~ - **erledigt am
  30.09.2026** (unten, "Die Beruehrungsregel"): der Ausstieg geschieht jetzt am
  beruehrten Kurs. Offen bleibt der DOCHT-Ausstieg (eine Beruehrung ohne
  Schluss jenseits der Marke loest weiterhin nichts aus).
- Die Einstiegszeile im Journal der Feed-Spuren traegt als Grund den
  Platzhalter "Der Grund, der im Journal steht." (aus `spur_buch`, auch im
  ECHTEN Journal). Der Ausstiegsgrund ist echt; der Einstiegsgrund sagt nichts.

### Die Beruehrungsregel (2026-09-30, T-177) - der Ausstieg sitzt auf der Marke

Ausgestiegen wurde zum SCHLUSS der Kerze, in der Stop oder Ziel beruehrt wurde -
nicht zu Stop- oder Zielkurs. Ein Laeufer ueberschiesst sein Ziel dadurch
deutlich: ADA stand mit Ziel +12 % im Buch und wurde mit +48 % geschlossen. Die
Gewinner wurden also zu GUT gerechnet, in beiden Familien gleich.

Jetzt gilt: **liegt die Marke in der Kerze, ist sie der Ausstieg** - gemessen am
Hoch (Long-Ziel) bzw. Tief (Long-Stop).

- **Eine Rechnung, zwei Wege:** `replay.beruehrte_marke(kerze, seite, stop, ziel)`
  gibt `stop`/`ziel`/`None`, `kurs_der_marke()` den Kurs. `replay.lauf_a`
  (Familie A) und `backtest_prognose.lauf` rufen dieselbe Funktion - vorher
  rechneten sie mit 10,0000 % gegen 10,4961 % dieselbe Bewegung zweimal.
- **Liegen beide Marken in einer Kerze, gilt der STOP.** Die guenstige
  Reihenfolge waere der Schoenheitsfehler; ein Backtest darf den Zweifel nicht
  zu seinen Gunsten aufloesen.
- **Der AUSLOESER bleibt der Schluss** - so entscheiden die Spuren live. Die
  Regel aendert nur den PREIS, nicht das WANN. Ein reiner Docht-Ausstieg ist
  bewusst nicht abgebildet.
- **Berichtigt wird die Journalzeile, nicht die Spur.** `replay.Beruehrungsjournal`
  sitzt vor `spur_buch.journal` (Familie B/C) bzw. vor dem Modul-Journal
  (Familie A): Markenpreis, `grund` und `einsatz_usd` (Erloes gerechnet wie die
  Spur, short spiegelverkehrt). Nur `grund` stop/ziel; Frist, Rueckdreh,
  Herzschlag und Buchbereinigung gehen unveraendert durch.
- `spur_buch.pruefe_ausstiege()` (LIVE-Pfad) ist **nicht angefasst**.
- **Gegenprobe an jeder Kennzahl:** `ausstiege_an_marke` / `ausstiege`, aus dem
  Journal gezaehlt (`replay.auf_der_marke`). Ein Lauf von vorher zeigt `0/1506`;
  `auswertung_alle.py` schreibt die Quote in jede Backtest-Zeile.
- **Die Stellenzahl der Zelle ist das MAXIMUM aus alter Zelle und Marke**
  (`_preis_text`): AUDIO stand mit Ziel 0,68171040 im Journal, die alte Zelle
  trug 0,681710 - die erste Fassung schnitt die Marke ab und der Ausstieg lag
  wieder daneben.

**Vorher/Nachher ueber sechs Spuren** (2021-01 bis 2026-09, Gebuehr 0,1 % je
Seite; `--lauf vor177` mit unveraendertem Code, `--lauf nach177` mit der Regel):

| Spur | Runden | Treffer | Summe vorher | Summe nachher | Ausstiege auf der Marke |
|---|---|---|---|---|---|
| wavetrend | 1128 -> 1128 | 54,3 % -> 54,3 % | +419,66 | +385,88 | 0/1506 -> 1506/1506 |
| macd_mtf | 774 -> 774 | 53,2 % -> 53,2 % | +299,90 | +285,02 | 0/1209 -> 1209/1209 |
| squeeze | 759 -> 759 | 51,0 % -> 51,0 % | +61,93 | **-6,34** | 0/1088 -> 1088/1088 |
| moondev_topmovers | 55 -> 135 | 60,0 % -> 49,6 % | +522,44 | +260,00 | 0/55 -> **134**/135 |
| moondev_funding | 21 -> 23 | 81,0 % -> 78,3 % | +156,50 | +87,00 | 0/21 -> 23/23 |
| supertrend | 854 -> 854 | 49,8 % -> 49,8 % | -24,17 | -24,17 | 492/492 -> 492/492 |

Was daran zu lesen ist:

- Bei **wavetrend, macd_mtf, squeeze und supertrend sind Rundenzahl und
  Trefferquote IDENTISCH** - die Regel verschiebt nur den Ausstiegskurs, nicht
  den Ausloeser. Das ist der beste Beleg, dass sie tut, was sie soll.
- **squeeze dreht ins Minus** (+61,93 -> -6,34): der ganze Vorsprung kam aus den
  zu guten Ausstiegen. Dieselbe Aussage gilt fuer jede Spur, deren Zahlen
  vorher im Plus lagen.
- **topmovers: 55 -> 135 Runden.** Das ist KEIN reiner Preisvergleich: der
  geaenderte Ausstiegskurs aendert den Buchpfad (Ratsche, freie Plaetze), also
  kommen zu den anderen Ausstiegen auch andere Einstiege. Wer die Zeile als
  Vorher/Nachher derselben Geschaefte liest, liest sie falsch.
- **supertrend war schon auf der Marke** (492/492 vorher): seine eigene
  Ausstiegsrechnung schreibt den Markenpreis - die Regel aendert dort nichts.
  Eine Regel, die nichts aendert, ist kein Widerspruch, sondern eine Messung.
- **Nicht abgebildet:** ein reiner Docht-Ausstieg (Beruehrung ohne Schluss
  jenseits der Marke) und ein Markenausstieg, der nur ueber mehrere Kerzen
  hinausgeht. Die Regel ist die untere Schranke der Ausstiegsqualitaet, kein
  Optimalpfad.
- **Eine Zeile blieb daneben:** 134 von 135 Ausstiegen des Feed-Laufs sitzen auf
  der Marke. Der eine Ausreisser ist `AUDIO`, 2021-03-06, Ziel 0,68171040 - die
  Zeile steht auf dem Kerzenschluss 0,681710, weil der Schritt fuer dieses
  Instrument keine Kerze bereitstellte. Der Zaehler dafuer ist
  `ohne_marke` in der Journal-Huelle; er steht seit dem 30.09.2026 im Bericht
  des Laufs neben `berichtigt` - **eine Ausnahme wird gezaehlt, nicht
  verschwiegen**.
- **Welcher Lauf gezeigt wird, ist selbst eine Regel:** `auswertung_alle`
  bevorzugt bei gleichem Umfang den Lauf MIT Kerzenuhr und dann den mit dem
  hoeheren Anteil Markenausstiege. Vorher entschied der Name - und `vor177`
  steht alphabetisch hinter `nach177`, also zeigte die Uebersicht genau den
  Lauf ohne die Regel (+0,372 % je Runde statt +0,342 %).

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
- **T-096 ist gebaut** (2026-09-29): Marktquerschnitt (`moondev_historie.py`),
  Adapter, `lauf_feed`, `lauf_c`, Gegenprobe. Offen bleiben die Spuren, deren
  Quelle es historisch nicht gibt (Tabelle oben).
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
python replay.py --spur moondev_signalwelle --feed --lauf ganz --takt 1H --mindest-symbole 20
python historie_probe.py --okx                   # zweite Boerse als Gegenprobe
```

`--setzen NAME=WERT` aendert einen Wert in der **Kopie** der Wachen - fuer
Spuren, deren Kill-Schalter den Lauf sonst abwuergt (siehe unten). Die echten
Wachen einer Spur werden davon nie beruehrt.

Nicht abrufbare Symbole (Binance fuehrt zwei USDT-Paare mit chinesischen Namen,
`urllib` kann solche Adressen nicht kodieren und der Fehler reisst den ganzen
Abruf ab) fliegen aus dem Universum und werden im Stand als `verworfen`
GENANNT - nie still weggelassen.

`--gegenprobe` ist das Tor: `squeeze` muss ueber den neuen Kern **dieselben
Runden** liefern wie das seit 21.09.2026 im Betrieb laufende
`backtest_prognose.py`. Liefert er sie nicht, ist der Kern falsch — nicht der
alte Rechner.

## Paarung je Position statt je Instrument (T-095, 30.09.2026)

Die Auswertung paarte Einstieg und Ausstieg ueber `offen[inst]` — **je
Instrument**, nicht je Position. Zwei gleichzeitige Positionen im selben
Instrument ueberschrieben einander; der ueberschriebene Einstieg war verloren
und seine Ausstiegszeile fand keinen Partner. Das traf jede Auswertung
(`kosten_wendepunkt`, `auswertung_alle`, `strategie_kennzahlen`), nicht nur den
Backtest — und die Teilmenge war nicht zufaellig: gleichzeitige Positionen im
selben Instrument sind eher gleichgerichtet.

Jetzt traegt jede Einstiegszeile eine Kennung (`pos_id`, Spalte am ENDE), die
Ausstiegszeile uebernimmt sie. Die gemeinsame Umsetzung ist
`Agenten/Handel/journalpaarung.py`; sie paart in vier Stufen:

1. **Kennung** — Ausstieg traegt die Kennung seines Einstiegs (Normalfall).
2. **Genau ein offener Einstieg** dieses Instruments (Altjournal) — eindeutig.
3. **Mehrere offene Einstiege** — Paarung ueber die kopierten
   Positionsmerkmale (Stop, Ziel, Kontrakte, Menge, Hebel, Seite). Ein
   Merkmal, das beide tragen und das sich unterscheidet, trennt sie.
4. **Sonst zweideutig** — die Zeile wird als unpaarig GEZAEHLT und im
   `stand()` ausgewiesen. Es wird nicht geraten.

Ein Altjournal ohne die Spalte bleibt lesbar: die Schreiber richten sich nach
dem **Kopf der Datei** (`pos_kennung.spalten`), ein Feld ohne Spalte wird
verworfen statt um einen Platz verschoben, und ein Journal ohne `pos_id`
meldet das einmalig auf stderr. Die vorhandenen Journale sind mit
`journal_pos_id_nachziehen.py` nachgezogen (Vorschau ist Standard).

### Vorher / Nachher (gemessen am 30.09.2026, `gegenprobe_alt_neu.py`)

Alte Regel und neue Regel ueber DIESELBEN Zeilen, nur die Paarung wechselt:

| Journal | alt (je Instrument) | neu (je Position) | zurueck |
|---|---|---|---|
| squeeze, Backtest 5,7 Jahre | 759 | **1088** | +329 |
| macd_mtf, Backtest | 774 | **1209** | +435 |
| wavetrend, Backtest | 1128 | **1506** | +378 |
| spiegel (Basis) | 934 | 1149 | +215 |
| kraken | 19 | 53 | +34 |
| kopier1zu1 | 13 | 29 | +16 |
| **Summe ueber alle Journale** | 23.999 | **29.414** | **+5.415** |

Drei Journale liefern WENIGER Runden: `scanner` 167 -> 156, `swap` 14 -> 11,
`xperp` 77 -> 71. Dort hat die alte Regel geraten — mehrere offene Einstiege
ohne Kennung, die kein Merkmal trennt (`zweideutig`: scanner 11, xperp 6,
swap 3). Die neue Regel zaehlt diese Zeilen als unpaarig, statt sie dem
falschen Einstieg zuzuschlagen. Weniger Runden sind hier die ehrlichere Zahl.

Gegenprobe im Konstrukt: zwei gleichzeitige Positionen im selben Instrument,
beide mit Ausstieg — alte Regel 1 Runde, neue Regel 2 Runden
(`Agenten/Handel/tests/test_journalpaarung.py`, 20 Tests).
