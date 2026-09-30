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
- **Reihenfolge der Laufzeit:** die Indikator-Auswertung ist quadratisch in der
  Kerzenzahl. Vor dem grossen Raster einen Einzellauf mit kurzem Fenster fahren
  und die Zeit messen; sonst laeuft ein 24-Kombinationen-Raster in die
  Werkzeuggrenze.

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
