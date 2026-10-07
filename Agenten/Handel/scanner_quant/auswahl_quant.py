"""XPERP-Rangliste mit Quant-Urteil - KOPIE von xperp/auswahl.py, die Altspur bleibt unberuehrt.

Gleiche Kennzahlen, Tore und Ranglisten wie xperp/auswahl.py; dazu je Wert
das Urteil aus quant.py fuer BEIDE Richtungen (aus den Tageskerzen, die
sammle() fuer den Hebel-Deckel ohnehin holt - kein zusaetzlicher Abruf):
    Q    quant_score der Richtung der Liste (long/short), 0..100
    !qd  Dehnung ueber dem Tor (Spitze in dieser Richtung; Score gedeckelt)
Die Reihenfolge der Listen bleibt die des Originals, ausser mit --rang quant.
okxf.py wird aus ../xperp GELESEN, nicht kopiert.

Das ist NUR die Auswahl. xperp/handeln.py (Live-Pfad) und bot.py sind nicht
kopiert und nicht verdrahtet - die Rangliste ist ein Vorschlag, keine
Anweisung.

Aufruf:
    python auswahl_quant.py                    # drei Ranglisten + Q-Spalte
    python auswahl_quant.py --zweck short --rang quant
    python auswahl_quant.py --wert RE          # ein Wert im Detail
"""

import argparse
import math
import os
import statistics as st
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
ALT = os.path.join(HIER, os.pardir, "xperp")      # Original: nur lesen
# ANHAENGEN, nicht vorn: der eigene Ordner bleibt sys.path[0].
if ALT not in sys.path:
    sys.path.append(ALT)
import okxf                                                 # noqa: E402
import quant                                                # noqa: E402

# Lange Linie fuer das Urteil. Spot nimmt 200 Tage; bei XPERP hat KEIN
# Kontrakt so viel Historie (07.10.2026: 0 von 181, laengster unter 210 Tage),
# mit 200 bliebe die ganze Spalte leer. 100 Tage erreichen rund 40 Kontrakte.
LANG = 100

# --- Modellannahmen ---------------------------------------------------------
# Sie gehoeren angepasst, wenn sich Gebuehren oder Wartungsmarge aendern.

WARTUNGSMARGE = 0.005      # Anteil des Positionswerts, der stehen bleiben muss
GEBUEHR_TAKER = 0.0005     # je Ausfuehrung
GEBUEHR_MAKER = 0.0002
BAR = "4H"                 # 300 Kerzen = rund 50 Tage
PRO_TAG = 6                # 4H-Kerzen je Tag

# 21 Tage Mindesthistorie, 42 Tage bis die Warnung faellt. Der Grund steht in
# Wissen/Handelsbots.md: "Einen Bot nie ueber weniger als ein Jahr bewerten."
# Ein Jahr gibt es bei XPERP nicht - die aeltesten Kontrakte laufen seit Mai
# 2026. Also wenigstens genug Kerzen, dass die 14-Tage-Kennzahl ueberhaupt
# existiert. Am 01.09.2026 standen DASH und POL mit 8,3 Tagen Historie weit
# oben in der Grid-Liste, weil ihre fehlende 14-Tage-Rendite als "+0.0%"
# gedruckt wurde und wie perfekte Seitwaertsbewegung aussah.
MIN_KERZEN = 21 * PRO_TAG
JUNG_KERZEN = 42 * PRO_TAG

# Tor aus scanner/wachen.json - dort 1.20 fuer Spot ohne Hebel. Fuer gehebelte
# Kontrakte ist es keine Frage der Vorliebe: Die Vola bestimmt direkt, wieviel
# Hebel ueberhaupt ueberlebt (siehe hebel_deckel).
VOLA_TOR = 1.20

