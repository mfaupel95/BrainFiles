"""Buch gegen BOERSE: Geister und Waisenauftraege (Kraken, rein lesend bis auf das Ausbuchen).

Warum es dieses Werkzeug gibt (Befund 30.09.2026, T-208)
-------------------------------------------------------
Die Spur `kraken` fuehrt ihr Buch selbst (zustand.json + handelsjournal.csv).
An der Boerse passiert aber auch, was die Spur nicht sieht:

  * Ein Stop-Loss wird von der BOERSE ausgeloest. Verkauft ist verkauft - das
    Buch fuehrt die Position weiter, weil `pruefe_ausstiege` nur Stop und Ziel
    gegen den lebenden Kurs prueft. Der Kurs kann nach dem Ausloesen wieder
    ueber den Stop steigen, dann merkt es niemand. So stand DOTEUR vom 27.09.
    bis 30.09. als Position im Buch, waehrend die Boerse sie am 29.09. um
    01:36 verkauft hatte (Stop O2YTEL-7R6ZT-ULOXRN, 45,99 DOT, 45,89 EUR
    nach Gebuehr) - ein GEIST.

  * Umgekehrt bleibt ein Schutzauftrag stehen, wenn seine Position weg ist
    (Kraken loescht ihn nicht) - eine WAISE. Ein Margin-SELL-Stop ohne
    Long-Position ist beim Ausloesen ein SHORT-Einstieg.

Der Abgleich liefert BEIDE Seiten und ist die eine Stelle, die den Unterschied
zwischen "Buch stimmt" und "Buch behauptet" misst.

Wichtig - Margin zaehlt mit
---------------------------
Ein Guthaben von 0 heisst NICHT, dass keine Position da ist. Am 30.09. lagen
274,6 SUI in vier MARGIN-Positionen, waehrend das Spot-Guthaben 0 SUI zeigte:
die vier SUIEUR-Auftraege sahen wie Waisen aus, obwohl sie genau diese
Positionen schuetzen. Deshalb wird der Bestand aus BEIDEN Quellen gebildet
(BalanceEx + OpenPositions) - und die Positionsliste selbst in beiden
Antwortformen gelesen (`positionen()`, Kraken liefert sie OHNE "open"-Huelle).

Was dieses Werkzeug NICHT tut
-----------------------------
Es storniert NICHTS. Eine Waise wird gemeldet; das Stornieren bleibt ein
eigener, ausdruecklicher Handgriff (`waisen_stops.py --stornieren`).
Ausgebucht wird nur mit einem ECHTEN Boersenerloes (Ledger/ClosedOrders) -
ist der nicht belegbar, bleibt die Position stehen und der Befund heisst
"unklar" statt einer geratenen Zahl.

Aufruf (aus diesem Ordner):
    python abgleich.py                 # Vorschau: nur melden, nichts schreiben
    python abgleich.py --anwenden      # Geister ausbuchen (Journal + Zustand)
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HIER, "handelsjournal.csv")
SCHUTZ = ("stop-loss", "stop-loss-limit", "take-profit", "stop-loss-profit")
# Ein Rest unter 2 % der Buchmenge gilt als "nicht mehr da" (Rundungsreste,
# Teilverkaeufe von Hand). Darueber wird gerechnet, darunter gemeldet.
WEG_QUOTE = 0.02


def _lade(name, pfad):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


kraken = _lade("kraken", os.path.join(HIER, "kraken.py"))
_stops = _lade("spot_stops", os.path.join(HIER, "spot_stops.py"))
_waisen = _lade("waisen_stops", os.path.join(HIER, "waisen_stops.py"))


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def positionen(kraken_modul):
    """Offene MARGIN-Positionen - in BEIDEN Formen der Antwort.

    Die EINE Fassung dieser Regel steht in waisen_stops.positionen(); hier
    nur durchgereicht, damit es keine zweite Wahrheit ueber die Antwortform
    gibt (Kraken liefert OpenPositions als {txid: {...}} OHNE "open"-Huelle,
    OpenOrders hat sie).
    """
    return _waisen.positionen(kraken_modul)


def kontobestand(kraken_modul, stops_modul=None):
    """{MUENZE: {"spot": x, "reserviert": y, "margin": z, "gesamt": x+z}}.

    `spot` ist die Gesamtmenge im Guthaben (Krakens `balance` schliesst die
    reservierte Menge `hold_trade` ein), `margin` der offene Rest der
    Margin-Positionen.
    """
    stops_modul = stops_modul or _stops
    bal = kraken_modul._roh_privat("BalanceEx") or {}
    bestand = {}
    for k, v in bal.items():
        if not isinstance(v, dict):
            continue
        muenze = stops_modul.norm(k)
        bestand[muenze] = {"spot": float(v.get("balance") or 0),
                           "reserviert": float(v.get("hold_trade") or 0),
                           "margin": 0.0, "gesamt": float(v.get("balance") or 0)}
    paare = stops_modul._paare_laden()
    for p in positionen(kraken_modul).values():
        muenze = stops_modul.muenze_aus_paar(p.get("pair"), paare)
        rest = float(p.get("vol") or 0) - float(p.get("vol_closed") or 0)
        e = bestand.setdefault(muenze, {"spot": 0.0, "reserviert": 0.0,
                                        "margin": 0.0, "gesamt": 0.0})
        e["margin"] += rest
        e["gesamt"] = e["spot"] + e["margin"]
    return bestand


def schutzauftraege(kraken_modul, stops_modul=None):
    """Offene Schutzauftraege (Stop und Ziel) mit ihrer Muenze."""
    stops_modul = stops_modul or _stops
    paare = stops_modul._paare_laden()
    raus = []
    for txid, o in ((kraken_modul._roh_privat("OpenOrders") or {}).get("open")
                    or {}).items():
        if not isinstance(o, dict):
            continue
        d = o.get("descr") or {}
        if d.get("ordertype") not in SCHUTZ:
            continue
        raus.append({"txid": txid, "paar": d.get("pair"),
                     "muenze": stops_modul.muenze_aus_paar(d.get("pair"), paare),
                     "menge": float(o.get("vol") or 0),
                     "preis": float(d.get("price") or 0),
                     "art": d.get("ordertype")})
    return raus


def _ist_live(p):
    """Nur echte Positionen haben eine Boersenseite (Papier hat keine)."""
    return bool(p.get("kauf_txid") or p.get("beleg"))


def befunde(positionen_liste, bestand, auftraege, quote=WEG_QUOTE):
    """Reine Rechnung: Buch + Bestand + Auftraege -> Befunde.

    Drei Arten:
      geist   - Position im Buch, an der Boerse nicht (mehr) vorhanden
      waise   - Schutzauftrag, dessen Muenze es an der Boerse nicht gibt
      teils   - Position nur noch teilweise da (Teilverkauf von Hand)
    """
    raus = []
    for p in positionen_liste or []:
        if not _ist_live(p):
            continue
        muenze = (_stops.norm(p.get("muenze")) if p.get("muenze")
                  else _stops.muenze_aus_paar(p.get("paar"), _stops._paare_laden()))
        menge = float(p.get("menge") or 0)
        da = float((bestand.get(muenze) or {}).get("gesamt") or 0)
        if da + 1e-9 >= menge * (1 - quote):
            continue
        raus.append({"art": "geist" if da <= menge * quote else "teils",
                     "paar": p.get("paar"), "muenze": muenze,
                     "menge": menge, "bestand": da,
                     "text": "%s: Buch %.8g, Boerse %.8g %s"
                             % (p.get("paar"), menge, da, muenze)})
    for a in auftraege or []:
        menge = float(a.get("menge") or 0)
        da = float((bestand.get(a.get("muenze")) or {}).get("gesamt") or 0)
        if da + 1e-9 >= menge * (1 - quote):
            continue
        raus.append({"art": "waise", "txid": a.get("txid"), "paar": a.get("paar"),
                     "muenze": a.get("muenze"), "menge": menge, "bestand": da,
                     "art_auftrag": a.get("art"),
                     "text": "%s %s %.8g @ %.6g ohne Bestand (%.8g %s da)"
                             % (a.get("art"), a.get("txid"), menge,
                                float(a.get("preis") or 0), da, a.get("muenze"))})
    return raus


def _ledger_eintraege(kraken_modul, asset, seit):
    """Alle Ledger-Eintraege zu einer Muenze (paginiert, aelteste zuerst)."""
    import time
    alle, ofs = [], 0
    while True:
        r = kraken_modul._roh_privat("Ledgers", asset=asset, start=seit, ofs=ofs,
                                     count=1000)
        led = (r or {}).get("ledger") or {}
        if not led:
            break
        alle.extend(led.items())
        ofs += len(led)
        if len(led) < 1000:
            break
    alle.sort(key=lambda kv: float(kv[1].get("time") or 0))
    return alle


def echter_ausstieg(kraken_modul, p, seit=None):
    """Der ECHTE Boersenerloes einer Buchposition - oder None.

    Erster Zeuge: die Order, die im Buch als Stop steht (`stop_txid`) in
    ClosedOrders. Zweiter Zeuge: der Ledger der Muenze (Verkauf nach dem
    Eroeffnen) mit der passenden Gegenbuchung in der Quotewaehrung.
    Ohne Zeugen wird NICHT gebucht - eine geratene Zahl waere schlimmer als
    eine offene Position.
    """
    import time
    seit = seit or (time.time() - 30 * 86400)
    txid = p.get("stop_txid")
    if txid:
        try:
            closed = (kraken_modul._roh_privat("ClosedOrders", start=seit)
                      or {}).get("closed") or {}
        except Exception:                                         # noqa: BLE001
            closed = {}
        o = closed.get(txid)
        if isinstance(o, dict) and float(o.get("vol_exec") or 0) > 0:
            cost = float(o.get("cost") or 0)
            fee = float(o.get("fee") or 0)
            if cost > 0:
                return {"menge": float(o.get("vol_exec") or 0),
                        "preis": float(o.get("price") or 0) or cost / float(o["vol_exec"]),
                        "brutto": cost, "gebuehr": fee, "netto": cost - fee,
                        "txid": txid, "quelle": "ClosedOrders %s" % txid,
                        "zeit": o.get("closetm")}
    # Zweiter Zeuge: Ledger der Muenze.
    muenze = (_stops.norm(p.get("muenze")) if p.get("muenze")
              else _stops.muenze_aus_paar(p.get("paar"), _stops._paare_laden()))
    try:
        eintraege = _ledger_eintraege(kraken_modul, muenze, seit)
    except Exception:                                             # noqa: BLE001
        return None
    verkauf = None
    for _, e in eintraege:
        if e.get("type") == "trade" and float(e.get("amount") or 0) < 0:
            verkauf = e
    if not verkauf:
        return None
    zeit = float(verkauf.get("time") or 0)
    menge = abs(float(verkauf.get("amount") or 0))
    # Gegenbuchung in der Quotewaehrung (gleicher Zeitstempel).
    gegen = None
    for asset in ("ZEUR", "EUR", "ZUSD", "USD", "USDC", "EURC"):
        for _, e in _ledger_eintraege(kraken_modul, asset, seit):
            if (e.get("type") == "trade" and abs(float(e.get("time") or 0) - zeit) < 1
                    and float(e.get("amount") or 0) > 0):
                gegen = e
                break
        if gegen:
            break
    if not gegen:
        return None
    brutto = float(gegen.get("amount") or 0)
    gebuehr = abs(float(verkauf.get("fee") or 0)) + abs(float(gegen.get("fee") or 0))
    return {"menge": menge, "preis": brutto / menge if menge else 0.0,
            "brutto": brutto, "gebuehr": gebuehr, "netto": brutto - gebuehr,
            "txid": verkauf.get("refid"), "quelle": "Ledger %s" % verkauf.get("refid"),
            "zeit": zeit}


def schon_gebucht(journal_pfad, p):
    """Steht fuer diese Position schon eine Ausbuchung im Journal?

    Macht das Ausbuchen idempotent: bricht der Lauf zwischen Journalzeile und
    Zustandsschreiben ab, darf der naechste Zyklus nicht eine ZWEITE
    Ausbuchungszeile schreiben (dann zaehlte die Runde doppelt).
    """
    if not journal_pfad or not os.path.exists(journal_pfad):
        return False
    menge = "%.8f" % float(p.get("menge") or 0)
    with open(journal_pfad, newline="", encoding="utf-8") as f:
        for z in csv.reader(f):
            if (len(z) >= 10 and z[2] == "verkauf" and z[3] == p.get("paar")
                    and z[6] == menge and "buch_nachgezogen_boerse" in z[9]):
                return True
    return False


def lauf(kraken_modul=None, stops_modul=None, buch=None, anwenden=False,
         schreibe=None, journal=None, journal_pfad=None):
    """Eine Runde Buch <-> Boerse.

    `buch` ist die Positionsliste (Vorgabe: kraken/handeln.lade_zustand()).
    `schreibe(z)` und `journal(*felder)` sind die Schreibwege der Spur; ohne
    sie wird nichts geschrieben (Vorschau). Rueckgabe: Bilanz-Dict.
    """
    kraken_modul = kraken_modul or kraken
    stops_modul = stops_modul or _stops
    journal_pfad = JOURNAL if journal_pfad is None else journal_pfad
    try:
        bestand = kontobestand(kraken_modul, stops_modul)
        auftraege = schutzauftraege(kraken_modul, stops_modul)
    except Exception as e:                                        # noqa: BLE001
        return {"gelesen": False, "fehler": "%s: %s" % (type(e).__name__, e),
                "befunde": [], "ausgebucht": 0}
    fund = befunde(buch, bestand, auftraege)
    bilanz = {"gelesen": True, "fehler": None, "zeit": _jetzt(),
              "befunde": fund, "geister": [f for f in fund if f["art"] == "geist"],
              "waisen": [f for f in fund if f["art"] == "waise"],
              "teils": [f for f in fund if f["art"] == "teils"],
              "ausgebucht": 0, "unklar": []}
    if not anwenden:
        return bilanz
    for f in bilanz["geister"]:
        p = next((x for x in buch if x.get("paar") == f["paar"]
                  and float(x.get("menge") or 0) == f["menge"]), None)
        if p is None:
            continue
        if schon_gebucht(journal_pfad, p):
            buch.remove(p)
            bilanz["ausgebucht"] += 1
            continue
        echt = echter_ausstieg(kraken_modul, p)
        if not echt:
            bilanz["unklar"].append(f["text"])
            continue
        if journal:
            journal(_jetzt(), "live", "verkauf", p["paar"],
                    "%.8g" % echt["preis"], "%.2f" % echt["netto"],
                    "%.8f" % echt["menge"], "", "",
                    "stop (boerse) buch_nachgezogen_boerse | %s" % echt["quelle"])
        buch.remove(p)
        bilanz["ausgebucht"] += 1
    if bilanz["ausgebucht"] and schreibe:
        schreibe()
    return bilanz


def _buch_und_schreiber():
    """Die Spur selbst (nur fuer den CLI-Weg)."""
    if HIER not in sys.path:
        sys.path.insert(0, HIER)
    handeln = _lade("kraken_handeln_abgleich", os.path.join(HIER, "handeln.py"))
    z = handeln.lade_zustand()
    return handeln, z


def main():
    ap = argparse.ArgumentParser(description="Buch gegen Boerse (Vorschau Standard)")
    ap.add_argument("--anwenden", action="store_true",
                    help="Geister wirklich ausbuchen (Journal + Zustand)")
    args = ap.parse_args()

    handeln, z = _buch_und_schreiber()
    positionen_liste = z.get("positionen") or []
    # Wichtig: geschrieben wird GENAU dieses z. Ein zweites lade_zustand()
    # haette die ausgebuchte Position wieder mitgebracht (Befund beim ersten
    # Lauf dieses Werkzeugs, 30.09.2026).
    def _schreibe():
        handeln.schreibe_zustand(z)
    bilanz = lauf(kraken, _stops, buch=positionen_liste, anwenden=args.anwenden,
                  schreibe=_schreibe, journal=handeln.journal)
    if not bilanz["gelesen"]:
        print("Boerse nicht lesbar (%s) - keine Aussage." % bilanz["fehler"])
        return 1
    # Dieselbe Bilanz, die der Zyklus in den Zustand schreibt - ein Werkzeug,
    # das man von Hand ruft, soll dieselbe Spur hinterlassen.
    z["buch_abgleich"] = {"zeit": bilanz["zeit"],
                          "geister": len(bilanz["geister"]),
                          "waisen": [f.get("txid") for f in bilanz["waisen"]],
                          "teils": len(bilanz["teils"]),
                          "ausgebucht": bilanz["ausgebucht"],
                          "unklar": bilanz["unklar"]}
    if args.anwenden:
        _schreibe()
    print("Buch: %d Position(en) | Geister: %d | Waisen: %d | Teils: %d"
          % (len(positionen_liste), len(bilanz["geister"]),
             len(bilanz["waisen"]), len(bilanz["teils"])))
    for f in bilanz["befunde"]:
        print("  %-7s %s" % (f["art"], f["text"]))
    if not bilanz["befunde"]:
        print("  Buch und Boerse stimmen ueberein.")
    if args.anwenden:
        print("Ausgebucht: %d" % bilanz["ausgebucht"])
        for t in bilanz["unklar"]:
            print("  UNKLAR (kein Boersenerloes belegbar): %s" % t)
    else:
        print("VORSCHAU - nichts geschrieben. Mit --anwenden ausbuchen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())