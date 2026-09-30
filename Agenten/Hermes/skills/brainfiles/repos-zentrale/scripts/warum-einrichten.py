"""Warum steht eine Zeile in EINRICHTEN (statt STARTBAR)? - rein lesende Sonde.

Die Zentrale gruppiert nach GRUENDEN, nicht nach Gefuehl. Diese Sonde druckt je
Zeile den Bereich, die Gruppe und jeden Grund - der schnelle Weg von "86 Zeilen
in EINRICHTEN" zu "2 echte Luecken, 84 Fehlalarme".

Aufruf (aus dem Werkzeug-Ordner Agenten/Werkzeuge/repos-zentrale):
    .venv/Scripts/python.exe <dieses Skript> [BEREICH]

BEREICH ist optional: REPOS, WERKSTATT oder HANDEL.
Es wird NICHTS geschrieben und kein Prozess gestartet.
"""
from __future__ import annotations

import sys
from pathlib import Path


def werkzeug_ordner(start: Path | None = None) -> Path:
    """Den Ordner Agenten/Werkzeuge/repos-zentrale finden - aufwaerts suchen.

    Kein absoluter Pfad: das Werkzeug liegt relativ zur Repo-Wurzel, und ein
    absoluter Pfad wuerde einen Umzug auf ein anderes Laufwerk nicht ueberleben.
    """
    hier = Path(start or Path.cwd()).resolve()
    for kandidat in (hier, *hier.parents):
        ziel = kandidat / "Agenten" / "Werkzeuge" / "repos-zentrale"
        if (ziel / "repos_zentrale.py").is_file():
            return ziel
    raise SystemExit(
        "Agenten/Werkzeuge/repos-zentrale nicht gefunden - aus dem Werkzeug-Ordner "
        "oder aus der BrainFiles-Wurzel aufrufen."
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    bereich = argv[0].upper() if argv else ""

    zent = werkzeug_ordner()
    sys.path.insert(0, str(zent))

    import manifest          # noqa: PLC0415
    import quellen           # noqa: PLC0415
    import repos_zentrale    # noqa: PLC0415
    import scan              # noqa: PLC0415

    p = repos_zentrale.pfade(zent)
    plaetze = [(w, scan.tief_scannen(w, pfad)) for w, pfad in quellen.alle(p["brainfiles"])]
    eintraege = manifest.manifest_laden(p["manifest_pfad"])
    zeilen = manifest.zeilen_bauen(plaetze, eintraege, p["profile_dir"])

    zaehler: dict[str, int] = {}
    for z in sorted(zeilen, key=lambda z: (z.bereich, z.gruppe, z.ordner.lower())):
        zaehler[z.gruppe] = zaehler.get(z.gruppe, 0) + 1
        if bereich and z.bereich != bereich:
            continue
        if z.gruppe in ("startbar", "doku", "kein_start"):
            continue
        print(f"[{z.gruppe:<10}] {z.bereich:<9} {z.ordner:<38} {z.repo.pfad_rel if z.repo else '-'}")
        for grund in z.gruende:
            print(f"             - {grund}")

    print()
    for gruppe in manifest.GRUPPEN_REIHENFOLGE:
        if zaehler.get(gruppe):
            print(f"{gruppe:<12} {zaehler[gruppe]}")
    print(f"Zeilen gesamt: {len(zeilen)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
