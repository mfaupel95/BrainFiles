"""5m-Historie fuer mosaic nachladen (Binance, oeffentlich, kein Schluessel).

Nur 5m: 30m und 4H leitet der Replay aus derselben Reihe ab (gleiche
Zeitachse, kein Versatz, keine zweite Datenquelle).

Aufruf:  python 5m_historie_holen.py --tage 120
"""
import argparse
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import historie_binance as hb                                      # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tage", type=int, default=120)
    p.add_argument("--instrumente", default="BTC-USDC,ETH-USDC,SOL-USDC")
    a = p.parse_args()

    bis = int(time.time() * 1000)
    von = bis - a.tage * 86_400_000
    for inst in [x.strip() for x in a.instrumente.split(",") if x.strip()]:
        t0 = time.time()
        reihen = hb.von_binance(inst, "5M", von, bis)
        gesamt = hb.speichere(inst, "5M", reihen)
        print("%s 5m: %d geholt, %d im Bestand, %.1f s"
              % (inst, len(reihen), gesamt, time.time() - t0))
    hb._schreibe_stand()


if __name__ == "__main__":
    main()