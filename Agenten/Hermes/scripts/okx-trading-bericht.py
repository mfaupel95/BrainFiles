"""OKX- und Handels-Tagesbericht: Marktdaten + Spurenkennzahlen + Vorschlaege.

Sammeln -> melden (kein Waechter): die Ausgabe IST die Meldung, sie kommt
taeglich 07:45 als no_agent-Hermes-Cron nach Telegram.

WARUM
-----
Es gibt schon den Tagesbericht des Dauerlaufs (Spurenlage, Spiegel, Stufen)
und auswertung_alle.py fuer Kennzahlen auf Zuruf. Was fehlt, ist der Blick
NACH AUSSEN: Was passiert gerade am OKX-DEX (ohne dass eine Spur einsteigt)?
Dazu die belastbaren Kennzahlen aller Spuren an einer Stelle und - nur als
Vorschlag - welche Spur ihre Parameter pruefen lassen sollte.

Grenzen (bewusst):
- Rein lesend. Kein Ein-/Ausstieg, keine Parameteraenderung, nichts schreiben.
- Vorschlaege zeigen an, WO eine Pruefung (handel-spur-optimierung) lohnt;
  sie ersetzen die Pruefung nicht und greifen nie ein (Schutzstufe 1).
- onchainos-CLI ohne Anmeldung genutzt (read-only). Kein Schluessel hier.

Fehlerrichtung:
  --onchainos-json <datei>  ersetzt die CLI durch eine Datei (Gegenprobe)
  --ticker-json    <datei>  ersetzt die OKX-REST-Kurse durch eine Datei
  --nur-spuren               nur der Spurenteil (offline pruefbar)

Aufruf:
  python Agenten/Hermes/scripts/okx-trading-bericht.py
"""
import argparse
import json
import os
import subprocess
import sys
# Die Haus-Bremse: okx_takt begrenzt ALLE OKX-Abrufe des Hauses
# prozessuebergreifend (Datei in Agenten/Handel/cache), damit
# Wache, Zentrale und die drei Dauerlauf-Stufen sich nicht
# gegenseitig in die Drosselung laufen. Gemessen 05.10.2026:
# 6 parallene Threads -> 93x 'OKX 50011', nacheinander -> 0.
import os as _os, sys as _sys
# Die Haus-Bremse gegen OKX-Drosselung. Sie liegt in Agenten/Handel/ und wird
# ueber den PFAD geladen (importlib), nicht ueber sys.path: diese Datei laeuft
# aus Agenten/Hermes/scripts/, wo der Handel-Ordner nicht im Pfad steht. Genau
# darum nehmen es die Spuren (sys.path.append) und die Werkzeuge hier
# (importlib) auf zwei Wegen - Einer waere an einer Stelle falsch.
_s = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(
    _os.path.abspath(__file__)))), "Handel", "okx_takt.py")
if not os.path.exists(_s):
    raise RuntimeError("Haus-Bremse fehlt: %s" % _s)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("okx_takt", _s)
okx_takt = _ilu.module_from_spec(_spec)
_sys.modules["okx_takt"] = okx_takt
_spec.loader.exec_module(okx_takt)

import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                    # Agenten/Hermes/scripts/ -> BrainFiles
HANDEL = WURZEL / "Agenten" / "Handel"
ONCHAINOS = os.environ.get("ONCHAINOS", "") or "onchainos"
OKX_TICKER = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
ZEITGRENZE = 25                             # Sekunden je Netzaufruf

# Spuren, deren Kennzahlen der Bericht zeigt (alle mit belastbarem Buch).
# Auswertung laeuft ueber auswertung_alle.kennzahlen_fuer - EINE Quelle.
SPUREN = ("xperp", "swap", "scanner", "kraken", "orbk", "spiegel", "gitter",
          "nautilus", "squeeze", "wavetrend", "macd_mtf", "supertrend",
          "mosaic", "moondev_funding", "moondev_listingarb", "moondev_topmovers",
          "moondev_marktlage", "iv_wand", "iv_waelle",
          "moondev_whale", "moondev_liquidation", "moondev_sentiment")


