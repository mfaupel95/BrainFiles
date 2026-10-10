# Spuren historisch nachrechnen (Backtest-Fundament)

Werkzeuge: `Agenten/Handel/historie_binance.py` (Daten; hiess bis 29.09.2026
`historie.py`), `historie_okx.py` (OKX-Futures-Kerzen fuer Familie E),
`replay.py` (Walk, Familien A-E), `optimieren.py`
(Parametersuche), `historie_probe.py --okx` (Gegenprobe gegen eine zweite
Boerse), `moondev_historie.py` (Marktquerschnitt der Feed-Spuren), `auswertung_alle.py`
(Abschnitt "Backtest (historisch)"). Doku: `MaxHirn/Wiki/Handel/Backtest-Fundament.md`,
Spezifikation und Plan unter `Agenten/Handel/docs/{design,plans}/`.

## Warum es das gibt

Eine Spur liefert im Betrieb rund EINE Runde am Tag; `MIN_RUNDEN=8` und der
f_max-Merksatz machen daraus ein Jahr Wartezeit. Der Backtest holt dieselben
Runden aus historischen Kerzen (gemessen: 750 bis 1130 auswertbare Runden je
Indikator-Spur ueber 5,7 Jahre statt 8 bis 23 live).

**Der Backtest ist eine Messung, keine Live-Erfahrung.** Seine Runden zaehlen
NICHT fuer die Freigabe-Bedingungen aus `Wissen/Handelsregeln.md`; Ausgabe in
eigener Sektion (`auswertung_alle.py` -> `backtest_stand()`), nie zu Live-Runden
addiert.

## Ablauf

```bash
cd Agenten/Handel
python historie_binance.py --stand                    # was liegt an Daten
python historie_binance.py --auffuellen --instrumente BTC-USDC,ETH-USDC,SOL-USDC --takte 1H,4H,1D
python replay.py --spur squeeze --lauf ganz   # ganze Historie
python replay.py --spur squeeze --gegenprobe  # Kern gegen backtest_prognose.py
python optimieren.py --spur squeeze --trocken # Plan + Laufzeitschaetzung, rechnet nichts
```

Marktquerschnitt (Feed-Spuren, eigener Kerzenvorrat):

```bash
python moondev_historie.py --stunden 40 --takt 1H --faeden 6 --von 2021-01-01
python replay.py --spur moondev_topmovers --feed --lauf ganz
python replay.py --spur moondev_funding --familie-c --lauf ganz
python historie_probe.py --okx                # zweite Boerse als Gegenprobe
```

Datenquelle ist fuer die meisten Spuren Binance (offen, kein Schluessel, 1H ab
2017). Sie ist ein **Proxy** fuer die Boerse der Spur: jedes Ergebnis traegt
`kerzenquelle: binance` und wird nie als OKX- oder Krakenkurs ausgegeben.
Abrufrate gemessen ~1000 Kerzen/s (1000 je Seite, ~0,25 s Pause) - 20
Instrumente x (1H+4H) sind rund 21 Minuten, kein Nebenbei-Lauf. **Ausnahme
Familie E (xperp):** die laedt die Kerzen ueber `historie_okx.py` von der
OKX-Futures-API und traegt `kerzenquelle: okx`.

## Die wichtigste Regel: die Spur selbst fahren, nie nachbauen

Der Replay baut KEINE zweite Umsetzung. Er laedt das Spurenmodul ueber den PFAD
(`importlib.util.spec_from_file_location`, eindeutiger Modulname - ueber
`sys.path` gewaenne der zuletzt eingefuegte Ordner) und ruft die Funktionen der
Spur. Fuenf Familien, fuenf Anschluesse:

| Familie | Buch | Anschluss |
|---|---|---|
| **A** | im Modul (`lade_wachen`, `journal`, `pruefe_einstieg`, `pruefe_ausstiege`) | Datennaht setzen, `pruefe_*` je Schritt rufen |
| **B** | `spur_buch.zyklus(ordner, quelle, signal, modus, ereignis_name)` | eigene `quelle(w)` unterlegen, `zyklus` je Schritt rufen |
| **C** | eigenes `lauf(modus)` + eigener Datensatz (moondev_funding) | eigene Quelle unterlegen, `lauf` je Schritt rufen |
| **D** | Mehrzeitrahmen (mosaic) bzw. eigene Rechnung (gitter, `walk()`) | Kerzen + Uhr liefern, die Spur entscheidet und bucht |
| **E** | Signal in `bot.py` (xperp), Kerzen von OKX-Futures | `bot.py` ueber den Pfad laden, `zeige_lage/trend/grid` je Schritt rufen |

Die Familie erkennt der Replay am **SPURNAMEN** - kein Schalter, der vergessen
werden kann (Familie E zusaetzlich ueber `--familie-e`).

`spur_buch.zyklus` nimmt `quelle` und `signal` **als Argumente** - der sauberste
Anschluss, den das Haus hat. Buchpfade kommen aus `pfade(ordner)`, deshalb
verschiebt EIN anderer `ordner` das ganze Buch.

## Vier Dinge stilllegen, bevor der erste Schritt laeuft

Jedes aus einem konkreten Grund - alle vier im `finally` zurueckstellen:

