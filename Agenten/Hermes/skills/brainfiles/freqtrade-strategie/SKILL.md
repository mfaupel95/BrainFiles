---
name: freqtrade-strategie
category: brainfiles
description: "Use when eine Freqtrade-Strategie gebaut wird."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [freqtrade, backtest, hyperopt, docker, brainfiles]
    related_skills: [handel-spur-studie, handel-spuren]
---

# Freqtrade-Strategie bauen, backtesten, optimieren

## When to Use

- "freqtrade echte strategie", "Strategie fuer den Freqtrade-Bot", "backteste
die Strategie", "hyperopt" — jede Arbeit an einer Freqtrade-Strategie im
Docker-Stack.
- Nicht fuer die Haus-Spuren in `Agenten/Handel/` (dort `handel-spuren` /
`handel-spur-studie`); dieses Skill ist der Freqtrade-spezifische Werkzeugteil.

Der Freqtrade-Stack laeuft als Docker-Container `freqtrade` (stable), der die
Strategien aus `Agenten/Handel/freqtrade/user_data/strategies/` liest (Mount auf
`/freqtrade/user_data`). Der Ordner ist GEPERRT, aber **nicht mehr ganz**: die
HANDARBEIT ist ueber eine Datei-Freigabeliste in der `.gitignore` sichtbar und
gehoert committet — `user_data/strategies/*.py`, `user_data/bots/*.json`,
`bots.json`, `bots_starten.sh`. Sonst verliert ein Datentraegerfehler sie still,
und keine Sitzung merkt es. GESPERRT bleiben `user_data/config.json` (traegt die
Zugangsdaten der Weboberflaeche, nie ausgeben), `user_data/data/` (Kursreihen,
neu ladbar) und die `*.sqlite`. Die Bots laufen im Trockenlauf: echte Schluessel
werden nie in den Backtest gezogen.

Fuer den Betrieb MEHRERER Bots aus diesem einen Stack: `references/mehrere-bots.md`
(Aufsatz-Muster, Startbefehl, Messreihenfolge) und
`scripts/backtest_archiv_lesen.py` (Ergebnisarchiv gegen die gedruckte Tabelle
nachzaehlen).

## Ablauf

1. **Strategie schreiben** als eigene `.py` in `.../strategies/` mit
   `INTERFACE_VERSION = 3`, `timeframe`, `startup_candle_count` (langsame EMA +
   ATR-Reserve, sonst still "0 Bereiche"). Das mitgelieferte Sample
   (`sample_strategy.py`) unberuehrt lassen — es existiert sonst als
   `SampleStrategy.py` doppelt und gibt beim Laden eine `DUPLICATE NAME`-Warnung
   (vorbestehend, harmlos).
2. **Daten laden**: `docker exec freqtrade freqtrade download-data --userdir
   /freqtrade/user_data -p <PAARE> -t 1h --days 400` — `--timerange
   YYYYMMDD-` sturz ab; `--days N` ist der verlaessliche Weg fuer "letzte N
   Tage".
3. **Backtest**: `docker exec freqtrade freqtrade backtesting --userdir
   /freqtrade/user_data --strategy <Name> --timerange ... --timeframe 1h`.
   Ergebniszeile mit Unix-Utensilien filtern: `grep -E "<Name> │|Market change"`
   (die Tabelle nutzt Unicode-Rahmen, plain grep auf Fehlerbalken trifft nichts).
4. **Gegentest der Parameter — nie demselben Fenster glauben.** Hyperopt nur auf
   dem ERSTEN Halbjahr trainieren, die besten Parameter dann im UNGESEHENEN
   zweiten Halbjahr backtesten. Optimiert man ueber den vollen Zeitraum und
   backtestet denselben Zeitraum, rechnet man eine Nachschau — Ergebnis
   wertlos. Der H2-Gegentest entscheidet: verlor die optimierte Kombination
   gegen die Baseline, ist es Overfit, und das ist das Verdikt (kein
   weiteroptimieren).
5. **Bericht mit ehrlicher Lesart.** Beleg (Ueberschrift + Ergebniszeile),
   Baseline gegen optimiert gegenueberstellen, Marktbewegung daneben (eine
   Strategie, die den Markt um 27 Punkte schlaegt, aber absolut negativ bleibt,
   ist ein guter Filter, kein Gewinner). Eine Empfehlung, keine Optionsliste.
6. **Nicht angefasst auflisten**: Container, config.json, gitignored
   Strategie/Daten, laufende dry_run-Bots, fremde Sitzungs-Commits.

## Mehrere Bots aus EINEM Stack (Aufsatz-Muster)

