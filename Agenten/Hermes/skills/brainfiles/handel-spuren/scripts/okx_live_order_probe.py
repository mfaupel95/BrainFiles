"""Live-Order einer Handelsspur LESEND am Handelsplatz nachpruefen.

Aufruf (aus Agenten/Handel, mit dem Spur-venv):
    scanner/.venv/Scripts/python.exe <dieses Skript> scanner
    scanner/.venv/Scripts/python.exe <dieses Skript> xperp

Warum es das gibt: eine Journal-Zeile `live,kauf` ist eine Buchung, kein Beleg.
Erst `avgPx` aus der OKX-Antwort zeigt, zu welchem Preis wirklich gefuellt wurde -
und ob Stop, Ziel und Risiko im Buch dazu passen. Es wird NICHTS geschrieben und
nichts bestellt; alle Aufrufe sind signierte GETs.

Liest <spur>/zustand.json (kauf_ord_id, stop_ord_id je Position) und befragt ueber
das okx-Modul der Spur (scanner/okx.py) das Konto. Gibt keine Schluessel aus -
nur Host, Kennungen, Preise, Zustaende.

Details und Deutung: references/live-order-nachpruefen.md
"""
import json
import os
import sys
from datetime import datetime, timezone

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _okx_modul():
    sys.path.insert(0, os.path.join(HANDEL, "scanner"))
    import okx  # noqa: E402
    return okx


def _positionen(spurordner):
    pfad = os.path.join(spurordner, "zustand.json")
    if not os.path.exists(pfad):
        return []
    z = json.load(open(pfad, encoding="utf-8"))
    roh = z.get("positionen") or z.get("position") or []
    if isinstance(roh, dict):
        roh = list(roh.values())
    return roh


def _zeige(titel, pfad, okx, nur_erste=True):
    print("\n== %s ==" % titel)
    try:
        d = okx._roh(pfad, signiert=True)
    except Exception as e:  # noqa: BLE001
        print("  FEHLER: %s: %s" % (type(e).__name__, str(e)[:300]))
        return None
    if not d:
        print("  (leer)")
        return None
    for eintrag in (d[:1] if nur_erste else d)[:20]:
        kurz = {k: eintrag.get(k) for k in (
            "instId", "ordId", "algoId", "side", "ordType", "state", "sz",
            "accFillSz", "avgPx", "fillPx", "fee", "feeCcy", "slTriggerPx",
            "tdMode", "cTime")}
        print("  " + json.dumps(kurz, ensure_ascii=False))
        if eintrag.get("cTime"):
            print("    Zeit: " + datetime.fromtimestamp(
                int(eintrag["cTime"]) / 1000, timezone.utc).astimezone().isoformat())
    return d


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    spurordner = os.path.abspath(sys.argv[1])
    okx = _okx_modul()

    print("Spur: %s" % spurordner)
    print("Basis-Host: %s" % okx._live_basis())
    print("Live-Schluessel vorhanden: %s" % okx.schluessel_vorhanden())

    cfg = okx._roh("/api/v5/account/config", signiert=True)
    if cfg:
        print("Konto: uid=%s mainUid=%s label=%s perm=%s" % (
            cfg[0].get("uid"), cfg[0].get("mainUid"),
            cfg[0].get("label"), cfg[0].get("perm")))
        if cfg[0].get("uid") != cfg[0].get("mainUid"):
            print("  ACHTUNG: Unterkonto - Orders erscheinen nur dort.")

    pos = _positionen(spurordner)
    if not pos:
        print("\nKeine Positionen in zustand.json.")
    for p in pos:
        inst = p.get("inst") or p.get("paar") or p.get("symbol")
        oid = p.get("kauf_ord_id")
        buch = p.get("einstieg") or p.get("preis_einstieg")
        print("\n---- %s | Buch-Einstieg %s | kauf_ord_id %s | stop_ord_id %s"
              % (inst, buch, oid, p.get("stop_ord_id")))
        if not oid:
            print("  (keine Order-ID = Papierposition)")
            continue
        d = _zeige("Order %s" % oid,
                   "/api/v5/trade/order?instId=%s&ordId=%s" % (inst, oid), okx)
        if d and d[0].get("avgPx") and buch:
            fill = float(d[0]["avgPx"])
            abw = fill / float(buch) - 1.0
            print("    Buch %.6f vs Fill %.6f = %+.2f %%" % (float(buch), fill, 100 * abw))
            if abs(abw) > 0.02:
                print("    ACHTUNG: Abweichung > 2 %% - der Einstieg im Buch ist"
                      " NICHT der Fuellungspreis. Stop, Ziel und Risiko mitpruefen.")
        sd = p.get("stop_ord_id")
        if sd:
            _zeige("Notausstieg %s" % sd,
                   "/api/v5/trade/order-algo?algoId=%s" % sd, okx)

    _zeige("Order-Historie SPOT (20)",
           "/api/v5/trade/orders-history?instType=SPOT&limit=20", okx, nur_erste=False)
    _zeige("Algo-Orders SPOT",
           "/api/v5/trade/orders-algo-pending?instType=SPOT&ordType=conditional&limit=20",
           okx, nur_erste=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
