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

## 5. Buchbereinigung ist keine Handelsrunde

Zeilen mit dem Grund `buchbereinigung` gehoeren in dieselbe Klasse wie
Herzschlag-Zwangsschluesse: keine Handelsentscheidung. Die EINE Definition liegt in
`Handel/stoerungen.py` (Waechter-Reaktionen UND Buchhaltungs-Korrekturen);
Runden-Zaehler, `lage()` und die Auswertungen schliessen beide aus. **Die Kapitalkurve
bleibt ungefiltert** — eine Buchung ist gebucht; Drawdown, Halbierung und Kill rechnen
weiter auf allen Zeilen. Wer eine neue Ausstiegsart einfuehrt, traegt ihren Grund dort
als Merkmal ein und laesst die Spuren-Suite laufen — eine vergessene Zeile zaehlt sonst
stillschweigend als Runde und verschiebt jede Kennzahl.

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
