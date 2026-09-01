"""XPERP-Bot: Lage lesen, Positionen rechnen, Orders vorlegen.

Der Bot loest nichts aus. Er holt die Kerzen, rechnet Signal, Groesse, Stop
und Ziel und legt die fertigen Befehle vor - ausgefuehrt werden sie von Max.
Die Ausnahme vom Handverbot in Wissen/Schutzregeln.md gilt ausdruecklich nur
fuer "nur Spot, nur Long, kein Hebel", also fuer scanner/handeln.py. Ein
gehebelter Futures-Bot faellt nicht darunter.

Die tragende Rechnung steht in groesse(): Der Stop-Abstand kommt aus dem ATR,
die Positionsgroesse aus dem Stop-Abstand, und der Hebel faellt hinten heraus.
Er ist Ergebnis, nicht Eingabe. "5x" ist damit ein Deckel, kein Ziel - genau
die Regel, die in Handel/README.md schon aus dem Titelvergleich gezogen wurde:
Die Hebelhoehe gehoert an die gemessene Volatilitaet gekoppelt, nicht an eine
Kurserwartung.

Aufrufe:
    python bot.py lage   --wert SOL
    python bot.py trend  --wert SOL
    python bot.py grid   --wert SOL
"""

import argparse
import json
import os
import sys

import indikatoren
import okxf

HIER = os.path.dirname(os.path.abspath(__file__))
BAR = "4H"


def wachen():
    with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
        return json.load(f)


# --- Rechnungen -------------------------------------------------------------

def liquidationspreis(einstieg, hebel, wartung, seite="long"):
    """Wo die Boerse zwangsschliesst. Isolierte Margin, ohne Nachschuss.

    Naeherung: Der Einschuss ist 1/hebel des Positionswerts; liquidiert wird,
    wenn davon nur noch die Wartungsmarge uebrig ist. Die echte Formel von OKX
    kennt zusaetzlich Gebuehren und Stufen der Wartungsmarge - sie liegt etwas
    frueher. Deshalb wird hier nie bis an die Liquidation herangeplant, sondern
    der Stop klar darueber gesetzt.
    """
    strecke = 1.0 / hebel - wartung
    return einstieg * (1 - strecke) if seite == "long" else einstieg * (1 + strecke)


def hebel_deckel(k, tage=7, wartung=0.005, obergrenze=20.0):
    """Groesster Hebel, der den groessten Ruecklauf der letzten Tage ueberlebt.

    Rueckblick, keine Zusage. Aber ein Hebel, der schon die letzte Woche nicht
    ueberstanden haette, braucht ueber die naechste nicht diskutiert zu werden.
    """
    hd = min(tage * 6, len(k) - 1)
    if hd < 2:
        return 1.0
    mae_l = mae_s = 0.0
    for i in range(len(k) - hd):
        e = k[i][4]
        mae_l = max(mae_l, 1 - min(r[3] for r in k[i + 1:i + 1 + hd]) / e)
        mae_s = max(mae_s, max(r[2] for r in k[i + 1:i + 1 + hd]) / e - 1)
    return (max(1.0, min(obergrenze, 1.0 / (mae_l + wartung))),
            max(1.0, min(obergrenze, 1.0 / (mae_s + wartung))))


