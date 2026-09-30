"""Ein Befehl, der die ganze Automatik belegt - Engine, Reaktion, Kopplung.

Aufruf:   python pruefen.py
Erwartet: "alles gruen", Exitcode 0.

Warum ein eigener Treiber und nicht "pytest im Wurzelverzeichnis": die drei
Teile liegen in drei Workspaces mit drei verschiedenen Testarten (pytest,
Selbsttest-Skript, pytest). Ein Treiber, der sie in fester Reihenfolge startet
und ihre Exitcodes auswertet, ist reproduzierbar - eine Anleitung im Text
nicht.

Reihenfolge ist Absicht: erst die Engine allein, dann die Reaktionsschicht
allein, dann das Zusammenspiel. Wenn das Zusammenspiel rot ist und die beiden
Haelften gruen, liegt der Fehler in der Kopplung - das spart beim naechsten
Ausfall die halbe Suche.

Kein Test hier fasst den Betrieb an: jeder laeuft in einem eigenen Temp-Ordner
(pytest tmp_path bzw. tempfile), mit Attrappen statt Board und Telegram.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

from automatik import pfade  # noqa: E402

ENGINE = pfade.engine()
REAKTION = pfade.reaktion()

LAEUFE = (
    ("Engine (t_9f7db046)", ENGINE,
     [sys.executable, "-m", "pytest", "tests/test_engine.py", "-q"]),
    ("Reaktionsschicht (t_f682e5c1)", REAKTION,
     [sys.executable, "test_reaktion.py"]),
    ("Kopplung Ende-zu-Ende (t_f7937187)", HIER,
     [sys.executable, "-m", "pytest", "tests/ende_zu_ende.py", "-q"]),
)


def main() -> int:
    if not ENGINE.exists() or not REAKTION.exists():
        print("FEHLT: Engine oder Reaktionsschicht nicht gefunden.")
        print("  Engine:   %s" % ENGINE)
        print("  Reaktion: %s" % REAKTION)
        print("Pfade umstellen ueber HERMES_AUTOMATIK_ENGINE / _REAKTION.")
        return 2

    rot = 0
    for name, ordner, kommando in LAEUFE:
        begonnen = time.time()
        fertig = subprocess.run(kommando, cwd=str(ordner), capture_output=True,
                                text=True, encoding="utf-8", errors="replace")
        dauer = time.time() - begonnen
        marke = "gruen" if fertig.returncode == 0 else "ROT  "
        letzte = [z for z in (fertig.stdout or "").splitlines() if z.strip()]
        print("%s  %-38s %5.1fs  %s" % (
            marke, name, dauer, letzte[-1][:60] if letzte else ""))
        if fertig.returncode != 0:
            rot += 1
            for zeile in (fertig.stdout or "").splitlines()[-25:]:
                print("      | " + zeile)
            for zeile in (fertig.stderr or "").splitlines()[-10:]:
                print("      ! " + zeile)

    print()
    if rot:
        print("%d von %d Laeufen ROT" % (rot, len(LAEUFE)))
        return 1
    print("alles gruen (%d Laeufe)" % len(LAEUFE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
