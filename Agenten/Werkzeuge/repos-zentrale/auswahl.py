"""Die Filter der Zentrale - als reine Rechnung, ohne Fenster pruefbar.

Das Fenster kennt zwei Arten zu filtern, und beide gehoeren hierher:

| Art | Beispiel | Wird von |
|---|---|---|
| Text | `kraken` in Name, Notiz, Pfad, Rolle, Art | Suchfeld |
| Kennzeichen | "nur auffaellig", "nur mit Start", "nur fremd" | Chips (an/aus) |

Dazu die Auswahl von Bereich (REPOS/WERKSTATT/HANDEL) und Gruppe
(STARTBAR/EINRICHTEN/NEU/NUR DOKU/FEHLT).

Regel: **die Kennzeichen wirken UND-verknuepft, der Text wirkt UND dazu.** Ein
ODER zwischen den Chips waere bequemer zu bedienen und schwerer zu verstehen -
wer "nur auffaellig" und "nur fremd" anmacht, will die Schnittmenge, nicht die
Vereinigung.

Sonderfall `scharf`: der Zustand steht nicht in der Zeile, sondern kommt von
aussen (handelstand.py) - dieses Modul fragt nur, ob eine Zeile als scharf
GEMELDET ist (`zeile.scharf`/`zeile.spur`-Attribute sind optional). Fehlt die
Angabe, gilt die Zeile als nicht scharf.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ALLE = "Alle"
ALLE_GRUPPEN = "Alle Gruppen"

GRUPPEN_TITEL = {
    "startbar": "STARTBAR",
    "einrichten": "EINRICHTEN",
    "neu": "NEU",
    "kein_start": "KEIN EIGENER START",
    "doku": "NUR DOKU",
    "fehlt": "FEHLT",
}

# Titel zurueck auf den Schluessel: die Gruppenauswahl im Fenster zeigt die
# Ueberschriften ("NUR DOKU"), gefiltert wird aber ueber den Schluessel
# ("doku"). Ohne diese Zuordnung waere der Gruppenfilter immer leer - ein
# Fehler, den man am Bildschirm fuer "es gibt nichts" haelt.
GRUPPEN_SCHLUESSEL = {v.lower(): k for k, v in GRUPPEN_TITEL.items()}


def gruppe_schluessel(name: str) -> str:
    """Einen Gruppennamen auf den Schluessel bringen ('NUR DOKU' -> 'doku')."""
    roh = str(name or "").split(" (")[0].strip().lower()
    if not roh or name == ALLE_GRUPPEN:
        return ""
    return GRUPPEN_SCHLUESSEL.get(roh, roh)

# Kennzeichen -> Klartext fuer den Knopf. Kurz halten: fuenf Chips muessen in
# eine Zeile passen.
KENNZEICHEN_TITEL = {
    "auffaellig": "auffaellig",
    "startbar": "startbar",
    "mit_start": "mit Start",
    "mit_bot": "mit Bot",
    "fremd": "fremd",
    "eigen": "eigen",
    "handel": "nur Handel",
    "spuren": "nur Spuren",
    "scharf": "scharf",
    "ohne_start": "ohne Start",
}


@dataclass(frozen=True)
class Filter:
    """Alles, was die Anzeige einschraenkt."""

    text: str = ""
    bereich: str = ""
    gruppe: str = ALLE_GRUPPEN
    kennzeichen: tuple[str, ...] = field(default_factory=tuple)

    def mit(self, kennzeichen: str) -> bool:
        return kennzeichen in self.kennzeichen


def _fremd(zeile) -> bool:
    return any(str(g).startswith("fremd:") for g in getattr(zeile, "gruende", []) or [])


def _text_trifft(zeile, text: str, ort: str = "") -> bool:
    teile = [
        getattr(zeile, "ordner", "") or "",
        getattr(zeile, "bot", "") or "",
        getattr(zeile, "notiz", "") or "",
        getattr(zeile, "anleitung", "") or "",
        getattr(zeile, "art", "") or "",
        getattr(zeile, "rolle", "") or "",
        getattr(zeile, "bereich", "") or "",
        orts_text(zeile, ort),
    ]
    return any(text in t.lower() for t in teile)


def orts_text(zeile, ort: str = "") -> str:
    """Der Pfad einer Zeile, wenn sie einen hat (Werkzeugdateien haben keinen Ordner-Pfad)."""
    repo = getattr(zeile, "repo", None)
    if repo is None:
        return ""
    return str(getattr(repo, "pfad", "") or "")


def kennzeichen_trifft(zeile, kennzeichen: str) -> bool:
    """Prueft EIN Kennzeichen gegen EINE Zeile."""
    gruppe = getattr(zeile, "gruppe", "")
    if kennzeichen == "auffaellig":
        return gruppe in ("neu", "fehlt")
    if kennzeichen == "startbar":
        return gruppe == "startbar"
    if kennzeichen == "mit_start":
        return bool(getattr(zeile, "start", None))
    if kennzeichen == "ohne_start":
        return not getattr(zeile, "start", None)
    if kennzeichen == "mit_bot":
        return bool(getattr(zeile, "bot_da", False))
    if kennzeichen == "fremd":
        return _fremd(zeile)
    if kennzeichen == "eigen":
        return not _fremd(zeile)
    if kennzeichen == "handel":
        return getattr(zeile, "bereich", "") == "HANDEL"
    if kennzeichen == "spuren":
        return bool(getattr(zeile, "spur", ""))
    if kennzeichen == "scharf":
        return bool(getattr(zeile, "scharf", False))
    return True          # unbekanntes Kennzeichen schraenkt nicht ein


def trifft(zeile, f: Filter) -> bool:
    """Erfuellt diese Zeile den Filter? (leerer Filter laesst alles durch)"""
    bereich = (f.bereich or "").strip()
    if bereich and bereich not in (ALLE, "Alle Bereiche"):
        # Der Bereich kann als "HANDEL (124)" ankommen - die Zahl abschneiden.
        if bereich.split(" (")[0] != getattr(zeile, "bereich", ""):
            return False
    gruppe = (f.gruppe or "").strip()
    if gruppe and gruppe != ALLE_GRUPPEN:
        if gruppe_schluessel(gruppe) != str(getattr(zeile, "gruppe", "")).lower():
            return False
    for k in f.kennzeichen:
        if not kennzeichen_trifft(zeile, k):
            return False
    text = (f.text or "").strip().lower()
    if text and not _text_trifft(zeile, text):
        return False
    return True


def filtern(zeilen: list, f: Filter) -> list:
    """Alle Zeilen, die den Filter erfuellen - in der uebergebenen Reihenfolge."""
    return [z for z in zeilen if trifft(z, f)]


def beschreibung(f: Filter) -> str:
    """Der Filter in Worten (fuer die Statuszeile) - leer, wenn nichts gesetzt ist."""
    teile = []
    if f.bereich and f.bereich not in (ALLE, "Alle Bereiche"):
        teile.append(f.bereich.split(" (")[0])
    if f.gruppe and f.gruppe != ALLE_GRUPPEN:
        teile.append(f.gruppe.split(" (")[0].upper())
    teile += [KENNZEICHEN_TITEL.get(k, k) for k in f.kennzeichen]
    if (f.text or "").strip():
        teile.append(f'"{f.text.strip()}"')
    return " · ".join(teile)