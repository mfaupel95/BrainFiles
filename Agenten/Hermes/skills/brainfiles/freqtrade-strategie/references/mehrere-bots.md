# Mehrere Freqtrade-Bots aus einem Stack

Die REGELN stehen im SKILL.md (`## Mehrere Bots aus EINEM Stack`). Hier stehen die
konkreten Befehle und die Reihenfolge, in der gemessen wird. Alle docker-Aufrufe
mit `MSYS_NO_PATHCONV=1`, sonst zerschneidet MSYS die Container-Pfade.

## 1. Aufsatz anlegen (`user_data/bots/<name>.json`)

Nur den Unterschied eintragen. Bewaehrtes Minimum:

```json
{
  "strategy": "<Strategieklasse>",
  "timeframe": "1h",
  "max_open_trades": 3,
  "dry_run": true,
  "api_server": { "listen_ip_address": "0.0.0.0", "listen_port": 8081 },
  "exchange": { "pair_whitelist": ["BTC/USDT", "ETH/USDT"] }
}
```

`list-strategies` ueber BEIDE `--config`-Dateien zeigt, ob der Aufsatz sauber
verschmilzt und die Strategie geladen wird — das ist die billigste Gegenprobe
gegen einen Tippfehler im Dateinamen.

## 2. Backtest ueber Aufsatz + Basis

```bash
MSYS_NO_PATHCONV=1 docker exec freqtrade freqtrade backtesting \
  --config /freqtrade/user_data/config.json \
  --config /freqtrade/user_data/bots/<name>.json \
  --userdir /freqtrade/user_data \
  --timerange 20240929-20260929 --strategy <Strategieklasse> --cache none
```

`--cache none` ist Pflicht: ein gecachtes Ergebnis zeigt nach einer
Strategieaenderung weiter die alten Zahlen.

## 3. Bot starten

```bash
MSYS_NO_PATHCONV=1 docker run -d --name freqtrade-<name> --restart unless-stopped \
  -p 127.0.0.1:8081:8081 -v <absoluter-pfad>/user_data:/freqtrade/user_data freqtrade \
  freqtrade trade --config /freqtrade/user_data/config.json \
  --config /freqtrade/user_data/bots/<name>.json \
  --db-url sqlite:////freqtrade/user_data/tradesv3-<name>.sqlite
```

Das Ganze als Skript (`bots_starten.sh`) festhalten: es ist die EINZIGE Stelle, an
der Port, Datenbankname und Aufsatz zusammenpassen. Nach dem Start pruefen:
`docker ps` und `curl http://127.0.0.1:<port>/api/v1/ping`.

## 6. „Die Bots sind weg" — erst die ENGINE pruefen, nicht den Stack

Symptom: alle Web-Oberflaechen leer, `curl http://127.0.0.1:8081/api/v1/ping`
antwortet nicht mehr (HTTP `000`), waehrend die Konfiguration unveraendert
aussieht. Die Ursache liegt eine Schicht tiefer:

```bash
wsl -l -v                      # ist die Distro docker-desktop STOPPED?
timeout 30 docker ps           # antwortet der Daemon ueberhaupt?
```

Laeuft `com.docker.backend` als Prozess, die Distro aber auf `Stopped`, hostet
KEIN Container — Docker Desktop ist gestartet, seine Linux-VM nicht. Reihenfolge:
Docker Desktop beenden und neu starten (`Stop-Process` auf
`Docker Desktop`/`com.docker.backend`/`com.docker.build`/`com.docker.sailor`,
dann die EXE starten), danach in einer Schleife auf die Engine warten
(`docker info` bis Erfolg, grosszuegig) — nicht auf einen festen `sleep`.

