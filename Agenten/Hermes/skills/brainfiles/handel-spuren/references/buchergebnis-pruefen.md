# Ein Buch-Ergebnis prüfen, bevor es als Gewinn gelesen wird

Ausloeser: „Das heisst, wir haetten X gewonnen?" oder eine Bilanz, die gut
aussieht. Ein Papierbuch ist eine MESSUNG, kein Kontostand - jede Zahl hat ihre
Fragen, bevor sie eine Antwort ist (die Reihenfolge unten einhalten): erst
rechnen, dann reden (Beleg: Spiegel-Buch, 13.09.2026: +518 USD, die keiner sind).

## 1. Papier oder Geld?

Kein Zweig, keine Order, kein Cent. Das sagen, BEVOR Zahlen fallen - sonst
liest sich eine Rechnung wie ein Kontostand. Die Bilanz ist ein Saldo aus
Buchzeilen.

## 2. Saldo oder Umsatz?

Die Bilanz summiert ABGESCHLOSSENE Positionen. Was fehlt, gehoert daneben:

- **Offene Positionen:** Anzahl x Einsatz = gebundenes Kapital. Ihr Ergebnis
  steht in keiner Bilanz. Immer mit abfragen (`zustand.json`), nicht wegreden.
- **Der Umsatz ist nicht das Risiko.** 45 Kopien x 50 USD = 2250 USD Umsatz,
  aber das Kapital war nur der Spitzenbestand (`max_offen` x Einsatz = 1000 USD).
  "+518 auf 2250" und "+518 auf 1000" sind verschiedene Aussagen.

## 3. Haengt die Zahl an wenigen Positionen?

Die Gegenprobe, die den Unterschied macht: die Summe **ohne die Top-1, Top-2,
Top-3** rechnen. Spiegel 13.09.: +518 -> +266 -> +187 -> +113 USD aus 45
Ausstiegen. Eine Zahl, die an drei von 45 Positionen haengt, ist eine Aussage
ueber diese drei Positionen, nicht ueber die Strategie.

## 4. Mittelwert ODER Median?

Bei schiefen Verteilungen widersprechen sie sich, und dann gehoeren BEIDE hin:
Mittelwert +23 % je Position, Median -30,8 %, 19 von 45 positiv. Der Median
sagt, was die typische Position tut; der Mittelwert, was die Summe tut. Wer nur
den Mittelwert zeigt, verkauft eine untaugliche Strategie als tragfaehig.

## 5. Was steckt NICHT in der Zahl?

- **Kosten sind eine Annahme je Seite, nicht je Trade gemessen.** Die Annahme
  gilt fuer die Einsatzgroesse, mit der sie gemessen wurde: bei zehnfach
  groesserem Einsatz bewegt der eigene Kauf den Preis, die Slippage waechst
  mit. Die Zahl skaliert nicht.
- **Der Weg dorthin.** Realisierte Verluste fallen VOR den Gewinnern: Spiegel
  26 Stops rund -500 USD, 19 Ziele rund +1045 USD. Ein Konto, das beides
  tragen muss, war zwischenzeitlich ein Drittel bis zur Haelfte im Minus - dort
  haetten echte Leute aufgehoert, und die Ausreisser waeren nie ins Buch
  gekommen. Ergebnisse immer als Verlauf sehen, nicht als Endsaldo.
- **Was ein Papierbuch nie sieht:** fehlgeschlagene Transaktionen, Gas- und
  Prioritaetsgebuehren, MEV/Sandwich, Liquiditaetsgrenzen (der eigene Verkauf
  drueckt den Preis).
- **Kill-Switch-Semantik pruefen: worauf geht er?** Das Spiegel-Buch prueft den
  Ruecklauf der OFFENEN Positionen, nicht die kumulierte Bilanz - realisierte
  Verluste stoppen es nicht. Diese Aussage nie aus dem Namen ableiten, sondern
  im Code lesen.

## 6. Was folgt daraus?

Keine Strategie-Aenderung aus einer Handvoll Positionen. Die Schwellen stehen
im Auswertungsmodul (`MIN_AUSSTIEGE` 8, je Gruppe 5); darunter gibt es Zahlen,
aber keine Empfehlung. Bei Live-Gedanken zuerst pruefen, ob der Bestand
ueberhaupt tragbar ist (Spitzenbindung + Drawdown), nicht die Rendite.

