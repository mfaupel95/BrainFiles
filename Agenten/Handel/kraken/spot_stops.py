"""Alle Kraken-SPOT-Bestaende ab einem Mindestwert mit einem Stop-Loss versehen.

Auftrag Max 24.09.2026 (Task T-051): "alle ab 50 EUR".

Warum ein eigenes Werkzeug: `mosaic/kraken_stops_7_5.py` rechnet den Stop aus
dem EINSTIEG des eigenen Buches. Diese Bestaende hat Max von Hand gekauft - es
gibt keinen Einstieg im Buch. Bezugspunkt ist deshalb der AKTUELLE Kurs
(Stop = Kurs minus Prozent), und die Regel bleibt dieselbe: der Stop liegt
immer UNTER dem Markt, nie darueber.

Vorschau ist der Standard. `--anwenden` ordert wirklich.

    python spot_stops.py                      # Vorschau, ab 50 EUR, 7,5 %
    python spot_stops.py --ab-eur 100 --prozent 10
    python spot_stops.py --anwenden
    python spot_stops.py --ohne BTC,ETH,SOL   # schon geschuetzte auslassen

Bereits geschuetzte Bestaende werden erkannt (offene stop-loss-Order ueber
dieselbe Waehrung) und uebersprungen - ein zweiter Stop auf dieselbe Menge
scheitert bei Kraken mit EOrder:Insufficient funds.
"""
import argparse
import importlib.util
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
MOSAIC = os.path.join(HANDEL, "mosaic")

# Muenznamen, die kein Handelspaar sind (Quote-Waehrungen, Staking-Belege)
KEINE_MUENZE = {"ZEUR", "ZUSD", "EUR", "USD", "USDC", "USDT", "DAI", "EURC",
                "PYUSD", "BETH", "ETH2", "ETH2.S"}


def _lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


kraken = _lade("kraken", os.path.join(HIER, "kraken.py"))

# Kraken haengt alten Muenzen ein X/Z voran ("XXBT", "XETH", "ZEUR", "ZUSD")
# und kennzeichnet Sonderformen ("ADA.S" gestakt, "HYPE.B"). Fuer den Vergleich
# zaehlt nur der nackte Muenzname.
_PRAEFIX = {"XXBT": "BTC", "XBT": "BTC", "XETH": "ETH", "XXLM": "XLM",
            "XXRP": "XRP", "XZEC": "ZEC", "XDG": "DOGE", "ZEUR": "EUR",
            "ZUSD": "USD", "ZGBP": "GBP", "ZJPY": "JPY", "ZCAD": "CAD",
            "ZCHF": "CHF", "ZAUD": "AUD"}


def norm(name):
    """Kraken-Schreibweise auf den nackten Muenznamen bringen (XXBT -> BTC)."""
    n = (name or "").strip().upper()
    if not n:
        return ""
    if "/" in n:                       # "SOL/EUR" -> "SOL"
        n = n.split("/")[0]
    for endung in (".S", ".B"):        # "ADA.S" (gestakt), "HYPE.B"
        if n.endswith(endung):
            n = n[: -len(endung)]
    return _PRAEFIX.get(n, n)


def wert_eur(betrag, kurs):
    return None if kurs is None else betrag * kurs


def paar_waehlen(muenze, paare, quote_reihe=("EUR", "USD")):
    """Das Handelspaar zu einer Muenzmenge - EUR vor USD, sonst None.

    paare: {paarname: {"base": ..., "quote": ...}} (schon normalisiert).
    """
    treffer = {}
    for paar, info in paare.items():
        if norm(info.get("base", "")) != muenze:
            continue
        q = norm(info.get("quote", ""))
        if q in quote_reihe and q not in treffer:
            treffer[q] = paar
    for q in quote_reihe:
        if q in treffer:
            return treffer[q]
    return None


def muenze_aus_paar(paar, paare):
    """"ETHEUR"/"XETHZEUR"/"SOL/EUR" -> "ETH"/"SOL" (ueber die Paartabelle)."""
    info = paare.get(paar)
    if info and info.get("base"):
        return norm(info["base"])
    n = (paar or "").strip().upper()
    if "/" in n:
        return norm(n.split("/")[0])
    # Lange Kraken-Form endet auf die ROHE Quote ("XXBTZUSD" -> "XXBT"), kurze
    # ("ALGOEUR") auf die nackte. Beide Formen muessen greifen.
    for q in ("ZUSDT", "ZUSDC", "ZEUR", "ZUSD", "ZGBP", "ZJPY", "ZCAD", "ZCHF",
              "ZAUD", "USDT", "USDC", "EUR", "USD", "GBP"):
        if n.endswith(q) and len(n) > len(q):
            return norm(n[: -len(q)])
    return norm(n)


