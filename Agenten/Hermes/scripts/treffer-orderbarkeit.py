"""Sind die 2 Treffer der weiten Fassung ueberhaupt ORDERBAR?

Auftrag Max 05.10.2026: "maerkte und werte erhoehen". Nach der Ruecknahme der
Filter-Erweiterung liefert die weite Fassung 2 LONG-Kandidaten. Die Frage,
die die Breite ueberhaupt beantworten soll, ist nicht "wie viele Kandidaten
sehen wir", sondern "koennen wir einen davon kaufen".

Ein Signal ohne PF_-Markt ist eine Zeile im Journal und sonst nichts - das
ist die Klasse, die am 02.10. als Buch-Geist auffiel (T-319).
"""
import importlib.util
import json
import os
import sys

HANDEL = r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel"


def lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


kp = lade(os.path.join(HANDEL, "omniquant", "kraken_perp.py"), "kp")
n = kp.lade_maerkte()
print("PF_-Maerkte geladen: %d\n" % n)

for bericht in ("neuester.weit.json", "neuester.json"):
    p = os.path.join(HANDEL, "prognose_berichte", bericht)
    if not os.path.exists(p):
        print("%s fehlt" % bericht)
        continue
    d = json.load(open(p, encoding="utf-8"))
    tr = d.get("treffer") or []
    print("=== %s | erzeugt %s | geprueft %s Maerkte | %d Treffer ==="
          % (bericht, str(d.get("erzeugt"))[:16], d.get("maerkte_geprueft"), len(tr)))
    if not tr:
        print("  (keine Treffer - nichts zu pruefen)\n")
        continue
    for t in tr:
        inst = t.get("inst")
        richtung = t.get("richtung")
        score = t.get("score")
        print("  %-14s %-6s Score %-6s C/R %-5s" % (
            inst, richtung, score, t.get("cr")))
        try:
            sym = kp.pf_markt(inst)
            print("       -> PF_-Markt: %s   ORDER MÖGLICH" % sym)
        except Exception as e:                             # noqa: BLE001
            print("       -> %s" % str(e)[:96])
            print("          KEINE ORDER. Signal ja, Position nein.")
    print()

# Gegenprobe der Regel: die weite Fassung hat eigene Tore, strengere nicht.
print("=== Gegenprobe: ist 'weit' wirklich die weichere? ===")
for f in ("prognose.json", "prognose.weit.json"):
    k = json.load(open(os.path.join(HANDEL, f), encoding="utf-8"))
    t = k["tore"]
    print("  %-22s hoechst_rsi=%-5s mindest_cr=%-5s ruecksetzer_bis=%-5s mindest_score=%s"
          % (f, t.get("hoechst_rsi"), t.get("mindest_cr"),
             t.get("ruecksetzer_bis_pct"), t.get("mindest_score")))
print("  -> mehr Kandidaten bei WEICHEN Toren. Das ist der ganze Unterschied,")
print("     nicht die Quote-Filter-Breite.")