Je Bot kommt ein **Aufsatz** in `user_data/bots/<name>.json` dazu, der NUR den
Unterschied traegt: `strategy`, `timeframe`, `max_open_trades`, `dry_run`,
`api_server.listen_port`, `exchange.pair_whitelist`. Alles andere (Exchange,
Schluessel, Risiko) kommt aus `user_data/config.json` — Freqtrade VERSCHMILZT
verschachtelte Dicts ueber mehrere `--config`-Dateien. Genau deshalb darf ein
Aufsatz keine Kopie der Basis sein: eine Kopie veraltet still und traegt die
Zugangsdaten ein zweites Mal.

Je Bot zwingend eigen:

- **eigene Datenbank** (`--db-url sqlite:////freqtrade/user_data/tradesv3-<name>.sqlite`),
  sonst schreiben alle Bots in dasselbe `tradesv3.sqlite` und die Buecher mischen.
- **eigener API-Port**, und der Port MUSS an ZWEI Stellen gleich sein: im Aufsatz
  (`api_server.listen_port`) UND in der Container-Portfreigabe.
- **`api_server.listen_ip_address: "0.0.0.0"`.** Im Container ist `127.0.0.1`
  dessen EIGENE Schleife; ein darauf gebundenes UI ist ueber die Portfreigabe
  nicht erreichbar (Symptom: Connection reset). Nach aussen absichern ueber die
  Freigabe `-p 127.0.0.1:<port>:<port>`, NICHT ueber die Bind-Adresse.

Reihenfolge, die sich bewaehrt: erst die Strategie backtesten (siehe Ablauf),
dann den Bot bauen — ein Bot auf einer ungemessenen Strategie laeuft blind.
Nachweis, dass er wirklich steht: er erscheint in `docker ps` UND
`curl http://127.0.0.1:<port>/api/v1/ping` antwortet. Der Modus in einem
Treiberlog (`<spur> (live) ok`) ist KEIN Orderbeleg, und ein laufender Container
ist kein Beweis fuer einen funktionierenden Orderweg.

## Fallen, die echte Zeit kosten

- **`load=True` ueberschreibt still die kodierten Defaults.** Die Hyperopt-Parameter
  (`IntParameter`/`DecimalParameter`) tragen ein `load=`-Flag. Bei `load=True`
  zieht JEDER Backtest die zuletzt gespeicherte Hyperopt-Datei (`.fthypt` unter
  `user_data/hyperopt_results/`) statt der kodierten JValues — zwei Strategien
  mit verschieden kodierten Defaults liefern dann BYTE-IDENTISCHE Ergebnisse,
  und man verliert Stunden auf der Spur "warum reagiert die Aenderung nicht".
  Fuer deterministische Laeufe: `load=False` in allen Parametern UND die
  `hyperopt_results/`-Dateien beiseite legen (`mv .../hyperopt_results
  .../hyperopt_results.bak-<tag>`), sonst laedt auch `--cache none` die alte
  Datei.
- **`buy_params`/`sell_params` als Klassenattribut uebersetzen `.value` NICHT.**
  Die Strategie liest `self.<param>.value` (den Default des `IntParameter`),
  nicht die Dictionaries. Eine Subklasse, die nur `buy_params`/
  `sell_params` setzt, rechnet faktisch mit den geerbten Defaults. Die
  Alternativ-Werte als DEFAULT der Parameterklasse setzen
  (`ema_fast = IntParameter(..., default=33, load=False)`), dann reagiert
  `.value` — und erst dann ist der Gegentest echt. Verifizieren mit
  `-vv` und `grep -E "Strategy Parameter"` (zeigt den tatsaechlich geladenen
  Wert; wenn zwei Laeufe denselben Wert nennen, laufen sie mit denselben
  Parametern).
- **`trailing_stop_positive_offset` MUSS groesser als
  `trailing_stop_positive` sein** — gleich grosse Werte wirft einen
  Config-Fehler beim Backtest-Start.
- **Ergebnis zwischenspeichern, bevor man weitermacht.** Ein noch so gutes
  Ergebnis ist erst dann ein Nachweis, wenn man es in diesem Lauf greifbar
  hat (`--export trades`, Ergebniszeile mitschneiden). Neue Strategien dazu
  genau eine Zeile.
- **Im Spot-Modus laedt `can_short = True` NICHT** — eine uebertragene Strategie
  laeuft still nur long, und die Short-Regeln kommen nie zum Einsatz. Wer das
  Ergebnis bewertet, muss das wissen, sonst erklaert er eine Zahl, die die halbe
  Strategie nie gesehen hat. Short braucht `trading_mode: futures` PLUS
  Futures-Daten (`BTC/USDT:USDT`-Form). Umgekehrt: die fehlende Short-Seite
  erklaert einen Verlust NICHT, wenn die Long-Seite in einem steigenden Markt
  verliert und die Gebuehrenlast dieselbe bliebe.
