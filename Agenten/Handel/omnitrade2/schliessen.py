"""Die Position des omnitrade2-XPERP-Laufs an der BOERSE glattstellen.

Warum es das braucht (gemessen 21.10.2026): der Live-Loop setzt seine Baseline
(``start_base``) beim ERSTEN Auftrag auf den aktuellen Bestand. Eine Position,
die vor einem Neustart schon offen war, ist fuer den neuen Prozess Fremdbestand -
er kann sie nie schliessen, und ein Signal in die Gegenrichtung baut eine
Positionsseite daneben auf. Wer den Lauf mit anderen Parametern neu startet,
muss deshalb vorher flach sein.

Ablauf, jede Stufe mit Nachkontrolle:
  1. Position an der Boerse lesen (nie aus dem Status des Loops).
  2. Schutz-Stops DIESER Richtung stornieren (sonst feuert der Stop mitten in
     die Schliessung).
  3. Market schliessen (``okxf.markt_schliessen``, reduceOnly) - Limit waere
     kein Ausstieg.
  4. Nachkontrolle: ist die Position weg? Bleibt sie stehen, wird der alte
     Stop SOFORT wieder gesetzt, damit die Position nicht nackt bleibt.

Vorschau ist die Vorgabe; ``--anwenden`` schreibt an die Boerse.

Aufruf aus dem Handel-Ordner:
    ..\\scanner\\.venv\\Scripts\\python.exe omnitrade2/schliessen.py --anwenden
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve().parent
NACHZIEHER = HIER / "nachziehen.py"
LAUF_DATEI = HIER / "lauf.json"
WARTE_S = 15


def nachzieher_laden():
    spec = importlib.util.spec_from_file_location("nachziehen_schliessen", NACHZIEHER)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


def lauf(anwenden: bool = False) -> dict:
    ergebnis = {"zeit": time.strftime("%Y-%m-%dT%H:%M:%S"), "handlung": [], "fehler": None}
    try:
        laufdaten = json.loads(LAUF_DATEI.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        ergebnis["fehler"] = "lauf.json nicht lesbar: %s" % e
        return ergebnis
    inst = laufdaten.get("inst") or ""
    if not inst:
        ergebnis["fehler"] = "lauf.json nennt kein Instrument"
        return ergebnis
    ergebnis["inst"] = inst

    nz = nachzieher_laden()
    okxf = nz.okxf_laden()
    pos = nz.position(okxf, inst)
    if pos is None:
        ergebnis["handlung"].append("keine Position an der Boerse - nichts zu schliessen")
        return ergebnis
    kontrakte = abs(float(pos["menge"]))
    ergebnis.update({"menge": pos["menge"], "seite": pos["seite"], "einstieg": pos["einstieg"]})

    stops = [s for s in (okxf.schutz_stops(inst) or [])
             if okxf.ist_schutz_stop(s) and nz.deckt_position(s, pos["seite"])]
    ergebnis["stops"] = [str(s.get("algoId") or "") for s in stops]
    notstop = None
    for s in stops:
        preis = s.get("slTriggerPx") or s.get("tpTriggerPx") or ""
        if str(preis).strip():
            notstop = float(preis)
            break
    ergebnis["stop_preis"] = notstop

    ergebnis["handlung"].append(
        "%s %s Kontrakte @ %s, %d Schutz-Stop(s) %s"
        % (pos["seite"], kontrakte, pos["einstieg"], len(stops), ergebnis["stops"]))
    if not anwenden:
        ergebnis["handlung"].append("Vorschau: Stops stornieren, dann Market schliessen.")
        return ergebnis

    for s in stops:
        kennung = str(s.get("algoId") or "")
        if not kennung:
            continue
        try:
            okxf.algo_stornieren(inst, kennung)
            ergebnis["handlung"].append("Stop storniert: %s" % kennung)
        except Exception as e:  # noqa: BLE001 - jeder Fehlschlag ist ein Befund
            ergebnis["fehler"] = "Storno %s scheiterte: %s" % (kennung, e)
            return ergebnis

    try:
        ordid = okxf.markt_schliessen(inst, kontrakte, pos["seite"], tdmode="isolated")
        ergebnis["handlung"].append("Market-Schliessung abgesetzt: %s" % ordid)
    except Exception as e:  # noqa: BLE001
        ergebnis["fehler"] = "Schliessung scheiterte: %s" % e
        if notstop:
            try:
                okxf.schutz_stop_setzen(inst, pos["seite"], kontrakte, notstop)
                ergebnis["handlung"].append("Stop wieder gesetzt bei %s" % notstop)
            except Exception as e2:  # noqa: BLE001
                ergebnis["fehler"] += " | Stop NICHT wieder gesetzt: %s" % e2
        return ergebnis

    for _ in range(WARTE_S):
        time.sleep(1)
        if nz.position(okxf, inst) is None:
            ergebnis["handlung"].append("NACHKONTROLLE: Position ist weg")
            ergebnis.pop("fehler", None)
            return ergebnis
    ergebnis["fehler"] = "NACHKONTROLLE: Position steht nach %d s noch" % WARTE_S
    if notstop:
        try:
            okxf.schutz_stop_setzen(inst, pos["seite"], kontrakte, notstop)
            ergebnis["handlung"].append("Stop wieder gesetzt bei %s" % notstop)
        except Exception as e:  # noqa: BLE001
            ergebnis["fehler"] += " | Stop NICHT wieder gesetzt: %s" % e
    return ergebnis


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Position des omnitrade2-Laufs glattstellen")
    ap.add_argument("--anwenden", action="store_true", help="wirklich an die Boerse schreiben")
    args = ap.parse_args(argv)
    ergebnis = lauf(anwenden=args.anwenden)
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    return 0 if not ergebnis.get("fehler") else 1


if __name__ == "__main__":
    raise SystemExit(main())
