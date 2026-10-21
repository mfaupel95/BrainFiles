---
id: 20260925-backtest-fundament
title: 'Handel — Backtest-Fundament (historische Daten)'
tags: [handel, backtest]
created: 2026-09-25
updated: 2026-10-07
related: ['[[Handel/Spuren-Uebersicht]]', '[[Handel/Kosten-und-Bedingungen]]', '[[Wissen/Handelsregeln]]']
summary: 'Wie die Spuren ueber 5,7 Jahre historische Daten nachgerechnet werden, was dabei herauskam und welche vier Fallen die Umsetzung aufgedeckt hat.'
---

# Backtest-Fundament

Quelle: `Agenten/Handel/historie_binance.py`, `replay.py`, Spezifikation
`Agenten/Handel/docs/design/2026-09-24-backtest-fundament-design.md`,
Plan `Werkstatt/Projekte/handel/plans/2026-09-24-backtest-fundament.md`.

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
| `historie_okx.py` | XPERP-Futures-Kerzen von OKX holen und in `daten/historie_okx/` ablegen - fuer Familie E (xperp), samt Kontrakt-Metadaten (`_instrumente.json`) |
| `replay.py` | eine Spur ueber die Historie fahren, ohne eine echte Datei anzufassen |
| `optimieren.py` | Parametersuche mit Walk-Forward (noch nicht gebaut) |

**Datenquelle ist fuer die meisten Spuren Binance, nicht die Boerse der Spur.**
Das ist ein bewusster Proxy (BTC-USDC/OKX und BTCUSDT/Binance laufen ueber
Arbitrage praktisch gleich), aber jedes Ergebnis traegt `kerzenquelle: binance`
— es wird nie als OKX- oder Krakenkurs ausgegeben. **Die Ausnahme ist Familie E
(xperp):** die laedt die Kerzen ueber `historie_okx.py` von der OKX-Futures-API
und traegt im Ergebnis `kerzenquelle: okx`.

## Die Spurenfamilien

| Familie | Wie das Buch laeuft | Wie der Replay andockt |
|---|---|---|
| **A** | Buch im eigenen Modul (`lade_wachen`, `journal`, `pruefe_einstieg`, `pruefe_ausstiege`), Daten ueber eine `*_quelle`-Naht | Naht besetzen, `pruefe_*` je Schritt rufen |
| **B** | `spur_buch.zyklus(ordner, quelle, signal, …)` — `quelle` und `signal` kommen **als Argumente** | eigene `quelle` unterlegen, `zyklus` je Schritt rufen |
| **C** | Spur mit eigenem `lauf(modus)` und eigenem Datensatz (moondev_funding) | eigene Quelle unterlegen, `lauf` je Schritt rufen |
| **D** | Mehrzeitrahmen (mosaic) bzw. eigene Rechnung (gitter, `walk()`) | Kerzen + Uhr liefern, die Spur entscheidet und bucht |
| **E** | Signal in `bot.py` (xperp), Kerzen von OKX-Futures | `bot.py` ueber den Pfad laden, `zeige_lage/trend/grid` je Schritt rufen |

Die Familie erkennt der Replay am **SPURNAMEN** — kein Schalter, der vergessen
werden kann (Familie E zusaetzlich ueber `--familie-e`). Details zu C, D und E
stehen in den Abschnitten weiter unten.

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

### Nachgeprueft am 30.09.2026: die Regel wirkt — und ein Vorzeichenfehler im Paarer

