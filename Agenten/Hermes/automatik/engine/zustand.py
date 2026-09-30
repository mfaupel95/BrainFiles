"""Zustand der Engine: Laufhistorie, Rate-Limits, Marken, Sperren.

SQLite, weil die Engine als mehrere kurze Prozesse laeuft (Cron ruft sie auf,
nicht ein Dauerdienst). Jeder Lauf muss den Stand des vorigen kennen:

laeufe          je Lauf eine Zeile (fuer Rate-Limit, Fehlerstreak, Verkettung)
marken          "wo war ich" je Trigger-Quelle (letzte Event-ID, mtime, Cron-Minute)
sperren         Regel dauerhaft gesperrt (bei_fehlerstreak) mit Grund
belegung        laufende Regeln (max_gleichzeitig, nicht_wenn_regel_laeuft)
bestaetigungen  offene Rueckfragen (modus=bestaetigung)

WAL ist eingeschaltet: dieser Rechner geht schlagartig aus (Kernel-Power 41),
und ein halb geschriebener Zustand waere schlimmer als ein fehlender.
"""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from . import pfade

SCHEMA = """
CREATE TABLE IF NOT EXISTS laeufe (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    regel_id      TEXT NOT NULL,
    zeit_unix     INTEGER NOT NULL,
    ergebnis      TEXT NOT NULL,
    exit_code     INTEGER,
    dauer_ms      INTEGER,
    trigger_typ   TEXT,
    ausgeloest_durch TEXT,
    abbruchgrund  TEXT
);
CREATE INDEX IF NOT EXISTS ix_laeufe_regel ON laeufe(regel_id, zeit_unix);

CREATE TABLE IF NOT EXISTS marken (
    schluessel TEXT PRIMARY KEY,
    wert       TEXT NOT NULL,
    zeit_unix  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sperren (
    regel_id  TEXT PRIMARY KEY,
    grund     TEXT NOT NULL,
    zeit_unix INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS belegung (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    regel_id  TEXT NOT NULL,
    pid       INTEGER NOT NULL,
    seit_unix INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bestaetigungen (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    regel_id   TEXT NOT NULL,
    frage      TEXT NOT NULL,
    kanal      TEXT,
    verfall_unix INTEGER NOT NULL,
    antwort    TEXT,
    zeit_unix  INTEGER NOT NULL
);
"""


def verbinden(datei: Path | None = None) -> sqlite3.Connection:
    ziel = Path(datei) if datei else pfade.zustand_datei()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(ziel), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(SCHEMA)
    return con


@contextmanager
def offen(datei: Path | None = None):
    con = verbinden(datei)
    try:
        yield con
        con.commit()
    finally:
        con.close()


# --- Laeufe ---------------------------------------------------------------

def lauf_merken(con, regel_id, ergebnis, exit_code=None, dauer_ms=0,
                trigger_typ="", ausgeloest_durch="", abbruchgrund=None,
                zeit_unix=None) -> int:
    cur = con.execute(
        "INSERT INTO laeufe (regel_id, zeit_unix, ergebnis, exit_code, dauer_ms,"
        " trigger_typ, ausgeloest_durch, abbruchgrund)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (regel_id, int(zeit_unix or time.time()), ergebnis, exit_code, int(dauer_ms),
         trigger_typ, ausgeloest_durch, abbruchgrund),
    )
    con.commit()
    return int(cur.lastrowid)


def laeufe_im_fenster(con, regel_id, fenster_s, nur_gestartet=True) -> int:
    """Zaehlt Laeufe der Regel im Zeitfenster.

    nur_gestartet: uebersprungene Laeufe (Rate-Limit, Abbruch) zaehlen NICHT
    gegen das Limit - sonst sperrt sich eine Regel durch ihre eigenen
    Ablehnungen selbst aus.
    """
    ab = int(time.time()) - int(fenster_s)
    if nur_gestartet:
        return int(con.execute(
            "SELECT COUNT(*) FROM laeufe WHERE regel_id=? AND zeit_unix>=?"
            " AND ergebnis IN ('erfolg','fehler','timeout','dry_run')",
            (regel_id, ab)).fetchone()[0])
    return int(con.execute(
        "SELECT COUNT(*) FROM laeufe WHERE regel_id=? AND zeit_unix>=?",
        (regel_id, ab)).fetchone()[0])


def letzter_lauf(con, regel_id, nur_gestartet=True):
    if nur_gestartet:
        return con.execute(
            "SELECT * FROM laeufe WHERE regel_id=? AND ergebnis IN"
            " ('erfolg','fehler','timeout','dry_run')"
            " ORDER BY zeit_unix DESC, id DESC LIMIT 1", (regel_id,)).fetchone()
    return con.execute(
        "SELECT * FROM laeufe WHERE regel_id=? ORDER BY zeit_unix DESC, id DESC"
        " LIMIT 1", (regel_id,)).fetchone()