**Die Container kommen von selbst zurueck.** Mit `--restart unless-stopped`
startet der Daemon sie beim Hochfahren neu; gemessen waren alle drei Bots nach
wenigen Sekunden `Up`, samt der offenen Position aus der Datenbank ("Found open
trade: NEAR/USDT"). `bots_starten.sh` ist dann NICHT noetig — es macht
`docker rm -f` + `docker run` und wuerde nur neu anlegen. Erst starten, wenn die
Container wirklich fehlen.

Nach dem Hochfahren braucht Freqtrade ein bis zwei Minuten, bis die Ports
antworten (die Weiterleitung steht nicht sofort) — zu frueh gemessen sieht wie
ein Startfehler aus. Beleg in dieser Reihenfolge: `docker ps` (Up), dann `ping`,
dann `docker logs --tail` (Zeile `state='RUNNING'`).

## 7. Der API-Zugang kommt aus der BASIS-config, nicht aus dem Aufsatz

`bots.py status` (und jedes eigene Statuswerkzeug) liest den Zugang meist aus
der Datei, die es gerade in der Hand hat — dem Aufsatz
`user_data/config.<name>.json`. Der traegt zwar ebenfalls `api_server.username`
und `password`, aber mit ANDEREN Werten als die laufenden Container akzeptieren:
`ping` antwortet (unauthentifiziert), `count`/`profit` liefern dagegen
`HTTPError` — die Zeile liest sich dann `erreichbar, count=HTTPError`.

Gemessen an einem Port mit beiden Saetzen: das Basis-Passwort liefert fuer
`ping`/`count`/`profit`/`status` je 200, das Aufsatz-Passwort 401.

- **Zugang aus `user_data/config.json` nehmen, vom Aufsatz nur den Port**
  (`listen_port`).
- **Pruefen, welcher Satz wirklich passt — nicht raten:** dieselben Endpunkte
  einmal mit dem Basis- und einmal mit dem Aufsatz-Zugang abfragen und die
  Statuscodes vergleichen. Umlaute/Passwoerter nie ausgeben, nur vergleichen
  (Laenge, Hash).
- **Der Zugang gehoert nicht in den Aufsatz.** Ein Aufsatz, der Zugangsdaten
  kopiert, veraltet still und traegt sie ein zweites Mal — genau die Trennung,
  die `references/mehrere-bots.md` oben beschreibt. Wer ein Statuswerkzeug
  baut, liest den Zugang an EINER Stelle.

## 8. Messreihenfolge VOR dem ersten Bot

Ein Bot auf einer ungemessenen Strategie laeuft blind. Reihenfolge:

1. **Daten vollstaendig und gleich lang.** Je Paar pruefen, dass alle Paare
dasselbe Fenster tragen — ein kurzes Paar verfaelscht den Vergleich.
2. **Zwei Jahre am Stueck** — die Gesamtzahl.
3. **Dieselbe Strategie in zwei Haelften** (H1/H2 getrennt). Erst die Halbierung
 zeigt, ob ein Ergebnis an einem Regime haengt; eine Zahl ueber alles verdeckt es.
4. **Gebuehrensumme gegen Ergebnis.** Liegt sie in derselben Groessenordnung, ist
der Verlust die Gebuehr.
5. **Trades/Tag ausrechnen** (`Trades / Tage`). Das ist die Kostenmaschine; die
Jahreslast in Prozent ist `Trades/Tag x 0,2` je Seite.
6. **Verteilung je Paar ansehen** (dieselbe Rechnung wie die Zaehlung im
Archivskript). Sitzt der Verlust in einem Drittel der Paarliste, ist die
Paarauswahl ein billigerer Hebel als jeder Parameter.

## 5. Portierungslandkarte (`bots.json`)

Wenn Agenten/Strategien aus einem Fremd-Repo uebertragen werden, traegt die
Landkarte je Eintrag: Name, Strategieklasse, Port, Zeitrahmen, Paarliste — und
bei den NICHT uebertragenen einen GRUND.

- **Jeder Absagegrund muss nachpruefbar sein und gegen die eigene Datenlage
  geprueft werden.** "Keine Historie vorhanden" ist ein Grund, der veraltet,
  sobald das Haus die Reihe selbst erhebt; dann steht dort eine Absage, die
  niemand mehr begruenden kann. Vor dem Weiterarbeiten die Gruende gegen die
  heute verfuegbaren Quellen halten.
- **Bei Grenzen des Zielsystems den SYSTEMgrund nennen, nicht den Datenmangel.**
  Ein Spot-Backtest sieht keine Funding-Rate — das ist ein Datenmodell-Punkt und
  bleibt wahr, auch wenn die Reihe vorliegt.