def groesse(w, instr, einstieg, stop, seite, deckel):
    """Kontrakte, Hebel und tatsaechliches Risiko einer Position.

    Reihenfolge: Risikobetrag geteilt durch Stop-Abstand ergibt den
    Positionswert. Erst danach wird geprueft, ob die Margin in den Rahmen
    passt - und wenn nicht, wird die Position kleiner, nicht der Stop weiter.
    """
    abstand = abs(einstieg - stop) / einstieg
    if abstand <= 0:
        return None

    hebel = min(w["max_hebel"], deckel)
    if hebel < 1:
        return None

    nominal_risiko = w["risiko_je_anlauf_usd"] / abstand
    nominal_margin = w["max_margin_je_anlauf_usd"] * hebel
    nominal = min(nominal_risiko, nominal_margin)

    kontrakte, echt = okxf.kontrakte_aus_nominal(instr, nominal, einstieg)
    if kontrakte <= 0:
        return None

    return {
        "kontrakte": kontrakte,
        "nominal": echt,
        "hebel": hebel,
        "margin": echt / hebel,
        "risiko": echt * abstand,
        "abstand": abstand,
        "gedeckelt": nominal_margin < nominal_risiko,
        "liq": liquidationspreis(einstieg, hebel, w["wartungsmarge"], seite),
    }


# --- Ausgaben ---------------------------------------------------------------

def hole(wert):
    instr = okxf.instrument(wert)
    k = okxf.kerzen(instr["instId"], BAR, 300)
    return instr, k


def zeige_lage(w, wert):
    instr, k = hole(wert)
    z = indikatoren.lage(k)
    dl, ds = hebel_deckel(k, wartung=w["wartungsmarge"])
    tick = okxf.tickers().get(instr["instId"], {})
    umsatz = float(tick.get("volCcy24h") or 0) * z["kurs"]
    tage = len(k) / 6.0

    print()
    print("=" * 66)
    print("%s   %s" % (wert.upper(), instr["instId"]))
    print("=" * 66)
    print("  Kurs           %.6f" % z["kurs"])
    print("  ATR(14)        %.6f  = %.2f%% vom Kurs" % (z["atr"], z["atr_pct"] * 100))
    print("  SuperTrend     %s seit %d Kerzen, Linie %.6f" % (
        "AUF" if z["st_richtung"] == 1 else "AB", z["st_dauer"], z["st_linie"]))
    print("  EMA20 / EMA50  %.6f / %.6f  -> %s" % (
        z["ema20"], z["ema50"], "auf" if z["ema20"] > z["ema50"] else "ab"))
    print("  RSI(14)        %.0f" % z["rsi"])
    print("  Effizienz      %.2f  (%s)" % (
        z["er"], "Gezappel - Grid-Futter" if z["er"] < 0.3
        else "gemischt" if z["er"] < 0.6 else "Trend - Grid wird zerrieben"))
    print()
    print("  SIGNAL: %s   (%s)" % (z["signal"].upper(), z["grund"]))
    print()
    print("  Hebel-Deckel   long %.1fx   short %.1fx   (groesster Ruecklauf 7 Tage)" % (dl, ds))
    print("  Umsatz 24h     %.1f Mio USD" % (umsatz / 1e6))
    print("  Historie       %.0f Tage" % tage)

    print()
    tore = [
        ("Historie >= %d Tage" % w["min_historie_tage"], tage >= w["min_historie_tage"]),
        ("Umsatz >= %.0f Mio" % (w["min_umsatz_24h_usd"] / 1e6),
         umsatz >= w["min_umsatz_24h_usd"]),
        ("Hebel-Deckel >= %g" % w["max_hebel"], max(dl, ds) >= w["max_hebel"]),
    ]
    for name, ok in tore:
        print("  [%s] %s" % ("x" if ok else " ", name))
    if not all(ok for _, ok in tore):
        print("\n  -> Mindestens ein Tor ist zu. Vorschlaege werden trotzdem")
        print("     gerechnet, aber mit gesenktem Hebel und mit Warnung.")
    return instr, k, z, (dl, ds)


