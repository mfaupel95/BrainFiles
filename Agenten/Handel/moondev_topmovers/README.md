# Bot-Spur `moondev_topmovers` (Papier)

Momentum der letzten 24 Stunden - aber nur unterhalb der Ueberhitzungsgrenze.

## Woher die Idee kommt

Der Agent `new_or_top_agent` aus `Werkstatt/Repos/moon-dev-ai-agents` macht genau das:
er sieht sich die neuen und die staerksten Coins der letzten 24 Stunden an und empfiehlt daraus. Sein Urteil faellt in einem Sprachmodell, seine Daten kommen ueber die
CoinGecko-**Pro**-API (Schluessel noetig). Beides laesst sich hier nicht sauber
nachbilden, deshalb:

- **Daten** ueber die oeffentliche CoinGecko-/Binance-API (`Handel/moondev_daten.py`)
  - dieselben Endpunkte, ohne Schluessel,
- **Regel** deterministisch im Haus: long bei einer 24h-Aenderung zwischen +8 % und +40 % und mindestens 20 Mio USD Tagesvolumen. Ueber +40 % gilt der Zug als abgefahren.
- **Buch** ein Haus-Buch (`Handel/moondev_buch.py`): Zustand, Journal, Kopie nach
  `Q:\Handel_Journal\moondev_topmovers` (Bedingung 4), Ratsche, Stop und Ziel.

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
cd Agenten/Handel/moondev_topmovers
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau   # was waere dran
..\scanner\.venv\Scripts\python.exe handeln.py --papier     # Papierlauf
..\scanner\.venv\Scripts\python.exe handeln.py --wachen     # Grenzen
```

Im Dauerlauf steht sie als `moondev_topmovers` in `dauerlauf.SPUREN`. Tests ohne Netz:
`python -m unittest test_moondev_topmovers` **aus dem Ordner `tests/`**.
