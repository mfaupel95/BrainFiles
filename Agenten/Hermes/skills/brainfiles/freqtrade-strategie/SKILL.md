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

Die statistischen Regeln fuer die Bewertung (Walk-Forward, Zeithalbierung,
Nullinie, "eine Zahl, die das Modell gesehen hat, ist keine Messung") stehen in
`handel-spur-studie` — dieses Skill hier ist der Freqtrade-spezifische Werkzeug- und
Ablaufteil.
