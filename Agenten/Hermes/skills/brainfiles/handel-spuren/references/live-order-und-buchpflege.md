# Live-Order und Buchpflege: was im Buch steht, muss an der Boerse existieren

Die teuerste Klasse von Fehlern in einer Live-Spur ist ein **Buch, das nicht zur
Boerse passt**. Sie kostet kein Geld direkt, aber sie laesst Plaetze belegt
aussehen, macht jeden Ausstieg fehlerhaft und macht jede Bilanz falsch. Dieses
Blatt ist die Sammlung der Faelle, die wirklich vorgekommen sind - als Regel,
nicht als Erzaehlung.

## 1. Order ANGENOMMEN ist keine Position - erst die Fuellung buchen

`order_limit()` liefert die `ordId`, sobald die Boerse die Order **akzeptiert**
hat. Das ist der Moment, in dem `state=live` und `accFillSz=0` gilt, nicht der
Moment des Kaufs. Wer hier bucht, hat eine Position im Buch, die es nicht gibt.

- Nach dem Absetzen **die Fuellung pruefen**, kurz warten (Limit kann in
  Sekundenbruchteilen fuellen): `okxf.gefuellte_kontrakte(inst, ord_id)` bzw.
  `order_stand()` lesen (`state`, `accFillSz`, `avgPx`).
- Teilfuellung: den Rest stornieren und **nur das Gehandelte** buchen; `avgPx`
  (nicht der geplante Preis) ist der Einstieg.
- Keine Fuellung und nicht marktbar -> **nicht buchen und nicht stornieren**
  (siehe 2). Keine Fuellung trotz Marktbarkeit -> echter Fehler: stornieren,
  Journal-Zeile `order_nicht_gefuellt`.

Der Massstab ist immer die **Boerse**, nie die eigene Zustandsdatei:
`/api/v5/account/positions` (OKX) bzw. Balance + offene Orders (Kraken).

## 2. Ein Limit HINTER dem Markt ist WARTEND, kein Fehler

Viele Spuren setzen ihren Einstieg aus einer eigenen Zonen-/Pullback-Rechnung -
das Limit liegt dann absichtlich unter dem Markt (Kauf) bzw. darueber (Verkauf).
Es fuellt, wenn der Kurs zurueckkommt. Wer das als Fehler behandelt und storniert,
produziert eine Schleife: Order setzen, Order wegwerfen, Order setzen - und im
Journal stehen mehrere gleichlautende Fehlerzeilen an einem Abend.

- **Marktbarkeit entscheidet** (`okxf.kurs_und_spanne(inst)` -> letzter Kurs,
  bester Bid, bester Ask): Kauf ist marktbar ab `Ask`, Verkauf bis `Bid`.
- **Nicht marktbar** -> Order bleibt liegen: Journal-Aktion `order_offen` mit
  `grund=limit_wartet`, Eintrag in `zustand["wartende"]` mit allen Feldern, die
  eine spaetere Position braucht (inst, seite, familie, einstieg, stop, ziel, liq,
  kontrakte, nominal, margin, hebel, ord_id, gestellt).
- **Auftragsverwaltung je Zyklus, vor der Einstiegsplanung:** fuer jeden
  wartenden Auftrag den Zustand fragen. `filled` -> Position aus dem Eintrag
  buchen (Journal `eroeffnen`, `grund=order_gefuellt`), Kontrakte aus `accFillSz`,
  Einstieg aus `avgPx`. `canceled`/`mmp_canceled` -> vergessen. Sonst liegen
  lassen. **Faellt die Abfrage aus, bleibt der Eintrag stehen** - ein Netzfehler
  darf keinen Auftrag verlieren, der an der Boerse liegt.
- Stop und Ziel haengen als `attachAlgoOrds` an der Order und werden beim
  Fuellen aktiv - der wartende Auftrag traegt sie deshalb nur zur Information.
- Warum die Verwaltung **vor** den neuen Einstiegen laeuft: ein ueber Nacht
  gefuellter Auftrag ist eine Position und belegt einen Platz.

## 3. Geisterpruefung: erst die ORDER fragen, dann ausbuchen

Eine Position mit `modus=live`, die in `/account/positions` fehlt, ist meist ein
Geist (Papier-Ueberbleibsel, geloeschte Order) - **aber nicht immer**: eine Order,
die genau waehrend der Pruefung fuellt, sieht identisch aus. Wird sie ausgebucht,
laeuft eine echte, gehebelte Position ohne Buch weiter.

- Reihenfolge: Position an der Boerse vorhanden -> behalten. Sonst **zuerst den
  Orderzustand** fragen: `accFillSz > 0` -> behalten (die Boerse fuehrt sie nur
  noch nicht in der Positionsliste). Erst wenn Order ungefuellt/erloschen ist und
  keine Position existiert -> ausbuchen (`grund=buchbereinigung_geist`) **und die
offene Order dazu stornieren** - sonst fuellt sie spaeter eine Position, die
  niemand beobachtet.
- `pos=0`-Zeilen der Boerse sind KEIN Bestand (OKX behaelt geschlossene
  Positionen als Zeile).
- **Netzfehler -> gar nichts buchen**, laut melden, Buch unberuehrt lassen.

### 3a. Der Abgleich prueft die EXISTENZ, nicht die GROESSE

Die Geisterpruefung fragt nur, OB die Position da ist (`abs(pos) >= 1e-9`). Eine
**teilweise** geschlossene Position - von Hand an der Boerse reduziert, z. B.
60 -> 19 Kontrakte - bleibt damit mit ihrer ALTEN Kontraktzahl im Buch stehen.
Folgen: ein Ausstieg will mehr Kontrakte verkaufen als existieren (Fehler oder
Teilfuellung), der Platz bleibt belegt, und jede Rechnung auf der Position ist zu
gross. Umgekehrt bleibt eine an der Boerse aufgestockte Position im Buch zu
klein.

- Nach JEDEM Eingriff an der Boerse - auch einem von Hand - **Soll (Buch) gegen
  Ist (Boerse) je Kontrakt vergleichen**, nicht nur "vorhanden/nicht vorhanden".
  `/api/v5/account/positions` liefert `pos` je `instId`; das ist die Zahl, gegen
  die das Buch gehalten wird.
- Eine Abweichung ist ein Befund, kein Rauschen: entweder ist das Buch zu gross
  (Teilschliessung nicht gebucht) oder zu klein (Bestand ohne Buch).

### 3b. Eine Ausbuchung darf keinen Verlust ERFINDEN

Die Ausbuchung schreibt eine `schliessen`-Zeile mit `margin_usd="0.00"`. Die
Kapitalkurve liest den Einsatz aus der `eroeffnen`-Zeile und den Ertrag aus
`margin_usd` der `schliessen`-Zeile - `0.00` heisst also: **die Runde zaehlt als
Totalverlust des Einsatzes.** Eine von Hand geschlossene Position, auch eine mit
Gewinn, hebt damit den Ruecklauf um ihren ganzen Einsatz an und kann Kill-Switch
und Ratsche ausloesen. Der Eingriff des Nutzers ist keine Handelsentscheidung der
Spur; ihn als Verlust zu verbuchen macht die Statistik falsch UND die Notbremse
scharf.

- Vor dem Ausbuchen nachrechnen: `ruecklauf_usd` aus `lage()` gegen
  `kill_switch_gesamt_usd`. Ein Geist-Eintrag ueber der Restluft
  (`deckel - ruecklauf`) sperrt die Spur im naechsten Zyklus und stellt flach.
