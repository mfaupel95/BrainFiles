"""Entscheidet, was das Handy erreicht. Reine Rechnung, damit die Regel
pruefbar bleibt - die Werte selbst stehen in auffaellig.json.

Der Median statt des Mittelwerts ist Absicht: ein einzelner langer Lauf soll
die Schwelle nicht so weit hochziehen, dass danach nichts mehr auffaellt.
"""

import json
import os
import statistics

HIER = os.path.dirname(os.path.abspath(__file__))


def regeln(pfad=None):
    with open(pfad or os.path.join(HIER, "auffaellig.json"),
              encoding="utf-8") as f:
        return json.load(f)


def _mit_ursache(grund, ereignis):
    """Haengt Fehlertext und Protokollpfad an den Grund.

    Ohne diesen Zusatz sagt die Meldung nur die Zahl ("Ergebniscode 1") -
    im Journal steht die Ursache, auf dem Handy nicht. Genau daran war die
    Meldung vom 10.09.2026 nicht zu deuten.
    """
    text = (ereignis.get("text") or "").strip()
    if text:
        grund += " - " + text
    log = ereignis.get("log")
    if log:
        grund += "\n  Protokoll: " + str(log)
    return grund

def bewerte(ereignis, historie, regeln_):
    """Gibt den Grund im Klartext zurueck - oder None fuer 'still sammeln'."""
    was = ereignis.get("was")
    if was == "hinweis":
        return "Hinweis: %s" % (ereignis.get("text") or "ohne Text")
    if was != "ende":
        return None
    if ereignis.get("code"):
        return _mit_ursache("Ergebniscode %s" % ereignis["code"], ereignis)
    dauer = ereignis.get("dauer_s")
    frueher = [e["dauer_s"] for e in historie
               if e.get("was") == "ende" and isinstance(e.get("dauer_s"), int)]
    if dauer is None or len(frueher) < int(regeln_["dauer_mindestlaeufe"]):
        return None
    mitte = statistics.median(frueher[-10:])
    if mitte > 0 and dauer > mitte * float(regeln_["dauer_faktor"]):
        return _mit_ursache("Dauer %s s statt sonst rund %s s"
                            % (dauer, int(mitte)), ereignis)
    return None


def ausbleibend(letzte_laeufe, regeln_, jetzt):
    """Wer laenger nicht gelaufen ist, als er duerfte."""
    offen = []
    for wer, stunden in sorted(regeln_.get("erwartet", {}).items()):
        letzter = letzte_laeufe.get(wer)
        if letzter is None or (jetzt - letzter).total_seconds() > stunden * 3600:
            offen.append(wer)
    return offen
