"""Einen CoinGecko-Abzug als Gegenprobe aufzeichnen.

Der Adapter uebersetzt Binance-Daten in die Sprache der Feed-Spuren. Ob er das
RICHTIG tut, kann nur ein Vergleich mit der Wirklichkeit zeigen - und die
Wirklichkeit der Spuren im Betrieb ist CoinGecko. Verglichen wird die
Groessenordnung, nicht die Stelle hinter dem Komma: zwei Boersen sind zwei
Preise, und CoinGecko mittelt ueber viele.

Einmal aufzeichnen, dann liegt der Abzug als Beleg neben den Daten
(daten/historie/coingecko_probe.json). Kein Schluessel noetig; die freie
Schnittstelle begrenzt die Abrufe, deshalb genau EIN Aufruf.
"""

import json
import os
import time
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(HIER, "daten", "historie", "coingecko_probe.json")
ADRESSE = ("https://api.coingecko.com/api/v3/coins/markets"
           "?vs_currency=usd&order=market_cap_desc&per_page=250&page=1"
           "&sparkline=false")


def main():
    anfrage = urllib.request.Request(ADRESSE, headers={"User-Agent": "BrainFiles/1.0"})
    with urllib.request.urlopen(anfrage, timeout=30) as a:
        maerkte = json.load(a)
    daten = {"abgerufen": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "quelle": ADRESSE,
             "maerkte": [{"symbol": m.get("symbol"), "name": m.get("name"),
                          "current_price": m.get("current_price"),
                          "total_volume": m.get("total_volume")}
                         for m in maerkte]}
    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    with open(ZIEL, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("%d Maerkte nach %s" % (len(daten["maerkte"]), ZIEL))


if __name__ == "__main__":
    main()