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
`/freqtrade/user_data`). Der ganze freqtrade-Ordner ist GITIGNORED (Strategie,
Daten, `config.json`) — Strategiearbeit wird NICHT committet, und `config.json`
enthaelt Zugangsdaten (nie ausgeben). Der Bot ist Papier/Trockenlauf: echte
Schluessel werden nie in den Backtest gezogen.

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

Die statistischen Regeln fuer die Bewertung (Walk-Forward, Zeithalbierung,
Nullinie, "eine Zahl, die das Modell gesehen hat, ist keine Messung") stehen in
`handel-spur-studie` — dieses Skill hier ist der Freqtrade-spezifische Werkzeug- und
Ablaufteil.
