"""Das Schema der laufenden Bots ANALYSIEREN - warum die Leiter leerlief.

Kernfrage: Die Sicherungsstufen eines Future-DCA sind ein Vorrat. Ist er
verbraucht und der Kurs faellt weiter, kauft der Bot nicht mehr nach und die
Position laeuft ungebremst in die Liquidation. Also muss die TIEFE der Leiter
zu dem passen, was das Instrument tatsaechlich macht.

Gemessen wird je Bot und je Instrument, aus den eigenen Tageskerzen:

* `leiter_tiefe_prozent`  - wie weit die Stufen reichen (maxSafetyOrds * pxSteps)
* `rueckgang_seit_einstieg` - wie weit der Kurs seit dem ersten Kauf gefallen ist
* `ueberschossen_prozent` - wie weit er UNTER die tiefste Stufe gelaufen ist
* `atr_prozent` (14 Tage) - die taegliche Bewegung
* `max_rueckgang_90_180_365` - der tiefste Rueckgang vom jeweiligen Hoch
* `abstand_zur_liquidation`

Daraus die Empfehlung fuer einen NEUEN Bot: die Leiter muss tiefer reichen als
der beobachtete Rueckgang (Barriere-Zone), die Stufen duerfen dabei nicht zu
grob werden, und die Liquidation muss darunter liegen.

Aufruf (aus diesem Ordner):  python analyse.py [--instrument X-USD_UM_XPERP-...]
"""
import argparse
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import bots        # noqa: E402
import waechter     # noqa: E402

assert waechter.__file__.startswith(HIER)


def atr_prozent(kerzen, tage=14):
    """Mittlere Tagesspanne in Prozent des Schlusses."""
    if len(kerzen) < tage + 1:
        return None
    spannen = [(float(k[2]) - float(k[3])) / float(k[4]) for k in kerzen[-(tage + 1):-1]]
    return sum(spannen) / len(spannen) * 100.0


def max_rueckgang(kerzen, tage):
    """Tiefster Rueckgang vom jeweils vorherigen Hoch, in Prozent."""
    reihe = kerzen[-int(tage):]
    if len(reihe) < 3:
        return None
    hoch, tiefster = None, 0.0
    for k in reihe:
        c = float(k[4])
        hoch = c if hoch is None else max(hoch, c)
        if hoch:
            tiefster = min(tiefster, c / hoch - 1.0)
    return tiefster * 100.0


def lage_einer_leiter(bot, details, orders, kurs, kerzen):
    """Eine Zeile Wahrheit je Bot: was war geplant, was ist passiert."""
    max_stufen = float(bot.get("maxSafetyOrds") or 0)
    schritt = float(bot.get("pxSteps") or 0)
    tiefe = max_stufen * schritt * 100.0                 # Prozent unter dem Start
    grenze, belegt, geplant = bots.letzte_kaufgrenze(orders, [])
    init = float((details or {}).get("initPx") or (bot.get("initPx") or 0) or 0)
    liq = float((details or {}).get("liqPx") or 0)
    rueckgang = (kurs / init - 1.0) * 100.0 if init else None
    ueberschossen = (kurs / grenze - 1.0) * 100.0 if grenze else None
    return {
        "algoId": str(bot.get("algoId")),
        "inst": bot.get("instId"),
        "stufen": int(max_stufen), "schritt_prozent": round(schritt * 100.0, 4),
        "leiter_tiefe_prozent": round(tiefe, 3),
        "initPx": init or None, "eur_avg": (details or {}).get("avgPx"),
        "letzte_grenze": grenze,
        "kurs": kurs,
        "rueckgang_seit_einstieg_prozent": round(rueckgang, 2) if rueckgang is not None else None,
        "ueberschossen_prozent": round(ueberschossen, 2) if ueberschossen is not None else None,
        "munition": bots.munition(bot.get("maxSafetyOrds"), (details or {}).get("fillSafetyOrds")),
        "liqPx": liq or None,
        "abstand_zur_liquidation_prozent": bots.liq_abstand(kurs, liq) if liq else None,
        "atr_prozent_14": round(atr_prozent(kerzen) or 0, 3) if kerzen else None,
        "max_rueckgang_90": round(max_rueckgang(kerzen, 90) or 0, 2) if kerzen else None,
        "max_rueckgang_180": round(max_rueckgang(kerzen, 180) or 0, 2) if kerzen else None,
        "max_rueckgang_365": round(max_rueckgang(kerzen, 365) or 0, 2) if kerzen else None,
        "kerzen": len(kerzen) if kerzen else 0,
        "letzter_boden_90": letzter_boden(kerzen, 90) if kerzen else None,
    }


