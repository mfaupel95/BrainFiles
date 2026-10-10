"""Signal-Vertrag fuer Fremd-Werkzeuge (kraken-cli, OKX Agent Trade Kit).

Quelle der Regeln: Hermes-Skill `fremdrepos-signal`. Dieses Modul prueft nur;
es handelt nicht und liest keine Wachen. Die Pruefung ist Voraussetzung dafuer,
dass ein Signal ueberhaupt in das wachen.json-Gate kommt - das Gate bleibt final.

Regeln
------
* Pflichtfelder: instrument, venue, direction, source, ts_utc, expiry_s, mode.
  size_pct ist Pflicht ausser bei direction == "flat".
* mode ist "paper" oder "demo". "live" wird nie angenommen.
* Stale: jetzt - ts_utc > expiry_s -> verworfen, kein Retry. Zeit aus der
  Zukunft (mehr als TOLERANZ_S) ebenfalls.
* size_pct liegt in (0, 1]; bool zaehlt nicht als Zahl.
"""
PFLICHT = ("instrument", "venue", "direction", "source", "ts_utc",
           "expiry_s", "mode")
VENUES = ("okx", "kraken")
RICHTUNGEN = ("long", "short", "flat")
MODI = ("paper", "demo")
TOLERANZ_S = 5


def _zahl(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def pruefe(signal, jetzt):
    """(True, "ok") oder (False, Grund). `jetzt` = Unix-Sekunden, wird uebergeben."""
    if not isinstance(signal, dict):
        return False, "kein Objekt"
    for feld in PFLICHT:
        if feld not in signal:
            return False, "Pflichtfeld fehlt: " + feld
    if signal["mode"] not in MODI:
        return False, "mode muss paper|demo sein (live nie): %r" % (signal["mode"],)
    if signal["venue"] not in VENUES:
        return False, "venue unbekannt: %r" % (signal["venue"],)
    if signal["direction"] not in RICHTUNGEN:
        return False, "direction unbekannt: %r" % (signal["direction"],)
    if not _zahl(signal["expiry_s"]) or signal["expiry_s"] <= 0:
        return False, "expiry_s muss > 0 sein"
    if not _zahl(signal["ts_utc"]):
        return False, "ts_utc keine Zahl"
    alter = jetzt - signal["ts_utc"]
    if alter > signal["expiry_s"]:
        return False, "stale: %ds alt, erlaubt %ds" % (alter, signal["expiry_s"])
    if alter < -TOLERANZ_S:
        return False, "ts_utc liegt in der Zukunft"
    if signal["direction"] != "flat":
        g = signal.get("size_pct")
        if not _zahl(g) or not (0 < g <= 1):
            return False, "size_pct muss in (0, 1] liegen"
    return True, "ok"
