#!/usr/bin/env python
"""Risiko-Beitrag-Wache: meldet, wenn sich das Risiko des Hauses bewegt.

Auftrag Max 03.10.2026: "Ja risiko beitrag wache machen".

WAS GEMELDET WIRD, UND WAS NICHT
--------------------------------
Gemeldet wird eine VERAENDERUNG, nicht der Stand: der Bericht enthaelt
sonst jeden Tag dieselbe Zahl, und eine Wache, die bei jedem Lauf dasselbe
sagt, wird abgeschaltet und damit blind.

Gemeldet werden:
  * eine Basis, die 25 % des Kapitals traegt (heute: BTC mit 2.958 USD in
    20 Spuren - das ist keine Buendelung von Fuenf Spuren, das ist EINE
    Wette, die siebzehnmal gefuehrt wird),
  * jede Position OHNE Schutz-Stop (T-123/T-273: das ist das eigentliche
    Risiko im Haus, nicht eine Rundenzahl),
  * eine Spur ueber ihrem eigenen Deckel,
  * der Gesamtzustand, wenn er sich um mehr als 10 % bewegt hat.

NICHT gemeldet wird: welcher Spuren es gehoert. Diese Wache zaehlt, sie
bewertet nicht.
"""
import importlib.util
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
MERK = os.path.join(HIER, "..", "cache", "risiko-wache.json")
KERN = os.path.join(WURZEL, "Agenten", "Handel", "risiko_beitrag.py")

ANTEIL_MELDEN = 20.0        # Prozent des Kapitals auf eine Basis
# 25 % war geraten und verfehlte BTC mit 24,4 %. Der Wert ist jetzt eine
# Schwelle UND es kommen immer die drei groessten Basen: die Frage
# "auf was liegt das meiste Geld" faellt auch dann an, wenn die Antwort
# knapp unter der Schwelle liegt.
BEWEGUNG_MELDEN = 10.0      # Prozent Veraenderung der Gesamtsumme

spec = importlib.util.spec_from_file_location("risiko_beitrag", KERN)
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)


def lage():
    """Die Zahlen, aus denen die Meldung entsteht - kein Fliesstext."""
    daten, gesamt = rb.ermittle()
    nach_basis = {}
    ohne_stop = []
    for d in daten:
        for p in d["positionen"]:
            b = rb.basisform(p["inst"])
            e = nach_basis.setdefault(b, {"nominal": 0.0, "risiko": 0.0,
                                          "n": 0, "spuren": set()})
            e["nominal"] += p["nominal"]
            e["risiko"] += p["risiko"]
            e["n"] += 1
            e["spuren"].add(d["spur"])
            if p["marke"]:
                ohne_stop.append((d["spur"], p["inst"]))
    ueber_deckel = [(d["spur"], d["risiko"], d["deckel"]) for d in daten
                    if d["deckel"] and d["risiko"] > d["deckel"]]
    return {"gesamt": gesamt, "positionen": sum(len(d["positionen"])
                                                for d in daten),
            "basen": {k: {"nominal": v["nominal"], "n": v["n"],
                          "spuren": sorted(v["spuren"])}
                      for k, v in nach_basis.items()},
            # Als STRINGS, nicht als Tupel: json schreibt Tupel als Listen
            # und laesst sie als Listen zurueckkommen - der Vergleich "%s|%s"
            # passte dann nie, und die Meldung kam bei JEDEM Lauf
            # wieder. Genau das schaltet eine Wache ab.
            "ohne_stop": sorted("%s|%s" % x for x in set(ohne_stop)),
            "ueber_deckel": ueber_deckel}


def main():
    lage_jetzt = lage()
    try:
        with open(MERK, encoding="utf-8") as fh:
            alt = json.load(fh)
    except (OSError, ValueError):
        alt = {}
    zeilen = []
    nominal_gesamt = sum(b["nominal"] for b in lage_jetzt["basen"].values()) or 1.0
    rang = sorted(lage_jetzt["basen"].items(),
                key=lambda kv: -kv[1]["nominal"])
    for platz, (basis, b) in enumerate(rang):
        anteil = b["nominal"] / nominal_gesamt * 100.0
        if anteil < ANTEIL_MELDEN and platz >= 3:
            continue
        alt_b = (alt.get("basen") or {}).get(basis)
        alt_anteil = ((alt_b or {}).get("nominal", 0) /
                       (sum(x["nominal"] for x in (alt.get("basen") or {}).values())
                        or 1.0) * 100.0)
        if alt_b and abs(anteil - alt_anteil) < 3.0:
            continue
        zeilen.append("Basis %s: %.2f USD in %d Positionen ueber %d Spuren "
                      "(%.1f %% des Kapitals, vorher %.1f %%)"
                      % (basis, b["nominal"], b["n"], len(b["spuren"]),
                         anteil, alt_anteil))
    alt_ohne = set(alt.get("ohne_stop") or [])
    for kennung in lage_jetzt["ohne_stop"]:
        if kennung in alt_ohne:
            continue
        spur, inst = kennung.split("|", 1)
        zeilen.append("OHNE SCHUTZ-STOP: %s haelt %s - das ist das eigentliche "
                      "Risiko, kein Rundenergebnis" % (spur, inst))
    alt_g = float(alt.get("gesamt") or 0)
    if alt_g and abs(lage_jetzt["gesamt"] - alt_g) / alt_g * 100.0 >= BEWEGUNG_MELDEN:
        zeilen.append("Gesamtrisiko %.2f USD, vorher %.2f USD (%+.1f %%)"
                      % (lage_jetzt["gesamt"], alt_g,
                         (lage_jetzt["gesamt"] - alt_g) / alt_g * 100.0))
    try:
        os.makedirs(os.path.dirname(MERK), exist_ok=True)
        with open(MERK, "w", encoding="utf-8") as fh:
            json.dump(lage_jetzt, fh, ensure_ascii=False, indent=1)
    except OSError:
        pass
    if not zeilen:
        return 0
    print("Risiko-Beitrag: %d Positionen, %.2f USD Gesamtrisiko"
          % (lage_jetzt["positionen"], lage_jetzt["gesamt"]))
    for z in zeilen:
        print("  - " + z)
    return 0


if __name__ == "__main__":
    sys.exit(main())
