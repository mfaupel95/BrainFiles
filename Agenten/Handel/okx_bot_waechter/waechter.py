"""Waechter ueber die echten OKX-Bots: laeuft ein Bot aus seiner letzten
kaufbaren Grenze heraus, wird er gestoppt - die Nachbildung eines Stop-Loss.

Warum das die Luecke schliesst: beide Botarten haben in Max' Konto `slPx`-leer
bzw. `slTriggerPx`-leer, also KEINEN boersenseitigen Stop. Ein Future-DCA kauft
planmaessig nach unten (`maxSafetyOrds` Sicherungskaeufe); sind sie alle
gefuellt und der Kurs faellt weiter, passiert GAR NICHTS mehr - die Position
laeuft ungebremst in die Liquidation. Genau dort greift dieser Waechter.

Die drei Grenzen, an denen er entscheidet:

1. **Letzte kaufbare Grenze** (Kern der Aufgabe): die tiefste Kaufstufe des
   laufenden Zyklus - bei einem DCA aus der Auftragsliste (`px`), gegengeprueft
   gegen die geplante Stufe (`initPx`, `pxSteps`, `pxStepsMult`,
   `maxSafetyOrds`); bei einem Grid die untere Grenze `minPx` (bzw. `maxPx` bei
   direction=short). Faellt der Kurs darunter (abzueglich `reserve_prozent`),
   kann der Bot nicht mehr nachkaufen -> `AUSGELAUFEN` -> **Stopp**.
2. **Munition**: `maxSafetyOrds - fillSafetyOrds`. 0 heisst: der naechste Weg
   nach unten hat keinen Kaeufer mehr -> `KNAPP`.
3. **Liquidation**: Abstand zum `liqPx`. Unter `liq_notfall_prozent` -> `NOTFALL`
   -> Stopp, unter `liq_warnung_prozent` -> `WARNUNG`.

Tore: `stop_erlaubt` in wachen.json UND `--anwenden`. Ohne beides ist jeder Lauf
ein Bericht. Je Bot kann `scharf: false` den Stopp zurueckhalten.

Aufruf (aus diesem Ordner):
    python waechter.py                 # Bericht
    python waechter.py --kurz          # je Bot eine Zeile
    python waechter.py --historie      # + geschlossene Grids (T-076)
    python waechter.py --anwenden      # stoppt, wenn Tor und Lage es hergeben
"""
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)
import bots  # noqa: E402

WACHEN = os.path.join(HIER, "wachen.json")
JOURNAL = os.path.join(HIER, "bot_waechter_journal.jsonl")
ZUSTAND = os.path.join(HIER, "zustand.json")

STOP_LAGEN = ("AUSGELAUFEN", "NOTFALL")


def jetzt():
    return datetime.now(timezone.utc)


def jz(ms):
    """OKX-Zeit (Millisekunden seit Epoche) als lesbarer Text."""
    try:
        return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).strftime("%d.%m. %H:%M")
    except (TypeError, ValueError):
        return "-"


