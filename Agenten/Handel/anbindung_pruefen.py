"""Anbindungs-Pruefung: kann jede freigegebene Spur ihre BOERSE wirklich?

Warum ein eigenes Werkzeug
--------------------------
`spuren_stand.py` sagt, ob eine Spur einen Order-Code HAT. Das ist eine
Aussage ueber die Datei. Hier wird die BOERSE gefragt - dieselben Wege,
die die Spur im Betrieb nutzt:

  * Schluessel vorhanden (sonst kein Orderweg)
  * Demo-Modus aus (ein Demo-Schluessel sieht aus wie ein live, ist aber
    keiner - genau dieser Fehlschluss hat den T-285-Roundtrip geprägt)
  * Guthaben in der QUOTE der Spur abrufbar (USDC und EURC sind auf dem
    EEA-Konto vorhanden, USDT ist es nicht)
  * der Kurs des Instruments kommt wirklich heraus

Was NICHT geprueft wird: es wird keine Order geschickt. Ein Werkzeug, das
Anbindung prueft und dabei handelt, ist kein Pruefwerkzeug.

Rausgabe: eine Zeile je Spur. ZEUGE ist immer die Börse selbst - kein
Name, keine Vermutung, sondern der gemessene Zustand mit Zeitstempel.
"""

import json
import os
import sys
from datetime import datetime

# Das Werkzeug liegt IN Agenten/Handel - eine Ebene darunter waere Agenten/,
# und dann laest os.path.join(HANDEL, spur, "wachen.json") ins Leere. Genau
# das ist am 03.10.2026 passiert: lade_wachen() bekam fuer jede Spur {} zurueck
# (es gibt kein Agenten/scanner/wachen.json), handel_erlaubt las sich als False,
# und der Lauf meldete 12 von 12 Spuren "bereit, aber gesperrt" - wo doch 10
# scharf sind. Siehe HANDEL = HIER, dieselbe Regel wie in jeder Spur.
HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = HIER
WURZEL = os.path.dirname(HANDEL)
if HANDEL not in sys.path:
    sys.path.append(HANDEL)
sys.path.append(os.path.join(HANDEL, "scanner"))

def instrument_der_spur(w, boerse):
    """Das Instrument DIESER Spur - nicht eine Vorgabe des Pruefers.

    Der erste Wurf fragte bei jeder Kraken-Spur nach "BTC-USDT-SWAP" und
    meldete fuenf Spuren als "kein Kurs". Das war der FEHLER DES PRUEFERS,
    nicht der Spuren: Kraken fuehrt BTC/EUR, die Futures-Marken heissen
    PF_XBTUSD. Eine Pruefung, die ihre eigene Voreinstellung fuer einen
    Befund haelt, ist schlimmer als keine - sie sieht gesunde Spuren kaputt
    und echte Ausfaelle alsnormal.
    """
    for feld in ("instrument", "paar", "symbol"):
        wert = w.get(feld)
        if wert:
            # "BTC/EUR" ist Kraken-Schreibweise, kein Instrument-Id
            if "/" in str(wert):
                return str(wert).replace("/", "-")
            return wert
    if boerse.startswith("kraken_futures"):
        return "PF_XBTUSD"
    if boerse == "kraken":
        return "XXBTZEUR"
    return "BTC-USDT-SWAP"


SPUREN = [
    ("scanner", "okx", "USDC"),
    ("xperp", "okx", "USDC"),
    ("mosaic", "okx", "USDC"),
    ("swap", "okx", "USDC"),
    ("moondev_signalwelle", "signalwelle", "USDC"),
    ("moondev_topmovers", "okx", "USDC"),
    ("moondev_listingarb", "okx", "USDC"),
    ("moondev_marktlage", "kraken", "EUR"),
    ("kraken", "kraken", "EUR"),
    ("nautilus_kraken", "kraken", "EUR"),
    ("omniquant", "kraken_futures", "USD"),
    ("omnitrade_futures", "kraken_futures", "USD"),
]


