# Tests und Auswertung einer Spur

## Tests richtig aufrufen

Die Sammlung laeuft aus dem SPURENORDNER heraus, nicht aus `tests/`:

    cd Agenten/Handel/<spur> && <venv-python> -m unittest discover -s tests -t . -p "test_*.py"

`-t .` gilt, wenn `tests/` ein `__init__.py` hat (orb, orbk); ohne
`__init__.py` scheitert es mit `ImportError: Start directory is not importable`,
dann ist `-s tests -t tests` (mit `PYTHONPATH=.`) der richtige Aufruf — die
Meldung sieht wie ein Code-Fehler aus, ist aber die Aufruf-form.

**„Ran 0 tests / NO TESTS RAN" ist das gefaehrlichste Testergebnis.** Es liest
sich wie ein gruener Lauf und ist keiner: unittest sammelt `TestCase`-Klassen
und `unittest.TestCase`-Erben, NICHT blosse Funktionen. Eine pytest-Stil-Datei
mitten im Baum (`def test_…` auf Modulebene, kein `import pytest` noetig) wird
vom unittest-Lauf uebersehen — und meldet das mit Exit-Code 0. Gemessen an
`Bus/tests/test_anbindung_handel.py`: `discover -s tests`, `discover -s tests
-t tests` und `discover -t tests` fanden alle null, es waren aber vier echte
Pruefungen, deren Bestehen eine ganze Verdrahtungsklasse traegt. Zwei Wege
zurueck: die Datei mit pytest fahren (im venv fehlt es haeufig, dann
`No module named pytest` sagt der Aufruf deutlich) oder die Funktionen direkt
aufrufen — Modul laden, je `name.startswith("test_")` `getattr(m,n)()`.
Merksatz: **eine Zahl „0 Tests" wird nie als Bestand gelesen.** Erst die Anzahl
mit der Zahl Testfunktionen im File vergleichen, dann ueberhaupt von gruen reden.

Aufrufe, die scheitern und dabei nach einem Code-Fehler aussehen:

- **Einzelne Testdatei** (`cd <spur>/tests && … -m unittest test_<name>`):
  `ModuleNotFoundError: No module named 'handeln'/'session'` — die Spurenmodule
  liegen eine Ebene hoeher, die Sammlung legt sie auf den Pfad, der Einzelstart nicht.
- `-m unittest tests.test_<spur>` aus dem Spurenordner: der Modulkopf schiebt
  `scanner/` und `HANDEL` auf `sys.path`, und je nach Reihenfolge gewinnt
  `scanner/handeln.py`. Symptom: `AttributeError: module 'handeln' has no attribute
  'pruefe_einstieg'. Did you mean: 'pruefe_einstiege'?` — der Test laeuft, prueft
  aber ein fremdes Modul. Bei dieser Meldung ZUERST `handeln.__file__` ausgeben
  lassen, bevor der eigene Code verdaechtigt wird.
  **Und der Fix im Testmodul selbst: `sys.path.insert(0, p)` OHNE die Bedingung
  `if p not in sys.path`.** Die Bedingung sieht vorsichtig aus und ist genau der
  Fehler: hat eine Nachbarspur `HANDEL`/`scanner` schon eingetragen, bleibt der
  EIGENE Spurenordner hinten stehen und `import handeln` holt weiter das fremde
  Modul — die REIHENFOLGE der `insert`-Aufrufe entscheidet, nicht die Absicht. Die
  eigene Spur zuletzt einfuegen (dann liegt sie vorne) und die Annahme im
  Testmodul absichern: `assert h.__file__.startswith(SPUR)`. Ein zweites Signal:
  meldet dieselbe Suite nach dem Fix ploetzlich MEHR Tests als vorher, hat sie
  vorher ein fremdes Modul geprueft (dessen Testklassen fehlten).

**Zwei Fehlschlaege sind VORBESTEHEND und trotzdem kein Befund.** Bevor eine
Suite-Fehlermeldung der eigenen Aenderung zugeschrieben wird, die Testdatei
selbst lesen:

- Ein festes `JETZT`/`jetzt` im Modul, das weit in der VERGANGENHEIT liegt,
  waehrend der gepruefte Code gegen `datetime.now()` rechnet — das Fenster
  (Stunden) ist dann laengst gerissen und der Test kann den gepruefen Fall gar
  nicht mehr herstellen. Er heilt nur, wenn die Uhr wieder passt.
