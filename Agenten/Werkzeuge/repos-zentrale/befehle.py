"""Was man mit einem Repo tun kann - als anklickbare Kommandos.

Der Zweck: Die Zentrale soll nicht nur Knoepfe zeigen, sondern sagen, WAS ein
Repo kann und WIE man es aufruft. Jedes Kommando traegt einen Klartext-Titel,
den fertigen Befehl und einen Hinweis, wo die Ausgabe landet.

Zwei Quellen, bewusst getrennt:

- **`grundkommandos`** - fuer jeden Eintrag gleich: Ordner, Terminal, Doku, Bot,
  Start. Sie brauchen kein Wissen ueber das Repo und werden nicht erfunden.
- **`manifestkommandos`** - das Feld `befehle` im Manifest: nur was einmal
  wirklich gelaufen ist (Hausregel), mit Titel und Hinweis.

Diese Datei kennt kein tkinter und kein Fenster - sie ist ohne Bildschirm
pruefbar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Was ein Kommando ausloest. "befehl" laeuft im Terminal, die uebrigen rufen
# genau die Aktion auf, die auch der gleichnamige Knopf im Fenster hat.
ARTEN = ("befehl", "start", "terminal", "ordner", "doku", "bot")


@dataclass
class Kommando:
    """Ein Eintrag in der Befehlsliste des Fensters."""

    was: str                     # Titel in Klartext ("Kanalbericht")
    art: str = "befehl"          # siehe ARTEN
    cmd: list[str] = field(default_factory=list)
    hinweis: str = ""


def befehl_text(cmd: list[str] | None) -> str:
    """Ein argv als lesbare Zeile zum Kopieren. Leerzeichen werden gequotet."""
    if not cmd:
        return ""
    teile = []
    for teil in cmd:
        teile.append(f'"{teil}"' if " " in teil else teil)
    return " ".join(teile)


def grundkommandos(zeile) -> list[Kommando]:
    """Die Handgriffe, die es bei jedem Projekt gibt.

    Ein Eintrag ohne Ordner auf der Platte (Gruppe FEHLT) bekommt KEINE
    Handgriffe: es gibt nichts zu oeffnen, und ein Knopf, der ins Leere zeigt,
    ist schlimmer als keiner.
    """
    if getattr(zeile, "repo", None) is None:
        return []
    liste: list[Kommando] = []
    if getattr(zeile, "start", None):
        liste.append(
            Kommando("Starten", "start", list(zeile.start), "Ausgabe im Terminal, Beleg im Log")
        )
    liste.append(Kommando("Terminal hier oeffnen", "terminal", [], "dann von Hand eintippen"))
    liste.append(Kommando("Ordner im Explorer", "ordner", [], ""))
    if zeile.repo.readme:
        liste.append(Kommando("Doku (README) oeffnen", "doku", [], zeile.repo.readme))
    if getattr(zeile, "bot_da", False) and getattr(zeile, "bot", None):
        liste.append(
            Kommando(f"Bot {zeile.bot} fragen", "bot", [], "Chat im Projektordner")
        )
    return liste


def manifestkommandos(zeile) -> list[Kommando]:
    """Die im Manifest hinterlegten Befehle - in der Reihenfolge der Datei."""
    liste: list[Kommando] = []
    for eintrag in getattr(zeile, "befehle", None) or []:
        cmd = list(eintrag.get("cmd") or [])
        if not cmd:
            continue
        liste.append(
            Kommando(
                was=str(eintrag.get("was") or befehl_text(cmd)),
                art="start" if eintrag.get("start") else "befehl",
                cmd=cmd,
                hinweis=str(eintrag.get("hinweis") or ""),
            )
        )
    return liste


def kommandos(zeile) -> list[Kommando]:
    """Grundkommandos und Manifest-Befehle, in dieser Reihenfolge."""
    return grundkommandos(zeile) + manifestkommandos(zeile)


def _venv_zeile(zeile) -> str:
    repo = getattr(zeile, "repo", None)
    if repo is None:
        return "Venv: kein Ordner auf der Platte"
    if repo.venv:
        return f"Venv: vorhanden ({repo.venv}) - die Befehle unten nutzen es"
    return "Venv: fehlt - 'python -m venv .venv' im Ordner, dann die Abhaengigkeiten"


def anleitung(zeile) -> str:
    """Der Textblock neben der Befehlsliste: wozu das Projekt da ist und wie man es anfasst."""
    teile: list[str] = []
    kopf = [getattr(zeile, "bereich", "") or "", getattr(zeile, "rolle", "") or ""]
    kopf = [t for t in kopf if t]
    if kopf:
        teile.append(" · ".join(kopf))
    if getattr(zeile, "notiz", ""):
        teile.append(f"Wozu: {zeile.notiz}")
    if getattr(zeile, "ordner", ""):
        pfad = getattr(getattr(zeile, "repo", None), "pfad", "")
        teile.append(f"Ordner: {pfad or zeile.ordner}")
    teile.append(_venv_zeile(zeile))
    if getattr(zeile, "gruende", None):
        teile.append("Zu tun: " + "; ".join(zeile.gruende))
    eigen = (getattr(zeile, "anleitung", "") or "").strip()
    if eigen:
        teile.append("")
        teile.append(eigen)
    else:
        teile.append("")
        teile.append(
            "Fuer dieses Repo ist noch kein Ablauf hinterlegt. Die Befehle unten sind die "
            "allgemeinen Handgriffe; eigene Befehle kommen in Agenten/Werkzeuge/repos-zentrale/"
            "repos-zentrale.json unter \"befehle\"."
        )
    return "\n".join(teile)