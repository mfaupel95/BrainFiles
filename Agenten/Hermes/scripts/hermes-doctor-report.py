#!/usr/bin/env python
"""Wrapper fuer den woechentlichen Diagnose-Cron (no_agent).

Der Cron-Scheduler ruft das Skript OHNE Argumente auf (das script-Feld ist
nur ein Pfad, _script_argv baut [python, path]). Dieser Wrapper reicht
--report an hermes-doctor.py weiter, damit die stdout-Lieferung die kompakte
Telegram-Zusammenfassung ist statt der Statuszeilen.
"""
import runpy
import sys

sys.argv = ["hermes-doctor.py", "--report"]
runpy.run_path("hermes-doctor.py", run_name="__main__")