1. **`ereignis.lauf`** - jeder Zyklus oeffnet eine Bus-Meldung. Ueber 50.000
   Schritte ist das eine Flut im Bus-Journal und Telegram-Nachrichten aus einem
   Backtest. Ersatz: Funktion, die `contextlib.nullcontext()` zurueckgibt.
2. **`spur_buch.spiegeln`** - Bedingung 4 kopiert nach `Q:`. Zusaetzlich
   `journal_zweitziel` in der Wachen-KOPIE auf den Backtest-Ordner biegen
   (Guertel und Hosentraeger).
3. **Die Risikostufe** (`HANDEL_RISIKO` aus der Umgebung nehmen) - sonst legt
   `risikostufe.datei()` `.mittel`-Dateien an.
4. **Die Uhr der Spur** (`<modul>.zeit_quelle` bzw. `spur_buch.zeit_quelle`) -
   siehe naechster Abschnitt.

Dazu: `SCHREIBEN=False` allein genuegt NICHT, es sichert nur `journal()`. Auch
`schreibe_zustand` und `spiegeln` muessen ins Leere laufen.

Importreihenfolge: `spur_buch` VOR `ereignis` importieren - `spur_buch` legt den
Bus-Ordner in `sys.path`, ein alphabetisch vorgezogenes `import ereignis` faellt
mit `ModuleNotFoundError` um, obwohl das Modul existiert.

## Die Kerzenuhr: sonst traegt das Journal die Wanduhr

Familie A hat **dieselbe** Naht wie Familie B (`zeit_quelle = None` +
`_jetzt()`), sie muss nur gesetzt werden. Wird sie nicht gesetzt, schreibt jede
Journalzeile die Uhrzeit des LAUFS - und jede Zeitrechnung darauf ist still
falsch (die Fensterteilung des Optimierers findet dann nichts und meldet
"0 Runden", was wie ein ehrliches "kein Hebel" aussieht).

Zusaetzlich schreibt der Replay zu jeder Zeile `_kerzen_ts` (Millisekunden der
Kerze). Die Auswertung benutzt diesen Stempel und faellt nur notfalls auf die
Spalte `zeit` zurueck.

## Fenster statt Praefix, und die Mindestzahl respektieren

Die Spur sieht je Schritt ein rollierendes Fenster, nicht alles bis hierher:

- **Treue:** im Betrieb fordert jede Spur eine feste `kerzen_anzahl` an, sie
  sieht nie die ganze Geschichte.
- **Laufzeit:** die Spuren rechnen ihre Indikatoren je Schritt ueber die ganze
  Reihe - ein wachsendes Praefix ist O(n^2). Gemessen ~0,011 s je Schritt; ein
  Praefix ueber 50.000 Kerzen waere ~16 Stunden, mit Fenster wenige Minuten.

Vorgabe ist `max(kerzen_anzahl, mindest_kerzen + 40)`. **Ein Fenster unter
`mindest_kerzen` laesst die Spur nie ein Signal bilden** und der Lauf meldet
"0 Runden" - das sieht wie ein Messergebnis aus, ist aber ein abgeschnittenes
Fenster (gemessen: eine Spur braucht fuer ihren Mehrzeitrahmen ~560 Basiskerzen).

Abschnitte fuer Such-/Prueffenster werden nach **KERZENINDIZES** geschnitten,
nicht nach Zeitstempeln: der Walk laeuft ueber die kuerzeste Reihe, ein Index
gilt fuer alle Instrumente. Ein Index, der versehentlich als Zeitstempel
uebergeben wird, ergibt ein still winziges Fenster.

## Das Journal muss die Zeilen DER SPUR enthalten

Selbst gebaute Zeilen sind wertlos: `kosten_wendepunkt.runden_aus_journal()`
paart Einstieg <-> Ausstieg **je Instrument** (Form B). Ein Journal mit nur
Ausstiegszeilen ergibt **0 Runden**. Richtig: die `journal()`-Aufrufe der Spur
abfangen (`modul.journal = lambda **f: gesammelt.append(dict(f, _kerzen_ts=ts))`)
und ihre eigenen Zeilen schreiben - `kauf` MIT `stop` und `ziel`, `verkauf` mit
Endpreis. Dann liest die Hausfunktion sie ohne Umweg.

## Kennzahlen: EINE Rechnung fuer beide Welten

`kosten_wendepunkt.wendepunkt()` liefert `runden, R, C, p, f_max, ev_ohne,
ergebnis_summe` - **kein `netto_pct_mittel`** (das stammt aus
`backtest_prognose.kennzahlen`). Wer es hier erwartet, stuerzt ab. Das
Vergleichsmass zwischen Kandidaten ist `ergebnis_summe / runden` **minus 2 x
Gebuehr je Seite** - also NETTO. Brutto bevorzugt die Einstellung mit den
meisten Runden statt der besten: ein engerer Stop erzeugt mehr, kleinere Runden
und damit mehr Gebuehren je Runde.

`f_max` ist der Gebuehrensatz, ab dem die Runde die Nulllinie trifft, und
unterstellt, dass jeder Gewinner sein Ziel und jeder Verlierer den Stop erreicht;
die tatsaechliche Verteilung liegt darunter. Deshalb brutto UND netto ausweisen.