# --- Die drei Familien ------------------------------------------------------
# Ein Tor, das fuer Krypto gemessen wurde, misst bei einer Aktie das Falsche.
# Gemessen am 03.09.2026 gegen die OKX-Ticker:
#
#   Umsatz 24h   Krypto bis 25 Mio (XRP), Aktien 0,3-2,8 Mio (Spitze SPCX),
#                Rohstoffe 1,5-10,7 Mio (XAU).
#   Spread       Krypto breit, Aktien eng: SPY 0,001 %, MSTR 0,036 %,
#                NVDA 0,066 % - trotz kleinerem Umsatz.
#
# Deshalb faellt der Umsatz-Bezug bei Aktien auf 1 Mio. Das ist keine
# Aufweichung: Bei 50 USD Margin und 5x Hebel steht eine Position von 250 USD
# gegen 1 Mio Tagesumsatz - 0,025 %. Der Umsatz war nie das Risiko, der Spread
# ist es, und der ist hier ein Zehntel des Krypto-Werts.
#
# vola_tor liegt bei Aktien niedriger, weil eine Aktie mit 120 % Jahresvola
# nicht ruhig ist wie ein Coin mit 120 %, sondern ein Einzelfall (Uebernahme,
# Zahlen, Squeeze). Rohstoffe schwanken am wenigsten und bekommen das engste
# Tor.
KATEGORIEN = {
    "krypto":   {"code": okxf.KRYPTO,   "umsatz_bezug": 3_000_000,
                 "vola_tor": 1.20, "kuerzel": "K"},
    "aktie":    {"code": okxf.AKTIE,    "umsatz_bezug": 1_000_000,
                 "vola_tor": 0.90, "kuerzel": "A"},
    "rohstoff": {"code": okxf.ROHSTOFF, "umsatz_bezug": 1_000_000,
                 "vola_tor": 0.60, "kuerzel": "R"},
}

# Kerzen, deren True Range unter diesem Anteil des Medians liegt, gelten als
# Ruhekerzen und zaehlen weder in die ATR noch in die Vola.
#
# Der Grund, gemessen am 03.09.2026 ueber 500 Stundenkerzen: Aktien-XPERP
# laufen 24/7, ihr Basiswert nicht. NVDA bewegt sich Mo-Fr 0,45 % je Stunde,
# Sa-So 0,07 % - Faktor 0,16. SPY 0,23, Gold 0,21. 144 von 500 Stunden sind
# damit Stillstand, der in eine ungefilterte ATR einfliesst und den Stop zu
# eng macht; Montag frueh greift er dann ohne Marktbewegung. Genau der Fehler,
# den Wissen/XPERP-Handel.md fuer Prozent-Stops beschreibt, eine Ebene tiefer.
#
# Warum kein Kalender: Ein Filter am Median deckt US-Boersenfeiertage mit ab,
# ohne dass jemand eine Feiertagsliste pflegt - und er regelt sich selbst.
# Gemessen an 4H-Kerzen: SOL 0 % gefiltert (Faktor 1,00), BTC 4 % (1,04),
# CL 6 % (1,05), MSTR 8 % (1,08), SPY 13 % (1,15), NVDA 14 % (1,14),
# XAU 16 % (1,17). Bei echtem 24/7 tut er nichts, genau wie beabsichtigt.
RUHE_ANTEIL = 0.25


