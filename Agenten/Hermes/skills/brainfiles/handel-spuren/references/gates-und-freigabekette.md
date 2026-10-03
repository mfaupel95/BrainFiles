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