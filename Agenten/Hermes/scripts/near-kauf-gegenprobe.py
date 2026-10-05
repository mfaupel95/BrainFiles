"""Ist der NEAR-Kauf von 02:51 eine echte Order oder ein Buch-Eintrag?

GEMESSEN um 02:51:04 UTC, drei Minuten nach der Buchbereinigung:
  live eroeffnen NEAR-USDC @4.9556, nominal 302.2916, stop 4.2856,
  ziel 5.592, grund=prognose-treffer-live

Das ist die erste NEAR-Position der Spur. Die Frage ist nicht, ob sie im
Buch steht - sie steht, das Buch wird ja geschrieben. Die Frage ist, ob
sie an der BOERSE steht. Genau daran scheiterten schon dreimal Positionen
dieses Hauses (xperp 21.09., scanner 21.09., ZRO 02.10.).

Drei Belege, unabhaengig voneinander:
  1. offene Positionen der Boerse je Symbol
  2. Margin: ist fuer die 302 USD Nennwert etwas gebunden?
  3. offene Algo-/Stop-Auftrage - ein Long ohne Schutz ist die groesste
     offene Luecke, die es im Haus gibt
"""
import importlib.util
import json
import os
import sys

HANDEL = r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel"
SPUR = os.path.join(HANDEL, "omniquant")


def lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


kp = lade(os.path.join(SPUR, "kraken_perp.py"), "kp")
kp.lade_maerkte()
kp.setze_ableitung(True)

z = json.load(open(os.path.join(SPUR, "zustand.json"), encoding="utf-8"))
pos = z.get("positionen") or []
w = json.load(open(os.path.join(SPUR, "wachen.json"), encoding="utf-8"))

print("=== 1. Buch ===")
for p in pos:
    print("  %-12s modus=%-6s nominal=%.2f eintieg=%s stop=%s ziel=%s"
          % (p.get("inst"), p.get("modus") or "FEHLT",
             float(p.get("nominal") or p.get("einsatz_usd") or 0),
             p.get("einstieg"), p.get("stop"), p.get("ziel")))
print("  Zielboerse laut Wache: %s | Einsatz %.2f USD | Hebel %s"
      % (w.get("boerse"), w.get("live_einsatz_usd"), w.get("hebel")))

print("\n=== 2. Boerse: offene Positionen ===")
for p in pos:
    inst = p.get("inst")
    try:
        off = kp.offene_positionen(inst)
        n = len(off) if isinstance(off, (list, dict)) else 0
        print("  %-12s -> %d offene Position(en)" % (inst, n))
        if n and isinstance(off, dict):
            for sym, d in list(off.items())[:3]:
                print("       %s: size=%s unrealisedPnl=%s"
                      % (sym, d.get("size"), d.get("unrealisedPnl")))
    except Exception as e:                                   # noqa: BLE001
        print("  %-12s -> ABFRAGE FEHLGESCHLAGEN: %s" % (inst, str(e)[:80]))

print("\n=== 3. Margin ===")
frei = kp.guthaben_usd()
print("  freie Margin jetzt: %.2f USD" % frei)
print("  (vor der Bereinigung und vor diesem Kauf waren es 88.21 USD)")

print("\n=== 4. Schutzauftrag - die groesste offene Luecke ===")
for p in pos:
    inst = p.get("inst")
    stop = p.get("stop")
    if not stop:
        print("  %-12s OHNE Stop im Buch" % inst)
        continue
    try:
        algo = kp._kf()._roh("/editorder")   # nur lesend
        treffer = [a for a in (algo if isinstance(algo, list) else [])
                   if str(a.get("symbol", "")).upper().startswith("PF_")]
        print("  %-12s Stop %.6g | offene Algo-Auftraege an der Boerse: %d"
              % (inst, float(stop), len(treffer)))
        for a in treffer[:6]:
            print("       %-12s %s %s @ %s (size %s)"
                  % (a.get("symbol"), a.get("orderType", "?"),
                     a.get("side", "?"), a.get("stopPrice") or a.get("limitPrice"),
                     a.get("size")))
    except Exception as e:                                   # noqa: BLE001
        print("  %-12s Stop %.6g | Auftraege nicht lesbar: %s"
              % (inst, float(stop), str(e)[:70]))

print("\n=== 5. Fazit ===")
alle_offen = []
for p in pos:
    try:
        o = kp.offene_positionen(p.get("inst"))
        if isinstance(o, (list, dict)) and o:
            alle_offen.append(p.get("inst"))
    except Exception:                                        # noqa: BLE001
        pass
if len(alle_offen) == len(pos) and pos:
    print("  ALLE Buchpositionen stehen an der Boerse: %s" % ", ".join(alle_offen))
    print("  -> Der Einstieg war ECHT. Die Buchbereinigung hat den Platz")
    print("     freigemacht, danach hat die Spur gekauft.")
else:
    print("  NICHT alle Buchpositionen stehen an der Boerse.")
    print("  -> GEIST-KLASSE: im Buch ja, an der Boerse nein.")