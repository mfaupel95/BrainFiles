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
- Schluessel: die gueltigen Hausvariablen sind **`KRAKEN_SPOT_API_KEY` /
  `KRAKEN_SPOT_API_SECRET`** (liest `kraken/kraken.py` UND der Kraken-MCP);
  OHLC/Ticker/AssetPairs sind ohne Schluessel lesbar. In `HKCU\Environment`
  liegt ZUSAETZLICH ein Paar `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` - es
  existiert, aber Kraken antwortet damit `EAPI:Invalid key`. **Ein Programm, das
  "Invalid key" meldet, waehrend ein anderes mit demselben Konto arbeitet, liest
  den anderen VARIABLENNAMEN, nicht einen falschen Schluessel:** erst den im
  Quelltext gelesenen Namen nachsehen, dann die generischen Namen aus den
  SPOT-Werten setzen (Wrapper `Agenten/Werkzeuge/kraken.ps1`).
- **Die Spot-Anbindung kann NUR kaufen/verkaufen: buy/sell, kein Short, kein
  Hebel.** `markt_kauf`/`markt_verkauf`/`stop_setzen` decken Long ab; ein
  Leerverkauf oder eine Position mit Hebel ist auf diesem Weg nicht machbar.
  Short-mit-Hebel ist **Margin-Trading** (eigener Margin-Schluessel mit
  Margin-Recht, freigegebenem Kontingent, `leverage`-Parameter, Margin-API,
  Nachschusspflicht) - ein anderer Pfad, kein Feature der Spot-Anbindung.
  Wer "Long UND Short" an einer Spur will, muss das als EIGENES Teilprojekt
  mit eigener Freischaltung planen, nicht als Erweiterung des vorhandenen
  Kraken-Spot-Wegs.

### Margin-Positionen liegen NICHT im Guthaben — und der Stop muss sie SCHLIESSEN

Wenn Positionen "auf Kraken" abgesichert werden sollen, sie aber in keiner
Bestandsliste auftauchen: **drei verschiedene Orte pruefen, in dieser
Reihenfolge** — Guthaben (`BalanceEx`, alle Waehrungen), offene
MARGIN-Positionen (`OpenPositions`, signiert) und erst danach die
Futures-Brieftasche (eigener Zugang). Gemessen: SUI, ZEC und NEAR waren weder in
`BalanceEx` noch im OKX-Konto, sondern als sechs SUIEUR-, eine NEAREUR- und eine
XZECZUSD-Margin-Position offen. **Aus "steht nicht im Guthaben" folgt nicht
"hat er nicht".**

`OpenPositions` gibt je Position: `vol`, `cost`, `margin`, `ordertxid`,
`posstatus`, `terms` (das ist die ROLLOVER-Gebuehr, z. B. `0.0200% per 4 hours` —
NICHT der Hebel) und `rollovertm`. Der Einstieg ist `cost / vol`.

- **Ein gewoehnlicher Verkaufsstop scheitert** (`EOrder:Insufficient funds`): die
  Stuecke gehoeren nicht der Brieftasche, sie sind geliehen/auf Margin gekauft.
- **Richtig ist die VERKNUEPFTE Schlussorder.** `AddOrder` mit
  `close[ordertxid]=<ordertxid der Position>`, `close[ordertype]=stop-loss`,
  `close[price]=<Preis>` PLUS die Hauptfelder (`type=sell`,
  `ordertype=stop-loss`, `volume=<Menge der Position>`, `price`, `leverage`).
  Kraken antwortet dann `descr.close = "close position @ stop loss ..."` und setzt
  das Flag `c` in `oflags` (`QueryOrders` zeigt beides). Wird die Position von
  Hand geschlossen, verschwindet der Stop mit ihr. **Ohne die Verknuepfung bleibt
  ein nackter Verkaufsstop stehen, der bei fehlender Position einen SHORT
  aufmacht** — der teuerste Fehler dieses Wegs.
- **Menge = Menge der POSITION, nie mehr** (sonst dreht der Rest short); der Hebel
  muss im Erlaubten des Paares liegen (`AssetPairs[paar].leverage_sell`; gemessen
  SUIEUR bis 10, NEAREUR bis 3, XZECZUSD bis 5). Fuer eine schliessende Order ist
  er Formsache — Hauptsache innerhalb der Grenze.
