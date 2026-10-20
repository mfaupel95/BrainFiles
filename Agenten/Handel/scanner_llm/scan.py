"""Taeglicher Scan der 'scanner_llm'-Spur: ein LEICHTER Marktscanner.

Holt Tageskerzen von OKX, bewertet jede Muenze mit der bewaehrten Regel des
Marktscanners (scanner/bewertung.py) und wendet die LEICHTEREN Tore dieser
Spur an (wachen.json: mindest_score, max_volatilitaet_pa, min_chance_risiko).
Wer sie passiert, ist ein KANDIDAT fuer den LLM-Qualitaetsfilter - dieses
Scan-Modul ist BEWUSST rein regelbasiert und ruft kein Modell.

Aufruf:
    <venv>\\python.exe scanner_llm\\scan.py            # voller Lauf
    <venv>\\python.exe scanner_llm\\scan.py --kurz     # nur die Tabelle

Der Scan loest nichts aus. Er liefert nur die Rangliste; der LLM-Filter und
das Handeln macht handeln.py in einem getrennten Schritt.

Die gemeinsam genutzten Module (bewertung, okx, risikostufe) werden ueber den
PFAD geladen statt ueber einen sys.path-Eintrag: die Spur startet mit ihrem
eigenen Ordner als sys.path[0], und der Handel-Ordner/der scanner-Ordner
liegen dort nicht (Hausmuster, wie risikostufe.py in scanner/handeln.py).
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# --- Gemeinsame Module ueber den PFAD laden -------------------------------
_HIER = Path(__file__).resolve().parent
_HANDEL = _HIER.parent
_SCANNER = _HANDEL / "scanner"

from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec


def _lade(name, datei):
    spec = _rs_spec(name, str(datei))
    modul = _rs_mod(spec)
    spec.loader.exec_module(modul)
    return modul


risikostufe = _lade("risikostufe", _HANDEL / "risikostufe.py")
bewertung = _lade("scanner_bewertung", _SCANNER / "bewertung.py")
okx = _lade("scanner_okx", _SCANNER / "okx.py")

BERICHTE = _HIER / "berichte"


def wachen():
    return risikostufe.skaliere(
        json.loads((_HIER / "wachen.json").read_text("utf-8")))


def lauf(kurz=False):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = wachen()
    uni = w.get("universum") or {}
    alle = uni.get("modus") == "alle"
    if alle:
        liste = [inst for inst, _ in okx.alle_paare(
            quote=uni.get("quotes", ["USDT", "USDC"]),
            min_volumen_usd=uni.get("min_volumen_24h_usd", 3000000))]
    else:
        liste = w["watchlist"]
    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print("=== Marktscanner scanner_llm %s | %d Werte (%s) ===" % (
        heute, len(liste), "ganzer Markt" if alle else "Watchlist"))
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
        "spur": "scanner_llm",
        "alle": alle,
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
    p.add_argument("--kurz", action="store_true",
                   help="nur Tabelle, kein Schreiben")
    a = p.parse_args()
    lauf(kurz=a.kurz)
