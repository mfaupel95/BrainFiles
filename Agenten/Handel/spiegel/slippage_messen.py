#!/usr/bin/env python3
"""Slippage messen statt annehmen: was ein 50-USDC-Kauf in dieser Tiefe kostet.

AUFTRAG Max 21.09.2026 ("slippage messen"), nach dem Befund der Schattenbuecher:
alle drei Spiegel-Arme sind nach Kosten negativ, waehrend sie VOR Kosten fast
auf null stehen (Hauptbuch -1,66 %). Die Kostenschaetzung ist damit der groesste
Einzelposten des Buchs - und sie war bisher eine Annahme aus `wachen.json`
(`slippage_pct` 3.0 je Seite, `gebuehr_pct` 1.0).

WAS DIESES SKRIPT MISST (Messung, keine Schaetzung):

  Round-Trip-Impact aus der ECHTEN Pool-Tiefe. Fuer jeden Token der juengsten
  Einstiege wird bei DexScreener der liquideste Pool geholt und der Preis-
  einfluss nach der Constant-Product-Naeherung gerechnet:

      Kauf:   p_ausfuehrung = p * (1 + S / Lq)
      Verkauf: p_ausfuehrung = p * (1 - S / Lq)
      Round-Trip-Verlust in Prozent ~ 2 * S / Lq * 100,

  mit S = Ordervolumen und Lq = Quote-Tiefe des Pools (die Haelfte der
  ausgewiesenen Liquiditaet, weil ein AMM-Kauf die Quote-Seite belastet).

WAS ES NICHT MISST (ehrlich benannt):
  - Die Tiefe wird JETZT geholt, nicht zum Zeitpunkt des Einstiegs. Fuer die
    Frage "ist die Annahme zu freundlich" reicht das: die Tiefe waechst nicht
    nachtraeglich, und tote Pools sind eher der Regelfall.
  - Kein Netzwerk-Delay, keine Prioritaet-Gebuehr, kein MEV. Die kommen oben
    drauf, nicht unten ab.

Aufruf (aus Agenten/Handel/spiegel):
    python slippage_messen.py                 # letzte 40 Einstiege, Groessen 50/100/500
    python slippage_messen.py --anzahl 80
    python slippage_messen.py --groessen 50,100
    python slippage_messen.py --json          # maschinenlesbar

Netz: api.dexscreener.com (frei, kein Schluessel). Reine Standardbibliothek.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
JOURNAL = HIER / "handelsjournal.csv"
WACHEN = HIER / "wachen.json"
DEX = "https://api.dexscreener.com/latest/dex/tokens/"


def _hol(url: str, versuche: int = 3):
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, TimeoutError, ValueError):
            if i == versuche - 1:
                return None
    return None


def einstiege(anzahl: int):
    """Die juengsten Einstiege (Token, Symbol, Preis, Einsatz, Marktkap)."""
    if not JOURNAL.is_file():
        return []
    with JOURNAL.open("r", newline="", encoding="utf-8") as f:
        zeilen = [r for r in csv.DictReader(f)
                  if (r.get("aktion") or "") in ("eroeffnen", "kauf")
                  and (r.get("token") or "")]
    return zeilen[-anzahl:]


def pool_daten(token: str):
    """(tiefe_quote_usd, preis_usd, marktkap_usd, dex) des liquidesten Pools."""
    d = _hol(DEX + urllib.parse.quote(token))
    paare = (d or {}).get("pairs") or []
    if not paare:
        return None
    best = max(paare, key=lambda p: float(
        (p.get("liquidity") or {}).get("usd") or 0))
    liq = float((best.get("liquidity") or {}).get("usd") or 0)
    try:
        preis = float(best.get("priceUsd") or 0)
    except (TypeError, ValueError):
        preis = 0.0
    try:
        kap = float(best.get("marketCap") or best.get("fdv") or 0)
    except (TypeError, ValueError):
        kap = 0.0
    return {"tiefe_quote_usd": liq / 2.0, "tiefe_usd": liq, "preis_usd": preis,
            "marktkap_usd": kap, "dex": best.get("dexId"),
            "paar": best.get("pairAddress")}


def impact_pct(groesse: float, tiefe_quote: float) -> float:
    """Round-Trip-Preiseinfluss in Prozent (Kauf + Verkauf)."""
    if tiefe_quote <= 0:
        return float("inf")
    return 2.0 * groesse / tiefe_quote * 100.0


def wachen_kosten():
    try:
        w = json.loads(WACHEN.read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return {}
    return {"slippage_pct": w.get("slippage_pct"),
            "gebuehr_pct": w.get("gebuehr_pct"),
            "band": w.get("marketcap_band_usd"),
            "einsatz": w.get("max_einsatz_je_kopie_usd")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anzahl", type=int, default=40,
                    help="wie viele der juengsten Einstiege gemessen werden")
    ap.add_argument("--groessen", default="50,100,500",
                    help="Ordervolumina in USD, mit Komma getrennt")
    ap.add_argument("--json", action="store_true", help="maschinenlesbar")
    a = ap.parse_args()
    groessen = [float(x) for x in a.groessen.split(",") if x.strip()]

    zeilen = einstiege(a.anzahl)
    if not zeilen:
        print("Keine Einstiege im Journal: %s" % JOURNAL)
        return 1

    w = wachen_kosten()
    treffer, ohne = [], []
    for r in zeilen:
        pd_ = pool_daten(r["token"])
        if not pd_ or pd_["tiefe_quote_usd"] <= 0:
            ohne.append(r.get("symbol") or r["token"][:8])
            continue
        treffer.append({"symbol": r.get("symbol") or r["token"][:8],
                        "marktkap_usd": pd_["marktkap_usd"],
                        "tiefe_usd": pd_["tiefe_usd"], "dex": pd_["dex"],
                        "impacts": {g: impact_pct(g, pd_["tiefe_quote_usd"])
                                    for g in groessen}})

    ergebnis = {"gemessen": len(treffer), "ohne_pool": len(ohne),
                "ohne_pool_beispiele": ohne[:8], "annahme": w,
                "je_groesse": {}}
    for g in groessen:
        werte = [t["impacts"][g] for t in treffer if t["impacts"][g] != float("inf")]
        if not werte:
            continue
        werte.sort()
        ergebnis["je_groesse"][str(int(g))] = {
            "median_pct": round(statistics.median(werte), 2),
            "p25_pct": round(werte[int(len(werte) * 0.25)], 2),
            "p75_pct": round(werte[int(len(werte) * 0.75) - 1], 2),
            "max_pct": round(werte[-1], 2),
        }
    tiefen = [t["tiefe_usd"] for t in treffer if t["tiefe_usd"] > 0]
    if tiefen:
        tiefen.sort()
        ergebnis["tiefe_usd"] = {"median": round(statistics.median(tiefen), 0),
                                 "p25": round(tiefen[int(len(tiefen) * 0.25)], 0)}

    if a.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=1))
        return 0

    print("=== SLIPPAGE-MESSUNG (Pool-Tiefe live, DexScreener) ===")
    print("Einstiege gemessen: %d   ohne auffindbaren Pool: %d"
          % (len(treffer), len(ohne)))
    if tiefen:
        e = ergebnis["tiefe_usd"]
        print("Pool-Tiefe: Median %.0f USD (p25 %.0f USD)" % (e["median"], e["p25"]))
    print()
    print("Round-Trip-Preiseinfluss aus der Tiefe (ohne Gebuehr, ohne MEV):")
    for g, v in ergebnis["je_groesse"].items():
        print("  %4s USD: Median %6.2f %%   p25 %6.2f %%   p75 %6.2f %%   max %8.2f %%"
              % (g, v["median_pct"], v["p25_pct"], v["p75_pct"], v["max_pct"]))
    print()
    if w:
        angenommen = w.get("slippage_pct")
        gebuehr = w.get("gebuehr_pct")
        print("Annahme im Wachenbuch: slippage_pct %s je Seite, gebuehr_pct %s je Seite"
              % (angenommen, gebuehr))
        if angenommen is not None:
            for g, v in ergebnis["je_groesse"].items():
                # Annahme gilt JE SEITE: Round-Trip = 2 x slippage
                soll = 2 * float(angenommen)
                urteil = ("zu freundlich" if v["median_pct"] > soll
                          else "zu streng" if v["median_pct"] < soll * 0.5
                          else "in der Naehe")
                print("  %4s USD: gemessen %6.2f %% gegen angenommen %5.2f %% -> %s"
                      % (g, v["median_pct"], soll, urteil))
    if ohne:
        print()
        print("Ohne Pool gefunden (%d): %s" % (len(ohne), ", ".join(ohne[:8])))
        print("  -> diese Kopien hatten zum Messzeitpunkt keinen handelbaren Pool")
    return 0


if __name__ == "__main__":
    sys.exit(main())