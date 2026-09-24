---
id: 20260921-boersen-und-schluessel
title: 'Handel — Boersen und Schluessel'
tags: [handel, zugaenge]
created: 2026-09-21
updated: 2026-09-23
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
