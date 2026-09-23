"""Einen vorgeschlagenen OKX-Bot BAUEN - nur auf ausdrueckliche Bestellung.

Zwei Tore muessen zusammenkommen: `bauen_erlaubt` in wachen.json UND der
Schalter `--anwenden`. Fehlt eines, zeigt das Programm den Koerper, den es
schicken WUERDE, und schickt nichts. Der Deckel `startgeld_max_usd` aus
wachen.json sperrt zu grosse Einsaetze zusaetzlich; `--deckel-aus` hebt ihn
bewusst auf (Begruendung gehoert dann in den Bericht, nicht ins Protokoll).

Aufruf (aus diesem Ordner):
    python bauen.py vorschlaege/dca-UV-USD_UM_XPERP-310718-20260923-173000.json
    python bauen.py <datei> --anwenden
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)
import bots  # noqa: E402

VORSCHLAEGE = os.path.join(HIER, "vorschlaege")
JOURNAL = os.path.join(HIER, "bot_bauen_journal.jsonl")
WACHEN = os.path.join(HIER, "wachen.json")


def finde(name):
    if os.path.isfile(name):
        return name
    p = os.path.join(VORSCHLAEGE, os.path.basename(name))
    return p if os.path.isfile(p) else None


def protokoll(eintrag):
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Vorgeschlagenen OKX-Bot bauen")
    ap.add_argument("vorschlag", help="Datei aus vorschlaege/")
    ap.add_argument("--anwenden", action="store_true", help="wirklich anlegen")
    ap.add_argument("--deckel-aus", action="store_true",
                    help="den Einsatzdeckel aus wachen.json uebergehen")
    a = ap.parse_args(argv)

    pfad = finde(a.vorschlag)
    if not pfad:
        print("Kein Vorschlag gefunden: %s" % a.vorschlag)
        return 2
    v = json.load(open(pfad, encoding="utf-8"))
    w = json.load(open(WACHEN, encoding="utf-8"))
    koerper = v.get("koerper") or {}
    art = v.get("art")
    inst = v.get("instId")
    budget = float(v.get("budget") or 0)
    deckel = float((w.get("_vorschlag") or {}).get("startgeld_max_usd") or 0)

    print("Vorschlag %s\n  Art %s | Instrument %s | Einsatz %s | Kurs %s | Boden %s"
          % (os.path.basename(pfad), art, inst, budget, v.get("kurs"), v.get("boden")))
    print("  %s" % (v.get("plan") or {}).get("_rechnung", ""))
    for w_ in (v.get("plan") or {}).get("warnungen") or []:
        print("  WARNUNG: %s" % w_)
    print("  Koerper: %s" % json.dumps(koerper, ensure_ascii=False))

    sperren = []
    if not w.get("bauen_erlaubt"):
        sperren.append("bauen_erlaubt steht auf false (wachen.json)")
    if not koerper:
        sperren.append("kein Koerper im Vorschlag")
    for w_ in (v.get("plan") or {}).get("warnungen") or []:
        if "Mindestinvestment" in w_:
            sperren.append(w_)
    if deckel and budget > deckel and not a.deckel_aus:
        sperren.append("Einsatz %s ueber dem Deckel startgeld_max_usd %s "
                       "(bewusst aufheben mit --deckel-aus)" % (budget, deckel))
    if not bots.schluessel_da():
        sperren.append("keine OKX-Schluessel in der Umgebung")

    if sperren or not a.anwenden:
        grund = ("Tor zu: " + "; ".join(sperren)) if sperren else \
            "Trockenlauf - '--anwenden' fehlt, es wurde NICHTS angelegt."
        print("\nNICHT GEBAUT (%s)" % grund)
        protokoll({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "vorschlag": os.path.basename(pfad), "art": art, "instId": inst,
                   "budget": budget, "angelegt": False, "grund": grund})
        return 0

    try:
        if art == "dca":
            antwort = bots.dca_anlegen(koerper)
        else:
            antwort = bots.grid_anlegen(koerper)
    except Exception as e:
        print("\nFEHLER beim Anlegen: %s: %s" % (type(e).__name__, str(e)[:400]))
        protokoll({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "vorschlag": os.path.basename(pfad), "art": art, "instId": inst,
                   "budget": budget, "angelegt": False,
                   "grund": "%s: %s" % (type(e).__name__, str(e)[:400])})
        return 1

    print("\nANGELEGT: %s" % json.dumps(antwort, ensure_ascii=False))
    print("Kontrolle: python waechter.py  (der neue Bot muss dort auftauchen)")
    protokoll({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "vorschlag": os.path.basename(pfad), "art": art, "instId": inst,
               "budget": budget, "angelegt": True, "koerper": koerper,
               "antwort": antwort})
    return 0


if __name__ == "__main__":
    sys.exit(main())