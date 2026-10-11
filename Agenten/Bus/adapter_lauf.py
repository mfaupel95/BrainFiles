#!/usr/bin/env python3
"""Ein Lauf ueber alle Fremd-Adapter (nautilus, moondev, itb) laut adapter_quellen.json.

Aufruf: python adapter_lauf.py [--vorschau]
Meldet neue Signale an den Bus (durchs Tor). --vorschau meldet nichts und zeigt nur,
welche Quellen lesbar sind. Fehlende Datei = Quelle uebersprungen, kein Fehler.
Stand je Quelle: Agenten/Bus/adapter_stand/<name>.json. Handelt nie.
"""
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

import adapter_itb       # noqa: E402
import adapter_moondev   # noqa: E402
import adapter_nautilus  # noqa: E402

STAND = os.path.join(HIER, "adapter_stand")


def _pfad(q, cfg):
    kandidaten = []
    if q.get("ort") == "werkstatt":
        wurzel = os.path.dirname(os.path.dirname(HIER))
        kandidaten.append(os.path.join(wurzel, "Werkstatt", q["datei"]))
        kandidaten.append(os.path.join(cfg.get("_basis_werkstatt", ["", "O:/Werkstatt"])[1], q["datei"]))
    else:
        kandidaten.append(q["datei"])
    return next((p for p in kandidaten if os.path.isfile(p)), None)


def lauf(cfg, vorschau=False):
    """Liste von (name, status, detail)."""
    os.makedirs(STAND, exist_ok=True)
    ergebnis = []
    for q in cfg.get("quellen", []):
        name = q.get("name", "?")
        if q.get("enabled") is not True:
            ergebnis.append((name, "aus", ""))
            continue
        p = _pfad(q, cfg)
        if p is None:
            ergebnis.append((name, "datei_fehlt", q.get("datei", "")))
            continue
        if vorschau:
            ergebnis.append((name, "lesbar", p))
            continue
        stand = os.path.join(STAND, name + ".json")
        kw = dict(size_pct=cfg.get("size_pct", 0.2), expiry_s=cfg.get("expiry_s", 180))
        mode = cfg.get("mode", "paper")
        if q["typ"] == "nautilus":
            r = adapter_nautilus.lauf(p, stand, mode=mode, **kw)
        elif q["typ"] == "moondev":
            r = adapter_moondev.lauf(p, stand, mode=mode, **kw)
        elif q["typ"] == "itb":
            r = adapter_itb.lauf(p, stand, q.get("instrument", "BTC-USDC"), **kw)
        else:
            r = ("fehler", 0, "typ unbekannt: %r" % (q["typ"],))
        ergebnis.append((name, r[0], " ".join(str(x) for x in r[1:])))
    return ergebnis


def main(argv):
    try:
        with open(os.path.join(HIER, "adapter_quellen.json"), encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError) as e:
        print("Konfig unlesbar: %s" % e)
        return 1
    for name, status, detail in lauf(cfg, "--vorschau" in argv):
        print("%-24s %-12s %s" % (name, status, detail))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
