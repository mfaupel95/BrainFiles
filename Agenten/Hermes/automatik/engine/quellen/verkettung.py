"""Trigger-Quelle skill_ergebnis: Verkettung nach einem anderen Regel-Lauf.

Gelesen wird die Lauftabelle der eigenen Zustands-DB, nicht das Log: die DB ist
die Wahrheit ueber "was ist gelaufen", das JSONL ist die Uebergabe nach aussen.

Die Marke ist die zuletzt gesehene Lauf-ID der Vorgaengerregel. Damit kann eine
Kette nicht ruckwaerts feuern und ein einzelner Vorgaenger-Lauf loest die
Folgeregel hoechstens einmal aus - auch wenn die Engine zweimal kurz
hintereinander aufgerufen wird.

Ketten sind absichtlich flach: ein Kettenlauf schreibt seinen eigenen Lauf in
dieselbe Tabelle, kann also eine weitere Regel ausloesen. Gegen Zyklen hilft
nicht die Quelle, sondern das Rate-Limit und abbruch.max_gleichzeitig der
Steuerung - deshalb ist beides fuer auto-Regeln Pflicht (S5/S6).
"""
from __future__ import annotations

from .. import zustand
from . import _schluessel

# Nur diese Ergebnisse gelten als Kettenglied. uebersprungen/dry_run/
# bestaetigung_offen sind KEIN Ergebnis des Skills und duerfen nichts ausloesen.
ERFOLG = ("erfolg",)
FEHLER = ("fehler", "timeout", "verstoss")


def pruefen(regeln, con, jetzt=None):
    from . import Ausloeser

    treffer = []
    for regel in regeln:
        b = regel.bedingungen
        vorgaenger = b.get("regel")
        status = b.get("status", "beliebig")
        if not vorgaenger:
            continue

        marke = _schluessel("kette", regel.id)
        letzte_id = int(zustand.marke_lesen(con, marke, 0) or 0)

        zeilen = con.execute(
            "SELECT id, ergebnis, exit_code, zeit_unix FROM laeufe"
            " WHERE regel_id=? AND id>? ORDER BY id LIMIT 20",
            (vorgaenger, letzte_id),
        ).fetchall()
        if not zeilen:
            continue

        for z in zeilen:
            ergebnis = z["ergebnis"]
            if status == "erfolg" and ergebnis not in ERFOLG:
                continue
            if status == "fehler" and ergebnis not in FEHLER:
                continue
            if status == "beliebig" and ergebnis not in ERFOLG + FEHLER:
                continue
            treffer.append(Ausloeser(
                regel_id=regel.id, typ="skill_ergebnis",
                ausgeloest_durch="regel '%s' lauf #%d: %s" % (
                    vorgaenger, z["id"], ergebnis),
                werte={
                    "vorgaenger": vorgaenger,
                    "vorgaenger_ergebnis": ergebnis,
                    "vorgaenger_exit": z["exit_code"],
                },
                prioritaet=regel.prioritaet,
            ))

        zustand.marke_setzen(con, marke, int(zeilen[-1]["id"]))

    return treffer