def geschuetzte(offene, paare=None):
    """Muenzmengen, die schon einen Stop tragen -> {Muenze: (paar, menge, preis)}.

    Nimmt die rohen OpenOrders-Zeilen (dicts). kraken.offene_orders() liefert
    dagegen nur Paarnamen (Liste von str) - daraus laesst sich nichts ableiten.
    """
    raus = {}
    for o in offene or []:
        if not isinstance(o, dict):
            continue
        if (o.get("descr") or {}).get("ordertype") not in ("stop-loss",
                                                          "stop-loss-limit"):
            continue
        d = o.get("descr") or {}
        muenze = muenze_aus_paar(d.get("pair"), paare or {})
        if muenze:
            raus[muenze] = (d.get("pair"), float(o.get("vol") or 0),
                            float(d.get("price") or 0))
    return raus


def plan(bestaende, halte, paare, kurse, offene=None, ab_eur=50.0, prozent=7.5,
         ohne=()):
    """Reine Rechnung: welche Muenzmenge bekommt welchen Stop?

    bestaende: {muenzname: gesamter Betrag}   halte: {muenzname: hold_trade}
    paare:     {paar: {base, quote}}          kurse: {paar: kurs}
    offene:    offene Orders (fuer den Vermerk "hat schon einen Stop")

    Geordert wird immer nur der FREIE Teil (Betrag minus hold_trade) - was eine
    bestehende Order schon reserviert, ist entweder geschuetzt oder laesst sich
    ohnehin nicht ein zweites Mal belegen (EOrder:Insufficient funds).
    """
    schon = geschuetzte(offene, paare)
    zeilen = []
    for roh, betrag in sorted(bestaende.items()):
        muenze = norm(roh)
        frei = max(0.0, float(betrag) - float((halte or {}).get(roh, 0.0)))
        zeile = {"muenze": muenze, "roh": roh, "menge": frei,
                 "gesamt": float(betrag), "status": "ok", "grund": ""}
        if muenze in KEINE_MUENZE:
            zeile.update(status="hinweis", grund="keine Muenzmenge (Quote/Staking)")
            zeilen.append(zeile)
            continue
        if frei <= 0 or frei < 1e-6 * float(betrag):
            # Der Rest ist Staub: die Order reserviert die Menge auf lot_decimals
            # gerundet, ein Haar bleibt als "frei" stehen.
            zeile.update(status="hinweis",
                         grund="vollstaendig reserviert (hold_trade)")
            zeilen.append(zeile)
            continue
        if muenze in ohne:
            zeile.update(status="hinweis", grund="per --ohne ausgelassen")
            zeilen.append(zeile)
            continue
        if muenze in schon:
            zeile["schon"] = "traegt schon einen Stop (%s @ %s)" % (schon[muenze][0],
                                                                    schon[muenze][2])
        paar = paar_waehlen(muenze, paare)
        if not paar:
            zeile.update(status="hinweis", grund="kein EUR/USD-Handelspaar")
            zeilen.append(zeile)
            continue
        kurs = kurse.get(paar)
        if not kurs:
            zeile.update(status="hinweis", grund="kein Kurs fuer %s" % paar)
            zeilen.append(zeile)
            continue
        zeile["paar"] = paar
        zeile["quote"] = norm(paare[paar]["quote"])
        zeile["kurs"] = kurs
        zeile["wert"] = frei * kurs
        if zeile["wert"] < ab_eur:
            zeile.update(status="hinweis",
                         grund="nur %.2f %s (unter %.0f)"
                               % (zeile["wert"], zeile["quote"], ab_eur))
            zeilen.append(zeile)
            continue
        stop = round(kurs * (1 - prozent / 100.0), 8)
        if stop >= kurs:
            zeile.update(status="hinweis", grund="Stop nicht unter dem Markt")
            zeilen.append(zeile)
            continue
        zeile["stop"] = stop
        zeilen.append(zeile)
    return zeilen


def _paare_laden():
    roh = kraken._roh_oeffentlich("AssetPairs")
    paare = {}
    for name, info in roh.items():
        paare[name] = {"base": info.get("base"), "quote": info.get("quote"),
                       "lot_decimals": info.get("lot_decimals"),
                       "ordermin": info.get("ordermin")}
    return paare


def _kurse_laden(paare_liste):
    kurse = {}
    for p in paare_liste:
        try:
            kurse[p] = kraken.letzter_kurs(p)
        except Exception as e:            # noqa: BLE001 - Kurs fehlt, Zeile wird Hinweis
            print("   Kurs fuer %s nicht abrufbar: %s" % (p, e), file=sys.stderr)
    return kurse


