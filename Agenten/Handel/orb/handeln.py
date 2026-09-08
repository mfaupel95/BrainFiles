"""Vierte Spur: ORB Index-CFD ueber OANDA, gerichtet (long/short), gehebelt
(Hebel faellt aus der Positionsrechnung), in EUR.

Aufruf (aus diesem Ordner):
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --vorschau
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --papier
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --live
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --wachen

Neun Sperren muessen ALLE offen sein, sonst laeuft trotz --live nur Papier
(Liste in live_sperren, Task 11). Ausstiege laufen NIE durch das
Freigabefenster - ein Stop muss auch greifen, wenn niemand davorsitzt.

Dieser Stand deckt nur die Ausstiegshaelfte des Zyklus: Zustand, Journal,
pruefe_ausstiege, flach_stellen (Notausstieg), --wachen. Der Einstieg
(pruefe_einstiege, Freigabefenster, live_sperren, --vorschau) kommt in
Task 10/11 und ersetzt dort den Platzhalter in lauf().
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

import oanda
import session as sess
import wachen_orb as wp

HIER = Path(__file__).resolve().parent
WACHEN = HIER / "wachen.json"
ZUSTAND = HIER / "zustand.json"
JOURNAL = HIER / "handelsjournal.csv"
FREIGABE_ZEITLIMIT_S = 120


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _wachen():
    return json.loads(WACHEN.read_text("utf-8"))


def lade_zustand():
    if ZUSTAND.exists():
        return json.loads(ZUSTAND.read_text("utf-8"))
    return {"positionen": [], "letzte_stops": {}, "letzter_lauf": None, "modus": None}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    ZUSTAND.write_text(json.dumps(z, ensure_ascii=False, indent=2), "utf-8")


def journal(*felder):
    neu = not JOURNAL.exists()
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        if neu:
            s.writerow(["zeit", "modus", "aktion", "inst", "richtung", "preis",
                        "eur", "units", "stop", "ziel", "grund"])
        s.writerow(felder)


def _inst_konf(w):
    return w["instrumente"][w["instrument_aktiv"]]


def _punkt_wert(w):
    return _inst_konf(w)["punkt_wert_eur"]


def _halber_spread_eur(w, units):
    return 0.5 * _inst_konf(w)["spread_punkte"] * _punkt_wert(w) * units


def _wert_eur(p, kurs, w):
    """Realisierter Wert der Position bei kurs, in EUR, VOR Spread."""
    diff = (kurs - p["einstieg"]) if p["richtung"] == "long" else (p["einstieg"] - kurs)
    return diff * _punkt_wert(w) * p["units"]


def _erloes_eur(p, kurs, w):
    """Realisierter G/V der Position bei kurs, in EUR, NACH Abzug des halben
    Spreads auf der Ausstiegsseite. Einzige Quelle fuer die Ausstiegsrechnung -
    _schliesse ruft nur hier."""
    return _wert_eur(p, kurs, w) - _halber_spread_eur(w, p["units"])


def _signierte_units(p):
    return p["units"] if p["richtung"] == "long" else -p["units"]


def _schliesse(p, kurs, w, live, grund, z):
    """Eine Position schliessen. Gibt True zurueck, wenn sie weg ist."""
    if live:
        try:
            oanda.markt_order(_inst_konf(w)["oanda"],
                              -_signierte_units(p), echt=True, live=True)
        except Exception as e:  # noqa: BLE001
            print("  Ausstieg %s fehlgeschlagen: %s" % (p["inst"], e), file=sys.stderr)
            return False
    gv = _erloes_eur(p, kurs, w)
    print("  ZU  %-10s %s @ %-10.5g (%s)  G/V %+.2f EUR"
          % (p["inst"], p["richtung"], kurs, grund, gv))
    journal(_jetzt(), "live" if live else "papier", "ausstieg", p["inst"],
            p["richtung"], "%.5f" % kurs, "%.2f" % (p["risiko_eur"] + gv),
            "%.4f" % p["units"], "", "", grund)
    if grund == "stop":
        z["letzte_stops"][p["inst"]] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return True


def pruefe_ausstiege(z, w, live):
    """Je offene Position: Stop / Ziel / Zwangsschluss. Ausstiege laufen nie
    durch das Freigabefenster. Zwangsschluss haengt an DER Position: sie schliesst
    spaetestens zum Cash-Close IHRES Eroeffnungstags - eine stehengebliebene
    Position (verpasster Lauf) geht damit im naechsten Lauf sofort zu, nie ueber
    Nacht (SPEC: kein Halten ueber Nacht)."""
    behalten = []
    jetzt = datetime.now(timezone.utc)
    ik = _inst_konf(w)
    for p in z["positionen"]:
        preis = oanda.preis(ik["oanda"], live)
        kurs = preis["bid"] if p["richtung"] == "long" else preis["ask"]
        grund = None
        if p["richtung"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif kurs >= p["ziel"]:
                grund = "ziel"
        else:
            if kurs >= p["stop"]:
                grund = "stop"
            elif kurs <= p["ziel"]:
                grund = "ziel"
        if grund is None and jetzt >= sess.zwangsschluss(ik, date.fromisoformat(p["eroeffnet"])):
            grund = "zwangsschluss"
        if not grund or not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def flach_stellen(z, w, live, grund):
    """Alle offenen Positionen sofort schliessen - Notausstieg fuer den
    Kill-Switch (Ruecklauf >= Grenze) und den alten Herzschlag."""
    behalten = []
    ik = _inst_konf(w)
    for p in z["positionen"]:
        preis = oanda.preis(ik["oanda"], live)
        kurs = preis["bid"] if p["richtung"] == "long" else preis["ask"]
        if not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def sitzung_da():
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


def zeige_wachen(w):
    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)
    print("=== Wachen-Status ORB  %s ===" % _jetzt())
    print("  Freigabe voll (Backtest+Papier)  %s   (Papier %d Sessions / %.1f Wochen, EV %s)"
          % (s["freigabe_voll"], s["papier_sessions"], s["papier_wochen"],
             "n/a" if s["rollierender_ev"] is None else "%+.3f" % s["rollierender_ev"]))
    print("  Ruecklauf  %.2f EUR von Hoechst %.2f  -> Faktor %.2f%s"
          % (s["ruecklauf_eur"], s["hoechststand_eur"], s["groessenfaktor"],
             "   >>> KILL" if s["kill"] else ""))
    print("  Herzschlag frisch  %s  (%s min, Grenze %d)"
          % (s["herzschlag_frisch"],
             "?" if s["herzschlag_alter_min"] is None else "%.0f" % s["herzschlag_alter_min"],
             w.get("herzschlag_max_minuten", 45)))
    print("  Journal-Zweitziel  %s" % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], w.get("journal_zweitziel"))
    print("  Journal ausser Haus  %s (%s)" % ("ok" if ok else "--", info))
    if s["kill"] and wp.sperre_zu("Wochenlauf: Kill-Switch, Ruecklauf %.2f EUR" % s["ruecklauf_eur"]):
        print("  -> handel_erlaubt auf false.")
    if s["ev_negativ"] and wp.sperre_zu("Wochenlauf: rollierender EV %.3f < 0" % s["rollierender_ev"]):
        print("  -> handel_erlaubt auf false.")


def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    w = _wachen()
    if modus == "wachen":            # reines Nachsehen - laeuft auch ohne aktives Instrument
        zeige_wachen(w)
        return
    if not w.get("instrument_aktiv"):
        print("instrument_aktiv ist null - Backtest (Task 7) hat noch kein Urteil. Kein Lauf.")
        return
    print("Zyklus kommt in Task 10/11.")  # Platzhalter NUR bis Task 10; dort ersetzt.


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    for name in ("vorschau", "papier", "live", "wachen"):
        g.add_argument("--" + name, action="store_const", dest="modus", const=name)
    a = p.parse_args()
    lauf(a.modus or "papier")
