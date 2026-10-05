# Exakte Aufrufe und Felder (Kraken und OKX)

Alles hier ist an echten Antworten abgelesen (24.09.2026). Vor dem Zusammensetzen
einer Order diese Datei laden - die Feldnamen sind nicht ratbar.

## Kraken: lesende Aufrufe

Ueber `Agenten/Handel/kraken/kraken.py` geladen (per Pfad, nicht ueber
`sys.path`):

```python
k = _lade("kraken", os.path.join(HANDEL, "kraken", "kraken.py"))
k._roh_privat("BalanceEx")                  # Spot-Bestand MIT Einlagen
tb = k._roh_privat("TradeBalance")          # eb, tb, m (Margin gebunden), n
op = k._roh_privat("OpenPositions")         # offene Margin-Positionen
k._roh_privat("OpenOrders")                 # offene Orders
k._roh_privat("QueryOrders", txid="<txid>", trades="false")
k._roh_oeffentlich("AssetPairs")            # Paarregeln, alle 1450
k.letzter_kurs("SUIEUR")                    # Ticker
```

`OpenPositions` liefert je Position:

| Feld | Bedeutung |
|---|---|
| `ordertxid` | **die Kennung fuer `close[ordertxid]`** |
| `pair`, `type` (`buy`/`sell`), `posstatus` | Paar und Richtung |
| `vol`, `vol_closed` | Menge der Position |
| `cost` | Einsatz; **Einstieg = `cost / vol`** |
| `margin` | gebundenes Margin |
| `terms`, `rollovertm` | Rollover-Gebuehr (z.B. `0.0200% per 4 hours`) - **NICHT der Hebel** |

`AssetPairs` je Paar: `lot_decimals`, `pair_decimals`, `ordermin`, `costmin`,
`leverage_buy`, `leverage_sell` (Liste, z.B. SUIEUR `[2..10]`, NEAREUR `[2,3]`,
XZECZUSD `[2..5]`).

## Kraken: Einzahlungen und Guthaben je Wallet

```python
k._roh_privat("DepositStatus", asset="USDC")            # Eingaenge je Waehrung
k._roh_privat("Ledgers", asset="USDC", start=<epoch>)   # PLURAL - 'Ledger' gibt 404
k._roh_privat("WithdrawStatus", asset="USDC")
```

Die vollstaendige Nachweis-Kette (Einzahlung, Gegenbuchung mit `refid`, Zielkonto,
Margin-Wallet, Futures `/accounts`) und ihre Fallen stehen in
`references/einzahlung-und-guthaben.md`. **Zugangsdaten nur auf Existenz pruefen:**
`reg query HKCU\Environment` druckt die Werte im Klartext - stattdessen
`[Environment]::GetEnvironmentVariable(name, 'User')` lesen und nur Laenge/Anfang
nennen.

## Kraken: Stop setzen

```python
# Spot
k.stop_setzen("XXBTZEUR", menge, 70047.0, echt=True)

# Margin - verknuepft mit der Position
k.stop_setzen("SUIEUR", pos["vol"], 0.8140, echt=True,
              leverage=10, close_txid=pos["ordertxid"])
```

`stop_setzen(paar, menge, stop_preis, echt=False, leverage=None, close_txid=None)`
rundet den Preis intern mit `preis_gerundet(paar, stop_preis, "auf")`.

Die Felder, die dabei an `AddOrder` gehen:

```
pair=<Paar>  type=sell  ordertype=stop-loss  volume=<Menge>  price=<Stop>
leverage=<Zahl>                       (nur Margin)
close[ordertxid]=<ordertxid>          (nur Margin, verknuepft die Position)
close[ordertype]=stop-loss
close[price]=<Stop>
validate=true                         (nur Probe; bei echt=True faellt es weg)
```

`validate=true` nimmt Kraken fuer alle diese Formen und antwortet z.B.:

```json
{"descr": {"order": "sell 30.694 SUIEUR @ stop loss 0.8140 with 5:1 leverage",
           "close": "close position @ stop loss 0.8140"}}
```

Gegengeprueft mit `QueryOrders` (so sieht ein richtiger, verknuepfter Stop aus):

