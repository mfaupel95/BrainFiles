"""
Zentrales Tracking-Modul fuer Omnitrade.
Schreibt Events in tracking.db (SQLite). Fehlerschluckend — kein Tracking-Fehler
darf den Handelslauf stoppen.

Generiert aus .telemetry/tracking-plan.yaml (Version 1, 2026-10-06).
"""
import json
import os
import sqlite3
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Event-Konstanten — NIE als String-Literal in den Spuren verwenden
# ---------------------------------------------------------------------------
class Events:
    SYSTEM_GESTARTET     = "system.gestartet"
    SYSTEM_GESTOPPT      = "system.gestoppt"
    SIGNAL_AUSGEWAEHLT   = "signal.ausgewaehlt"
    FREIGABE_ENTSCHIEDEN = "freigabe.entschieden"
    POSITION_EROEFFNET   = "position.eroeffnet"
    ZYKLUS_ABGESCHLOSSEN = "zyklus.abgeschlossen"
    SPUR_KONFIGURIERT    = "spur.konfiguriert"
    # Ergaenzt 2026-10-21 (telemetrie.py, Haken in spur_buch.py)
    LAUF_FEHLGESCHLAGEN  = "lauf.fehlgeschlagen"
    STOERUNG_ERKANNT     = "stoerung.erkannt"
    POSITION_NACHGEZOGEN = "position.nachgezogen"


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
_DB_PFAD: Path | None = None
_EXPLIZIT = False     # True, sobald init_tracking() einen eigenen Pfad bekam
_LOG = logging.getLogger(__name__)


def _unter_test() -> bool:
    """Laeuft dieser Prozess als Test? (python -m unittest ... / python test_x.py)

    Grund (2026-10-21): die xperp- und Scanner-Tests riefen track_* ohne eigene
    Datenbank auf und schrieben in die echte tracking.db - dort stammen
    Hunderte Ereignisse von Testfixtures (z. B. XAU-USD_UM_XPERP-310620,
    W0-USDC), was die KB-Kennzahlen verfaelscht.
    """
    start = os.path.basename(sys.argv[0] or "").lower()
    return start.startswith("test_") or "unittest" in start or start == "__main__.py"