Gebuehr je Spur aus ihrer `wachen.json` (`gebuehr_taker`), sonst der Satz der
Boerse der Spur (OKX Spot 0,10 %/Seite, OKX Perps 0,05 %, Kraken 0,60 %). Einen
pauschalen Ersatz gibt es nicht: fuer eine Perp-Spur waere eine 0,10-%-Annahme
der zwanzigfache Satz und jedes Nettoergebnis zu schlecht.

## Die stille Null ist der Normalfall - fuenf Gegenproben

Der charakteristische Fehler eines Backtests ist ein Ergebnis, das wie eine
Messung aussieht und keine ist. Vor jeder Zahl:

1. **Runden > 0?** Null Runden liegt meist am Fenster (unter `mindest_kerzen`)
   oder am Journal (nur Ausstiegszeilen, falscher Instrumentname).
2. **Zeiten plausibel?** Journalzeiten muessen Kerzenzeiten sein, nicht die
   Wanduhr des Laufs.
3. **Bewegung moeglich?** `abs(ausstieg/einstieg - 1)` muss zu Stop und Ziel
   passen (Stop 5 %, Ziel 10 % -> ueber 50 % ist unmoeglich und deutet auf Kerzen
des einen und Positionen des anderen Instruments).
4. **Gegenprobe gegen den alten Rechner.** Der neue Kern muss auf denselben
   Kerzen Runde fuer Runde dieselben Werte liefern wie das bestehende
   `backtest_prognose.py`. Weicht er ab, ist der neue Kern falsch, nicht der alte.
5. **Inventar vor/nach.** Dateiliste und Groessen des echten Spurenordners UND
der `Q:`-Spiegelung vor und nach einem Lauf vergleichen; der Backtest darf
   ausserhalb von `daten/backtest/` nichts anfassen.

## Parametersuche (Optimierer)

**Nur Schluessel tunen, die die Spur wirklich liest.** Erst messen, welche Namen
in `<spur>/handeln.py` als `w.get("...")` vorkommen und welche davon in der
`wachen.json` stehen. Ein geratener Name wirkt nicht, alle Kandidaten sind
identisch und die Suche meldet "kein Hebel". Deshalb prueft der Optimierer jeden
Suchschluessel gegen die `wachen.json` und **bricht mit Namensliste ab**, statt
still zu rechnen. Gemessen: die vier Indikator-Spuren lesen aus ihren Wachen nur
die Ausstiegs-Geometrie (`pflicht_stop_prozent_min`, `pflicht_stop_prozent_max`,
`ziel_r_vielfaches`, `max_offene_positionen`); ihre Indikatorschwellen stehen als
Konstanten im Code.

**Das Urteil lautet: besser als die HEUTIGE Einstellung, in JEDEM auswertbaren
Fenster, netto.** Der Vergleich eines Kandidaten gegen seine EIGENE Suchhaelfte
misst den Regimewechsel zwischen den Haelften, nicht den Vorteil des Parameters -
gemessen liess er 14 von 18 und in einem zweiten Lauf 18 von 18 Kandidaten
durch, war also kein Filter. Deshalb in dieser Reihenfolge:

1. **Grundlinie zuerst messen:** dieselbe Rechnung im selben Zeitraum mit den
   heutigen Wachen-Werten. Ohne diese Zahl ist "besser" bedeutungslos.
2. **Netto vergleichen** (siehe Kennzahlen) - brutto bevorzugt die Einstellung
   mit den meisten Runden.
3. **Jedes auswertbare Fenster muss gewonnen werden**, mindestens zwei. Bei vier
   Fenstern waere "erstes gegen letztes" willkuerlich: die Wahl des Paares
   entscheidet ueber den Ausgang. Alle Fenster gewonnen und im Mittel trotzdem
   negativ ist kein Hebel.
4. **Mindestvorsprung 0,10 % je Runde** - darunter ist der Unterschied nicht von
   Rauschen zu trennen.

- Mindestens 600 Kerzen je Fenster, sonst ist ein Fenster keine Stichprobe.
- Mindestens 30 Runden je Fenster, nicht 8. Bei ~0,5 % Vorsprung und ~5 %
  Streuung braucht es die Groessenordnung 100 Runden, um beides zu trennen; mit
  der Schwelle 8 kam jeder Kandidat durch. Ein Fenster unter der Schwelle zaehlt
  als "nicht auswertbar", nicht als gewonnen.
- **Die Periode gehoert in den Bericht.** Dieselbe Spur steht ueber 5,7 Jahre bei
  +0,08 % je Runde netto und im 12-Monats-Prueffenster bei -0,99 % - ein
  Vorzeichen aus EINEM Zeitraum ist keine Eigenschaft der Spur.
- **Tote Rasterfelder erkennen und melden.** Liefern zwei Werte eines Feldes
  Runde fuer Runde identische Zahlen, greift das Feld nie (gemessen:
  `pflicht_stop_prozent_max` 8 gegen 12, der ATR-Stop bleibt darunter). Ein
  solches Feld sieht wie ein Versuch aus und ist keiner - es fliegt aus dem
  Raster, und das Werkzeug meldet es selbst.
- Mehr Fenster kosten KEINE zusaetzliche Laufzeit: der Walk laeuft je Kandidat
  einmal, die Fensterzahl teilt nur die Journalzeilen auf. Die Grenze setzt die
  Rundenzahl je Fenster, nicht die Rechenzeit.
