"""Wache: meldet stille Spuren, die auffallen.

no_agent-Muster: die Ausgabe IST die Meldung, leere Ausgabe = nichts senden.
Ruft das Haus-Werkzeug Agenten/Handel/stille_spuren.py mit --wache auf,
damit es genau EINE Definition von "auffaellig" gibt.

Gemeldet wird nur, was eine Entscheidung braucht:
  TOT           Spur laeuft nicht mehr (Zustand veraltet / Ordner weg)
  UEBERFAELLIG  Position ueber ihrer Frist, ohne gebuchten Ausstieg
Gesundes Warten (WARTET/HAELT) bleibt still.
"""
import os
import subprocess
import sys

HANDEL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "Handel")
WERKZEUG = os.path.join(HANDEL, "stille_spuren.py")
PYTHON = os.path.join(HANDEL, "scanner", ".venv", "Scripts", "python.exe")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not os.path.isfile(WERKZEUG):
        print("Stille-Spuren-Wache: Werkzeug fehlt: %s" % WERKZEUG)
        return 0
    python = PYTHON if os.path.isfile(PYTHON) else sys.executable

    # PYTHONHOME/PYTHONPATH entfernen: ein geerbtes uv-venv vergiftet sonst
    # den Start des Spuren-venv (Hausfalle).
    umgebung = dict(os.environ)
    umgebung.pop("PYTHONHOME", None)
    umgebung.pop("PYTHONPATH", None)

    try:
        lauf = subprocess.run(
            [python, WERKZEUG, "--wache"], cwd=HANDEL, env=umgebung,
            capture_output=True, text=True, timeout=240, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired:
        print("Stille-Spuren-Wache: Pruefung lief in die Zeitgrenze (240 s).")
        return 0
    except Exception as e:                                   # noqa: BLE001
        print("Stille-Spuren-Wache: Pruefung nicht moeglich: %s" % e)
        return 0

    text = (lauf.stdout or "").strip()
    if lauf.returncode != 0:
        fehler = (lauf.stderr or "").strip().splitlines()
        print("Stille-Spuren-Wache: Pruefung endete mit Code %d%s"
              % (lauf.returncode, (": " + fehler[-1]) if fehler else ""))
        return 0

    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