def init_tracking(db_pfad: Path | None = None) -> None:
    """DB initialisieren. Idempotent — mehrfache Aufrufe sind sicher."""
    global _DB_PFAD, _EXPLIZIT
    if db_pfad is None:
        db_pfad = Path(__file__).parent / "tracking.db"
    else:
        _EXPLIZIT = True
    _DB_PFAD = db_pfad
    try:
        with _verbinden() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts         TEXT    NOT NULL,
                    event      TEXT    NOT NULL,
                    properties TEXT    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_event ON events(event);
                CREATE INDEX IF NOT EXISTS idx_events_ts    ON events(ts);

                CREATE TABLE IF NOT EXISTS spur_tagesstand (
                    datum                   TEXT NOT NULL,
                    spur_name               TEXT NOT NULL,
                    zyklus_count_7d         INTEGER,
                    zyklus_count_30d        INTEGER,
                    win_rate_7d_pct         REAL,
                    win_rate_30d_pct        REAL,
                    avg_ergebnis_pct_30d    REAL,
                    offene_positionen_count INTEGER,
                    letzte_aktivitaet_at    TEXT,
                    PRIMARY KEY (datum, spur_name)
                );
            """)
    except Exception:
        _LOG.exception("tracking: DB-Initialisierung fehlgeschlagen")


def _verbinden() -> sqlite3.Connection:
    if _DB_PFAD is None:
        init_tracking()
    return sqlite3.connect(str(_DB_PFAD))


def track(event: str, properties: dict[str, Any]) -> None:
    """Beliebiges Event schreiben. Fehlerschluckend.

    Unter einem Testlauf wird nur geschrieben, wenn der Test eine eigene
    Datenbank angegeben hat (init_tracking(pfad)); die echte tracking.db bleibt
    sauber.
    """
    if _unter_test() and not _EXPLIZIT:
        return
    try:
        ts = datetime.now(timezone.utc).isoformat()
        with _verbinden() as con:
            con.execute(
                "INSERT INTO events (ts, event, properties) VALUES (?, ?, ?)",
                (ts, event, json.dumps(properties, ensure_ascii=False)),
            )
    except Exception:
        _LOG.exception("tracking: Schreibfehler (event=%s)", event)


# ---------------------------------------------------------------------------
# Typisierte Event-Funktionen — eine Funktion je Event
# ---------------------------------------------------------------------------

def track_system_gestartet(
    spur_name: str,
    modus: str,      # "paper" | "live"
    risikostufe: str = "basis",  # "basis" | "mittel" | "hoch"
) -> None:
    track(Events.SYSTEM_GESTARTET, {
        "spur_name": spur_name,
        "modus": modus,
        "risikostufe": risikostufe,
    })


def track_system_gestoppt(
    spur_name: str,
    laufzeit_minuten: int,
    grund: str,      # "normal" | "fehler" | "manuell" | "crash"
) -> None:
    track(Events.SYSTEM_GESTOPPT, {
        "spur_name": spur_name,
        "laufzeit_minuten": laufzeit_minuten,
        "grund": grund,
    })


def track_signal_ausgewaehlt(
    spur_name: str,
    instrument: str,
    richtung: str,           # "long" | "short"
    is_paper: bool,
    risikostufe: str = "basis",
    signal_score: float | None = None,
) -> None:
    props: dict[str, Any] = {
        "spur_name": spur_name,
        "instrument": instrument,
        "richtung": richtung,
        "is_paper": is_paper,
        "risikostufe": risikostufe,
    }
    if signal_score is not None:
        props["signal_score"] = signal_score
    track(Events.SIGNAL_AUSGEWAEHLT, props)


def track_freigabe_entschieden(
    spur_name: str,
    instrument: str,
    entscheidung: str,  # "freigegeben"|"abgelehnt"|"zeitlimit"|"abgebrochen"
    modus: str,         # "live" | "paper"
    ablehnungsgrund: str | None = None,
) -> None:
    props: dict[str, Any] = {
        "spur_name": spur_name,
        "instrument": instrument,
        "entscheidung": entscheidung,
        "modus": modus,
    }
    if ablehnungsgrund is not None:
        props["ablehnungsgrund"] = ablehnungsgrund
    track(Events.FREIGABE_ENTSCHIEDEN, props)


def track_position_eroeffnet(
    spur_name: str,
    instrument: str,
    richtung: str,       # "long" | "short"
    einstieg_kurs: float,
    stop_kurs: float,
    ziel_kurs: float,
    nominal_eur: float,
    is_paper: bool,
    risikostufe: str = "basis",
    hebel: float | None = None,
) -> None:
    props: dict[str, Any] = {
        "spur_name": spur_name,
        "instrument": instrument,
        "richtung": richtung,
        "einstieg_kurs": einstieg_kurs,
        "stop_kurs": stop_kurs,
        "ziel_kurs": ziel_kurs,
        "nominal_eur": nominal_eur,
        "is_paper": is_paper,
        "risikostufe": risikostufe,
    }
    if hebel is not None:
        props["hebel"] = hebel
    track(Events.POSITION_EROEFFNET, props)


def track_zyklus_abgeschlossen(
    spur_name: str,
    instrument: str,
    richtung: str,           # "long" | "short"
    einstieg_kurs: float,
    ausstieg_kurs: float,
    ergebnis_pct: float,
    ergebnis_eur: float,
    haltedauer_stunden: float,
    ausstiegsgrund: str,     # "ziel"|"stop"|"liquidation"|"manuell"|"zeitlimit"
    is_paper: bool,
    risikostufe: str = "basis",
    hebel: float | None = None,
    signal_score: float | None = None,
) -> None:
    props: dict[str, Any] = {
        "spur_name": spur_name,
        "instrument": instrument,
        "richtung": richtung,
        "einstieg_kurs": einstieg_kurs,
        "ausstieg_kurs": ausstieg_kurs,
        "ergebnis_pct": ergebnis_pct,
        "ergebnis_eur": ergebnis_eur,
        "haltedauer_stunden": haltedauer_stunden,
        "ausstiegsgrund": ausstiegsgrund,
        "is_paper": is_paper,
        "risikostufe": risikostufe,
    }
    if hebel is not None:
        props["hebel"] = hebel
    if signal_score is not None:
        props["signal_score"] = signal_score
    track(Events.ZYKLUS_ABGESCHLOSSEN, props)


def track_spur_konfiguriert(
    spur_name: str,
    geaendertes_feld: str,
    alter_wert: str | None = None,
    neuer_wert: str | None = None,
) -> None:
    props: dict[str, Any] = {
        "spur_name": spur_name,
        "geaendertes_feld": geaendertes_feld,
    }
    if alter_wert is not None:
        props["alter_wert"] = alter_wert
    if neuer_wert is not None:
        props["neuer_wert"] = neuer_wert
    track(Events.SPUR_KONFIGURIERT, props)


def track_lauf_fehlgeschlagen(
    spur_name: str,
    dauer_s: float,
    is_paper: bool,
    risikostufe: str = "basis",
) -> None:
    """Ein Zyklus einer Spur endete mit Fehler. Erfolgreiche Laeufe werden
    bewusst NICHT gemeldet (Minutentakt x 26 Spuren waeren ~37 000 Zeilen/Tag)."""
    track(Events.LAUF_FEHLGESCHLAGEN, {
        "spur_name": spur_name,
        "dauer_s": dauer_s,
        "is_paper": is_paper,
        "risikostufe": risikostufe,
    })


def track_position_nachgezogen(
    spur_name: str,
    instrument: str,
    stop_alt: float,
    stop_neu: float,
    is_paper: bool,
    quelle: str = "trailing",   # "trailing" | "ratsche"
    hoch_r: float | None = None,
    pos_id: str | None = None,
) -> None:
    """Der Stop einer offenen Position wurde an der Boerse nachgezogen."""
    props: dict[str, Any] = {
        "spur_name": spur_name,
        "instrument": instrument,
        "stop_alt": stop_alt,
        "stop_neu": stop_neu,
        "quelle": quelle,
        "is_paper": is_paper,
    }
    if hoch_r is not None:
        props["hoch_r"] = hoch_r
    if pos_id:
        props["pos_id"] = pos_id
    track(Events.POSITION_NACHGEZOGEN, props)


def track_stoerung_erkannt(
    spur_name: str,
    art: str,               # "herzschlag_alt"|"abruf_fehler"|"api_fehler"|"journal_luecke"
    dauer_s: float | None = None,
    flachgestellt: bool = False,
) -> None:
    props: dict[str, Any] = {
        "spur_name": spur_name,
        "art": art,
        "flachgestellt": flachgestellt,
    }
    if dauer_s is not None:
        props["dauer_s"] = dauer_s
    track(Events.STOERUNG_ERKANNT, props)


# ---------------------------------------------------------------------------
# KB-Metriken-Export (nach snapshot_sync aufrufen)
# ---------------------------------------------------------------------------

def kb_snapshot_json(ziel_pfad: Path | None = None) -> None:
    """
    Liest spur_tagesstand + Events und schreibt MaxHirn/Wissen/KB/data/spur-metriken.json.
    Enthaelt alle Metriken, die der Cloud-Agent fuer die KB-Note braucht.
    Fehlerschluckend.
    """
    if ziel_pfad is None:
        ziel_pfad = Path(__file__).parent.parent.parent / "MaxHirn" / "Wissen" / "KB" / "data" / "spur-metriken.json"
    try:
        with _verbinden() as con:
            spuren = [r[0] for r in con.execute(
                "SELECT DISTINCT spur_name FROM spur_tagesstand ORDER BY spur_name"
            ).fetchall()]

            def _profit_faktor(spur: str, tage: int) -> float | None:
                rows = con.execute("""
                    SELECT json_extract(properties,'$.ergebnis_eur') FROM events
                    WHERE event = ? AND json_extract(properties,'$.spur_name') = ?
                      AND ts >= datetime('now',?)
                """, (Events.ZYKLUS_ABGESCHLOSSEN, spur, f"-{tage} days")).fetchall()
                werte = [r[0] for r in rows if r[0] is not None]
                gewinne = sum(v for v in werte if v > 0)
                verluste = abs(sum(v for v in werte if v < 0))
                if verluste == 0:
                    return None
                return round(gewinne / verluste, 2)

            def _max_drawdown(spur: str, tage: int) -> float | None:
                # Equity-Kurve in Prozent des Nominals (Start 100), nie ueber 100 %.
                rows = con.execute("""
                    SELECT json_extract(properties,'$.ergebnis_pct') FROM events
                    WHERE event = ? AND json_extract(properties,'$.spur_name') = ?
                      AND ts >= datetime('now',?) ORDER BY ts
                """, (Events.ZYKLUS_ABGESCHLOSSEN, spur, f"-{tage} days")).fetchall()
                werte = [r[0] for r in rows if r[0] is not None]
                if not werte:
                    return None
                equity = peak = 100.0
                max_dd = 0.0
                for v in werte:
                    equity *= max(0.0, 1 + v / 100)
                    peak = max(peak, equity)
                    max_dd = max(max_dd, (peak - equity) / peak * 100)
                return round(max_dd, 1)

            def _stop_quote(spur: str, tage: int) -> float | None:
                rows = con.execute("""
                    SELECT json_extract(properties,'$.ausstiegsgrund') FROM events
                    WHERE event = ? AND json_extract(properties,'$.spur_name') = ?
                      AND ts >= datetime('now',?)
                """, (Events.ZYKLUS_ABGESCHLOSSEN, spur, f"-{tage} days")).fetchall()
                gesamt = len(rows)
                if gesamt == 0:
                    return None
                verluste_mit_stop = sum(
                    1 for r in rows
                    if r[0] == "stop"
                )
                verluste_gesamt_rows = con.execute("""
                    SELECT COUNT(*) FROM events
                    WHERE event = ? AND json_extract(properties,'$.spur_name') = ?
                      AND json_extract(properties,'$.ergebnis_pct') < 0
                      AND ts >= datetime('now',?)
                """, (Events.ZYKLUS_ABGESCHLOSSEN, spur, f"-{tage} days")).fetchone()
                verluste_gesamt = verluste_gesamt_rows[0] if verluste_gesamt_rows else 0
                if verluste_gesamt == 0:
                    return None
                return round(verluste_mit_stop / verluste_gesamt * 100, 1)

            export: dict = {
                "generiert_at": datetime.now(timezone.utc).isoformat(),
                "spuren": {},
            }
            for spur in spuren:
                row = con.execute(
                    "SELECT * FROM spur_tagesstand WHERE spur_name = ? ORDER BY datum DESC LIMIT 1",
                    (spur,)
                ).fetchone()
                if not row:
                    continue
                cols = [d[0] for d in con.execute("PRAGMA table_info(spur_tagesstand)").fetchall()]
                basis = dict(zip(cols, row))
                export["spuren"][spur] = {
                    **basis,
                    "profit_faktor_30d": _profit_faktor(spur, 30),
                    "max_drawdown_30d_pct": _max_drawdown(spur, 30),
                    "stop_ausloesung_rate_30d_pct": _stop_quote(spur, 30),
                }

        ziel_pfad.parent.mkdir(parents=True, exist_ok=True)
        import json as _json
        ziel_pfad.write_text(_json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        _LOG.exception("tracking: kb_snapshot_json fehlgeschlagen")


# ---------------------------------------------------------------------------
# Snapshot-Sync (taeglich aufrufen, z. B. aus wochenbericht.py)
# ---------------------------------------------------------------------------

def snapshot_sync(spur_name: str, offene_positionen_count: int = 0) -> None:
    """
    Berechnet Tagesstand fuer eine Spur aus den Events und schreibt ihn in
    spur_tagesstand. Aufruf taeglich je Spur, z. B. nach Dauerlauf-Ende.
    """
    heute = datetime.now(timezone.utc).date().isoformat()
    try:
        with _verbinden() as con:
            def _zyklus_count(tage: int) -> int:
                row = con.execute("""
                    SELECT COUNT(*) FROM events
                    WHERE event = ? AND json_extract(properties,'$.spur_name') = ?
                      AND ts >= datetime('now',?)
                """, (Events.ZYKLUS_ABGESCHLOSSEN, spur_name, f"-{tage} days")).fetchone()
                return row[0] if row else 0

            def _win_rate(tage: int) -> float | None:
                rows = con.execute("""
                    SELECT json_extract(properties,'$.ergebnis_pct') FROM events
                    WHERE event = ? AND json_extract(properties,'$.spur_name') = ?
                      AND ts >= datetime('now',?)
                """, (Events.ZYKLUS_ABGESCHLOSSEN, spur_name, f"-{tage} days")).fetchall()
                if not rows:
                    return None
                gewinner = sum(1 for r in rows if r[0] is not None and r[0] > 0)
                return round(gewinner / len(rows) * 100, 1)

            def _avg_ergebnis(tage: int) -> float | None:
                row = con.execute("""
                    SELECT AVG(json_extract(properties,'$.ergebnis_pct')) FROM events
                    WHERE event = ? AND json_extract(properties,'$.spur_name') = ?
                      AND ts >= datetime('now',?)
                """, (Events.ZYKLUS_ABGESCHLOSSEN, spur_name, f"-{tage} days")).fetchone()
                return round(row[0], 2) if row and row[0] is not None else None

            def _letzte_aktivitaet() -> str | None:
                row = con.execute("""
                    SELECT MAX(ts) FROM events
                    WHERE json_extract(properties,'$.spur_name') = ?
                """, (spur_name,)).fetchone()
                return row[0] if row else None

            con.execute("""
                INSERT OR REPLACE INTO spur_tagesstand
                (datum, spur_name, zyklus_count_7d, zyklus_count_30d,
                 win_rate_7d_pct, win_rate_30d_pct, avg_ergebnis_pct_30d,
                 offene_positionen_count, letzte_aktivitaet_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                heute, spur_name,
                _zyklus_count(7), _zyklus_count(30),
                _win_rate(7), _win_rate(30),
                _avg_ergebnis(30),
                offene_positionen_count,
                _letzte_aktivitaet(),
            ))
    except Exception:
        _LOG.exception("tracking: snapshot_sync fehlgeschlagen (spur=%s)", spur_name)
