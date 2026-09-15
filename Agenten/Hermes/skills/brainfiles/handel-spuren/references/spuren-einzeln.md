# Einzelne Handels-Spuren im Detail

Ausgelagert aus SKILL.md, um das 100.000-Zeichen-Limit einzuhalten.
Datiert - Massstab ist der Stand am jeweiligen Tag, nicht heute.

## SWAP anbinden (Stand 11.09.2026)

- **Das Universum ist FUTURES-fest.** `okxf.instrumente()` liefert nur
  `ruleType=xperp` unter `instType=FUTURES`. SWAP-Reihen ueber
  `okxf._mit_wiederholung("/api/v5/public/instruments?instType=SWAP")` mit
  `state=live`, `ctType=linear`, `settleCcy=USDT`, Endung `-USDT-SWAP`
  (11.09.2026: 464 lebende Reihen gegen 207 Futures-Ticker). Bewerten kann SWAP
  schon: `swap_instrument()`, `instrument("...-SWAP")`, `tickers("SWAP")`,
  `ist_swap` in bot.py, `historie.swap_id()`.
- **Ein voller Bewertungslauf dauert Minuten.** Zwei Kerzenabrufe je Reihe, OKX
  laesst rund 40 Anfragen je 2 s zu. Vorher nach Umsatz sortieren, nur die Spitze
  holen — und die Zahl der bewerteten Reihen in den Ausgabekopf schreiben, sonst
  sieht eine kurze Liste wie ein leeres Universum aus.
- **Kandidaten der SWAP-Spur muessen den vollen instId tragen.**
  `okxf.instrument("CHIP")` loest auf den XPERP-Kontrakt auf, nicht auf
  `CHIP-USDT-SWAP`. Ein Anlauf, der das Instrument aus dem Basiswert holt, handelt
  still den falschen Kontrakt.
- **Eine Papierspur darf kein Modul importieren, das den Live-Order-Pfad traegt.**
  `xperp/handeln.py` enthaelt `hebel_setzen` und `order_limit`; wer es importiert
  — auch nur fuer Pfadkonstanten —, haengt die Papierspur an dieselbe Leitung.
  Papier zuerst als eigenes Modul ohne Order-Funktion, per Test belegt; der
  Live-Zweig spaeter bewusst nach xperp-Muster.
- **Der Verweigerungsgrund haelt den Dauerlauf still.** `handeln.py --live`
  druckt genau einen Grund ohne das Wort „Freigabefenster“;
  `dauerlauf.nur_fenster_fehlt` liest die Zeile und fragt deshalb keine Freigabe
  an, die nichts oeffnen koennte. Wer den Text anfasst, prueft beide gedruckten
  Zeilen (`--vorschau`, `--live`) gegen dieselbe Regel — Test ueber die gedruckten
  Zeichenketten, nicht ueber die Datei.

## Omniquant-Spur (Papierbuch auf dem Prognose-Bericht, 13.09.2026)

- **Zwei Seams statt einem.** `omniquant/handeln.py` hat `bericht_quelle`
  (None -> `prognose_berichte/neuester.json`) und `letzter_kurs_quelle`
  (None -> `okx.letzter_kurs`) als Modulvariablen; Tests setzen Lambdas, `tearDown`
  stellt zurueck. Ein Signal ohne `richtung`-Feld ist keine Auskunft und wird
  uebersprungen, nicht geraten — der Bericht vom 12.09.2026 (alte prognose.py)
  hatte kein Richtungsfeld, der vom 13.09. schon.
- **Eine Merkliste, die nie aufhoert zu sperren, ist ein Tor, das nie aufgeht.**
  Die erste Fassung von `erledigt` blockierte den Wiedereinstieg eines Paares fuer immer; ein frischer Bericht mit neuen Kerzen und Grenzen ist eine neue Lage. Nur
  Eintraege vom HEUTIGEN Tag sperren, Aelteres beim Schreiben aufraeumen — per
  Test belegt.
- **Der Tagesbericht rechnet den Stop-Abstand richtungsbewusst — oder jede gesunde
  short-Position sieht aus wie gerissen.** `zeile_position` in tagesbericht.py
  rechnete `kurs/stop - 1` ohne Richtung. Bei short liegt der Stop UEBER dem Kurs:
  das Produkt ist immer negativ, die Anzeige meldet "Stop gerissen", obwohl nur
  die normale Luft zum Stop gemeint ist (Befund an der ersten omniquant-short
  WLFI-USDT, 13.09.2026). Fix: Richtungsfaktor `vz` (long +1, short -1), Default
  long ohne `seite`/`richtung`. Der Stop-Abstand ist damit der Abstand IN
  Positionsrichtung — negativ genau dann, wenn der Kurs den Stop durchlief.
