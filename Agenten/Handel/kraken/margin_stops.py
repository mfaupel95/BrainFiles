"""Kraken-MARGIN-Positionen mit einem Stop-Loss absichern.

Auftrag Max 24.09.2026: "Sui Zec und near auf kraken ebenfalls absichern".
Gesucht und gefunden wurden sie NICHT im Spot-Guthaben (dort liegen sie nicht),
sondern als offene MARGIN-Positionen (`OpenPositions`): 6x SUIEUR, 1x NEAREUR,
1x XZECZUSD (dazu ein Staubrest von 0,00000023 NEAR).

Warum das nicht dasselbe ist wie bei einer Spot-Position:
* Eine Margin-Position gehoert nicht zur Brieftasche - ein gewoehnlicher
  Verkaufsstop scheitert an "Insufficient funds".
* Der Stop muss die Position SCHLIESSEN. Kraken nimmt dafuer
  `close[ordertxid]=<ordertxid der Position>`; die Order haengt dann an genau
  dieser Position ("close position @ stop loss ..."). Wird die Position von Hand
  geschlossen, verschwindet der Stop mit ihr - ohne die Verknuepfung bliebe ein
  nackter Verkaufsstop stehen, der bei fehlender Position einen SHORT aufmacht.
* Die Menge muss die der Position sein (nie mehr - sonst dreht der Rest short).

Stop = Einstieg der Position (cost/vol) minus 7,5 %, gerundet auf die Stellen
des Paares. Liegt der so errechnete Preis NICHT unter dem Markt, wird die
Position uebersprungen und gemeldet: ein Stop ueber dem Markt waere ein
sofortiger Verkauf, keine Absicherung.

Aufruf aus Agenten/Handel:
    scanner/.venv/Scripts/python.exe kraken/margin_stops.py              # Vorschau
    scanner/.venv/Scripts/python.exe kraken/margin_stops.py --anwenden
"""

import argparse
import importlib.util
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, os.path.join(HANDEL, "scanner"))   # fuer die Kurswege

ZIEL_PROZENT = 7.5


def _lade(name, pfad):
    schluessel = "%s@%s" % (name, os.path.abspath(pfad))
    if schluessel in sys.modules:
        return sys.modules[schluessel]
    spec = importlib.util.spec_from_file_location(schluessel, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[schluessel] = m
    spec.loader.exec_module(m)
    return m


kraken = _lade("kraken", os.path.join(HIER, "kraken.py"))


def einstieg(position):
    """Einstiegspreis einer Margin-Position: cost / vol."""
    vol = float(position.get("vol") or 0)
    if vol <= 0:
        return None
    return float(position.get("cost") or 0) / vol


def stop_preis(einstiegspreis, kurs, prozent=ZIEL_PROZENT):
    """Stop unter dem Einstieg - und NIE ueber dem Markt.

    Rueckgabe (preis_oder_None, grund). Ein Stop ueber dem Markt loest sofort
    aus: das waere ein Verkauf zum Marktpreis, nicht eine Absicherung.
    """
    if not einstiegspreis or not kurs:
        return None, "kein Einstieg/Kurs"
    preis = einstiegspreis * (1 - prozent / 100.0)
    if preis >= kurs:
        return None, ("%.4f liegt nicht unter dem Markt (%.4f) - die Position "
                      "waere sofort verkauft" % (preis, kurs))
    return preis, None


def ist_staub(position, paarinfo):
    """Positionen unter der Mindestordergroesse kann Kraken nicht ordern."""
    vol = float(position.get("vol") or 0)
    ordermin = float((paarinfo or {}).get("ordermin") or 0)
    return vol < ordermin or vol <= 0


def hebel(paarinfo, seite="sell"):
    """Der hoechste von Kraken erlaubte Hebel des Paares.

    Fuer eine SCHLIESSENDE Order ist der Hebel nur Formsache - er darf aber
    nicht ueber dem Erlaubten liegen, sonst lehnt Kraken ab.
    """
    werte = (paarinfo or {}).get("leverage_%s" % seite) or []
    return max(werte) if werte else None


def plan(positionen, kurse, paarinfo, prozent=ZIEL_PROZENT):
    """Was zu tun ist - reine Rechnung, kein Netz, keine Order.

    Rueckgabe: Liste von dicts mit txid, paar, menge, einstieg, stop, hebel,
    hinweis (None = orderbar).
    """
    zeilen = []
    for tx, p in positionen.items():
        if str(p.get("posstatus") or "open") != "open":
            continue
        if float(p.get("vol") or 0) <= 0:
            continue
        paar = p.get("pair")
        info = paarinfo.get(paar) or {}
        e = einstieg(p)
        kurs = kurse.get(paar)
        s, grund = stop_preis(e, kurs, prozent)
        if ist_staub(p, info):
            grund = "Staub (%.10f < ordermin %s)" % (float(p["vol"]),
                                                     info.get("ordermin"))
        zeilen.append({
            "txid": tx,
            "ordertxid": p.get("ordertxid"),
            "paar": paar,
            "menge": float(p.get("vol") or 0),
            "einstieg": e,
            "kurs": kurs,
            "stop": s,
            "hebel": hebel(info),
            "hinweis": grund,
        })
    return zeilen


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--anwenden", action="store_true",
                   help="wirklich ordern (sonst nur rechnen)")
    p.add_argument("--prozent", type=float, default=ZIEL_PROZENT,
                   help="Abstand unter dem Einstieg (Standard 7,5)")
    a = p.parse_args()

    positionen = kraken._roh_privat("OpenPositions") or {}
    paare = sorted({q.get("pair") for q in positionen.values() if q.get("pair")})
    alle = kraken._roh_oeffentlich("AssetPairs") or {}
    kurse = {}
    for q in paare:
        try:
            kurse[q] = kraken.letzter_kurs(q)
        except Exception:                                        # noqa: BLE001
            kurse[q] = None
    zeilen = plan(positionen, kurse, alle, a.prozent)

    if not zeilen:
        print("Keine offene Margin-Position - nichts zu tun.")
        return 0

    print("%-10s %-22s %-14s %-10s %-10s %-10s %s"
          % ("Paar", "Position", "Menge", "Einstieg", "Kurs", "Stop", "Hinweis"))
    orderbar = []
    for z in zeilen:
        print("%-10s %-22s %-14s %-10s %-10s %-10s %s"
              % (z["paar"], z["txid"], z["menge"],
                 "%.6f" % z["einstieg"] if z["einstieg"] else "-",
                 z["kurs"] if z["kurs"] else "-",
                 z["stop"] if z["stop"] else "-", z["hinweis"] or "ok"))
        if not z["hinweis"] and z["stop"]:
            orderbar.append(z)

    if not a.anwenden:
        print("\nVORSCHAU - %d von %d Positionen orderbar. Mit --anwenden ausfuehren."
              % (len(orderbar), len(zeilen)))
        return 0

    gesetzt = 0
    for z in orderbar:
        tx = kraken.stop_setzen(z["paar"], z["menge"], z["stop"], echt=True,
                                leverage=z["hebel"], close_txid=z["ordertxid"])
        print("   Stop gesetzt: %-10s %-22s %s" % (z["paar"], tx, z["stop"]))
        gesetzt += 1
    print("\n%d Stop(s) gesetzt." % gesetzt)

    print("--- offene Orders jetzt ---")
    for tx, o in kraken.offene_orders().items():
        print("   %-22s %-10s %-12s %-14s %s"
              % (tx, o["paar"], o["art"], o["menge"], o["preis"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
