"""Messen: wie breit ist der Kandidatenbestand je Quote-Kombination?

Rein lesend, keine Order, kein Schalter. Auftrag Max 05.10.2026:
"ja aber maerkte und werte erhoehen".

Die Frage, die vorher nur beantwortet wurde durch Raten: der Kandidaten-
bestand schrumpft, wenn man `maerkte` auf USDC allein stellt. Gemessen wird
jetzt, was jede Variante wirklich liefert - und ZUSAETZLICH, wie viele der
Kandidaten ueberhaupt an einem PF_-Markt haengen, denn die Order laeuft ja
ueber Kraken Futures, nicht ueber OKX Spot.

Genau das ist der Punkt, der beim blossen Umstellen von `maerkte`
untergeht: ein OKX-Spot-Paar ohne PF_-Gegenstueck ist als SIGNAL nutzbar
(der Kurs stimmt), aber nicht als ORDER.
"""
import importlib.util
import json
import os
import sys
import time

HANDEL = r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel"


def lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


kp = lade(os.path.join(HANDEL, "omniquant", "kraken_perp.py"), "kp")
okx = lade(os.path.join(HANDEL, "scanner", "okx.py"), "okx")

t0 = time.time()
try:
    n_pf = kp.lade_maerkte()
except Exception as e:                                        # noqa: BLE001
    print("MARKTLISTE NICHT LADBAR: %s" % e)
    sys.exit(2)
pf = kp.maerkte()
print("PF_-Maerkte (Kraken Futures, tradeable): %d  [%ds]" % (n_pf, time.time() - t0))

# Welche Basis traegt der Zielmarkt ueberhaupt?
basen_pf = set()
for s in pf:
    rumpf = s[3:]                     # PF_ abziehen
    if rumpf.endswith("USD"):
        basen_pf.add(rumpf[:-3])
print("Basen am Zielmarkt: %d\n" % len(basen_pf))

VOL = 3_000_000
VARIANTEN = [
    (["USDT", "USDC"], "heutige Fassung (beide)"),
    (["USDC"], "nur USDC - die enge Umstellung"),
    (["USDT"], "nur USDT"),
    (None, "ohne Quote-Filter (alles)"),
]

ergebnis = {}
for quote, name in VARIANTEN:
    t = time.time()
    paare = okx.alle_paare(quote=quote, min_volumen_usd=VOL)
    basis = []
    hat_pf = 0
    for inst, _umsatz in paare:
        b = inst.rsplit("-", 1)[0].upper()
        basis.append(b)
        # Gegenstueck am Zielmarkt: Basis oder die XBT-Schreibweise
        if b in basen_pf or ("XBT" if b == "BTC" else b) in basen_pf:
            hat_pf += 1
    ergebnis[name] = {
        "quote": quote, "paare": len(paare), "mit_pf_markt": hat_pf,
        "basen": sorted(set(basis)),
    }
    print("%-38s %3d Paare  davon mit PF_-Markt: %3d  [%ds]"
          % (name, len(paare), hat_pf, time.time() - t))

print("\n--- Welche Basis fehlt am Zielmarkt? (heutige Fassung) ---")
heute = set(ergebnis["heutige Fassung (beide)"]["basen"])
fehlend = sorted(b for b in heute if b not in basen_pf
                 and ("XBT" if b == "BTC" else b) not in basen_pf)
print("  %d von %d: %s" % (len(fehlend), len(heute), ", ".join(fehlend)))
if fehlend:
    print("  -> das sind Signale OHNE Orderweg: handelbar als Signal,")
    print("     aber nicht als Position. Sie zaehlen mit, wenn die Frage")
    print("     'welche Basis ist am Zielmarkt erreichbar' nicht gestellt wird.")

# Gegenprobe: die naechsten Wert-Plaetze. `werte` beschneidet die Liste nach
# Umsatz - die Frage ist, WO abgeschnitten wird, nicht OB.
t = time.time()
paare = okx.alle_paare(quote=["USDT", "USDC"], min_volumen_usd=VOL)
print("\n--- wo schneidet 'werte' zu? (Umsatz desc, %d Paare) ---" % len(paare))
print("%-6s %-16s %14s  %s" % ("#", "Paar", "Umsatz 24h", "PF_-Markt?"))
for i, (inst, umsatz) in enumerate(paare, 1):
    b = inst.rsplit("-", 1)[0].upper()
    hat = "ja" if (b in basen_pf or ("XBT" if b == "BTC" else b) in basen_pf) else "NEIN"
    if i <= 8 or i in (10, 15, 20, 25, 30, 40, 50) or (i > 50 and hat == "ja"):
        print("%-6d %-16s %14.0f  %s" % (i, inst, umsatz, hat))
    if i == 50:
        print("  ...")
print("  [%ds gesamt]" % (time.time() - t))

json.dump({k: {kk: vv for kk, vv in v.items() if kk != "basen"}
           for k, v in ergebnis.items()},
          open(os.path.join(HANDEL, "..", "Hermes", "logs",
                            "maerkte_messung.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nGespeichert: Agenten/Hermes/logs/maerkte_messung.json")