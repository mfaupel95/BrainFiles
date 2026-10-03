#!/usr/bin/env python
"""Wrapper: tasks-wache.py im Modus --voll (die Regel, warum zwei Modi
statt einem, steht dort). Das Cron-Feld script nimmt nur den Dateinamen,
deshalb dieser Aufrufer je Modus.

Der Kern heisst tasks-WACHE.py mit einem Bindestrich - ein Bindestrich ist
in einem Modulnamen unmoeglich, ein normales `import tasks_wache` schlaegt
daher immer fehl. Der Weg ist deshalb der Pfad-Import mit
importlib.util, genau so wie die Spurmodule im Handel."""
import importlib.util, os, sys
KERN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks-wache.py")
spec = importlib.util.spec_from_file_location("tasks_wache", KERN)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
sys.argv = ["tasks-wache.py", "--voll"]
sys.exit(mod.main())
