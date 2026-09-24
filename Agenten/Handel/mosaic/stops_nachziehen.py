"""Stop-Kennungen der mosaicschen Positionen im Buch nachziehen (24.09.2026).

BEFUND (gemessen am 24.09.2026): mosaics Buch fuehrte drei LIVE-Positionen
(BTC-USDC, ETH-USDC, SOL-USDC), aber nur die juengste trug `boerse` - und
KEINE trug `stop_txid`. An der Boerse lagen die Schutz-Stops sehr wohl
(XBTEUR 71940,1 · ETHEUR 2240,10 · SOLEUR 98,84), die Spur konnte sie aber
nicht adressieren: kein Storno, kein Ersatz, und ein Waisen-Stop faellt
niemandem auf. Der scanner hatte aus derselben Ursache 23 Kopien desselben
Stops im Zustand.

Dieses Werkzeug liest die offenen Orders bei Kraken und traegt je Position die
Kennung des passenden Stop-Loss ein (Paar ueber kraken_spot.PAARE, Menge mit
Toleranz). Es stellt KEINE Order und storniert nichts.

Aufruf aus dem mosaic-Ordner:
    ../scanner/.venv/Scripts/python.exe stops_nachziehen.py
    ../scanner/.venv/Scripts/python.exe stops_nachziehen.py --anwenden
"""

import argparse
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, os.path.join(HANDEL, "scanner"))

import wachen_pruefung as wp                                       # noqa: E402

ZUSTAND = os.path.join(HIER, "zustand.json")
WACHEN = os.path.join(HIER, "wachen.json")
TOLERANZ = 0.01          # 1 % Mengentoleranz - Boersen runden


def _lade(name, pfad):
    schluessel = "%s@%s" % (name, os.path.abspath(pfad))
    if schluessel in sys.modules:
        return sys.modules[schluessel]
    spec = importlib.util.spec_from_file_location(schluessel, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[schluessel] = modul
    spec.loader.exec_module(modul)
    return modul


kraken_spot = _lade("kraken_spot", os.path.join(HIER, "kraken_spot.py"))
kraken = _lade("kraken", os.path.join(HANDEL, "kraken", "kraken.py"))


# Kraken nennt dasselbe Paar in zwei Schreibweisen: die Order-Anfrage nimmt
# XXBTZEUR/XETHZEUR, die offene Order traegt in `descr.pair` die kurze Form
# XBTEUR/ETHEUR. Ein Vergleich der rohen Zeichenketten findet deshalb nichts
# (gemessen 24.09.2026: BTC und ETH fielen durch, nur SOLEUR passte). Beide
# Seiten werden auf (Basis, Quote) zurueckgefuehrt.
ALIAS = {"XXBT": "BTC", "XBT": "BTC", "XETH": "ETH", "XDG": "DOGE",
         "ZEUR": "EUR", "ZUSD": "USD", "ZGBP": "GBP", "ZJPY": "JPY"}
QUOTEN = ("ZEUR", "ZUSD", "ZGBP", "ZJPY", "USDT", "USDC", "EUR", "USD",
          "GBP", "JPY", "BTC", "ETH")


def zerlege(paar):
    """'XXBTZEUR'/'XBTEUR' -> ('BTC', 'EUR'); unbekannt -> (None, None)."""
    p = (paar or "").upper().replace("/", "").strip()
    for quote in QUOTEN:
        if p.endswith(quote) and len(p) > len(quote):
            basis, q = p[:-len(quote)], quote
            break
    else:
        return None, None
    basis = ALIAS.get(basis, ALIAS.get(basis[1:], basis) if basis.startswith("X") else basis)
    return basis, ALIAS.get(q, q)


def passender_stop(pos, orders):
    """(txid, order) des Stop-Loss dieser Position - oder (None, None)."""
    paar = kraken_spot.PAARE.get(pos.get("inst"))
    if not paar:
        return None, None
    soll = zerlege(paar)
    menge = float(pos.get("menge") or 0)
    for txid, o in orders.items():
        if zerlege(o.get("paar")) != soll:
            continue
        if "stop" not in (o.get("art") or "").lower():
            continue
        try:
            om = float(o.get("menge") or 0)
        except ValueError:
            continue
        if menge and abs(om - menge) > max(TOLERANZ * menge, 1e-12):
            continue
        return txid, o
    return None, None


def main():
    p = argparse.ArgumentParser(description="Stop-Kennungen ins mosaic-Buch ziehen")
    p.add_argument("--anwenden", action="store_true", help="wirklich schreiben")
    a = p.parse_args()

    with open(WACHEN, encoding="utf-8") as f:
        w = json.load(f)
    with open(ZUSTAND, encoding="utf-8") as f:
        z = json.load(f)

    orders = kraken.offene_orders()
    print("Kraken: %d offene Order(s)" % len(orders))
    for txid, o in orders.items():
        print("  %s  %-10s %-6s %-10s menge %-14s preis %s"
              % (txid[:20], o.get("paar"), o.get("seite"), o.get("art"),
                 o.get("menge"), o.get("preis")))

    offen = [q for q in z.get("positionen", []) if q.get("modus") == "live"]
    print("\nBuch: %d Live-Position(en)" % len(offen))
    fehlten = 0
    for pos in offen:
        hat = pos.get("stop_txid")
        txid, o = passender_stop(pos, orders)
        if hat and txid == hat:
            print("  %-10s hat die Kennung schon (%s)" % (pos["inst"], hat[:20]))
            continue
        if txid is None:
            print("  %-10s KEIN passender Stop an der Boerse gefunden (Menge %s, "
                  "Paar %s) - nichts eingetragen"
                  % (pos["inst"], pos.get("menge"), kraken_spot.PAARE.get(pos["inst"])))
            continue
        fehlten += 1
        print("  %-10s -> %s (Stop %s, Menge %s)  boerse=kraken"
              % (pos["inst"], txid[:20], o.get("preis"), o.get("menge")))
        if a.anwenden:
            pos["stop_txid"] = txid
            pos["boerse"] = "kraken"
            pos["boersen_stop_fehlt"] = False

    if not a.anwenden:
        print("\nVORSCHAU: %d Kennung(en) wuerden eingetragen. Kein Schreibzugriff, "
              "keine Order." % fehlten)
        return 0
    if not fehlten:
        print("\nNichts zu tun.")
        return 0

    bak = ZUSTAND + ".bak-%s" % datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(ZUSTAND, bak)
    with open(ZUSTAND, "w", encoding="utf-8", newline="\n") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([ZUSTAND], ziel)
    print("\n%d Kennung(en) eingetragen (Sicherung %s), Spiegelung: %s"
          % (fehlten, os.path.basename(bak), "ok" if ok else "FEHLER " + str(info)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())