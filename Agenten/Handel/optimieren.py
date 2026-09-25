"""Parametersuche je Spur auf dem Backtest-Fundament (Walk-Forward).

Verfahren: ein Lauf je Kandidat ueber den gewaehlten Zeitraum, danach werden
die Journalzeilen auf die Fenster verteilt und je Fenster gerechnet. Uebernommen
wird nur, was im PRUEFENSTER (der zweiten Haelfte) und im rollierenden Mittel
besser ist. Ein Kandidat, der dort verliert, ist "kein Hebel" - das ist ein
Ergebnis, kein Fehlschlag. (Gitter-Befund 15.09.2026: 42 Kombinationen spannten
0,17 bis 2,22 % - der Parameter ist selten der Hebel.)

Nur EIN Lauf je Kandidat, nicht einer je Fenster: die Zeiten stehen im
Journal (virtuelle Uhr), die Aufteilung passiert danach. Das ist derselbe
Vergleich und um ein Vielfaches billiger.

WAS SICH UEBERHAUPT SUCHEN LAESST (gemessen 2026-09-25): die vier
Indikator-Spuren (squeeze, wavetrend, macd_mtf, supertrend) lesen aus ihrer
wachen.json NUR die Ausstiegs-Geometrie - `pflicht_stop_prozent_min`,
`pflicht_stop_prozent_max`, `ziel_r_vielfaches` und die Platzzahl. Ihre
Indikatorschwellen stehen als Konstanten im Code (squeeze.signal() ist eine
feste Regel ueber ti.squeeze_momentum). Wer hier einen Schluessel in
`spur_opt.json` eintraegt, den die Spur nicht liest, bekommt KEINE stille
Nullnummer: `pruefe_schluessel()` bricht ab und nennt die fehlenden Namen.

Geschrieben wird NIE in eine wachen.json. Ausgabe ist eine Vorschlagsdatei
`daten/backtest/<spur>/optimierung.json`; die Uebernahme entscheidet Max.

Aufruf:
    python optimieren.py --spur squeeze --trocken      Plan und Laufzeitschaetzung
    python optimieren.py --spur squeeze --monate 6 --fenster 2
"""

import argparse
import datetime as dt
import hashlib
import itertools
import json
import os

import historie
import replay

HIER = os.path.dirname(os.path.abspath(__file__))
OPT_PFAD = os.path.join(HIER, "spur_opt.json")

# Fenster duerfen nicht beliebig klein sein: unter dieser Zahl Kerzen ist ein
# Fenster keine Stichprobe mehr.
MINDEST_KERZEN_JE_FENSTER = 600

# Gemessene Kosten eines Schrittes (2026-09-25, squeeze 1H ueber 50.223 Kerzen:
# 9 Minuten -> ~0,011 s je Schritt und Instrument). Nur fuer die Schaetzung im
# Trockenlauf, nicht fuer eine Entscheidung.
SEKUNDEN_JE_SCHRITT = 0.011


def suchtabelle(spur):
    with open(OPT_PFAD, encoding="utf-8") as f:
        d = json.load(f)
    if spur not in d:
        bekannte = ", ".join(sorted(k for k in d if not k.startswith("_")))
        raise KeyError("kein Suchbereich fuer %r in spur_opt.json - bekannt: %s"
                       % (spur, bekannte))
    return d[spur]


def pruefe_schluessel(spur, tabelle, w):
    """Bricht ab, wenn ein Suchschluessel nicht in der wachen.json steht.

    Ein Schluessel, den die Spur nicht liest, wirkt nicht - alle Kandidaten
    waeren identisch und die Suche meldete "kein Hebel". Genau diese stille
    Nullnummer soll hier nicht entstehen.
    """
    fehlend = [k for k in tabelle["schluessel"] if k not in w]
    if fehlend:
        raise RuntimeError(
            "Suchschluessel fehlen in %s/wachen.json: %s (vorhanden sind: %s)"
            % (spur, ", ".join(fehlend),
               ", ".join(sorted(k for k, v in w.items()
                                if isinstance(v, (int, float))))))
    return True


def kandidaten(tabelle, grenze=None):
    """Alle Kombinationen des Rasters, in stabiler Reihenfolge."""
    namen = sorted(tabelle["raster"])
    aus = [dict(zip(namen, werte))
           for werte in itertools.product(*(tabelle["raster"][n] for n in namen))]
    return aus[:grenze] if grenze else aus