def _auswertung():
    """auswertung_alle aus dem Handel-Ordner laden (reine Stdlib).

    Eine zweite Formel hier waere eine zweite Wahrheit; der Bericht ruft die
    vorhandene Kennzahlenfunktion und nichts Eigenes.
    """
    if str(HANDEL) not in sys.path:
        sys.path.insert(0, str(HANDEL))
    import auswertung_alle
    return auswertung_alle


def hole_json(url, zeitgrenze=ZEITGRENZE):
    """JSON von einer URL, oder None bei jedem Netzfehler.

    Ohne User-Agent antwortet OKX mit 403 - der Browser-Kopf ist Pflicht
    (gefundene Falle beim Bau: curl ging, urllib nicht).
    """
    anfrage = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 okx-trading-bericht"})
    try:
        okx_takt.reserviere()
        with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except (OSError, ValueError, urllib.error.URLError):
        return None


def onchainos_aufruf(argumente, zeitgrenze=120):
    """onchainos-CLI aufrufen, (ok: bool, daten: dict|None)."""
    try:
        r = subprocess.run([ONCHAINOS] + argumente,
                           capture_output=True, text=True, timeout=zeitgrenze,
                           errors="replace",
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError):
        return False, None
    if r.returncode != 0:
        return False, None
    try:
        d = json.loads(r.stdout or "")
    except ValueError:
        return False, None
    return bool(d.get("ok")), d


def _zahl(w):
    try:
        return float(w)
    except (TypeError, ValueError):
        return None


def marktteil(onchainos_json=None, ticker_json=None):
    """Zeilen des Marktteils: DEX-Top-Volumen, Leaderboard, BTC/ETH/SOL.

    Alle drei Quellen einzeln abgesichert: faellt eine aus, steht nur diese
    eine Zeile als Hinweis da, der Rest des Marktteils bleibt stehen.
    """
    z = []
    # 1) onchainos memepump: die 5 hoechsten 1h-Volumina (Trench-Teil)
    if onchainos_json:
        daten = onchainos_json
    else:
        ok, daten = onchainos_aufruf(["memepump", "tokens", "--chain", "solana"])
    if not daten or not daten.get("data"):
        z.append("OKX-DEX (memepump): keine Daten")
    else:
        liste = []
        for t in daten["data"]:
            m = t.get("market") or {}
            vol = _zahl(m.get("volumeUsd1h"))
            mc = _zahl(m.get("marketCapUsd"))
            if vol is None:
                continue
            liste.append((vol, mc, t.get("symbol"), t.get("name")))
        liste.sort(key=lambda x: -x[0])
        z.append("OKX-DEX Top-Volumen 1h (Solana):")
        for vol, mc, sym, name in liste[:5]:
            mc_s = ("%.0f" % mc) if mc and mc > 0 else "?"
            z.append("  %-14s %8.0f USD/h  MC %s" %
                     (str(sym)[:14] or (name or "?")[:14], vol or 0, mc_s))
    # 2) onchainos leaderboard: Top-3 nach 7-Tage-Volumen
    if not onchainos_json:
        ok2, lb = onchainos_aufruf(
            ["leaderboard", "list", "--chain", "solana",
             "--time-frame", "3", "--sort-by", "4"])
        if ok2 and lb.get("data"):
            z.append("Leaderboard 7T (Volumen):")
            for e in lb["data"][:3]:
                z.append("  %-20s %12.0f USD  WR %s" %
                         (str(e.get("walletAddress", ""))[:20],
                          _zahl(e.get("txVolume")) or 0,
                          ("%.1f%%" % (_zahl(e.get("winRatePercent")) or 0))
                          if e.get("winRatePercent") else "?"))
        elif onchainos_json:
            pass  # Gegenprobe: Leaderboard-Teil bewusst ausgelassen
        else:
            z.append("OKX-DEX (leaderboard): keine Daten")
    # 3) OKX-REST Spot-Ticker fuer BTC/ETH/SOL (kein Schluessel noetig)
    if ticker_json is not None:
        daten = ticker_json
    else:
        roh = hole_json(OKX_TICKER)
        daten = {"data": roh.get("data") if roh else None, "code": None}
    z.append("OKX-Spot:")
    gefunden = 0
    for x in (daten.get("data") or []):
        if x.get("instId") in ("BTC-USDT", "ETH-USDT", "SOL-USDT"):
            last, op = _zahl(x.get("last")), _zahl(x.get("open24h"))
            if last is None:
                continue
            pct = (100.0 * (last - op) / op) if op else None
            z.append("  %-9s %10.2f  (%s%%)" %
                     (x["instId"], last,
                      ("%+.2f" % pct) if pct is not None else "n/a"))
            gefunden += 1
    if gefunden == 0:
        z.append("  (Ticker nicht lesbar)")
    return z


