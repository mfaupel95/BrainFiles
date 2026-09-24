# Alterswache fuer den Systempruefungsbericht.
#
# Warum es diese Wache gibt: Am 19.-22.09.2026 hing Block 14 der Systempruefung
# an einem toten Docker-Daemon. Jeden Morgen entstand ein Tagesprotokoll, die
# Aufgabe stand auf "Ready" - nur der Bericht letzter-lauf.md wurde drei Tage
# nicht mehr geschrieben, und niemand sah es. Diese Wache prueft genau das eine:
# wie alt ist der Bericht.
#
# Aufruf (leere Ausgabe = kein Befund, Exit 0):
#   scanner/.venv/Scripts/python.exe scripts/berichts-alter.py
#   ... --stunden 26 --pfad <anderer Bericht>
# Stdlib only. Kein Netzzugriff, kein Schreiben.

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

STANDARD_RELATIV = Path("Agenten") / "Routinen" / "logs" / "systempruefung-letzter-lauf.md"
MUSTER = re.compile(r"^#\s*Systempruefung\s+(\d{4})-(\d{2})-(\d{2})", re.MULTILINE)


def standard_pfad() -> Path:
    """Repo-Wurzel ueber die eigenen Elternordner finden.

    Nicht die Tiefe zaehlen (der Skill liegt je nach Profil auf anderer Ebene),
    sondern den ersten Elternordner nehmen, unter dem Agenten/Routinen/logs liegt.
    """
    for eltern in Path(__file__).resolve().parents:
        if (eltern / STANDARD_RELATIV).exists():
            return eltern / STANDARD_RELATIV
    return Path(__file__).resolve().parents[6] / STANDARD_RELATIV


STANDARD = standard_pfad()


def berichtsdatum(pfad: Path):
    """Datum aus der Kopfzeile '# Systempruefung JJJJ-MM-TT'."""
    if not pfad.exists():
        return None, f"Bericht fehlt: {pfad}"
    text = pfad.read_text(encoding="utf-8", errors="replace")
    # Die Berichte beginnen mit einem UTF-8-BOM (Set-Content -Encoding UTF8) - 
    # ohne lstrip("\ufeff") findet der Anker ^# die Kopfzeile nicht.
    text = text.lstrip("\ufeff")
    treffer = MUSTER.search(text)
    if not treffer:
        return None, f"Kopfzeile '# Systempruefung <Datum>' nicht gefunden in {pfad.name}"
    jahr, monat, tag = (int(t) for t in treffer.groups())
    return datetime(jahr, monat, tag), None


def main() -> int:
    p = argparse.ArgumentParser(description="Meldet einen veralteten Systempruefungsbericht.")
    p.add_argument("--pfad", type=Path, default=STANDARD)
    p.add_argument("--stunden", type=float, default=26.0,
                   help="Schwelle in Stunden (Standard 26: taeglicher Lauf 07:00 plus Reserve)")
    p.add_argument("--leise-ok", action="store_true",
                   help="auch bei frischem Bericht eine Zeile ausgeben (Standard: leer)")
    a = p.parse_args()

    datum, fehler = berichtsdatum(a.pfad)
    if fehler:
        print(f"Systempruefung-Berichtsalter: {fehler}")
        return 1

    alter_h = (datetime.now() - datum).total_seconds() / 3600.0
    if alter_h > a.stunden:
        print(f"Systempruefung-Berichtsalter: Bericht vom {datum:%d.%m.%Y} ist "
              f"{alter_h:.1f} h alt (Schwelle {a.stunden:.0f} h). Moeglich: der Lauf "
              f"wurde abgebrochen - Ende des Protokolls "
              f"Agenten/Routinen/logs/systempruefung-{datetime.now():%Y-%m-%d}.log pruefen "
              f"und einmal von Hand starten.")
        return 1

    if a.leise_ok:
        print(f"Systempruefung-Berichtsalter: {alter_h:.1f} h - frisch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