- Ein zu kurzer Zeitraum ist eine Rechnung, kein Fehler: 6 Monate im 4H-Takt
  sind 1092 Kerzen und reichen fuer 2 Fenster nicht. Der Zeitraum wird angehoben
  **und gemeldet** - still eine andere Zahl zu rechnen waere schlimmer.
- Die Suche schreibt NIE in eine `wachen.json`, sondern eine Vorschlagsdatei
  unter `daten/backtest/<spur>/optimierung.json`. Die Uebernahme entscheidet Max.

## Laufzeit und Start

Mehrminuetige Laeufe (voller Walk, Rastersuche) im **Hintergrund mit
Benachrichtigung** starten und mit `process_manage` pollen, nicht im Vordergrund
blockieren. Lange Testsuiten ebenso: ein `execute_code`-Aufruf hat eine feste
Zellgrenze, die einen laengeren inneren Aufruf kappt - lange Laeufe ueber das
Terminal-Werkzeug (eigene Frist) oder im Hintergrund fahren.

**Ein Lauf, dessen Ergebnis du erst nach der naechsten Sitzung brauchst, muss
das Sitzungsende ueberleben** (`persist_on_release=true`). Ohne das raeumt das
Ende der Sitzung den Prozess ab - und zwar **lautlos**: das Journal bleibt
mitten im Zeitraum stehen, es gibt keinen Traceback und nie eine
Abschlussmeldung. Der Abbruch ist von "rechnet noch" nicht zu unterscheiden,
und die Auswertung arbeitet auf einem halbfertigen Buch. Ein Zwei-Stunden-Lauf
ist ein Auftrag zum Abgeben, nicht zum Danebensitzen.

- **Tod am ZEITSTEMPEL erkennen, nie am Log-Inhalt.** Letzte Schreibzeit der
  Logdatei gegen die HOST-Uhr halten (`ls -l --time-style=+%H:%M:%S` gegen
  `git log -1 --format=%ci` bzw. windows-mcp `Get-Date`): eine Datei, die seit
  Stunden nicht gewachsen ist, gehoert zu keinem laufenden Prozess. Ein Log
  voller Fortschrittszeilen beweist nur, dass er einmal gerechnet hat.
- **Den halben Lauf vor dem Neustart aus dem Weg raeumen** (Ordner beiseite
  legen oder unter neuem `--lauf` fahren). Die Auswertung waehlt den Ordner mit
  den meisten Zeilen; Bruchstueck und Neulauf im selben Ordner sind keine
  saubere Messung. Gibt der Neustart keine Meldung, in einem ZWEITEN Aufruf
  nachzaehlen, ob der Prozess lebt und das Journal waechst.

## Marktquerschnitt statt Kerzenreihe (Feed-Spuren)

Nicht jede Spur entscheidet ueber EINE Reihe. Die Feed-Spuren (Top-Movers,
Marktbreite, 1h-Signalwelle, Funding) entscheiden ueber einen
**Marktquerschnitt**: wer hat in 24 h am meisten zugelegt, wie viele Coins
stehen ueberhaupt im Plus. Ihre `quelle(w)` holt das von einem Datenanbieter;
historisch wird derselbe Querschnitt aus Kerzen vieler Paare gebaut (eigener
Ordner, eigener Kerzenform — s. unten). Fuenf Regeln, sonst wird die Zahl falsch
statt leer:

1. **Den Rang JE ZEITPUNKT aus dem Volumen DIESES Zeitpunkts bilden, nie aus
   einer fest einmal gewaehlten Liste.** Eine feste Liste traegt den heutigen
   Markt in die Vergangenheit: das Universum von 2026 haette 2021 gehandelt.
   Gegenprobe: derselbe Tag muss einen anderen Ersten haben als sein Vormonat.
2. **`kurse` traegt ALLE geladenen Symbole, `daten` nur die Kandidaten.**
   `spur_buch.pruefe_ausstiege` arbeitet ueber `kurse` — fehlt dort ein Symbol
   (weil es aus den Top N gefallen ist), schliesst diese Position NIE und der
   Lauf meldet weniger Runden, als es gab. Das ist der gefaehrlichste Fehler
   dieses Zuschnitts, weil das Ergebnis plausibel aussieht.
3. **Das sechste Kerzenfeld ist das QUOTE-Volumen** (USD), nicht das
   Basisvolumen. Eine Schwelle wie "mindestens 20 Mio USD" ist mit
   Basisvolumen um den Faktor Kurs verfehlt — die Spur haette nie gehandelt.
   Feed-Kerzen deshalb in einem EIGENEN Ordner und Namensschema ablegen, sonst
   verwechselt sie jemand mit der gewoehnlichen Kerze.
4. **Der Adapter muss GENAU die Felder liefern, die die Entscheidung liest**
   (`name`, `aenderung_24h`, `volumen_24h`, `kurs` bzw. `breite` bzw.
   `aenderung_1h`). Ein Adapter mit erfundenen Feldnamen laesst die Spur still
   ohne Signal laufen und erzeugt eine Zahl, die wie ein Messwert aussieht.
   Gegenprobe, die nicht veraltet: den Quelltext der `quelle()` der Spur nach
   den Feldnamen durchsuchen (`inspect.getsource`) — wer die Spur umbaut, bekommt
   einen roten Test, statt eine stille Null.
