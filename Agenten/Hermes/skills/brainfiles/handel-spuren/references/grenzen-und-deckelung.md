# Grenzen einer Spur: welche Zahl bindet, und der Deckel vor dem Fenster

Fuer Auftraege der Form „Limit pro Trade X, insgesamt Y“, „Deckel hochschrauben“,
„handel erlaubt“ — also Aenderungen an den GRENZEN einer bestehenden Spur. Gilt
fuer Papier- und Live-Grenzen gleichermassen; die Live-Grenzen heissen eigen
(`live_*`).

## 1. Wer liest die Zahl, die ich aendere?

Vor jeder Aenderung greppen, wer den Schluessel liest — nicht nur, wo er steht:

```
grep -rn "live_max_pro_trade_usd\|live_max_gesamt_usd\|max_pro_trade_usd" <spur>/
```

- Ein Grenzwert wird fast immer ueber einen **einen Leser** geholt
  (`_live_grenze(w, "max_pro_trade_usd", <ersatz>)` liest `live_max_pro_trade_usd`,
  sonst den Papierwert), damit Papier und Live getrennte Zahlen haben. Wer den
  Papierwert aendert und den Live-Treffer meint, hat nichts geaendert.
- **Ein Kommentar-/Vermerkfeld ist keine Messung.** Gemessen: der datierte Vermerk
  an der Grenze nannte „10“, der tatsaechliche Wert war 50 — ein alter Text, der wie
  eine Tatsache aussieht, kostet eine ganze Runde. Nach jeder Aenderung den VERMERK
  mitziehen und die alten Zahlen darin richtigstellen; sonst fuehrt die naechste
  Sitzung mit einer falschen Zahl.

## 2. Welche der vier Grenzen bindet?

Es gibt vier Kandidaten, und nur einer ist der Engpass. Rechne sie aus und NENNE
den bindenden, statt die Aenderung zu feiern:

| Grenze | Wirkung |
|---|---|
| Betrag **je Trade** (`live_max_pro_trade_usd`) | deckelt den einzelnen Einsatz |
| **Gesamt**deckel (`live_max_gesamt_usd`) | deckelt die Summe aller offenen Positionen |
| **Plaetze** (`live_max_offene_positionen`) | deckelt die Zahl der Positionen |
| **Guthaben** in der Kontowaehrung | deckelt alles zusammen, unabhaengig von der Konfiguration |

Merksatz: **Plaetze x Betrag gegen den Gesamtdeckel halten.** 5 Plaetze a 100 =
500 bei Deckel 400 heisst: ab der vierten Position ist nicht mehr der Betrag der
Engpass, sondern der Deckel. Der Guthaben-Deckel schlaegt beide, sobald das freie
Guthaben kleiner ist als Betrag x Plaetze — das ist der Normalfall und kein Fehler.

## 3. Den Einsatz auf das freie Guthaben deckeln — VOR dem Freigabefenster

Ein Betrag, den die Boerse gar nicht deckt, ist kein Grenzproblem, sondern eine
abgelehnte Order: sie schreibt eine Fehlerzeile ins Journal und sieht wie ein
Defekt aus, obwohl die Spur richtig gerechnet hat. Deshalb steht die Deckelung
**vor** der Anzeige des Freigabefensters und vor der Mengenrechnung:

```python
def betrag_gedeckelt(betrag, w):
    """Einsatz auf das FREIE Guthaben deckeln (Gebuehr + etwas Luft)."""
    frei = op_guthaben(GUTHABEN_WAEHRUNG)
    if not frei:
        return betrag, "kein freies %s-Guthaben gemeldet" % GUTHABEN_WAEHRUNG
    geb = float(w.get("gebuehr_taker", 0.006) or 0.0)
    deckel = frei * (1 - geb - 0.002)
    if betrag <= deckel:
        return betrag, None
    return deckel, "Einsatz %.2f -> %.2f EUR gedeckelt (%.2f frei)" % (betrag, deckel, frei)
```

- **Keinen neuen Mindestbetrag erfinden:** reicht der gedeckelte Betrag nicht fuer
die Mindestmenge des Paares, lehnt die vorhandene Mengenrechnung ab (`menge_fuer`).
- **Die Gebuehr des VENUE nehmen, nicht die der Heimatboerse** (Kraken taker 0,6 %,
  Deribit anders, OKX anders) — sonst ist der Deckel zu hoch und die Order platzt
  genau an der Grenze.
- Die Deckelung **sichtbar machen** (`print` in der Vorschau): bei der Frage
  „warum ist die Position kleiner als eingestellt?“ ist diese Zeile die Antwort.
- Gilt auch beim Guthabentor (`mindest_guthaben_*`): erst pruefen, ob das Tor noch
der Verwendung entspricht (ein Tor „3 x Einsatz 30 = 100“ ist veraltet, wenn der
Mindesteinsatz laengst 60 ist), dann erst die Zahl senken.

