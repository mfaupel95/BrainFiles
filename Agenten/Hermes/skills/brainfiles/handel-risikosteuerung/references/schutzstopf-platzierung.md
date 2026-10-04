# Schutzstopf auf einer bereits offenen Position platzieren

Auftrag: eine Position liegt ohne Stop im Buch. Der Reflex ist, den Stop zu
setzen — der manchmal falsch ist, weil nicht jede Spur mit einem Stop aussteigt.

**Vorher lesen, was die Spur als Ausstieg benutzt.** Ein Stop an der falschen
Stelle ist kein Schutz, sondern eine Behauptung: er feuert genau dann, wenn die
Strategie noch am Arbeiten ist.

## Entscheidung nach Ausstiegsmodell

| Ausstiegsmodell der Spur | Stopplatzierung | Begruendung |
|---|---|---|
| **Gitter / Leiter** | EINE Stufe unter der untersten Leiterstufe | Der naechste Schritt der Strategie ist der KAUF einer tieferen Stufe. Ein Stop ueber dieser Stufe feuert, bevor die Strategie selbst kaufen kann. Unterhalb der Leiter ist die Voraussetzung erledigt, und der Notaus greift genau dort. |
| **Trendfolge / Indikator** | Moeglichst weit (Notaus), Ziel unveraendert | Der Indikator verlaesst die Position selbst; der Stop ist die Grenze des Gedankens, nicht der Ausstieg. Zu nah am Einstieg entscheidet der Stop mit. |
| **Zeitfenster / Frist** | Normaler Stop, aber nie so weit, dass die Frist nie erreicht wird | Wenn die Frist der eigentliche Ausstieg ist, ist der Stop die Nebenrolle — er darf den Ablauf nicht uebernehmen. |
| **Reine Feedsignal-Spur** (`spur_buch`, kein Orderweg) | Normaler Stop wie in der Wachen | Papierbuch: der Stop schuetzt Statistik und Kapitalkurve, nicht eine Boersenposition. Das ist kein Vorbehalt, sondern der Unterschied zwischen Risiko im Papier und Risiko am Markt. |
| **Live-Spur** | Immer, und der Stop ist **an der Boerse**, nicht im Buch | Ein Vermerk im Zustand ist Buchhaltung. Geprueft wird gegen die echten Schutzauftraege, nicht gegen die eigene Liste. |

## Distanz aus der Geometrie ableiten, nicht raten

1. **Geometrie der Spur auslesen**: Stufen, Schrittweite, Einstieg und Ziel der
   betroffenen Position. Aus der Wachen, nicht aus dem Gedächtnis.
2. **Der Kurs liegt meist zwischen zwei Stufen.** Die Leiter um den Einstieg
   herum ablesen und die Frage stellen: *wo liegt die naechste Stufe, auf die
   die Strategie wartet?* Der Stop muss darunter liegen.
3. **Restrisiko gegen das Kill-Budget rechnen.** `Restrisiko = Einsatz ×
   (Stop / Einstieg − 1)`. Der Anteil am Kill-Schalter entscheidet, ob der
   Notaus zulaessig ist — ein Stop, der das Kill-Budget allein frisst, ist ein
   zweiter Kill.
4. **Namen geben.** `stop_art` (z. B. `notaus_gitterunterkante`), Zeitstempel und
   ein Vermerk, WARUM so weit. In der Wachen zusaetzlich ein Schalter, der das
   Verhalten benennt, damit die naechste Position nicht wieder ohne Schutz
   entsteht.

## Vermerk statt Journalzeile

Ein nachtraeglich gesetzter Stop ist **kein Handel**. Er gehoert in den Zustand
und in den Kommentar der Wachen, **nicht** in das Journal. Eine Journalzeile
wuerde in der Auswertung wie eine Transaktion erscheinen und die Kennzahlen
verfaelschen.

## Gegenprobe, die den Auftrag abschliesst

Nach dem Setzen das **Gesamtrisiko des Hauses vorher/nachher** messen. Der
Unterschied muss genau dem erklaerten Betrag entsprechen:

    Gesamtrisiko sinkt um  (Einsatz der ungeschuetzten Position)  −  (Restrisiko)

Jede andere Differenz bedeutet: es wurde mehr als eine Position angefasst, oder
die Rechnung zaehlt etwas doppelt. Beides ist ein Befund, kein Rundungsfehler.