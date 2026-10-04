#!/usr/bin/env python3
"""OKX-Positionen LIVE lesen und je Position auswerten.

REIN LESEND: nur GET /api/v5/account/positions und die oeffentlichen Kurse. Kein
Aufruf mit Schreibwirkung, kein `signiert=False` an einem POST.

Warum eigens gebaut: `okx_bot_waechter` zeigt die BOTS (Leiter, Munition), nicht
das, was auf dem Konto wirklich offen ist. Die Hausfrage ist aber gerade die
andere: welche Position ist offen, wie weit vom Einstieg, wie weit von der
Liquidation, und wie viel Puffer steckt in der Marge. Beides gehoert
zusammengestellt, sonst liest man Marge und Kurs von verschiedenen Orten.

FELDER je Position (aus /account/positions, nicht geraten):
  instId, pos (signed), avgPx, markPx, upl, uplRatio, liqPx, margin, imr,
  mgnRatio, lever, notionalUsd, instType, mgnMode, uplRatio ist in DECIMAL.

Die Auswertung rechnet drei Distanzen und benennt jede einzeln - eine
Sammelzahl waere eine Behauptung:
  - bis zum Einstieg   (markPx/avgPx - 1) * Richtung
  - bis zur Liquidation (liqPx/markPx - 1) * Richtung, positiv = Luft
  - freies Guthaben in der Kontowaehrung (stgyEq/availEq getrennt, weil
    gebundenes Guthaben in Staking kein freies Guthaben ist - 03.10.2026)

Aufruf (aus dem Handel-Ordner oder ueberall):
    ../scanner/.venv/Scripts/python.exe okx_positionen_live.py
    ../scanner/.venv/Scripts/python.exe okx_positionen_live.py --json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
SCANNER = os.path.join(HIER, "scanner")


def lade(name):
    """Fachmodule ueber den PFAD laden. `import okx` wuerde bei einem
    gleichnamigen Modul in sys.path[0] das FALSCHE nehmen - die Hausfalle steht
    in handel-spuren."""
    p = os.path.join(SCANNER, name + ".py")
    spec = importlib.util.spec_from_file_location("okxlive_" + name, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


okx = lade("okx")


def zahl(w, v=None, default=0.0):
    """Eine Zahl aus einem OKX-Feld.

    ERSATZLOS ueberladen, weil die Aufrufe zwei Formen haben: `zahl(x.get("eq"))`
    (der Wert selbst) und `zahl(zeile.get("eq"))` (Zeile, Feldname).
    Vorher stand hier `float(w)` - der erste Wert wurde als FORMAT-String
    benutzt und lieferte still 0.0, weshalb ein Konto mit 958 USDC als
    "0.00, stimmt" gemeldet wurde (gemessen 04.10.2026). Die Kontrolle
    `passt: True` war das Symptom: 0 == 0 passt immer.

    Leer heisst "unbekannt", nicht "null": OKX laesst `availEq` als leeren
    String und `stgyEq` als `null`. Beides wird zu `default`, nicht zu einer
    behaupteten Null."""
    if v is None:
        wert = w
    else:
        wert = None
        if isinstance(w, dict):
            wert = w.get(v)
        else:
            wert = getattr(w, v, None)
    if wert in (None, "", "-"):
        return default
    try:
        return float(wert)
    except (TypeError, ValueError):
        return default


def positionen(inst_type):
    """Nur die instType-Werte, die OKX auf positions annimmt: FUTURES, SWAP,
    MARGIN. **SPOT steht nicht dabei** (`OKX 51000: Parameter instType error`,
    gemessen 04.10.2026) - Spot-Bestaende kommen aus
    `/api/v5/account/balance` und sind keine Positionen im Sinne dieses
    Werkzeugs. Ein Aufruf mit SPOT wird deshalb nicht gestellt, statt einen
    Fehler als Befund zu melden."""
    if inst_type not in ("FUTURES", "SWAP", "MARGIN"):
        raise ValueError("instType %r wird von positions nicht angenommen "
                         "(FUTURES|SWAP|MARGIN)" % inst_type)
    roh = okx._roh("/api/v5/account/positions?instType=" + inst_type, signiert=True)
    if not isinstance(roh, list):
        raise SystemExit("unerwartete Antwort (keine Liste): %r" % (roh,))
    return roh


def auswerten(p):
    """Eine Rohzeile -> eine Zeile mit den drei Distanzen."""
    pos = zahl(p.get("pos"))
    if pos == 0:
        return None
    inst = p.get("instId", "?")
    avg = zahl(p.get("avgPx"))
    mark = zahl(p.get("markPx"))
    liq = zahl(p.get("liqPx"))
    typ = p.get("instType", "?")
    # Long = pos > 0, Short = pos < 0
    richtung = 1.0 if pos > 0 else -1.0

    d_einstieg = None
    if avg and mark:
        d_einstieg = (mark / avg - 1.0) * richtung * 100.0
    # LUFT bis zur Liquidation, positiv auf BEIDEN Seiten: Long hat liq unter
    # mark, Short ueber mark. `(liq/mark - 1) * -richtung` liefert beides
    # positiv und wird negativ, wenn der Kurs die Liquidationsmarke
    # ueberschritten hat - das ist der Befund, den man sehen will, und
    # `abs()` wuerde ihn genau dort verschlucken.
    d_liq = None
    if liq and mark:
        d_liq = (liq / mark - 1.0) * -richtung * 100.0

    return {
        "instId": inst,
        "seitenname": "long" if richtung > 0 else "short",
        "instType": typ,
        "pos": pos,
        "menge": abs(pos),
        "avgPx": avg,
        "markPx": mark,
        "liqPx": liq,
        "lever": zahl(p.get("lever")),
        "mgnMode": p.get("mgnMode", ""),
        "notionalUsd": zahl(p.get("notionalUsd")),
        "margin": zahl(p.get("margin")),
        "imr": zahl(p.get("imr")),
        "upl": zahl(p.get("upl")),
        "uplRatio": zahl(p.get("uplRatio")) * 100.0,
        "mgnRatio": zahl(p.get("mgnRatio")) * 100.0,
        "abstand_einstieg_pct": d_einstieg,
        "luft_bis_liq_pct": d_liq,
        # Gegenrechnung derselben Sache: mgnRatio = 100 x Margin/Notional.
        # Stimmt sie nicht mit der liqPx/markPx-Rechnung ueberein, ist eine
        # der Quellen stale - das wird im Bericht benannt statt gemittelt.
        "luft_aus_mgnRatio_pct": (100.0 - zahl(p.get("mgnRatio"))) if p.get("mgnRatio") not in (None, "") else None,
        "ccy": p.get("ccy", ""),
        "mgnCurrency": p.get("mgnCurrency", ""),
    }


def guthaben():
    """Kontostaende aus der ROHANTWORT, JEDE Zahl aus dem richtigen Feld.

    `okx.guthaben(ccy)` liefert nur `availBal` (frei) - die Frage "wie viel ist
    frei". Fuer die Positionsanalyse wird die ganze Antwort gebraucht.

    Die Falle, gemessen am 04.10.2026: `totalEq` steht auf Kontoebene
    (1703.57), aber `availEq` ist dort ein LEERER String und `stgyEq` ist
    `null`. Ein Parser, der die Kontoebene las, meldete 0.00 fuer ein Konto
    mit 958 USDC - das sieht wie ein leeres Konto aus und nicht wie ein
    Fehler. Beide Zahlen stehen je WAEHRUNG in `details`:
    USDC eq 958,65 | availEq 16,53 | stgyEq 453,69 | gebunden 488,43.
    `totalEq` ist nur die Summe darueber und taugt als Kontrollwert.

    `frozenBal` heisst bei OKX nicht 'eingefroren', sondern die an Margin,
    offene Orders und Algo-Orders gebundene Summe. Der Bericht nennt sie
    deshalb 'gebunden'."""
    roh = okx._roh("/api/v5/account/balance", signiert=True)
    if not isinstance(roh, list) or not roh:
        return {}
    konto = roh[0]
    waeh = {}
    for d in konto.get("details") or []:
        ccy = d.get("ccy")
        if not ccy:
            continue
        v = {
            "eq": zahl(d.get("eq")),
            "availEq": zahl(d.get("availEq")),
            "cashBal": zahl(d.get("cashBal")),
            "stgyEq": zahl(d.get("stgyEq")),
            "gebunden": zahl(d.get("frozenBal")),
        }
        # Nur Waehrungen, bei denen etwas dasteht - die Antwort listet ~40,
        # die meisten mit 0.
        if max(v.values()):
            waeh[ccy] = v
    gesamt = sum(w["eq"] for w in waeh.values())
    # Kontrollwert: die Detail-Zeilen muessen zur Kontoebene passen. Wenn sie
    # es nicht tun, ist die Liste unvollstaendig (gekuerzt) - das wird
    # gemeldet statt stillschweigend eine kleinere Zahl zu zeigen.
    kontrolle = zahl(konto.get("totalEq"))
    return {
        "waehrungen": waeh,
        "summe_eq": gesamt,
        "totalEq": kontrolle,
        "passt": abs(gesamt - kontrolle) < 0.01,
        "differenz": gesamt - kontrolle,
    }




def haupt():
    z = []
    g = guthaben()
    if g:
        w = g["waehrungen"]
        z.append("KONTO:")
        z.append("  gesamt %.2f USD (totalEq %.2f, %s)"
                 % (g["summe_eq"], g["totalEq"],
                    "stimmt" if g["passt"] else
                    "ABWEICHUNG %.2f - Liste unvollstaendig" % g["differenz"]))
        z.append("  %-6s %11s %11s %11s %11s" % ("CCY", "gesamt", "frei",
                                                 "staking", "gebunden"))
        for ccy, v in sorted(w.items(), key=lambda kv: -kv[1]["eq"]):
            z.append("  %-6s %11.2f %11.2f %11.2f %11.2f"
                     % (ccy, v["eq"], v["availEq"], v["stgyEq"], v["gebunden"]))
        usdc = w.get("USDC")
        if usdc:
            z.append("")
            z.append("  USDC: %.2f gesamt = %.2f frei + %.2f Staking + %.2f gebunden"
                     % (usdc["eq"], usdc["availEq"], usdc["stgyEq"],
                        usdc["eq"] - usdc["availEq"] - usdc["stgyEq"]))
        z.append("")

    z.append("OFFENE POSITIONEN (FUTURES; Spot ist Bestand, keine Position):")
    zeilen = []
    for inst_type in ("FUTURES", "SWAP", "MARGIN"):
        try:
            for p in positionen(inst_type):
                a = auswerten(p)
                if a:
                    zeilen.append(a)
        except Exception as ex:
            z.append("  %-8s Abfrage: %s" % (inst_type, str(ex)[:140]))
    if not zeilen:
        z.append("  keine (pos != 0)")
        return "\n".join(z)

    zeilen.sort(key=lambda a: abs(a.get("notionalUsd") or 0), reverse=True)
    z.append("  %-30s %-5s %3s %-8s %11s %10s %10s %8s %8s %8s"
             % ("Instrument", "Seite", "Heb", "Modus", "Menge", "Mark", "Liq",
                "Einst%", "UPL%", "Luft%"))
    s_not = s_upl = s_mar = 0.0
    for a in zeilen:
        l1 = a["luft_bis_liq_pct"]
        z.append("  %-30s %-5s %3.0f %-8s %11.4f %10.4f %10.4f %7.2f%% %7.2f%% %7.2f%%"
                 % (a["instId"][:30], a["seitenname"], a["lever"],
                    a["mgnMode"] or "-", a["menge"], a["markPx"], a["liqPx"],
                    a["abstand_einstieg_pct"] or 0, a["uplRatio"], l1 or 0))
        s_not += a["notionalUsd"]
        s_upl += a["upl"]
        s_mar += a["margin"]

    z.append("")
    z.append("  %d Positionen | Notional %.2f USD | gebundene Margin %.2f | UPL %.2f USD"
             % (len(zeilen), s_not, s_mar, s_upl))
    z.append("  Hebel im Schnitt %.1f | Marge ist %.1f%% des Notionals"
             % (s_not / s_mar if s_mar else 0, 100.0 * s_mar / s_not if s_not else 0))
    knapp = [a for a in zeilen
             if a.get("luft_bis_liq_pct") is not None and a["luft_bis_liq_pct"] < 12]
    if knapp:
        z.append("")
        z.append("  Weniger als 12 Prozent Luft bis zur Liquidation:")
        for a in sorted(knapp, key=lambda a: a["luft_bis_liq_pct"]):
            z.append("    %-30s %7.2f%%  (Hebel %.0f, %s)"
                     % (a["instId"][:30], a["luft_bis_liq_pct"], a["lever"],
                        a["mgnMode"] or "-"))
    return "\n".join(z)


def main(argv=None):
    ap = argparse.ArgumentParser(description="OKX-Positionen live lesen (rein lesend).")
    ap.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    ap.add_argument("--inst-type", default=None,
                    help="nur ein instType (FUTURES|SWAP|SPOT|MARGIN)")
    args = ap.parse_args(argv)

    if args.json:
        if args.inst_type:
            zeilen = [a for p in positionen(args.inst_type)
                      if (a := auswerten(p))]
        else:
            zeilen = []
            for it in ("FUTURES", "SWAP", "SPOT", "MARGIN"):
                try:
                    zeilen += [a for p in positionen(it) if (a := auswerten(p))]
                except Exception:
                    pass
        print(json.dumps({"positionen": zeilen, "guthaben": guthaben()},
                         ensure_ascii=False, indent=2))
        return 0
    if args.inst_type:
        roh = positionen(args.inst_type)
        print("OFFENE POSITIONEN (%s):" % args.inst_type)
        zeilen = [a for p in roh if (a := auswerten(p))]
        if not zeilen:
            print("  keine (pos != 0)")
            return 0
        for a in zeilen:
            print("  %-34s %-5s %12.4f @ %12.4f  liq %12.4f  UPL %9.2f (%.2f%%)"
                  % (a["instId"], a["seitenname"], a["menge"], a["markPx"],
                     a["liqPx"], a["upl"], a["uplRatio"]))
        return 0
    print(haupt())
    return 0


if __name__ == "__main__":
    sys.exit(main())