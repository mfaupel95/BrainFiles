#!/usr/bin/env python3
"""Robinhood-Radar (robinhood_radar): bewerteten Wallets auf Robinhood Chain nachkaufen.

AUFTRAG Max 22.09.2026: "Radar -papierspur und -bot".

WAS HIER GEMESSEN WIRD
----------------------
Der FOMO-Robinhood-Radar (`Werkstatt/Repos/fomo-robinhood-radar`) liest die
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
            finally:
                con.close()
    except Exception as e:                                          # noqa: BLE001
        return {}, {}, ["Radar-Datenbank nicht lesbar (%s)" % e]

    daten, kurse = _kennzahlen(w, time.time())
    return daten, kurse, fehler


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
    a = p.parse_args()
    modus = a.modus or "papier"
    if modus == "live" and not _live_erlaubt():
        print("--live verweigert: handel_erlaubt ist false und freigabe.erfuellt "
              "ist nicht gesetzt - Handelsregeln Punkt 3 (scharf schalten von "
              "Hand). Diese Spur hat zusaetzlich keinen Orderaufruf.")
        modus = "papier"
    return spur_buch.zyklus(HIER, quelle, signal, modus,
                            ereignis_name="handel/robinhood_radar")


if __name__ == "__main__":
    raise SystemExit(main())