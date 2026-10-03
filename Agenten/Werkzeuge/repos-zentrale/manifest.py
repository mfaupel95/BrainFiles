"""Das Manifest lesen, pruefen und mit der Platte zusammenfuehren.

Das Manifest ist die EINZIGE Stelle, an der ein Startbefehl steht. Es wird
hier nicht erfunden: fehlt der Befehl, ist das ein Zustand ("kein Startbefehl
belegt"), kein Fehler. Die Platte schlaegt das Manifest im Zustand - ein Ordner
ohne Eintrag verschwindet nicht, er erscheint als "neu".

Seit 30.09.2026 traegt ein Eintrag eine **Wurzel** (`wurzel`, Vorgabe "repos")
und darin einen **Pfad** (`pfad`, Vorgabe = Ordnername). Damit steht die
Zentrale auf mehreren Orten gleichzeitig, ohne dass ein Name doppelt sein darf:
der Schluessel eines Eintrags ist das Paar (wurzel, pfad).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import quellen
import scan

# Feste Reihenfolge, damit das Fenster bei jedem Lauf gleich aussieht.
GRUPPEN_REIHENFOLGE = ("startbar", "einrichten", "neu", "kein_start", "doku", "fehlt")


@dataclass
class Eintrag:
    """Ein Projekt im Manifest, so wie es in der Datei steht."""

    ordner: str
    art: str = ""
    gruppe: str = ""          # "doku" erzwingt die Gruppe NUR DOKU
    start: list[str] | None = None
    einrichten: list[str] | None = None
    bauen: list[str] | None = None
    # Ketten: mehrere Befehle NACHEINANDER (venv anlegen, dann Abhaengigkeiten).
    # Bewusst eine Liste von argv-Listen und KEINE Shell-Zeile - die Hausregel
    # "argv, nie eine Zeichenkette" gilt auch fuer eine Kette.
    einrichten_kette: list[list[str]] | None = None
    bauen_kette: list[list[str]] | None = None
    bot: str | None = None
    notiz: str = ""
    anleitung: str = ""                 # Klartext-Ablauf fuer das Fenster
    befehle: list[dict] | None = None   # anklickbare Befehle (was/cmd/hinweis)
    warnungen: list[str] = field(default_factory=list)   # stoert den Start NICHT
    venv_pflicht: bool = False
    node_modules_pflicht: bool = False
    pfad_pflicht: str | None = None   # Datei/Ordner im Projekt, ohne den der Start nicht geht
    port: int | None = None
    # Zeitfenster fuer den Beleg-Lauf (fuellen --belege). Vorgabe FRIST_S (90 s)
    # reicht fuer schnelle Starts; lange Laeufe (Training) setzen es je Eintrag.
    beleg_frist_s: int | None = None
    fehler: list[str] = field(default_factory=list)
    erlaubt: bool = True
    wurzel: str = "repos"             # Kennung aus quellen.py
    pfad: str = ""                    # Pfad innerhalb der Wurzel (Vorgabe: ordner)
    rolle: str = ""                   # Klartext-Rolle (Spur, Werkzeug, Ausgabe, Ablage)

    def __post_init__(self) -> None:
        if not self.pfad:
            self.pfad = self.ordner


@dataclass
class Zeile:
    """Eine Zeile im Fenster: Manifest-Eintrag plus das, was die Platte sagt."""

    ordner: str
    gruppe: str
    repo: scan.Repo | None = None
    art: str = ""
    start: list[str] | None = None
    einrichten: list[str] | None = None
    bauen: list[str] | None = None
    einrichten_kette: list[list[str]] | None = None
    bauen_kette: list[list[str]] | None = None
    venv_pflicht: bool = False
    node_modules_pflicht: bool = False
    pfad_pflicht: str | None = None
    port: int | None = None
    beleg_frist_s: int | None = None
    bot: str | None = None
    bot_da: bool = False
    notiz: str = ""
    anleitung: str = ""
    befehle: list[dict] = field(default_factory=list)
    gruende: list[str] = field(default_factory=list)
    wurzel: str = "repos"
    bereich: str = "REPOS"
    rolle: str = ""

    @property
    def start_da(self) -> bool:
        return bool(self.start)

    @property
    def schluessel(self) -> tuple[str, str]:
        return (self.wurzel, (self.repo.pfad_rel if self.repo is not None else self.ordner))


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


def _ketten(wert, feld: str, fehler: list[str]) -> list[list[str]] | None:
    """Eine Kette von Befehlen: je Eintrag ein argv, hoechstens acht Schritte.

    Ein kaputter Schritt faellt EINZELN raus (mit Grund), die uebrigen bleiben -
    wie bei `befehle`. Eine leere Kette gibt None.
    """
    if wert is None:
        return None
    if not isinstance(wert, list):
        fehler.append(f"{feld} muss eine Liste von Befehlen sein, "
                      f"gefunden: {type(wert).__name__}")
        return None
    sauber: list[list[str]] = []
    for i, roh in enumerate(wert[:8], 1):
        cmd = _argv(roh, f"{feld}[{i}]", fehler)
        if cmd:
            sauber.append(cmd)
    return sauber or None


def _ordner_erlaubt(name) -> bool:
    """Ein Ordnername darf kein Pfad sein - kein Trenner, kein Aufstieg."""
    if not isinstance(name, str) or not name:
        return False
    if name in (".", ".."):
        return False
    return not any(t in name for t in ("/", "\\"))


def _pfad_erlaubt(pfad) -> bool:
    """Ein Pfad IM Projekt darf Unterordner nennen, aber nicht ausbrechen.

    `Projekte/NautilusTrader` und
    `freqtrade/user_data/strategies/ema_cross.py` sind erlaubt (die Wurzeln
    liegen unterschiedlich tief); `../../etc`, `C:/x` und Backslashes nicht.
    """
    if not isinstance(pfad, str) or not pfad:
        return False
    if ".." in pfad or "\\" in pfad or pfad.startswith("/") or ":" in pfad:
        return False
    return len([t for t in pfad.split("/") if t]) <= 8


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
            einrichten_kette=_ketten(roh.get("einrichten_kette"), "einrichten_kette", fehler),
            bauen_kette=_ketten(roh.get("bauen_kette"), "bauen_kette", fehler),
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
            beleg_frist_s=roh.get("beleg_frist_s") if isinstance(roh.get("beleg_frist_s"), int) and roh.get("beleg_frist_s") > 0 else None,
            fehler=fehler,
            wurzel=str(roh.get("wurzel") or "repos"),
            pfad=str(roh.get("pfad") or ""),
            rolle=str(roh.get("rolle") or ""),
        )
        # Die Vermerke des Eintrags lesen. Das Feld stand seit jeher in der
        # Datei und wurde nie gelesen - ein Vermerk, den niemand sieht, ist
        # keiner (gefunden am 30.09.2026, als `kein_start` darauf aufbauen
        # sollte).
        rohe_warnungen = roh.get("warnungen")
        if isinstance(rohe_warnungen, list):
            eintrag.warnungen.extend(
                str(w) for w in rohe_warnungen if isinstance(w, str) and w.strip()
            )
        elif rohe_warnungen:
            eintrag.fehler.append(
                f"warnungen muss eine Liste von Texten sein, "
                f"gefunden: {type(rohe_warnungen).__name__}"
            )
        if not _ordner_erlaubt(ordner):
            eintrag.erlaubt = False
            eintrag.fehler.append(f"Ordnername unbrauchbar: {ordner!r}")
        if not _pfad_erlaubt(eintrag.pfad):
            eintrag.erlaubt = False
            eintrag.fehler.append(f"Pfad unbrauchbar: {eintrag.pfad!r}")
        if quellen.wurzel_von(eintrag.wurzel) is None:
            eintrag.erlaubt = False
            eintrag.fehler.append(f"unbekannte Wurzel: {eintrag.wurzel!r}")
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

    # Fremd-Material kommt aus EINER Quelle (Agenten/FREMD-Liste.json), nicht aus
    # handgepflegten Manifest-Feldern: die Rolle sagt, was es ist, der Hinweis
    # sagt, was damit zu tun ist. Das Manifest darf die Rolle ueberschreiben -
    # dann steht sie so im Fenster, und die Liste bleibt die Herkunftsangabe.
    rolle = e.rolle
    fremd_treffer = None
    modul = quellen.fremd_modul()
    if modul is not None:
        fremd_treffer = modul.ist_fremd(
            quellen.pfad_in_wurzel(repo.wurzel, repo.pfad_rel)
        )
    if fremd_treffer is not None:
        rolle = rolle or fremd_treffer.art

    # KEIN EIGENER START (30.09.2026): eine Zeile ohne Startbefehl ist nicht
    # automatisch unfertig. Fremdes, das nur gelesen wird, und eine Klasse, die
    # ein anderes Programm laedt, brauchen gar keinen - sie in EINRICHTEN zu
    # stellen hiesse "es fehlt noch etwas", und das waere falsch. Was hier
    # landet, ist eine Aussage ueber den Grund, nicht ueber einen Mangel.
    #
    # Die Bedingung ist eng: es darf KEIN anderer Grund vorliegen (ein fehlendes
    # venv bleibt EINRICHTEN), und der Grund muss dabeistehen - als kuratierte
    # Gruppe, als Vermerk (`warnungen`, z. B. aus fuellen.OHNE_START) oder in
    # der Fremd-Liste als "nur lesen".
    nur_der_befehl = startgruende == ["kein Startbefehl belegt"]
    if nur_der_befehl and not e.start and (
        e.gruppe == "kein_start"
        or e.warnungen
        or (fremd_treffer is not None and "nur lesen" in fremd_treffer.regel)
    ):
        gruppe = "kein_start"

    # Der Bot ist ein Hinweis, kein Startkriterium: ein fehlendes Profil darf ein
    # lauffaehiges Projekt nicht in eine andere Gruppe schieben.
    gruende = list(startgruende)
    gruende += list(e.warnungen)
    if e.bot and not bot_da:
        gruende.append(f"Bot-Profil fehlt: {e.bot}")
    if fremd_treffer is not None:
        gruende.append(f"fremd: {fremd_treffer.regel} ({fremd_treffer.herkunft})")

    return Zeile(
        ordner=repo.ordner,
        gruppe=gruppe,
        repo=repo,
        art=repo.art,
        start=e.start,
        einrichten=e.einrichten,
        bauen=e.bauen,
        einrichten_kette=e.einrichten_kette,
        bauen_kette=e.bauen_kette,
        venv_pflicht=e.venv_pflicht,
        node_modules_pflicht=e.node_modules_pflicht,
        pfad_pflicht=e.pfad_pflicht,
        port=e.port,
        beleg_frist_s=e.beleg_frist_s,
        bot=e.bot,
        bot_da=bot_da,
        notiz=e.notiz,
        anleitung=e.anleitung,
        befehle=list(e.befehle or []),
        gruende=gruende,
        wurzel=repo.wurzel,
        bereich=quellen.bereich(repo.wurzel),
        rolle=rolle,
    )


def zeilen_bauen(
    plaetze: list[tuple[quellen.Wurzel, list[scan.Repo]]],
    eintraege: list[Eintrag],
    profile_dir: Path | str | None,
) -> list[Zeile]:
    """Platte und Manifest zu Fensterzeilen zusammenfuehren.

    `plaetze` ist je Wurzel die Liste der dort gefundenen Ordner. Ein Eintrag
    ohne Ordner auf der Platte wird "fehlt" - aber nur in SEINER Wurzel; ein
    gleichnamiger Ordner in einer anderen Wurzel ist ein anderer Eintrag.
    """
    profile_dir = Path(profile_dir) if profile_dir else None
    nach_schluessel = {(e.wurzel, e.pfad): e for e in eintraege if e.erlaubt}

    zeilen: list[Zeile] = []
    for wurzel_obj, repos in plaetze:
        for repo in repos:
            e = nach_schluessel.get((repo.wurzel, repo.pfad_rel))
            if e is None:
                zeilen.append(
                    Zeile(
                        ordner=repo.ordner,
                        gruppe="neu",
                        repo=repo,
                        art=repo.art,
                        gruende=["kein Eintrag im Manifest"] + list(repo.zurueckhaltung),
                        wurzel=repo.wurzel,
                        bereich=quellen.bereich(repo.wurzel),
                    )
                )
                continue
            zeilen.append(_zeile(repo, e, profile_dir))

    for e in eintraege:
        if e.erlaubt and (e.wurzel, e.pfad) not in nach_schluessel_platte(plaetze):
            zeilen.append(
                Zeile(
                    ordner=e.ordner,
                    gruppe="fehlt",
                    art=e.art,
                    bot=e.bot,
                    notiz=e.notiz,
                    gruende=["Ordner fehlt in dieser Wurzel"],
                    wurzel=e.wurzel,
                    bereich=quellen.bereich(e.wurzel),
                    rolle=e.rolle,
                )
            )
    return zeilen


def nach_schluessel_platte(
    plaetze: list[tuple[quellen.Wurzel, list[scan.Repo]]],
) -> set[tuple[str, str]]:
    """Die Schluessel aller Ordner, die wirklich auf der Platte liegen."""
    return {(r.wurzel, r.pfad_rel) for _, repos in plaetze for r in repos}


def reihenfolge_index(gruppe: str) -> int:
    """Sortierhilfe: die feste Gruppenreihenfolge, Unbekanntes nach hinten."""
    try:
        return GRUPPEN_REIHENFOLGE.index(gruppe)
    except ValueError:
        return len(GRUPPEN_REIHENFOLGE)
