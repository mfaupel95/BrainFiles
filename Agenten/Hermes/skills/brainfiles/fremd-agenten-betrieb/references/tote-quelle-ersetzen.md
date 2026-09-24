# Eine tote Datenquelle durch oeffentliche Endpunkte ersetzen

Gilt, wenn ein Fremd-Agent seine Daten bei einem Dienst holt, der gar nicht mehr
antwortet (kein HTTP-Status, nur Connect-Timeout) - dann hilft KEIN Schluessel,
sondern nur ein Ersatzweg. Messungen, Bauart und die Grenze des Verfahrens.

## Bauart: Ersatzmodul mit identischer Schnittstelle

- Neue Datei NEBEN der toten Quelle (`api_frei.py` neben `api.py`) im selben
  Paket. Klasse und Methodennamen sind identisch, die Importzeile der Agenten
  wird getauscht (`from src.agents.api_frei import MoonDevAPI`) - mit dem
  Rueckweg als Kommentar daneben.
- Erstversuch bleibt die echte Quelle (kurze Frist), Ersatz greift danach; der
  Agent sieht EINE Schnittstelle, nicht zwei Wege.
- Die Methode liefert ein DataFrame mit den Spaltennamen, die der Agent ohnehin
  selbst setzt (`df.columns = [...]`) - also stimmen REIHENFOLGE und
  Bedeutung je Position, nicht nur die Namen. Ein vertauschtes Paar
  (long/short) faellt nirgends auf und rechnet still falsch.
- Die Klasse kapselt je Methode `try/except` und gibt bei Ausfall `None` zurueck;
  der Agent ueberspringt dann seinen Zyklus.

## Endpunkte je Methode (gemessen)

| Gebraucht | Oeffentlich tragfaehig | Anmerkung |
|---|---|---|
| Funding-Saetze aller Symbole | Binance `/fapi/v1/premiumIndex` | ALLE Symbole in EINEM Aufruf (gemessen ~910 Zeilen), Feld `lastFundingRate` = 8-h-Satz; Jahr = `rate * 3 * 365` |
| Open Interest (wenige Symbole) | Binance `/fapi/v1/openInterest?symbol=` | ein Symbol je Aufruf; Preis aus `premiumIndex` (`markPrice`) |
| Open Interest (alle Symbole) | OKX `/api/v5/public/open-interest?instType=SWAP` | ein Aufruf, Feld `oiCcy` (Menge) und `oiUsd` |
| Liquidationen | OKX `/api/v5/public/liquidation-orders?instType=SWAP&uly=BTC-USDT&state=filled&limit=100` | `instType` UND `uly`/`instId` sind PFLICHT (ohne: HTTP 400). Binance `/fapi/v1/allForceOrders` ist **404** (nicht mehr oeffentlich) |
| nicht ersetzbar | Copybot-Positionen, Folgelisten, "recent transactions" | dienst-eigene Datenbank; `None` statt Nullen |

Zwei Fallen an den Boersendaten:

- **`side`-Konvention ist bei OKX dieselbe wie bei Binance:** `SELL` = Long
  liquidiert, `BUY` = Short liquidiert. OKX liefert klein (`sell`/`buy`) -
  `side.upper()` genuegt.
- **`sz` bei OKX-SWAP sind KONTRAKTE, keine Coins.** USD-Wert =
  `sz * ctVal * bkPx`; `ctVal` kommt aus `/api/v5/public/instruments?instType=SWAP`
  (je Instrument, z. B. 0,01 BTC). Wer `sz` als Coins liest, berichtet um
  Groessenordnungen falsche Volumina.

## Beweis, der traegt

Je Agent EIN echter Lauf mit sichtbarer Ausgabe und ZAHLEN: Anzahl Saetze /
Ereignisse und die USD-Summen je Zeitfenster (1 h, 4 h). Zahlen aus dem Lauf
nennen, nicht "Datenquelle ersetzt".

Beobachtete Werte als Plausibilitaetsmassstab (24.09.2026): BTC-OI ~8 Mrd USD,
ETH ~6 Mrd USD (Binance); 300 Liquidations-Zeilen aus drei `uly`-Aufrufen
(BTC/ETH/SOL).

## Wenn der Laufzeittest schon sauber sein soll

- `python -u` bzw. `PYTHONUNBUFFERED=1`, sonst ist das Log trotz laufendem
  Prozess leer (Blockpuffer) - ein Timeout-Kill wirft die Ausgabe weg.
- Alle Key-Namen exportieren, die der Konstruktor prueft. Agenten verlangen oft
  zwei bis drei (Analyse-Anbieter neben dem Datenweg) und sterben VOR der ersten
  Datenzeile; die Haus-Bruecke als `*_BASE_URL` mitgeben.
- Nach dem Tausch `py_compile` ueber die angefassten Dateien und ein Kurzlauf je
  Agent - im selben Durchgang `git -C <klon> diff --numstat` je Datei lesen: die
eigene Aenderung ist 4/1 (Kommentarzeilen plus Import), alles Groessere ist
  fremde Arbeit und bleibt liegen.
