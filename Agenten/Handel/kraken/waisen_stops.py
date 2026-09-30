"""Waisen-Stops finden: Schutz-Orders, deren Position es nicht mehr gibt.

Warum das noetig ist (Befund 24.09.2026, Auftrag "Warum kann ich SUI/EUR nicht
schliessen?"):
  * Eine MARGIN-Position wird geschlossen -> Kraken LOESCHT den zugehoerigen
    Stop-Loss NICHT. Der Stop bleibt "open" und sieht in der Oberflaeche aus wie
    eine offene Position.
  * Ein Margin-Close ordert NICHTS (es gibt keinen Bestand zum Verkaufen) - er
    scheitert mit "EOrder:Insufficient funds", weil weder Guthaben noch Position
    da sind. Genau das ist die Antwort auf "warum kann ich nicht schliessen".
  * GEFAEHRLICH: ein Margin-SELL-Stop ohne Long-Position ist beim Ausloesen ein
    SHORT-Einstieg - er verkauft, was nicht da ist. Deshalb muss er weg.
  * SPOT-Stops sind harmlos, solange die Muenze im Guthaben liegt (hold_trade
    zaehlt die reservierte Menge). Liegt sie nicht mehr da, sind auch sie Waisen.

Vorschau ist Standard. Erst mit --stornieren wird etwas storniert.
"""
import argparse
import importlib.util
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))


def _lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


kraken = _lade("kraken", os.path.join(HIER, "kraken.py"))
_stops = _lade("spot_stops", os.path.join(HIER, "spot_stops.py"))


def positionen(kraken_modul):
    """Offene MARGIN-Positionen - in BEIDEN Formen der Antwort.

    Kraken liefert `OpenPositions` als {txid: {...}} OHNE "open"-Huelle
    (`OpenOrders` hat sie). Wer nur .get("open") liest, sieht NIE eine
    Position - und haelt dann jeden Schutzauftrag fuer eine Waise.

    Befund 30.09.2026 (T-208): genau das passierte mit vier SUIEUR-Auftraegen,
    waehrend 274,6 SUI in vier Margin-Positionen lagen. Ein Guthaben von 0
    heisst NICHT, dass keine Position da ist.
    """
    roh = kraken_modul._roh_privat("OpenPositions") or {}
    if not isinstance(roh, dict):
        return {}
    if isinstance(roh.get("open"), dict):
        return roh["open"]
    return {k: v for k, v in roh.items() if isinstance(v, dict)}


def lage(kraken_modul, stops_modul):
    """Offene Orders, offene Positionen, Guthaben -> Liste mit Bewertung."""
    bal = kraken_modul._roh_privat("BalanceEx") or {}
    guthaben = {stops_modul.norm(k): (float(v.get("balance") or 0),
                                      float(v.get("hold_trade") or 0))
                for k, v in bal.items()}
    positionen_roh = positionen(kraken_modul)
    paare = stops_modul._paare_laden()
    offene = list(((kraken_modul._roh_privat("OpenOrders") or {}).get("open")
                   or {}).items())

    mpos = {}
    for p in positionen_roh.values():
        muenze = stops_modul.muenze_aus_paar(p.get("pair"), paare)
        rest = float(p.get("vol") or 0) - float(p.get("vol_closed") or 0)
        mpos[muenze] = mpos.get(muenze, 0.0) + rest

    zeilen = []
    for txid, o in offene:
        if not isinstance(o, dict):
            continue
        d = o.get("descr") or {}
        if d.get("ordertype") not in ("stop-loss", "stop-loss-limit"):
            continue
        muenze = stops_modul.muenze_aus_paar(d.get("pair"), paare)
        vol = float(o.get("vol") or 0)
        bestand, reserviert = guthaben.get(muenze, (0.0, 0.0))
        hat_position = mpos.get(muenze, 0.0)
        if hat_position > 0:
            lage_ = "geschuetzt (Position %.8g da)" % hat_position
        elif reserviert + 1e-9 >= vol:
            lage_ = "geschuetzt (Guthaben reserviert)"
        else:
            lage_ = "WAISE (keine Position, %.8g %s im Guthaben)" % (bestand, muenze)
        zeilen.append({"txid": txid, "paar": d.get("pair"),
                       "menge": vol, "preis": float(d.get("price") or 0),
                       "muenze": muenze, "lage": lage_,
                       "waise": lage_.startswith("WAISE")})
    return zeilen


def main():
    ap = argparse.ArgumentParser(description="Waisen-Stops finden (Vorschau "
                                             "Standard)")
    ap.add_argument("--stornieren", action="store_true",
                    help="Waisen wirklich stornieren")
    args = ap.parse_args()

    zeilen = lage(kraken, _stops)
    waisen = [z for z in zeilen if z["waise"]]
    print("Schutz-Orders an der Boerse: %d, davon Waisen: %d"
          % (len(zeilen), len(waisen)))
    for z in zeilen:
        marke = "WAISE " if z["waise"] else "ok    "
        print("  %s %-20s %-9s %-14.8g @ %-10.6g %s"
              % (marke, z["txid"], z["paar"], z["menge"], z["preis"], z["lage"]))
    if not waisen:
        print("\nNichts zu tun.")
        return 0
    if not args.stornieren:
        print("\nVORSCHAU - nichts storniert. Mit --stornieren ausfuehren.")
        return 0

    gut = 0
    storno = getattr(kraken, "stornieren", None) or kraken.order_stornieren
    for z in waisen:
        try:
            r = storno(z["txid"])
            print("  STORNIERT %-20s %s" % (z["txid"], r if r else "angenommen"))
            gut += 1
        except Exception as e:            # noqa: BLE001 - je Order melden
            print("  FEHLER     %-20s %s" % (z["txid"], e))
    print("\n%d von %d Waisen storniert." % (gut, len(waisen)))
    nach = [z for z in lage(kraken, _stops) if z["waise"]]
    print("Gegenprobe an der Boerse: %d Waisen uebrig." % len(nach))
    return 0 if gut == len(waisen) else 1


if __name__ == "__main__":
    sys.exit(main())