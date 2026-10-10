"""wachen.json-Tor fuer Signale aus Fremd-Werkzeugen.

Reihenfolge: erst signal_schema.pruefe (Form, nie live, Stale), dann die
Wache in fremd_signale/wachen.json. Alles hier ist eine Zulassungsliste: was
nicht ausdruecklich erlaubt ist, kommt nicht durch. Ist die Wache unlesbar,
fehlt ein Feld oder steht `fremd_signale_erlaubt` nicht exakt auf true, ist
das Tor ZU. Das Modul handelt nicht; es entscheidet nur.
"""
import json
import os

import signal_schema

HIER = os.path.dirname(os.path.abspath(__file__))
WACHE = os.path.join(HIER, "fremd_signale", "wachen.json")


def lade(pfad=WACHE):
    """Wache lesen. Fehler -> None (= Tor zu), nie eine Ausnahme."""
    try:
        with open(pfad, encoding="utf-8") as f:
            w = json.load(f)
        return w if isinstance(w, dict) else None
    except (OSError, ValueError):
        return None


def _liste(w, schluessel):
    v = w.get(schluessel)
    return v if isinstance(v, list) else []


def entscheide(signal, wache, jetzt):
    """(True, "ok") oder (False, Grund)."""
    if not isinstance(wache, dict) or wache.get("fremd_signale_erlaubt") is not True:
        return False, "Tor zu (fremd_signale_erlaubt nicht true)"
    ok, grund = signal_schema.pruefe(signal, jetzt)
    if not ok:
        return False, grund
    if signal["mode"] == "live" or signal["mode"] not in _liste(wache, "modi_erlaubt"):
        return False, "mode nicht erlaubt: %r" % (signal["mode"],)
    if signal["source"] not in _liste(wache, "quellen_erlaubt"):
        return False, "source nicht erlaubt: %r" % (signal["source"],)
    if signal["instrument"] not in _liste(wache, "instrumente_erlaubt"):
        return False, "instrument nicht erlaubt: %r" % (signal["instrument"],)
    if signal["direction"] != "flat":
        deckel = wache.get("size_pct_max")
        if isinstance(deckel, bool) or not isinstance(deckel, (int, float)) or deckel <= 0:
            return False, "size_pct_max fehlt in der Wache"
        if signal["size_pct"] > deckel:
            return False, "size_pct %s ueber Deckel %s" % (signal["size_pct"], deckel)
    return True, "ok"
