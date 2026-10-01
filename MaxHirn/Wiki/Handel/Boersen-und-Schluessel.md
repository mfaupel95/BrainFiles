---
id: 20260921-boersen-und-schluessel
title: 'Handel — Boersen und Schluessel'
tags: [handel, zugaenge]
created: 2026-09-21
updated: 2026-09-30
related: ['[[Handel/Gates-und-Freigabe]]', '[[Wissen/Zugaenge]]']
summary: 'Welcher Schluesselsatz zu welcher Boerse und welcher Spur gehoert, was die OKX-Fehlercodes bedeuten — ohne jeden Schluesselwert.'
---

# Boersen und Schluessel

**Hier stehen keine Werte und keine Wertteile.** Werte liegen ausschliesslich in
`Wissen/Zugaenge.md` (Stufe 0: nie lesen, nie ausgeben, nie protokollieren) bzw. in den
Windows-Benutzervariablen.

## OKX

- Max' Konto ist **EEA**: `OKX_BASE=https://eea.okx.com`. NICHT `www.okx.com`, NICHT
  `my.okx.com` (= Portal-Host).
- **Je Spur ein anderer Variablensatz** — die falsche Variable zu aendern wirkt nicht:
  `xperp` und `mosaic` lesen `OKX_API_KEY` / `OKX_SECRET` / `OKX_PASSPHRASE`;
  `scanner` liest `OKX_LIVE_API_KEY` / `…_SECRET` / `…_PASSPHRASE`.
  Die okx-Module lesen die Werte mit Registry-Rueckfall (der MCP-Client reicht
  Benutzervariablen **nicht** an Serverprozesse durch).
- `OKX_SIMULATED=1` erzwingt den Papier-/Demo-Modus — fuer echtes Live muss die Variable weg.
- **Margin ist USDC, nicht USDT.** Gemessen: `/api/v5/account/positions?instType=FUTURES`
  zeigt `mgnMode=isolated, ccy=USDC`; eine Abfrage mit `ccy=USDT` liefert eine **leere** Liste
  — auf dem Konto gibt es gar kein USDT (USDC ~1001 eq / ~255 frei, EURC 15,99, Kleinstreste).
  `xperp/okxf.guthaben_usdt()` lieferte deshalb 0.0 und gibt bei leerem USDT jetzt das freie
  USDC zurueck. **Wer eine Finanzierungsaussage trifft, prueft die Margin-Waehrung der
  POSITION, nicht den Namen der Waehrung im Kopf.**

### Fehlercode 50101

`APIKey does not match current environment` = der Schluessel gehoert zu einem anderen Host
oder einer anderen Umgebung: EEA vs. global, Demo-Key, oder fehlende IP-Whitelist.
**Pruefen mit einem signierten LESEaufruf (`guthaben`, `offene_orders`) gegen den
Registry-Host** — nie gegen einen geratenen Host. Stand 21.09.2026 lieferte der xperp-Satz
50101; echte Orderfaehigkeit ist damit ungeklaert, obwohl das Konto den Handel zulaesst.

### Fehlercode 50014 / 51400 — Storno einer Algo-Order

**Regel: jedes `cancel-algos` schickt `instId` mit.** OKX verlangt beim Abbestellen eines
Conditional-Stops das Instrument; ohne es kommt `50014 Parameter instId can not be empty`,
und der Stop laesst sich **nie** abbestellen. Gemessen am 23.09.2026 am EEA-Host:

| Aufruf | Antwort |
|---|---|
| `cancel-algos` nur mit `algoId` | `50014 Parameter instId can not be empty` |
| `cancel-algos` mit `algoId` **und** `instId` | `51400 … has been filled, canceled or does not exist` (bei einer Attrappen-Kennung) |

`51400` heisst **erledigt, nicht Fehler**: der Stop ist gefuellt, storniert oder existiert
nicht mehr. Wird es als Fehler behandelt, bleibt der Merker fuer immer liegen und der
Live-Lauf meldet jede Runde „offener Stop … bleibt liegen". Genau das war der Befund:
`scanner/zustand.json` trug 23 Kopien desselben Stops (3940642343922589696), entstanden
beim Ziel-Ausstieg von ZEC-USDC am 22./23.09., solange der Verkauf zusaetzlich am
falschen Host scheiterte (`50119`, siehe `_live_basis`).

Nachweis: `Agenten/Handel/scanner/okx.stop_stornieren(algo_id, inst)` +
`handeln.raeume_offene_stops` (Dedupe, fehlendes `inst` wird lesend nachgeholt);
Tester `scanner/tests/test_okx_stornieren.py`; Bestandsaufraeumer
`scanner/stops_bereinigen.py` (Vorschau Standard, `--anwenden`, `--stornieren`).
Gegenprobe: Probe-Zustand mit 23 Kopien → `23 -> 0`, Positionen unveraendert,
Buch gegen Boerse 5/5 (`/api/v5/trade/orders-algo-pending?ordType=conditional`).

## Kraken

- Zugang ueber `Agenten/Handel/kraken/kraken.py`; Variablen `KRAKEN_*`. Ordern mit
  `echt=True` moeglich, `validate=True` rechnet nur durch (Trockenlauf).
- Kraken-Pro-Abo: Kauf+Verkauf bis 10.000 EUR Monatsvolumen gebuehrenfrei → `gebuehr_taker: 0`
  in `kraken/wachen.json`. Siehe [[Handel/Kosten-und-Bedingungen]] fuer das Risiko daran.
