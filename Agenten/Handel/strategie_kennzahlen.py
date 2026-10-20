"""Kennzahlen je Handels-Spur aus `strategy_metrics.py` (29.09.2026).

Wozu: Max hat ein Formelblatt geschickt (`strategie_metrics.py`). Es rechnet
Kennzahlen, wie das Haus sie NOCH nicht hatte - vor allem zwei:

* **t-Statistik der Expectancy** - beantwortet "ist der Vorteil von 0
  unterscheidbar?". Das Haus sagt bisher nur "unter 8 Runden ist es ein Befund,
  keine Messung"; hier steht die Zahl dazu.
* **Stop aus der MAE** - `stop_from_mae()` setzt den Stop auf das 90-%-Quantil
  des groessten Zwischenverlusts der GEWINNER. Damit kommt der Stop aus den
  eigenen Daten statt aus einer geratenen Zahl.

Was hier NICHT gerechnet wird und warum: Sharpe, Sortino, Calmar, VaR/CVaR und
die Annualisierung brauchen eine ZEITREIHE von Tagesrenditen des
Strategie-Kapitals. Das Haus fuehrt Runden, keine Tageswerte - eine Umrechnung
waere eine Erfindung. Deshalb stehen diese Kennzahlen hier nicht, und das ist
kein Versehen (siehe Wiki/Handel/Strategie-Kennzahlen.md).

Basis sind die RUNDEN aus `auswertung_alle.runden_fuer()` - die Zuordnung
Spur -> Rechenweg liegt dort, hier wird sie nicht nachgebaut.

Aufruf (aus Agenten/Handel, venv mit numpy/pandas, also `.venv`):
    .venv/Scripts/python.exe strategie_kennzahlen.py
    .venv/Scripts/python.exe strategie_kennzahlen.py scanner kraken xperp
"""
from __future__ import annotations

import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

import auswertung_alle as a          # noqa: E402
import strategie_metrics as sm       # noqa: E402

# Weniger Runden sind ein Befund, keine Messung (Hausregel, wie MIN_RUNDEN).
MIN_RUNDEN = 8


