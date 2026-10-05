"""Warum stehen PAPIER-Positionen in einem LIVE-Buch?

Gemessen 05.10.2026: alle 9 Positionen in omniquant/zustand.json sind aus
`papier`-Einstiegen entstanden (28.09.-03.10.), 8 davon ohne `modus`-Feld
und ohne `einsatz_usd`. Das Zustandsfeld `modus` sagt seit dem 01.10.
`live` - die Spur wurde scharf geschaltet, aber die Papier-Positionen
blieben stehen.

Folge: `live_max_offene_positionen: 1` ist mit 9 Positionen weit
ueberzogen, und die Börse fuehrt NULL davon (gemessen 05.10. ueber
`/derivatives/api/v3/accounts/trade/v2/openpositions` je Symbol). Das Buch
ist also mit Positionen voll, die es nicht gibt - jeder Einstieg scheitert
am Platz, unabhaengig von jedem Signal.

Die Frage, die dieses Skript beantwortet: GIBT es in dieser Spur einen Weg,
solche Altlasten auszubuchen? `bueche_papier_altlasten_aus()` ist die
Hausfunktion - aber omniquant hat sie nicht (gemessen: kein Treffer in
omniquant/*.py).

Rein lesend. Kein Schreiben, keine Freigabe-Aenderung.
"""
import importlib.util
import inspect
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


from importlib.util import spec_from_file_location as sfl, module_from_spec  # noqa: E402

sp = sfl("handeln_oq", os.path.join(SPUR, "handeln.py"))
hd = module_from_spec(sp)
sp.loader.exec_module(hd)

lp = lade(os.path.join(SPUR, "live_perp.py"), "lp")

print("=== 1. Der Modus-Schalter: wo wird er gesetzt? ===")
for z in inspect.getsource(hd).splitlines():
    if "modus" in z and ("=" in z or "live" in z.lower()):
        s_ = z.strip()
        if s_.startswith("#") or len(s_) < 5:
            continue
        print("   %s" % s_[:110])

print("\n=== 2. Gibt es eine Buchbereinigung in dieser Spur? ===")
namen = [n for n in dir(hd) if "bereinig" in n.lower() or "altlast" in n.lower()]
namen += [n for n in dir(lp) if "bereinig" in n.lower() or "altlast" in n.lower()]
print("   in handeln.py/live_perp.py: %s" % (namen or "KEINE"))
for pfad in ("handeln.py", "live_perp.py", "kraken_perp.py"):
    t = open(os.path.join(SPUR, pfad), encoding="utf-8").read()
    hat = [z.strip() for z in t.splitlines()
           if "bueche_papier_altlasten" in z or "altlasten" in z.lower()]
    print("   %-16s %s" % (pfad, hat[:2] or "kein Treffer"))

print("\n=== 3. Wie zaehlt die Spur ihre Plaetze? ===")
zp = None
for z in inspect.getsource(hd).splitlines():
    if "max_offene_positionen" in z or "live_max_offene" in z:
        print("   %s" % z.strip()[:110])

print("\n=== 4. Gegenprobe: wie macht es die HAUSFUNktion? ===")
sp_buch = lade(os.path.join(HANDEL, "spur_buch.py"), "spur_buch")
fun = [n for n in dir(sp_buch) if "altlast" in n.lower() or "bereinig" in n.lower()]
print("   in Handel/spur_buch.py: %s" % (fun or "KEINE"))
if fun:
    f = getattr(sp_buch, fun[0])
    print("\n   %s(%s) - Signatur/Doc:" % (fun[0], ", ".join(
        p for p in inspect.signature(f).parameters)))
    doc = inspect.getdoc(f) or "(kein Docstring)"
    print("   " + doc.replace("\n", "\n   ")[:900])

print("\n=== 5. Was heisst das fuer den Auftrag 'NEAR freigeben'? ===")
w = json.load(open(os.path.join(SPUR, "wachen.json"), encoding="utf-8"))
z = json.load(open(os.path.join(SPUR, "zustand.json"), encoding="utf-8"))
print("   Freigabe live_pf_ableitung: %s (erteilt 01.10.2026)"
      % w.get("live_pf_ableitung"))
print("   Buch: %d Positionen, Platz-Tor %s, davon an der Boerse: 0"
      % (len(z.get("positionen") or []), w.get("live_max_offene_positionen")))
print("   -> Die Freigabe ist erteilt. Der Einstieg scheitert an 9")
print("      Buchpositionen, von denen keine existiert. Beides ist")
print("      getrennt zu loesen, und die Reihenfolge ist nicht frei:")