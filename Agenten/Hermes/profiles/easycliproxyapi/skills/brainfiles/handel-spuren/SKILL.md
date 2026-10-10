---
name: handel-spuren
description: "Handelsspuren scanner/xperp/orb: Sperren, Freigabe, Tore."
category: brainfiles
---

# Handelsspuren

## Wann
Jede Änderung unter `Agenten/Handel/**`: eine Sperre ergänzen, eine Freigabe
verdrahten, ein neues Analysemodul bauen, Wachenwerte anfassen, Tests schreiben,
eine Spur an einen fremden Feed haengen (Kurs-, Signal- oder Wallet-Daten).
Auch beim Deuten einer Bus-Meldung, die eine Spur als „Ergebniscode 1“ meldet.
Spuren: scanner, xperp (Hauptweg), orb, swap, spiegel, kraken (stillgelegt).

## Landkarte (nur was zum Arbeiten nötig ist)
- `Agenten/Handel/<spur>/` — je Spur `handeln.py`, `wachen.json` (die Grenzen;
nur gelesen, einzige Ausnahme `sperre_zu` true→false), `zustand.json`,
  `handelsjournal.csv`.
- `Agenten/Handel/dauerlauf.py` — 24/7-Treiber. Startet je Spur
  `handeln.py --live/--papier` als Unterprozess und **liest dessen Ausgabe**.
- `Agenten/Handel/freigabe.py` — Bestätigungsfenster am Bildschirm, je
  Vorschlag einzeln.
- `Agenten/Handel/freigabefenster.py` — Zeitfenster fürs Handy (`/ja`, `/nein`,
  `/stop`), eigener Zustand in `freigabe_fenster.json`, nie in wachen.json.
- `Agenten/Handel/prognose.py` — Beobachter über den ganzen Markt, stellt keine
  Order, kennt keine Spur, Tore in `prognose.json`.
- `Agenten/Handel/spiegel/` — Papierbuch auf einem fremden Feed (OnchainOS):
  `lesen.py` liest nur, `spiegel.py` bucht nach, kein Orderpfad. Muster fuer
  jede weitere Feed-Anbindung: `references/fremdfeed-papierbuch.md`.
- Interpreter immer `.venv\Scripts\python.exe` im Handel-Ordner, Aufruf aus dem
  jeweiligen Spurordner.

## Prozedur
1. **Lage lesen, nicht erinnern.** `handeln.py --vorschau` mit
   `MAXHIRN_ROUTINE=1` läuft ohne Fenster und nennt jede geschlossene Sperre.
   Die Sperrliste im Code lesen (`sperren_live`), nicht aus dem Gedächtnis.
2. **Sichern** (Stufe 1): `.bak-JJJJMMTT` für jede Datei, die angefasst wird —
   auch `wachen.json` und `zustand.json`, wenn ein Testlauf sie berühren kann.
3. **Ändern:** Sperren gehören in `sperren_live()` bzw. die gleichnamige
   Funktion der Spur, nicht verstreut in den Rumpf von `lauf()`.
4. **Ohne Broker testen.** `cd <spur> && python -m unittest discover -s tests`.
   Den Interpreter dabei **absolut** angeben
   (z. B. `C:/…/Handel/scanner/.venv/Scripts/python.exe`): ein relativer Pfad
   bricht nach dem `cd`, und die leere Ausgabe sieht danach wie „keine Tests“
   aus statt wie ein Fehler.
   Für den Live-Pfad `pruefe_einstiege`/`pruefe_ausstiege` per Lambda stilllegen,
   das Fenster regulär öffnen, den Lauf starten und die Zustandsdateien
   vorher/nachher per Hash vergleichen. Ein Test darf `markt_kauf` nie
   erreichen. Eine geänderte Ausgabezeile zusätzlich **rendern statt lesen**:
   die `print`-Anweisung per `ast.get_source_segment` aus der Datei holen, mit
   `ast.parse`/`compile` übersetzen und mit Beispieldaten ausführen — dann steht
   schwarz auf weiß da, was der Nutzer zu sehen bekommt. Eine Formatprüfung im
   Kopf ist kein Nachweis, und `ast.parse` allein prüft nur die Syntax.
