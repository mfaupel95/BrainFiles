"""Gegenprobe nach dem Merge: der Executor muss spur_buch aus Agenten/Handel
laden (T-346) und bei einem nicht freigegebenen Auftrag eine MELDUNG liefern,
nicht mit ImportError abbrechen. Laeuft aus Agenten/Hermes/scripts/ - genau
dem Verzeichnis, aus dem der Cron startet."""
import importlib.util
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(SCRIPTS, "..", "..", ".."))
HANDEL = os.path.join(WURZEL, "Agenten", "Handel")

pfad = os.path.join(SCRIPTS, "signal-executor.py")
spec = importlib.util.spec_from_file_location("signal_executor_probe", pfad)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

assert m.HANDEL == HANDEL, (m.HANDEL, HANDEL)

# spur_buch muss ohne sys.path-Hilfe aus HANDEL ladbar sein (der Fix)
pf = os.path.join(HANDEL, "spur_buch.py")
assert os.path.exists(pf), pf

# Auftrag an eine Spur, die es nicht gibt -> wachen.json nicht lesbar,
# also eine Meldung und KEIN Traceback
ok, txt = m.ausfuehren("gibtsnicht", ["inst", "long", 1.0, "2026-10-05T00:00:00"])
assert ok is False and isinstance(txt, str) and txt, (ok, txt)

# Gegenprobe des eigentlichen Wegs: eine echte, nicht freigegebene Spur
spur = "iv_waelle"
ok2, txt2 = m.ausfuehren(spur, ["ETH-USD-260925-40000-C", "long", 1.0,
                                "2099-01-01T00:00:00"])
assert ok2 is False, (ok2, txt2)
assert "freigabe" in txt2 or "handel_erlaubt" in txt2, txt2

print("OK: spur_buch ladbar aus", HANDEL)
print("OK: Auftrag ohne Freigabe ->", txt2[:90])