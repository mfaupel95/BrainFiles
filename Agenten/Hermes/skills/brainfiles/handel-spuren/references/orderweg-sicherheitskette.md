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

## 5. Ein NEUER Ausfuehrungsweg traegt ALLE Tore selbst

Die vier Schritte oben betreffen den gewohnten Weg durch `sperren_live()`.
Ein Weg, der **ausserhalb** davon ordert - heute der `signal-executor`, der
einen Auftrag aus einer Queue abarbeitet, waehrend der Dauerlauf nur noch
ueberwacht - erbt davon **nichts**.

Beim Bauen geprueft wurden `handel_erlaubt` und `freigabe.erfuellt`. **Nicht**
geprueft wurde das Freigabefenster (`freigabefenster.lade(spur).offen()`), weil
es normalerweise `sperren_live()` erledigt. Bei drei live-faehigen Spuren
haette ein Signalwechsel damit eine echte Order **ohne** Zeitfenster gesetzt -
genau die Luecke, die Handelsregeln Punkt 3 schliesst.

**Regel fuer jeden neuen Ausfuehrungsweg:** jedes Tor der gewohnten Kette
noch einmal auflisten und einzeln beantworten - Freigabe, Freigabefenster,
Schluessel, Demo-Modus, Mindestguthaben, Orderweg vorhanden. **Und ein
Import- oder Lesefehler bedeutet: keine Order.** Ein Weg, der bei Unsicherheit
durchlaesst, ist kein Weg; die Verweigerung ist das sichere Ergebnis, weil
ein liegengebliebener Auftrag spaeter ausgefuehrt werden kann und eine
versehentlich gesetzte Order nicht zurueckgenommen werden kann.

Gegenprobe je Tor, nicht nur am Ende: eine Spur ohne Freigabe und eine
abgeschaltene Spur geben beide `False` zurueck und lassen den Auftrag in der
Queue liegen. Ein Weg, der keine Queue kennt (es gibt keinen Auftrag, der
spaeter nachgeholt wird), gehoert nicht gebaut.

## 6. Eine LEERE Antwort ist kein Befund - sie ist ein Ausfall

Der schwerste Fehler dieser Kette, weil er nicht wie ein Fehler aussieht: aus
einem **Ausfall** wird eine **Tatsache behauptet**.

Eine Spur waehlt ihre Instrumente laufend neu (CoinGecko-Top-Mover). Der Adapter
prueft darum vor jeder Order, ob das Instrument ueberhaupt einen Boersenmarkt
hat - richtig gedacht. Die Marktliste kam jedoch leer zurueck (siehe 6b), und der
Aufrufer las daraus: **„GENIUS hat an der OKX keinen Spotmarkt"**.

Das ist eine erfundene Tatsache. Bei jedem Abrufstoerung waere **jedes**
Instrument als unhandelbar gemeldet worden, und ein Token, das einen Markt HAT,
waere **dauerhaft gesperrt** - wegen eines Netzaussetzers. Ein Ausfall darf nie
wie eine Messung aussehen.

**Regel: die leere Liste und die vollstaendig gelesene Liste sind zwei
verschiedene Saetze.**

- leere Liste (oder nicht lesbar) -> **Ausfall**: `Meldend` mit dem Satz
  „Instrumentliste nicht lesbar"; Ein- und Ausstieg ruht, bis der Abruf wieder
  gelingt. **Keine** Instrument-Aussage.
- vollstaendig gelesen, Paar fehlt -> **Befund**: „kein Markt".

Der Zweig, der nicht ausfuehrt, braucht denselben Aufruf - sonst macht nur der
Ein-, nicht der Ausstigg die Unterscheidung. Und der Test haelt beide fest
(`assertRaises` auf der leeren Liste, `None` auf der gefuellten ohne Paar);
ein Test, der `assertIsNone(boersenpaar(...))` verlangt, **schreibt den Fehler
fest** - genau das stand zuerst drin.

### 6b. Die zwei Ursachen, die die leere Liste erzeugten

Beide sind Delegationsfehler und beide sehen im Bericht aus wie ein
Boersenproblem:

- **Argumentreihenfolge eines Fremdmoduls.** `okx._roh(pfad, methode="GET",
  ...)` - der **Pfad kommt zuerst**. Der Aufruf `_roh("GET", "/api/v5/...")`
  ist nicht falsch aufgerufen, er ist *stumm* falsch: die Liste war leer, kein
  Fehler. Vor jedem Aufruf eines Hausmoduls die Signatur ansehen, nicht den
  Namen der Funktion raten.
- **Fremdname falsch delegiert.** Der Adapter rief `okx.guthaben(ccy)` auf; in
  `mosaic/okx_spot.py` heisst die Funktion `guthaben_waehrung(ccy)` - ein
  `guthaben` gibt es dort nicht. Ergebnis: `AttributeError`, und das meldete die
  Anbindungs-Pruefung als **„Guthaben nicht lesbar"** neben einer Zeile, die
  sonst vollstaendig gesund aussah.

**Merksatz fuer Delegation:** ein `AttributeError` im fremden Modul ist ein
**Namenfehler**, kein Datenfehler. Er darf nie als „nicht lesbar" enden, weil
der Unterschied unterscheidet, ob man die Boerse oder den eigenen Aufruf
untersucht.

## Merksatz

Ein Ausstiegspfad ist die einzige Code-Stelle, die **immer** funktionieren muss -
und er ist meist die, die am spaetesten gebaut und am seltensten gelaufen ist.
Er braucht keinen Freigabepflicht-Pfad, sondern einen eigenen.