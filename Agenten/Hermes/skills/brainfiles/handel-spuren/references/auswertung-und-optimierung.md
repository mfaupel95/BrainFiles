# Auswerten und optimieren: von den Journalen zur EINEN belegten Aenderung

## Wann
Auftrag „werte die vorhandenen Daten aus", „optimiere die Strategien", oder wenn
die Frage ansteht, ob eine Spur die Freigabe (Bedingung 1: 50 Runden, netto
positiv nach Gebuehren und Funding) traegt.

## Grundsatz
Aus 3-20 Runden laesst sich kein Parameter begruenden. Der Weg ist nicht „Zahlen
ansehen und drehen", sondern eine Reihenfolge, die am Ende ENTWEDER eine
Aenderung mit Zahlen UND Gegenprobe ergibt ODER den Satz, dass es fuer eine
Schwelle nicht reicht. **Eine Aenderung je Durchgang** - mehrere gleichzeitig,
und keine ist mehr zurechenbar.

## Schritt 1 - Runden zaehlen, bevor gerechnet wird
- `Agenten/Handel/auswertung_alle.py` (aus dem Handel-Ordner, venv-Python):
  xperp, swap, scanner, kraken, orbk, gitter, nautilus. Paart Einstieg/Ausstieg
  je Instrument, `MIN_RUNDEN = 8`, Kosten aus der Zeile.
- `<spur>/auswertung.py` fuer spiegel, omniquant, gitter; die gemeinsame
  Mechanik steht in `Handel/buchauswertung.py` (`MIN_AUSSTIEGE = 8`).
- Lage am 14.09.2026 als Maßstab dafuer, wie duenn das Material ist: xperp 20,
  scanner 14, orbk 15, spiegel 107, swap 3, kraken 9, omniquant 0, gitter 0,
  nautilus 0 (bauartbedingt: Quote-Sammler ohne Orderpfad).

## Schritt 2 - Attribution: sind die Runden echt?
Datum und Grund jeder Runde gegen die eigene Sitzung halten. kraken sah nach
„8 von 9 Herzschlag-Ausstiegen" aus; tatsaechlich stammten 4 vom Testlauf
12.09. und 4 vom Verifikationslauf 14.09. (16:44) - das Buch war fast leer.
Ein Buch aus eigenen Testrunden ist kein Maß, sondern ein Arbeitsunfall.

## Schritt 3 - Kosten aus der ZEILE, nie aus dem Gefuehl
Je Spur ein anderes Feld:
- xperp, swap: `margin_usd` (Einsatz/Erloes), Kosten aus `nominal_usd` x
  `gebuehr_pct` beider Seiten + Funding.
- scanner: `usd` aus Kauf- und Verkaufszeile; GEBUEHR_PCT 0,0005 je Seite,
  im Journal schon eingerechnet.
- kraken: `eur`; Gebuehr aus `wachen.json` (seit 14.09.2026 0 %, Abo).
- spiegel: `einsatz_usd` / `wert_usd`, slippage_pct 3,0 + gebuehr_pct 1,0 je Seite.
- orbk: `gv_usd` fertig; omniquant: `einsatz_usd` / `wert_usd`.
Einen Kostensatz zu senken, damit die Zahlen besser aussehen, ist das Gegenteil
von Messen (`references/tor-kalibrierung.md`).

## Schritt 4 - Geometrie-Gegenprobe (die tragende Zahl)
Break-even-Trefferquote = Stop / (Stop + Ziel). Liegt die gemessene Quote
deutlich darueber, ist die Geometrie in Ordnung - ein Parameterwechsel waere
geraten. Gemessen am 14.09.2026:
- xperp/swap: Stop 1,5 ATR, Ziel 3,0 ATR -> 33 % noetig, **55 %** gemessen
- scanner: Stop 5-12 %, Ziel >= 1,5 R -> <= 40 % noetig, **64 %** gemessen
- orbk: `ziel_k` 1,5 -> 40 % noetig, **53 %** gemessen
- spiegel: Stop 25 %, Ziel 60 % -> 29 % noetig, **39 %** gemessen