def spurenteil(nur_spuren=None):
    """Zeilen des Spurenteils: Kennzahlen aller belastbaren Spuren + Vorschlaege.

    Vorschlag = Hinweis auf eine Pruefung, nie eine Aenderung. Die Schwelle
    (negativer Wert ODER Trefferquote unter 45 % bei belastbarem Buch) ist
    eine Aufmerksamkeitsgrenze, kein Handelsurteil.
    """
    ausw = _auswertung()
    z = ["Spuren (geschlossene Runden, nach Kosten):"]
    vorschlaege = []
    for spur in (nur_spuren or SPUREN):
        try:
            k = ausw.kennzahlen_fuer(spur)
        except Exception:
            k = None
        if not k:
            continue
        n = k.get("n", 0)
        pct = k.get("pct")
        treffer = k.get("treffer_pct")
        if pct is None:
            continue
        z.append("  %-18s %3d Runden  %+6.2f%%  Treffer %5.1f%%" %
                 (spur, n, pct, treffer if treffer is not None else 0.0))
        # Nur ein belastbares Buch (MIN_RUNDEN=8 wie in auswertung_alle)
        # rechtfertigt einen Vorschlag - 1-3 Runden sind Rauschen, keine
        # Aussage, und ein Vorschlag daraus waere ein Fehlalarm.
        if not ausw.belastbar(k):
            continue
        if pct < 0 or (treffer is not None and treffer < 45.0):
            vorschlaege.append(
                "%s: %d Runden, %+.2f%%, Treffer %.0f%% - Parameter pruefen "
                "(handel-spur-optimierung), nichts geaendert"
                % (spur, n, pct, treffer or 0.0))
    if vorschlaege:
        z.append("Vorschlaege (nur Hinweise, kein Eingriff):")
        for v in vorschlaege[:5]:
            z.append("  - " + v)
    else:
        z.append("Keine Spur unter der Aufmerksamkeitsschwelle.")
    return z


def bericht(onchainos_json=None, ticker_json=None, nur_spuren=False):
    """Der ganze Bericht als Zeilenliste - importierbar ohne print."""
    z = ["OKX-/Handels-Bericht"]
    if not nur_spuren:
        z += marktteil(onchainos_json, ticker_json)
    z += spurenteil()
    z.append("Rein lesend; nichts wurde geaendert.")
    return z


def main():
    ap = argparse.ArgumentParser(description="OKX- und Handels-Tagesbericht")
    ap.add_argument("--onchainos-json", default=None,
                    help="Datei statt onchainos-CLI (Gegenprobe, gleiche Form)")
    ap.add_argument("--ticker-json", default=None,
                    help="Datei statt OKX-REST-Ticker (Gegenprobe)")
    ap.add_argument("--nur-spuren", action="store_true",
                    help="nur den Spurenteil (offline pruefbar)")
    ap.add_argument("--alles", action="store_true", help="(Kompatibilitaet)")
    args = ap.parse_args()

    onchainos_json = None
    if args.onchainos_json:
        try:
            with open(args.onchainos_json, encoding="utf-8") as f:
                onchainos_json = json.load(f)
        except (OSError, ValueError) as e:
            print("OKX-/Handels-Bericht: --onchainos-json nicht lesbar (%s)" % e)
            return 0
    ticker_json = None
    if args.ticker_json:
        try:
            with open(args.ticker_json, encoding="utf-8") as f:
                ticker_json = json.load(f)
        except (OSError, ValueError) as e:
            print("OKX-/Handels-Bericht: --ticker-json nicht lesbar (%s)" % e)
            return 0

    for zeile in bericht(onchainos_json, ticker_json, args.nur_spuren):
        print(zeile)
    return 0


if __name__ == "__main__":
    sys.exit(main())