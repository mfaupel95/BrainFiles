# Frequenz, Hebel und Stop an einem Fremdlaeufer

## Wann
Max fragt an einem FREMDPROGRAMM, das schon laeuft (Rust-Laeufer, CLI,
Bot-Framework): „kann das nicht oefter handeln?", „mit Hebel", „mit
Trailing-Stop", „in kurzen Zeitintervallen", „hoehere Trefferchance".
Reihenfolge: erst die FAEHIGKEITEN des Laeufers am Code feststellen, dann die
Gebuehr rechnen, dann messen. Nicht mit einer Optionsliste antworten.

## 1. Drei Faehigkeiten am CODE feststellen, nicht am Gefuehl
Jede der drei Fragen hat eine Stelle im Code, an der sie beantwortet ist:

| Frage | Fundstelle | Was die Antwort bedeutet |
|---|---|---|
| Oefter? | der Takt ist ein Schalter des Lauf-Befehls (`--interval`), die Zahl der Runden kommt vom SIGNAL | 0 Orders in 2,4 h ist ein Signalbefund, kein Loop-Problem |
| Stop/Trailing? | sucht der Live-Loop eine Stop-/Algo-Order an der Boerse, oder rechnet er den Stop im Prozess? | im Prozess gerechnet = Software-Stop, stirbt mit dem Prozess |
| Hebel? | wird das Leverage-Modul des Risk-Crates von cli/engine AUFGERUFEN? | ein Guard-Modul mit Docstring ist kein Beleg — greppen |

- **Ein Risk-Modul ohne Aufrufer ist toter Code.** Ein `LeverageGuard` mit
  `max_leverage`/`min_liquidation_distance` und gruenen Unit-Tests sagt nichts
  darueber, ob der Live-Pfad Hebel kennt: eine Suche (`search_files`, grep) ueber
  `<cli>/src` und `<engine>/src` muss einen echten Aufruf zeigen, sonst ist die
  Antwort „gibt es nicht".
- **Ein Laeufer, der nur Market-Orders schickt, hat keinen Boersen-Stop.** Ein
  Stop im Strategie-Skript wird vom Evaluator im Prozess geprueft - das ist die
  Klasse Fehler, die das Haus teuer gelernt hat (Position ohne Schutzauftrag an
  der Boerse). Hausregel: der Stop geht MIT der Order an die Boerse
  (`attachAlgoOrds` / Algo-Order). Wer einen Fremdlaeufer live nimmt, prueft das
  VOR dem Scharfschalten und sagt es.
- **Skript-Stop gegen Backtest-Stop sind zwei verschiedene Groessen.** Im
  Backtest wird das Trailing-Hoch aus dem KERZENHOCH fortgeschrieben, im
  Live-Evaluator aus dem KERZENSCHLUSS - der Backtest ist also optimistischer als
  der laufende Betrieb, besonders auf langen Kerzen. Diese Abweichung gehoert in
  den Bericht, nicht in die Fussnote.
- **Spot ist Long-only.** Ein „mehr handeln" ueber die Short-Seite ist bei einem
  Spot-Lauf keine Parameterfrage, sondern eine andere Strategie (eigener Zweig).

## 2. Hebel wird nie geraten
- Ein Hebel ist eine ZAHL. „hoch", „aggressiv" und „so viel wie geht" sind keine
  Angaben, und eine fehlende Angabe wird nicht sinngemaess ergaenzt.
- Der Deckel wird GERECHNET, nicht gewaehlt: `hebel_deckel(mae) = min(20, 1 /
  (mae + Wartungsmarge))` aus dem groessten beobachteten Ruecklauf
  (`xperp/auswahl.py`) - Liquidation greift rund bei `1/Hebel` minus
  Wartungsmarge. Ein Vorschlag darf mit dieser Rechnung genannt werden; scharf
  wird er nur mit Max' Zahl.
- Ein Hebel vervielfacht NICHT die Trefferchance. Er vervielfacht Ergebnis UND
  Gebuehr relativ zum Einsatz. Die Frage „hoher Hebel fuer mehr Treffer" ist die
  falsche Frage; die richtige ist „welcher Satz je Seite" (siehe 3).

## 3. Die entscheidende Zahl ist die Gebuehr aufs NOMINAL
- Die Gebuehr faellt auf den NOMINALWERT an, nicht auf die Margin. Eine Runde
  mit `k` Prozent kostet bei Hebel `L` also `k * L` Prozent der Margin: bei 10x
  und 1,2 % je Runde sind das 12 % der Margin — mehr als die typische Bewegung
  einer 5-Minuten-Kerze.
