"""Erreichbarkeit der Drawdown-Ratsche je Spur.

Der scanner hatte eine Ratsche, deren Schwelle (150 USD) ueber dem hoechsten
je erreichten Gewinnstand (140.24 USD) lag - sie konnte nie ausloesen. Diese
Pruefung stellt dieselbe Frage an JEDE Spur, und zwar mit der jeweiligen
eigenen Rechnung: jede Spur wird ueber ihr eigenes lage() befragt, nicht ueber
eine nachgebaute Formel. Eine nachgebaute Formel prueft die Formel, nicht die
Spur.

Kein Schreiber: liest nur wachen.json und handelsjournal.csv.
"""

import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = HIER                       # dieses Skript liegt in Handel/

# spur -> (ordner, modul, wachen-datei). swap erbt die Wachen von xperp
# (swap/handeln.py: import wachen_xperp as wx) - deshalb dasselbe Modul,
# aber die eigene wachen.json.
SPUREN = [
    ("xperp",  "xperp",  "xperp",  "wachen_xperp",  "wachen.json"),
    ("swap",   "swap",   "xperp",  "wachen_xperp",  "wachen.json"),
    ("orbk",   "orbk",   "orbk",   "wachen_orb",    "wachen.json"),
    ("kraken", "kraken", "kraken", "wachen_kraken", "wachen.json"),
]

# Was jede Spur als Nenner benutzt (aus dem jeweiligen Modul gelesen, nicht
# geraten) - nur zur Anzeige der Schwelle in USD/EUR.
NENNER = {
    "xperp":  "max_margin_gesamt_usd",
    "swap":   "max_margin_gesamt_usd",
    "orbk":   "kill_switch_gesamt_usd",
    "kraken": "max_gesamt_eur",
}


def befrage(spur, ordner, modulordner, modulname, wachendatei):
    md = os.path.join(HANDEL, modulordner)
    if md not in sys.path:
        sys.path.insert(0, md)
    for m in [k for k in list(sys.modules) if k in (modulname, "basis")]:
        del sys.modules[m]
    mod = __import__(modulname)

    wpath = os.path.join(HANDEL, ordner, wachendatei)
    with open(wpath, "r", encoding="utf-8") as f:
        w = json.load(f)
    journal = os.path.join(HANDEL, ordner, "handelsjournal.csv")

    s = mod.lage(w, journal, {})

    prozent = w.get("drawdown_halbierung_prozent", 15.0)
    nenner = w.get(NENNER[spur])
    schwelle = prozent / 100.0 * nenner
    hoch = s.get("hoechststand_usd", 0.0)

    return {
        "spur": spur,
        "prozent": prozent,
        "nenner": NENNER[spur],
        "nenner_wert": nenner,
        "schwelle": schwelle,
        "hoechststand": hoch,
        "ruecklauf": s.get("ruecklauf_usd", 0.0),
        "faktor": s.get("groessenfaktor"),
        "im_gewinn": hoch == 0 or schwelle <= hoch,
    }


def main():
    print("%-8s %7s %-22s %9s %10s %11s %7s %s"
          % ("Spur", "Prozent", "Nenner", "Schwelle", "Hoechstst.", "Ruecklauf",
             "Faktor", "im_gewinn"))
    print("-" * 96)
    spaet = []
    fehler = []
    for spur, ordner, modulordner, modulname, wachendatei in SPUREN:
        try:
            r = befrage(spur, ordner, modulordner, modulname, wachendatei)
        except Exception as e:                                    # noqa: BLE001
            print("%-8s FEHLER %s: %s" % (spur, type(e).__name__, e))
            fehler.append(spur)
            continue
        print("%-8s %6.1f%% %-22s %9.2f %10.2f %11.2f %7s %s"
              % (r["spur"], r["prozent"], "%s=%s" % (r["nenner"], r["nenner_wert"]),
                 r["schwelle"], r["hoechststand"], r["ruecklauf"],
                 r["faktor"], "ja" if r["im_gewinn"] else "erst im Minus"))
        if not r["im_gewinn"]:
            spaet.append(r["spur"])

    print()
    if fehler:
        print("NICHT GEPRUEFT (Fehler): %s" % ", ".join(fehler))
    if spaet:
        print("GREIFT ERST IM MINUS: %s" % ", ".join(spaet))
    if not fehler and not spaet:
        print("Alle Ratschen greifen noch im Gewinn (oder die Spur ist noch ohne Runden).")


if __name__ == "__main__":
    main()
