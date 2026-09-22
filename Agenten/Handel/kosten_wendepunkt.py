#!/usr/bin/env python3
"""Wie viel Gebuehr traegt eine Spur? - die Kosten-Wendepunkte aller Spuren.

WARUM: Mehrere Papier-Spuren sind nur wegen der Kraken-Pro-Gebuehr von 0 %
positiv (orbk ist die auffaelligste: die Runden sind rund 0,5 % breit). Faellt
das Abo weg, kommt die Gebuehr zurueck und die Spuren kippen - bisher stand das
nur als Merksatz in den Handelsregeln, nicht als Zahl je Spur.

Die Rechnung ist eine Zeile:  EV = p*(C - f) - (1-p)*(R + f)
                              =>  f_max = p*C - (1-p)*R
Darin sind R der mittlere Risikoabstand (Einstieg -> Stop), C der mittlere
Chancenabstand (Einstieg -> Ziel), p die gemessene Trefferquote und f die
Gebuehr je Runde (Kauf + Verkauf, in Prozent des Einsatzes). f_max ist die
Gebuehr, ab der die Spur bei UNSERER gemessenen Trefferquote nur noch die
Nullinie trifft.

WAS ES NICHT TUT: keine Prognose, keine Strategie. Es rechnet die eigene
Vergangenheit der Spur nach - und nur Spuren, deren Journal Stop und Ziel
mitschreibt.

Aufruf (aus dem Handel-Ordner):
    python kosten_wendepunkt.py
    python kosten_wendepunkt.py --spuren orbk,gitter,moondev_topmovers
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stoerungen  # gleicher Ordner: Zwangsschluesse sind keine Runden

HIER = Path(__file__).resolve().parent

EINSTIEG = ("kauf", "eroeffnen", "KAUF", "EINSTIEG", "buy")
AUSSTIEG = ("verkauf", "schliessen", "AUSSTIEG", "sell", "exit")


def _zahl(r, *namen):
    for n in namen:
        v = r.get(n)
        if v not in (None, ""):
            try:
                return float(v)
            except ValueError:
                continue
    return None


def runden_aus_journal(pfad: Path):
    """((R, C, ergebnis_prozent), zwangsschluesse) - aus beiden Journalformen.

    Form A (orbk): eine Zeile je FERTIGER Runde mit einstieg/stop/ziel/ausgang.
    Form B (Spuren mit spur_buch): je Einstieg eine Zeile mit stop/ziel, je
    Ausstieg eine Zeile mit preis - gepaart wird je Instrument.
    """
    if not pfad.is_file():
        return [], []
    with pfad.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return [], []
    felder = set(rows[0])
    if {"einstieg", "stop", "ziel", "ausgang"} <= felder:
        raus = []
        for r in rows:
            e = _zahl(r, "einstieg")
            s = _zahl(r, "stop")
            z = _zahl(r, "ziel")
            if not e or not s or not z:
                continue
            ergebnis = ((_zahl(r, "ausstieg") or e) / e - 1) * 100
            raus.append((abs(e - s) / e * 100, abs(z - e) / e * 100, ergebnis))
        return raus, []

    # Form B: paaren
    offen, raus, zwang = {}, [], []
    for r in rows:
        akt = (r.get("aktion") or "").strip()
        inst = (r.get("inst") or r.get("symbol") or "").strip()
        preis = _zahl(r, "preis")
        if not inst or not preis:
            continue
        if akt in EINSTIEG:
            s, z = _zahl(r, "stop"), _zahl(r, "ziel")
            if s is None and r.get("stop_pct"):
                s = preis * (1 - float(r["stop_pct"]) / 100)
            if s and z:
                offen[inst] = (preis, s, z)
        elif akt in AUSSTIEG and inst in offen:
            e, s, z = offen.pop(inst)
            # ZWANGSSCHLUESSE ZAEHLEN NICHT MIT: ein Ausstieg mit "herzschlag"
            # im Grund ist keine Handelsentscheidung, sondern die Folge eines
            # Ausfalls. Sie sitzen meist im Verlust - wer sie mitzaehlt, macht
            # die Trefferquote kuenstlich schlecht (gemessen am 21.09.2026:
            # omniquant stand mit 8 solcher Zeilen als "25 % Treffer, nicht
            # tragfaehig" in der Tabelle, obwohl ALLE acht Zwangsschluesse der
            # Ausfaelle vom 16./17.09. waren).
            if stoerungen.ist_stoerung(r.get("grund")):
                zwang.append((inst, (r.get("grund") or "").strip()))
                continue
            raus.append((abs(e - s) / e * 100, abs(z - e) / e * 100,
                         (preis / e - 1) * 100))
    return raus, zwang


def wendepunkt(runden):
    if not runden:
        return None
    R = statistics.fmean(r[0] for r in runden)
    C = statistics.fmean(r[1] for r in runden)
    p = len([r for r in runden if r[2] > 0]) / len(runden)
    f_max = p * C - (1 - p) * R          # in Prozent des Einsatzes je Runde
    ev_ohne = p * C - (1 - p) * R
    return {"runden": len(runden), "R": R, "C": C, "p": p,
            "f_max": f_max, "ev_ohne": ev_ohne,
            "ergebnis_summe": sum(r[2] for r in runden)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spuren", help="Komma-Liste; sonst alle mit Journal")
    a = ap.parse_args()
    # Je JOURNAL eine Zeile, nicht je Ordner: ein Ordner kann mehrere Buecher
    # fuehren (Basis/Mittel, knapp/weit, futures). Ein Sammel-glob ueber
    # handelsjournal*.csv zaehlt sonst dasselbe Buch mehrfach - und die
    # umskalierten Altbestaende (".falsch-skaliert-*") gehoeren nie in eine
    # Kennzahl.
    dateien = []
    for s in sorted(HIER.glob("*/handelsjournal*.csv")):
        if "falsch" in s.name or ".bak-" in s.name:
            continue
        if a.spuren and s.parent.name not in [x.strip() for x in a.spuren.split(",")]:
            continue
        teil = s.name.replace("handelsjournal", "").replace(".csv", "")
        dateien.append((s.parent.name + teil.replace(".", "/"), s))
    if not dateien and a.spuren:
        print("keine Journale zu: %s" % a.spuren)
        return 2

    print("%-22s %6s %6s %6s %6s   %s" % (
        "Spur", "Runden", "R %", "C %", "Treffer", "Gebuehr, ab der die Spur kippt"))
    zeilen = []
    for name, pfad in dateien:
        runden, zwang = runden_aus_journal(pfad)
        w = wendepunkt(runden)
        if not w:
            print("%-22s %6s   -      -      -      keine messbare Runde" % (name, 0))
            continue
        wachen = pfad.parent / "wachen.json"
        geb = None
        if wachen.is_file():
            d = json.loads(wachen.read_text(encoding="utf-8"))
            geb = d.get("gebuehr_taker")
        hinweis = ""
        if w["f_max"] <= 0:
            hinweis = "  <<< schon bei 0 % Gebuehr nicht tragfaehig"
        elif w["f_max"] < 0.4:
            # 0,4 % sind die Taker-Gebuehr beider Seiten ohne Abo - wer darunter
            # liegt, handelt nur, solange die Gebuehr 0 ist.
            hinweis = "  <<< haengt an der Gebuehrfreiheit (unter 0,4 %)"
        if geb is not None and geb > 0 and geb >= w["f_max"]:
            hinweis += " UND die gesetzte Gebuehr %.3f %% liegt darueber" % geb
        zahl = ("  (%d Zwangsschluss-Zeile(n) nicht mitgezaehlt)" % len(zwang)
                if zwang else "")
        print("%-22s %6d %6.2f %6.2f %5.0f%%   %+.2f %% je Runde%s%s" % (
            name, w["runden"], w["R"], w["C"], w["p"] * 100, w["f_max"], hinweis, zahl))
        zeilen.append((name, w))

    print("\nLesart: f_max ist die Gebuehr JE RUNDE (Kauf+Verkauf) in Prozent des "
          "Einsatzes,\nbei der die gemessene Trefferquote nur noch die Nullinie "
          "trifft. Kraken-Pro: 0 %;\nohne Abo 0,4 % (Taker 0,2 % je Seite). "
          "Spuren mit f_max unter 0,4 %\nhaengen an der Gebuehrfreiheit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