5. **Der erste Tag einer Reihe hat keine Vortagesschliessung — er wird
   AUSGELASSEN, nicht geschaetzt.** Und: nur Ueberlebende sind ladbar (vor heute
   delistete Paare fehlen), was die Marktbreite nach oben verzerrt. Diesen Satz
   gehoert in jede Antwort, die eine Breitenzahl nennt.

**Eine Spur mit eigenem `lauf(modus)` ist eine eigene Familie (C).** Sie fuehrt
kein Kerzenbuch: sie liest ihren eigenen Datensatz, haelt ihren Zustand selbst
und schreibt ihr Journal selbst. Dann NICHT das Journal abfangen (`SCHREIBEN`
aus), sondern die DREI PFADE in den Backtest-Ordner biegen und die Nahten
setzen, die die Spur fuer ihre eigenen Tests schon benutzt (`funding_quelle`,
`zeit_quelle`); nur `spiegeln` laeuft ins Leere. So liest die Hausfunktion
`runden_aus_journal()` dieselbe Zeilenform wie im Betrieb, und es entsteht keine
zweite Journalform. Sie gehoert NICHT in die Familie der Kerzen-Walks — dort
fehlt ihr die Reihe und der Lauf meldet still null.

**Instrumentnamen statt Symbole beachten:** die Spuren sprechen die Namen ihres
Datenanbieters (`BTC`, nicht `BTCUSDT`). Fehlt eine Zuordnung, faellt die Spur
mit `KeyError` um — die Namensliste also VOR dem Datenholen pruefen und fehlende
Zuordnungen ergaenzen, statt sie im Lauf zu entdecken. Kurse fuer den
Zuschnitt kommen aus DERSELBEN Ablage wie der Rest (eine Quelle, ein Stand); ein
zweiter Datenweg fuer den Mark-Preis waere ein zweiter Stand.

## Der Kill-Schalter ist eine Sackgasse — `--setzen` hilft

Gemessen am 29.09.2026: der Funding-Lauf endete nach **sechs Tagen** mit
`kill_ausgeloest = true`, obwohl das Buch im Plus stand. Kein Einstellungsfehler,
sondern der Bauart nach eine Sackgasse:

`spur_buch.zyklus` kehrt bei gesetztem `kill` SOFORT zurueck und leert die
Positionen. Der Kill rechnet aber auf der **Kapitalkurve** (Ruecklauf vom
Hoechststand), und die erholt sich nur durch neue Trades — genau die sperrt der
Kill. **Ein einmal ausgeloester Kill geht in keinem `spur_buch`-Buch wieder auf**,
und betroffen ist jede Feed-Spur, nicht nur Funding. Im Betrieb faellt das nicht
auf, weil der Mensch den Deckel von Hand hebt (xperp 21.09.2026: 40 -> 100).

Fuer die Messung ueber den ganzen Zeitraum laeuft die Spur deshalb ein zweites
Mal mit erhoehtem Deckel — **in der Kopie der Wachen**, nie in der echten:

```bash
python replay.py --spur moondev_funding --familie-c --lauf ohnekill \
  --setzen kill_switch_gesamt_usd=1000000
```

`replay.buch_ordner(spur, lauf, setzen={...})` legt die Wachen-Kopie an und
schreibt hinein, was gesetzt wurde (`_backtest_gesetzt`); die echte
`<spur>/wachen.json` bleibt Byte fuer Byte gleich (Test `SetzenTest`, vergleicht
die Quelle vor/nach). Wer den Deckel in der echten Wachen hebt, greift in den
laufenden Betrieb ein — das ist ein anderer Vorgang und braucht Max' Entscheidung.

## Ausstiege am Kerzenschluss - behoben, und was das Verifizieren zutage brachte

Bis zum 30.09.2026 stieg der Replay zum SCHLUSS der Kerze aus, in der Stop oder
Ziel beruehrt wurde — nicht zum Stop- oder Zielkurs. Ein Laeufer ueberschiesst
sein Ziel dadurch (ADA stand mit Ziel +12 % im Buch und wurde mit +48 %
geschlossen). **Behoben** mit `replay.beruehrte_marke()`/`kurs_der_marke()`
(T-177): liegt die Marke in der Kerze, ist SIE der Ausstieg; liegen beide Marken
darin, gilt der STOP (der Zweifel wird nicht zu Gunsten des Backtests
aufgeloest). Der AUSLOESER bleibt der Kerzenschluss — so entscheiden die Spuren
live. Gegenprobe je Lauf: `replay.auf_der_marke(journal)`; ein Lauf von vorher
zeigt `0/1506`, danach `1506/1506`.

**Werkzeug zum Beziffern: `Agenten/Handel/kerzenschluss_bias.py`** (rein lesend,
je Austrittszeile, ohne Paarung): `zuviel Gewinn`/`zuviel Verlust` in
Prozentpunkten der Marke, `netto` als vorzeichenrichtige Summe, Spalte `Marke%`
(100 % heisst: der Lauf stammt von nach dem Fix). Gemessen an wavetrend ueber
5,7 Jahre: der alte Kurs lag auf der Verlustseite 938 Punkte schlechter und auf
der Gewinnseite 445 Punkte besser als die Marke — **netto war das Ergebnis um
~492 Punkte zu SCHLECHT gerechnet**. Die Verlustseite dominiert, weil ein Stop
im Docht weit unter dem Stop schliessen kann.