def kennzahlen(k):
    """Alle Kennzahlen eines Werts aus seinen Kerzen."""
    c = [r[4] for r in k]
    n = len(c)
    kurs = c[-1]

    ren = [c[i] / c[i - 1] - 1 for i in range(1, n)]

    # True Range je Kerze - Grundlage fuer ATR und fuer den Ruhefilter.
    tr = [max(k[i][2] - k[i][3],
              abs(k[i][2] - k[i - 1][4]),
              abs(k[i][3] - k[i - 1][4])) for i in range(1, n)]

    # Ruhekerzen raus (siehe RUHE_ANTEIL oben). Die Indizes gelten fuer tr und
    # ren gleichermassen, beide beginnen bei Kerze 1.
    schwelle = st.median(tr) * RUHE_ANTEIL if tr else 0.0
    aktiv = [i for i, t in enumerate(tr) if t >= schwelle]
    ruhe_anteil = 1 - len(aktiv) / len(tr) if tr else 0.0

    tr_a = [tr[i] for i in aktiv]
    ren_a = [ren[i] for i in aktiv]

    # Vola aus den aktiven Kerzen, annualisiert mit der Zahl der Kerzen, die
    # es im Jahr tatsaechlich gibt. Wer ueber alle 6x365 annualisiert, obwohl
    # ein Fuenftel davon Stillstand ist, meldet eine Aktie zu ruhig.
    aktive_pro_jahr = PRO_TAG * 365 * (len(aktiv) / len(tr)) if tr else 0
    vola = (st.stdev(ren_a) * math.sqrt(aktive_pro_jahr)
            if len(ren_a) > 2 else 0.0)

    # ATR(14) in Prozent - der Massstab fuer jeden Stop-Abstand
    atr = st.mean(tr_a[-14:]) / kurs if len(tr_a) >= 14 else 0.0

    def rendite(tage):
        b = tage * PRO_TAG
        return (c[-1] / c[-1 - b] - 1) if n > b else None

    # Kaufman Efficiency Ratio ueber 7 Tage: Nettobewegung geteilt durch
    # zurueckgelegten Weg. Nahe 1 = sauberer Trend, nahe 0 = Gezappel.
    f = c[-min(42, n - 1):]
    weg = sum(abs(f[i] - f[i - 1]) for i in range(1, len(f)))
    netto = abs(f[-1] - f[0])
    er = netto / weg if weg > 0 else 0.0
    weg_pct = weg / kurs                     # Weg in Prozent des Kurses

    # SMA-Ausrichtung
    def sma(tage):
        b = tage * PRO_TAG
        return st.mean(c[-b:]) if n >= b else None
    ueber = sum(1 for t in (3, 7, 14, 30)
                if sma(t) is not None and kurs > sma(t))
    von = sum(1 for t in (3, 7, 14, 30) if sma(t) is not None)

    # Groesster Ruecklauf gegen eine Long- bzw. Short-Position ueber 7 Tage.
    # Daraus faellt der Hebel, der ueberhaupt ueberlebt haette.
    hd = min(42, n - 1)
    mae_long = mae_short = 0.0
    for i in range(n - hd):
        e = c[i]
        tief = min(r[3] for r in k[i + 1:i + 1 + hd])
        hoch = max(r[2] for r in k[i + 1:i + 1 + hd])
        mae_long = max(mae_long, 1 - tief / e)
        mae_short = max(mae_short, hoch / e - 1)

    spanne = (max(r[2] for r in k[-hd:]) / min(r[3] for r in k[-hd:]) - 1)

    return {
        "kurs": kurs, "kerzen": n, "vola": vola, "atr": atr,
        "r7": rendite(7), "r14": rendite(14), "r30": rendite(30),
        "er": er, "weg": weg_pct, "ueber_sma": ueber, "von_sma": von,
        "mae_long": mae_long, "mae_short": mae_short, "spanne": spanne,
        "ruhe": ruhe_anteil,
    }


def mae_tage(kt, tage=7):
    """Groesster Ruecklauf gegen Long bzw. Short ueber N Tage, aus Tageskerzen.

    Getrennt von kennzahlen(), weil diese Groesse eine andere Reihe braucht:
    Sie darf nicht davon abhaengen, wie weit das 4H-Fenster zurueckreicht.
    """
    mae_l = mae_s = 0.0
    for i in range(len(kt) - tage):
        e = kt[i][4]
        if e <= 0:
            continue
        mae_l = max(mae_l, 1 - min(r[3] for r in kt[i + 1:i + 1 + tage]) / e)
        mae_s = max(mae_s, max(r[2] for r in kt[i + 1:i + 1 + tage]) / e - 1)
    return mae_l, mae_s