```
status   open
vol      666.99922
descr    {'pair': 'SUIEUR', 'type': 'sell', 'ordertype': 'stop-loss',
          'price': '0.8140', 'leverage': '10:1',
          'order': 'sell 666.99922 SUIEUR @ stop loss 0.8140',
          'close': 'close position @ stop loss 0.8140'}
oflags   fciq        # 'c' = Close-Order, 'f' = Gebuehr in der Quote-Waehrung
margin   True
```

## Kraken: Fehlermeldungen deuten

| Meldung | Ursache | Abhilfe |
|---|---|---|
| `EOrder:Insufficient funds` | Menge ist reserviert (zweiter Stop) ODER Buchmenge > Brieftasche (Brutto vs. Netto) | stornieren -> setzen; `stop_menge()` = `min(Position, verfuegbar)`, abgerundet |
| `EOrder:Invalid price:...can only be specified up to N decimals` | roher Rechenwert | `preis_gerundet(paar, preis, "auf")` |
| `EAPI:Invalid nonce` | ein anderes Werkzeug (z.B. kraken-cli) hat den Schluessel-Nonce hochgesetzt | `nonce_pool.vorwaerts()`; `_roh_privat` wiederholt bis zu dreimal |
| `EAPI:Invalid key` | falscher VARIABLENNAME gelesen (`KRAKEN_API_KEY` statt `KRAKEN_SPOT_API_KEY`) | das SPOT-Paar benutzen |
| `EGeneral:Permission denied` (Spot) / `authenticationError` (Futures) | **zuerst die HERKUNFT** (VPN/Proxy aktiv? IP gewechselt?), danach Schluessel/Rechte, zuletzt eine zeitweise Konto-Sperre | Reihenfolge unten abarbeiten - **einen neuen Schluessel zu erzeugen hilft hier fast nie** |
| `5xx`/`1020` OHNE JSON | cloudflare/Netz, kein Kraken-Fehler | kurze Pause, dann wiederholen - `content-type` im Zeugen zeigt es |

**Reihenfolge beim Deuten einer Abweisung** (gemessen: derselbe Futures-Aufruf
wurde mit laufendem NordLynx-Tunnel als `authenticationError` abgewiesen und ging
ohne Tunnel sofort wieder; der Spot-Weg lief waehrenddessen durch):

1. **Herkunft pruefen** - `Get-NetAdapter` auf den VPN-Adapter und die
   oeffentliche IP. Ein VPN-Ausgang ist eine ANDERE IP, und Kraken-Derivatives
   ist herkunftsempfindlich, waehrend der Spot-Weg es nicht ist. Ein
   `authenticationError` ist KEIN Beweis fuer einen falschen Schluessel.
2. **Belegen, dass die eigenen Werte unveraendert sind** - Hash der Registry-Werte
   gegen den letzten bekannten Stand (PowerShell-History), Laenge, keine
   Rand-Leerzeichen. Nicht den Wert ausgeben.
3. **Zweite Umsetzung gegenhalten** - die offizielle kraken-cli oder ein
   Einzelaufruf; erst wenn BEIDE abweisen, ist es der Schluessel.
4. **Erst dann** Rechte/Konto-Lockout annehmen: nach vielen Fehlversuchen sperrt
   Kraken ein Konto zeitweise (`EGeneral:Temporary lockout`, ~15 min) und jeder
   weitere Versuch setzt den Timer zurueck - dann NICHT weiterklopfen, sondern
   die Lage mit `Agenten/Handel/kraken_abweisungs_sonde.py` messen und warten.

**Abweisung ohne Zeugen ist keine Messung.** Ein Nachweis ueber die Lage (Status,
Header, Rohantwort) laeuft als Sonde + Cron `kraken-abweisung-wache`; sie misst
OEFFENTLICHE und SIGNIERTE Wege, weil ein fallender oeffentlicher Aufruf kein
Schluesselproblem sein kann. Details: Wiki `Werkzeuge/kraken-abweisungs-sonde.md`,
Lektion 3 in `Lektionen/Boersen-und-Schluessel.md`.

## OKX (scanner/okx.py)

