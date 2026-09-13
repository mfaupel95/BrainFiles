"""Tiefe Historie fuer XPERP-Kontrakte, die zu jung fuer belastbare Zahlen sind.

Ein frisch gelisteter XPERP - CHIP-USD_UM_XPERP-310822 war am 01.09.2026
14 Tage alt - traegt die Kennzahlen nicht, die vor einer gehebelten Order
zaehlen: der groesste 7-Tage-Ruecklauf (aus dem der Hebel-Deckel faellt) und
die Trefferquote stehen auf zu wenigen Kerzen. Genau die Falle aus
Wissen/Handelsbots.md: "Kurze Fenster taeuschen zuverlaessig" - und beim
XPERP taeuscht das Fenster nach oben, weil der Kontrakt sein ganzes bisheriges
Leben auf einem lokalen Tief begonnen hat.

Der gleiche Basiswert wird als gewoehnlicher USDT-SWAP aber oft Monate laenger
gehandelt (CHIP-USDT-SWAP: seit 21.04.2026, rund 133 Tage). Dieses Modul zieht
diese Reihe und liefert sie an bot.pruefpflicht / bot.hebel_deckel weiter.

Die Trennung, die das rechtfertigt:

  - Das AKTUELLE Signal (SuperTrend, EMA, RSI, ATR jetzt) kommt weiter vom
    gehandelten Kontrakt. Es beschreibt den Kurs, den man wirklich kauft, und
    die Order liegt auf dem XPERP, nicht auf dem SWAP.
  - Die STATISTIK (Hebel-Deckel, Trefferquote, Vola p.a.) darf aus der tiefen
    Reihe kommen. Sie beschreibt das Verhalten des Basiswerts - und das ist
    bei XPERP und SWAP dasselbe: gleicher Index, ATR% deckungsgleich (CHIP am
    01.09.2026: 4,6 % XPERP gegen 4,4 % SWAP).

Kein Netzzugriff ausser ueber okxf. Nichts wird ausgeloest.

Aufruf:
    python historie.py CHIP                      # Vergleich jung <-> tief
    python historie.py CHIP --quelle CHIP-USDT-SWAP
    python historie.py RE   --quelle selbst      # kein Ersatz, nur der Kontrakt
"""

import argparse
import math
import statistics as st
import sys

import okxf

BAR = "4H"
PRO_TAG = 6


def swap_id(inst_id):
    """'RE-USD_UM_XPERP-310620' -> 'RE-USDT-SWAP'. Nur der Basiswert zaehlt."""
    basis = inst_id.split("-")[0].upper()
    return basis + "-USDT-SWAP"


def tiefe_reihe(inst_id, quelle=None, seiten=12):
    """Kerzenreihe fuer die Statistik.

    quelle:
        None / "auto"  -> <Basis>-USDT-SWAP. Faellt auf den Kontrakt selbst
                          zurueck, wenn es diese Reihe nicht gibt oder sie
                          nicht laenger ist als die eigene.
        "<instId>"     -> genau diese Reihe (z.B. "CHIP-USDT-SWAP").
        "selbst"       -> ausdruecklich der Kontrakt selbst, kein Ersatz.

    Rueckgabe: (kerzen, quelle_instId, ist_ersatz)
    """
    eigen = okxf.kerzen_lang(inst_id, BAR, seiten=seiten)

    if quelle == "selbst":
        return eigen, inst_id, False

    ziel = swap_id(inst_id) if quelle in (None, "auto") else quelle
    if ziel.upper() == inst_id.upper():
        return eigen, inst_id, False

    try:
        tief = okxf.kerzen_lang(ziel, BAR, seiten=seiten)
    except okxf.OKXFehler:
        return eigen, inst_id, False

    if len(tief) <= len(eigen):
        return eigen, inst_id, False
    return tief, ziel, True


# --- Vergleich (nur __main__) --------------------------------------------------

def _vola_pa(c):
    ren = [c[i] / c[i - 1] - 1 for i in range(1, len(c))]
    return st.pstdev(ren) * math.sqrt(PRO_TAG * 365) if len(ren) > 2 else 0.0


def _zeile(name, k, inst_id, bot, ind):
    c = [r[4] for r in k]
    a = ind.atr(k, 14)
    atr_pct = a[-1] / c[-1] * 100 if a[-1] else 0.0
    dl, ds = bot.hebel_deckel(inst_id, tage=7, wartung=0.005)
    tq_l = bot.trefferquote(k, 1.5, 3.0, "long")
    tq_s = bot.trefferquote(k, 1.5, 3.0, "short")
    noetig = bot.noetige_quote(3 * a[-1] / c[-1], 1.5 * a[-1] / c[-1],
                               2 * 0.0005) if a[-1] else None
    print("  %-16s %6.0f %8.0f%% %7.2f%% %8.1fx %7.1fx %9s %9s %9s" % (
        name, len(k) / PRO_TAG, _vola_pa(c) * 100, atr_pct, dl, ds,
        "%.0f%%" % (tq_l["quote"] * 100) if tq_l["quote"] else "n/a",
        "%.0f%%" % (tq_s["quote"] * 100) if tq_s["quote"] else "n/a",
        "%.0f%%" % (noetig * 100) if noetig else "n/a"))


def _main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wert", help="Basiswert oder voller instId, z.B. CHIP")
    p.add_argument("--quelle", default="auto",
                   help="'auto' (Standard), 'selbst' oder ein instId")
    p.add_argument("--seiten", type=int, default=12,
                   help="je 100 Kerzen rueckwaerts (Standard 12 = ~200 Tage)")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    instr = okxf.instrument(a.wert)
    iid = instr["instId"]
    jung = okxf.kerzen_lang(iid, BAR, seiten=a.seiten)
    tief, quelle, ersatz = tiefe_reihe(iid, a.quelle, a.seiten)

    print()
    print("=" * 92)
    print("%s   (%s)" % (a.wert.upper(), iid))
    print("=" * 92)
    print("  Kontrakt gelistet:  %s Kerzen a %s  = %.1f Tage" % (
        len(jung), BAR, len(jung) / PRO_TAG))
    if ersatz:
        print("  Tiefe Reihe:        %s  -> %s Kerzen = %.1f Tage" % (
            quelle, len(tief), len(tief) / PRO_TAG))
    else:
        print("  Tiefe Reihe:        keine laengere gefunden - es bleibt beim Kontrakt")
    print()

    try:
        import bot
        import indikatoren
    except Exception as e:            # noqa: BLE001 - bot.py evtl. gerade in Arbeit
        print("  (bot.py nicht importierbar: %s)" % e)
        print("  Reihen stehen bereit, der Vergleich braucht aber bot.py.")
        return 0

    print("  %-16s %6s %9s %8s %9s %8s %9s %9s %9s" % (
        "Reihe", "Tage", "Vola pa", "ATR%", "Deckel L", "Deckel S",
        "Treff L", "Treff S", "noetig"))
    _zeile("Kontrakt jung", jung, iid, bot, indikatoren)
    if ersatz:
        _zeile("tief (" + quelle.split("-")[0] + " SWAP)", tief, quelle, bot, indikatoren)
        print()
        print("  Die tiefe Reihe ist die belastbare. Weicht 'Treff' unter 'noetig'")
        print("  oder 'Deckel' unter den max_hebel aus wachen.json, ist der Anlauf")
        print("  auf der einzig langen Historie negativ - Wissen/Handelsbots.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
