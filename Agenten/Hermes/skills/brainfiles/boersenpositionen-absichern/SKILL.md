---
name: boersenpositionen-absichern
description: Offene Kontopositionen nachträglich mit Stop-Loss versehen.
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Handel, Kraken, OKX, Stop-Loss, Absicherung]
---

# Bestehende Börsenpositionen nachträglich absichern

Hängt einen Schutz-Stop an Positionen, die schon offen sind - Spot genauso wie
Margin. Es geht **nicht** um den Stop beim Einstieg (den setzt die Spur selbst),
sondern um den Handgriff danach: Position gefunden, Preis gerechnet, Order
gestellt, Buch nachgezogen, alles am echten Konto belegt. Die Buchmechanik der
Spuren steht im Skill `handel-spuren`; hier steht der Weg ans Konto.

Reine Standardbibliothek plus die Hausmodule `Agenten/Handel/kraken/kraken.py`
und `Agenten/Handel/scanner/okx.py`; kein Schluessel im Klartext, nichts wird
neu erfunden.

## When to Use

- "Kraken positionen mit stop loss 7,5% ausstatten"
- "Sui Zec und near auf kraken ebenfalls absichern"
- "sichere die offenen Positionen ab", "Stop nachziehen", "Notausstieg fehlt"
- Eine Position ist in `zustand.json` sichtbar, aber ohne `stop_txid`
- Vor dem Scharfschalten einer Spur: "hat jede offene Position einen Stop?"

## Prerequisites

- Lauf aus `Agenten/Handel`; Interpreter immer `scanner/.venv/Scripts/python.exe`.
- Kraken-Schluessel als Windows-Benutzervariablen `KRAKEN_SPOT_API_KEY` +
  `KRAKEN_SPOT_API_SECRET` (das Paar `KRAKEN_API_KEY`/`KRAKEN_API_SECRET` wird
  von Kraken abgelehnt - wer "Invalid key" sieht, liest den anderen Namen).
- OKX: `OKX_LIVE_API_KEY/SECRET/PASSPHRASE` (scanner) bzw.
  `OKX_API_KEY/SECRET/PASSPHRASE` (xperp, mosaic) und `OKX_BASE=https://eea.okx.com`.
- Die Werkzeuge liegen bereit: `kraken/margin_stops.py`,
  `mosaic/kraken_stops_7_5.py`, `kraken/kraken.py` (`stop_setzen`).

## How to Run

Immer erst rechnen, dann ordern - Vorschau ist der Standard.

- Kraken-Margin: `scanner/.venv/Scripts/python.exe kraken/margin_stops.py`
  (dann `--anwenden`, optional `--prozent 7.5`)
- Kraken-Spot (mosaic-Buch): `scanner/.venv/Scripts/python.exe mosaic/kraken_stops_7_5.py`
  (dann `--anwenden`, danach `--nur-buch`)

Beide ueber das `terminal`-Werkzeug aufrufen. Vor jedem `--anwenden` die
Vorschautabelle lesen: jede Zeile muss `ok` sein, kein "Hinweis".

## Quick Reference

| Zweck | Aufruf |
|---|---|
| Spot-Bestand sehen | privat `BalanceEx` (nicht `Balance`) |
| Margin-Positionen sehen | privat `OpenPositions` |
| Offene Orders | privat `OpenOrders` |
| Eine Order pruefen | privat `QueryOrders` (`txid=`) |
| Paarregeln | oeffentlich `AssetPairs` (`lot_decimals`, `pair_decimals`, `ordermin`, `costmin`, `leverage_sell`) |
| Stop setzen | `kraken.stop_setzen(paar, menge, preis, echt=True, leverage=None, close_txid=None)` |
| OKX-Stop setzen | `okx.stop_setzen(inst, basismenge, stop_preis)` |
| OKX-Stop abbestellen | `okx.stop_stornieren(algo_id, inst)` - **inst ist Pflicht** |
| Buch nachziehen | `mosaic/kraken_stops_7_5.py --nur-buch` |
| Buchspiegel pruefen | `./scanner/.venv/Scripts/python.exe spiegelstand.py` |

Die exakten Feldnamen der Order-Aufrufe stehen in
`references/boersen-aufrufe.md` - laden, bevor eine Order zusammengesetzt wird.

## Procedure

1. **Ort klaeren, nicht raten.** Eine Position liegt an DREI Stellen: Spot
   (`BalanceEx`), Margin-Positionen (`OpenPositions`), Futures-Brieftasche
   (eigener Ort). Wer nur das Guthaben liest, schliesst falsch "hat er nicht".
   Genau daran scheiterte die Suche nach SUI/ZEC/NEAR: sie standen als 6x
   `SUIEUR`, 1x `NEAREUR`, 1x `XZECZUSD` in `OpenPositions`.
2. **Einstieg je Position bestimmen.** Margin: `cost / vol`. Spot aus dem Buch
   (`einstieg`) oder aus der Ordnerhistorie. Ohne Einstieg keinen Stop setzen.
3. **Stop rechnen und pruefen:** `einstieg * (1 - prozent/100)`. Liegt das
   Ergebnis NICHT unter dem aktuellen Kurs, die Position ueberspringen und
   melden - ein Stop ueber dem Markt ist ein sofortiger Verkauf, keine
   Absicherung.
4. **Menge deckeln.** `stop_menge()` = `min(Position, verfuegbar)`, abgerundet
   auf `lot_decimals`. Die Brieftasche fuehrt den NETTO-Zufluss (Gebuehr schon
   abgezogen), das Buch den Bruttowert - ein Stop ueber die Buchmenge scheitert.
   Bei Margin: genau die Menge der Position, nie mehr (sonst dreht der Rest short).
