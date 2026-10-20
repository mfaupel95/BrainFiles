"""Runde aus dem Block-Event-Log des jev-trader-Bots rekonstruieren.

Der jev-trader (TypeScript/bun auf der Monad-Blockchain, Kuru-Orderbuch) hat
seinen Lauf als JSONL geschrieben: JEDE Zeile ist ein Block-Event mit einem
`position`-Feld (side/size/entryPrice) und einem `totals`-Feld (kumulative
Zaeler incl. realizedUsd). Einzelne Fills stehen NICHT im Log - sie sind nur
in den totals enthalten (Gemessen: 546 Fills, aber kein fill-Objekt je Zeile).

Der Kern-Trick: Der Bot skaliert stetig nach (same side, size aendert sich) -
da ist kein Roundtrip fertig. Ein ROUNDTRIP SCHLIESST erst, wenn die Seite
wechselt: side wird flat ODER dreht von long nach short bzw. short nach long.
Dann ist eine Position realisiert (eine "Bein"/geschlossene Runde).

Der G/V des geschlossenen Beins ist die AENDERUNG von totals.realizedUsd
zwischen dem Oeffnen dieses Beins und seinem Schliessen. Beim Skalieren
innerhalb EINES Beins aendert sich realizedUsd nicht (kein realisierter
Schritt, nur eine Veraenderung der offenen Groesse) - der Betrag springt
genau an den Bein-Grenzen. Darum stimmt die Summe aller Bein-G/V exakt mit
der letzten totals.realizedUsd ueberein (verifiziert: -0.2822 auf dem echten
Log, 50 Beine).

Ausstiegsgrund: aus der Kursbewegung gegen den Einstieg abgeleitet
(ziel/stop); ohne vorliegenden Kurs oder ohne Bewegung gilt zwangsschluss.

Einheiten: ts ist epoch_ms; preise in MON (die Handelswaehrung des Bots).
gv_usd steht fertig in realisiert (USD) - es ist schon das Ergebnis je
Einheit, in USD. Es gibt KEINEN Einsatz pro Runde im Log: das Buch fuehrt
Punkte/Ergebnis, keinen Kapitalbetrag (wie orb/orbk).
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def parse_event(zeile):
    """Eine JSONL-Zeile in ein Event-Dict. Kaputte Zeilen -> None (ueberspringen).

    Das Log darf nicht an einer kaputten Zeile zerbrechen: ein eingeknickter
    Datensatz soll die restlichen 63k Zeilen nicht verwerfen.
    """
    zeile = zeile.strip()
    if not zeile:
        return None
    try:
        e = json.loads(zeile)
    except ValueError:
        return None
    if not isinstance(e, dict):
        return None
    return e


def _f(event, key):
    """Nur Dict-Felder auslesen - ein Event ohne das Feld ist kein Bein-Anfang."""
    v = event.get(key)
    return v if isinstance(v, dict) else None


def rekonstruiere_runden(events):
    """Alle geschlossenen Roundtrips aus der Event-Folge.

    events: iterierbar, jedes ein dict aus parse_event() (None wird
    uebersprungen). Rueckgabe: Liste von dicts, ein Eintrag je
    GESCHLOSSENEM Bein:
      side, open_ts, close_ts, einstieg (entryPrice beim Oeffnen),
      ausstieg (mid beim Schliessen), gv_usd (realized-Delta des Beins),
      ausgang (ziel/stop/zwangsschluss), haltetage
    """
    runden = []
    offen = None          # dict mit den Bein-Daten, oder None wenn flat
    vor_seite = "flat"    # Seite des VORIGEN Events (Vergleichsanker)
    vor_real = 0.0
    vor_ts = None

    for e in events:
        if e is None:
            continue
        pos = _f(e, "position")
        if pos is None:
            continue
        seite = pos.get("side") or "flat"
        totals = _f(e, "totals") or {}
        real = totals.get("realizedUsd")
        real = float(real) if real is not None else vor_real
        ts = e.get("ts") or vor_ts
        mid = e.get("mid")

        if seite == vor_seite and seite != "flat":
            # Skalieren innerhalb eines Beins: active Bein weiter, keine Grenze.
            vor_ts = ts
            continue

        # Seite hat sich geaendert -> moegliche Schliessung.
        if offen is not None:
            # Das bisherige Bein wird hier geschlossen (flat ODER Dreh).
            ausgang = _ausgang(offen["einstieg"], mid, offen["side"])
            runden.append({
                "side": offen["side"],
                "open_ts": offen["open_ts"],
                "close_ts": ts,
                "einstieg": offen["einstieg"],
                "ausstieg": mid,
                "gv_usd": round(real - offen["open_real"], 6),
                "ausgang": ausgang,
                "haltetage": (ts - offen["open_ts"]) / 86400.0,
            })
            offen = None

        if seite != "flat":
            # Neues Bein oeffnen (vom flat ODER als Dreh).
            offen = {
                "side": seite,
                "open_ts": ts,
                "open_real": real,
                "einstieg": pos.get("entryPrice") or mid,
            }
        vor_seite = seite
        vor_real = real
        vor_ts = ts

    return runden


def _ausgang(einstieg, ausstieg, side):
    """Ausstiegsgrund aus der Kursbewegung gegen den Einstieg ableiten.

    ziel: Kurs lief fuer den Einstieg richtig. stop: gegen den Einstieg.
    Ohne vorliegenden Kurs oder ohne Bewegung (Einstieg == Ausstieg) gibt es
    keine Richtung - dann zwangsschluss.
    """
    if einstieg is None or ausstieg is None:
        return "zwangsschluss"
    if ausstieg == einstieg:
        return "zwangsschluss"
    if side == "long":
        return "ziel" if ausstieg > einstieg else "stop"
    return "ziel" if ausstieg < einstieg else "stop"


def _iso(ms):
    """epoch_ms -> ISO-String (UTC). None bleibt None."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000.0, timezone.utc).isoformat()


