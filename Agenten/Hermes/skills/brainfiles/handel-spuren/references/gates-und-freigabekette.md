# Tore, Freigaben und die Trennung von Monitor und Ausfuehrung

Jede Spur hat zwei Fragen: **darf sie handeln** und **was traegt ihr Signal**.
Die beiden gehoeren getrennt, und beide gehoeren an eine feste Stelle.

## 1. Ein Tor ist ein Verweigerer, kein Setzer

`freigabe.erfuellt` bleibt der von Hand gesetzte Haken des Menschen. Jede
Zahlengroesse ist eine **zusaetzliche Sperre in derselben Kette**, und sie
rechnet. Sie vergibt nichts.

Ein Werkzeug, das Freigaben vergibt, ist eine Behauptung. Eins, das
verweigert, kann nur zu streng liegen - und das sieht man sofort, weil es
sagt warum.

Im Zweifel **verweigern**: Ein Torschutz, der bei seinem eigenen Ausfall
durchlaesst, ist kein Torschutz. Fehlt das Modul oder ist die Zahl nicht
lesbar, lautet die Antwort "nein", nicht "weiter".

### Ein gesetzter Haken loest nicht das Problem dahinter

Wird auf Auftrag "setz die Freigabe" gesagt, ist das **eine** von N
Sperren. Die Antwort ist dann eine Tabelle mit **einer Zeile je Tor** und
ihrem Ergebnis - nicht das Wort "gesetzt". Tore sind AND-verknuepft: das
Aufheben eines Hakens macht die Rechnung der anderen sichtbar, die vorher
nie zur Sprache kam.

Der typische Fehler ist die Meldung nach dem Setzen: „Haken gesetzt" mit dem
Gefuehl von Erledigung. Sie ist falsch, sobald eine zweite Sperre greift -
und der Nutzer prueft genau die, indem er ausprobiert. Gemessen: der Haken
wurde auf `true` gesetzt, die Spur handelte trotzdem nicht, weil ein
Gebuehren-Tor `excess +0,01 % - gebuehr 0,20 % = -0,19 %` rechnete. Auf
„ja setzen" folgte deshalb zurueck auf Papier - nicht aus Sturheit, sondern
weil das Einhalten des eigenen Kriteriums wichtiger war als das Erfuellen des
Worts.

