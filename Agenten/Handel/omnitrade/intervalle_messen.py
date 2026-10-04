"""Intervalle messen: wie oft, wie treffsicher, und was die Gebuehren fressen.

WARUM DIESES WERKZEUG EXISTIERT
-------------------------------
Die Frage "kann omnitrade oefter handeln, mit Hebel und Trailing-Stop?" ist
keine Gefuehlssache, sondern eine Messung: die Signalzahl je Zeiteinheit, die
Trefferquote und der Gebuehrensatz entscheiden sie. Dieses Werkzeug faehrt die
Strategien aus `strategien/` ueber dieselben Tage auf mehreren Kerzenlaengen
(5m/15m/1h/4h) und mehreren Gebuehrensatzen (Kraken-Spot 0,6 % je Seite,
OKX/Kraken-Futures 0,05 % je Seite) durch den ECHTEN Rust-Backtest
(`omnitrade-cli backtest`, dieselbe Engine wie der Live-Lauf).

Nichts wird dabei nachgebaut: das Skript laedt die Kerzen (Binance, oeffentlich,
kein Schluessel), schreibt sie in das CSV-Format des Backtests und ruft das
fertige Binary. `OMNI_LONG_ONLY=1` stellt den Spot-Live-Lauf nach (sell
schliesst nur die Long-Position, eroeffnet keine Short-Gegenposition).

Aufruf (aus Agenten/Handel/omnitrade):
    ../../scanner/.venv/Scripts/python.exe intervalle_messen.py --tage 60
    ... --takte 15m,5m --skripte adx_macd,rsi30_stop5 --gebuehren 0.006,0.0005
Ergebnis: Tabelle auf stdout, Rohzahlen in cache/intervalle-<zeit>.json.
"""

import argparse
import json
import os
import subprocess
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
WURZEL = os.path.dirname(os.path.dirname(HANDEL))
OMNITRADE = os.path.join(WURZEL, "Werkstatt", "omnitrade")
BIN_KANDIDATEN = (os.path.join(OMNITRADE, "target-live", "release", "omnitrade-cli.exe"),
                  os.path.join(OMNITRADE, "target", "release", "omnitrade-cli.exe"),
                  os.path.join(OMNITRADE, "target", "debug", "omnitrade-cli.exe"))


def binary():
    """Das JUENGSTE vorhandene Binary - dieselbe Reihenfolge wie
    omnitrade_start.py. Ein alter Bau kennt neue Sprachfunktionen nicht (der
    Debug-Bau vom 30.09. 09:31 kannte `adx` nicht und liess adx_macd mit
    'UndefinedFunction' durchfallen), deshalb entscheidet das Alter, nicht der
    Pfad."""
    da = [p for p in BIN_KANDIDATEN if os.path.isfile(p)]
    if not da:
        raise SystemExit("kein omnitrade-cli.exe gefunden - bitte `cargo build`")
    # Reihenfolge wie omnitrade_start.py: der Live-Bau zuerst. Der Debug-Bau
    # liegt zuletzt - er ist derselbe Code, aber rund zehnmal langsamer.
    return da[0]
CACHE = os.path.join(HIER, "cache")

if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)
import historie_binance as hb                                  # noqa: E402

# Kerzenlaenge -> Millisekunden, fuer das Fenster und die Runden je Tag.
MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000,
      "4h": 14_400_000, "1d": 86_400_000}


def ende_bis(wert):
    """`--bis` lesbar machen: Millisekunden, Sekunden oder ISO-Zeit.

    WARUM (04.10.2026): zwei Luefe mit derselben Tageszahl sind nicht
    dieselbe Messung. Ohne festen Endpunkt laeuft `--tage 28` immer "jetzt",
    und der Unterschied zwischen 20:44 und 23:47 ergab 3,25 Stunden
    verschobene Kerzen - dieselbe Strategie las +117,04 und +187,47. Eine
    Tageszahl ist erst ein Fenster, wenn Anfang UND Ende feststehen.
    Fuer den Vergleich zweier Fenster setzt man deshalb beide auf denselben
    Endpunkt: `--bis <ms> --tage 28` und `--bis <ms> --tage 42` sind dann
    ineinander enthalten, statt zwei verschiedene Marktstuecke zu sein.
    """
    if wert is None:
        return None
    wert = str(wert).strip()
    if wert.isdigit():
        n = int(wert)
        return n if n > 10_000_000_000 else n * 1000
    for muster in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M",
                   "%Y-%m-%d"):
        try:
            return int(time.mktime(time.strptime(wert, muster)) * 1000)
        except ValueError:
            continue
    raise SystemExit("--bis nicht lesbar: %r (erwartet Millisekunden, "
                     "Sekunden oder ISO-Zeit)" % wert)


def kerzen_holen(inst, takt, tage, jetzt_ms=None):
    """Kerzen von Binance als Backtest-CSV-Text (Kopf wie daten/*.csv)."""
    jetzt = jetzt_ms if jetzt_ms is not None else int(time.time() * 1000)
    von = jetzt - tage * 86_400_000
    reihen = hb.von_binance(inst, takt.upper(), von, jetzt)
    kopf = "timestamp_ms,open,high,low,close,volume\n"
    zeilen = ["%d,%.8f,%.8f,%.8f,%.8f,%.8f" % tuple(r[:6]) for r in reihen]
    return kopf + "\n".join(zeilen) + "\n", len(reihen)


