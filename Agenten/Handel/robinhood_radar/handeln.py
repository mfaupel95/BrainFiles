#!/usr/bin/env python3
"""Robinhood-Radar (robinhood_radar): bewerteten Wallets auf Robinhood Chain nachkaufen.

AUFTRAG Max 22.09.2026: "Radar -papierspur und -bot".

WAS HIER GEMESSEN WIRD
----------------------
Der FOMO-Robinhood-Radar (`Werkstatt/fomo-robinhood-radar`) liest die
On-Chain-Aktivitaet von Tradern auf Robinhood Chain (Chain-ID 4663) und
BEWERTET die Wallets mit einem Sprachmodell (0-100). Diese Spur kopiert nicht
die Rangliste (das waere Zuchtauswahl nach dem Ergebnis), sondern das
GESCHEHEN: kauft eine Kohorte von mindestens `mindest_kaeufer` bewerteten
Wallets denselben Token innerhalb von `signal_fenster_stunden`, ist das ein
Signal.

Die Regel, nachrechenbar
------------------------
1. KAeufe im Fenster (Standard 6 h) von Wallets mit `score >= mindest_score`
   (Standard 60) und `status != dropped` werden je Token gezaehlt.
2. Ein Token ist Kandidat, wenn ihn mindestens `mindest_kaeufer` (Standard 2)
   VERSCHIEDENE bewertete Wallets gekauft haben.
3. KEIN Signal, wenn dieselbe Kohorte im selben Fenster mehr verkauft als
   gekauft hat (`verkaufs_anteil`, Standard 0,5) - sonst kauft die Spur in
   einen Abverkauf hinein.
4. Einstiegspreis ist der PREIS DES JUENGSTEN BEOBACHTETEN KAUFS
   (`usd_value / token_amount`) mit einem Nachlauf-Aufschlag
   (`nachlauf_prozent`) - der Radar sammelt im Takt, die eigene Buchung liegt
   also hinter dem Vorbild. Ohne diese Kosten waere das Buch eine
   Wunschrechnung; siehe wachen.json `_kosten`.
5. Danach das Buch von `Handel/spur_buch.py`: Stop in Prozent, Ziel als
   R-Vielfaches, Ratsche, Risikovorfilter, Spiegelung nach Q:.

Richtung nur LONG - auf dieser Kette gibt es fuer uns keinen Leerverkauf.
Papier, kein Orderpfad: `--live` verweigert mit Grund.

Aufruf (aus dem Spurordner):
    python handeln.py --vorschau     # rechnen, nichts schreiben
    python handeln.py --papier       # Papierzyklus (Standard)
    python handeln.py --wachen       # Grenzen zeigen
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
# Reihenfolge: die eigene Spur ZULETZT (gleichnamige Module aus scanner/
# duerfen 'handeln' und 'lesen' nicht verdecken).
for _p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

import spur_buch                                                   # noqa: E402
import lesen                                                       # noqa: E402

# Test-Seam: None = echte Radar-Datenbank.
datenquelle = None
# Stand eines Zyklus (Reihenfolge nach Staerke, Zahl der ausgegebenen Signale).
_zyklus: dict = {}


def _kennzahlen(w, jetzt_ts):
    """Alle Kandidaten aus den Rohzeilen der Radar-Datenbank.

    Reine Rechnung auf uebergebenen Zeilen - kein Netz, keine Datei. So ist die
    Auswahlregel offline pruefbar (tests/test_robinhood_radar.py).
    """
    fenster = float(w.get("signal_fenster_stunden", 6)) * 3600.0
    mindest_score = float(w.get("mindest_score", 60.0))
    mindest_kaeufer = int(w.get("mindest_kaeufer", 2))
    verkaufs_anteil = float(w.get("verkaufs_anteil", 0.5))

    kohorte: dict = {}
    for k in kaeufe:
        if jetzt_ts - float(k["ts"]) > fenster:
            continue
        score = k.get("score")
        if score is None or float(score) < mindest_score:
            continue                      # unbewertet ist nicht gleich gut
        if (k.get("status") or "") == "dropped":
            continue
        e = kohorte.setdefault(k["mint"], {"kaeufer": {}, "umsatz": 0.0,
                                           "juengster_ts": 0.0, "preis": 0.0})
        e["kaeufer"][k["wallet"]] = max(e["kaeufer"].get(k["wallet"], 0.0),
                                        float(score))
        e["umsatz"] += float(k["usd"])
        if float(k["ts"]) > e["juengster_ts"]:
            e["juengster_ts"] = float(k["ts"])
            e["preis"] = float(k["usd"]) / float(k["menge"])

    nachlauf = 1.0 + float(w.get("nachlauf_prozent", 2.0)) / 100.0
    daten, kurse, ablehnung = {}, {}, {}
    for mint, e in kohorte.items():
        if len(e["kaeufer"]) < mindest_kaeufer:
            ablehnung["zu wenige bewertete Kaeufer"] = \
                ablehnung.get("zu wenige bewertete Kaeufer", 0) + 1
            continue
        if e["preis"] <= 0:
            ablehnung["kein beobachteter Preis"] = \
                ablehnung.get("kein beobachteter Preis", 0) + 1
            continue
        verkauft = float(verkaufsdruck.get(mint, 0.0))
        if verkauft > verkaufs_anteil * e["umsatz"]:
            ablehnung["Kohorte verkauft selbst"] = \
                ablehnung.get("Kohorte verkauft selbst", 0) + 1
            continue
        preis = e["preis"] * nachlauf
        daten[mint] = {
            "mint": mint,
            "preis": preis,
            "kaeufer": sorted(e["kaeufer"]),
            "anzahl_kaeufer": len(e["kaeufer"]),
            "bester_score": max(e["kaeufer"].values()),
            "umsatz_kauf_usd": round(e["umsatz"], 2),
            "umsatz_verkauf_usd": round(verkauft, 2),
            "juengster_kauf": e["juengster_ts"],
            "alter_minuten": round((jetzt_ts - e["juengster_ts"]) / 60.0, 1),
        }
        kurse[mint] = preis

    # Staerkste zuerst: Umsatz, dann Zahl der Kaeufer, dann bester Score.
    reihe = sorted(daten, key=lambda m: (daten[m]["umsatz_kauf_usd"],
                                         daten[m]["anzahl_kaeufer"],
                                         daten[m]["bester_score"]),
                   reverse=True)
    _zyklus.clear()
    _zyklus.update({"reihe": reihe, "ablehnung": ablehnung,
                    "bereit": set(reihe[:max(0, int(w.get("max_neue_je_zyklus",
                                                           1)))]),
                    "ausgegeben": 0})
    return daten, kurse


def quelle(w):
    """Kandidaten aus der Radar-Datenbank. Rueckgabe wie bei allen Buch-Spuren."""
    global kaeufe, verkaufsdruck
    daten, kurse, fehler = {}, {}, []
    try:
        if datenquelle is not None:
            kaeufe, verkaufsdruck = datenquelle(w)
        else:
            con = lesen.verbinde()
            try:
                jetzt_ts = time.time()
                seit = jetzt_ts - float(w.get("signal_fenster_stunden", 6)) * 3600.0
                kaeufe = lesen.kaeufe(con, seit)
                verkaufsdruck = lesen.verkaufsdruck(con, seit)
                # T-299: eine OFFENE Position braucht einen Kurs, sonst
                # prueft `spur_buch.pruefe_ausstiege` gar nichts und die
                # Position steht ewig. Der letzte beobachtete Handel DIESES
                # Tokens ist der beste Kurs, den diese Kette hergibt - er
                # kommt in `kurse`, nicht in `daten`: er darf eine Position
                # beenden, aber keinen neuen Einstieg ausloesen.
                for inst in _offene_instanzen():
                    preis, _ts = lesen.letzte_beobachtung(con, inst)
                    if preis > 0 and inst not in kurse:
                        kurse[inst] = preis
            finally:
                con.close()
    except Exception as e:                                          # noqa: BLE001
        return {}, {}, ["Radar-Datenbank nicht lesbar (%s)" % e]

    daten, kurse2 = _kennzahlen(w, time.time())
    # Die Einstiegspreise der Kandidaten haben Vorrang vor dem blossen
    # letzten Handel (sie tragen den Nachlauf-Aufschlag).
    kurse2.update(kurse)
    return daten, kurse2, fehler


def _offene_instanzen(ordner=None):
    """Die Instrumente, die im Buch OFFEN sind (leer bei fehlendem Zustand)."""
    ordner = ordner or HIER
    try:
        _, zustand_pfad, _ = spur_buch.pfade(ordner)
        z = spur_buch.lade_zustand(zustand_pfad)
    except (OSError, ValueError):
        return []
    return [p.get("inst") for p in z.get("positionen", []) if p.get("inst")]


def raeume_ohne_kurs(w, ordner=None, con=None, jetzt_ts=None):
    """Positionen schliessen, fuer die die Kette zu lange nichts mehr zeigt.

    T-299, Anlass: drei Papierpositionen vom 22./23.09.2026 standen ohne
    Kurs im Buch. `spur_buch.pruefe_ausstiege` ueberspringt eine Position
    ohne Kurs - mit der Absicht, sie stehen zu lassen. Auf dieser Kette
    bedeutet das: der Token wird nicht mehr gehandelt, und die Position
    blockiert einen der drei Plaetze fuer immer (gemessen 02.10.2026:
    `max_offene_positionen` 3, drei Positionen offen, `datenlage.kandidaten`
    1 - die Spur konnte nichts Neues eroeffnen).

    Regel: liegt die LETZTE beobachtete Fuellung dieses Tokens laenger als
    `beobachtung_max_alter_stunden` zurueck (Vorgabe 24 h), wird die
    Position zum letzten bekannten Kurs geschlossen - geschlossen wird zum
    Beobachtungspreis, nicht zum Einstieg; ist gar keine Fuellung da,
    neutral zum Einstieg. Der Grund heisst `buchbereinigung_kein_kurs` und
    faellt damit unter `stoerungen.BUCHHALTUNG`: das ist eine Buchbereinigung,
    keine Handelsentscheidung, und darf nicht als Runde gezaehlt werden.

    Rueckgabe: (geraeumte_instanzen, [(inst, preis, alter_h)], fehler).
    """
    ordner = ordner or HIER
    jetzt_ts = jetzt_ts or time.time()
    grenze_h = float(w.get("beobachtung_max_alter_stunden", 24.0))
    _, zustand_pfad, journal_pfad = spur_buch.pfade(ordner)
    z = spur_buch.lade_zustand(zustand_pfad)
    positionen = z.get("positionen") or []
    if not positionen:
        return [], [], []

    eigen = con is None
    if eigen:
        try:
            con = lesen.verbinde()
        except Exception as e:                                      # noqa: BLE001
            return [], [], ["Radar-Datenbank nicht lesbar (%s)" % e]

    behalten, geraeumt, befund = [], [], []
    buchungen = []   # (p, kurs, gv, alter_h) - nach der Schleife GEMEINSAM gebucht
    try:
        for p in positionen:
            preis, ts = lesen.letzte_beobachtung(con, p["inst"])
            alter_h = (jetzt_ts - ts) / 3600.0 if ts > 0 else None
            if alter_h is not None and alter_h <= grenze_h:
                behalten.append(p)
                continue
            # Zu alt oder gar nicht beobachtet: schliessen.
            kurs = preis if preis > 0 else float(p["einstieg"])
            vz = 1 if p["seite"] == "long" else -1
            gv = float(p["nominal"]) * (kurs / float(p["einstieg"]) - 1.0) * vz
            buchungen.append((p, kurs, gv, alter_h))
            geraeumt.append(p["inst"])
            befund.append((p["inst"], kurs, alter_h))
    finally:
        if eigen and con is not None:
            con.close()

    if geraeumt:
        # Erst verschwinden die Positionen aus dem Zustand, dann kommt je
        # Ausstieg Zeile UND Zustand zusammen (spur_buch.buche) - eine
        # Buchung, die nur das Journal erreicht, wuerde einen Geist
        # erzeugen (T-356).
        z["positionen"] = behalten
        for p, kurs, gv, alter_h in buchungen:
            spur_buch.buche(
                z, zustand_pfad, journal_pfad, zeit=spur_buch.jetzt(),
                modus="papier", aktion="verkauf", inst=p["inst"],
                seite=p["seite"], preis=spur_buch.pformat(kurs),
                einsatz_usd="%.2f" % (float(p["nominal"]) + gv),
                stop=spur_buch.pformat(p["stop"]),
                ziel=spur_buch.pformat(p["ziel"]),
                stop_pct="%.2f" % float(p["stop_pct"]),
                grund="buchbereinigung_kein_kurs", pos_id=p.get("pos_id", ""))
            print("GERAEUMT %s: letzte Beobachtung %s -> %.8g, G/V %+.2f USD"
                  % (p["inst"],
                     ("vor %.1f h" % alter_h) if alter_h is not None else "nie",
                     kurs, gv))
        spur_buch.spiegeln(zustand_pfad, journal_pfad, z, w)
    return geraeumt, befund, []


def signal(d, w, mint=None):
    """'long', wenn der Token von genug bewerteten Wallets gekauft wurde.

    Je Zyklus wird nur der STAERKSTE Kandidat (bzw. die staerksten
    `max_neue_je_zyklus`) zum Einstieg angeboten. Sonst fuellt der erste
    Zyklus mit Daten das ganze Buch auf einmal, und die Auswertung kann nicht
    zeigen, welcher Rang traegt. Der Aufrufer (spur_buch) nennt den Token
    ueber `d["mint"]`; fehlt er, gilt der staerkste Kandidat als gemeint.
    """
    mint = mint or d.get("mint")
    if float(d.get("anzahl_kaeufer") or 0) < int(w.get("mindest_kaeufer", 2)):
        return None
    if float(d.get("preis") or 0) <= 0:
        return None
    bereit = _zyklus.get("bereit")
    if bereit is not None and mint not in bereit:
        return None
    if _zyklus.get("ausgegeben", 0) >= int(w.get("max_neue_je_zyklus", 1)):
        return None
    _zyklus["ausgegeben"] = _zyklus.get("ausgegeben", 0) + 1
    return "long"


def _verteilung(werte):
    """min, p25, Median, p75, max, Schnitt - die Verteilung, nicht nur ein
    Mittelwert (Regel 8 der Tor-Kalibrierung)."""
    werte = sorted(werte)
    if not werte:
        return None

    def q(anteil):
        # Lineare Interpolation (wie in kopier/_verteilung): bei gerader Anzahl
        # ist der Median das Mittel der beiden mittleren Werte.
        x = anteil * (len(werte) - 1)
        unten = int(x)
        oben = min(len(werte) - 1, unten + 1)
        rest = x - unten
        return werte[unten] * (1 - rest) + werte[oben] * rest
    return {"n": len(werte), "min": werte[0], "p25": q(0.25),
            "median": q(0.50), "p75": q(0.75), "max": werte[-1],
            "schnitt": sum(werte) / len(werte)}


def nachlauf_messen(fills, trigger_ts=None):
    """Nachlauf je Kauf: Kurs des NAECHSTEN beobachteten Handels gegen den Kauf.

    Reine Rechnung auf uebergebenen Zeilen (offline pruefbar). Der Radar
    sammelt im Takt; die eigene Buchung liegt hinter dem Vorbild. Wie weit der
    Kurs in dieser Zwischenzeit weg ist, steht NIRGENDS in der Kette - nur in
    der eigenen Sammlung, naemlich am naechsten beobachteten Handel desselben
    Tokens. Genau das ist der Posten, den ein Nachahmer verliert.
    """
    je_token = {}
    for f in fills:
        je_token.setdefault(f["mint"], []).append(f)
    aus = []
    for mint, reihe in je_token.items():
        reihe = sorted(reihe, key=lambda x: x["ts"])
        for i, f in enumerate(reihe):
            if f["seite"] != "buy" or f["preis"] <= 0:
                continue
            if trigger_ts is not None and mint not in trigger_ts:
                continue
            naechste = next((g for g in reihe[i + 1:]
                             if g["preis"] > 0), None)
            if naechste is None:
                continue
            aus.append({"mint": mint, "wallet": f["wallet"],
                        "preis_kauf": f["preis"], "preis_naechster": naechste["preis"],
                        "seite_naechster": naechste["seite"],
                        "abstand_s": max(0.0, float(naechste["ts"]) - float(f["ts"])),
                        "nachlauf_pct": (naechste["preis"] / f["preis"] - 1) * 100})
    return aus


def messen(w, con=None):
    """T-268: die Kostenannahme der Spur gegen die eigene Sammlung halten.

    Gemessen wird der Nachlauf (Kurs des naechsten beobachteten Handels gegen
    den Kauf). Zwei Stichproben: ALLE Kaeufe der Sammlung und die Kaeufe, die
    die eigene Regel als Signal genommen haette (Kohorte von bewerteten
    Wallets). Die Gebuehr selbst (gebuehr_taker) ist in den Daten NICHT
    sichtbar - sie steckt im Poolpreis; sie bleibt eine Annahme und steht so
    in wachen.json. Das Buch wird nicht angefasst.
    """
    eigene = con is None
    try:
        if eigene:
            con = lesen.verbinde()
        alle = lesen.alle_fills(con)
        fenster = float(w.get("signal_fenster_stunden", 6)) * 3600.0
        juengster = lesen.juengster_kauf(con) if alle else 0.0
        kaeufe = lesen.kaeufe(con, max(0.0, juengster - fenster)) if alle else []
    except lesen.DatenbankFehlt as e:
        print("Radar-Datenbank nicht lesbar: %s" % e)
        return 1
    finally:
        if eigene and con is not None:
            con.close()

    if not alle:
        print("Die Sammlung ist leer - der Radar hat noch nichts beobachtet. "
              "Das ist ein Ergebnis (kein Messwert), kein Fehler.")
        return 1

    alle_k = nachlauf_messen(alle)

    # Signalfall: je Token der JUENGSTE Kauf der bewerteten Kohorte ist der
    # Ausloeser unserer Regel (dieselbe Rechnung wie in _kennzahlen).
    mindest = int(w.get("mindest_kaeufer", 2))
    mindest_score = float(w.get("mindest_score", 60.0))
    kohorte = {}
    for k in kaeufe:
        if (k.get("score") is None or float(k["score"]) < mindest_score
                or (k.get("status") or "") == "dropped"):
            continue
        kohorte.setdefault(k["mint"], set()).add(k["wallet"])
    trigger_mints = {m for m, wl in kohorte.items() if len(wl) >= mindest}
    signal_k = nachlauf_messen(alle, trigger_ts=trigger_mints)

    print("Nachlauf-Messung robinhood_radar (T-268)")
    print("  Fuellungen in der Sammlung: %d, davon %d Kaeufe mit naechster "
          "Beobachtung" % (len(alle), len(alle_k)))
    print("  Signalfall (Kohorte >= %d bewertete Wallets): %d Token, %d Kaeufe "
          "mit naechster Beobachtung" % (mindest, len(trigger_mints),
                                         len(signal_k)))
    for name, werte in (("alle Kaeufe", [x["nachlauf_pct"] for x in alle_k]),
                        ("Signalfall", [x["nachlauf_pct"] for x in signal_k])):
        v = _verteilung(werte)
        if v is None:
            print("  %-12s keine Messwerte" % name)
            continue
        print("  %-12s n=%-3d min %+8.2f%%  p25 %+8.2f%%  Median %+8.2f%%  "
              "p75 %+8.2f%%  max %+8.2f%%  Schnitt %+8.2f%%"
              % (name, v["n"], v["min"], v["p25"], v["median"], v["p75"],
                 v["max"], v["schnitt"]))
    if alle_k:
        abst = _verteilung([x["abstand_s"] for x in alle_k])
        print("  Abstand Signal -> naechste Beobachtung: Median %.0f s, "
              "groesster %.0f s" % (abst["median"], abst["max"]))
    print("  Annahme in wachen.json: %.1f %% Nachlauf + %.2f %% Gebuehr je Seite"
          % (w.get("nachlauf_prozent", 2.0), w.get("gebuehr_taker", 0.01) * 100))
    print("  Die Gebuehr selbst ist in diesen Daten NICHT messbar (sie steckt "
          "im Poolpreis) - sie bleibt eine Annahme.")

    ordner = os.path.join(HIER, "daten")
    os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, "messung.json"), "w", encoding="utf-8") as f:
        json.dump({"zeit": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   "annahme_nachlauf_prozent": w.get("nachlauf_prozent", 2.0),
                   "annahme_gebuehr_taker": w.get("gebuehr_taker", 0.01),
                   "fuellungen": len(alle),
                   "verteilung_alle": _verteilung([x["nachlauf_pct"]
                                                    for x in alle_k]),
                   "verteilung_signal": _verteilung([x["nachlauf_pct"]
                                                      for x in signal_k]),
                   "werte_alle": alle_k, "werte_signal": signal_k},
                  f, indent=2, ensure_ascii=False)
    return 0


def _live_erlaubt() -> bool:
    w = json.loads((Path(HIER) / "wachen.json").read_text(encoding="utf-8"))
    return bool(w.get("handel_erlaubt")) and bool(
        (w.get("freigabe") or {}).get("erfuellt"))


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau", help="nur rechnen, nichts schreiben")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier", help="Papierbuch (Standard)")
    g.add_argument("--live", action="store_const", dest="modus", const="live",
                   help="verweigert: diese Spur hat keinen Live-Zweig")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen", help="nur den Wachenstand zeigen")
    g.add_argument("--messen", action="store_const", dest="modus",
                   const="messen",
                   help="Nachlauf der eigenen Sammlung messen (T-268)")
    g.add_argument("--raeumen", action="store_const", dest="modus", const="raeumen",
                   help="Positionen ohne frischen Kurs zeigen, nichts schreiben (T-299)")
    g.add_argument("--raeumen-anwenden", action="store_const", dest="modus",
                   const="raeumen_anwenden",
                   help="Positionen ohne frischen Kurs schliessen und buchen (T-299)")
    a = p.parse_args()
    modus = a.modus or "papier"
    if modus == "messen":
        return messen(json.loads((Path(HIER) / "wachen.json").read_text(
            encoding="utf-8")))
    if modus in ("raeumen", "raeumen_anwenden"):
        w = json.loads((Path(HIER) / "wachen.json").read_text(encoding="utf-8"))
        if modus == "raeumen":
            _, zustand_pfad, _ = spur_buch.pfade(HIER)
            z = spur_buch.lade_zustand(zustand_pfad)
            offen = z.get("positionen") or []
            if not offen:
                print("Buch leer - nichts zu raeumen.")
                return 0
            try:
                con = lesen.verbinde()
            except lesen.DatenbankFehlt as e:
                print("Radar-Datenbank nicht lesbar: %s" % e)
                return 1
            try:
                grenze = float(w.get("beobachtung_max_alter_stunden", 24.0))
                jetzt = time.time()
                print("Raeum-Vorschau (Grenze %.0f h):" % grenze)
                for p in offen:
                    preis, ts = lesen.letzte_beobachtung(con, p["inst"])
                    alter = (jetzt - ts) / 3600.0 if ts > 0 else None
                    alt = alter is None or alter > grenze
                    print("  %s  Einstieg %.8g  letzte Beobachtung %s  %s"
                          % (p["inst"], float(p["einstieg"]),
                             ("vor %.1f h" % alter) if alter is not None else "nie",
                             "-> WIRD GERAEUMT" if alt else "bleibt"))
            finally:
                con.close()
            print("Vorschau: keine Dateien geschrieben.")
            return 0
        geraeumt, _befund, fehler = raeume_ohne_kurs(w)
        for f in fehler:
            print("Uebersprungen (%s)" % f, file=sys.stderr)
        print("%d Position(en) geraeumt." % len(geraeumt))
        return 0 if geraeumt or not fehler else 1
    if modus == "live" and not _live_erlaubt():
        print("--live verweigert: handel_erlaubt ist false und freigabe.erfuellt "
              "ist nicht gesetzt - Handelsregeln Punkt 3 (scharf schalten von "
              "Hand). Diese Spur hat zusaetzlich keinen Orderaufruf.")
        modus = "papier"
    return spur_buch.zyklus(HIER, quelle, signal, modus,
                            ereignis_name="handel/robinhood_radar",
                            datenlage=lambda: dict(_zyklus.get("ablehnung") or {}))


if __name__ == "__main__":
    raise SystemExit(main())