def wochen_trend(kerzen_woche, fenster=30, vergleich=4):
    """Der uebergeordnete Trend im Wochenchart - als Zahl, nicht als Gefuehl.

    Definition (bewusst einfach und nachpruefbar): Durchschnitt der letzten
    `fenster` Wochenschlusskurse gegen denselben Durchschnitt `vergleich`
    Wochen frueher, dazu der letzte Kurs gegen den Durchschnitt.

    aufwaerts   = Kurs ueber dem Durchschnitt UND der Durchschnitt steigt
    abwaerts    = Kurs unter dem Durchschnitt UND der Durchschnitt faellt
    seitwaerts  = alles andere (die beiden Zeugen widersprechen sich)
    """
    reihen = [float(k[4]) for k in (kerzen_woche or [])]
    if len(reihen) < fenster + vergleich:
        return {"lage": "unbekannt", "kerzen": len(reihen),
                "hinweis": "zu wenig Wochenkerzen (%d, noetig %d)"
                           % (len(reihen), fenster + vergleich)}
    jetzt = sum(reihen[-fenster:]) / fenster
    davor = sum(reihen[-(fenster + vergleich):-vergleich]) / fenster
    kurs = reihen[-1]
    if kurs > jetzt and jetzt > davor:
        lage = "aufwaerts"
    elif kurs < jetzt and jetzt < davor:
        lage = "abwaerts"
    else:
        lage = "seitwaerts"
    return {"lage": lage, "kurs": kurs, "sma": round(jetzt, 6), "sma_davor": round(davor, 6),
            "sma_steigt": jetzt > davor, "kurs_ueber_sma": kurs > jetzt,
            "kurs_ueber_sma_prozent": round((kurs / jetzt - 1.0) * 100.0, 2) if jetzt else None,
            "kerzen": len(reihen),
            "wochen_seit_hoch_prozent": round(
                (kurs / max(reihen) - 1.0) * 100.0, 2)}


def _betrag(z):
    return abs(float(z)) if z is not None else 0.0


def letzter_boden(kerzen, tage=90):
    """Tiefstes Tief der letzten Tage - die Barriere, unter der der Markt war."""
    reihe = kerzen[-int(tage):]
    if not reihe:
        return None
    return min(float(k[3]) for k in reihe)


