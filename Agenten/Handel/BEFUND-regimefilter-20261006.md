# BEFUND Regimefilter fuer die Prognose-Spuren (T-101) — 06.10.2026

Frage (T-101): laesst sich das schlechte Regime VORHER erkennen? Die erste
Parametersuche (25.09.2026) zeigte: in JEDER der vier Prognose-Spuren
(squeeze, wavetrend, macd_mtf, supertrend) ist ein Halbjahr fuer JEDEN
Parameter negativ, und die Stop-Breite wirkt monoton — eine Risiko-
einstellung, kein Hebel. Wenn es einen Hebel gibt, dann die Frage: laesst
sich das negative Fenster ankuendigen?

## Vorgehen

Fundament replay.py + optimieren.py wie gefordert: `replay.py --spur X
--lauf regime_studie --gebuehr 0.1` faehrt jede Spur mit ihrem HEUTIGEN
Stand ueber die volle Binance-Historie (2021-01 .. 2026-09, 1H, 3
Instrumente BTC/ETH/SOL-USDC). Aus dem Journal werden Einstieg/Ausstieg je
pos_id gepaart (Haus-Paarung gegenprobe: identische Rundenzahl 1964/1870/
752/857 und identische Mittelwerte). An jeden EINSTIEG-Zeitpunkt werden drei
Regime-Merkmale ohne Zukunfts-Blick gelegt:

  * Trendlage gegen den 200er: Schluss > SMA200 der 1H-Kerzen (eigenes Paar)
  * Volatilitaet: ATR14 / Schluss (eigenes Paar), geteilt am Median
  * Marktbreite: Anteil des Historien-Universums (29 Reihen mit >= 80 %
    Abdeckung) ueber seiner SMA200

Disziplin wie beim Gitter-Befund (15.09.2026): Suchfenster = erste 60 % der
Zeitachse, Prueffenster = letzten 40 %. Die Mediane (Vol, Breite) werden
NUR auf dem Suchfenster bestimmt und dann auf beide Fenster angewandt.
Ein Filter "haelt", wenn er in BEIDEN Fenstern mindestens 0,20 Prozentpunkte
Mittelwert-Differenz bei je mindestens 20 Runden je Seite trennt.

Werkzeug: `Agenten/Handel/regime_studie.py` (wiederverwendbar,
`REGIME_DATEN` zeigt auf einen Baum mit daten/), Zahlen in
`regime_studie.json`.

## Ergebnisse (Mittelwert netto je Runde in %, 2 x 0,1 % Gebuehr abgezogen)

squeeze (1964 Runden; gesamt -0,24 % Such / -0,23 % Pruef):

| Merkmal (gut = ...)      | Such gut      | Such schlecht | Pruef gut     | Pruef schlecht| haelt |
|--------------------------|---------------|---------------|---------------|---------------|-------|
| Trend > SMA200           | -0,33 (38 %)  | -0,35 (38 %)  | -0,23 (40 %)  | -0,23 (40 %)  | nein  |
| Vol >= Median            | -0,24 (39 %)  | -0,44 (37 %)  | -0,42 (37 %)  | -0,16 (41 %)  | nein  |
| Breite >= Median         | -0,38 (38 %)  | -0,30 (39 %)  | -0,11 (41 %)  | -0,33 (38 %)  | nein  |
| Trend UND Breite         | -0,33 (38 %)  | -0,35 (38 %)  | -0,16 (41 %)  | -0,28 (39 %)  | nein  |

wavetrend (1870 Runden; gesamt -0,23 % Such / +0,15 % Pruef):

| Merkmal (gut = ...)      | Such gut      | Such schlecht | Pruef gut     | Pruef schlecht| haelt |
|--------------------------|---------------|---------------|---------------|---------------|-------|
| Trend > SMA200           | -0,36 (32 %)  | -0,12 (34 %)  | +0,18 (36 %)  | +0,11 (35 %)  | nein  |
| Vol >= Median            | -0,35 (32 %)  | -0,15 (34 %)  | +0,30 (36 %)  | +0,10 (35 %)  | nein  |
| Breite >= Median         | -0,39 (32 %)  | -0,10 (34 %)  | +0,39 (37 %)  | -0,05 (34 %)  | nein  |
| Trend UND Breite         | -0,47 (32 %)  | -0,05 (34 %)  | +0,34 (37 %)  | +0,00 (35 %)  | nein  |

macd_mtf (752 Runden; gesamt -2,20 % in BEIDEN Fenstern):

