---
id: 20260930-freqtrade-bots
title: 'Freqtrade-Bots aus den Moon-Dev-Agenten'
tags: [handel, freqtrade, bots, backtest]
created: 2026-09-30
updated: 2026-10-01
related: ['[[Handel/Spuren-Uebersicht]]', '[[Handel/Backtest-Fundament]]', '[[Handel/Kosten-und-Bedingungen]]', '[[Betrieb/Docker-und-Sandbox]]', '[[Betrieb/Systemleistung-2026-09-29]]']
summary: 'Wie die drei Moon-Dev-Agenten als Freqtrade-Bots laufen, was die Backtests ueber sie sagen (alle negativ, die Gebuehr IST der Verlust) und was die Frequenzbremse (T-197) und die kurze Seite (T-198) messbar geaendert haben: die Rundenzahl, nicht das Ergebnis je Runde.'
---

# Freqtrade-Bots aus den Moon-Dev-Agenten

Die alte Aufgabe: die Agenten aus `Werkstatt/Repos/moon-dev-ai-agents` nach
Freqtrade uebertragen. Die Uebertragungsliste liegt in
`Agenten/Handel/freqtrade/bots.json` — **3 portiert, 11 nicht portierbar**,
dazu die Eintraege unter `als_schutzschicht_portiert` (das
`risk_agent`-Verhalten steckt jetzt als Freqtrade-Schutzschicht in allen Bots).

## Was laeuft

| Bot | Container | Port | Strategie | Paare | Plaetze |
|---|---|---|---|---|---|
| Trading Agent | `freqtrade-trading-agent` | 8081 | `MoonDevTradingAgent` | 12 | 4 |
| Top Movers | `freqtrade-topmovers` | 8082 | `MoonDevTopMovers` | 24 | 3 |
| Marktlage/Regime | `freqtrade-marktlage-regime` | 8083 | `MoonDevMarketRegime` | 1 | 1 |
| (Vorgaenger) | `freqtrade` | 8080 | `SampleStrategy` | — | — |

Alle drei: `dry_run: true`, Zeitrahmen 1h, je eine **eigene Datenbank**
(`user_data/tradesv3-<bot>.sqlite`). Ohne eigene Datei schreiben alle drei in
dieselbe `tradesv3.sqlite` und die Buecher sind nicht mehr zu trennen —
`--db-url` ist kein Beiwerk, sondern die Trennung.

Start: `bash Agenten/Handel/freqtrade/bots_starten.sh` (legt die Container neu
an, `--restart unless-stopped`; nach einem Docker-Neustart kommen sie von
selbst wieder).

## Die Aufsaetze (Overlays)

Jeder Bot hat in `user_data/bots/<name>.json` nur seinen **Aufsatz**:
Strategie, Zeitrahmen, Plaetze, `dry_run`, API-Port, Paarliste. Zugangsdaten,
Boerse und Risiko bleiben in `user_data/config.json`. Freqtrade mischt mehrere
`--config` tief ineinander, deshalb sind es zwei Dateien statt einer Kopie —
so liegen die Zugangsdaten der Weboberflaeche genau einmal auf der Platte.

**Falle (gemessen 30.09.2026):** der Aufsatz setzte zuerst
`api_server.listen_ip_address = 127.0.0.1`. Das ist IM Container der eigene
Loopback — die Weboberflaeche war von aussen nicht erreichbar, alle drei Bots
antworteten mit `ConnectionReset`. Richtig ist `0.0.0.0` im Container; die
Absicherung nach aussen macht das Port-Mapping `-p 127.0.0.1:<port>:<port>`.
Eine Bindung an den Loopback ist kein Schutz, sondern ein Defekt.

## Was der Backtest sagt — und zwar zum ersten Mal

Die drei Strategien waren **nie gemessen** worden. Am 29.09.2026 wurden dafuer
24 Paare auf 1h ueber zwei Jahre geladen (2024-09-29 → 2026-09-29, gleiche
Laenge bei allen Paaren), dann gerechnet:

| Strategie | 2 Jahre | H1 (2024-10…2025-09) | H2 (2025-09…2026-09) |
|---|---|---|---|
| `MoonDevTradingAgent` | **−66 %** (Treffer 25 %, max. Rueckgang 83 %) | −62,9 % (1543 Trades) | −55,5 % (1418 Trades) |
| `MoonDevTopMovers` | negativ | −18,3 % (608) | −33,9 % (316) |
| `MoonDevMarketRegime` | negativ | −25,5 % (113) | −15,9 % (98) |

