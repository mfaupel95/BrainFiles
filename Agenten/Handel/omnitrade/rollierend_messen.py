"""Rollierendes Fenster: ROBUSTHEIT statt Schnappschuss.

WARUM
-----
Ein einzelnes 30-/42-Tage-Fenster dreht das Vorzeichen zwischen Messungen
(gemessen 01.10.2026: adx_macd 15m war +838/60T, -331/42T, +101/30T). Kuerzer
als 30 Tage sind es 15-20 Runden - nicht mehr belastbar; laenger misst ein
altes Regime. Die Frage "haelt die Strategie in der letzten Zeit?" beantwortet
deshalb eine FAMILIE von Fenstern: rollierende 30-Tage-Fenster im Sieben-Tage-
Schritt ueber den ganzen Horizont. Gezaehlt wird, wie viele Fenster POSITIV
sind - ein Wert, der auch bei gegenlaeufigen Einzelfenstern stabil bleibt.

Aufruf (aus Agenten/Handel/omnitrade):
    ../../scanner/.venv/Scripts/python.exe rollierend_messen.py
        --fenster 30 --schritt 7 --tage 180 --takte 15m,1h
    --skripte adx_macd,adx_macd_trail,rsi_long_only --gebuehren 0.0005,0.006

Die eigentliche Rechnung faehrt DERSELBE Rust-Backtest wie der Live-Lauf
(uebernommen aus intervalle_messen.py: binary(), backtest(), Kerzen von
Binance). DD wird ausgewiesen, aber NICHT interpretiert - T-292 (Buchungs-
artefakt: total_equity zaehlt den Positionswert nicht zurueck).
"""

import argparse
import json
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)
# historie_binance liegt im uebergeordneten Handel-Ordner (umbenannt 29.09.2026,
# weil xperp/historie.py die Spur-eigene Datei ist)
_ueber = os.path.dirname(HIER)
if _ueber not in sys.path:
    sys.path.insert(0, _ueber)
import intervalle_messen as messung  # noqa: E402
import historie_binance as hb        # noqa: E402


def kerzen_alle(inst, takt, tage, jetzt_ms=None):
    """Alle Kerzen des Horizonts (ein Abruf je Takt, nicht je Fenster)."""
    jetzt = jetzt_ms if jetzt_ms is not None else int(time.time() * 1000)
    von = jetzt - tage * 86_400_000
    return hb.von_binance(inst, takt, von, jetzt)


def fenster_csv(reihen, von_ms, bis_ms, ordner, name):
    """Ein Fenster als Backtest-CSV; (pfad, kerzen) oder (None, 0)."""
    im = [r for r in reihen if von_ms <= r[0] < bis_ms]
    if len(im) < 100:                      # Warmup schafft kein Signal
        return None, 0
    kopf = "timestamp_ms,open,high,low,close,volume\n"
    text = kopf + "\n".join("%d,%.8f,%.8f,%.8f,%.8f,%.8f" % tuple(r[:6])
                            for r in im) + "\n"
    os.makedirs(ordner, exist_ok=True)
    pfad = os.path.join(ordner, name)
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return pfad, len(im)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instrument", default="BTC-USDT")
    ap.add_argument("--tage", type=int, default=180, help="gesamter Horizont")
    ap.add_argument("--fenster", type=int, default=30, help="Fensterlaenge Tage")
    ap.add_argument("--schritt", type=int, default=7, help="Fensterabstand Tage")
    ap.add_argument("--takte", default="15m,1h")
    ap.add_argument("--skripte", default="adx_macd,adx_macd_trail,rsi_long_only")
    ap.add_argument("--gebuehren", default="0.0005,0.006")
    ap.add_argument("--einsatz", type=float, default=10000.0)
    ap.add_argument("--menge", type=float, default=0.1)
    ap.add_argument("--daten-ordner", default=os.path.join(messung.OMNITRADE,
                                                           "daten", "rollierend"))
    a = ap.parse_args()

    skripte = [s.strip() for s in a.skripte.split(",") if s.strip()]
    gebuehren = [float(g) for g in a.gebuehren.split(",") if g.strip()]
    takte = [t.strip() for t in a.takte.split(",") if t.strip()]
    jetzt_ms = int(time.time() * 1000)

    laeufe = []
    for takt in takte:
        print("Kerzen %s (%d Tage) ..." % (takt, a.tage), flush=True)
        reihen = kerzen_alle(a.instrument, takt.upper(), a.tage, jetzt_ms)
        print("  %d Kerzen" % len(reihen), flush=True)
        schritt = a.schritt * 86_400_000
        von0 = jetzt_ms - a.tage * 86_400_000
        start = von0
        n_fenster = 0
        while start + a.fenster * 86_400_000 <= jetzt_ms:
            von_ms, bis_ms = start, start + a.fenster * 86_400_000
            name = "rollierend_%s_%s_%s.csv" % (
                takt, a.instrument.replace("-", "").lower(),
                time.strftime("%Y%m%d", time.gmtime(von_ms / 1000.0)))
            pfad, n = fenster_csv(reihen, von_ms, bis_ms, a.daten_ordner, name)
            start += schritt
            if not pfad:
                continue
            n_fenster += 1
            for skript in skripte:
                eigen = os.path.join(HIER, "strategien", skript + ".omni")
                if os.path.isfile(eigen):
                    sp = eigen.replace("\\", "/")
                else:
                    sp = os.path.join("strategien", skript + ".omni")
                    if not os.path.isfile(os.path.join(messung.OMNITRADE, sp)):
                        continue
                for gebuehr in gebuehren:
                    r = messung.backtest(sp, pfad.replace("\\", "/"),
                                         gebuehr, a.einsatz, a.menge)
                    laeufe.append({"takt": takt, "skript": skript,
                                   "gebuehr": gebuehr, "von": von_ms,
                                   "kerzen": n, "ok": r.get("ok"),
                                   "runden": r.get("runden", 0.0),
                                   "treffer": r.get("treffer", 0.0),
                                   "pnl": r.get("pnl", 0.0),
                                   "roh": r.get("roh", "")[:100]})
            print("  Fenster ab %s (%d Kerzen) fertig" % (
                time.strftime("%Y-%m-%d", time.gmtime(von_ms / 1000.0)), n),
                flush=True)

    print()
    print("%-4s %-14s %-7s %9s %9s %10s %10s %9s" %
          ("Takt", "Skript", "Gebuehr", "Fenster", "positiv", "med.Runden",
           "med.PnL$", "Sum.PnL$"))
    g = {}
    for r in laeufe:
        g.setdefault((r["takt"], r["skript"], r["gebuehr"]), []).append(r)
    for (takt, skript, gebuehr), liste in sorted(g.items()):
        pos = sum(1 for r in liste if r["pnl"] > 0)
        runden = sorted(r["runden"] for r in liste)
        pnl = sorted(r["pnl"] for r in liste)
        m = len(liste) // 2
        print("%-4s %-14s %-7.4f %9d %9d %10.0f %10.2f %9.2f" %
              (takt, skript, gebuehr, len(liste), pos, runden[m], pnl[m],
               sum(r["pnl"] for r in liste)))

    ziel = os.path.join(messung.CACHE, "rollierend-%s.json"
                        % time.strftime("%Y%m%d-%H%M%S"))
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump({"instrument": a.instrument, "fenster_tage": a.fenster,
                   "schritt_tage": a.schritt, "horizont_tage": a.tage,
                   "laeufe": laeufe}, f, indent=2)
    print("\nRohzahlen: %s" % ziel)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())