## Werkzeugfallen beim Bauen einer Auswertung

- **Das Journal mit `csv.DictReader` und den Feldnamen aus dem Header lesen,
  nie mit festen Spaltenindizes.** Der Header wandert (24 Spalten hier, andere
  bei anderen Spuren), und ein Index-Offset (`r[17]` fuer `grund`) trifft
  daneben - die Ausgabe sieht dann aus wie „schliessen grund=stop", obwohl die
  Wirklichkeit anders war. Vor dem Filtern `print(header)` und die Namen aus
  der ersten Zeile nehmen; Zeilen mit `z.get("inst")` statt `r[3]` filtern.
- **Eine Ausgabe, die in einer Zeile zusammengefuehrt ankommt („1 lines
  output"), ist kein Journal-Inhalt.** Die Ursache kann ein kaputter
  f-String im eigenen Abruf sein (verschachtelte Klammern, `%`-Formate, ein
  Dict statt einer Zahl) - dann die Ausgabe in einem SCHLICHTEN Lauf erneut
  holen (kein Formatieren, `print(repr(zeile))`), bevor man die Zahlen
  deutet. Zweimal nacheinander dasselbe Merkwuerdige ist ein Lese-Artefakt,
  kein Befund.
- **Nicht jede Journal-Spalte ist eine Zahl.** Ein generischer Lader, der alles
  durch `float()` schickt ("erst als Zahl versuchen"), macht aus
  `kette="solana"` ein `None` - danach liest sich jedes Band als "?". Erst
  Zahl, dann Rohwert behalten.
- **Was die Zielzeile nicht traegt, muss gejoint werden.** Die Schliessen-Zeile
  des Spiegel-Journals traegt keine Marktkapitalisierung (sie steht nur beim
  Eroeffnen) - ohne Join ueber den Token ist die wichtigste Frage ("traegt
  Nachahmen in kleinen Buechern?") nicht nach Band stellbar. Vor dem Bauen eine
  echte Zeile jeder Aktion lesen, nicht das Spaltenschema.

## 7. Wer hat gezaehlt? Mit einer EIGENEN Paarung nachzaehlen

Eine Kennzahl, die ein Werkzeug aus demselben Journal rechnet, ist NICHT
gegengeprueft, wenn man das Werkzeug ein zweites Mal aufruft: derselbe Code
liefert dieselbe Zahl, auch wenn die Zahl falsch ist. Nachzaehlen heisst, die
Runden unabhaengig nachzubauen - eigene FIFO-Paarung je Instrument, eigene
Erloes-minus-Einsatz-Rechnung, ohne die Funktion des Berichts zu importieren -
und erst dann beide Zahlen nebeneinander zu legen. Immer alle drei Felder
vergleichen (Rundenzahl, Trefferzahl, Ergebnis): eine Abweichung in der Zahl,
die man nicht verglichen hat, bleibt sonst stehen.

Weichen die Zahlen ab, ist die Frage nicht „wer hat den Fehler", sondern
„welche Zeilen zaehlt die eine Seite nicht mit". Die Ausnahmen stehen im
Auswertungsmodul, nicht im Journal: Zwangsschluss und Buchhaltungs-Korrektur
fallen aus Rundenzahl und Quote (`stoerungen.ist_stoerung`), waehrend ihre
Buchungen in der Kapitalkurve bleiben. Erst die Zaehlung der GRUENDE zeigt,
welche Klasse fehlt (`Counter(grund)` je Runde) - danach steht fest, ob die
Zahl falsch war oder nur enger definiert als sie gelesen wird. Beides gehoert in
den Bericht: die Zahl, ihre Ausnahmen und die Aussage, ob das Urteil steht.

Und die Trennschaerfe der Ausnahme pruefen, statt sie anzunehmen: `anpassen`
und `buch_nachgezogen_boerse` (Mengenabgleich des Buchs) zaehlen weiter als
Runde, weil `stoerungen.BUCHHALTUNG` nur `buchbereinigung` kennt. Wer die
Definition erweitert, aendert sie fuer ALLE Buecher - das ist eine Entscheidung
von Max, kein Fix nebenbei.
