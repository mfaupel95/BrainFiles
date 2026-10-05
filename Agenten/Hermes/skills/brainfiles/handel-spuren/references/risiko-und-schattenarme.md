# Risiko-Werkzeuge, Basis-Deckel, Schattenarme, Stop im Gitter

Dichte Hausbefunde. Jeder Abschnitt ist eine Regel, kein Vorfall.

## 1. DER WERKZEUG-PFAD IN Agenten/Handel: `HANDEL` ist EINE oder ZWEI Ebenen

Skripte, die DIREKT in `Agenten/Handel` liegen, schreiben `HANDEL = HIER`.
Skripte unter `Agenten/Handel/<spur>/` schreiben
`HANDEL = os.path.dirname(HIER)`.

Falsch ist `HANDEL = os.path.dirname(HIER)` fuer ein Skript IN `Agenten/Handel`:
das zeigt auf `Agenten/`, jede Spur-Schleife laeuft ins Leere.

**Warum das teuer ist:** das Ergebnis ist kein Absturz, sondern eine leere
Ergebnisliste. Ein Bericht, der "keine offenen Positionen im Haus" meldet,
liest sich wie ein Befund. Zwei Skripte an einem Tag (ein Freigabe-Tor und
ein Risiko-Werkzeug) fielen auf dieselbe falsche Ebene und lieferten beide
eine Zahl, die aussah wie eine Messung.

**Merksatz:** `dirname(HIER)` zeigt auf `Agenten/`. Das ist nie `Agenten/Handel`.

## 2. RISIKO-BEITRAG: drei Groessen, drei Bedeutungen

| Groesse | Definition | Wofuer sie da ist |
|---|---|---|
| Kapital (nominal) | Einsatz je Position | Streuung ueber Basen, BINDET NEUE EINSTIEGE |
| Risiko | `nominal * (stop/einstieg - 1)` je Seite | was bei einem Stop verloren geht |
| Beitrag je Basis | Summe ueber alle Schreibweisen einer Basis | die Frage "auf was liegt das meiste Geld" |

**Eine Position OHNE Stop ist nicht risikofrei, sie ist der ganze Einsatz.**
Zaehle sie nicht als Zahl, sondern melde sie als Befund - das ist in der
Regel der einzige Befund, den die Wache liefert.

**Risiken addieren sich, Kapital auf eine Basis stapelt sich.** Beides ist
korrekt. Die Differenz zwischen SPURENSUMME und BASIS-SUMME ist KEINE
Doppelzaehlung und darf nicht so genannt werden - jede Position hat ihren
eigenen Stop.

**Die Wache meldet eine VERAENDERUNG, nie den Stand.** Sonst wird sie
abgeschaltet und damit blind. Gegenprobe gehoert in den Test: erster Lauf
meldet, zweiter schweigt.

**Falle in der Merkdatei:** JSON schreibt Tupel als Listen und laesst sie
als Listen zurueckkommen. Ein Vergleich `"%s|%s" % tupel` passt danach nie
und die Meldung kommt bei JEDEM Lauf wieder. Merke Strings, keine Tupel.

## 3. BASIS-DECKEL: eine TABELLE, keine Zahl

`GRENZE = {"BTC": 50.0}`, Vorgabe 20 %. Ein Sonderfall ist eine Tabelle mit
einem Eintrag, kein Sonderfall im Code.

**Was ein Deckel bindet: NEUE EINSTIEGE. Bestehende Positionen laufen
weiter.** Eine Position zu schliessen ist eine Order und gehoert in die
Freigabekette wie jede andere. Ein Deckel, der beim Start sofort N Spuren
einfriert, ist ein Abschaltknopf mit anderem Namen. Der Deckel meldet den
Iststand und wartet auf den naechsten Einstieg - wer eine Basis einmal
ueberschreitet, hat sie schon bezahlt.

**Eingebaut wird der Deckel dort, wo echte Orders entstehen**
(`sperren_live()`, der asynchrone Executor) - NICHT in der
Signalberechnung. Eine Spur, die ein Signal sieht und es nicht handelt,
sieht fuer tot aus: der Stille-Spuren-Wache wuerde sie als tot melden,
ohne zu wissen warum. Im Tor wird der Einstieg abgelehnt und protokolliert,
die Spur laeuft weiter.

**Alias-Vorbereinheitlichung ist Pflicht, nicht Kosmetik.** Fuenf
Schreibweisen von BTC (`BTC-USDT-SWAP`, `BTC-USDC`, `BTC-USDT`, `XBT-USD`,
`BTC-USD_UM_XPERP-...`) sind EINE Basis. Ohne die Zuordnung `XBT -> BTC`
(Kraken fuehrt Bitcoin als XBT) sperrt der Deckel vier Fuenftel und laesst
das Fuenftel durch: ein Deckel, den man mit einem anderen Namen umgeht, ist
kein Deckel. **Gegenprobe im Test: die alte Fassung nachbauen und zeigen,
dass sie durchgelassen haette.**