- Eine Annahme, die eine BETRIEBSAenderung ueberholt hat: erwartet der Test
  eine offene Frage (`anfrage_offen()`), die ein spaeter eingebauter
  Automatismus sofort bestaetigt, ist der Test falsch und nicht der Code. Solche
  Stellen im Bericht als vorbestehend benennen (mit Grund), statt sie zu
  „reparieren" — sie gehoeren der Sitzung, die den Automatismus gebaut hat.

## Ein Fehlschlag aus der vollen Suite: erst zuordnen, dann fixen

Eine Suite ueber hunderte Tests meldet beim ersten Lauf meist mehr rote Punkte,
als die eigene Aenderung verursacht hat. In DIESER Reihenfolge zuordnen - jeder
Schritt ist billiger als der naechste:

1. **Die Testdatei ALLEIN fahren**, bevor irgendetwas geaendert wird. Ist der Test
   im Einzellauf gruen, war der Fehlschlag ein Lade-/Lastartefakt (Reihenfolge der
   `sys.path`-Eintraege, geteilter Modulzustand zwischen Testdateien), kein
   Regressionsbefund.
2. **Den BETREFF des Fehlschlags gegen die eigene Aenderung halten.** Faellt er an
   einem Modul, das man nicht angefasst hat (doppelter Modulname im Baum, fremde
   Datei), gehoert er im Bericht als fremd benannt; bei Verdacht auf ein
   gleichnamiges Modul `modul.__file__` ausgeben lassen.