def _stop_aus_wachen(spur):
    """Der Stop, den die Spur heute fahrt - als Anteil (0.05 = 5 %)."""
    p = os.path.join(HIER, spur, "wachen.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            w = json.load(f)
    except (OSError, ValueError):
        return None
    for k in ("pflicht_stop_prozent_min", "stop_prozent"):
        if isinstance(w.get(k), (int, float)):
            return float(w[k]) / 100.0
    return None


def mae_gefuehrt(spur):
    """(gefuellte, alle) MAE-Werte im Journal - wird die Spalte ueberhaupt gefuehrt?

    Befund 29.09.2026: Der scanner schreibt bei Ausstiegen mit Grund 'ziel'
    durchweg `mae_pct = 0.0000`; echte Werte stehen nur bei stop,
    herzschlag_alt und den Buchhaltungs-Korrekturen. Ein Stop aus dieser Spalte
    waere deshalb 0 % und damit wertlos. Der Bericht nennt das beim Namen,
    statt eine Null als Messwert auszugeben.
    """
    gefuellt = gesamt = 0
    for z in a.zeilen(spur):
        roh = z.get("mae_pct")
        if roh in (None, ""):
            continue
        gesamt += 1
        try:
            if abs(float(roh)) > 1e-9:
                gefuellt += 1
        except ValueError:
            continue
    return gefuellt, gesamt


def mae_der_gewinner(spur):
    """MAE (Anteil) aller Ausstiege mit Grund 'ziel' - die Gewinner der Spur.

    Nur ECHTE Werte; der Platzhalter 0.0000 wird verworfen.
    """
    raus = []
    for z in a.zeilen(spur):
        if (z.get("grund") or "").strip().lower() != "ziel":
            continue
        roh = z.get("mae_pct")
        if roh in (None, ""):
            continue
        try:
            wert = abs(float(roh)) / 100.0
        except ValueError:
            continue
        if wert > 1e-9:
            raus.append(wert)
    return raus


def bericht(spur, nur_gueltige=True):
    runden = a.runden_fuer(spur)
    # Runden aus der Fehlerzeit (Scanner-Einstieg = Vortagesberichtspreis, bis
    # 02.10.2026 22:23 UTC) zaehlen nicht - gleicher Stichtag und gleiche Regel
    # wie auswertung_alle.kennzahlen_fuer. Die MAE-Werte der Gewinner kommen
    # weiter aus allen Ausstiegszeilen (sie hängen an keiner Runde); der
    # Bericht nennt die Zahl der ausgeschlossenen Runden in n_vor_fix.
    n_vor_fix = 0
    if nur_gueltige and spur in a.GUELTIG_AB:
        grenze = a.zeitfenster.parse(a.GUELTIG_AB[spur])
        gueltig = [r for r in runden if not a._vor_fix(r, grenze)]
        n_vor_fix = len(runden) - len(gueltig)
        runden = gueltig
    if not runden:
        return None
    import stoerungen                                            # noqa: PLC0415

    # Zwangsschluesse SIND gebucht (sie bleiben in Drawdown und Kill-Switch),
    # gehoeren aber nicht in die Verteilung der KENNZAHLEN: ein
    # Herzschlag-Ausstieg ist keine Handelsentscheidung. Dieselbe Lesart wie
    # kennzahlen() im Haus.
    echt, stoer = stoerungen.teile_runden(runden)
    pnl = [r["ergebnis"] for r in echt
           if isinstance(r.get("ergebnis"), (int, float))]
    if len(pnl) < 2:
        return None
    e = sm.expectancy(pnl)
    gewinner_mae = mae_der_gewinner(spur)
    stop_daten = sm.stop_from_mae(gewinner_mae, 0.9) if len(gewinner_mae) >= 5 else None
    gefuellt, gesamt = mae_gefuehrt(spur)
    return {"spur": spur, "e": e, "stop_vorschlag": stop_daten,
            "stop_heute": _stop_aus_wachen(spur),
            "n_gewinner_mae": len(gewinner_mae),
            "n_stoerung": len(stoer), "n_vor_fix": n_vor_fix,
            "mae_gefuellt": gefuellt, "mae_gesamt": gesamt,
            "einheit": a.einheit_fuer(spur)}


def main(argv):
    spuren = argv or [s for s in a.SPUREN if a.runden_fuer(s)]
    print("Kennzahlen aus den Runden (Quelle: auswertung_alle.runden_fuer)\n")
    print("%-22s %4s %4s %7s %9s %6s %7s %9s  %s"
          % ("Spur", "n", "St.", "Treffer", "Erwartung", "PF", "t-Stat",
             "Stop(M)", "Stop heute"))
    zeilen_ = []
    for spur in spuren:
        b = bericht(spur)
        if not b:
            continue
        e = b["e"]
        sv = b["stop_vorschlag"]
        sh = b["stop_heute"]
        marke = "" if e["trades"] >= MIN_RUNDEN else "  (Befund, keine Messung)"
        if sv is not None:
            stop_text = "%.2f%%" % (100 * sv)
        elif b["mae_gefuellt"] < 5:
            stop_text = "MAE ungefuehrt"
        else:
            stop_text = "-"
        print("%-22s %4d %4d %6.1f%% %9.2f %6.2f %7.2f %9s  %s%s"
              % (spur, e["trades"], b["n_stoerung"], 100 * e["winrate"],
                 e["expectancy"], e["profit_factor"], e["t_stat"], stop_text,
                 "%.2f%%" % (100 * sh) if sh is not None else "kein Wert in wachen.json",
                 marke))
        zeilen_.append((spur, b))
    ungefuehrt = [s for s, b in zeilen_ if b["mae_gefuellt"] < 5]
    if ungefuehrt:
        print("\nMAE wird nicht gefuehrt (Platzhalter 0.0000 in den Ausstiegszeilen):")
        for spur, b in zeilen_:
            if b["mae_gefuellt"] < 5:
                print("  %-20s %d von %d Zeilen mit echtem Wert" % (spur, b["mae_gefuellt"], b["mae_gesamt"]))
        print("  -> der Stop-Vorschlag aus der MAE ist deshalb nicht rechenbar.")
    for spur, b in zeilen_:
        if b["n_vor_fix"]:
            print("\n%s: %d Runden vor dem Preisfix (02.10.2026 22:23 UTC) nicht"
                  " mitgerechnet (Einstieg war der Vortagesberichtspreis)."
                  % (spur, b["n_vor_fix"]))
    print("\nSt. = Zwangsschluesse, aus den KENNZAHLEN herausgenommen (gebucht")
    print("bleiben sie: Drawdown und Kill-Switch sehen sie weiter).")
    print("Erwartung = Ø Ergebnis je Runde in USD/EUR (brutto, wie im Journal).")
    print("t-Stat >= 2 heisst: der Vorteil ist von 0 unterscheidbar (95 %),")
    print("t-Stat um 0 heisst: Rauschen. Stop(M) = 90-%-Quantil der MAE der")
    print("Gewinner (nur bei >= 5 echten Werten) - der datengetriebene")
    print("Stop-Vorschlag.")
    print("Sharpe/Sortino/Calmar stehen hier NICHT: sie brauchen Tagesrenditen,")
    print("die das Haus nicht fuehrt (Runden, keine Tageswerte).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))