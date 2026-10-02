#!/usr/bin/env python3
"""Sperrgruende aller Spuren aus ihrer eigenen Vorschau - rein lesend.

WARUM: Der Dauerlauf oeffnet ein Live-Fenster nur, wenn die Vorschau GENAU EINEN
Grund nennt und dieser "Freigabefenster" heisst (dauerlauf.nur_fenster_fehlt).
Wer einen Schalter anfasst (handel_erlaubt, Grenzen, Wachen), muss deshalb sehen,
welche Spur danach nur noch am Fenster haengt - sonst fragt der Dauerlauf nach
einer Freigabe, die niemand erwartet hat.

Aufruf (aus dem Handel-Ordner):
    python sperrgruende.py
    python sperrgruende.py --nur scanner orb
    python sperrgruende.py --zeit 120
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent


def spurenliste():
    t = (HIER / "dauerlauf.py").read_text(encoding="utf-8")
    i = t.index("SPUREN = {"); block = t[i:i + 20000]
    namen, tiefe = [], 0
    for nr, z in enumerate(block.splitlines()):
        if nr == 0:
            tiefe = 1
            continue
        tiefe += z.count("{") - z.count("}")
        if tiefe <= 0:
            break
        m = re.match(r'\s{4}"([A-Za-z0-9_]+)":\s*\{', z)
        if m:
            namen.append(m.group(1))
    return namen


def sperrgrund(spur: str, zeit: int):
    ordner = HIER / spur
    if not (ordner / "handeln.py").is_file():
        return spur, None, "kein handeln.py"
    # Je Spur ihr EIGENER Interpreter. Der Scanner-venv traegt nicht
    # nautilus_trader; mit ihm stuerzt die Vorschau der Nautilus-Arme ab
    # (ModuleNotFoundError), und ein abgestuerzter Lauf liefert keine
    # Sperrzeile - so galten nautilus und nautilus_kraken als blind
    # (T-313, 02.10.2026). Reihenfolge: die Spur selbst, dann Nachbarspuren.
    kandidaten = [HIER / spur / ".venv" / "Scripts" / "python.exe"]
    if spur.startswith("nautilus"):
        kandidaten.append(HIER / "nautilus" / ".venv" / "Scripts" / "python.exe")
    kandidaten.append(HIER / "scanner" / ".venv" / "Scripts" / "python.exe")
    python = next((k for k in kandidaten if k.is_file()), kandidaten[-1])
    umg = dict(os.environ, MAXHIRN_ROUTINE="1")
    umg.pop("PYTHONHOME", None); umg.pop("PYTHONPATH", None)
    try:
        p = subprocess.run([str(python), "handeln.py", "--vorschau"], cwd=str(ordner),
                           capture_output=True, text=True, timeout=zeit, env=umg)
    except subprocess.TimeoutExpired:
        return spur, None, "Zeitueberschreitung (%d s)" % zeit
    for z in (p.stdout or "").splitlines():
        if "gesperrt durch" in z or "gesperrt:" in z:
            return spur, z.split(":", 1)[-1].strip(), None
    return spur, None, "keine Sperrzeile"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nur", nargs="*")
    ap.add_argument("--zeit", type=int, default=120)
    a = ap.parse_args()
    spuren = a.nur or spurenliste()
    fenster_allein = []
    for s in spuren:
        name, grund, fehler = sperrgrund(s, a.zeit)
        if fehler:
            print("%-18s %s" % (name, fehler))
            continue
        gruende = [g.strip() for g in grund.split(";")]
        marke = ""
        if len(gruende) == 1 and "Freigabefenster" in gruende[0]:
            marke = "  <<< NUR das Fenster - der Dauerlauf fragt hier nach Freigabe"
            fenster_allein.append(name)
        print("%-18s %d Grund/Gruende  %s%s" % (name, len(gruende), grund[:110], marke))
    print()
    if fenster_allein:
        print("Fenster allein fehlt bei: %s" % ", ".join(fenster_allein))
    else:
        print("Keine Spur haengt allein am Fenster.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