Merksatz: **bei einer Kette aus drei Sperren ist die Antwort drei Zeilen,
keine eine.** Und wer eine Sperre setzt, gegen deren Grundsatz er selbst
geschrieben hat, misst die Bedingung nach, die er selbst notiert hat
(„wiedereinschalten nur, wenn der Excess ueber der Gebuehr liegt") und
nennt die Zahl. Faellt sie durch, ist das Ergebnis `zurueck auf Papier` -
und die Historie des Vorgaenger-Vermerks bleibt daneben stehen, nicht
ersetzt.

### "X freigeben" heisst erst lesen, ob X schon freigegeben ist

Ein Freigabeauftrag ist kein Freigabeschalter. Steht das Feld bereits auf `true`,
ist die Arbeit gegenstandslos - und die Antwort ist dann nicht "gesetzt",
sondern: **steht schon, und das, was tatsaechlich blockiert, ist Y.**

Diese Diagnose ist selbst eine Messung, und sie hat denselben Fehlermodus wie
jede andere Sperrpruefung: wer ein Tor aufruft, ohne den Zustand zu setzen, den
der Aufrufer setzt (Flag aus der Wachen-Datei, geholte Marktliste, Freigabestufe),
meldet **per Konstruktion** eine Sperre. Sie sieht vollstaendig plausibel aus,
weil die Begruendung echt ist und der Marktzustand echt ist - nur der
aufrufende Zustand fehlt. Deshalb drei Aufrufe mit derselben Eingabe: ohne
Freigabe, mit Freigabe, mit Ausstiegs-Ausnahme. Nur wenn der mittlere durchlaesst,
ist die Sperre echt. Gegenprobe dazu ist der Gegenentwurf: laesst die Freigabe
nichts aendern, ist die Freigabe nicht die Sperre.

### Ein gefilterter Kandidat ist meist kein Tor, sondern das Buch

`N Treffer; N gefiltert` bei ansonsten offener Kette heisst in der Regel
**nicht**, dass die Tore zu sind. Zwei Filter, die dort greifen und beide aus
dem Buch kommen, nicht aus der Konfiguration:
- `(inst, seite)` ist bereits offen -> der Kandidat ist ein Duplikat.
- die **Basis** ist bereits belegt (`max_je_basiswert`).

Beide zaehlen Buchbestand. Steht der Bestand im falschen Modus, filtern sie
Signale, die es gibt. Der Weg zur Ursache: die Trefferzahl der Zeile gegen die
Positionen im Buch halten, Basis fuer Basis, und dann **das Buch gegen die
Boerse** - beide Abfragen gehoeren zusammen, weil der haeufigste Befund
beide zugleich ist (siehe naechster Abschnitt).

Zwei Namen desselben Basiswerts sind dabei EIN Filter, nicht zwei: ein
gueltiger Kandidat auf `X-USDC` wird vom ge/offenen `X-USDT` derselben Basis
gefiltert, wenn `max_je_basiswert` greift. Wer beide Treffer einzeln
untersucht und keine Basis-Grenze nennt, findet fuer jeden eine
Erklaerung und sieht die gemeinsame Ursache nicht.

### Die Torkette gehoert in REIHENFOLGE geprueft, nicht stichprobenartig

Wenn mehrere Tore moeglich sind, ist die Reihenfolge der Aufruf: erst das
Tor, das die Spur selbst zuerst nimmt, bis zum ersten, das greift. Ein
Skript, das ein mittleres Tor prueft, kann gruen sein und die Spur trotzdem
nicht handeln - der echte Blocker stand eine Stufe weiter vorn oder hinten.

Der beste Beleg ist der **Vorschau-Lauf im Betriebsmodus**
(`MAXHIRN_ROUTINE=1 ... handeln.py --vorschau`): er liefert Filterzahlen UND
die Sperrzeile in der Reihenfolge der Spur selbst, mit dem Wortlaut des
Grundes. Wenn diese Zeile „nichts" nennt und trotzdem Treffer filtert, ist der
Filter im Buch - siehe oben.

## 1a. Papier-Positionen in einem Live-Buch blockieren jede Freigabe

**Der Moduswechsel richtet nur das Zustandsfeld, nicht die Positionen.** Wird
eine Spur scharf geschaltet, setzt der Zyklus `z["modus"]`, laesst aber jede
Position stehen, die vorher aus einem `papier`-Einstieg entstanden ist. Diese
Positionen tragen dann **kein `modus`-Feld** und **keinen Einsatz**.

Die Folge ist dreifach und uebersieht man jede einzelne:
- sie werden von der Platzrechnung **nicht** als belegt gezaehlt (sie zaehlt nur
  `modus == "live"`), der Deckel aber schon - das Buch meldet dadurch eine
  Belegung, die es rechnerisch nicht hat;
- die Duplikat- und Basisfilter **sperren** neue Signale auf derselben Basis,
  ohne dass eine Sperrenzeile entsteht;
- sie sind ueber die Boerse **nicht vorhanden**, was als Platzmangel liest.

**Deshalb hat eine Freigabe hier nichts zu tun.** Das Aufheben jeder Sperre
aendert nichts, solange Buchpositionen ohne Börsen-Gegenstueck stehen. Der
Nachweis ist billig und immer derselbe: **Buch gegen offene Positionen je
Symbol, jede Position einzeln.** Alles im Buch, was an der Boerse 0 offene
Positionen meldet, ist ein Geist und blockiert.

Beim Ausbuchen gehoert die Buchung **neutral**: Wert = Einsatz, Grund
`buchbereinigung`. Sonst erzeugt die Bereinigung selbst einen Verlust, der in
die Kapitalkurve laeuft. Und die Reihenfolge ist nicht frei: erst alle
neutraalen Papier-Geiste ausbuchen, **dann** die Positionen mit `modus: live`
gegen die Boerse pruefen (die koennen echt sein und brauchen eine eigene
Entscheidung), **erst dann** ist die Platzfrage messbar und eine neue Freigabe
ueberhaupt eine Frage.

Merksatz: **ein Tor, das an einem Buch haengt, dessen Eintraege es nicht gibt,
ist kein Tor - es ist eine Buchhaltungsluecke, die sich als Sperre ausgibt.**

### Ein Signal ohne Ausfuehrungsweg ist ein eigener Befund

Ein Kandidat kann an einem PF_-Markt handelbar sein und trotzdem nicht
orderbar sein, weil eine Ableitung (Basis-Umbenennung, `PF_<BASIS>USD`) am
Zielmarkt unter einem ANDEREN Namen laeuft. Gemessen loeste `BTC` auf
`PF_BTCUSD` auf - es gibt aber nur `PF_XBTUSD`; die Meldung „gibt es am
Zielmarkt nicht" sah damit wie ein toter Markt aus, obwohl die Basis sehr
wohl handelbar war.

Zwei getrennte Fragen also: **handelbar** (steht ein Markt dafuer?) und
**orderbar** (durchlaesst der Aufruf den Namen durch?). Der Unterschied
entscheidet, wo man sucht - ein nicht aufloesbarer Name ist ein
Tabellenproblem, keine Marktlage. Beide Namen einer Basis (alle Quotes)
gleich behandeln, sonst zeigt die eine Quote „handelbar" und die andere
„unbekannt".

Merksatz: **ein toter Markt im Haus sieht genauso aus wie ein echter
Fehlstand.** Bevor eine Basis als nicht handelbar gemeldet wird, die
Marktliste selbst fragen und nach einem Namen mit abweichendem Praefix
suchen.

Merksatz zur Luecke: **eine Spur ohne Buchbereinigung kann ihre Altlasten nicht
ausbuchen.** Der Aufraeumer `bueche_papier_altlasten_aus()` ist nicht ueberall
der Standard - vor einer Freigabe fragen, ob die Spur ihn ueberhaupt hat. Fehlt
er, ist das die Ursache und nicht der Schalter.

### Ein Skript, das alle Tore selbst traegt, darf an keinem Import scheitern

Jeder Weg ausserhalb des gewohnten Kettenverlaufs (Executor, Wache, Cron)
importiert die Tor-Module selbst. Faellt einer dieser Importe aus, ist die
**gesamte Kette** weg - und der Fehler sieht am Anfang wie ein Torschutz
aus („im Zweifel keine Order"), ist aber keiner. Gemessen: `sys.path.insert`
fehlte vor dem ersten von vier Importen einer flachen Datei, der Lauf brach
jede Minute ab, und keine Spur kam je zu einem Einstieg - ohne eine Spur-
Logzeile.

## 1b. Drei getrennte Schalter, drei getrennte Belege

`handel_erlaubt` (Zulassung der Spur), `freigabe.erfuellt` (der von Hand
gesetzte Haken) und das **Zeitfenster** sind drei Dinge. Ein Auftrag kann eins,
zwei oder alle drei meinen — jede Fehlzuordnung ergibt eine scharfe Spur, die
es nicht ist, oder eine gesperrte, die es nicht mehr ist.

Reihenfolge beim Umlegen, jede Stufe mit eigenem Beleg:

1. **Der Haken in der Wache** (`freigabe.erfuellt`). Gehoert als
   `<feld>_vermerk` daneben: WORUM es geht, welche Messung vorher stand und was
   der Vermerk ueberholt. Ein Vermerk, der eine Abschaltung begruendet, wird
   bei einer neuen Freigabe **nicht geloescht, sondern ergaenzt** — er ist die
   Historie und der Grund, warum die Freigabe eine Entscheidung war. Ersetzt
   man ihn, verliert die naechste Sitzung die Begruendung; laesst man ihn
   unverändert stehen, behauptet er das Gegenteil des heutigen Zustands. Beides
   ist schlecht: **ergaenzen mit Datum und Auftrag**.
2. **Der Vorschau-Lauf im Routine-Modus**
   (`MAXHIRN_ROUTINE=1 handeln.py --vorschau`) als Zwischenbeleg. „Live waere
   gesperrt durch: nichts" heisst: jeder Schalter ist offen, es fehlt nur noch
   das Fenster. Das ist die Aussage, die man dem Auftraggeber vorlegt — und sie
   unterscheidet „klar" von „setzen war nicht moeglich".
3. **Das Zeitfenster ueber den VORGESEHENEN Weg**: `anfrage_stellen()` und
   dann `oeffnen()` — genau die beiden Aufrufe, die `AUTO_FREIGABE` im
   Dauerlauf und `/ja` vom Handy gehen. **Nie `offen_bis` von Hand schreiben**
   und die Datei-Sperre umgehen: das ueberspringt die Wiedervorlage-Fristen
   (dieselbe Frage alle 30 Minuten) und hinterlaesst keinen Vermerk, warum es
   offen ist.
4. **Der echte Dauerlauf-Zyklus als Endbeleg**, aus dem Log, mit Zeit und
   Spur: die Zeile `(live) ok` der SPUR. Sie belegt den Modus des Laufs, nicht
   eine Order — die Order belegt erst die Journalzeile mit `modus=live`.

Bei jeder Freigabe-Erhoehung gilt dieselbe Grenze wie bei einer Grenz-Erhoehung
(siehe Abschnitt 4): **`oeffnen()` kann keine Grenze heben.** Einsatz, Hebel
und Platzzahl kommen aus der Wache. Wer beides in einem Auftrag meint, macht
zwei Schritte und sagt, welcher welcher war.

## 1c. Eine Live-Spur zurueck auf Papier: drei Stellen, erst pruefen, dann schalten

Die Ruecknahme einer Live-Freigabe ist der Spiegel der Freigabe und beruehrt
dieselben drei Stellen, die sie scharf geschaltet haben:

1. **`wachen.json`**: `handel_erlaubt=false`, `freigabe.erfuellt=false`,
   `herzschlag_max_minuten` zurueck auf 180 (Papier-Regel). Die Vermerke
   **ergaenzen** mit Datum und Auftrag, nie ersetzen - der alte Vermerk ist
   die Begruendung, warum die Freigabe eine Entscheidung war.
2. **`dauerlauf.AUTO_FREIGABE`**: die Spur entfernen. Eine deaktivierte Spur,
   die weiter in der Auto-Freigabe steht, oeffnet weiter Fenster und sieht
   live aus, obwohl sie es nicht ist.
3. **Der Test, der den Live-Zustand eingefroren hat** (z. B.
   `test_start_live_aktiv` mit `assertIs(handel_erlaubt, True)`). Er wurde
   beim Scharfschalten auf den Live-Stand gedreht und muss beim
   Deaktivieren zurueckgedreht werden - sonst ist die Suite rot, obwohl der
   Code stimmt.

**Reihenfolge: erst pruefen, dann schalten.** Vor dem Umlegen der Schalter
zwei Dinge gegen die Boerse und das Journal belegen, sonst ist die
Ruecknahme ein Eingriff in eine laufende Position:

- **keine offene Position** (`zustand.json` ohne `position`-Dict, `modus`
  nicht `live`)
- **keine `,live,`-Zeile im Journal** - eine Spur, die live geschaltet war,
  aber nie eine Live-Order ausgefuehrt hat, ist gefahrlos zurueckzunehmen;
  eine mit offener Live-Position braucht eine eigene Entscheidung.

Der haeufigste Grund fuer die Ruecknahme ist ein **Punktebuch ohne Einsatz**:
die Spur fuehrt Runden in Punkten, die Gebuehr ist dort nicht abziehbar, und
die Live-Freigabe basierte auf einer Zahl, die die Kosten nie sah. Dann ist
die Rechnung `f_max` (Kosten-Wendepunkt) gegen die gesetzte Gebuehr je Runde
der Beleg - liegt die Gebuehr um Groessenordnungen darueber, ist die
Ruecknahme die ehrliche Antwort, nicht eine Formalie.

## 2. Wo ein Tor gehoert: VOR der Order, nicht in die Signallogik

Jedes Tor gehoert an die Stelle, an der die Order wirklich entsteht:

- `spur_buch.sperren_live()` fuer die Buch-Spuren
- der Orderweg-Adapter der Spur (`markt_kauf` / `markt_verkauf`)
- der asynchrone Executor, falls einer laeuft

**Nicht** in die Signalberechnung. Eine Spur, die ein Signal sieht und es
nicht handelt, sieht fuer tot aus: eine Stillstands-Wache meldet sie als
tot, ohne zu wissen warum. Am Tor wird der Einstieg abgelehnt und
protokolliert - die Spur laeuft weiter und sieht gesund aus.

**Und niemals nach der Order.** Ein Gatter, das hinter `markt_kauf` steht,
ist bei Live genau einen Zyklus zu spaet: die Order ist schon draussen.
Der Anker ist die **Schleife ueber die Kandidaten**, nicht die Stelle, an
der das Buch-Dict entsteht.

## 3. Vier Bedingungen fuer eine belastbare Freigabe

1. `runden >= 8` - darunter ist jede Zahl eine Behauptung
2. `runden_mit_basislinie >= 8` - ohne Basislinie gibt es keinen Excess,
   nur einen Rundendurchschnitt
3. `excess_nach_gebuehr > 0`, wobei `excess` = Rundenergebnis **minus
   Marktbewegung im selben Fenster** (BUY & HOLD desselben Instruments).
   Die Gebuehr kommt aus `gebuehr_toder_taker` der wachen und ist der
   Anteil **je Seite** - eine Runde ist Kauf + Verkauf und kostet das
   Doppelte
4. **kein Befund im Audit.** Eine Spur mit einem Befund ist nicht gemessen,
   sondern beanstandet. Ohne diese Bedingung segnet das Tor die groesste
   Zahl im Haus ab, weil die groesste Zahl die mit dem groessten Rechenfehler
   ist.

Eine Spur **ohne Auditrundlage** wird nicht gesperrt, sondern als
unbewiesen behandelt. Ein Torschutz, der wegen seiner eigenen
Unkenntnis schweigt, waere derselbe Fehler.

## 4. Der Deckel bindet neue Einstiege, nicht Bestehendes

Ein Basis-, Positions- oder Risikodeckel sperrt **neue** Einstiege.
Bestehende Positionen laufen weiter bis Stop oder Ziel.

Eine bestehende Position zu schliessen ist eine **Order** und gehoert in
die Freigabekette wie jede andere. Ein Deckel, der zwangsverkauft, ist ein
Abschaltknopf mit anderem Namen.

Der Deckel wird bei null angelegt: Wer eine Basis einmal ueberschreitet,
hat sie schon bezahlt. Ein Deckel, der beim Start sofort zwanzig Spuren
einfriert, ist kein Deckel.

## 5. Synonyme gehoeren zusammen, sonst ist das Tor ein Loch

Bevor ein Deckel oder eine Gruppierung traegt: **alle Schreibweisen
derselben Basis zusammenfassen.** Fuenf Namen, ein Deckel.

Bekannte Synonyme im Haus: `XBT` = `BTC` (Kraken), `BTC-USD_UM_XPERP-*` =
`BTC-USDT-SWAP`, `BTC-USDC` = `BTC-USDT`. Ohne die Zuordnung sperrt der
Deckel `BTC-USDT-SWAP` und laesst `XBT-USD` durch - **ein Deckel, den man
mit einem anderen Namen umgeht, ist kein Deckel.**

Die Gegenprobe dazu: die alte (falsche) Formulierung in einem Test
nachbauen und zeigen, was sie bewirkt haette.

## 6. Ein Ausfall darf nie wie eine Messung aussehen

Das ist der teuerste Fehler der ganzen Kette.

Ein leeres Ergebnis - leere Marktliste, leere Antwort, kein Kurs - ist ein
**Ausfall**. Wird er als Sachverhalt gemeldet ("diesen Markt gibt es
nicht"), ist die Wirkung doppelt: die Spur steht still **und** das
Instrument wird dauerhaft gesperrt, sobald der Abruf einmal gehetzt hat.

Merksatz: **Ein Ausfall ist kein Befund, sondern eine Luecke.** Beim
Auffinden trennen: leere Liste -> Abbruch mit Grund; vollstaendig gelesene
Liste ohne den gesuchten Eintrag -> "gibt es nicht".

Zwei Zusatzregeln, die sich daraus ergeben und teurer sind als der Grundsatz:

- **Ein Fehler aus einem laufenden Hintergrundvorgang beweist den Zustand
  nicht.** Erst den Prozess beenden, dann die Datei lesen; ein Fehler, der in
  einem ganzt sekundenfenster entstandenen Lauf auftrat, kann eine halb
  geschriebene Datei beschreiben. Zurueckgenommen werden muss die Behauptung,
  nicht der Vorgang.
- **Ein Wert, der bei ALLEN Kandidaten fehlt, ist fast immer der Schluessel und
  nie der Markt.** Ein Werkzeug, das ein Feld liest, das es nicht gibt, liefert
  fuer alles `None` - und `None` sieht aus wie eine Eigenschaft der Daten.
  Belegt wird das dadurch, dass man das Feld gegen den Schluessel des
  Aufrufers prueft, nicht durch eine Vermutung ueber die Daten.

## 7. Der Rueckgabewert eines Tors ist Teil des Vertrags

Ein Gate gibt **immer denselben Wert auf beiden Wegen** zurueck. Ein
Bool auf dem einen Weg und ein String auf dem anderen, geprueft mit
`is not` gegen einen Konstante, sperrt jeden Pfad, der den anderen nimmt -
in der Praxis: **jede Spur, die das Feld nicht gesetzt hat.**

```
if wert != ERLAEUT:        # ERLAEUT ist ein String
    return True             # ... und hier ein bool zurueckgeben
```

Test zuerst schreiben: `flag_aus_lasst_immer_durch`. Ein Gate, das nur im
aktiven Zustand getestet ist, ist ungetestet.

## 8. Signal ausloesen, Zeit nicht: der Trennungsbau

Wenn Ein- und Ausstiege **indikatorindiziert** laufen sollen und die
regelmaessige Pruefung nur Positionen und Signale ueberwachen soll:

1. Die Spur prueft wie bisher (offene Positionen, Stop, Ziel, Signale)
2. Bei **Wechsel** der Signalrichtung schreibt sie einen Auftrag in eine
   Queue und handelt **nicht selbst** (`continue`)
3. Ein asynchroner Executor, unabhaegig vom Takt, liest die Queue und
   handelt

Der Vergleich liegt im Zustand (`vor_signal`), damit dasselbe Signal nicht
jeden Takt erneut feuert. Der Exit-Anker sitzt `zusatz_ausstieg`:
gefragt wird **nach** Stop und Ziel, damit ein gerissener Stop Vorrang hat.

Der Executor muss **alle** Queues des Hauses fahren. Eine fest verdrahtete
Spur raeumt eine von dreizehn ab.

## 9. Jede laufzeitdatei einer Spur ist stufenfaehig

Basis, mittel und hoch fahren dieselbe Spur mit **eigener** `vor_signal`
und eigenem Zustand. Eine Datei mit **festem** Namen sammelt alles in
eine Queue: gemessen drei Eintraege in acht Minuten, je Instrument dreimal
derselbe Wechsel.

Dieselbe Regel gilt fuer die Merksdatei einer Wache: `risikostufe.datei()`
oder ein Suffix je Stufe, sonst meldet eine Stufe das Echo der anderen.

## 10. Eine Warteschlange ist ein Briefkasten, kein Protokoll

Faellt niemand sie ab, waechst sie unbegrenzt.

- Eintraege aelter als eine halbe Stunde **verfallen** - der Markt ist
  weiter, und ein alter Auftrag ist Ballast
- die Liste ist **begrenzt** (zwozig echte Wechsel reichen)
- **jeder** Zweig schreibt die Datei neu, auch der, der den Auftrag
  liegen laesst - sonst bleiben die abgelaufenen Eintraege fuer immer
  stehen, weil der Filter nur aus der Rueckgabe arbeitet

## 11. Merksdateien speichern Primitive, keine Tupel

`json` schreibt Tupel als Listen und laesst sie als Listen zurueckkommen.
Ein Vergleich `"%s|%s" % eintrag` passt danach **nie**, und die Meldung
kommt bei jedem Lauf wieder. Genau so wird eine Wache abgeschaltet und
damit blind.

## 12. Ein Torschutz wird erst beim Setzen der Merksdatei zum Torschutz

Der erste Lauf einer neuen Wache meldet den **gesamten Bestand**, weil
ihre Merksdatei bei null steht. Das ist kein Fehler im Werkzeug, es ist
fehlender Startzustand - und der ist in einem echten Haus eine
Entscheidung: ab welchem Zaehlstand "neu" gemeldet wird.

Wer eine Wache aufruft, **setzt die Merksdatei auf den Iststand**, sonst
spielt die Historie nach.

## 13. Eine Wache meldet eine VERAENDERUNG

Schwellwerte sind Zahlen und keine Schluesselwoerter. Eine willkuerlich
gesetzte Grenze verfehlt den Befund knapp daneben - dann gilt: **die drei
groessten immer melden** und die Schwelle zusaetzlich. Die Frage "auf was
liegt das meiste" faellt auch dann an, wenn die Antwort knapp unter der
Schwelle liegt.

## 14. Tests pruefen die Regel, nicht den Stand

Ein Test, der eine feste **Anzahl** (Spuren, Eintraege, Positionen) oder
einen festen **Wert** einfriert, meldet Aenderung statt Fehler und geht bei
jeder Erweiterung kaputt.

Stattdessen:

- **keine Phantomfaelle**: die Wache darf nichts melden, was es nicht gibt
- **keine stumme Faelle**: wo eine Warteschlange liegt, muss die Wache die
  Spur kennen

Und der **Weg** zaehlt: `spur_buch` ruft `signal(daten[inst], w)` und
uebergibt damit die **innere** Map. Eine Funktion, die dort im aeusseren
Dict nach `symbol` sucht, rechnet nie - und sieht vollstaendig gesund aus.