def _betrag_gerundet(zeile, paare):
    """Menge auf lot_decimals abrunden und gegen ordermin pruefen."""
    info = paare.get(zeile["paar"], {})
    stellen = info.get("lot_decimals")
    stellen = 8 if stellen is None else int(stellen)   # 0 ist gueltig (PEPE)!
    menge = float(int(zeile["menge"] * 10 ** stellen)) / 10 ** stellen
    mindest = float(info.get("ordermin") or 0)
    if menge < mindest:
        return None, "Menge %s unter ordermin %s" % (menge, mindest)
    return menge, ""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anwenden", action="store_true", help="wirklich ordern")
    ap.add_argument("--ab-eur", type=float, default=50.0,
                    help="Mindestwert des Bestandes (Standard 50)")
    ap.add_argument("--prozent", type=float, default=7.5,
                    help="Abstand unter dem Kurs (Standard 7,5)")
    ap.add_argument("--ohne", default="", help="Muenznamen, die ausgelassen werden")
    args = ap.parse_args()
    ohne = {norm(x) for x in args.ohne.split(",") if x.strip()}

    bal = kraken._roh_privat("BalanceEx") or {}
    bestaende, halte = {}, {}
    for k, v in bal.items():
        b = float(v.get("balance") or 0)
        if b > 0:
            bestaende[k] = b
            halte[k] = float(v.get("hold_trade") or 0)
    offene = list(((kraken._roh_privat("OpenOrders") or {}).get("open") or {}).values())
    paare = _paare_laden()

    # Kurse nur fuer die Muenzmengen holen, die ueberhaupt in Frage kommen
    kandidaten = []
    for roh, betrag in bestaende.items():
        muenze = norm(roh)
        frei = betrag - halte.get(roh, 0.0)
        if muenze in KEINE_MUENZE or muenze in ohne or frei <= 0:
            continue
        p = paar_waehlen(muenze, paare)
        if p:
            kandidaten.append(p)
    kurse = _kurse_laden(sorted(set(kandidaten)))

    zeilen = plan(bestaende, halte, paare, kurse, offene=offene,
                  ab_eur=args.ab_eur, prozent=args.prozent, ohne=ohne)

    print("Kraken-Spotbestaende, freier Teil ab %.0f, Stop %.1f %% unter dem Kurs"
          % (args.ab_eur, args.prozent))
    print("Muenze     Paar        Menge frei       Kurs        Stop        Wert")
    zu_tun = []
    for z in zeilen:
        schon = (" | " + z["schon"]) if z.get("schon") else ""
        if z["status"] != "ok":
            print("  %-10s %-11s %-16s %-11s %-11s %s"
                  % (z["muenze"], z.get("paar", "-"), "-", "-", "-", z["grund"]))
            continue
        menge, fehler = _betrag_gerundet(z, paare)
        if fehler:
            print("  %-10s %-11s %-16s %-11s %-11s %s"
                  % (z["muenze"], z["paar"], z["menge"], z["kurs"], "-", fehler))
            continue
        z["stop_menge"] = menge
        zu_tun.append(z)
        print("  %-10s %-11s %-16.8g %-11.6g %-11.6g %.2f %s%s"
              % (z["muenze"], z["paar"], menge, z["kurs"], z["stop"], z["wert"],
                 z["quote"], schon))
    print("\n%d Bestand/Bestaende ab %.0f %s ohne Stop."
          % (len(zu_tun), args.ab_eur, (zu_tun[0]["quote"] if zu_tun else "")))
    if not args.anwenden:
        print("VORSCHAU - nichts geordert. Mit --anwenden ausfuehren.")
        return 0

    gut, offen = 0, []
    for z in zu_tun:
        try:
            # stop_setzen gibt die txid zurueck (str) oder None, wenn Kraken nur
            # gerechnet hat; Fehler wirft es als Ausnahme.
            txid = kraken.stop_setzen(z["paar"], z["stop_menge"], z["stop"],
                                      echt=True)
            if not txid:
                print("  UNKLAR   %-10s %s - Kraken lieferte keine Kennung"
                      % (z["muenze"], z["stop"]))
                offen.append(z["muenze"])
                continue
            print("  GESETZT %-10s %-16.8g @ %.8g  %s"
                  % (z["muenze"], z["stop_menge"], z["stop"], txid))
            gut += 1
        except Exception as e:            # noqa: BLE001 - je Bestand melden, weiter
            print("  FEHLER   %-10s %s" % (z["muenze"], e))
            offen.append(z["muenze"])
    print("\n%d von %d gesetzt." % (gut, len(zu_tun)))
    if offen:
        print("Ohne Bestaetigung: %s - an der Boerse nachsehen (OpenOrders), "
              "nicht erneut anwenden." % ", ".join(offen))
    return 0 if gut == len(zu_tun) else 1


if __name__ == "__main__":
    sys.exit(main())