def hebel_deckel(mae):
    """Groesster Hebel, der den beobachteten Ruecklauf ueberlebt haette.

    Liquidation greift rund bei 1/hebel minus Wartungsmarge. Wer mehr Hebel
    nimmt, als hier steht, waere im Beobachtungsfenster mindestens einmal
    ausgestoppt worden - nicht als Prognose, sondern als Rueckblick.
    """
    if mae <= 0:
        return 20.0
    return max(1.0, min(20.0, 1.0 / (mae + WARTUNGSMARGE)))


def bewerte(z, umsatz, bezug=3_000_000):
    """Drei Eignungen, je 0..100. Getrennt, weil sie sich widersprechen."""
    # Bezugsgroesse 3 Mio USD am Tag fuer Krypto: gemessen am 01.09.2026
    # erreicht das im XPERP-Universum ausser BTC/ETH kaum ein Wert. Das
    # Universum ist duenn - das ist ein Befund, kein Massstabsfehler. Fuer
    # Aktien und Rohstoffe steht der Bezug bei 1 Mio, begruendet in
    # KATEGORIEN oben.
    liquide = min(1.0, umsatz / bezug) if umsatz else 0.0
    ruhig = max(0.0, 1.0 - z["vola"] / 2.0)

    # Long: Trend nach oben, SMA-Ausrichtung, nicht zu wild
    auf = sum(x for x in (z["r7"], z["r14"]) if x is not None)
    lo = (max(0.0, min(1.0, auf * 3)) * 0.40
          + (z["ueber_sma"] / z["von_sma"] if z["von_sma"] else 0) * 0.25
          + ruhig * 0.20 + liquide * 0.15)

    # Short: Trend nach unten. Positives Funding ist ein Zuschuss, kein Grund.
    ab = -auf
    sh = (max(0.0, min(1.0, ab * 3)) * 0.40
          + (1 - (z["ueber_sma"] / z["von_sma"] if z["von_sma"] else 0)) * 0.25
          + ruhig * 0.20 + liquide * 0.15)

    # Grid: viel Weg bei wenig Richtung. Der Weg muss die Gebuehren tragen,
    # deshalb zaehlt er absolut mit und nicht nur das Verhaeltnis.
    gr = (min(1.0, z["weg"] / 0.60) * 0.35
          + (1 - z["er"]) * 0.35
          + liquide * 0.20 + ruhig * 0.10)

    return {"long": lo * 100, "short": sh * 100, "grid": gr * 100}


