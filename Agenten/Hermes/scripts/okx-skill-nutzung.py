"""Wrapper: skill-usage-report nur fuer okx-*/handel-* Skills.

Der woechentliche okx-skill-nutzung-Cron ruft diesen Wrapper, weil der
Cron-Scheduler dem `script`-Feld keine Argumente mitgibt. Der Filter selbst
lebt in skill-usage-report.py (--nur) - hier steht nur der Aufruf, keine
zweite Auswertung.
"""
import importlib.util
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "skill-usage-report.py"

spec = importlib.util.spec_from_file_location("skill_usage_report", ZIEL)
modul = importlib.util.module_from_spec(spec)
sys.modules["skill_usage_report"] = modul
spec.loader.exec_module(modul)

sys.argv = ["skill-usage-report.py", "--nur", "okx,handel"]

if __name__ == "__main__":
    sys.exit(modul.main())