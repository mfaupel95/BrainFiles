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

## Fallen (OKX-API)
- `50110` — öffentliche IP fehlt in der API-Key-Whitelist. Im Portal eintragen
  oder Whitelist deaktivieren.
- `50101` — „APIKey does not match current environment“: Key gegen falsches
  environment verwendet (Demo-Key auf Live-Endpunkt).
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

## Backtest im nautilus-venv (13.09.2026)

Werkzeuge im Ordner (eigene Rueckgabe-Dateien, keine Netzverbindung):
`backtest.py` (EMA-Cross, Vorlage), `backtest_grid.py` + `grid_strategie.py`
(statische Kaufleiter), `bars_aus_daten.py` (Kursdaten -> Bars),
`test_grid.py` (19 Tests, echte Engine-Laeufe), `seitwaerts_probe.py`
(Seitwaerts-Fenster suchen). Start jeweils mit
`.venv/Scripts/python.exe <datei>`, Tests mit `-m unittest test_grid`.

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