5. **Versionieren.** `.gitignore` ist eine **Whitelist** (erst alles ignorieren,
   dann einzeln freigeben). Jede neue `.py`/`.json`/Testdatei braucht eine
   eigene `!`-Zeile, sonst landet sie still nicht im Verlauf. Eine solche Zeile
   ohne `!` ist eine **Sperre** - sie sieht wie eine Freigabe aus und bewirkt
   das Gegenteil; mehrfach eingefuegte, gleiche Bloecke sind dasselbe Symptom.
   Gegenprobe deshalb zweimal: `git check-ignore -v <pfad>` nennt die
   entscheidende Regel, und `git status --porcelain <ordner>` muss die neuen
   Dateien als `??` zeigen. Versionierte Textdateien dabei nie komplett neu
   schreiben: die Fassung aus `HEAD` holen (Verlauf LF, Arbeitsbaum gern CRLF)
   und genau die gewollten Stellen ersetzen. `git diff --stat` muss danach die
   geaenderte Zeilenzahl zeigen, nicht die ganze Datei.

## Pitfalls
- **Der Sperrtext ist eine Schnittstelle.** `dauerlauf.nur_fenster_fehlt` liest
  die Zeile `Live waere gesperrt durch: …` und stellt nur dann eine
  Freigabe-Anfrage, wenn dort genau EIN Grund steht und dieser
  „Freigabefenster“ enthält — kein `;` und kein `:` darin. Die Formulierung
  ändern, ohne die Leser zu suchen, heißt: es wird nie gefragt, und jedes `/ja`
  bleibt folgenlos. Vor jeder Textänderung nach den Verbrauchern greppen.
- **Diagnose in jedem Modus drucken, den ein Aufrufer parst.** Eine Zeile, die
  nur im `--live`-Zweig fällt, existiert für `--vorschau` nicht — und
  `--vorschau` ist genau das, womit der Dauerlauf die Lage prüft.
- **Gemeldet wird zeilenweise, nicht im Block.** Der Dauerlauf filtert die
  Ausgabe jeder Spur nach Stichwörtern (`verkauf`, `stop`, `KILL`, `gesperrt`)
  und schickt **nur die passende Zeile** nach Telegram. Jede Zeile, die eines
  dieser Wörter enthalten kann, muss Instrument und Seite selbst nennen; eine
  Fortsetzungszeile ohne Subjekt kommt unzuordenbar an. Bei jeder neuen
  Ausgabezeile prüfen, ob sie allein verständlich ist — und bei einer kurzen
  Seite wie `Liq über Stop, Ziel darunter` auch, ob sie ohne die Richtung
  (`long`/`short`) wie ein Fehler aussieht.
- **Zwei Prozesse mit identischer Kommandozeile sind kein Doppellauf.** Ein
  venv-Start erzeugt ein Paar aus Launcher und echtem Interpreter, beide mit
  derselben `CommandLine`. Bevor ein Doppellauf gemeldet wird: jede PID
  einzeln mit Startzeit und Eltern-PID ausgeben und die Liste vollständig
  zeigen. Ein Fehlalarm kostet mehr Vertrauen als die Prüfung Zeit — und muss,
  wenn er passiert ist, ausdrücklich zurückgenommen werden.
- **Erst nachsehen, wer den Ausstieg speist, bevor eine Marktart als unsicher
  gilt.** `pruefe_ausstiege` rechnet allein aus `zustand.json` und schliesst per
  instId; `okxf.positionen()` und `okxf.offene_orders()` sind FUTURES-fest,
  haben aber keinen einzigen Aufrufer im Handel-, Bus- und Testbaum. Eine
  Aussage wie „fuer SWAP gibt es keine Stop-Ueberwachung, weil positionen()
  FUTURES-gefiltert ist“ ist damit schlicht falsch. Vor jeder solchen Aussage
  die Aufrufer greppen - ein Fehlalarm kostet mehr Vertrauen als die Pruefung
  Zeit.
