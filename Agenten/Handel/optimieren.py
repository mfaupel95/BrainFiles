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

WAS SICH UEBERHAUPT SUCHEN LAESST (Stand T-097, 05.10.2026): die vier
Indikator-Spuren (squeeze, wavetrend, macd_mtf, supertrend) lesen ihre
Indikatorschwellen inzwischen aus der wachen.json (`squeeze_laenge`/
`squeeze_bb_mult`/`squeeze_kc_mult`, `wt_n1`/`wt_n2`/`wt_ueberverkauft`,
`mtf_faktoren`/`mtf_schnell`/`mtf_langsam`/`mtf_signal`,
`supertrend_n`/`supertrend_faktor`, je `atr_n`). Bis 05.10.2026 standen
diese Schwellen fest im Code (squeeze.signal() war eine feste Regel ueber
ti.squeeze_momentum); seit der Hebung kann ein Schluessel in `spur_opt.json`
die Indikatorrechnung selbst variieren. Ausstiegs-Geometrie bleibt
suchbar wie zuvor (`pflicht_stop_prozent_min`, `pflicht_stop_prozent_max`,
`ziel_r_vielfaches`). Wer einen Schluessel in `spur_opt.json` eintraegt,
den die Spur nicht liest, bekommt KEINE stille
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

import historie_binance
import replay

HIER = os.path.dirname(os.path.abspath(__file__))
OPT_PFAD = os.path.join(HIER, "spur_opt.json")

# Fenster duerfen nicht beliebig klein sein: unter dieser Zahl Kerzen ist ein
# Fenster keine Stichprobe mehr.
MINDEST_KERZEN_JE_FENSTER = 600

# Unter dieser Rundenzahl ist ein Fenster keine Stichprobe: bei ~0,5 % Vorsprung
# je Runde und ~5 % Streuung braucht es die Groessenordnung 100 Runden, damit
# Vorsprung und Rauschen zu trennen sind. Der erste Entwurf liess 8 zu - damit
# "ueberlebten" 18 von 18 Kandidaten.
MINDEST_RUNDEN_JE_FENSTER = 30

# Ein Kandidat muss die heutige Einstellung um mindestens so viel schlagen, dass
# der Unterschied nicht im Rauschen liegt.
MINDEST_VORSPRUNG_PCT = 0.10

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


def je_runde(k, gebuehr_pct=0.0):
    """Ergebnis je Runde in Prozent des Einsatzes - NETTO, nach Gebuehren.

    Die Hausfunktion `kosten_wendepunkt.wendepunkt()` liefert R, C, p, f_max,
    ev_ohne und ergebnis_summe; ein Feld `netto_pct_mittel` gibt es dort NICHT
    (das stammt aus `backtest_prognose.kennzahlen`). Wer es hier erwartet,
    stuerzt ab - genau das ist am 2026-09-25 passiert.

    Die Gebuehr MUSS abgezogen werden: `ergebnis_summe` ist brutto. Ein engerer
    Stop erzeugt mehr, kleinere Runden - brutto sieht das oft besser aus,
    waehrend je Runde 2 x Gebuehr mehr bezahlt wird. Wer brutto vergleicht,
    empfehlt die Einstellung mit den meisten Runden statt der besten.
    """
    if "netto_pct_mittel" in k:
        roh = float(k["netto_pct_mittel"])
    else:
        runden = k.get("runden") or 0
        if not runden:
            return -2 * gebuehr_pct
        roh = float(k.get("ergebnis_summe", 0.0)) / runden
    return roh - 2 * float(gebuehr_pct)


def urteil_aus(such, pruef, weitere=None, grundlinie=None, gebuehr_pct=0.0,
               mindest_runden=MINDEST_RUNDEN_JE_FENSTER):
    """Ueberlebt ein Kandidat? Verglichen wird NETTO gegen den STATUS QUO.

    Der erste Entwurf verglich die Such- gegen die Pruefhaelfte DESSELBEN
    Kandidaten. Gemessen am 2026-09-25: in einem 6-Monats-Zeitraum war die erste
    Haelfte fast durchweg negativ und die zweite positiv - darauf "ueberlebten"
    14 von 18 (squeeze) und 18 von 18 (supertrend). Ein Filter, der alles
    durchlaesst, filtert nicht; die Ursache war der Regimewechsel zwischen den
    Haelften, nicht ein Vorteil der Parameter.

    Die handlungsrelevante Frage ist eine andere: ist der Kandidat im
    PRUEFENSTER besser als die EINSTELLUNG, DIE HEUTE LAEUFT? Genau das prueft
    `grundlinie` - dieselbe Rechnung im selben Zeitraum mit den heutigen Werten.
    """
    weitere = weitere or []
    if pruef.get("runden", 0) < mindest_runden:
        return {"ueberlebt": False,
                "grund": "unter %d Runden - ein Befund, keine Messung "
                         "(Vorsprung und Streuung sind sonst nicht zu trennen)"
                         % mindest_runden}
    if not pruef.get("runden"):
        return {"ueberlebt": False, "grund": "kein Hebel: Prueffenster ohne Runde"}
    netto = je_runde(pruef, gebuehr_pct)
    if netto <= 0:
        return {"ueberlebt": False,
                "grund": "kein Hebel: netto %.3f %% je Runde im Prueffenster" % netto}
    if grundlinie is not None:
        netto_basis = je_runde(grundlinie, gebuehr_pct)
        if netto - netto_basis < MINDEST_VORSPRUNG_PCT:
            return {"ueberlebt": False,
                    "grund": "kein Hebel: %.3f %% netto gegen %.3f %% der "
                             "heutigen Einstellung (Vorsprung unter %.2f %%)"
                             % (netto, netto_basis, MINDEST_VORSPRUNG_PCT)}
    elif je_runde(pruef, gebuehr_pct) <= je_runde(such[0], gebuehr_pct):
        return {"ueberlebt": False, "grund": "kein Hebel: Prueffenster nicht besser"}
    mittel = (netto + sum(je_runde(x, gebuehr_pct) for x in weitere)) / (1 + len(weitere))
    if mittel <= 0:
        return {"ueberlebt": False,
                "grund": "kein Hebel: rollierendes Mittel nicht positiv (%.3f %%)"
                         % mittel}
    return {"ueberlebt": True,
            "grund": "netto %.3f %% je Runde, %.3f %% besser als heute"
                     % (netto, netto - je_runde(grundlinie, gebuehr_pct)
                        if grundlinie is not None else 0.0)}


