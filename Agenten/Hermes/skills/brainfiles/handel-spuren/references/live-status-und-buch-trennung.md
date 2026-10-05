# Live-Status einer Spurenfamilie beurteilen und Papier- von Live-Buechern trennen

Gilt fuer die Fragen "welche Spuren duerfen handeln, welche sind live, woran haengt
welche" und fuer den Fall, dass eine Spur live geht, deren Buch noch Papier traegt.

## 1. Werkzeuge (rein lesend)

- `Agenten/Handel/spuren_stand.py` — eine Tabelle ueber alle Spuren aus
  `dauerlauf.SPUREN` (die Spurenliste wird GELESEN, nicht abgetippt): erlaubt,
  herzschlag, Fenster, `freigabe.erfuellt`, Orderpfad, Buchgroesse je Zustandsdatei,
  Zyklusalter. `--json` fuer die Weiterverarbeitung, `--nur live` fuer die Spuren mit
  Orderpfad.
- `Agenten/Handel/sperrgruende.py` — laeuft je Spur deren eigene `handeln.py --vorschau`
  und zeigt die Sperrzeile. Markiert die Spuren, bei denen NUR das Freigabefenster
  fehlt.

## 2. Die Freigabe-Regel, an der alles haengt

Der Dauerlauf oeffnet ein Live-Fenster selbst nur, wenn die Vorschau **genau EINEN**
Grund nennt und dieser Grund das Wort `Freigabefenster` enthaelt (`dauerlauf.nur_fenster_fehlt`).
Zwei Gruende, ein anderer Grund oder gar keine Sperrzeile = keine Anfrage, keine Freigabe.

Folge fuer jede Schalteraenderung: **nach dem Umlegen `sperrgruende.py` laufen lassen.**
Sonst entsteht eine Freigabe-Anfrage, die niemand erwartet — oder eine Spur geht scharf,
weil man einen Grund versehentlich weggenommen hat. Die Spuren, die allein am Fenster
haengen, sind zugleich die Liste der Spuren, die zahlfaehig sind; weicht sie von
`AUTO_FREIGABE` ab, ist das die Entscheidung, die dem Nutzer vorgelegt wird.

## 3. `handel_erlaubt` ist ein Schalter, keine Faehigkeit

Der Wert sagt nur "darf", nicht "kann". Ob eine Spur real ordern kann, entscheidet der
CODE: gibt es im Spurenordner einen Aufruf des Order-Endpunkts der Boerse
(`/api/v5/trade/order`, `AddOrder`, `place_order`, `submit_order`, …) in einer Datei
AUSSERHALB von `tests/` und `.venv/`?

