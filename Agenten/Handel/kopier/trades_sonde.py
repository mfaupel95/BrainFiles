"""Sonde: was liefert trades/batch wirklich? (nur lesend, Wegwerfskript)

Warum: die Nachlauf-Messung (kopier.py --messen) ueberspringt Kandidaten
STILL, wenn kein Kauf gefunden wird. Diese Sonde zeigt die Rohantwort, damit
'kein Kauf' von 'falsch gelesen' zu unterscheiden ist.
"""
import json
import sys
import os

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel\kopier")
import lesen  # noqa: E402

w = json.load(open(os.path.join(HIER, "..", "kopier", "wachen.json"),
                   encoding="utf-8"))
z = json.load(open(os.path.join(HIER, "..", "kopier", "zustand.json"),
                   encoding="utf-8"))
verf = json.load(open(os.path.join(HIER, "..", "kopier", "verfolgte.json"),
                      encoding="utf-8"))
wallets = [x["wallet"] for x in verf["wallets"]]
print("verfolgte Wallets:", len(wallets))

# Ein paar Portfolios holen und die ersten Positionen zeigen
geprueft = 0
for wal in wallets[:3]:
    try:
        pf = lesen.portfolio(wal)
    except lesen.Lesefehler as e:
        print("  Portfolio %s: %s" % (wal[:10], e))
        continue
    pos = [p for p in pf["positions"].values()
           if not p["is_exited"] and not p["dust"] and not p["vermutlich_verloren"]]
    print("  %s: %d Positionen" % (wal[:10], len(pos)))
    for p in pos[:2]:
        mint = p["mint"]
        print("    Token %s (%s) preis=%s kap=%s" %
              (mint[:12], p["symbol"], p["preis"], p["marktkap_usd"]))
        try:
            roh = lesen.trade_batch(mint, [wal])
        except lesen.Lesefehler as e:
            print("      trade_batch FEHLER: %s" % e)
            continue
        print("      Antwort-Schluessel: %s" % list(roh.keys())[:3])
        trades = (roh or {}).get(wal) or []
        print("      Trades fuer diese Wallet: %d" % len(trades))
        for t in trades[:4]:
            print("        typ=%s preis=%s betrag=%s zeit=%s"
                  % (t.get("typ"), t.get("preis"), t.get("betrag_usd"),
                     t.get("zeit_ms")))
        geprueft += 1
        if geprueft >= 4:
            break
    if geprueft >= 4:
        break
print("fertig, %d Token geprueft" % geprueft)