"""Herzschlag-Wache: meldet, wenn eine Spur nicht mehr lebt - von aussen.

WARUM (Review 09.10.2026): der Notausstieg bei altem Herzschlag steckt IM Lauf
der Spur (`xperp/handeln.py`, Bedingung 3) und greift erst, wenn der Dauerlauf
wieder laeuft. Faellt der Prozess oder der Rechner aus, merkt es niemand, bis
die taegliche Systempruefung (Block 11) es in ihrem Bericht nennt. Diese Wache
liest nur die Zustandsdateien und meldet den WECHSEL ("Spur X seit N min
still", "wieder lebendig") ueber den Bus - sie schreibt in keine Spur und stellt
keine Order.

Eine Spur zaehlt als still, wenn `zustand.json["letzter_lauf"]` aelter ist als
ihr `herzschlag_max_minuten` (wachen.json, Vorgabe 180). Spuren ohne
`letzter_lauf` (nie gelaufen) zaehlen nicht. Welche Spuren gelten, kommt aus
`dauerlauf.SPUREN` (per AST gelesen, wie in befehle.py).

Aufruf (rein lesend ausser der Merkdatei cache/herzschlag-wache.json):
    python herzschlag_wache.py          # prueft, meldet bei Wechsel, Exit 1 wenn still
    python herzschlag_wache.py --stand  # nur ausgeben, nichts melden

Einplanen muss man das von Hand (z. B. alle 10 Minuten als Aufgabe); dieses
Skript startet nichts von selbst.
"""

from __future__ import annotations

import ast
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
MERK = os.path.join(HIER, "cache", "herzschlag-wache.json")
VORGABE_MAX_MIN = 180


def spurliste(handel=HIER):
    """Die Spuren aus `dauerlauf.SPUREN` oder [] (eine geratene Liste waere
    schlimmer als keine)."""
    try:
        with open(os.path.join(handel, "dauerlauf.py"), encoding="utf-8") as fh:
            baum = ast.parse(fh.read())
        for k in baum.body:
            if isinstance(k, ast.Assign) and any(
                    getattr(t, "id", None) == "SPUREN" for t in k.targets):
                if isinstance(k.value, ast.Dict):
                    out = []
                    for key, val in zip(k.value.keys, k.value.values):
                        if not isinstance(key, ast.Constant):
                            continue
                        ordner = key.value
                        if isinstance(val, ast.Dict):
                            for kk, vv in zip(val.keys, val.values):
                                if (isinstance(kk, ast.Constant)
                                        and kk.value == "ordner"
                                        and isinstance(vv, ast.Constant)):
                                    ordner = vv.value
                        out.append((key.value, ordner))
                    return out
    except Exception:                                          # noqa: BLE001
        pass
    return []


def _json(pfad):
    try:
        with open(pfad, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def alter_min(letzter_lauf, jetzt):
    """Minuten seit `letzter_lauf` (ISO) oder None, wenn fehlend/unlesbar."""
    if not letzter_lauf:
        return None
    try:
        t = datetime.fromisoformat(letzter_lauf)
    except (ValueError, TypeError):
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (jetzt - t).total_seconds() / 60.0


def stille_spuren(handel=HIER, jetzt=None):
    """{spur: alter_min} aller Spuren, deren Herzschlag ueber ihrer Grenze liegt."""
    jetzt = jetzt or datetime.now(timezone.utc)
    still = {}
    for name, ordner in spurliste(handel):
        d = os.path.join(handel, ordner)
        a = alter_min(_json(os.path.join(d, "zustand.json")).get("letzter_lauf"),
                      jetzt)
        if a is None:
            continue
        grenze = _json(os.path.join(d, "wachen.json")).get(
            "herzschlag_max_minuten", VORGABE_MAX_MIN)
        try:
            grenze = float(grenze)
        except (TypeError, ValueError):
            grenze = VORGABE_MAX_MIN
        if a > grenze:
            still[name] = a
    return still


def wechsel(still, merk):
    """(neu_still, wieder_da) gegenueber der Merkdatei."""
    alt = set((merk or {}).get("still") or [])
    jetzt = set(still)
    return sorted(jetzt - alt), sorted(alt - jetzt)


def lauf(handel=HIER, jetzt=None, melden=True, merkdatei=MERK):
    still = stille_spuren(handel, jetzt)
    merk = _json(merkdatei)
    neu, da = wechsel(still, merk)
    if melden and handel == HIER:
        try:
            import telemetrie                                # noqa: PLC0415
            for s in neu:
                telemetrie.stoerung(s, "herzschlag_alt", dauer_s=still[s] * 60)
        except Exception:                                    # noqa: BLE001
            pass                  # Telemetrie darf die Wache nie stoeren
    if melden and (neu or da):
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(handel), "Bus"))
            import ereignis                                  # noqa: PLC0415
            if neu:
                ereignis.hinweis(
                    "handel/herzschlag-wache",
                    "Spur still: " + ", ".join(
                        "%s (%.0f min)" % (s, still[s]) for s in neu))
            if da:
                ereignis.hinweis("handel/herzschlag-wache",
                                 "Wieder lebendig: " + ", ".join(da))
        except Exception:                                    # noqa: BLE001
            pass                  # eine Wache darf an der Meldung nicht sterben
    if melden:
        os.makedirs(os.path.dirname(merkdatei), exist_ok=True)
        with open(merkdatei, "w", encoding="utf-8") as fh:
            json.dump({"still": sorted(still)}, fh)
    return still, neu, da


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    still, _, _ = lauf(melden="--stand" not in argv)
    for s, a in sorted(still.items()):
        print("%-24s still seit %6.0f min" % (s, a))
    if not still:
        print("Alle Spuren mit Herzschlag sind frisch.")
    return 1 if still else 0


if __name__ == "__main__":
    sys.exit(main())
