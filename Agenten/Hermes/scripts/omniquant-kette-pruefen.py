"""Was macht die Spur mit den 2 NEAR-Signalen WIRKLICH?

Nachfrage, nicht Behauptung: `live_pf_ableitung` steht seit dem 01.10. auf
true. Trotzdem kam kein Einstieg. Es gibt also einen Grund, und der liegt
mit hoher Wahrscheinlichkeit NICHT am Freigabe-Tor.

Geprueft wird jede Sperre der Kette in der Reihenfolge, in der die Spur sie
nimmt - `live_perp.kaufe()` ist der einzige Ort, an dem diese Spur Geld
ausgibt. Jede Tuer wird einzeln geprueft und der Grund genannt.
"""
import importlib.util
import json
import os
import sys

HANDEL = r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel"
SPUR = os.path.join(HANDEL, "omniquant")
sys.path.insert(0, SPUR)
sys.path.insert(0, os.path.join(HANDEL, "scanner"))
sys.path.insert(0, os.path.join(HANDEL, "..", "Bus"))

from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402

s = spec_from_file_location("handeln_oq", os.path.join(SPUR, "handeln.py"))
hd = module_from_spec(s)
s.loader.exec_module(hd)

import kraken_perp as kp                                        # noqa: E402
import live_perp as lp                                          # noqa: E402

assert hd.__file__.startswith(SPUR), hd.__file__

w = hd.lade_wachen() or {}
print("=== 1. Wache, wie die Spur sie liest ===")
print("  prognose_fassung   = %s" % w.get("prognose_fassung"))
print("  bericht            = %s" % os.path.basename(hd.bericht_pfad(w)))
print("  live_pf_ableitung  = %s" % w.get("live_pf_ableitung"))
print("  handel_erlaubt     = %s" % w.get("handel_erlaubt"))
print("  freigabe.erfuellt  = %s" % (w.get("freigabe") or {}).get("erfuellt"))
print("  live_einsatz_usd   = %s" % w.get("live_einsatz_usd"))
print("  hebel              = %s" % w.get("hebel"))
print("  mindest_guthaben   = %s" % w.get("mindest_guthaben_usd"))

print("\n=== 2. Ist der Bericht frisch genug? (Tor: max_bericht_alter_stunden) ===")
import datetime
pfad = hd.bericht_pfad(w)
d = json.load(open(pfad, encoding="utf-8"))
erz = d.get("erzeugt")
print("  Bericht: %s" % os.path.basename(pfad))
print("  erzeugt: %s" % erz)
try:
    t = datetime.datetime.fromisoformat(str(erz))
    jetzt = datetime.datetime.now(t.tzinfo)
    alter_h = (jetzt - t).total_seconds() / 3600.0
    grenze = float(w.get("max_bericht_alter_stunden", 26))
    print("  Alter: %.1f h (Grenze %.0f h) -> %s"
          % (alter_h, grenze, "OK" if alter_h <= grenze else "ZU ALT - TOR ZU"))
except Exception as e:                                          # noqa: BLE001
    print("  Alter nicht lesbar: %s" % e)

print("\n=== 3. Die Kandidaten und ihr Weg zum Zielmarkt ===")
kp.lade_maerkte()
kp.setze_ableitung(bool(w.get("live_pf_ableitung")))
treffer = d.get("treffer") or []
print("  Treffer im Bericht: %d" % len(treffer))
for t_ in treffer:
    inst = t_.get("inst")
    print("\n  %s  Score %s  C/R %s  Richtung %s"
          % (inst, t_.get("score"), t_.get("cr"), t_.get("richtung")))
    try:
        sym = kp.pf_markt(inst)
        print("    Zielmarkt:  %s  (geprueft gegen /instruments)" % sym)
    except Exception as e:                                      # noqa: BLE001
        print("    Zielmarkt:  %s" % str(e)[:90])
        continue
    try:
        kurs = kp.letzter_kurs(inst)
        print("    Kurs:       %.6g USD" % kurs)
        g = lp.einsatz_und_grenzen(w)
        grund = kp.hebel_grund(inst, g["einsatz"], kurs, w)
        print("    Einsatz:    %.2f USD bei Hebel %s" % (g["einsatz"], w.get("hebel")))
        if grund:
            print("    HEBEL-TOR: %s" % grund)
        else:
            k = kp.kontrakte_fuer(inst, g["einsatz"], kurs, w)
            print("    Kontrakte:  %d  Nennwert %.2f USD  (Hebel ist %.2f)"
                  % (k, kp.nennwert_usd(inst, k, kurs),
                     kp.effektiver_hebel(inst, k, kurs, g["einsatz"])))
            print("    Einschuss:  %.2f USD (Marktplan EEA 10%%)"
                  % kp.einschuss_usd(inst, k, kurs))
    except Exception as e:                                      # noqa: BLE001
        print("    Rechnung:   %s" % str(e)[:90])

print("\n=== 4. Die Sperren der Kette, jede einzeln ===")
frei = kp.guthaben_usd()
print("  freie Margin:        %.2f USD (Tor: >= %.2f) -> %s"
      % (frei, float(w.get("mindest_guthaben_usd", 0)),
         "OK" if frei >= float(w.get("mindest_guthaben_usd", 0)) else "ZU WENIG"))
for feld in ("live_max_offene_positionen", "live_max_gesamt_usd",
             "max_neu_je_zyklus", "max_je_basiswert"):
    if feld in w:
        print("  %-24s %s" % (feld, w[feld]))
grund = lp.live_sperren(w, hd.lade_zustand() or {})
print("\n  live_sperren(): %s" % (grund if grund else "KEINE SPERRE"))