# Spuren historisch nachrechnen (Backtest-Fundament)

Werkzeuge: `Agenten/Handel/historie.py` (Daten), `replay.py` (Walk),
`optimieren.py` (Parametersuche). Doku: `MaxHirn/Wiki/Handel/Backtest-Fundament.md`,
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
python historie.py --stand                    # was liegt an Daten
python historie.py --auffuellen --instrumente BTC-USDC,ETH-USDC,SOL-USDC --takte 1H,4H,1D
python replay.py --spur squeeze --lauf ganz   # ganze Historie
python replay.py --spur squeeze --gegenprobe  # Kern gegen backtest_prognose.py
python optimieren.py --spur squeeze --trocken # Plan + Laufzeitschaetzung, rechnet nichts
```

Datenquelle ist Binance (offen, kein Schluessel, 1H ab 2017). Sie ist ein
**Proxy** fuer die Boerse der Spur: jedes Ergebnis traegt `kerzenquelle: binance`
und wird nie als OKX- oder Krakenkurs ausgegeben. Abrufrate gemessen ~1000
Kerzen/s (1000 je Seite, ~0,25 s Pause) - 20 Instrumente x (1H+4H) sind rund
21 Minuten, kein Nebenbei-Lauf.

## Die wichtigste Regel: die Spur selbst fahren, nie nachbauen

Der Replay baut KEINE zweite Umsetzung. Er laedt das Spurenmodul ueber den PFAD
(`importlib.util.spec_from_file_location`, eindeutiger Modulname - ueber
`sys.path` gewaenne der zuletzt eingefuegte Ordner) und ruft die Funktionen der
Spur. Zwei Familien, zwei Anschluesse:

| Familie | Buch | Anschluss |
|---|---|---|
| **A** | im Modul (`lade_wachen`, `journal`, `pruefe_einstieg`, `pruefe_ausstiege`) | Datennaht setzen, `pruefe_*` je Schritt rufen |
| **B** | `spur_buch.zyklus(ordner, quelle, signal, modus, ereignis_name)` | eigene `quelle(w)` unterlegen, `zyklus` je Schritt rufen |

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
  eigener Umbau, eigenes Teilprojekt.
- Aktien/Rohstoffe: nur Tageskerzen, also nur auf Tagesbasis nachrechenbar.

## Bericht

Je Spur eine Zeile mit Runden, Trefferquote, Ergebnis je Runde und Zeitraum -
und IMMER der Grund, wenn keine Zahlen da sind ("kein Lauf" und "nicht
nachrechenbar" sind verschiedene Dinge, ein leeres Feld ist von einem Messwert
nicht zu unterscheiden). Bei mehreren Laeufen gewinnt der mit den MEISTEN
Zeilen, nicht der neueste: die Parametersuche schreibt viele kurze Fensterlaeufe,
deren Zahlen neben einem Lauf ueber die ganze Historie irrefuehrend klein sind.
Der abgedeckte Zeitraum kommt aus den Kerzenstempeln; fehlen sie (alte Laeufe),
das sagen statt die Wanduhr als Zeitraum auszugeben.
