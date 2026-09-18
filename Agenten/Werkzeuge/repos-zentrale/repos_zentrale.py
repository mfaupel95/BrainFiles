"""Einstieg der Repos-Zentrale.

    .venv\\Scripts\\pythonw.exe repos_zentrale.py          # Fenster
    .venv\\Scripts\\python.exe   repos_zentrale.py --pruefen   # nur auflisten

Alle Pfade kommen aus der Lage dieser Datei - nichts ist absolut eingetragen,
damit die Zentrale einen Umzug auf ein anderes Laufwerk ueberlebt.
"""

from __future__ import annotations

import argparse
from pathlib import Path

HIER = Path(__file__).resolve().parent


def pfade(hier: Path = HIER) -> dict[str, Path]:
    """Wo Repos, Manifest, Bot-Profile und Logs liegen."""
    brainfiles = hier.parents[2]           # Agenten/Werkzeuge/repos-zentrale -> BrainFiles
    return {
        "repos_basis": brainfiles / "Werkstatt" / "Repos",
        "manifest_pfad": hier / "repos-zentrale.json",
        "profile_dir": hier.parents[1] / "Hermes" / "profiles",
        "log_ordner": hier / "logs",
    }


def pruefen(p: dict[str, Path]) -> int:
    """Ohne Fenster pruefen: Platte lesen, Gruppen zeigen, Auffaelligkeiten nennen."""
    import fenster
    import manifest
    import scan

    repos = scan.repos_scannen(p["repos_basis"])
    eintraege = manifest.manifest_laden(p["manifest_pfad"])
    zeilen = manifest.zeilen_bauen(repos, eintraege, p["profile_dir"], p["repos_basis"])
    gruppen = fenster.nach_gruppen(zeilen)

    print(f"Repos-Bestand : {p['repos_basis']}")
    print(f"Repos auf Platte: {len(repos)}   Manifest-Eintraege: {len(eintraege)}")
    print(f"Bots (Profile)  : {len(list(p['profile_dir'].glob('*/config.yaml')))}")
    for name, zeilen_gruppe in gruppen.items():
        print(f"  {fenster.gruppen_titel(name, len(zeilen_gruppe))}")
        for z in zeilen_gruppe:
            start = " ".join(z.start) if z.start else "-"
            print(f"      {z.ordner:<38} {z.art:<14} start: {start}")

    auffaellig = [z for z in zeilen if z.gruppe in ("neu", "fehlt")]
    if auffaellig:
        print("\nAuffaellig:")
        for z in auffaellig:
            print(f"  ! {z.ordner}: {'; '.join(z.gruende)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        description="Repos-Zentrale - ein Fenster fuer alle Projekte unter Werkstatt/Repos"
    )
    zerleger.add_argument(
        "--pruefen", action="store_true",
        help="nur laden und auflisten, kein Fenster oeffnen",
    )
    args = zerleger.parse_args(argv)
    p = pfade()
    if args.pruefen:
        return pruefen(p)

    import fenster

    f = fenster.Fenster(**p)
    f.root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
