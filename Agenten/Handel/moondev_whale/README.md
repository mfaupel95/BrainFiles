# Bot-Spur `moondev_whale` (Papier, mit lokalem Sprachmodell)

Das offene Interesse (Open Interest) springt - und ein Sprachmodell urteilt, ob
das ein Kauf oder ein Verkauf ist.

## Woher die Idee kommt

Der Agent `whale_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` beobachtet das
offene Interesse ueber ein Zeitfenster, erkennt eine Anomalie gegen den
Durchschnitt (`WHALE_THRESHOLD_MULTIPLIER = 1.31`) und laesst dann ein
Sprachmodell antworten: Zeile 1 `BUY`/`SELL`/`NOTHING`, Zeile 2 ein Grund,
Zeile 3 `Confidence: X%`. Seine Daten kommen von Hyperliquid, sein Urteil von
Anthropic oder DeepSeek - beides mit Schluessel.

Hier laeuft dieselbe Arbeitsteilung ohne Schluessel:

- **Daten** OKX oeffentlich (`Handel/moondev_daten.py`): `/public/open-interest`,
  `/rubik/stat/contracts/open-interest-volume` (5-Minuten-Punkte, 48 h) und
  `/market/candles` fuer den Kurs.
- **Gate** deterministisch: `|OI-Aenderung| >= max(mindest_aenderung_pct,
  schwelle_mal_mittel x mittlere absolute OI-Aenderung)`. Ohne Anomalie wird das
  Modell GAR NICHT gefragt.
- **Urteil** das lokale Modell (`Handel/llm_lokal.py`, Ollama auf
  127.0.0.1:11434, Temperatur 0, fester Seed) - Vertrag wortgleich zum Bot. Die
  Confidence ist ein Gate: unter `llm_mindest_confidence` faellt das Urteil aus.
- **Buch** `Handel/spur_buch.py` - Ratsche, Stop/Ziel, Kopie nach
  `Q:\Handel_Journal\moondev_whale` (Bedingung 4).

## Grenzen

- **Kein Live-Zweig.** Der Fremd-Agent handelt auf Hyperliquid mit echten
  Schluesseln; hier wird Papier gebucht, ein `--live` verweigert.
- **Das Modell urteilt, das Gate rechnet.** Wer wissen will, ob das Urteil etwas
  taugt, muss die geschlossenen Runden auswerten (`auswertung_alle.py`) - bis
  dahin ist die Richtung des Modells eine Behauptung, keine Messung.
- **Der Bot selbst laeuft nicht.** Er ist ein Monolith mit `main()`, braucht
  `OPENAI_KEY`/`ANTHROPIC_KEY` und haengt an der Hyperliquid-Schicht des Repos.
  Nachgebaut ist die Idee, nicht der Code.

## Aufruf

```powershell
cd Agenten/Handel/moondev_whale
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau   # was waere dran
..\scanner\.venv\Scripts\python.exe handeln.py --papier     # Papierlauf
..\scanner\.venv\Scripts\python.exe handeln.py --wachen     # Grenzen
```

Modellvergleich (welches lokale Modell den Vertrag haelt und wie lange es
braucht): `..\scanner\.venv\Scripts\python.exe ..\llm_probe.py`.

Tests ohne Netz und ohne Modell: `python -m unittest test_moondev_whale`
**aus dem Ordner `tests/`**.
