"""Cron-Bruecke zum ai4trade-Heartbeat (T-113).

Die Logik liegt bei der Sache: ``Agenten/Handel/ai4trade/heartbeat.py`` (dort
liegt auch die .env mit der Kennung). Der Scheduler laeuft aber nur Skripte aus
``Agenten/Hermes/scripts/`` - deshalb diese duenne Bruecke. Sie entscheidet
nichts: sie laedt das Spur-Skript ueber den PFAD (nicht ueber sys.path, sonst
koennte ein gleichnamiges Modul gewinnen) und ruft ``main()``.

Leere Ausgabe = nichts senden (Watchdog-Muster).
"""
import importlib.util
import os
import sys

SPUR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "Handel", "ai4trade", "heartbeat.py")


def main():
    if not os.path.exists(SPUR):
        print("ai4trade-Heartbeat: %s fehlt" % SPUR)
        return 1
    spec = importlib.util.spec_from_file_location("ai4trade_heartbeat_spur",
                                                  SPUR)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    return m.main([])


if __name__ == "__main__":
    sys.exit(main())