3. **Liest der Test ein ERZEUGNIS, das niemand mehr schreibt?** Altersgrenzen
   („Bericht 34,5 h alt, Grenze 26 h") schlagen zu, wenn der Erzeuger nicht lief -
   das heilt mit einem frischen Lauf und ist kein Codefehler.
4. Erst wenn 1-3 den Fall nicht erklaeren: die eigene Aenderung stashen und
   gegenproben (SKILL.md, Prozedur Schritt 4).

Merksatz: „Suite rot" ist keine Aussage ueber die eigene Aenderung. Zu jedem
Fehlschlag gehoert im Bericht ein Satz, WARUM er nicht der eigene ist - sonst
liest der naechste Leser die Zahl als Regression und sucht an der falschen Stelle.

## Tests gegen echte Laufzeitdateien schuetzen: das Modul patchen, das den Pfad BESITZT

Ein Test, der die Pfad-Konstante des falschen Moduls patcht, liest still die
ECHTEN Laufzeitdateien — er haengt am Bestand statt an seinem Fixture. Wandert
eine Spur-Funktion in ein anderes Modul (z. B. `spur_spiegel` nach `lage.py`,
tagesbericht re-exportiert nur noch), patcht der alte Test weiter
`tagesbericht.HIER` — die Funktion baut ihren Ordner aber ueber das `HIER` des
Moduls, in dem SIE definiert ist, und liest das echte Journal. Eine
hartkodierte Erwartung ("1 Ausstiege") faellt dann nach ein paar Tagen
Dauerlauf ("875 Ausstiege"), schlimmer: eine falsche Erwartung kann gegen
Live-Daten gruen bleiben.

Regel: **vor dem Patch nachsehen, wo die Funktion ihren Pfad wirklich aufbaut**
(Modul-Konstante, nicht Funktionsargument), und das besitzende Modul patchen
(z. B. `patch.object(lage, "HIER", t)` ZUSAETZLICH zu tagesbericht). Eine
hartkodierte Zeilenzahl im Test ist nur gueltig, wenn das gelesene Journal
nachweislich das Temp-Journal ist — im Zweifel die Pfad-Konstante pruefen, die
der Test-Code durchlaufen muss. Erkennungszeichen, dass ein Test am echten
Bestand haengt: die Erwartung nennt eine Zahl, die mit dem Dauerlauf waechst.

## Ausstiegsrechnung: zwei Fehler, die jede neue Spur aus der Vorlage erbt

1. **G/V auf den NOMINALWERT, nicht auf den Kurs.**
   Richtig: `gv = nominal * (kurs - einstieg) / einstieg * vz`, `erloes = nominal + gv`.
   Falsch und unauffaellig: `gv = (kurs - einstieg) * vz` — die rohe Kursdifferenz.
   Bei BTC ist das ein Faktor in Zehntausenden: aus 100 USD Nominal und 3 % Gewinn
   wird ein „Erloes“ in Kurshoehe. Erkennungszeichen im Journal: Erloes > Einsatz x 3
   ohne Hebel. Jede Spur braucht einen Test, der 3 % Kursgewinn bei 100 USD Einsatz
   auf +3 USD festnagelt (Gegenprobe: die alte Formel ergaebe hier +3000).
2. **Nur Positionen des EIGENEN Instruments pruefen.** `pruefe_ausstiege(z, k, w)`
   bekommt `k` — die Kerzen eines Instruments — und lief ueber alle Positionen; eine
   SOL-Position wurde so mit dem BTC-Kurs bewertet. Signatur
   `pruefe_ausstiege(z, k, w, nur=None)` und in der Schleife
   `if nur is not None and p.get("inst") != nur: behalten.append(p); continue`,
   Aufruf mit `nur=inst`.

Ein verdorbenes Journal NICHT loeschen: als
`handelsjournal.falsch-skaliert-JJJJMMTT.csv` daneben legen und leer neu starten —
die Spur legt die Datei beim naechsten Schreibvorgang selbst mit Kopfzeile an
(`journal()` prueft `not os.path.exists`). Die offenen Positionen in `zustand.json`
sind davon nicht betroffen: falsch war nur die Ausstiegsrechnung.

## Anschluss an die Auswertung

In `auswertung_alle.py` sind drei Stellen zu bedienen, sonst bleibt die Spur
unsichtbar oder stumm:

1. `SPUREN` um die Spur erweitern (steuert `--spur` und die Uebersicht),
2. eine `runden_*`-Funktion fuer ihr Journal-Format,
3. der Zweig in `kennzahlen_fuer()` — DAS ist der eigentliche Anschluss: ohne ihn
   faellt die Spur in den leeren `else`-Zweig und `/strategien` meldet „keine
   geschlossene Runde“, obwohl Zeilen im Journal stehen.

`/strategien` in `befehle.py` ruft `aa.kennzahlen_fuer(spur)`; Spuren mit eigenem
`auswertung.py` stehen in `EIGENE_AUSWERTUNG`. Kosten nur behaupten, wenn sie in der
Zeile stehen — fuehrt die `wachen.json` kein `gebuehr_taker`, ist `kosten = 0` und
nicht geschaetzt.

Muster fuer den Test: `Agenten/Handel/tests/test_indikator_auswertung.py` —
synthetisches Journal schreiben, per `csv.DictReader` einlesen, `runden_*` direkt
aufrufen (kein Netz, kein Lauf, kein Schreiben in echte Pfade).

## Was eine Kennzahl tragen muss: die Gebuehren-Grenze

Eine Trefferquote ohne die Gebuehr sagt nichts. `Agenten/Handel/kosten_wendepunkt.py`
rechnet je Buch die Gebuehr, ab der die Spur nur noch die Nullinie trifft:

    f_max = p*C - (1-p)*R

R = mittlerer Abstand Einstieg→Stop, C = mittlerer Abstand Einstieg→Ziel,
p = gemessene Trefferquote, f = Gebuehr JE RUNDE (Kauf + Verkauf, in Prozent des
Einsatzes). Drei Regeln, die dabei gelten:

- **Zwangsschluesse zuerst ausschliessen — in JEDEM Zaehlwerkzeug.** Runden zaehlen
  heisst: `stoerungen.ist_stoerung(grund)` fragen (Waechter-Reaktionen UND
  Buchhaltungs-Korrekturen), genau wie `auswertung_alle.kennzahlen` es tut. Ein
  Zwangsschluss sitzt meist im Verlust und macht die Trefferquote kuenstlich schlecht:
  gemessen an einer Spur, deren acht Buchzeilen ALLE `herzschlag` trugen — sie stand
  damit als „8 Runden, 25 % Treffer, nicht tragfaehig“ in der Tabelle und in einer
  Notiz, obwohl sie gar keine Messung hatte. Neue Auswertungen immer gegen ein Buch
  pruefen, das nur Zwangsschluesse enthaelt: dort muss „keine messbare Runde“ stehen.
- **Je JOURNAL zaehlen, nicht je Ordner.** Ein Spurenordner fuehrt mehrere Buecher
  (Basis/Mittel, knapp/weit, futures); ein Sammel-glob ueber
  `handelsjournal*.csv` zaehlt dasselbe Buch mehrfach und mischt Varianten.
  Umskalierte Altbestaende (`.falsch-skaliert-*`) gehoeren in KEINE Kennzahl.
- **Unter 8 Runden ist die Zahl ein Befund, keine Messung** — dieselbe Schwelle
  wie in der Uebersicht, und der Grund, warum ein „100 % Treffer“ aus zwei
  Runden nichts ueber die Spur sagt.
- **Runden sind nur so gut wie ihre Risikobreite.** Ein Buch mit ~0,5 % breiten
  Runden kann nur ohne Gebuehr bestehen (0,4 % Runde = fuenfmal der Vorteil);
  steht die Gebuehr nicht in der `wachen.json`, ist sie 0 und die Spur rechnet
  zu freundlich. Faellt ein Gebuehrenrabatt weg, zuerst diesen Wert zuruecknehmen
  — nicht die Trefferquote neu deuten.

## Eine Anzeigezeile ist ein Pruefgegenstand, kein Formatierungsrest

Jede Zeile, die eine Kennzahl zeigt, gehoert in eine EIGENE Funktion
(`tagesbericht.livezeile()`, `rundenzeile()`, `stufenzeile()`, `buchzeile()`). Nur
dann ist sie ohne Netz, ohne Berichtslauf und ohne echten Spurordner pruefbar: der
Test gibt eine GEFAELSCHTE Lage hinein (`{"buchlage": "belastbar", "schluessel":
"scanner", "waehrung": "USD", "kennzahlen": {...}}`) und prueft die REGEL, nicht den
Tageswert. Eine Zeile, die im Inneren einer Schleife entsteht (`_baue`), kann das
nicht — ihr fehlender Zusatz faellt erst dem Leser am Telefon auf, und der sieht
dann nur die Haelfte der Wahrheit.

Zwei Tests je Zeile, beide kurz:

1. Regel gegen gefaelschte Lage — je Zweig einer (`belastbar` mit und ohne
   Ausnahmen, `zu_wenige_runden`, `kein Buch` mit/ohne Datum, kein Schluessel =
   keine Zeile).
2. Regel gegen das ECHTE Buch, ohne Tageswert: `k = auswertung_alle.kennzahlen_fuer(spur,
   von=..., bis=...)` holen und bedingt pruefen (`if k.get("n_stoerung"):
   assertIn("ohne Handelsentscheidung", z)`). Der Test bleibt gruen, wenn sich die
   Zahlen bewegen, und wird rot, wenn der Zusatz verschwindet.

Merksatz: eine richtige Rechnung ist kein Schutz gegen eine irrefuehrende Anzeige.
Wer eine Kennzahl prueft, stellt ZWEI Fragen — rechnet sie richtig, und nennt sie,
was sie weggelassen hat?

## „Kein Journal“ ist zuerst ein WARTEN, kein Fehler

Mehrere Spurvorlagen schreiben **nur Handelszeilen**, keine Zykluszeile (das
Spur-Buch ebenso: `spur_buch.zyklus` journalt erst beim Einstieg). Ein fehlendes
Journal heisst dort „hat noch nichts gekauft“ — erst wenn die Spur AUCH nicht
mehr laeuft, ist es ein Betriebsfehler. Die Auswertung unterscheidet das an der
Aenderungszeit von `zustand.json` (heute/gestern = laeuft) und meldet die Faelle
getrennt; eine Sammelmeldung „Betriebsfehler“ fuer eine wartende Spur schickt die
naechste Sitzung auf eine falsche Fehlersuche.

## Die Uhr im Test: fester Bezugspunkt nur, wo er auch ankommt

Ein Test mit festem `JETZT` ist nur an seinem eigenen Tag gruen. Zwei Faelle
sind zu trennen — der Unterschied hat am 21.09.2026 zwei Fehler in der
Handel-Suite verursacht, die tagelang wie echte Regressionen aussahen:

1. **Reine Funktionstests** (`vf.pruefe(..., JETZT)`) duerfen ein festes JETZT
   benutzen — sie uebergeben es der geprueften Funktion, also muss auch das
   synthetische Journal gegen dieses JETZT geschrieben werden
   (`journal(..., jetzt=JETZT)`).
2. **Einbautests**, die durch die halbe Kette laufen (`buch.einstieg()` →
   `risikovorfilter` → `datetime.now()`), bekommen das feste JETZT NICHT
   durchgereicht. Dort muss der Helfer die ECHTE Uhr nehmen, sonst liegt das
   synthetische Journal ausserhalb des Zeitfensters und der Filter greift
   nicht — der Test faellt, obwohl der Code stimmt.

Dritte Form derselben Klasse: ein Test, der eine Frage offen erwartet, die
der Code inzwischen automatisch bestaetigt (`dauerlauf.AUTO_FREIGABE` seit
20.09.2026). Solche Politik-Schalter im `setUp` stilllegen und im `tearDown`
zuruecklegen — sonst prueft der Test eine Lage, die es nicht mehr gibt.

Regel: einen Test nie an die Wanduhr oder an einen Kalendertag binden, und
jeden Schalter, den der Test stilllegen muss, ausdruecklich sichern und
zuruecklegen.

## Ein Messwerkzeug mit Attrappen-Naht: zwei Fallen

Ein Kopf-Werkzeug unter `Agenten/Handel/`, das eine Boersenantwort BRAUCHT
(Paartabelle, Kursliste, Kontostaende), bekommt einen Seam, damit der Test ohne
Netz laeuft. Zwei Dinge brechen dabei still:

- **Ist der Seam ein AUFRUFBARES (`abruf()`), faellt ein blankes dict-Fixture um**
  (`'dict' object is not callable`). Im Werkzeug normalisieren
  (`return abruf if callable(abruf) else (lambda: abruf)`), dann darf der Test die
  Antwort direkt hinlegen. Ohne Normalisierung schreibt jeder Test `lambda: ATT`,
  und wer es vergisst, sieht einen Typfehler statt einer Messung.
- **Ein neuer OPTIONALER Parameter gehoert ans ENDE der Signatur.** Wird er in der
  Mitte eingefuegt, rutschen die vorhandenen POSITIONELLEN Aufrufer still in den
  falschen Slot: die Funktion laeuft durch und liefert ein LEERES Ergebnis — das
  Werkzeug meldet dann „nicht messbar" statt eines Fehlers, und die Ursache steht
  nirgends. Hinten anhaengen oder den Aufrufer auf Keyword umstellen und nach
  jeder Signaturaenderung die Aufrufer greppen (`grep -n "<funktionsname>("`),
  statt sich auf die Tests zu verlassen — ein Aufrufer ohne Test faellt sonst
  niemandem auf.

**Und die Attrappe muss den POSITIVEN Fall enthalten.** Ein Fixture, das nur den
Normalfall abbildet, laesst die Gegenprobe („hier MUSS etwas gefunden werden")
gruen durchlaufen, ohne etwas zu pruefen: das Instrument, das „nur in der anderen
Waehrung erreichbar" sein soll, braucht im Fixture wirklich KEIN Paar in der
eigenen Waehrung — sonst bestaetigt der Test die Regel mit einem Datensatz, der
sie gar nicht beruehrt. Der Fehlschlag der Gegenprobe zeigt dann nicht den Code,
sondern das Fixture.

## Zwei GEGENPROBEN, die zeigen, dass der Test die Regel trifft

Ein Test, der nur den gewuenschten Pfad beschreibt, beweist, dass der Code laeuft
— nicht, dass er die Regel erfuellt. Zwei gebaeufige Faelle, in denen die Suite
gruen ist und der Fix wirkungslos war, lassen sich mit derselben Technik tragen:
**die Regel im Produktionscode entfernen** (Filter, Sperre, Haken) und dieselben
Tests erneut fahren. Faellt die Suite nicht, prueft der Test den Zustand oder den
Aufruf, nicht die Entscheidung.

- **Zwei unabhaengige Regeln = zwei Gegenproben**, auch wenn eine Zeile Code sie
  enthaelt: dort zwei Tests (Deckungsfilter entfernt -> rot, Preissperre entfernt
  -> rot) statt einer, weil eine entfernte Zeile beide Treffer verliert und man
  nicht sieht, welche Regel der zweite Test wirklich deckt.
- **Vor dem Entfernen die Datei sichern und danach zurueckspielen**, sonst
  bleibt der gebrochene Stand liegen und der „gruene" Lauf beweist nichts mehr.
  Der Weg ist eine Kopie neben die Datei (nicht nach `/tmp`, nicht nach einem
  fremden Repo-Ordner) und `cp` zurueck, danach derselbe Testlauf gruen — beide
  Laeufe gehoeren in den Bericht.
- **Nur die Regel entfernen, nicht den Aufruf.** Wird der Aufruf mitentfernt,
  faellt der Test an einem `AttributeError` statt an der Behauptung — das sieht
  wie ein Klassenfehler des Tests aus und belegt nichts.

**Und die Attrappen-Form muss zum Leseweg passen.** Produktionscode liest
Boersenantworten per `.get()`; eine Attrappe aus einem Objekt mit Attributen
(`self.d`) laesst jeden Test an `AttributeError: … has no attribute 'get'`
scheitern — an der Attrappe, nicht an der Regel. Solche Fixtures als `dict`
ableiten. Ebenso gehoert zur Attrappe JEDE Methode, die der gepruefte Weg ruft
(`schutz_stops` neben `positionen`): eine fehlende Attrappen-Methode macht die
ganze Datei rot und liest sich wie ein Produktionsfehler.

## Der Seam ist die LADEFunktion, nicht das geladene Modul

Ein Wrapper, der sein Boersenmodul ueber den **Pfad** laedt
(`spec_from_file_location` bei **jedem** Aufruf), hat zwei Instanzen im Spiel: die
importierte (`import kraken_futures`) und die, die der Produktivcode sich selbst
laedt. Ein Patch auf `_roh` der importierten Instanz erreicht die zweite nicht —
der Test laeuft, die Attrappe wird nie benutzt, und der Test misst an der echten
Boerse.

Erkennungszeichen: die Attrappe wird nie aufgerufen, obwohl der Test sie
offenbar einsetzt (`self.rufe` bleibt leer), oder der Fehler kommt aus einem
Modulpfad, den der Test gar nicht angefasst hat.

- **Richtig: die Ladefunktion patchen.** `kp._kf = lambda: kf` — dann bekommt der
  Produktivpfad die Attrappe, und die Antwort je **Pfad** liefern (`/tickers` den
  Kurs, `/openPositions` den Bestand). Eine flache Antwort pro Testfall reicht
  nicht: ein Aufruf trifft mehrere Endpunkte nacheinander.
- **Die Attrappe nimmt `**kwargs`.** `_roh` fuehrt je nach Aufruf `signiert=` und
  `post=` mit. Eine Attrappe mit fester Signatur scheitert an
  `TypeError: unexpected keyword argument` — am Testgeruest, nicht an der Regel.
- **Merksatz:** „meine Attrappe wurde nicht aufgerufen" ist kein Testfehler,
  sondern die Meldung, dass die Naht falsch liegt. Die Frage lautet immer:
  **welche Instanz benutzt der Produktivcode?**

## Gegenprobe: die VORBESTEHENDEN roten Punkte zuerst wegrechnen

Bevor eine Fehlermeldung der eigenen Aenderung zugeschrieben wird, beide Zustaende
mit **derselben** Suite messen und die Fehlernamen differenzieren:

    mit der Aenderung:  FAILED (failures=3, errors=6)
    mit dem HEAD-Stand:  FAILED (failures=3, errors=6)   <- identische Namen
    neu durch mich: []        weg durch mich: []

Das ist billiger als Raten und im Bericht belegbar. Zwei Mittel, beide brauchbar:

- **Regel entfernen, Kopien zurueckspielen:** die geaenderten Dateien sichern, die
  Regel zuruecknehmen, Suite fahren, Kopien zurueckspielen, Suite nochmal fahren.
  Beide Laeufe gehoeren in den Bericht.
- **HEAD-Stand laden, ohne den Arbeitsbaum anzufassen:** `git show HEAD:<pfad>` in
  die Datei schreiben, Suite fahren, dann die eigene Fassung zurueckspielen.
  **Kein `git checkout`** — das ueberschreibt uncommittete Arbeit einer parallelen
  Sitzung und liefert eine Fehlermeldung, die wie ein Dateischwund aussieht.

Merksatz: „die Suite war schon rot" ist eine **Behauptung, keine Messung**, bis die
Fehlernamen beider Laeufe nebeneinander liegen.

## Den Vertrag der Funktion MESSEN, bevor du zusagst

Ein Test, der eine Annahme ueber die gepruefte Funktion trifft, liefert bei
falscher Annahme ein GRUENES Ergebnis ueber eine falsche Behauptung. Drei
Annahmen fielen in einem einzigen Testsatz, alle drei aus dem Kopf statt aus
dem Aufruf:

- **Der Rueckgabewert ist nicht der, den der Name verspricht.** Eine
  Richtungsfunktion liefert `1 / -1`, nicht `"long" / "short"` - der Name der
  Variablen im Aufrufer (`sig`, `seite`) sagt nichts ueber den Typ.
- **Eine Reihenfunktion liefert eine REIHE, keine Zahl.** `sma`/`ema` geben
  eine Liste mit `None` am Anfang zurueck; `reihe[-1]` ist der Wert, die
  Funktion selbst ist keiner.
- **Die Prämisse kann mathematisch falsch sein.** Auf einer linearen Reihe
  laeuft die EMA in die SMA (beide liefern denselben Wert); die Behauptung
  „EMA liegt ueber der SMA" ist dort falsch. Eine faelschliche Praemisse faellt
  nicht als Fehlschlag auf, sie wird zur Behauptung des Tests.

Faustregel: **bevor die erste Erwartung geschrieben wird, die Funktion einmal
mit Beispieldaten aufrufen und Rueckgabetyp und Werte ansehen.** Was der Name
und die Benutzung nahelegen, ist kein Beleg - und im Testkommentar festhalten,
was gemessen wurde (`GEMESSEN: liefert 1 / -1`), damit der naechste Leser die
Annahme nicht erneut macht.

Zwei Faelle derselben Klasse: ein Signalkanal, den die eine Spur als Tupel
entpackt (`seite, _linie = sig`) und die andere als String vergleicht - die
Attrappe muss den gemessenen Vertrag je Spur tragen; und eine **Schwelle aus
der Wachen lesen statt eine feste Zahl setzen** (`mindest_kerzen` unterscheidet
sich je Spur um das Doppelte), weil eine feste Zahl bei der einen Spur den
Weg gar nicht durchlaeuft und der Test dort nichts prueft.

## Ein Pruefskript, das EIN Buchschema annimmt, erzeugt Fehlbefunde

Ein Werkzeug, das ueber alle Spuren laeuft, kann nicht annehmen, dass sie
dasselbe Format fuehren. Zwei gemessene Fehlbefunde:

- **Positionsfelder:** eine Bestandspruefung las `inst`/`einstieg` und meldete
  fuer sieben Positionen „kein Einstieg" - die Spur fuehrt `symbol`/`token`
  und `einsatz_usd`. Der Befund sah aus wie ein Datenverlust und war einer.
  Also: eine Spufe, deren Felder `None` liefert, ist **zuerst ein
  Schemafehler**, bis der Quelltext gelesen ist.
- **Namenslisten sind nicht Spur-Namen:** `lage.HOLER` ist ein Tupel von
  FUNKTIONsnamen (`spur_macd_mtf`), nicht von Spurennamen. Eine Mitgliedschaft
  mit dem Spurennamen meldet fuer jede Spur „FEHLT" und sieht wie ein
  Verdrahtungsloch aus. Vor jeder „fehlt"-Aussage den Container ansehen:
  Tuple, Funktion oder Liste von Funktionsnamen, und die Form der Elemente.

Merksatz: **ein Befund, der ALLE Spuren oder eine ganze Gruppe gleich
verdächtigt, ist fast immer der Befund des Werkzeugs, nicht der Spuren.** Ein
Befund, der eine Spur nennt, pruefen; ein Befund, der alle nennt, das Skript.