## 4. Ein wiederholtes Signal: die Position vergroessern, nicht verdoppeln

Faellt das NEBEN Signal fuer dasselbe Instrument in derselben Richtung, ist die
Antwort nicht eine zweite Position. Gemessen: vier Spuren haelten 3-4 Positionen
auf EINEM Instrument (macd_mtf vier lange ETH, supertrend vier kurze BTC,
wavetrend drei, kopier1zu1 fuenf auf zwei Memecoins). Der Platzzaehler
`max_offene_positionen` zaehlt damit die PositionsANZAHL statt des eingesetzten
Kapitals — vier halbe Positionen sind fuer das Risiko dasselbe wie eine volle,
aber viermal so teuer im Platz.

Die Regel gehoert an **eine** Stelle (`Handel/skalieren.py`), nicht in jede Spur:

```python
offen = finde_offene(z["positionen"], inst, seite)   # gleiches Instrument UND Seite
if offen is not None:
    f = skaliere(offen, einstieg, nominel, stop_pct, r)
    # Journal: zweite Kaufzeile, GLEICHE pos_id, KUMULATIVER Einsatz, GEWOGENER Preis
    return
z["positionen"].append(_p)
```

Drei Regeln, alle aus dem Messfall:

1. **Der Einstieg wird der GEWICHTE Mittelpreis** (`(alt_ein*alt_nom + neu*nom)/summe`).
   Der rohe neue Preis macht aus zwei Signalen eine falsche Basis.
2. **Stop und Ziel entstehen NEU aus diesem Einstieg** und demselben Prozentsatz.
   Sonst laufen Stop, Ziel und Groesse auseinander — und ein alter Stop an einem
   groesseren Einsatz ist genau der Fehler, den die Stopdeckung sucht.
3. **Ein Seitenwechsel ist KEIN Skalieren.** Er ist ein neues Signal mit eigener
   Richtung und gehoert als eigene Position ins Buch.

**Die Journalform ist die heikle Stelle.** Die Skalierungszeile traegt den
KUMULATIVEN Einsatz, nicht ihr eigenes Stueck: bei Erloes 1200 und zwei Kaeufen
ueber je 500 gibt die Inkrementform +700 statt +200 aus — eine Trefferquote, die
keine ist.

**GEMESSEN, welche Zeile die Zuordnung nimmt: die LETZTE.** `journalpaarung`
ordnet nach `pos_id` und nimmt bei mehreren Zeilen derselben Kennung die zuletzt
geschriebene — also nach dieser Regel genau den kumulativen Stand. **Bau darum
KEINE eigene Verdichtung in den Rechenweg.** Genau das wurde zuerst gebaut, die
Gegenprobe blieb gruen (mit stillgelegter Regel meldete derselbe Test weiter
`+200`), also war der Code toter Code: der Pfad erfuellt die Aufgabe bereits. Ein
Rechenweg mit toter Logik ist eine Last, kein Beleg — nach jeder Verdachts-
Ergaenzung in einer Auswertung zuerst die Gegenprobe fahren und dann suchen, wer
die Aufgabe WIRKLICH erledigt, bevor man den eigenen Teil stehen laesst.

Merksatz: **Skalieren passt zur gemessenen Form einer Strategie** — zu einem
duennen Signal mit wenigen, grossen Gewinnern. Bei einer Strategie ohne Richtung
vergroessert es nur das richtungslose Exposure. Vorher die Trefferquote messen.

### 4b. Die ALTEN Stapel aufraeumen (die Regel wirkt erst auf neue Signale)

Die Skalierungsregel aendert nichts an Positionen, die schon offen sind — ein
Stapel bleibt, bis das naechste Signal auf dieselbe Richtung trifft. Wer ihn
vorher weghaben will, raeumt ihn ab, und das ist eine **Buchhaltungs-
Bereinigung**, keine Handelsrunde:

- Die groesste Position der Gruppe bleibt, ihre `pos_id` bleibt. Die uebrigen
  werden in sie eingerechnet: gewichteter Einstieg, Summe des Nominals, Stop und
  Ziel neu aus dem gemittelten Einstieg (wie beim Skalieren).
- Jede weggefallene Position bekommt eine `verkauf`-Zeile mit einem Grund, der
  `buchbereinigung` enthaelt (`stoerungen.BUCHHALTUNG`). Damit erscheint sie in
  KEINER Kennzahl als Runde und die Trefferquote bleibt unberuehrt. **Ihr Erloes
  ist der neue gewogene Einstieg** — der Ausgleich ist exakt null und erfindet
  weder Gewinn noch Verlust. Ein Ausstieg zum Kurs wuerde eine Phantomrunde
  erzeugen, die in der Quote steht.
