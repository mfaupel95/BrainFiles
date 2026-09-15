# Bot-Spur `moondev_marktlage` (Papier)

BTC-Regime aus Kurs und Marktbreite - ein Coin allein sagt wenig, wenn der ganze Markt dagegen laeuft.

## Woher die Idee kommt

Der Agent `coingecko_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` macht genau das:
er beschreibt die Lage des Gesamtmarkts und leitet daraus eine Richtung ab. Sein Urteil faellt in einem Sprachmodell, seine Daten kommen ueber die
CoinGecko-**Pro**-API (Schluessel noetig). Beides laesst sich hier nicht sauber
nachbilden, deshalb:

- **Daten** ueber die oeffentliche CoinGecko-/Binance-API (`Handel/moondev_daten.py`)
  - dieselben Endpunkte, ohne Schluessel,
- **Regel** deterministisch im Haus: long, wenn BTC 24h mindestens +2 % steht UND mindestens 60 % der Top-100-Coins im Plus liegen; short spiegelbildlich bei -2 % und hoechstens 40 %.
- **Buch** ein Haus-Buch (`Handel/moondev_buch.py`): Zustand, Journal, Kopie nach
  `Q:\Handel_Journal\moondev_marktlage` (Bedingung 4), Ratsche, Stop und Ziel.

## Grenzen

- **Kein Live-Zweig.** Die Fremd-Agenten handeln mit echten Schluesseln
  (Hyperliquid/Solana); diese Spur bucht Papier, ein `--live` verweigert.
- **Kein Sprachmodell.** Was der Bot "empfiehlt", ist hier eine nachrechenbare
  Regel. Wer das Urteil des Bots will, braucht einen LLM-Schluessel - dann waere
  es eine andere Spur mit anderem Charakter.
- **Nicht der Bot selbst.** Die Datenschicht ist dieselbe Idee, nicht derselbe
  Code: der Bot ist ein Monolith mit `main()` und laesst sich nicht als Funktion
  aufrufen (anders als `moondev_funding`, das eine echte Bot-Funktion nutzt).

## Aufruf

```powershell
cd Agenten/Handel/moondev_marktlage
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau   # was waere dran
..\scanner\.venv\Scripts\python.exe handeln.py --papier     # Papierlauf
..\scanner\.venv\Scripts\python.exe handeln.py --wachen     # Grenzen
```

Im Dauerlauf steht sie als `moondev_marktlage` in `dauerlauf.SPUREN`. Tests ohne Netz:
`python -m unittest test_moondev_marktlage` **aus dem Ordner `tests/`**.