- Richtig ist eine **neutrale oder echte** Buchung: den Einsatz als Ertrag
  zurueckbuchen (Eingriff ohne Handelsergebnis) oder den realisierten PnL von der
  Boerse holen (`/api/v5/account/positions-history` -> `realizedPnl`).
- Eine Bereinigung ist **idempotent** (zweiter Lauf meldet "Buch ist leer"),
  fasst Positionen MIT Orderkennung nicht an (dort haengt echtes Geld - die
  gehoeren ueber den normalen Ausstiegspfad geschlossen) und bucht den echten
  Kurs-G/V, nicht null. Vorbild: `scanner/buchbereinigung.py` mit
  `--vorschau`/`--anwenden`.

## 4. Ein Papierlauf schliesst keine echte Position

Buch ist EINES fuer Papier und Live; `modus` trennt sie. Laeuft die Spur im
Papier (kein Freigabefenster, `handel_erlaubt=false`) und loest dabei der
Kill-Switch oder ein alter Herzschlag aus, dann schliesst `flach_stellen` auch
`modus=live`-Positionen - **nur im Buch, an der Boerse bleibt die Position offen.**
Ergebnis: echte Position ohne Buch.

- Regel: im Papierlauf bleiben `modus=live`-Positionen stehen und werden
  gemeldet; geschlossen werden sie ausschliesslich vom Live-Lauf.
- **Die Regel gilt in JEDEM Zweig - und muss in JEDEM Zweig getestet werden.**
  Ein Waechter im Live-Zweig (`live_ausstiege`, `flach_stellen_live`) sagt nichts
  ueber den Papierzweig: dort lief `pruefe_ausstiege` weiter mit den eigenen
  Kerzen und buchte eine echte Position mit `grund=ziel` aus, waehrend der
  Live-Zweig dieselbe Position als "laufend" sah. Wer die Modus-Trennung an einer
  Stelle einbaut, hat sie an der falschen eingebaut.
- **Der Kill-Pfad des Papierzweigs zaehlt mit:** `z["positionen"] = []` loescht
  auch Live-Positionen. Regel in eine eigene, pruefbare Funktion ziehen
  (`nur_papier_verwerfen(z)`) statt als Zeile in `lauf()` stehen zu lassen.
- **Ein einziger Papierzyklus genuegt fuer den Schaden.** Die Luecke zwischen
  Ablauf und Auto-Freigabe des Freigabefensters (Sekunden bis Minuten) ist ein
  normaler Betriebszustand, kein Randfall - genau dort entsteht der Geist.
- **Testform fuer den PAPIERzweig** (der Live-Test deckt das nicht ab):
  Live-Position UND Papier-Position ins Buch, Kerze ueber dem Ziel und eine unter
  dem Stop -> die Live-Position bleibt stehen, die Papier-Position wird verkauft,
  im Journal steht nur der Papierverkauf; dazu der Kill-Pfad und ein leeres Buch
  (kein KeyError).
- **Falschbuchung richtig zuruecknehmen:** die `papier,verkauf`-Zeile ist sachlich
  falsch und erzeugt sonst eine Runde, die nie stattfand. Sie nach
  `handelsjournal.verworfen-JJJJMMTT.csv` sichern, aus dem Journal entfernen und
  durch `live,anpassen,<inst>,<seite>,...,buch_nachgezogen_boerse` ersetzen
  (`anpassen` paart keine Runde). Vorher `.bak-JJJJMMTT` von Zustand UND Journal.
- **Werte fuer die Rueckbuchung von der Boerse holen, nicht aus dem Buch:**
  Guthaben (Menge) + offene Order-Algos (Stop-Kennung) lesen, die
  Eroeffnungszeile des Journals gegenlesen, nichts schaetzen.
- **Zurueckbuchen heisst NICHT "der Live-Zweig verkauft sie gleich":** Stop und
  Ziel der wiederhergestellten Position sind in der Waehrung ihrer Boerse gerechnet
  und der Live-Zweig entscheidet mit dem Kurs DIESER Boerse (siehe
  `zweite-boerse.md`). Ein Ziel, das im Papierzweig "erreicht" war, kann live weit
  entfernt sein - erst nachsehen, dann erwarten.

### 4a. Eine Variable, die nur im LIVE-Zweig entsteht, toetet den PAPIERzweig

Die beiden Zweige teilen sich den Rumpf hinter der Verzweigung. Wird eine
Variable im `if live:`-Zweig gebunden und danach im gemeinsamen Buchungssatz
gelesen, wirft der PAPIERzweig `UnboundLocalError` - und der Papierzweig ist der,
der am haeufigsten laeuft (Fenster zu, `handel_erlaubt=false`, jede Stufe).
Gemessen: `gefuellt`/`fuellung_bestaetigt` entstanden nur im Live-Zweig (sie kamen
mit der Fuellungs-Abfrage), der gemeinsame Satz las sie - **jeder Papierkauf warf
seit Tagen**, waehrend die Spur live normal weiterkaufte und der Treiber den
Fehler nur als "fehlgeschlagener Zyklus" verbuchte.

- **Gemeinsam genutzte Variablen werden VOR der Verzweigung vorbelegt**, mit dem
  Wert, der fuer den anderen Zweig gilt - hier: ein Papierkauf hat keine
  Boersenfuellung, also `gefuellt, fuellung_bestaetigt = menge, True`. Eine
  Vorbelegung mit `None` waere die naechste Falle (der Buchungssatz schreibt sie
  in den Zustand).
- **Jeder Zweig wird einmal echt gefahren.** Ein Test, der nur den Live-Zweig
  anfasst, ist gruen, waehrend der Papierzweig in jedem Zyklus stirbt; die
  Testform fuer den Papierzweig steht in Abschnitt 4.
- **Nach einem roten Lauf nicht aufhoeren beim ersten Fix.** Die acht roten Tests
  hatten drei Ursachen uebereinander (Zweig-Variable, eine Attrappe ohne die neue
  Funktion, ein Test mit dem Stand VOR der Regel); nach jedem Fix neu fahren -
  die naechste Schicht wird erst sichtbar, wenn die vorige weg ist.
- **Eine Attrappe, die eine aufgerufene Funktion gar nicht kennt, macht den Test
  ROT** (`AttributeError`) - das ist die gute Richtung und der Grund, warum die
  Suite den Zweig-Fehler ueberhaupt fand. Wer die Attrappe um die fehlende
  Funktion erweitert, prueft danach den GANZEN Weg, nicht nur den einen Aufruf.

## 5. Nach jeder Wiederherstellung: hat die Position einen Stop?

`attachAlgoOrds` werden beim Fuellen aktiv - greift das nicht (z. B. weil die
Order erst spaeter fuellte oder ein Storno dazwischenkam), liegt die Position
**ohne boersenseitigen Stop**. Pruefen mit
`/api/v5/trade/orders-algo-pending?instType=FUTURES` fuer **jede** `ordType`
(`conditional` UND `oco` - der Anlageweg entscheidet die Liste; eine leere
`conditional`-Antwort ist bei einer `oco`-Position ein FALSCHES "kein Stop",
siehe 5c). Ist die Liste leer, den Stop mit den Werten der Eroeffnungszeile nachsetzen
(`/api/v5/trade/order-algo`, `ordType=conditional`, `slTriggerPx`, `slOrdPx=-1`,
`reduceOnly=true`, Gegenrichtung der Position). Eine gehebelte Position ohne Stop
laeuft bis zur Liquidation, wenn der Rechner ausfaellt.