def urteil_walkforward(je_fenster, basis_fenster, gebuehr_pct=0.0,
                       mindest_runden=MINDEST_RUNDEN_JE_FENSTER):
    """Urteil ueber ALLE Fenster - nicht "erstes gegen letztes".

    Die erste Fassung verglich die Suchhaelfte des ERSTEN mit der Pruefhaelfte
    des LETZTEN Fensters. Bei zwei Fenstern ist das noch vertretbar, bei vier
    willkuerlich: welches Paar man nimmt, entscheidet ueber den Ausgang. Hier
    zaehlt jedes auswertbare Fenster als eigener Vergleich Kandidat gegen
    Grundlinie, und ein Kandidat muss sie ALLE gewinnen - bei mindestens zwei
    auswertbaren Fenstern.

    Auswertbar heisst: genug Runden. Ein Fenster mit 5 Runden kann keinen
    Vorsprung von einem halben Prozent zeigen, es ist Rauschen.
    """
    gewonnen, verloren, zu_wenig, netto_liste = 0, 0, 0, []
    for kand, basis in zip(je_fenster or [], basis_fenster or []):
        if kand.get("runden", 0) < mindest_runden:
            zu_wenig += 1
            continue
        n_kand, n_basis = je_runde(kand, gebuehr_pct), je_runde(basis, gebuehr_pct)
        netto_liste.append(n_kand)
        if n_kand > n_basis + MINDEST_VORSPRUNG_PCT:
            gewonnen += 1
        else:
            verloren += 1
    if gewonnen + verloren < 2:
        return {"ueberlebt": False, "fenster_gewonnen": gewonnen,
                "fenster_verloren": verloren, "fenster_zu_wenig": zu_wenig,
                "netto_mittel": round(sum(netto_liste) / len(netto_liste), 4)
                                if netto_liste else 0.0,
                "grund": "weniger als 2 auswertbare Fenster (%d zu wenig Runden) "
                         "- ein Befund, keine Messung" % zu_wenig}
    mittel = sum(netto_liste) / len(netto_liste)
    if verloren:
        return {"ueberlebt": False, "fenster_gewonnen": gewonnen,
                "fenster_verloren": verloren, "fenster_zu_wenig": zu_wenig,
                "netto_mittel": round(mittel, 4),
                "grund": "kein Hebel: verliert in %d von %d auswertbaren Fenstern"
                         % (verloren, gewonnen + verloren)}
    if mittel <= 0:
        return {"ueberlebt": False, "fenster_gewonnen": gewonnen,
                "fenster_verloren": verloren, "fenster_zu_wenig": zu_wenig,
                "netto_mittel": round(mittel, 4),
                "grund": "kein Hebel: gewinnt jedes Fenster, ist aber im Mittel "
                         "negativ (%.3f %%)" % mittel}
    return {"ueberlebt": True, "fenster_gewonnen": gewonnen,
            "fenster_verloren": verloren, "fenster_zu_wenig": zu_wenig,
            "netto_mittel": round(mittel, 4),
            "grund": "gewinnt alle %d auswertbaren Fenster, netto %.3f %% je Runde"
                     % (gewonnen, mittel)}


