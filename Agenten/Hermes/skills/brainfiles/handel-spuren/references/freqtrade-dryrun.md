# Freqtrade-Bots: eine fremde Engine als Papierflotte

Wann: Die Frage kommt als „was koennen die Bots, wie erreiche ich die, wie
schnell sind die" — oder wenn eine Portierungsarbeit ansteht („die
Trading-Agenten als Bots nachbauen"). Muster im Haus:
`Agenten/Handel/freqtrade/` mit `bots.json` (die Zuordnung ist die Wahrheit),
`bots.py` (lesender Zugang), `bots_starten.sh` (Start), `user_data/strategies/`
(die Strategien), `logs/` (alle Backtest-Luefe) und
`Agenten/Handel/freqtrade_bridge.py` (Bruecke in die Handelszentrale).

## Zuerst die Form bestimmen, dann urteilen

Ein Freqtrade-Bot ist KEINE `spur_buch`-Spur und gehoert nicht in `dauerlauf`.
Er hat seinen eigenen Takt, sein eigenes Buch (eine SQLite je Bot), seine
eigene Gebuehren- und ROI-Logik und seinen eigenen Risk-Stack. Die House-Regeln
(Freigabe, Spiegelung, Ratsche) greifen dort nicht. Also zwei getrennte Fragen
stellen:

1. **Was kann die Engine?** Alles, was aus OHLCV folgt — plus im Futures-Modus
   Funding und Mark-Preis. Portierbar ist genau das; alles andere braucht eine
   Fremdquelle, die im Haus archiviert sein muss (Zwangsschluesse zum Beispiel
   sind fuer den Ruecklauf verloren, wenn sie nicht gespeichert wurden).
   Nicht portierbar ist alles, was die Engine nicht sieht — die Absage MIT
   Grund gehoert in dieselbe Datei wie die portierbaren Boten, sonst sucht
   das naechste Mal jemand den fehlenden Agenten.
2. **Was taugt die Regel?** Nie aus dem Papierlauf. Der Verlust ist meist die
   Gebuehren, und das sieht im Lauf wie ein Signalfehler aus.

## Der Todesbeweis: Rendite je Runde gegen Round-Trip-Kosten

Das ist die eine Rechnung, die eine Freqtrade-Messung entscheidet:

    avg_profit_pro_trade  vs  2 * gebuehr_je_seite

Liegt der Schnitt **unter** den Round-Trip-Kosten, ist der Verlust die Gebuehr
und nicht die Regel — eine Parameteroptimierung aendert daran nichts. In den
Backtest-Reports steht der Schnitt in der TOTAL-Zeile (`Avg Profit %`), die
Laufzeit im Log (erste bis letzte Zeile, je Datei in `logs/`). Bei 1h-Kerzen,
Signal-Exit und hoher Frequenz ist das der Normalfall: Haltedauer wenige Stunden
gegen zwei Gebuehren je Runde.

Wer das nur am Backtest-Loss sieht, haelt es fuer ein Parameterproblem. Der
Beleg ist der Vergleich beider Zahlen — und die Aussage lautet dann „Struktur",
nicht „schlecht parametriert". Die Antwort auf eine Backtestfrage gehoert also
mit dieser Rechnung und nicht mit einem gerundeten Prozentsatz.

## Long und Short: jede Seite EIGEN messen, bevor eine Short-Fassung gebaut wird

Die Anfrage lautet fast immer „long und short abwechselnd nach Indikatoren".
Die Antwort ist selten die gebaute Variante, sondern eine Messung, und sie geht
ueberraschend oft gegen die Erwartung:

    long   -20,68 %   Sharpe -0,35   Profit-Faktor 0,83
    short  -34,50 %   Sharpe -0,52   Profit-Faktor 0,76
    beide  -48,13 %   Sharpe -0,95   Profit-Faktor 0,77

Drei Laeufe derselben Strategie, nur die Seite unterscheidet sich, Futures-Modus
mit Funding-Rate. Zwei Regeln daraus:

1. **Die kurze Seite traegt nicht automatisch, und die Kombination ist nicht die
   Summe der beiden.** Gemessen verliert die kurze Seite MEHR als die lange, und
   long+short verliert mehr als jede Seite einzeln. Wer nur die lange Seite
   kennt, schliesst daraus „die kurze Seite holt das Defizit rein" — das ist
   unbelegt. Also: **erst `long`, `short` und `beide` getrennt fahren**, dann
   bauen. Das kostet zwei Backtests und spart eine falsche Strategie.
2. **Eine Short-Regel wird nicht erfunden.** Von drei portierten Agenten hatte
   genau einer eine dokumentierte Short-Seite (aus dem Fremd-Agenten
   uebernommen); bei den beiden anderen gab es nichts zu uebertragen. Eine
   selbst gebaute Gegenseite ist eine NEUE Strategie und traegt nicht den Namen
   der portierten — das gehoert in den Bericht, nicht in die Klasse. Die
   Futures-Strategie bleibt long-only und sagt das auch.

