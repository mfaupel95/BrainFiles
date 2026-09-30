"""Einstieg der Zentrale: Repos · Werkstatt · Handel in einem Fenster.

    .venv\\Scripts\\pythonw.exe repos_zentrale.py              # Fenster
    .venv\\Scripts\\python.exe   repos_zentrale.py --pruefen   # nur auflisten
    .venv\\Scripts\\python.exe   repos_zentrale.py --pruefen --bereich HANDEL

Alle Pfade kommen aus der Lage dieser Datei - nichts ist absolut eingetragen,
damit die Zentrale einen Umzug auf ein anderes Laufwerk ueberlebt.
"""

from __future__ import annotations

import argparse
from pathlib import Path

HIER = Path(__file__).resolve().parent


def pfade(hier: Path = HIER) -> dict[str, Path]:
    """Wo BrainFiles-Wurzel, Manifest, Bot-Profile und Logs liegen."""
    brainfiles = hier.parents[2]           # Agenten/Werkzeuge/repos-zentrale -> BrainFiles
    return {
        "brainfiles": brainfiles,
        "manifest_pfad": hier / "repos-zentrale.json",
        "profile_dir": hier.parents[1] / "Hermes" / "profiles",
        "log_ordner": hier / "logs",
    }


def pruefen(p: dict[str, Path], bereich: str = "") -> int:
    """Ohne Fenster pruefen: Platte lesen, Bereiche zeigen, Auffaelligkeiten nennen."""
    import fenster
    import manifest
    import quellen
    import scan

    plaetze = [(w, scan.tief_scannen(w, pfad)) for w, pfad in quellen.alle(p["brainfiles"])]
    eintraege = manifest.manifest_laden(p["manifest_pfad"])
    zeilen = manifest.zeilen_bauen(plaetze, eintraege, p["profile_dir"])

    print(f"Wurzel         : {p['brainfiles']}")
    for w, basis in quellen.alle(p["brainfiles"]):
        anzahl = len(next((r for k, r in plaetze if k.kennung == w.kennung), []))
        print(f"  {w.titel:<20} {basis}  ({anzahl} Ordner)")
    print(f"Manifest-Eintraege: {len(eintraege)}   Zeilen: {len(zeilen)}   "
          f"Bots (Profile): {len(list(p['profile_dir'].glob('*/config.yaml')))}")
    print(f"Summe: {fenster.zusammenfassung(zeilen)}")

    for kennung, gruppen in fenster.nach_bereichen(zeilen).items():
        if bereich and kennung.upper() != bereich.upper():
            continue
        print()
        print(f"== {kennung} ==")
        for name, zeilen_gruppe in gruppen.items():
            print(f"  {fenster.gruppen_titel(name, len(zeilen_gruppe))}")
            for z in zeilen_gruppe:
                start = " ".join(z.start) if z.start else "-"
                rolle = z.rolle or "-"
                print(f"      {z.ordner:<38} {z.art:<12} {rolle:<14} start: {start}")

    auffaellig = fenster.auffaellige(zeilen)
    if auffaellig:
        print("\nAuffaellig:")
        for z in auffaellig:
            print(f"  ! {z.bereich}/{z.ordner}: {'; '.join(z.gruende)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        description="Zentrale - ein Fenster fuer Repos, Werkstatt und Handel"
    )
    zerleger.add_argument(
        "--pruefen", action="store_true",
        help="nur laden und auflisten, kein Fenster oeffnen",
    )
    zerleger.add_argument(
        "--bereich", default="",
        help="nur diesen Bereich auflisten (REPOS, WERKSTATT, HANDEL)",
    )
    args = zerleger.parse_args(argv)
    p = pfade()
    if args.pruefen:
        return pruefen(p, args.bereich)

    import fenster

    f = fenster.Fenster(**p)
    f.root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
