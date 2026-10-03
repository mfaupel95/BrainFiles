"""Einstieg der Zentrale: Repos · Werkstatt · Handel in einem Fenster.

    .venv\\Scripts\\pythonw.exe repos_zentrale.py              # Fenster
    .venv\\Scripts\\python.exe   repos_zentrale.py --pruefen   # nur auflisten
    .venv\\Scripts\\python.exe   repos_zentrale.py --pruefen --bereich HANDEL
    .venv\\Scripts\\python.exe   repos_zentrale.py --handel    # Stand der Spuren
    .venv\\Scripts\\python.exe   repos_zentrale.py --test scanner

Alle Pfade kommen aus der Lage dieser Datei - nichts ist absolut eingetragen,
damit die Zentrale einen Umzug auf ein anderes Laufwerk ueberlebt.

**Scharf geschaltet wird nur im Fenster.** Die Handelsregeln (Punkt 3) verlangen
dafuer ein Fenster, das die Werte zeigt, sie aendern laesst und ein Feld zum
Bestaetigen hat - die Knoepfe dafuer sitzen in der Handels-Karte und im Dialog
`schalter.py`. Ein Kommandozeilen-Schalter dafuer waere genau das, was die Regel
ausschliesst; hier gibt es deshalb nur LESENDE Aufrufe (`--handel`, `--test`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

HIER = Path(__file__).resolve().parent


def pfade(hier: Path = HIER) -> dict[str, Path]:
    """Wo BrainFiles-Wurzel, Manifest, Bot-Profile, Logs und Einstellungen liegen."""
    brainfiles = hier.parents[2]           # Agenten/Werkzeuge/repos-zentrale -> BrainFiles
    return {
        "brainfiles": brainfiles,
        "manifest_pfad": hier / "repos-zentrale.json",
        "profile_dir": hier.parents[1] / "Hermes" / "profiles",
        "log_ordner": hier / "logs",
        "einstellungen_pfad": hier / "einstellungen.json",
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
    import handelstand

    fenster.spuren_markieren(zeilen, handelstand.laufplan(p["brainfiles"]), {})

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
                spur = fenster.spur_kurz(z) or "-"
                print(f"      {z.ordner:<38} {z.art:<12} {rolle:<14} "
                      f"{spur:<7} start: {start}")

    auffaellig = fenster.auffaellige(zeilen)
    if auffaellig:
        print("\nAuffaellig:")
        for z in auffaellig:
            print(f"  ! {z.bereich}/{z.ordner}: {'; '.join(z.gruende)}")
    return 0


def handel_tabelle(p: dict[str, Path], nur: str = "") -> int:
    """Den Stand aller Handels-Spuren als Tabelle zeigen (rein lesend)."""
    import handelstand

    daten = handelstand.zustand(p["brainfiles"])
    plan = handelstand.laufplan(p["brainfiles"])
    print(f"{'Spur':<24} {'Ordner':<22} {'Order':<6} {'erlaubt':<8} {'Haken':<6} "
          f"{'Fenster':<18} {'Buch':<18} Zyklus")
    for name in sorted(daten):
        e = daten[name]
        if nur == "scharf" and not e.get("scharf"):
            continue
        if nur == "live" and not e.get("order"):
            continue
        buch = ", ".join(f"{k}:{v}" for k, v in (e.get("buch") or {}).items()) or "-"
        alter = f"{e['alter']} min" if e.get("alter") is not None else "-"
        print(f"{name:<24} {(plan.get(name) or {}).get('ordner', '?'):<22} "
              f"{(e.get('art') or 'keiner'):<6} {str(e.get('erlaubt')):<8} "
              f"{str(e.get('frei')):<6} {str(e.get('fenster') or '-'):<18} "
              f"{buch:<18} {alter}")
    scharf = [n for n, e in daten.items() if e.get("scharf")]
    print(f"\n{len(daten)} Spuren, {len(scharf)} mit Orderweg und handel_erlaubt: "
          f"{', '.join(scharf) or 'keine'}")
    return 0


def vorschau_test(p: dict[str, Path], spur: str) -> int:
    """`--vorschau` einer Spur ausfuehren - der einzige Beleg fuer ihren Modus.

    Rein lesend: die Vorschau schreibt keine Datei. Die Ausgabe geht auf die
    Konsole; im Fenster landet sie zusaetzlich in `logs/`.
    """
    import subprocess

    import handelstand

    if spur not in handelstand.spurnamen(p["brainfiles"]):
        print(f"'{spur}' ist keine Spur aus dauerlauf.SPUREN.")
        print("Bekannt: " + ", ".join(sorted(handelstand.spurnamen(p["brainfiles"]))))
        return 2
    argv = handelstand.vorschau_argv(p["brainfiles"], spur)
    print("Aufruf: " + " ".join(argv))
    print("-" * 60)
    try:
        p_ = subprocess.run(
            argv, cwd=str(handelstand.handel_ordner(p["brainfiles"])),
            env=handelstand.vorschau_umgebung(), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("ABBRUCH nach 300 s - die Spur hat nicht geantwortet.")
        return 3
    print(p_.stdout or "")
    if p_.stderr:
        print("--- stderr ---")
        print(p_.stderr)
    print("-" * 60)
    print(f"Exit-Code {p_.returncode}")
    return 0 if p_.returncode == 0 else 1


def pruefbericht(p: dict[str, Path], bereich: str = "", schreiben: bool = True) -> int:
    """Alle Projekte messen und den Bericht nach logs/ schreiben (rein lesend).

    Derselbe Lauf wie der Knopf "Alles pruefen" im Fenster - nur ohne Fenster,
    damit er auch aus einer Routine heraus laufen kann. Gemessen wird: venv
    (laeuft sie?), node_modules, Pflichtpfad, Git-Zustand, README, Bot-Profil,
    Port. Nichts wird dabei eingerichtet oder geaendert.
    """
    import datetime as dt

    import fenster
    import manifest
    import pflege
    import quellen
    import scan

    plaetze = [(w, scan.tief_scannen(w, pfad)) for w, pfad in quellen.alle(p["brainfiles"])]
    eintraege = manifest.manifest_laden(p["manifest_pfad"])
    zeilen = manifest.zeilen_bauen(plaetze, eintraege, p["profile_dir"])
    fenster.spuren_markieren(zeilen, {}, {})
    if bereich:
        zeilen = [z for z in zeilen if z.bereich.upper() == bereich.upper()]

    text, auffaellig = pflege.sammelbericht(zeilen, log_ordner=p["log_ordner"])
    zeilen_text = text.splitlines()
    print(zeilen_text[2] if len(zeilen_text) > 2 else text)
    for ordner, punkte in auffaellig[:15]:
        print(f"  {ordner:<40} " + "; ".join(f"{x.name}: {x.text}" for x in punkte[:3]))
    if len(auffaellig) > 15:
        print(f"  ... {len(auffaellig) - 15} weitere")
    if schreiben:
        p["log_ordner"].mkdir(parents=True, exist_ok=True)
        ziel = p["log_ordner"] / f"pruefbericht-{dt.datetime.now():%Y%m%d-%H%M}.log"
        ziel.write_text(text, encoding="utf-8", newline="\n")
        print(f"Bericht: {ziel}")
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
    zerleger.add_argument(
        "--handel", action="store_true",
        help="Stand der Handels-Spuren als Tabelle (rein lesend)",
    )
    zerleger.add_argument(
        "--nur", default="",
        help="mit --handel: 'scharf' oder 'live'",
    )
    zerleger.add_argument(
        "--test", default="", metavar="SPUR",
        help="--vorschau dieser Spur ausfuehren (rein lesend)",
    )
    zerleger.add_argument(
        "--pruefbericht", action="store_true",
        help="alle Projekte messen (venv, Git, Pflichtpfad ...) und nach logs/ schreiben",
    )
    args = zerleger.parse_args(argv)
    p = pfade()
    if args.test:
        return vorschau_test(p, args.test)
    if args.handel:
        return handel_tabelle(p, args.nur)
    if args.pruefbericht:
        return pruefbericht(p, args.bereich)
    if args.pruefen:
        return pruefen(p, args.bereich)

    import fenster

    f = fenster.Fenster(**p)
    f.root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())