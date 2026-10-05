# IV-Wand-Spur (Deribit)

Aus einem Reel von `atraintrades` ("Can't beat the IV Walls") gebaut, dann auf
echten Daten geprueft. Die Spur ist **Papier** (`handel_erlaubt: false`), hat
keinen Live-Zweig und ist **nicht** in `dauerlauf.SPUREN` eingetragen.

## Was im Video steckt (Beleg: die Textebenen, Bild fuer Bild)

Max' Clip ist 16 Sekunden und bricht mitten im Satz ab - die Textebenen des
Reels laufen in dieser Reihenfolge durch:

`QUANT` `HISTORICAL` `VOLATILITY` `PRICING` | `IV` `90%` `WE` `BECAUSE`
`REVERSALS` `THE` `STOPS` `BELOW` `REVERSAL` `CONSISTENTLY`

Darunter laufen zwei Charts: erst Kurvenscharen mit senkrechten Grenzlinien
(die Optionsbepreisung), dann Kerzen mit farbigen Zonen und roten Kreisen an
Hochs und Tiefs (die Waende und die Umkehrpunkte). Rundum auf Instagram
bestaetigt der Urheber den Kern woertlich: *"Using historical volatility plus
contract pricing, you can find our IV walls, which gives us our expected
range. In over 30 days we've only ..."* - und im Clip: `WE BECAUSE REVERSALS
THE STOPS BELOW REVERSAL CONSISTENTLY` (= "we place the stops below/beyond the
reversal, consistently").

Zusammengesetzt sind das **drei Bausteine**:

1. Historische Volatilitaet (HV) **plus** Optionsbepreisung (IV) ergeben eine
   **erwartete Tagesspanne**.
2. Strikes mit hohem offenem Interesse sind **Waende**; die Spanne sagt, welche
   Wand heute ueberhaupt erreichbar ist.
3. Gehandelt wird **gegen** die Bewegung an der Wand, **Stop knapp hinter die
   Wand** (dort liegt die Absicherung der Gegenseite), Ziel zurueck nach innen.

## Was auf 400 Handelstagen wirklich messbar ist

Daten: Deribit oeffentlich, BTC, Stundenkerzen + Tages-DVOL, 16.09.2026.
Kein Blick nach vorn: die Spanne fuer Tag D kommt aus dem DVOL-Schluss von
Tag D-1 und dem Tageroeffnungskurs. Gebuehr 0.05 % je Seite.

**A) Haelt die Spanne?** Anteil der Tage, die der Kurs vollstaendig in der
Spanne verbrachte (Klammer: nur der Schlusskurs):

- IV aus DVOL, k=1.000: 49,0 % (77,0 %)
- IV aus DVOL, k=1.645: **82,0 %** (92,8 %)
- HV aus 20 Tagen, k=1.645: 73,7 % (89,5 %)
- Mischung 50/50, k=1.645: 80,2 % (91,2 %)

Der Befund: Die IV-Spanne ist die **bessere** der beiden Quellen, aber sie ist
**nicht** die 90-%-Decke, die das Reel verspricht - rund jeder fuenfte Tag
bricht aus der 90-%-Spanne aus. Fuer den Schlusskurs stimmt die Erwartung
(92,8 %) fast genau, fuer die Tagesspitzen nicht. Genau das ist die
brauchbare Aussage: die Spanne taugt zum **Rechnen und Dosieren**, nicht als
Versprechen.

**B) Zahlt der Fade an der Spannengrenze?** Einstieg bei Beruehrung, Stop in
Sigma, Ziel als Anteil des Rueckwegs, je Tag und Seite hoechstens eine Runde,
Stop hat im selben Stundenbalken Vorrang (konservativ):

| Ziel | k | Stop 0.20 | 0.35 | 0.50 | 1.00 (je Runde, netto) |
|---|---|---|---|---|---|
| voller Rueckweg | 1.000 | -0.127 | -0.076 | -0.065 | -0.043 |
| halber Rueckweg | 1.000 | **+0.146** | **+0.235** | **+0.276** | **+0.359** |
| voller Rueckweg | 1.645 | +0.041 | +0.017 | +0.094 | -0.039 |
| halber Rueckweg | 1.645 | **+0.271** | **+0.314** | **+0.369** | **+0.287** |

Das ist der eigentliche Fund, und er widerspricht dem naiven Lesen des Videos:
**der volle Rueckweg zur Tagesmitte traegt nicht**, der **halbe** traegt - und
zwar in **allen acht** Feldern, mit glattem Verlauf zwischen Nachbarfeldern
(kein Zufallstreffer in einer einzelnen Einstellung).

Gegenprobe auf dem gewaehlten Feld (k=1.0, Stop 0.5 Sigma, Ziel 0.5):

- erste 200 Tage: n=104, Treffer 67,3 %, **+0,316 %** je Runde
- zweite 200 Tage: n=105, Treffer 65,7 %, **+0,235 %** je Runde
- Short-Seite: n=92, **+0,288 %** | Long-Seite: n=117, **+0,266 %**
- 204 von 400 Tagen loesen ueberhaupt aus

Beide Haelften und beide Seiten positiv, Stopquote 24-28 %.

## Was NICHT gemessen werden kann

Die **Waende selbst**. Das offene Interesse je Strike gibt es bei Deribit nur
als Momentaufnahme, keine Historie - in den Gueteproben oben steckt deshalb nur
die **Spanne**, nicht der Wand-Filter. Der Fade wurde an der Spannengrenze
getestet, nicht am Strike. Das ist die ehrliche Luecke: die Wand soll die
Runde auswaehlen, messbar ist bisher nur die Spanne. Aufloesen laesst sich das
nur vorwaerts (Papierbetrieb), nicht rueckwaerts.

Stand 16.09.2026, BTC 75.593, DVOL 39,06 %, HV20 26,59 %, gerechnet 32,83 %
(Tagessigma 1.299, 90-%-Spanne 73.456 bis 77.729): Call-Wand 80.000 (OI
22.419) = **3,39 Sigma** entfernt, Put-Wand 60.000 (OI 14.260) = **12,01
Sigma**. Beide liegen damit hinter der Grenze von 3 Sigma - an solchen Tagen
gibt es nach dieser Lehre **kein Geschaeft**, und das Werkzeug sagt das auch
(`kein_signal`). Genau dieser Filter folgt aus dem Video und war im Backtest
nicht messbar.

## 29.09.2026 - Zweiter Einstiegsweg: der Fade an der Spannengrenze

Max: *"journal fuer IV_waelle bauen, andere journale ueberpruefen - viele haben
0 runden, da stimmt doch etwas nicht."* Fuer diese Spur war die Ursache genau
das, was oben unter "Was NICHT gemessen werden kann" steht.

**Befund.** Die Spur machte seit dem 19.09.2026 (Eintrag in `dauerlauf.SPUREN`)
kein einziges Geschaeft - deshalb gab es kein Journal. Gemessen mit der eigenen
Sonde am 29.09.2026: BTC 83.107, Tagesbasis 84.470, Tagessigma 1.765. Call-Wand
90.000 = **3,13 Sigma**, Put-Wand 60.000 = **13,9 Sigma**. Das Tor verlangt eine
Wand im Band Grenze..3 Sigma UND hoechstens 0,5 % Abstand zum Kurs. OI-Waende
sitzen an runden Zahlen (80.000/90.000/100.000), die Tagesspanne ist wenige
Prozent breit - der geforderte Abstand ist ein Vielfaches des Moeglichen. Das
Tor geht also praktisch nie auf, und die Wandregel ist bis heute nicht messbar.

**Was gebaut wurde.** `iv_waelle.signal_an_der_spanne()`: Kurs >= obere Grenze
-> short, Kurs <= untere Grenze -> long, Stop 0,5 Sigma **hinter** die Grenze,
Ziel der halbe Rueckweg zur Tagesmitte. Das ist genau das Feld, das in Tabelle B
ueber 400 Tage gemessen ist (k=1,0 / Stop 0,5 Sigma / halber Rueckweg:
**+0,276 % je Runde**, 204 von 400 Tagen mit Signal, beide Haelften und beide
Seiten positiv). Der Wandweg bleibt **erster** Weg und hat Vorrang; der
Spannenweg greift nur, wenn er kein Signal liefert (`einstieg_an_der_spanne` in
`wachen.json`, abschaltbar).

Dazu der **Ausstieg am Tagesende** (`handeln.tagesende`): die Tagesspanne gehoert
zu einem UTC-Tag (sie kommt aus dessen Eroeffnungskurs), und im Backtest endet
jede Runde im selben Tag. Ohne diesen Ausstieg laeuft eine Position gegen eine
Spanne, die es nicht mehr gibt. Stop und Ziel bleiben vorrangig.

Jede Position traegt jetzt `ausloeser` (`wand` oder `spanne`) und das Journal
den Grund `iv_waelle:wand` bzw. `iv_waelle:spanne` - sonst waere ein Gewinn dem
falschen Weg zugeschrieben.

**Nachweis.** `tests/test_spanne_weg.py` (16 Tests, ohne Netz), darunter ein
**voller Papierzyklus in einen Temp-Ordner**: das Journal entsteht mit
Kopfzeile, bekommt die kauf-Zeile und im naechsten Zyklus die verkauf-Zeile mit
Grund `ziel` - also eine echte Runde, die `auswertung_alle` zaehlen kann.
Das echte Journal liegt als `handelsjournal.csv` mit Kopfzeile bereit; die erste
Zeile kommt mit dem ersten Geschaeft. Am 29.09. lag der Kurs mit 83.107 nur
**0,48 %** ueber der unteren Grenze (82.705) - der Ausloeser ist also nah.

## 05.10.2026 - T-122: zweites Instrument und ein Ziel, das nicht traegt

`spannenweg_zweites_instrument.py` misst den Spannenweg auf EINEM zweiten
Instrument (ETH) und vergleicht die beiden Ziele getrennt. Der Grund fuer
die Trennung: `backtest_iv_waelle.pruefe_fade()` rechnet den VOLLEN Rueckweg
zur Tagesmitte, die Zahl oben (+0,276 %) kam aber aus `ziel_anteil=0.5`, dem
HALBEN Rueckweg in `iv_waelle.signal()`. Zwei verschiedene Regeln an einem
Ort - das ist jetzt getrennt gemessen, statt die eine gegen die andere zu
stellen.

Daten: Deribit oeffentlich, 400 Tage, IV aus dem Vortages-DVOL, Gebuehr
0,05 % je Seite, keine OI-Historie.

| Instrument | HALBER Rueckweg (NOTIZ-Regel) | voller Rueckweg |
|---|---|---|
| BTC | n=206, Treffer 66,5 %, **+0,285 % je Runde** (Summe +58,8 %) | n=206, **-0,028 % je Runde** |
| ETH | n=191, Treffer 67,0 %, **+0,421 % je Runde** (Summe +80,4 %) | n=191, **+0,050 % je Runde** |

Zwei Befunde:

1. **Die BTC-Zahl der Notiz haelt** (+0,285 % gegen +0,276 %, Rundenzahl
   206) - die Gueteprobe stimmt. ETH liegt mit +0,421 % hoeher, beide
   Haelfften und beide Instrumente positiv (BTC +0,333 / +0,238 %,
   ETH +0,498 / +0,345 %). Punkt (b) aus T-122 ist damit beantwortet: der
   Spannenweg traegt nicht nur an BTC.
2. **Der volle Rueckweg traegt NICHT** (-0,028 % je Runde an BTC). Das ist
   kein Messfehler, sondern der Grund, warum die Spur `ziel_anteil=0.5`
   setzt: der Kurs laeuft nach dem Stop oft weiter bis zur Mitte und dreht
   dort. Wer den vollen Rueckweg nimmt, zahlt das. Diese Regel gehoert in
   jeden Aufruf, der die Spur rechnet - eine Zahl aus dem Backtest-Default
   waere hier eine falsche Zahl.

**Was bleibt ungemessen (unveraendert).** Der WANDWEG, nicht der Spannenweg:
Deribit liefert das offene Interesse je Strike nur als Momentaufnahme, es
gibt keine Historie. Damit kann niemand sagen, ob eine Wand damals ein
Signal war - rueckwaerts nicht rekonstruierbar, nur vorwaerts im Papierbetrieb.
Das ist kein offener Arbeitsauftrag mehr, sondern eine Grenze der Daten.
Im Code steht der Filter als Vorrang vor dem Spannenweg und wird im
Journal als `wand` sichtbar, sobald er greift.


**Offen geblieben.** Nur der Wandfilter (siehe oben), nicht der Spannenweg.
Der Wandfilter laeuft mit und wird im Journal als `wand` sichtbar, wenn er
einmal greift; Deribit-Finanzierung (Perpetual-Funding) fehlt weiter.

## Aufbau

- `daten.py` - Deribit oeffentlich (Index, DVOL, Kerzen, Optionskette), mit
  Zwischenspeicher unter `daten/`.
- `iv_waelle.py` - Spanne, Waende, Wandelage, Signal. Reine Standardbibliothek.
- `backtest_iv_waelle.py` - Gueteprobe A (Spanne) und B (Fade).
- `feinprobe_fade.py` - Raster ueber Grenze, Stop und Zielanteil.
- `tests/test_iv_waelle.py` - 28 Tests, ohne Netz.
- `wachen.json` - Grenzen; `handel_erlaubt` steht auf `false`.

Start aus diesem Ordner:

```
python backtest_iv_waelle.py
python feinprobe_fade.py
cd tests && python -m unittest test_iv_waelle
```

## Offen

1. **Waende im Papierbetrieb pruefen** - nur so wird der Filter gemessen. Dafuer
   braucht die Spur einen Zyklus wie die anderen (Zustand, Journal, Spiegelung
   nach `Q:\Handel_Journal\iv_waelle`).
2. **Gebuehr**: 0,10 % je Runde sind im Backtest drin, aber Deribits
   Kontraktgroesse und Finanzierung (Perpetual-Funding) fehlen. Der Backtest
   rechnet den Kursgewinn, nicht die Haltedauer.
3. **Zweite Waehrung erledigt** (05.10.2026, ETH +0,421 % je Runde -
   siehe oben). Offen bleibt: nur 400 Tage, also EIN Regime, und kein
   Walk-Forward.
4. Die **0,80-%-Runde** aus dem Krypto-Abo gilt hier nicht: Deribit ist eine
   andere Boerse. Ob Max dort ueberhaupt handeln will, ist seine Entscheidung.
 (keine OI-Historie
bei Deribit) - jetzt laeuft er wenigstens mit und wird im Journal als `wand`
sichtbar, wenn er einmal greift. Nur BTC, nur ein Regime; Deribit-Finanzierung
(Perpetual-Funding) fehlt weiter.

## Aufbau

- `daten.py` - Deribit oeffentlich (Index, DVOL, Kerzen, Optionskette), mit
  Zwischenspeicher unter `daten/`.
- `iv_waelle.py` - Spanne, Waende, Wandelage, Signal. Reine Standardbibliothek.
- `backtest_iv_waelle.py` - Gueteprobe A (Spanne) und B (Fade).
- `feinprobe_fade.py` - Raster ueber Grenze, Stop und Zielanteil.
- `tests/test_iv_waelle.py` - 28 Tests, ohne Netz.
- `wachen.json` - Grenzen; `handel_erlaubt` steht auf `false`.

Start aus diesem Ordner:

```
python backtest_iv_waelle.py
python feinprobe_fade.py
cd tests && python -m unittest test_iv_waelle
```

## Offen

1. **Waende im Papierbetrieb pruefen** - nur so wird der Filter gemessen. Dafuer
   braucht die Spur einen Zyklus wie die anderen (Zustand, Journal, Spiegelung
   nach `Q:\Handel_Journal\iv_waelle`).
2. **Gebuehr**: 0,10 % je Runde sind im Backtest drin, aber Deribits
   Kontraktgroesse und Finanzierung (Perpetual-Funding) fehlen. Der Backtest
   rechnet den Kursgewinn, nicht die Haltedauer.
3. **Zweite Waehrung erledigt** (05.10.2026, ETH +0,421 % je Runde -
   siehe oben). Offen bleibt: nur 400 Tage, also EIN Regime, und kein
   Walk-Forward.
4. Die **0,80-%-Runde** aus dem Krypto-Abo gilt hier nicht: Deribit ist eine
   andere Boerse. Ob Max dort ueberhaupt handeln will, ist seine Entscheidung.