**Schwellen nicht raten.** Eine geratene 25 % verfehlte eine Basis mit
24,4 %. Neben dem Schwellwert immer die N groessten Basen melden - die
Frage "auf was liegt das meiste Geld" faellt auch dann an, wenn die
Antwort knapp unter der Schwelle liegt.

**Die Polaritaet eines Tor-Rueckgabewerts ist Teil des Vertrags.** Der Tor
liefert `(GESPERRT, grund)` zurueck - nicht `(offen, grund)`. Ein Test, der
die beiden Werte vertauscht, kehrt saemtliche Behauptungen um: drei Tests
fielen aus, waehrend der Tor einwandfrei arbeitete. Daraus drei Regeln:
(a) die Reihenfolge im Docstring des Tors festhalten, (b) die Testvariable
nach dem WERT benennen (`gesperrt, grund = ...`), nie nach dem Gegenteil -
`offen` als Name fuer einen Wert, der `gesperrt` bedeutet, faellt erst beim
Lesen auf, (c) beide Werte in mindestens einem Fall belegen, sonst faellt
eine Umkehr nicht auf.

## 4. EIN STOP IN EINER GITTERSTRATEGIE

Ein Gitter hat keinen Stop - sein Ausstieg ist die naechste Leiterstufe,
sein Risiko die Naechstkaeufe. Ein Stop nach gewoehnlicher Art **arbeitet
gegen das Gitter**, wenn er ueber der naechsten Kaufstufe liegt: er feuert,
bevor das Gitter selbst kaufen kann. Das ist kein Schutz, sondern eine
Behauptung.

**Der Platz ist unterhalb der untersten Leiterstufe.** Dort ist die Leiter
zu Ende und die Voraussetzung der Strategie stirbt. Gemessen: 12 Stufen von
62657 bis 93986, Stufe 8 gekauft, Kurs 84770 - Notaus eine Stufe unter
Stufe 0 bei 60304,80, also -28,33 % vom Einstieg.

**Vorher den Kill-Schalter lesen.** Manche Kill blockieren nur Kauforders
("keine neuen Kauforders, belegte Stufen verkaufen weiter") und flachen
nicht ab. Eine Position ohne Stop ist dann vollstaendig ungesichert, egal
was der Kill-Name verspricht.

**Vermerk im Zustand, KEINE Journalzeile** - es ist kein Handel, sondern
eine Schranke.

## 5. SCHATTENARM: dieselbe Regel, zweiter Markt

Muster wie `squeeze_eth`: `HANDEL_BUCH=eth` haengt das Suffix an **jede**
Buchdatei. Vier Pflichten:

1. **Der Starter setzt die Umgebung VOR dem Kern-Import.** Der Kern liest
   das Suffix beim Laden; ein Starter, der es danach setzt, laeuft mit den
   falschen Dateinamen und schreibt in das Hauptbuch.
2. **Eigener Spiegel** (`journal_zweitziel` je Arm). Ohne eigenen Spiegel
   schreiben Haupt- und Schattenarm dieselbe Datei, und Bedingung 4 ist
   "erfuellt", weil sie ueberschreiben statt zu spiegeln.
3. **Der Hauptarm laeuft unveraendert weiter.** Ein Schattenarm, der den
   Hauptarm mitnimmt, hat keine Vergleichsgrundlage.
4. **`.gitignore` je Arm** (`zustand.<arm>*.json`,
   `handelsjournal.<arm>*.csv`, `signal_queue.<arm>*.json`). Wachen und
   Starter sind versionierbar, Buchdateien nicht - sonst laedt der Arm beim
   Start seine eigene Historie als Zustand.

**Der Test, der das beweist:** den Arm wirklich laufen lassen und die
Aenderungszeit des Haupt-Zustands vergleichen. Nicht nur die Dateinamen
pruefen.

## 7. OFFENER BESTAND: Schutzdruck messen, Luecken schliessen

Wenn bereits Positionen offen sind, ist die Frage nicht „hat die Position einen
Stop?", sondern „**wie viele Stuecke sind geschuetzt?**". Ein booleaner Treffer
genuegt nicht. Werkzeuge: `okx_positionen_live.py` (nur lesend),
`okx_tp_stufen.py` (Trockenlauf als Vorgabe).

1. **Von der Boerse lesen, nie aus dem Hausbuch.** Das Buch kann
   `fremdposition_uebernommen` fuehren und damit eine Stop behaupten, den die
   Boerse nicht traegt — und umgekehrt.
2. **Je Position drei Distanzen einzeln benennen**: Abstand zum Einstand, Luft
   bis zur Liquidationsmarke, gesetzte Marge. Die Luft rechnet sich
   `(liqPx/markPx - 1) * -Richtung`, damit Long und Short beide **positiv**
   sind; ein negatives Vorzeichen ist der Befund „Kurs ueber der
   Liquidationsmarke" und wird nicht mit `abs()` verschluckt.
3. **Menge summieren, Seite pruefen, nach Stop und Ziel trennen.** Schutz
   zaehlt nur mit `reduceOnly`, Seite gegen die Position und vorhandener
   Ausloesung. Zwei halbe Stops schuetzen nicht so viel wie ein ganzer.
