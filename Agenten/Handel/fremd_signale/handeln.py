#!/usr/bin/env python3
"""Papier-Ausfuehrung der durchs Tor gelassenen Fremd-Signale.

Aufruf: python handeln.py --vorschau | --papier   (--live gibt es nicht)

--vorschau  liest Journal und Buch, rechnet, schreibt NICHTS.
--papier    schreibt das Papierbuch (fremd_signale/zustand.json).
Startet nichts von selbst; der Dauerlauf kennt diese Spur nicht.
Kurse: oeffentlich (Kraken-Ticker fuer "X/USD", OKX fuer "...-SWAP" und Spot "BASE-USDC"), kein Schluessel.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scanner"))
sys.path.insert(0, str(WURZEL.parent / "Bus"))

import atomar          # noqa: E402
import fremd_papier    # noqa: E402
import fremd_tor       # noqa: E402
import journal         # noqa: E402

ZUSTAND = HIER / "zustand.json"


def kurs(inst):
    if inst.endswith("-SWAP"):
        import okx
        return okx.letzter_kurs(inst)
    if "-" in inst:  # OKX-Spot, z. B. BTC-USDC (oeffentlicher Ticker, User-Agent noetig)
        req = urllib.request.Request("https://www.okx.com/api/v5/market/ticker?instId=" + inst,
                                     headers={"User-Agent": "brainfiles/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return float(json.load(r)["data"][0]["last"])
    paar = inst.replace("/", "")
    url = "https://api.kraken.com/0/public/Ticker?pair=" + paar
    with urllib.request.urlopen(url, timeout=10) as r:
        d = json.load(r)
    if d.get("error"):
        raise OSError(str(d["error"])[:80])
    return float(next(iter(d["result"].values()))["c"][0])


def main(argv):
    if "--live" in argv:
        print("Kein Live-Zweig: diese Spur ist nur Papier. --live verweigert.")
        return 2
    if "--papier" not in argv and "--vorschau" not in argv:
        print(__doc__)
        return 2
    schreiben = "--papier" in argv
    wache = fremd_tor.lade()
    if wache is None or wache.get("fremd_signale_erlaubt") is not True:
        print("Tor zu (fremd_signale_erlaubt nicht true) - nichts zu tun.")
        return 0
    z = atomar.lade_json(ZUSTAND, fremd_papier.leer)
    jetzt = int(time.time())
    fremd_papier.stops_pruefen(z, kurs, wache, jetzt)
    for sid, ok, grund in fremd_papier.verarbeite(z, journal.lesen(), kurs, wache, jetzt):
        print("%s  %s  %s" % (sid[:8], "ausgefuehrt" if ok else "abgelehnt", grund))
    print("offen: %d | geschlossen: %d | PnL %.2f USD"
          % (len(z["offen"]), len(z["geschlossen"]), z["pnl_usd"]))
    if schreiben:
        atomar.schreibe_json(ZUSTAND, z)
    else:
        print("(Vorschau - nichts geschrieben)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