5. **Preis runden** auf `pair_decimals` (`kraken.preis_gerundet(paar, preis, "auf")`).
   Ein roher Rechenwert wird abgelehnt; "auf" haelt den Long-Stop nie tiefer als
   gerechnet.
6. **Order stellen** (exakte Felder: `references/boersen-aufrufe.md`). Spot:
   einfacher Verkaufsstop. Margin: **verknuepft** mit `close[ordertxid]` der
   Position - sonst bleibt ein nackter Stop stehen, der ohne Position einen
   Short aufmacht.
7. **Reihenfolge beachten.** Kraken reserviert die Menge eines Stop-Loss: ein
   zweiter Stop auf dieselbe Menge scheitert mit `EOrder:Insufficient funds`.
   Also **stornieren -> setzen**, und wenn das Setzen scheitert, den ALTEN Stop
   sofort wiederherstellen. Nach einem Spot-Handgriff den Stop zuerst pruefen,
   dann stornieren.
8. **Am Konto nachsehen** (nicht im Buch): `OpenOrders` listet je Position einen
   `stop-loss`; `QueryOrders(txid=...)` muss `descr.close` = `close position @
   stop loss ...` zeigen und das Flag `c` in `oflags` tragen. Frisch gesetzte
   Stops erscheinen **nicht sofort** - vor jeder "Stop fehlt"-Aussage zweimal
   abfragen.
9. **Buch folgt der Boerse.** `stop`, `stop_txid` und die echte `menge` ins
   `zustand.json` schreiben (`--nur-buch` beim Spot-Werkzeug macht genau das),
   dann spiegeln (Bedingung 4) und `spiegelstand.py` muss byte-gleich melden.
10. **Loecher melden, nicht schweigen.** Positionen, die uebersprungen wurden
    (Staub, Stop nicht unter dem Markt) und Bestaende ohne Stop gehoeren in die
    Antwort - sonst sieht "8 Stops gesetzt" nach "alles geschuetzt" aus.

## Pitfalls

- **Paarschreibweisen.** Kraken nennt dasselbe Paar zweimal: in der Order-Anfrage
  `XXBTZEUR`/`XETHZEUR`, in der offenen Order (`descr.pair`) `XBTEUR`/`ETHEUR`.
  Ein Vergleich der rohen Zeichenketten haelt ein geschuetztes Paar fuer
  ungeschuetzt. Immer auf `(Basis, Quote)` normalisieren (`XBT`/`XXBT` -> `BTC`).
- **Reservierte Menge.** Ein Stop-Loss sperrt die Stuecke: "erst neu, dann alt"
  ist unmoeglich (`EOrder:Insufficient funds`). In der Luecke eines
  Fehlversuchs steht die Position ohne Stop - das im Bericht sagen.
- **Margin-Stop ohne Verknuepfung** ist gefaehrlich: ohne `close[ordertxid]`
  bleibt der Verkaufsstop nach einem Handverkauf stehen und eroeffnet einen Short.
- **Ein Formsache-Hebel.** Fuer eine schliessende Margin-Order ist der Hebel
  unwichtig, muss aber im Erlaubten des Paares liegen (`leverage_sell`; SUIEUR
  bis 10, NEAREUR bis 3, XZECZUSD bis 5). `validate=true` nimmt Kraken fuer alle
  Formen an und kostet nichts - so vorher pruefen.
- **Ein Schalter, der ueberall an ist, sagt nichts.** `handel_erlaubt` und
  `freigabe.erfuellt` stehen in jeder Spur auf true; eine Live-Sperre, die nur
  diese liest, laesst `--live` durch und ein Buch mit `modus=live` OHNE Order
  entsteht ("Buch war Fiktion"). Sperren am ORDERWEG festmachen
  (`LIVE_ORDERWEG`, `live_gate()`) und `--live` immer auf Papier zwingen, wenn
  kein Orderaufruf existiert.
- **Nach `--anwenden` nicht erneut anwenden.** Ein zweiter Lauf sieht den alten
  Buchpreis, storniert den frischen Stop und setzt einen neuen - erst `--nur-buch`.
- **OKX GET-Parameter gehoeren in den PFAD**, `body` ist fuer POST; `_roh(...)`
  gibt die DATA-LISTE zurueck, nicht das Antwort-Dict. `cancel-algos` verlangt
  `instId` (sonst 50014), und `51400` heisst "gibt es nicht mehr" = erledigt,
  kein Fehler.
- **Nur die eigene Kontraktfamilie/Familie anfassen** und Handpositionen als
  solche erkennen (OKX `tag='OTversionB'`, Kraken `OpenPositions` mit `margin`).

## Verification

```bash
cd Agenten/Handel
scanner/.venv/Scripts/python.exe kraken/margin_stops.py       # Zeilen: alle "ok"
scanner/.venv/Scripts/python.exe kraken/margin_stops.py --anwenden
./scanner/.venv/Scripts/python.exe spiegelstand.py            # byte-gleich
```

Bestanden, wenn `OpenOrders` je Position genau einen `stop-loss` zeigt, dessen
Preis unter dem Markt liegt, `QueryOrders` je Margin-Order `close position @
stop loss` meldet und `spiegelstand.py` byte-gleich ist. Ein "(papier) ok" im
`dauerlauf.log` ist KEIN Beleg - die Boerse ist der Zeuge.
