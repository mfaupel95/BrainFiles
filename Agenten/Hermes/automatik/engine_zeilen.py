"""Erzeugt echte Engine-Lauf-Zeilen (kein Handwerk, kein erfundenes Format).

Ruft engine/protokoll.py aus t_9f7db046 auf und schreibt die Zeilen nach
stdout. Damit belegt der Durchstich, dass die Reaktionsschicht das Format
verarbeitet, das die Engine WIRKLICH schreibt - nicht das, was in der
Spezifikation steht.
"""

import json
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "t_9f7db046"
if not (ENGINE / "engine" / "protokoll.py").exists():
    sys.exit("Engine-Workspace fehlt: %s" % ENGINE)
sys.path.insert(0, str(ENGINE))

from engine import protokoll  # noqa: E402

FAELLE = [
    dict(
        ergebnis="erfolg",
        exit_code=0,
        dauer_ms=1180,
        aktionen_genutzt=["lesen", "bericht_schreiben"],
        ausgabe="52 Skills; none=20, local=6, extern=16",
    ),
    dict(ergebnis="uebersprungen", exit_code=None, abbruchgrund="rate_limit"),
    dict(ergebnis="dry_run", exit_code=None),
    dict(ergebnis="fehler", exit_code=7, abbruchgrund="Skript brach ab", dauer_ms=310),
]

for fall in FAELLE:
    modus = "dry_run" if fall["ergebnis"] == "dry_run" else "auto"
    eintrag = protokoll.eintrag_bauen(
        regel_id="inventar-nach-skill-aenderung",
        trigger_typ="datei",
        ausgeloest_durch="skills/brainfiles/mcp-sync/SKILL.md",
        skill="scripts/inventar.py",
        modus=modus,
        registry_version="1.0.0",
        **fall,
    )
    # erlaubte_aktionen kennt nur die Registry, nicht das Protokoll; die Engine
    # haengt sie ueber extra an. Hier derselbe Weg, damit die Grenzpruefung greift.
    eintrag["erlaubte_aktionen"] = ["lesen", "bericht_schreiben"]
    print(json.dumps(eintrag, ensure_ascii=False))
