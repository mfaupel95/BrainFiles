"""Auswertung des jev_trader-Papierbuchs: laesst sich das Signal tragen?

Die Mechanik steht im Haus in `Handel/auswertung_alle.py` (kennzahlen,
belastbar, zeige) - hier steht nur, was jev_trader anders macht: sein Buch
fuehrt je geschlossener Runde EINE Zeile im orb-Schema
(zeit,inst,richtung,einstieg,stop,ziel,ausgang,ausstieg,gv_punkte,gv_usd,
mfe_pct,mae_pct,haltetage), und sein Ergebnis steht fertig in `gv_usd`.
Es gibt KEINEN Einsatz pro Runde (der Bot skaliert sein Bein nach und das
Log fuehrt keinen Kapitalbetrag) - das Buch ist ein Punkte-/Ergebnisbuch
wie orb/orbk. Prozent-Aussagen auf einen Kapitalbetrag waeren deshalb
Behauptungen und bleiben aus; gerechnet wird auf USD und auf Runden.

Die Runden-Werte sind der Input, nicht umgekehrt: Diese Auswertung liest
ihr eigenes handelsjournal.csv. Sie ist SELBSTSTAENDIG lauffaehig
(python auswertung.py) und dient zugleich dem Tagesbericht.

Aufruf:
    scanner/.venv/Scripts/python.exe auswertung.py
    scanner/.venv/Scripts/python.exe auswertung.py --min 20
"""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
JOURNAL = HIER / "handelsjournal.csv"
WACHEN = HIER / "wachen.json"

MIN_RUNDEN = 8        # Haus-Schwelle: ab hier gilt eine Messung als belastbar


def lade_zeilen(pfad=JOURNAL):
    """Alle Journal-Zeilen (orb-Schema) als Liste von dicts."""
    if not Path(pfad).exists():
        return []
    with open(pfad, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _zahl(x):
    if x is None:
        return None
    s = str(x).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def runden_aus_journal(zeilen):
    """Gescloss Runden aus dem Journal - jede Zeile ist EINE Runde.

    Wie runden_orbk in auswertung_alle.py: gv_usd (sonst gv_punkte) ist das
    Ergebnis der Zeile. Zeilen ohne Ausgang sind keine abgeschlossene Runde.
    """
    out = []
    for r in zeilen:
        gv = _zahl(r.get("gv_usd"))
        if gv is None:
            continue
        out.append({
            "zeit": r.get("zeit", ""),
            "richtung": (r.get("richtung") or "").strip() or "",
            "einstieg": _zahl(r.get("einstieg")),
            "ausstieg": _zahl(r.get("ausstieg")),
            "gv_usd": gv,
            "ausgang": (r.get("ausgang") or "").strip() or "ohne",
            "haltetage": _zahl(r.get("haltetage")),
        })
    return out


def kennzahlen(runden):
    """Die Kennzahlblock eines Punke-Buchs: Ergebnis je Runde, ohne Einsatz.

    Rueckgabe: dict mit n, ergebnis (Summe gv_usd), EV je Runde, Treffer,
    beste/schlechteste Runde (USD), Ausstiegsgruende.
    """
    if not runden:
        return None
    summe = sum(r["gv_usd"] for r in runden)
    treffer = sum(1 for r in runden if r["gv_usd"] > 0)
    gruende = {}
    for r in runden:
        gruende[r["ausgang"]] = gruende.get(r["ausgang"], 0) + 1
    halten = [r["haltetage"] for r in runden if r["haltetage"] is not None]
    return {
        "n": len(runden),
        "ergebnis": summe,
        "ev": summe / len(runden),
        "treffer": treffer,
        "treffer_pct": 100.0 * treffer / len(runden),
        "best": max(r["gv_usd"] for r in runden),
        "schlecht": min(r["gv_usd"] for r in runden),
        "gruende": dict(sorted(gruende.items(), key=lambda kv: -kv[1])),
        "halten_tage": statistics.median(halten) if halten else None,
    }


def belastbar(k, min_runden=MIN_RUNDEN):
    return bool(k) and k["n"] >= min_runden


def zeige(k):
    """Mehrzeiliger Bericht - die gleiche Form, mit der das Haus arbeitet."""
    if k is None:
        print("  keine geschlossene Runde im Journal")
        return
    print("  %-28s %d" % ("geschlossene Runden", k["n"]))
    print("  %-28s %+.6f USD (%.4f USD je Runde)"
          % ("Ergebnis (realisiert)", k["ergebnis"], k["ev"]))
    print("  %-28s %.0f %%  (%d von %d)"
          % ("Treffer (Gewinn > 0)", k["treffer_pct"], k["treffer"], k["n"]))
    print("  %-28s %+.6f USD / %+.6f USD"
          % ("beste / schlechteste Runde", k["best"], k["schlecht"]))
    if k["halten_tage"] is not None:
        print("  %-28s %.3f Tage" % ("Haltedauer (Median)", k["halten_tage"]))
    print("  Ausstiegsgruende: %s"
          % ", ".join("%s %d" % (g, n) for g, n in k["gruende"].items()))
    if not belastbar(k):
        print("  -> nur %d Runden: ein Befund, keine Messung. Belastbar ab %d."
              % (k["n"], MIN_RUNDEN))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pfad", default=str(JOURNAL), help="Journal-CSV")
    p.add_argument("--min", type=int, default=MIN_RUNDEN,
                   help="Schwelle fuer 'belastbar'")
    a = p.parse_args()

    k = kennzahlen(runden_aus_journal(lade_zeilen(a.pfad)))
    print("=== JEV_TRADER Auswertung (Papier) ===")
    zeige(k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