def sammle(werte=None, still=False, kategorien=None):
    """Kennzahlen aller Kontrakte der genannten Familien.

    kategorien: Liste von Schluesseln aus KATEGORIEN. None = alle drei.
    """
    if kategorien is None:
        kategorien = list(KATEGORIEN)

    instr, familie = {}, {}
    for name in kategorien:
        kat = KATEGORIEN[name]
        for x in okxf.instrumente(kat["code"]):
            basis = x["instId"].split("-")[0]
            instr[basis] = x
            familie[basis] = name

    if werte:
        instr = {k: v for k, v in instr.items() if k in werte}
    tick = okxf.tickers()

    ergebnis = []
    for i, (basis, x) in enumerate(sorted(instr.items()), 1):
        iid = x["instId"]
        if not still:
            print("  %3d/%d %-10s" % (i, len(instr), basis), end="\r",
                  file=sys.stderr)
        try:
            k = okxf.kerzen(iid, BAR, 300)
        except Exception:                       # noqa: BLE001
            continue
        if len(k) < MIN_KERZEN:
            continue
        z = kennzahlen(k)

        # Der Hebel-Deckel kommt aus TAGESKERZEN, nicht aus den 4H-Kerzen
        # oben. 300 4H-Kerzen sind nur 50 Tage; 300 Tageskerzen sind 300.
        # Gemessen am 01.09.2026 an SOL: ueber 50 Tage sieht der groesste
        # 7-Tage-Ruecklauf nach 9,5 % aus (Deckel 10x), ueber 200 Tage sind
        # es 27,9 % (Deckel 3,5x) - der Einbruch vom 31.05.2026 lag ausserhalb
        # des kurzen Fensters. Handelsregeln, Spur 2 machen diesen Wert zur
        # festen Grenze; er darf nicht vom Fensterrand abhaengen.
        kt = []
        try:
            kt = okxf.kerzen(iid, "1D", 300)
            if len(kt) >= 14:
                z["mae_long"], z["mae_short"] = mae_tage(kt, 7)
                z["tage_gemessen"] = len(kt)
            time.sleep(0.06)
        except Exception:                       # noqa: BLE001
            z["tage_gemessen"] = len(k) / PRO_TAG

        # Quant-Urteil aus denselben Tageskerzen; None = unter LANG+10 Tage.
        z["quant"] = {"long": quant.urteil(kt, richtung="long", lang=LANG),
                      "short": quant.urteil(kt, richtung="short", lang=LANG)}

        t = tick.get(iid, {})
        # volCcy24h ist bereits Basiswaehrung (Kontrakte x ctVal). Wer hier
        # nochmal mit ctVal multipliziert, meldet BONK mit 167 Billionen
        # Umsatz - passiert am 01.09.2026 im ersten Wurf.
        umsatz = float(t.get("volCcy24h") or 0) * z["kurs"]
        kat = KATEGORIEN[familie.get(basis, "krypto")]
        z.update(basis=basis, instId=iid, umsatz=umsatz,
                 kategorie=familie.get(basis, "krypto"),
                 vola_tor=kat["vola_tor"],
                 max_lever=float(x["lever"]),
                 punkte=bewerte(z, umsatz, kat["umsatz_bezug"]))
        ergebnis.append(z)
        time.sleep(0.06)                        # OKX: 40 Anfragen je 2 s
    if not still:
        print(" " * 30, end="\r", file=sys.stderr)
    return ergebnis


def _q_spalte(z, zweck):
    """(Spalte, Warnung) fuer die Listen; Grid hat kein Richtungsurteil."""
    if zweck == "grid":
        return "", ""
    q = z["quant"][zweck]
    if q is None:
        return "    - ", ""
    return " %5.1f" % q["quant_score"], (" !qd" if q["zu_gedehnt"] else "")


