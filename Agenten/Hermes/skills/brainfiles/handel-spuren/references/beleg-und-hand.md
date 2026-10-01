# Freigabe-Beleg und Hand: wer eine Order ausfuehrt

Die eine Bruecke zwischen Spur-Entscheidung und Boersen-Order. Gilt fuer jede
Spur, die einen Auftrag ABGEBEN statt selbst ausfuehren soll, und fuer jede
Anbindung, die Orders aus einer SITZUNG heraus ausloesen koennte (MCP-Werkzeug,
CLI, Bot, Chat).

## Warum es das gibt

Ein Tauschwerkzeug (MCP-Server, CLI, Bot) darf nicht selbst entscheiden: es ist
aus jeder Sitzung, jedem Bot und jeder A2A-Nachricht aufrufbar, kennt aber keine
Wachen, kein Buch, keinen Herzschlag und keinen Kill-Switch. Ein Verbot im Text
haelt das nicht (Text ist keine Sperre). Die Loesung ist eine **Erlaubnis als
Datei**: `Agenten/Handel/freigabebeleg.py`.

```
Spur (kennt Wachen, Buch, Kill-Switch) --stellt aus--> Beleg <--verlangt-- Hand (MCP/CLI/Skript)
```

- `schreibe(spur, seite, paar, menge, preis_max|preis_min, grund, gueltig_sekunden, zusatz)`
  **verweigert**, wenn kein Freigabefenster offen ist ODER `handel_erlaubt=false` -
  also unter genau den Bedingungen, unter denen die Spur ohnehin handeln darf.
- Inhalt: Spur, Seite, Paar, Hoechstmenge, Hoechstpreis, Frist (Standard 180 s)
  und `zusatz` fuer das, was nur die Spur weiss (Stop, Ziel). Die Hand soll den
  Auftrag vollstaendig kennen, sonst entscheidet sie doch.
- **Einmalig:** `pruefe(...)` vor dem Ausfuehren, `verbrauche(...)` danach.
- `preis_max` gilt nur bei `buy`, `preis_min` nur bei `sell` - vertauscht ist es
  eine Erlaubnis fuer den falschen Preis.
- `offene()`/`uebersicht()` sind lesend und nennen die offenen Belege.
- Der Beleg hat keinen Erzeuger-Zwang ausserhalb der Spur: stellt nur eine Spur
  aus, und nur sie kennt die Wachen.

## Der Spur-Zweig: abgeben oder selbst ausfuehren

Die Entscheidung steht als FELD in der `wachen.json` der Spur
(`order_ueber: "mcp"`), damit ein Schalter nicht im Code versteckt ist:

1. **Beleg ausstellen** - in beiden Varianten. Schlaegt das fehl, faellt der
   Einstieg aus: eine Spur ohne Freigabefenster darf auch auf ihrem EIGENEN Weg
   nicht kaufen. Wer den Beleg nur im Abgabe-Zweig ausstellt, umgeht das Tor.
2. **`order_ueber: "mcp"`** - die Spur ordert NICHT. Sie schreibt eine
   Journalzeile (`kauf_beleg`) und laesst den Beleg liegen; ausgefuehrt wird von
   der Hand.
3. **eigener Weg** (Feld fehlt oder `"spur"`) - die Spur **verbraucht den Beleg
   VOR der Order** und ordert dann selbst.

**Der Verbrauch VOR der Order ist der Kern der Einmaligkeit.** Bliebe der Beleg
nach einer eigenen Order liegen, koennte die Hand dieselbe Order innerhalb der
Frist ein zweites Mal ausfuehren - ein echter Doppelkauf, kein Schoenheitsfehler.
Umgekehrt gilt: nach einem Fehlschlag wird KEIN Beleg aufgehoben, der naechste
Zyklus entscheidet neu.

## Die Hand: zwei Wege, ein Tor

- **Aus einer Sitzung:** das MCP-Werkzeug `kraken_order_mit_beleg` prueft und
  verbraucht denselben Beleg. Das frueher offene Werkzeug `kraken_order_aufgeben`
  kann NICHT mehr echt ausfuehren (nur noch pruefen), und ein Sammelstorno
  (`kraken_order_stornieren('all')`) ist gesperrt, weil es den Schutz-Stop einer
  offenen Position mitnimmt. **Einzelstorno bleibt erlaubt** - es kuerzt nur
  Risiko. **Ausstiege haengen NIE am Beleg**, nur Einstiege; Stop und Notaus
  bleiben frei.