### Zwei Fallen beim Nachrechnen (beide fast als falscher Befund gemeldet)

1. **Die Richtung fehlte im Haus-Paarer.** `kosten_wendepunkt._paarung_form_b`
   rechnete `(preis/einstieg - 1)` OHNE die Seite: ein Short, der im Ziel
   schliesst, stand als VERLUST im Buch. Gemessen an wavetrend (55 % Shorts):
   Summe +679 ohne Vorzeichen gegen -513 mit Vorzeichen, Trefferquote 54 %
   gegen 33 % — und das betraf jede gemischt handelnde Spur (squeeze, macd_mtf,
   supertrend, wavetrend haben rund 50 % Shorts je Buch). Behoben am 30.09.2026
   (`seite` aus der Einstiegszeile, `vorz = -1` bei short; fehlende Seite gilt
   als long und wird als `ohne_seite` ausgewiesen). Test:
   `tests/test_kosten_wendepunkt.RichtungTest`.
2. **Eine einseitige Summe ist keine Nettozahl.** Die erste Fassung von
   `kerzenschluss_bias.py` zaehlte nur die Ausstiege JENSEITS der Marke und
   liess die auf der guten Seite weg; die Summe war damit einseitig und ergab
   +493 statt -48. Vorzeichenrichtig rechnen: fuer einen Long ist ein hoeherer
   Ausstieg IMMER besser (egal ob Stop oder Ziel), fuer einen Short immer
   schlechter — EIN Vorzeichen je Richtung, nicht je Marke.

Nachweis vor dem Bericht: die drei Wege muessen dasselbe sagen — die
Zeilenrechnung (`kerzenschluss_bias`), eine Schluessel-Paarung ueber
`(inst, stop, ziel)` und `kosten_wendepunkt.paarung` auf denselben zwei
Journalen. Vor dem Fix taten sie das nicht, und genau das war der Hinweis auf
Falle 1.

## Gegenprobe gegen eine ZWEITE Boerse (nicht gegen die Uhr)

`historie_probe.py --okx` holt die Schlusskurse der groessten 50 Paare von OKX
(oeffentlich, kein Schluessel) nach `daten/historie/okx_probe.json`;
`GegenprobeBoerseTest` haelt sie gegen die eigene Tafel. Ergebnis: 50 Paare,
alle innerhalb 5 %. Zwei Fehlversuche auf dem Weg — beide Fehler des VERGLEICHS,
nicht der Daten, und beide haetten fast eine falsche Aussage ergeben:

1. **Binance-Tageskerze gegen OKX-Ticker "jetzt":** vier Symbole lagen 10-11 %
   auseinander (CELO/BERA/ONE/HBAR). Die Kerze war der Stand des Abrufs am
   MORGEN, der Ticker der Stand am ABEND — der Vergleich prueft die Uhr.
2. **Binance-1D gegen OKX-1D:** 0 von 50 trafen sich. OKX' Tageskerze beginnt um
   00:00 **UTC+8**, Binances um 00:00 UTC; dieselbe Zahl "1D" bedeutet dort eine
   andere Tagesgrenze.

Richtig ist der Vergleich desselben ZEITPUNKTS: der Schluss der letzten
**abgeschlossenen** Binance-Tageskerze gegen die OKX-STUNDENkerze, die auf
dieser Grenze endet (`ts + 24 h`). Die laufende Tageskerze ist ausgenommen — ihr
"Schluss" ist der Stand des Abrufs.

CoinGecko, die Quelle der Spuren im Betrieb, antwortet von diesem Rechner HTTP
403. Ein Test, der daran haengt, meldet SKIP **mit Grund** statt still zu
bestehen. `daten/` ist komplett ungetrackt (132 MB), der Abzug also nicht
versioniert — auf einem frischen Klon ist der Test deshalb ehrlich SKIP.

## Die Schrittzahl haengt an `--mindest-symbole`

Ab wie vielen Reihen ein Zeitpunkt als Schritt zaehlt, entscheidet die
Schrittzahl: die 1h-Signalwelle liefert mit der Vorgabe 30 genau 21.628
Schritte, mit 20 genau 50.337 — **und in beiden Laeufen dieselben 62 Runden**.
Wer zwei Laeufe vergleicht, muss diese Zahl mitlesen; sonst sieht der
Unterschied wie ein Datenfehler aus.

## Der Einstiegsgrund im Journal ist ein Platzhalter

Jede Einstiegszeile der `spur_buch`-Spuren traegt als `grund` den Satz
"Der Grund, der im Journal steht." — auch in den ECHTEN Journalen (gemessen
15.09.2026). Der Ausstiegsgrund (`ziel`/`stop`) ist echt; der Einstiegsgrund
sagt nichts. Beim Auswerten nicht hineininterpretieren.

## Zwei Sitzungen, eine Datei: Namenskollision

Zwei Sitzungen bauten am selben Tag je eine Pruefklasse `GegenprobeTest` in
DERSELBEN Testdatei. Die spaetere Definition verdeckt die fruehere **still** —
eine der beiden Pruefungen lief nie, und die Suite war trotzdem gruen. Vor dem
Zusammenfuehren zweier Sitzungen in einer Datei nach doppelten Definitionen
suchen (`search_files` nach `^class ` und die Namen vergleichen) und jeder
Pruefung ihren eigenen Namen geben. Gilt genauso fuer Funktionsnamen.