def fenster(laenge, n_fenster):
    """[(such, pruef)] als Indexpaare - lueckenlos, ueberlappungsfrei.

    Die Pruefhaelfte eines Fensters endet dort, wo die Suchhaelfte des naechsten
    beginnt. So faellt keine Kerze zwischen die Fenster und keine wird doppelt
    gezaehlt.
    """
    laenge, n = int(laenge), int(n_fenster)
    if n < 1:
        raise ValueError("n_fenster muss mindestens 1 sein")
    if laenge < n * MINDEST_KERZEN_JE_FENSTER:
        raise ValueError("Reihe zu kurz: %d Kerzen fuer %d Fenster (mindestens %d)"
                         % (laenge, n, n * MINDEST_KERZEN_JE_FENSTER))
    breite = laenge // n
    aus = []
    for i in range(n):
        von = i * breite
        bis = von + breite
        mitte = von + breite // 2
        aus.append(((von, mitte), (mitte, bis)))
    return aus


def kerzen_je_monat(takt):
    """Kerzen eines Monats - 1H rund 730, 4H ein Viertel davon."""
    return {"1H": 730, "4H": 182, "1D": 30}.get(takt, 730)


def urteil_aus(such, pruef, weitere=None, mindest_runden=8):
    """Ueberlebt ein Kandidat das Prueffenster?"""
    weitere = weitere or []
    if pruef.get("runden", 0) < mindest_runden:
        return {"ueberlebt": False,
                "grund": "unter %d Runden - ein Befund, keine Messung"
                         % mindest_runden}
    if not pruef.get("runden"):
        return {"ueberlebt": False, "grund": "kein Hebel: Prueffenster ohne Runde"}
    if pruef["netto_pct_mittel"] <= such[0]["netto_pct_mittel"]:
        return {"ueberlebt": False, "grund": "kein Hebel: Prueffenster nicht besser"}
    mittel = (pruef["netto_pct_mittel"]
              + sum(x["netto_pct_mittel"] for x in weitere)) / (1 + len(weitere))
    if mittel <= 0:
        return {"ueberlebt": False,
                "grund": "kein Hebel: rollierendes Mittel nicht positiv (%.3f %%)"
                         % mittel}
    return {"ueberlebt": True,
            "grund": "Prueffenster und rollierendes Mittel besser (%.3f %%)" % mittel}