- Kurze Intervalle und Hebel sind deshalb nur tragfaehig, wo der Satz je Seite
  klein ist. Gemessene Haus-Werte je Seite: Kraken-Spot 0,6 %,
  Kraken-Futures 0,04-0,05 %, OKX rund 0,05 %. Der Faktor zwischen Spot und
  Futures ist groesser als der Faktor zwischen 1x und 10x Hebel.
- Merksatz: **kurz + Hebel gehoert auf den Markt mit dem kleinen Satz, nicht auf
  Spot.** Eine Frage nach „mehr Runden und Hebel" ist zuerst eine Frage nach der
  Boerse.

## 4. Messen statt argumentieren
- Der Fremdlaeufer bringt seinen EIGENEN Backtester mit — den benutzen, nicht
  nachbauen (eine Nachbildung optimiert die Nachbildung).
- Muster `Agenten/Handel/omnitrade/intervalle_messen.py`: Kerzen holen
  (`historie_binance.von_binance`, oeffentlich, kein Schluessel), in das
  CSV-Format des Backtests schreiben (`timestamp_ms,open,high,low,close,volume`),
  dann das Binary je Kombination aus Takt x Gebuehrensatz aufrufen und Runden,
  Trefferquote, PnL und Drawdown als Tabelle ausgeben (Rohzahlen in `cache/`).
  Ergebnis: „oefter" ist eine Zahl, kein Versprechen.
- **Den Live-Modus nachstellen, nicht den bequemsten.** Ein Spot-Lauf braucht
  `OMNI_LONG_ONLY=1` (sell schliesst nur die Long-Position), sonst rechnet der
  Backtest Shorts mit, die live nie entstehen.
- **Die Datenquelle kann den kurzen Takt nicht kennen.** `historie_binance.TAKTE`
  fuehrt nur 1H/4H/1D — ein Aufruf mit `5m`/`15m` faellt mit `KeyError: '5m'` um.
  Vor der Messung kurzzeitiger Takte die Tabelle erweitern (`{"5M": "5m", ...}`)
  und die Gross-/Kleinschreibung der Aufrufstelle pruefen.
- **Die Groesse so wählen, dass das Konto die Gebühr trägt.** Bei kleiner
  Anfangsbilanz scheitern die Läufe am Gebührensatz (`InsufficientBalance`) —
  ein Kombinationsraster bekommt dann Löcher, die wie „kein Ergebnis“ gelesen
  werden. Vor dem Raster die größte Einzelposition (Nominal + Gebühr) gegen
  die Bilanz rechnen.
- **Der Drawdown eines fremden Backtesters wird geprüft, bevor er als Zahl
  zitiert wird.** Buchet der Account einen Kauf als VOLLEN Abzug vom Cash und
  zählt der Positionswert im Equity NICHT zurück, sieht jede offene Position
  die große Kurve — die DD-Spalte misst dann nichts (PnL, Runden und
  Trefferquote sind davon unberührt). Einen offenen Lauf gegen eine
  Zeilenrechnung halten, bevor aus dem DD eine Grenze abgeleitet wird.
- **Trailing erzeugt Runden, nicht Vorteile — das ist eine Messung, keine
  Regel.** Im gemessenen Fenster verdoppelte der Trailing-Stop die Rundenzahl
  (Ausstieg je Rücksetzer) und senkte den PnL; über die Trendlänge nachdenken,
  bevor ein Trailing-Skript zum Standard erklärt wird.
- **Reihenfolge der Laufzeit:** die Indikator-Auswertung ist quadratisch in der
  Kerzenzahl. Vor dem grossen Raster einen Einzellauf mit kurzem Fenster fahren
  und die Zeit messen; sonst laeuft ein 24-Kombinationen-Raster in die
  Werkzeuggrenze.
- **Das Binary waehlen wie der Starter es waehlt.** Bei mehreren Bauen
  (`target-live/release`, `target/release`, `target/debug`) entscheidet die
  Reihenfolge des Startskripts, nicht das Alter — ein aelterer Bau kennt
  neuere Sprachfunktionen nicht und liess Strategien mit `UndefinedFunction`
  durchfallen, die live funktionierten. Release statt Debug, wenn beide da
  sind: rund zehnmal schneller bei gleichem Code.
