"""Die Grenze zwischen eigenem Code und Fremd-Material im Baum.

Warum es dieses Modul gibt: Fremd-Material liegt mitten in eigenen Ordnern
(`Agenten/Handel/OpenAlice` macht 81 % der Zeilen in `Agenten/Handel`), und jede
Bestands-, Such- oder Aufraeumfrage musste es bisher im Kopf abziehen. Hier steht
die Liste EINMAL: `Agenten/FREMD-Liste.json` - gelesen von Python (dieses Modul)
und von PowerShell (`ConvertFrom-Json`), angezeigt als `Agenten/FREMD.md`.

Was fremd heisst: Material, das wir **nicht pflegen** - ein Klon, ein Import, ein
Fremdprojekt im eigenen Baum. Kriterium ist nicht Sprache, Groesse oder Qualitaet,
sondern die Frage: *aendern wir es, oder benutzen wir es?*

Drei Regeln, die daraus folgen:

1. Fremdes wird nicht gezaehlt (`ohne_fremd`, `bestand.py`).
2. Fremdes wird nicht aufgeraeumt (kein Umbenennen, Verschieben, Loeschen).
3. Fremdes wird nicht verschwiegen (die Zentrale zeigt es als Zeile mit Rolle
   und Herkunft).

Nur Standardbibliothek, keine absoluten Pfade - die Wurzel kommt aus `__file__`,
damit der Umzug auf eine andere Platte nichts bricht.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Agenten/Werkzeuge/fremd.py -> [0] Werkzeuge, [1] Agenten, [2] BrainFiles
WURZEL_TIEFE = 2
DATEINAME = "FREMD-Liste.json"
FELDER = ("pfad", "art", "herkunft", "regel", "warum")


@dataclass(frozen=True)
class Fremd:
    """Ein Eintrag der Liste: was, woher, und was damit zu tun ist."""

    pfad: str
    art: str
    herkunft: str
    regel: str
    warum: str
    nur_git: bool = False   # nur Git-Klone unter pfad sind fremd (Werkstatt seit 14.10.2026)

    def __str__(self) -> str:                                  # pragma: no cover
        return f"{self.pfad} ({self.art})"


def wurzel() -> Path:
    """Die BrainFiles-Wurzel - aus dem eigenen Ort, nicht aus dem Aufrufer."""
    return Path(__file__).resolve().parents[WURZEL_TIEFE]


def liste_pfad(wurzel_dir: Path | None = None) -> Path:
    return Path(wurzel_dir or wurzel()) / "Agenten" / DATEINAME


def _normal(rel: str) -> str:
    return str(rel).replace("\\", "/").strip("/").lower()


def _ist_git_kloon(rel_pfad: str) -> bool:
    """Liegt unter dem Pfad ein Git-Klon? (fuer Eintraege mit nur_git=True).

    Die Liste kennt nur relative Pfade; die Platte entscheidet. Ein Pfad ohne
    Ordner oder ohne .git ist kein Klon und damit nicht fremd.
    """
    try:
        p = wurzel() / rel_pfad.replace("\\", "/").strip("/")
    except OSError:
        return False
    return (p / ".git").exists()


def laden(wurzel_dir: Path | None = None) -> list[Fremd]:
    """Die Liste lesen. Eine fehlende oder kaputte Datei ergibt eine leere Liste -
    `pruefen()` sagt dann, was fehlt, statt hier zu werfen."""
    pfad = liste_pfad(wurzel_dir)
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    eintraege = []
    for e in roh.get("eintraege", []):
        if all(isinstance(e.get(f), str) for f in FELDER):
            eintraege.append(Fremd(
                **{f: e[f] for f in FELDER},
                nur_git=bool(e.get("nur_git", False)),
            ))
    return eintraege


def ist_fremd(rel_pfad, eintraege: list[Fremd] | None = None) -> Fremd | None:
    """Liegt dieser Pfad in fremdem Material? Der GENAUESTE Eintrag gewinnt.

    Verglichen wird auf Pfadgrenzen: `…/OpenAlice` trifft `…/OpenAlice/src`,
    aber nicht `…/OpenAlice2`. Gross-/Kleinschreibung spielt keine Rolle.
    """
    eintraege = laden() if eintraege is None else eintraege
    ziel = _normal(rel_pfad)
    treffer = None
    for e in eintraege:
        p = _normal(e.pfad)
        if ziel == p or ziel.startswith(p + "/"):
            if getattr(e, "nur_git", False) and not _ist_git_kloon(rel_pfad):
                continue
            if treffer is None or len(p) > len(_normal(treffer.pfad)):
                treffer = e
    return treffer


def ohne_fremd(pfade, eintraege: list[Fremd] | None = None) -> list:
    """Nur die Pfade, die NICHT in fremdem Material liegen."""
    eintraege = laden() if eintraege is None else eintraege
    return [p for p in pfade if ist_fremd(p, eintraege) is None]


def pruefen(
    wurzel_dir: Path | None = None,
    eigene_wurzeln=(),
) -> list[str]:
    """Befunde zur Liste selbst - leer heisst gesund.

    `eigene_wurzeln` sind die Pfade, die das Haus selbst fuehrt (die Zentrale
    kennt sie in `quellen.py`); ein Fremd-Eintrag darf keine davon SEIN. Sie
    werden hereingereicht statt hier wiederholt, damit es keine zweite Liste gibt.
    """
    w = Path(wurzel_dir or wurzel())
    datei = liste_pfad(w)
    befunde: list[str] = []

    if not datei.is_file():
        return [f"Liste fehlt: {datei}"]
    try:
        roh = json.loads(datei.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"Liste ist kein gueltiges JSON: {e}"]

    rohe = roh.get("eintraege")
    if not isinstance(rohe, list) or not rohe:
        return ["Die Liste hat keine Eintraege."]

    gesehen: set[str] = set()
    nur_git_eintraege: set[str] = set()
    for i, e in enumerate(rohe):
        kopf = f"Eintrag {i + 1}"
        for feld in FELDER:
            if not isinstance(e.get(feld), str) or not e[feld].strip():
                befunde.append(f"{kopf}: Feld '{feld}' fehlt oder ist leer.")
        pfad = e.get("pfad")
        if not isinstance(pfad, str) or not pfad:
            continue
        kopf = f"Eintrag '{pfad}'"
        if "\\" in pfad:
            befunde.append(f"{kopf}: Backslash im Pfad - bitte '/' verwenden.")
        if ".." in pfad.split("/"):
            befunde.append(f"{kopf}: '..' im Pfad - die Liste bleibt in der Wurzel.")
        if pfad.startswith("/") or ":" in pfad:
            befunde.append(f"{kopf}: absoluter Pfad - relativ zur Wurzel angeben.")
        n = _normal(pfad)
        if n in gesehen:
            befunde.append(f"{kopf}: doppelt in der Liste.")
        gesehen.add(n)
        nur_git = bool(e.get("nur_git", False))
        if nur_git:
            nur_git_eintraege.add(n)
        if not (w / pfad).exists():
            befunde.append(f"{kopf}: Ordner liegt nicht auf der Platte.")
        for eigene in eigene_wurzeln:
            if n == _normal(eigene):
                if nur_git:
                    # Ein nur_git-Eintrag liegt BEWUSST auf der eigenen Wurzel:
                    # er markiert nur die Git-Klone darunter (Werkstatt seit
                    # 14.10.2026), die Ablage selbst bleibt eigen.
                    continue
                befunde.append(f"{kopf}: ist eine EIGENE Wurzel ({eigene}) - "
                               f"eigen und fremd kann nicht beides gelten.")

    # Kein Baum im Baum: der genauere Eintrag waere toter Text. Ein nur_git-Netz
    # darf explizite Eintraege enthalten - die koennen eine eigene Regel tragen
    # und gewinnen ueber den laengsten Treffer.
    for a in gesehen:
        for b in gesehen:
            if a != b and a.startswith(b + "/") and b not in nur_git_eintraege:
                befunde.append(f"'{a}' liegt in '{b}' - ein Eintrag genuegt (der kuerzere).")
    return befunde


def als_text(wurzel_dir: Path | None = None) -> str:
    """Die Liste als Tabelle - fuer die Anzeige in Agenten/FREMD.md."""
    zeilen = ["| Pfad | Art | Herkunft | Regel |", "|---|---|---|---|"]
    for e in laden(wurzel_dir):
        zeilen.append(f"| `{e.pfad}` | {e.art} | {e.herkunft} | {e.regel} |")
    return "\n".join(zeilen)


if __name__ == "__main__":                                     # pragma: no cover
    import argparse

    p = argparse.ArgumentParser(description="Fremd-Material im BrainFiles-Baum")
    p.add_argument("--pruefen", action="store_true", help="nur pruefen")
    p.add_argument("--tabelle", action="store_true", help="die Anzeige ausgeben")
    a = p.parse_args()
    if a.tabelle:
        print(als_text())
    elif a.pruefen:
        b = pruefen()
        print("\n".join(b) if b else f"gesund: {len(laden())} Eintraege")
    else:
        for e in laden():
            print(f"{e.pfad:<60} {e.art:<16} {e.regel}")