### 5a. Was der Ausstieg zuerst ABBESTELLT, muss er bei einem Fehlschlag zuruecklegenn

Ein Live-Verkauf bestellt VOR der Verkaufsorder den boersenseitigen Schutz-Stop
ab (sonst nimmt der Stop die Verkaufsorder weg). Scheitert der Verkauf danach -
andere Fehlermeldung, falscher Host, abgelehnte Order -, steht die Position
**ohne Stop** an der Boerse: gehebelt bis zur Liquidation, und im Buch sieht sie
unveraendert aus. Der Verlust waere nicht aus dem Journal ablesbar.

- Jeder Ausstiegspfad braucht den Rueckweg: scheitert der Verkauf, den Stop mit
  der **echten Fuellungsmenge** wieder anlegen und das in die Meldung schreiben.
- Probe je offener Live-Position:
  `/api/v5/trade/orders-algo-pending?ordType=conditional` - eine Position ohne
  Eintrag dort ist ungeschuetzt.
- Testform: den Bestellweg stilllegen und `markt_verkauf` scheitern lassen; der
  Test muss danach eine **Stop-Bestellung** sehen, nicht nur "kein Absturz".
- Merksatz: eine Operation in zwei Schritten (abbestellen, dann handeln) ist erst
  fertig, wenn der Abbruch sie rueckgaengig macht.

### 5b. Ein Stop-MERKER braucht Dedupe und eine Wache

Lässt sich ein boersenseitiger Stop beim Ausstieg nicht abbestellen, merkt sich die
Spur ihn (`zustand["offene_stops"]`) und versucht es im naechsten Live-Lauf erneut.
Zwei Fehler, die dabei entstehen, sind unsichtbar und wachsen:

- **Das Storno braucht die `instId`.** OKX antwortet auf `cancel-algos` ohne sie mit
  `50014 Parameter instId can not be empty` - der Stop ist dann NIE abbestellbar, und
  jede Runde meldet "bleibt liegen". Gemessen am EEA-Host: mit `instId` kommt fuer
dieselbe Order `51400 … has been filled, canceled or does not exist`. **`51400` heisst
  erledigt, nicht Fehler** - wer es als Fehler wertet, laesst den Merker fuer immer
  stehen. Alteintraegen ohne Instrument die `instId` lesend nachholen (`order-algo`
  liefert `instId` und `state`).
- **Ein Merker, der nur beim Erfolg faellt, braucht einen Dedupe.** Ohne Duplikat-Schutz
  haengt jeder weitere Ausstiegsversuch denselben Stop erneut an; solange zugleich der
  Verkauf scheitert (z. B. falscher Host -> `50119`), bleibt die Position im Buch und der
  naechste Zyklus merkt wieder - der Zaehler waechst unbemerkt, waehrend der Schalter
  "ok" meldet.

Regel: **jeder Merker, der wachsen kann, gehoert in eine Wache.** Die Wache
(`Agenten/Hermes/scripts/live_wache.py`, `stop_lage`) vergleicht in BEIDE Richtungen -
Stop an der Boerse ohne Position (Waisenstop: kann eine spaetere Position zum alten
Preis verkaufen) und Position ohne Boersenstop (kein Notausstieg) - und meldet nur den
WECHSEL der Lage, sonst stuende dieselbe Zeile in jedem Takt.

Aufraeumen des Bestands (eigenes Werkzeug, Vorschau Standard, `--anwenden`): je Eintrag
den ECHTEN Boersenzustand lesen, erledigte und doppelte entfernen, unlesbare STEHEN
LASSEN (lieber behalten als eine echte Order vergessen), Waisen nur mit ausdruecklichem
`--stornieren` abbestellen. Eine Zustandsdatei, die juenger ist als ein Zyklus, nicht
anfassen - der laufende Zyklus ueberschreibt die Aenderung ohnehin und man verliert eine
Buchung. Nachweis: Buch gegen Boerse zaehlen
(`/api/v5/trade/orders-algo-pending?ordType=conditional`), beide Richtungen muessen
leer sein.

### 5c. Der Stop-Zustand ist Teil des Abgleichs — und ein Buchfeld luegt

Die Stop-Pruefung aus 5 gehoert in **jeden Live-Zyklus**, nicht an die
Eroeffnung. Ein Buchfeld, das nur beim Kauf gesetzt wird (`boersen_stop_fehlt`),
behauptet danach dauerhaft "Stop ist da" — auch wenn ein Storno von Hand, ein
abgebrochener Verkauf oder eine von Hand reduzierte Stueckzahl die Position
laengst ungeschuetzt gelassen hat. Der Befund ist stumm: die Spur meldet "ok",
das Buch sieht vollstaendig aus, und es gibt keinen Notausstieg.

- **Ein Feld, das nur in einem Zweig geschrieben wird, ist keine Wache.** Wer
  den Zustand behaupten will, muss ihn in JEDEM Zyklus an der Boerse lesen —
  derselbe Abgleich wie die Geisterpruefung, nur mit Stop statt Groesse.
- **Alle Algo-Typen fragen, nicht einen:** OKX legt Stops je nach Anlageweg als
  `conditional` ODER `oco` ab. Eine Abfrage nur auf `conditional` liest sich bei
  einer `oco`-Position wie "kein Stop" — und wer darauf hin nachsetzt, hat einen
  Doppelstop (zwei Verkaufsorders auf denselben Bestand).
- **Vor dem Nachsetzen nach dem INSTRUMENT fragen, nicht nach der gemerkten
  Kennung.** Die im Buch stehende Stop-Kennung kann veraltet sein, waehrend an der
  Boerse ein lebender Stop existiert: die Pruefung "ist DIESE id noch wirksam?"
  beantwortet dann "nein" und setzt einen zweiten Stop. Richtig ist "hat dieses
  Instrument ueberhaupt einen offenen Stop dieser Seite?".
- **Den Ausstieg am BESTAND erkennen, nicht am Algo-Zustand.** OKX laesst die
  Algo-Antwort nach dem Ausloesen auf `state=effective` und `accFillSz=0` stehen,
  obwohl der Stop gefeuert und eine echte Market-Sell-Fuellung entstanden ist
  (ein `cancel-algos` darauf antwortet `51400`, also "erledigt"). Reihenfolge:
  **erst den Bestand der Basiswaehrung lesen** (`/account/balance?ccy=<coin>`);
  ist er auf null, ist die Position an der Boerse weg — dann den echten Preis aus
  der juengsten gefuellten Order der Verkaufsseite holen und mit dem Ergebnis
  buchen. Ohne belegten Preis wird NICHT gebucht: laut melden, Buch unberuehrt.
- **Was hier passiert, gehoert gemeldet.** Ein nachgesetzter Stop und eine
  boersenseitig verkaufte Position sind Ereignisse, nicht Buchhaltung — ohne
  Meldung erfaehrt niemand, dass eine Position ungeschuetzt stand.
- **Werkzeug als Muster:** `scanner/boersenstops.py` (Vorschau Standard,
  `--anwenden`) liest je Position Bestand UND Stop-Zustand, setzt fehlende Stops
  nach, bucht boersenseitige Ausstiege mit echtem Preis aus und raeumt Waisenstops
  ab; die Buchdatei wird nur geschrieben, wenn sie nicht juenger als ein Zyklus
  ist. Direkt aus dem Live-Zweig aufrufbar.