- **`validate=true` nimmt Kraken fuer alle diese Formen an.** Eine Probe kostet
  nichts und zeigt die Beschreibung, die Kraken versteht ("sell 30.694 SUIEUR @
  stop loss 0.8140 with 5:1 leverage" + "close position @ stop loss 0.8140") —
  vor jeder echten Order zeigen, was sie bewirkt.
- **Staub ist nicht orderbar:** liegt die Menge unter `ordermin`/`costmin` des
  Paares, wird die Position uebersprungen und GEMELDET (gemessen: 0,00000023 NEAR).
- **Ein Stop ueber dem Markt ist kein Schutz, sondern ein sofortiger Verkauf.**
  Liegt "Einstieg minus X %" ueber dem aktuellen Kurs (Einstieg ueber dem Markt),
  Position ueberspringen und den Grund nennen — nicht stillschweigend ordern.
- Diese Positionen gehoeren KEINER Spur: sie stehen in keinem Buch, keine
  Spiegelung kennt sie. Im Bericht als Konto-Zeile fuehren (Position, Menge,
  Einstieg, Stop, Kennung) und **keine Buchzeile erfinden** — der Abgleich
  Buch <-> Boerse darf sie nicht als "fehlend" zaehlen.
- Werkzeug: `Agenten/Handel/kraken/margin_stops.py` (Vorschau Standard,
  `--anwenden` ordert, `--prozent`); die Orderfelder haengen an
  `kraken.stop_setzen(..., leverage=..., close_txid=...)` — rueckwaerts
  kompatibel, alle bisherigen Aufrufer bleiben unveraendert.

### Dasselbe Paar, zwei Schreibweisen - nie roh vergleichen

Kraken nimmt in der Order-Anfrage `XXBTZEUR` / `XETHZEUR`, liefert in der offenen
Order (`/0/private/OpenOrders`, Feld `descr.pair`) aber die KURZE Form `XBTEUR` /
`ETHEUR`. Ein Abgleich Buch <-> Boerse ueber die rohen Zeichenketten findet die
Positionen dann nicht und haelt geschuetzte Positionen fuer ungeschuetzt (nur das
Paar ohne X/Z-Praefix, z. B. `SOLEUR`, passt). Beide Seiten auf (Basis, Quote)
zurueckfuehren: X/Z-Praefixe und Aliasse aufloesen, Quote-Kandidaten nach Laenge
absteigend probieren (`ZEUR` VOR `EUR`, sonst bleibt das `Z` am Basisnamen haengen),
dann vergleichen.

- `kraken.offene_orders()` (lesend, `/0/private/OpenOrders`) liefert
  `{txid: {paar, seite, art, menge, preis, eroeffnet}}` - damit ist der Schutz einer
  Position belegbar und die Kennung ins Buch nachtragbar
  (`mosaic/stops_nachziehen.py`, Vorschau Standard, `--anwenden` schreibt mit `.bak`
  und spiegelt). Ein Buch ohne Stop-Kennung kann den Stop spaeter nicht stornieren
  oder ersetzen - ein Waisen-Stop faellt niemandem auf.
- Ein Stop gehoert nur zu SEINER Position: Paar UND Menge muessen passen
  (Toleranz ~1 %, Boersen runden). Ein Stop ueber eine andere Menge ist nicht der
  Schutz dieser Position.
- **Eine fehlende Waehrung in der Kontoliste ist 0, kein Fehler.** Die
  Guthaben-Werkzeuge blenden Nullbestaende standardmaessig aus: fehlt `ZEUR` in der
  Antwort, ist das Guthaben 0 (und das Guthaben-Tor der Spur zu Recht zu), nicht der
  Abruf kaputt.

### Orderpreise: die Boerse rundet nicht, sie lehnt ab

Ein Order-/Stop-Preis muss auf die Nachkommastellen des PAARES gerundet sein,
sonst gibt es keinen Notausstieg: Kraken antwortet `EOrder:Invalid price:SOL/EUR
price can only be specified up to 2 decimals` und die Position steht ohne Stop da
(bei OKX heisst die Grenze `tickSz`). Je Paar verschieden (SOLEUR/XETHZEUR 2,
XXBTZEUR 1, AKEEUR 8, KASEUR 5).

- Runden **AUF** (Long-Stop nie tiefer als gerechnet) und das Ergebnis fertig
  formatiert zurueckgeben — `str(float)` schreibt sonst `1e-08`, und die Boerse
  liest das nicht als Zahl.
- Die Rundung gehoert in die EINE Funktion, die den Preis setzt
  (`kraken.stop_setzen`, `okx_spot.algo_stop_setzen`), nicht in jeden Aufrufer.
- **Ohne Geld pruefen:** bei Kraken `AddOrder` mit `validate=true` (rechnet
  durch, platziert nicht) — der gerundete Preis wird angenommen, der rohe nicht.
- **Nach einem fehlgeschlagenen Einstieg, der zurueckverkauft wurde, kann eine
  Order als WAISE stehenbleiben** (gesehen: eine Take-Profit-Verkaufsorder mit
  `vol 0` fuer ein Paar ohne Position). Nach jedem Rueckverkauf `OpenOrders` UND
  `orders-algo-pending` ansehen und den Befund als Konto-Zeile nennen, statt ihn
  zu verschweigen.

### Einen bestehenden Stop VERSETZEN: Kraken reserviert die Menge

- **Kraken reserviert die Menge eines Stop-Loss.** Ein zweiter Stop auf dieselbe
  Menge wird mit `EOrder:Insufficient funds` abgelehnt, obwohl die Position offen
  ist. Reihenfolge beim AENDERN: alten Stop stornieren -> neuen setzen -> und wenn
  das Setzen scheitert, den ALTEN sofort wiederherstellen. "Erst den neuen setzen,
  dann den alten stornieren" klingt sicherer und ist es nicht: scheitert der neue
  (z. B. an der Menge), steht die Position in der Zwischenzeit OHNE Stop da.
- **Das Buch fuehrt brutto, die Brieftasche netto.** Die Boerse schreibt den
  Netto-Zufluss gut (Gebuehr abgezogen): das Buch fuehrte 0,00066027 BTC,
  verfuegbar waren 0,0006527067. Ein Stop ueber die Buchmenge scheitert — und
  waehrend des Fehlversuchs ist die Position ungeschuetzt. **Stop-Menge =
  min(Buchmenge, verfuegbar), ABGERUNDET auf die Lotstellen** (`stop_menge()`);
  Aufrunden laesst die Order wieder scheitern.
- **`OpenOrders` zeigt einen frisch gesetzten Stop nicht sofort.** Die Abfrage
  direkt danach zaehlte 2 statt 3 Orders, eine Sekunde spaeter 3. Vor jeder
  Aussage "der Stop fehlt" ein zweites Mal fragen — und nie aus der Liste allein
  schliessen, dass eine Order abgelehnt wurde.
- **Nach dem Handgriff das Buch aus den OFFENEN Orders nachziehen, nicht neu
  ordern.** Ein zweiter `--anwenden`-Lauf wuerde den frisch gesetzten Stop
  stornieren und einen dritten setzen. Dafuer ein eigener Modus (`--nur-buch`):
  je Position Stop, Kennung und Menge aus `offene_orders()` uebernehmen, verglichen
  ueber (Basis, Quote) — sonst passt `XXBTZEUR` nicht auf `XBTEUR` und das Buch
  meldet "kein Stop an der Boerse", obwohl einer liegt.
- Ein Handgriff an echten Stops ist eine GELD-Aktion: erst rechnen und zeigen
  (`--vorschau`), dann ausfuehren, danach die offenen Orders als Beleg nennen
  (Kennung, Menge, Preis je Position).

**Wie eine Spur eine Order ABGIBT, statt sie selbst auszufuehren (Freigabe-Beleg
+ ausfuehrende Hand): `references/beleg-und-hand.md`.**

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

**Die EINHEIT des nonce ist die zweite Falle, und sie kommt von AUSSEN.** Kraken
vergleicht nur "groesser als der gemerkte Peak", unabhaengig von jeder Einheit -
wer in Mikrosekunden rechnet, ist gegen ein Werkzeug in NANOSEKUNDEN rund eine
Million Mal kleiner, und danach wird JEDE eigene Abfrage abgelehnt (gemessen: die
offizielle `kraken-cli` signiert in ns, ~1,78e18; nach EINEM Aufruf kam von der
ganzen Hausseite nur noch `EAPI:Invalid nonce`). **Regel: die eigene Nonce-Einheit
muss die GROESSTE sein, die irgendein Werkzeug auf denselben Schluessel sendet.**
Vor dem Anbinden eines zweiten Clients seine Einheit MESSEN (Sonde
`Agenten/Hermes/cache/kraken_nonce_sonde.py`) und den Pool heben -
`max(int(time.time()*1e9), letzter+1)`: `max()` haelt die Datei monoton, ein
Sprung nach OBEN ist harmlos, ein Wert darunter toedlich. **Das Symptom taucht
meist NICHT an der Spur auf, die den zweiten Client benutzt:** sichtbar wurde es
an der Live-Sperre einer ANDEREN Kraken-Spur ("Guthaben nicht abrufbar"), weil
dort der erste signierte Leseaufruf des Zyklus scheiterte. Also nie nur die Spur
pruefen, die umgebaut wurde.

**Zwei Fallen, die ein Pool NICHT loest — beide gemessen 2026-09-19:**
1. **Drift-Korrektur (nonce = Serverzeit statt Wallclock) macht es SCHLIMMER**
   und ist der falsche Weg. Sie senkt den nonce UNTER den von parallelen
   Sendern gesetzten Kraken-Peak → dauerhaft `EAPI:Invalid nonce`. Die einzige
   nachweislich funktionierende Erhebung war die monotone **Wallclock**
   (`max(time.time()*1e9, letzter+1)` — die 5/5-Sonde). Nicht "korrigieren",
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

## Kontostand und Orderlage lesen (signiert)

Drei getrennte Abrufe — nie einer fuer alle drei Fragen:

```bash
python -c "import okxf;b=okxf._roh('/api/v5/account/balance?ccy=USDC', signiert=True);d=b[0]['details'][0];print(d['eq'],d['availEq'],d['frozenBal'],d['isoEq'],d['stgyEq'])"
python -c "import okxf;print(len(okxf._roh('/api/v5/trade/orders-pending', signiert=True)))"
python -c "import okxf;print([(o['instId'],o['side'],o['slTriggerPx']) for o in okxf._roh('/api/v5/trade/orders-algo-pending?ordType=conditional', signiert=True)])"
```

- **`okxf._roh` gibt die Liste DIREKT zurueck** (kein `["data"]`-Mantel). Ein
  `.get('data')` darauf ist ein Attributfehler, kein leeres Ergebnis.
  **Diese drei Regeln gelten fuer BEIDE Module** — `okxf._roh` in `xperp/` und
  `okx._roh` in `scanner/` haben dieselbe Signatur und dieselbe Antwortform.
  Der Unterschied ist nur die Quelle: `okxf` liest FUTURES (`instType=FUTURES`,
  `XPERP`-Namen), `okx` liest SPOT. Wer die Signatur am einen Modul gelesen hat,
  traegt sie nicht ungeprueft auf das andere — dort kostet es drei Fehlversuche
  (ein Dict an erster Stelle, fehlendes `signiert=True`, POST statt GET auf
  einen Konto-Endpunkt), die alle drei wie „keine Daten" aussehen.
- **Kaufkraft ist `availEq`, nicht `eq`.** `frozenBal` zerfaellt in `isoEq`
  (Margin der isolierten Positionen **inklusive** `upl`) und `stgyEq`.
  Gemessen: `eq` 864, `frozenBal` 856, `availEq` 8,13 — eine Spur kann dabei
  „Live waere gesperrt durch: nichts" melden, weil ihre eigenen Tore offen sind;
  die Order scheitert dann erst am freien Betrag. Kaufkraft immer in der
  Waehrung nennen, in der bezahlt wird (Spot-USDC-Kauf und Perp-Margin liegen
  im selben Konto, `acctLv=2` rechnet je Waehrung).
- **`stgyEq` ist das GEWACHSTE Guthaben (Staking/Earn), nicht eine undokumentierte
  Reserve** — und es ist damit der Grund, warum ein Konto „viel Geld, aber nichts
  frei" zeigt. Gemessen: `eq` 406,87 USDC bei `stgyEq` 309,98 und `availEq`
  0,0047; nach dem Unstaken `availEq` 377,03. Wer den Wert als „Reserve"
  abtut, erklaert ein Guthaben-Tor zum Wunder. Die Staking-INSTANZEN selbst
  liefert die API auf dem EEA-Host nicht (die `finance/staking-defi`-Positions-
  und -Orderpfade geben 404) — **die Sperrfrist und der Zinsverlust sind damit
  nicht abrufbar**, das bleibt eine Kontohandlung des Benutzers. Ein Freimachen
  ist keine Zuweisung: die erste scharf geschaltete Spur nimmt es im selben
  Zyklus.
- **Der Aufruf: das erste Argument ist der PFAD, kein Body.** Signatur
  `_roh(pfad, methode="GET", body=None, signiert=False)` — ein Dict an erster
  Stelle bricht mit `TypeError: can only concatenate str (not "dict") to str` ab,
  und ohne `signiert=True` antwortet die Boerse `50103: OK-ACCESS-KEY can not be
  empty`.
- **GET-Parameter gehoeren in den PFAD, nicht in den Body.** Ein
  POST-Body auf einen Konto-Endpunkt liefert `50115: Invalid request type
  (HTTP 405)` — die Frage ist dann nicht „keine Daten", sondern „falsche Methode".
  Richtig: `'/api/v5/account/positions?instType=FUTURES'` mit `signiert=True`.
- **Bedingte Stops liegen unter `/api/v5/trade/`, nicht unter `/api/v5/account/`.**
  `/api/v5/account/orders-algo-pending` gibt **404** — und 404 auf diesem Pfad liest
  sich wie „keine Schutzauftrage vorhanden". Vor dem Befund den Pfad pruefen:
  `'/api/v5/trade/orders-algo-pending?ordType=conditional'`.
- **Bedingende Stops liegen NICHT in `orders-pending`,** sondern nur in
  `orders-algo-pending?ordType=conditional`. „0 offene Auftraege" ist damit
  keine Aussage ueber den Schutz einer Position (siehe
  `references/wartende-auftraege-belegen-platz.md`).
- **Das Buch ist der zweite Zeuge — und der schwaechere.** Eine Position ohne
  Orderkennung (`kauf_ord_id`/`ord_id`, bei aelteren Spuren das Feld `modus`)
  ist keine Position an der Boerse: sie belegt nur einen Platz und laesst jeden
  Ausstieg in einen Boersenfehler laufen. Vor jeder Aussage „die Spur haelt N
  Positionen" die Boerse fragen und die Live-Zeilen im Journal zaehlen.

### Fuellungen sind der Zeuge fuer JEDEN ausgefuehrten Verkauf

`positions-history` beantwortet „welches Ergebnis hatte diese Position",
**nicht** „zu welchem Kurs wurde verkauft" — dort steht `avgPx: None`. Der
Ausfuehrungspreis steht nur in `/api/v5/trade/fills`:

```python
fills = okxf._roh("/api/v5/trade/fills", signiert=True)   # Liste, kein data-Mantel
# je Zeile: instId, side (sell = Verkauf einer Long), fillSz, fillPx, ts, fillPnl
```

Ohne Zeitfilter liefert der Endpunkt die letzten 100 Fuellungen des Kontos ueber
ALLE Instrumente — darum erst je `instId` gruppieren, dann Zeitfenster und Seite
filtern. Fuer den Verkauf einer Long-Position ist `side == "sell"` die gesuchte
Zeile (ein `buy` schliesst eine Short). **Bei Verkauf in mehreren Wellen ist
der mengengewichtete Kurs aller Fuellungen die richtige Zahl**, nicht der letzte
Fill. Felder: `fillSz`, `fillPx`, `fillMarkPx`, `fillPnl`, `fee`, `side`,
`posSide`, `ts`, `ordId`, `tradeId` — **nicht** `sz` und nicht `fillSz` unter
beiden Namen verwechseln; ein Zugriff auf den falschen Namen trifft den
`KeyError`.

Ein Abgleich, der eine Position an der Boerse nicht mehr findet, hat mit diesem
Endpunkt die Wahl zwischen „Geist" (kein Verkauf bezeugt → neutral) und
„Verkauf" (bezeugt → echter Kurs). Ohne ihn bleiben beide Verkaeufe beim
Neutral-Buchen, und der Erloes fehlt in der Kapitalkurve. Befund und Rueckweg
stehen in `references/handgriffe-von-hand.md`.

### OKX WebSocket: die Kerzenkanaele liegen auf dem BUSINESS-Feed

Livestream statt Polling (Event-Trigger, Fuehrpreis-Vergleich). Die Reihenfolge
vor dem Bauen: erst eine 15-Sekunden-Sonde (connect + subscribe + erste Frames
ausdrucken), dann Code — sie verifiziert URL, Kanalname und Instrument in einem
Lauf.

- **`candle<bar>`-Kanaele liegen auf `wss://ws.okx.com:8443/ws/v5/business`,
  nicht auf `/public`.** Auf `/public` wirft JEDE Kerzen-Subscription
  `"event":"error" ... doesn't exist` — auch fuer BTC-USDT, waehrend `tickers`
  dort funktioniert. Wer auf `/public` baut, sieht nie Daten und wird nach
  30 s still getrennt (code 4004).
- **Die Marktdaten-Hosts sind GLOBAL.** Regions-Hosts wie `ws.eea.okx.com`
  loesen im DNS NICHT auf; oeffentliche Kerzen sind nicht konto-gebunden —
  EEA-Instrumente (BTC-USDC) subscriben sauber am globalen Business-Feed.
  Der Region-Host kommt erst ins Spiel, wenn ein PRIVATER Kanal gebraucht wird.
- **Business-Kerzen haben 9 Felder**, `[ts, o, h, l, c, vol, volCcy,
  volCcyQuote, confirm]`; `confirm` ist das LETZTE Feld (Index 8), `"1"` =
  abgeschlossene Kerze. Das REST-Format (6 Felder) ist es NICHT — ein
  Laengen-Check auf das alte Format verwirft jede echte Kerze still, der
  Konsument verhungert ohne Fehlerzeile.
- **Lebendigkeit: alle <30 s den TEXT `ping` senden** (Antwort `pong`).
  Kommt `4004 No data received in 30s` TROTZ versendeter Pings, ist der
  echte Grund fast immer eine GESCHEITERTE Subscription (es kam nie `data`)
  — dann nach `"event":"error"` in den Frames suchen, nicht den Ping-Loop
  debuggen. Eine Subscription bestaetigt sich je Instrument mit
  `"event":"subscribe"`; fehlen die Bestaetigungen nach Sekunden, war sie falsch.
- `websocket-client`-Fallen: `run_forever(ping_interval=0)` verlangt trotzdem
  `ping_timeout > 0`, sonst wirft es sofort `WebSocketException` (eigenen
  Text-Ping-Thread nutzen und den Bibliotheks-Ping abschalten); ein `import sys`
  INNERHALB eines Zweigs macht `sys` fuer die GANZE Funktion lokal — der erste
  Zugriff davor bricht mit `UnboundLocalError`.
- **Ein Ereignis-Trigger, der die Spur-Logik frueher ruft, ist ein ZUSATZ-Prozess,
  kein Ersatz:** Sperrenkette unangetastet, der Zyklus bleibt Rueckfallebene,
  jede Trigger-Buchung traegt ihre Herkunft im Journal (`herkunft=trigger` vs
  `zyklus`), sonst ist der Fuehrpreis-Vergleich zwei Wochen spaeter unlesbar.
  Ein Papier-Trigger neben einer LIVE-Spur ist sicher, weil
  `pruefe_ausstiege(z, live=False)` echte Positionen stehen laesst und nur
  meldet — vorher pruefen, nicht annehmen.

## Kraken Futures (futures.kraken.com) — Einheiten, die man nicht raten darf

Der Ticker `/derivatives/api/v3/tickers` ist oeffentlich (kein Schluessel) und
traegt Funding UND offenes Interesse — aber in Einheiten, die eine
Cross-Venue-Rechnung (z. B. ein Carry-Scanner) still falsch machen, wenn man
sie aus der Doku oder dem Namen raet. Gemessen 07.10.2026 an PF_XBTUSD:

- **`fundingRate` ist ein ABSOLUTER Betrag in der Kontraktwaehrung, keine
  Rate.** BTC meldete 2,19 auf ~83.400 = 0,0026 % — als Bruch gelesen waere
das 219 % je Zyklus und ein „extremes Funding", das es nicht gibt. Die
vergleichbare Zahl ist **`relativeFundingRate`** (Rate relativ zum Spot,
~2,6e-05). Fuer einen Funding-Vergleich IMMER `relativeFundingRate` nehmen,
nie `fundingRate`.
- **Kraken nennt KEIN Funding-Intervall.** Die API-Doku und Nautilus
  ("does not specify a fixed funding period") geben es nicht her; die
  historische Funding-API (`/derivatives/api/v3/historicalfundingrates`)
  antwortet fuer PF_-Symbole mit 404. Eine annualisierte Kraken-Funding-Zahl
  ist damit GERATEN — als relative Rate JE ZYKLUS ausweisen und die
  Jahreszahl weglassen, statt ein Intervall zu erfinden. (OKX nennt sein
  Intervall: 3 Zyklen/Tag, annualisierbar.)
- **`openInterest` ist in KONTRakten (je 1 Einheit der Basis), nicht in
  USD.** BTC 2.309 Kontrakte = ~192 Mio USD, nicht "2.309 USD". Ein
  Duenn-Check muss Kontrakte x Preis rechnen, sonst gilt jeder PF_-Markt als
  duenn.
- **`fundingRateCoefficient: 8` in `/derivatives/api/v3/instruments` ist
  KEIN Intervall in Stunden** — es ist ein Koeffizient der Funding-Formel.
  Nicht als Periodenlaenge deuten.

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

### Zwangsschluesse (Liquidationsbaender) — der Strom zeigt die Vergangenheit

- **Der oeffentliche Strom ist ein Ausschnitt, kein Bestand.** `/api/v5/public/
  liquidation-orders` liefert nur die letzten ~100 Eintraege; gemessen deckten die
  100 Eintraege 1,8 bis 14,7 Minuten ab, der juengste war 0,6 bis 26 Minuten alt.
  Wer "die Wand der letzten Stunde" rechnet, rechnet auf Minuten — die Zeitspanne
  des Abrufs vor der Deutung messen und im Bericht mitnennen.
- **Die SEITE eines Bandes ist die Richtung des letzten Laufs, keine Eigenschaft
  des Bandes.** Longs werden beim FALLEN liquidiert, Shorts beim STEIGEN; in
  beiden Messungen waren 100 von 100 Liquidationen Longs. Eine short-liquidierte
  Wand, die eine Long-Spur braucht, existiert nur mitten in einem Aufwaertsimpuls.
- **Ein Band entsteht dort, wo der Kurs GERADE WAR.** Das groesste Band lag 0,25 %
  UEBER dem Spot und bestand ganz aus liquidierten Longs: die Verkaeufe sind
  durch das Band gelaufen, der Kurs war schon darunter. Eine Regel "die Wand muss
  VOR dem Kurs liegen (in Handelsrichtung)" ist damit fast nie erfuellbar — die
  Spur meldet "falsche Seite" und schweigt, obwohl der Cluster real ist.
- **Richtig ist eine Toleranz HINTER dem Kurs** (`hinter_dem_spot_prozent`, 0,5 %):
  der Cluster zaehlt als Beschleuniger, auch wenn er knapp hinter dem Kurs sitzt;
  die Entfernungsgrenze (`max_abstand_prozent`) bleibt der Deckel, `0` stellt die
  strenge Fassung wieder her. Die These bleibt "MIT dem Cluster", nur die
  Lageanforderung wird weicher — eine Liquidationswand ist ein Beschleuniger, kein
  Widerstand.
- Eine Wache, die "falsche Seite" meldet, ist eine LAGEaussage, kein Fehler: sie
  sagt, dass der Impuls vorbei ist. Beim Nachmessen Abstand UND Masse mitdrucken
  (Sonde `liq_wand/probe_seiten.py`), sonst ist "falsche Seite" nicht von "Daten
  fehlen" zu unterscheiden.

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