def zeige_trend(w, wert):
    instr, k, z, (dl, ds) = zeige_lage(w, wert)
    if z["signal"] == "kein":
        print()
        print("Kein Einstieg: %s" % z["grund"])
        print("Der Bot erfindet kein Signal, wenn die Indikatoren sich widersprechen.")
        return 0

    seite = z["signal"]
    deckel = dl if seite == "long" else ds
    atr = z["atr"]
    vz = 1 if seite == "long" else -1

    # Limit unter den Kurs legen (bei Short darueber) - der Einstieg soll
    # Maker sein, nicht Taker. Er kann dadurch liegenbleiben; das ist der
    # bewusste Unterschied zum Marktkauf.
    einstieg = okxf.auf_tick(instr, z["kurs"] - vz * w["einstieg_atr_abschlag"] * atr)
    stop = okxf.auf_tick(instr, einstieg - vz * w["stop_atr_faktor"] * atr)
    ziel = okxf.auf_tick(instr, einstieg + vz * w["ziel_atr_faktor"] * atr)

    g = groesse(w, instr, einstieg, stop, seite, deckel)
    if not g:
        print("\nPosition waere kleiner als ein Kontrakt - kein Vorschlag.")
        return 1

    print()
    print("-" * 66)
    print("TREND-ANLAUF  %s" % seite.upper())
    print("-" * 66)
    print("  Einstieg (Limit)  %.6f   %.2f ATR vom Kurs" % (
        einstieg, w["einstieg_atr_abschlag"]))
    print("  Stop              %.6f   %.2f ATR = %.2f%%" % (
        stop, w["stop_atr_faktor"], g["abstand"] * 100))
    print("  Ziel              %.6f   %.2f ATR = %.2f%%   (%.1f:1)" % (
        ziel, w["ziel_atr_faktor"], abs(ziel - einstieg) / einstieg * 100,
        w["ziel_atr_faktor"] / w["stop_atr_faktor"]))
    print()
    print("  Kontrakte         %g  a %s %s" % (
        g["kontrakte"], instr["ctVal"], instr["ctValCcy"]))
    print("  Positionswert     %.2f USD" % g["nominal"])
    print("  Hebel             %.1fx   (Deckel %.1fx aus dem Ruecklauf, %g aus wachen.json)" % (
        g["hebel"], deckel, w["max_hebel"]))
    print("  Margin            %.2f USD  von %g erlaubt" % (
        g["margin"], w["max_margin_je_anlauf_usd"]))
    print("  Risiko bei Stop   %.2f USD  von %g Budget%s" % (
        g["risiko"], w["risiko_je_anlauf_usd"],
        "  (durch Margin gedeckelt)" if g["gedeckelt"] else ""))
    print()
    print("  Liquidation bei   %.6f" % g["liq"])
    sicher = (stop > g["liq"]) if seite == "long" else (stop < g["liq"])
    if sicher:
        luft = abs(stop - g["liq"]) / einstieg * 100
        print("  -> Der Stop liegt %.2f%% vor der Liquidation. Die Position wird" % luft)
        print("     ausgestoppt, nicht zwangsgeschlossen. So soll es sein.")
    else:
        print("  -> WARNUNG: Der Stop liegt HINTER der Liquidation. Die Boerse")
        print("     schliesst vor dem Stop - der Verlust ist dann die ganze Margin,")
        print("     nicht der gerechnete Risikobetrag. Hebel senken.")

    befehle(instr, seite, g["kontrakte"], einstieg, ziel, stop, g["hebel"])
    return 0