## Die Fahrbarkeits-Landkarte: eine Liste ist kein Weg

Bevor irgendein Lauf gestartet wird, muss jede Spur in GENAU EINER von zwei
Listen stehen - fahrbar oder mit Grund vermerkt. Ein dritter Zustand existiert
nicht und ist der gefaehrlichste: eine Spur in keiner der beiden Listen sieht
wie eine fahrbare aus und scheitert erst beim Lauf.

Die Landkarte programmatisch vergleichen, nie die Dateien lesen - die Listen
liegen als Konstanten vor und laufen sonst auseinander:

```python
import dauerlauf, replay, auswertung_alle as aa
fahrbar = (set(replay.SPUREN_TEIL_A) | set(replay.SPUREN_TEIL_B)
           | set(replay.SPUREN_TEIL_C) | set(replay.SPUREN_TEIL_E)
           | set(replay.MEHRZEITRAHMEN) | set(replay.EIGENE_RECHNUNG))
luecke = [s for s in dauerlauf.SPUREN
          if s not in fahrbar and s not in replay.NICHT_NACHRECHENBAR]
fehlt_auswertung = [s for s in dauerlauf.SPUREN if s not in set(aa.SPUREN)]
```

Jede Luecke ist ein Befund: entweder fehlt der Fahrweg oder der Grund. Dieselbe
Rechnung gegen `auswertung_alle.SPUREN` findet die zweite Haelfte - eine Spur,
die laeuft, aber in keiner Auswertung auftaucht, hat ein Buch und keine Zahl.

Drei Fallen, jede gemessen:

1. **Eine Fahrweise in der Tabelle ohne Route aus `main()` ist toter Code.**
   `SPUREN_TEIL_B` listet die spur_buch-Spuren, `lauf_b()` ist gebaut und
   getestet - und `main()` ruft es NIE auf. Der Aufruf faellt in den generischen
   Kerzen-Weg (Familie A) und meldet dort "die Spur nennt kein Instrument".
   **Die Zahl der gelisteten Spuren sagt nichts ueber die Zahl der fahrbaren.**
   Diagnose in einem Griff: nach dem AUFRUFER des Wegs suchen
   (`search_files` auf `lauf_b\(`), nicht nach seiner Definition.
2. **Eine Verweigerungsliste, die nur EINEN Eingang bewacht, gibt auf den
   anderen den falschen Grund.** `NICHT_NACHRECHENBAR` wird in `lauf_b`,
   `lauf_feed` und `lauf_c` geprueft - nicht in `lauf_a`. Eine dort vermerkte
   Kern-Spur (xperp, scanner, swap, kraken) laeuft deshalb in die generische
   Meldung "kein Instrument" statt in den ehrlichen Satz "keine Kerzen-Naht".
   Beide Saetze verweigern, aber nur einer nennt die Ursache - und der Leser
   folgt dem falschen Hinweis, sucht ein Instrument, das nie das Problem war.
   **Der Grund gehoert an den Eingang, den der Aufruf wirklich nimmt.**
3. **Ein Vermerk ohne Satz daneben ist nur ein Name.** Ein Eintrag in
   `NICHT_NACHRECHENBAR` ohne Grund ist von einer vergessenen Spur nicht zu
   unterscheiden - der Grund ist der halbe Wert des Eintrags.

**Der stehende Auftrag dahinter: jede Spur muss auswertbar und nachverfolgbar
sein, und das regelmaessig.** Eine Spur ohne Fahrweg und ohne Grund ist deshalb
kein Randfall, sondern eine offene Aufgabe. Ist eine Spur heute nicht
nachrechenbar, gehoert der GRUND in die Liste UND der Punkt in
`MaxHirn/Archiv/TASKS.md` - nicht die stille Luecke. Und wer eine Luecke
schliesst, prueft danach die Landkarte erneut: die gefundene Luecke war meist
nicht die einzige.

## Nicht nachrechenbar (mit Grund vermerken, nie schaetzen)

Die Datenquelle entscheidet, nicht die Naht. Ohne frei abrufbare Historie bleibt
die Spur ohne Backtest und bekommt einen GRUND im Bericht:

- Open-Interest-Historie (Options- und Perp-OI) und Liquidationshistorie sind
frei nicht abrufbar.
- Nachrichtenschlagzeilen von damals sind nicht archiviert (Sprachmodell-Spuren
  mit Schlagzeilen-Eingang).
- Onchain-/Wallet-Historie fremder Sammlungen reicht nur wenige Tage zurueck.
- Einstiege an Quote-Ticks gibt es nur live.
- Spuren ohne Kerzen-Naht (die Kern-Spuren mit Kontostand und Ranglisten) -
  eigener Umbau, eigenes Teilprojekt. **Ausnahme: xperp hat seit dem 07.10.2026
  mit Familie E einen eigenen Weg** (OKX-Futures-Kerzen + `bot.py`); die
  uebrigen Kern-Spuren (scanner, swap, kraken) weiterhin nicht.
- Aktien/Rohstoffe: nur Tageskerzen, also nur auf Tagesbasis nachrechenbar.

## Familie E: xperp (bot.py + OKX-Futures, 06./07.10.2026)