def fehlerstreak(con, regel_id) -> int:
    """Wie viele Fehlerlaeufe in Folge (jung nach alt, bis zum ersten Erfolg)."""
    n = 0
    for z in con.execute(
        "SELECT ergebnis FROM laeufe WHERE regel_id=? AND ergebnis IN"
        " ('erfolg','fehler','timeout') ORDER BY zeit_unix DESC, id DESC LIMIT 50",
            (regel_id,)):
        if z["ergebnis"] in ("fehler", "timeout"):
            n += 1
        else:
            break
    return n


# --- Marken ---------------------------------------------------------------

def marke_lesen(con, schluessel, standard=None):
    z = con.execute("SELECT wert FROM marken WHERE schluessel=?", (schluessel,)).fetchone()
    return z["wert"] if z else standard


def marke_setzen(con, schluessel, wert):
    con.execute(
        "INSERT INTO marken (schluessel, wert, zeit_unix) VALUES (?,?,?)"
        " ON CONFLICT(schluessel) DO UPDATE SET wert=excluded.wert,"
        " zeit_unix=excluded.zeit_unix",
        (schluessel, str(wert), int(time.time())),
    )
    con.commit()


# --- Sperren -------------------------------------------------------------

def sperren(con, regel_id, grund):
    con.execute(
        "INSERT INTO sperren (regel_id, grund, zeit_unix) VALUES (?,?,?)"
        " ON CONFLICT(regel_id) DO UPDATE SET grund=excluded.grund,"
        " zeit_unix=excluded.zeit_unix",
        (regel_id, grund, int(time.time())),
    )
    con.commit()


def ist_gesperrt(con, regel_id):
    z = con.execute("SELECT grund FROM sperren WHERE regel_id=?", (regel_id,)).fetchone()
    return z["grund"] if z else None


def entsperren(con, regel_id):
    con.execute("DELETE FROM sperren WHERE regel_id=?", (regel_id,))
    con.commit()


# --- Belegung (gleichzeitige Laeufe) -------------------------------------

def belegen(con, regel_id, pid) -> int:
    cur = con.execute(
        "INSERT INTO belegung (regel_id, pid, seit_unix) VALUES (?,?,?)",
        (regel_id, int(pid), int(time.time())))
    con.commit()
    return int(cur.lastrowid)


def freigeben(con, belegung_id):
    con.execute("DELETE FROM belegung WHERE id=?", (int(belegung_id),))
    con.commit()


def belegt_zahl(con, regel_id) -> int:
    return int(con.execute(
        "SELECT COUNT(*) FROM belegung WHERE regel_id=?", (regel_id,)).fetchone()[0])


def laufende_regeln(con) -> set[str]:
    return {z["regel_id"] for z in con.execute("SELECT DISTINCT regel_id FROM belegung")}


def belegung_aufraeumen(con, max_alter_s=7200) -> int:
    """Verwaiste Belegungen entfernen (Prozess weg, Rechner abgestuerzt)."""
    grenze = int(time.time()) - int(max_alter_s)
    n = con.execute("DELETE FROM belegung WHERE seit_unix < ?", (grenze,)).rowcount
    con.commit()
    return int(n or 0)


# --- Bestaetigungen ------------------------------------------------------

def bestaetigung_anlegen(con, regel_id, frage, kanal, verfall_s) -> int:
    cur = con.execute(
        "INSERT INTO bestaetigungen (regel_id, frage, kanal, verfall_unix, zeit_unix)"
        " VALUES (?,?,?,?,?)",
        (regel_id, frage, kanal, int(time.time()) + int(verfall_s), int(time.time())))
    con.commit()
    return int(cur.lastrowid)


def bestaetigung_antwort(con, regel_id):
    """Offene, nicht verfallene Zustimmung? Rueckgabe 'ja'|'nein'|None.

    In einer Sitzung ohne anwesenden Nutzer gilt keine Antwort als Nein (S8) -
    das entscheidet der Aufrufer, hier wird nur der Stand geliefert.
    """
    z = con.execute(
        "SELECT antwort, verfall_unix FROM bestaetigungen WHERE regel_id=?"
        " ORDER BY id DESC LIMIT 1", (regel_id,)).fetchone()
    if not z:
        return None
    if z["antwort"] in ("ja", "nein"):
        return z["antwort"]
    if int(z["verfall_unix"]) < int(time.time()):
        return "nein"  # verfallen = Nein
    return None
