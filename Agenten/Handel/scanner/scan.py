"""Taeglicher Scan der Watchlist. Holt Tageskerzen von OKX, bewertet jede
Muenze und schreibt einen datierten Bericht nach berichte/.

Aufruf:
    .venv\\Scripts\\python.exe scanner\\scan.py            # voller Lauf
    .venv\\Scripts\\python.exe scanner\\scan.py --kurz     # nur die Tabelle

Der Scan loest nichts aus. Er liefert nur die Rangliste; das Handeln macht
handeln.py in einem getrennten Schritt.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import bewertung
import okx

HIER = Path(__file__).resolve().parent
BERICHTE = HIER / "berichte"


def wachen():
    return json.loads((HIER / "wachen.json").read_text("utf-8"))


def lauf(kurz=False):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = wachen()
    uni = w.get("universum") or {}
    if uni.get("modus") == "alle":
        # Der ganze OKX-Spotmarkt: Paare der konfigurierten Quote-
        # Waehrungen ueber dem Mindestumsatz, absteigend nach Umsatz
        # (eine tickers-Abfrage statt einer je Paar). Die Watchlist bleibt
        # als enge Liste und Rueckfall erhalten.
        liste = [inst for inst, _ in okx.alle_paare(
            quote=uni.get("quotes", ["USDT", "USDC"]),
            min_volumen_usd=uni.get("min_volumen_24h_usd", 3000000))]
    else:
        liste = w["watchlist"]
    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print("=== Marktscanner %s | %d Werte (%s) ===" % (
        heute, len(liste),
        "ganzer Markt" if uni.get("modus") == "alle" else "Watchlist"))
    pause = 0.25 if len(liste) > 30 else 0.15

    zeilen = []
    for inst in liste:
        try:
            k = okx.kerzen(inst, "1D", 300)
            if len(k) < 120:
                print("  %-10s zu wenig Historie (%d)" % (inst, len(k)))
                continue
            b = bewertung.bewerten(k)
            b["inst"] = inst
            zeilen.append(b)
        except Exception as e:  # noqa: BLE001
            print("  %-10s Fehler: %s" % (inst, e), file=sys.stderr)
        time.sleep(pause)

    zeilen.sort(key=lambda z: z["score"], reverse=True)

    gate_s = w["mindest_score"]
    gate_v = w["max_volatilitaet_pa"]
    gate_cr = w["mindest_chance_risiko"]

    print()
    print("%-10s | %5s | %6s | %6s | %5s | %7s | %s"
          % ("Wert", "Score", "Chance", "Risiko", "C/R", "Vola pa", "Tor"))
    print("-" * 70)
    for z in zeilen:
        vola = z["kennzahlen"]["volatilitaet_pa"]
        durch = (z["score"] >= gate_s and vola <= gate_v
                 and z["verhaeltnis"] >= gate_cr)
        print("%-10s | %5.1f | %6.1f | %6.1f | %5.2f | %7.2f | %s"
              % (z["inst"], z["score"], z["chance"], z["risiko"],
                 z["verhaeltnis"], vola, "JA" if durch else "-"))

    bericht = {
        "datum": heute,
        "erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tore": {"mindest_score": gate_s, "max_volatilitaet_pa": gate_v,
                 "mindest_chance_risiko": gate_cr},
        "werte": zeilen,
    }

    if not kurz:
        BERICHTE.mkdir(exist_ok=True)
        (BERICHTE / ("%s.json" % heute)).write_text(
            json.dumps(bericht, ensure_ascii=False, indent=2), "utf-8")
        (BERICHTE / "neuester.json").write_text(
            json.dumps(bericht, ensure_ascii=False, indent=2), "utf-8")
        print("\nBericht: berichte/%s.json" % heute)

    return bericht


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--kurz", action="store_true", help="nur Tabelle, kein Schreiben")
    a = p.parse_args()
    lauf(kurz=a.kurz)