def lade_wachen(pfad=WACHEN):
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def f(x, stellen=6):
    """Kurszahl ohne Exponentialschreibweise - 1e-05 liest niemand."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "-"
    if v == 0:
        return "0"
    if abs(v) >= 1000:
        return "%.2f" % v
    if abs(v) >= 1:
        return "%.4f" % v
    return ("%." + str(stellen) + "f") % v


# --- Die Bewertung: reine Funktion, ohne Netz testbar ------------------------

def bot_scharf(algo, w):
    """Tor je Bot: stop_erlaubt UND nicht ausdruecklich unscharf."""
    if not w.get("stop_erlaubt"):
        return False, "stop_erlaubt ist aus (wachen.json)"
    ausnahme = (w.get("bots") or {}).get(str(algo)) or {}
    if ausnahme.get("scharf") is False:
        return False, "Bot %s ist auf scharf=false gesetzt" % algo
    return True, ""


def bewerte_dca(bot, details, orders, kurs, w):
    """Lage eines Future-DCA-Bots."""
    art = "Future-DCA"
    max_safety = bot.get("maxSafetyOrds")
    gefuellt = details.get("fillSafetyOrds")
    rest = bots.munition(max_safety, gefuellt)
    plan = bots.stufen_plan(details.get("initPx"), bot.get("pxSteps"),
                            bot.get("pxStepsMult"), max_safety)
    grenze, belegt, geplant = bots.letzte_kaufgrenze(orders, plan)
    liq = details.get("liqPx")
    abstand = bots.liq_abstand(kurs, liq)
    reserve = float(w.get("reserve_prozent") or 0.0)
    gruende = []

    lage = "OK"
    if grenze and kurs:
        schwelle = grenze * (1 - reserve / 100.0)
        if kurs < schwelle:
            lage = "AUSGELAUFEN"
            gruende.append("Kurs %s unter der letzten Kaufgrenze %s (kein Nachkauf mehr)"
                           % (f(kurs), f(grenze)))
        elif kurs < grenze:
            lage = "KNAPP"
            gruende.append("Kurs %s schon unter der Kaufgrenze %s" % (f(kurs), f(grenze)))
    if rest == 0 and lage == "OK":
        lage = "KNAPP"
        gruende.append("alle %s Sicherungskaeufe gefuellt - keine Munition mehr" % max_safety)
    if abstand is not None:
        if float(w.get("liq_notfall_prozent") or 0) and abstand <= float(w["liq_notfall_prozent"]):
            lage = "NOTFALL"
            gruende.append("nur %s%% bis zur Liquidation (%s)" % (f(abstand, 1), f(liq)))
        elif abstand <= float(w.get("liq_warnung_prozent") or 0):
            lage = "NOTFALL" if lage == "AUSGELAUFEN" else "WARNUNG"
            gruende.append("%s%% bis zur Liquidation (%s)" % (f(abstand, 1), f(liq)))
    if not details.get("slPx"):
        gruende.append("kein boersenseitiger Stop gesetzt (slPx leer)")

    return {
        "algoId": str(bot.get("algoId") or ""), "art": art, "inst": bot.get("instId"),
        "richtung": bot.get("direction"), "lage": lage,
        "kurs": kurs, "grenze": grenze, "stufe_belegt": belegt, "stufe_geplant": geplant,
        "munition": rest, "max_safety": max_safety, "gefuellt": gefuellt,
        "liqPx": liq, "liq_abstand": abstand,
        "pnl_prozent": 100 * float(bot.get("pnlRatio") or 0),
        "total_pnl": float(bot.get("totalPnl") or 0),
        "invest": float(bot.get("investmentAmt") or 0),
        "ccy": bot.get("investmentCcy"), "hebel": bot.get("lever"),
        "seit": jz(bot.get("cTime")), "gruende": gruende,
    }


def bewerte_grid(bot, details, kurs, w):
    """Lage eines Future-Grid-Bots. Untere Grenze: minPx, bei short maxPx."""
    d = dict(bot)
    d.update({k: v for k, v in (details or {}).items() if v not in ("", None)})
    richtung = (d.get("direction") or "").lower()
    try:
        unten, oben = float(d.get("minPx") or 0), float(d.get("maxPx") or 0)
    except (TypeError, ValueError):
        unten, oben = 0.0, 0.0
    if richtung == "short":
        grenze, seite = (oben or None), "obere Grenze (short)"
    else:
        grenze, seite = (unten or None), "untere Grenze"
    liq = d.get("liqPx")
    abstand = bots.liq_abstand(kurs, liq)
    reserve = float(w.get("reserve_prozent") or 0.0)
    gruende, lage = [], "OK"
    if grenze and kurs:
        raus = kurs < grenze * (1 - reserve / 100.0) if richtung != "short" \
            else kurs > grenze * (1 + reserve / 100.0)
        knapp = (kurs < grenze) if richtung != "short" else (kurs > grenze)
        if raus:
            lage = "AUSGELAUFEN"
            gruende.append("Kurs %s ausserhalb der %s %s - keine Kaufstufe mehr"
                           % (f(kurs), seite, f(grenze)))
        elif knapp:
            lage = "KNAPP"
            gruende.append("Kurs %s an der %s %s" % (f(kurs), seite, f(grenze)))
    if abstand is not None:
        if float(w.get("liq_notfall_prozent") or 0) and abstand <= float(w["liq_notfall_prozent"]):
            lage = "NOTFALL"
            gruende.append("nur %s%% bis zur Liquidation" % f(abstand, 1))
        elif abstand <= float(w.get("liq_warnung_prozent") or 0):
            lage = "NOTFALL" if lage == "AUSGELAUFEN" else "WARNUNG"
            gruende.append("%s%% bis zur Liquidation" % f(abstand, 1))
    if not d.get("slTriggerPx"):
        gruende.append("kein boersenseitiger Stop gesetzt (slTriggerPx leer)")
    return {
        "algoId": str(d.get("algoId") or ""), "art": "Future-Grid", "inst": d.get("instId"),
        "richtung": richtung, "lage": lage, "kurs": kurs, "grenze": grenze,
        "stufe_belegt": None, "stufe_geplant": grenze,
        "munition": None, "max_safety": None, "gefuellt": None,
        "liqPx": liq, "liq_abstand": abstand,
        "pnl_prozent": 100 * float(d.get("pnlRatio") or 0),
        "total_pnl": float(d.get("totalPnl") or 0),
        "invest": float(d.get("investment") or d.get("sz") or 0),
        "ccy": d.get("feeCcy") or "USDC", "hebel": d.get("lever"),
        "seit": jz(d.get("cTime")), "gruende": gruende,
    }


# --- Sammeln, Melden, Stoppen ----------------------------------------------

def sammle(w, nur_dca=False, nur_grid=False):
    """Alle laufenden Bots mit Lage. Fehler je Bot werden gemeldet, nicht geschluckt."""
    raus, fehler = [], []
    if not nur_grid:
        try:
            for b in bots.dca_laufend():
                try:
                    algo = b["algoId"]
                    detail = bots.dca_details(algo)
                    zyklen = bots.dca_zyklen(algo)
                    cid = ""
                    for z in zyklen:
                        if z.get("currentCycle"):
                            cid = z.get("cycleId") or ""
                            break
                    if not cid and zyklen:
                        cid = zyklen[-1].get("cycleId") or ""
                    orders = bots.dca_orders(algo, cid) if cid else []
                    kurs = bots.kurs(b["instId"])
                    raus.append(bewerte_dca(b, detail, orders, kurs, w))
                except Exception as e:
                    fehler.append("DCA %s: %s: %s" % (b.get("instId"), type(e).__name__,
                                                      str(e)[:160]))
        except Exception as e:
            fehler.append("DCA-Liste: %s: %s" % (type(e).__name__, str(e)[:160]))
    if not nur_dca:
        try:
            for b in bots.grid_laufend():
                try:
                    algo = b["algoId"]
                    detail = bots.grid_details(algo)
                    kurs = bots.kurs(b["instId"])
                    raus.append(bewerte_grid(b, detail, kurs, w))
                except Exception as e:
                    fehler.append("Grid %s: %s: %s" % (b.get("instId"), type(e).__name__,
                                                       str(e)[:160]))
        except Exception as e:
            fehler.append("Grid-Liste: %s: %s" % (type(e).__name__, str(e)[:160]))
    return raus, fehler


def zeile(l, kurz=False):
    """Eine Zeile je Bot - der Waechter-Cron schickt genau diese Zeilen."""
    kopf = "%s %s %s" % (l["lage"], l["art"], l["inst"])
    if l.get("richtung"):
        kopf += " (%s x%s)" % (l["richtung"], l.get("hebel") or "-")
    teile = [kopf,
             "Kurs %s" % f(l["kurs"]),
             "Grenze %s" % f(l["grenze"]),
             "Abstand %s" % (("%s%%" % f(100 * (l["kurs"] - l["grenze"]) / l["grenze"], 1))
                             if l.get("grenze") and l.get("kurs") else "-"),
             "Munition %s" % (("%s/%s" % (l["munition"], l["max_safety"]))
                              if l.get("munition") is not None else "-"),
             "Liq %s (%s%%)" % (f(l["liqPx"]),
                                f(l["liq_abstand"], 1) if l.get("liq_abstand") is not None else "-"),
             "PnL %+.1f%%" % l["pnl_prozent"],
             "Einsatz %s %s" % (f(l["invest"], 2), l.get("ccy") or "")]
    if not kurz:
        teile.append("algo %s" % l["algoId"])
    return " | ".join(teile)


def stoppe(l, w):
    """Den Bot stoppen - nur hier, nur hinter dem Tor."""
    stop_art = str((w.get("bots") or {}).get(l["algoId"], {}).get("stop_art")
                   or w.get("stop_art") or "1")
    if l["art"] == "Future-DCA":
        antwort = bots.dca_stoppen(l["algoId"], stop_art)
    else:
        antwort = bots.grid_stoppen(l["algoId"], l["inst"], stop_art)
    grund = "; ".join(l["gruende"]) or l["lage"]
    with open(JOURNAL, "a", encoding="utf-8") as jf:
        jf.write(json.dumps({
            "ts": jetzt().isoformat(timespec="seconds"), "algoId": l["algoId"],
            "art": l["art"], "inst": l["inst"], "lage": l["lage"],
            "stop_art": stop_art, "kurs": l["kurs"], "grenze": l["grenze"],
            "liqPx": l["liqPx"], "pnl_prozent": l["pnl_prozent"],
            "grund": grund, "antwort": antwort,
        }, ensure_ascii=False) + "\n")
    return antwort


def schreibe_zustand(bots_lage, fehler):
    z = {"letzter_lauf": jetzt().isoformat(timespec="seconds"),
         "bots": [{k: v for k, v in l.items() if k != "gruende"} for l in bots_lage],
         "fehler": fehler}
    with open(ZUSTAND, "w", encoding="utf-8") as fh:
        json.dump(z, fh, ensure_ascii=False, indent=1)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    anwenden = "--anwenden" in argv
    kurz = "--kurz" in argv
    historie = "--historie" in argv
    w = lade_wachen()
    lage, fehler = sammle(w)

    print("OKX-Bot-Waechter  %s  Host %s" % (
        jetzt().strftime("%d.%m.%Y %H:%M UTC"), bots.host()))
    if not lage and not fehler:
        print("Keine laufenden Future-Bots (grid/contract_grid, dca/contract_dca).")
    rang = {"NOTFALL": 0, "AUSGELAUFEN": 1, "KNAPP": 2, "WARNUNG": 3, "OK": 4}
    for l in sorted(lage, key=lambda x: (rang.get(x["lage"], 9), x["inst"] or "")):
        print(zeile(l, kurz))
        for g in l["gruende"]:
            print("    - %s" % g)
    for f_ in fehler:
        print("FEHLER %s" % f_)

    kandidaten = [l for l in lage if l["lage"] in STOP_LAGEN]
    if anwenden:
        for l in kandidaten:
            scharf, grund = bot_scharf(l["algoId"], w)
            if not scharf:
                print("GESPERRT %s %s - %s" % (l["inst"], l["algoId"], grund))
                continue
            try:
                antwort = stoppe(l, w)
                print("GESTOPPT %s %s (Stop-Art %s) -> %s"
                      % (l["inst"], l["algoId"], w.get("stop_art") or "1",
                         json.dumps(antwort, ensure_ascii=False)[:200]))
            except Exception as e:
                print("FEHLER beim Stoppen von %s: %s: %s"
                      % (l["inst"], type(e).__name__, str(e)[:200]))
    else:
        if kandidaten:
            print("%d Bot(s) wuerden gestoppt - '--anwenden' fehlt (Vorgabe: nur Bericht)."
                  % len(kandidaten))
            if not w.get("stop_erlaubt"):
                print("Tor zu: stop_erlaubt steht auf false in wachen.json.")
        elif lage:
            print("Kein Bot ausserhalb seiner letzten kaufbaren Grenze.")

    schreibe_zustand(lage, fehler)
    if historie:
        try:
            import grid_historie as gh
            gh_alle = gh.zeilen()
            if not gh_alle:
                print("Historie: keine geschlossenen Contract-Grids.")
            else:
                z = gh.summen(gh_alle)
                print("Historie: %d geschlossene Grids (Netz %+.2f / Richtung %+.2f / "
                      "Gesamt %+.2f / Einsatz %.2f, %d OHNE Stop)"
                      % (z["n"], z["netz"], z["richtung"], z["gesamt"],
                         z["invest"], z["ohne_stop"]))
        except Exception as e:
            print("Historie-FEHLER: %s: %s" % (type(e).__name__, str(e)[:160]))
    return 0 if not fehler else 1


if __name__ == "__main__":
    sys.exit(main())