# Boersenzugriff fuer Backtests und Papierspuren

Kompakte Signatur-Landkarte und Fallen fuer die Datenquellen der Spuren.
Die Regeln in SKILL.md gelten immer; hier steht das Nachschlagewissen.

## OKX (okxf.py in xperp/)

- `okxf.kerzen(inst, bar="1H", anzahl=300)` — oeffentlich, OHNE Token. Antwort
  als `[ts_ms, o, h, l, c, vol]`, aufsteigend. **Unbekannter instId = leere
  Liste, keine Exception.** Bar-Namen: `15m`, `1H`, `4H`, … (nicht `M15`).
- `okxf.kerzen_lang(inst, bar, seiten)` — history-candles, 100 je Seite,
  rueckwaerts via `after`. Freie Historie: **~14 Monate M15** (gemessen:
  400 Seiten = 40.000 Kerzen bis 416 Tage zurueck), nicht 2 Jahre und nicht
  nur 3 Monate.
- `okxf.instrumente(kategorie)` filtert auf `ruleType=xperp` unter
  `instType=FUTURES` — liefert fuer SWAP/SPOT grundsaetzlich 0. Existenz eines
  normalen Perps pruefen mit `okxf.swap_instrument(inst_id)` (wirft `51001`
  bei Unbekannt) oder direktem public-instruments-Call.
- Schluessel: `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE` (okxf),
  Host `OKX_BASE`, Demo-Schalter `OKX_SIMULATED`/`OKX_DEMO`. Gesucht wird erst
  in der Prozessumgebung, dann in der Registry HKCU\Environment
  (`_aus_registry`). Werte setzen mit
  `[Environment]::SetEnvironmentVariable(<name>, <wert>, 'User')`.
- Demo-Modus: Header `x-simulated-trading: 1`; Demo-Keys sind EIGENE
  Schluessel, nicht die Live-Keys. `50119` = Key existiert nicht — falscher
  Host, falscher Modus, oder Key veraltet/widerrufen. `OKX_BASE` muss die API
  sein (`https://www.okx.com` bzw. `https://eea.okx.com`), nicht
  `https://my.okx.com` (Web-Oberflaeche).

## OKX-Spot ohne Schluessel (okx.py in scanner/) — die Grenze, die Spuren still tötet

`okx.kerzen(inst, bar="1D", anzahl=300)` ist der SPOT-Abruf (scanner, kraken
und die Prognose-Spuren); `okxf.kerzen` in xperp/ ist der FUTURES-Abruf. Nicht
verwechseln.

- Antwort `[ts_ms, o, h, l, c, vol]`, aufsteigend, **6 Felder**. Aeltere
  mitgelieferte Kerzendateien im Handel-Ordner führen nur FUENF Felder (kein
  Volumen): `zu_hoeherem_zeitrahmen()` liest `g[5]` und bricht mit
  `IndexError`. Live-Daten sind davon nicht betroffen — die Datei ist ein
  aelterer Export, fuer Tests auf sechs Felder normalisieren (Volumen 0.0).
- **Oeffentlich hoechstens 1440 Stundenkerzen (60 Tage), egal was man
  anfordert.** `limit` gilt je Abruf (max 300); `after` blaettert rueckwaerts
  (aelter als der uebergebene Stempel). Seit 15.09.2026 blaettert
  `okx.kerzen()` selbst nach, wenn `anzahl > 300`, entdoppelt ueber den
  Zeitstempel und liefert `anzahl` Kerzen (600 -> 600, 700 -> 700). Der
  Standardaufruf (<= 300) bleibt eine einzige Abfrage.
- **Eine Blaetterung, die weniger liefert als angefordert, meldet das nicht.**
  Genau daran ist eine Aussage gescheitert: ein „8-Wochen-Prueffenster" waren
  96 Kerzen (4 Tage), weil der Abruf still bei 1440 endet. Wer laengere
  Fenster braucht, nimmt die mitgelieferte Reihe (`--lokal`) fuer das AELTERE
  Fenster und den Live-Abruf fuer das juengere; und die Funktion muss bei zu
  wenig Kerzen LAUT abbrechen statt ein kuerzeres Fenster als erfuellt
  auszugeben.
