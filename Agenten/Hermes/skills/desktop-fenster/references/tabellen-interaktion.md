# Tabellen filtern und auf mehrere Zeilen wirken

Zwei Bauformen, die immer zusammen mit "die Liste ist unbrauchbar" kommen.
Beide gehoeren in die gemeinsame Tabellenklasse, nicht in jeden Reiter -
sonst benutzt die zweite Liste eine zweite Kopie des Filters.

## 1. Spaltenfilter (Freitext bleibt, eine Spalte kommt dazu)

Ein Freitextfilter allein ist zu schwach, sobald eine **Zahl** die Frage
ist: "welche Spuren haben mehr als 50 % Treffer" laesst sich ueber
`"50"` nicht stellen, denn die Zahl steht in mehreren Spalten.

Bauform: **zwei** Felder neben dem Freitext - ein `Combobox` (Spaltenname,
`state="readonly"`, Werte = genau die Spalten der Tabelle) und ein
Eingabefeld (Bedingung). Plus ein Knopf, der **alle drei** leert; drei
einzeln zu leeren ist eine Klick-Falle.

Die Bedingung ist Freitext mit **drei** Anweisungen, weil eine Zahl anders
verglichen wird als ein Wort:

| Eingabe | Bedeutung |
|---|---|
| `>50` `<0` `>= 8` `<=3.5` `=7` | numerisch |
| `papier` `live` | Teilstring, wie der Freitextfilter |
| leer | keine Bedingung, jede Zeile passt |

**Die Zahl aus dem Text holen, nicht aus der Zelle.** Anzeigen tragen Einheiten
und Vorzeichen: `12,5 %`, `-3,10 USD`, `+2 %`, `1.234,5`, `0,17 EUR`. Eine
reine Funktion extrahiert die erste Zahl und entscheidet ueber Komma und
Punkt nach der Nachkommastellenzahl - **beide** Schreibweisen muessen
gehen, sonst filtert eine Liste still falsch je nach Quelle.

Drei Regeln, die sich beim Bauen bewaehrt haben:

- **Ohne Zahl passt nichts.** `>Papier` wirft die Zeile raus, statt still
  nichts zu finden - sonst haelt der Nutzer eine leere Liste fuer ein Ergebnis.
- **Unbekannte Spalte und fehlende Zelle blenden NICHT aus.** Sie geben
  "passt" zurueck. Ein Spaltenname, den es nicht gibt (Tippfehler, alte
  Tabelle), darf nie eine leere Liste erzeugen.
- **Der Filter sortiert nicht.** Die Reihenfolge bleibt die der Quelle;
  Sortieren macht der Spaltenkopf, das ist eine eigene Sache. Ein Test, der
  eine Sortierung erwartet, beschreibt eine Funktion, die es nicht gibt.

Der Filter gehoert in die `Tabelle`-Klasse und wirkt damit in **allen**
Reitern. Jede Tabelle, die ihn nicht bekommt, ist eine Ausnahme - die braucht
einen Grund im Kommentar.

## 2. Mehrfachaktion auf einer Liste

Wenn eine Aktion auf eine Zeile geht ("Freigeben"), geht sie fast immer auf
mehrere. Bauform:

- `selectmode="extended"` (Strg-Klick). Ohne das gibt es keine Mehrfachauswahl,
  und der Knopf sieht trotzdem so aus, als gaebe es eine.
- **Ein Dialog fuer die Auswahl**, nicht einer je Zeile. Sonst N Dialoge.
- **Nur die Zeilen, fuer die die Vorbedingung gilt.** Ein Eintrag ohne
  wartende Anfrage gehoert nicht in den Dialog: die Frage kann niemand
  beantworten. Die Auswahl vor dem Dialog filtern, nicht danach.
- **Gemeinsame Werte = das schaerfste Minimum.** Bei einer Dauer ist das die
  kuerzeste der Anfragen - sonst bekommt eine 30-Minuten-Anfrage eine Stunde,
  die niemand bestellt hat. Das Minimum ist eine Regel, kein Geschmack.
- **Je Eintrag einzeln ausfuehren, nicht im Buendel**, wenn die Aktion eine
  Sperre je Eintrag nimmt. Ein Buendel verpasst den Rest, wenn der erste
  Eintrag die Sperre haelt.
- **Die Meldung nennt Erfolge UND Misserfolge.** "3 freigegeben | kraken:
  Sperre belegt" ist die ehrliche Zeile; wer drei waehlt und eins scheitert,
  will beides sehen.
- Ein Eintrag, der **wirft**, darf den Vorgang nicht abbrechen - die
  anderen werden trotzdem bearbeitet.

## Zwei Fallen beim Erweitern einer Tabelle

**Die Spaltenliste steht an EINER Stelle.** Steht sie an zweien (Aufbau und
Zellenlieferant), ist eine Erweiterung an der einen wirkungslos - ohne
Fehlermeldung. Bei `ttk.Treeview` ist der Fehler zusaetzlich still: ein
Tuple zu kurz als `values` verliert die hinteren Spalten **ohne** jede
Meldung, die Tabelle sieht nur schmaler aus.

**Ein Test auf eine feste Zellenzahl prueft nichts.** `assertEqual(len(zeile),
7)` meldet jede Spaltenerweiterung als Fehler und jede Kuerzung als Erfolg -
er prueft nicht, ob die Anzeige stimmt, sondern nur, dass sie unveraendert
ist. Richtig ist die **Eigenschaft**: Zellenanzahl == Spaltenanzahl, Spalten
eindeutig, keine leere Ueberschrift. Als Regressionsschutz ist das strenger,
weil es den echten Fehler (Tuple zu kurz) genau dann faellt.

## Messen, was die Liste jetzt hergibt

Ein Filter, der eine leere Liste liefert, ist nicht ungetestet, sondern
**unbekannt**. Der Filter wird mit zwei Werten gefahren, von denen einer
passen und einer nicht passen muss, und die Anzeige nennt beide:
`Auto=ja -> ['xperp', 'moondev_marktlage']`, `Auto=nein -> []`.