- **Skripte, die fuer einen beidseitigen Motor geschrieben sind, vergiften den
  Long-only-Modus.** Zwei `stop_loss`-Zeilen (unter dem Kurs fuer Long, ueber
  dem Kurs fuer Short) ueberschreiben sich: im Long-only-Backtest gewinnt die
  obere Zeile, der Stop liegt UEBER dem Einstieg und jede Position verlaesst
  sich sofort — die Zahlen sind Muell, ohne dass ein Fehler kommt. Vor der
  Messung eine Long-only-Fassung ohne die Short-Zeile bauen.

## 5. Neue Skriptfassungen ins Haus legen, nicht in den Klon
- Der Klon liegt unter `Werkstatt/` (Junction auf `O:`) und damit ausserhalb des
  Schreibbereichs: `write_file` verweigert mit `outside HERMES_WRITE_SAFE_ROOT`.
- Neue Strategie-Fassungen und Messwerkzeuge gehoeren nach
  `Agenten/Handel/<spur>/strategien/` bzw. `<spur>/`; der Fremd-Backtester
  akzeptiert einen ABSOLUTEN Pfad (`C:/...`) und laeuft mit `cwd` im Klon.
- Eine Variante erst validieren lassen, bevor das Raster laeuft (bei
  omnitrade: `omnitrade-cli validate --script <pfad>`), sonst ist der ganze Lauf
  eine Fehlermeldung mal N.

## 6. Statusdateien des Fremdlaeufers sparsam lesen
- Die Statusdatei traegt neben `state`, `pid`, `net_quantity`, `orders_placed`,
  `last_signal` auch `recent_candles` (hunderte Eintraege) und `recent_orders`.
  Nie komplett ausgeben — die Ausgabe sprengt den Kontext und verdeckt die
  eigentliche Antwort. Nur die Felder lesen, die die Frage tragen.
- `state: running` ist kein Lebensbeweis: nach einem harten Ende bleibt die Datei
  mit toter PID auf `running` stehen. Zwei Zeugen (Datei frisch UND PID lebt),
  sonst spiegelt die Haus-Spur einen toten Lauf.
- Die Altersgrenze waechst mit dem Kerzenabstand der Datei (sie wird nur beim
  Verarbeiten einer Kerze geschrieben) — bei 1h-Takt also stuendlich; eine feste
  5-Minuten-Grenze erklaert einen gesunden Lauf fuer tot.

## 7. Was der Laeufer NICHT kann, bleibt ein Befund
- Kein Orderweg im Fremdprogramm heisst: die Haus-Spur spiegelt seine Position und
  ordert ueber den erprobten Haus-Weg (`Agenten/Handel/omnitrade/` -> Kraken-Spot).
  Ein Hebel laesst sich auf diesem Weg nicht nachruesten (Spot), und einen
  Kraken-Adapter in Rust zu bauen hiesse: zweiter Schluessel, zweiter
  Nonce-Zaehler.
- Fuer Hebel die Wege nehmen, die ihn schon haben und den Stop an die Boerse
  legen (Kraken Futures, OKX XPERP) — nicht den Spot-Laeufer verbiegen.
- Am Ende in dieser Form berichten: was am Code belegbar ist (mit Fundstelle),
  welche Zahl die Entscheidung traegt (Gebuehr je Seite gegen Margin), was
  gemessen wurde und was noch eine Entscheidung von Max braucht (die Hebelnzahl).

## 8. Das Hebel-Bein als EIGENE Spur bauen, nicht als zweite Boerse in der Spot-Spur

Ein Buch fuehrt EINE Waehrung: Spot rechnet in USDC/EUR, Futures in USD. Zwei
Boersen in einem Buch waeren zwei Waehrungen in einer Rechnung — deshalb eine
eigene Spur mit demselben Signal (die Rechnung `quelle`/`signal`/`ausstieg`
per importlib ueber den PFAD aus der Spot-Spur laden, nicht abschreiben).

Der Futures-Orderweg ist ein neuer Boersenname in `spur_buch`:
- `orderweg()` bekommt einen Dict-Eintrag (`"kraken_futures":
  "<spur>/weg"`), und `venue_inst()` bekommt einen Zweig, der den
  Spur-Instrumentnamen in den KONTRAKTNAMEN uebersetzt (`PF_<Basis>USD`,
  nur BTC heisst dort XBT). BEIDES zusammen, mit einem Smoke-Aufruf belegt.