- Code-Ersetzungen an Dateien mit `\n` im Quelltext: die Muster als
  RAW-Strings schreiben (r'''...'''), sonst interpretiert Python das `\n`
  im Muster als Zeilenumbruch, waerend die Datei die zwei Zeichen Backslash-n
  enthaelt - die Ersetzung greift ins Leere. Der Fixer muss ausserdem die
  Zeilenenden des Originals erhalten (CRLF/LF vorher erkennen), sonst wird aus
  einer Zeilenaenderung ein Volltext-Diff.
- **Eine Sperre muss auch aufgehen können.** Ein Tor, das nie öffnet, sieht wie
  Sicherheit aus und ist ein Fehler: `references/tor-kalibrierung.md`.
- **Zwei Fassungen derselben Sperre, eine Wahrheit.** Neue Spuren nach dem
  Muster einer bereits richtigen Spur bauen, nicht eine dritte Variante
  erfinden (xperp war beim Freigabe-Weg zuerst richtig).
- **Zustandsdateien vergiften sich.** `zustand.json` wächst bei jedem echten
  Lauf; sichern statt reparieren.
- **Eine Ablehnung darf nicht gleich wieder gefragt werden.** Die Antwortfrist
  (`ANTWORT_FRIST_MINUTEN`, 30 min) bestimmt nur, wie lange eine Anfrage
  offensteht - nicht, wann erneut gefragt wird. Ohne eigene Frist stand hier
  alle 30 Minuten dieselbe Frage, auch 15 Minuten nach einem `/nein`.
  `freigabefenster.neue_anfrage_erlaubt()` haelt zwei Wiedervorlage-Fristen:
  2 h nach einer unbeantworteten Anfrage, 12 h nach einer Ablehnung (`/nein`,
  `/stop`); Grundlage sind `anfrage_gestellt` und `zuletzt_geschlossen` der
  eigenen Zustandsdatei, keine zweite Merkdatei. Das ist keine Sperre -
  scharfgeschaltet wird weiter am Bildschirm oder per Antwort auf die naechste
  Anfrage. Nachweis: `tests/test_telegram_freigabe.py`, `WiedervorlageTest` und
  `WiedervorlageImLaufTest` (die zweite prueft, dass die Frist im Dauerlauf
  ankommt).
- **Vor jeder Aenderung an `SPUREN` erst nachsehen, was schon laeuft.** Ein
  Handstart neben dem Dienst ist kein zweiter Lauf derselben Sache: zwei Poller
  an einem Telegram-Token nehmen sich gegenseitig die Nachrichten weg (409),
  und der Handstart laeuft oft mit einem anderen Interpreter (System-Python
  statt `scanner/.venv`). Alle `python*dauerlauf*`-Prozesse mit Startzeit und
  Eltern-PID auflisten, dann genau einen ueber `Routinen/handel-dauerlauf.ps1`
  starten - der setzt `dauerlauf.pid` und raeumt eine verwaiste Sperre selbst
  auf.
- **Nur `dauerlauf.py` selbst braucht einen Neustart.** Jede Spur laeuft als
  Unterprozess (`subprocess.run([PYTHON, SPUREN[spur].get("skript",
  "handeln.py"), modus])`) - eine
  Aenderung an `handeln.py`, `wachen.json` oder einem Spurmodul greift schon im
  naechsten Zyklus. Was im laufenden Prozess steht (`SPUREN`,
  `pruefe_anfragen`, die Aufrufe von `tagesbericht`), wirkt erst nach einem
  Neustart - und der Lauf schickt danach sofort einen Tagesbericht, weil sein
  eigener Merker leer ist (am 12.09.2026: zwei Berichte an einem Abend).
- **Tests dürfen keinen Konfigurationswert behaupten.** Ein Test, der auf den
  heutigen Inhalt von `wachen.json` baut (z. B. „Kraken ist stillgelegt“),
  bricht in dem Moment, in dem Max den Schalter von Hand umlegt — und wird dann
  abgeschwächt statt ernst genommen. Die echte Datei als **Form** nehmen
  (Felder vorhanden, Typ stimmt), die Behauptung über eine Kopie mit
  ausdrücklich gesetzten Werten führen: die Mechanik prüfen, nicht den Stand.
- **`.env`, `Wissen/Zugaenge.md`, `proxy.yaml` sind tabu** — nie lesen,
  ausgeben oder protokollieren.