def empfehlung(zeile, max_stufen=12, atr_vielfaches=3.0, band=(0.15, 0.5),
               liq_abstand=0.05, mindest_tiefe=10.0, hoechst_tiefe=60.0,
               mindest_schritt=0.3, kleiner_schritt=2.5, hoechst_schritt=5.0):
    """Welche Leiter passt zu DIESEM Instrument?

    Die Regel steht in ATR-Einheiten, nicht in Prozent: eine Leiter muss tiefer
    reichen als das Instrument an einem guten Tag laeuft, sonst ist sie an
    einem einzigen Tag verbraucht (gemessen: ATR 8-13 %/Tag bei Leitern von
    4-8 % Tiefe - deshalb liefen alle fuenf leer).

    * Tiefe   = max(3 x ATR, beobachteter 90/180/365-Tage-Rueckgang, 10 %) - nie ueber 60 %
    * Abstand = mindestens 0,15 x ATR und 0,3 %; hoechstens 0,5 x ATR und 5 %,
                aber nie kleiner als 2,5 % - eine Stufe muss eine echte Bewegung
                sein, sonst verbraucht die Leiter sich an Rauschen
    * Hebel   so, dass die Liquidation 5 % UNTER dem Planboden liegt
    """
    atr = float(zeile.get("atr_prozent_14") or 0)
    kandidaten = [_betrag(zeile.get(k)) for k in
                  ("max_rueckgang_90", "max_rueckgang_180", "max_rueckgang_365")]
    beobachtet = max(kandidaten) if kandidaten else 0.0
    if not atr and not beobachtet:
        return {"fehler": "keine Kerzen - keine Empfehlung"}
    ziel = max(atr_vielfaches * atr, beobachtet, mindest_tiefe)
    ziel = min(ziel, hoechst_tiefe)
    warnungen = []

    if atr:
        schritt_min = max(band[0] * atr, mindest_schritt)
        schritt_max = min(max(band[1] * atr, kleiner_schritt), hoechst_schritt)
        noetig = int(round(ziel / schritt_min)) or 2          # feinste sinnvolle Stufe
        stufen = max(2, min(noetig, int(max_stufen)))
        schritt = ziel / stufen
        if schritt > schritt_max:                             # zu grob -> Tiefe zuruecknehmen
            warnungen.append("Stufen (%d) sind bei diesem Instrument der Engpass: der Abstand "
                             "waere %.2f %%, gedeckelt auf %.2f %% - die Leiter wird damit nur "
                             "%.2f %% tief (noetig waeren %d Stufen)."
                             % (stufen, schritt, schritt_max, schritt_max * stufen, noetig))
            schritt = schritt_max
            ziel = schritt * stufen
        if noetig > int(max_stufen):
            warnungen.append("%d Stufen waeren noetig, %d sind erlaubt (dca_max_steps)."
                             % (noetig, int(max_stufen)))
    else:                                                     # ohne ATR bleibt der Rueckgang
        stufen = max(2, min(int(max_stufen), 10))
        schritt = ziel / stufen
        warnungen.append("keine ATR-Messung - Abstand aus dem Rueckgang gerechnet")

    kurs = zeile["kurs"]
    plan_boden = kurs * (1 - ziel / 100.0)
    avg = kurs * (1 - ziel / 200.0)
    ziel_liq = plan_boden * (1 - liq_abstand)
    hebel = int(min(10, max(1, 1.0 / (1.0 - ziel_liq / avg)))) if avg > 0 else 1
    boden_90 = zeile.get("letzter_boden_90")
    if boden_90 and plan_boden > boden_90:
        warnungen.append("der Planboden %.6f liegt UEBER dem 90-Tage-Tief %.6f - die Leiter "
                         "endet, bevor der Markt dort war" % (plan_boden, boden_90))
    reicht = (zeile.get("leiter_tiefe_prozent") or 0) >= ziel
    return {
        "instrument_rueckgang_180_prozent": round(beobachtet, 2),
        "atr_prozent_14": round(atr, 3),
        "atr_vielfaches": atr_vielfaches,
        "ziel_tiefe_prozent": round(ziel, 2),
        "stufen": stufen,
        "stufen_noetig_fuer_ziel": noetig if atr else None,
        "schritt_prozent": round(schritt, 4),   # schritt ist hier BEREITS Prozent (ATR-Einheiten)
        "planboden": round(plan_boden, 6),
        "avg_wenn_voll": round(avg, 6),
        "hebel": hebel,
        "liq_bei_hebel": round(avg * (1 - 1.0 / hebel), 6) if hebel else None,
        "sl_pct": round((avg - plan_boden) / avg, 4) if avg else None,
        "letzter_boden_90": boden_90,
        "leiter_reicht": reicht,
        "warnungen": warnungen,
        "hinweis": ("Die alte Leiter war %s %% tief, gebraucht werden %s %% - %s"
                    % (zeile.get("leiter_tiefe_prozent"), round(ziel, 2),
                       "ausreichend" if reicht else "ZU KURZ")),
    }


def sammle_analyse(w):
    zeilen, roh = [], {}
    for b in bots.dca_laufend():
        inst = b.get("instId")
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
            kurs = bots.kurs(inst)
            kerzen = bots.kerzen(inst, "1D", 365) or []
            z = lage_einer_leiter(b, det, ords, kurs, kerzen)
            z["empfehlung"] = empfehlung(z, max_stufen=int(w.get("dca_max_steps") or 12))
            zeilen.append(z)
            roh[inst] = {"algoId": b["algoId"], "kurs": kurs}
        except Exception as e:
            zeilen.append({"algoId": b.get("algoId"), "inst": inst,
                           "fehler": "%s: %s" % (type(e).__name__, e)})
    return zeilen, roh


