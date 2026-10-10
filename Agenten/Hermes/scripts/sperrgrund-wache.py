#!/usr/bin/env python
"""Wrapper: sperrgrund-wache.py aus dem cache/-Ordner (der Kern).

Das Cron-Feld `script` akzeptiert nur Dateinamen relativ zu
Agenten/Hermes/scripts/. Der T-080-Kern liegt aber - wie vom Auftrag
gefordert - unter Agenten/Hermes/cache/sperrgrund-wache.py. Deshalb dieser
dünne Aufrufer je Modus, nach dem Muster tasks-wache-voll.py: den Kern per
importlib.util über den Pfad laden (ein Bindestrich im Namen verhindert
`import sperrgrund_wache`), main() aufrufen.

Verhalten gehört zum Kern: nur ÄNDERUNGEN des Sperrgrundes melden, leere
Ausgabe = nichts senden (Watchdog-Muster).
"""
import importlib.util
import os
import sys

KERN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cache", "sperrgrund-wache.py",
)
spec = importlib.util.spec_from_file_location("sperrgrund_wache", KERN)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
sys.argv = ["sperrgrund-wache.py"]
sys.exit(mod.main())
