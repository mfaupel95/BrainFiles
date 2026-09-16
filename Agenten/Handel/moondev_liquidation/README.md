# Bot-Spur `moondev_liquidation` (Papier, mit lokalem Sprachmodell)

Zwangsschluesse in beide Richtungen - und ein Sprachmodell urteilt, ob der Markt
dabei einen Boden oder einen Top bildet.

## Woher die Idee kommt

Der Agent `liquidation_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` summiert
die Zwangsschluesse der letzten Minuten getrennt nach Seite, vergleicht sie mit
dem vorigen Stand und laesst ein Sprachmodell antworten (`LIQUIDATION_ANALYSIS_
PROMPT`): Zeile 1 `BUY`/`SELL`/`NOTHING`, Zeile 2 ein Grund, Zeile 3
`Confidence: X%`. Seine Daten kommen ueber die Moon-Dev-API
(`MOONDEV_API_KEY`), sein Urteil von Claude oder DeepSeek.

Hier laeuft dieselbe Arbeitsteilung ohne Schluessel:

- **Daten** OKX oeffentlich: `/public/liquidation-orders?instType=SWAP&uly=
  BTC-USDT&state=filled`. `posSide` nennt die Seite des Kontos, das liquidiert
  wurde (`long` = ein Long wurde zwangsgeschlossen). `sz` steht in KONTRAKTEN -
  der USD-Wert entsteht erst ueber `ctVal` (0.01 BTC je Kontrakt); ohne diese
  Zahl waeren alle Summen um Faktor 100 falsch.
- **Gate** deterministisch: OKX gibt nur die NEUESTEN 100 Saetze heraus. Darum
  wird nicht ein festes Fenster gerechnet, sondern die **Spanne gemessen** und
  die Summe darauf bezogen (USD je Stunde). Geurteilt wird nur, wenn die Spanne
  zwischen 10 und 240 Minuten frisch ist, die Rate ueber
  `mindest_rate_usd_pro_stunde` liegt UND das Ungleichgewicht deutlich ist
  (Long-Anteil >= 0.75 oder <= 0.25) oder eine Kaskade laeuft. Die Schwellen
  stammen aus einer Messung vom 17.09.2026 (siehe `wachen.json`,
  `_schwellen_herkunft`).
- **Urteil** das lokale Modell (`Handel/llm_lokal.py`, Ollama, Temperatur 0,
  fester Seed), Vertrag wie beim Bot. Confidence unter
  `llm_mindest_confidence` = kein Handel.
- **Buch** `Handel/spur_buch.py`, Kopie nach
  `Q:\Handel_Journal\moondev_liquidation` (Bedingung 4).

## Grenzen

- **Kein Live-Zweig.** Papier; ein `--live` verweigert.
- **Ein Ausschnitt, kein Gesamtbild.** OKX veroeffentlicht nicht alle
  Zwangsschluesse, sondern die neuesten 100 gefuellten. Die Spur rechnet den
  Ausschnitt ehrlich (Spanne, Rate, Anteil) und behauptet nichts ueber das, was
  ausserhalb liegt.
- **Das Modell urteilt, das Gate rechnet.** Ob die Richtung taugt, sagen erst
  die geschlossenen Runden (`auswertung_alle.py`).

## Aufruf

```powershell
cd Agenten/Handel/moondev_liquidation
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau   # was waere dran
..\scanner\.venv\Scripts\python.exe handeln.py --papier     # Papierlauf
..\scanner\.venv\Scripts\python.exe handeln.py --wachen     # Grenzen
```

Tests ohne Netz und ohne Modell: `python -m unittest test_moondev_liquidation`
**aus dem Ordner `tests/`**.
