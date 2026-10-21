"""jev_trader - Papier-Spur ueber das Block-Event-Log des jev-trader-Bots.

Der jev-trader (TypeScript/bun auf der Monad-Blockchain, Kuru-Orderbuch) hat
seinen Lauf als JSONL geschrieben (events.jsonl, ~63k Block-Events). Diese
Spur liest dieses Log, rekonstruiert die GESCHLOSSENEN Roundtrips aus dem
`position`-Feld (siehe einlesen.py) und bucht sie als Papier-Journal
(handelsjournal.csv) im Haus-Schema - damit erscheint jev_trader in der
normalen Handel-Auswertung.

PAPIER-FEST: Es gibt keinen Live-Pfad und keinen Boersen-Call. handel_erlaubt
bleibt false, die Quelle ist eine Datei, nicht ein Markt. --live ist kein
gueltiger Aufruf; --vorschau nennt den Grund.

Idempotenz: Der Lauf merkt sich in zustand.json die Zeit der zuletzt
gebuchten Runde (`letzte_runde_ts`). Beim naechsten Lauf werden nur Runden
angehaengt, deren Schliesszeit NEUER ist - ein zweiter Lauf ueber dieselbe
Datei bucht nichts doppelt.

Zyklus (--papier):
  1. events.jsonl lesen, Roundtrips rekonstruieren
  2. nur neue Runden ans Journal haengen (idempotent)
  3. zustand.json schreiben, Journal + Zustand nach Q: spiegeln (Bedingung 4)
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent

# Gemeinsame Handel-Module ueber den PFAD laden (Hausmuster _rs_spec/_rs_mod,
# s. orb/handeln.py): die Spur startet mit ihrem eigenen Ordner als sys.path[0],
# ein blankes 'import risikostufe' haenge an der Reihenfolge der Eintraege.
from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec

_rs_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "risikostufe.py")
_rs_spec_obj = _rs_spec("risikostufe", _rs_datei)
risikostufe = _rs_mod(_rs_spec_obj)
_rs_spec_obj.loader.exec_module(risikostufe)

# atomar.py: Zustand atomar schreiben und laut lesen.
_at_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "atomar.py")
_at_spec_obj = _rs_spec("atomar", _at_datei)
atomar = _rs_mod(_at_spec_obj)
_at_spec_obj.loader.exec_module(atomar)

# wachen_pruefung.py (scanner): spiegele_journal / vermerke_spiegelung
# (Bedingung 4). Ueber den PFAD, wie orb es ueber wachen_orb tut.
_wp_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "scanner", "wachen_pruefung.py")
_wp_spec_obj = _rs_spec("wachen_pruefung", _wp_datei)
wp = _rs_mod(_wp_spec_obj)
_wp_spec_obj.loader.exec_module(wp)

_BUS = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "Bus")
# ereignis importiert "bus" aus dem Bus-Ordner - der muss auf sys.path
# liegen, sonst scheitert der PFAD-Ladevorgang (Hausmuster scanner).
sys.path.insert(0, _BUS)
_ev_spec = _rs_spec("ereignis", os.path.join(_BUS, "ereignis.py"))
ereignis = _rs_mod(_ev_spec)
_ev_spec.loader.exec_module(ereignis)

import einlesen  # noqa: E402   (gleicher Ordner)

ZUSTAND = risikostufe.datei(HIER / "zustand.json")
JOURNAL = risikostufe.datei(HIER / "handelsjournal.csv")

SPUR = "jev_trader"

KOPF = ["zeit", "inst", "richtung", "einstieg", "stop", "ziel", "ausgang",
        "ausstieg", "gv_punkte", "gv_usd", "mfe_pct", "mae_pct", "haltetage"]


def _jetzt():
    return datetime.now(timezone.utc)


def _wachen():
    return json.loads((HIER / "wachen.json").read_text(encoding="utf-8"))


def lade_zustand():
    z = atomar.lade_json(ZUSTAND, lambda: None)
    if z is not None:
        return z
    return {"letzte_runde_ts": None, "letzter_lauf": None}


def schreibe_zustand(z):
    atomar.schreibe_json(ZUSTAND, z)


def quelle(w):
    """Pfad zur events.jsonl aus der Wache. Fehlt er, ist die Spur tot."""
    q = w.get("quelle")
    if not q:
        return None
    p = Path(q)
    return p if p.exists() else None


def rekonstruiere(w):
    """Alle geschlossenen Roundtrips aus der Quelle (einlesen.py)."""
    q = quelle(w)
    if q is None:
        return []
    return einlesen.rekonstruiere_runden(einlesen.lese_events(q))


def _neue_runden(runden, z):
    """Nur Runden, deren Schliesszeit neuer ist als die zuletzt gebuchte."""
    letzte = z.get("letzte_runde_ts")
    if letzte is None:
        return runden
    return [r for r in runden if r["close_ts"] > letzte]


def journal(*felder):
    neu = not JOURNAL.exists()
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        if neu:
            w.writerow(KOPF)
        w.writerow(felder)


def buch_runden(runden, z):
    """Neue Runden ans Journal haengen. Rueckgabe: Anzahl gebuchter Runden."""
    neu = _neue_runden(runden, z)
    for r in neu:
        journal(*einlesen.journal_zeile(r))
    if neu:
        z["letzte_runde_ts"] = max(r["close_ts"] for r in neu)
    return len(neu)


def lauf(w=None):
    """Der Papierzyklus: lesen, neue Runden buchen, Zustand schreiben.

    Rueckgabe: (meldungen, anzahl_neu). Kein Boersen-Call, keine Order.
    """
    w = w or _wachen()
    z = lade_zustand()
    z["letzter_lauf"] = _jetzt().isoformat()
    runden = rekonstruiere(w)
    anzahl = buch_runden(runden, z)
    schreibe_zustand(z)
    meldungen = []
    if anzahl:
        meldungen.append("PAPIER: %d neue geschlossene Runde(n) gebucht"
                         % anzahl)
    else:
        meldungen.append("PAPIER: keine neue Runde (Log unveraendert)")
    return meldungen, anzahl


def zeige_wachen(w):
    q = quelle(w)
    z = lade_zustand()
    kopie = ("   |   Journal-Zweitziel %s%s"
             % (w.get("journal_zweitziel") or "-- nicht gesetzt",
                "" if "journal_zweitziel_ok" not in z
                else " (letzte Kopie %s)" % z["journal_zweitziel_ok"]))
    return ("jev_trader: handel_erlaubt=%s, freigabe=%s, quelle=%s%s"
            % (w.get("handel_erlaubt"), (w.get("freigabe") or {}).get("erfuellt"),
               q if q else "-- fehlt", kopie))


def live_sperren(w):
    """Alle Gruende, die einen Live-Lauf verhindern. Diese Spur hat KEINEN
    Live-Pfad - sie ist papierfest. Leere Liste gaebe es nie."""
    gruende = []
    if not w.get("handel_erlaubt"):
        gruende.append("wachen.json handel_erlaubt=false")
    if not (w.get("freigabe") or {}).get("erfuellt"):
        gruende.append("freigabe.erfuellt=false")
    if not w.get("journal_zweitziel"):
        gruende.append("journal_zweitziel nicht gesetzt (Bedingung 4)")
    gruende.append("kein Live-Pfad (Papier-Spur)")
    return gruende


def _journal_stats():
    """Runden/Treffer/Ergebnis aus dem Journal - fuer --vorschau."""
    import auswertung
    k = auswertung.kennzahlen(
        auswertung.runden_aus_journal(auswertung.lade_zeilen()))
    return k


def _main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("modus", nargs="?", default="papier",
                   choices=("papier", "--papier", "status", "vorschau",
                            "--status", "--vorschau"))
    p.add_argument("--papier", dest="flag_papier", action="store_true")
    p.add_argument("--status", dest="flag_status", action="store_true")
    p.add_argument("--vorschau", dest="flag_vorschau", action="store_true")
    a = p.parse_args(argv)
    modus = a.modus
    if a.flag_papier:
        modus = "papier"
    if a.flag_status:
        modus = "status"
    if a.flag_vorschau:
        modus = "vorschau"

    w = _wachen()
    if modus == "status":
        print(zeige_wachen(w))
        return 0
    if modus == "vorschau":
        print(zeige_wachen(w))
        k = _journal_stats()
        if k:
            print("  Journal: %d Runden, %.0f %% Treffer, Ergebnis %+.6f USD "
                  "(EV %+.4f USD/Runde)"
                  % (k["n"], k["treffer_pct"], k["ergebnis"], k["ev"]))
        else:
            print("  Journal: noch keine geschlossene Runde")
        print("Live waere gesperrt durch: %s"
              % "; ".join(live_sperren(w)))
        return 0

    meldungen, _anzahl = lauf(w)
    for m in meldungen:
        print(m)
    z = lade_zustand()
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        wp.spiegele_journal([ZUSTAND], ziel)
    print("Journal ausser Haus: %s (%s)" % ("ok" if ok else "--", info))
    return 0


def main(argv=None):
    with ereignis.lauf("handel/jev_trader"):
        return _main(argv)


if __name__ == "__main__":
    sys.exit(main())
