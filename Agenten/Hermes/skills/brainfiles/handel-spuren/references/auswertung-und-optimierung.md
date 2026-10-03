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

## Schritt 2b - Hat die Auswahlregel Edge - oder hat nur die Spur einen Orderpfad?

Zwei Fehler treffen zusammen und ergeben eine Spur, die in jeder Rangliste vorn
steht.

**1. Eine Auswahlregel wird gegen null gemessen statt gegen die Basislinie.**
Ein Mittelwert oder eine Trefferquote gegen null sagt nichts darueber, ob die
REGEL etwas hinzufuegt - sie kann schlicht das Marktniveau abbilden. Edge ist die
Differenz zur Auswahl OHNE Regel, gemessen an denselben Instrumenten, im selben
Zeitraum, mit derselben Gebuehr. Vorgehen: je Berichtstag alle bewerteten
Maerkte nehmen, die Kursentwicklung nach 1/3/7 Tagen je Markt holen, dann die
Auswahl (z. B. Score >= Schwelle) gegen die Gesamtheit stellen, die Differenz in
Prozentpunkten nennen und ein t-Test ueber die beiden Gruppen rechnen. Ein
|t| < 2 heisst: die Regel ist gegen die Basislinie nicht unterscheidbar - auch
wenn sie gegen null positiv aussieht. Das ist zugleich die Antwort auf „die Spur
X als Filter an die anderen Spuren haengen?": kein Edge heisst Filter weglassen,
nicht Filter verstaerken, und ein Filter, der nur das Marktniveau abbildet,
schneidet Runden weg, ohne bessere zu finden. Zusaetzlich je Score-Band
ausweisen - steigt der Score und faellt das Ergebnis, ist es kein Signal.

**2. „Die beste Spur" verwechselt Vorhersagequalitaet mit Handvormacht.** Die
Spur, die vorn steht, ist haeufig die EINZIGE mit echtem Orderpfad - sie hat
Runden, die die anderen nicht haben. Vor jeder Empfehlung „nimm die beste Spur
als Vorlage" beide Faehigkeiten getrennt feststellen: kann sie handeln (Orderweg,
Freigabe, Guthaben) und sagt ihr Signal etwas voraus (Forward-Return gegen die
Basislinie). Eine Spur ohne Orderpfad kann die bessere Strategie sein und trotzdem
nie sichtbar werden; eine Spur mit Orderpfad und ohne Edge ist das Gegenteil.
Beide Zustaende gehoeren in denselben Befund, sonst wird die unsichtbare zur
besten und die sichtbaren zur geaenderten Loesung.

