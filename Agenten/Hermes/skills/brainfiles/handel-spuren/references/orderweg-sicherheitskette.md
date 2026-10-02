# Der Orderweg: drei Fehler, die zusammen eine echte Sicherheitsluecke ergaben

Gemessen am 01.10.2026 an `omniquant` auf Kraken Futures (PF_HBARUSD). Alle drei
Fehler sind in EINER Kette aufgetreten und jede einzelne Faelle sah harmlos aus.
Die Boehrse sah am Ende eine Position, die das Haus nicht mehr aufloesen konnte.

## 1. Eine Order MIT Kennung EXISTIERT - "noch keine Fuellung" ist nicht "kein Kauf"

`gefuellte_menge()` las `/fills` sofort nach dem Kauf. Die Boerse hatte noch nicht
gefuellt, also kam ein Bruchteilwert oder 0 zurueck. Der Aufrufer rechnete
`int(0.4)` = **0** und bestellte daraufhin:

* den Schutz-Stop mit `size: 0` -> Kraken: `invalidArgument: 0`
* die Rueckdrehung mit `size: 0` -> **wirkungslos, aber als Erfolg protokolliert**

Ergebnis: 5706 Kontrakte ohne jeden Schutz, und das Journal meldete
"Position wegen fehlendem Stop zurueckgedreht". Es war nie zurueckgedreht.

**Regel:** `gefuellte_menge` gibt `(menge, bestaetigt)` zurueck. `bestaetigt=False`
heisst "Bestaetigung offen", nicht "0 ausgefuehrt". Ein nicht lesbarer Aufruf ist
ebenfalls **kein** Nullbefund - er wird nie zu `0` (Spot: `kraken.gefuellte_menge(txid,
standard=None)`, Futures: eigene Warte-Schleife mit `max(1, int(round(menge)))`,
weil ein Kontrakt die kleinste handelbare Einheit ist).

Trifft genauso die kraken-Spur: dort las der Aufrufer 0, buchte die gefuellte
Order nicht, und die Spur kaufte denselben Wert im naechsten Zyklus erneut
(FILEUR viermal, ~200 EUR fuer EIN Signal).

## 2. Eine Rueckdrehung gilt erst als gelungen, wenn die BOERSE sie bestaetigt

Der Fehler oben macht alles schlimmer: die "Sicherung" hat nichts gesichert und
es stand trotzdem "Erfolg" im Journal.

**Regel:** nach der Rueckdrehung `offene_positionen()` lesen. Ist die Position
dort noch da, ist es **kein** Rollback, sondern eine `SICHERHEITSLUECKE` - und die
gehoert lauten ins Journal, samt der Aufforderung, es von Hand zu klaeren. Ein
Fehlerpfad, der einen Fehler **meldet** und dann so weitermacht, als waere er weg,
ist schlimmer als ein Absturz.

## 3. Ein EINSTIEGS-Gate darf den AUSSTIEG nie blockieren

`live_pf_ableitung` ist ein Freigabepflicht fuer einen **neuen** Markt ("die
Ableitung kostet echtes Geld bei einem Instrument, das der Mensch nie gesehen
hat"). Der Aufrufer las die Modul-Variable, die nur im Einstiegszweig gesetzt
wurde. Im Ausstiegszweig war sie `False` -> `ValueError` bei **jedem** Kursabruf.
Die Live-Position stand zwei Stunden, jede Ausstiegsrechnung scheiterte am selben
Gate.

**Regel:** Freigabe-Pflichten gehoeren zum Einstieg. Der Ausstieg laeuft ueber
`pf_markt(inst, fuer_ausstieg=True)` und darf die Markt-Pruefung gegen
`/instruments` **nicht** umgehen - nur die Freigabepflicht. "Nicht erlaubt zu
eroeffnen" und "darf sich nicht schliessen" sind zwei verschiedene Saetze.

Dasselbe Muster bei der **Marktliste**: sie wurde nur im Einstiegszweig geladen.
Nach Schritt 3 aufgeloest, loest der Ausstieg immer noch nicht, wenn die Liste
fehlt. Beide Wege laden sie - `pruefe_ausstiege()` ruft `markte_laden()` genauso
wie `kaufe()`.

## 4. Buch gegen Boerse ist eine eigene Pruefung, und sie hat eine eigene Fehlerklasse

Am Ende standen drei Orders an der Boerse und eine Position:

```
Boerse:  2771 Kontrakte        <- die Hand des Menschen
Buch:    2935                  <- die Spur
Orders:  2935 (die Spur), 5393 x2 (Waisen aus dem fehlgeschlagenen Lauf)
```

Der Waisen-Stop lag **0,19 %** unter dem Kurs. Ein Move haette 5393 verkauft, von
denen nur 2771 existierten -> Teilfuellung, Rest bleibt liegen.

Gemessen wurde in dieser Reihenfolge: erst alle Orders und Positionen an der
Boerse lesen, **dann** zuordnen, **dann** handeln. Ein Waisen-Stop ist keine
kosmetische Altlast, sondern eine Order, jederzeit ausloesbar.

Der Test dazu prueft die REGEL ("wirkt die Rueckdrehung?") und nicht den Wert -
mit Gegenprobe: ohne die Pruefung schlaegt der Test fehl.

## Merksatz

Ein Ausstiegspfad ist die einzige Code-Stelle, die **immer** funktionieren muss -
und er ist meist die, die am spaetesten gebaut und am seltensten gelaufen ist.
Er braucht keinen Freigabepflicht-Pfad, sondern einen eigenen.