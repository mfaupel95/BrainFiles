"""ORB auf Kraken - Papierzyklus (Spur orbk).

Reine Simulation: Kerzen von der oeffentlichen Kraken-API, Buch in
zustand.json, kein einziger Order-Call. handel_erlaubt bleibt false -
 diese Datei kann gar nicht echt handeln.

--live ist trotzdem ein gueltiger Aufruf: der Dauerlauf schaltet eine Spur nur
scharf, wenn ihr Zeitfenster offen ist (freigabefenster.py). Ohne Live-Pfad
gibt es nichts freizugeben - der Aufruf nennt genau einen Grund (ohne das Wort
"Freigabefenster", damit der Dauerlauf keine Anfrage stellt) und laeuft als
Papier weiter, statt mit einem argparse-Fehler abzubrechen. Muster: spiegel.py.

Zyklus (alle 15 min):
  1. Ausstiege zuerst: offene Papier-Position gegen Stop/Ziel/Zwangsschluss
  2. Einstieg: wenn Session-Fenster offen und noch nicht gehandelt ->
     Opening Range (00:00-00:30 UTC) fertig -> Breakout pruefen
  3. Journal + Zustand schreiben
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
BUS = HIER.parent.parent / "Bus"
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "kraken"))
sys.path.insert(0, str(BUS))

import ereignis
import kraken
import session as sess
import wachen_orb as wp


ZUSTAND = HIER / "zustand.json"
JOURNAL = HIER / "handelsjournal.csv"

# Genau ein Grund, ohne das Wort "Freigabefenster": der Dauerlauf liest diese
# Zeile im Vorschau-Modus (nur_fenster_fehlt) und fragt nur dann nach einer
# Freigabe, wenn genau dieser Grund dort steht. Diese Spur hat keinen
# Live-Pfad - es gibt nichts freizugeben, also wird auch nicht gefragt.
# Gedruckt wird sie NUR in --vorschau und --live, nicht im Papierlauf: der
# Dauerlauf schickt jede Ausgabezeile mit dem Wort "gesperrt" nach Telegram
# (dauerlauf.zyklus) - ein Lauf alle 15 Minuten waere Spam.
GRUND_KEIN_LIVE = ("Live waere gesperrt durch: kein Live-Pfad in dieser "
                   "Spur (Papier)")


def _jetzt():
    return datetime.now(timezone.utc)


def _wachen():
    return json.loads((HIER / "wachen.json").read_text(encoding="utf-8"))


def lade_zustand():
    if ZUSTAND.exists():
        z = json.loads(ZUSTAND.read_text(encoding="utf-8"))
        z.setdefault("modus", "papier")
        return z
    return {"position": None, "letzter_lauf": None, "herzschlag_ok": True,
            "modus": "papier"}


def schreibe_zustand(z):
    z.setdefault("modus", "papier")
    ZUSTAND.write_text(json.dumps(z, indent=2, ensure_ascii=False),
                       encoding="utf-8")


def journal(*felder):
    neu = not JOURNAL.exists()
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if neu:
            w.writerow(["zeit", "inst", "richtung", "einstieg", "stop",
                        "ziel", "ausgang", "ausstieg", "gv_punkte", "gv_usd"])
        w.writerow(felder)


def _inst_konf(w):
    key = w.get("instrument_aktiv")
    if not key:
        return None, None
    return key, w["instrumente"][key]


def _punkte_zu_usd(punkte, konf):
    return punkte * konf.get("punkt_wert_usd", 1.0)


def _range_fenster(w, key, tag):
    """(start, ende) der Opening Range fuer den UTC-Tag."""
    start, ende = sess.opening_range_fenster(w["instrumente"][key], tag)
    return start, ende


def pruefe_ausstiege(z, w, jetzt=None):
    """Offene Papier-Position: Stop/Ziel/Zwangsschluss. Rueckgabe (veraendert, grund)."""
    p = z.get("position")
    if not p:
        return False, None
    jetzt = jetzt or _jetzt()
    key = p["inst"]
    konf = w["instrumente"][key]
    tag = p["tag"] if isinstance(p["tag"], date) else date.fromisoformat(p["tag"])
    if p["richtung"] == "long":
        stop_verletzt = p["letzter_kurs"] <= p["stop"]
        ziel_verletzt = p["letzter_kurs"] >= p["ziel"]
    else:
        stop_verletzt = p["letzter_kurs"] >= p["stop"]
        ziel_verletzt = p["letzter_kurs"] <= p["ziel"]
    zwang = jetzt >= sess.zwangsschluss(konf, tag)
    if zwang:
        _schliesse(p, p["letzter_kurs"], "zwangsschluss")
        return True, "zwangsschluss"
    if stop_verletzt:
        _schliesse(p, p["stop"], "stop")
        return True, "stop"
    if ziel_verletzt:
        _schliesse(p, p["ziel"], "ziel")
        return True, "ziel"
    return False, None


def _schliesse(p, kurs, grund):
    # zustand.json serialisiert alles zu Strings: "tag" kommt beim Lesen als
    # ISO-String zurueck, nicht als date. Ohne das Umparsen scheiterte jeder
    # echte Ausstieg mit AttributeError, die Position liess sich nicht
    # schliessen (aufgefallen 13.09.2026: Ziel erreicht, jeder Papierlauf
    # endete mit Rueckgabe 1).
    tag = p["tag"] if isinstance(p["tag"], date) else date.fromisoformat(p["tag"])
    gv = (kurs - p["einstieg"]) if p["richtung"] == "long" else (p["einstieg"] - kurs)
    gv_usd = _punkte_zu_usd(gv, {})
    journal(tag.isoformat(), p["inst"], p["richtung"], p["einstieg"],
            p["stop"], p["ziel"], grund, kurs, round(gv, 4), round(gv_usd, 2))
    p["ausgang"] = grund
    p["ausstieg"] = kurs
    p["gv_punkte"] = gv


def _kerzen_heute(w, key):
    """Die heutigen M15-Kerzen des Instruments (Kraken-oeffentlich)."""
    konf = w["instrumente"][key]
    paar = konf["kraken"]
    roh = kraken.kerzen(paar, intervall=15, anzahl=720)
    heute = _jetzt().date()
    return [{"zeit": datetime.fromtimestamp(r[0] / 1000, timezone.utc),
             "o": r[1], "h": r[2], "l": r[3], "c": r[4]}
            for r in roh if datetime.fromtimestamp(r[0] / 1000, timezone.utc).date() == heute]


def opening_range(kerzen, w, key, tag):
    start, ende = _range_fenster(w, key, tag)
    im_fenster = [k for k in kerzen if start <= k["zeit"] < ende]
    if len(im_fenster) < 2:
        return None
    zwei = im_fenster[:2]
    return max(k["h"] for k in zwei), min(k["l"] for k in zwei)


def breakout_signal(kerzen, hoch, tief):
    """Erste Kerze nach der Range, die darueber/darunter schliesst."""
    for k in kerzen:
        if k["c"] > hoch:
            return "long", k["c"]
        if k["c"] < tief:
            return "short", k["c"]
    return None, None


# Test-Seam: Tests ersetzen die Quelle durch synthetische Kerzen.
kerzen_quelle = None  # None -> echte Kraken-Kerzen (ueber _kerzen_heute)


def pruefe_einstieg(z, w, jetzt=None):
    """Papier-Einstieg nach ORB-Regeln. Rueckgabe (einstieg, meldung)."""
    jetzt = jetzt or _jetzt()
    key, konf = _inst_konf(w)
    if not key:
        return None, "kein instrument_aktiv (Backtest-Urteil fehlt)"
    tag = sess.handelstag(jetzt)
    start, ende = _range_fenster(w, key, tag)
    if jetzt < ende:
        return None, "Range laeuft noch (%s bis %s)" % (
            start.strftime("%H:%M"), ende.strftime("%H:%M"))
    if jetzt >= sess.zwangsschluss(konf, tag):
        return None, "Session vorbei"
    if _schon_gehandelt_heute(z, tag):
        return None, "heute schon gehandelt"
    kerzen = (kerzen_quelle(w, key) if kerzen_quelle
              else _kerzen_heute(w, key))
    hr = opening_range(kerzen, w, key, tag)
    if hr is None:
        return None, "keine komplette Range (Daten?)"
    hoch, tief = hr
    if hoch - tief < w["mindest_range_punkte"][key]:
        return None, "Range zu klein (%.2f Pkt)" % (hoch - tief)
    if hoch - tief > w["max_range_punkte"][key]:
        return None, "Range zu gross (%.2f Pkt)" % (hoch - tief)
    richtung, kurs = breakout_signal(kerzen, hoch, tief)
    if not richtung:
        return None, "kein Breakout (Range %.2f..%.2f)" % (tief, hoch)
    stop = tief if richtung == "long" else hoch
    ziel = (kurs + w["ziel_k"] * (hoch - tief) if richtung == "long"
            else kurs - w["ziel_k"] * (hoch - tief))
    z["position"] = {"inst": key, "richtung": richtung, "einstieg": kurs,
                     "stop": stop, "ziel": ziel, "tag": tag.isoformat(),
                     "letzter_kurs": kurs}
    return "papier", "%s %s @ %.4f (Stop %.4f, Ziel %.4f)" % (
        richtung, key, kurs, stop, ziel)


def _schon_gehandelt_heute(z, tag):
    p = z.get("position")
    return bool(p and p.get("tag") == tag.isoformat())


def lauf(modus="papier"):
    w = _wachen()
    z = lade_zustand()
    jetzt = _jetzt()
    z["letzter_lauf"] = jetzt.isoformat()

    meldungen = []

    # 1. Ausstiege zuerst
    veraendert, grund = pruefe_ausstiege(z, w, jetzt)
    if veraendert:
        p = z.pop("position", None)
        meldungen.append("AUSSTIEG (Papier, %s): %s %s, Einstieg %.4f" % (
            grund, p["richtung"], p["inst"], p["einstieg"]))

    # 2. Einstieg
    if not z.get("position"):
        einstieg, meldung = pruefe_einstieg(z, w, jetzt)
        if einstieg:
            meldungen.append("EINSTIEG (Papier): " + meldung)
        elif meldung:
            meldungen.append("kein Einstieg: " + meldung)

    # Herzschlag + Zustand
    if z.get("position"):
        z["position"]["letzter_kurs"] = _letzter_kurs(w, z["position"]["inst"])
    schreibe_zustand(z)
    return meldungen


def _letzter_kurs(w, key):
    konf = w["instrumente"][key]
    return kraken.letzter_kurs(konf["kraken"])


def zeige_wachen(w):
    key, konf = _inst_konf(w)
    if not konf:
        return "kein instrument_aktiv - Spur gesperrt (Backtest fehlt)"
    return ("%s (%s): handel_erlaubt=%s, aktiv=%s" %
            (key, konf["kraken"], w["handel_erlaubt"], key))


def main(argv=None):
    # Der Dauerlauf startet dieses Skript als eigenen Prozess (SPUREN
    # ["orbk"], skript=handeln.py) - Start und Ende melden sich deshalb hier
    # am Bus.
    # Muster: xperp/handeln.py. Ein toter Bus bricht den Lauf nicht ab.
    with ereignis.lauf("handel/orbk"):
        return _main(argv)


def _main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("modus", nargs="?", default="papier",
                   choices=("papier", "--papier", "status", "vorschau",
                            "--status", "--vorschau", "live", "--live"))
    p.add_argument("--papier", dest="flag_papier", action="store_true")
    p.add_argument("--status", dest="flag_status", action="store_true")
    p.add_argument("--vorschau", dest="flag_vorschau", action="store_true")
    p.add_argument("--live", dest="flag_live", action="store_true")
    a = p.parse_args(argv)
    modus = a.modus
    if a.flag_papier:
        modus = "papier"
    if a.flag_status:
        modus = "status"
    if a.flag_vorschau:
        modus = "vorschau"
    if a.flag_live:
        modus = "live"
    w = _wachen()
    if modus == "status":
        print(zeige_wachen(w))
        return 0
    if modus == "vorschau":
        # Der Dauerlauf liest die Sperrgruende aus genau diesem Modus.
        print(zeige_wachen(w))
        print(GRUND_KEIN_LIVE)
        return 0
    if modus == "live":
        # Der Dauerlauf ruft --live nur, wenn ein Fenster offen ist. Diese
        # Spur hat keinen Live-Pfad - statt mit einem argparse-Fehler
        # (Rueckgabe 2, sieht wie ein Absturz aus) abzubrechen, nennt sie den
        # Grund und laeuft als Papier weiter. Muster: spiegel.py.
        print(GRUND_KEIN_LIVE)
    meldungen = lauf()
    for m in meldungen:
        print(m)
    return 0


if __name__ == "__main__":
    sys.exit(main())