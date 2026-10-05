"""Wie gross ist das Universum, mit dem eine Feed-Spur im Ruecklauf rechnet?

T-144: die Signalwelle wurde mit "41 Symbole gegen 250 Coins" verglichen. Das
ist die falsche Gegenueberstellung - `anzahl_coins` (250) begrenzt nichts,
weil auf der Platte nur 41 Stundenreihen liegen. Der Unterschied zwischen den
beiden Zahlen ist nicht die Verzerrung; die Verzerrung ist der Trichter, den
die Regel danach anlegt.

Dieses Werkzeug misst den Trichter an der Stelle, an der er entsteht:
`Bestand.tafel_stunde()` liefert je Zeitpunkt die Kandidaten, und die Wache
nennt `anzahl_coins`, `mindest_volumen_usd` und das 1h-Band. Jede Stufe wird
ueber die Zeitpunkte gemittelt.

Es liest nur von der Platte (`daten/historie/feed/`) und braucht kein Netz.

    python universum_messen.py                      # alle Feed-Spuren
    python universum_messen.py --spur moondev_signalwelle
    python universum_messen.py --stichprobe 400    # schneller, mit Toleranz
"""
import argparse
import json
import os
import sys
import time

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import moondev_historie as mh                                   # noqa: E402

FEED = os.path.join(HANDEL, "daten", "historie", "feed")
STICHTPROBE_VORGABE = 400

# takt -> (Quelle in der Wache, Liste-Feld, Untergrenze, Obergrenze)
SPUREN = {
    "moondev_signalwelle": {
        "takt": "1H", "anzahl": "anzahl_coins",
        "tor": ("volumen_24h", "mindest_volumen_usd", "min"),
        "band": ("aenderung_1h", "mindest_plus_1h_pct",
                 "hoechst_plus_1h_pct"),
    },
    "moondev_topmovers": {
        "takt": "1D", "anzahl": "anzahl_coins",
        "tor": ("volumen_24h", "min_volumen_24h_usd", "min"),
        "band": ("aenderung_24h", "min_plus_24h_pct", "max_plus_24h_pct"),
    },
    "moondev_marktlage": {
        "takt": "1D", "anzahl": "anzahl_coins",
        "tor": None, "band": None,
    },
}


def _mittel(x):
    return sum(x) / float(len(x)) if x else 0.0


def lade_wachen(spur):
    pfad = os.path.join(HANDEL, spur, "wachen.json")
    if not os.path.isfile(pfad):
        return None
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def misse(spur, stichprobe=STICHTPROBE_VORGABE, grenze=2000):
    """Alles, was T-144 braucht - als Dict, damit ein Test es pruefen kann."""
    bau = SPUREN[spur]
    takt = bau["takt"]
    w = lade_wachen(spur) or {}
    top = int(w.get(bau["anzahl"], 250) or 250)

    b = mh.Bestand()
    symbole = b.laden(takt)
    zeiten = b.schritte(mindest_symbole=grenze)

    schritt = max(1, len(zeiten) // max(1, int(stichprobe)))
    punkte = zeiten[::schritt]

    n_roh, n_begrenzt, n_tor, n_band = [], [], [], []
    for ts in punkte:
        if takt == "1H":
            z = b.tafel_stunde(ts)
        else:
            z = b.tafel(ts, top=top)
            z = list(z.values())
        n_roh.append(len(z))
        z = z[:top]
        n_begrenzt.append(len(z))
        if bau["tor"]:
            feld, schluessel, _ = bau["tor"]
            if schluessel in w:
                grenze_w = float(w[schluessel])
                z = [r for r in z if _zahl(r.get(feld)) >= grenze_w]
        n_tor.append(len(z))
        if bau["band"]:
            feld, lo_s, hi_s = bau["band"]
            if lo_s in w and hi_s in w:
                lo, hi = float(w[lo_s]), float(w[hi_s])
                z = [r for r in z
                     if lo <= _zahl(r.get(feld)) <= hi]
        n_band.append(len(z))

    return {
        "spur": spur,
        "takt": takt,
        "symbole_auf_der_platte": len(symbole),
        "symbole_im_taguniversum": len(mh._lade_universum()),
        "anzahl_coins": top,
        "zeitpunkte": len(zeiten),
        "schritte": schritt,
        "stichproben": len(punkte),
        "roh": _kennzahlen(n_roh),
        "begrenzt": _kennzahlen(n_begrenzt),
        "nach_tor": _kennzahlen(n_tor),
        "nach_band": _kennzahlen(n_band),
    }


def _zahl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _kennzahlen(x):
    return {"min": min(x) if x else 0, "max": max(x) if x else 0,
            "mittel": round(_mittel(x), 3)}


def bericht(spur, m):
    z = (m["symbole_auf_der_platte"], m["symbole_im_taguniversum"])
    aus = ["%s (%s)" % (spur, m["takt"])]
    aus.append("  Platte: %d Symbole mit %s-Reihen, Tages-Universum %d"
               % (z[0], m["takt"], z[1]))
    aus.append("  anzahl_coins=%d begrenzt auf: %d Symbole (Mittel %.1f)"
               % (m["anzahl_coins"], m["begrenzt"]["max"],
                  m["begrenzt"]["mittel"]))
    aus.append("  nach dem Volumentor:              %d (Mittel %.1f)"
               % (m["nach_tor"]["max"], m["nach_tor"]["mittel"]))
    aus.append("  nach dem Regel-Band:              %d (Mittel %.3f)"
               % (m["nach_band"]["max"], m["nach_band"]["mittel"]))
    aus.append("  gemessen: %d Zeitpunkte, je %d. = %d Stichproben"
               % (m["zeitpunkte"], m["schritte"], m["stichproben"]))
    return "\n".join(aus)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--spur", default=None, choices=sorted(SPUREN))
    p.add_argument("--stichprobe", type=int, default=STICHTPROBE_VORGABE)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    spuren = [a.spur] if a.spur else sorted(SPUREN)
    t0 = time.time()
    ergebnis = {}
    for spur in spuren:
        m = misse(spur, a.stichprobe)
        ergebnis[spur] = m
        if not a.json:
            print(bericht(spur, m))
            print()
    if a.json:
        print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())