- **Verdrahtung wie jede Spur, aber papierfest:** `dauerlauf.SPUREN` (mit
  `skript`-Schluessel), Bus-SPUREN, Tagesbericht-Funktion + baue()-Tupel,
  `ereignis.lauf("handel/omniquant")`, .gitignore-Whitelist. `--vorschau` druckt
  die Sperrenzeile ohne das Wort Freigabefenster, damit der Dauerlauf nie fragt
  (Muster: spiegel-Spur). Signalquelle ist der VOLLE Prognose-Bericht.
- **Der Bericht meldet Paare, nicht Vermoegenswerte — eine Mess-Spur braucht einen
  Streuungs-Filter.** SOL-USDC und SOL-USDT sind zwei Treffer, aber ein Asset;
  zwei Positionen im selben Basiswert sind Klumpen und verzerren die Antwort, ob
  die Prognose traegt. `omniquant` hat `max_je_basiswert` (1) in wachen.json:
  heute geschlossener Basiswert kommt heute nicht wieder (Merkliste um Quote-Ebene
  erweitert), offener Basiswert bekommt keine zweite Position, innerhalb eines
  Zyklus geht je Basiswert nur der Staerkste durch (Bericht ist
  C/R-x-Score-sortiert). Bereits offene Doppel bleiben liegen — der Filter wirkt
  nur auf neue Kandidaten. Nachweis: Trockenlauf mit echtem Bericht (6 Treffer ->
  4 Basiswerte), Test zaehlt Basiswerte, nicht Treffer. Solche Kennzahlen gehoeren
  in wachen.json (Grenze), nicht in den Code.
- **Ein Papierbuch muss BEIDE Kostenseiten rechnen, sonst ist die Kernfrage schon
  zu optimistisch beantwortet.** `_ergebnis` rechnete nur die Ausstiegsseite,
  waehrend `_kostenfaktor` als toter Code daneben lag und der Docstring zwei
  Seiten behauptete: das Ergebnis war um die Haelfte der Kosten zu gut (0,25 %
  statt 0,5 % je Trade). Richtig ist `nominal * (1+bewegung) * (1-k)/(1+k)` fuer
  long und short; wichtigster Test des Buchs: **eine Position ohne Kursbewegung
  muss ein Minus von rund 2k ergeben**. Wer die Kostenseite nicht testet, misst
  Wunschzahlen. Abgeleitet: ein Short kann nicht mehr verlieren als seinen Einsatz
  -> `max(0.0, ...)` gegen einen negativen Erloes.
