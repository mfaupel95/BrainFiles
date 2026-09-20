# moondev_signalwelle

Ehrliches Gegenstueck zu VIP-Signal-Kanaelen (Anlass: Screenshot 20.09.2026,
NVDAUSDT Perpetual 10x Hebel, +27 % ROI, ohne Verlusthistorie).

## Warum diese Spur

Ein Kanal-Signal ist eine Gewinnkarte ohne Track Record (Survivorship Bias),
mit Hebel ohne sichtbare Stop-Regel, oft auf synthetischen Produkten, die auf
keiner Haus-Boerse handelbar sind. Diese Spur bildet dieselbe Grundidee -
kurzfristige starke Kursbewegung als Signal - deterministisch und ohne Hebel
nach:

- **Daten**: CoinGecko `/coins/markets` mit `price_change_percentage=1h,24h`,
  oeffentlich, ohne Schluessel (`Handel/moondev_daten.py`).
- **Regel**: Long, wenn die 1h-Aenderung zwischen `mindest_plus_1h_pct` und
  `hoechst_plus_1h_pct` liegt UND das Tagesvolumen ueber
  `mindest_volumen_usd` - eine Welle, die gerade anrollt, keine Spike-Kerze
  und kein totes Volumen.
- **Buch**: Haus-Buch ueber `Handel/spur_buch.py` (Zustand, Journal,
  Q:-Spiegel, Ratsche, Stop/Ziel) - dieselbe Mechanik wie
  `moondev_topmovers`, nur 1h statt 24h.
- **Kein Hebel, kein Live**: Spot-Papier mit Hausrisiko. `--live` verweigert
  ausdruecklich mit Verweis auf den Hebel-Unterschied zum VIP-Kanal.

## Unterschied zu moondev_topmovers

| | topmovers | signalwelle |
|---|---|---|
| Fenster | 24h | 1h |
| Mindestbewegung | +8 % | +3 % |
| Ueberhitzungsgrenze | +40 % | +15 % |
| Stop | 8 % (5-12 %) | 7 % (6-12 %) |
| Idee | Tagesbewegung ist schon gelaufen | Welle rollt gerade an |

## Grenzen (wachen.json)

Risiko 5 USD/Position, 3 Plaetze, Buchrisiko 15 USD, Ratsche bei 15 USD
Drawdown, Kill-Switch bei 45 USD. `handel_erlaubt: false` - reine
Papierbeobachtung bis zur Bewaehrung (Bedingung 1: 50 Runden netto positiv).

## Nachweis (20.09.2026)

8/8 Tests gruen (`tests/test_moondev_signalwelle.py`), kein Schreiben in den
echten Spurenordner (Modulwaechter), Vorschau schreibt nichts, Papierlauf
bucht und spiegelt nach Q:, `--live` verweigert mit Begruendung.