4. **Alle ordTypes lesen** (`conditional`, `oco`, `trigger`,
   `move_order_stop`). Ein reiner `conditional`-Abruf uebersieht genau die
   OCO-Ordnungen, die die Haelfte der Absicherung tragen.
5. **Abstand zum EINSTAND und zum KURS getrennt rechnen.** Ein Stop am
   Einstand-Niveau ist nach einem Nachkauf weit vom Kurs entfernt — er schuetzt
   den Ruecksetzer, nicht mehr den Einstieg. Ein Zielpreis 1-2 % ueber dem Kurs
   heisst: die Position ist rechnerisch schon am Ziel. Beides gehoert in den
   Bericht, **bevor** eine weitere Order darueber gelegt wird.
6. **Luecke mit einem OCO schliessen, Preise vom bestehenden Order
   uebernehmen.** Der vorhandene Preis ist der Beleg, dass die Position vom Haus
   aufgebaut wurde; ein neu gerechneter waere eine zweite Wahrheit neben der
   ersten. Ein OCO loest pro Stueck nur einmal aus, zwei getrennte Orders
   koennen sich beim Treffer ueberschneiden.
7. **Eigener Orderweg, wenn die Hausfunktion fest auf eine Marktform verdrahtet
   ist.** Eine Spot-Hilfe mit festem `tdMode: cash` und `side: sell` tut auf
   einem Perpetual nichts.

**Der Auftrag kann erledigt sein, bevor er ausgefuehrt wird.** „Setz drei
Take-Profit-Stufen" auf eine Position, die kurz zuvor einen OCO mit Stop **und**
Ziel auf die volle Menge bekommen hatte, haette eine zweite TP-Ebene auf
dieselbe Position gelegt, deren Menge sich mit der Zielmenge ueberschneidet und
beim ersten Treffer doppelt verkauft. **Vor dem Bauen den Bestand messen und
sagen, ob der Auftrag ueberhaupt noetig ist.** Dass sich zwischen zwei Messungen
etwas geaendert hat (Parallelsitzung, Nachkauf-Leiter, Handgriff), ist ein
Befund und wird benannt — nicht stillschweigend uebergangen.

## 8. MESSWERKZEUG GEGEN DIE BOERSE: die Uebersetzung liefert 0, ohne zu melden

Beim Bau von `okx_positionen_live.py` lieferten vier verschiedene
Uebersetzungsfehler **alle eine 0**, ohne eine Exception — ein Konto mit 949
Einheiten meldete „0.00". Diese Klasse ist in `messwerkzeug-gegenprobe` und
`trugschluesse` ausgefuehrt; fuer Handelswerkzeuge kommen drei davon vor:

- **Ein Feld kann auf der uebergeordneten Ebene fehlen und je Einheit da
  sein.** Leerer String und `null` heissen „hier nicht", nicht „null". Bei
  `/account/balance` steht `totalEq` auf Kontoebene, `availEq` ist dort LEER
  und `stgyEq` ist `null` — die Zahlen stehen je Waehrung in `details`.
  Ein Feld mit zwei Ebenen wird **pro Ebene** gelesen.
- **`/positions` kennt kein `instType=SPOT`** (51000). Spot ist Bestand, keine
  Position — nachfragen statt den Fehler als Befund zu melden.
- **Eine Hilfsfunktion mit fest verdrahteter Marktform** liefert auf der
  anderen Form keinen Fehler, sondern gar nichts.

**Kontrollzeile braucht einen Nicht-Null-Sollwert.** `abs(gesamt - kontrolle)
< 0.01` meldete `passt: True`, waehrend beide Zahlen 0 waren. Gegen 0 pruefen
ist gegen nichts pruefen.

Der Reflex "Konzentration loesen = streuen" ist meist falsch, und die
Messung kostet einen Blick in die Wachen:

1. **Ist die Spur ueberhaupt auf dieses Instrument festgelegt?** Indikator-
   Spuren fuehren eine Instrumentenliste (`['BTC-USDC', 'ETH-USDC',
   'SOL-USDC']`) und liegen nur deshalb auf BTC, weil BTC staerker war.
   Umlegen hiesse dann nicht streuen, sondern die Regel "folge dem
   staerksten Markt" durch "folge dem naechsten" ersetzen - ohne Messung.
2. **Hat die Spur auf IRGENDEINEM Coin einen messbaren Vorteil?** Der
   Excess nach der Basislinie entscheidet. Wo er gegen null geht, verteilt
   Umlegen eine Null auf mehr Maerkte.
3. **Ist die Liquiditaet das Problem?** Fast nie - sie ist es nicht, und
   es lohnt nicht, sie als Argument zu pruefen.

**Schattenarm als Antwort auf die Frage**, wenn 1. und 2. keine Sperre
ergeben: derselbe Indikator fest auf dem zweiten Markt, beide Zahlen
nebeneinander. Zwei stark korrelierte Maerkte (BTC/ETH) sind dabei KEINE
Streuung - sie beantworten die Frage, ob die Regel coin-spezifisch oder
generell ist.