def main(argv=None):
    a = argparse.ArgumentParser(description="Schema der OKX-DCA-Bots analysieren")
    a.add_argument("--json", action="store_true", help="Maschinenlesbar ausgeben")
    a.add_argument("--woche", action="store_true",
                   help="nur den uebergeordneten Trend im Wochenchart zeigen")
    args = a.parse_args(argv)

    w = waechter.lade_wachen()
    if args.woche:
        for b in bots.dca_laufend():
            inst = b.get("instId")
            basis = str(inst).split("-")[0]
            # Die Kontrakte selbst sind zu jung fuer einen Wochenchart (7-26 Kerzen).
            # Der Trend des Underlyings kommt vom SPOT-Paar - dort liegen Jahre.
            quelle, kw = None, None
            for kandidat in ("%s-USDT" % basis, "%s-USDC" % basis, inst):
                try:
                    reihe = bots.kerzen(kandidat, "1W", 200) or []
                except Exception:
                    reihe = []
                if len(reihe) >= 34:
                    quelle, kw = kandidat, reihe
                    break
                if kw is None or len(reihe) > len(kw):
                    quelle, kw = kandidat, reihe
            tr = wochen_trend(kw or [])
            print("%-26s Woche: %-10s (%-12s Kurs %s gegen Durchschnitt %s, der %s) - %s %% "
                  "unter dem Wochenhoch, %d Wochenkerzen"
                  % (inst, tr.get("lage"), quelle, tr.get("kurs"), tr.get("sma"),
                     "steigt" if tr.get("sma_steigt") else "faellt",
                     tr.get("wochen_seit_hoch_prozent"), tr.get("kerzen") or 0,
                     ))
            print("%-26s        Abstand zum Durchschnitt: %s %% (der Durchschnitt holt auf)"
                  % ("", tr.get("kurs_ueber_sma_prozent")))
        return 0
    zeilen, _ = sammle_analyse(w)
    if args.json:
        print(json.dumps(zeilen, ensure_ascii=False, indent=1))
        return 0
    for z in zeilen:
        if z.get("fehler"):
            print("FEHLER %s: %s" % (z.get("inst"), z["fehler"]))
            continue
        e = z.get("empfehlung") or {}
        print("%-26s Stufen %2d x %s%% = %6.2f%% tief | Rueckgang seit Kauf %7.2f%% | "
              "unter der Grenze %7.2f%%"
              % (z["inst"], z["stufen"], z["schritt_prozent"], z["leiter_tiefe_prozent"],
                 z["rueckgang_seit_einstieg_prozent"] or 0,
                 z["ueberschossen_prozent"] or 0))
        print("%-26s ATR %5.2f%%/Tag | max. Rueckgang 90/180/365 Tage: %6.2f%% / %6.2f%% / %6.2f%%"
              % ("", z["atr_prozent_14"] or 0, z["max_rueckgang_90"] or 0,
                 z["max_rueckgang_180"] or 0, z["max_rueckgang_365"] or 0))
        if e.get("fehler"):
            print("%-26s %s" % ("", e["fehler"]))
        else:
            print("%-26s SOLL: %d Stufen a %s%% = %.2f%% tief (Boden %s, Hebel %d, Liq %s, "
                  "slPct %s) - %s"
                  % ("", e["stufen"], e["schritt_prozent"], e["ziel_tiefe_prozent"],
                     e["planboden"], e["hebel"], e["liq_bei_hebel"], e["sl_pct"],
                     e["hinweis"]))
            if e.get("letzter_boden_90"):
                print("%-26s 90-Tage-Tief %s | ATR %s%%/Tag | Struktur %s"
                      % ("", e["letzter_boden_90"], e.get("atr_prozent_14"),
                         "Leiter endet unter dem Tief"
                         if e["planboden"] <= e["letzter_boden_90"]
                         else "Leiter endet UEBER dem Tief"))
            for w_ in e.get("warnungen") or []:
                print("%-26s WARNUNG: %s" % ("", w_))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())