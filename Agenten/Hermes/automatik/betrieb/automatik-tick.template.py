"""Cron-Vorlage: ein Engine-Tick ohne Modellaufruf.

NICHT INSTALLIERT. Wer die Engine in den Takt nehmen will, kopiert diese Datei
nach Agenten/Hermes/scripts/automatik-tick.py und legt einen Cron-Auftrag mit
script="automatik-tick.py" und no_agent=true an (Muster: bus-waechter, siehe
BETRIEB.md).

Regeln fuer ein Cron-Skript in diesem Haus:
- Leere Ausgabe heisst "nichts zu melden" und wird nicht zugestellt. Darum wird
  hier nur geschrieben, wenn wirklich etwas gelaufen ist.
- Kein Modell, kein Agent. Der Tick ist ein Prozess, der prueft und endet.
- Fehler der Engine gehoeren in die Ausgabe, nicht in ein stilles Log: ein
  Automatiksystem, das seinen eigenen Ausfall verschweigt, ist schlimmer als
  keines.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ENGINE = Path(
    "C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/kanban/workspaces/t_9f7db046")
REGISTRY = ENGINE / "betrieb" / "registry.yaml"

os.environ.setdefault("HERMES_AUTOMATIK_BASIS", str(ENGINE / "betrieb" / "arbeit"))
os.environ.setdefault("HERMES_AUTOMATIK_REGISTRY", str(REGISTRY))
sys.path.insert(0, str(ENGINE))

from engine import registry, steuerung, zustand  # noqa: E402
from engine.quellen import sammeln  # noqa: E402


def main() -> int:
    try:
        reg = registry.laden(REGISTRY)
    except registry.RegistryFehler as e:
        print("Automatik gestoppt - Registry abgelehnt: %s" % e.meldung)
        for d in e.details[:10]:
            if d:
                print("  - %s" % d)
        return 1

    meldungen = []
    with zustand.offen() as con:
        zustand.belegung_aufraeumen(con)
        for a in sammeln(reg, con):
            r = reg.nach_id(a.regel_id)
            if r is None:
                continue
            eintrag = steuerung.ausfuehren(r, a, con, reg.version)
            # Nur berichten, was einen Menschen angeht.
            if eintrag["ergebnis"] in ("fehler", "timeout", "verstoss",
                                       "bestaetigung_offen"):
                meldungen.append("%s: %s (%s)" % (
                    a.regel_id, eintrag["ergebnis"],
                    eintrag.get("abbruchgrund") or a.ausgeloest_durch))

    for m in meldungen:
        print(m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