- **Zweite Boerse fuer dieselbe Spur** (Muster, 21.09.2026): `mosaic/kraken_spot.py` stellt
  dieselben Funktionsnamen bereit wie `okx_spot.py` und ruft dahinter `kraken/kraken.py`;
  `handeln.venue_binden(w)` waehlt das Modul ueber das Feld `boerse` (Standard okx) und bindet
  die Test-Seams neu — **VOR** der ersten Sperrenpruefung. Paarabildung EINMAL in
  `kraken_spot.PAARE` (BTC-USDC→XXBTZEUR, ETH-USDC→XETHZEUR, SOL-USDC→SOLEUR); unbekanntes
  Paar = `ValueError` (nie still ersatzweise handeln). Die wachen-Instrumente bleiben in
  OKX-Namen, damit Kerzen und Papierzweig unberuehrt bleiben.

## Deribit

`iv_waelle` liest die oeffentlichen Deribit-Endpunkte (Daten, kein Schluessel). Gebuehr in
der eigenen `wachen.json` auf 0,05 % — bewusst NICHT 0.

## OKX-Optionsdaten (oeffentlich, ohne Schluessel)

- `/api/v5/public/open-interest?instType=OPTION&uly=BTC-USD` — `oi`/`oiCcy`/`oiUsd` JE OPTION
  in EINEM Aufruf.
- `/api/v5/public/opt-summary?uly=BTC-USD` — `markVol` (= IV) je Option.
- **Nicht verfuegbar:** OI ueber Rubik (`/rubik/stat/option/open-interest-volume-strike` →
  `expTime`-Fehler in jedem probierten Format) und OI in `opt-summary`.
- Strike/Verfall/Art stehen in der `instId` (`BTC-USD-260925-79000-C`). OKX-Verfall ist
  **08:00 UTC**. Spot ueber `okx.letzter_kurs(inst)` — die Funktion heisst NICHT `okx.kurs()`.
- `/api/v5/market/candles` gibt oeffentlich nur **1440 Stundenkerzen** (60 Tage), egal was man
  anfordert.

## Schluessel gefunden, HOST nicht — OKX 50119 (23.09.2026)

Der scanner scheiterte eine Nacht lang bei **jedem** Verkauf: `OKX 50119: API key doesn't
exist (HTTP 401)`. Der Schluessel war gesund — der **Host** war falsch.

- `okx.py` suchte den Schluessel mit **Registry-Rueckfall** (`_variable`), den Host aber nur in
  der **Prozessumgebung** (`_env`). Ein Kindprozess, der die Windows-Benutzervariablen nicht
  geerbt hat (aus einem MCP-Server oder einer geplanten Aufgabe gestartet), fand also den
  EEA-Schluessel ueber die Registry — und signierte damit gegen `www.okx.com`. Genau das gibt
  50119/50101. Denken und messen: probeweise mit `env -u OKX_BASE` starten.
- **Merksatz: Schluessel und Host gehoeren zu EINEM Zugang.** Wer einen von beiden mit
  Rueckfall liest, muss den anderen genauso lesen. `xperp/okxf.py` und `mosaic/okx_spot.py`
  hatten den Rueckfall laenger, `scanner/okx.py` fehlte er — jetzt alle drei gleich.
- Die Meldung nennt seit dem Fix beide Seiten (`spricht <url> an, OKX_BASE aus der Registry ist
  <url>`), sonst sucht man den Fehler wieder beim Schluessel.

**Zweiter Befund derselben Nacht:** `_live_verkauf` bestellt ZUERST den Notausstieg ab (sonst
blockiert er den Bestand). Scheitert der Verkauf danach, stand die Position **ohne Stop** an der
Boerse, bis der naechste Zyklus es erneut versuchte — ZEC stand so bei +19 % ueber Nacht ohne
Schutz. `_schutz_zurueck()` legt den Stop jetzt mit der echten Fuellungsmenge wieder an (ein
alter, nicht stornierbarer Stop bleibt unberuehrt; ohne Stop-Preis wird gemeldet, nicht geraten).
Ein fehlgeschlagener Verkauf ist ein halber Vorgang — der halbe Zustand muss zurueckgenommen
werden.

## Zwei Boersen fuer EINE Spur (23.09.2026, mosaic)