def tabelle(daten, zweck, n=12, rang="punkte"):
    ueber = {"long": "LONG - Aufwaertstrend",
             "short": "SHORT - Abwaertstrend",
             "grid": "GRID - viel Weg, wenig Richtung"}[zweck]
    print()
    print("=" * 100)
    print(ueber)
    print("=" * 100)
    print("%-9s %1s %8s %7s %7s %6s %5s %5s %5s %6s %7s  %s" % (
        "Wert", "", "Kurs", "7T", "14T", "Vola", "ATR%", "Weg%", "ER", "Hebel",
        "Umsatz", "Punkte") + ("   Q" if zweck != "grid" else ""))

    mae = "mae_short" if zweck == "short" else "mae_long"
    def schluessel(d):
        if rang == "quant" and zweck != "grid":
            q = d["quant"][zweck]
            return -(q["quant_score"] if q else -1.0)    # ohne Urteil ans Ende
        return -d["punkte"][zweck]

    for z in sorted(daten, key=schluessel)[:n]:
        deckel = hebel_deckel(z[mae])
        warn = ""
        if z["vola"] > z.get("vola_tor", VOLA_TOR):
            warn += " !vola"
        # Ueber 30 % Ruhekerzen heisst: der Kontrakt laeuft 24/7, sein
        # Basiswert nicht. Ein Stop steht dann ueber Nacht und ueber das
        # Wochenende in einem Buch, das den Gap am Montag nicht auffaengt.
        if z.get("ruhe", 0) > 0.30:
            warn += " !ruht(%.0f%%)" % (z["ruhe"] * 100)
        if deckel < 5:
            warn += " !hebel<5"
        if z["kerzen"] < JUNG_KERZEN:
            warn += " !jung(%dT)" % (z["kerzen"] // PRO_TAG)
        # Fehlende Kennzahlen als n/a, nicht als 0 - eine fehlende
        # 14-Tage-Rendite sieht als "+0.0%" wie Seitwaertsbewegung aus.
        def pz(v):
            return "%+6.1f%%" % (v * 100) if v is not None else "   n/a"
        print("%-9s %1s %8.4f %s %s %5.0f%% %5.2f %5.0f %5.2f %5.1fx %6.1fM  %5.1f%s" % (
            z["basis"],
            KATEGORIEN[z.get("kategorie", "krypto")]["kuerzel"],
            z["kurs"], pz(z["r7"]), pz(z["r14"]),
            z["vola"] * 100, z["atr"] * 100, z["weg"] * 100, z["er"],
            deckel, z["umsatz"] / 1e6, z["punkte"][zweck],
            _q_spalte(z, zweck)[0] + warn + _q_spalte(z, zweck)[1]))


def detail(z):
    print()
    print("=" * 70)
    print("%s   (%s)" % (z["basis"], z["instId"]))
    print("=" * 70)
    print("  Kurs            %.6f      Kerzen %d x %s" % (z["kurs"], z["kerzen"], BAR))
    print("  Rendite          7T %+.1f%%   14T %+.1f%%   30T %s" % (
        (z["r7"] or 0) * 100, (z["r14"] or 0) * 100,
        "%+.1f%%" % (z["r30"] * 100) if z["r30"] is not None else "n/a"))
    print("  ueber SMA        %d von %d (3/7/14/30 Tage)" % (z["ueber_sma"], z["von_sma"]))
    tor = z.get("vola_tor", VOLA_TOR)
    print("  Familie         %s" % z.get("kategorie", "krypto"))
    for r in ("long", "short"):
        q = z["quant"][r]
        if q is None:
            print("  Quant %-5s     kein Urteil (unter %d Tageskerzen)" % (
                r, LANG + quant.LUFT))
        else:
            print("  Quant %-5s     %5.1f  Ordnung %d/4  Guete %.2f  Dehnung %+.1f ATR%s" % (
                r, q["quant_score"], q["ordnung"], q["effizienz30"],
                q["dehnung_atr"], "  !gedehnt" if q["zu_gedehnt"] else ""))
    print("  Vola p.a.       %5.0f%%   %s von %.0f%%" % (
        z["vola"] * 100, "UEBER dem Tor" if z["vola"] > tor else "unter dem Tor",
        tor * 100))
    if z.get("ruhe", 0) > 0.02:
        print("  Ruhekerzen      %5.0f%% - aus ATR und Vola herausgerechnet" % (
            z["ruhe"] * 100))
    print("  ATR(14)         %5.2f%% vom Kurs" % (z["atr"] * 100))
    print("  7T-Spanne       %5.1f%%" % (z["spanne"] * 100))
    print("  Weg / ER        %5.1f%% Weg bei ER %.2f  (%s)" % (
        z["weg"] * 100, z["er"],
        "eher Gezappel" if z["er"] < 0.3 else
        "gemischt" if z["er"] < 0.6 else "eher Trend"))
    print("  Umsatz 24h      %5.1f Mio USD" % (z["umsatz"] / 1e6))
    print()
    print("  Groesster Ruecklauf ueber 7 Tage und der Hebel, der ihn ueberlebt:")
    print("    gegen Long   %5.1f%%  ->  hoechstens %4.1fx" % (
        z["mae_long"] * 100, hebel_deckel(z["mae_long"])))
    print("    gegen Short  %5.1f%%  ->  hoechstens %4.1fx" % (
        z["mae_short"] * 100, hebel_deckel(z["mae_short"])))
    print()
    print("  Punkte: Long %.0f   Short %.0f   Grid %.0f" % (
        z["punkte"]["long"], z["punkte"]["short"], z["punkte"]["grid"]))

    # Was ein Grid hier kosten wuerde
    stufe = z["atr"]
    zyklus = 2 * GEBUEHR_MAKER
    print()
    print("  Grid-Probe: eine Stufe von 1 ATR = %.2f%%, ein Zyklus kostet %.2f%%" % (
        stufe * 100, zyklus * 100))
    if stufe > zyklus * 3:
        print("    -> Stufengewinn traegt die Gebuehr (%.1fx)" % (stufe / zyklus))
    else:
        print("    -> ZU ENG: Gebuehr frisst den Stufengewinn")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--zweck", choices=("long", "short", "grid", "alle"),
                   default="alle")
    p.add_argument("--wert", help="ein Basiswert im Detail, z.B. RE")
    p.add_argument("--anzahl", type=int, default=12)
    p.add_argument("--rang", choices=("punkte", "quant"), default="punkte",
                   help="Reihenfolge der Long-/Short-Listen (Standard wie Original)")
    p.add_argument("--kategorie", choices=tuple(KATEGORIEN) + ("alle",),
                   default="alle",
                   help="krypto (115 Werte), aktie (45), rohstoff (4)")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    kats = None if a.kategorie == "alle" else [a.kategorie]

    if a.wert:
        d = sammle([a.wert.upper()], kategorien=kats)
        if not d:
            print("kein XPERP-Kontrakt zu %r (oder zu wenig Historie)" % a.wert)
            return 1
        detail(d[0])
        return 0

    print("Scanne XPERP (%s) ueber %s-Kerzen ..." % (
        ", ".join(kats or KATEGORIEN), BAR), file=sys.stderr)
    d = sammle(kategorien=kats)
    print("%d Werte bewertet, %s" % (len(d), time.strftime("%Y-%m-%d %H:%M")))
    for zweck in (("long", "short", "grid") if a.zweck == "alle" else (a.zweck,)):
        tabelle(d, zweck, a.anzahl, a.rang)
    print()
    print("K/A/R    = Krypto / Aktie / Rohstoff. Eigene Tore je Familie:")
    for name, kat in KATEGORIEN.items():
        print("           %-9s Vola-Tor %3.0f%%, Umsatz-Bezug %.1f Mio" % (
            name, kat["vola_tor"] * 100, kat["umsatz_bezug"] / 1e6))
    print("Q        = quant_score der Richtung (scanner_quant/quant.py); "
          "'-' = unter %d Tage Historie" % (LANG + quant.LUFT))
    print("!qd      = Dehnung ueber 6 ATR in dieser Richtung, Score auf 50 gedeckelt")
    print("!vola    = ueber dem Tor seiner Familie")
    print("!ruht    = ueber 30% Ruhekerzen: laeuft 24/7, der Basiswert nicht.")
    print("           ATR und Vola sind um diese Kerzen bereinigt; das Gap-Risiko")
    print("           zum Wochenstart bleibt und gehoert in die Positionsgroesse.")
    print("!hebel<5 = 5x haette den groessten Ruecklauf der letzten 7 Tage nicht ueberlebt")
    print("!jung    = unter %d Tagen Historie; die Kennzahlen tragen noch nicht." % (
        JUNG_KERZEN // PRO_TAG))
    print("ER       = Nettobewegung / zurueckgelegter Weg. Niedrig = Gezappel = Grid-Futter.")
    print("Hebel    = Deckel aus dem groessten Ruecklauf der letzten 7 Tage,")
    print("           Rueckblick und keine Zusage fuer die naechsten 7.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