- **Was die Auswertung braucht, muss ins Journal, waehrend die Position laeuft.**
  Ausstiegszeilen ohne `score`/`cr` lassen keine Kalibrierung zu, und ohne
  mitgefuehrte Extreme (`mfe_pct`/`mae_pct`, an den Zykluspunkten fortgeschrieben,
  also Untergrenze) kann die Auswertung nicht trennen, ob ein Stop zu eng war
  (Position lief erst ins Plus) oder das Signal falsch. **Spalten nur per
  Kopfzeilen-Migration erweitern** — ein `DictWriter` mit neuer fieldnames-Liste
  auf einer Datei mit alter Kopfzeile schreibt Werte, die `DictReader` danach
  unter `None` ablegt.
  - **Die BESTEHENDE Datei mitmigrieren, nicht nur die Kopfzeile im Code.** Der
    Kopf in `journal()` wird nur beim ANLEGEN geschrieben (`if neu:`) — bei einer
    gewachsenen Datei aendert eine Code-Aenderung allein gar nichts: ab dann
    stehen n+3 Werte unter einer n-spaltigen Kopfzeile. Einmalig die Datei
    umschreiben (Kopf erweitern, jede Altzeile um so viele Leerfelder auffuellen,
    wie Spalten dazukamen), `lineterminator` explizit setzen — `csv.writer`
    schreibt sonst CRLF in eine LF-Datei oder umgekehrt, und aus der Migration
    wird ein Volltext-Diff.
  - **Der Ausstiegspfad ist nicht der einzige Schreiber.** Neue Spalten fuellen
    ALLE Ausstiegsstellen — auch der Notausstieg (`flach_stellen`, Kill-Switch /
    alter Herzschlag). Wird nur `pruefe_ausstiege` versorgt, fehlen die Werte
    ausgerechnet bei den Runden, die eine Stoerung erzeugt hat. Die Kaufzeile
    traegt die neuen Felder leer (`""`), nicht `0` — eine Null waere eine
    Messung, die nie stattfand.
  - **Eine Schema-Migration laesst Bedingung 4 auf ABWEICHUNG springen — das ist
    die richtige Antwort, kein Defekt.** Die Kopie ausser Haus traegt noch das
    alte Schema, `spiegelstand.py` vergleicht byte-genau. Ablauf, damit die
    Meldung deutbar bleibt: (1) `spiegelstand.py` VOR der Migration laufen lassen
    — nur wer weiss, dass vorher alles gleich war, darf die Abweichung der
    eigenen Aenderung zuschreiben; (2) migrieren; (3) belegen, dass die lokale
    Datei ohne die neuen Spalten byte-gleich der Kopie ist (Leerfelder und
    Kopf-Zusatz wegrechnen, `==` auf den Rohbytes) — erst dann ist die lokale
    Fassung nachweislich dieselbe Historie und nicht ein zweites Buch;
    (4) vorwaerts kopieren, `cmp` je Datei; (5) `spiegelstand.py` erneut. Wer bei
    Schritt 3 abkuerzt und einfach kopiert, ueberschreibt im Zweifel eine gesunde
    Kopie mit einer kaputten Migration.
  - **Die offenen Positionen bekommen die Felder NICHT rueckwirkend.** Sie laufen
    ueber den `get()`-Rueckfall weiter und werden ab dem naechsten Zyklus
    gemessen; ein rekonstruierter oder geschaetzter Startwert waere eine erfundene
    Messung. Nachweis am lebenden System: einen Zyklus abwarten und die Felder in
    `zustand.json` zeigen — ein gruener Testlauf beweist nur die Mechanik, nicht
    dass der Dauerlauf den neuen Code fuehrt.
- **Eine Auswertung behauptet nichts unter N Beobachtungen.** Unter
  `min_ausstiege` (8) gibt es Rohzahlen und den Satz, dass es fuer eine Schwelle
  nicht reicht; je Gruppe (Band, Richtung, Grund) erst ab 5 ein Hinweis, als Frage
  formuliert ('Schwelle pruefen'), nie als Anweisung: die Tore wurden an 41
  Maerkten kalibriert, drei Trades sind kein Gegenbeweis. Netto->Brutto wird
  zurueckgerechnet (`brutto_pct`), nicht geschaetzt.
- **Eine Auswertung wird an EINER Stelle gerechnet und an allen gezeigt.**
  Tagesbericht und GUI holen ihre Zeilen aus derselben Funktion
  (`auswertung.kernzeile()`/`kernzeilen()`, per `spur_omniquant()["bilanz"]` bzw.
  direkt) — zwei Formeln fuer dieselbe Frage sind zwei Wahrheiten. Fehlt das
  Modul, gehoert der Grund in die Zeile (`Auswertung nicht lesbar: …`), nicht ein
  leeres Feld.
- **Jede GUI-Zeile ist eine Behauptung ueber einen Zustand — jeder gelesene
  Feldname muss gegen die Schreiberseite geprueft werden.** Befund 13.09.2026: die
  Fusszeile las `einsatz_pro_position`, `kumulierte_verluste`, `kill_switch`;
  geschrieben werden `verluste_usd` und die Grenzen aus wachen.json. Folge:
  dauerhaft "Einsatz: ?" und "0.00 USD" Verlust, Kill-Switch selbst bei gerissenem
  Deckel auf "frei" — eine Anzeige, die im Zweifel das Gegenteil sagt. Zwei
  Gegenmittel: den abgeleiteten Wert als **reine Funktion** (`fuss_texte(z, w)`)
  aus der GUI ziehen, damit ein Test ohne Fenster greift; und ein Quelltext-Test,
  der erfundene Feldnamen im GUI-Code verbietet. Ein `ok`-Zyklus im Dauerlauf
  beweist nichts ueber die Anzeige — die hat keinen Waechter.