- **Im Betrieb:** `Agenten/Handel/beleg_hand.py` (Vorschau ist Standard) fuehrt
  genau das aus, was im Beleg steht (Paar, Menge, Hoechstpreis, Stop, Ziel) und
  bucht die Position in das ECHTE Buch der Spur (Journal, Zustand, Spiegelung -
  Bedingung 4). Gerufen von Cron `beleg-hand` (5 min, `no_agent`, leise wenn
  nichts offen).

**Ohne den zweiten Weg ist der Beleg-Weg im Dauerlauf ein Stillstand:** die Spur
gibt ab, und niemand nimmt. Ein Beleg, den nur eine Sitzung ausfuehren kann, ist
fuer einen Dauerprozess kein Weg.

## Die Fuellung wird abgewartet, nicht sofort abgefragt

`gefuellte_menge(txid)` DIREKT nach `AddOrder` zu lesen ist eine Aussage ueber
einen Zeitpunkt, nicht ueber den Auftrag: eine Market-Order ist einen Moment
spaeter gefuellt als sie angenommen wurde. Kommt dabei 0 zurueck, meldet die Hand
"Kauf ohne Fuellung" - und die Spur bucht keine Position.

**Eine falsche "keine Fuellung" ist teurer als eine falsche "gefuellt".** Ohne
gebuchte Position sieht der naechste Zyklus denselben Wunsch wieder offen und
stellt denselben Beleg erneut; die Hand kauft erneut. Gemessen: derselbe Wert
vier mal in einer Stunde gekauft (~200 EUR statt 50 EUR), waehrend das Buch EINEN
Kauf fuehrte - und die Auftragsliste der Boerse zeigte den Fill 53 s VOR der
Fehlermeldung im Journal.

- **Warten statt einmal lesen:** nach `AddOrder` Orderzustand/Fuellmenge
  wiederholt abfragen (Sekundentakt, ~10 s Frist, wie die
  wartende-Auftraege-Logik in `xperp`) und erst danach "ohne Fuellung" melden.
  Ein Zwischenstand ist ein eigener Ausgang (`order_offen`), kein Fehler.
- **Ein Beleg darf nicht neu gestellt werden, solange eine Order zum selben
  Instrument offen oder ungeklaert ist.** Sonst wird der Beleg zum Verstaerker:
  jede Wiederholung ist ein zweiter echter Kauf.
- **Gegenprobe an der Boerse, nicht am Journal:** geschlossene Auftraege je
  Instrument zaehlen und die Menge gegen das Buch halten. Vier Kaeufe zu ~50 EUR
  gegen eine Buchmenge von einem Kauf ist der Befund; die Fehlermeldung im
  Journal ist nur das Symptom.
- **Ein Buchposten, der nur `paar` + `menge` traegt, ist keine Position.** Ohne
  Einstiegspreis, Einsatz und Stop erkennt die Spur ihren eigenen Bestand nicht
  wieder (sie kauft nach) und jeder Leser zeigt Unsinn - der Tagesbericht fuehrte
  drei 50-EUR-Positionen als "1 EUR"/"2 EUR". Was die Hand bucht, muss die
  Felder tragen, die die Spur selbst beim Einstieg schreibt.
- **Ein Wiederholkauf endet meist nicht durch Einsicht, sondern durch leeres
  Guthaben.** Danach kommt statt des Doppelkaufs eine Ablehnung wegen fehlender
  Deckung - das ist der Nachhall, nicht die Ursache. Wer den Fehler sucht, findet
  ihn in den geschlossenen Auftraegen der vergangenen Stunden.

## Fallen

- **Hochwertige Attrappen verdecken den Boersenkontakt im Test.** Die Attrappe
  muss an der UNTERSTEN Transportschicht sitzen (Stolperdraht), sonst kann ein
  Test mit `echt=True` wirklich kaufen - siehe `handelsspur-anlegen`, Abschnitt
  Tests.
- **Der Fenster-Name ist der SPURNAME, nicht der der Nachbarspur.** Ein zweiter
  Weg auf derselben Boerse, der das Fenster der Haus-Spur benutzt, schaltet sich
  mit ihr scharf.