- **Warmlauf gegen Abrufgrenze rechnen, BEVOR eine Spur verdrahtet wird.** Ein
  Indikator, der mehr Historie braucht als der Abruf hergibt, liefert nicht
  ungenaue Werte, sondern gar keine: die Ausrichtung bleibt `None`, das
  Zusammenspiel („alle einig") ist dauerhaft falsch, und die Spur kann NIE
  handeln — im Test gruen, im Betrieb stumm. Beispiel MACD ueber mehrere
  Zeitrahmen mit Faktor 16: 16 x (26 + 9) = **560 Basiskerzen**; mit dem
  alten 300er-Deckel war der 16er-Rahmen immer `None`. Nachgemessen an echten
  Kerzen: bei 500 `None`, ab 550 vorhanden. Behoben wird der ABRUF, nicht der
  Schwellwert — den Indikator klein rechnen misst eine andere Strategie.
- **Geteilte Indikator-Bibliothek:** `Handel/ti_indikatoren.py`
  (`squeeze_momentum`, `macd`, `zu_hoeherem_zeitrahmen`, `macd_mtf`,
  `wavetrend`), reine Standardbibliothek, Konvention wie `xperp/indikatoren.py`
  (Eingabe `[ts, o, h, l, c, vol]`, Ausgabe gleicher Laenge, `None`-Praefix
  statt Auffuellung mit dem ersten Kurs). `macd_mtf` gibt die AKTUELLE
  Ausrichtung je Zeitrahmen zurueck (`{faktor: {macd, signal, hist,
  ausrichtung}, "einig": bool}`), keine Reihe — es wird auf einem rollenden
  Fenster aufgerufen, nicht je Index. `supertrend` liegt in
  `xperp/indikatoren.py` und wurde nicht doppelt gebaut.

## Kraken (kraken.py in kraken/)

- `kraken.kerzen(paar, intervall, anzahl)` — oeffentlich, **max 720 Kerzen je
  Abruf, `since` wird IGNORIERT** (identische Antwort fuer since=0/1,7e9;
  reproduziert 2026-09). M15 → 7,5 Tage, 1H → 30 Tage, 1440 → 2 Jahre. Fuer
  Intraday-Backtests unbrauchbar; OKX nehmen. Der Kraken-MCP-Server nutzt
  dieselbe oeffentliche API, also dieselbe Grenze.
- Antwort kommt unter dem **kanonischen** Paarnamen (HYPEUSD → XHYPEUSD
  o.ae.): nie `d.get(paar)`, sondern den einzigen Nicht-`last`-Eintrag nehmen
  (`kraken._erste_reihe`). `last` = Zeitstempel der JUENGSTEN Kerze.
- Schluessel: `KRAKEN_API_KEY`, `KRAKEN_API_SECRET` (private Calls);
  OHLC/Ticker/AssetPairs sind ohne Schluessel lesbar.
- **Die Spot-Anbindung kann NUR kaufen/verkaufen: buy/sell, kein Short, kein
  Hebel.** `markt_kauf`/`markt_verkauf`/`stop_setzen` decken Long ab; ein
  Leerverkauf oder eine Position mit Hebel ist auf diesem Weg nicht machbar.
  Short-mit-Hebel ist **Margin-Trading** (eigener Margin-Schluessel mit
  Margin-Recht, freigegebenem Kontingent, `leverage`-Parameter, Margin-API,
  Nachschusspflicht) - ein anderer Pfad, kein Feature der Spot-Anbindung.
  Wer "Long UND Short" an einer Spur will, muss das als EIGENES Teilprojekt
  mit eigener Freischaltung planen, nicht als Erweiterung des vorhandenen
  Kraken-Spot-Wegs.

### Kraken `EAPI:Invalid nonce` — ein Sequencing-Problem, kein Schluessel-Problem

Kommen private Kraken-Calls mit `EAPI:Invalid nonce` zurueck, ist die
**Signatur korrekt** (Key+Secret+`api_sign` kanonisch; der Fehler kommt als
fachliche `error`-Liste, nicht als HTTP 401/403 — Kraken hat die Anfrage
verarbeitet und nur den nonce abgelehnt). Nicht den Key verdaechtigen, sondern
den nonce-Wert.

**Diagnose (Reihenfolge, jeweils eigener Balance-Aufruf mit gesetztem nonce):**
1. `public/Time` holen → Serverzeit s. Lokale Uhr dagegenhalten: eilt sie der
   Serverzeit VORAUS (hier 2-3 s), liegt ein Wallclock-nonce in der Zukunft und
   wird abgelehnt — Kraken akzeptiert nur ~Gegenwart bis ~1-2 s Zukunft
   (Gegenprobe: +1 Tag sicher abgelehnt).
2. Nicht-monoton sondieren: nonces **weit VOR** (s-600s) und **weit NACH**
   (s+300s) der Serverzeit. Werden BEIDE abgelehnt, sitzt der bei Kraken
   gespeicherte nonce-Peak auf/ueber der aktuellen Serverzeit — der gueltige
   Korridor (Peak < nonce < Serverzeit+~2 s) ist LEER, und **kein nonce
   funktioniert**, bis die echte Zeit den Peak ueberholt (Sekunden bis Minuten)
   ODER der sendende Prozess neustartet.
3. Wer treibt den Peak ueber die Serverzeit? Ein Prozess, der den nonce aus der
   LOKALEN Uhr ableitet, waehrend die Uhr voreilt — sobald zwei Programme
denselben `KRAKEN_API_KEY` nutzen (Haus-`kraken.py` UND der Kraken-MCP-Server,
README warnt: „eigenen Schluessel je Programm"), sendet einer nonces in der
Zukunft, Kraken merkt sie sich als neuen Peak, und der andere wird dauerhaft
abgelehnt. Laufende Prozesse (MCP-Instanzen, Spur-Kinds) tragen die ALTE Logik
im Speicher — ein Fix greift erst nach Neustart der Prozesstrees.

**Fix-Kern:** ein geteilter, persistenter nonce-Pool (`kraken/nonce_pool.py`),
den ALLE Programme mit demselben Key laden, als monoton steigende Datei mit
Datei-Lock. Fuer die Sperre das **O_EXCL-Sperrdatei-Muster** verwenden —
`msvcrt.locking` (8-Byte-Sperre) scheitert auf leerer/kuerzerer Datei mit
Permission denied. Nur wenn alle Sender denselben Pool nutzen, ueberholt
niemand mehr; die Laufzeitdatei ist strikt lokal (nie committen).

**Zwei Fallen, die ein Pool NICHT loest — beide gemessen 2026-09-19:**
1. **Drift-Korrektur (nonce = Serverzeit statt Wallclock) macht es SCHLIMMER**
   und ist der falsche Weg. Sie senkt den nonce UNTER den von parallelen
   Sendern gesetzten Kraken-Peak → dauerhaft `EAPI:Invalid nonce`. Die einzige
   nachweislich funktionierende Erhebung war die monotone **Wallclock**
   (`max(time.time()*1e6, letzter+1)` — die 5/5-Sonde). Nicht "korrigieren",
   sondern den gemeinsamen Zaehler streng monoton halten.
2. **Sitzt der Kraken-seitige nonce-Peak STUNDEN ueber der aktuellen Zeit,
   hilft kein lokaler Pool.** Wenn monotone nonces in normalem Bereich ueber
   mehrere Minuten ALLE abgelehnt werden (und auch ein Sweep ueber ±Stunden
   um die Serverzeit nichts akzeptiert), ist der gespeicherte Peak nicht mehr
   einzuholen — weder Wallclock noch Serverzeit erreicht ihn. Kein Code und
   kein Neustart loest das; es braucht einen **neuen API-Key** (Kraken-Login
   + 2FA liegt beim Benutzer) oder das Warten, bis die echte Zeit den Peak
   einholt.

**Nonce-Logik IMMER in dem Uhren-Kontext testen, in dem die Sender laufen.**
Der Hermes-Terminal-Backend ist eine Docker-Sandbox, deren Uhr von der
Windows-Host-Uhr abweichen kann (gemessen >10 s bis zur Serverzeit, waehrend
der Host nur ~2-3 s voreilt). Ein nonce, der in der Sandbox "richtig"
aussieht, ist im Host-Kontext falsch. Messung und Signatur gegen die
**Kraken-Serverzeit** (`public/Time`) und die **Host-Uhr** ausfuehren, nicht
gegen die Sandbox-Uhr.

## Credentials: Stufe-0-Weg (nie Werte durch die Konversation)

Schluesseldateien (`MaxHirn\Wissen\OKX_API.env` und Co.) sind Stufe 0 — nie
lesen, ausgeben, protokollieren. Eintragen, ohne dass ein Wert die Sitzung
passiert:

```powershell
# Namen der Variablen im Log zeigen, Werte NIE ausgeben
foreach($zeile in [IO.File]::ReadAllLines($env_datei)){
  if($zeile -and -not $zeile.StartsWith('#') -and $zeile.Contains('=')){
    $t = $zeile.Split('=',2)
    if($t[0].Trim() -match '^OKX_'){
      [Environment]::SetEnvironmentVariable($t[0].Trim(), $t[1].Trim().Trim('"'), 'User')
      $namen += $t[0].Trim()
    }
  }
}
Write-Output ($namen -join ', ')   # nur Namen
```

Danach existierende Registry-Eintraege NUR als Namen + `[bool]$reg.$_` belegen
(`$reg.PSObject.Properties.Name`), nie die Werte.

## Spur auf andere Boerse duplizieren

1. Ordner komplett kopieren (ohne `.backup-*` und ohne `daten/`-Cache).
2. Nur die Datenquelle austauschen: `backtest.py`-Funktion ersetzen
   (Format-Mapping pruefen — okxf und kraken liefern beide
   `[ts_ms, o, h, l, c, vol]`, das passt; OANDA lieferte Diktate).
3. `wachen.json`-Instrumentenblock + `tests/test_wachen_json.py` anpassen;
   Test der alten Boerse (z. B. `test_keine_okx_reste`) mitziehen.
4. Cache-Dateinamen mit `/`-Sanierung (`paar.replace("/", "_")`).
5. Alle Tests im Spurordner, dann Backtest mit Cache — vorher Daten-Tiefe
   messen (aelteste Kerze), sonst 1-2 Sessions statt Urteil.
6. **Live bleibt gesperrt bis zum Backtest-Urteil** (`handel_erlaubt=false`,
   `instrument_aktiv=null`). Fuer einen PAPIER-Zyklus im Dauerlauf darf
   `instrument_aktiv` trotzdem gesetzt werden (z. B. `ETH_USD` fuer den
   Vorwaerts-Test) — `handel_erlaubt=false` ist die eigentliche Sperre, und
   ein handeln.py ohne Order-Calls kann ohnehin kein Geld bewegen. Den
   Backtest-Neubestand als Kommentar in `wachen.json` festhalten
   (`_backtest`-Feld), damit nicht erneut nach OANDA-Dateien gesucht wird.
7. Spur in `SPUREN` eintragen (Papier- oder Urteils-abhaengig), Neustart,
   ersten Zyklus im Log abwarten. Siehe SKILL.md: Rueckgabe-N-Diagnose und
   der zweite Zyklus als Ausstiegspfad-Test.


## Deribit — Optionsdaten und Volatilitaetsindex, oeffentlich, kein Schluessel

Basis `https://www.deribit.com/api/v2`. Der frei zugaengliche Ort fuer
Optionsdaten (Strike, offenes Interesse, Markt-IV) UND einen gehandelten
Volatilitaetsindex; OKX und Kraken liefern beides nicht. Alles ohne Token lesbar.

- `public/get_index_price?index_name=btc_usd` — Indexpreis.
- `public/get_volatility_index_data?currency=BTC&start_timestamp=&end_timestamp=&resolution=1D`
  — DVOL-Tagesreihe, Zeile `[ts, open, high, low, close]`, rund 400 Tage Tiefe.
- `public/get_tradingview_chart_data?instrument_name=BTC-PERPETUAL&resolution=60`
  — Kerzen als getrennte Felder `ticks/open/high/low/close/volume`.
  **Hoechstens 5000 Punkte je Anfrage** (ein Jahr Stundenkerzen = zwei Anfragen)
  — in Bloecken blaettern und ueber den Zeitstempel entdoppeln.
- `public/get_book_summary_by_currency?currency=BTC&kind=option` — je Instrument
  `open_interest`, `mark_iv`, `underlying_price`, `volume`. Kontraktname
  `BTC-<Verfall>-<Strike>-C|P`.

Fallen:
- **Offenes Interesse gibt es nur als Momentaufnahme, keine Historie.** Jede
  Rechnung, die Strikes nach OI auswaehlt, ist rueckwirkend NICHT pruefbar, nur
  vorwaerts. Das vor dem Bauen sagen, nicht nach dem Backtest entdecken.
- Strikes ueber ALLE Verfallstage summieren (ein Verfallstag allein ist zu duenn
  besetzt) und Strikes direkt am Kurs ausschliessen - das ist Hedge-Bestand, keine
  Wand.
- Deribit-Gebuehr ist NICHT 0: 0,05 % je Seite beim Taker. Anders als bei den
  uebrigen Spuren, wo ein Abo die Gebuehr traegt, gilt der 0-%-Satz hier nicht.

## Orderflow aus OKX (CVD, Taker-Volumen, Tape-Tiefe)

- Ein 4h-CVD kommt NICHT aus dem rohen Tape. /api/v5/market/history-trades liefert 100 Trades pro Anfrage; bei BTC-USDT-SWAP 28 s für
  vier Stunden wären rund 4000 Anfragen je Wert. Dieselbe Aussage mit einer
  Anfrage: /api/v5/rubik/stat/taker-volume-contract je instId, period=5m|15m|30m|1H|4H|1D, 100 Eimer pro Abruf, Zeile
  [ts, Verkaufsvolumen, Kaufvolumen] in Kontrakten wie die Kerzen. Vor dem
  Bauen einmal messen, wie viel Zeit das Tape deckt.
- Host-Falle bei /rubik/ mit instId: nur www.okx.com antwortet; my.okx.com und
  eea.okx.com liefern code=0 mit LEERER Liste (kein Fehler, stilles "kein
  Signal"). okxf.py: eigener Host RUBIK_BASIS, nicht OKX_BASE. OKX_BASE auf
  dieser Maschine zeigt auf my.okx.com (Web-Oberflaeche), nicht den API-Host.
- Rubik drosselt strenger: ein 429 kommt als OKXFehler('50011 Too Many
  Requests') und OKXFehler wird von _mit_wiederholung NICHT wiederholt. Jeder
  neue Abruf im Signalpfad faengt ihn selbst, wartet einmal kurz und faellt
  auf "kein Signal" zurueck mit Grund und benutztem Host in der Ausgabe.
  lage() laeuft je Zyklus je Spur; ein Datenabruf darf nie umbringen.
- Eine neue Komponente lage() bekommt das Instrument, nicht die Reihe:
  lage(k, ..., inst=<voller instId>, <name>_lage=<fertiges Ergebnis>), inst
  fuer den Abruf, das fertige Ergebnis fuer die Anzeige.

## Eine neue Fremd-API anbinden: erst messen, dann bauen

Gilt fuer jede Datenquelle, die neu in eine Spur kommt (durchgerechnetes
Beispiel: `references/santiment.md`). Die Reihenfolge verhindert den
Fehlschluss, „die API liefert nichts“ mit „meine Abfrage ist falsch“ zu
verwechseln.

1. **Die freie Stufe wird GEMESSEN, nicht aus der Doku geschlossen.** Ein Aufruf
   ohne Schluessel beantwortet „was geht heute“; die Doku nennt oft die bezahlte
   Stufe. Ergebnis mit Datum notieren.
2. **Schranken stehen in der Fehlermeldung der API, nicht im Handbuch** — und
   sie sind oft PRO KENNZAHL verschieden: dieselbe API erlaubt einer Metrik die
   Gegenwart und einer anderen nur Daten bis vor einem Monat. Die Grenze einmal
   aus der Antwort herauslesen und im Werkzeug abfragen, statt sie zu raten.
3. **Eine leere Reihe ist kein Fehler und kein Marktereignis.** Ausserhalb des
   erlaubten Fensters kommt HTTP 200 mit leerem Ergebnis. Wer das als „null
   Aktive Adressen“ liest, erfindet einen Absturz im Markt; leer heisst nur:
   falsche Frage fuer diese Stufe.
4. **Feldnamen aus dem mitgelieferten Schema, nie aus dem Gedaechtnis.** Gute
   Doku-Repos bringen das komplette Schema mit; geratene Feldnamen liefern leere
   Ergebnisse, die wie ein Datenproblem aussehen.
5. **Das Werkzeug hat eine Probe (`--probe`).** Sie ruft jeden noetigen Pfad
   einmal und meldet, wie viele geantwortet haben — damit ist „die Quelle traegt“
   ein Befehl statt einer Behauptung, und die naechste Sitzung sieht sofort, ob
   eine Stufe weggefallen ist.

## Kurs fuer Berichtszeilen: bare Symbole ⇄ instId

Positions-Zustaende speichern bare Symbole (`AAVE`, `HYPE`), aber
`okx.letzter_kurs()` will eine instId (`AAVE-USDT`) — ein direkter Aufruf mit
nacktem Symbol liefert Fehler/None, und der Bericht zeigt „(kein Kurs)“-Zeilen
mit rohen Floats.

- **Den Lookup in der ANZEIGE-Schicht fixen, nicht die Spur.** Varianten-
  Schleife probieren: Symbol, `Symbol-USDT`, `Symbol-USDC`, erster Treffer
  gewinnt, sonst `None`. Die Spur-Instanz umzubauen wuerde die Ausstiege der
  Bot-Spuren brechen: sie laufen ueber ihre eigene Quelle (CoinGecko) mit dem
  bare Symbol als Schluessel und waeren danach still ohne Kurs.
- **Strukturelle Luecken ehrlich als „(kein Kurs)“ stehen lassen und so
  kommentieren:** DAI hat auf OKX kein Spot-Paar (51001), FIGR_HELOC stammt
  aus der FTX-Zeit, ANT im Spiegel ist eine Feed-Datenluecke — keins davon ist
  ein Anzeigefehler, der einen Workaround vertraegt.
- **Test:** den Boersen-Lookup mocken und je Variantenstufe einzeln pruefen
  (erstes Mock liefert, zweites wirft → Fallback greift), letzte Stufe `None`.