- **Eine neue Spur muss in die Meldungen, sonst meldet sie niemand.** Vier
  Stellen, alle vier noetig: `dauerlauf.SPUREN` (mit `"skript"`, wenn die
  Einstiegsdatei nicht `handeln.py` heisst - sonst startet der Lauf
  `handeln.py` im Spurordner, und die Logzeile `<spur> Rueckgabe 2` heisst
  nichts anderes als „Datei nicht gefunden“), `Bus/handel_befehle.SPUREN`
  (fuer `/status`), `tagesbericht.spur_<name>()` **und** der Eintrag im Tupel
  in `baue()`.
- **Keine Behauptung ueber eine andere Spur im Code.** Ein Satz wie „SWAP:
  Papierpfad, kein Live-Zweig“ oder ein Flag `papierfest` altert in Minuten:
  SWAP bekam waehrend derselben Sitzung einen Live-Pfad, und `/status` und
  Tagesbericht logen danach. Was gemeldet wird, wird aus `wachen.json` und
  `zustand.json` der Spur **gelesen** (Werte, Modus) - und vor jeder Aussage
  ueber fremde Spuren erst `git log --oneline -5`: an diesem Baum arbeiten
  mehrere Sitzungen gleichzeitig.
- **Wachen-Module liegen nicht immer im eigenen Ordner.** Liegt das
  `pruefmodul` woanders (SWAP liest `xperp/wachen_xperp.py`), muss der Pfad
  dorthin auf `sys.path` - sonst schreibt der Bericht „Wachen nicht lesbar“,
  obwohl nur der Import fehlte. Ein fester Modulpfad aus `__file__` (nicht aus
  einer in Tests umgebogenen Konstante) haelt das aus.
- **Ausstiegsgruende nach Schwere pruefen, nicht nach Naehe.** Die
  Liquidationsschwelle liegt immer hinter dem Stop: Stand der Stop zuerst im
  `if`, war der Liquidationszweig toter Code, und ein Gap bis hinter die Liq
  meldete „stop" statt „LIQUIDATION". Beide Spuren pruefen die Liq zuerst
  (`xperp/handeln.py`, `swap/handeln.py`); Nachweis `xperp/test_ausstieg.py`
  (9 Tests, Long und Short, Kurs genau auf der Schwelle; `okxf.markt_schliessen`
  im Test durch einen Werfer ersetzt, damit kein Test den Order-Pfad erreicht).
  Am Geld aendert die Reihenfolge nichts - gerechnet wird mit dem echten Kurs,
  geschlossen wird unabhaengig vom Grund; falsch war nur das Journal-Etikett.
- **Ausgabe testen, nicht Quelltext.** Wer eine gedruckte Zeile pruefen will,
  darf nicht die Datei durchsuchen: Modulkopf und Kommentare erklaeren die
  Regel und enthalten dieselben Woerter. Die `print`-Argumente per `ast` holen
  und genau die Zeichenkette pruefen, die der Verbraucher liest.
- **Eine Vorschau, die schreibt, ist keine Vorschau.** Laeuft in `--vorschau`
  der Ausstiegspfad mit, schliesst sie Kopien im Journal und schreibt den
  Zustand nicht - danach sagen Journal und Zustand Verschiedenes, und die
  naechste Runde schliesst dieselbe Position ein zweites Mal. Richtig ist ein
  Schalter an **einer** Stelle (modulweites `SCHREIBEN`, das `journal()` und
  `schreibe_zustand()` gemeinsam pruefen), nicht ein `if modus == "vorschau"`
  an jedem Aufrufer; die Ausgabezeilen der Vorschau markieren sich als
  „WAERE ZU“. Nachweis: ein Test laesst die Vorschau mit einer offenen Position
  laufen und prueft, dass das Journal leer bleibt und die Zustandsdatei nicht
  angelegt wird.

## SWAP anbinden (Stand 11.09.2026)

