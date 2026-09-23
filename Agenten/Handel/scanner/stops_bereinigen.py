"""Offene Stops der scanner-Spur gegen die Boerse abgleichen und aufraeumen.

Warum es das gibt (Befund 23.09.2026)
-------------------------------------
``zustand.json`` trug 23 Kopien DESSELBEN Stop (3940642343922589696), jede
Runde meldete der Live-Lauf "offener Stop ... bleibt liegen: OKX 50014:
Parameter instId can not be empty". Zwei Fehler auf einmal:

  * ``cancel-algos`` braucht die instId - ohne sie antwortet OKX mit 50014,
    und der Stop liess sich NIE stornieren (seit 22.09. taeglich versucht),
  * der Merker hieb denselben Stop bei jedem Versuch erneut in die Liste.

Behoben ist beides im Code (``okx.stop_stornieren(algo_id, inst)`` +
``handeln._merke_offenen_stop``). Dieses Werkzeug bringt den BESTAND in
Ordnung: es fragt zu jedem gemerkten Stop den echten Boersenzustand ab und
entfernt alles, was dort nicht mehr aktiv ist. Ein Stop, den es an der Boerse
noch gibt und der zu KEINER offenen Position gehoert, ist ein Waisenstop - er
wird gemeldet und nur mit ``--stornieren`` abbestellt (er koennte sonst eine
spaetere Position desselben Instruments zum alten Stoppreis verkaufen).

Aufruf (aus ``Agenten/Handel/scanner``):

    python stops_bereinigen.py               # Vorschau, schreibt nichts
    python stops_bereinigen.py --anwenden    # zustand.json bereinigen
    python stops_bereinigen.py --anwenden --stornieren   # Waisen auch abbestellen

Geschrieben wird nur ``zustand.json`` der scanner-Spur - und nur, wenn sie
nicht juenger als ``MIN_ALTER_S`` ist: ein laufender Zyklus wuerde eine frische
Aenderung ohnehin ueberschreiben, und mitten in den Zyklus zu schreiben kostet
eine Buchung.
"""

import argparse
import json
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
ZUSTAND = os.path.join(HIER, "zustand.json")
MIN_ALTER_S = 300          # nicht in einen laufenden Zyklus schreiben
ERLEDIGT = ("canceled", "filled", "order_failed")

sys.path.insert(0, HIER)
import okx  # noqa: E402


def _lade(pfad):
    with open(pfad, "r", encoding="utf-8") as f:
        return json.load(f)


def _speichere(pfad, z):
    with open(pfad, "w", encoding="utf-8", newline="\n") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _boersenstand(stop_ord_id):
    """(state, instId) eines Stops oder (None, None), wenn er nicht lesbar ist."""
    try:
        d = okx.stop_details(stop_ord_id) or {}
    except Exception as e:  # noqa: BLE001
        print("   %s nicht lesbar: %s" % (stop_ord_id, e), file=sys.stderr)
        return None, None
    return (d.get("state") or "").lower(), d.get("instId") or None


def bereinige(z, stornieren=False, anwenden=False):
    """Vorschau/Ausfuehrung. Rueckgabe: (bereinigt, waisen, journal)."""
    offen = z.get("offene_stops") or []
    positionen = z.get("positionen") or []
    gefuehrt = {p.get("stop_ord_id") for p in positionen if p.get("stop_ord_id")}

    gesehen, rest, waisen, erledigt, doppelt = set(), [], [], [], 0
    for e in offen:
        sid = e.get("stop_ord_id")
        if not sid:
            continue
        if sid in gesehen:
            doppelt += 1
            print("   %s doppelt gemerkt - eine Kopie faellt weg" % sid)
            continue
        gesehen.add(sid)
        state, inst = _boersenstand(sid)
        if inst and not e.get("inst"):
            e["inst"] = inst
        if state is None:
            # Nicht lesbar: lieber behalten als eine echte Order vergessen.
            rest.append(e)
            print("   %s bleibt (Boersenzustand unbekannt)" % sid)
            continue
        if state in ERLEDIGT:
            erledigt.append(sid)
            print("   %s erledigt an der Boerse (%s) - Eintrag faellt"
                  % (sid, state))
            continue
        if sid in gefuehrt:
            rest.append(e)                  # gehoert zu einer offenen Position
            print("   %s gehoert zur offenen Position - bleibt gemerkt" % sid)
            continue
        waisen.append((sid, e.get("inst"), state))
        if stornieren and anwenden:
            try:
                weg = okx.stop_stornieren(sid, e.get("inst"))
                print("   WAISE %s storniert (%s)" % (sid, weg or "war schon weg"))
                erledigt.append(sid)
                continue
            except Exception as ex:  # noqa: BLE001
                print("   WAISE %s nicht stornierbar: %s" % (sid, ex),
                      file=sys.stderr)
        rest.append(e)

    if anwenden:
        if len(rest) != len(offen):
            z["offene_stops"] = rest
    return {"rest": len(rest), "erledigt": len(erledigt), "doppelt": doppelt,
            "waisen": waisen, "offen_zuvor": len(offen)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anwenden", action="store_true",
                    help="zustand.json wirklich schreiben (Standard: Vorschau)")
    ap.add_argument("--stornieren", action="store_true",
                    help="Waisenstops an der Boerse abbestellen (nur mit "
                         "--anwenden)")
    ap.add_argument("--pfad", default=ZUSTAND,
                    help="abweichende zustand.json (fuer Tests)")
    a = ap.parse_args(argv)

    if not os.path.exists(a.pfad):
        print("keine %s - nichts zu tun" % a.pfad)
        return 0
    if a.anwenden:
        alter = time.time() - os.path.getmtime(a.pfad)
        if alter < MIN_ALTER_S:
            print("zustand.json ist %d s alt (jünger als %d s) - ein Zyklus "
                  "laeuft vermutlich gerade. Spaeter erneut versuchen."
                  % (alter, MIN_ALTER_S))
            return 2

    z = _lade(a.pfad)
    print("offene_stops vorher: %d, Positionen: %d"
          % (len(z.get("offene_stops") or []), len(z.get("positionen") or [])))
    print("Modus: %s" % ("ANWENDEN" if a.anwenden else "Vorschau (schreibt nichts)"))
    erg = bereinige(z, stornieren=a.stornieren, anwenden=a.anwenden)
    print("erledigt/entfernt: %d   doppelt: %d   bleiben: %d   Waisen: %d"
          % (erg["erledigt"], erg["doppelt"], erg["rest"], len(erg["waisen"])))
    for sid, inst, state in erg["waisen"]:
        print("   WAISENSTOP %s %s (%s) - gehoert zu keiner offenen Position"
              % (sid, inst, state))
    if a.anwenden and erg["offen_zuvor"] != erg["rest"]:
        _speichere(a.pfad, z)
        print("zustand.json geschrieben: offene_stops %d -> %d"
              % (erg["offen_zuvor"], erg["rest"]))
    elif not a.anwenden:
        print("nichts geschrieben (Vorschau) - mit --anwenden ausfuehren")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())