def felder_ohne_wirkung(ergebnisse):
    """Suchfelder, deren Werte im Ergebnis NICHTS unterscheiden.

    Gemessen am 2026-09-25: `pflicht_stop_prozent_max` 8 und 12 lieferten
    dieselben Zahlen - der Deckel greift nie, weil der ATR-Stop darunter bleibt.
    Ein solches Feld ist fuer die Suche wertlos, und wer es nicht bemerkt,
    haelt ein Raster von 18 Kandidaten fuer 18 verschiedene Versuche.
    """
    gruppen = {}
    for e in ergebnisse:
        f = (e.get("je_fenster") or [{}])[-1]
        gruppen.setdefault((f.get("runden"), round(f.get("ergebnis_summe", 0.0), 6)),
                           []).append(e.get("werte") or {})
    tot = set()
    for werte_liste in gruppen.values():
        if len(werte_liste) < 2:
            continue
        for name in set().union(*[set(w) for w in werte_liste]):
            if len({w.get(name) for w in werte_liste}) > 1:
                tot.add(name)
    return sorted(tot)


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
                           "'python historie_binance.py --auffuellen'" % spur)
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
        reihen = replay.lade_reihen(i, takt)[von_index:]
        kuerzeste = reihen if kuerzeste is None else kuerzeste
    reihen = replay.lade_reihen(replay._instrumente(w)[0], takt)[von_index:]
    grenzen = []
    for such_i, pruef_i in abschnitte:
        grenzen.append((
            dt.datetime.fromtimestamp(reihen[such_i[0]][0] / 1000.0, dt.timezone.utc),
            dt.datetime.fromtimestamp(reihen[min(pruef_i[1], len(reihen) - 1)][0] / 1000.0,
                                      dt.timezone.utc)))

    ergebnisse = []
    grundlinie, grundlinie_fenster = None, None
    with tempfile.TemporaryDirectory() as tmp:
        temp = os.path.join(tmp, "fenster.csv")

        # ZUERST die heutige Einstellung im SELBEN Zeitraum messen. Ohne diese
        # Zahl ist "besser" bedeutungslos: der Vergleich mit der eigenen
        # Suchhaelfte hat am 2026-09-25 nur den Regimewechsel zwischen den
        # Haelften gemessen und 18 von 18 Kandidaten durchgelassen.
        basis_patch = {k: w[k] for k in tab["schluessel"] if k in w}
        try:
            with contextlib.redirect_stdout(io.StringIO()) if still else \
                    contextlib.nullcontext():
                replay.lauf_a(spur, gebuehr_pct, "grundlinie", wachen_patch=basis_patch,
                              abschnitt=(von_index, gesamt))
            basis_zeilen = _journal_zeilen(os.path.join(
                replay.buch_ordner(spur, "grundlinie"), "handelsjournal.csv"))
            basis_fenster = [_fenster_kennzahlen(basis_zeilen, a, b, temp)
                             for a, b in grenzen]
            grundlinie = basis_fenster[-1] if basis_fenster else None
            grundlinie_fenster = basis_fenster
        except Exception as e:                                     # noqa: BLE001
            print("Grundlinie nicht messbar (%s) - es wird gegen die Suchhaelfte "
                  "verglichen." % str(e)[:120])

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
            if grundlinie_fenster and len(grundlinie_fenster) == len(je_fenster):
                # Mehrere Fenster: jedes Paar zaehlt (Walk-Forward).
                u = urteil_walkforward(je_fenster, grundlinie_fenster, gebuehr_pct)
            else:
                u = urteil_aus([je_fenster[0]], je_fenster[-1], je_fenster[1:-1],
                               grundlinie=grundlinie, gebuehr_pct=gebuehr_pct)
            ergebnisse.append({"werte": werte, "je_fenster": je_fenster,
                               "netto_je_runde": round(
                                   je_runde(je_fenster[-1], gebuehr_pct), 4), **u})

    ergebnisse.sort(key=lambda x: (
        x.get("ueberlebt", False), x.get("netto_je_runde", 0.0)), reverse=True)

    # TOTE RASTERFELDER: Kandidaten mit identischen Zahlen. Gemessen am
    # 2026-09-25 lieferten `pflicht_stop_prozent_max` 8 und 12 dieselben
    # Ergebnisse - der Deckel greift in diesem Zeitraum nie, das Feld ist fuer
    # die Suche wertlos. Das gehoert in den Bericht, nicht in eine Randnotiz.
    aus = dict(plan)
    aus["kandidaten"] = ergebnisse
    aus["ueberlebt"] = [e["werte"] for e in ergebnisse if e.get("ueberlebt")]
    aus["grundlinie"] = grundlinie
    aus["grundlinie_netto_je_runde"] = round(
        je_runde(grundlinie or {}, gebuehr_pct), 4)
    aus["ohne_wirkung"] = felder_ohne_wirkung(ergebnisse)
    aus["mindest_runden_je_fenster"] = MINDEST_RUNDEN_JE_FENSTER
    aus["mindest_vorsprung_pct"] = MINDEST_VORSPRUNG_PCT
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
                      "heute_netto_je_runde": aus["grundlinie_netto_je_runde"],
                      "beste_netto_je_runde": (aus["kandidaten"] or [{}])[0].get(
                          "netto_je_runde"),
                      "ueberlebt": aus["ueberlebt"],
                      "ohne_wirkung": aus["ohne_wirkung"],
                      "gebuehr_pct": aus["gebuehr_pct"],
                      "kerzenquelle": aus["kerzenquelle"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
