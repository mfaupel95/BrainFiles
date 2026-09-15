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
