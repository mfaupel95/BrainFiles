# Gebuehren belegen statt annehmen

Wann: eine Spur soll beurteilt werden (f_max, netto, Freigabe), zwei Spuren tragen
fuer dieselbe Boerse verschiedene Saetze, oder eine Spur meldet im Bericht
"BRUTTO und UNBEKANNT".

Kernsatz: Eine Gebuehr wird an einer ECHTEN Fuellung UND am Kontotarif gemessen -
nie an einer Tarifseite, nie aus dem Gedaechtnis, nie von einer anderen Boerse.

## Die zwei Zeugen (OKX, rein lesend, ohne Order)

* **Tarif des Kontos**: `GET /api/v5/account/trade-fee?instType=SPOT` (bzw.
  `FUTURES`) -> `level`, `maker`, `taker` als Bruchteil je Seite. OHNE `instId`
  funktioniert es; MIT `instId` antwortet OKX bei XPERP-Kontrakten
  `50016 instId and instType don't match`.
* **Echte Fuellung**: `GET /api/v5/trade/fills?instType=SPOT&limit=20` ->
  `fee`, `feeCcy`, `fillPx`, `fillSz`. Der Satz ist
  `|fee| / (fillSz * ctVal * ctMult * fillPx)`; `ctVal`/`ctMult` kommen aus
  `/api/v5/public/instruments` - **ein XPERP-Kontrakt ist NICHT 1 USD**
  (gemessen: ZEC 0,01 / ADA 10 / VVV 0,1). Ohne die Kontraktgroesse rechnet man
  den Satz um Faktor 100 falsch.
* Aufruf im Haus: `scanner/okx.py` (`_roh(pfad, signiert=True)`; GET-Parameter
  gehoeren in den PFAD). `OKX_SIMULATED` darf NICHT gesetzt sein - sonst misst
  man das Papierkonto, und dessen Tarif sagt nichts ueber echtes Geld.
* **Kraken**: Fuellung plus `/0/private/TradeVolume` (der Haus-Client hat dafuer
  keinen eigenen Aufruf; die Messung vom 22.09.2026 steht in
  `kraken/wachen.json` unter `_gebuehren_abo_widerlegt`). Futures: eigener
  Dienst `futures.kraken.com` - gemessen 25.09.2026: 0,04-0,05 % je Seite.

## Messwerte 01.10.2026 (eigenes OKX-Konto, EEA)

| Markt | taker je Seite | Zeugen |
|---|---|---|
| OKX Spot | **0,10 %** (`gebuehr_taker: 0.001`) | Tarif `Lv1 taker=-0.001` UND Fuellung `HYPE-USDC` 0,002772544 auf 2,77254 USDC |
| OKX Futures/XPERP | **0,05 %** (`gebuehr_taker: 0.0005`) | Tarif `taker=-0.0005` UND Fuellungen ZEC-/ADA-`USD_UM_XPERP` je 0,0500 % |
| Kraken Spot | 0,60 % (`0.006`) | Fuellung + `TradeVolume` (22.09.2026) |
| Kraken Futures | 0,04-0,05 % (`gebuehr_pct: 0.05`) | Round-Trip 0,0029 USD auf 4,55 USD (25.09.2026) |

Vorher rechnete das Haus OKX-**Spot** mit 0,05 % - dem halben Satz, weil der
Futures-Satz fuer beide Maerkte benutzt wurde. Jede Netto-Zahl war damit um
0,1 Prozentpunkte je Runde zu freundlich, auch bei `scanner` (der einzigen Spur
mit belegtem Vorteil).

## Einheiten - der haeufigste Fehler

* `gebuehr_taker` = **Bruch je Seite** (`0.001` = 0,10 %). `replay.gebuehr_fuer()`
  gibt daraus Prozent je Seite (`* 100`); die Auswertung rechnet
  `kosten = einsatz * 2 * gebuehr`; `kosten_wendepunkt.urteil()` vergleicht mit
  `f_max` in **Prozent je Runde** (bis 30.09.2026 wurde der Bruch mit
  Prozentzeichen gedruckt - Faktor 100 zu klein).
* `gebuehr_pct` = **Prozent je Seite** (`0.1` = 0,10 %) - eigene Arme
  (`gitter`, `omniquant`, `kopier`, `kopier1zu1`, `nautilus*`). Zwei Felder, zwei
  Einheiten: wer eines setzt und das andere liest, aendert nichts.
* **Die Auswertung liest NUR `gebuehr_taker`.** Ein Arm, der nur `gebuehr_pct`
  traegt, meldet "BRUTTO und UNBEKANNT", obwohl die Zahl bekannt ist - beide
  Felder setzen (so geschehen bei `nautilus` und `nautilus_kraken_futures`).
* Der Futures-Arm `nautilus_kraken_futures` faehrt aus dem Ordner
  `nautilus_kraken`, seine Wachen heissen `wachen.futures.json`; ohne
  `auswertung_alle.WACHEN_SUFFIX` liest der Bericht die Spot-Wachen.

## Die Boerse der SPUR, nicht des Ordners

Spot und Perp kosten bei derselben Boerse verschieden viel. Die Zuordnung steht
in `replay.SPUR_BOERSE` und ist nur ein RUECKFALL - der eigene Wert in der
`wachen.json` hat Vorrang. Genau deshalb blieben zwei falsche Zuordnungen lange
unsichtbar: `gitter` stand als Perp (handelt aber BTC-USDT auf dem OKX-Spot),
`orb` stand als Spot (handelt `BTC-USDT-SWAP`). Beim Eintragen die eigene
`wachen.json` lesen, nicht den Ordner- oder Spurnamen deuten.

## Werkzeug

    cd Agenten/Handel
    .venv/Scripts/python.exe gebuehren_setzen.py              # Vorschau
    .venv/Scripts/python.exe gebuehren_setzen.py --anwenden   # mit .bak-JJJJMMTT
    .venv/Scripts/python.exe gebuehren_setzen.py --messen     # Kontosaetze abfragen

Nach dem Setzen: `auswertung_alle.py` laufen lassen und pruefen, dass nur noch
Spuren mit WIRKLICH unbekanntem Markt "BRUTTO und UNBEKANNT" melden.

## Nicht raten

Ist der Markt einer Spur nicht belegt (kein Instrument in der `wachen.json`,
Code nennt keinen), bleibt die Spur OHNE Gebuehrenfeld - "BRUTTO und UNBEKANNT"
ist dann die ehrliche Anzeige (`moondev_sniper`: pump.fun-Token, offen). Saetze
aus einem anderen Markt (Solana-Onchain 1 % bei `kopier`, Robinhood Chain 1 % bei
`robinhood_radar`) sind Modellannahmen und brauchen eine Entscheidung, keine
Messung.