"""Beobachtet die offenen Scanner-Positionen (USDC-Spot) und meldet
Kurs/Stop/TP-Aenderungen an Telegram. Rein lesend, KEINE Orders.
Aufruf: python beobachte_live.py [--einmal]
Ohne --einmal laeuft es alle 60s (zum Test: --einmal).
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scanner"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import okx
import melder

Z = Path(__file__).resolve().parent / "scanner" / "zustand.json"

def lade():
    return json.loads(Z.read_text(encoding="utf-8")).get("positionen", [])

def meldung(pos):
    inst = pos["inst"]
    try:
        kurs = okx.letzter_kurs(inst)
    except Exception as e:
        return None, "{}: kurs-fehler {}".format(inst, e)
    stop = pos.get("stop")
    ziel = pos.get("ziel")
    einstieg = pos.get("einstieg")
    gv = (kurs - einstieg) / einstieg * 100
    txt = "{}: @{} ({:+.2f}%)\n  stop {}  ziel {}".format(
        inst, kurs, gv, "%.2f" % stop if stop else "-",
        "%.2f" % ziel if ziel else "-")
    flag = None
    if stop and kurs <= stop:
        flag = "stop"
    if ziel and kurs >= ziel:
        flag = "ziel"
    return flag, txt

def haupt(einmal):
    melder.bereit()
    letzte = {}
    while True:
        for pos in lade():
            inst = pos["inst"]
            flag, txt = meldung(pos)
            if txt is None:
                continue
            schluessel = (inst, flag)
            if schluessel != letzte.get(inst):
                if flag:
                    melder.sende("<b>{}</b>\n{}".format("STOP erreicht" if flag == "stop" else "ZIEL erreicht", txt))
                    letzte[inst] = schluessel
                else:
                    # bei --einmal auch normale Anzeige melden
                    if einmal:
                        melder.sende("Beobachtung\n" + txt, stumm=True)
        if einmal:
            return
        time.sleep(60)

if __name__ == "__main__":
    haupt("--einmal" in sys.argv)