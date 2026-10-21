# Bot-Spur `moondev_listingarb` (Papier)

Grosse Coins, die bei Binance (noch) nicht handelbar sind - die Wette des Bots auf ein kommendes Listing.

## Woher die Idee kommt

Der Agent `listingarb_agent` aus `Werkstatt/moon-dev-ai-agents` macht genau das:
er sucht Coins, die gross sind, aber an einer grossen Boerse noch fehlen, und kauft sie vor dem Listing. Sein Urteil faellt in einem Sprachmodell, seine Daten kommen ueber die
CoinGecko-**Pro**-API (Schluessel noetig). Beides laesst sich hier nicht sauber
nachbilden, deshalb:

- **Daten** ueber die oeffentliche CoinGecko-/Binance-API (`Handel/moondev_daten.py`)
  - dieselben Endpunkte, ohne Schluessel,
- **Regel** deterministisch im Haus: long, wenn ein Coin in den Top 100 nach Marktkapitalisierung steht, mindestens 1 Mrd USD Marktkapital und 30 Mio USD Tagesvolumen hat - und bei Binance NICHT handelbar ist.
- **Buch** ein Haus-Buch (`Handel/moondev_buch.py`): Zustand, Journal, Kopie nach
  `Q:\Handel_Journal\moondev_listingarb` (Bedingung 4), Ratsche, Stop und Ziel.

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
cd Agenten/Handel/moondev_listingarb
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau   # was waere dran
..\scanner\.venv\Scripts\python.exe handeln.py --papier     # Papierlauf
..\scanner\.venv\Scripts\python.exe handeln.py --wachen     # Grenzen
```

Im Dauerlauf steht sie als `moondev_listingarb` in `dauerlauf.SPUREN`. Tests ohne Netz:
`python -m unittest test_moondev_listingarb` **aus dem Ordner `tests/`**.
