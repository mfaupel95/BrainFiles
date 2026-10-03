# „Null Runden" - welche Null ist es?

Wann: Die Auswertung meldet fuer eine Spur `keine geschlossenen Runden`, oder die
Frage kommt als „warum hat X 0 Runden, da stimmt doch etwas nicht".

## Der Weg zum Befund: messen, dann einordnen - NIE aus der Rundenzahl schliessen

Der Fehler, der hier am meisten Geld kostet, ist nicht ein falscher Parameter,
sondern eine vorschnelle Massnahme. Die Auswertung zaehlt **GESCHLOSSENE**
Runden. Eine Spur, die heute zwei Positionen eroeffnet hat und deren Stop noch
nicht erreicht ist, steht dort bei null - und sieht in der Tabelle des Berichts
aus wie eine, die nie funktioniert hat.

**Vor jeder Empfehlung, eine Spur stillzulegen oder zu priorisieren, laeuft der
Befund-Lauf und die LAGE wird genannt - nicht die Rundenzahl:**

    cd Agenten/Handel
    scanner/.venv/Scripts/python.exe ../skills/brainfiles/handel-spuren/scripts/null_runden_befund.py

Der Lauf liest nur. Er ordnet jede Spur nach genau dieser Tabelle ein und nennt
die Begruendung mit ("4 Position(en) ohne Ausstieg - je Position pruefen, ob
sie einen Kurs bekommt"). `--alle` zeigt jede Spur, `--nur <n>` verengt auf
weniger geschlossene Runden.

**Eine Bestandsaufnahme ueber die GANZE Flotte, die man ohnehin schon laufen
laesst, ist der Befund-Lauf — wenn man die richtigen Spalten liest.** Zwei
Zahlen genuegen, um jede Null zu sortieren: **Journal-Zeilen** (0 = nie
geschrieben = wartet) und **offene Positionen** (0 = leeres Buch, >0 = die Spur
arbeitet). Wer nach einer solchen Bestandsaufnahme aus der Spalte
„Runden: 0" eine Stilllegungsliste baut, hat die Auswertung gemacht und den
Befund nicht - und der Fehler ist teuer, weil die Liste plausibel aussieht und
Max sie bestaetigt. Geprueft an einem Tag, an dem 13 von 14 zur Stilllegung
vorgeschlagenen Spuren am selben Tag Positionen eroeffnet hatten: die Rundenzahl
war richtig, die Schlussfolgerung genau umgekehrt. Faustregel: **eine Stilllege-
liste entsteht nie aus einer Spalte, sondern aus zwei.**

**Die Reihenfolge der Antworten ist fest:**

1. **BUCH VOLL** - es gibt Positionen. Sie sind der Grund fuer alles Weitere;
   eine Spur mit offenen Positionen wird nie stillgelegt, sondern auf ihre
   Stopps geprueft.
2. **ARBEITET** - Positionen im Buch, Stop/Ziel noch nicht erreicht. Das ist
   Normalbetrieb, kein Befund.
3. **NUR AUSBUECHER** - das Journal zaehlt Buchhaltung, keine Handel.
4. **WARTET** - leerer Journal, keine Position, Zustand frisch.
5. **FEHLT** - keine Ergebnisdatei. Bedingung 4 unerfuellbar, siehe unten.

Merksatz fuer den Bericht: **"0 Runden" ist ohne Lage eine halbe Aussage.**
Wer sie als "stirbt nie" liest, hat die Frage noch nicht gestellt.

## Erst trennen, dann suchen

Eine Null hat fuenf Bedeutungen. In der Auswertung sehen sie gleich aus, es sind
aber fuenf verschiedene Lagen - nur zwei davon sind ein Fehler:

| Lage | Kennzeichen | Fehler? |
|---|---|---|
| wartet auf das erste Signal | Journal leer, keine Position, Zustand frisch | nein |
| arbeitet, Stop noch nicht erreicht | Positionen im Buch, Journal ohne Ausstieg | nein |
| Ausbuecher ohne Handelsentscheidung | Journal nur mit `buchbereinigung`/`herzschlag` | nein (Anzeige!) |
| **Buch voll bei vorhandenen Kandidaten** | Position ohne Kurs, Platz belegt, kein Einstieg | **ja** |
| **Stall** | offene Position, deren Instrument nicht mehr geprueft wird | **ja** |

Merksatz: Eine Null ist erst dann eine Aussage, wenn dabeisteht, was sie zaehlt.
Ein Text, der alle fuenf Lagen gleich beschreibt, versteckt genau die zwei echten
Fehler. Beim Bauen einer Kennzahl die Gegenfrage stellen: welche Zustaende fallen
auf denselben Satz?

## Die fuenfte Lage: die Datei fehlt ueberhaupt

Die Tabelle oben setzt voraus, dass das Journal da ist. Ein im Lauf erzeugtes
Erzeugnis, das erst beim **ersten Schreibvorgang** angelegt wird, ist aber genau
dann nicht da, wenn die Spur noch nie gehandelt hat - und **das Fehlen einer Datei
unterscheidet „noch nie ein Signal" nicht von „das Journal ist kaputt"**. Beide
Laeufe enden in der Zeile `Handelsjournal.csv fehlt`, und beide sehen harmlos aus.

Gemessen: `spur_buch.journal()` legte die Datei erst beim ersten Eintrag an, also
hatten 7 von 38 Spuren gar kein Journal - und damit auch nichts ausser Haus
(Bedingung 4 war fuer sie unerfuellbar, ohne dass irgendwo ein Fehler stand). Der
Befund fiel nur ueber eine Bestandsaufnahme der Dateien, nicht ueber einen Fehler.

**Regel: eine Spur legt ihre Ergebnisdatei im ersten Zyklus an, nicht im ersten
Treffer.** Der Aufruf gehoert VOR die Datenpruefung, sonst gilt er nur auf dem
Weg, der Daten hat:

```python
if modus in ("papier", "live"):
    lege_journal_an(journal_pfad)   # legt die Kopfzeile an, schreibt keine Zeile
```

Drei Bedingungen gehoeren dazu, sonst zieht die Regel den Lesemodus mit:

1. **Leer heisst null Zeilen, nicht null Zeilen ohne Kopfzeile.** Die Datei muss
   ohne Weiteres lesbar sein; deshalb `writeheader()`, nicht `open(..., "w")`.
2. **Die lesenden Modi bleiben lesend.** `--vorschau` und `--wachen` legen nichts
   an — der Dauerlauf fragt jede Spur zusaetzlich mit `--vorschau` ab, und eine
   Vorschau, die eine Datei anlegt, ist keine Vorschau.
3. **Der Schreibschalter des Moduls gilt.** Wo `SCHREIBEN=False` ist (Replay,
   Tests), legt die Funktion nichts an — ein Test darf nie in einen echten
   Zielpfad schreiben.

Merksatz: **eine leere Datei ist ein antwortbares Zeichen, ein fehlendes File
nicht.** Wer beides als „kein Journal" liest, hat die Frage schon falsch
beantwortet, bevor er sie gestellt hat.

Beleg-Nachweis statt Vermutung: `auswertung_alle.offene_positionen(spur)` liest
den Zustand tolerant (fehlende Datei, kaputtes JSON, fehlendes `positionen`-Feld
geben `None`) und `zeige()` nennt die Lage im Klartext - „aber N offene
Position(en) im Buch", „daneben N Ausstiege ohne Handelsentscheidung", „wartet
auf ihr erstes Signal".

## Die Stall-Falle (der teuerste der vier Faelle)

Ein Zyklus, der seine Ausstiege ueber `for inst in w["instrumente"]` faehrt,
verliert jede Position, deren Instrument spaeter aus der Liste genommen wird
(Instrumententausch, Boersenwechsel, Quote-Wechsel USDT -> USDC). Sie wird nie
wieder angesehen, nie geschlossen, belegt den Platz und steht im Buch.

Regel: **Ausstiege laufen ueber Plan + Bestand, Einstiege nur ueber den Plan.**

```python
plan = wp.plan_instrumente(w)              # die Wachenliste
verwaist = wp.verwaiste_instrumente(w, z)  # offen, aber nicht mehr im Plan
if verwaist:
    print("Verwaiste Instrumente ...", file=sys.stderr)   # melden, nie still
for inst in wp.pruef_instrumente(w, z):    # Plan + Bestand
    ...
    if inst in plan:                       # Einstieg bleibt begrenzt
        pruefe_einstieg(...)
```

Die drei Helfer liegen in `scanner/wachen_pruefung.py` und gehoeren dorthin, wo
`wp` schon importiert ist - die Spur selbst wird nicht umgebaut.

## Die Falle eine Ebene tiefer: der Kurs kommt aus der Plan- oder Feed-Liste

Auch eine **Datensammel-Schleife** kann an derselben Verengung leiden. Zwei
Formen, beide enden gleich: die Position bekommt keinen Kurs mehr, `pruefe_ausstiege`
behaelt sie, sie wird nie geschlossen und belegt einen Platz.

1. **Kurse ueber die Planliste.** Die Funktion, die `kurse` baut, laeuft ueber
   `w["instrumente"]` - faellt ein Symbol heraus, verliert seine Position den Kurs.
   Fix: dieselbe Liste wie beim Ausstieg, also Plan + Bestand:

```python
def hole_kurse(w, z):
    verwaist = wp.verwaiste_instrumente(w, z)
    if verwaist:
        print("Verwaiste Instrumente ...", file=sys.stderr)
    for inst in wp.pruef_instrumente(w, z):     # NICHT w["instrumente"]
        ...
```

   Den Aufrufer mitziehen: `hole_kurse(w, z)` statt `hole_kurse(w)`.

2. **Kurse aus dem AKTUELLEN Feed.** Bei Feed-Spuren entsteht `kurse` aus den
   heutigen Kandidaten. Wechseln die Kandidaten taeglich (Top-Movers, Trending,
   Bewertung faellt unter die Schwelle), verliert die Position ihren Kurs,
   obwohl ihr Symbol nirgends gestrichen wurde. Nach dem Aufbau von `kurse` die
   gehaltenen Positionen nachziehen - Vorlage im Haus ist
   `moondev_sniper/handeln.py`:

```python
for p in z.get("positionen", []):
    if p.get("inst") in kurse:
        continue
    try:
        preis = <einzelkurs>(p["inst"])
    except Exception as e:                     # noqa: BLE001
        fehler.append("Preis %s: %s" % (p["inst"], str(e)[:80]))
        continue
    if preis:
        kurse[p["inst"]] = preis
```

   Ein einzelner Kursabruf darf den Zyklus nie kippen (Fehler sammeln, nicht
   werfen) - ein Verbindungsabbruch hat sonst den ganzen Lauf gekostet.

Eine Position ohne Kurs NIE stillschweigend behalten: melden, mit Symbol und
Eroeffnungszeit. Melden allein heilt nicht - der naechste Schritt ist immer der
Einzelkurs-Abruf.

### Die dritte Form: es gibt fuer den gehaltenen Token gar KEINEN Kurs

Die beiden Faelle oben lassen sich durch einen Abruf heilen, weil die Quelle
den Kurs auch fuer eine Position liefern kann, die nicht mehr im Plan oder im
Feed-Kandidaten ist. **Es gibt Quellen, fuer die das nicht gilt**: eine Onchain-
Kette, deren Sammler nur beobachtete TRANSAKTIONEN meldet. Ein Token, den
niemand mehr handelt, hat dort keinen Preis - nicht einen veralteten, keinen.
Dann faellt der Einzelkurs-Abruf leer, die Position bleibt, und weil
`max_offene_positionen` klein ist, ist das kein Ausreisser, sondern ein
Zustand: **das Buch ist voll, es gibt Kandidaten, und es passiert nichts.**
Gemessen: drei Plaetze besetzt, drei Positionen 125 bis 222 Stunden ohne
Beobachtung, ein Kandidat vorhanden, kein Einstieg in Tagen.

Der Einzelkurs-Abruf ist hier die falsche Kur, die meldende Zeile auf stderr
die unmoegliche. Zwei Schrauben, beide noetig:

1. **Die Quelle beantwortet die Frage nach einer OFFENEN Position, nicht nach
   einem Kandidaten.** Auch hier gehoert der Preis in `kurse`, nicht in `daten`
   - ein nachgezogener Kurs darf einen Einstieg ausloesen, den es nie gab.
   Die Einstiegspreise der Kandidaten (mit Nachlauf-Aufschlag) haben Vorrang vor
   dem nackten letzten Handel. Der Leser bekommt dafuer eine eigene Funktion
   mit derselben Form wie die uebrigen: `letzte_beobachtung(con, token)` -
   juengste Fuellung, Kauf ODER Verkauf, ueber Handelsvolumen in Tokens. Bei
   dieser Form ist sie eine TABELLE, keine Regel: ohne sie ist das Neuschreiben
   einer Abfrage, und die landet in `daten`.
2. **Eine Altersgrenze raeumt, was keine Quelle mehr beantwortet.** Position
   offen, letzte Beobachtung aelter als `<grenze>` (Vorgabe 24 h) oder nie
   beobachtet: schliessen. Zum letzten bekannten Kurs, ohne jede Beobachtung
   neutral zum Einstieg. **Der Grund heisst so, dass er unter
   `stoerungen.BUCHHALTUNG` faellt** - das ist eine Buchbereinigung, keine
   Handelsentscheidung, und darf in keiner Kennzahl als Runde mitzaehlen. Ein
   eigener Grundname ohne Merkmal erhaelt eine erfundene Runde, die dann in der
   Trefferquote steht.

Vorschau als eigener Schalter, Anwenden als zweiter (`--raeumen` /
`--raeumen-anwenden`): die Raeumung loest Zeilen im Journal und in allen drei
Risikostufen aus, das gehoert gesehen, bevor es geschieht. Der Nachweis danach
ist dreifach - Buch aller drei Stufen leer, `spiegelstand` byte-gleich, und die
geraeumten Zeilen mit `stoerungen.teile_runden` gegengeprueft (null echte
Runden).

Merksatz fuer die Fehlersuche: **„Buch voll bei vorhandenen Kandidaten" ist
selbst eine Null-Lage.** Sie faellt in derselben Auswertung zusammen mit
wartet / arbeitet / nur Ausbuecher / Stall - und ist die einzige davon, bei der
der Zustand fortbesteht. Bevor eine Spur als wartend eingestuft wird, `kurse`
und `positionen` vergleichen: eine Position ohne Kurs ist immer ein Befund.

## Den Stall in allen Spuren finden (Audit-Rezept)

    cd BrainFiles
    git grep -l '"instrumente"' -- 'Agenten/Handel/*/wachen*.json'
    grep -n 'for inst in\|instrumente' Agenten/Handel/<spur>/handeln.py

Jeden Fund einordnen, bevor etwas geaendert wird - nicht jede Liste ist ein
Fehler:

- **Ausstiegs-Schleife ueber die Planliste** = die Falle, umstellen.
- **Einstiegs-Schleife** ist richtig so (Einstiege bleiben auf den Plan
  begrenzt); eine Spur darf daneben eine solche Schleife behalten.
- **Schleife ueber die Marktdaten des Zyklus** (`for inst in sorted(daten)`) ist
  sicher.
- **Datensammel-Schleife ueber die Planliste oder den Feed** = dieselbe Falle
  eine Ebene tiefer (siehe oben).

Fuer die zweite Form ist der Vergleich der `quelle()`-Funktionen das schnellste
Werkzeug: welche Spur zieht die Preise der gehaltenen Positionen nach und welche
nicht?

## Buchformat und Rechenweg

- **Kein Rechenweg.** Ein Journal fuehrt Aktionen, die der Verteiler nicht kennt
  (Arme buchen `eroeffnen`/`schliessen`, nicht `kauf`/`verkauf`) - Ergebnis ist
  eine harte Null bei vorhandenen Runden. Neues Buchformat heisst immer:
  Rechenweg an der EINEN Stelle nachziehen (`runden_fuer()`), nicht in jedem
  Aufrufer.
- **Fehlender Kurs.** Eine Position ohne Kurs darf nicht stillschweigend
  uebersprungen werden - melden, sonst blockiert sie unsichtbar.
- **Ausbuecher** (`buchbereinigung`, Zwangsschluss) sind zu Recht keine Runden -
  aber dann muss die Anzeige genau das sagen.
- **Feldname beim Verkauf.** Der Erloes steht im SELBEN Feld wie der Einsatz beim
  Kauf (`einsatz_usd`) - ein Test, der `erloes_usd` erwartet, prueft eine
  Annahme, nicht das Journal.

## Ein Test gegen die Zeile meldet Umbau, keine Fehler

Der Test, der eine solche Regel festhaelt, prueft die EIGENSCHAFT: im Quelltext
muss `if inst in plan:` unmittelbar vor dem Einstiegsaufruf stehen - gleich wie
der Aufruf heisst und wie er eingerueckt ist (Muster statt exakter Zeile). Ein
Test gegen eine exakt eingerueckte Zeile oder gegen `inspect.getsource(<eine
Funktion>)` wird bei jeder Verlagerung rot, ohne dass sich am Verhalten etwas
geaendert hat; eine verlegte Zuordnung ist kein Fehler. Ebenso: eine feste Zahl
oder ein Commit-Hash als Erwartung meldet Aenderung, nicht Fehler - pruefe die
Regel.

Und: den ERZEUGER benutzen, nicht ein handgebautes dict. Ein Test, der die
Anzeige gegen ein selbst zusammengesetztes Kennzahlen-dict prueft, prueft die
eigene Annahme - `kennzahlen([...], "USD")` aufrufen und dessen Rueckgabe
verwenden. Sonst ist der Test gruen, weil Annahme und Nachbau gleich falsch sind.

## Nachweis

    cd Agenten/Handel
    scanner/.venv/Scripts/python.exe auswertung_alle.py | grep -A3 "=== <SPUR> ==="
    scanner/.venv/Scripts/python.exe -c "import auswertung_alle as a; print(a.runden_fuer('<spur>'))"

Ein Nachweis ist keine Wache: fuer Spuren, die still stehen sollen, gehoert ein
Cron dazu (Muster `Agenten/Hermes/scripts/spur-wache.py`). Nach jeder Aenderung
an den Buchpfaden zusaetzlich `spiegelstand.py` laufen lassen - die Buecher
muessen byte-gleich nach Q: gespiegelt sein.
