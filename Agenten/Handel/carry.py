"""carry.py - Cross-Venue-Spread und Funding, nach Gebuehren bewertet.

Rein lesend. Kein Buch, kein Journal, kein Orderweg - dieses Werkzeug stellt
die Zahlen hin, ueber die eine Spur entscheiden KOENNTE (T-3xx, gebaut nach
der Messung vom 04.10.2026: die im Netz kursierende "Arbitrage ueber 150
Maerkte" scheitert schon an der Gebuehr - groesste echte Luecke zwischen zwei
fuer uns erreichbaren Maerkten 0,012 %, Kraken-Spot-Gebuehr 0,60 % je Seite).

Was hier steht, ist die zweite, ehrliche Form:

  * je Basiswert (BTC, ETH, SOL) die vier Venues, die wir wirklich haben:
      OKX-Spot, OKX-Perp, Kraken-Spot, Kraken-Futures,
  * die Basis jedes Perp gegen den Spot DERSELBEN Boerse (Cash-and-Carry),
  * das Funding je Perp ANNUALISIERT (OKX 3 Zyklen/Tag, Kraken stuendlich),
  * die Kosten je den GEMESSENEN Gebuehren (01.10.2026, eigene Konto-Fuellungen:
      OKX Spot 0,10 %/Seite, OKX Perp 0,05 %, Kraken Spot 0,60 %,
      Kraken Futures 0,04-0,05 % -> konservativ 0,05 %),
  * und das Urteil: bleibt nach einer vollen Runde (4 Seiten) etwas uebrig?

Nur ausgewiesen wird, was die Rechnung traegt. Extrem-Funding auf duennen
Maerkten wird markiert, nicht gehandelt (gemessen 04.10.2026: PF_XBTUSD meldet
Funding 0,46 bei 2 036 Kontrakten offenem Interesse gegen 2 271 365 auf
PI_XBTUSD - ein Signal auf einem Markt, den man nicht fuellen kann, ist eine
Falle).

Aufruf (aus dem Handel-Ordner):
  scanner/.venv/Scripts/python.exe carry.py
  scanner/.venv/Scripts/python.exe carry.py --json
  scanner/.venv/Scripts/python.exe carry.py --breit     (mehr Basiswerte)
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HANDEL = os.path.dirname(os.path.abspath(__file__))
if HANDEL not in sys.path:
    sys.path.append(HANDEL)
try:
    import okx_takt  # noqa: E402  (Haus-Bremse gegen OKX-Drosselung)
except Exception:  # noqa: BLE001 - Werkzeug muss auch ohne den Takt laufen
    okx_takt = None

# --- Gemessene Gebuehren (01.10.2026, eigene Fuellungen; siehe gebuehren_setzen.py)
GEBUEHR = {
    "okx_spot": 0.0010,
    "okx_perp": 0.0005,
    "kraken_spot": 0.0060,
    "kraken_futures": 0.0005,  # gemessen 0,04-0,05 %, konservativ 0,05
}

# Basiswerte: die drei, die auf ALLEN vier Venues liegen.
BASISWERTE = {
    "BTC": {"okx_spot": "BTC-USDT", "okx_perp": "BTC-USDT-SWAP",
            "kraken_spot": "XBTUSDT", "kraken_futures": "PF_XBTUSD"},
    "ETH": {"okx_spot": "ETH-USDT", "okx_perp": "ETH-USDT-SWAP",
            "kraken_spot": "ETHUSDT", "kraken_futures": "PF_ETHUSD"},
    "SOL": {"okx_spot": "SOL-USDT", "okx_perp": "SOL-USDT-SWAP",
            "kraken_spot": "SOLUSDT", "kraken_futures": "PF_SOLUSD"},
}
BREIT = {
    "XRP": {"okx_spot": "XRP-USDT", "okx_perp": "XRP-USDT-SWAP",
            "kraken_spot": "XRPUSDT", "kraken_futures": "PF_XRPUSD"},
    "DOGE": {"okx_spot": "DOGE-USDT", "okx_perp": "DOGE-USDT-SWAP",
             "kraken_spot": "XDGUSDT", "kraken_futures": "PF_DOGEUSD"},
}

# Ein Perp-Funding dieser Groesse (in Bruch) waere > ~0,5 %/Tag = ~200 %/a:
# auf einem duennen Markt eher Datenartefakt als Carry. Markieren, nie handeln.
FUNDING_EXTREM_PRO_TAG = 0.005
# Unter diesem offenen Interesse (USD) gilt ein Kraken-Futures-Markt als duenn.
KRAKEN_OI_MIN_USD = 1_000_000

OKX_BASIS = "https://www.okx.com"
KRAKEN_FUTURES = "https://futures.kraken.com"
KRAKEN_SPOT = "https://api.kraken.com"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# --- Journal-Konfiguration ---
JOURNAL_DIR = Path(__file__).resolve().parent / "carry"
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
ZUSTAND_DATEI = JOURNAL_DIR / "zustand.json"
JOURNAL_DATEI = JOURNAL_DIR / "handelsjournal.csv"


def _get_json(url, get_json=None):
    """Eine JSON-URL lesen. get_json ist die Test-Naht (None = urllib)."""
    if get_json is not None:
        return get_json(url)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as ant:
        return json.loads(ant.read().decode())


def _okx_ruf(pfad, get_json=None):
    if okx_takt is not None:
        try:
            okx_takt.reserviere()
        except Exception:  # noqa: BLE001
            pass
    return _get_json(OKX_BASIS + pfad, get_json)


def _okx_ticker(inst, get_json=None):
    d = _okx_ruf("/api/v5/market/ticker?instId=" + inst, get_json)["data"][0]
    return {"last": float(d["last"]), "bid": float(d["bidPx"]),
            "ask": float(d["askPx"])}


def _okx_funding(inst, get_json=None):
    d = _okx_ruf("/api/v5/public/funding-rate?instId=" + inst,
                 get_json)["data"][0]
    return float(d["fundingRate"])


def _kraken_futures(get_json=None):
    d = _get_json(KRAKEN_FUTURES + "/derivatives/api/v3/tickers", get_json)
    aus = {}
    for t in d.get("tickers", []):
        s = t.get("symbol", "")
        if s in ("PF_XBTUSD", "PF_ETHUSD", "PF_SOLUSD", "PF_XRPUSD",
                 "PF_DOGEUSD"):
            aus[s] = {
                "last": t.get("last"), "bid": t.get("bid"), "ask": t.get("ask"),
                "index": t.get("indexPrice"),
                # Vorsicht Einheiten (gemessen 07.10.2026): `fundingRate` ist
                # bei PF_-Maerkten der ABSOLUTE Betrag in der Kontraktwaehrung
                # (BTC: 2,19 auf ~83.400 = 0,0026 %), `relativeFundingRate` ist
                # die Rate relativ zum Spot - DIE ist die vergleichbare Zahl.
                # Ein Funding-Intervall gibt Kraken NICHT an (Nautilus
                # "does not specify a fixed funding period").
                "funding_rel": t.get("relativeFundingRate"),
                "funding_rel_pred": t.get("relativeFundingRatePrediction"),
                # openInterest ist in KONTRakten (je 1 Einheit der Basis),
                # nicht in USD - fuer den Duenn-Check mit dem Preis rechnen.
                "oi": t.get("openInterest"),
            }
    return aus


def _kraken_spot(paare, get_json=None):
    if not paare:
        return {}
    d = _get_json(KRAKEN_SPOT + "/0/public/Ticker?pair=" + ",".join(paare),
                  get_json)
    aus = {}
    r = d.get("result", {})
    for k, v in r.items():
        aus[k] = {"last": float(v["c"][0]), "bid": float(v["b"][0]),
                  "ask": float(v["a"][0])}
    return aus


def sammeln(breit=False, get_json=None):
    """Alle vier Venues abfragen. Rueckgabe: {basis: {venue: daten, ...}}.

    Ein fehlender Markt (z.B. XRPUSDT-Spot bei Kraken) ist kein Fehler,
    sondern eine leere Luecke; ein komplett toter Abruf wird als
    'fehler' eingetragen statt den ganzen Lauf zu werfen.
    """
    basiswerte = dict(BASISWERTE)
    if breit:
        basiswerte.update(BREIT)
    aus = {}
    fehler = []

    def _fangen(tag, fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            fehler.append("%s: %s" % (tag, str(e)[:100]))
            return None

    for basis, m in basiswerte.items():
        z = {}
        t_okx_spot = _fangen("okx_spot_" + m["okx_spot"],
                             lambda: _okx_ticker(m["okx_spot"], get_json))
        f_okx_perp = _fangen("okx_funding_" + m["okx_perp"],
                             lambda: _okx_funding(m["okx_perp"], get_json))
        t_okx_perp = _fangen("okx_perp_" + m["okx_perp"],
                             lambda: _okx_ticker(m["okx_perp"], get_json))
        if t_okx_spot:
            z["okx_spot"] = t_okx_spot
        if t_okx_perp:
            z["okx_perp"] = t_okx_perp
            if f_okx_perp is not None:
                z["okx_perp"]["funding"] = f_okx_perp
        aus[basis] = z
    kf = _fangen("kraken_futures", lambda: _kraken_futures(get_json)) or {}
    for basis, m in basiswerte.items():
        pf = kf.get(m["kraken_futures"])
        if pf:
            aus[basis]["kraken_futures"] = pf
    ks = _fangen("kraken_spot",
                 lambda: _kraken_spot([m["kraken_spot"] for m in
                                       basiswerte.values()], get_json)) or {}
    for basis, m in basiswerte.items():
        sp = ks.get(m["kraken_spot"])
        if sp:
            aus[basis]["kraken_spot"] = sp
    # Fehler zentral zurueckgeben (alle Bausteine sammeln global in `fehler`)
    aus["_fehler"] = fehler[:]
    return aus


def _mittel(angebot):
    if angebot is None:
        return None
    ask = angebot.get("ask")
    bid = angebot.get("bid")
    if ask and bid:
        return (ask + bid) / 2
    return angebot.get("last")


def auswerten(daten, fehler=None):
    """Je Basiswert die Carry-Tabelle bauen - reine Funktion, testbar ohne Netz.

    Eintraege: basis, okx_spot, okx_perp, kraken_spot, kraken_futures mit
    preis, funding_pa, basis_bp, oi, duenn, extrem, netto_bp, urteil.
    """
    fehler = fehler if fehler is not None else daten.get("_fehler", [])
    zeilen = []
    for basis, z in sorted(daten.items()):
        if basis == "_fehler":
            continue
        okx_spot = _mittel(z.get("okx_spot"))
        okx_perp = z.get("okx_perp")
        okx_funding = (okx_perp or {}).get("funding")
        kraken_spot = _mittel(z.get("kraken_spot"))
        kf = z.get("kraken_futures") or {}

        zeile = {"basis": basis, "okx_spot": okx_spot,
                 "okx_perp": _mittel(okx_perp),
                 "kraken_spot": kraken_spot,
                 "kraken_futures": _mittel(kf),
                 "okx_funding_pa": None, "kraken_funding_rel": None,
                 "okx_basis_bp": None, "kraken_basis_bp": None,
                 "oi_usd": None, "duenn": False, "extrem": False,
                 "netto_bp": None, "urteil": "-"}

        # Funding: OKX annualisiert (3 Zyklen/Tag sind OKX-Doku und messbar),
        # Kraken nur als relative Rate JE ZYKLUS - Kraken nennt kein
        # Intervall, eine annualisierte Kraken-Zahl waere geraten.
        if okx_funding is not None:
            zeile["okx_funding_pa"] = okx_funding * 3 * 365 * 100
            if abs(okx_funding) > FUNDING_EXTREM_PRO_TAG / 24:  # je 8h-Zyklus
                zeile["extrem"] = True
        kf_funding = kf.get("funding_rel")
        if kf_funding is not None:
            zeile["kraken_funding_rel"] = kf_funding * 100  # % je Zyklus
            # Auch als hypothetisches Jahresfunding bei 3 Zyklen/Tag zeigen:
            # nur zum Vergleich, NICHT als Messung (Intervall unbekannt).
            if abs(kf_funding) > FUNDING_EXTREM_PRO_TAG:
                zeile["extrem"] = True
        oi = kf.get("oi")
        preis_kf = zeile["kraken_futures"]
        if oi is not None and preis_kf:
            zeile["oi_usd"] = oi * preis_kf
            if zeile["oi_usd"] < KRAKEN_OI_MIN_USD:
                zeile["duenn"] = True

        # Basis des Perp gegen den Spot DERSELBEN Boerse
        if okx_spot and zeile["okx_perp"]:
            zeile["okx_basis_bp"] = (zeile["okx_perp"] / okx_spot - 1) * 10000
        if kraken_spot and zeile["kraken_futures"]:
            zeile["kraken_basis_bp"] = (zeile["kraken_futures"] /
                                        kraken_spot - 1) * 10000

        # Vollstaendige Cash-and-Carry-Runde: 2 Einstiege + 2 Ausstiege.
        # Spot-Seite je Boerse, Perp-Seite je Boerse. Beispiel long-Spot +
        # short-Perp OKX: 2x OKX-Spot-Gebuehr + 2x OKX-Perp-Gebuehr.
        beste = None
        if zeile["okx_basis_bp"] is not None:
            kosten_bp = (GEBUEHR["okx_spot"] + GEBUEHR["okx_perp"]) * 2 * 10000
            beste = zeile["okx_basis_bp"] - kosten_bp
            zeile["boerse"] = "okx"
        if zeile["kraken_basis_bp"] is not None:
            kosten_bp_k = (GEBUEHR["kraken_spot"] +
                           GEBUEHR["kraken_futures"]) * 2 * 10000
            n_k = zeile["kraken_basis_bp"] - kosten_bp_k
            if beste is None or abs(n_k) < abs(beste):
                beste = n_k
                zeile["boerse"] = "kraken"
        zeile["netto_bp"] = beste
        if zeile["extrem"] or zeile["duenn"]:
            zeile["urteil"] = "Markt-Falle (extrem/duenn), kein Carry"
        elif beste is not None and beste > 0:
            zeile["urteil"] = "nach Gebuehren positiv (%.2f bp)" % beste
        elif beste is not None:
            zeile["urteil"] = "deckt %s nicht" % "Gebuehren"
        zeilen.append(zeile)
    return zeilen, fehler


def zeilen_text(zeilen, fehler):
    linien = []
    ueb = ("Basis  OKX-Spot   OKX-Perp  Basis OKX  Funding OKX/a  "
           "Kraken-Futures  Kraken-Spot  Basis KF  Funding KF/Zykl  "
           "OI USD       netto bp  Urteil")
    linien.append(ueb)
    for z in zeilen:
        def fmt(x, breite=10):
            if x is None:
                return "-".rjust(breite)
            if isinstance(x, float) and abs(x) < 1 and x != 0:
                return ("%.5f" % x).rjust(breite)
            return ("%.4f" % x).rjust(breite)
        duenn = "DUENN " if z["duenn"] else ""
        extrem = "EXTREM " if z["extrem"] else ""
        linien.append(
            "%-5s %-10s %-10s %-9s %-12s %-14s %-12s %-9s %-12s %-12s %-10s %s"
            % (z["basis"],
               fmt(z["okx_spot"]), fmt(z["okx_perp"]),
               fmt(z["okx_basis_bp"], 9) if z["okx_basis_bp"] is not None
               else "-".rjust(9),
               fmt(z["okx_funding_pa"], 12) if z["okx_funding_pa"] is not None
               else "-".rjust(12),
               fmt(z["kraken_futures"]), fmt(z["kraken_spot"]),
               fmt(z["kraken_basis_bp"], 9) if z["kraken_basis_bp"] is not None
               else "-".rjust(9),
               fmt(z["kraken_funding_rel"], 12)
               if z["kraken_funding_rel"] is not None else "-".rjust(12),
               ("%d" % z["oi_usd"]) if z["oi_usd"] is not None
               else "-".rjust(10),
               ("%.1f" % z["netto_bp"]).rjust(10) if z["netto_bp"] is not None
               else "-".rjust(10),
               extrem + duenn + z["urteil"]))
    linien.append("")
    linien.append("Gebuehren je Seite (gemessen 01.10.2026): OKX-Spot 0,10 %, "
                  "OKX-Perp 0,05 %, Kraken-Spot 0,60 %, Kraken-Futures 0,05 %%")
    linien.append("Runde = 2 Einstiege + 2 Ausstiege derselben Boerse. "
                  "netto bp = beste Basis minus Rundenkosten.")
    linien.append("Kraken-Funding: relative Rate JE ZYKLUS (Kraken nennt kein "
                  "Intervall - keine Jahreszahl erfunden). OKX-Funding: p.a. "
                  "bei 3 Zyklen/Tag.")
    if fehler:
        linien.append("")
        linien.append("Fehler (abgefangen):")
        linien.extend("  - " + f for f in fehler)
    return "\n".join(linien)


def _schreibe_journal(zeilen, fehler):
    """Zustand + Journal schreiben. Kein Orderweg - nur Aufzeichnung."""
    erstellt = datetime.now(timezone.utc).isoformat()
    zustand = {"erstellt": erstellt, "zeilen": zeilen, "fehler": fehler}
    tmp = ZUSTAND_DATEI.with_suffix(".tmp")
    tmp.write_text(json.dumps(zustand, ensure_ascii=False, indent=1,
                                  default=str), encoding="utf-8")
    os.replace(str(tmp), ZUSTAND_DATEI)
    with open(JOURNAL_DATEI, "a", encoding="utf-8", newline="") as f:
        if f.tell() == 0:
            f.write("zeitstempel,basis,okx_spot,okx_perp,"
                    "kraken_spot,kraken_futures,okx_basis_bp,"
                    "boerse,netto_bp,urteil\n")
        for z in zeilen:
            ts = datetime.now(timezone.utc).isoformat()
            f.write("%s,%s,%.4f,%.4f,%.4f,%.4f,%.4f,%s,%.1f,%s\n" % (
                ts, z["basis"],
                z.get("okx_spot") or 0, z.get("okx_perp") or 0,
                z.get("kraken_spot") or 0, z.get("kraken_futures") or 0,
                z.get("okx_basis_bp") or 0, z.get("boerse") or "-",
                z.get("netto_bp") if z.get("netto_bp") is not None else 0,
                z.get("urteil", "-").replace(",", ";")))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true",
                    help="Ausgabe als JSON statt Tabelle")
    ap.add_argument("--breit", action="store_true",
                    help="auch XRP und DOGE abfragen")
    args = ap.parse_args()

    daten = sammeln(breit=args.breit)
    zeilen, fehler = auswerten(daten)

    try:
        _schreibe_journal(zeilen, fehler)
    except Exception as e:
        fehler.append("journal: %s" % str(e)[:100])

    if args.json:
        print(json.dumps({"erstellt": datetime.now(timezone.utc).isoformat(),
                          "fehler": fehler, "zeilen": zeilen},
                         ensure_ascii=False, indent=1, default=str))
    else:
        print(zeilen_text(zeilen, fehler))
    return 0


if __name__ == "__main__":
    sys.exit(main())
