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
- Dasselbe gilt fuer `pruefe_ausstiege` im Papiermodus.
- Beim Wiederherstellen einer echten Position: Werte aus der ERoeffnungszeile des
  Journals nehmen, nichts schaetzen, und eine eigene Journal-Zeile mit
  `grund=buchwiederherstellung` schreiben, damit der Eingriff nachvollziehbar ist.
  Sicherung der Zustandsdatei vorher anlegen.

## 5. Nach jeder Wiederherstellung: hat die Position einen Stop?

`attachAlgoOrds` werden beim Fuellen aktiv - greift das nicht (z. B. weil die
Order erst spaeter fuellte oder ein Storno dazwischenkam), liegt die Position
**ohne boersenseitigen Stop**. Pruefen mit
`/api/v5/trade/orders-algo-pending?instType=FUTURES&ordType=conditional`.
Ist die Liste leer, den Stop mit den Werten der Eroeffnungszeile nachsetzen
(`/api/v5/trade/order-algo`, `ordType=conditional`, `slTriggerPx`, `slOrdPx=-1`,
`reduceOnly=true`, Gegenrichtung der Position). Eine gehebelte Position ohne Stop
laeuft bis zur Liquidation, wenn der Rechner ausfaellt.

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
