"""Integrationsphasen der Fremd-Repos im BrainFiles-Baum.

Warum es dieses Modul gibt: FREMD-Liste.json sagt, *was* Fremd-Material ist.
Dieses Modul verwaltet FREMD-Phasen.json - es sagt, *wie weit* ein Fremd-Repo
in der Integration ist (Phase 0-4) und ob es gerade blockiert ist.

Phasen:
  0  Inventur     README, Lizenz, Eignung; Eintrag in FREMD-Liste.json
  1  Adapter      Eigener Uebersetzer/Wrapper fertig und registriert
  2  Papier-Lauf  Herzschlag laeuft, Signale im Journal
  3  Walk-forward Out-of-sample-Test dokumentiert (Ergebnis kann negativ sein)
  4  Live         handel_erlaubt=true nach positivem Walk-forward

Nur Standardbibliothek, keine absoluten Pfade.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

WURZEL_TIEFE = 2  # Agenten/Werkzeuge/fremdrepos.py -> [0] Werkzeuge, [1] Agenten, [2] BrainFiles
DATEINAME = "FREMD-Phasen.json"
PHASEN = (0, 1, 2, 3, 4)
STATI = ("offen", "in_arbeit", "fertig", "blockiert")
PFLICHT = ("name", "pfad", "rolle", "phase_aktuell", "status", "geaendert")


@dataclass
class FremdPhase:
    name: str
    pfad: str
    rolle: str
    phase_aktuell: int
    status: str
    geaendert: str
    blockiert_weil: str | None = None
    notiz: str | None = None

    def __str__(self) -> str:
        return f"{self.name} (Phase {self.phase_aktuell}, {self.status})"


def wurzel() -> Path:
    return Path(__file__).resolve().parents[WURZEL_TIEFE]


def datei_pfad(wurzel_dir: Path | None = None) -> Path:
    return (wurzel_dir or wurzel()) / "Agenten" / DATEINAME


def laden(wurzel_dir: Path | None = None) -> list[FremdPhase]:
    """Alle Eintraege lesen. Fehlende oder kaputte Datei ergibt leere Liste."""
    pfad = datei_pfad(wurzel_dir)
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    eintraege = []
    for e in roh.get("eintraege", []):
        if not all(k in e for k in PFLICHT):
            continue
        if not isinstance(e["phase_aktuell"], int) or e["phase_aktuell"] not in PHASEN:
            continue
        if e["status"] not in STATI:
            continue
        eintraege.append(FremdPhase(
            name=e["name"],
            pfad=e["pfad"],
            rolle=e["rolle"],
            phase_aktuell=e["phase_aktuell"],
            status=e["status"],
            geaendert=e["geaendert"],
            blockiert_weil=e.get("blockiert_weil"),
            notiz=e.get("notiz"),
        ))
    return eintraege


def setzen(
    name: str,
    phase: int,
    status: str,
    blockiert_weil: str | None = None,
    notiz: str | None = None,
    pfad: str | None = None,
    rolle: str | None = None,
    wurzel_dir: Path | None = None,
) -> FremdPhase:
    """Einen Eintrag anlegen oder aktualisieren. Schreibt FREMD-Phasen.json."""
    dp = datei_pfad(wurzel_dir)
    try:
        roh = json.loads(dp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        roh = {"eintraege": []}

    heute = str(date.today())
    eintraege = roh.get("eintraege", [])
    gefunden = False
    for e in eintraege:
        if e.get("name") == name:
            e["phase_aktuell"] = phase
            e["status"] = status
            e["blockiert_weil"] = blockiert_weil
            if notiz is not None:
                e["notiz"] = notiz
            if pfad is not None:
                e["pfad"] = pfad
            if rolle is not None:
                e["rolle"] = rolle
            e["geaendert"] = heute
            gefunden = True
            break

    if not gefunden:
        if not pfad:
            raise ValueError(f"Neuer Eintrag '{name}' braucht --pfad")
        if not rolle:
            raise ValueError(f"Neuer Eintrag '{name}' braucht --rolle")
        eintraege.append({
            "name": name,
            "pfad": pfad,
            "rolle": rolle,
            "phase_aktuell": phase,
            "status": status,
            "blockiert_weil": blockiert_weil,
            "notiz": notiz,
            "geaendert": heute,
        })

    roh["eintraege"] = eintraege
    roh["stand"] = heute

    tmp = dp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(roh, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(dp)

    alle = laden(wurzel_dir)
    return next(e for e in alle if e.name == name)


def pruefen(wurzel_dir: Path | None = None) -> list[str]:
    """Konsistenzcheck. Leer = gesund."""
    w = wurzel_dir or wurzel()
    dp = datei_pfad(w)
    befunde: list[str] = []

    if not dp.is_file():
        return [f"Datei fehlt: {dp}"]
    try:
        roh = json.loads(dp.read_text(encoding="utf-8"))
    except ValueError as ex:
        return [f"Kein gueltiges JSON: {ex}"]

    eintraege = roh.get("eintraege")
    if not isinstance(eintraege, list) or not eintraege:
        return ["Keine Eintraege."]

    gesehen: set[str] = set()
    for i, e in enumerate(eintraege):
        kopf = f"Eintrag {i + 1}"
        for feld in PFLICHT:
            if feld not in e:
                befunde.append(f"{kopf}: Pflichtfeld '{feld}' fehlt.")
        name = e.get("name", f"#{i + 1}")
        kopf = f"'{name}'"
        phase = e.get("phase_aktuell")
        if not isinstance(phase, int) or phase not in PHASEN:
            befunde.append(f"{kopf}: phase_aktuell muss 0-4 sein, ist {phase!r}.")
        status = e.get("status")
        if status not in STATI:
            befunde.append(f"{kopf}: status muss eines von {STATI} sein, ist {status!r}.")
        if status == "blockiert" and not e.get("blockiert_weil"):
            befunde.append(f"{kopf}: status=blockiert ohne blockiert_weil.")
        pfad_str = e.get("pfad", "")
        if pfad_str and not (w / pfad_str).exists():
            befunde.append(f"{kopf}: Pfad '{pfad_str}' existiert nicht.")
        n = str(name).lower()
        if n in gesehen:
            befunde.append(f"{kopf}: Name doppelt.")
        gesehen.add(n)
    return befunde


def _tabelle(eintraege: list[FremdPhase]) -> None:
    fmt = "%-28s %5s  %-10s  %s"
    print(fmt % ("Name", "Phase", "Status", "Blockierung / Notiz"))
    print("-" * 80)
    for e in eintraege:
        extra = e.blockiert_weil or e.notiz or ""
        print(fmt % (e.name, e.phase_aktuell, e.status, extra[:44]))


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Fremdrepo-Integrationsphasen")
    p.add_argument("--liste", action="store_true", help="Tabelle ausgeben")
    p.add_argument("--json", action="store_true", help="JSON ausgeben")
    p.add_argument("--pruefen", action="store_true", help="Konsistenzcheck")
    p.add_argument("--befund", metavar="NAME", help="Exitcode 1 wenn blockiert")
    p.add_argument("--setze", metavar="NAME", help="Eintrag anlegen/aktualisieren")
    p.add_argument("--phase", type=int, choices=PHASEN)
    p.add_argument("--status", choices=STATI)
    p.add_argument("--blockiert-weil", default=None)
    p.add_argument("--notiz", default=None)
    p.add_argument("--pfad", default=None)
    p.add_argument("--rolle", default=None)
    a = p.parse_args()

    if a.liste:
        _tabelle(laden())
        return 0

    if a.json:
        dp = datei_pfad()
        print(dp.read_text(encoding="utf-8") if dp.is_file() else "[]")
        return 0

    if a.pruefen:
        bs = pruefen()
        print("\n".join(bs) if bs else f"gesund: {len(laden())} Eintraege")
        return 1 if bs else 0

    if a.befund:
        for e in laden():
            if e.name == a.befund:
                if e.status == "blockiert":
                    print(f"{e.name}: blockiert — {e.blockiert_weil or '(kein Grund)'}")
                    return 1
                print(f"{e.name}: {e.status} (Phase {e.phase_aktuell})")
                return 0
        print(f"{a.befund}: nicht gefunden")
        return 2

    if a.setze:
        if a.phase is None or not a.status:
            print("--setze braucht --phase und --status", file=sys.stderr)
            return 1
        try:
            e = setzen(
                a.setze, a.phase, a.status,
                blockiert_weil=a.blockiert_weil,
                notiz=a.notiz,
                pfad=a.pfad,
                rolle=a.rolle,
            )
            print(f"Gesetzt: {e}")
        except ValueError as ex:
            print(str(ex), file=sys.stderr)
            return 1
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
