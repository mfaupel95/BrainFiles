# Bot-Spur `moondev_sentiment` (Papier, mit lokalem Sprachmodell)

Was die Ueberschriften sagen - und ein Sprachmodell macht daraus long, short
oder nichts.

## Woher die Idee kommt

Der Agent `sentiment_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` sammelt
Texte zu seinen Tokens, bewertet die Stimmung (zwischen -1 und +1) und meldet
erst, wenn der Betrag ueber `SENTIMENT_ANNOUNCE_THRESHOLD` (0.4) liegt. Seine
Texte kommen von Twitter ueber `twikit` (Konto/Cookies noetig), seine Bewertung
aus einem HuggingFace-Modell.

Hier laeuft dieselbe Idee mit dem, was ohne Konto oeffentlich ist:

- **Daten** die Titel der neuesten Meldungen aus den oeffentlichen RSS-Feeds von
  CoinDesk, Cointelegraph und CryptoSlate (`Handel/moondev_daten.py`), dazu der
  BTC-Kurs aus OKX-Kerzen (24 h und 1 h Aenderung).
- **Gate** ohne frische Schlagzeilen kein Urteil: erst ab
  `mindest_schlagzeilen` Ueberschriften wird gefragt. Das ist die Uebertragung
  der Bot-Schwelle 0.4 - hier nicht als Zahl zwischen -1 und 1, sondern als
  Mindestmenge an Text.
- **Urteil** das lokale Modell (`Handel/llm_lokal.py`): es liest die
  Schlagzeilen und antwortet im Vertrag des Bots (`BUY`/`SELL`/`NOTHING`,
  `Confidence: X%`). Unter `llm_mindest_confidence` faellt das Urteil aus.
- **Buch** `Handel/spur_buch.py`, Kopie nach
  `Q:\Handel_Journal\moondev_sentiment` (Bedingung 4).

## Grenzen

- **Kein Live-Zweig.** Papier; ein `--live` verweigert.
- **Ueberschriften, keine Artikel.** Bewertet wird der Titel, den der Markt
  zuerst sieht - nicht der Inhalt, nicht die Wirkung. Drei Feeds, nicht "die
  Presse".
- **Nicht der Bot.** Er bewertet Tweets mit einem eigenen Modell; hier liest ein
  lokales Modell Schlagzeilen. Dieselbe Idee, andere Quelle, anderer Text.
- **Das Modell urteilt, das Gate rechnet.** Ob die Richtung taugt, sagen erst
  die geschlossenen Runden (`auswertung_alle.py`).

## Aufruf

```powershell
cd Agenten/Handel/moondev_sentiment
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau   # was waere dran
..\scanner\.venv\Scripts\python.exe handeln.py --papier     # Papierlauf
..\scanner\.venv\Scripts\python.exe handeln.py --wachen     # Grenzen
```

Tests ohne Netz und ohne Modell: `python -m unittest test_moondev_sentiment`
**aus dem Ordner `tests/`**.