- **Ein Kostenfreibetrag ist ein RUNDENBUDGET, keine Lizenz fuer mehr Frequenz —
  und er dreht kein Vorzeichen.** Vor "lohnt sich das Abo fuer schnelleren
  Handel?" zwei Rechnungen aus dem Bestand:
  (1) Freivolumen / Einsatzgroesse = Runden je Monat (Kraken Pro, 10.000 EUR:
  ~100 Runden bei 50 EUR, ~500 bei 10 EUR — Minutenhandel sprengt das in Tagen).
  (2) Was kostet eine Runde OHNE Gebuehr? Die stillgelegte Kraken-Tages-Spur wurde
  gebuehrenfrei nachgerechnet und blieb bei -0,57 % je Runde: die Gebuehr war
  nicht die Ursache, das Signal trug nicht. Wer Gebuehrenfreiheit als
  Strategie-Argument bringt, muss diese Zahl zeigen.
  Dazu die Handelsrealitaet: schneller takten macht ein TAGES-Signal nicht besser,
  es altert nur (prognose.py erlaubt Berichte bis 26 h, Tore auf Tageskerzen
  kalibriert). Und eine Maschine, die unvermittelt ausgeht, kann keine Minutenspur
  mit offenen Positionen beaufsichtigen (Herzschlag-Regel bei den Pitfalls: 180
  Minuten Papier, 45 mit Handelserlaubnis). Ort fuer solche Kostenfakten:
  `Handel/CryptoPredictions_Wissen.md` (anhaengen) plus der `_gebuehren`-Block der
  betroffenen `wachen.json` — kein neuer Code, solange keine Strategie sich
  aendert. Stellt eine zweite Spur dieselbe Frage (traegt das Buch nach Kosten?),
  gehoert die Mechanik in ein gemeinsames Modul (`Handel/buchauswertung.py`); die
  Spur bringt nur mit, was anders ist: Aktionsnamen (omniquant "AUSSTIEG", spiegel
  "schliessen" — immer case-insensitiv vergleichen), Zusatzspalten, Gruppen,
  Baender. Kosten in ZWEI Faktoren abbilden: das eine Buch rechnet
  slippage+gebuehr als einen Satz je Seite, das andere beide Saetze nacheinander
  ((1+s)(1+g) beim Kauf). Sonst bedeutet "vor Kosten" in zwei Buechern zwei
  verschiedene Dinge; die Umkehrformel im Test haelt das fest.
- **Zwei Spuren mit gleichnamigem Modul sind eine Falle.** `import auswertung`
  gibt beim zweiten Mal das ERSTE Modul zurueck (sys.modules) — die zweite Spur
  traegt die Zahlen der ersten. Ueber den Dateipfad laden
  (`importlib.util.spec_from_file_location`) und dabei `sys.dont_write_bytecode`
  setzen: der Import legt sonst einen `__pycache__`-Eintrag im Spurordner an, und
  ein Bericht darf nichts schreiben (`test_bericht_schreibt_nichts`).
- **Bei schiefen Verteilungen gehoert der Median neben den Mittelwert.** Erstes
  echtes Ergebnis des Spiegel-Buchs: Mittelwert +23 % je Position, Median -30,8 %,
  Treffer 19/45. Der Durchschnitt traegt an wenigen Ausreissern, die typische
  Kopie verliert — die Kernzahlen muessen beide Zahlen nennen.
  `omniquant/gui.py` ist eine Tkinter-App: liest zustand.json + neuester.json +
  handelsjournal.csv, holt Kurse/Kerzen ueber `scanner/okx` in
  Hintergrund-Threads (Netz blockiert das Fenster nicht; Refresh 15 s), schreibt
  NICHTS — Dauerlauf bleibt der einzige Schreiber. Neben der Positionstabelle
  zeigt sie die letzten Schliessungen aus dem Journal (G/V aus wert/einsatz
  gerechnet; das Journal hat kein gv-Feld) und einen Kerzenchart: Klick auf eine
  Tabellenzeile laedt `okx.kerzen(inst, bar="1D", anzahl=90)` (aufsteigend,
  [ts,o,h,l,c,vol]), ohne Auswahl das erste Instrument. Der Stop-Abstand nutzt
  dieselbe richtungsbewusste Formel wie zeile_position im Tagesbericht.