**Kein einziges Fenster positiv.** Und der Grund ist nicht die Richtung,
sondern die Frequenz: `MoonDevTradingAgent` macht 3,23 Trades pro Tag. In der
Config steht kein `fee`, also rechnet Freqtrade mit der Boersengebuehr
(Binance 0,1 % je Seite = 0,2 % je Runde). Bei 3,23 Runden/Tag sind das über
**240 % Kosten im Jahr** — mehr, als jede Strategie erwirtschaften kann. Der
Beleg steht im Backtest selbst: Gebuehren 8.399 USDT gegen ein Ergebnis von
−8.335 USDT. **Der Verlust IST die Gebuehr.**

## Warum sie trotzdem laufen

Die Bots laufen im Probebetrieb, weil die Messung zwar die Strategie
verurteilt, aber der Auftrag war, die Uebertragung nach Freqtrade
nachvollziehbar zu machen — und weil ein laufender Papierbot die Frage
„warum verliert der?" jeden Tag neu und mit echten Kursen beantwortet.
**Scharf gestellt wird hier nichts:** `dry_run: true`, kein Orderweg, kein
Guthaben, keine Freigabe. Ein Live-Betrieb dieser drei waere nach dieser
Messung nicht zu verantworten.

Der naheliegende naechste Schritt war nicht ein Parameter, sondern die
**Frequenz**: die Vorfilter der Feed-Spuren (`Handel/risikovorfilter.py`) und
die Sperrfrist nach Ziel-Ausstieg (`handeln.in_zielsperre`) existierten im Haus
schon — sie fehlten nur in der Freqtrade-Uebertragung. Was daraus geworden ist,
steht im naechsten Abschnitt: gebaut, gemessen, und **nicht** eingeschaltet.

## Die Frequenzbremse — gebaut, gemessen, aus (T-197, 01.10.2026)

Die Bremse liegt in `user_data/strategies/frequenzbremse.py` (reine Rechnung,
keine Freqtrade-Importe) und wird von `moondev_basis.confirm_trade_entry`
gerufen. Vier Regeln, jede mit ihrer Herkunft:

| Regel | Zahl | Herkunft |
|---|---|---|
| Sperrfrist nach Ziel-Ausstieg | 2 h | `scanner/wachen.json` (Auftrag Max 23.09.2026) |
| Abklingzeit nach Stop | 96 h (4 Tage) | `scanner/wachen.json` `abklingzeit_tage 4` |
| Fenster-Vorfilter (Verlust/Gewinn) | 12 h, 5 % | `risk_agent` (MAX_LOSS/GAIN 12 h, 5 %) |
| Mindestabstand zwischen Einstiegen | Suchpunkt (6/24/48 h) | **nicht** aus dem Haus — gemessen |

Die USD-Grenzen des `risk_agent` (25/25) sind bewusst **aus**: sie haengen an
einem kleinen Konto, waehrend der Backtest mit 10.000 USDT und ~3.300 USDT je
Platz rechnet — 25 USD waeren dort 0,76 % des Einsatzes und wuerden jeden Handel
sofort ersticken. Uebertragen wurde die **prozentuale** Fassung, weil sie
skalenfrei ist.

**Der Vergleichslauf (2 Jahre, 12 bzw. 24 USDT-Paare, 1h, Gebuehr 0,10 % je
Seite), Bot `MoonDevTradingAgent`:**

| Lauf | Trades | /Tag | Ergebnis | je Runde |
|---|---|---|---|---|
| ohne Bremse | 2954 | 4,06 | −83,35 % | −0,17 % |
| nur Ziel-Sperrfrist 2 h | 2951 | 4,06 | −83,41 % | −0,17 % |
| nur Abklingzeit nach Stop 96 h | 2922 | 4,02 | −82,36 % | −0,16 % |
| nur Fenster-Vorfilter | 2869 | 3,95 | −82,86 % | −0,17 % |
| **volle Bremse** | 2877 | 3,96 | −82,62 % | −0,17 % |
| nur Mindestabstand 6 h | 2712 | 3,73 | −79,18 % | −0,16 % |
| nur Mindestabstand 24 h | 2328 | 3,20 | −79,48 % | −0,19 % |
| nur Mindestabstand 48 h | 1942 | 2,67 | −68,18 % | −0,16 % |

Die entscheidende Spalte ist die letzte: **das Ergebnis je Runde bewegt sich
nicht** (−0,16 bis −0,21 % in jeder der neun Einstellungen). Die Bremse senkt die
Zahl der Runden — bis zu 34 % beim 48-h-Abstand —, aber sie kann keine Regel
tragfaehig machen, die je Runde weniger verdient als die Gebuehr kostet. Sie
verkleinert nur den Schaden. Bei den beiden anderen Bots wurde es mit Bremse
sogar **schlechter**: `MoonDevTopMovers` −46,0 → −55,4 %, `MoonDevMarketRegime`
−37,2 → −39,2 % (die gesperrten Einstiege waren also nicht die schlechten).

