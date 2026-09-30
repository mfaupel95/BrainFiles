"""Trigger-Quelle datei: ein Pfadmuster hat sich geaendert.

Kein Betriebssystem-Waechter, sondern ein Vergleich bei jedem Engine-Aufruf:
Dateiliste + mtime/Groesse werden als Marke gespeichert, beim naechsten Aufruf
verglichen. Das passt zum Prozessmodell (kurzer Lauf, vom Cron gestartet) und
ueberlebt einen Absturz - ein Waechter im Speicher taete das nicht.

mindestabstand_s entprellt: ein Editor schreibt beim Speichern mehrfach, ein
git-Wechsel beruehrt hunderte Dateien. Innerhalb des Abstands wird der Stand
zwar uebernommen (sonst haengt die Engine ewig an derselben Aenderung), aber
kein Ausloeser erzeugt.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .. import pfade, zustand
from . import _schluessel

MAX_DATEIEN = 5000  # Sicherung gegen ein zu weites Muster


def _stand(muster: list[str]) -> dict:
    """Aktueller Stand: {pfad: "mtime_ns:groesse"} fuer alle Treffer."""
    wurzel = pfade.wurzel()
    stand: dict[str, str] = {}
    for m in muster:
        p = Path(m)
        if p.is_absolute():
            basis, rest = Path(p.anchor), p.relative_to(p.anchor).as_posix()
        else:
            basis, rest = wurzel, m
        try:
            for treffer in basis.glob(rest):
                if not treffer.is_file():
                    continue
                try:
                    s = treffer.stat()
                except OSError:
                    continue
                stand[treffer.as_posix().lower()] = "%d:%d" % (s.st_mtime_ns, s.st_size)
                if len(stand) >= MAX_DATEIEN:
                    return stand
        except (OSError, ValueError):
            continue
    return stand


def _unterschied(alt: dict, neu: dict) -> dict[str, list[str]]:
    return {
        "created": sorted(set(neu) - set(alt)),
        "deleted": sorted(set(alt) - set(neu)),
        "modified": sorted(p for p in set(alt) & set(neu) if alt[p] != neu[p]),
    }


def pruefen(regeln, con, jetzt=None):
    from . import Ausloeser

    jetzt = float(jetzt if jetzt is not None else time.time())
    treffer = []

    for regel in regeln:
        b = regel.bedingungen
        muster = list(b.get("pfad_muster") or [])
        if not muster:
            continue
        gefragt = b.get("aktion")  # None = jede Aenderung
        abstand = int(b.get("mindestabstand_s", 0))

        marke = _schluessel("datei", regel.id)
        roh = zustand.marke_lesen(con, marke)
        neu = _stand(muster)

        if roh is None:
            # Erster Lauf: Stand aufnehmen, nichts ausloesen. Sonst gilt der
            # gesamte Bestand als "gerade erzeugt".
            zustand.marke_setzen(con, marke, json.dumps({"stand": neu, "zeit": jetzt}))
            continue

        try:
            gespeichert = json.loads(roh)
            alt = gespeichert.get("stand") or {}
            letzte_meldung = float(gespeichert.get("gemeldet") or 0)
        except (json.JSONDecodeError, TypeError, ValueError):
            alt, letzte_meldung = {}, 0.0

        unterschied = _unterschied(alt, neu)
        relevant = (
            unterschied[gefragt] if gefragt
            else unterschied["created"] + unterschied["modified"] + unterschied["deleted"]
        )

        if not relevant:
            zustand.marke_setzen(con, marke, json.dumps(
                {"stand": neu, "zeit": jetzt, "gemeldet": letzte_meldung}))
            continue

        if abstand and (jetzt - letzte_meldung) < abstand:
            # Entprellt: Stand uebernehmen, aber nicht ausloesen.
            zustand.marke_setzen(con, marke, json.dumps(
                {"stand": neu, "zeit": jetzt, "gemeldet": letzte_meldung}))
            continue

        zustand.marke_setzen(con, marke, json.dumps(
            {"stand": neu, "zeit": jetzt, "gemeldet": jetzt}))
        treffer.append(Ausloeser(
            regel_id=regel.id, typ="datei",
            ausgeloest_durch="%d Datei(en) %s, zuerst: %s" % (
                len(relevant), gefragt or "geaendert", relevant[0]),
            werte={
                "pfade": relevant[:20],
                "anzahl": len(relevant),
                "aktion": gefragt or "geaendert",
            },
            prioritaet=regel.prioritaet,
        ))

    return treffer