| Merkmal (gut = ...)      | Such gut      | Such schlecht | Pruef gut     | Pruef schlecht| haelt |
|--------------------------|---------------|---------------|---------------|---------------|-------|
| Trend > SMA200           | -2,14 (20 %)  | -2,63 (18 %)  | -2,34 (19 %)  | -2,45 (18 %)  | nein  |
| Vol >= Median            | -1,51 (25 %)  | -3,27 (13 %)  | -0,44 (32 %)  | -3,47 (12 %)  | JA    |
| Breite >= Median         | -2,36 (19 %)  | -2,43 (19 %)  | -2,37 (19 %)  | -2,43 (19 %)  | nein  |
| Trend UND Breite         | -2,01 (21 %)  | -2,70 (17 %)  | -2,14 (20 %)  | -2,58 (17 %)  | JA    |

supertrend (857 Runden; gesamt +0,12 %):

| Merkmal (gut = ...)      | Such gut      | Such schlecht | Pruef gut     | Pruef schlecht| haelt |
|--------------------------|---------------|---------------|---------------|---------------|-------|
| Trend > SMA200           | -0,09 (35 %)  | -0,01 (33 %)  | +0,02 (39 %)  | -0,29 (32 %)  | nein  |
| Vol >= Median            | -0,77 (30 %)  | +0,67 (38 %)  | -0,81 (28 %)  | +0,09 (38 %)  | nein  |
| Breite >= Median         | -0,04 (34 %)  | -0,06 (34 %)  | -0,18 (37 %)  | -0,08 (34 %)  | nein  |
| Trend UND Breite         | +0,14 (36 %)  | -0,16 (33 %)  | +0,08 (40 %)  | -0,29 (33 %)  | JA    |

## Befund

Der Hebel liegt NICHT im Regime. Kein Regimefilter macht eine der vier
Spuren ueber Gebuehren positiv:

  1. 13 von 16 Kombinationen trennen nicht konsistent (Vorzeichen oder
     Groessenordnung wandern zwischen Such- und Prueffenster) — fuer
     squeeze gilt das fuer ALLE vier Merkmale trotz 1964 Runden; die
     Mittelwerte liegen je Fenster innerhalb 0,1 Prozentpunkte beieinander.
  2. DREI Kombinationen trennen konsistent, alle zeigen in dieselbe
     Richtung — aber die "gute" Seite bleibt negativ oder um Null:
       * macd_mtf bei hoher Volatilitaet: -1,51 % gegen -3,27 % (Such),
         -0,44 % gegen -3,47 % (Pruef). Der Filter haelbe den Verlust je
         Runde, aber BEIDE Seiten verlieren — eine Spur, die in keinem
         Regime ueber die 0,20 % Gebuehr kommt, wird durch den Filter
         nicht handelbar.
       * macd_mtf Trend+Breite: -2,01 gegen -2,70 / -2,14 gegen -2,58 —
         dieselbe Aussage, schwaecher.
       * supertrend Trend+Breite: +0,14 gegen -0,16 / +0,08 gegen -0,29 —
         die gute Seite ist nach Gebuehr nahe Null.
     Bei 16 Tests sind 1-3 konsistente Treffer die Erwartung des
     Multiple-Testing; die Richtung (hohe Volatilitaet = Trends = bessere
     Trendfolge) ist plausibel, aber ohne eigenes Prueffenster-Design nicht
     belastbar genug, um darauf zu bauen.
  3. Marktbreite ALLEIN trennt in keiner Spur; Trend gegen den 200er allein
     ebenfalls nicht. Der vielversprechendste einfache Indikator (Breite)
     traegt die Frage nicht.

Nebenbefund: wavetrends Vorzeichen folgt dem ZEITfenster (Such -0,23 %,
Pruef +0,15 %) ohne dass eines der drei Merkmale das ankuendigt — dieselbe
Klasse wie der adx_macd-Befund (T-349: "das Vorzeichen folgt dem Fenster,
nicht der Strategie").

## Konsequenz

KEIN Code an den vier Spuren geaendert (sie laufen unveraendert Papier,
handel_erlaubt=false). Kein Regimefilter wird eingebaut — "kein Filter
haelt" ist wie beim Gitter das vollwertige Ergebnis. macd_mtf bleibt
strukturell negativ (-2,2 % je Runde ueber 5,7 Jahre in JEDEM Fenster);
supertrend traegt nur den schmalen Gitter-artigen Rand (+0,12 % je Runde).

Naechster Schritt (Entscheidung Max): nichts — oder, falls die Spur-Liste
bereinigt wird, macd_mtf als Kandidat fuer Stilllegung notieren, weil auch
der beste Regimefilter den Verlust nur halbiert.
