"""HBAR zurueck ins Buch von xperp - die Position ist ECHT.

WAS PASSIERT IST (gemessen 21.09.2026, 20:33-20:40):
  - HBAR-USD_UM_XPERP-310815 wurde um 16:06 als Limit-Order eroeffnet; die
    Boerse hatte sie nur ANGENOMMEN (accFillSz 0, state live), xperp buchte
    trotzdem eine Position.
  - Um 20:33 lief die neue Geisterpruefung - zu diesem Zeitpunkt war die Order
    noch nicht gefuellt, die Position also scheinbar ein Geist. Sie wurde
    ausgebucht.
  - Kurz danach hat die Order GEFUELLT (accFillSz 9.4, avgPx 0.08956) - es
    liegt also eine echte Position an der Boerse, ohne Eintrag im Buch.
    Ohne Buch: kein Ausstieg, kein Funding, keine Bilanz.
  - BZ und CRCL hat in derselben Minute der Kill-Switch geschlossen
    (xperp/wachen.json kill_switch_gesamt_usd 40); xperp ist seither gesperrt
    (handel_erlaubt=false). Die Absicht dieser Spur war also: FLACH.

Dieses Skript stellt NUR den Bucheintrag wieder her - es verkauft nichts.
Werte stammen aus der Eroeffnungszeile im Journal, nicht aus einer Schaetzung:
  Einstieg 0.089560, 9.4 Kontrakte, 84.19 nominal, 16.84 Margin, 5x,
  Stop 0.085580, Ziel 0.097530, Liquidation 0.072096.

    python -m ... (aus dem xperp-Ordner)     # Trockenlauf
    ... --anwenden                            # schreibt zustand.json
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZUSTAND = HIER / "zustand.json"
JOURNAL = HIER / "handelsjournal.csv"

INST = "HBAR-USD_UM_XPERP-310815"
POSITION = {
    "inst": INST, "basis": "HBAR", "seite": "long", "familie": "krypto",
    "einstieg": 0.08956, "stop": 0.08558, "ziel": 0.09753,
    "liq": 0.072096, "kontrakte": 9.4, "nominal": 84.19, "margin": 16.84,
    "hebel": 5.0, "gebuehr_taker": 0.0005, "modus": "live",
    "ord_id": "3942552192558157824",
    "eroeffnet": "2026-09-21", "eroeffnet_zeit": "2026-09-21T14:06:51+00:00",
    "funding_zuletzt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "funding_summe": 0.0,
    "_vermerk": ("zurueckgebucht am 21.09.2026 20:4x, weil die Order kurz nach "
                 "der Geisterpruefung gefuellt ist (accFillSz 9.4) - die "
                 "Position ist echt, sie fehlte nur im Buch."),
}


def main() -> int:
    anwenden = "--anwenden" in sys.argv
    z = json.loads(ZUSTAND.read_text(encoding="utf-8"))
    vorhanden = {p.get("inst") for p in z.get("positionen", [])}
    if INST in vorhanden:
        print("HBAR steht schon im Buch - nichts zu tun.")
        return 0
    print("Buch vorher : %s" % [p.get("inst") for p in z.get("positionen", [])])
    print("einzutragen : %s %s @ %s, %g Kontrakte, Stop %s, Ziel %s"
          % (POSITION["inst"], POSITION["seite"], POSITION["einstieg"],
             POSITION["kontrakte"], POSITION["stop"], POSITION["ziel"]))
    if not anwenden:
        print("\nTrockenlauf - mit --anwenden schreiben.")
        return 0

    shutil.copy2(ZUSTAND, ZUSTAND.with_suffix(".json.bak-20260921"))
    z.setdefault("positionen", []).append(dict(POSITION))
    ZUSTAND.write_text(json.dumps(z, ensure_ascii=False, indent=1),
                       encoding="utf-8", newline="")
    # Journal: eine Zeile, damit die Wiederherstellung nachvollziehbar ist.
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        f.write("%s,live,eroeffnen,%s,long,krypto,%.6f,%g,%.2f,%.2f,%.2f,"
                "%.6f,%.6f,%.6f,,,,,,,,buchwiederherstellung\n"
                % (datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   INST, POSITION["einstieg"], POSITION["kontrakte"],
                   POSITION["nominal"], POSITION["margin"], POSITION["hebel"],
                   POSITION["stop"], POSITION["ziel"], POSITION["liq"]))
    print("HBAR steht wieder im Buch (Sicherung: zustand.json.bak-20260921)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
