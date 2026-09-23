"""Wache ueber die echten OKX-Bots (Future DCA, Future Grid) - meldet nur Neues.

Der Waechter selbst (`Agenten/Handel/okx_bot_waechter/waechter.py`) rechnet und
haelt die Tore (`stop_erlaubt`, `bauen_erlaubt`). Diese Wache hier ruft ihn nur
und entscheidet, was eine Nachricht wert ist:

* ein Bot, der in eine STOPP-Lage kommt (AUSGELAUFEN / NOTFALL) - sofort,
* ein Bot, dessen Lage sich sonst aendert (auch die Erholung zurueck auf OK),
* derselbe Zustand erneut, aber hoechstens alle 6 Stunden.

Leere Ausgabe = nichts zu senden (Hausmuster fuer no_agent-Crons).

Aufruf:  python okx-bot-wache.py [--alles]
"""
import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(HIER)))   # BrainFiles (scripts -> Hermes -> Agenten -> Wurzel)
HANDEL = os.path.join(WURZEL, "Agenten", "Handel")
SPUR = os.path.join(HANDEL, "okx_bot_waechter")
CACHE = os.path.join(HIER, "..", "cache", "okx-bot-wache.json")
CACHE = os.path.abspath(CACHE)

STOPP_LAGEN = ("AUSGELAUFEN", "NOTFALL")
WIEDERHOLUNG_H = 6.0

if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)
if SPUR not in sys.path:
    sys.path.append(SPUR)


def lade(name, pfad):
    """Ein Modul ueber den PFAD laden - nie ueber sys.path[0] raten."""
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _lies():
    if not os.path.exists(CACHE):
        return {}
    try:
        with open(CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _schreib(daten):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(daten, fh, ensure_ascii=False, indent=1)


def _stunden_seit(zeitstempel):
    if not zeitstempel:
        return None
    try:
        t = datetime.fromisoformat(zeitstempel)
    except Exception:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() / 3600.0


def meldungen(lagen, w, waechter):
    """Was ist eine Nachricht wert? Alles andere faellt weg."""
    alt = _lies()
    neu = {}
    raus = []
    jetzt = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for l in lagen:
        if l.get("fehler"):
            neu[l["algoId"]] = {"lage": "FEHLER", "seit": jetzt, "gemeldet": jetzt}
            raus.append("%s: Abruf gescheitert - %s" % (l.get("inst") or l.get("algoId"), l["fehler"]))
            continue
        k = l["algoId"]
        v = alt.get(k) or {}
        erste_meldung = v.get("lage") != l["lage"]
        faellig = (_stunden_seit(v.get("gemeldet")) or 999) >= WIEDERHOLUNG_H
        stop = l["lage"] in STOPP_LAGEN
        if erste_meldung or (faellig and (stop or l["lage"] != "OK")):
            raus.append(waechter.zeile(l))
            for g in l.get("gruende") or []:
                raus.append("    - %s" % g)
        neu[k] = {"lage": l["lage"], "seit": v.get("seit") if not erste_meldung else jetzt,
                  "gemeldet": jetzt if (erste_meldung or faellig) else v.get("gemeldet"),
                  "inst": l.get("inst"), "art": l.get("art")}
    _schreib(neu)
    return raus


def main(argv=None):
    a = argparse.ArgumentParser(description="Wache ueber die OKX-Bots")
    a.add_argument("--alles", action="store_true",
                   help="jeden Bot melden, nicht nur Aenderungen")
    args = a.parse_args(argv)

    waechter = lade("okx_bot_waechter_wache", os.path.join(SPUR, "waechter.py"))
    try:
        w = waechter.lade_wachen()
        lagen, fehler = waechter.sammle(w)
    except Exception as e:
        print("OKX-Bot-Wache: Abruf gescheitert - %s: %s" % (type(e).__name__, e))
        return 1

    gor = []
    if args.alles:
        gor = [waechter.zeile(l) for l in lagen]
    else:
        gor = meldungen(lagen, w, waechter)
    for f in fehler:
        gor.append("Nicht abrufbar: %s" % f)
    if gor:
        print("OKX-Bots (Future DCA/Grid): %d Bot(s) im Blick" % len(lagen))
        for z in gor:
            print(z)
    return 0


if __name__ == "__main__":
    sys.exit(main())