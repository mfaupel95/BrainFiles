#!/usr/bin/env python3
"""Bewertet die Einstellungen eines OKX-DCA-Bots gegen echte Kursdaten.

Zwei Teile:
  1. Leitergeometrie - reicht die Nachkaufleiter bis an den Stop-Loss heran,
     oder liegt reserviertes Geld tot unter einer Schwelle, die nie erreicht
     wird?
  2. Rueckrechnung ueber echte Kerzen - wie oft haette der Bot sein Ziel
     erreicht, und deckt die Trefferquote das Verhaeltnis von Gewinn zu
     Verlust?

Aufruf:
    python dca_auswertung.py                 # Kurzfassung, 12 Monate
    python dca_auswertung.py --tage 30       # anderer Zeitraum
    python dca_auswertung.py --details       # je Variante Gewinn/Verlust

Die Bot-Werte unten in KONFIG anpassen; sie stehen alle in der Antwort von
dca_get_order_details bzw. dca_get_orders.

Wichtig: OKX antwortet ohne User-Agent mit HTTP 403 - siehe HEADERS.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- Bot-Einstellungen (Stand des BTC-Bots vom 24.08.2026) ------------------
KONFIG = dict(
    einstieg=79917.0,   # initPx
    init=28.0,          # initOrdAmt, Margin in USDC
    safety=8.0,         # safetyOrdAmt
    n_safety=8,         # maxSafetyOrds
    schritt=0.0044,     # pxSteps
    schritt_mult=0.94,  # pxStepsMult
    vol_mult=1.1,       # volMult
    hebel=10,           # lever
    tp=0.006,           # tpPct
    sl=0.03,            # slPct - haengt am EINSTIEG, nicht am Schnitt
    trigger=0.0177,     # Preis-Trigger als Abstand nach unten, None = keiner
)
GEBUEHR = 0.0005       # 0,05 % je Ausfuehrung, gemessen am echten Fill
HEADERS = {"User-Agent": "Mozilla/5.0"}   # ohne dies: HTTP 403


def kerzen_holen(bar="1H", anzahl=8760, inst="BTC-USDT", cache=True):
    """Kerzen von OKX holen, aufsteigend sortiert als [ts, o, h, l, c]."""
    datei = "kerzen_%s_%s_%d.json" % (inst, bar, anzahl)
    if cache and os.path.exists(datei):
        return json.load(open(datei))
    basis = ("https://www.okx.com/api/v5/market/history-candles"
             "?instId=%s&bar=%s&limit=100" % (inst, bar))
    rows, after, fehler = [], None, 0
    while len(rows) < anzahl and fehler < 10:
        u = basis + ("&after=%s" % after if after else "")
        try:
            req = urllib.request.Request(u, headers=HEADERS)
            antwort = urllib.request.urlopen(req, timeout=15).read().decode()
            d = json.loads(antwort)
        except Exception as e:
            fehler += 1
            print("  Fehler %d: %s" % (fehler, e), file=sys.stderr)
            time.sleep(1)
            continue
        if d.get("code") != "0" or not d.get("data"):
            break
        b = d["data"]
        rows.extend(b)
        after = b[-1][0]
        time.sleep(0.1)
    rows = [[int(r[0])] + [float(x) for x in r[1:5]] for r in rows]
    rows.sort(key=lambda r: r[0])
    if cache:
        json.dump(rows, open(datei, "w"))
    return rows


def leiter(einstieg, k=KONFIG, mult=None):
    """Preise und Nominalbetraege der Nachkaufleiter, relativ zum Einstieg."""
    mult = k["schritt_mult"] if mult is None else mult
    stufen = [(einstieg, k["init"] * k["hebel"])]
    p, s = einstieg, k["schritt"]
    for i in range(k["n_safety"]):
        p = p * (1 - s)
        s *= mult
        stufen.append((p, k["safety"] * (k["vol_mult"] ** i) * k["hebel"]))
    return stufen


def geometrie(k=KONFIG):
    """Wie viel der Reserve ist unter dem festen Stop-Loss erreichbar?"""
    sl_preis = k["einstieg"] * (1 - k["sl"])
    reserve = k["init"] + sum(k["safety"] * k["vol_mult"] ** i
                              for i in range(k["n_safety"]))
    print("Einstieg %.0f, fester Stop-Loss %.0f (%.0f %% darunter)"
          % (k["einstieg"], sl_preis, k["sl"] * 100))
    print("%-6s | %-11s | %-17s | %s"
          % ("Mult", "Leiterende", "nutzbare Stufen", "einsetzbar"))
    print("-" * 64)
    for mult in (0.94, 1.0, 1.1, 1.2):
        st = leiter(k["einstieg"], k, mult)
        nutzbar = [s for s in st if s[0] > sl_preis]
        marke = "  <-- eingestellt" if abs(mult - k["schritt_mult"]) < 1e-9 else ""
        print("%-6.2f | %11.0f | %6d von %-6d | %3.0f von %3.0f $%s"
              % (mult, st[-1][0], len(nutzbar) - 1, k["n_safety"],
                 sum(x[1] for x in nutzbar) / k["hebel"], reserve, marke))


def runde(rows, i, k, mult, sl_pct, trigger_pct, horizont, tp_zuerst=False):
    """Eine Runde ab Kerze i durchspielen. Gibt (Ausgang, Ergebnis) zurueck."""
    einstieg = rows[i][4]
    stufen = leiter(einstieg, k, mult)
    nr, notional, size = 1, stufen[0][1], stufen[0][1] / einstieg
    sl = einstieg * (1 - sl_pct)
    trig = einstieg * (1 - trigger_pct) if trigger_pct else None

    def schluss(px):
        return size * px - notional - GEBUEHR * (notional + size * px)

    for j in range(i + 1, min(i + 1 + horizont, len(rows))):
        hoch, tief = rows[j][2], rows[j][3]

        def abwaerts():
            nonlocal nr, notional, size
            if trig and tief <= trig:
                return "trigger", trig
            while (nr < len(stufen) and tief <= stufen[nr][0]
                   and stufen[nr][0] > sl):
                px, n = stufen[nr]
                notional += n
                size += n / px
                nr += 1
            return ("sl", sl) if tief <= sl else None

        def aufwaerts():
            ziel = (notional / size) * (1 + k["tp"])
            return ("tp", ziel) if hoch >= ziel else None

        for f in ((aufwaerts, abwaerts) if tp_zuerst else (abwaerts, aufwaerts)):
            r = f()
            if r:
                return r[0], schluss(r[1])
    return "offen", schluss(rows[min(i + horizont, len(rows) - 1)][4])


def ruecklauf(rows, varianten, k=KONFIG, horizont=72, schritt=2, details=False):
    print("%-32s | %6s | %7s | %5s | %6s | %8s"
          % ("Variante", "Ziel", "Trigger", "Stopp", "offen", "je Runde"))
    print("-" * 82)
    for name, mult, sl_pct, trig in varianten:
        z = {"tp": 0, "trigger": 0, "sl": 0, "offen": 0}
        gewinne, verluste, summe, n = [], [], 0.0, 0
        for i in range(0, len(rows) - horizont - 1, schritt):
            art, pnl = runde(rows, i, k, mult, sl_pct, trig, horizont)
            z[art] += 1
            summe += pnl
            n += 1
            if art == "tp":
                gewinne.append(pnl)
            elif art != "offen":
                verluste.append(pnl)
        print("%-32s | %5.1f%% | %6.1f%% | %4.1f%% | %5.1f%% | %+7.2f $"
              % (name, z["tp"] / n * 100, z["trigger"] / n * 100,
                 z["sl"] / n * 100, z["offen"] / n * 100, summe / n))
        if details and verluste:
            mg = sum(gewinne) / len(gewinne)
            mv = abs(sum(verluste) / len(verluste))
            quote = len(gewinne) / (len(gewinne) + len(verluste)) * 100
            print("%-32s   Gewinn %.2f $, Verlust %.2f $ im Schnitt -> "
                  "noetig %.1f %%, erreicht %.1f %%"
                  % ("", mg, mv, mv / (mg + mv) * 100, quote))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tage", type=int, default=365)
    p.add_argument("--details", action="store_true")
    p.add_argument("--kein-cache", action="store_true")
    a = p.parse_args()

    print("=== 1. Leitergeometrie ===")
    geometrie()

    print("\n=== 2. Rueckrechnung ueber %d Tage ===" % a.tage)
    rows = kerzen_holen("1H", a.tage * 24, cache=not a.kein_cache)
    print("%d Stundenkerzen, %s bis %s\n"
          % (len(rows),
             time.strftime("%d.%m.%Y", time.localtime(rows[0][0] / 1000)),
             time.strftime("%d.%m.%Y", time.localtime(rows[-1][0] / 1000))))
    t = KONFIG["trigger"]
    ruecklauf(rows, [
        ("Ist-Zustand", 0.94, 0.03, t),
        ("Mult 1,05 statt 0,94", 1.05, 0.03, t),
        ("ohne Preis-Trigger", 0.94, 0.03, None),
        ("Stop-Loss 6 %, ohne Trigger", 0.94, 0.06, None),
        ("Trigger erst bei -3 %", 0.94, 0.03, 0.03),
    ], details=a.details)
    print("\nGrenzen: Funding-Gebuehren sind nicht enthalten, die echten Werte"
          "\nliegen darunter. Stundenkerzen loesen nicht auf, ob Hoch oder Tief"
          "\nzuerst kam. Vergangenheit sagt nichts ueber die Zukunft.")


if __name__ == "__main__":
    main()