- **`sitzung_da()` darf im Dauerlauf nie wahr werden:** der Dauerlauf setzt
  `MAXHIRN_ROUTINE=1` in BEIDEN Modi, ein Live-Lauf kann sich also nicht fuer
  eine Sitzung am Bildschirm halten und auf eine Freigabe warten, die niemand
  geben kann. Das Zeitfenster (`freigabefenster.py`) ist der zweite, ehrliche Weg.
- **Die `--vorschau` stellt keinen Beleg aus und schreibt nichts** (kein
  Zustand, kein Journal, keine Order) - sonst baut jeder Testlauf Erlaubnisse.
- **Eine Einheit fuer alle Schalter:** Ein Vorschau-Lauf, der die Sperrenliste
  ausgibt, muss GENAU EINEN Grund mit dem Wort "Freigabefenster" nennen, sonst
  kann der Dauerlauf nicht unterscheiden, ob nur das Fenster fehlt
  (`dauerlauf.nur_fenster_fehlt`).
- **Eine neue Spur auf dem MCP-Weg braucht BEIDE Enden:** den Aussteller im
  Spurcode UND die Hand im Betrieb. Nur eines von beiden zu bauen hinterlaesst
  eine Spur, die entweder nichts ausfuehrt oder nichts abgibt.

## Eine Spur hat EINEN Beleg - hoechstens einer je Zyklus (T-283, 01.10.2026)

BEFUND: die kraken-Spur stellte im Zyklus 11:25:51 **neun** Belege in EINEM Lauf aus
(ALGO/AVAX/LINK/TRX/DOT/SUI/LTC/ADA/SOL, je 50 EUR = 450 EUR Absicht bei
`max_gesamt_eur` 200) und schrieb neun `kauf_beleg`-Zeilen ins Journal. Ausgefuehrt
werden konnte nur der LETZTE, weil eine Spur genau EINE Belegdatei hat und jedes neue
`schreibe()` den vorigen still ueberschrieb. Journal und Belegdatei erzaehlten zwei
Geschichten. Zweitens war die Frist (180 s) kuerzer als der Takt des Ausfuehrers
`beleg-hand` (5 Minuten): ein Beleg, der direkt nach einem Lauf entstand, war beim
naechsten Lauf immer schon verfallen.

Fuenf Regeln, die daraus folgen:

1. **`schreibe()` verweigert, solange ein GUELTIGER, unverbrauchter Beleg liegt** -
   sie ueberschreibt keinen mehr. Abgelaufene und verbrauchte blockieren nicht
   (`offener()` laesst sie durchfallen).
2. **Die Spur stellt hoechstens EINEN Beleg je Zyklus aus** und bricht danach ab.
   Ohne diesen Abbruch erzwingt Regel 1 nur Fehlerzeilen je Kandidat statt einer
   Entscheidung. Der naechste Kandidat kommt im naechsten Zyklus.
3. **Ein offener Beleg ist ein RESERVIERTER Platz und reserviertes Kapital.** Er
   zaehlt gegen `max_offene_positionen` UND gegen `max_gesamt_eur`; dafuer traegt er
   den Einsatz in `zusatz["eur"]`. Ohne diese Reservierung prueft `pruefe_einstiege`
   nur die ausgefuehrten Positionen - ein noch nicht ausgefuehrter Auftrag war
   unsichtbar, und genau so entstanden neun Belege.
4. **Frist > Takt des Ausfuehrers.** `GUELTIG_SEKUNDEN` 600 bei 5-Minuten-Cron. Wer
   die Frist senkt, muss den Takt mitnehmen (oder umgekehrt) - sonst stirbt jeder
   Beleg, der kurz nach einem Handler-Lauf entsteht, vor dem naechsten Lauf.
5. **Verfallene Belege werden EINMAL gemeldet** (Zeile + Journalzeile
   `beleg_verfallen`, Merker `verfallen_gemeldet`). Ein verfallener Beleg ist kein
   Schaden - er kauft nicht -, aber er ist UNSICHTBAR: `offene()` laesst ihn weg, und
   ohne Meldung sieht niemand, dass eine beschlossene Order nie ausgefuehrt wurde.

Der Merksatz dazu: **ein Beleg ist eine Erlaubnis, keine Warteschlange.** Was nicht
sofort ausgefuehrt werden kann, darf gar nicht erst entstehen.
