#!/usr/bin/env python3
"""Order-Plaene fuer das OKX-Demo aus den durchs Tor gelassenen Fremd-Signalen.

Aufruf: python demo_plan.py --vorschau | --vormerken | --verwerfen <instrument>   (kein --live, sendet nie selbst)

--vorschau   liest Journal und Demo-Buch, gibt die Plaene als JSON-Zeilen aus, schreibt NICHTS.
--vormerken  dito, haelt die Positionen im Demo-Buch (fremd_signale/demo_zustand.json) fest.
--verwerfen  nimmt eine vorgemerkte Position wieder aus dem Buch (Order abgelehnt/nicht gefuellt
             bzw. nach dem Verkauf), damit Buch und Boerse zusammenpassen.
Ausfuehren tut Hermes: je Plan `spot_place_order` (okx-agentkit) mit genau diesen args.
Ist das Tor zu, passiert nichts.
"""
import json
import sys
import time
import importlib.util
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scanner"))
sys.path.insert(0, str(WURZEL.parent / "Bus"))

import atomar        # noqa: E402
import fremd_demo    # noqa: E402
import fremd_papier  # noqa: E402
import fremd_tor     # noqa: E402
import journal       # noqa: E402

ZUSTAND = HIER / "demo_zustand.json"


def _kurs_fn():
    spec = importlib.util.spec_from_file_location("fremd_handeln", HIER / "handeln.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.kurs


def plaene(zustand, zeilen, kurs_fn, wache, jetzt):
    """Journal abarbeiten. Liefert [(id, ok, plan_oder_grund)]; nur Demo-Signale."""
    aus = []
    for z in zeilen:
        if not isinstance(z, dict) or z.get("was") != "signal":
            continue
        sid = z.get("id")
        if not sid or sid in zustand["verarbeitet"]:
            continue
        try:
            signal = json.loads(z.get("text") or "")
        except ValueError:
            zustand["verarbeitet"].append(sid)
            continue
        if not isinstance(signal, dict) or signal.get("mode") != "demo":
            continue  # Papier-Signale gehoeren dem Papierbuch, nicht erneut markieren
        zustand["verarbeitet"].append(sid)
        try:
            preis = kurs_fn(signal.get("instrument"))
        except Exception as f:  # noqa: BLE001
            aus.append((sid, False, "Kurs nicht lesbar: %s" % type(f).__name__))
            continue
        aus.append((sid,) + fremd_demo.plane(zustand, signal, preis, wache, sid, jetzt))
    zustand["verarbeitet"] = zustand["verarbeitet"][-500:]
    return aus


def main(argv):
    if "--live" in argv:
        print("Kein Live-Zweig: nur Demo. --live verweigert.")
        return 2
    if "--verwerfen" in argv:
        i = argv.index("--verwerfen")
        if i + 1 >= len(argv):
            print("--verwerfen braucht ein Instrument.")
            return 2
        z = atomar.lade_json(ZUSTAND, fremd_papier.leer)
        if z["offen"].pop(argv[i + 1], None) is None:
            print("nicht im Demo-Buch: " + argv[i + 1])
            return 1
        atomar.schreibe_json(ZUSTAND, z)
        print("verworfen: " + argv[i + 1])
        return 0
    if "--vorschau" not in argv and "--vormerken" not in argv:
        print(__doc__)
        return 2
    wache = fremd_tor.lade()
    if wache is None or wache.get("fremd_signale_erlaubt") is not True:
        print("Tor zu (fremd_signale_erlaubt nicht true) - nichts zu tun.")
        return 0
    z = atomar.lade_json(ZUSTAND, fremd_papier.leer)
    for sid, ok, rest in plaene(z, journal.lesen(), _kurs_fn(), wache, int(time.time())):
        print(json.dumps({"id": sid, "ok": ok, ("plan" if ok else "grund"): rest}, ensure_ascii=False))
    if "--vormerken" in argv:
        atomar.schreibe_json(ZUSTAND, z)
    else:
        print("(Vorschau - nichts geschrieben)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
