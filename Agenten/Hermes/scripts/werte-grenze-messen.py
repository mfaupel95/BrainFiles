"""Messen: wie faellt die Order-Trefferquote, wenn `werte` waechst?

Rein lesend. Auftrag Max 05.10.2026: "ja aber maerkte und werte erhoehen".

Die Frage, die vorher niemand gestellt hatte: `werte` beschneidet die
Marktliste NACH UMSATZ. Jede Verlaengerung dieser Liste nimmt auch
Basen auf, fuer die es am Zielmarkt (Kraken Futures) keinen PF_-Markt
gibt. Ein solches Instrument ist als SIGNAL vollwertig - der Kurs stimmt -
aber als ORDER nicht ausfuehrbar.

Also: wo faellt die Quote der ausfuehrbaren Kandidaten ab? Genau dort ist
die sinnvolle Grenze, und sie ist eine Zahl, kein Wunsch.
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
okx = lade(os.path.join(HANDEL, "scanner", "okx.py"), "okx")
kp.lade_maerkte()

VOL = 3_000_000
MAXWERT = 3000                      # --werte kann nicht groesser werden
paare = okx.alle_paare(quote=None, min_volumen_usd=VOL)
print("Alle Spot-Paare ueber %g USD Umsatz: %d" % (VOL, len(paare)))
print("(MAXWERT=%d, darueber kann --werte ohnehin nicht gehen)\n" % MAXWERT)


def ausfuehrbar(inst):
    """Kann die ORDER raus?  pf_markt ist die eine Wahrheit des Orderwegs."""
    try:
        kp.pf_markt(inst, fuer_ausstieg=True)
        return True, ""
    except Exception as e:                                # noqa: BLE001
        return False, str(e)


# Kumulativ: von Platz 1 bis n - wie viele davon kann die Spur wirklich ordern?
zeilen = []
kumulativ_ja = 0
stufen = [5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 150, 200, 300, 500,
          MAXWERT]
for i, (inst, umsatz) in enumerate(paare, 1):
    ja, grund = ausfuehrbar(inst)
    kumulativ_ja += 1 if ja else 0
    if i in stufen or (ja is False and not zeilen):
        zeilen.append((i, kumulativ_ja, kumulativ_ja / i * 100.0, inst, grund))

print("%-6s %-9s %-10s %s" % ("wert", "orderbar", "Quote", "letzter Nicht-Orderbar"))
print("-" * 78)
for i, k, q, inst, _g in zeilen:
    marke = "  <- ab hier faellt es" if 0 < q < 100 and i >= 10 else ""
    print("%-6d %-9d %-9.1f%% %-12s%s" % (i, k, q, inst, marke))

# Wo genau liegen die Luecken?
print("\n--- Alle nicht ausfuehrbaren Kandidaten (Begruende) ---")
gruende = {}
for inst, _u in paare:
    ja, grund = ausfuehrbar(inst)
    if ja:
        continue
    kurz = ("kein PF_-Markt" if "gibt es am Zielmarkt nicht" in grund
            else "kein Markt (gemessen)" if "keinen Markt" in grund
            else grund[:60])
    gruende.setdefault(kurz, []).append(inst)
for g, liste in sorted(gruende.items(), key=lambda kv: -len(kv[1])):
    print("  %-46s %2d  %s" % (g[:46], len(liste), ", ".join(sorted(liste)[:8])))

# Die entscheidende Zahl: ab welchem `werte` bringt jeder weitere Platz
# ueberhaupt noch etwas ein?
print("\n--- Grenze: bringt der naechste Platz noch einen Order-Kandidaten? ---")
letzter_ja = 0
letzter_nein = 0
for i, (inst, _u) in enumerate(paare, 1):
    ja, _g = ausfuehrbar(inst)
    if ja:
        letzter_ja = i
    else:
        letzter_nein = max(letzter_nein, i)
print("  letzter ausfuehrbare Kandidat:   Platz %d" % letzter_ja)
print("  letzter NICHT ausfuehrbarer:    Platz %d" % letzter_nein)
print("  -> sinnvoller Wertbereich: 1..%d" % letzter_ja)

json.dump({"paare": len(paare), "orderbar": letzter_ja,
           "quote_ende": letzter_ja / len(paare) * 100.0,
           "nicht_ausfuehrbar": {g: sorted(v) for g, v in gruende.items()}},
          open(os.path.join(HANDEL, "..", "Hermes", "logs",
                            "werte_messung.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nGespeichert: Agenten/Hermes/logs/werte_messung.json")