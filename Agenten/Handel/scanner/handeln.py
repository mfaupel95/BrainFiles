"""Aus der Rangliste des Scans Vorschlaege bauen und - im Rahmen der Wachen -
ausfuehren.

Aufruf:
    python scanner\\handeln.py --vorschau          # nur zeigen, was er taete
    python scanner\\handeln.py --papier            # Papierhandel, Standard der Routine
    python scanner\\handeln.py --live              # echte Orders (siehe Sperren unten)

Drei Sperren muessen ALLE offen sein, sonst laeuft trotz --live nur Papier:
    1. wachen.json  handel_erlaubt == true
    2. OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE als Benutzervariablen
    3. --live ausdruecklich auf der Kommandozeile
Fehlt eine, wird Papier gehandelt und es wird gesagt, welche Sperre zu war.

Jede Aktion landet in handelsjournal.csv. Der offene Bestand steht in
zustand.json. Beide werden nicht versioniert (Rauschen), aber gesichert.

Der Live-Pfad (okx.markt_kauf / markt_verkauf / stop_setzen) ist mangels
gueltiger Schluessel noch NICHT gegen echte Orders getestet. Vor dem ersten
scharfen Lauf mit einem einzigen Wert und Kleinstbetrag gegenpruefen.
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone, date
from pathlib import Path

import okx
import scan

HIER = Path(__file__).resolve().parent
ZUSTAND = HIER / "zustand.json"
JOURNAL = HIER / "handelsjournal.csv"


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def lade_zustand():
    if ZUSTAND.exists():
        return json.loads(ZUSTAND.read_text("utf-8"))
    return {"positionen": [], "letzte_stops": {}, "letzter_lauf": None,
            "modus": None}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    ZUSTAND.write_text(json.dumps(z, ensure_ascii=False, indent=2), "utf-8")


def journal(*felder):
    neu = not JOURNAL.exists()
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        if neu:
            s.writerow(["zeit", "modus", "aktion", "inst", "preis", "usd",
                        "stop", "ziel", "grund"])
        s.writerow(felder)


# --- Vorschlaege ---------------------------------------------------------------

def stop_prozent(z, w):
    """Stop-Abstand: aus Volatilitaet und Drawdown, hart gedeckelt."""
    vola = z["kennzahlen"]["volatilitaet_pa"]
    roh = 3.0 + 6.0 * min(vola, 1.5)          # ~5 % ruhig, ~12 % wild
    return max(w["pflicht_stop_prozent_min"],
               min(w["pflicht_stop_prozent_max"], round(roh, 1)))


def vorschlaege(bericht, w):
    aus = []
    for z in bericht["werte"]:
        vola = z["kennzahlen"]["volatilitaet_pa"]
        if not (z["score"] >= w["mindest_score"]
                and vola <= w["max_volatilitaet_pa"]
                and z["verhaeltnis"] >= w["mindest_chance_risiko"]):
            continue
        einstieg = z["preis"]
        sp = stop_prozent(z, w)
        stop = round(einstieg * (1 - sp / 100.0), 6)
        ziel = round(einstieg + 2.0 * (einstieg - stop), 6)   # Chance/Risiko 2:1
        aus.append({"inst": z["inst"], "score": z["score"], "einstieg": einstieg,
                    "stop": stop, "stop_pct": sp, "ziel": ziel,
                    "usd": w["max_pro_trade_usd"]})
    return aus


# --- Ausstieg / Einstieg ---------------------------------------------------

def in_abklingzeit(inst, z, w):
    d = z["letzte_stops"].get(inst)
    if not d:
        return False
    tage = (date.fromisoformat(_heute()) - date.fromisoformat(d)).days
    return tage < w["abklingzeit_tage"]


def pruefe_ausstiege(z, live):
    behalten = []
    for p in z["positionen"]:
        kurs = okx.letzter_kurs(p["inst"])
        grund = None
        if kurs <= p["stop"]:
            grund = "stop"
        elif kurs >= p["ziel"]:
            grund = "ziel"
        if not grund:
            behalten.append(p)
            continue
        erloes = p["usd"] * kurs / p["einstieg"]
        gv = erloes - p["usd"]
        if live:
            try:
                d = okx.order_details(p["inst"], p["kauf_ord_id"])
                menge = float(d.get("accFillSz") or 0) or p["usd"] / p["einstieg"]
                okx.markt_verkauf(p["inst"], round(menge, 8))
            except Exception as e:  # noqa: BLE001
                print("  Verkauf %s fehlgeschlagen: %s" % (p["inst"], e),
                      file=sys.stderr)
                behalten.append(p)
                continue
        print("  ZU  %-10s @ %.6f  (%s)  G/V %+.2f USD"
              % (p["inst"], kurs, grund, gv))
        journal(_jetzt(), "live" if live else "papier", "verkauf", p["inst"],
                "%.6f" % kurs, "%.2f" % erloes, "", "", grund)
        if grund == "stop":
            z["letzte_stops"][p["inst"]] = _heute()
    z["positionen"] = behalten


def pruefe_einstiege(z, vs, w, live):
    gehalten = {p["inst"] for p in z["positionen"]}
    eingesetzt = sum(p["usd"] for p in z["positionen"])
    for v in vs:
        if len(z["positionen"]) >= w["max_offene_positionen"]:
            break
        if eingesetzt + v["usd"] > w["max_gesamt_usd"]:
            continue
        if v["inst"] in gehalten or in_abklingzeit(v["inst"], z, w):
            continue
        kauf_id = None
        if live:
            try:
                kauf_id = okx.markt_kauf(v["inst"], v["usd"])
                d = okx.order_details(v["inst"], kauf_id)
                menge = float(d.get("accFillSz") or 0)
                if menge > 0:
                    okx.stop_setzen(v["inst"], round(menge, 8), v["stop"])
            except Exception as e:  # noqa: BLE001
                print("  Kauf %s fehlgeschlagen: %s" % (v["inst"], e),
                      file=sys.stderr)
                continue
        z["positionen"].append({
            "inst": v["inst"], "einstieg": v["einstieg"], "usd": v["usd"],
            "stop": v["stop"], "ziel": v["ziel"], "eroeffnet": _heute(),
            "kauf_ord_id": kauf_id,
        })
        eingesetzt += v["usd"]
        gehalten.add(v["inst"])
        print("  AUF %-10s @ %.6f  Stop %.6f (-%.1f%%)  Ziel %.6f  %d USD"
              % (v["inst"], v["einstieg"], v["stop"], v["stop_pct"],
                 v["ziel"], v["usd"]))
        journal(_jetzt(), "live" if live else "papier", "kauf", v["inst"],
                "%.6f" % v["einstieg"], "%.2f" % v["usd"],
                "%.6f" % v["stop"], "%.6f" % v["ziel"], "score %.1f" % v["score"])


# --- Hauptlauf ---------------------------------------------------------------

def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = scan.wachen()
    bpfad = scan.BERICHTE / "neuester.json"
    if not bpfad.exists():
        print("Kein Bericht. Erst scan.py laufen lassen.")
        return
    bericht = json.loads(bpfad.read_text("utf-8"))

    # Live-Sperren pruefen
    live = False
    if modus == "live":
        gruende = []
        if not w.get("handel_erlaubt"):
            gruende.append("wachen.json handel_erlaubt=false")
        if not okx.schluessel_vorhanden():
            gruende.append("OKX-Schluessel nicht gesetzt")
        if gruende:
            print("--live angefordert, aber gesperrt: " + "; ".join(gruende))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    vs = vorschlaege(bericht, w)
    print("=== Handeln (%s) | Bericht %s | %d Vorschlaege ==="
          % ("LIVE" if live else "Papier", bericht["datum"], len(vs)))

    z = lade_zustand()
    z["modus"] = "live" if live else "papier"

    if modus == "vorschau":
        for v in vs:
            print("  %-10s Score %.1f  Einstieg %.6f  Stop %.6f (-%.1f%%)  Ziel %.6f"
                  % (v["inst"], v["score"], v["einstieg"], v["stop"],
                     v["stop_pct"], v["ziel"]))
        eing = sum(p["usd"] for p in z["positionen"])
        print("\nOffener Bestand: %d Positionen, %d USD gebunden"
              % (len(z["positionen"]), eing))
        return

    print("- Ausstiege -")
    pruefe_ausstiege(z, live)
    print("- Einstiege -")
    pruefe_einstiege(z, vs, w, live)

    eing = sum(p["usd"] for p in z["positionen"])
    print("\nStand: %d/%d Positionen, %d/%d USD gebunden"
          % (len(z["positionen"]), w["max_offene_positionen"],
             eing, w["max_gesamt_usd"]))
    schreibe_zustand(z)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau", help="nur zeigen")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier", help="Papierhandel (Standard)")
    g.add_argument("--live", action="store_const", dest="modus",
                   const="live", help="echte Orders, wenn alle Sperren offen")
    a = p.parse_args()
    lauf(a.modus or "papier")