- **Testform:** Boersenmodul als Attrappe (Antworten je Fall), Journal in eine
  Temp-Datei, vier Faelle — Stop wirksam (nichts tun), Stop fehlt (setzen, mit
  Menge = Bestand), Bestand weg (buchen mit Fuellungspreis), Bestand weg ohne
  ermittelbaren Preis (nicht buchen, melden).

### 5d. DECKUNG ist eine eigene Pruefung - Existenz ist keine Menge

Alle bisherigen Abgleichsstufen fragen OB: die Geisterpruefung, ob die Position
da ist (3), die Groessenpruefung, ob die Kontraktzahl stimmt (3a), die
Stop-Pruefung, ob EIN Schutzauftrag liegt (5, 5c). Keine davon fragt, **wie viele
Kontrakte dieser Schutz abdeckt**. `_stop_vorhanden()` ist ein boolescher
Existenztest: es gibt `True` zurueck, sobald IRGENDEIN Schutz gefunden ist, und
wirft die Menge dabei weg. Ein Stop ueber 1 Kontrakt gilt dort wie einer ueber
145.

Das ist keine Verallgemeinerung, sondern eine gemessene Luecke: Position 145
Kontrakte an der Boerse, sechs OCO-Stops mit 45+11+1+29+12+28 = 126 - **19
Kontrakte bis zur Liquidation**, waehrend Spur, Bericht und Abgleich „ok"
sagten. Dieselbe Blindstelle hatte T-278 gestreift (ein Trailing-Stop ohne
`slTriggerPx`); dort blieb sie unbeziffert, hier steht die Zahl.

- **GESCHUETZT ist, was die MENGE deckt.** `sum(sz)` ueber die Schutzauftraege
  gegen die Kontraktzahl an der **Boerse** stellen (nicht gegen das Buch: ein
  Handgriff kann das Buch verkleinert haben, und was die Boerse haelt, ist
  ungeschuetzt, egal was das Buch behauptet). Die Restmenge ist die Luecke.
  **Der Unterschied ist teuer, er ist nicht theoretisch.** Dieselben acht
  Positionen einer Spur, zweimal gerechnet: gegen das Buch (`usd / einstieg`)
  sieben ungeschuetzt und 39,23 EUR; gegen die Boerse (Bestand) eine
  ungeschuetzte Position und 2,08 EUR. Der Faktor 19 kam daher, dass
  `usd / einstieg` der **geplante** Einsatz ist, waehrend die Boerse den
  Bestand nach Gebuehr und Ausfuehrung haelt. Ein Handgriff verschiebt das
  Buch, ohne die Boerse zu beruehren — und jede Coverage-Zahl, die das Buch
  als `soll` nimmt, misst Buchhaltung und nennt sie Deckung.
- **`reduceOnly` ist eine Regel des ORDWEGS, nicht des Marktes.** Es zu
  verlangen ist richtig, wenn der eigene Bestellweg das Feld setzt
  (`okxf.schutz_stop_setzen()`); es ist falsch, wenn er es nicht setzt. Eine
  Spur, deren `stop_setzen()` kein `reduceOnly` schreibt, bekommt von der
  Boerse `reduceOnly: "false"` fuer **jeden** ihrer Stops — und ein Filter
  darauf verwirft jeden echten Schutz und meldet die ganze Position als
  ungeschuetzt. Gemessen: sieben von acht Positionen als ungeschuetzt gemeldet,
  weil die Regel aus der Nachbarspur kopiert war. **Vor dem Uebernehmen eines
  Schutz-Filters aus einer anderen Spur fragen, ob deren Bestellweg dasselbe
  Feld setzt** — die Filterregel folgt dem Bestellweg, nicht dem Markt.
- **Die Toleranz kommt aus `lotSz`, nicht aus einer festen Zahl.** OKX rechnet
  die Kontraktzahl in Instrument-Schritten, und die unterscheiden sich
  (`lotSz` 0,000001 gegen 0,001 auf zwei Maerkten derselben Spur). Zu streng
  (1e-9 fest) meldet eine Lot-Rundung von 1e-8 als Luecke; zu lax (1e-3 fest)
  verdeckt sie eine echte. Korrekt ist **ein halber Lot-Schritt des jeweiligen
  Marktes**, aus der Instrumenttabelle. Die Toleranz steckt danach im Ergebnis,
  nicht im Vergleich — die gemeldete Luecke ist die um die Toleranz verminderte.
- **Mehr Bestand an der Boerse als im Buch ist KEINE Deckungsluecke.** Ein
  Buch, das 55 Stueck fuehrt, bei einem Bestand von 123 an der Boerse, ergibt
  gegen die Boerse gerechnet eine "Luecke" von 68 — und beschreibt genau das
  Gegenteil: ungebuchter oder von Hand gehaltener Bestand. Eine Stufe, die das
  als Deckungsluecke meldet, behauptet etwas Falsches und erzeugt einen
  Aufraeumauftrag, den niemand bestellt hat. **Vor dem Bauen der Stufe
  feststellen, wer den Mehrbestand gehoert** (andere Spur? Handkauf?).
  Gehoert er niemandem ausser dem Nutzer, ist das eine **Entscheidung von ihm**
  und keine Codefrage: der Befund geht als Bestandsliste in den Bericht, und
  es wird nichts angefasst.
- **Ein reiner Mengen-Zaehler verwechselt sich mit einem Schutz-Zaehler.** Als
  Schutz zaehlt ein Auftrag, wenn die Seite
  GEGEN die Position laeuft und eine Ausloesung traegt (`slTriggerPx` ODER
  `tpTriggerPx` - ein Trailing traegt kein `slTriggerPx`). Der Filter ist
  derselbe wie `okxf.ist_schutz_stop`, nur MIT der Menge - genau daran scheitert
  die Existenzvariante.
- **Ein Nachsetzen holt nur die LUECKE, nie den Bestand.** Bestehende Schuetzte
  werden nicht storniert und nicht nachgezogen: bei zwei Stops auf denselben
  Bestand feuert der engere zuerst und zieht den Schutz unbemerkt enger (T-278).
- **Zwei Preise, die ein Nachsetzen verweigern muss.** Ein long-Stop AUF oder
  UEBER dem Kurs verkauft sofort zum Markt - das ist kein Schutz, sondern ein
  Ausstieg. Ein Stop auf oder unter `liqPx` kommt nach der Liquidation nie zur
  Ausloesung und ist ebenfalls wertlos. Beide Faelle: **nicht stellen und
  melden**, statt eine scheinbare Sicherung zu bauen, die im Buch wie Deckung
  aussieht.
- **Ein solcher Stop wird als TOT gemeldet, nicht still uebergangen.** Er
  belegt Kontraktzahl, schuetzt aber nichts - dieselbe Buchzahl, dieselbe
  Fehlwirkung wie ein toter Vermerk.
- **Ein Werkzeug, das dafuer keinen Preis erfindet.** Ohne ausdruecklichen
  Preisschalter stellt `--anwenden` nichts; es zeigt die Luecke und den
  erlaubten Korridor (unter dem Kurs, ueber der Liquidation) und laesst die
  Wahl Max. Ein geratener Schutzpreis ist eine Order, die jemand nicht
  bestellt hat.
- **Nachgesetzter Schutz ist KEIN Handel:** Vermerk in den ZUSTAND, keine
  Journalzeile. Eine `anpassen`- oder `schliessen`-Zeile erzeugt eine Runde,
  die nie stattfand.
