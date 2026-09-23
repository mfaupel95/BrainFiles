"""Neue OKX-Bots VORSCHLAGEN - gerechnet, nicht geraten.

Die Idee in einem Satz: **Ein neuer Bot bekommt seinen Stop eingebaut.** Beim
Future-DCA ist das die letzte Sicherungsstufe (`pxSteps` x `maxSafetyOrds` unter
dem Einstieg); der Abstand vom mittleren Einstieg bis dorthin wird als `slPct`
mitgegeben, damit die Boerse selbst schliesst, wenn der Plan ausgereizt ist.
Beim Future-Grid ist es `slTriggerPx` an der unteren Kante `minPx`.

Datenwege: der aktuelle Kurs und die Kerzen kommen ueber `bots.py` / `okx.kerzen`
(oeffentlich), die Parameter-Vorschlaege von OKX selbst ueber
`GET /api/v5/tradingBot/grid/ai-param` - dazu die eigene Rechnung aus dem
Kursverlauf. Was OKX vorschlaegt und was der Verlauf hergibt, wird BEIDES
gezeigt; gebaut wird nur, was ausdruecklich bestellt ist (bauen.py).

Aufruf (aus diesem Ordner):
    python vorschlag.py --art dca  --inst UV-USD_UM_XPERP-310718 --budget 100
    python vorschlag.py --art grid --inst BTC-USD_UM_XPERP-310404 --budget 150
    python vorschlag.py --art dca  --inst ... --boden 2.10 --tage 30
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)
import analyse  # noqa: E402
import bots  # noqa: E402
import okx  # noqa: E402

VORSCHLAEGE = os.path.join(HIER, "vorschlaege")


# --- Reine Rechnung ---------------------------------------------------------

def boden_aus_kerzen(kerzen, tage):
    """Tiefster Tiefstkurs der letzten <tage> Tagesskerzen ([ts,o,h,l,c,v])."""
    reihen = list(kerzen or [])[-int(tage):]
    tiefs = [r[3] for r in reihen if r[3]]
    return min(tiefs) if tiefs else None


def hoehe_aus_kerzen(kerzen, tage):
    reihen = list(kerzen or [])[-int(tage):]
    hochs = [r[2] for r in reihen if r[2]]
    return max(hochs) if hochs else None


def dca_plan(preis, boden, budget, n_max=12, px_schritt=0.0075, tp_pct=0.05,
             sl_pct=0.0, hebel_max=10, sicherheitsabstand=0.05,
             fallraum_prozent=None):
    """Einen Future-DCA-Plan rechnen, dessen TIEFSTE Stufe auf dem Planboden liegt.

    Der Planboden ist der KUERZERE von zwei Wegen: der eingestellte Fallraum
    (`fallraum_prozent`, Vorgabe aus wachen.json) und der Weg bis zum Marktboden
    (`boden`, z. B. Tagestief). So wird der Fallraum bei einem stark gefallenen
    Kurs nicht riesig: ein Boden 55 % unter dem Kurs ergaebe sonst Stufen von
    4,6 % Abstand und einen "Stop" 38 % unter dem Einstieg - ein Stop, der nie
    greift. Der Marktboden bleibt die harte Untergrenze: unter ihm wird nicht
    geplant.

    Rueckgabe: dict mit den Feldern fuer den Bot und der Rechnung dazu.
    """
    preis, boden = float(preis), float(boden)
    budget = float(budget)
    if preis <= 0 or boden <= 0 or boden >= preis:
        return {"fehler": "Boden (%s) muss unter dem Kurs (%s) liegen." % (boden, preis)}
    if budget <= 0:
        return {"fehler": "Budget muss groesser als 0 sein."}
    spanne_boden = 1.0 - boden / preis
    wunsch = (float(fallraum_prozent) / 100.0) if fallraum_prozent else spanne_boden
    spanne = min(wunsch, spanne_boden)
    if spanne <= 0:
        return {"fehler": "Fallraum ist 0 - kein Plan moeglich."}
    n = max(1, int(round(spanne / float(px_schritt))))
    n = min(int(n_max), n)
    px_steps = spanne / n                            # letzte Stufe GENAU auf dem Planboden
    pro_ordnung = budget / (n + 1)
    # Mittlerer Einstieg, wenn ALLE Stufen fuellen: gleichmaessig verteilte
    # Stufen und gleiche Betraege -> Mittel der Stufen.
    stufen = [preis * (1 - px_steps * k) for k in range(1, n + 1)]
    plan_boden = stufen[-1] if stufen else boden
    avg = sum([preis] + stufen) / (n + 1)
    # Hebel so, dass die Liquidation mit Abstand UNTER dem PLANboden liegt:
    # liq ~ avg * (1 - 1/L)  ->  L <= 1 / (1 - ziel/avg), ziel = plan_boden*(1-abstand)
    ziel_liq = plan_boden * (1 - sicherheitsabstand)
    l_max = 1.0 / (1.0 - ziel_liq / avg) if avg > ziel_liq else 1.0
    hebel = max(1, min(int(hebel_max), int(l_max)))
    liq = avg * (1 - 1.0 / hebel)
    sl = (avg - plan_boden) / avg * 100.0 if not sl_pct else sl_pct * 100.0
    return {
        "art": "contract_dca", "direction": "long",
        "kurs": preis, "boden": boden, "planboden": round(stufen[-1], 6) if stufen else boden,
        "fallraum_prozent": spanne * 100.0,
        "maxSafetyOrds": n, "pxSteps": round(px_steps, 6),
        "initOrdAmt": round(pro_ordnung, 4), "safetyOrdAmt": round(pro_ordnung, 4),
        "pxStepsMult": "1", "volMult": "1",
        "investmentAmt": round(budget, 2),
        "avg_px_wenn_voll": avg,
        "letzte_stufe": stufen[-1] if stufen else boden,
        "leverage_max_rechnung": round(l_max, 2), "hebel": hebel, "liq_bei_hebel": liq,
        "tpPct": tp_pct, "slPct": round(sl / 100.0, 4), "slMode": "market",
        "_rechnung": ("%d Sicherungsstufen a %s%% Abstand; die letzte liegt bei %s - das ist "
                      "die letzte kaufbare Grenze dieses Bots (%s%% unter dem Kurs, "
                      "Marktboden waere %s). Betraege je %s, zusammen %s. Voll gefuellt "
                      "liegt der mittlere Einstieg bei %s, die Liquidation bei Hebel %d "
                      "bei %s (%.0f%% unter dem Planboden). slPct %s%% laesst die Boerse "
                      "an der letzten Stufe schliessen - der Stop ist damit eingebaut."
                      % (n, round(px_steps * 100, 3),
                         round(stufen[-1], 6) if stufen else boden,
                         round(spanne * 100, 1), round(boden, 6),
                         round(pro_ordnung, 2), round(budget, 2), round(avg, 6), hebel,
                         round(liq, 6), sicherheitsabstand * 100, round(sl, 2))),
    }


def grid_plan(ai, kurs, boden, hoehe, budget, grid_max=120, hebel_vorgabe=3):
    """Grid-Parameter: OKX-Vorschlag und eigene Kante gegenueberstellen."""
    min_px = float(ai.get("minPx") or boden or 0)
    max_px = float(ai.get("maxPx") or hoehe or 0)
    if min_px and boden and boden < min_px:
        min_px = boden                       # nie eine Kante ueber dem Boden
    if max_px and hoehe and hoehe > max_px:
        max_px = hoehe
    grid_num = int(float(ai.get("gridNum") or 0) or 0)
    if not grid_num:
        grid_num = min(int(grid_max), 40)
    grid_num = min(int(grid_max), max(2, grid_num))
    min_invest = float(ai.get("minInvestment") or 0)
    abstand = (max_px - min_px) / grid_num if grid_num else 0
    warnungen = []
    if min_invest and float(budget) < min_invest:
        warnungen.append("Einsatz %s liegt unter dem Mindestinvestment von OKX (%s) - "
                         "dieser Bot laesst sich so nicht anlegen."
                         % (round(float(budget), 2), round(min_invest, 2)))
    if min_px > 0 and kurs and kurs > max_px:
        warnungen.append("der Kurs %s liegt schon UEBER der oberen Kante %s"
                         % (round(kurs, 6), round(max_px, 6)))
    if min_px > 0 and kurs and kurs < min_px:
        warnungen.append("der Kurs %s liegt schon UNTER der unteren Kante %s"
                         % (round(kurs, 6), round(min_px, 6)))
    return {
        "art": "contract_grid", "direction": ai.get("direction") or "long",
        "kurs": kurs, "minPx": round(min_px, 6), "maxPx": round(max_px, 6),
        "gridNum": grid_num, "runType": "1", "sz": round(float(budget), 2),
        "abstand_je_stufe": round(abstand, 6),
        "abstand_je_stufe_prozent": round(abstand / kurs * 100.0, 3) if kurs else None,
        "leverage_max_rechnung": float(ai.get("lever") or hebel_vorgabe),
        "hebel": int(hebel_vorgabe),
        "minInvestment_laut_okx": min_invest,
        "erwartung_okx": {"annualizedRate": ai.get("annualizedRate"),
                          "perGridProfitRatio": ai.get("perGridProfitRatio"),
                          "duration": ai.get("duration")},
        "slTriggerPx": round(min_px, 6), "tpTriggerPx": round(max_px, 6),
        "warnungen": warnungen,
        "_rechnung": ("%d Stufen von %s bis %s (Richtung %s, Hebel %d), Abstand je Stufe "
                      "%s%% , Einsatz %s. slTriggerPx = untere Kante (%s): liegt der Kurs "
                      "darunter, schliesst die Boerse den Bot selbst. OKX nennt fuer "
                      "diesen Bereich ein Mindestinvestment von %s."
                      % (grid_num, round(min_px, 4), round(max_px, 4),
                         ai.get("direction") or "long", int(hebel_vorgabe),
                         round(abstand / kurs * 100.0, 3) if kurs else "-",
                         round(float(budget), 2), round(min_px, 6), round(min_invest, 2))),
    }


def koerper_dca(p, inst):
    return {
        "instId": inst, "algoOrdType": "contract_dca", "direction": "long",
        "lever": str(p["hebel"]), "initOrdAmt": str(p["initOrdAmt"]),
        "maxSafetyOrds": str(p["maxSafetyOrds"]), "safetyOrdAmt": str(p["safetyOrdAmt"]),
        "pxSteps": str(p["pxSteps"]), "pxStepsMult": str(p["pxStepsMult"]),
        "volMult": str(p["volMult"]), "tpPct": str(p["tpPct"]),
        "slPct": str(p["slPct"]), "slMode": p["slMode"],
        "triggerParams": [{"triggerAction": "start", "triggerStrategy": "instant"}],
    }


def koerper_grid(p, inst):
    return {
        "instId": inst, "algoOrdType": "contract_grid", "maxPx": str(p["maxPx"]),
        "minPx": str(p["minPx"]), "gridNum": str(p["gridNum"]),
        "runType": str(p["runType"]), "sz": str(p["sz"]),
        "direction": p["direction"], "lever": str(p["hebel"]),
        "slTriggerPx": str(p["slTriggerPx"]), "tpTriggerPx": str(p["tpTriggerPx"]),
        "triggerParams": [{"triggerAction": "start", "triggerStrategy": "instant"}],
    }


def tiefe_bestimmen(tiefe_schalter, kerzen, kurs, v, max_stufen):
    """Den Fallraum des Plans bestimmen - gemessen, nicht geraten.

    'auto' heisst: aus dem ATR des Instruments und seinem beobachteten
    Rueckgang. Das ist die Lehre aus den fuenf leer gelaufenen Leitern (4-8 %
    tief bei 8-13 % Tagesspanne). Ohne Kerzen faellt es auf den festen Wert
    aus wachen.json zurueck - ehrlich, mit Hinweis.
    """
    fest = float(v.get("dca_fallraum_prozent") or 15.0)
    if str(tiefe_schalter).lower() != "auto":
        try:
            return float(tiefe_schalter), None
        except ValueError:
            return fest, None
    z = {"kurs": kurs,
         "atr_prozent_14": analyse.atr_prozent(kerzen),
         "max_rueckgang_90": analyse.max_rueckgang(kerzen, 90),
         "max_rueckgang_180": analyse.max_rueckgang(kerzen, 180),
         "max_rueckgang_365": analyse.max_rueckgang(kerzen, 365),
         "letzter_boden_90": analyse.letzter_boden(kerzen, 90),
         "leiter_tiefe_prozent": 0.0}
    e = analyse.empfehlung(z, max_stufen=int(max_stufen),
                           atr_vielfaches=float(v.get("dca_atr_vielfaches") or 3.0))
    if e.get("fehler"):
        e = dict(e)
        e.setdefault("warnungen", [])
        e["warnungen"] = list(e["warnungen"]) + [
            "%s - es gilt der feste Wert %s %%" % (e["fehler"], fest)]
        return fest, e
    return float(e["ziel_tiefe_prozent"]), e


def inst_typ(inst):
    """Aus der Kennung ableiten, welcher Markt gemeint ist.

    `/api/v5/public/instruments` verlangt `instType` - ohne es antwortet OKX
    "Parameter instType can not be empty". Die Kennung verraet ihn meist:
    '...-SWAP' ist SWAP, ein Datumsanhang ('-310718') oder '_UM_' ist FUTURES,
    '-C'/'-P' am Ende ist OPTION, alles andere SPOT. Geraten wird nicht: die
    Kandidaten werden der Reihe nach GEFRAGT.
    """
    i = (inst or "").upper()
    if i.endswith("-SWAP"):
        return ["SWAP"]
    if "_UM_" in i or i.endswith(tuple("-%d" % d for d in range(10))) or i.count("-") >= 3:
        return ["FUTURES", "SWAP"]
    if i.endswith("-C") or i.endswith("-P"):
        return ["OPTION"]
    return ["SPOT", "FUTURES", "SWAP"]


def instrument_pruefen(inst):
    """Gibt es das Instrument? (oeffentlich, ohne Schluessel)"""
    letzter = ""
    for typ in inst_typ(inst):
        try:
            d = okx._roh("/api/v5/public/instruments?instType=%s&instId=%s" % (typ, inst),
                         "GET")
        except Exception as e:
            letzter = "%s: %s" % (type(e).__name__, str(e)[:150])
            continue
        if not d:
            continue
        i = d[0]
        return {"instId": i.get("instId"), "instType": i.get("instType"),
                "ctVal": i.get("ctVal"), "ctValCcy": i.get("ctValCcy"),
                "tickSz": i.get("tickSz"), "lotSz": i.get("lotSz"),
                "maxLever": i.get("lever"), "listeZeit": i.get("listTime"),
                "expTime": i.get("expTime")}
    return {"fehler": "Instrument %s nicht gefunden (%s)" % (inst, letzter or "keine Liste")}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Neuen OKX-Bot vorschlagen (schreibt nichts an der Boerse)")
    ap.add_argument("--art", choices=["dca", "grid"], required=True)
    ap.add_argument("--inst", required=True)
    ap.add_argument("--budget", type=float, default=None)
    ap.add_argument("--boden", type=float, default=None,
                    help="Kurs, unter dem nichts mehr gekauft werden soll (Vorgabe: Tagestief)")
    ap.add_argument("--hoehe", type=float, default=None)
    ap.add_argument("--tage", type=int, default=30, help="Zeitfenster fuer Boden/Hoehe")
    ap.add_argument("--hebel", type=int, default=None)
    ap.add_argument("--tiefe", default="auto",
                    help="Fallraum des Plans: 'auto' (aus ATR und beobachtetem Rueckgang "
                         "gerechnet) oder eine Zahl in Prozent")
    a = ap.parse_args(argv)

    w = json.load(open(os.path.join(HIER, "wachen.json"), encoding="utf-8"))
    v = w.get("_vorschlag") or {}
    budget = a.budget or float(v.get("budget_usd") or 100.0)

    inst_info = instrument_pruefen(a.inst)
    print("Instrument: %s" % json.dumps(inst_info, ensure_ascii=False))
    if inst_info.get("fehler"):
        print("ABBRUCH: %s" % inst_info["fehler"])
        return 2

    kurs = bots.kurs(a.inst)
    kerzen = okx.kerzen(a.inst, "1D", max(60, a.tage + 5))
    boden = a.boden if a.boden is not None else boden_aus_kerzen(kerzen, a.tage)
    hoehe = a.hoehe if a.hoehe is not None else hoehe_aus_kerzen(kerzen, a.tage)
    print("Kurs %s | Boden (%d Tage) %s | Hoehe %s | Kerzen %d"
          % (kurs, a.tage, boden, hoehe, len(kerzen)))

    if a.art == "dca":
        max_stufen = int(v.get("dca_max_steps") or 12)
        tiefe, basis = tiefe_bestimmen(a.tiefe, kerzen, kurs, v, max_stufen)
        if basis:
            print("Tiefe AUTO %.2f %% (ATR %s %%/Tag, groesster Rueckgang %s %%, "
                  "90-Tage-Tief %s, %s Stufen noetig)"
                  % (tiefe, basis.get("atr_prozent_14"),
                     basis.get("instrument_rueckgang_180_prozent"),
                     basis.get("letzter_boden_90"), basis.get("stufen_noetig_fuer_ziel")))
            for w_ in basis.get("warnungen") or []:
                print("  WARNUNG: %s" % w_)
        p = dca_plan(kurs, boden, budget, n_max=max_stufen,
                     px_schritt=float(v.get("dca_px_steps") or 0.0075),
                     tp_pct=float(v.get("dca_tp_pct") or 0.05),
                     sl_pct=float(v.get("dca_sl_pct") or 0.0),
                     fallraum_prozent=tiefe,
                     hebel_max=a.hebel or int(v.get("dca_lever_max") or 10))
        if basis and not p.get("fehler"):
            p["tiefe_auto"] = True
            p["basis"] = {k: basis.get(k) for k in
                          ("atr_prozent_14", "instrument_rueckgang_180_prozent",
                           "letzter_boden_90", "stufen_noetig_fuer_ziel", "atr_vielfaches")}
            p["warnungen"] = list(p.get("warnungen") or []) + list(basis.get("warnungen") or [])
        koerper = koerper_dca(p, a.inst) if not p.get("fehler") else None
    else:
        ai = bots.grid_ai_param(a.inst, richtung="long", dauer="14D")
        print("OKX-Vorschlag: %s" % json.dumps(ai, ensure_ascii=False))
        p = grid_plan(ai, kurs, boden, hoehe, budget,
                      grid_max=int(v.get("grid_num_max") or 120),
                      hebel_vorgabe=a.hebel or int(v.get("grid_lever") or 3))
        koerper = koerper_grid(p, a.inst)

    if p.get("fehler"):
        print("ABBRUCH: %s" % p["fehler"])
        return 2

    print("\n--- Vorschlag ---")
    print(p["_rechnung"])
    print(json.dumps({k: val for k, val in p.items() if not k.startswith("_")},
                     ensure_ascii=False, indent=1))
    print("\n--- Koerper fuer die Boerse (bauen.py schickt ihn) ---")
    print(json.dumps(koerper, ensure_ascii=False, indent=1))

    os.makedirs(VORSCHLAEGE, exist_ok=True)
    name = "%s-%s-%s.json" % (a.art, a.inst.replace("/", "_"),
                              datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    pfad = os.path.join(VORSCHLAEGE, name)
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump({"erstellt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "instId": a.inst, "art": a.art, "budget": budget,
                   "kurs": kurs, "boden": boden, "hoehe": hoehe,
                   "instrument": inst_info, "plan": p, "koerper": koerper},
                  f, ensure_ascii=False, indent=1)
    print("\nAbgelegt: %s" % pfad)
    print("Bauen: python bauen.py %s --anwenden" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())