Unabhaengig nachgemessen (`Agenten/Handel/kerzenschluss_bias.py`, je
Austrittszeile, ohne Paarung): **wavetrend/ganz 0 % der Ausstiege auf der Marke,
wavetrend/nach177 100 %** — die Regel tut, was sie soll. Der alte Kerzenschluss
lag netto **492 Prozentpunkte zu schlecht**: auf der Verlustseite 938 Punkte
tiefer als der Stop, auf der Gewinnseite 445 Punkte ueber dem Ziel. Die
Verlustseite dominiert, weil ein Stop im Docht weit unter dem Stop schliessen
kann — die frueher notierte Lesart („die Gewinner sind zu gut") beschreibt nur
die kleinere Haelfte.

**Dabei kam ein Fehler heraus, der die Tabelle oben mitbetrifft:**
`kosten_wendepunkt._paarung_form_b` rechnete das Rundenergebnis OHNE die
Handelsrichtung. Fuer wavetrend (55 % Shorts) standen damit Trefferquote 54,2 %
und Summe +679 in der Auswertung; richtig sind **33,2 % und -513**. Betroffen ist
jede gemischt handelnde Spur — squeeze, macd_mtf, supertrend und wavetrend haben
rund 50 % Shorts je Buch. Behoben am 30.09.2026 (`seite` aus der
Einstiegszeile), Test `tests/test_kosten_wendepunkt.RichtungTest`.

Fuer die Tabelle oben heisst das: die RICHTUNG der Aussagen bleibt (die Regel
verschiebt nur den Ausstiegskurs, nicht den Ausloeser), die ZAHLEN der vier
Indikator-Spuren sind nachzurechnen — als **T-230** notiert. Supertrend bleibt
davon unberuehrt in seiner Aussage (492/492 schon vorher): seine eigene
Ausstiegsrechnung schreibt den Markenpreis.

Merksatz: **drei Wege muessen dasselbe sagen.** Zeilenrechnung,
Schluessel-Paarung ueber `(inst, stop, ziel)` und `kosten_wendepunkt.paarung`
gaben +492 / +492 / **-47,7** — der Ausreisser war der Fehler, nicht die
Mehrheit.

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
  `kopier`, `kopier1zu1`, die Nautilus-Arme — sowie `scanner`, `swap`,
  `kraken`, weil sie keine Kerzen-Naht haben (T-091). **`xperp` ist seit dem
  07.10.2026 aus dieser Liste heraus** — es faehrt jetzt ueber Familie E
  (OKX-Futures-Kerzen + `bot.py`, siehe unten).

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

Familie E (xperp) braucht die OKX-Futures-Historie und einen eigenen Weg:

```bash
cd Agenten/Handel
python historie_okx.py --auffuellen --instrumente RE,BTC --takte 1H,4H   # Kerzen + _instrumente.json
python historie_okx.py --stand
python replay.py --spur xperp --lauf test --max-kerzen 320               # bot-methode trend (Vorgabe)
python replay.py --spur xperp --lauf lage  --bot-methode lage  --max-kerzen 320
python replay.py --spur xperp --lauf grid  --bot-methode grid  --max-kerzen 320
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

## Ein zu kleines Fenster ist keine fehlende Historie (2026-10-01)

Gemeldet aus dem Leitstand-Reiter: `replay.py --spur supertrend --max-kerzen 200`
brach ab mit

    RuntimeError: keine Historie fuer supertrend - erst
    'python historie_binance.py --auffuellen'

— obwohl in `daten/historie/` **12.559 4H-Kerzen je Reihe** lagen. Die
Anweisung war falsch und hätte nichts geändert: Nachfüllen war nie das Problem.

Ursache war die **Reihenfolge** in `kerzen_fuer()`: die Reihe wurde ZUERST auf
`max_kerzen` geschnitten und DANACH gegen `mindest_kerzen + 20` geprüft. Mit 200
Kerzen gegen einen Bedarf von 320 fiel jedes Instrument aus dem Lauf — und der
Text nannte das einzige Übel, das nicht vorlag. `lauf_b` (Familie B) hatte
dieselbe Form: der Schnitt lag vor der Schleife `range(mindest_kerzen, laenge)`,
die dann leer lief und **0 Runden** meldete. Eine Zahl, die wie ein Messergebnis
aussieht und keines ist.

Seit 01.10.2026 werden zwei Gründe getrennt benannt — sie verlangen zwei
verschiedene Taten:

| Befund | Text | Tat |
|---|---|---|
| Historie auf der Platte zu kurz | „Historie fehlt oder ist zu kurz … erst `historie_binance.py --auffuellen`" | nachfüllen |
| `--max-kerzen` unter dem Bedarf der Spur | „Fenster zu klein … braucht mindestens 320 Kerzen je Reihe (mindest_kerzen 300 + 20). Mit `--max-kerzen 320` oder mehr (0 = alle) wiederholen" | Fenster größer |

Der Bedarf steht an EINER Stelle (`replay.bedarf(w) = mindest_kerzen + 20`,
Konstante `KERZEN_PUFFER`), weil die Schleife in `lauf_a` von `mindest_kerzen`
bis ans Ende läuft — mit genau `mindest_kerzen` Kerzen gäbe es keinen einzigen
Schritt. Die Schleuse sitzt in `kerzen_fuer()` selbst (`HistorieFehlt`), damit
auch `gegenprobe()` nicht mehr mit leerem Kerzen-Dict durchläuft und zweimal
null Runden als „gleich: true" meldet — das war ein falscher Freispruch.
Auf der Kommandozeile: eine Zeile auf stderr statt eines Tracebacks, Exit 2.
`--fenster` (Kerzen je Schritt) wird genauso geprüft; ein von Hand gesetztes
Fenster unter dem Bedarf lief vorher ebenfalls still in „0 Runden".

Der Leitstand-Reiter prüft die Grenze VOR dem Start
(`leitstand_backtests.pruefe_replay` → `replay.bedarf_fuer(spur)`, liest die
`wachen.json` direkt, ohne das Spurenmodul zu laden) und zeigt den Satz in der
Meldezeile statt eines Tracebacks im Protokoll.

**Merksatz:** Wird eine Prüfung nach dem Schneiden gemacht, nennt sie das
falsche Übel — erst messen, was DA ist, dann schneiden, und beide Fälle im Text
unterscheiden. Und: ein Lauf, der „0 Runden" melden kann, ohne je einen Schritt
gerechnet zu haben, ist kein Messergebnis, sondern ein stiller Ausfall.

Bedarf je Spur (gemessen 01.10.2026): supertrend 320 (mindest_kerzen 300),
macd_mtf 620 (600), squeeze/wavetrend/mosaic 320, gitter/orb/orbk 320 (Vorgabe,
die `wachen.json` trägt kein `mindest_kerzen`). Ein Lauf mit 320 Kerzen im
4H-Takt rechnet 20 Schritte — genug für einen Rauchtest, nicht für eine Zahl.
Tests: `Agenten/Handel/tests/test_replay.py` (`FensterOderHistorieTest`, 7) und
`tests/test_leitstand_backtests.py` (Replay, +3).

### Was der Replay NICHT fahren kann (01.10.2026)

`orb` und `orbk` standen in `replay.SPUREN_TEIL_A` — und damit in der Spurliste des
Leitstand-Reiters —, aber JEDER Lauf endete in einer Verweigerung: ihr `handeln.py` hat
kein `lade_wachen()`, und ihre `wachen.json` nennt die Instrumente als DICT mit
**Börsennamen** (`BTC_USDT` → `BTC-USDT-SWAP`) statt als Liste von Spur-Namen, dazu ohne
`kerzen_takt`/`mindest_kerzen`. Sie stehen jetzt in `replay.NICHT_NACHRECHENBAR` mit Grund
(`orbk` hat einen eigenen Backtest: `orbk/backtest.py`); das Fenster bietet sechs Spuren an
(squeeze, wavetrend, macd_mtf, supertrend, gitter, mosaic).

**Merksatz: eine angebotene Taste, die nur scheitern kann, ist schlechter als eine
fehlende.** Die Prüfung ist ein Blick ins Spurenmodul (`lade_wachen()` vorhanden?) und in
die Wachen (`instrumente` als Liste von Spur-Namen? Takt und `mindest_kerzen` gesetzt?),
nicht ein Blick auf den Ordnernamen.

### Die Gebuehr kommt aus der Spur, nicht von der Kommandozeile (01.10.2026)

`replay.py --gebuehr` stand fest auf **0.1 %/Seite**. Fuer die vier Indikator-Spuren
(OKX-Spot, gemessen 0,10 %) war das richtig - fuer `mosaic` (Kraken, **0,60 %**)
rechnete damit jeder Backtest SECHSMAL zu guenstig, und die Zahl sah plausibel aus.
Die Vorgabe ist jetzt der gemessene Satz der Spur (`gebuehr_taker` x 100 aus ihrer
`wachen.json`); ein ausdrueckliches `--gebuehr` schlaegt sie, auch `0`. Der Lauf
schreibt beides ins Ergebnis (`gebuehr_pct`, `gebuehr_quelle`), der Leitstand laesst
das Feld leer und zeigt daneben "Satz der Spur: 0.6 %/Seite".

**Merksatz: eine Vorgabe, die fuer eine Spur richtig ist, ist fuer die naechste
geraten.** Wo die Zahl eine Eigenschaft der Sache ist (der Markt der Spur), wird sie
aus der Sache gelesen - nicht in den Aufruf geschrieben.

### Nachgemessen 01.10.2026: die Zahlen von 29.09. sind ueberholt (Kerzenschluss-Regel)

Vier Spuren ueber die volle Historie, Ausstieg an der Marke, Gebuehr aus der Wachen
(0,10 %/Seite = 0,20 % je Runde, OKX-Spot):

    Spur         Runden   Treffer   f_max/Runde   Abstand zur Rundengebuehr   Ergebnis-Summe
    supertrend     854     35,8 %     0,380 %       1,90x                     +134,80
    squeeze       1088     34,9 %     0,239 %       1,20x                     +260,15
    macd_mtf      1209     34,7 %     0,200 %       1,00x (genau null)        +207,96
    wavetrend     1506     33,2 %    -0,020 %      -0,10x (tot)               -20,94

Die Zahlen vom 29.09. (squeeze 759/51,0 %, wavetrend 1128/54,3 %, macd_mtf 774/53,2 %,
supertrend 854/49,8 %) sind damit **ueberholt** - nicht wegen der Gebuehr, sondern wegen
der **Kerzenschluss-Regel vom 30.09.**: der Ausstieg liegt jetzt an der beruehrten Marke
(sind beide Marken in einer Kerze, gilt der STOP), nicht am Schluss der Kerze. Die
Trefferquote faellt dadurch um 15-20 Punkte (51-54 % -> 33-36 %), und `f_max` rutscht an
die Rundengebuehr heran:

- **supertrend** behaelt als einzige Luft (1,90x); nur 492 ihrer 854 Ausstiege liegen an
  einer Marke, der Rest endet per Frist.
- **squeeze** hat 20 % Luft, **macd_mtf** liegt EXAKT auf der Nulllinie (0,1997 % gegen
  0,200 %), **wavetrend** ist negativ - sie verliert schon bei 0 % Gebuehr.
- Auf Kraken (1,2 %/Runde) waere KEINE der vier tragfaehig.

**Merksatz: eine Trefferquote ohne die Ausstiegsregel daneben ist keine Kennzahl.** Wer die
51-54 % im Kopf hat, haelt diese vier fuer deutlich robuster als sie sind.

`mosaic` und `gitter` liessen sich zu diesem Zeitpunkt gar nicht fahren (mosaic:
`TypeError`, gitter: `AttributeError`) - beide standen aus der Replay-Liste heraus. Seit
dem 01.10.2026 fahren sie ueber den Familie-D-Weg (siehe unten, T-294/T-295).

### Familie D (01.10.2026): mosaic und gitter sind fahrbar (T-294/T-295)

Beide liessen sich bis dahin nicht fahren, und beide aus demselben Grund: ihre Fahrweise
passt nicht in den EINEN Aufruf `pruefe_einstieg(inst, k, z, w, faktor)` /
`pruefe_ausstiege(z, k, w)`.

    python replay.py --spur mosaic --lauf t294
    python replay.py --spur gitter --lauf t295

Einen Schalter gibt es nicht - der Replay erkennt die Familie am SPURNAMEN. Ein Schalter
waere eine zweite Wahrheit, und `--spur mosaic` ohne ihn liefe genau in den `TypeError`,
den der Adapter behebt.

- **mosaic** braucht DREI Kerzenreihen (4H/30M/5M). Sie kommen aus EINER 5m-Basis und
  werden verdichtet; eine groebere Kerze zaehlt erst, wenn sie ABGESCHLOSSEN ist (die
  laufende 4H-Kerze waere ein Blick in die Zukunft und entwertete jede Kennzahl darauf).
  120 Tage 5m nachladen: `python 5m_historie_holen.py --tage 120`.
  Ergebnis 03.06.-01.10.2026: **16 Runden, 4 offen**, Treffer 75 %, `f_max` 6,25 % je
  Runde, Summe +100 USD auf 100 USD Nominal (Kraken-Satz 0,60 %/Seite, BRUTTO im
  Journal - die Gebuehr steckt in der Replay-Kennzahl).
- **gitter** bringt seine Rechnung selbst mit (`walk()`); der Replay liefert Kerzen und
  Uhr und nimmt seine Journalzeilen ab. Auf der 1H-Historie (50.223 Kerzen, BTC-USDT):
  **31 Zyklen, +504 USD auf 1000 Einsatz (+50,4 %)** - Halten waere +191 % gewesen.
  `kosten_wendepunkt` kann dieses Journal nicht auswerten: eine Gitterstufe hat keinen
  Stop und kein Ziel.

**Determinismus ist geprueft, nicht behauptet**: zwei Laeufe ueber dieselben Kerzen
ergeben ein byte-gleiches Journal (`tests/test_replay_familie_d.py`). Dafuer musste die
Positionskennung festgenagelt werden - ihr Zufallsteil ist im BETRIEB richtig (zwei
Positionen im selben Instrument entstehen in derselben Sekunde, die Zeit allein waere
kein eindeutiger Schluessel) und machte zwei Backtest-Laeufe ungleich
(`replay.kennung_fest()`).

### Familie E (06./07.10.2026): xperp ueber OKX-Futures und bot.py

xperp war bis dahin nicht nachrechenbar (keine Kerzen-Naht, T-091). Seit dem
07.10.2026 faehrt es als **Familie E**: die Kerzen kommen von der
OKX-Futures-API (`historie_okx.py`), das Signal aus `xperp/bot.py` — die Spur
entscheidet, der Replay liefert Zeit und Daten.

```bash
cd Agenten/Handel
python historie_okx.py --auffuellen --instrumente RE,BTC --takte 1H,4H   # Kerzen + _instrumente.json
python historie_okx.py --stand                                          # was liegt an Daten
python replay.py --spur xperp --lauf test --max-kerzen 320             # Vorgabe: bot-methode trend
python replay.py --spur xperp --lauf lage  --bot-methode lage  --max-kerzen 320
python replay.py --spur xperp --lauf grid  --bot-methode grid  --max-kerzen 320
```

**Neue Argumente (nur Familie E):**

- `--bot-methode {lage,trend,grid}` — welche `bot.py`-Methode gefahren wird.
  Vorgabe **`trend`** (der Live-Pfad der Spur). `lage` rechnet nur das Signal
  und erzeugt **keine Order** (0 Runden sind dort ein gueltiges Ergebnis);
  `trend` legt EINE Order mit Limit/Stop/Ziel aus den Wachen-Faktoren;
  `grid` eine Leiter von Long-Stufen mit gemeinsamem Boden-Stop. Die Wahl
  steht im Ergebnis (`bot_methode`).
- `--familie-e` — optional; der Replay erkennt die Familie ohnehin am
  Spurnamen (`--spur xperp` reicht).

**Anforderungen (sonst bricht der Lauf mit Grund ab):**

- **OKX-Historie:** `python historie_okx.py --auffuellen` legt
  `daten/historie_okx/<VOLLER_INSTID>_<takt>.json` an. XPERP-Kontrakte laufen
  erst seit **Mai 2026** — weiter zurueck gibt es keine Kerzen (Datengrenze,
  kein Fehler). Ein Rollover sind zwei Reihen unter vollem instId.
- **Kontrakt-Metadaten:** `_instrumente.json` (ctVal/lotSz/minSz/tickSz) wird
  beim `--auffuellen` mitgeschrieben; ohne sie bricht der Lauf mit KeyError
  ab, statt mit Attrappenwerten zu rechnen.
- **`bot.py` ueber den Pfad** (`replay._bot_modul`): xperp wird nur waehrend
  des Ladens kurz auf `sys.path` gelegt und danach wieder entfernt — die
  Lehre aus `spur_modul()`, eine Reihenfolge der Eintraege entscheidet, welche
  Fassung geladen wird.
- **Instrumente aus der wachen.json:** xperp traegt kein `instrumente`-Feld,
  sondern `familien` (krypto/aktie/rohstoff) mit je `aktiv` + `instCategory`.
  `replay._insts_okx` loest die aktiven Familien netzfrei ueber die
  Metadaten-Datei auf — keine zweite Instrumentenliste neben der Wachen.
- `mindest_kerzen` fehlt in der Wachen und wird auf **300** gesetzt (so viele
  Kerzen holt `bot.py` in `hole()`).

**OKX-Unterschiede, die nur Familie E behandelt:**

- instIds tragen ein Ablaufdatum (`RE-USD_UM_XPERP-310620`); Kerzen liegen
  unter dem VOLLEN instId, Basisnamen werden ueber die Metadaten aufgeloest.
- `bot.py` rechnet auf **4H-Kerzen** (`bot.BAR`), nicht auf dem Wachen-Takt.
- Der Hebel-Deckel will Tageskerzen; die kommen aus derselben 4H-Reihe
  **verdichtet** (Test-Seam `tages_kerzen_quelle`).
- Der 24h-Umsatz (Tor in `zeige_lage`) ist aus den Kerzen **geschaetzt**
  (Summe Volumen x Schluss der letzten 24 h) — historische Ticker gibt es
  nicht.
- **CVD faellt aus** (keine Taker-Volumen-Historie in Kerzen): das Signal
  bleibt vollstaendig, nur „kein CVD" steht im Grund (`cvd_quelle`-Naht).

**Zwei dokumentierte Grenzen (T-096 legt sie offen):**

1. **Funding ist nicht in den Kerzen** (`funding() -> None`): die
   Pruefpflicht rechnet ohne Funding-Kosten, das Journal fuehrt keinen
   Funding-Beitrag. Live zahlt eine gehaltene XPERP-Position alle 8 h.
2. **Der Kill-Switch wird nicht abgebildet** (wie in allen Familien): ein
   Lauf kann ueber den Deckel hinaus weiterhandeln, den die lebende Wache
   haette schliessen lassen.

**Ausstiegslogik (Familie E):**

- **Fill am Limit:** `bot.py` legt LIMIT-Orders (der Long-Einstieg liegt
  `einstieg_atr_abschlag` unter dem Markt). Eine Order wird erst gebucht, wenn
  eine Kerze das Limit beruehrt (Long: Tief <= Limit) — wie im Betrieb, wo
  `handeln.py` wartende Auftraege fuehrt, sobald die Boerse fuellt. Nach
  `order_gueltig_kerzen` (Wachen-Feld, Vorgabe 24 = 4 Tage bei 4H) verfaellt
  eine ungefuellte Order. Ein Instant-Fill zum Limitpreis waere die in T-096
  dokumentierte Falle (besser als live moeglich).
- **Ausstiege ueber Stop/Ziel an der Kerze** — dieselbe Beruehrungsregel wie
  in allen Familien (T-177): liegt die Marke in der Kerze, ist sie der
  Ausstieg; liegen beide drin, gilt der Stop. Der Ausloeser bleibt der
  Kerzenschluss.
- **Ein Anlauf je Instrument:** neue Orders kommen nur, wenn das Instrument
  weder Position noch offenes Limit hat (Live: ein Anlauf je Wert).

Geschrieben wird ausschliesslich unter `daten/backtest/xperp/<lauf>/`; der
echte Spurenordner bleibt unberuehrt. Tests: `tests/test_replay_familie_e.py`
(Mechanik mit Bot-Stub + echte `bot.py` unter dem okxf-Ersatz, kein Netz) und
`tests/test_historie_okx.py`. Der Leitstand bietet xperp seit dem 07.10.2026
in der Replay-Liste an.

## Der Drawdown der omnitrade-Rust-Engine war ein Buchungsartefakt (T-287/T-292)

Der Rust-Backtest (`Werkstatt/omnitrade`) meldete `max_drawdown` 72-90 % auf einer Kurve,
die nie gefallen ist. Ursache ist die BUCHUNG, nicht das Risiko:

`AccountState::apply_buy_fill` zieht den Nennwert VOLL vom Guthaben ab (der Short bucht
ihn in `apply_sell_fill` voll zu), `total_equity` rechnete aber nur
`balance + unrealized_pnl`. Waehrend einer offenen Long-Position stand die Equity damit
auf Hoehe des unrealisierten PnL - ein Einbruch um die halbe Kontogroesse beim Einstieg
und sofort die grosse Drawdown-Kurve.

Behoben mit `Position::market_value()` (vorzeichenrichtig: Long `+notional + unrealized`,
Short `-notional + unrealized` = `+/- quantity * current_price`) und einem
`total_equity`, das diesen Marktwert summiert. PnL, Rundenzahl und Trefferquote waren
unberuehrt - die Equity holt sich beim Schliessen zurueck, was sie beim Oeffnen verliert.

    adx_macd, BTC-1h, 10000 Start, 0,05 %/Seite, OMNI_LONG_ONLY=1
      vorher   PnL 1397,84   Runden 9   Treffer 33,33 %   Max Drawdown 75,18 %
      nachher  PnL 1397,84   Runden 9   Treffer 33,33 %   Max Drawdown  8,15 %

Gegenprobe: mit der alten Formel faellt der neue Backtest-Test mit `max_drawdown 0.5` -
er belegt den Fehler, nicht nur die Aenderung. `cargo test --workspace`: 325 gruen.

**Merksatz: eine Equity, die den Positionswert nicht mitzaehlt, macht aus jedem Einstieg
einen Absturz. Der Drawdown war die einzige falsche Zahl - und genau die, aus der Grenzen
abgeleitet werden.**
