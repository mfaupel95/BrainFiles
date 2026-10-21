---
name: handel-risikosteuerung
description: "Use when eine Risikoschranke ueber das Buch gebaut wird."
category: brainfiles
platforms: [windows]
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Handel, Risiko, Deckel, Wachen, BrainFiles]
    related_skills: [handel-spuren, handel-spur-optimierung, trugschluesse]
---

# Risiko ueber das ganze Buch steuern

## When to Use

- Ein Konzentrationsdeckel wird verlangt („kein Instrument darf mehr als X %
  tragen"), oder eine bestehende Grenze soll je Basis gelten.
- Eine offene Position liegt ohne Schutzstop im Buch.
- Eine stehende Wache soll Belastung, Konzentration oder fehlenden Schutz melden.
- Vor einer Kapitalentscheidung oder einem Bericht ueber das Haus gefragt wird:
  „auf was liegt eigentlich das meiste Geld?".

## Wann
Eine Schranke ueber **alle** Spuren, nicht ueber eine: Deckel auf Konzentration
(„kein Instrument darf mehr als X % tragen"), Gruppierung nach Basis, ein
Schutz auf einer bereits offenen Position, oder eine stehende Wache, die
Belastung meldet. Abgrenzung: eine einzelne Spur anbinden/auswerten steht in
`handel-spuren`, eine Spur mathematisch verbessern in `handel-spur-optimierung`,
Zustaende belegen statt vermuten in `trugschluesse`.

Die Hausregel gilt unveraendert: **kein Geld selbst bewegen.** Jede Massnahme,
die eine bestehende Position schliesst, ist eine Order und gehoert in die
Freigabekette — eine Schranke bauen heisst nie, eine Position aufzurueumen.

## Reihenfolge — nicht abkuerzen

1. **Das Buch lesen, nicht die Notizen.** Alle Risikostufen einbeziehen: Basis,
   `.mittel`, `.hoch` sind drei Buecher, aber **ein** Haus. Ein Deckel, der nur
   die Basis sieht, ist an den Tagen falsch, an denen eine andere Stufe laeuft.
   Je Position gehende Felder sammeln: Instrument, Seite, Einstieg, Stop, Nominal.
2. **Zwei Linsen trennen und beide nennen.** *Risiko* = Abstand Einstieg/Stop auf
   das Nominal. *Kapital* = das Nominal selbst. Beide addieren sich je Position
   korrekt (jede Position hat ihren Stop); gestapelt ist das **Kapital auf einer
   Basis**. Die Differenz zwischen SpURENSUMME und BASIS-SUMME ist deshalb
   **keine** „Doppelzaehlung" — wer sie so nennt, hat die Rechnung nicht
   verstanden und korrigiert dann die falsche Zahl.
3. **Nach kanonischer Identitaet gruppieren, nie nach dem Symbol-String.** Alle
   Schreibweisen einer Basis fuehren auf EINEN Namen: Perp-Suffix (`-SWAP`),
   Perp-Bindung (`_UM_XPERP`), Quote-Anhaenge (`-USDC`, `-USDT`, `-USD`, `-EUR`)
   und boerseneigene Abweichungen (Krypto-Bitcoin heisst je nach Boerse `BTC`
   oder `XBT` — beide gehoeren zusammen). **Ein Deckel, den man mit einem
   anderen Namen umgeht, ist kein Deckel.**
4. **Eine Position ohne Schutzstop ist kein Befund nebenbei, sie ist der
   Befund.** Sie ist nicht risikofrei, sie ist der **ganze Einsatz** offen. Sie
   gehoert in die erste Zeile der Meldung und in den Betrag, mit dem die
   Gesamtzahl nach der Korrektur sinkt.
5. **Ein Deckel bindet NEUE Einstiege, nie bestehende Positionen.** Wer eine
   Basis einmal ueberschreitet, hat sie schon bezahlt — das Kapital lag schon
   drin. Ein Deckel, der beim Start sofort N Spuren einfriert, ist ein
   Abschaltknopf mit anderem Namen. Bestehende Positionen laufen unter ihren
   gebuchten Stops und Fristen aus; sie zu schliessen ist eine Order.
6. **Der Deckel ist eine Tabelle, keine Zahl.** Je Basis eine Grenze plus der
   Grund im Wachen-Kommentar. Ein Sonderfall ist immer eine Entscheidung, die man
   begruendet — nicht ein Wert, den man nachjustiert, weil eine Basis knapp
   drueber liegt.
7. **Das Tor gehoert an den ORDERAUFruf, nicht in die Signalberechnung.** Eine
   Spur, die ein Signal sieht und es nicht handelt, sieht fuer tot aus; eine
   Stille-Wache wuerde sie als tot melden, ohne zu wissen warum. Am Orderweg
   wird der Einstieg abgelehnt und protokolliert — die Spur laeuft weiter und
   sieht gesund aus. Jeden echten Orderweg pruefen: das gemeinsame Buch
   (`spur_buch.sperren_live()`) **und** der asynchrone Executor. Fehlt die
   Verdrahtung in einem von beiden, ist die Schranke halb gebaut.
8. **Die Wache meldet eine Veraenderung, nie den Stand.** Sonst wird sie
   abgeschaltet und damit blind. Verglichen wird gegen den letzten Lauf, nicht
   gegen gestern.

## Offene Börsenpositionen: das Hausbuch ist nicht die Wahrheit

Bricht der Positionsschutz an einer Live-Spur, ist die erste Frage **woher die
Position stammt** — nicht welcher Stop fehlt. Eine Position, die du selbst per
Order eröffnet hast, steht im Hausbuch; eine von Hand, von einem Bot oder von
einer Parallelsitzung geöffnete steht nur an der Börse. Das Buch kann dabei
laut und falsch sein.

**Die drei Fälle, alle drei gemessen:**

1. **Das Buch behauptet einen Schutz, den die Börse nicht hat.** Eine
   `fremdposition_uebernommen`-Buchzeile trägt Stop *und* Ziel, weil die
   Spurenlogik sie so befüllt — geprüft an der Börse war dort nichts. Der
   Buch-Stop ist eine Absichtserklärung, kein Auftrag.
2. **Die Börse hat einen Schutz, den das Buch nicht kennt.** Zwischen zwei
   Messungen (Minuten) lag ein vollständiger OCO auf der vollen Menge. Die
   Grundlage ist eine Live-Spur oder ein Bot; das Buch führt die Position erst
   danach.
3. **Die Menge passt nicht.** Nachkauf- oder Teilausstiegsleiter hinterlassen
   Stops, deren `sz` nicht zur Position passt: 67 % geschützt, ein Posten mit
   `sz=0`, oder 107 % (zwei Stops auf getrennten Teilmengen plus Rest).

**Die Messung ist eine Tabelle aus zwei Abfragen, nicht eine Zahl:**

- `GET /api/v5/account/positions?instType=FUTURES` → Position, Seite, Menge,
  `avgPx`, `markPx`, `liqPx`, `mgnMode`, `lever`
- `GET /api/v5/trade/orders-algo-pending?ordType=<typ>` → die Schutzaufträge

**Alle drei ordTypes lesen**: `conditional`, `oco` und `trigger`. Ein OCO trägt
Stop *und* Ziel in einem Auftrag, ein `conditional` nur einen — wer nur einen
Typ liest, meldet eine vollgeschützte Position als halb geschützt oder
umgekehrt. Der Endpunkt liefert **nur lebende** Aufträge; ein erfüllter oder
stornierter Posten taucht nicht mehr auf, sein Fehlen ist also kein Beweis,
dass nie einer da war.

**Die Kennzahl ist die SUMME der Mengen auf der Schutzseite**, nicht der
größte Einzelwert: zwei halbe Stops schützen nicht so viel wie ein ganzer.
Für einen Long zählt `side=sell`, für einen Short `side=buy` — Posten der
Gegenseite gar nicht. Überdeckung (>100 %) ist ein eigener Befund, keine
Genauigkeit.

**Vor jeder Aktion den Zustand neu lesen.** Zwischen Analyse und Handlung
ändert sich das Konto: Mengen wachsen, Stops werden nachgesetzt. Wer eine
Minute später auf einer alten Tabelle handelt, setzt eine zweite Schutzebene
auf eine bereits gesicherte Position — das ist kein Fehler, den man bemerkt,
sondern einer, der beim ersten Treffer doppelt verkauft.

**Ist die Position bereits vollständig geschützt, ist die Handlung „nichts".**
Der Auftrag „setz intelligen Take-Profit in Stufen" bedeutet nicht „setze
zusätzlich Stufen": liegt ein OCO auf der vollen Menge, heisst die Antwort
„das ist bereits gedeckt, hier ist die Lücke in einer anderen Position", nicht
eine weitere Order.

## Einen gestuften Take-Profit rechnen

Take-Profit in Stufen ist eine **Mengenrechnung zuerst**: die Summe der
Teilmengen muss exakt die Position ergeben. Ein Restbetrag ist entweder eine
Order, die die Börse ablehnt, oder eine Teilmenge, die ungeschützt bleibt, weil
der Stop auf den vollen Bestand zeigt.

- **Rest auf die frühen Stufen**, nicht auf die letzte: ein Rest auf der letzten
  Stufe bleibt bis zum letzten Treffer ungeschützt.
- **Der Stop wird zuerst gesetzt**, dann die Stufen. Eine TP-Stufe ohne Stop
  ist eine Position, die beim nächsten Neustart des Algo-Bestands nackt dasteht.
- **Ein eigener Orderweg statt eines allgemeinen Helfers.** Ein Helfer, der für
  Spot geschrieben wurde (`tdMode: cash`, `side: sell` fest verdrahtet), lehnt
  auf einem Perpetual ab — und ein stillschweigend falsch gesetzter Schutz ist
  schlimmer als keiner. `tdMode` folgt der Position (`cross`/`isolated`), die
  Seite folgt der Seite der Position.
- **Marktauslösung, nicht Limitpreis** (`slOrdPx: -1` / `tpOrdPx: -1`): bei
  einem Momentum-Ausbruch verpasst ein Limitpreis genau den Move, der ihn
  ausgelöst hat.
- **Gleichverteilte Stufen zwischen Einstand und Ziel**, jede 1/n der Menge.
  Eine risikogewichtete Staffelung (frühere Stufen näher am Einstand) löst bei
  einem 0,03-USD-Instrument nichts — die Gebühr je Seite frisst den ersten
  Abstand auf.
- **Rechnung im Bericht, keine Formel im Skript:** Triggerpreis, Abstand in
  Prozent, Menge, Erlös je Stufe und die Summe. Ein Nutzer, der eine Order
  freigibt, will die fünf Zahlen sehen, nicht den Aufruf.

## Pitfalls

- **Skripte direkt in `Agenten/Handel` brauchen `HANDEL = HIER`, nicht
  `os.path.dirname(HIER)`.** Im zweiten Fall zeigt der Pfad auf `Agenten/`, die
  Spur-Schleife laeuft ins Leere und das Ergebnis lautet „keine offenen
  Positionen im Haus". Das ist schlimmer als ein Absturz: die Zahl sieht aus wie
  ein Befund und ist keiner. Fuer Dateien **unter** `Agenten/Handel/<spur>/` gilt
  weiter `HANDEL = os.path.dirname(HIER)`.
- **Die Merkdatei einer Wache speichert Strings, keine Tupel.** JSON schreibt
  Tupel als Listen und laesst sie als Listen zurueckkommen; der Vergleich
  passt dann nie, und dieselbe Meldung kommt bei **jedem** Lauf wieder — genau
  so wird eine Wache abgeschaltet.
- **Eine geratene Schwelle verfehlt den Wert knapp darunter.** Neben der
  Schwelle immer die **Top-N** unbedingt ausgeben: die Frage „auf was liegt das
  meiste Geld" faellt auch dann an, wenn die Antwort knapp unter der Grenze
  liegt.
- **Die Polaritaet eines Rueckgabewerts ist Teil des Vertrags.** `liefert
  (gesperrt, grund)` und im Test als `(offen, grund)` gelesen heisst: drei
  Tests melden das Gegenteil. Steht im Docstring, und die Testvariable heisst
  nach dem **Wert**, nicht nach der Hoffnung.
- **Pfade aus `__file__`: die Ebenen zaehlen.** `os.pardir` zu oft oder zu
  selten ergibt `ModuleNotFoundError` auf ein Modul, das sehr wohl im Haus liegt.
- **Ein Gate-Schluessel, der beim Aufruf still verworfen wird, sieht wie eine
  Messung aus.** Nach dem Bau immer **zwei** Werte gegen dieselbe Grundlage
  fahren und die Zahlen vergleichen; sind sie gleich, ist nicht der Markt
  schuld, sondern die Verdrahtung.
- **Ein Vergleichsschalter braucht einen Gegenbeweis.** „Der Arm legt seine
  eigene Dateien an" ist zuwenig — zusaetzlich pruefen, dass der Hauptarm
  unangetastet blieb (Aenderungszeitstempel vorher/nachher).
- **Eine Börse kennt zwei Kontostände, und beide sind richtig.** Auf der
  Kontoebene steht die Gesamtsumme, aber die *freie* Position steht als leerer
  String und der Staking-Anteil als `null`. Die belastbaren Werte je Währung
  stehen in der Detailliste. Wer die Kontoebene liest, meldet für ein Konto mit
  950 Einheiten „0.00" — und das sieht wie ein leeres Konto aus, nicht wie ein
  Fehler.
- **`frozenBal` heißt bei OKX nicht „eingefroren".** Es ist die an Margin,
  offene Orders und Algo-Orders **gebundene** Summe. Als „eingefroren"
  etikettiert liest sie sich wie gesperrtes Kapital, das man freischalten muss.
- **`positions` kennt kein `instType=SPOT`** und lehnt es mit einem
  Parameterfehler ab. Spot-Bestand kommt aus `account/balance`, keine
  Position im Sinne einer Absicherung.
- **Ein Kontrollwert, der zwei Nullen vergleicht, ist keine Kontrolle.** Summiere
  die Detailzeilen und vergleiche sie mit der Gesamtsumme — bei Null und Null
  ist das grün, ohne dass irgendetwas geprüft wurde. Das ist der Fall, in dem
  eine Prüfung den Fehler *bestätigt* statt ihn zu finden.
- **Ein Helfer darf eine Aufrufform haben, nicht zwei.** Ein Helfer mit
  `zahl(wert)` und `zahl(container, feldname)` wird irgendwann verwechselt, und
  die Verwechslung faellt still aus: der Wert landet als Feldname in einer
  Suche und das Ergebnis ist 0,0 statt der echten Zahl. Beschreibe die Form
  einmal und rufe sie ueberall gleich auf.
- **Bedingung 5 (rollierender EV) ist eine harte Code-Schranke ohne
  wachen.json-Schalter.** Anders als die Freigabe-Bedingungen (netto-positiv,
  Wochen, Runden), die per `_entfaellt`-Vermerk gelockert werden, sperrt
  `ev_negativ = ev < 0` die Spur hart — es gibt keinen Schalter in der Wachen.
  Vor „Live stellen" die echten Sperrgruende pruefen (`--vorschau` mit
  `MAXHIRN_ROUTINE=1`): nennt die Ausgabe Bedingung 5, ist ein
  wachen.json-Schalter wirkungslos; die Schranke braucht eine Code-Aenderung
  oder einen ausdruecklichen `_ev_entfaellt`-Vermerk (Risikoentscheidung Max).
- **Ein Schalter fuer Live-Verhalten ist wirkungslos, solange die Spur als
  Papier laeuft.** Ein Schalter, der das automatische Schliessen von
  Live-Positionen steuert, greift nur im Live-Modus; im Papierlauf werden
  Live-Positionen nie geschlossen, unabhaengig vom Schalter. Vor der Zusage
  „der Schalter wirkt" pruefen, dass das Freigabefenster offen ist und die
  Spur wirklich live laeuft — sonst ist die Aenderung inert und die
  Handpositionen bleiben stehen, obwohl der Schalter auf true steht.
- **`json.dump(..., sort_keys=True)` schreibt die ganze Datei neu.** Ein
  einzelner neuer Schluessel in einer wachen.json wird so zu einem
  Ganzdatei-Diff (alle Schluessel umsortiert) — Konfliktrisiko mit parallelen
  Sitzungen und unlesbarer Commit. Den Schluessel gezielt einfuegen (bytes
  lesen, an der Stelle einsetzen) statt die Datei neu zu serialisieren; den
  inhaltlichen Diff gegen HEAD~1 pruefen, wenn doch neu geschrieben wurde.

## Verification

Der Auftrag ist fertig, wenn diese vier Zeilen sichtbar sind:

1. **Wirkung als Zahl.** Gesamtrisiko vor/nach der Aenderung; die Differenz
   muss genau der erklaerte Betrag sein (eine nachtraeglich gesetzte Schranke
   senkt das Gesamtrisiko um `Einsatz − Restrisiko`).
2. **Der Deckel ist nicht umgehbar.** Zwei oder mehr Schreibweisen derselben
   Basis gegen das Tor fahren — alle muessen dasselbe ergeben.
3. **Die Wache schweigt, wenn nichts passiert.** Erster Lauf meldet, zweiter
   schweigt; das Loeschen der Merkdatei laesst sie wieder melden (sonst prueft
   der Test einen Zustand, nicht eine Funktion).
4. **Jede neue Spur hat ihr eigenes Spiegelziel.** Hauptarm und Schattenarm auf
   dasselbe `Q:\`-Verzeichnis zu schreiben erfuellt Bedingung 4 durch
   Ueberschreiben, nicht durch Spiegeln.

Sammelnachweis:

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && \
  ./scanner/.venv/Scripts/python.exe basis_deckel.py && \
  ./scanner/.venv/Scripts/python.exe spiegelstand.py
```

## Reference

Wo der Schutzstopf auf einer bereits offenen Position hingehört — je nach
Ausstiegsmodell (Gitter, Trend, Zeitfenster, reiner Notaus) — und wie man die
Distanz aus der Geometrie der Spur ableitet:
`references/schutzstopf-platzierung.md`.