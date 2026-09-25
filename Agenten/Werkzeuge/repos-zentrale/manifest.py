"""Das Manifest lesen, pruefen und mit der Platte zusammenfuehren.

Das Manifest ist die EINZIGE Stelle, an der ein Startbefehl steht. Es wird
hier nicht erfunden: fehlt der Befehl, ist das ein Zustand ("kein Startbefehl
belegt"), kein Fehler. Die Platte schlaegt das Manifest im Zustand - ein Klon
ohne Eintrag verschwindet nicht, er erscheint als "neu".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import scan

# Feste Reihenfolge, damit das Fenster bei jedem Lauf gleich aussieht.
GRUPPEN_REIHENFOLGE = ("startbar", "einrichten", "neu", "doku", "fehlt")


@dataclass
class Eintrag:
    """Ein Repo im Manifest, so wie es in der Datei steht."""

    ordner: str
    art: str = ""
    gruppe: str = ""          # "doku" erzwingt die Gruppe NUR DOKU
    start: list[str] | None = None
    einrichten: list[str] | None = None
    bauen: list[str] | None = None
    bot: str | None = None
    notiz: str = ""
    anleitung: str = ""                 # Klartext-Ablauf fuer das Fenster
    befehle: list[dict] | None = None   # anklickbare Befehle (was/cmd/hinweis)
    warnungen: list[str] = field(default_factory=list)   # stoert den Start NICHT
    venv_pflicht: bool = False
    node_modules_pflicht: bool = False
    pfad_pflicht: str | None = None   # Datei/Ordner im Repo, ohne den der Start nicht geht
    port: int | None = None
    fehler: list[str] = field(default_factory=list)
    erlaubt: bool = True


@dataclass
class Zeile:
    """Eine Zeile im Fenster: Manifest-Eintrag plus das, was die Platte sagt."""

    ordner: str
    gruppe: str
    repo: scan.Repo | None = None
    art: str = ""
    start: list[str] | None = None
    einrichten: list[str] | None = None
    bot: str | None = None
    bot_da: bool = False
    notiz: str = ""
    anleitung: str = ""
    befehle: list[dict] = field(default_factory=list)
    gruende: list[str] = field(default_factory=list)

    @property
    def start_da(self) -> bool:
        return bool(self.start)


def _argv(wert, feld: str, fehler: list[str]) -> list[str] | None:
    """Ein Befehl ist eine nicht-leere Liste von Zeichenketten (argv, keine Shell)."""
    if wert is None:
        return None
    if isinstance(wert, list) and wert and all(isinstance(x, str) and x for x in wert):
        return list(wert)
    fehler.append(
        f"{feld} muss eine nicht-leere Liste von Zeichenketten sein (argv), "
        f"gefunden: {type(wert).__name__}"
    )
    return None


def _befehle(wert, fehler: list[str]) -> list[dict] | None:
    """Die Befehlsliste: je Eintrag ein Titel und ein argv (keine Shell-Zeile).

    Ein kaputter Eintrag faellt EINZELN raus (mit Grund), die uebrigen bleiben -
    eine falsch geschriebene Zeile darf die ganze Liste nicht wegnehmen.
    """
    if wert is None:
        return None
    if not isinstance(wert, list):
        fehler.append(f"befehle muss eine Liste sein, gefunden: {type(wert).__name__}")
        return None
    sauber = []
    for i, roh in enumerate(wert, 1):
        if not isinstance(roh, dict):
            fehler.append(f"befehle[{i}] ist kein Objekt")
            continue
        cmd = _argv(roh.get("cmd"), f"befehle[{i}].cmd", fehler)
        if not cmd:
            continue
        sauber.append(
            {
                "was": str(roh.get("was") or ""),
                "cmd": cmd,
                "hinweis": str(roh.get("hinweis") or ""),
                "start": bool(roh.get("start")),
            }
        )
    return sauber


def _ordner_erlaubt(name) -> bool:
    """Ein Ordnername darf kein Pfad sein - kein Trenner, kein Aufstieg."""
    if not isinstance(name, str) or not name:
        return False
    if name in (".", ".."):
        return False
    return not any(t in name for t in ("/", "\\"))


def manifest_laden(pfad: Path | str) -> list[Eintrag]:
    """Manifest lesen. Eine fehlende oder kaputte Datei gibt eine leere Liste."""
    pfad = Path(pfad)
    if not pfad.is_file():
        return []
    try:
        rohdaten = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []
    if not isinstance(rohdaten, dict):
        return []
    eintraege = []
    for roh in rohdaten.get("repos") or []:
        if not isinstance(roh, dict):
            continue
        ordner = roh.get("ordner") or ""
        fehler: list[str] = []
        warnungen: list[str] = []
        eintrag = Eintrag(
            ordner=ordner,
            art=str(roh.get("art") or ""),
            gruppe=str(roh.get("gruppe") or ""),
            start=_argv(roh.get("start"), "start", fehler),
            einrichten=_argv(roh.get("einrichten"), "einrichten", fehler),
            bauen=_argv(roh.get("bauen"), "bauen", fehler),
            bot=str(roh["bot"]).lower() if roh.get("bot") else None,
            notiz=str(roh.get("notiz") or ""),
            anleitung=str(roh.get("anleitung") or ""),
            befehle=_befehle(roh.get("befehle"), warnungen),
            warnungen=warnungen,
            venv_pflicht=bool(roh.get("venv_pflicht")),
            node_modules_pflicht=bool(roh.get("node_modules_pflicht")),
            pfad_pflicht=(
                str(roh["pfad_pflicht"])
                if roh.get("pfad_pflicht") and ".." not in str(roh["pfad_pflicht"])
                else None
            ),
            port=roh.get("port") if isinstance(roh.get("port"), int) else None,
            fehler=fehler,
        )
        if not _ordner_erlaubt(ordner):
            eintrag.erlaubt = False
            eintrag.fehler.append(f"Ordnername unbrauchbar: {ordner!r}")
        eintraege.append(eintrag)
    return eintraege


def _zeile(repo: scan.Repo, e: Eintrag, profile_dir: Path | None) -> Zeile:
    bot_da = bool(e.bot) and profile_dir is not None and (
        Path(profile_dir) / e.bot / "config.yaml"
    ).is_file()

    # Was den START verhindert - nur das entscheidet ueber die Gruppe.
    startgruende = list(e.fehler)
    if e.start is None and not e.fehler:
        startgruende.append("kein Startbefehl belegt")
    if e.venv_pflicht and repo.venv is None:
        startgruende.append("venv fehlt")
    if e.node_modules_pflicht and not repo.node_modules:
        startgruende.append("node_modules fehlt (npm install)")
    if e.pfad_pflicht and not (repo.pfad / e.pfad_pflicht).exists():
        startgruende.append(f"{e.pfad_pflicht} fehlt (bauen)")

    gruppe = "einrichten" if startgruende else "startbar"
    if e.gruppe == "doku":
        gruppe = "doku"

    # Der Bot ist ein Hinweis, kein Startkriterium: ein fehlendes Profil darf ein
    # lauffaehiges Repo nicht in eine andere Gruppe schieben.
    gruende = list(startgruende)
    gruende += list(e.warnungen)
    if e.bot and not bot_da:
        gruende.append(f"Bot-Profil fehlt: {e.bot}")

    return Zeile(
        ordner=repo.ordner,
        gruppe=gruppe,
        repo=repo,
        art=repo.art,
        start=e.start,
        einrichten=e.einrichten,
        bot=e.bot,
        bot_da=bot_da,
        notiz=e.notiz,
        anleitung=e.anleitung,
        befehle=list(e.befehle or []),
        gruende=gruende,
    )


def zeilen_bauen(
    repos: list[scan.Repo],
    eintraege: list[Eintrag],
    profile_dir: Path | str | None,
    repos_basis: Path | str,
) -> list[Zeile]:
    """Platte und Manifest zu Fensterzeilen zusammenfuehren."""
    profile_dir = Path(profile_dir) if profile_dir else None
    repos_basis = Path(repos_basis)
    nach_ordner = {e.ordner: e for e in eintraege if e.erlaubt}

    zeilen: list[Zeile] = []
    for repo in repos:
        e = nach_ordner.get(repo.ordner)
        if e is None:
            zeilen.append(
                Zeile(
                    ordner=repo.ordner,
                    gruppe="neu",
                    repo=repo,
                    art=repo.art,
                    gruende=["kein Eintrag im Manifest"] + list(repo.zurueckhaltung),
                )
            )
            continue
        zeilen.append(_zeile(repo, e, profile_dir))

    for e in eintraege:
        if e.erlaubt and not (repos_basis / e.ordner).is_dir():
            zeilen.append(
                Zeile(
                    ordner=e.ordner,
                    gruppe="fehlt",
                    art=e.art,
                    bot=e.bot,
                    notiz=e.notiz,
                    gruende=["Ordner fehlt im Repo-Bestand"],
                )
            )
    return zeilen


def reihenfolge_index(gruppe: str) -> int:
    """Sortierhilfe: die feste Gruppenreihenfolge, Unbekanntes nach hinten."""
    try:
        return GRUPPEN_REIHENFOLGE.index(gruppe)
    except ValueError:
        return len(GRUPPEN_REIHENFOLGE)