def _kompakt(spur, werte):
    schluessel = hashlib.md5(
        json.dumps(werte, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return "%s_%s" % (spur, schluessel)


def _journal_zeilen(pfad):
    import csv
    try:
        with open(pfad, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except (OSError, ValueError):
        return []


def _zeit_von(zeile):
    """Zeitstempel einer Journalzeile - bevorzugt der KERZENstempel.

    `_kerzen_ts` setzt der Replay selbst (Millisekunden der Kerze). Die Spalte
    `zeit` ist nur der Rueckfall: sie kommt aus der Uhr der Spur und traegt bei
    einer nicht gesetzten Uhr die Wanduhr des Laufs.
    """
    ts = zeile.get("_kerzen_ts")
    if ts not in (None, "", "None"):
        try:
            return dt.datetime.fromtimestamp(float(ts) / 1000.0, dt.timezone.utc)
        except (TypeError, ValueError):
            pass
    try:
        return dt.datetime.fromisoformat(zeile["zeit"])
    except (KeyError, TypeError, ValueError):
        return None


def _fenster_kennzahlen(zeilen, von, bis, temp_pfad):
    """Kennzahlen der Zeilen in [von, bis) - ueber die Hausfunktion."""
    import csv
    teil = []
    for z in zeilen:
        t = _zeit_von(z)
        if t is not None and von <= t < bis:
            teil.append(z)
    if not teil:
        return {"runden": 0}
    felder = list(zeilen[0])
    with open(temp_pfad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=felder, extrasaction="ignore")
        w.writeheader()
        for z in teil:
            w.writerow(z)
    return replay.kennzahlen(temp_pfad)


def suche(spur, gebuehr_pct, n_fenster=2, monate=6, max_kandidaten=40,
          trocken=False, still=True):
    """Rastersuche mit Walk-Forward. Gibt das Urteil je Kandidat zurueck."""
    import contextlib
    import io
    import tempfile

    tab = suchtabelle(spur)
    w = dict(replay.spur_modul(spur).lade_wachen())
    pruefe_schluessel(spur, tab, w)
    takt = replay._takt(w)
    gesamt = replay.kerzenlaenge(spur, w)
    if not gesamt:
        raise RuntimeError("keine Historie fuer %s - erst "
                           "'python historie.py --auffuellen'" % spur)
    kerzen = min(gesamt, int(monate) * kerzen_je_monat(takt))
    # Ein zu kurzer Zeitraum ist kein Fehler des Aufrufers, sondern eine Rechnung:
    # 6 Monate im 4H-Takt sind 1092 Kerzen und reichen fuer 2 Fenster nicht.
    # Der Zeitraum wird angehoben UND GEMELDET - still eine andere Zahl zu
    # rechnen waere schlimmer als der Abbruch.
    noetig = int(n_fenster) * MINDEST_KERZEN_JE_FENSTER
    if kerzen < noetig:
        neu = -(-noetig // kerzen_je_monat(takt))
        print("Zeitraum angehoben: %d Monate im %s-Takt sind %d Kerzen, fuer %d "
              "Fenster noetig sind %d -> %d Monate."
              % (monate, takt, kerzen, n_fenster, noetig, neu))
        monate = neu
        kerzen = min(gesamt, int(monate) * kerzen_je_monat(takt))
    von_index = gesamt - kerzen
    abschnitte = fenster(kerzen, n_fenster)
    kand = kandidaten(tab, max_kandidaten)

    plan = {"spur": spur, "kerzen": kerzen, "von_index": von_index,
            "n_fenster": n_fenster, "kandidaten": len(kand),
            "schlussel": tab["schluessel"], "takt": takt,
            "geschaetzte_sekunden": int(len(kand) * kerzen * SEKUNDEN_JE_SCHRITT)}
    if trocken:
        return {"plan": plan, "kandidaten": [], "ueberlebt": []}

    # Die Fenstergrenzen in Zeit umrechnen: die Zeilen aus dem Journal tragen
    # die virtuelle Uhr, der Index ist die Kerzenposition im Abschnitt.
    kuerzeste = None
    for i in replay._instrumente(w):
        reihen = historie.lade(i, takt)[von_index:]
        kuerzeste = reihen if kuerzeste is None else kuerzeste
    reihen = historie.lade(replay._instrumente(w)[0], takt)[von_index:]
    grenzen = []
    for such_i, pruef_i in abschnitte:
        grenzen.append((
            dt.datetime.fromtimestamp(reihen[such_i[0]][0] / 1000.0, dt.timezone.utc),
            dt.datetime.fromtimestamp(reihen[min(pruef_i[1], len(reihen) - 1)][0] / 1000.0,
                                      dt.timezone.utc)))

    ergebnisse = []
    with tempfile.TemporaryDirectory() as tmp:
        temp = os.path.join(tmp, "fenster.csv")
        for werte in kand:
            lauf = _kompakt(spur, werte)
            try:
                with contextlib.redirect_stdout(io.StringIO()) if still else \
                        contextlib.nullcontext():
                    replay.lauf_a(spur, gebuehr_pct, lauf, wachen_patch=werte,
                                  abschnitt=(von_index, gesamt))
            except Exception as e:                                 # noqa: BLE001
                ergebnisse.append({"werte": werte, "fehler": str(e)[:200]})
                continue
            journal = os.path.join(replay.buch_ordner(spur, lauf),
                                   "handelsjournal.csv")
            zeilen = _journal_zeilen(journal)
            je_fenster = []
            for a, b in grenzen:
                je_fenster.append(_fenster_kennzahlen(zeilen, a, b, temp))
            if len(je_fenster) < 2:
                ergebnisse.append({"werte": werte, "fehler": "zu wenige Fenster"})
                continue
            u = urteil_aus([je_fenster[0]], je_fenster[-1], je_fenster[1:-1])
            ergebnisse.append({"werte": werte, "je_fenster": je_fenster, **u})

    ergebnisse.sort(key=lambda x: (
        x.get("ueberlebt", False),
        (x.get("je_fenster") or [{}])[-1].get("netto_pct_mittel", 0)), reverse=True)
    aus = dict(plan)
    aus["kandidaten"] = ergebnisse
    aus["ueberlebt"] = [e["werte"] for e in ergebnisse if e.get("ueberlebt")]
    aus["kerzenquelle"] = "binance"
    aus["gebuehr_pct"] = gebuehr_pct
    ziel = os.path.join(replay.wurzel(), spur)
    os.makedirs(ziel, exist_ok=True)
    with open(os.path.join(ziel, "optimierung.json"), "w", encoding="utf-8") as f:
        json.dump(aus, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return aus


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spur", required=True)
    ap.add_argument("--fenster", type=int, default=2)
    ap.add_argument("--monate", type=int, default=6)
    ap.add_argument("--max-kandidaten", type=int, default=40)
    ap.add_argument("--gebuehr", type=float, default=None)
    ap.add_argument("--trocken", action="store_true")
    a = ap.parse_args()
    w = dict(replay.spur_modul(a.spur).lade_wachen())
    g = a.gebuehr if a.gebuehr is not None else replay.gebuehr_fuer(a.spur, w)
    aus = suche(a.spur, g, a.fenster, a.monate, a.max_kandidaten, a.trocken)
    if a.trocken:
        print(json.dumps(aus["plan"], indent=2, ensure_ascii=False))
        print("Trockenlauf: nichts gerechnet, nichts geschrieben.")
        return
    print(json.dumps({"spur": aus["spur"], "kandidaten": len(aus["kandidaten"]),
                      "ueberlebt": aus["ueberlebt"],
                      "gebuehr_pct": aus["gebuehr_pct"],
                      "kerzenquelle": aus["kerzenquelle"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