- Die behaltene Position bekommt eine `kauf`-Zeile mit kumulativem Nominal und
  gewogenem Einstieg (dieselbe `pos_id`), weil die Zuordnung je `pos_id` die
  letzte Kaufzeile nimmt.
- **Vorher das Schema pruefen, nicht danach.** Gruppiert wird nach (Instrument,
  Seite); fuehrt eine Spur diese Felder nicht (etwa weil sie `symbol`/`token`
  statt `inst` benutzt), liefert der Schluessel `None`, ALLE Positionen dieser
  Spur landen in EINER Gruppe, und das Werkzeug verschmilzt das ganze Buch. Dann
  gehoert die Spur aus dem Lauf, nicht in die Ausgabe (Regel dazu in
  `anbindungs-audit.md`).

Vorschau ist der Standard; die Summenzeile der Vorschau muss die Summe BEIDER
Seiten zeigen (`vorher` und `nachher` des Nominals) — ein Werkzeug, das nach dem
Zusammenfassen ueber die schon veraenderte Liste summiert, meldet eine kleinere
Zahl und sieht damit harmlos aus.

## 4c. Eine Spur mit belegtem Vorteil vergroessern: PLAETZE hoch, Groesse nicht

Steigt fuer eine Spur die Erlaubnis, mehr Kapital zu fahren, ist die erste
Entscheidung nicht „wie viel mehr", sondern **welchen Hebel**:
`max_offene_positionen` hoch ODER `max_pro_trade_usd` hoch.

**Die Positionsgroesse bleibt.** Sie ist die Groesse, ueber die die Stichprobe
gemessen ist: der Vorteil einer Spur ist an einem bestimmten Einsatz je Trade
nachgewiesen, nicht am Prinzip „mehr ist auch besser". Wird stattdessen der
Einsatz je Trade gehoben, gilt die Messung fuer eine Groesse, die nie gelaufen
ist - und die Ausschlaege je Position wachsen um denselben Faktor wie das
Risiko, waehrend der Vorteil je Position gleich bleibt. Der Platzzaehler
hingegen vergroessert die Zahl unabhaengiger Beobachtungen: dieselbe Regel,
mehr Stichproben.

Die Rechnung, die es zu nennen gilt, ist der freie Bestand, nicht die
Wunschzahl: gebundenes Kapital + freies Guthaben ergibt die Obergrenze, und
der Zielwert wird als „so viel, wie heute gedeckt ist" notiert, nicht als
Rundzahl. Gemessen: 469 USD gebunden, 377 USD frei — die Obergrenze war die
Kante dessen, was trug, nicht eine aufgerundete Zahl. Steht die Grenze hoeher
als das gedeckte Guthaben, entscheidet nicht die Konfiguration, sondern der
Guthaben-Tor, und die hoehere Zahl sieht in der Vorschau wie eine wirksame
Anderung aus, ohne eine zu sein.

**Wessen Kapital das ist, entscheidet die Messung, nicht die bestehende
Wuchengrenzen.** Ein Deckel-Feld verteilt die Erlaubnis historisch, nicht nach
Verdienst: gemessen eine Spur mit 124 Runden und deutlich von null
unterscheidbarem Vorteil bei einem kleineren Deckel als eine mit weniger
Runden und einem Vorteil nahe null. Wer eine bewiesene Spur hochfaehrt und
eine unbewiesene unangetastet laesst, hat das Kapital nur nach der Reihenfolge
des Baus verteilt, nicht nach seinem Wert.

Merksatz: **Skalieren heisst „mehr unabhaengige Versuche", nicht „hoehere
Wette"** — und eine vergroesserte Spur gehoert an das freie Guthaben, nicht
an die Rundzahl.

1. **Vorher/nachher am echten Objekt zeigen:**
   `<spur>/handeln.py --vorschau` mit `MAXHIRN_ROUTINE=1` (so ruft der Dauerlauf sie
   auf) muss `Live waere gesperrt durch: nichts` sagen — genau EIN Grund, sonst
   greift die Auto-Freigabe nicht.
2. **Die Rechnung der Grenze direkt pruefen** (Funktion mit gepatchtem Guthaben und
   Waehrung, nicht das ganze Buch) — und mit einem Kontostand, der die Grenze reisst.
3. **Die Reihenfolge im Code festnageln** (Quelltext-Test): der Deckel-Aufruf muss
   VOR dem Orderaufruf stehen. Ein Test, der nur den Rueckgabewert prueft, merkt
   nicht, wenn die Deckelung hinter der Order landet.
4. **Spiegelung und Buch unberuehrt nachweisen** (`spiegelstand.py`), und im Bericht
   sagen, was NICHT angefasst wurde (offene Positionen, Stops, Fremdguthaben).
5. Wirkt **ohne Neustart** des Dauerlaufs, solange die Spur je Zyklus als eigenes
   Kind startet; nur die Wachen-Datei wird bei jedem Zyklus neu gelesen.