- **GUI-Start verifiziert man am FENSTER, nicht am Start-Status.** Start:
  venv-python gui.py im omniquant-Ordner; GUI-Startprozesse sind venv-Paare aus
  Launcher + Interpreter. Der `Start-Process -PassThru`-PID ist der Launcher und
  meldet eine LEERE MainWindowTitle — der Titel steht auf dem Kind: alle
  python-Prozesse nach MainWindowTitle durchsuchen. Auch die Fensterliste des
  Screenshot-Tools kann „No windows found" sagen, obwohl das Fenster im Bild
  sichtbar ist — das BILD auswerten (vision_analyze), nicht die Metadaten.
- **Eine Tk-Builder-Methode kennt kein `root`.** `_baue()` laeuft aus `__init__`
  heraus und hat nur `self.root`; ein blosses `root` im Builder ist ein NameError.
  `ttk` ist nicht Teil von `import tkinter as tk` — explizit
  `from tkinter import ttk`. Beide Fehler erscheinen erst beim ECHTEN Start (ein
  tk-Mock im Importtest verdeckt sie); nach jedem GUI-Umbau echten Start mit
  Fenster-Titel pruefen, nicht nur ast.parse.
- **Die stderr-Umleitung einer GUI nie per `Get-Content -Tail` lesen, solange der
  Prozess lebt.** Er haelt die Datei offen; das Tail wartet auf neuen Inhalt und
  haengt bis zum Timeout. Start-Debug: erst Prozess-Lebenspruefung, Logdatei nur
  lesen, wenn der Prozess TOT ist (dann steht der Traceback drin; lebt er, ist der
  Start geglueckt).

## Kraken-Spur wieder im Dauerlauf (`Handel/kraken`, 14.09.2026)

- **Sie war stillgelegt, nicht entfernt.** `stillgelegt: true` in
  `kraken/wachen.json` liess `handeln.py` jeden Papier- und Live-Lauf verweigern,
  `--wachen`/`--vorschau` blieben erlaubt. Wieder anlaufen: NUR diesen Schalter
  umlegen und die Spur in `dauerlauf.SPUREN` aufnehmen
  (`{"ordner": "kraken", "waehrung": "EUR"}`); die Aufgabe `MaxHirn-Kraken-Spur3`
  rechnet dann nur noch den Scan.
- **Der Herzschlag muss zum Takt passen — bei jeder Spur im Takt, nicht nur hier.**
  2880 Minuten (48 h) passen zur Tagesroutine und decken im Viertelstundentakt
  nichts ab; jede Grenze unter der Selbstheilungszeit macht jeden Rechnerneustart
  zum Notausstieg. Die Regel (180 Minuten Papier, 45 mit Handelserlaubnis) steht
  bei den Pitfalls und gilt fuer jede Spur im Takt. Wer ihn aendert, aendert ihn
  in DERSELBEN Sitzung wie den Takt — sonst stellt der erste Lauf alles flach,
  weil der letzte gesunde Lauf aelter ist als das neue Fenster (539 min > 180:
  vier Papierpositionen als `herzschlag_alt` geschlossen, bevor der Dauerlauf die
  Spur uebernahm). Mit diesem Flush rechnen, im Bericht nennen, die Spur erst
  danach als uebernommen ansehen; vermeiden laesst er sich, indem man den Wert
  erst setzt, waehrend die Spur schon im Takt laeuft.
- **Der Einstand kommt vom lebenden Kurs, nicht aus der Rangliste.** Solange die
  Spur einmal am Tag direkt nach dem Scan lief, war der Berichtspreis Sekunden
  alt; im Takt waere er bis zu einen Tag alt. `_kurs_jetzt(inst, rueckfall)` holt
  `kraken.letzter_kurs` (Rueckfall: Berichtspreis), Stop und Ziel rechnen auf
  diesem Kurs. Der Bericht waehlt nur noch AUS.
- **Eine alte Rangliste darf nicht handeln.** `bericht_max_alter_tage` (3) sperrt
  die EINSTIEGE, wenn das Datum fehlt, unlesbar oder zu alt ist — Ausstiege laufen
  immer. Ohne die Sperre handelt ein ausgefallener Scan an einer Liste von
  vorvorgestern.
- **Tests unter `kraken/tests/`** (AUSSTIEG-Zeile mit Filterwort, Alter der
  Rangliste, lebender Einstand): `discover -s tests -t tests` aus dem
  kraken-Ordner. Die `.gitignore`-Whitelist braucht
  `!Agenten/Handel/kraken/tests/*.py` — sonst faengt die Regel `*` sie mit ein.

