---
name: nautilus-okx-handel
description: "OKX-Paper-Node in NautilusTrader aufsetzen/reparieren."
category: brainfiles
---

# NautilusTrader OKX-Node (Demo/Paper)

## Wann
OKX-Paper-/Demo-Node in NautilusTrader aufsetzen, starten, Credentials oder
Region prüfen, eine Order-Aufgabe testen — alles, was den lokalen
Nautilus-Knoten gegen die OKX-API betrifft. Abgrenzung: scanner/xperp/orb sind
`handel-spuren`; OKX-Wallet/Onchain sind die `okx-*`-Bundled-Skills.

Fuer den Rust-KI-Stack (NautilusTrader-Rust-Crates + Hugging-Face-candle,
Zwei-Ebenen-Architektur, candle-0.11-API, BacktestEngine in Rust):
`references/rust-stack.md`.

## Kernkonfiguration (bewährt, Stand Nautilus 1.231)
- OKX kennt nur **DEMO** und **LIVE** — kein „paper“. `environment` ist
  `OKXEnvironment.DEMO` (Demo-Key) bzw. `LIVE` (Live-Key); `region` ist das
  Enum `OKXRegion` (EEA), nie der String `"us"`.
- **Demo-Key → Region EEA** (`my.okx.com` / `eea.okx.com`). Ein GLOBAL-Aufruf
  mit einem EEA-Key liefert 50119 („API key doesn't exist“).
- `load_spreads=False` für EEA DEMO — der Spread-Endpoint antwortet dort mit
  404, und BTC-Quotes brauchen keine Spreads.
- **Factories vor `node.build()` registrieren** (`OKXLiveDataClientFactory`,
  `OKXLiveExecClientFactory` unter Venue „OKX“), sonst
  „No LiveDataClientFactory“.
- Credentials als **ein** vollständiger Satz aus einer Quelle lesen
  (`HKCU\Environment`), nie Registry-Werte mit Prozess-Umgebung mischen.
- Paper-Client-Order-IDs müssen **alphanumerisch** sein.
- `nautilus_trader` ist nicht global installiert — der Node läuft aus einem
  eigenen `.venv` (nicht das Handel-venv der scanner/xperp-Spuren).
- **OpenBLAS bricht beim Import ab** („Memory allocation still failed after
  10 retries“), wenn Threads knapp sind oder viele Prozesse parallel laufen:
  vor dem Start `OPENBLAS_NUM_THREADS=1` und `OMP_NUM_THREADS=1` setzen —
  die Thread-Allokation begrenzen, nicht den RAM (RAM war frei).

## Fallen (OKX-API)
- `50110` — öffentliche IP fehlt in der API-Key-Whitelist. Im Portal eintragen
  oder Whitelist deaktivieren.
- **HTTP 401: IMMER den Body lesen** (19.09.2026) — OKX verpackt Business-
  Fehler als HTTP 401, der Code im Body discriminiert: `50101` = Key passt
  nicht zum Environment (EEA-LIVE-Key mit Demo-Header), `50119` = Key
  existiert auf dieser Region nicht (Global-Aufruf mit EEA-Key). Gemessen:
  EEA-LIVE-Key -> my.okx.com OHNE x-simulated-trading = 200, MIT
  Demo-Header = 50101, www.okx.com = 50119. Ein Demo-Header-Aufruf auf
  einen LIVE-Key ist nie der Weg zu einem Demo-Test — demo_order_test.py
  verlangt einen echten DEMO-Key (OKX-Portal, Bereich Demo Trading) und
  stoppt sonst sauber im Preflight, keine Order wird gesendet.
- `50101` — „APIKey does not match current environment“: Key gegen falsches
  environment verwendet (Demo-Key auf Live-Endpunkt).
- `50124` — „This API Key does not have trading permission for the market“:
  der Key hat `trade` im Account-Config, aber nicht fuer DERIVATIVES (SWAP ist
  Derivatives). Im Portal beim API-Key die Trade-Permission zusaetzlich fuer
  Contracts/Derivatives setzen — ein Haekchen bei Spot allein reicht nicht.
  Kommt VOR der Margin-Pruefung, also auch bei leerem Konto.
- **Balance pruefen, bevor eine Order erwartet wird:** `/api/v5/account/balance`
  zeigt, welche Waehrungen das Konto hat. Ein Demo-Konto kann Dollar-basierte
  Waehrungen (USD/USDG/USDC) haben, aber KEIN USDT — dann scheitert eine
  BTC-USDT-SWAP-Order an der Margin, selbst wenn die Permission stimmt.
  `avail None`/`eq None` = Waehrung fehlt, nicht "Konto leer".
- `403 code 1010` ohne `User-Agent`-Header; mit `Mozilla/5.0` kommt die echte
  Antwort (z. B. 50110) statt eines Geoblock-Fehlschlusses.
- Fehlende Quotes („node.run() – verbinde …“ und danach nichts) haben zwei
  geklaerte Ursachen: (1) der **Data-Client darf KEINE Zugangsdaten** bekommen —
  mit Schluessel meldet er sich zusaetzlich am privaten business-Websocket an
  und schlaegt bei IP-Whitelist-Fehler komplett fehl, oeffentliche Quotes
  inklusive; (2) der **Order-Client ist opt-in** — sonst wartet der Kernel 60 s
  auf ihn und keine Strategie startet, kein Abo. Belegbar sauberer Pfad:
  Data-Client ohne Credentials, Order-Client opt-in, `test_gui_quote_pfad.py`
  mit ankommenden Quote-Ticks.

## Kraken-Adapter (Spot) — fuer die Migration von OKX-SWAP

Der installierte Nautilus-1.231-Kraken-Adapter (geprueft 19.09.2026) ist der
Weg, die nautilus-Spur von OKX-Derivat auf Kraken-Spot (BTC/EUR, gebuehrfrei
bis 10k EUR Monatsvolumen) umzustellen. Verifizierte API-Fakten:
- Venue-Konstante `KRAKEN` (`KRAKEN_VENUE = Venue("KRAKEN")`), Client-ID
  `KRAKEN_CLIENT_ID`; Factories `KrakenLiveDataClientFactory` /
  `KrakenLiveExecClientFactory`; Configs `KrakenDataClientConfig` /
  `KrakenExecClientConfig`.
- `KrakenEnvironment` hat nur `LIVE` und `DEMO` — **Demo ist nur fuer
  FUTURES verfuegbar, Spot hat kein Demo**. Ein Spot-Quote-Feed laeuft also
  gegen LIVE (oeffentliche Quotes brauchen keinen Key).
- `KrakenProductType` hat `SPOT` und `FUTURES`; Default ist `(SPOT,)`.
- Env-Variablen: `KRAKEN_SPOT_API_KEY` / `KRAKEN_SPOT_API_SECRET` (Spot),
  `KRAKEN_FUTURES_*` (Futures).
- **Der Exec-Client braucht ein WebSocket-Token.** Ein Kraken-Key ohne die
  Berechtigung `Access WebSockets API` scheitert beim Connect mit
  `RuntimeError(Authentication error: Failed to get WebSocket token: API
  error: EGeneral:Permission denied)`, waehrend DERSELBE Key ueber REST
  (Guthaben, offene Orders) einwandfrei antwortet. Erst den REST-Gegenbeweis
  fuehren, dann im Portal den Haken setzen — nie umgekehrt den Schluessel fuer
  fuer tot erklaeren. Ohne WS-Recht bleibt der REST-Orderpfad der einzige Weg
  - und der ist seit 24.09.2026 GEBaut (`kraken_rest.py` + Live-Zweig in
  `handeln.py`): die Order laeuft direkt ueber den hauseigenen
  `kraken/kraken.py`-REST-Client, Nautilus bleibt fuer Quotes/Strategie
  (Details: `references/kraken-spur.md`).
- Spot ist CASH (kein Hebel): die auf SWAP gebaute Spur (max_hebel 5) wird
  auf Spot zu einem 1x-Kauf — andere Mechanik, kein Derivat.
- Vollstaendige Adapter-API, Instrument-IDs, Order-Test, der
  postxid-Fill-Bug (1.231.0) und warum 2.0.0rc5 trotz verifiziertem Fix kein
  brauchbares Ziel ist: `references/kraken-spur.md`.

## Dauerlauf-Spur (seit 13.09.2026)
- `nautilus/handeln.py` ist der Zyklus-Einstieg fuer den Dauerlauf
  (`dauerlauf.py` → SPUREN, Spurname `nautilus`): je Zyklus eine BEGRENZTE
  Node-Session (~30 s), Quotes sammeln, Herzschlag (`zustand.json`
  `letzter_lauf`) + Journal schreiben. Papierfest wie spiegel/omniquant:
  `--live` verweigert mit einem Grund OHNE das Wort Freigabefenster, damit
  der Dauerlauf keine Freigabe anfragt (getestet in test_handeln.py).
- Der Dauerlauf startet die Spur ueber das Feld `"python"` im SPUREN-Eintrag
  mit dem nautilus-eigenen venv — nautilus_trader liegt NICHT im
  scanner-venv. Neue Spuren mit eigenem venv bekommen dasselbe Feld.
- **Bedingung 4 ist verdrahtet** (13.09.2026): nach Herzschlag und Journal
  kopiert der Zyklus `handelsjournal.csv` + `zustand.json` nach
  `journal_zweitziel` (`Q:\Handel_Journal\nautilus`) — via
  `scanner/wachen_pruefung.spiegele_journal`, per `importlib` aus dem
  Dateipfad geladen (kein `sys.path`-Eintrag fuer `scanner/`, dort liegen
  `okx.py`/`handeln.py`). Fehlendes Ziel = kein Zyklusfehler (Rueckgabe 0);
  der Stand steht in `zustand.json` (`journal_zweitziel_ok`/_info) und in
  `handeln.py --wachen`. Nachweis: `cmp handelsjournal.csv
  Q:/Handel_Journal/nautilus/handelsjournal.csv` — byte-gleich, auch fuer
  den automatischen Dauerlauf-Zyklus.
- Nautilus-Logger nimmt keine printf-Args: `self.log.info("x %s", y)` wirft
  `TypeError: an integer is required` — immer f-string einsetzen.
- Kennzahlen dieser Spur fuer einen Bericht (Herzschlag, Zyklen, Quotes je
  Zyklus, Takt-Treue, Bus-Rueckgabecodes) stehen im `nautilus`-Abschnitt von
  `handel-spuren/references/spur-bericht.md`; der 1-s-Lauf je Zyklus dort ist
  die Vorschau von `dauerlauf.nur_fenster_fehlt`, kein Fehler.

## Node starten — Docker bevorzugt (ab 19.09.2026)
- **Docker ist die robuste Startmethode** (kein Desktop, kein Fokus-/DPI-/
  Virtuelle-Desktop-Kampf, startet nach Neustart selbst):
  `docker build -t nautilus-demo-node:1.231.0 .` dann
  `docker run -d --name nautilus-demo --restart unless-stopped -e
  OKX_API_KEY=dummy-node-key -e OKX_API_SECRET=dummy-node-secret -e
  OKX_API_PASSPHRASE=dummy-node-pass nautilus-demo-node:1.231.0`;
  Quotes: `docker logs -f nautilus-demo`. Dockerfile + requirements-node.txt
  liegen im nautilus-Ordner (eigenes Repo, committen).
- **Nautilus-OKXFactory verlangt die Env-Variablen HART**, auch fuer den
  oeffentlichen HTTP-Client (Instrumenten-Metadaten) — im Container stehen
  Dummy-Werte, echte Keys verlassen den Rechner nie. Der Quotenstrom selbst
  braucht keine Schluessel.
- **`load_client_configs` verlangte die Keys auch im reinen Quoten-Modus**
  (SystemExit) — seit 19.09.2026 nur noch bei `mit_order_client=True`.
  Der Quoten-Modus ist damit ohne Keys lauffaehig (Doku versprach es, der
  Code hielt es nicht).

## DEMO-Order-Smoke-Test (`demo_order_test.py`)
- **Der Test ist der EINZIGE Pfad fuer eine echte DEMO-Order** (nie LIVE):
  Default ist read-only Preflight, `--execute` erlaubt genau EINE DEMO-Runde
  (Market-Buy, Stop-Protection, Reduce-Only-Close), Evidenz als append-only
  JSONL in `logs/demo-orders-*.jsonl` ohne Credentials/Balances.
- **`load_client_configs` braucht `mit_order_client=True`** (2 Stellen: `get()`
  und der Node-Aufbau) — ohne Exec-Client ist `execution` leer und `guard()`
  wirft `KeyError 'OKX'`. Der reine Quoten-Modus (Default False) hat keinen
  Exec-Client und kann keine Orders senden.
- **Preflight stoppt sicher vor jeder Order:** `require_clean` (keine
  Bestand/Orders/Algos) und `require_trade` (Key-Permission) laufen VOR dem
  Senden. Ein Auth-Fehler (HTTP 401) bricht im Preflight ab, es wird nichts
  gesendet — der Test ist damit ein sicheres Diagnosewerkzeug fuer die Keys.
- **Keys pruefen ohne Portal:** 401 auf `my.okx.com` UND `www.okx.com` heisst
  Key deaktiviert/geloescht oder Passphrase geaendert (siehe Fallen oben);
  die aktuelle oeffentliche IP (`Invoke-RestMethod api.ipify.org`) im
  OKX-Portal freigeben, wenn die Whitelist aktiv ist.

## Docker-Log-Auswertung in PowerShell (systempruefung.ps1 Block 14)
- **EAP lokal auf Continue** fuer den docker-Aufruf: mit
  `$ErrorActionPreference='Stop'` zaehlt stderr von docker als Fehler
  (NativeCommandError) und die Zuweisung bleibt leer.
- **docker logs liefert ANSI-Escape-Sequenzen** (`\x1b[...m`) - vor dem
  Regex-Match entfernen (`$_ -replace "\x1b\[[0-9;]*m", ""`), sonst
  beginnt die Zeile nicht mit der Ziffer und `^\d{4}-` matcht nie.
- **`[datetimeoffset]` statt `[datetime]::ParseExact(AssumeUniversal)`**
  fuer den UTC-Zeitstempel: ParseExact speichert als Local und verfaelscht
  die Differenz um die Zeitzone (120 min). `[datetimeoffset]::Parse(ts+'Z',
  InvariantCulture, AssumeUniversal)` respektiert das Z korrekt.

## GUI-Node starten (nautilus_gui.py)
- **Das GUI startet den Node NICHT von selbst** — Status bleibt STOPPED, bis
  der Button "▶ Start DEMO-Node" geklickt wird. Es gibt kein
  Autostart-Argument; ein Start per `Start-Process` oeffnet nur das leere
  Fenster. Oeffnen + Klick auf den Start-Button, ODER headless den
  Zyklus-Einstieg (`handeln.py`/`run_okx_paper_node.py`) nehmen.
- **Fuer den reinen Quotenstrom sind KEINE Keys noetig** (Data-Client ohne
  Credentials). Das Badge "Keys: OK ✓" spiegelt nur, ob die drei
  Env-Variablen in der Prozessumgebung stehen; der Haken "Order-Client
  (DEMO)" ist opt-in und der EINZIGE Pfad, der die Keys wirklich braucht.
  Startet das GUI per Wrapper, die Variablen in dessen Umgebung setzen
  (nicht nur in HKCU\Environment — os.environ liest die Prozessumgebung).
- Der GUI-Zyklus macht dieselbe Bedingung-4-Spiegelung wie die Dauerlauf-
  Spur (Journal/Zustand nach Q:\Handel_Journal\nautilus).

## Backtest im nautilus-venv (13.09.2026)

Werkzeuge im Ordner (eigene Rueckgabe-Dateien, keine Netzverbindung):
`backtest.py` (EMA-Cross, Vorlage), `backtest_grid.py` + `grid_strategie.py`
(statische Kaufleiter), `bars_aus_daten.py` (Kursdaten -> Bars),
`test_grid.py` (19 Tests, echte Engine-Laeufe), `seitwaerts_probe.py`
(Seitwaerts-Fenster suchen). Start jeweils mit
`.venv/Scripts/python.exe <datei>`, Tests mit `-m unittest test_grid`.
- **`daten/*.csv` sind TAGESdaten** (`Datum,Open,High,Low,Close`), keine
1H-Kerzen: BTC reicht bis 2014 zurueck (~4.347 Zeilen). Alle Dateien sind
CRLF — neue Zeilen NUR mit CRLF anhaengen, sonst Mischzeilenenden und
Ganzdatei-Diff.
- **Auffrischen seit 19.09.2026: `nautilus/daten_auffrischen.py`**
  (yfinance, Start `.venv/Scripts/python.exe daten_auffrischen.py`, Tests
  `-m unittest test_daten_auffrischen`): fehlende Tage ab dem letzten
  CSV-Datum anhaengen, eine unmoegliche Schlusszeile (Close < Low o. a.)
  entfernen und durch die frische Zeile fuer dasselbe Datum ersetzen,
  Ticker ohne neue Daten dokumentieren statt abzubrechen. yfinance ist
  nicht vorinstalliert: `pip install yfinance` ins nautilus-venv.
- **yfinance-Aufruf mit `auto_adjust=False`** — der Default (True) liefert
  Dividenden-/Split-bereinigte Preise, die nicht zur unbereinigten
  Historie der Dateien passen.
- **MATIC-USD liefert seit 2025-03-24 keine neuen Daten** (Yahoo-Ticker
  wurde zu POL umbenannt). "keine neuen Daten" ist ein Befund JE Ticker,
  kein Abbruchgrund fuer die ganze Auffrischung.
- **`entferne_letzte_unmoegliche` MUSS die Datei zurueckschreiben** (19.09.2026):
  entfernt sie die defekte Zeile nur im Speicher, bleibt sie im Bestand und
  yfinance liefert sie beim naechsten Lauf erneut -> Datums-Doppel (passiert:
  08-10-Kerzen in BTC/ETH/SOL/XRP, erst der Sweep deckte es auf).
  `--saeubern` bereinigt den Bestand einmalig (ALLE unmoeglichen Zeilen und
  Datums-Doppel, letzte gewinnt).
- **`daten/*.csv` ist NICHT versioniert** (gitignore `*` greift in
  `Agenten/Handel/daten`): vor massenhaften Schreiblauefen
  `daten.bak-JJJJMMTT` anlegen, git kann die Daten nicht wiederherstellen.
  Der Sweep verwarf unmoegliche Kerzen bereits (nautilus-Engine), nur
  unsichtbar im tail — eine Saetuberung aendert Aktien-Ergebnisse spuerbar
  (AAPL trail +39,4 -> -30,2).

- **Die Venue kommt vom INSTRUMENT, nie geraten.** `Venue("SIM")` neben einem
  BINANCE-Instrument laesst `add_instrument` mit "Cannot add an Instrument
  without first adding its associated venue" scheitern; `venue =
  instrument.venue` und alles laeuft. Daran war `backtest.py` von Anfang an
  kaputt - es lief nie durch, ohne dass es auffiel.
- **`BarDataWrangler` haengt an der Herkunft des Rahmens.** Er reicht
  `data.values` als beschreibbaren Puffer nach Cython; mit pandas 3.0.5 ist
  `.values` NUR bei `read_csv` beschreibbar - ein aus Listen oder einem
  numpy-Array gebauter Rahmen bricht mit `buffer source array is read-only` ab.
  Bars deshalb selbst bauen (`bars_aus_daten.bars_bauen`): Preise auf die
  Instrumentgenauigkeit runden, DANN auf Plausibilitaet pruefen (sonst
  scheitert der Bar-Konstruktor an der gerundeten Kerze), unmoegliche Kerzen
  verwerfen und zaehlen.
- **Eine unmoegliche Kerze steht in den eigenen Daten:** die letzte Zeile von
  `Agenten/Handel/daten/BTC-USD.csv` (2026-08-10) hat ein Close unter dem
  Tagestief. Jede Auswertung dieser Reihe muss die Zeile ueberspringen und die
  Zahl der gerechneten Kerzen ausweisen.
- **Orderkennungen muessen bei JEDER Absendung neu sein.** Wird eine Stufe
  nach einem Verkauf neu armiert, entsteht sonst dieselbe `ClientOrderId` und
  die Engine weist sie mit "duplicate ClientOrderId" ab - die Stufe bleibt
  danach leer, und der Fehler steht nur im Log (kein Rueckgabecode, keine
  Ausnahme). Zaehler in die Kennung (`G001B003`), und ein Test, der dieselbe
  Stufe zweimal durch einen Zyklus fuehrt.
- **Eine Kauflimit ueber dem Markt ist eine getarnte Marketorder** und wird im
  Backtest sofort gefuellt (zu Marktpreis, nicht zum Stufenpreis): ohne Wache
  ist der Einsatz in einer Kerze verbraucht. Test ueber die ABGESCHICKTEN
  Orders, nicht ueber Fills - eine Order, die nie fuellt, steht in keinem
  Fill-Bericht.
- **Der Kontoreport bewertet offenen Bestand zum EINSTAND.** Ohne Quote-Ticks
  gibt es keine Marktbewertung; ein Buch, das mit Bestand endet, liest sich
  damit zu gut (13.09.2026: Engine 9.962,78 gegen nachgerechnet 8.230,09 USDT,
  Differenz genau der Einstandswert des Bestands). `buch_aus_fills()` rechnet
  Cash + Bestand x Schlusskurs; der Engine-Wert bleibt als Gegenprobe in der
  Ausgabe stehen. Nur wenn das Buch am Ende FLACH ist, sind beide gleich.
- **`FixedFeeModel` verlangt eine POSITIVE Gebuehr** - 0 wird abgelehnt
  (`commission="0.000001 USDT"` ist die Null, die durchgeht).
  `MakerTakerFeeModel` liest die Gebuehren aus dem INSTRUMENT.
- **`TraderId` braucht einen Bindestrich** (`\"PRUEF-001\"`); ein Wert ohne
  '-' laesst den Rust-Kern panicken, nicht Python.
- **Fill-Bericht: Spalten heissen `side`/`avg_px`/`quantity`, nicht
  `order_side`/`last_px`/`last_qty`**, und `commissions` ist TEXT
  (`1.20003013 USDT`) - mit `re.sub` parsen, nicht mit `float()`. Die Zahl der
  Spalten ist gross; vor dem Auswerten `list(fills.columns)` zeigen.
- **Ein Grid gehoert gegen Buy-and-Hold auf DEMSELBEN Einsatz gerechnet.**
  Konto und Einsatz muessen gleich gross sein (Konto = Einsatz), sonst stehen
  Rendite und Vergleich auf zwei Grundlagen. Ergebnis 13.09.2026 (1H
  BTC-USDT, -32 % Kurs): Grid -17,7 %, Halten -32,0 %; in drei nach Regel
  gesuchten Seitwaerts-Fenstern +1,8..+14,3 % gegen ~0 % beim Halten - und
  jeweils mit HALBIERTER Stufenzahl besser, weil die Gebuehren mit der
  Frequenz wachsen.

## Strategie-Sweep (`sweep_strategien.py`, seit 16.09.2026)

Drei Strategien (EMA-Cross, Grid, Trailing-Ausstiegsform) ueber alle
`daten/*.csv` auf EINER Grundlage: Konto = Einsatz, 1x, Taker 0,05 %, kein
Funding. Ergebnis als Tabelle + `sweep_ergebnis.json`; jede Strategie einzeln
in try/except gefangen, Fehler dokumentiert statt abgebrochen. EMA und Grid
laufen in der Engine (Wiederverwendung von `backtest.py`/`backtest_grid.py`),
Trailing als reine Simulation der Ausstiegsform (die Spur bezieht ihre
Einstiege aus der kopier-Spur; im Sweep dient der EMA-Cross als synthetisches
Signal - gemessen wird die FORM, nicht ein Markt-Urteil).

- **Nautilus-1.231-Importpfade:** `AccountType`/`OmsType` aus
  `nautilus_trader.model.enums` (nicht `common.enums` - der Name existiert dort
  nicht), `Money`/`TraderId`/`BarType`/`Venue` aus `nautilus_trader.model`,
  `USDT` aus `model.currencies`. Die bestehenden Backtests sind die
  Import-Referenz - von dort abschreiben, nicht aus dem Gedaechtnis.
- **candle-0.11 hat die API geaendert:** `Linear::new(weight, bias)` ist jetzt
  die freie Funktion `candle_nn::linear(in, out, vb)`, und `AdamW::new(vars,
  lr)` heisst `AdamW::new_lr(vars, lr)`. Vor dem Schreiben die Signaturen in
  `~/.config/cargo/registry/src/index.crates.io-*/candle-nn-0.11.0/src/` pruefen,
  nicht aus dem Gedaechtnis (Details: `references/rust-stack.md`).
- **`bars[i].ts_event` ist int-Nanosekunden.** `ts_event + timedelta` wirft
  TypeError; erst `datetime.fromtimestamp(te/1e9, tz=timezone.utc)`. Und eine
  Funktion, die ein datetime erwartet (z. B. `ausstiegsgrund`), darf nicht mit
  einem ISO-String gefuettert werden - `str >= datetime` ist der naechste
  TypeError.
- **Trailing-Simulation: feste Einsatzgroesse je Trade (kein Zinseszins) und
  Frist ab der Einstiegs-Bar, nie ab "jetzt".** Sonst kompoundieren lange
  Trends ins Absurde (NVDA 182.000 %) und die Frist greift nie. Damit wird die
  Spalte erst mit EMA/Grid vergleichbar.
- **`backtest_grid.lauf(quelle, stufen, unten, oben, spanne, einsatz,
  ohne_gebuehr, von, bis)`** liefert `rendite_prozent`/`buy_and_hold_prozent`.
  Auf Penny-Assets (LUNC, DOGE) wirft die Spannenrechnung
  `ValueError: verlangt 0 < unten < oben` - pro Instrument abfangen und im
  JSON dokumentieren. Eine 12-Stufen-Leiter um den ERSTEN Kurs handelt einen
  Range-Laeufer nicht (`fills=0` ist ein Befund, kein Fehler).
- **`backtest_grid_ergebnis.json` wird von JEDEM Grid-Lauf ueberschrieben**
  (auch vom Sweep): nach einem Sweep ist der Arbeitsbaum nicht sauber - die
  Ergebnisdatei gehoert in denselben Commit.
- **Warnungsflut schluckt die Ausgabe.** Die Backtests laufen auf pandas 3.x und
  schreiben je Zeile eine `Pandas4Warning`; mit einer Ausgabefilterung
  (`Select-Object -First N`) stehen dann nur Warnungen im Fenster und die
  Ergebnistabelle faellt heraus. Im Skript oben `warnings.filterwarnings("ignore")`
  setzen (der Kategorie-Filter `FutureWarning` allein greift nicht).

## Ablage (Kostenfalle)
- Lauffähiger Node-Code gehört nach `Agenten/Handel/` (versioniert, in der
  Sicherung nach G:), **nicht** in die Werkstatt — die wird geleert und ist von
  der Sicherung ausgeschlossen; dort angelegte Arbeit ist weg.
- Die Node-Historie (eigenes `.git`) liegt ausser Haus im privaten
  GitHub-Repo `mfaupel95/nautilus` (Remote `origin`, Zweig `master`); nach
  jeder Aenderung am Node **committen UND pushen** — robocopy nimmt `.git`
  generell aus (`/XD .git`), ungepushte Commits existieren also nur auf
  diesem Rechner. `.gitignore` mit `set-okx-env.ps1`, `*.env`, `*.key`,
  `*.pem` niemals lockern: ein einmal committeter Schluessel bleibt im
  Verlauf und verlangt History-Rewrite.
- Verlust-Recovery: `O:\Werkstatt\` ist die Zweitkopie und hält oft den
  überlebenden Git-Klon inkl. `.venv`. `G:`/`Q:` enthalten **keine**
  Werkstatt-Inhalte (nur MaxHirn/Agenten).