def zeige_grid(w, wert):
    instr, k, z, (dl, _) = zeige_lage(w, wert)
    atr, kurs = z["atr"], z["kurs"]

    spanne_abs = w["grid_spanne_atr"] * atr
    unten = kurs - spanne_abs
    if unten <= 0:
        print("\nSpanne reicht unter null - grid_spanne_atr senken.")
        return 1
    spanne_rel = spanne_abs / kurs

    # Der strukturelle Test. Die oberste Stufe hat den weitesten Weg bis zum
    # Boden des Rasters; ueberlebt sie ihn nicht, sterben die oberen Stufen,
    # bevor die unteren kaufen. Das ist der Befund aus Handel/README.md,
    # Abschnitt "Grid mit Hebel - die Konstruktion traegt nicht".
    hebel_max = 1.0 / (spanne_rel + w["wartungsmarge"] + w["grid_puffer"])
    hebel = min(w["max_hebel"], hebel_max, dl)

    stufen = int(w["grid_stufen"])
    schritt = (kurs / unten) ** (1.0 / stufen)      # geometrisch
    stufe_pct = schritt - 1
    zyklus = 2 * w["gebuehr_maker"]

    print()
    print("-" * 66)
    print("GRID  (nur Long-Stufen, jede mit eigenem Ziel und Stop)")
    print("-" * 66)
    print("  Spanne            %.6f bis %.6f  = %.1f%% tief (%.1f ATR)" % (
        unten, kurs, spanne_rel * 100, w["grid_spanne_atr"]))
    print("  Stufen            %d, geometrisch, Abstand %.2f%%" % (stufen, stufe_pct * 100))
    print()
    print("  Hebel aus der Spanne: hoechstens %.1fx" % hebel_max)
    print("  Hebel aus dem Ruecklauf: hoechstens %.1fx" % dl)
    print("  -> gewaehlt %.1fx" % hebel)
    if hebel_max < w["max_hebel"]:
        print("     (unter den %g aus wachen.json - die Spanne ist zu tief fuer mehr;" % w["max_hebel"])
        print("      mehr Hebel wuerde die oberen Stufen liquidieren, bevor die")
        print("      unteren kaufen)")

    if stufe_pct < zyklus * w["min_stufe_gebuehr"]:
        print()
        print("  ABBRUCH: Ein Stufengewinn von %.3f%% traegt den Zyklus von %.3f%%" % (
            stufe_pct * 100, zyklus * 100))
        print("  nicht (%.0ffach gefordert). Weniger Stufen oder groessere Spanne." % (
            w["min_stufe_gebuehr"]))
        return 1

    # Ein Long-Raster in einen laufenden Abwaertstrend zu legen heisst, auf
    # dem ganzen Weg nach unten zuzukaufen. Das ist der zweite Befund aus
    # Handel/README.md: "Ein Grid ist keine Absicherung; es erhoeht das
    # Engagement, waehrend der Kurs faellt."
    if z["st_richtung"] == -1:
        print()
        print("  WARNUNG: SuperTrend steht seit %d Kerzen auf AB." % z["st_dauer"])
        print("  Ein Long-Grid kauft dann auf dem ganzen Weg nach unten zu. Die")
        print("  Stufen fuellen sich der Reihe nach, ohne dass eine ihr Ziel")
        print("  erreicht. Erst wenn der SuperTrend dreht, arbeitet das Raster.")

    boden = okxf.auf_tick(instr, unten * (1 - w["grid_puffer"]))
    margin_je = w["max_margin_gesamt_usd"] / stufen
    print()
    print("  Stufengewinn %.2f%% gegen Zyklus %.3f%% = %.0ffach gedeckt" % (
        stufe_pct * 100, zyklus * 100, stufe_pct / zyklus))
    print("  Gemeinsamer Stop aller Stufen: %.6f" % boden)
    print()
    print("  %-3s %-11s %-11s %-11s %8s %8s" % (
        "Nr", "Kauf", "Ziel", "Stop", "Kontr.", "Margin"))

    zeilen = []
    for i in range(1, stufen + 1):
        kauf = okxf.auf_tick(instr, kurs / (schritt ** i))
        ziel = okxf.auf_tick(instr, kurs / (schritt ** (i - 1)))
        nominal = margin_je * hebel
        kontrakte, echt = okxf.kontrakte_aus_nominal(instr, nominal, kauf)
        if kontrakte <= 0:
            print("  %-3d %-11.6f  -- zu klein fuer einen Kontrakt" % (i, kauf))
            continue
        liq = liquidationspreis(kauf, hebel, w["wartungsmarge"], "long")
        warn = "" if boden > liq else "  !! Stop hinter Liquidation"
        print("  %-3d %-11.6f %-11.6f %-11.6f %8g %7.2f$%s" % (
            i, kauf, ziel, boden, kontrakte, echt / hebel, warn))
        zeilen.append((i, kauf, ziel, kontrakte))

    print()
    print("  Gesamte Margin    %.2f USD von %g erlaubt" % (
        sum(z[3] * float(instr["ctVal"]) * z[1] for z in zeilen) / hebel,
        w["max_margin_gesamt_usd"]))
    print("  Verlust, wenn alle Stufen kaufen und der Boden faellt:")
    verlust = sum(z[3] * float(instr["ctVal"]) * (z[1] - boden) for z in zeilen)
    print("    rund %.2f USD  (Kill-Switch steht bei %g)" % (
        verlust, w["kill_switch_gesamt_usd"]))
    margin_gesamt = sum(z[3] * float(instr["ctVal"]) * z[1] for z in zeilen) / hebel
    if verlust > w["kill_switch_gesamt_usd"] and verlust > 0:
        passt = margin_gesamt * w["kill_switch_gesamt_usd"] / verlust
        print("    -> UEBER dem Kill-Switch. Der Verlust waechst linear mit der")
        print("       Margin, also passt das Raster bei hoechstens %.0f USD" % passt)
        print("       Gesamtmargin (statt %.0f). Alternativ: engere Spanne" % margin_gesamt)
        print("       (grid_spanne_atr senken) - sie verkuerzt den Weg zum Boden.")

    print()
    print("  Was das Grid nicht kann: Faellt der Kurs unter %.6f, sind alle" % boden)
    print("  Stufen gestoppt und das Raster ist leer. Steigt er ueber %.6f," % kurs)
    print("  ohne vorher zu fallen, passiert gar nichts. Ein Grid gewinnt in")
    print("  der Seitwaertsbewegung und verliert im Trend - Effizienz steht")
    print("  bei %.2f." % z["er"])

    for i, kauf, ziel, kontrakte in zeilen:
        befehle(instr, "long", kontrakte, kauf, ziel, boden, hebel, nr=i)
    return 0