- **Bei hoher Frequenz ist die Gebuehr der eigentliche Gegner.** Traegt
  `config.json` keinen `fee`-Schluessel, rechnet Freqtrade mit dem
  Boersen-Standard (Binance 0,1 % je Seite). Vor jeder Bewertung die
  GEBUEHRENSUMME gegen das Ergebnis stellen: liegt sie in derselben
  Groessenordnung, ist der "Verlust" die Gebuehr, und kein Strategieparameter
  aendert das. Die Jahreslast in Prozent ist `Trades/Tag x 0,2`.
- **Die Kante VOR Gebuehr ist die Zahl, die ueber die Strategie entscheidet —
  nicht das Netto-Ergebnis.** Rechne `Kante = Ergebnis + Gebuehrsumme`
  (Gebuehr = 2 x fee x Umsatzvolumen) und stelle sie gegen die Gebuehr je
  Runde. Eine stabile positive Kante bei negativem Netto heisst: die Regel
  hat ein Signal, die Boerse kostet es auf — der Hebel ist die Gebuehr
  (Futures/Maker), nicht die Strategie. Eine Kante, die ueber Stops,
  Ausstiegslogik und Halbjahre konstant bleibt, ist real; eine, die mit dem
  Parameter wandert, ist Rauschen. Gemessen (BtcRegimeKurz, 14 Laeufe):
  Kante stabil +0,09 bis +0,14 % je Umsatz, Gebuehr 0,20 % je Runde ->
  Verhaeltnis 0,6:1 (Spot, sicherer Verlust); Futures 0,10 % je Runde ->
  1,2:1 (kein sicherer Verlust, aber auch kein lebender Profit).
  GEMESSEN am 05./07.10.2026 (BtcRegimeKurz, BTC 1h, gleiche Strategie):
  Spot (0,1 %/Seite) H1 −25,9 % / H2 −22,7 %; Futures (0,05 %/Seite,
  `trading_mode: futures`, gleiche Regeln) H1 +0,04 % / H2 −4,2 % — die
  Differenz von ~20–26 pp je Halbjahr ist exakt die Gebuehreneinsparung.
  Die Kante vor Gebuehr war in 12+4 Laeufen stabil +0,09 bis +0,14 % je
  Umsatz; Futures hebt das Verhaeltnis Kante:Gebuehr von 0,6:1 auf
  1,2:1 — aber auch dort bleibt ein Halbjahr negativ, die Kante ist real,
  nur zu duenn (kein lebender Profit, nur kein sicherer Verlust).
- **Futures-Backtest: Daten UND Config muessen beide auf `futures` stehen, und
  die Summary-Tabelle hat eine ANDERE Spaltenstruktur als Spot.** Daten laden
  mit `download-data ... --trading-mode futures` (sonst fehlt die Funding-Rate),
  Config mit `trading_mode: futures` + `margin_mode: isolated` (aus der
  Spot-Basis ableiten, `pair_whitelist` auf die `:USDT`-Form). Die
  `STRATEGY SUMMARY`-Zeile zeigt in Futures-Modus hinten einen Prozentwert, der
  NICHT das Gesamtergebnis ist (gemessen: +10,73 % gelesen, real +0,04 %) —
  die Wahrheit steht in den `EXIT REASON STATS` (Summe der Zeilen) bzw. der
  `Total profit`-Spalte. Vor jedem Urteil die Exit-Reasons aufsummieren, nicht
  die erste Zeile der Summary glauben.
- **Ein `Fatal exception` im Backtest ist nicht automatisch ein Strategiefehler.**
  Erst denselben Lauf wiederholen und den Zeitpunkt gegen den Zustand der
  Docker-Maschine halten — ein sterbender Daemon bricht mitten im Lauf ab.
  Laeuft er beim zweiten Mal durch, war es die Umgebung, und am Code wird NICHTS
  geaendert.
- **Eine zweifelhafte Zeile der Ergebnisse-Tabelle gegen das ARCHIV pruefen,
  nicht gegen die Tabelle.** Die gedruckte Zusammenfassung kann ein Paar doppelt
  zeigen (Filter-/Anzeigeartefakt); die Wahrheit steht in
  `user_data/backtest_results/*.zip` (JSON -> `strategy` -> `trades`, je Trade
  `pair`). `scripts/backtest_archiv_lesen.py` zaehlt das nach. Eine doppelte
  Zeile in der Anzeige ist kein Datenfehler — erst nachzaehlen, dann melden.
