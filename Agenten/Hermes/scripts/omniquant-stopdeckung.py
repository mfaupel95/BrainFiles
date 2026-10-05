"""Stop-Deckung an der BOERSE pruefen - und die Position selbst (05.10.2026).

Zwei Fragen, die vorher niemand stellen konnte, weil der Weg fehlte:
  1. Ist der Schutz-Stop an der Boerse? (`/openorders`, nicht `/editorder`)
  2. Deckt er die GESAMTE Position? (T-323: 145 Kontrakte, Stop ueber
     126, 19 ungeschuetzt - ohne Mengenvergleich sieht das niemand)

Rein lesend. Keine Order, kein Storno, kein Schalter.
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

print("=== 1. Die Position im Buch ===")
for p in pos:
    print("  %-12s modus=%-6s Kontrakte=%-5s Einstieg=%-10s Stop=%-10s Ziel=%s"
          % (p.get("inst"), p.get("modus") or "FEHLT", p.get("kontrakte"),
             p.get("einstieg"), p.get("stop"), p.get("ziel")))
if not pos:
    print("  (Buch leer)")

print("\n=== 2. Was die BOERSE fuehrt ===")
for p in pos:
    inst = p.get("inst")
    try:
        off = kp.offene_positionen(inst)
        for q in (off or []):
            print("  %-12s size=%-8s side=%-6s entryPrice=%-10s unrealisedPnl=%s"
                  % (q.get("symbol"), q.get("size"), q.get("side"),
                     q.get("entryPrice"), q.get("unrealisedPnl")))
    except Exception as e:                                    # noqa: BLE001
        print("  %-12s Position nicht lesbar: %s" % (inst, str(e)[:60]))

print("\n=== 3. Offene Auftraege (/openorders) ===")
for p in pos:
    inst = p.get("inst")
    try:
        orders = kp.offene_auftraege(inst)
    except Exception as e:                                    # noqa: BLE001
        print("  %-12s nicht lesbar: %s" % (inst, str(e)[:60]))
        continue
    print("  %s: %d offene Auftraege" % (inst, len(orders or [])))
    for o in (orders or []):
        print("     %-12s %-11s %-5s size=%-7s stop=%-10s reduceOnly=%s"
              % (o.get("symbol"), o.get("orderType"), o.get("side"),
                 o.get("unfilledSize") or o.get("size"),
                 o.get("stopPrice"), o.get("reduceOnly")))

print("\n=== 4. Deckt der Stop die Position? ===")
for p in pos:
    inst = p.get("inst")
    k = p.get("kontrakte")
    stark = kp.schutzstop_vorhanden(inst, kontrakte=k)
    schwach = kp.schutzstop_vorhanden(inst, kontrakte=None)
    print("  %-12s Kontrakte=%-5s | mit Mengenvergleich: %-5s | ohne: %s"
          % (inst, k, stark, schwach))
    if schwach and not stark:
        print("     -> WARNUNG: ein Stop liegt an, deckt aber NICHT die")
        print("        ganze Position. Genau der Befund aus T-323.")
    if not schwach:
        print("     -> KEIN SCHUTZ an der Boerse. Das ist der Befund,")
        print("        der xperp (21.09.), scanner (21.09.) und ZRO")
        print("        (02.10.) zu Geistern gemacht hat.")

print("\n=== 5. Gegenprobe: sieht die Funktion ueberhaupt etwas? ===")
# Ein Symbol OHNE Position und OHNE Order muss "nein" sagen - sonst waere
# die Funktion immer wahr und damit nutzlos.
try:
    leere = kp.schutzstop_vorhanden("STRK-USDT", kontrakte=1)
    print("  STRK-USDT (keine Position): %s" % leere)
    print("  -> %s" % ("die Funktion unterscheidet" if leere is False
                        else "FEHLER: sie sagt immer ja"))
except Exception as e:                                       # noqa: BLE001
    print("  STRK-USDT: %s" % str(e)[:60])