Deshalb ist `bremse` **standardmaessig aus** — dieselbe Haltung wie beim
Haus-Vorfilter (`risikovorfilter.STANDARD["risikovorfilter"] = False`): eine
stillschweigend drosselnde Neuerung waere schlimmer als keine. Wer sie will,
setzt `moondev.bremse: true` in seiner Bot-Konfiguration; die Aufsaetze fuer
jede Variante liegen in `user_data/messung/`.

**Nebenbei gemessen, und wichtiger als die Bremse:** die Frequenz kommt aus dem
**Signal-Ausstieg**, nicht aus dem Einstieg. Mit `signal_ausstieg: false` fallen
die Runden von 2954 auf 389 (−87 %) und das Ergebnis von −83,35 % auf −25,99 %.
Positiv ist auch das nicht — aber wer an der Frequenz drehen will, muss dort
ansetzen, nicht bei einer Einstiegssperre.

## Die kurze Seite — gebaut, gemessen, nicht besser (T-198, 01.10.2026)

`can_short = True` laedt im Spot-Modus nicht (`strategy_resolver.py`);
Futures-Daten und `trading_mode: futures` sind noetig. Von den drei Agenten hat
genau EINER eine belegte Short-Regel — `coingecko_agent` bzw.
`moondev_marktlage/wachen.json`: short bei BTC −2 % und hoechstens 40 % der
Messlatte im Plus. Fuer `trading_agent` und `new_or_top_agent` gibt es keine,
und dort wurde auch keine erfunden.

`MoonDevMarketRegimeFutures` faehrt dieselbe Strategie mit kurzer Seite; der
Schalter `moondev.seite` (long/short/beide) macht die drei Laeufe vergleichbar.
Zwei Jahre, zwoelf Paare als `BTC/USDT:USDT` usw., 1h, Gebuehr 0,05 % je Seite
(Futures-Satz):

| Seite | Trades | Ergebnis | je Runde |
|---|---|---|---|
| nur lang | 210 | −20,68 % | −0,10 % |
| nur kurz | 215 | −34,50 % | −0,17 % |
| beide | 425 | −48,13 % | −0,13 % |

**Die kurze Seite erklaert den Verlust nicht** — sie verdoppelt die Zahl der
gebuehrenzahlenden Runden und macht das Ergebnis schlechter als die lange Seite
allein. Und die Zahl, die daneben auffaellt: derselbe Bot, dieselbe lange Seite,
dieselben 210 Runden — im **Spot** −37,24 %, im **Futures** −20,68 %. Der
Unterschied ist der Gebuehrensatz (0,10 % gegen 0,05 % je Seite) abzueglich der
Funding-Kosten. Der groesste gemessene Hebel an diesen Bots ist damit der
**Kostensatz**, nicht die Regel.

Beleg, dass die Funding-Rate wirklich mitgerechnet wird: `download-data
--trading-mode futures` legt je Paar drei Reihen ab (OHLCV, `mark`,
`funding_rate` — fuer BTC/USDT:USDT 2199 Funding-Ereignisse in zwei Jahren,
Summe +10,56 %), und jeder Trade im Export traegt ein Feld `funding_fees`
(gemessen: 425 von 425 Trades, Summe −56,84 USD).

## Nachrechnen

```powershell
cd Agenten\Handel\freqtrade
.\messung-frequenzbremse.sh all      # 9 Varianten trading-agent + vor/voll der anderen
.\messung-shortseite.sh              # Futures: nur lang / nur kurz / beide
.\.venv\Scripts\python.exe messung-auswerten.py     # Tabelle aus den Protokollen
.\.venv\Scripts\python.exe -m unittest discover -s tests -t tests   # 22 Tests
```

`FALLE:` ein Lauf **ohne** Aufsatz ist nicht der Zustand „vorher" — die Vorgabe
in `frequenzbremse.py` aendert sich mit der Zeit. Der Vergleichslauf ist der mit
`user_data/messung/aus.json`; `messung-frequenzbremse.sh vor <bot>` setzt ihn.

**Warum lokal und nicht in Docker:** am 01.10.2026 antwortete die Docker-Engine
nicht mehr (CLI laeuft in den Timeout, keine Container, keine Images), und die
Messung sollte nicht auf die Reparatur warten. Freqtrade 2026.9 liegt deshalb in
`Agenten/Handel/freqtrade/.venv` (Python 3.13). Der Docker-Weg bleibt der
Hausweg; die Zahlen der Vorfassung (Freqtrade 2026.8) stehen in den Protokollen
vom 30.09.2026 und decken sich mit dem lokalen Lauf (2958 gegen 2954 Runden,
−83,90 gegen −83,35 % — die Differenz ist die Version).