def befehle(instr, seite, kontrakte, einstieg, ziel, stop, hebel, nr=None):
    """Die fertigen Aufrufe. Sie werden ausgegeben, nicht ausgefuehrt."""
    kopf = "Befehl" if nr is None else "Befehl Stufe %d" % nr
    print()
    print("  --- %s (von Hand auszufuehren) ---" % kopf)
    print("  Hebel setzen:")
    print("    okxf.hebel_setzen(%r, %g, 'isolated')" % (instr["instId"], hebel))
    print("  Order mit Ziel und Stop in einem:")
    print("    okxf.order_limit(%r, %r, %g, %.6f, tp=%.6f, sl=%.6f)" % (
        instr["instId"], "buy" if seite == "long" else "sell",
        kontrakte, einstieg, ziel, stop))


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("befehl", choices=("lage", "trend", "grid"))
    p.add_argument("--wert", required=True, help="Basiswert, z.B. SOL oder RE")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = wachen()
    try:
        if a.befehl == "lage":
            zeige_lage(w, a.wert)
            return 0
        if a.befehl == "trend":
            return zeige_trend(w, a.wert)
        return zeige_grid(w, a.wert)
    except okxf.OKXFehler as e:
        print("OKX: %s" % e, file=sys.stderr)
        return 1
    finally:
        if a.befehl in ("trend", "grid"):
            print()
            print("=" * 66)
            print("Der Bot hat nichts ausgeloest. Keine Order, keine Signatur.")
            print("Die Ausnahme vom Handverbot in Wissen/Schutzregeln.md gilt")
            print("nur fuer Spot ohne Hebel - dieser Ordner faellt nicht darunter.")
            print("=" * 66)


if __name__ == "__main__":
    raise SystemExit(main())