## Schritt 5 - Zwangsschluesse abtrennen, bevor gerechnet wird
Die wichtigste Verteilung ist nicht die Hoehe der Gewinne, sondern **wer die
Runde beendet hat**. `Handel/stoerungen.py` ist dafuer das Werkzeug:
- `python stoerungen.py` - Uebersicht je Spur (Zeilen, Ausstiege, echt,
  Stoerung, Marke „Kennzahl unbrauchbar" wenn Stoerungen >= echte Runden).
- `python stoerungen.py --liste` - die Stoerungen chronologisch, mit Haeufung
  nach Tag und Spur. **Die Haeufung IST die Fehlersuche:** 21 Stoerungen, alle
  in einem Vorfallsfenster, sieben an einem Tag = eine Stoerungskette, kein
  Dauerzustand. Ausserhalb des Fensters kein einziger.
- `ist_stoerung(grund)` ist die EINE Definition (Merkmale `herzschlag`,
  `zwangsschluss`, `notaus`); `auswertung_alle.kennzahlen` benutzt sie.
- Gemessen 15.09.2026: xperp 23 Ausstiege -> 11 echte Runden, kraken 10 -> 2,
  swap 5 -> 4, Summe 296 echt / 21 Stoerung.
- **Die Trennung wirkt an DREI Stellen, alle drei noetig:** die Uebersicht
  (`stoerungen.py`), die Auswertung (`auswertung_alle.kennzahlen`) UND die
  Wachenfassungen. `scanner/wachen_pruefung.py`, `xperp/wachen_xperp.py`,
  `kraken/wachen_kraken.py`, `orbk/wachen_orb.py` liefern in `lage()`
  `runden_echt`, `runden_stoerung`, `runden_papier_echt` und
  `rollierender_ev_echt`; `handeln.py --wachen` und der Tagesbericht zeigen
  Handelsrunden UND die Stoerungen. Ohne diesen dritten Ort zaehlt genau die
  Zahl weiter Stoerungen mit, gegen die die Freigabebedingung (50 Runden)
  geprueft wird - das Werkzeug allein aendert daran nichts.
- **Die Kapitalkurve bleibt UNGEFILTERT** (`drawdown(runden)`, Halbierung,
  Kill-Switch): eine Stoerung ist gebucht und hat Geld bewegt. Wer sie aus der
  Kurve nimmt, schoenet das Risiko, gegen das die Sicherung gebaut ist. Nur
  Kennzahlen (Rundenzahl, Trefferquote, Erwartungswert) rechnen auf den echten
  Runden. Bedingung 5 (`ev_negativ` -> Sperre zu) lief am 15.09.2026
  unveraendert auf allen Runden; der EV der echten Runden steht daneben - die
  Umstellung der AUTOMATIK ist eine Entscheidung von Max, sie kann in beide
  Richtungen wirken (kraken: Sperre zu, xperp: Sperre auf).
- **Eine Zahl im Quelltext ist eine Behauptung, die nachgemessen gehoert.** Die
  Beispielzahlen im Kopf von `stoerungen.py` ("-0,74 gegen +38,14 USD") trugen
  die Messung nicht; nachgerechnet ueber `sum(r["gv"])` je Gruppe: xperp echte
  Runden +39,50 gegen Stoerungen +4,73 (je Runde +3,59 gegen +1,92), kraken
  +4,59 gegen -4,50 EUR. Vor jeder Uebernahme fremd geschriebener Zahlen in
  Notiz oder Ausgabe selbst nachrechnen.
- **Die Richtung der Verzerrung ist nicht vorhersagbar - deshalb beides zeigen.**
  Bei kraken waren die Zwangsschluesse +4,59 EUR POSITIV und die zwei echten
  Runden -4,50 EUR negativ (geschoent); bei xperp umgekehrt (-0,74 gegen
  +38,14 USD, getruebt). Wer die Stoerungen stillschweigend weglaesst, baut eine
  Bilanz, die von der Vorfallshistorie abhaengt; wer sie mitzaehlt, misst
  Stoerungen statt Strategie.
- Vorher/nachher gegen die alte Zahl halten und beides nennen: 12 von 20 Ausstiegen
  als `herzschlag_alt` hiess nicht 20 Runden, sondern 8 - und die Trefferquote
  der echten war eine andere als die der gemischten.

## Parameter optimieren: suchen, dann pruefen (nie bis es passt)
Gilt fuer jede Parameter-Optimierung (Gitter `spanne_prozent`/`stufen`, Tore,
Schwellen). Reihenfolge:
1. **Die ECHTE Logik fahren, nicht eine Nachbildung.** Das Werkzeug laedt das
   Spurmodul ueber `spec_from_file_location` und ruft dessen eigene Funktionen
   (bei gitter: `leiter_bauen()`, `arme()`, `walk()`), mit derselben
   Zustandsstruktur, die die Testsuite vorlegt (`gitter/tests/test_gitter.py`).
   Ein Filter wird auf das Modulglobal gehaengt, das der Walk ohnehin aufruft
   (`h.arme`) - also genau an der Stelle, an der die echte Spur ihre Stufen
   belegt. Eine zweite Umsetzung daneben misst die Nachbildung.
   Werkzeuge: `gitter/backtest_gitter.py`, `suche_gitter.py`,
   `regime_gitter.py`, `filter_gitter.py`, `optimieren_gitter.py`.
2. **Zwei Fenster ohne Ueberlappung.** Auf dem Suchfenster suchen, auf einem
   Fenster DANACH pruefen. Acht Wochen sind EIN Marktzustand; ohne Gegenprobe ist
   der Bestwert von N Kombinationen nicht von Zufall zu unterscheiden. Gealterte
   lokale Reihe fuer das Suchfenster, Live-Abruf fuer das Prueffenster, die
   Ueberlappung explizit nachrechnen und ausgeben.
3. **Den Parameterraum einmal ganz messen, bevor gedreht wird.** Spannt er fast
   nichts (42 Kombinationen zwischen +0,17 % und +2,23 %), ist der Parameter nicht
   der Hebel - dann die Abhaengigkeit messen, statt weiter zu suchen: Fenster
   ueber die ganze Reihe schieben und Ergebnis gegen die Marktbewegung stellen
   (`regime_gitter.py`). Korrelation +0,78 hiess hier: das Gitter folgt der
   Marktrichtung, gewinnt in fallenden Fenstern (+7 bis +13 pp Vorsprung),
   verliert in starken in beide Richtungen (bei |Markt| >= 15 % im Mittel
   -6,91 %).
4. **Erst dann einen Filter pruefen - und ihn fallen lassen, wenn er ungesehen
   nicht haelt.** Bestwert auf dem Suchfenster lieferte ungesehen +0,86 % gegen
   +1,80 % ohne Filter: kein Filter eingebaut.
5. **Nur einbauen, was auf beiden Fenstern UND im Walk-Forward traegt**, und die
   Groesse der Verbesserung nennen (hier ~1,4 pp auf acht Wochen - real, aber
   klein). Die bleibende Einschraenkung gehoert in denselben Satz: das Mittel
   ueber alle Fenster blieb negativ. „Optimiere bis positiv" laesst sich dann
   nicht ehrlich liefern - das wird gesagt, statt so lange zu drehen, bis ein
   Fenster positiv ist.
6. **Pruefen, WANN der geaenderte Wert gelesen wird.** Die Gitter-Leiter entsteht
   nur im Erstlauf (`neu = not z.get("leiter")`) und wird nie verschoben - ein
   geaenderter `stufen`-Wert wirkt erst auf eine frische Leiter. Das im Bericht
   datieren, nicht als sofort wirksam verkaufen.

## Schritt 6 - Gruppen und Baender, mit Stichproben-Disziplin
- Erst ab 8 Beobachtungen je Gruppe; dazu immer die Zahl der VERSCHIEDENEN
  Instrumente/Token. spiegel: unter 1 Mio **88 Runden aus 63 Token**
  Ø +16,5 % (unter 250k Ø +14,72 %, 250k-1M Ø +20,41 %), 1M-5M 15 Runden aus
  11 Token Ø -12,32 %, ab 5M 4 Runden aus 2 Token Ø -22,29 %.
- Die Gegenhypothese pruefen, bevor der Befund steht. Beispiel: die
  Slippage-Annahme ist ein fester Satz je Runde und trifft JEDES Band gleich -
  sie kann die Rangfolge nicht drehen und taugt nicht als Erklaerung.
- Ein Tor, das nie gegriffen hat, ist kein Parameter: `mindest_score` 60 im
  scanner, niedrigster eingegangener Score im Journal 68,4.
- Ein Schnitt ueber viele kleine Gruppen ist ein Kurvenfit: spiegel hat 19
  Wallets, zwei tragen das Buch (+15,06 % bei 30 Runden, +28,20 % bei 22), der
  Rest 1-5 Runden - daraus KEINE Wallet-Auswahl ableiten.
- Bei schiefen Verteilungen gehoert der Median neben den Mittelwert (spiegel:
  Mittel +10,98 %, Median -29,36 %).

## Schritt 7 - Die eine Aenderung, mit ihren drei Ablageorten
Beispiel 14.09.2026: `spiegel/wachen.json` `marketcap_band_usd` von
`[50000, 20000000]` auf `[50000, 1000000]`. Begruendung aus den Daten: das Ziel
von +60 % wurde ueber 1 Mio in 17 Runden ZWEIMAL erreicht, unter 1 Mio in 88
Runden 34 mal; dort laeuft stattdessen der Stop. Offene Positionen ueber 1 Mio
bleiben stehen und laufen in Stop, Ziel oder Frist aus (keine Zwangsschliessung).
Ablage:
1. `_`-Feld in `wachen.json` (`_marktkap_band`) mit Zahlen und Ruecknahme-
   Bedingung - neben dem Wert, nicht in einer Notiz.
2. Abschnitt in `MaxHirn/Wissen/Handelsregeln.md` (Zahlen, Gegenprobe und
   ausdruecklich, was NICHT geaendert wurde), `updated:` auf den heutigen Tag.
3. Regel/Test im Skill (hier) und, wo es geht, ein Test, der die neue Grenze
   prueft - nicht nur den heutigen Wert.

## Schritt 8 - Nachweis
- Werkzeug erneut laufen lassen: `auswertung_alle.py --spur <spur>` bzw.
  `<spur>/auswertung.py`.
- Tests der Spur: `discover -s tests -t tests` aus dem Spurordner.
- `spiegelstand.py` (byte-genau, 9/9) und `systempruefung.ps1`
  („0 zu entscheiden") - eine Aenderung ist erst fertig, wenn diese zwei Zeilen
  sie bestaetigen.

## Was eine duenne Stichprobe NICHT hergibt
- Parameter auf < 8 Runden (swap 3, kraken 5 echte Runden).
- Kostensaetze senken.
- Ein Tor anfassen, das nie gegriffen hat.
- Gruppen aussortieren, deren Ergebnis an 2-3 Runden haengt.
- Eine Strategie nach ihrem Mittelwert beurteilen, ohne den Median zu nennen.
- Aus eigenen Testrunden einen Befund machen.

## Die Backtest-Seite: was existiert, und was daran fehlt
Drei Spuren haben einen eigenen Backtest-Motor (kein Verbesserer noetig):
- `gitter/backtest_gitter.py` - faehrt `gitter/handeln.py` SELBST auf
  historischen Kerzen (`--stufen`, `--spanne-prozent`, `--wochen`, `--json`),
  stellt Gitter gegen Buy-and-Hold. **Immer mit den Werten der lebenden Spur
  fahren** (`--stufen 12 --spanne-prozent 20`), sonst bewertet man die Vorgaben
  des Skripts statt der Strategie.
- `orbk/backtest.py` - ORB nach SPEC, Urteil je Instrument und Einstiegsmodell,
  Spread-Sensitivitaet. Ein "Nein" mit dem Zusatz *unter 10 Verlierer* heisst
  **zu wenig Daten**, nicht schlechte Strategie (ETH_USD 7 Sessions: 42,9 %
  Treffer, Break-even 24,1 % - positiv, aber unbewiesen).
- `nautilus/backtest_grid.py` (eigenes venv, lokale Daten, kein Netz) -
  schreibt `backtest_grid_ergebnis.json` (Feld `differenz_zu_hold`).
Die Luecke dahinter: **kein Urteil landet irgendwo.** `freigabe.backtest_bestanden`
steht in mehreren `wachen.json` auf `false` und wird von NIEMANDEM geschrieben;
gitter/orbk drucken nur auf die Konsole, nautilus legt eine JSON ab. Und der
Verbesserer (der einzige Weg mit Vorschlag + Anwenden) kann nur den Scanner:
`lauf.einmal()` verlangt `wachen["watchlist"]` und `ruecktest.py` bildet den
Ein-/Ausstieg von `scanner/handeln.py` nach. Eine weitere Spur dort anschliessen
heisst **Adapter bauen** (Kandidatenquelle + Ein-/Ausstiegsregel der Spur), nicht
nur einen Eintrag in `spuren.json`.
Ein Backtest-Urteil in ein Tor zu schreiben (`freigabe.*`) ist eine Entscheidung
von Max - erst den Befund zeigen, dann fragen.
- Einen Parameter einbauen, der nur auf dem Suchfenster gewinnt (ungesehen
  schlechter als gar keine Aenderung).
- Zwangsschluesse weglassen ODER mitzaehlen - beides ist falsch; sie gehoeren
  getrennt ausgewiesen.
- Aus einem Parameterraum, der fast nichts spannt, eine Verbesserung ableiten.