Ein Auftrag von Max („gerne auf okx und kraken") heisst nicht zwei Spuren, sondern eine Spur mit
einer **Boersenliste**:

- `wachen.json`: `"boersen": ["kraken", "okx"]` — die Reihenfolge ist der **Vorrang**.
  `venue_binden()` nimmt die erste Boerse, die **einsatzbereit** ist: Schluessel vorhanden,
  kein Demo-Modus, mindestens `mindest_guthaben` **in der Waehrung dieser Boerse** frei
  (`guthaben_waehrung_je_boerse`). Ist keine bereit, bleibt es bei der ersten — die
  Sperrenkette nennt dann deren Grund, damit im Bericht nicht drei Gruende stehen.
- **Das Guthaben ist die Waehrung der Boerse, nicht des Kontos im Kopf.** Kraken handelt in
  EUR, OKX-Spot gegen USDC. Ein einzelnes `guthaben_waehrung: "EUR"` haette OKX nach EUR
  gefragt und ewig gesperrt.
- **Jede Position traegt ihr `boerse`-Feld**, und der Ausstieg laeuft ueber die Boerse, an der
  sie liegt (`venue_fuer_position()`) — nicht ueber die, die gerade gewaehlt ist. Ohne das
  verkauft eine Kraken-Position ueber den OKX-Weg ins Leere.
- **Einzelboerse bleibt eine Netzabfrage aermer:** die Bereitschaftspruefung laeuft nur bei
  mehreren Boersen. Sonst waere jeder Zyklus ein signierter Aufruf mehr.
- Gemessen 23.09.2026: Kraken 96,81 EUR frei (handelt), OKX 0,03 USDC frei (faellt durch das
  60er-Tor). Derselbe Schluesselsatz, der die Position oeffnet, muss sie auch schliessen
  koennen — beide Wege werden vorher mit `validate=true` geprueft.

## Kraken-Flotte (nicht verwechseln)

`kraken` (Spot-Spur, EUR) · `nautilus_kraken` / `nautilus_kraken_futures` (Papier-Arme,
nautilus-venv) · `moondev_marktlage.live_kraken.py` (abgetrennter Live-Zweig, nicht verdrahtet)
· `kraken_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` (Fremd-Bot, eigener Treiber
`MaxHirn-MoonDev-Dauerlauf`).

## Dasselbe Paar, zwei Schreibweisen (Kraken)

Ein Abgleich BUCH gegen BOERSE darf die Paarnamen nicht roh vergleichen. Kraken
nimmt in der Order-Anfrage `XXBTZEUR` / `XETHZEUR`, liefert in der offenen Order
(`/0/private/OpenOrders`, Feld `descr.pair`) aber die kurze Form `XBTEUR` /
`ETHEUR`. Gemessen am 24.09.2026 beim Nachtragen der Stop-Kennungen in mosaics
Buch: von drei Positionen passte nur `SOLEUR` - BTC und ETH sahen aus wie
ungeschuetzte Positionen, obwohl an der Boerse ein Stop lag. Beide Seiten auf
(Basis, Quote) zurueckfuehren (X/Z-Praefixe und Aliasse aufloesen), dann
vergleichen. Das Werkzeug dafuer ist `mosaic/stops_nachziehen.py`, die
Erkennung frieren 7 Tests ein.

## `EAPI:Invalid nonce` heisst nicht "unsere Werte steigen nicht"

Kraken vergleicht die nonce gegen den HOECHSTEN Wert, den es je Schluessel
gesehen hat. Der gemeinsame Pool (`kraken/nonce_pool.py`) haelt die eigenen
Werte streng steigend - aber sobald ein Werkzeug auf DENSELBEN Schluessel einen
hoeheren Wert sendet (die offizielle `kraken-cli` signiert in Nanosekunden aus
ihrer eigenen Uhr), ist jeder Pool-Wert darunter und Kraken lehnt ab, bis die
Uhr den fremden Wert eingeholt hat. Ein Wiederholversuch mit demselben Wert
hilft dann nicht. Richtig: `nonce_pool.vorwaerts(sekunden)` schiebt den
gemeinsamen Zaehler in der DATEI vor (sonst waere der naechste normale Aufruf
wieder zu niedrig), und `kraken._roh_privat` wiederholt bei "Invalid nonce" bis
zu dreimal mit vorgeschobenem Wert. Symptom, an dem man es erkennt: derselbe
Aufruf gelingt eine Minute spaeter wieder, ohne dass sich am Code etwas
geaendert hat.

## Ein Stop-Loss reserviert die Menge - und das Buch fuehrt brutto

Handgriff 24.09.2026 (Kraken-Stops der mosaic-Positionen von 5 % auf 7,5 %
gestellt, Werkzeug `Agenten/Handel/mosaic/kraken_stops_7_5.py`):

* **Kraken reserviert die Menge eines Stop-Loss.** Ein zweiter Stop auf dieselbe
  Menge scheitert mit `EOrder:Insufficient funds` - "erst neuen Stop setzen,
  dann den alten stornieren" ist damit unmoeglich. Richtig ist: alten Stop
  stornieren, neuen setzen, und wenn das Setzen scheitert, den alten SOFORT
  wiederherstellen.
* **Das Buch fuehrt die Buchmenge, die Brieftasche den Netto-Zufluss.** Gemessen:
  Buch 0.00066027 BTC, verfuegbar 0.0006527067 (die Gebuehr ging vom Zufluss ab).
  Ein Stop ueber die Buchmenge scheitert - und waehrend des Fehlversuchs stand
  die Position OHNE Stop da. Deshalb gilt: Stop-Menge = min(Buchmenge,
  verfuegbar), ABGERUNDET auf die Lotstellen (`stop_menge()`).
* Der Handgriff laeuft in drei Schritten: `--vorschau` (rechnen),
  `--anwenden` (ordern), `--nur-buch` (Buch aus den OFFENEN Orders nachziehen,
  ohne zu ordern). Nach einem Handgriff NIE einfach `--anwenden` erneut laufen
  lassen - das wuerde den frisch gesetzten Stop wieder stornieren.
* Ein frisch gesetzter Stop erscheint in `OpenOrders` **nicht sofort** (die
  Abfrage direkt danach zeigte 2 statt 3 Orders). Vor jeder "Stop fehlt"-Aussage
  eine zweite Abfrage machen.

## Eine Margin-Position liegt NICHT in der Brieftasche

Gemessen 24.09.2026, als SUI, ZEC und NEAR "auf Kraken" abgesichert werden
sollten (Auftrag Max) und im Guthaben nicht zu finden waren:

* `BalanceEx` zeigte kein SUI, kein ZEC, kein NEAR - die drei lagen als
  **offene Margin-Positionen** in `OpenPositions` (6x SUIEUR, 1x NEAREUR,
  1x XZECZUSD, dazu ein Staubrest). Wer nur das Guthaben liest, schliesst
  falsch "hat er nicht". **Erst Guthaben, dann `OpenPositions`, dann die
  Brieftasche der Futures** - drei verschiedene Orte.
* `OpenPositions` gibt je Position: `vol`, `cost`, `margin`, `ordertxid`,
  `terms` (Rollover-Gebuehr, NICHT der Hebel - SUIEUR 0,02 % je 4 h) und
  `posstatus`. Der Einstieg ist `cost / vol`.
* Ein gewoehnlicher Verkaufsstop scheitert bei einer Margin-Position
  (`EOrder:Insufficient funds`): die Stuecke gehoeren nicht der Brieftasche.
* **Richtig ist die verknuepfte Schlussorder:** `AddOrder` mit
  `close[ordertxid]=<ordertxid der Position>`, `close[ordertype]=stop-loss`,
  `close[price]=<Preis>` plus die Hauptfelder (`type=sell`,
  `ordertype=stop-loss`, `volume=<Menge der Position>`, `price`, `leverage`).
  Kraken antwortet dann `"close": "close position @ stop loss ..."`, die Order
  traegt das Flag `c` in `oflags` - und wenn die Position von Hand geschlossen
  wird, verschwindet der Stop mit ihr. **Ohne die Verknuepfung bleibt ein
  nackter Verkaufsstop stehen, der bei fehlender Position einen SHORT
  aufmacht.**
* Die Menge ist die der Position, nie mehr (sonst dreht der Rest short); der
  Hebel muss im Erlaubten des Paares liegen (`leverage_sell` aus `AssetPairs`;
  SUIEUR bis 10, NEAREUR bis 3, XZECZUSD bis 5). Fuer eine schliessende Order
  ist er nur Formsache.
* `validate=true` nimmt Kraken fuer ALLE diese Formen an - eine Probe kostet
  nichts und zeigt die Beschreibung, die Kraken versteht.
* Werkzeug: `Agenten/Handel/kraken/margin_stops.py` (Vorschau Standard,
  `--anwenden` ordert). Nachweis: 8 Stops gesetzt, alle mit
  `close position @ stop loss` in `QueryOrders` bestaetigt.

## Kraken Futures ist ein eigener Dienst (24.09.2026)

Futures ist NICHT die Spot-API mit anderem Host. Eigene Basis, eigene
Signatur, eigene Schluessel:

* Basis `https://futures.kraken.com/derivatives/api/v3`, Kopf
  `APIKey`/`Nonce`/`Authent`.
* `Authent = base64(HMAC-SHA512(base64decode(secret), SHA256(postData +
  nonce + "/api/v3" + pfad)))`. **Der Signaturpfad traegt KEIN
  "/derivatives"** - mit dem vollen Pfad antwortet Kraken
  `Authentication error`. Pfad und Aufrufpfad sind zwei verschiedene Dinge.
* Schluessel `KRAKEN_FUTURE_API_KEY`/`KRAKEN_FUTURE_API_SECRET` (HKCU) -
  die Spot-Schluessel gelten hier nicht und umgekehrt. Wer nur einen liest
  oder den Host raet, bekommt "Invalid key", obwohl der Zugang lebt.
* **Kein Koerper am lesenden Aufruf.** Ein GET mit `data=b""` wird zum POST
  und laeuft in `HTTP 404 NOT_FOUND` (auch das sieht wie ein Rechteproblem
  aus, ist aber keins): Lesen = GET ohne Koerper, Ordern = POST mit Formkoerper.
* Einheiten: Die Order nimmt KONTRAKTE. Bei `PF_XBTUSD` ist contractSize 1,
  also 1 Kontrakt = 1 USD Nominal; BTC-Menge x Kurs = Kontraktzahl, tickSize 1.
* Ausstieg und Schutz-Stop gehoeren als **`reduceOnly`** abgeschickt
  (orderType `stp` mit `stopPrice`) - sonst eroeffnet ein Ausstieg eine neue
  Position auf der Gegenseite.
* Besicherung kommt aus dem CASH-Konto der Futures-Boerse: ohne freies USD
  ist jede Order abgelehnt. Ein Coin-Bestand in `fi_<coin>usd` hilft nicht.
  Am 24.09.2026: USD 0.00 - der Weg ist gebaut, aber nicht fahrbar.

Umsetzung: `Agenten/Handel/nautilus_kraken/kraken_futures.py`; der Live-Zweig
ruft weiterhin `kraken_rest`, das per `KRAKEN_PRODUKT=futures` das
Futures-Modul laedt. Nachweis: signierte Leseaufrufe gruen, PF_XBTUSD 84385,
Stop 78000.4 -> 78001, 24 Tests gruen.

## Ein geschlossener Margin-Trade laesst seinen Stop zurueck (24.09.2026)

Wird eine Margin-Position geschlossen, **loescht Kraken den zugehoerigen
Stop-Loss NICHT**. Der Stop bleibt `open`, steht weiter in `OpenOrders` und
sieht in der Oberflaeche aus wie eine offene Position - ein Schliessversuch
scheitert dann ohne Bestand und ohne Position (`OpenPositions` ist leer).
Das war die Antwort auf "warum kann ich SUI/EUR nicht schliessen": die
Position war um 21:30/21:55/23:39 zu 0,8937-0,8997 EUR verkauft (Einstiege
0,84/0,88), offen lagen nur noch die Stops.

Ein solcher Waise ist nicht harmlos: ein Margin-SELL-Stop ohne Long-Position
verkauft, was nicht da ist - beim Ausloesen entsteht ein **SHORT**. Am
24.09.2026 waren es 7 Waisen mit rund 940 EUR Nominal (5x SUIEUR 615 SUI
@0,777/0,814, ZECUSD 0,1834 @1410,4, NEAREUR 31,19 @3,5591) bei 500 EUR
freier Margin - sie haetten wirklich geordert.

Werkzeug: `Agenten/Handel/kraken/waisen_stops.py` (Vorschau Standard,
`--stornieren`). Wache: Cron `waisen-wache` (30 min, no_agent, Telegram)
meldet neue Waisen sofort und dieselben hoechstens alle 6 h - sie storniert
**nie**, ein Waechter mit Loeschrecht an einem echten Konto ist selbst ein
Risiko.

Zweite Falle derselben Nacht: `OpenOrders` traegt die TXID im **Schluessel**,
nicht im Wert. Mit `o.get("txid")` kam eine leere Kennung heraus und Kraken
antwortete `EOrder:Invalid order` - storniert war dabei nichts.

## WAISEN-STOPS BEI OKX - MILDER, ABER DASSELBE MUSTER (25.09.2026)

Dieselbe Klasse wie bei Kraken (siehe oben): eine Schutz-Order bleibt stehen,
wenn ihre Position oder ihr Bestand verschwunden ist. Bei OKX ist der Schaden
kleiner und die Erkennung anders:

* **Spot** (`tdMode=cash`): mehr als der Bestand laesst sich nicht verkaufen,
  ein zu grosser Stop ist harmlos. Gefaehrlich ist nur, dass der Stop den
  Bestand **sperrt** (Reservierung) - ein manueller Verkauf scheitert dann.
* **Perp/XPERP** (`tdMode=isolated` oder `cross`) mit `reduceOnly=true`:
  OKX schliesst hoechstens, stockt nie auf. Ein Stop, der groesser ist als die
  Position (Befund: MON-USD_UM_XPERP 4143 gegen 2985), ist damit **kein** Risiko,
  nur eine Notiz ("ueberdeckt").
* Bei **Kraken-Margin** ist es anders: ein Sell-Stop ohne Long-Position ist ein
  echter Auftrag und eroeffnet beim Ausloesen einen **SHORT**. Deshalb dort Alarm,
  hier Notiz.

Werkzeuge (25.09.2026):
`Agenten/Handel/okx_waisen.py` (Vorschau storniert nichts, `--stornieren` fasst
nur Waisen an) und `Agenten/Handel/kraken/waisen_stops.py`. Beide werden von der
Wache `waisen-wache` (Cron, 30 min, no_agent) **je Boerse getrennt** aufgerufen;
ein Messfehler der einen Boerse wird gemeldet, statt die andere zu verdecken.

**Lehre:** Eine Kennzahl ohne ihre Boerse ist wertlos - "Stop groesser als
Position" heisst bei OKX (reduceOnly) harmlos und bei Kraken-Margin lebensgefaehrlich.
Vor jeder Alarmstufe die Mechanik des jeweiligen Handelsplatzes pruefen.
## Das Futures-Guthaben liegt im flex-Konto, nicht im cash-Konto (25.09.2026)

Gemessen am echten Konto, nachdem Max Geld auf das Kraken-Futures-Konto gelegt
hatte: `/derivatives/api/v3/accounts` antwortet mit BEIDEN Kontenformen -

- `accounts.cash.balances` = alles 0,0 (die alte Form),
- `accounts.flex` = `availableMargin` 141,5931, `balanceValue` 141,9984,
  `currencies` mit USD 8,8926, EUR 45,7427, USDC 81,0838,
  `type: multiCollateralMarginAccount`.

`kraken_futures.guthaben()` las nur `cash.balances` und meldete deshalb **0,0 USD**,
obwohl 141,59 USD verfuegbar waren: das Guthaben-Tor der Spur war dauerhaft zu -
ohne Fehlermeldung, ohne Absturz, ohne Logzeile. Jetzt liest es flex zuerst
(`availableMargin` bzw. `currencies.<CCY>.available`) und cash nur als Rueckfall
fuer reine Cash-Konten.

**Lehre:** Ein Tor, das 0 liest, sieht wie "kein Geld" aus und nicht wie ein Fehler.
Wer ein Guthaben-Tor baut, haelt die ROHE Antwort der Boerse einmal daneben und
prueft, ob das gelesene Feld ueberhaupt gefuellt ist.

### Die Ursache war der VPN (25.09.2026, gemessen)

Derselbe Aufruf antwortete stundenweise mit `authenticationError` - fuer jede nonce
und mit zwei unabhaengigen Umsetzungen (unser Modul und die offizielle kraken-cli),
waehrend die Werte in `HKCU\Environment` unveraendert waren. **Es war NordVPN:**

| Zustand | Ausgangs-IP | Futures-Weg | Spot-Weg |
|---|---|---|---|
| NordLynx-Tunnel verbunden | `45.150.x.x` (NordVPN-Knoten) | `authenticationError` | laeuft (0,7059 EUR) |
| Tunnel getrennt | `92.208.x.x` (eigener Anschluss) | **laeuft** (141,5876 USD) | laeuft |

Der Futures-Weg ist also herkunftsempfindlich, der Spot-Weg nicht. Wer eine
Abweisung deutet, prueft deshalb ZUERST die eigene Herkunft (`Get-NetAdapter`
auf `NordLynx`, die oeffentliche IP) und erst danach Schluessel, Rechte oder
Konto-Lockout. **Ein `authenticationError` ist kein Beweis fuer einen falschen
Schluessel** - die eigene IP war es hier, und ein neu erzeugter Schluessel haette
nichts geholfen. Werkzeug fuer den Zeugen (Status, Header, Rohkoerper je Weg):
`Agenten/Handel/kraken_abweisungs_sonde.py`.

### EURC ist kein ZEUR — und Kraken hat eine stille Ordergroessen-Grenze (27.09.2026, gemessen)

Die kraken-Spur sperrte mit "nur ~52 EUR frei, noetig 60", obwohl das Konto laut
Dashboard ~350 "EUR" zeigte. Der Grund: das Guthaben lag als **EURC**
(Euro-Referenz-Stablecoin, `298.27`), nicht als ZEUR (`51.64`). Der Code prüft
ausschliesslich `kraken.guthaben("ZEUR")` (`mindest_guthaben_eur`), und
`BalanceEx` zeigt fuer EURC `hold_trade=0.0`, also "frei" — aber EURC zaehlt
nicht fuer den Fiat-Spot-Orderweg. USDC lag fast bei 0 (`0.0096`). Merksatz:
**ein EUR-Stablecoin ist kein EUR-Guthaben**, wer eine Finanzierungsaussage
trifft, liest die Handelswaehrung des Orderwegs, nicht die Anzeige im Konto.

Der Umtausch EURC→EUR (`EURCEUR`, Kurs `0.9998`, online) war in Tranchen noetig:
`10`, `100` und `150` gingen durch, `200` und `298.27` gaben `EOrder:Insufficient
funds`, obwohl die Balance frei war. Das ist eine **stille Ordergroessen-Grenze
je Order** (genauer Schwellwert unbestimmt, irgendwo <200 EURC). Wer grosse
Betraege umschichtet, teilt sie in Tranchen unterhalb der Grenze auf, statt
gegen die Ablehnung zu pruefen und rate-limits zu fressen. Nach Abzug der
Tranchen stand `ZEUR 349.30`, die kraken-Spur meldete "Live waere gesperrt
durch: nichts". Beleg der Grenze: txids OLZBYR/OODG5H/OMQXSL/OA6H5F, BalanceDiff
298.27-288.27-38.27.

Hinweis: Nur 3 Paare haben EURC als Quote (`ETHEURC`, `SOLEURC`, `XBTEURC`) —
eine Spur "direkt auf EURC" umzustellen beschneidet die rund 30 Instrumente der
Watchlist auf BTC/ETH/SOL, es gibt also keinen Grund, die Spur von ZEUR
wegzubewegen, wenn das Konto EURC traegt.

#### Nachtrag 30.09.2026: die Spur liest die Quote jetzt JE PAAR (Auftrag Max)

Der Merksatz von oben bleibt in Kraft — **EURC ist weiterhin kein
ZEUR-Guthaben**. Was sich geaendert hat, ist die Richtung der Antwort: statt das
Guthaben in die Waehrung der Spur zu zwingen (umtauschen, in Tranchen, siehe
oben), geht die Spur in die Waehrung des GUTHABENS und ordert EURC- und
USDC-gequotete **Paare**. Die Aussage "kein Grund, von ZEUR wegzubewegen" galt
fuer eine Spur, die EINE Waehrung kennt; seit dem 30.09.2026 kennt sie alle
drei.

`Agenten/Handel/kraken/quote.py` holt die Quote aus `AssetPairs` (Feld `quote`,
Rueckfall `wsname` "BASIS/QUOTE") — nicht aus einer Liste im Code. Die Falle,
an **1455 Paaren** gemessen:

| AssetPairs `quote` | Posten im Kontostand |
|---|---|
| `ZEUR`, `ZUSD`, `ZCAD` | `ZEUR`, `ZUSD`, `ZCAD` (Fiat traegt das Z) |
| `EURC`, `USDC` | `EURC`, `USDC` (Stablecoins nicht) |
| `CHF` (bei EURCHF) | **`ZCHF`** — Ausreisser |

Deshalb wird die Quote nicht in einen Namen uebersetzt, sondern gegen den
tatsaechlich abgerufenen Kontostand aufgeloest (Code selbst, dann `Z`+Code, dann
ohne fuehrendes `Z`). Findet sich keiner, ist das Guthaben 0 und die Waehrung
gilt als nicht vorhanden. Ein unbekanntes Paar ist ein **Fehler**
(`QuoteUnbekannt`), kein Rueckfall auf EUR — wer die Quote raet, handelt im
falschen Markt.

Gemessenes Angebot: EURC als Quote auf **3** Paaren (`ETHEURC`, `SOLEURC`,
`XBTEURC`), USDC auf 13 der 17 Instrumente der Watchlist — FIL, SUI, TRX und XLM
haben kein USDC-Paar. Historie: EURC 377–378 Tageskerzen, USDC 654 (XBT/ETH
720), der Scan braucht 120. Watchlist 17 → 33 Paare; Scan am 30.09. ueber alle
33 ohne Fehler, **12 ueber dem Tor, vier davon in der neuen Waehrung**
(ALGOUSDC 73,5 / DOTUSDC 73,3 / AVAXUSDC 68,3 / ETHEURC 66,8).

Das Tor ist trotzdem zu: gemessen **46,81 EUR / 25,08 USDC / 0,00 EURC frei**
gegen `mindest_guthaben_je_quote` 60 je Waehrung. Die Erweiterung nimmt die
Sperre weg, die aus der festen EUR-Annahme kam — sie schaltet nichts scharf.
Wer das EURC-Paar nutzen will, muss EURC halten; das ist eine Handlung von Max,
kein Dateischalter.

#### Gemessen 30.09.2026: der Umtausch lohnt NICHT (Werkzeug `kraken/quoten_vergleich.py`)

Die Frage "soll ich EUR in EURC/USDC tauschen, um das Tor zu oeffnen" ist
messbar, und die Antwort ist nein — aus zwei unabhaengigen Gruenden:

1. **Der Umtausch erschliesst kein Instrument.** Kein Instrument der
   Watchlist ist nur in USDC oder EURC erreichbar; alle 17 haben ein EUR-Paar.
   Kraken fuehrt 546 Paare mit Quote EUR gegen 47 mit USDC und **3** mit EURC
   (XBT, ETH, SOL — alle drei auch in EUR).
2. **Der Markt ist dort nicht besser, sondern schlechter.** Median aus drei
   Abrufen je Paar, 13 Instrumente: die USDC-Paare sind im Mittel **6,6 bp
   weiter** als die EUR-Paare (EURC: 3,7 bp weiter). Ein Rundlauf zahlt rund
   einen Spread, der Umtausch kostet einmalig **60 bp** (Taker 0,60 %) — es
   gibt **keinen Break-even**.

| Instrument | EUR-Spread | USDC-Spread | Vorteil USDC |
|---|---|---|---|
| XBT | 0,0 bp | 0,0 bp | ±0,0 |
| ETH | 0,5 | 2,3 | −1,9 |
| SOL | 1,0 | 3,4 | −2,4 |
| LINK | 2,5 | 9,1 | −6,6 |
| LTC | 1,7 | 15,8 | −14,1 |
| ATOM | 9,9 | 29,7 | −19,8 |
| ALGO | 11,0 | 26,8 | −15,7 |
| BCH | 6,3 | 16,9 | −10,6 |

**Merksatz:** eine Quotewaehrung ist kein Marktplatz, sondern eine Waehrung.
Ob sie sich lohnt, entscheidet nicht "habe ich Guthaben darin", sondern
(1) erschliesst sie ein Instrument, und (2) ist ihr Markt enger. Beides wird
gemessen, nicht angenommen. Der Umtauschweg selbst existiert
(`EURCEUR` ordermin 4, costmin 0,45; `USDCEUR` ordermin 5, costmin 0,45;
EURC/EUR notiert bei 1,0001) — er ist nur nicht sinnvoll.

**Was die Erweiterung trotzdem wert ist:** sie ist eine Versicherung, keine
Ertragsquelle. Liegt das Guthaben einmal in USDC oder EURC, kann die Spur ohne
Umtausch handeln; laege es nur in EUR und EUR waere leer, muesste sie sonst
erst tauschen (60 bp) und dabei auf ein Fenster warten. Deshalb bleiben die
Gates und die Watchlist stehen — nur eben bei 0,00 EURC und 25,08 USDC
unbenutzt.

## Der Stop-Zustand steht an der Boerse, nicht im Buch (30.09.2026, T-207)

Am 30.09.2026 trugen die drei Kraken-Schutz-Stops der Spur `mosaic` (BTC/ETH/SOL,
zusammen rund 258 EUR) an der Boerse den Status `canceled` — `mosaic/zustand.json`
meldete weiterhin `boersen_stop_fehlt: false`. Gefunden wurde das nur, weil
`kraken/spot_stops.py` von Hand nachsah; die Spur selbst hat ihren eigenen Stop nie
nachgefragt. Dieselbe Klasse wie T-118 (xperp, 26.09.) und T-208 (kraken-Buch).

Werkzeug: `Agenten/Handel/mosaic/boersenabgleich.py` (Vorschau ist Standard,
`--anwenden` schreibt), eingebaut in `mosaic/handeln.py` in **jedem** Zyklus der
Basis — nicht nur im Live-Zweig. Der Live-Zweig laeuft namlich genau dann nicht,
wenn eine Sperre zu ist (Guthaben in der falschen Waehrung, kein Fenster,
Herzschlag), und genau dann waeren die echten Positionen ungeschuetzt.
Wache: Hermes-Cron `mosaic-stop-wache` (Job `2faf001c30d6`, alle 30 Minuten,
`no_agent`, Telegram) — leere Ausgabe = nichts senden; sie liest im Vorschaumodus
und nennt die betroffene Position, statt die Regeln nachzubauen.

Drei Regeln entscheiden den Fall:

1. Gesichert wird der **Bestand der Boerse**, nicht die Menge im Buch.
2. Eine verschwundene Position wird nur ausgebucht, wenn der Ausstiegspreis
   belegbar ist (Kraken `ClosedOrders`, OKX `letzte_fuellung`) — sonst bleibt das
   Buch stehen und die Position wird gemeldet.
3. Fremde Stops (Kennung kennt das Buch nicht, etwa von Hand gesetzt) werden
   **nie** angefasst.

**Merksatz:** ein Feld im Buch ist eine Behauptung, die altert. Ob ein Notausstieg
wirklich steht, weiss nur die Boerse — und diese Aussage muss in jedem Zyklus
fallen, nicht nur im Live-Zweig.

## Nicht verkaufbare Posten: Ordermin und Sonderformen (01.10.2026, T-280)

Beim Umschichten blieben drei Posten liegen — aus ZWEI verschiedenen Gruenden, die man
am Betrag nicht unterscheidet. Gemessen mit `kraken/lagerbestand.py` (lesend, neue
Fassung):

| Code | Menge | Lage | Paar | ordermin | fehlt bis ordermin |
|---|---|---|---|---|---|
| PEPE | 409.009,94 | unter_ordermin | PEPEEUR | 1.500.000 | 1.090.990,06 |
| ONDO | 10,74331 | unter_ordermin | ONDOEUR | 15 | 4,25669 |
| ADA.S | 50,63776095 | kein_paar | — | — | — |

1. **Ordermin**: Kraken verlangt je Paar eine Mindestmenge (`ordermin` in `AssetPairs`),
   unabhaengig vom Wert. PEPE und ONDO sind kein Defekt — die Order waere schlicht
   abgelehnt worden. Weg: sammeln, bis der Bestand ueber dem Ordermin liegt.
2. **Sonderformen haben GAR KEIN Paar.** `AssetPairs` fuehrt keine einzige Basis mit
   einem Punkt; gemessen zeigen ADA.S, ATOM21.S, HYPE.B und XPEV.EQ deshalb eine leere
   Paarliste. `.S` ist die gestakte Form (ADA.S = gestakte Cardano) — der Weg ist
   Unstaking, nicht eine Order; `.B` und `.EQ` sind ebenfalls reine Kontencodes ohne
   Markt. Was sie genau sind, ist offen — eine Order ist dort jedenfalls kein Weg.
3. **Barmittel ist kein Befund.** USDC/ZEUR/ZUSD haben kein Paar mit sich selbst als
   Basiswert, sie stehen als `quote` im Buch. Das Werkzeug fuehrt sie getrennt
   (`barmittel`) — sie mit „gestakt“ zu erklaeren waere eine falsche Ursache, und die
   Ursache ist genau das, wonach man hier sucht.

Der ganze Bestand am 01.10.2026: 22 Posten, davon 13 festliegend — die drei genannten
plus zehn Staubposten (DOT 0,0016 gegen ordermin 3,9; SUI 0,00003 gegen 5; JUP 0,00009
gegen 23; YOM 127,96 gegen 300; LAPTOP 8,572 gegen 25; HYPE 1,2e-06 gegen 0,1). Wert
der drei Sichtbaren: PEPE 1,61 EUR, ONDO 4,70 EUR. **Es lohnt kein Umbau** — aber die
Ursache muss man kennen, sonst sucht man beim naechsten Mal wieder.

**Dasselbe Muster auf der anderen Boerse:** OKX lehnt `BETH-USDT` (160,77 USD) und
`OKSOL-USDT` (20,00 USD) mit `51155 ... local compliance restrictions` ab; die Sperre
ist an `/public/instruments` NICHT zu sehen und kommt VOR jeder Mengenpruefung. Ein
Fehlercode, der die Ursache nennt, ist die Ausnahme — nachpruefen am Instrumentenrecord
ist die Regel.

Werkzeug: `Agenten/Handel/kraken/lagerbestand.py` (Vorgabe: nur festliegende Posten,
`--alle`, `--json`, `--ohne-kurse`). Tests `kraken/tests/test_lagerbestand.py`.

## Der Hebel steht am KONTRAKT, nicht in der Order (01.10.2026, T-285)

`/sendorder` nimmt einen `leverage`-Parameter an — Kraken Futures **ignoriert ihn**.
Der Hebel dieses Kontos steht in `/leveragepreferences`, und zwar JE KONTRAKT:

```
PF_SOLUSD 7.0   PF_HBARUSD 10.0   PF_CSPRUSD 3.09   PF_KASUSD 5.0
PF_XBTUSD 8.0   PF_ZECUSD 9.0     PF_DOGSUSD 4.9    PF_SUIUSD 7.0   ... (18 Eintraege)
```

Es gibt keine Kontoeinstellung „Hebel“, nur diese Tabelle. Gemessen: **Margin =
Nennwert / Hebel** — 1 Kontrakt PF_SOLUSD bei 118,03 USD Nominal belegt 16,86 USD
(7x), nicht die 11,80 USD aus dem Margenplan (EEA retail 10 %). Wer den Plan allein
liest, plant 5 USD zu wenig ein; bei PF_CSPRUSD (3,09x) unterschaetzt der Plan um
Faktor 3.

**Behoben:** `kraken_futures.einschuss()` nimmt jetzt das STRENGERE von Plan und
Hebel-Obergrenze (`max(plan, 1/hebel)`), Tabelle 60 s gecacht (`hebel_je_kontrakt`),
Grundlage fuer `handelbar()` und damit fuer jede Guthaben-Sperre. Die Order selbst
bleibt unveraendert: gesetzt wird die Obergrenze mit `PUT /leveragepreferences`
(Parameter als FORMKOERPER — als Query-String antwortet dieselbe Signatur mit
`authenticationError`), das macht `omnitrade_futures/weg.hebel_vorbereiten()` vor dem
Zyklus, sobald `handel_erlaubt` steht.

## Das Futures-Guthaben ist nicht mehr knapp (01.10.2026, T-284)

Die Notiz „1,28 USD frei“ war der Stand vom Vormittag. Gemessen am Abend:
**availableMargin 83,37 USD** (EUR 62,82 + USDC 83,80 verfuegbar; 83,38 sind als
initialMargin durch drei laufende nautilus-Positionen gebunden — SUI/HBAR/HYPE).
Das Tor der Spur `omnitrade_futures` (`mindest_guthaben 25 USD`) ist damit **offen**;
1 Kontrakt PF_SOLUSD braucht 16,86 USD. `handeln.py --vorschau` nennt dann keinen
Guthaben-Grund mehr.

**Merksatz:** ein Guthaben ist eine Momentaufnahme, kein Zustand — eine Zahl aus dem
Vormittag entscheidet am Abend nichts. Und `cash.balances` bleibt bei Kraken Futures
0,00: das Geld liegt im flex-Konto (`availableMargin`).

### Nachtrag 01.10.2026, 23:31: der 1-Kontrakt-Roundtrip lief — `/fills` ist kaputt

Eine parallele Sitzung hat den Roundtrip auf `PF_STRKUSD` gefahren (VPN getrennt):
Kauf **angenommen und gefuellt**, danach scheiterte das Fill-Polling an
`authenticationError` auf `/fills`, die Position blieb **ohne Stop** stehen und
wurde von Hand geschlossen (drei vorherige Positionen wiederhergestellt).

- **Belegt:** Kauf UND Verkauf werden ohne VPN angenommen. Und: eine 1-Kontrakt-
  Probe gehoert auf einen BILLIGEN Markt — `futures_probe.py` rechnete „1 Kontrakt
  = 1 USD Nominal“ und haette mit der Vorgabe 8 Kontrakte PF_XBTUSD einen Kauf
  ueber 676.816 USD Nennwert ausgeloest, der bei 83 USD freier Margin
  durchgegangen waere.
- **NICHT belegt:** die Margin-Hoehe. Der Roundtrip hat kein Equity vorher/nachher
  gemessen — die 16,86 USD oben sind die **Rechnung** aus der Preference (7x),
  nicht die Messung. Genau dafuer fehlt noch ein Lauf mit
  `availableMargin` vor und nach der Order.
- **Offen:** warum `/fills` mit `authenticationError` antwortet, waehrend
  `/accounts` und `/openpositions` antworten.

**Merksatz:** eine Order, die angenommen wird, belegt nicht die Margin. Und ein
Fill-Polling, das nicht antwortet, laesst die Position ohne Notausstieg stehen —
der Stop darf nicht am Polling haengen.
