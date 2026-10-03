"""Was im Kraken-Konto liegt - und was davon NICHT handelbar ist (T-280).

Warum es dieses Werkzeug gibt
-----------------------------
Beim Umschichten am 01.10.2026 blieben drei Posten liegen, und die Ursachen
waren ZWEI verschiedene Dinge, die man nicht am Betrag sieht:

  * **Ordermin**: Kraken verlangt je Paar eine Mindestmenge. PEPE lag mit
    409.009,94 gegen `ordermin` 1.500.000 (PEPEEUR), ONDO mit 10,74331 gegen 15.
    Kein Defekt, nur zu klein - die Order waere abgelehnt worden.
  * **Sonderformen**: ADA.S, ATOM21.S, HYPE.B, XPEV.EQ haben UEBERHAUPT kein
    Paar. Gemessen: `AssetPairs` fuehrt keine einzige Basis mit einem Punkt.
    Eine Order ist damit nicht der Weg, sondern Unstaking bzw. ein Wandeln.
  * **Barmittel** (USDC, ZEUR, ZUSD) haben ebenfalls kein Paar mit sich selbst
    als Basiswert - sie stehen als QUOTE im Buch. Sie sind kein Befund und
    werden getrennt gefuehrt: sie mit "gestakt" zu erklaeren waere eine falsche
    Ursache, und die Ursache ist genau das, was hier gesucht wird.

Beides ist an `AssetPairs` nachpruefbar, `ordermin` steht dort JE PAAR - raten
ist unnoetig. Dieselbe Verwechslung gab es auf der anderen Boerse: OKX lehnt
BETH-USDT und OKSOL-USDT mit `51155 ... local compliance restrictions` ab, und
die Sperre ist an `/public/instruments` NICHT zu sehen.

Aufruf (Lesen, keine Order, kein Schreiben):
    python lagerbestand.py            # nur die festliegenden Posten
    python lagerbestand.py --alle     # der ganze Bestand
    python lagerbestand.py --json     # maschinenlesbar
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken as k                                                   # noqa: E402

# Quotewaehrungen in der Reihenfolge, in der ein Paar fuer die Bewertung
# gesucht wird: EUR zuerst (das Haus rechnet in EUR), dann USD-nahe Quoten.
QUOTEN = ("ZEUR", "USDC", "ZUSD")

STAND = "handelbar"
UNTER_ORDERMIN = "unter_ordermin"
KEIN_PAAR = "kein_paar"
BARMITTEL = "barmittel"

# Was als "liegt fest" zaehlt: eine Order ist nicht moeglich, und Warten allein
# hilft nicht (unter_ordermin: sammeln; kein_paar: Unstaking/Wandeln).
FEST = (UNTER_ORDERMIN, KEIN_PAAR)


def paare_lesen(roh=None) -> dict:
    """Alle Paare aus AssetPairs: {paarname: record} (lesend, oeffentlich)."""
    antwort = k._roh_oeffentlich("AssetPairs") if roh is None else roh
    if isinstance(antwort, dict) and "result" in antwort:
        antwort = antwort.get("result") or {}
    return {name: d for name, d in (antwort or {}).items() if isinstance(d, dict)}


def basen_index(paare: dict) -> dict:
    """Basiswert -> [(paarname, quote)] - der Index, den eine Order braucht."""
    index: dict = {}
    for name, d in paare.items():
        basis = d.get("base")
        if not isinstance(basis, str) or not basis:
            continue
        index.setdefault(basis, []).append((name, d.get("quote")))
    for basis in index:
        index[basis].sort()
    return index


def _passendes_paar(zeilen):
    """Das Paar, in dem ein Posten verkauft werden kann - EUR zuerst."""
    for quote in QUOTEN:
        for name, q in zeilen:
            if q == quote:
                return name, quote
    return (zeilen[0][0], zeilen[0][1]) if zeilen else (None, None)


def _zahl(wert):
    try:
        return float(wert or 0.0)
    except (TypeError, ValueError):
        return 0.0


def lage(staende: dict, paare: dict) -> list[dict]:
    """Je Posten mit Bestand > 0 eine Zeile: handelbar / unter_ordermin / kein_paar.

    Rein rechnend (kein Netz): `staende` kommt aus `kraken.kontostaende()`,
    `paare` aus `paare_lesen()`. Ein Posten ohne Paar ist deshalb nicht
    "unbekannt", sondern eine Sonderform (gestakt oder tokenisiert) - der
    Unterschied entscheidet, ob Warten hilft oder Unstaking.
    """
    index = basen_index(paare)
    quoten = {d.get("quote") for d in paare.values() if isinstance(d.get("quote"), str)}
    zeilen = []
    for code, menge_roh in sorted((staende or {}).items()):
        menge = _zahl(menge_roh)
        if menge <= 0:
            continue                     # Staub und Nullstaende sind kein Befund
        treffer = index.get(code) or []
        if not treffer:
            if code in quoten:
                # Barmittel, keine Sonderform: USDC/ZEUR stehen als QUOTE im
                # Buch, nicht als Basiswert. Sie mit "gestakt" zu erklaeren
                # waere eine falsche Ursache - und genau danach sucht man hier.
                zeilen.append({"code": code, "menge": menge, "lage": BARMITTEL,
                               "paar": None, "quote": None, "ordermin": None,
                               "costmin": None, "fehlt": None,
                               "grund": "Barmittel/Quotewaehrung (%s) - kein "
                                        "Handelsposten, sondern die Gegenseite" % code})
                continue
            zeilen.append({"code": code, "menge": menge, "lage": KEIN_PAAR,
                           "paar": None, "quote": None, "ordermin": None,
                           "costmin": None, "fehlt": None,
                           "grund": "kein Paar mit base=%s - Sonderform "
                                    "(gestakt oder tokenisiert), keine Order moeglich"
                                    % code})
            continue
        name, quote = _passendes_paar(treffer)
        d = paare.get(name) or {}
        ordermin = _zahl(d.get("ordermin"))
        costmin = _zahl(d.get("costmin"))
        if ordermin and menge < ordermin:
            zeilen.append({"code": code, "menge": menge, "lage": UNTER_ORDERMIN,
                           "paar": name, "quote": quote, "ordermin": ordermin,
                           "costmin": costmin, "fehlt": round(ordermin - menge, 8),
                           "grund": "%.8g von ordermin %.8g - sammeln, dann geht es "
                                    "ueber %s" % (menge, ordermin, name)})
            continue
        zeilen.append({"code": code, "menge": menge, "lage": STAND,
                       "paar": name, "quote": quote, "ordermin": ordermin,
                       "costmin": costmin, "fehlt": 0.0,
                       "grund": "verkaufbar ueber %s" % name})
    return zeilen


def werte_ergaenzen(zeilen: list[dict], kurs_fn=None) -> list[dict]:
    """Wert in EUR je Posten - nur fuer Zeilen mit Paar (Netzabruf je Paar)."""
    kurs_fn = kurs_fn or (lambda paar: k.letzter_kurs(paar))
    for z in zeilen:
        if not z.get("paar"):
            z["wert_quote"] = None
            continue
        try:
            kurs = float(kurs_fn(z["paar"]))
        except Exception:                                          # noqa: BLE001
            z["wert_quote"] = None
            continue
        z["kurs"] = kurs
        z["wert_quote"] = round(z["menge"] * kurs, 4)
    return zeilen


def _tabelle(zeilen: list[dict]) -> str:
    kopf = "%-10s %16s %-15s %-12s %14s %16s %12s" % (
        "CODE", "MENGE", "LAGE", "PAAR", "ORDERMIN", "FEHLT BIS ORDERMIN", "WERT")
    linien = [kopf, "-" * len(kopf)]
    for z in zeilen:
        linien.append("%-10s %16.8g %-15s %-12s %14s %16s %12s"
                      % (z["code"], z["menge"], z["lage"], z.get("paar") or "-",
                         ("%.8g" % z["ordermin"]) if z.get("ordermin") else "-",
                         ("%.8g" % z["fehlt"]) if z.get("fehlt") else "-",
                         ("%.2f" % z["wert_quote"]) if z.get("wert_quote") is not None else "-"))
    return "\n".join(linien)


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--alle", action="store_true",
                   help="auch die handelbaren Posten zeigen (Standard: nur festliegende)")
    a.add_argument("--json", action="store_true", help="maschinenlesbar")
    a.add_argument("--ohne-kurse", action="store_true",
                   help="ohne Kursabrufe (dann ohne Wert-Spalte)")
    args = a.parse_args()

    staende = k.kontostaende()
    zeilen = lage(staende, paare_lesen())
    fest = [z for z in zeilen if z["lage"] in FEST]
    if not args.ohne_kurse:
        werte_ergaenzen(zeilen)
    ausgabe = zeilen if args.alle else fest

    if args.json:
        print(json.dumps({"n_posten": len(zeilen), "n_festliegend": len(fest),
                          "posten": ausgabe}, ensure_ascii=False, indent=2))
        return 0
    if not ausgabe:
        print("kein festliegender Posten - alles handelbar")
        return 0
    print(_tabelle(ausgabe))
    print()
    for z in ausgabe:
        print("%-10s %s" % (z["code"], z["grund"]))
    print()
    print("%d von %d Posten liegen fest (unter ordermin oder ohne Paar)"
          % (len(fest), len(zeilen)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())