- **Ein Bot, dessen API vom Host nicht antwortet, ist nicht automatisch tot —
  erst IM Container pruefen, dann die Portweiterleitung verdaechtigen.**
  Symptom: `curl http://127.0.0.1:<port>/api/v1/ping` gibt nichts (HTTP 000),
  aber `docker ps` zeigt den Container up und das Log heartbeattet frisch.
  Diagnose in zwei Schritten: (1) `docker exec <bot> python -c "import
  urllib.request; print(urllib.request.urlopen('http://127.0.0.1:<port>/api/v1/ping',
  timeout=5).read())"` — antwortet es dort `pong`, ist der Bot gesund und das
  Problem ist die Weiterleitung, nicht der Prozess. (2) Gegenprobe mit einem
  NICHT-freqtrade-Container (z. B. n8n auf 5678): antwortet der, ist die
  Weiterleitung nicht global kaputt, sondern haengt nur fuer die frisch
  gestarteten freqtrade-Container. Heilweg: `docker restart <bot>` (dry_run-Bots
  uebernehmen ihre offenen Papierpositionen), danach `curl` erneut. Ein
  Neustart aller 20 Bots in einer Schleife kann einzelne Container ueber
  Commit-Druck verlieren (docker.exe: "Resource temporarily unavailable" /
  "out of memory allocating heap arena map") — danach die fehlenden Ports
  einzeln neu starten und alle 20 gegenpruefen. Gemessen 11.10.2026: 20/20
  Container up und gesund, 0/20 Ports vom Host erreichbar, n8n ok; nach
  Restart 20/20 `pong`.
- **Eine Config-Aenderung an einem laufenden Bot ueber die API verifizieren
  heisst: die AUFSATZ-Zugangsdaten nehmen, nicht die Basis.** Jeder Aufsatz
  (`config.<name>.json`) traegt EIGENE Web-UI-Zugangsdaten; die Basis-`config.json`
  gibt auf 8081-8083 401. Und `show_config` liefert `strategy` als NAMENS-STRING,
  nicht als Dict — `use_exit_signal`/`signal_ausstieg` stehen dort gar nicht.
  Der verlaessliche Beleg fuer einen geschalteten Schalter ist, den Container
  die Config-Datei lesen zu lassen
  (`docker exec <bot> python -c "import json; print(json.load(open('/freqtrade/user_data/config.<name>.json'))['moondev'])"`)
  und den Neustart-Zeitpunkt gegen die Aenderung zu halten. Ein Schalter, der
  in der Config steht, wirkt erst nach dem Neustart des Bots.
- **Ein Strategie-Schalter, der gemessen werden soll, gehoert in den
  `moondev`-Block der Config, nicht als Konstante in den Code.** Die Basis-Strategie
  liest `config.get("moondev").get("signal_ausstieg")` und setzt daraus
  `use_exit_signal` — so laeuft derselbe Code vorher/nachher, und der Default
  im Code bleibt True, damit ein fehlender Config-Eintrag die Regel nicht still
  umstellt. Die Aufsatz-Configs sind GITIGNORED (tragen Zugangsdaten); die
  ENTSCHEIDUNG gehoert deshalb als datierter Vermerk in die versionierte
  Strategie-Datei, sonst ist sie nach einem Datentraegerfehler weg.

## Einen laufenden Bot nach einem Schalter beobachten (Wache)

Nach einem Strategie-/Config-Schalter (z. B. `signal_ausstieg=false`) will man
sehen, ob er wirkt, ohne die Bots anzufassen. Die Freqtrade-REST-API liefert das:
`GET /api/v1/trades?limit=50` gibt je Trade `exit_reason`, `profit_abs`,
`profit_ratio`, `pair`, `trade_id`, `is_open`. Eine Wache pollt das, merkt sich
je Bot die hoechste `trade_id` in einer Merkdatei und meldet nur NEUE
geschlossene Trades mit ihrem Exit-Grund. So ist sofort sichtbar, ob ein
Schalter greift: enden neue Trades nicht mehr mit `exit_signal`, arbeitet er.

- **Merkdatei VOR dem ersten echten Lauf auf den aktuellen Stand initialisieren.**
  Startet die Wache mit `letzte_trade_id=0`, meldet der erste Lauf die GANZE
  Historie (hier 29 Trades) als "neu". Erst den aktuellen Maximalstand je Bot
  in die Merkdatei schreiben, dann laeuft der erste Cron-Lauf leer und meldet
  nur, was ab jetzt passiert.
- **Zugangsdaten aus dem AUFSATZ, nicht aus der Basis** — jeder Bot traegt
  eigene Web-UI-Zugangsdaten in `config.<name>.json` (siehe API-Falle oben).
- **Watchdog-Muster**: leere Ausgabe = nichts senden; der Cron laeuft `no_agent`
  mit dem Skript als einziger Meldung. Der Job-Eintrag in `cron/jobs.json` ist
  Laufzeitstand (ignoriert) — nur das Wache-Skript wird committet.

Die statistischen Regeln fuer die Bewertung (Walk-Forward, Zeithalbierung,
Nullinie, "eine Zahl, die das Modell gesehen hat, ist keine Messung") stehen in
`handel-spur-studie` — dieses Skill hier ist der Freqtrade-spezifische Werkzeug- und
Ablaufteil.
