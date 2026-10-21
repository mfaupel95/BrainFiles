"""Journal-Abgleich: fehlende Abschluesse aus den Handelsjournalen in tracking.db nachtragen.

Die Haken in spur_buch.py/xperp melden Abschluesse in Echtzeit. Spuren mit
eigenem Schliesscode (omniquant, swap, kill_gemeinsam, ...) und Zwangsschluesse
tun das nicht. Dieses Modul liest die Journale unter Agenten/Handel/<spur>/ und
schreibt jeden Abschluss, der in tracking.db fehlt, als zyklus.abgeschlossen mit
dem Zeitstempel der Journalzeile und quelle="journal_abgleich".

Regeln:
  * Ein Abschluss gilt als vorhanden, wenn es in tracking.db dasselbe Spur+Instrument
    innerhalb von +-180 s gibt (wie die Bereinigung). Ein zweiter Lauf ergaenzt nichts.
  * Einstieg, Nominal und Richtung kommen aus der passenden Eroeffnungszeile
    (pos_id, sonst die juengste offene Zeile desselben Instruments). Ohne Eroeffnung
    wird nichts geschrieben, sondern als "ohne_einstieg" gezaehlt.
  * G/V = Nominal * Preisaenderung (ohne Gebuehren/Funding), ergebnis_pct auf das Nominal.
  * Schreibt nie in die Handelsdateien. Wirft nicht nach aussen, wenn aufgerufen als Routine.

    python journal_abgleich.py                 # Trockenlauf
    python journal_abgleich.py --apply         # nachtragen (Sicherung beim ersten Mal)
"""

import argparse
import bisect
import collections
import csv
import glob
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
FENSTER_S = 180
TAGE = 35
OEFFNEN = ("kauf", "eroeffnen", "einstieg")
SCHLIESSEN = ("verkauf", "schliessen", "ausstieg")
NOMINAL = ("nominal_usd", "einsatz_usd", "usd")


def _zeit(text):
    try:
        t = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.timestamp()


def _zahl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _grund(text):
    return (text or "").strip().split(" ")[0].lower() or "unbekannt"