- **Die Deckung gehoert in JEDEN Live-Zyklus, nicht an die Eroeffnung.** Am
  05.10.2026 hatte eine Spur an Kraken Futures einen Live-Zweig mit gesetztem
  Schutz-Stop - und trotzdem fehlte der zweite Weg: `live_perp.stopdeckung_pruefen()`
  laeuft jetzt VOR der Ausstiegsentscheidung ueber alle Positionen mit
  `modus=live`. Ein Stop kann nach dem Kauf wegfallen (Storno, zu kleine Menge,
  eine nie ausgefuellte Order), ohne dass das Buch etwas davon erhaelt. Muster:
  `omniquant/live_perp.py`, `tests/test_stopdeckung_live.py`.
- **Ein gesetzter Stop ist kein Beweis - er wird NACHKONTROLLIERT.** Nach dem
  Nachsatz liest die Funktion die Deckung ein zweites Mal mit der Kontraktzahl.
  Ein Nachsatz ohne Nachkontrolle meldet Erfolg, auch wenn die Boerse nur die
  Haelfte nimmt (T-323).
- **Ein Abruf-Fehler fasst NICHTS an.** Faellt die Deckungsabfrage aus, wird
  nichts gesetzt und nichts gebucht, sondern eine Journalzeile `aktion=fehler`
  geschrieben: ein Netzfehler darf keinen Stop doppelt setzen und keine
  Position loeschen.
- **Testform:** Filter entfernen -> rot; Preissperre entfernen -> rot. Der
  Gegenbeweis gehoert in den Aufbau, sonst prueft die Suite nur, dass der Code
  laeuft. Attrappen-Regel: die Auftrags-Attrappe muss ein **dict** sein, weil der
  Produktionscode per `.get()` liert - ein Objekt mit Attributen laesst jeden
  Test an der Kapazitaet der Attrappe scheitern statt an der Regel (bei
  `okxf.schutz_stops` zusaetzlich die Liste liefern, nicht nur `positionen`).
- **Die Stufe muss an BEIDEN Zweigen haengen, nicht nur am Nachsetz-Zweig.**
  Der gemessene Fall liegt im *gesunden* Zweig: der gemerkte Stop ist wirksam
  und deckt trotzdem zu wenig. Eine Inline-Passage hinter
  `if wirksam: continue` ist toter Code, den keine Suite sieht, die nur den
  Reparierzweig fahrt. Beide Zweige rufen **eine** Funktion - zwei Aufrufe
  bedeuten zwei Wahrheiten, die auseinanderlaufen koennen.

### 5e. Die Deckungsstufe in eine neue Spur einziehen: erst messen, dann bauen

Diese Regel hat vier Spuren gebaut und bei der fuenften **bewusst nichts
gebaut**. Die Reihenfolge ist nicht Geschmack:

- **Ein Pruefpfad, der in drei Nachbarspuren steht, ist kein Auftrag, ihn in
  der vierten auch zu bauen.** Zuerst messen. Kommt "alles gedeckt" heraus,
  ist das ein **Ergebnis**, kein offener Punkt: die Stufe wuerde eine
  Boersenabfrage je Zyklus fuer eine Zahl kaufen, die immer 0 ist. Sag es
  und hoer auf.
- **Kommt die Rechnung gegen die Boerse zu hoch, loest sie sich als
  Bestandsdifferenz auf.** Ein Buch mit 55 Stueck bei einem Bestand von 123
  ergibt "68 ungeschuetzt" — und beschreibt das Gegenteil: ungebuchter
  Bestand. Ein Bestand ohne Buch ist **Geld des Nutzers** (Handkauf, oder eine
  Position, die keine Spur fuehrt). Eine Stufe, die das als Deckungsluecke
  meldet, erzeugt einen Aufraeumauftrag, den niemand bestellt hat.
- **In beiden Faellen gehoert der Befund in den Bericht, nicht in den Code.**
  Als Bestandsliste mit der Frage: gehoert das dir, oder ist es ungebucht?
  Das ist eine **Entscheidung von ihm**, und eine Task-Zeile, die eine
  Entscheidung als Arbeit tarnt, wird naechste Woche wie eine offene Arbeit
  behandelt.
- Umgekehrt gebaut ist die Stufe ein permanenter Zyklusaufruf, der eine Zahl
  produziert, die niemand verantwortet.

### 5f. Filterregeln folgen dem BESTELLWEG, nicht dem Markt

Beim Einziehen der Coverage in eine neue Spur kommen drei Filter mit, die
dort **falsch** sein koennen. Alle drei erzeugen eine Zahl, die plausibel
aussieht und falsch ist — und alle drei fallen sofort auf, wenn die neue
Stufe "alles ungeschuetzt" meldet. Deshalb: **bei "alles ungeschuetzt" ist
zuerst der Filter der Verdacht, nicht der Bestand**, und dann liest man die
Rohfelder eines einzelnen Auftrags (`reduceOnly`, `sz`, `state`), statt das
Ergebnis zu deuten.

| Mitgebrachter Filter | Wann er falsch ist | Symptom |
|---|---|---|
| `reduceOnly` verlangen | der Bestellweg der neuen Spur setzt das Feld nicht | die Boerse meldet `reduceOnly: "false"` fuer jeden Stop, der Filter verwirft alle |
| feste Toleranz (`1e-9`) | der Markt rechnet in `lotSz`-Schritten | Lot-Rundung von `1e-8` wird als Luecke gemeldet |
| `soll` aus dem Buch (`usd / einstieg`) | der geplante Einsatz != der Bestand nach Gebuehr | Faktor 19 zwischen Buch- und Boersenrechnung (Abschnitt 5d) |

Das ist die Verallgemeinerung von Abschnitt 5d fuer den Einbau, und es ist
zugleich der Grund, warum die drei Regeln dort je **fuer sich** begruendet
sind statt gemeinsam: sie haben verschiedene Mechanismen und verschiedene
Belege.

## 15. Eine UNBESTAETIGTE Fuellung ist keine Null - und eine Null wird nie zur Order

Der teuerste Einzelfehler dieser Liste: aus einer Boersenantwort, die **noch nicht
gefüllt** ist, wird eine **bestellte Groesse von 0**. Von dort laeuft eine Kette,
die jede Station als Erfolg meldet.

Gemessen an einer Live-Position (PF_HBARUSD, Kraken Futures):

    Fuellung sofort nach dem Kauf gelesen  -> Teilwert 0.4 (Boerse noch nicht gefuellt)
    int(0.4)                                -> 0
    Schutz-Stop mit size: 0                -> Kraken: "invalidArgument: 0"
    "Rueckdrehung" mit size: 0              -> wirkungslos, KEIN Fehler
    Journal                                  -> "Position wegen fehlendem Stop
                                               zurueckgedreht"      (= falsch)
    Ergebnis an der Boerse                   -> Position steht, ohne wirksamen Stop

Drei Regeln, jede davon haette allein geholfen:

- **Fuellung bestaetigen, bevor aus ihr eine Groesse wird.** Direkt nach dem Kauf
  ist die Fuellung normalerweise noch nicht da; die Boersenantwort ist dann leer
  oder ein Bruchteil. Die Lesefunktion wartet (Zeitfenster + Abstand) und gibt
  `(menge, bestaetigt)` zurueck. `bestaetigt=False` heisst **"Bestaetigung offen"**,
  nicht "0 ausgefuehrt" - dieser Unterschied ist der ganze Fix.
