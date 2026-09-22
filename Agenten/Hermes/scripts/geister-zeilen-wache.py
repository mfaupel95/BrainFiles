"""Wache: kaputte Geister-Zeilen in den Handelsjournalen auf den echten Wert.

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut**, dann wird nichts gesendet (Watchdog-Muster wie bus-waechter.py).
Gemeldet wird nur, was wirklich korrigiert wurde - oder ein Fehler.

WARUM ES DIESEN WAECHTER GIBT
------------------------------
Am 21.09.2026 buchte `bueche_geister_aus` in xperp eine von Hand geschlossene
Position mit `margin_usd = 0.00`. Die Wachen lesen die schliessen-Zeile als
ERLOES - die Runde zaehlte damit als TOTALVERLUST ihres Einsatzes (HBAR:
-16.84 USD in genau der Drawdown-Kurve, aus der der Kill-Switch liest).

Der CODE ist seit dem 22.09.2026 repariert (`_geist_erloes`: echtes
Boersenergebnis, sonst neutral). Alte Zeilen tragen die 0.00 aber weiter, und
eine Wache, die nur den Code prueft, sieht sie nie. Diese hier liest die
Journale selbst und zieht jede kaputte Zeile auf den echten Wert.

WAS ES NICHT TUT
----------------
Es aendert NICHTS ausser der einen Zahl in dieser einen Zeile - keine Zeile
wird geloescht, keine andere Zahl angefasst. Das Journal selbst bleibt die
Wahrheit; die Wache repariert nur den bekannten Schreibfehler.

RUHE-BEDINGUNG: eine Spur, die gerade schreibt (Journal juenger als
MIN_RUHE_MIN), wird NICHT angefasst. Das Werkzeug liest und schreibt die
ganze Datei - liefe es mitten in einen Zyklus, koennte eine frische Zeile
verloren gehen. Ein Zyklus dauert Sekunden bis Minuten, der Takt hier ist
Stunden; Warten kostet also nichts.

Aufruf:
    python Agenten/Hermes/scripts/geister-zeilen-wache.py
    python Agenten/Hermes/scripts/geister-zeilen-wache.py --vorschau
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                 # Agenten/Hermes/scripts -> BrainFiles
WERKZEUG = WURZEL / "Agenten" / "Handel" / "xperp" / "geister_nachziehen.py"

# Ein Journal, das juenger ist, wird nicht angefasst (siehe oben).
MIN_RUHE_MIN = 5.0


def lade_werkzeug(pfad=None):
    """geister_nachziehen.py per Pfad laden - es ist kein installiertes Modul."""
    p = str(pfad or WERKZEUG)
    spec = importlib.util.spec_from_file_location("geister_nachziehen", p)
    if spec is None or spec.loader is None:
        return None
    modul = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modul)
    except Exception:                                          # noqa: BLE001
        return None
    return modul


def _alter_minuten(pfad):
    try:
        return (time.time() - os.path.getmtime(pfad)) / 60.0
    except OSError:
        return None


def befunde(werkzeug, journale=None, min_ruhe_min=MIN_RUHE_MIN):
    """(reif, ruhend) - zwei Listen von (pfad, kaputte_zeilen).

    `reif` = hat kaputte Zeilen und darf angefasst werden,
    `ruhend` = hat kaputte Zeilen, wird aber gerade noch geschrieben.
    """
    reif, ruhend = [], []
    for p in (journale if journale is not None else werkzeug._journale()):
        try:
            _, _, _, kaputt, fehler = werkzeug._kaputte_zeilen(p)
        except Exception:                                      # noqa: BLE001
            continue
        if fehler or not kaputt:
            continue
        alter = _alter_minuten(p)
        if alter is None or alter < min_ruhe_min:
            ruhend.append((p, kaputt))
        else:
            reif.append((p, kaputt))
    return reif, ruhend


def wachen(werkzeug=None, journale=None, min_ruhe_min=MIN_RUHE_MIN,
           anwenden=True):
    """Rueckgabe: (meldungen, fehler). Leere Meldungen = nichts zu senden."""
    werkzeug = werkzeug or lade_werkzeug()
    if werkzeug is None:
        return [], "geister-zeilen-wache: %s nicht ladbar" % WERKZEUG
    reif, ruhend = befunde(werkzeug, journale=journale,
                           min_ruhe_min=min_ruhe_min)
    meldungen = []
    for pfad, kaputt in reif:
        spur = os.path.basename(os.path.dirname(pfad))
        if not anwenden:
            for n, inst, alt, neu in kaputt:
                meldungen.append("%s: %s Erloes %s -> %s (Vorschau)"
                                 % (spur, inst, alt, neu))
            continue
        korrigiert, geschrieben = werkzeug.korrigiere_datei(
            pfad, anwenden=True, still=True)
        _, _, _, danach, _ = werkzeug._kaputte_zeilen(pfad)
        if danach:
            meldungen.append("%s: %d Zeile(n) NICHT korrigiert (noch offen)"
                             % (spur, len(danach)))
            continue
        for n, inst, alt, neu in korrigiert:
            meldungen.append("%s: %s  Erloes %s -> %s" % (spur, inst, alt, neu))
        meldungen.append("%s: %d Geister-Zeile(n) auf den echten Wert gezogen"
                         % (spur, len(korrigiert)))
    return meldungen, None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--vorschau", action="store_true",
                   help="nur zeigen, nichts schreiben")
    p.add_argument("--ruhe", type=float, default=MIN_RUHE_MIN,
                   help="Mindestalter des Journals in Minuten")
    a = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    meldungen, fehler = wachen(min_ruhe_min=a.ruhe, anwenden=not a.vorschau)
    if fehler:
        print(fehler)
        return 0
    if meldungen:
        print("Geister-Zeilen im Journal korrigiert (Handgriffe von Hand):")
        for m in meldungen:
            print("  " + m)
        print("Regel: eine handgeschlossene Position wird mit dem echten "
              "Boersenergebnis gebucht, sonst neutral - nie als Vollverlust.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