```python
okx._roh("/api/v5/account/balance", signiert=True)      # Kontostand
okx._roh("/api/v5/account/positions?instType=SWAP", signiert=True)
okx.stop_setzen(inst, basismenge, stop_preis)            # Bedingte Stop-Order
okx.stop_inst(algo_id)                                   # instId lesend holen
okx.stop_stornieren(algo_id, inst)                       # inst ist PFLICHT
```

- GET-Parameter gehoeren in den PFAD: `_roh(body=...)` schickt einen REQUEST-BODY
  (POST) und wird bei GET falsch signiert.
- `_roh` gibt die **DATA-Liste** zurueck, nicht das Antwort-Dict - `.get()` darauf
  faellt mit `AttributeError` um, obwohl der Abruf geklappt hat.
- Preise auf `tickSz` runden; Stops laufen ueber `/api/v5/trade/order-algo`
  (`ordType=conditional`) und ueberleben einen Neustart.
- `cancel-algos` verlangt `instId` (ohne: `50014 Parameter instId can not be
  empty`); `51400` heisst "gefuellt, storniert oder gibt es nicht" = **erledigt**.
- `50119 API key doesn't exist` / `50101 APIKey does not match current
  environment` = meist der FALSCHE HOST, nicht ein toter Schluessel: Schluessel
  UND Host ueber denselben Weg lesen (`_live_basis()` mit Registry-Rueckfall).
- Die eigene Kontraktfamilie pruefen (`BZ-USD_UM_XPERP-310509`), Handpositionen
  tragen `tag='OTversionB'`.

## OKX: einen BESTEHENDEN Stop aendern statt stornieren und neu setzen

```python
okxf.stop_nachziehen(algo_id, inst, stop_preis)
# POST /api/v5/trade/amend-algos
# {"algoId": ..., "instId": ..., "newSlTriggerPx": ..., "newSlOrdPx": "-1"}
```

Die Position laeuft weiter, **nur der Ausloesepreis wandert**; die `algoId` bleibt
dieselbe. Das ist der Unterschied zum Weg `algo_stornieren()` +
`schutz_stop_setzen()`: dort gibt es zwischen beiden Aktionen ein Fenster OHNE
Schutz, und der Weg traegt in der Antwort `sCode != 0` trotzdem kein Fehlerzeichen
im Weg selbst — der Aufrufer muss `sCode` lesen. `-1` als Auftragspreis laesst als
Market ausfuehren (ein Limit-Stop fuellt im Absturz nicht).

**Probe ohne Geld: denselben Wert zurueckschreiben.** Ein offener Stop bekommt
exakt seinen jetzigen Preis; nach der Aenderung muessen algoId, Marke und Menge
unveraendert dastehen. Haette die Route nicht gegriffen, waere der Stop weg —
so ist der Erfolg am Bestand ablesbar statt behauptet.

Merksatz: **zwei Arten von Auftraegen, zwei Wege.** `algo_stornieren()`
nimmt eine `algoId` aus `order-algo`, `order_stornieren()` eine `ordId` aus
`order`. Wer beim Weglassen der einen Art das Falsche storniert, bekommt `51400`
("gefuellt, storniert oder gibt es nicht") — was wie ein Erfolg aussieht und
die Sorge ausloest, obwohl der Schutz noch steht.

Der Trailing-Stop ueber diesen Weg, samt den drei Toren, die er braucht:
`references/trailing-stop.md`.

## Die Werkzeuge

| Werkzeug | Flags |
|---|---|
| `kraken/margin_stops.py` | `--anwenden`, `--prozent 7.5`; Vorschau ist Standard |
| `mosaic/kraken_stops_7_5.py` | `--anwenden`, `--nur-buch`; Vorschau ist Standard |
| `kraken/kraken.py` | `stop_setzen(..., leverage=, close_txid=)`, `offene_orders()`, `order_stornieren(txid)`, `preis_gerundet(paar, preis, richtung)` |
| `scanner/okx.py` | `stop_setzen`, `stop_stornieren(algo_id, inst)`, `stop_inst`, `stop_details` |

Reine Rechenfunktionen (ohne Netz, damit ohne Nebenwirkung testbar):
`margin_stops.einstieg()`, `.stop_preis()`, `.ist_staub()`, `.hebel()`, `.plan()`,
`kraken_stops_7_5.stop_menge()`, `.normal()`.
