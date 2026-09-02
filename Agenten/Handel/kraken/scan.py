"""Taeglicher Scan der Kraken-Watchlist. Holt Tageskerzen von Kraken,
bewertet jedes Paar und schreibt einen datierten Bericht nach berichte/.

Aufruf:
    ..\\scanner\\.venv\\Scripts\\python.exe scan.py          # voller Lauf
    ..\\scanner\\.venv\\Scripts\\python.exe scan.py --kurz   # nur die Tabelle

Bewertet wird mit scanner/bewertung.py - demselben Modell wie Spur 1, nicht
mit einem zweiten. Es rechnet auf reinen Kerzen und kennt keine Boerse; damit
sind die Scores der beiden Spuren vergleichbar.

Der Scan loest nichts aus. Er liefert nur die Rangliste; das Handeln macht
handeln.py in einem getrennten Schritt.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import kraken

HIER = Path(__file__).resolve().parent
BERICHTE = HIER / "berichte"

sys.path.insert(0, str(HIER.parent / "scanner"))
import bewertung  # noqa: E402


def wachen():
    return json.loads((HIER / "wachen.json").read_text("utf-8"))


def lauf(kurz=False):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = wachen()
    liste = w["watchlist"]
    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print("=== Kraken-Scan %s | %d Paare ===" % (heute, len(liste)))

    zeilen = []
    for paar in liste:
        try:
            k = kraken.kerzen(paar, 1440, 720)
            if len(k) < 120:
                print("  %-10s zu wenig Historie (%d)" % (paar, len(k)))
                continue
            b = bewertung.bewerten(k)
            b["inst"] = paar
            zeilen.append(b)
        except Exception as e:  # noqa: BLE001
            print("  %-10s Fehler: %s" % (paar, e), file=sys.stderr)
        time.sleep(0.35)          # Kraken zaehlt Abrufe je Schluessel

    zeilen.sort(key=lambda z: z["score"], reverse=True)

    gate_s = w["mindest_score"]
    gate_v = w["max_volatilitaet_pa"]
    gate_cr = w["mindest_chance_risiko"]

    print()
    print("%-10s | %5s | %6s | %6s | %5s | %7s | %s"
          % ("Paar", "Score", "Chance", "Risiko", "C/R", "Vola pa", "Tor"))
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
        "boerse": "kraken",
        "waehrung": w.get("waehrung", "EUR"),
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