- **Das Universum ist FUTURES-fest.** `okxf.instrumente()` liefert nur
  `ruleType=xperp` unter `instType=FUTURES`. SWAP-Reihen kommen ueber
  `okxf._mit_wiederholung("/api/v5/public/instruments?instType=SWAP")` mit
  `state=live`, `ctType=linear`, `settleCcy=USDT` und Endung `-USDT-SWAP`
  (11.09.2026: 464 lebende Reihen gegen 207 Futures-Ticker). Bewerten kann SWAP
  schon: `swap_instrument()`, `instrument("...-SWAP")`, `tickers("SWAP")`,
  `ist_swap` in bot.py, `historie.swap_id()`.
- **Ein voller Bewertungslauf dauert Minuten.** Zwei Kerzenabrufe je Reihe, OKX
  laesst rund 40 Anfragen je 2 s zu. Vorher nach Umsatz sortieren und nur die
  Spitze holen - und die Zahl der bewerteten Reihen in den Kopf der Ausgabe
  schreiben, sonst sieht eine kurze Liste wie ein leeres Universum aus.
- **Kandidaten der SWAP-Spur muessen den vollen instId tragen.**
  `okxf.instrument("CHIP")` loest auf den XPERP-Kontrakt auf, nicht auf
  `CHIP-USDT-SWAP`. Ein Anlauf, der das Instrument aus dem Basiswert holt,
  handelt still den falschen Kontrakt.
- **Eine Papierspur darf kein Modul importieren, das den Live-Order-Pfad
  traegt.** `xperp/handeln.py` enthaelt `hebel_setzen` und `order_limit`; wer es
  importiert - auch nur, um Pfadkonstanten umzubiegen -, haengt die Papierspur an
  dieselbe Leitung. Papier zuerst als eigenes Modul ohne Order-Funktion, per Test
  belegt; der Live-Zweig entsteht spaeter bewusst nach xperp-Muster.
- **Der Verweigerungsgrund haelt den Dauerlauf still.** `handeln.py --live`
  druckt genau einen Grund, in dem das Wort „Freigabefenster“ nicht vorkommt;
  `dauerlauf.nur_fenster_fehlt` liest diese Zeile und fragt deshalb keine
  Freigabe an, die nichts oeffnen koennte. Wer den Text anfasst, muss beide
  gedruckten Zeilen (`--vorschau` und `--live`) gegen dieselbe Regel pruefen -
  und den Test dazu ueber die gedruckten Zeichenketten laufen lassen, nicht
  ueber die Datei.

## Werkzeugfallen am Host
- Das Host-PowerShell-Werkzeug hat eine harte Zeitgrenze (~300 s). Eine
  rekursive Größenmessung über einen großen Baum reißt sie. Stattdessen
  vorher/nachher `Win32_LogicalDisk.FreeSpace` messen oder je Ordner einzeln —
  der Zuwachs ist die belastbare Zahl.
- Windows begrenzt die Kommandozeile (~32k Zeichen): ein großer
  PowerShell-Here-String scheitert mit `WinError 206`. Lange Dateien in Teilen
  schreiben (`Set-Content`, dann `Add-Content`) oder einen kleinen Applier
  lesen lassen, der die Nutzlast aus einer Datei holt.
- Geschriebene `.py`/`.json` danach prüfen statt annehmen: `ast.parse` bzw.
  `json.loads`, dazu kein BOM und kein `\r`. Beim Weg über einen
  PowerShell-Here-String mit `utf-8-sig` einlesen, `\r` entfernen, dann mit
  `newline=""` schreiben.

## References
- `references/freigabe-kette.md` — Punkt 3 der Handelsregeln in beiden
  Fassungen: Bildschirmfenster und Zeitfenster, wer wann öffnet, was eine
  Freigabe nicht kann.
- `references/tor-kalibrierung.md` — Schwellen und Kostenannahmen kalibrieren,
  ohne dass sie entweder nichts filtern, nie aufgehen oder eine Wunschrechnung
  sind (Tore, Filter, Slippage/Gebühr).
- `references/fremdfeed-papierbuch.md` — eine Spur an einen fremden Signal-Feed
  haengen (Copy-Trading, Spiegelung, Signalstudie): Leser mit Schreibschutz,
  Auswahlregel gegen Zuchtauswahl, Kosten zweimal gerechnet, Tore vor jeder
  Buchzeile.