**Kontrolle, wenn eine Spur ungewoehnlich gut dasteht:** Runden mit einer
Haltedauer im Takt des Aufrufers herausrechnen - das ist die Zyklusdauer, keine
Marktbewegung - und BEIDE Kennzahlen nennen; Ergebnis je Instrument ausweisen.
Ein Ergebnis, das an einem Instrument haengt, ist ein Ergebnis dieses
Instruments. Warum das je Spur passiert: ein Tagesbericht traegt als `preis` den
Schlusskurs von gestern, und nimmt der Einstieg daraus, liegt er bei steigendem
Markt UNTER dem Kurs - das Ziel ist dann schon beim Kauf erfuellt. Die
herausgerechneten Runden wegzulassen waere Schoenung, nicht Messung.

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
   - **Vorberechnen ist erlaubt, aber nur mit Gleichheits-Nachweis.** Rechnet die
     Spur ihren Indikator bei JEDEM Schritt neu (MACD-MTF ueber drei Zeitrahmen
     ist O(n^2); ein Lauf ueber 7000 Kerzen dauert Minuten), rechnet der Treiber
     die Indikator-Arrays einmal je Instrument vor — und muss dann beweisen, dass
     er dasselbe entscheidet. Pruefskript nach dem Muster
     `Agenten/Handel/bt_opt/verify_equivalence.py`: je Index das vorberechnete
     Signal gegen `signal()` der Spur stellen UND den Einstieg (Wert, Stop, Ziel,
     Nominal) gegen `pruefe_einstieg()` (SCHREIBEN=False, Journal abgefangen) —
     Ergebnis als Zaehlung („1200 Schritte, 0 Abweichungen"), nicht als Urteil.
     Abweichungen im ROHsignal sind zu erwarten und kein Fehler, wenn der Treiber
     nur EINE Seite nachbildet: dann die gepruefte Seite benennen.
     Die Kopie der Einstiegslogik im Treiber ist genau der Grund fuer diesen
     Nachweis — sie ist eine zweite Wahrheit, bis sie belegt ist. Ohne den
     Nachweis sind die Varianten-Zahlen die Zahlen der Nachbildung.
     Die Treiber und der Nachweis gehoeren versioniert (`!Agenten/Handel/*.py`
     greift, ein Unterordner wie `bt_opt/` braucht eine eigene `!`-Zeile).
2. **Zwei Fenster ohne Ueberlappung.** Auf dem Suchfenster suchen, auf einem
   Fenster DANACH pruefen. Acht Wochen sind EIN Marktzustand; ohne Gegenprobe ist
   der Bestwert von N Kombinationen nicht von Zufall zu unterscheiden. Gealterte
   lokale Reihe fuer das Suchfenster, Live-Abruf fuer das Prueffenster, die
   Ueberlappung explizit nachrechnen und ausgeben.
   Reicht die Historie nicht fuer ein Fenster DANACH, ist die Halbierung
   derselben Reihe (H1/H2) das Minimum. Staerker ist ein zweiter Zeitrahmen mit
   anderem Kalenderbereich — die 4H-Reihe reicht Monate weiter zurueck als die
   1H-Reihe und deckt damit einen Zeitraum ab, den die Suche nie gesehen hat.
   Der Nachweis, dass die Vorberechnung auch dort stimmt, gehoert dazu
   (Stichproben-Indizes gegen die schrittweise Rechnung, Trefferzahl nennen).
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
   - **Ein schaerferer Filter macht die RUNDE besser, nicht den Ertrag.** Eine
     zusaetzliche Bestaetigungs-Bedingung hebt Trefferquote, Wert je Runde und
     senkt den Ruecklauf (im Beispiel: 48,4 -> 51,9 % Quote, +2,28 -> +2,79 %/R,
     -63,5 -> -54,8), aber sie laesst Runden fallen (62 -> 54; auf dem zweiten
     Fenster 38 -> 27). Deshalb IMMER auch die Summe vergleichen: sie kann trotz
     besserer Runde kleiner werden. Beides gehoert in den Befund, sonst wird eine
     Qualitaets-Verbesserung als Ertrags-Verbesserung verkauft.
   - **Zwei Sorten Variante, zwei Urteile.** Parameter-Knoepfe (Ziel-R, Stop-Band)
     verschieben die Rundenzahl und halten den Vorsprung je Runde nicht;
     Faktor-/Fenster-Aenderungen am Indikator verschlechtern oft durchweg. Der
     tragbare Fund war eine BESTAETIGUNGS-Bedingung am selben Indikator (das
     Histogramm muss auch im groesseren Zeitrahmen steigen) - kein neuer
     Parameter, damit kein Overfit im Sinne der Hausmethodik. Wirkt ein Knopf
     identisch zum Stand (`stop max15`), bindet er nicht und ist kein Befund.
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

## Backtest einer NEUEN Strategie auf Fremddaten

Wenn keine eigenen Runden existieren, sondern eine Behauptung von aussen geprueft
werden soll, sind diese Regeln die Mindestausstattung - ohne sie ist die Zahl
wertlos, egal wie gross sie aussieht:
1. **Kein Blick nach vorn.** Jede Eingangsgroesse fuer Tag D stammt aus Daten BIS
   D-1 (Vortagesschluss der Volatilitaet, Tageroeffnungskurs), nie aus dem
   Tagesverlauf. Sonst wird die Zukunft mitgemessen.
2. **Konservative Balkenreihenfolge.** Liegen Stop und Ziel im SELBEN Balken,
   zaehlt der Stop. Immer. Die optimistische Reihenfolge macht aus jeder
   Strategie einen Gewinner; nur die konservative ist zu verteidigen.
3. **Gebuehr je Seite abziehen und die Boerse nennen.** Ein 0-%-Satz aus einem
   Abo gilt nur fuer die Boerse, fuer die das Abo gilt - auf eine andere Boerse
   uebertragen ist er geschenkte Rendite.
4. **Nie aus EINEM Feld lesen.** Raster ueber die Nachbarwerte (z. B. Grenzweite,
   Stopabstand, Zielanteil), Stichprobe halbieren, nach Seite trennen (long /
   short). Erst ein glattes Muster ueber Nachbarn, das in beiden Haelften UND auf
   beiden Seiten dasselbe Vorzeichen traegt, ist ein Befund. Ein einzelnes
   positives Feld ist Zufall - genau dafuer ist die Gegenprobe da. Die Gegenprobe
   gehoert mit in den Bericht (z. B. "+0,32 % erste und +0,24 % zweite Haelfte"),
   sonst ist der Bestwert nicht von einem Kurvenfit zu unterscheiden.
5. **Ziel auf den GEMESSENEN Anteil setzen, nicht auf den erzaehlten.** Eine
   Umkehrstrategie zahlt oft nur auf dem halben Rueckweg; der volle Rueckweg zur
   Tagesmitte kann in ALLEN Feldern negativ sein. Wer den erzaehlten Wert
   einbaut, baut eine Strategie, die der Autor nicht gemessen hat.

Was der Backtest baulich NICHT messen kann (Groessen ohne Historie, z. B. offenes
Interesse je Strike), wird als Luecke AUSGEWIESEN und nicht durch eine
Ersatzkonstruktion geheilt - dieser Teil ist nur vorwaerts pruefbar. Und das
Ergebnis darf der Quelle WIDERSPRECHEN: der Widerspruch gehoert in den Bericht,
nie weggeglaettet. Traegt eine Haelfte der Fremdstrategie und die andere nicht,
wird die tragende uebernommen und die andere als unbestaetigt benannt.

## Kennzahlen je Spur: was die eigene Datenlage traegt

Kommt ein Kennzahlen-Formelblatt von aussen (Sharpe, Sortino, Calmar, VaR/CVaR,
Expectancy, MAE/MFE), wird es NICHT ganz uebernommen. Reihenfolge:

1. **Zeitbasierte Kennzahlen brauchen Tagesrenditen - das Haus fuehrt Runden.**
   Sharpe, Sortino, Calmar, CAGR, VaR/CVaR und jede Annualisierung setzen eine
   taegliche Kapitalkurve voraus. Runden auf Tageswerte umzurechnen ist eine
   ERFINDUNG: nicht einbauen, sondern im Bericht als Luecke benennen („das
   braucht eine taegliche Reihe, die wir nicht fuehren"). Wer sie will, baut
   zuerst die Reihe.
2. **Die t-Statistik der Expectancy ist die Zahl hinter „unter 8 Runden ist es
   ein Befund".** `t = mean(pnl) / (std(pnl) / sqrt(n))` ueber die ECHTEN Runden
   (Zwangsschluesse raus, siehe Schritt 5). |t| < 2 heisst: nicht von 0
   unterscheidbar. Immer n UND t zusammen nennen - ein t ohne Fallzahl ist
   keine Aussage, und eine grosse Trefferquote mit t um 1 ist Rauschen.
3. **Eine abgeleitete Kennzahl erst gegen die FUELLQUOTE ihrer Spalte pruefen.**
   Ein Stop-Vorschlag aus der MAE der Gewinner ist nur so gut wie die Spalte: ein
   konstanter Platzhalter (bei Ziel-Ausstiegen durchweg `0.0000`) macht daraus
   0 % - und 0 % sieht wie ein Messwert aus. Also vorher zaehlen, wie viele
   Zeilen einen echten Wert tragen, und unter der Schwelle „MAE nicht gefuehrt"
   ausgeben statt eine Null zu drucken. Gilt fuer jede Spalte, aus der eine
   Kennzahl abgeleitet wird.
4. **Zwei Regeln, bevor eine Zuordnung wiederverwendet wird.** Wird eine
   Tabelle (Spur -> Rechenweg) aus einer Funktion herausgezogen, damit ein
   zweites Werkzeug sie nutzt, muss die ALTE Funktion die neue rufen - sonst
   stehen zwei Wahrheiten nebeneinander, und die zweite altert still. Und die
   Gegenprobe muss wissen, was der Verbraucher FILTERT: `kennzahlen()` nimmt
   Zwangsschluesse heraus, also gilt `n + n_stoerung == len(runden)`, nicht
   `n == len(runden)` - eine Gegenprobe mit der falschen Gleichung meldet
   „ABWEICHUNG" auf korrektem Code. Laeuft parallel eine zweite Sitzung im
   selben Baum, vor dem Schreiben den frischen Stand lesen und ihre Erweiterung
   (neue Spurenliste, neue Einheit) mitziehen.
5. **Ein Werkzeug mit numpy/pandas braucht das passende venv - und ein Test in
   der Suite wird dann uebersprungen statt rot.** Nicht jedes venv im Haus
   traegt numpy (das scanner-venv nicht). Vor dem Bauen pruefen, welcher
   Interpreter die Abhaengigkeit hat, und im Test `skipUnless(<import ging>)`
   mit einer gemeinsamen Basisklasse setzen: sonst faellt die ganze Suite rot,
   obwohl nur der Interpreter nicht passt.

Werkzeug im Haus: `Agenten/Handel/strategie_kennzahlen.py` (venv `Handel/.venv`)
rechnet je Spur t-Statistik und Stop-Vorschlag aus der MAE; die Runden kommen
ueber `auswertung_alle.runden_fuer(spur)`.

6. **Die Trefferquote ist in der Indikator-Auswahl das FALSCHE Mass — sie kann
   dem PnL entgegengesetzt laufen.** Gemessen an einem Takt, einem Fenster und
   einer Gebuehr (BTC 15m, 60 Tage, 0,05 % je Seite, acht Skripte nebeneinander):
   die Mean-Reversion-Varianten hatten die HOECHSTE Trefferquote des Feldes
   (67,7 % und 58,8 %) und das SCHLECHTESTE Ergebnis (−638,99 und −693,51);
   die Trendvarianten hatten 24,8 bis 30,2 % Treffer und die besten Ergebnisse
   (+816,55 und +942,40). Die Logik: ein Trendfilter laesst die wenigen Gewinner
   laufen und nimmt viele kleine Verluste; eine Mean-Reversion-Regel holt kleine
   Gewinne haeufig und gibt sie in einem Ausreisser zurueck. Also:
   * Bei der Frage „welcher Indikator?“ ist die Trefferquote **nicht** die
     Entscheidungsgrundlage; gerechnet wird t-Statistik und Ergebnis je Runde.
   * Ein Indikator, der nur eine Bewegung des Trends abbildet, bringt neben
     einer vorhandenen Trendbedingung **keine** Information (RSI neben
     `ema20 > ema50` misst dieselbe Bewegung) und wird nicht eingebaut.
   * Ein Oszillator als EINSTIEG ist meist zu langsam (gemessen: zwei Signale in
     60 Tagen) — als Filter taugt er, als Taktgeber nicht.
   * Die Belegausgabe ist die Tabelle selbst: Takt, Fenster, Gebuehr und
     Ergebnis JE Skript nebeneinander, sonst laesst sich die Aussage nicht
     nachvollziehen.

## Die Auswertung selbst lesen, bevor man ihr glaubt

Vier Dinge, die eine Summe kleiner machen, als sie aussieht:

1. **Die Summe ist meist EINE Spur.** Vor dem Urteil den Anteil der groessten
   Spur an der Stufensumme nachrechnen (der Scanner trug 82 % in Basis und
   96 % in mittel). Steht der Rest bei null oder im Minus, ist die Summe ein
   Befund ueber eine Spur, nicht ueber das System - so berichten.
2. **Papierzeilen tragen keine Gebuehr: ihre Summen sind BRUTTO.** Die Spalte
   „Kosten (aus den Zeilen)" zeigt bei allen Papierbuechern 0,00 %, bei den
   echten 0,05-0,60 %. Brutto- und Nettosummen nie in dieselbe Rangfolge
   stellen; fuer ein Papierbuch kommt der Satz aus der `wachen.json` oder aus
   einer gemessenen Fuellung.
   **Der Ausweis gehoert in die Kennzahl selbst, nicht in eine Fussnote.** Die
   Trennung braucht DREI Teile an EINER Stelle: ein Flag je Spur, ob die
   Gebuehr schon IM Journal steckt (`GEBUEHR_SCHON_DRIN` = xperp/swap/scanner/
   kraken; scanner/kraken rechnen sie in den Betrag, xperp/swap ueber
   `gebuehr_pct`/`funding_pct`), die Gebuehr aus der `wachen.json`
   (`gebuehr_fuer(spur)` - EIN Leser, nicht zwei) und ein `netto`, das nur
   gerechnet wird, wenn das Flag es erlaubt. Zwei Fehler, die jede Fassung
   einmal macht: **zweimal abziehen** (waere so falsch wie gar nicht - der
   `kosten_netto` gehoert auf 0, wenn die Gebuehr schon drin ist) und die
   **Vorgabe „netto"** (wer nichts angibt, bekommt die ehrliche Antwort
   „brutto": die Funktion zieht NIE etwas ab, sie weist nur aus). Ein Bericht
   ohne bekannten Satz sagt **„BRUTTO und UNBEKANNT"**, nicht „0,00 %" - und
   eine Zahl, die nur aus der Zeile kommt, wird nicht stillschweigend
   korrigiert, sondern mit der zweiten Zahl daneben gestellt. Gemessen an einer
   Handvoll Spuren verschiebt das die Urteile: +10,82 -> +9,62 USD,
   -5,02 -> -6,02, +38,85 -> +37,92, +2,30 -> +2,00.
   **Der Ausweis gehoert in JEDE Anzeige, nicht nur in die Konsole.** Die
   Konsole (`auswertung_alle.py`) liest niemand taeglich; gelesen werden
   `/strategien` im Telegram-Bot und die „7 Tage"-Zeile des Tagesberichts. Beide
   brauchen denselben Zusatz aus EINER Funktion (`befehle._brutto_zusatz(k)`:
   „netto %+.2f" / „(Punkte, brutto)" / „(brutto, Gebuehr unbekannt)", leer
   wenn die Spur schon netto rechnet), und die Einheit kommt aus der Kennzahl
   (`k["einheit"]`) statt als „USD" im Formatstring zu stehen - sonst traegt
   ein Punktebuch wieder eine Waehrung. Zwei Grenzen dabei: der Telegram-Text
   ist auf 4000 Zeichen begrenzt und ein Zusatz je Zeile summiert sich ueber
   ~40 Spuren (`len(befehle.strategien())` messen, nicht schaetzen), und nach
   der Aenderung muss der SkillsBot-Task neu starten - das Modul liegt im
   laufenden Prozess im Speicher.
3. **Fehlt der Gebuehrenschluessel GANZ, rechnet das Werkzeug mit 0 % - und
   eine tote Spur sieht tragfaehig aus.** Vor jeder Uebernahme eines
   `f_max`-Urteils (`kosten_wendepunkt.py`) pruefen, ob die `wachen.json` der
   Spur ueberhaupt ein Gebuehrenfeld traegt (`grep gebuehr <spur>/*.py`), und
   den Satz gegen die BOERSE der Spur halten, nicht gegen den Namen: `orbk` ist
   ORB auf Kraken-Spot und braucht dort 1,2 % je Runde (0,600 % je Seite
   gemessen), waehrend die eigene Rechnung +0,01 bis +0,03 % zeigt. Ein `f_max`
   unter dem Gebuehrensatz der eigenen Boerse heisst tot, unabhaengig von der
   Runde. Der Warnsatz des Werkzeugs („haengt an der Gebuehrfreiheit") ist ein
   Verdacht, kein Lob.
4. **Nur ein `f_max` unter 0 % ist der harte Todesbeweis** - er gilt ohne jede
   Gebuehrenannahme. Eine Spur mit -0,6 %/Runde ueber 13-20 Runden ist keine
   duenne Stichprobe, sondern eine Messung; sie gehoert stillgelegt oder
   umgebaut, nicht weiter beobachtet.
5. **Der Gebuehrensatz hat eine EINHEIT, und sie steht nicht im Namen.**
   `gebuehr_taker` in der `wachen.json` ist ein **Bruch je Seite** (0.0005 =
   0,05 %, 0.006 = 0,600 %), `f_max` aus `kosten_wendepunkt.py` dagegen
   **Prozent je Runde**. Wer die beiden Zahlen direkt vergleicht, liegt um
   Faktor 100 daneben und erklaert jede Spur fuer tragfaehig: gemessen druckte
   das Werkzeug den Bruch mit Prozentzeichen und stellte ihn dem Rundensatz
   gegenueber - jede Gebuehrenaussage war um 100 zu klein, und das sah wie ein
   Messwert aus. Die Umrechnung gehoert an EINE Stelle als reine Funktion
   (`geb_runde = 2.0 * geb * 100.0`, also Seite mal zwei mal hundert) samt
   Einheiten-Kommentar im Docstring - nicht an jeder Druckstelle neu, sonst
   wandert der Faktor wieder aus einer davon heraus. Beleg: eine eigene
   Testdatei, die die EINHEIT prueft (0.006 -> "0.600 % je Seite" / "1.200 %
   je Runde") und den alten Faktor-100-Fehler als Gegenprobe festhaelt; danach
   `orbk` 1,200 %/Runde gegen `f_max` +0,03 % = tot um Faktor 40. **Ein
   Bruch-Feld und ein Prozent-Feld duerfen nie ohne Umrechnung in dieselbe
   Zeile.**
6. **Ein Buch ohne Einsatz hat keinen Prozentwert - und die Anzeige darf keinen
   behaupten.** Fuehren Spuren ihre Runde in PUNKTEN (die ORB-Buecher: `gv_usd`
   ist die Kursstrecke mal `punkt_wert_usd`, bei diesen Instrumenten 1:1 - also
   der Gewinn JE EINHEIT), gibt es kein „Ergebnis in Prozent": die Zeile
   zeigte trotzdem `(+0.00 %)` und die Einheit „USD", und die Summe der
   Kursstrecken las sich wie ein Geldbetrag. Zwei Regeln: (a) ohne Einsatz
   keinen Prozentwert drucken, sondern den Grund nennen („kein Einsatz im Buch
   (Punktebuch) - Prozent nicht rechenbar") und die Einheit auf „Punkte"
   stellen; (b) **KEINEN Einsatz erfinden.** Der naheliegende Weg
   (`risiko_pro_trade / stop_abstand`, so steht es in der SPEC der Spur) ergibt
   bei einem Stop, der die Range-Hoehe IST (ORB, bei ETH oft 0,4 %), ein
   Nominal von einigen tausend USD - das ist eine Design-Entscheidung, keine
   Reparatur. Statt dessen ein groessenunabhaengiges Maß daneben: **Ergebnis in
   R** = `gv / |einstieg - stop|`, je Runde und in Summe, mit Trefferquote. Das
   ergab die erste ehrliche Zahl dieser Spuren (orbk +2,18 R, orb -0,46 R) -
   vorher stand dort ein positives „USD", das nur eine Punktesumme war.
   **Und pruefen, ob die Spur ueberhaupt in der Auswertung steht:** `orb` fehlte
   ganz, weil nur `orbk` in der Liste stand - eine Spurgruppe still auf null zu
   setzen ist derselbe Fehler wie eine falsche Zahl.

Fallen beim Fahren und Deuten:
- **„alle" heisst: ein Aufruf je Stufe.** `auswertung_alle.py` kennt kein
  `--alle` (Basis ohne Argument, dann `--risiko mittel|hoch`), dazu
  `kosten_wendepunkt.py`. Die Laeufe in EINE Datei haengen und je Stufe einen
  Abschnitt setzen, sonst stehen drei Ergebnisse ohne Etikett untereinander.
- **Ein Auswerter, der die Ausgabe parst, muss das VOLLE Etikett treffen.** Zwei
  Zeilen beginnen mit demselben Wort („Ergebnis auf den Einsatz" und
  „Ergebnis … USD"); ein Praefix-Match zieht die falsche Zeile, und die Summe
  ist still falsch. Etikett vollstaendig matchen und die Rohzeilen daneben
  legen, bevor die Zahl in einen Bericht geht.
- **Eine Uhrzeit im Kopf eines Berichts ist keine Zeitquelle.** Die Berichte
  stempeln mit der Uhr des ausfuehrenden Prozesses (die Sandbox kann Tage
  zurueckliegen). Datum fuer Notiz, Commit und Antwort aus
  `git log -1 --format=%ci` oder vom Host nehmen - sonst wandert ein falsches
  Datum in den Bericht.
- **Die Stufen sind getrennte Buecher, kein Maßstab.** Dieselbe Spur kann in
  Basis und hoch gegenlaeufige Vorzeichen tragen (xperp) - ein Summenvergleich
  ueber die Stufen ohne Paarung je Instrument und Zeitfenster misst
  „andere Geschaefte" gegen „mehr Einsatz" (`references/risikostufen.md`).

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
