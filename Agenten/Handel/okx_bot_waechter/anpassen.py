"""Parameter eines LAUFENDEN OKX-Bots anpassen - Leiter und Stop, ohne Neustart.

Beweis, dass dieser Weg fuer unser Konto existiert (Sonde 23.09.2026, ohne
Aenderung): ein Amend mit einer algoId, die es nicht gibt, antwortet
`OKX 51291: The bot doesn't exist or has already stopped` - also gibt es den
Endpunkt, die Signatur stimmt und der Host passt. Ein GET darauf antwortet
`OKX 3: Operation not supported` (falscher Weg). Der Koerper traegt laut Doku:

    POST /api/v5/tradingBot/dca/amend-order-algo
    algoId, pxSteps, pxStepsMult, volMult, tpPct, slPct,
    initOrdAmt, safetyOrdAmt, maxSafetyOrds, reserveFunds, triggerParams

Also ALLE Leiterparameter - der laufende Bot wird umgestellt, und fuer den
naechsten Zyklus (nach dem Take-Profit) gelten die neuen Werte weiter.

Zwei Dinge aendern sich NICHT durch ein Amend:
* was schon gefuellt ist (die Position bleibt, wie sie ist),
* ob Geld da ist: neue Sicherungsstufen brauchen freies Guthaben. Ohne freie
  Mittel sind zusaetzliche Stufen nur auf dem Papier vorhanden.

Aufruf:
    python anpassen.py                     # Bericht: alt gegen neu, je Bot
    python anpassen.py --nur-schutz        # nur slPct setzen, Leiter unberuehrt
    python anpassen.py --stufen 20 --anwenden   # braucht anpassen_erlaubt=true
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import analyse   # noqa: E402
import bots      # noqa: E402
import waechter   # noqa: E402

assert waechter.__file__.startswith(HIER)

JOURNAL = os.path.join(HIER, "bot_waechter_journal.jsonl")


def freies_guthaben(ccy="USDC"):
    """Frei verfuegbares Guthaben in der Margin-Waehrung des Kontos."""
    try:
        zeilen = bots.hole("/api/v5/account/balance?ccy=%s" % ccy)
    except Exception:
        return None
    for z in zeilen or []:
        for detail in z.get("details") or []:
            if detail.get("ccy") == ccy:
                for feld in ("availEq", "availBal", "cashBal"):
                    try:
                        return float(detail.get(feld))
                    except (TypeError, ValueError):
                        continue
    return None


def _zahl(d, schluessel, vorgabe=None):
    try:
        return float(d.get(schluessel))
    except (TypeError, ValueError):
        return vorgabe


def margin_bedarf(details, bot, ziel_boden):
    """Was kostet es, die Liquidation bis unter den Planboden zu druecken?

    Hergeleitet, nicht geraten: fuer eine isolierte Position gilt
        Abstand(Einstand -> Liquidation) = Margin / Notional + Rest,
    wobei der Rest die Wartungsrate UND alles ist, was die Boerse sonst
    anrechnet (z.B. einrealisierte Gewinne, die als Puffer auf der Position
    liegen). Margin, Notional und der Abstand sind alle bekannt - der Rest
    faellt damit heraus und wird NICHT angenommen. Ist er gross (ueber 5 %),
    steckt mehr Margin in der Position als die Leiterbetraege hergeben; das
    wird gemeldet, weil es die Rechnung sonst still verschoenert.
    """
    avg = _zahl(details, "avgPx")
    liq = _zahl(details, "liqPx")
    notional = _zahl(details, "notionalUsd")
    if not (avg and liq and notional):
        return None
    init_amt = _zahl(bot, "initOrdAmt", 0.0)
    safety_amt = _zahl(bot, "safetyOrdAmt", 0.0)
    gefuellt = _zahl(details, "fillSafetyOrds", 0.0) or 0.0
    margin_ist = init_amt + gefuellt * safety_amt
    liq_abstand = 1.0 - liq / avg
    rest = liq_abstand - margin_ist / notional
    ziel_abstand = 1.0 - ziel_boden / avg
    noetig = max(0.0, (ziel_abstand - liq_abstand) * notional)
    return {"margin_ist": round(margin_ist, 2), "notional_usd": round(notional, 2),
            "liq_abstand_prozent": round(liq_abstand * 100.0, 2),
            "rest_prozent": round(rest * 100.0, 2),
            "ziel_abstand_prozent": round(ziel_abstand * 100.0, 2),
            "noetige_margin_usdc": round(noetig, 2),
            "rest_hoch": rest > 0.05}


def koerper_margin(algo_id, amt):
    return {"algoId": str(algo_id), "amt": ("%g" % float(amt))}


def koerper_amend(algo_id, px_steps, px_steps_mult, vol_mult, tp_pct, sl_pct,
                  init_amt, safety_amt, max_safety, reserve=False):
    """Der vollstaendige Koerper - die Boerse verlangt ALLE Felder."""
    return {
        "algoId": str(algo_id),
        "pxSteps": ("%g" % float(px_steps)),
        "pxStepsMult": ("%g" % float(px_steps_mult)),
        "volMult": ("%g" % float(vol_mult)),
        "tpPct": ("%g" % float(tp_pct)),
        "slPct": ("%g" % float(sl_pct)),
        "initOrdAmt": ("%g" % float(init_amt)),
        "safetyOrdAmt": ("%g" % float(safety_amt)),
        "maxSafetyOrds": str(int(max_safety)),
        "reserveFunds": bool(reserve),
        "triggerParams": [{"triggerAction": "start", "triggerStrategy": "instant"}],
    }


def plan_fuer_bot(bot, details, orders, kurs, kerzen, w, a):
    """Alt gegen neu rechnen - und sagen, was das Geld dazu sagt."""
    geo = a
    alt_stufen = _zahl(bot, "maxSafetyOrds", 0.0)
    alt_schritt = _zahl(bot, "pxSteps", 0.0)
    init_amt = _zahl(bot, "initOrdAmt", 0.0)
    safety_amt = _zahl(bot, "safetyOrdAmt", 0.0)
    mult = _zahl(bot, "pxStepsMult", 1.0)
    vol_mult = _zahl(bot, "volMult", 1.0)
    grenze, _, _ = bots.letzte_kaufgrenze(orders, [])
    liq = _zahl(details, "liqPx")
    avg = _zahl(details, "avgPx")
    gefuellt = _zahl(details, "fillSafetyOrds", 0.0)

    # Vorschlag aus der Analyse (ATR-Regel), sofern keine Vorgabe kommt
    z = {"kurs": kurs, "atr_prozent_14": analyse.atr_prozent(kerzen),
         "max_rueckgang_90": analyse.max_rueckgang(kerzen, 90),
         "max_rueckgang_180": analyse.max_rueckgang(kerzen, 180),
         "max_rueckgang_365": analyse.max_rueckgang(kerzen, 365),
         "letzter_boden_90": analyse.letzter_boden(kerzen, 90),
         "leiter_tiefe_prozent": alt_stufen * alt_schritt * 100.0}
    e = analyse.empfehlung(z, max_stufen=int(w.get("dca_max_steps") or 12))

    # Was der Bot HEUTE hat: die ongoing-list nennt tpPct/slPct nicht immer,
    # deshalb aus den Preisen rechnen (tpPx bzw. slPx gegen den Einstand).
    tp_px = _zahl(details, "tpPx")
    sl_px = _zahl(details, "slPx")
    bot_tp = _zahl(bot, "tpPct")
    quelle_tp = "Feld"
    if bot_tp is None and tp_px and avg:
        bot_tp = tp_px / avg - 1.0
        quelle_tp = "aus tpPx %s / Einstand %s" % (tp_px, round(avg, 6))
    bot_sl = _zahl(bot, "slPct")
    quelle_sl = "Feld"
    if bot_sl is None and sl_px and avg:
        bot_sl = 1.0 - sl_px / avg
        quelle_sl = "aus slPx %s" % sl_px
    if bot_sl is None:
        bot_sl = 0.0

    # Vorgabe: NICHTS erfinden. Ein Amend ohne ausdrueckliche Wahl laesst Leiter
    # und Stop, wie sie sind - sonst setzt ein Amend still einen Stop, den es
    # nie gab (oder nimmt einen weg).
    neu_stufen = int(geo.stufen if geo.stufen else (int(alt_stufen) if not geo.schritt
                                                   else int(e.get("stufen") or alt_stufen)))
    if geo.schritt:
        neu_schritt = float(geo.schritt) / 100.0
        neu_stufen = int(geo.stufen or e.get("stufen") or alt_stufen)
    elif geo.stufen:
        neu_schritt = float(e.get("ziel_tiefe_prozent") or 0.0) / 100.0 / max(1, neu_stufen)
    else:
        neu_schritt = alt_schritt
    neu_tp = float(geo.tp_pct if geo.tp_pct is not None else (bot_tp or 0.0))
    neu_sl = float(geo.sl_pct if geo.sl_pct is not None else bot_sl)
    if geo.nur_schutz:
        neu_stufen, neu_schritt = int(alt_stufen), alt_schritt
        neu_tp = float(geo.tp_pct if geo.tp_pct is not None else (bot_tp or 0.0))

    tiefe_neu = neu_stufen * neu_schritt * 100.0
    zusaetzliche = max(0, neu_stufen - (gefuellt or 0))
    bedarf = zusaetzliche * safety_amt
    frei = freies_guthaben("USDC")
    kurs_fuer_boden = grenze or kurs
    # Boden des NEUEN Plans vom ersten Kauf aus: bei laufendem Bot ist der
    # erste Kauf der Einstand - der Plan wird von dort aus nach unten gelegt.
    basis = avg if avg else kurs
    plan_boden = basis * (1 - tiefe_neu / 100.0)

    warnungen = []
    if bedarf > 0 and frei is not None and bedarf > frei:
        warnungen.append("die %d zusaetzlichen Stufen brauchen rund %.2f USDC, frei sind "
                         "%.2f - sie entstehen, koennen aber nicht fuellen."
                         % (zusaetzliche, bedarf, frei))
    if neu_sl and avg and plan_boden >= avg * (1 - neu_sl):
        warnungen.append("slPct %s (%s) liegt UEBER dem Planboden %s - der Stop greift vor "
                         "der tiefsten Stufe" % (neu_sl, round(avg * (1 - neu_sl), 6),
                                                 round(plan_boden, 6)))
    if liq and plan_boden <= liq:
        warnungen.append("der Planboden %s liegt UNTER der Liquidation %s - die tiefsten "
                         "Stufen erreicht der Bot nie" % (round(plan_boden, 6), liq))
    if geo.nur_schutz and not neu_sl:
        warnungen.append("ohne slPct aendert --nur-schutz nichts")

    return {
        "algoId": str(bot.get("algoId")), "inst": bot.get("instId"),
        "kurs": kurs, "avgPx": avg, "letzte_grenze": grenze, "liqPx": liq,
        "alt": {"stufen": int(alt_stufen), "schritt_prozent": round(alt_schritt * 100.0, 4),
                "tiefe_prozent": round(alt_stufen * alt_schritt * 100.0, 2),
                "gefuellt": int(gefuellt or 0), "tpPct": bot_tp, "slPct": bot_sl,
                "tp_quelle": quelle_tp, "sl_quelle": quelle_sl},
        "neu": {"stufen": neu_stufen, "schritt_prozent": round(neu_schritt * 100.0, 4),
                "tiefe_prozent": round(tiefe_neu, 2), "tpPct": round(neu_tp, 4),
                "slPct": round(neu_sl, 4), "planboden": round(plan_boden, 6)},
        "empfehlung_atr": {k: e.get(k) for k in ("ziel_tiefe_prozent", "stufen",
                                                 "schritt_prozent", "atr_prozent_14",
                                                 "letzter_boden_90", "sl_pct")},
        "margin": margin_bedarf(details, bot, plan_boden),
        "bedarf_usdc": round(bedarf, 2), "frei_usdc": frei,
        "koerper": koerper_amend(bot.get("algoId"), neu_schritt, mult, vol_mult, neu_tp,
                                 neu_sl, init_amt, safety_amt, neu_stufen,
                                 reserve=bool(geo.reserve)),
        "warnungen": warnungen + list(e.get("warnungen") or []),
    }


def protokoll(eintrag):
    with open(JOURNAL, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Parameter laufender OKX-DCA-Bots anpassen")
    ap.add_argument("--stufen", type=int, default=None, help="neue Zahl der Sicherungsstufen")
    ap.add_argument("--schritt", type=float, default=None, help="neuer Abstand in Prozent")
    ap.add_argument("--tp-pct", type=float, default=None)
    ap.add_argument("--sl-pct", type=float, default=None,
                    help="Stop der Boerse, z.B. 0.20 fuer 20 %% unter dem Einstand")
    ap.add_argument("--nur-schutz", action="store_true",
                    help="nur tpPct/slPct setzen, die Leiter nicht anfassen")
    ap.add_argument("--reserve", action="store_true",
                    help="reserveFunds=true (Geld fuer Sicherungsstufen reservieren)")
    ap.add_argument("--margin", type=float, default=None,
                    help="Margin an diesen Bot nachschiessen (dca/margin/add), drueckt die "
                         "Liquidation nach unten")
    ap.add_argument("--nur", default=None, help="nur diese algoId anfassen")
    ap.add_argument("--anwenden", action="store_true", help="wirklich senden")
    a = ap.parse_args(argv)

    w = waechter.lade_wachen()
    if a.anwenden and not any([a.stufen, a.schritt, a.tp_pct, a.sl_pct, a.nur_schutz,
                               a.margin]):
        print("GESPERRT: keine Aenderung gewaehlt. --anwenden braucht --stufen, --schritt, "
              "--sl-pct, --tp-pct oder --nur-schutz - sonst wuerde ein Amend die Werte "
              "stillschweigend neu schreiben.")
        return 2
    if not w.get("anpassen_erlaubt") and a.anwenden:
        print("GESPERRT: anpassen_erlaubt steht auf false in wachen.json - es wurde nichts "
              "gesendet. (Ein Amend aendert einen LAUFENDEN Bot mit echtem Geld.)")
        return 2

    pläne = []
    for b in bots.dca_laufend():
        if a.nur and str(b.get("algoId")) != str(a.nur):
            continue
        try:
            det = bots.dca_details(b["algoId"])
            zyk = bots.dca_zyklen(b["algoId"])
            cid = None
            for c in zyk or []:
                if c.get("currentCycle") in (True, "true", "1"):
                    cid = c.get("cycleId")
            if cid is None and zyk:
                cid = zyk[-1].get("cycleId")
            ords = bots.dca_orders(b["algoId"], cid) if cid else []
            kurs = bots.kurs(b.get("instId"))
            kerzen = bots.kerzen(b.get("instId"), "1D", 365) or []
            pläne.append(plan_fuer_bot(b, det, ords, kurs, kerzen, w, a))
        except Exception as e:
            print("FEHLER %s: %s: %s" % (b.get("instId"), type(e).__name__, e))
    if not pläne:
        print("kein laufender Future-DCA-Bot gefunden")
        return 1

    for p in pläne:
        print("%-26s Kurs %s | Stufen %d x %s%% = %s%% tief  ->  %d x %s%% = %s%% tief"
              % (p["inst"], p["kurs"], p["alt"]["stufen"], p["alt"]["schritt_prozent"],
                 p["alt"]["tiefe_prozent"], p["neu"]["stufen"], p["neu"]["schritt_prozent"],
                 p["neu"]["tiefe_prozent"]))
        print("%-26s Planboden %s (Einstand %s, Liquidation %s) | tpPct %s -> %s | "
              "slPct %s -> %s"
              % ("", p["neu"]["planboden"], p["avgPx"], p["liqPx"],
                 p["alt"]["tpPct"], p["neu"]["tpPct"], p["alt"]["slPct"], p["neu"]["slPct"]))
        print("%-26s zusaetzliche Stufen brauchen %s USDC, frei sind %s"
              % ("", p["bedarf_usdc"], p["frei_usdc"]))
        if p.get("margin"):
            m = p["margin"]
            print("%-26s Wand: Liquidation %s unter dem Einstand = %s%% | Leiterbetraege "
                  "heute %s von %s notional (Rest %s%%%s)"
                  % ("", p["liqPx"], m["liq_abstand_prozent"], m["margin_ist"],
                     m["notional_usd"], m["rest_prozent"],
                     " = mehr Margin als die Leiter hergibt" if m["rest_hoch"] else ""))
            if m["noetige_margin_usdc"] > 0:
                print("%-26s fuer eine Leiter bis %s%% tief fehlen %s USDC Margin an diesem "
                      "Bot" % ("", m["ziel_abstand_prozent"], m["noetige_margin_usdc"]))
        print("%-26s Stop heute: %s (%s) | Vorschlag der Analyse: slPct %s"
              % ("", p["alt"]["slPct"], p["alt"]["sl_quelle"],
                 (p["empfehlung_atr"] or {}).get("sl_pct")))
        for w_ in p["warnungen"]:
            print("%-26s WARNUNG: %s" % ("", w_))
        if a.margin:
            koerper_m = koerper_margin(p["algoId"], a.margin)
            if a.anwenden:
                try:
                    antwort = bots.sende("/api/v5/tradingBot/dca/margin/add", koerper_m)
                    protokoll({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "art": "margin", "algoId": p["algoId"], "inst": p["inst"],
                               "amt": a.margin, "antwort": antwort})
                    print("%-26s MARGIN %s USDC nachgeschossen: %s"
                          % ("", a.margin, json.dumps(antwort, ensure_ascii=False)[:160]))
                except Exception as e:
                    protokoll({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "art": "margin", "algoId": p["algoId"], "inst": p["inst"],
                               "amt": a.margin, "fehler": str(e)})
                    print("%-26s FEHLER beim Margin-Nachschuss: %s" % ("", e))
            else:
                print("%-26s Margin-Koerper: %s" % ("", json.dumps(koerper_m)))
        if a.anwenden and (a.nur_schutz or a.stufen or a.schritt or a.tp_pct is not None
                           or a.sl_pct is not None):
            try:
                antwort = bots.sende("/api/v5/tradingBot/dca/amend-order-algo", p["koerper"])
                protokoll({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "art": "amend", "algoId": p["algoId"], "inst": p["inst"],
                           "alt": p["alt"], "neu": p["neu"], "koerper": p["koerper"],
                           "antwort": antwort})
                print("%-26s ANGEPASST: %s" % ("", json.dumps(antwort, ensure_ascii=False)[:200]))
            except Exception as e:
                protokoll({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "art": "amend", "algoId": p["algoId"], "inst": p["inst"],
                           "fehler": "%s: %s" % (type(e).__name__, e)})
                print("%-26s FEHLER beim Amend: %s" % ("", e))
        else:
            print("%-26s Koerper: %s" % ("", json.dumps(p["koerper"], ensure_ascii=False)))
        print()
    if not a.anwenden:
        print("Trockenlauf. Mit --anwenden senden (Tor: anpassen_erlaubt=true in wachen.json).")
    return 0


if __name__ == "__main__":
    sys.exit(main())