## Was am 30.09.2026 dazwischenkam

Beim Start der Bots starb der Docker-Daemon und nahm **alle** Container mit.
Ursache war kein Fehler der Bots: **Commit-Erschoepfung** (1,0 GB frei von
86,4 GB), ausgeloest von einem MCP-Spawn-Sturm — der Gateway gleicht alle paar
Minuten die MCP-Server mit der Config ab, wollte `MCP_DOCKER`
(Docker-MCP-Server) starten, Docker war gerade weg, und daraufhin startete der
Abgleich jedes Mal **alle sechs lokalen Gruppen** neu: 146 Python-Prozesse.
Ohne Commit kann die WSL-VM nicht hochkommen, ohne VM kein Docker — ein
geschlossener Kreis. Einzelheiten und die Kur stehen in
[[Betrieb/Systemleistung-2026-09-29]].

Die Bots selbst haben das ueberlebt: `--restart unless-stopped` brachte alle
drei von allein zurueck, sobald Docker wieder lief.

## In der Handelszentrale (01.10.2026)

Der FreqTrade-Reiter der Zentrale (`Agenten/Handel/handelszentrale.py`, Reiter
"FreqTrade") zeigt die Bots aus `freqtrade/bots.json`: eine Zeile je Bot mit Port,
Strategie, Rahmen, Modus, Zustand, offen/max, Trades und G/V geschlossen — dazu die
offenen Positionen, die letzten geschlossenen Trades und G/V je Tag (14 Tage) des
angewählten Bots.

Wichtig für alle, die den Reiter lesen oder weiterbauen:

* Der Basis-Container auf 8080 gehört nicht zur Liste. Er fährt nur `SampleStrategy`,
  sein Zweck ist offen (T-199), und er antwortete am 30.09. nicht. Die Brücke zeigte
  vorher ausschliesslich ihn — der Reiter war taub, während drei Bots liefen.
* Angemeldet wird mit der Basis-config, der Port kommt vom Bot. Die Aufsatz-Dateien
  `config.<name>.json` tragen eigene Zufallspasswörter, die die laufenden Container
  ablehnen (401). Dieselbe Lehre steht in `bots.py::_api_stand`;
  `freqtrade_bridge.zugang_fuer()` setzt sie um. Dass ein Zugang für drei Bots bleibt,
  ist offen (T-300).
* Nur lesend. `freqtrade_bridge.ERLAUBT` ist eine Whitelist von GET-Endpunkten;
  `forceenter`, `forceexit`, `start`, `stop` gibt es in der Brücke nicht, und
  `tests/test_freqtrade_bridge.py` prüft das am Quelltext.

Nachprüfen: `cd Agenten/Handel && python freqtrade_bridge.py` (Liste plus Übersicht)
oder `python handelszentrale.py --pruefen` (letzter Block der Ausgabe).

## Offen

- Die **Bremse** ist gebaut, gemessen und aus (T-197) — wer sie will, schaltet
  sie je Bot ein. Der eigentliche Hebel liegt woanders: der Signal-Ausstieg
  erzeugt die Frequenz, und der Kostensatz entscheidet ueber das Vorzeichen.
- Die **kurze Seite** ist fuer den einen Bot gebaut, der eine belegte Regel hat
  (T-198) — sie macht das Ergebnis nicht besser. `trading_agent` und
  `new_or_top_agent` haben keine Short-Regel; dort wurde keine erfunden.
- `bots.json` nennt 11 Agenten als **nicht portierbar**. Zwei dieser Absagen
  waren falsch und sind am 01.10.2026 richtiggestellt (T-199): Funding kommt im
  Futures-Modus mit, und die OI-Reihe existiert oeffentlich (nur nicht
  archiviert). Die Absage bei den Zwangsschluessen bleibt — es gibt dort keine
  Historie nachzuladen.
- Der Vorgaenger-Container `freqtrade` (8080, `SampleStrategy`) laeuft weiter
  und hat keinen Zweck mehr; er wurde nicht angefasst.
- Der **Docker-Ausfall** vom 01.10.2026 ist nicht behoben, nur umgangen: die
  Engine antwortete nicht mehr (CLI in den Timeout, keine Container), die
  Freqtrade-Bots auf 8081-8083 sind dadurch **aus**. Die Messung lief im lokalen
  venv. Reparatur und Neustart der Container sind offen.