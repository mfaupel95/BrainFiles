"""OKX: Schutz-Orders finden, deren Position bzw. Bestand es nicht mehr gibt.

Befund 24.09.2026 (Auftrag "refine", nachdem die Kraken-Waisen auffielen):
dieselbe Klasse gibt es bei OKX. Ein `conditional`-Algo-Zuschlag ueberlebt das
Schliessen der Position, und im schlimmsten Fall verkauft er, was nicht da ist -
bei einem Perp-Kontrakt entsteht daraus ein SHORT.

Gemessen am 24.09.2026 (LIVE): 5 Algo-Stops, davon
  * BTC-USDC 0,00132754 @ 80673,7  -> Bestand BTC = 0            -> WAISE
  * ETH-USDC 0,037301  @ 2501,27   -> Bestand ETH = 0            -> WAISE
  * SOL-USDC / HYPE-USDC           -> Bestand vollstaendig RESERVIERT
                                      (availEq 0, eq = Menge)    -> in Ordnung
  * MON-USD_UM_XPERP sell 4143     -> Position nur 2985 Kontrakte -> UEBERDECKT

Zwei Eigenheiten, die die Rechnung ausmachen:
  * Bei OKX-SPOT reserviert eine Bedingte Verkaufsorder die Muenze: `eq` bleibt
    stehen, `availEq` geht auf 0. Wer nur `availEq` liest, haelt jeden SCHARFEN
    Stop fuer verwaist - hier zaehlt `eq`.
  * Bei Perps wird gegen die Position DERSELBEN instId verglichen (die Kennung
    traegt beim XPERP die Nummer mit, z. B. MON-USD_UM_XPERP-310711).

Vorschau ist der Standard; abbestellt wird nur mit `--stornieren`, und nur
WAISEN - "UEBERDECKT" wird gemeldet, nicht angefasst (dort steht eine echte
Position, nur die Menge passt nicht).
"""

import argparse
import importlib.util
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
OKX_PFAD = os.path.join(HIER, "scanner", "okx.py")


def _laden(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _basis(inst):
    """BTC-USDC -> BTC, MON-USD_UM_XPERP-310711 -> MON."""
    return (inst or "").split("-")[0].upper()


def _zahl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def lage(okx):
    """Zeilen (dicts) aller OKX-Schutz-Orders mit ihrer Deckung.

    Rueckgabe je Zeile: kennung, inst, art, menge, preis, lage
    ('OK'|'WAISE'|'UEBERDECKT'), waise (bool), grund, deckung.
    """
    stops = okx._roh("/api/v5/trade/orders-algo-pending?ordType=conditional",
                     signiert=True) or []
    pos = {p.get("instId"): _zahl(p.get("pos"))
           for p in (okx._roh("/api/v5/account/positions", signiert=True) or [])
           if isinstance(p, dict)}
    bl = okx._roh("/api/v5/account/balance", signiert=True) or []
    eq = {d.get("ccy"): _zahl(d.get("eq"))
          for d in ((bl[0].get("details") if bl else []) or [])
          if isinstance(d, dict)}

    zeilen = []
    for s in stops:
        if not isinstance(s, dict):
            continue
        inst = s.get("instId") or ""
        menge = _zahl(s.get("sz"))
        preis = _zahl(s.get("slTriggerPx") or s.get("tpTriggerPx"))
        art = s.get("tdMode") or ""
        if art == "cash":
            deckung = eq.get(_basis(inst), 0.0)
            quelle = "Bestand %s" % _basis(inst)
        else:
            deckung = abs(pos.get(inst, 0.0))
            quelle = "Position %s" % inst

        if deckung <= 0:
            lage_txt, grund = "WAISE", "kein %s" % quelle
        elif menge > deckung + 1e-9:
            # Harmlos bei reduceOnly (OKX kann nur schliessen, nie aufstocken)
            # und bei Spot (mehr als der Bestand laesst sich nicht verkaufen) -
            # deshalb eine Notiz, kein Alarm.
            lage_txt, grund = "UEBERDECKT", "%s %.6g < Order %.6g%s" % (
                quelle, deckung, menge,
                ", reduceOnly" if str(s.get("reduceOnly")).lower() == "true" else "")
        else:
            lage_txt, grund = "OK", quelle
        zeilen.append({
            "kennung": s.get("algoId") or "",
            "inst": inst,
            "art": art,
            "menge": menge,
            "preis": preis,
            "lage": lage_txt,
            "waise": lage_txt == "WAISE",
            "grund": grund,
            "deckung": deckung,
        })
    return zeilen


def storniere(okx, kennung, inst=None):
    """Einen Algo-Zuschlag abbestellen.

    Falle (23.09.2026): `cancel-algos` verlangt `instId` - ohne es antwortet OKX
    50014 'Parameter instId can not be empty', der Stop laesst sich NIE
    abbestellen. Und 51400 'has been filled, canceled or does not exist' heisst:
    erledigt, kein Fehler.
    """
    if not inst:
        inst = okx.stop_inst(kennung)
    return okx.stop_stornieren(kennung, inst)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="OKX-Schutz-Orders ohne Position finden (Vorschau Standard)")
    ap.add_argument("--stornieren", action="store_true",
                    help="gefundene WAISEN wirklich abbestellen ('UEBERDECKT' nie)")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    okx = _laden("okx_waisen", OKX_PFAD)
    zeilen = lage(okx)
    waisen = [z for z in zeilen if z["waise"]]
    gross = [z for z in zeilen if z["lage"] == "UEBERDECKT"]

    print("OKX-Schutz-Orders: %d geprueft, %d in Ordnung, %d WAISEN, %d ueberdeckt"
          % (len(zeilen), len(zeilen) - len(waisen) - len(gross),
             len(waisen), len(gross)))
    for z in zeilen:
        print("  %-9s %-26s %-9s %-14.8g @ %-10.6g (%s)"
              % (z["lage"], z["inst"], z["art"], z["menge"], z["preis"],
                 z["grund"]))
    if not args.stornieren:
        if waisen:
            print("\nNichts geaendert (Vorschau). Zum Abbestellen: --stornieren")
        return 0

    gut = 0
    for z in waisen:
        try:
            storniere(okx, z["kennung"], z["inst"])
            print("  STORNIERT %-26s %s" % (z["inst"], z["kennung"]))
            gut += 1
        except Exception as e:                      # noqa: BLE001 - je Order melden
            print("  FEHLER     %-26s %s: %s" % (z["inst"], z["kennung"], e))
    print("\n%d von %d Waisen abbestellt." % (gut, len(waisen)))
    for z in gross:
        print("  UEBERDECKT bleibt stehen: %s (%s) - Position ist echt, Menge pruefen"
              % (z["inst"], z["grund"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())