def abschluesse(spur_ordner, seit=0.0):
    """Abschluesse einer Spur aus ihren Journalen. -> (liste, ohne_einstieg)"""
    spur = os.path.basename(os.path.normpath(spur_ordner))
    zeilen = []
    for f in sorted(glob.glob(os.path.join(spur_ordner, "handelsjournal*.csv"))):
        if "verworfen" in f:
            continue
        with open(f, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                t = _zeit(r.get("zeit"))
                if t is not None and r.get("inst") and r.get("modus") in ("papier", "live"):
                    zeilen.append((t, r))
    zeilen.sort(key=lambda x: x[0])
    offen = collections.defaultdict(list)      # inst -> [(t, zeile)]
    liste, ohne = [], 0
    for t, r in zeilen:
        a = (r.get("aktion") or "").lower()
        inst = r["inst"]
        if a in OEFFNEN:
            offen[inst].append((t, r))
            continue
        if a not in SCHLIESSEN:
            continue
        kand = offen.get(inst, [])
        pid = r.get("pos_id")
        wahl = None
        if pid:
            wahl = next((i for i in range(len(kand) - 1, -1, -1)
                         if kand[i][1].get("pos_id") == pid), None)
        if wahl is None and kand:
            wahl = len(kand) - 1
        if wahl is None:
            if t >= seit:
                ohne += 1
            continue
        t0, o = kand.pop(wahl)
        if t < seit:
            continue
        einstieg, ausstieg = _zahl(o.get("preis")), _zahl(r.get("preis"))
        if not einstieg or ausstieg is None:
            ohne += 1
            continue
        richtung = (o.get("seite") or "long").lower()
        pct = (ausstieg / einstieg - 1) * 100 * (-1 if richtung == "short" else 1)
        nominal = next((_zahl(o.get(k)) for k in NOMINAL if _zahl(o.get(k))), None)
        liste.append({
            "t": t, "spur": spur, "inst": inst, "richtung": richtung,
            "einstieg": einstieg, "ausstieg": ausstieg,
            "pct": round(pct, 4),
            "eur": round(nominal * pct / 100, 4) if nominal else None,
            "stunden": round((t - t0) / 3600, 4),
            "grund": _grund(r.get("grund")), "paper": r.get("modus") != "live",
        })
    return liste, ohne


def _vorhanden(con, spur):
    d = collections.defaultdict(list)
    for (pr, ts) in con.execute(
            "SELECT properties, ts FROM events WHERE event='zyklus.abgeschlossen'"):
        p = json.loads(pr)
        if p.get("spur_name") == spur and p.get("instrument"):
            t = _zeit(ts)
            if t is not None:
                d[p["instrument"]].append(t)
    for k in d:
        d[k].sort()
    return d


def _nah(liste, t):
    i = bisect.bisect_left(liste, t)
    return any(0 <= j < len(liste) and abs(liste[j] - t) <= FENSTER_S for j in (i - 1, i))


def _sicherung(db_pfad):
    ziel = db_pfad + ".vor-abgleich"
    if os.path.exists(ziel):
        return None
    src = sqlite3.connect(db_pfad)
    dst = sqlite3.connect(ziel)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return ziel


def abgleich(db_pfad, handel_dir=HIER, tage=TAGE, schreiben=False, spur=None):
    """Gleicht Journale gegen tracking.db ab. -> {spur: {"fehlt": n, "ohne_einstieg": n, "geschrieben": n}}"""
    seit = (datetime.now(timezone.utc) - timedelta(days=tage)).timestamp()
    con = sqlite3.connect(db_pfad)
    bericht = {}
    try:
        ordner = [d for d in sorted(glob.glob(os.path.join(handel_dir, "*")))
                  if os.path.isdir(d) and glob.glob(os.path.join(d, "handelsjournal*.csv"))
                  and os.path.basename(d) not in ("tests", "telemetrie")]
        gesichert = False
        for o in ordner:
            name = os.path.basename(o)
            if spur and name != spur:
                continue
            liste, ohne = abschluesse(o, seit)
            vorh = _vorhanden(con, name)
            fehlt = [a for a in liste if not _nah(vorh.get(a["inst"], []), a["t"])]
            geschr = 0
            if schreiben and fehlt:
                if not gesichert:
                    _sicherung(db_pfad)
                    gesichert = True
                with con:
                    for a in fehlt:
                        con.execute(
                            "INSERT INTO events (ts, event, properties) VALUES (?, ?, ?)",
                            (datetime.fromtimestamp(a["t"], timezone.utc).isoformat(),
                             "zyklus.abgeschlossen", json.dumps({
                                 "spur_name": a["spur"], "instrument": a["inst"],
                                 "richtung": a["richtung"], "einstieg_kurs": a["einstieg"],
                                 "ausstieg_kurs": a["ausstieg"], "ergebnis_pct": a["pct"],
                                 "ergebnis_eur": a["eur"], "haltedauer_stunden": a["stunden"],
                                 "ausstiegsgrund": a["grund"], "is_paper": a["paper"],
                                 "risikostufe": "basis", "quelle": "journal_abgleich"},
                                 ensure_ascii=False)))
                        geschr += 1
            if liste or ohne:
                bericht[name] = {"fehlt": len(fehlt), "ohne_einstieg": ohne, "geschrieben": geschr}
    finally:
        con.close()
    return bericht


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="fehlende Abschluesse schreiben")
    ap.add_argument("--db", default=os.path.join(HIER, "tracking.db"))
    ap.add_argument("--handel", default=HIER, help="Ordner mit den Spuren")
    ap.add_argument("--tage", type=int, default=TAGE)
    ap.add_argument("--spur")
    a = ap.parse_args(argv)
    b = abgleich(a.db, a.handel, a.tage, a.apply, a.spur)
    for s, z in sorted(b.items()):
        print("%-24s fehlt %4d | ohne Einstieg %3d | geschrieben %4d" %
              (s, z["fehlt"], z["ohne_einstieg"], z["geschrieben"]))
    print("%s: %d fehlende Abschluesse, %d geschrieben" % (
        "Nachtrag" if a.apply else "Trockenlauf",
        sum(z["fehlt"] for z in b.values()), sum(z["geschrieben"] for z in b.values())))


if __name__ == "__main__":
    sys.exit(main())
