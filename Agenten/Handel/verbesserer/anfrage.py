"""TP4, Teil 2: die reine Ordner- und Textlogik fuer den Anfrage-Typ
``verbesserung`` im Dauerlauf.

``dauerlauf.py`` ruft von hier nur duenn ab: einen offenen Vorschlag finden,
ihn als ``ANGEFRAGT`` markieren, einen Telegram-Kurztext bauen und den
wartenden Ordner wiederfinden, wenn ``/ja`` oder ``/nein`` kommt. Alles, was
danach passiert (Bytes schreiben, ``git apply``, committen, archivieren),
macht ``anwenden.py`` (Task 11).

Ein Vorschlagsordner heisst ``<YYYY-MM-DD>-<spurschluessel>`` und liegt direkt
unter ``berichte/``. Angewandte Vorschlaege wandern nach ``berichte/erledigt/``,
abgelehnte nach ``berichte/abgelehnt/`` - Ordner unter diesen beiden Namen
zaehlen hier nie als offen oder wartend.

Nur Standardbibliothek.
"""

from pathlib import Path

# Ordnernamen, die nie ein offener Vorschlag sein koennen - das Archiv von
# ``anwenden.py``.
_ARCHIV = ("erledigt", "abgelehnt")

# Marker-Datei, die ``markiere_angefragt`` anlegt: ab dann laeuft eine Anfrage
# und der Ordner wird von ``offener_vorschlag`` uebersprungen.
_MARKER = "ANGEFRAGT"


def _direkte_vorschlaege(berichte_dir):
    """Direkte Unterordner von ``berichte_dir``, alphabetisch, ohne die
    Archivordner ``erledigt/`` und ``abgelehnt/``.

    Ein fehlendes ``berichte_dir`` liefert einfach nichts.
    """
    berichte_dir = Path(berichte_dir)
    if not berichte_dir.is_dir():
        return
    for ordner in sorted(berichte_dir.iterdir(), key=lambda p: p.name):
        if not ordner.is_dir():
            continue
        teile = ordner.relative_to(berichte_dir).parts
        if any(teil in _ARCHIV for teil in teile):
            continue
        yield ordner


def _spur_aus_name(name):
    """Spurschluessel aus dem Ordnernamen ``<datum>-<spur>`` - ``lauf.py``
    schreibt hier ``spur1``. Leerer String, wenn der Name nicht passt."""
    teile = name.split("-", 3)
    return teile[-1] if len(teile) == 4 and teile[-1] else ""


def offener_vorschlag(berichte_dir):
    """Juengster direkter Unterordner von ``berichte_dir`` mit ``commit.txt``,
    der nicht in ``erledigt/``/``abgelehnt/`` liegt und noch keine Datei
    ``ANGEFRAGT`` traegt. ``None``, wenn keiner passt.

    "Juengster" heisst: der alphabetisch groesste Ordnername - die Namen sind
    datumspraefigiert (``2026-09-13-spur1``), das genuegt.
    """
    treffer = [o for o in _direkte_vorschlaege(berichte_dir)
               if (o / "commit.txt").is_file()
               and not (o / _MARKER).exists()]
    return treffer[-1] if treffer else None


def markiere_angefragt(ordner):
    """Leere Datei ``ordner/ANGEFRAGT`` anlegen. Existiert sie schon, bleibt
    sie unberuehrt."""
    (Path(ordner) / _MARKER).touch()


def wartet(berichte_dir):
    """Direkter Unterordner mit einer Datei ``ANGEFRAGT``, noch nicht in
    ``erledigt/``/``abgelehnt/``. ``None``, wenn keiner wartet. Bei mehreren
    der alphabetisch groesste (juengste)."""
    treffer = [o for o in _direkte_vorschlaege(berichte_dir)
               if (o / _MARKER).exists()]
    return treffer[-1] if treffer else None


def text(ordner):
    """Telegram-Kurztext zu einem Vorschlag: Spur, geaenderte Schluessel und
    OOS-Delta aus ``commit.txt``, dann die Schlusszeile mit ``/ja`` und
    ``/nein``.
    """
    ordner = Path(ordner)
    spur = _spur_aus_name(ordner.name)

    commit = ordner / "commit.txt"
    inhalt = commit.read_text(encoding="utf-8") if commit.is_file() else ""
    titel = ""
    schluessel = ""
    oos = ""
    for roh in inhalt.splitlines():
        zeile = roh.strip()
        if not zeile:
            continue
        if not titel:
            titel = zeile
        if zeile.startswith("Geaenderte Schluessel:"):
            schluessel = zeile.split(":", 1)[1].strip()
        elif zeile.startswith("OOS netto_gv_je_runde:"):
            oos = zeile

    if not spur:
        spur = titel or "?"

    zeilen = ["<b>Verbesserungsvorschlag %s</b>" % spur]
    if schluessel:
        zeilen.append("Geaenderte Schluessel: %s" % schluessel)
    if oos:
        zeilen.append(oos)
    zeilen.append("")
    zeilen.append("/ja wendet an und committet, /nein archiviert")
    return "\n".join(zeilen)