## Gitter-Spur (`Handel/gitter`, Papierbuch auf OKX-Stundenkerzen, 14.09.2026)

- **Der Ordner heisst `gitter`, nicht `grid`.** Es gibt schon `Handel/grid.py`
  (Simulator); ein Ordner `grid/` daneben waere ein Namensvetter im selben
  Suchpfad — `import grid` traefe das Paket statt der Datei, der Simulator waere
  still kaputt.
- **Ein Gitter ist ein Buch, keine Wache.** Kein Stop, kein Ziel je Position — das
  Ziel ist die naechste Stufe. Deshalb `positionen` mit `ziel` und ohne `stop`,
  und **Bedingung 3 greift bewusst nicht** (nichts am Markt, das unbewacht waere;
  ein Ausfall holt beim naechsten Zyklus alle Kerzen nach). Wer eine
  Herzschlag-Wache erzwingt, verkauft beim Neustart Inventar zum Marktpreis.
- **Die Kerzen-Regel ist die Aussage der Spur.** Je abgeschlossener Kerze: erst
  Kaeufe (Tief <= Stufe), dann Verkaeufe (Hoch >= naechste Stufe), nur fuer Lose,
  die VOR dieser Kerze lagen; am Ende neu armieren (`arme(z, schluss)`), laufende
  Kerze verwerfen. Ohne die Regel "nichts verkauft, was in derselben Kerze gekauft
  wurde" erfindet der Durchlauf Zyklen, die es nie gab — der Backtest rechnet
  dieselbe Regel (Order aus Kerze N wirkt ab N+1).
- **Nachziehen ab dem letzten Kerzenstempel**, nicht nur die neueste Kerze: das
  Fenster (300 Kerzen) deckt 12,5 Tage ab, ein Neustart verliert nichts. Stempel
  in `zustand.json` (`letzte_kerze_ts`), im Test gegen einen zweiten,
  unterbrochenen Durchlauf geprueft.
- **Raster der Boerse lesen**, nicht raten: `okx._mit_wiederholung(
  "/api/v5/public/instruments?instType=SPOT&instId=...")` liefert tickSz, lotSz,
  minSz. Preise runden (`raster()` über Decimal — `78236.4/0.1` ist in Gleitkomma
  782364.0000000001), Mengen ABrunden, unter minSz auf 0 setzen, sonst reisst die
  Summe den Einsatz.
- **Die Positionsliste wird ABGELEITET, nicht gepflegt.** `positionen_aus(z)`
  rechnet sie aus `lose` (Bus und Handelszentrale lesen dieselben Felder:
  inst/seite/einstieg/menge/nominal/ziel/eroeffnet). Zwei getrennte Quellen laufen
  auseinander, die Anzeige sagt "0 Positionen" bei offenem Bestand. Kein
  `hebel`-Feld: ein Spot-Gitter hat keinen.
- **Journaldatei mit Kopfzeile anlegen, auch ohne Buchung.** Der byte-genaue Stand
  der Kopie ausser Haus vergleicht DATEIEN — eine fehlende Datei liest sich wie
  ein Unterschied, obwohl beide Seiten nichts haben (`spiegelstand` meldete
  `gitter ABWEICHUNG` bei leerem Buch).

## Nautilus-Spur (OKX-DEMO-Node als Papierzyklus, 13.09.2026)

- **Backtest-Seite dieser Spur:** `nautilus/backtest_grid.py` +
  `grid_strategie.py` (statische Kaufleiter, Stufenformel gleich
  `Handel/grid.py`) + `bars_aus_daten.py` + `test_grid.py`, Start ueber das
  nautilus-eigene venv. Die Fallen dieser Umgebung (Venue vom Instrument,
  BarDataWrangler/pandas 3, eindeutige Orderkennungen, Kontoreport bewertet
  offenen Bestand zum Einstand) stehen im Skill `nautilus-okx-handel` — vor einem
  Backtest dort nachsehen.
- **Eine Event-Engine wird als BEGRENZTER Zyklus angebunden, nicht als
  Dauerprozess.** Der Dauerlauf ruft je Zyklus eine Spur als Unterprozess auf
  (Timeout 600 s) — ein Node, der bis Strg+C laeuft, passt nicht ins Muster.
  `nautilus/handeln.py` startet den Node je Zyklus fuer ~30 s (Thread, dann
  `node.stop()`), sammelt BTC-USDT-SWAP-Quotes vom oeffentlichen Websocket,
  schreibt Herzschlag (`zustand.json` `letzter_lauf`) + Journal, beendet sich.
  30 s bringen ~40 Ticks (gemessen 12./13.09.2026) — genug als Lebenszeichen.