def zeilen_eines_events(zeilen):
    """Direkt aus vorgelegten JSONL-Zeilenlesung die Runden bauen (Test-Seam)."""
    return rekonstruiere_runden(parse_event(z) for z in zeilen)


def lese_events(pfad):
    """Iterator ueber alle Events einer JSONL-Datei (Pfad oder Dateiobjekt)."""
    if isinstance(pfad, (str, Path)):
        with open(pfad, encoding="utf-8", newline="") as f:
            for zeile in f:
                e = parse_event(zeile)
                if e is not None:
                    yield e
    else:
        for zeile in pfad:
            e = parse_event(zeile)
            if e is not None:
                yield e


def journal_zeile(r):
    """Eine geschlossene Runde als CSV-Zeile im Hausformat (orb-Schema).

    Spalten: zeit,inst,richtung,einstieg,stop,ziel,ausgang,ausstieg,
             gv_punkte,gv_usd,mfe_pct,mae_pct,haltetage
    stop/ziel und mfe/mae sind hier nicht massagebend (kein Stopp im Log) -
    Stopfeld leer, Ergebnis steckt in gv_usd.
    """
    richtung = "long" if r["side"] == "long" else "short"
    return [
        _iso(r["close_ts"]),
        "JEV_TRADER",                      # ein Instrument: der Bot handelt JEV/
        richtung,
        "%.6f" % r["einstieg"] if r["einstieg"] is not None else "",
        "",                                # kein bekannte Stop-Marke
        "",                                # kein bekanntes Ziel-Marke
        r["ausgang"],
        "%.6f" % r["ausstieg"] if r["ausstieg"] is not None else "",
        "",                                # Punkte (nicht gefuehrt)
        "%.6f" % r["gv_usd"],
        "",                                # mfe
        "",                                # mae
        "%.4f" % r["haltetage"],
    ]