def lade_wachen(spur):
    try:
        with open(os.path.join(HANDEL, spur, "wachen.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def weg_fuer(boerse):
    """Der Adapter, den spur_buch.orderweg() liefern wuerde."""
    import spur_buch
    return spur_buch.orderweg({"boerse": boerse})


def pruefe(spur, boerse, quote):
    w = lade_wachen(spur)
    zustand = "%-6s" % ("an" if w.get("handel_erlaubt") else "-")
    r = {"spur": spur, "boerse": boerse, "quote": quote, "handel_erlaubt":
         bool(w.get("handel_erlaubt")), "weg": False, "schluessel": False,
         "demo": None, "guthaben": None, "kurs": None, "fehler": []}
    try:
        weg = weg_fuer(boerse)
    except Exception as e:                                   # noqa: BLE001
        r["fehler"].append("Weg nicht ladbar: %s" % str(e)[:80])
        return r
    if weg is None:
        r["fehler"].append("kein Orderweg fuer boerse=%s" % boerse)
        return r
    r["weg"] = True
    for name, fn in (("schluessel", "schluessel_vorhanden"),
                     ("demo", "demo_modus")):
        try:
            r[name] = getattr(weg, fn)()
        except Exception as e:                               # noqa: BLE001
            r["fehler"].append("%s: %s" % (fn, str(e)[:60]))
    try:
        r["guthaben"] = round(float(weg.guthaben_waehrung(quote)), 2)
    except Exception as e:                                   # noqa: BLE001
        r["fehler"].append("Guthaben %s: %s" % (quote, str(e)[:60]))
    inst = instrument_der_spur(w, boerse)
    try:
        k = weg.letzter_kurs(inst)
        r["kurs"] = ("%.6f" % float(k)) if k is not None else None
        if k is None:
            r["fehler"].append("kein Kurs fuer %s" % inst)
    except Exception as e:                                   # noqa: BLE001
        r["fehler"].append("Kurs %s: %s" % (inst, str(e)[:60]))
    return r


def main():
    print("Anbindungs-Pruefung %s - es wird NICHTS geordert"
          % datetime.now().strftime("%d.%m. %H:%M"))
    print("%-22s %-16s %-6s %5s %-8s %10s %-12s %s"
          % ("Spur", "Boerse", "Quote", "Weg", "Demo", "Guthaben", "Kurs",
             "Befund"))
    print("-" * 118)
    zeilen = []
    for spur, boerse, quote in SPUREN:
        r = pruefe(spur, boerse, quote)
        demoklar = "nein" if r["demo"] is False else ("JA" if r["demo"] else "?")
        mark = ""
        if r["demo"]:
            mark = "DEMO-MODUS"
        elif not r["schluessel"]:
            mark = "kein Schluessel"
        elif r["guthaben"] is None:
            mark = "Guthaben nicht lesbar"
        elif r["kurs"] is None:
            mark = "kein Kurs"
        else:
            mark = "bereit" if r["handel_erlaubt"] else "bereit, aber gesperrt"
        zeilen.append((r, mark))
        print("%-22s %-16s %-6s %5s %-8s %10s %-12s %s"
              % (spur, boerse, quote, "ja" if r["weg"] else "NEIN", demoklar,
                 ("%.2f" % r["guthaben"]) if r["guthaben"] is not None else "-",
                 r["kurs"] or "-", mark))
        for f in r["fehler"]:
            print("    ! " + f)
    print()
    ok = [r for r, m in zeilen if m.startswith("bereit")]
    gesperrt = [r for r, m in zeilen if m.startswith("bereit, aber")]
    kaputt = [(r, m) for r, m in zeilen if m in ("DEMO-MODUS", "kein Schluessel",
                                                  "Guthaben nicht lesbar",
                                                  "kein Kurs")
              or m == "NEIN"]
    print("bereit: %d | gesperrt: %d | beanstandet: %d"
          % (len(ok), len(gesperrt), len(kaputt)))
    for r, m in kaputt:
        print("  %-22s %s" % (r["spur"], m))
    return 0


if __name__ == "__main__":
    sys.exit(main())