- Eine Spur ohne solchen Aufruf bleibt Papier, egal was in der Wachen-Datei steht — der
  Wert ist dann ein Etikett. Beim Setzen ausdruecklich als Vermerk in die Wachen-Datei
  schreiben ("Schalter ohne Orderpfad, wer einen Live-Zweig anschliesst prueft zuerst
  Wachen, Grenzen und Fenster"), sonst sieht er in der naechsten Sitzung wie eine
  Absicherung aus.
- Eine Spur, deren Orderaufruf nur in einer `*_test.py` steht, hat ebenfalls keinen
  Live-Pfad im Betrieb.
- **spur_buch-Nutzer haben ihren Orderweg im GEMEINSAMEN Kern, nicht im Spurordner.**
  `spuren_stand.orderweg()` sucht nur im Spurordner nach Orderfunktionen — eine Spur,
  die `spur_buch.zyklus()` aufruft (moondev_listingarb, moondev_topmovers,
  trendwende_btc), meldet darum faelschlich "keiner", obwohl `spur_buch.orderweg()`
  ueber `boerse` aus der wachen.json ein echtes Modul liefert (mosaic/okx_spot oder
  kraken_spot). Erkennung erweitern: `import spur_buch` ODER `spur_buch.py` in
  `handeln.py` UND ein `boerse`-Feld in der wachen.json = Live-Pfad. Ohne diese
  Erkennung zeigt `/live` und der Tagesbericht eine scharfe Spur als Papier — ein
  Anzeigefehler, kein Codefehler.
- **Die Sperre im CODE muss am ORDERWEG haengen, nicht am Schalter.** Seit dem
  Sammelauftrag stehen `handel_erlaubt` UND `freigabe.erfuellt` in JEDER `wachen.json`
  auf true; eine `_live_erlaubt()`, die nur diese zwei Felder liest, laesst `--live`
  durch — und eine Spur ohne Orderaufruf schreibt dann ein Buch mit `modus=live`, das
  an keiner Boerse existiert (dieselbe Fiktion wie ein Papierbuch im Live-Modus, nur
  schwerer zu sehen). Muster: Modulkonstante `LIVE_ORDERWEG = False` plus eine REINE
  Funktion `live_gate(modus) -> (modus, meldung)`, die `--live` immer auf Papier zieht
  und den Grund nennt. Rein, damit der Test sie ohne Buchzugriff pruefen kann
  (Form: `references/test-friert-stand-ein.md`, dritte Familie).

## 4. Ein Live-Lauf darf kein Papierbuch erben

Ein Buch, das in beiden Modi in dieselbe Zustandsdatei schreibt, enthaelt nach dem
Wechsel Positionen, die nie eine Order hatten (kein `kauf_ord_id` bzw. `kauf_txid`).
Zwei Schadwirkungen: die Plaetze sind belegt (kein Neukauf), und der Ausstiegspfad
versucht, Bestaende zu verkaufen, die am Konto gar nicht liegen.

Muster (in `scanner/handeln.py` gebaut, in `kraken/handeln.py` nachgezogen):

1. Am ANFANG jedes Live-Laufs die Positionen ohne echte Order ermitteln.
2. Jede mit einem Kurs bewerten und als **Papier**-Verkauf mit dem Grund
   `buchbereinigung` ins Journal schreiben.
3. Positionen ohne Kurs liegen lassen (nicht blind buchen) und das melden.
4. Der Aufraeumschritt darf im Vorschau-Modus nicht laufen (`live` ist dort falsch).

Fallen:

- **Nie die echte Funktion als Probe gegen das echte Buch laufen lassen** — sie schreibt
  Journalzeilen. Gegen eine Kopie testen. Sind die Zeilen trotzdem schon geschrieben und
  das Buch noch voll, das Buch von Hand leeren (Sicherung daneben), damit Buch und Journal
  gleich stehen; **Journalzeilen werden nie geloescht**.
- Bei einer zweiten Spur denselben Fix nicht "analog" behaupten: pruefen, ob der
  Papier-Ausstiegspfad dieser Spur eine Modus-Pruefung je Position hat (die eine Spur
  mischt Papier und Live in einem Buch, die andere trennt ueber das Positionsfeld).

### Wer eine Spur ohne diese Funktion vorfindet (25.09.2026)

Drei Spuren handeln auf Kraken und fuehren Papier und Live in EINEM Buch; die
Plaetze sind knapp (kraken 4, nautilus_kraken 4, mosaic 5 live). Gemessen an
diesem Tag:

- `kraken`: 4 Papier-Positionen ohne `kauf_txid` belegten alle vier Plaetze.
- `nautilus_kraken`: 4 Papier-Positionen, Spur ARMIERT (`handel_erlaubt=true`,
  `freigabe.erfuellt=true`) - jeder Live-Zyklus lief in "Buch voll", eine echte
  Order kam nie zustande. Diese Spur hatte die Aufraeumfunktion GAR NICHT; sie
  wurde nachgezogen (`handeln.bueche_papier_altlasten_aus`, Marker `modus !=`
  `live`, Aufruf VOR `sammle_quoten` - die Platzzahl wird dort geprueft).
- `mosaic`: eine Papier-Position unter vier; `live_einstiege` zaehlt Positionen
  ohne `modus=live` mit, sie nimmt also einem echten Kauf einen Platz weg.
- `moondev_marktlage`: NICHT betroffen - sein Live-Zweig fuehrt eine eigene
  Zustandsdatei (`zustand.live.json`), das Papierbuch blockiert dort nichts.
  Vor dem Aufraeumen pruefen, wer mit wem dasselbe Buch teilt.

Werkzeug `Agenten/Handel/papierbuch_schliessen.py` (Vorschau ist Standard,
`--anwenden` schreibt, `--spur <name>`): es ruft die Funktion DER SPUR, bucht
und spiegelt nach Q:. Es fasst keine Zustandsdatei an, die juenger als 300 s ist
(dort laeuft ein Zyklus). Interpreter beachten: `nautilus_kraken` laeuft im
`nautilus/.venv`, die anderen im `scanner/.venv`.

Zwei Nachwirkungen, die man kennen muss:

- Der Papierzweig fuellt die Plaetze im naechsten Zyklus wieder (Signale der
  Kopier-Spur). Die Einmal-Bereinigung wirkt deshalb nur bis dahin - der
  dauerhafte Fix ist der Aufraeumschritt im Live-Lauf, der das Buch erst beim
  Scharfschalten leert. Genau dafuer laeuft er dort.
- Nach dem Aufraeumen bleibt oft nur noch das GELD als Sperre (25.09.2026:
  Kraken-EUR frei 0,71 EUR, `mindest_guthaben_eur` 60 bzw. 1,00 EUR). Das ist
  die ehrliche Lage - nicht die Papierposition war der letzte Grund.

## 4a. Ein Pruefskript, das den Zustand nicht setzt, erfindet Sperren

Bevor du auf einen Auftrag reagierst, der eine Freigabe oder ein Tor
nennt: **hat der Aufruf den Zustand gesetzt, den der BETRIEB setzt?** Ein
Pruefskript, das ein Wachen-Feld liest, ohne es vorher zu setzen, hat seinen
eigenen Vorgabewert erfunden und meldet eine Sperre, die es nicht gibt -
und verschiebt damit die Arbeit auf die falsche Baustelle.

Merksatz: **eine Sperre, die nur dein Aufruf erzeugt, ist kein Befund.**
Gegenprobe: denselben Namen einmal ohne und einmal mit dem Betriebszustand
aufrufen. Identisches Ergebnis heisst: es gab nie eine Sperre. Danach die
Torkette in REIHENFOLGE prüfen, jede Tuer einzeln, mit dem Grund im
Klartext - der echte Blocker liegt selten bei der Tuer, die man zuerst
vermutet. (Beispiel: gemeldet „durch `live_pf_ableitung` gesperrt", das Feld
stand seit Tagen auf `true`; der Blocker lag eine Stufe tiefer - das Buch
war voll mit Positionen, die es an der Boerse nicht gab.)

Der beste Befund dieser Art kommt aus dem **Vorschau-Lauf im
Routine-Modus** (`MAXHIRN_ROUTINE=1 ... handeln.py --vorschau`), nicht aus
einem eigenen Skript: er zeigt Filter- und Sperrzeilen in der Reihenfolge,
in der die Spur sie selbst nimmt, samt Zeile „Live waere gesperrt durch:
…". Ein Skript ahmt diese Reihenfolge nach und kann sie verschieben.

## 5. Buchbereinigung ist keine Handelsrunde

Zeilen mit dem Grund `buchbereinigung` gehoeren in dieselbe Klasse wie
Herzschlag-Zwangsschluesse: keine Handelsentscheidung. Die EINE Definition liegt in
`Handel/stoerungen.py` (Waechter-Reaktionen UND Buchhaltungs-Korrekturen);
Runden-Zaehler, `lage()` und die Auswertungen schliessen beide aus. **Die Kapitalkurve
bleibt ungefiltert** — eine Buchung ist gebucht; Drawdown, Halbierung und Kill rechnen
weiter auf allen Zeilen. Wer eine neue Ausstiegsart einfuehrt, traegt ihren Grund dort
als Merkmal ein und laesst die Spuren-Suite laufen — eine vergessene Zeile zaehlt sonst
stillschweigend als Runde und verschiebt jede Kennzahl.

### Drei Fehler, die eine Bereinigung stillschweigend falsch macht

1. **Das richtige Feld lesen.** Die Felder einer Position heissen je nach
   Spur `einstieg` (nicht `preis`) und `nominal` (nicht `einsatz_usd`). Ein
   falscher Feldname liefert **keinen Fehler, sondern `0.00`** - und bucht
   damit neun Positionen zu 50 statt 450 USD. Deshalb gehoeren Kurs und
   Einsatz je Position in die **Trockenlauf-Ausgabe**, einzeln und mit dem
   Feldnamen daneben: nur so sieht man, dass alle 50 statt aller 0.00 sind.
2. **Ohne Kurs nicht buchen.** Eine Position ohne Einstiegskurs laesst sich
   nicht ehrlich ausgleichen; sie bleibt stehen und wird als Befund
   gemeldet. Eine Ausgleichszeile mit Kurs `0.00` waere geraten, und
   geraten wird hier nichts.
3. **Gegen die BOERSE klassifizieren, nicht gegen das Buch.** Ein Filter,
   der `(inst, seite)` gegen `z["positionen"]` prueft, findet einen Geist
   genauso wie eine echte Position - beide haben denselben Schluessel. Nur
   die Boersenantwort trennt sie. (Deshalb blockierte eine von neun
   Positionen den Einstieg, obwohl keine davon an der Boerse stand.)

Und die **Gegenprobe, die nie bestehen kann**: wer eine eigene Summe
vorher/nachher vergleicht (etwa „Runden-Bestand"), zieht per Definition
genau das ab, was gerade ausgetragen wurde, und meldet bei JEDER korrekten
Bereinigung eine Abweichung. Richtig sind die **Eigenschaften**:
Rundenzahl der Hausrechnung vor/nachher (muss gleich sein), Ergebnis der
Hausrechnung (muss unveraendert sein), und je Zeile `wert_usd ==
einsatz_usd`. Eine Pruefung, die nie anschlaegt, wird abgeschaltet und
damit blind.

## 5a. Der Schutznachweis einer Position ist eine eigene Pruefdimension

„Die Position steht an der Boerse" und „die Position ist geschuetzt" sind
zwei Fragen. Die erste beantwortet eine offene-Positions-Abfrage, die zweite
einen lesbaren Weg zu den **offenen Schutzauftraegen** - und genau der
fehlt manchen Borsen-Wegen. Ein Endpunkt, der mit `requiredArgumentMissing`
antwortet, ist ein **fehlgeschlagener Abruf**, nicht „keine Auftraege" -
beide zu verwechseln heisst, einen Long ohne Stop fuer geschuetzt zu halten.

Also: meldet die Schutzabfrage einen Fehler, ist das eine offene Luecke mit
Task, kein beruhigender Befund. Ein Long ohne nachweisbaren Stop ist die
ganze Position, und genau daran sind im Haus mehrere Geister entstanden.
Ist der Leser nicht vorhanden, gehoert der Zustand als **„nicht lesbar"**
gemeldet, nicht als „kein Stop".

## 5b. Ein Orderweg pro Produktart, und was daran verschieden ist

Eine Spur kann heute Spot und morgen gehebelt handeln — dann braucht sie einen
ZWEITEN Weg, nicht einen umgebauten. Der beste Bau ist ein eigenes Modul mit
**denselben Funktionsnamen**, das in die Boersentabelle des Spurcodes kommt
(`BOERSEN = {"okx": okx_spot, "okx_perp": okx_perp}`). Der Rest der Spur
aendert sich nicht; was sich aendert, steht an genau zwei bis drei Stellen und
muss dort benannt sein:

1. **Der Betrag bedeutet etwas anderes.** `menge_fuer(inst, betrag, kurs)`
   rechnet bei Spot die MARGIN aus, bei Futures den NOMINALWERT. Derselbe
   Aufruf, zwei Bedeutungen. Gehebelt gehoert deshalb eine Umrechnung in den
   Aufrufer (Margin x Hebel), nicht in die Wache — eine Wache, die den Hebel
   traegt, wird sonst an einer Stelle als Nominal gelesen.
2. **Der Hebel geht als Argument an den Kauf**, gesetzt VOR der Order. Nicht
   im Modul als versteckter Wert: sonst laeuft ein Aufruf ungehebelt auf einem
   gehebelten Weg, ohne dass irgendetwas es meldet.
3. **Der Pflicht-Stop braucht eine ZUSATZPRUEFUNG, die es bei Spot nicht
   gibt**: er muss zwischen Liquidationsmarke und Kurs liegen, sonst kommt er
   nie. Die Pruefung gehoert VOR den Einstieg (ein verweignerter Einstieg
   kostet nichts, eine Position ohne wirksamen Stop kostet die Margin).

Weitere Stolpersteine, gemessen beim Bau:

- **Die Kontowaehrung steht nicht auf der oberen Ebene der Balance-Antwort.**
  `/api/v5/account/balance?ccy=USDC` liefert oben `availEq=''`, `availBal=None`
  und erst in `details[0]` die Zahlen. Wer die oberen Felder liest, bekommt 0.00
  — das sieht wie ein leeres Konto aus und sperrt die Spur an einem
  Guthaben-Tor, das offen ist. Der richtige Wert ist `details[0].availEq` (freie
  Margin), nicht `eq` (das auch Gebundenes enthaelt).
- **Ein gemeinsamer Bausen-Stop lohnt sich, eine neue Signatur nicht.** Der Weg
  holt HTTP, Takt und Schluessel aus dem vorhandenen gehebelten Modul per Pfad.
  Eine zweite Signatur im Haus ist eine zweite Fehlerquelle mit demselben
  Aufgabenbereich.
- **Ein Vertragstest, der die Funktionsnamen des neuen Wegs gegen die des
  Bestandswegs haelt, findet echte Luecken.** Beim Bauen fehlte eine Funktion,
  die der Aufrufer spaeter bindet — beim Lesen des Codes fiel sie nicht auf,
  der erste Lauf an echten Kursen haette es gezeigt.
- **Der Liquidationsabstand folgt aus 1/hebel, nicht aus dem Wunsch.** Bei 6x
  rund 16 %, bei 12x rund 8 % (Wartungsmarge 0,5 % mitgerechnet) — damit ist
  die Grenze benennbar, ab der ein 5-%-Stop unerreichbar wird.
- **`posMode` liest man, statt `posSide` zu setzen.** Steht das Konto auf
  `net_mode`, lehnt OKX eine `posSide`-Angabe ab; auf `long_short_mode` wird sie
  gebraucht. Die Antwort entscheidet das, nicht die Gewohnheit.

## 6. Waehrung einer Spur umstellen

Vor dem Umstellen auf ein anderes Quote- oder Margin-Produkt pruefen, was die Boerse
ueberhaupt kennt — und was das KONTO hergibt:

- Quote-Waehrungen sind nicht austauschbar: OKX hat rund 295 `*-USDC`-Paare, aber EURC
  nur als `EURC-USD`/`EURC-USDC`, also gar nicht als Quote (ein Bestand in EURC laesst
  sich nur tauschen, nicht als Paar handeln).
- Perpetuals und Optionen sind ein PRODUKT, keine Waehl der Waehrung; XPERP-Kontrakte
  sind USDC-marginiert, auch wenn man USDT erwartet. Die Margin-Waehrung steht an der
  POSITION, nicht im Kopf des Kontos:
  `/api/v5/account/positions?instType=FUTURES` liefert `mgnMode` und `ccy` je Position.
  Erst damit ist eine Finanzierungsaussage belegt; ein Guthaben, das die Waehrung nicht
  kennt, meldet faelschlich null.
- Ein Instrumentenwechsel gehoert in die Wachen-Datei (nicht in den Code), die alten
  Positionen bleiben unter ihrem alten Instrument stehen und laufen normal aus.

## 8. Die Zeile "Live-Anbindung" im Tagesbericht

Seit dem Auftrag vom 21.09.2026 steht `handel_erlaubt=true` in JEDER `wachen.json` -
auch bei Spuren ohne einen einzigen Orderaufruf im Code. Der Tagesbericht zeigte damit
29x "erlaubt" und verschwieg, welche Spur ueberhaupt Geld bewegen kann.
`tagesbericht.livezeile()` (Zeile direkt unter `spiegelzeile()`) trennt darum drei
Gruppen in einer Zeile: `haus` (eigene Orderanbindung der Spur), `fremd` (eine
Fremd-Laufzeit ordert, z.B. der Nautilus-DEMO-Node) und die Zahl der Spuren ohne
Orderweg. Ein `(F)` hinter dem Namen heisst: Freigabefenster steht offen.

Regeln dabei:
- Die Erkennung kommt aus `spuren_stand.sammle()` - DIESELBE Quelle wie `/live` und
  `spuren_stand.py`. Eine zweite Liste im Bericht waere beim naechsten neuen
  Spurordner veraltet.
- Ein Fehler darf den Bericht nicht kippen: `except` liefert "nicht geprueft (<grund>)",
  genau wie `spiegelzeile()`.
- Getestet wird gegen eine GEFAELSCHTE Erhebung (`ss.sammle` im Test ersetzen), nicht
  gegen die echten Spurordner - sonst haengt der Test am Tagesstand des Dauerlaufs
  (`tests/test_tagesbericht_livezeile.py`).
- Wirkt erst nach einem Dauerlauf-Neustart: `dauerlauf.py` importiert `tagesbericht`
  beim Start.

## 9. Ein gemeinsames Buch fuer Papier und Live: das `modus`-Feld

Ein Buch, in das BEIDE Modi schreiben, braucht an jeder Position die Herkunft. Sonst
entsteht eine Endlosschleife: der Papierzweig legt eine Position an, der naechste
Live-Zyklus haelt sie fuer eine Altlast und bucht sie aus (`buchbereinigung`), der
naechste Papierzweig legt sie wieder an. Gemessen in `swap` (Journal 22.-24.09.2026,
dreimal: eroeffnen, 13 bis 28 Minuten spaeter ausgebucht) — die Papierstrecke kam so
NIE an Stop oder Ziel, ihre Zahlen sind wertlos. Die teurere Richtung: ohne das Feld
kann der Live-Zweig eine ECHTE Position ausbuchen; sie bleibt ohne Buch an der Boerse
stehen (Geister-Muster).

Regel, in `swap/handeln.py` durchgesetzt (Vorbild `mosaic`):

1. **Jede Position traegt `modus`** (`live`/`papier`) — gesetzt im Einstieg, auch im
   Papierzweig.
2. **`pruefe_ausstiege()` und `flach_stellen()` fassen nur den EIGENEN Zweig an**
   (`(p.get("modus") or "papier") != eigen -> behalten`). Ohne diese Zeile schickt ein
   Live-Lauf ein echtes `markt_schliessen()` fuer eine Scheinposition.
3. **Die Plaetze/Margin-Tore zaehlen nur den eigenen Zweig** (`plaetze = len(meine)`,
   `meine` beim Einstieg mitgefuehrt). Sonst blockiert der Papierlauf den Live-Lauf.
4. **Die Bereinigung raeumt nur noch ALTBESTAND ohne `modus`-Feld.** Eine Position ohne
   Feld ist keinem Zweig zuzuordnen — genau der teure Fall —, eine Papierposition im
   Live-Buch ist dagegen harmlos.
5. Vor der Aenderung des Bestands: die Zuordnung fehlt nur bei Positionen aus der Zeit
   davor; sie zaehlen als Papier.

Beleg statt Vermutung: das JOURNAL liest man spaltenweise (`modus,aktion,...,grund`) und
zwar fuer BEIDE Modi — drei `eroeffnen` mit `papier` und ein paar Minuten spaeter
`buchbereinigung` sind der Beweis. Zustand und Log allein zeigen die Schleife nicht.

## 10. „Welche Spur handelt live und auf welchem Kanal?“ — drei Zeugen, in dieser Reihenfolge

Auf die Frage nach dem aktuellen Live-Stand gibt es vier Quellen, und jede allein
liegt falsch. Die Reihenfolge ist die Antwort:

1. **Die Boerse** (offene Positionen, offene Schutz-/Limit-Auftraege, Kontostand je
   Waehrung) — einzige Quelle fuer „es existiert“.
2. **Das Journal, nach echter Kauf-/Verkaufsaktion gefiltert** — einzige Quelle fuer
   „die Spur hat es getan“.
3. **Der Zustand** (`modus=live` je Position) — traegt die Kanal-Zuordnung, aber
   Positionen ohne Orderkennung sind die bekannte Fiktion.
4. **Das Log / die Wachen-Schalter** — nur Modus und Absicht, nie ein Beleg.

### Die drei Zaehlfehler, die diese Abfrage teuer machen

- **`(live)` im Dauerlauf-Log ist der MODUS DES DAUERLAUFS.** Die Zeile
  `<spur> (live) ok` heisst, dass der Lauf mit `--live` gestartet wurde — sie sagt
  nichts darueber, ob geordert wurde. Ein Buch mit `(live)` und null Orderkennung
  ist genau diese Verwechslung.
- **`modus=live` im Journal braucht einen AKTIONSfilter.** `zyklus`, `funding` und
  `rollover` tragen denselben Modus wie ein Kauf. Ohne Filter zaehlt eine reine
  Quote-Spur Hunderte „Live-Zeilen“, die nie eine Order waren (gemessen: eine
  Futures-Arm-Spur 218 gegen 0 Kaeufe). Erlaubte Aktionen je Familie:
  `kauf`/`verkauf` (scanner, Kraken-Spot), `eroeffnen`/`schliessen` (xperp, Nautilus-
  Arme), `EINSTIEG`/`AUSSTIEG` (omniquant) — die Liste gehoert zu
  `stoerungen.py`, nicht in den Kopf.
- **Jede Boerse braucht ihren EIGENEN Zugang.** Ein Konto wird nie ueber einen Weg
  vollstaendig sichtbar: OKX-Futures und OKX-Spot teilen sich das Konto, aber nur
  `/api/v5/account/positions` kennt die gehebelten Positionen (Spot-Bestand steht in
  `/api/v5/account/balance`), und Kraken hat zwei voellig getrennte Konten
  (Spot-Bestand vs. Futures-flex) mit je eigenem Schluesselsatz und eigenem
  Endpunkt. Ein Abruf, der beide Seiten beantworten soll, beantwortet eine.
  Fertige lesende Wege:
  - OKX (beides): `Agenten/Handel/okx_positionen_live.py` — Kontostand je Waehrung,
    offene FUTURES-Positionen mit Einstieg/Liquidation, Schutz-Auftraege mit Menge.
  - Kraken Spot: `kraken.kontostaende()` (Bestand = Position, Antwort OHNE
    `open`-Mantel) und `kraken.offene_orders()` (Schutz + Limits).
  - Kraken Futures: `nautilus_kraken/kraken_futures.py` — `guthaben()`,
    `offene_positionen()`, `offene_orders()`; das Modul ueber den PFAD laden, es
    liegt im Nautilus-Ordner und nicht in `kraken/`.
- **Ein Buch fuehrt genau EINE Waehrung, eine Brieftasche kann Positionen in
  mehreren fuehren.** Derselbe Basiswert auf zwei Boersen ist ZWEI Positionen; in
  der Antwort nach Boerse und Kanal (Spot / gehebelt, Waehrung) gruppieren, nicht
  nach Instrument.

### Was ohne Buch dasteht, gehoert ausdruecklich dazu

Eine Position an der Boerse, die in keinem Journal und keinem Zustand auftaucht,
ist kein Befund zum rueckbuchen, sondern eine **Konto-Zeile** (Position, Menge,
Einstieg, UPL, Kennung) neben den Spurbuechern — und der Nutzer entscheidet, ob er
sie selbst angelegt hat. Umgekehrt ist eine offene Order mit einem Merkmal, das der
Hausweg nicht erzeugen kann (etwa ein Kraken-Spot-Limit mit „with N:1 leverage“ im
Beschreibungstext — der Haus-Spot-Weg hat keinen Hebel), von Hand gelegt. Beides
gehoert in dieselbe Antwort, getrennt von den Spurzeilen.

**Die Bestaetigung des Nutzers ist ein dauerhafter Stand, kein Einmalhinweis.**
Er hat eigene Positionen auf demselben Konto (gemessen: Kraken-Futures-Kontrakte
und ein Spot-Limit mit Hebel), die in keinem Spurenbuch stehen. Nach seiner
Bestaetigung gilt: diese Kontostandzeilen sind als **von Hand** gefuehrt und
tauchen in keinem Folgebefund mehr auf — sie weder ausbuchen noch „fremd" nennen
noch bei jedem Lauf erneut vorlegen. Geaendert wird nur, was er selbst sagt. Ohne
diese Regel wird dieselbe gepruefte Position bei jeder Sitzung neu als Befund
gemeldet, und die Diagnose-Liste verliert ihre Aussagekraft.

### Ausgabeform fuer den Nutzer

Je Boerse ein Block mit Kanal und Waehrung, darunter je Spur die Positionen mit
Menge und Kennung; danach eine kurze Liste „Live-Modus, aber keine Order“ (Spuren,
deren Log `(live)` sagt und deren Buch leer ist) und die stummen Risikostufen
ausdruecklich NICHT als live. Journal-Zeilen mit `modus=live` in einer stummen
Stufe immer DATIEREN — sie sind Historie aus der Zeit vor der Stumm-Regel, kein
aktuelles Handeln; die Gegenprobe ist der Zeitstempel der Zeile, nicht ihr Modus.
