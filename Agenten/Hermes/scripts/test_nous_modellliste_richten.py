"""Gegenprobe fuer scripts/nous-modellliste-richten.py - auf einer KOPIE, nie auf der echten Config."""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve()
HERMES = HIER.parents[2]
SPEC = importlib.util.spec_from_file_location("nous_richten", HERMES / "scripts" / "nous-modellliste-richten.py")
mod = importlib.util.module_from_spec(SPEC)
sys.modules["nous_richten"] = mod
SPEC.loader.exec_module(mod)

fehler = 0


def pruefe(name: str, bedingung: bool, zusatz: str = "") -> None:
    global fehler
    print(("OK   " if bedingung else "ROT  ") + name + (" | " + zusatz if zusatz else ""))
    if not bedingung:
        fehler += 1


with tempfile.TemporaryDirectory() as tmp:
    probe = Path(tmp) / "config.yaml"
    shutil.copy2(HERMES / "config.yaml", probe)
    # Ausgangslage herstellen: Block ueber die echte Funktion entfernen
    pruefe("Ausgangslage hat den Block", mod.KENNUNG in probe.read_bytes())
    mod._zuruecknehmen(probe, True)
    ohne = probe.read_bytes()
    pruefe("Ausgangslage ohne Block", mod.KENNUNG not in ohne)
    import yaml
    pruefe("ohne Block weiter lesbar", yaml.safe_load(ohne.decode("utf-8"))["model"]["provider"] == "nous")

    models = ["a/b", "c/d:batch", "e/f:free"]
    ergebnis = mod._eintragen(probe, models, False)
    pruefe("Trockenlauf schreibt nicht", "Trockenlauf" in ergebnis and mod.KENNUNG not in probe.read_bytes(), ergebnis)

    ergebnis = mod._eintragen(probe, models, True)
    neu = probe.read_bytes()
    pruefe("Eintragen schreibt", mod.KENNUNG in neu and len(neu) > len(ohne), ergebnis)
    pruefe("Zeilenenden bleiben CRLF", neu.count(b"\r\n") == neu.count(bytes([10])))
    import yaml
    d = yaml.safe_load(neu.decode("utf-8"))
    pruefe("YAML liest den Block", list(d["providers"]["nous"]["models"]) == models, str(list(d["providers"])[:3]))
    pruefe("model-Block unberuehrt", d["model"]["provider"] == "nous" and d["model"]["default"] == "deepseek/deepseek-v4.1-flash")
    pruefe("Rest der Config gleich", neu.replace(mod._block(models), b"") == ohne)

    pruefe("zweites Eintragen ist still", "schon eingetragen" in mod._eintragen(probe, models, True))

    ergebnis = mod._zuruecknehmen(probe, False)
    pruefe("Zuruecknehmen trocken", "Trockenlauf" in ergebnis)
    ergebnis = mod._zuruecknehmen(probe, True)
    zurueck = probe.read_bytes()
    pruefe("Zuruecknehmen stellt her", zurueck == ohne, "%d -> %d Bytes" % (len(neu), len(zurueck)))

print("\nFehler:", fehler)
sys.exit(1 if fehler else 0)