- **Der Kontraktnamen-Zweig muss VOR dem Bindestrich-Rueckfall stehen.**
  `if "-" in inst: return inst` kehrt fuer jeden gespiegelten Lauf sofort
  zurueck — die omnitrade-Laeufe liefern "SOL-USDC", ohne eigenen Zweig haette
  die Order einen Marktnamen bekommen, den es an der Boerse nicht gibt, und der
  Fehler waere erst im Live-Einstieg aufgefallen.
- **Ein fuzzy Patch an einer Funktion kann deren Schlusszeile still loeschen**
  (belegt: der `return "%s-%s"`-Abschluss von `venue_inst` verschwand, kein
  Fehler, nur `None` statt Paarname). Nach jedem Patch an einer Funktion das
  Modul importieren und die Funktion mit Vertretern ALLER Zweige aufrufen —
  `ast.parse` faengt eine fehlende return-Zeile nicht.
- Werte, die `spur_buch` den Orderfunktionen NICHT mitreicht (der Hebel),
  traegt der Adapter als Modulzustand mit einem Setter, den `handeln.py` vor
  dem Zyklus aus der wachen setzt — Vorgabe 1.0, damit ein vergessener Setter
  sichere haftet.
- `menge_fuer` liefert GANZE Kontrakte und rundet AB: ein Einsatz unter dem
  kleinsten Kontrakt bricht den Einstieg ab (`fehler` statt Menge) — eine
  gerundete AUF-Rundung wuerde eine Menge ordern, die das Konto nicht traegt.
  `max_pro_trade_usd` deshalb so setzen, dass genau die gewuenschte
  Kontraktzahl passt.
- **Der Hebel sitzt NICHT in der Order - `/sendorder`-`leverage` wird ignoriert.**
  Gemessen am echten Konto: mit, ohne und als Zahl geschickt, die Marginreserve
  blieb immer der 10 %-Plan. Der Hebel gehoert an den KONTRAKT:
  `PUT /leveragepreferences` mit `{symbol: PF_SOLUSD, maxLeverage: 7}` stellt
  isolated margin ein, danach reserviert 1 Kontrakt `nennwert / hebel` (belegt:
  11,79 -> 16,80 USD auf 117,33 Nominal). zwei Regeln dazu:
  - **PUT mit FORMKOEPRER senden.** Dieselbe Signatur als Query-String
    (`PUT /leveragepreferences?symbol=...`) antwortet `authenticationError`;
    dieselben Parameter als `application/x-www-form-urlencoded`-Body mit der
    Signatur ueber `postData + nonce + pfad` gehen durch. (`_roh(methode="PUT")`)
  - **Idempotent und nur im Live-Zweig setzen: zuerst GET, nur bei Abweichung
    PUT, Ruecklesen als Gegenprobe.** Muster: `weg.hebel_vorbereiten()` - ohne
    Ruecklesen prueft nichts, dass der Hebel steht, und Papier soll die Boerse
    nicht anfassen.
- **Der Beleg ist die MARGINRESERVE, nicht die Antwort:** Guthaben vor/nach der
  Order stellen, das Delta ist die Margin je Kontrakt - `nennwert/7` gegen
  `nennwert/10` unterscheidet man an einer Zahl.
- **`authenticationError` in einer Orderantwort beweist NICHT, dass die Order
  scheiterte.** Gemessen: Antwort mit authenticationError, hinter der die Order
  GEFUEHLT war (Guthaben fiel um die Margin, `/openpositions` zeigte die
  Position). Vor dem Neuer-Ordern nach einem geplatzten "Fehler" erst
  `/openpositions` und das Guthaben lesen, sonst sammelt man Dubletten.
  Gegenprobe: bei echtem Auth-Fail scheitert auch der LESER - lebt der Leser,
  ist die Fehlerzeile verdachtig.
- **Guthaben auf das Futures-Konto kommt von der SPOT-Seite, nicht von der
  Futures-Seite.** Die Futures-API `/transfer` lehnt `fromAccount: spot` ab,
  und der Spot-Weg braucht die Withdraw-Berechtigung am Spot-Schluessel
  (`WithdrawMethods` antwortet sonst `EGeneral:Permission denied`). Ohne die
  Berechtigung ist der Transfer Handarbeit im Portal - ein Kontofakt, kein
  Codebug. EUR/USDC sind als Flex-Collateral zugelassen.
- Papierspur bleibt Papier: der Live-Zweig haengt an derselben Sperrenkette,
  `mindest_guthaben` an der Margin des kleinsten Kontrakts plus Puffer — und
  das Guthaben wird GEMESSEN, nicht aus der Erinnerung behauptet (das
  Futures-Konto kann seit dem letzten Blick leer sein).