- **Nie auf 0 herunterrechnen.** Ein Kontrakt ist die kleinste handelbare Einheit:
  `max(1, int(round(menge)))`. Eine Fuellung, die auf 0 rundet, wird als
  Fehlerbehandlung behandelt, nicht als Groesse.
- **Ein Abfragefehler ist KEIN Nullbefund.** Faellt `/fills` aus, ist das Ergebnis
  "unbekannt". Aus "unbekannt" darf nie "0 ausgefuehrt" werden - derselbe Fehler
  wie ein Kalendersystem, das ein leeres Feld als Zahlenwert liest.

**Unbestaetigt heisst: mit der BESTELLTEN Groesse weiterarbeiten und offen melden.**
Nicht auf 0 buchen (das erzeugt eine Position, die es nicht gibt), nicht abbrechen
(das verliert eine Order, die existiert). Die Position traegt ein Kennzeichen
(`fuellung_offen`), damit ein spaeterer Abgleich sie nachziehen kann.

### 15a. Eine Rueckdrehung gilt erst, wenn die BOERSE die Position nicht mehr fuehrt

"Verkauf abgeschickt" ist keine Rueckdrehung. Sie gilt als gelungen, wenn **danach
an der Boerse keine Position mehr steht** (`offene_positionen(inst)` leer). Sonst
gilt sie als Fehlgeschlagene - mit einer lauten Lueckenmeldung, nicht als Erfolg:

    verkauft, Boerse fuehrt weiter  ->  "SICHERHEITSLÜCKE: Stop fehlgeschlagen UND
                                        Rueckdrehung ohne Wirkung" + kein weiterer Einstieg

Im Fehlerfall wird ein zweites `except` geflogen; das ist richtig, deckt aber nur
den **Ausnahme**fall. Die Regel gilt fuer die stille Variante: der Aufruf kehrt
zurueck, die Boerse tut nichts, das Journal meldet Erfolg. Genau das ist der
gemessene Fall.

Merksatz: **ein Rueckweg, dessen Wirksamkeit nicht gemessen wird, ist eine Annahme.**
Jede Sicherung, die eine Lage zuruecknehmen soll, wird gegen die Boerse geprueft,
nicht gegen den Erfolg ihres eigenen Aufrufs.

## 16. Ein Einstiegs-Gate darf den Ausstieg nie sperren