- **Papierfest wie spiegel/omniquant:** `--live` verweigert mit einem Grund OHNE
  das Wort Freigabefenster, damit `dauerlauf.nur_fenster_fehlt` nie eine Freigabe
  anfragt, die nichts oeffnen kann. Der Node hat keinen Live-Zweig (Schluessel
  read_only, keine IP-Whitelist fuer Orders).
- **Eigenes venv noetig:** nautilus_trader liegt nur in `nautilus/.venv`. Der
  SPUREN-Eintrag traegt `"python"` (siehe Landkarte); Verkabelung sonst identisch
  (Bus-SPUREN, tagesbericht `spur_nautilus` + baue-Tupel,
  `ereignis.lauf("handel/nautilus")`).
- **Nautilus-Logger nimmt keine printf-Args:** `self.log.info("x %s", y)` wirft
  `TypeError: an integer is required` — immer f-strings (`f"x {y}"`). Gleiche
  Falle in Strategie/on_start wie in jedem Callback.
- **Vorschau-schreibt-nichts-Test ueber WEGLEGEN pruefen, nicht ueber den
  tmp-Pfad.** Echte zustand.json/Journal per `os.replace` in ein tmp legen,
  `--vorschau` laufen lassen, pruefen dass der ORIGINALPFAD nicht neu entsteht
  (der tmp-Pfad existiert natuerlich — dahin wurde verschoben).
  `tearDown`/finally stellt zurueck.
- **Eine fremde Log-Zeile trifft den Stichwortfilter zufaellig — der fehlende
  Handler ist die Ursache.** NautilusTrader warnt bei jedem `node.stop()` ("The
  `Strategy.on_stop` handler was called when not overridden …"), solange die
  Strategie diesen Handler nicht selbst stellt. Die Zeile ist harmlos, sieht wie
  ein Fehler aus, traegt ANSI-Codes des Rich-Loggers und enthaelt `on_stop` — also
  `stop`, ein Filterwort des Dauerlaufs (13.09.2026 genau so als angeblicher
  Fehler nach Telegram). Beide Gegenmittel noetig: der **eigene `on_stop`** (Abo
  abmelden; Gegenprobe mit entzogenem Handler (`del QuoteSammler.on_stop`) bringt
  die Warnung zurueck) und ein **Log-Pegel ERROR** fuer den begrenzten Lauf,
  ausgelagert in eine pruefbare `baue_node_config()`. Alarme der Spur laufen ueber
  Rueckgabecode und `quotes_letzter_zyklus`, nie ueber fremde Logs.
- **Am `sys.stdout`-Redirect vorbei.** Nautilus-Logzeilen erscheinen NICHT in
  einer `contextlib.redirect_stdout`-Umleitung — sie gehen direkt auf die Konsole
  (13.09.2026: die on_stop-Warnung stand im Prozesslauf, nicht im eingesammelten
  Puffer). Eine Spur kann fremden Log-Laerm nicht selbst wegfiltern; nur Handler
  und Log-Pegel wirken. Ein Test, der "keine Filterwoerter in der Ausgabe"
  behaupten will, muss den echten Prozesslauf (subprocess, stdout+stderr)
  auswerten, nicht einen Redirect.
- **Eigenes .git der Spur:** zustand.json/handelsjournal.csv in die EIGENE
  `.gitignore` des Spur-Repos aufnehmen (Laufzeitzustand), nur Code + Tests +
  README committen und pushen. BrainFiles-Repo und Spur-Repo sind getrennt — beide
  Commits + Pushes gehoeren zum Anbinden. Ein Rollout ueber `Handel/**` im
  BrainFiles-Repo nimmt eine Datei im eigenen Repo NICHT mit: `git add` steigt in
  ein fremdes Repo nicht hinab. Nach jeder solchen Aenderung
  `git -C <spur> status --short` pruefen und dort EINZELN committen
  (`git commit -o <datei>`) — fremde Aenderungen im selben Baum (ein laufender
  Backtest schreibt seine Ergebnisdatei) bleiben liegen.