xperp war bis dahin nicht nachrechenbar (keine Kerzen-Naht, T-091). Seit dem
07.10.2026 faehrt es als Familie E: Kerzen von der OKX-Futures-API
(`historie_okx.py`), Signal aus `xperp/bot.py`. Die Spur entscheidet, der
Replay liefert Zeit und Daten.

```bash
cd Agenten/Handel
python historie_okx.py --auffuellen --instrumente RE,BTC --takte 1H,4H   # Kerzen + _instrumente.json
python replay.py --spur xperp --lauf test --max-kerzen 320               # bot-methode trend (Vorgabe)
python replay.py --spur xperp --lauf lage  --bot-methode lage  --max-kerzen 320
python replay.py --spur xperp --lauf grid  --bot-methode grid  --max-kerzen 320
```

- **`--bot-methode {lage,trend,grid}`** (Vorgabe `trend`, der Live-Pfad):
  `lage` rechnet nur das Signal und erzeugt KEINE Order (0 Runden sind dort
  ein gueltiges Ergebnis); `trend` legt EINE Order mit Limit/Stop/Ziel aus den
  Wachen-Faktoren; `grid` eine Leiter von Long-Stufen mit gemeinsamem
  Boden-Stop. Die Wahl steht im Ergebnis (`bot_methode`).
- **Anforderungen:** `historie_okx.py --auffuellen` (XPERP-Kontrakte laufen
  erst seit Mai 2026 - Datengrenze, kein Fehler), die Kontrakt-Metadaten
  `_instrumente.json` (ctVal/lotSz/tickSz, sonst KeyError statt Attrappen),
  `bot.py` ueber den Pfad (`replay._bot_modul`, xperp nur waehrend des Ladens
  auf `sys.path`), Instrumente aus den `familien` der wachen.json (kein
  `instrumente`-Feld), `mindest_kerzen` faellt auf 300 zurueck.
- **OKX-Unterschiede:** instIds tragen ein Ablaufdatum, Kerzen liegen unter
  dem VOLLEN instId; `bot.py` rechnet auf 4H (`bot.BAR`); der Hebel-Deckel
  bekommt Tageskerzen aus derselben 4H-Reihe verdichtet; der 24h-Umsatz ist
  aus den Kerzen geschaetzt; **CVD faellt aus** (keine Taker-Historie).
- **Zwei dokumentierte Grenzen (T-096):** Funding ist nicht in den Kerzen
  (`funding() -> None`, live zahlt eine XPERP-Position alle 8 h) und der
  Kill-Switch wird nicht abgebildet (wie in allen Familien).
- **Ausstiegslogik:** Fill am Limit (eine Order wird erst gebucht, wenn eine
  Kerze das Limit beruehrt; nach `order_gueltig_kerzen`, Vorgabe 24 = 4 Tage
  bei 4H, verfaellt sie), Ausstiege ueber Stop/Ziel an der Kerze (dieselbe
  Beruehrungsregel T-177 wie in allen Familien), ein Anlauf je Instrument.

Tests: `tests/test_replay_familie_e.py` (Mechanik mit Bot-Stub + echte
`bot.py` unter dem okxf-Ersatz, kein Netz) und `tests/test_historie_okx.py`.
Der Leitstand bietet xperp seit dem 07.10.2026 in der Replay-Liste an.

## Bericht

Je Spur eine Zeile mit Runden, Trefferquote, Ergebnis je Runde und Zeitraum -
und IMMER der Grund, wenn keine Zahlen da sind ("kein Lauf" und "nicht
nachrechenbar" sind verschiedene Dinge, ein leeres Feld ist von einem Messwert
nicht zu unterscheiden). Bei mehreren Laeufen gewinnt der mit den MEISTEN
Zeilen, nicht der neueste: die Parametersuche schreibt viele kurze Fensterlaeufe,
deren Zahlen neben einem Lauf ueber die ganze Historie irrefuehrend klein sind.
Der abgedeckte Zeitraum kommt aus den Kerzenstempeln; fehlen sie (alte Laeufe),
das sagen statt die Wanduhr als Zeitraum auszugeben.

**Die Regel hat eine Folge, die man kennen muss: ein ABGELOESTER Lauf gewinnt weiter.**
Wird ein Zeitraum nach einem Fix neu gefahren, laesst die Anzeige den alten,
laengeren Ordner stehen — die neue Zahl ist gerechnet und trotzdem unsichtbar.
Gemessen: ein Lauf vor der Kerzenuhr hatte 2180 Zeilen, der datierte Neulauf 591;
ueber Wochen stand deshalb "759 Runden ... Zeitraum unbekannt" in der Ausgabe,
waehrend 26 datierte Laeufe daneben lagen. Diagnose in EINEM Blick: die Kopfzeile
der Journale lesen — traegt sie `_kerzen_ts`, ist der Lauf datiert; fehlt die
Spalte, ist er von vor der Kerzenuhr. Konsequenz beim Neufahren: den alten Ordner
NICHT ueberschreiben, sondern beiseite legen (`mv <lauf> <lauf>.voruhr-<JJJJMMTT>`),
dann neu fahren. Das erhaelt den alten Beleg und macht den neuen sichtbar.
Eine Backtest-Zeile OHNE Zeitraum ist keine Messung, sondern eine Zahl mit
fehlendem Beleg — sie so lesen und den Neulauf veranlassen, statt sie zu zitieren.
