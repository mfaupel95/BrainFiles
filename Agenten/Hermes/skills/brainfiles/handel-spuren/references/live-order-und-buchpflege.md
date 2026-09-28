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
  geaendert hatte.