Der Umstieg auf Futures selbst ist eine andere Frage und oft die einzige, die
etwas bringt: er senkt die Kosten (gemessen 0,05 % statt 0,60 % je Seite), er
erzeugt aber keine Kante. Beide Fragen getrennt beantworten und beide mit der
Trefferquote UND dem Ergebnis nennen — eine Trefferquote von 28,6 % auf beiden
Seiten bei einem Unterschied von 27 Prozentpunkten im Ergebnis ist das ganze
Argument.

## Zugang und Erreichbarkeit (gemessen)

- **Container, nicht Prozesse.** Ein Bot = ein Container
  (`freqtrade-<name>`), je mit eigenem Volume auf `user_data/`, eigenem
  `--db-url` (`tradesv3-<name>.sqlite`) und einem Port **auf 127.0.0.1**. Nach
  aussen nur ueber die Portweiterleitung; im Container muss
  `listen_ip_address` auf `0.0.0.0` stehen, sonst laeuft die Weiterleitung in
  die eigene Schleife (im Container ist 127.0.0.1 das eigene Loopback).
- **Ein Start fuer die Flotte**, nicht drei Handstarts: ein Skript mit
  `docker rm -f` + `docker run --restart unless-stopped` je Bot, danach Wartezeit
  und ein Log-Schnippsel je Bot. Ein Neustart ist damit reproduzierbar.
- **Config-Mischung:** Basis-`config.json` plus je Bot eine Aufsatz-Datei
  (`config.<name>.json`). Alles Drueberliegende kommt aus der Basis (Exchange,
  Keys, Risiko), aus dem Aufsatz nur was die Strategie bestimmt (Zeitrahmen,
  Strategie, Paarliste, `max_open_trades`, API-Port, `bot_name`). Aufsatz-Dateien
  werden zur Laufzeit erzeugt — sie sind ein Ergebnis, keine Quelle.
- **Zugangsdaten:** je Bot ein eigenes `api_server`-Paar; die Container
  akzeptieren ihr eigenes Aufsatz-Passwort und lehnen das Basis-Passwort ab.
  Eine Bruecke nimmt den PORT vom Bot und die ANMELDUNG aus seinem Aufsatz
  (mit Basis-Rueckfall fuer Alt-Container). Passwoerter nie in eine Ausgabe,
  nie in ein Log, nie in eine Meldung — sie stehen in der Aufsatz-Datei.
- **Zwei Zugaenge, die man verwechselt:** die REST-API (`/api/v1/...`,
  lesend) und die Web-UI auf demselben Port. Beide brauchen die Anmeldung. Der
  Reiter in der Handelszentrale geht ueber die Bruecke, nicht ueber die UI.

## Zwei Fallen, die beide schon Geld gekostet haben

- **`can_short` im Spot-Modus wird nicht geladen.** Die Strategie setzt es,
  die Engine ignoriert es — die kurze Seite der portierten Regeln kommt nie zum
  Einsatz, ohne dass irgendwo ein Fehler steht. Im Spot-Modus ist die Regel
  long-only und behauptet es nicht anders; die Futures-Fassung ist eine eigene
  Strategieklasse (`can_short = True`), nicht ein Schalter in der alten.
- **`minimal_roi` und `stoploss` sind KLASSENATTRIBUTE.** Wer sie in
  `__init__` ueberschreibt, muss das nach `super().__init__()` tun — sonst
  liest die Engine den alten Wert. Die Geometrie (Ziel als R-Vielfaches des
  Stops) gehoert als Zahl an die Basis der Strategie, nicht in jeden Aufruf.

## Was man beim Messen trennt

Die Backtest-Dateien in `logs/` sind nach **Regelvariante** benannt
(`bt-<was-geaendert-wurde>-<bot>.txt`), nicht nur nach Bot. Das ist der
teuerste Teil des Bestands und der Grund, warum `logs/` nicht versioniert
wird. Beim Vergleich zweier Laeufe gilt: **die Ausstiegsregel gehoert neben die
Trefferquote** — eine Aenderung an Stop, Ziel, Frist, Trailing oder am
Zeitrahmen macht die alte Zahl ungueltig; neu messen, nicht zitieren.

Der Paper-Lauf gegen den Backtest ist die zweite Achse: der Backtest ist der
Vergleich mit dem Markt, der Lauf die Kontrolle, ob die Engine das im
Tagesbetrieb ueberhaupt macht (0 Trades ueber Tage ist eine kaputte Anbindung,
kein neutrales Signal). Beide Achsen getrennt nennen — sie messen
Verschiedenes, und eine schlechte Zahl in der einen entlastet die andere nicht.

## Nachweis fuer eine Portierung

Je Bot: (1) eine Regel, die ohne Sprachmodell nachrechenbar ist — der Grund
steht als Kandidatengeschichte in `bots.json`; (2) die Basis-Geometrie aus den
HAUS-Zahlen der entsprechenden Feed-Spur (`stop_prozent`, `ziel_r_vielfaches`),
nicht aus dem Fremd-Repo — das Bot-Repo liefert keine, und eine geratene
Geometrie sieht spaeter wie eine gemessene aus; (3) ein Backtest ueber ein
Fenster, das einen Vollstaendigkeitssprung und ein ruhiges Fenster abdeckt;
(4) ein laufender Dry-Run mit gelesenen Trades ueber die Bruecke.