Freigabe-Schalter, die einen NEUEN Markt eroeffnen sollen (z. B. "diesen vom
Prognose-Bericht gebrachten Namen noch nicht von Hand freigegeben"), sind **Einstiegs-
Tore**. Sie gehoeren nicht auf den Ausstiegspfad. Zwei Auspraegungen, beide gemessen:

- **Ein modulweiter Schalter, der nur im Einstiegszweig gesetzt wird.** Die
  Freigabe-Funktion schreibt eine Modulvariable; `pruefe_ausstiege()` laeuft mit
  dem Vorgabewert `False` und scheitert an **jedem** Kursabruf. Die Live-Position
  stand zwei Stunden da, waehrend jede Rueckrechnung denselben Fehler bekam - das
  Journal sah wie ein Datenproblem aus, nicht wie ein gesperrter Ausstieg.
  Loesung: der Aufrufer sagt, fuer welchen Zweck er aufloest -
  `pf_markt(inst, fuer_ausstieg=False)`, und der Ausstieg ruft mit `True`.
- **Eine Vorbedingung, die nur auf einem Weg hergestellt wird.** Gehoert eine
  Marktliste, Kennung oder Tabelle zum Aufloesen, muss **jeder** Weg sie laden, der
  sie braucht. Nur im Einstieg geladen heisst: auch ohne jedes Gate bleibt die
  offene Position unauflösbar ("Marktliste nicht geladen").

**Der Ausstieg umgeht die Freigabepflicht, NIE den Beweis.** Ein Ausstieg trifft
keine neue Marktwahl - er handelt in einem Markt, in dem bereits Position steht.
Deshalb darf `fuer_ausstieg` die Freigabe aufheben, aber nicht die Pruefung, ob es
diesen Markt ueberhaupt gibt (Kapitel 14: Namen normalisieren, nicht raten). Wird
auch das umgangen, ist ein Ausstieg in einem nicht belegten Markt moeglich.

Merksatz: **ein Gate, das einen Einstieg verhindert, ist ein Schutz; dasselbe Gate
auf dem Ausstieg ist eine Kette.** Wer eine offene Position nicht schliessen kann,
traegt sie - mit Margin, Funding und voller Unsicherheit, bis der Kurs laeuft.

## 6. Sperre aufloesen heisst: die Ursache mit aufloesen

Ein Kill-Switch setzt `handel_erlaubt=false` **und** stellt flach. Ein blosses
Zuruecksetzen des Schalters reicht nicht, wenn die Kurve die Schwelle noch
reisst: der naechste Zyklus stellt sofort wieder flach (und verkauft dabei die
gerade wiederhergestellte Position). Vor dem Entsperren:

- `lage()` fragen: `ruecklauf_usd` gegen `kill_switch_gesamt_usd`.
- Liegt der Ruecklauf darueber: Deckel anheben (mit datiertem Vermerk in
  `wachen.json`: `_entsperrt_von`, `_kill_switch_erhoeht`, Grund und Ruecknahme)
  **oder** bewusst flach bleiben. Beides ist eine Entscheidung von Max, keine
  stille Nebenwirkung.
- **Die Ratsche mitlesen:** `groessenfaktor` ist bei tiefem Ruecklauf reduziert -
  neue Positionen sind dann halb so gross. Das im Bericht nennen, sonst wirkt die
  Freigabe kleiner als erwartet.

## 7. Bedingung 4 (Spiegelung) gehoert an den ZYKLUSANFANG

Steht die Spiegelung nur am Ende des Zyklus, dann spiegelt ein Zyklus, der in die
Zeitgrenze laeuft oder abstuerzt, **gar nichts**: Q: bleibt stehen, und
`spiegelstand.py` meldet eine Abweichung, die wie ein Datenproblem aussieht.

- Deshalb: **zuerst** spiegeln (Stand des letzten Zyklus) **und** am Ende noch
  einmal. Damit ist die Kopie hoechstens einen Zyklus alt.
- Ein Vorschau-Lauf schreibt nichts - die Spiegelung dort nicht erwarten.
- Beweis: `mtime` von Q:-Datei gegen die lokale Datei halten, dann
  `spiegelstand.py` (muss alle Spuren byte-gleich melden).
- **Ein Ausgang kann jeden Ausgang vergessen** - der Zyklus hat mehrere
  (`--wachen`, "kein Bericht", abgebrochener Lauf, Notausstieg). Dagegen hilft ein
  Test, der die QUELLE liest und vor JEDEM `return` der `lauf()`-Funktion eine
  Spiegelung verlangt (`test_spiegelung_jeder_zyklus.py`): er faellt bei jeder
  neuen Rueckkehr, auch bei einer, die es heute noch nicht gibt. Eine Zusicherung
  auf "spiegelt am Ende" fangen den Fall nicht ab, weil der abgebrochene Zyklus
  das Ende nie erreicht.

## 8. Ein Dienstprozess ist keine Sitzung am Bildschirm

`isatty()` auf stdin ist bei einem Dienstprozess nicht verlaesslich - erbt er ein
Terminal, haelt sich die Spur fuer eine **Sitzung am Bildschirm** und wartet auf
eine Freigabe, die niemand geben kann. Symptom: jeder Zyklus laeuft in die
Zeitgrenze des Treibers (`TIMEOUT`, Rueckgabe 124), waehrend die Spur selbst
"nichts tut".

- Die Routine-Umgebungsvariable (z. B. `MAXHIRN_ROUTINE=1`) in **beiden** Modi
  setzen (Papier UND live) - nicht mit der Begruendung "bei live ist die Freigabe
  ohnehin erteilt" weglassen.
- Die Zeitgrenze eines Zyklus muss zum Aufwand der Spur passen (breite Scanner
  brauchen mehr als enge Signal-Spuren); eine zu knappe Grenze killt die Spur
  mitten in der Buchfuehrung.

## 10. Spuren ohne modus-Filter: Live-Lauf sendet echte Sell-Orders auf Papier-Positionen

Nicht jede Spur prueft `p.get("modus") == "live"` vor einem Boersen-Ausstieg.
In `swap/handeln.py` gibt es weder `bueche_papier_altlasten_aus()` noch einen
modus-Check in `pruefe_ausstiege()` — der Ausstiegspfad ruft `okxf.markt_schliessen()`
auf jede Position, unabhaengig davon, ob sie mit einer echten Order eroeffnet wurde.

Konsequenz: eine Papier-Position (kein `modus`-Feld, keine `kauf_txid`) hat im
Live-Lauf einen echten Market-Sell-Befehl zur Folge. OKX gibt einen Fehler zurueck
(Position existiert dort nicht), der in stderr landet; die Position verschwindet
trotzdem aus dem Buch. **Kein Geldverlust, aber ein blinder Boersenaufruf.**

Zusaetzliche Diagnosefalle: `buche_funding()` in swap schreibt `modus="live"` basierend
auf dem LAUFMODUS, nicht dem Positionsmodus. Eine Papier-Position in einem Live-Lauf
erhaelt funding-Eintraege mit `modus=live` — sieht wie eine echte Position aus.

- **Diagnose:** `grep -c ",live," <spur>/handelsjournal.csv` gegen `len(z["positionen"])
halten. Volles Buch ohne live-Kauf-/Verkaufszeilen = Papier-Geister. Dann je Position
`p.get("modus")` und `p.get("kauf_txid")` / `p.get("ord_id")` pruefen — `None`
bei `modus=live`-Lauf = Altlast.
- **Bereinigung:** Positionen ohne `modus='live'` (inkl. ohne Feld) per
  `buchbereinigung`-Eintrag ausbuchen: Journal-Zeile schreiben (Einstiegskurs als
  Preis), aus `zustand['positionen']` entfernen. Sicherung `.bak-JJJJMMTT` vorher.
- **Dauerhaft:** wie bei scanner/xperp ein `bueche_papier_altlasten_aus()` am Beginn
  jedes Live-Laufs einfuegen, und in `pruefe_ausstiege()` einen modus-Check:
  `if live and p.get("modus") != "live": behalten.append(p); continue`.

## 9. Tests schreiben nie ins echte Buch

`journal` und das Boersenmodul (`okxf`/`kraken`) im Test ersetzen; `SCHREIBEN`
aus, `zustand.json` nicht anfassen, `markt_schliessen`/`order_limit` als Mock -
sonst hinterlaesst ein Testlauf Positionen, die im Betrieb als Geister auftauchen.
Ein Modulwaechter (Dateiliste + Groessen vor/nach) faengt jeden Test, der nach
aussen schreibt.

## 11. "Ich habe von Hand geschlossen - wie reagiert der Dauerlauf?"

Reihenfolge im Live-Zyklus (`xperp/handeln.py`, sinngemaess in jeder Spur):
Papier-Altlasten ausbuchen -> wartende Auftraege abarbeiten -> **Geister gegen die
Boerse pruefen** -> Kill-Switch -> Herzschlag -> Ausstiege -> Einstiege. Der
Aufraeumteil laeuft VOR jedem neuen Einstieg, ein frei gewordener Platz wirkt
also im naechsten Zyklus.

- **Was hat der Nutzer getan?** Nicht aus dem Buch und nicht aus `pos=0`-Zeilen
  schliessen. Belege in dieser Reihenfolge:
  - `/api/v5/account/positions-history` (`realizedPnl`, `cTime`/`uTime`) - zeigt
    GESCHLOSSENE Positionen samt Ergebnis.
  - `/api/v5/trade/fills?instType=FUTURES` - einzelne Fuellungen. **XPERP-Kontrakte
    laufen unter `FUTURES`, nicht unter `SWAP`**: eine `instType=SWAP`-Abfrage
    liefert `[]` und liest sich wie "nichts passiert".
  - Boersen-Zeitstempel sind UTC - gegen die lokale Uhr umrechnen, sonst wirkt
    ein Vorgang von gerade eben wie von gestern.
  - Zeigen die Belege weniger Schliessungen als der Nutzer nennt, nachfragen -
    `positions-history` ist die Wahrheit, nicht die Erinnerung.
- **Was macht der naechste Zyklus?** Vollstaendige Schliessung -> Geist, wird
  ausgebucht (mit dem Verlust-Fehler aus 3b). Teilschliessung -> gar nichts (3a).
  Eine **Vorschau zeigt das nicht**: die Geisterpruefung liegt hinter dem
  Vorschau-`return` und laeuft nur im echten Live-Zyklus. Wer das Verhalten
  belegen will, liest den Code-Pfad oder wartet den Zyklus ab.
- **Wirkung vorhersagen statt behaupten:** die Runden mit der EIGENEN Funktion
  der Spur lesen (`wachen_xperp.runden_aus_journal`), daraus Hoechststand und
  Ruecklauf bilden und den hypothetischen Geister-Eintrag addieren. Eine im
  Bericht nachgebaute Formel prueft die Formel, nicht die Spur.
- **Kein Buchfeld erfinden:** fehlt z. B. `margin_usd` in `zustand.json`, kommt
  der Einsatz aus der `eroeffnen`-Zeile des Journals - nicht schaetzen.

## 12. Ein Konto, mehrere Spuren: die Kaufkraft ist geteilt

Spot-Kauf (scanner) und Perp-Margin (xperp) greifen auf DASSELBE Guthaben zu.
Fuellt eine Spur ihre isolierte Margin, sinkt die freie Kaufkraft der anderen -
**ohne Fehlermeldung in irgendeiner Spur**. Symptom: die Spur sagt "ok", die
Vorschau nennt keinen Sperrgrund, und es entsteht trotzdem keine Position.

- Massstab ist `availEq` je Waehrung (`/api/v5/account/balance?ccy=...`), NICHT
  `eq`. Liegt der freie Betrag unter dem Mindestbetrag der Spur, unterbleibt der
  Kauf ohne Sperrtext.
- Reihenfolge der Diagnose: **erst Guthaben lesen, dann Tore.** `availEq`,
  `frozenBal` und `isoEq` aus der Balance-Antwort nehmen; `isoEq` ist die Margin
  der offenen Positionen samt `upl`. Bleibt danach eine Luecke (OKX fuehrt z. B.
  einen `stgyEq`-Topf), ist sie NICHT aus den Positionen erklaerbar - das als
  offenen Befund benennen, nicht als Rechnung ausgeben.
- Die Zeile "Live waere gesperrt durch: nichts" heisst nur: **kein Tor sperrt.**
  Sie ist kein Beleg, dass ein Kauf zustande kommt.

## 13. Die Live-Sperre haengt am ORDERWEG, nicht am Schalter

Ein Sammelauftrag ("schalte alle Spuren scharf") setzt `handel_erlaubt=true` UND
`freigabe.erfuellt=true` in JEDER `wachen.json` — auch in Spuren, die gar keinen
Orderaufruf haben. Eine Live-Sperre, die nur diese zwei Felder liest, laesst
`--live` danach **ueberall** durch. Fuer eine Spur ohne Orderweg heisst das:
sie schreibt Buchungen mit `modus=live`, die an keiner Boerse existieren — genau
das Muster "Buch war Fiktion", nur diesmal vom eigenen Tor erzeugt statt von
einem Papierlauf.

- Die Sperre prueft den **Orderweg** (Konstante `LIVE_ORDERWEG = False` bzw. das
  Vorhandensein des Boersenmoduls), nicht die Schalter. Ein Schalter, der
  ueberall an ist, sagt nichts mehr.
- Die Entscheidung als **reine Funktion** bauen (`live_gate(modus) -> (modus,
  meldung)`), die `main()` aufruft: so kann der Test beide Faelle pruefen, ohne
  `main()` zu starten — und ohne dass ein Testlauf in das echte Buch schreibt.
- Der Text nennt den GRUND ("diese Spur hat keinen Orderaufruf"), nicht nur das
  Ergebnis; sonst sieht die Verweigerung wie ein fehlender Schalter aus und wird
  beim naechsten "schalte alles scharf" wieder aufgemacht.
- Gegenprobe: `handeln.py --live` im Kindprozess starten und pruefen, dass die
  Verweigerungszeile kommt — nicht nur, dass `wachen.json` false traegt.

## 14. Beim Abgleich Namen normalisieren, nicht vergleichen

Dieselbe Boerse nennt dasselbe Paar in zwei Schreibweisen: Kraken traegt in der
Order-Anfrage `XXBTZEUR`/`XETHZEUR`, in der Liste der offenen Orders aber
`XBTEUR`/`ETHEUR`. Ein Abgleich ueber den rohen String findet dann 1 von 3 Stops
und liest sich wie eine Datenluecke ("Kennung fehlt") statt wie ein Namensproblem.

- Vor jedem Vergleich **auf (Basis, Quote) zurueckfuehren** (X/Z-Praefixe und
  Fuellzeichen entfernen, Gross-/Kleinschreibung vereinheitlichen) und erst dann
  paaren; die Normalisierung gehoert in EINE Funktion, die alle Aufrufer nutzen.
- Dasselbe gilt fuer Instrument-Schreibweisen zwischen den Boersen (OKX `BTC-USDC`
  gegen Kraken `XXBTZEUR`) — eine Abbildungstabelle, kein `if` je Aufrufstelle.
- Ein Abgleich, der weniger Treffer liefert als erwartet, ist zuerst ein
  Namensverdacht, dann erst ein Datenverdacht. Beleg: nach der Normalisierung
  fanden sich alle drei Stop-Kennungen, ohne dass sich an der Boerse etwas
  geaendert hat.

## 17. Unklare Position: die Reihenfolge der Zeugen, und was NICHT angefasst wird

Auftrag der Form „X-Verwirrung klaeren auf <Boerse>“: an der Boerse stehen
Position und offene Orders, das Haus fuehrt Buch, Journal und Spiegel, und die
Zahlen sagen nicht dasselbe. Fuenf Regeln, alle aus einem gemessenen Fall
(Position, deren Groesse im Buch rund 5 % ueber der Boerse lag, zwei
Order-Saetze mit fremder Menge an derselben Position und ein Stop 1,3 % unter
dem Kurs).

1. **Boerse zuerst, vollstaendig: Position UND offene Orders.** Eine
   Orderliste ohne die Position sagt nichts darueber, ob die Orders gehoeren.
   Dann das Buch, das die Position fuehrt, dann Journal und Spiegel - nur um zu
   pruefen, ob das Haus sie ueberhaupt kennt. Nie umgekehrt: ein Journal ist
   eine Behauptung des Hauses. Ein MCP-Werkzeug ist die bequemere Abfrage,
   ersetzt den Haus-Weg im Spurenbaum aber nicht; liefert es nichts (der
   Kraken-Server verliert gelegentlich seinen stdio-Kindprozess), ist der
   Haus-Weg der Zeuge.

2. **Zuordnungsschluessel ist das Tripel (Menge, Kurs, Zeitstempel).** Passt die
   Menge zu keinem Buch und zu keiner Journalzeile, ist die Order fremd.
   **Fremde Orders werden nicht angefasst** - sie sind Max' Geld und Max'
   Order. Erst benennen lassen, dann stornieren, und nie im Rahmen einer
   „Klaerung“ mitnehmen. Zwei Saetze (Stop + Ziel) an einer Position sind
   normal; drei oder mehr mit verschiedenen Mengen sind der Befund.

3. **Die Stop-Groesse gehoert an die GEFUELLTE Menge, und `unfilledSize` wird
   gegen die Positionsgroesse gestellt - nicht als Rundungsrest gelesen.**
   `reduceOnly` verhindert den Fehlverkauf ueber die Positionsgroesse hinaus,
   aber es verhindert NICHT, dass der Stop feuert und die ganze Position
   mitnimmt. Ein Stop mit `unfilledSize` groesser als die Position gehoert zu
   einem anderen Kauf - dieselbe Luecke wie in 3a, nur an der Order statt am
   Buch, und dieselbe Konsequenz: Soll gegen Ist je Kontrakt, vor JEDER
   Order-Aktion.

4. **Die Stop-DISTANZ zum Kurs entscheidet die Reihenfolge, nicht der
   Stoppreis.** Je Liste `(Kurs - Stop) / Kurs` in Prozent ausgeben, aufsteigend
   sortiert. Gemessen: der eigene Notaus lag 11 % unter dem Kurs, ein fremder
   Stop 1,3 % - bei 1,3 % ist die Position weg unabhaengig von allem, was im
   Buch steht. Ohne diese Distanz nennt man vier Preise und der Leser kann die
   Dringlichkeit nicht sehen. Ein **Take-Profit, der ein Vielfaches des
   Einstiegs ist** (gemessen 3,05x), ist ein Befund zum Nennen (Verdacht auf
   Zahlendreher, Sollwert des Buchs daneben) und **kein Wert, den man
   repariert**.

5. **`ok` im Dauerlauf-Log ist ein MODUS, kein Beleg.** `(live) ok` heisst: der
   Kindprozess ist mit dem Modus live beendet worden - nicht, dass die Position
   behandelt wurde. Ein Beleg ist eine Journalzeile oder eine Aenderung an der
   Boerse. Ebenso endet eine Fehlerreihe nicht mit dem Zustand: eine Spur, die
   ihre Live-Position nicht schliessen kann (Abschnitt 16), schreibt dieselbe
   Zeile im Viertelstundentakt weiter, waehrend der letzte Lauf `ok` meldet.
   Also die letzten N Fehlerzeilen der Spur lesen, nicht die letzte
   Protokollzeile.

Ein Symbol in vier Papierbuechern und an der Boerse ist kein Widerspruch,
sondern Normalfall: alle Fundstellen mit Modus nennen und sagen, dass kein
Papierbuch etwas an den Boersen-Orders aendert - sonst entsteht der Eindruck,
man muesse die Buecher „in Uebereinstimmung bringen“, ein Schritt, der nichts
loest und Papierpositionen zerstoert.