def csv_schreiben(inst, takt, tage, ordner, jetzt_ms=None):
    text, n = kerzen_holen(inst, takt, tage, jetzt_ms)
    os.makedirs(ordner, exist_ok=True)
    pfad = os.path.join(ordner, "%s_%s.csv" %
                        (inst.replace("/", "").replace("-", "").lower(), takt))
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return pfad, n


def backtest(skript, daten, gebuehr, einsatz, menge=0.1, slippage_bps=5.0):
    """Ein Lauf des ECHTEN Backtests. Rueckgabe: Dict aus der Ausgabe."""
    befehl = [binary(), "backtest", "--script", skript, "--data", daten,
              "--initial-balance", str(einsatz), "--quantity", str(menge),
              "--fee-rate", str(gebuehr), "--slippage-bps", str(slippage_bps)]
    umg = dict(os.environ)
    umg["OMNI_LONG_ONLY"] = "1"          # wie der Spot-Live-Lauf
    p = subprocess.run(befehl, cwd=OMNITRADE, env=umg, capture_output=True,
                       text=True, timeout=900)
    aus = {"ok": p.returncode == 0, "roh": (p.stdout or "") + (p.stderr or "")}
    for zeile in aus["roh"].splitlines():
        for name, schluessel in (("Total PnL:", "pnl"), ("Final Balance:", "ende"),
                                 ("Total Trades:", "runden"),
                                 ("Win Rate:", "treffer"),
                                 ("Max Drawdown:", "dd")):
            if zeile.strip().startswith(name):
                rest = zeile.split(":", 1)[1].strip().rstrip("%")
                try:
                    aus[schluessel] = float(rest)
                except ValueError:
                    pass
    return aus


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instrument", default="BTC-USDT")
    ap.add_argument("--tage", type=int, default=60)
    ap.add_argument("--takte", default="5m,15m,1h,4h")
    ap.add_argument("--skripte", default="adx_macd,rsi30_stop5,adx_macd_trail")
    ap.add_argument("--gebuehren", default="0.006,0.0005",
                    help="Gebuehr JE SEITE (0.006 Kraken-Spot, 0.0005 Futures)")
    ap.add_argument("--einsatz", type=float, default=10000.0)
    ap.add_argument("--menge", type=float, default=0.1)
    ap.add_argument("--daten-ordner", default=os.path.join(OMNITRADE, "daten", "messung"))
    ap.add_argument("--bis", default=None,
                    help="fester FensterENDE (ms, s oder ISO) - ohne das laeuft "
                         "jeder Lauf bis 'jetzt' und zwei Tageszahlen sind "
                         "verschiedene Marktstuecke, nicht verschiedene Fenster")
    args = ap.parse_args()

    bis_ms = ende_bis(args.bis)
    takte = [t.strip() for t in args.takte.split(",") if t.strip()]
    skripte = [s.strip() for s in args.skripte.split(",") if s.strip()]
    gebuehren = [float(g) for g in args.gebuehren.split(",") if g.strip()]

    print("Kerzen holen (%s, %d Tage%s) ..." % (
        args.instrument, args.tage,
        ", bis %s" % args.bis if args.bis else ""))
    daten = {}
    for takt in takte:
        pfad, n = csv_schreiben(args.instrument, takt, args.tage,
                                args.daten_ordner, bis_ms)
        daten[takt] = (pfad, n)
        print("  %-4s %6d Kerzen  %s" % (takt, n, os.path.basename(pfad)))

    ergebnisse = []
    for takt in takte:
        for skript in skripte:
            # Haus-eigene Fassung (mit Trailing-Stop) gewinnt, sonst die des
            # Klons. Der Klon liegt unter Werkstatt/ (Junction nach O:), dort
            # schreibt das Haus nicht - neue Fassungen liegen hier.
            eigen = os.path.join(HIER, "strategien", skript + ".omni")
            if os.path.isfile(eigen):
                skript_pfad = eigen.replace("\\", "/")
            else:
                skript_pfad = os.path.join("strategien", skript + ".omni")
                if not os.path.isfile(os.path.join(OMNITRADE, skript_pfad)):
                    print("  uebersprungen: %s fehlt" % skript_pfad)
                    continue
            for gebuehr in gebuehren:
                r = backtest(skript_pfad, daten[takt][0], gebuehr,
                             args.einsatz, args.menge)
                r.update(takt=takt, skript=skript, gebuehr=gebuehr,
                         kerzen=daten[takt][1])
                ergebnisse.append(r)
                if not r["ok"]:
                    print("  FEHLER %s/%s: %s" % (takt, skript,
                                                  r["roh"].strip()[:200]))

    print()
    print("%-5s %-15s %-8s %7s %7s %9s %8s %8s" %
          ("Takt", "Skript", "Gebuehr", "Kerzen", "Runden", "Treffer%", "PnL", "DD%"))
    for r in ergebnisse:
        if not r["ok"]:
            continue
        print("%-5s %-15s %-8.4f %7d %7.0f %9.1f %8.2f %8.2f" %
              (r["takt"], r["skript"], r["gebuehr"], r["kerzen"],
               r.get("runden", 0), r.get("treffer", 0.0), r.get("pnl", 0.0),
               r.get("dd", 0.0)))

    os.makedirs(CACHE, exist_ok=True)
    ziel = os.path.join(CACHE, "intervalle-%s.json" % time.strftime("%Y%m%d-%H%M%S"))
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump({"instrument": args.instrument, "tage": args.tage,
                   "bis": bis_ms, "einsatz": args.einsatz, "menge": args.menge,
                   "laeufe": ergebnisse}, f, indent=2)
    print()
    print("Rohzahlen: %s" % ziel)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())