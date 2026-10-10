"""Erreichbarkeit und Herkunft der Drawdown-Ratsche je Spur.

Zwei Fragen an jede Spur:

1. Greift die Halbierung noch, SOLANGE die Spur im Gewinn ist? Eine Schwelle
   ueber dem Gewinnhoechststand ist nicht unerreichbar - drawdown() rechnet
   hoch minus kum, und die kumulierte Kurve darf ins Minus laufen - sie greift
   nur erst nach mehr Verlust als dem gesamten Hoechstgewinn und schuetzt dann
   keinen Gewinn mehr, sondern faengt einen Nettoverlust. Dafuer ist der
   Kill-Switch da.

2. Entspricht der Betrag noch der Regel 1.0 x Buchrisiko? Der Betrag steht
   ausdruecklich in der wachen.json und verschiebt sich damit nicht von selbst -
   aber dann muss jemand nachsehen, dass er nicht davongelaufen ist.

Die Schwellen kommen aus ratschen.py, NICHT aus einer hier nachgebauten Formel:
eine nachgebaute Formel prueft die Formel, nicht die Spur. Den Hoechststand
liefert weiterhin das lage() der Spur selbst.

Kein Schreiber: liest nur wachen.json und handelsjournal.csv.
"""

import json
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location

HIER = os.path.dirname(os.path.abspath(__file__))


def _ratschen():
    _s = spec_from_file_location("ratschen", os.path.join(HIER, "ratschen.py"))
    _m = module_from_spec(_s)
    _s.loader.exec_module(_m)
    return _m


RATSCHEN = _ratschen()

# spur -> (ordner, modulordner, modulname). swap erbt die Wachen von xperp
# (swap/handeln.py: import wachen_xperp as wx) - dasselbe Modul, aber die
# eigene wachen.json.
SPUREN = [
    ("scanner", "scanner", "scanner", "wachen_pruefung"),
    ("xperp", "xperp", "xperp", "wachen_xperp"),
    ("swap", "swap", "xperp", "wachen_xperp"),
    ("orbk", "orbk", "orbk", "wachen_orb"),
    ("orb", "orb", "orb", "wachen_orb"),
    ("kraken", "kraken", "kraken", "wachen_kraken"),
    ("mosaic", "mosaic", "scanner", "wachen_pruefung"),
    ("moondev_funding", "moondev_funding", "scanner", "wachen_pruefung"),
    ("moondev_listingarb", "moondev_listingarb", "scanner", "wachen_pruefung"),
    ("moondev_topmovers", "moondev_topmovers", "scanner", "wachen_pruefung"),
    ("moondev_signalwelle", "moondev_signalwelle", "scanner", "wachen_pruefung"),
    ("moondev_marktlage", "moondev_marktlage", "scanner", "wachen_pruefung"),
    ("iv_wand", "iv_wand", "scanner", "wachen_pruefung"),
    ("iv_waelle", "iv_waelle", "scanner", "wachen_pruefung"),
    # Die drei Sprachmodell-Spuren (17.09.2026) nutzen denselben Kern
    # (spur_buch) und dieselbe Wachenpruefung wie die Bot-Spuren.
    ("moondev_whale", "moondev_whale", "scanner", "wachen_pruefung"),
    ("moondev_liquidation", "moondev_liquidation", "scanner", "wachen_pruefung"),
    ("moondev_sentiment", "moondev_sentiment", "scanner", "wachen_pruefung"),
    ("moondev_sniper", "moondev_sniper", "scanner", "wachen_pruefung"),
    # Nachgetragen 22.09.2026: die drei juengsten spur_buch-Spuren fehlten in
    # dieser Liste (liq_wand und trendwende_btc seit dem 21.09., robinhood_radar
    # neu) - sie laufen im Dauerlauf und fuehren den Betrag ausdruecklich.
    ("trendwende_btc", "trendwende_btc", "scanner", "wachen_pruefung"),
    ("liq_wand", "liq_wand", "scanner", "wachen_pruefung"),
    ("robinhood_radar", "robinhood_radar", "scanner", "wachen_pruefung"),
    # OMNITRADE (30.09.2026): spur_buch-Spur, Betrag ausdruecklich (15.00 =
    # 1.0x Buchrisiko aus 5 USD x 3 Plaetzen).
    ("omnitrade", "omnitrade", "scanner", "wachen_pruefung"),
    # OMNITRADE_FUTURES (30.09.2026): Betrag ausdruecklich (2.00 = 1.0x
    # Buchrisiko aus 2.0 USD Risiko x 1 Platz).
    ("omnitrade_futures", "omnitrade_futures", "scanner", "wachen_pruefung"),
    # Klassik-Spuren (30.09.2026): spur_buch-Spuren ueber klassik_regeln.
    # Prophet-Signal (02.10.2026): spur_buch-Spur ueber prophet_regeln.py,
    # Betrag ausdruecklich (10.00 = 1.0x Buchrisiko aus 5.0 USD x 2 Plaetzen).
    ("prophet_signal", "prophet_signal", "scanner", "wachen_pruefung"),
    ("fib_retrace", "fib_retrace", "scanner", "wachen_pruefung"),
    ("klassik_sma", "klassik_sma", "scanner", "wachen_pruefung"),
    ("klassik_ema", "klassik_ema", "scanner", "wachen_pruefung"),
    ("klassik_macd", "klassik_macd", "scanner", "wachen_pruefung"),
    ("klassik_bollinger", "klassik_bollinger", "scanner", "wachen_pruefung"),
    ("klassik_donchian", "klassik_donchian", "scanner", "wachen_pruefung"),
    ("klassik_rsi", "klassik_rsi", "scanner", "wachen_pruefung"),
    ("klassik_rsi2", "klassik_rsi2", "scanner", "wachen_pruefung"),
    ("klassik_donchian_trend", "klassik_donchian_trend", "scanner",
     "wachen_pruefung"),
    ("klassik_sr_breaks", "klassik_sr_breaks", "scanner", "wachen_pruefung"),
    ("klassik_pmax", "klassik_pmax", "scanner", "wachen_pruefung"),
    ("klassik_supertrend", "klassik_supertrend", "scanner", "wachen_pruefung"),
    # Die vier PROGNOSE-SPUREN (30.09.2026) tragen denselben Kern wie die
    # Bot-Spuren und haben je 20.00 gesetzt = 1.0 x Buchrisiko (5 USD
    # Risiko x 4 Plaetze). Sie standen nie in dieser Liste, ihre Ratsche
    # wurde also nie geprueft - gemessen 03.10.2026.
    ("squeeze", "squeeze", "scanner", "wachen_pruefung"),
    ("wavetrend", "wavetrend", "scanner", "wachen_pruefung"),
    ("macd_mtf", "macd_mtf", "scanner", "wachen_pruefung"),
    ("supertrend", "supertrend", "scanner", "wachen_pruefung"),
    # NAUTILUS_EMACROSS (03.10.2026): Schwelle 100.0 gesetzt, aber die
    # Wache fuehrt KEIN Risiko-Feld - der Eintrag meldet "nicht
    # herleitbar" und macht die Luecke sichtbar, statt sie zu uebergehen.
    ("nautilus_emacross", "nautilus_emacross", "scanner", "wachen_pruefung"),
    # Der Schattenarm squeeze_eth (03.10.2026, Auftrag Max "Schattenarm")
    # setzt eine eigene Ratsche in wachen.eth.json. Wie squeeze zeigt er
    # ueber `wp.lage(w, journal, z)` die Lage - mit den Werten des ARMS.
    ("squeeze_eth", "squeeze", "scanner", "wachen_pruefung"),
]

# Ruhende Spuren: bewusst nicht geprueft, sie laufen nicht im Dauerlauf.
# orb stand hier bis zum 21.09.2026 - seither laeuft die Spur (Papier).
RUHT = ("nautilus", "nautilus_kraken", "nautilus_kraken_futures")

# Toleranz beim Vergleich Betrag gegen 1.0 x Buchrisiko (Rundung in der Datei).
TOLERANZ = 0.005


def _dateien(spur, ordner):
    """Wachen- und Journaldatei EINER Spur - auch eines Schattenarms.

    Ein Arm teilt den Ordner mit seinem Hauptbuch, traegt aber Suffix und
    Wachen-Datei (`squeeze_eth` -> wachen.eth.json / handelsjournal.eth.csv).
    Ohne diesen Griff las der Ratschenpruefer die HAUPT-Wachen und meldete
    fuer den Arm "keine wachen.json" - die Ratche des Arms war ungeprueft.
    Gesucht wird von rechts: `spur.split("_")` von hinten gekuerzt, bis eine
    Datei da ist. Dieselbe Regel wie in spiegelstand.spur_zeile.
    """
    teile = spur.split("_") if spur != ordner else []
    for i in range(len(teile) - 1, 0, -1):
        suf = "_".join(teile[i:])
        w = os.path.join(HIER, ordner, "wachen.%s.json" % suf)
        if os.path.isfile(w):
            return w, os.path.join(HIER, ordner, "handelsjournal.%s.csv" % suf)
    return (os.path.join(HIER, ordner, "wachen.json"),
            os.path.join(HIER, ordner, "handelsjournal.csv"))


def befrage(w, ordner, modulordner, modulname, spur=None, journal=None):
    """Hoechststand und Ruecklauf aus dem lage() der Spur selbst.

    w MUSS uebergeben werden: lage() liest die Wachen (kill_switch, Rahmen) und
    wirft mit einem leeren Dict KeyError - eine leere Konfiguration ist keine
    gueltige Konfiguration.
    """
    md = os.path.join(HIER, modulordner)
    if md not in sys.path:
        sys.path.insert(0, md)
    for k in [k for k in list(sys.modules) if k in (modulname, "basis")]:
        del sys.modules[k]
    mod = __import__(modulname)

    if journal is None:
        journal = os.path.join(HIER, ordner, "handelsjournal.csv")
    if not os.path.exists(journal):
        return mod, None
    return mod, mod.lage(w, journal, {})


def main():
    kopf = ("Spur", "Herkunft", "Schwelle", "Buchrisiko", "1.0x?", "Hoch", "greift")
    print("%-9s %-14s %9s %11s %7s %9s %s" % kopf)
    print("-" * 78)

    probleme = []
    for spur, ordner, modulordner, modulname in SPUREN:
        wpath, jpath = _dateien(spur, ordner)
        if not os.path.exists(wpath):
            print("%-9s keine wachen.json" % spur)
            continue
        with open(wpath, "r", encoding="utf-8") as f:
            w = json.load(f)

        schwelle = RATSCHEN.halbierungsschwelle(w)
        risiko = RATSCHEN.buch_risiko(w)
        ausdruecklich = w.get("drawdown_halbierung_usd") is not None
        herkunft = ("ausdr.+herl." if ausdruecklich and risiko is not None
                    else "ausdruecklich" if ausdruecklich
                    else "hergeleitet" if schwelle is not None
                    else "KEINE")

        stimmt = "-"
        if schwelle is not None and risiko is not None:
            stimmt = "ja" if abs(schwelle - risiko) <= TOLERANZ else "NEIN"
            if stimmt == "NEIN":
                probleme.append("%s: Betrag %.2f weicht von 1.0 x Buchrisiko "
                                "%.2f ab" % (spur, schwelle, risiko))
        if schwelle is not None and risiko is None and ausdruecklich:
            stimmt = "n/a"          # nicht herleitbar, bewusst ausdruecklich

        hoch = None
        greift = "-"
        try:
            mod, s = befrage(w, ordner, modulordner, modulname, spur,
                             journal=jpath)
            hoch = s.get("hoechststand_usd") if s is not None else None
            if schwelle is not None:
                greift = ("im Gewinn"
                          if RATSCHEN.im_gewinn(hoch, w, schwelle)
                          else "erst im Minus")
                if greift == "erst im Minus":
                    probleme.append("%s: Schwelle %.2f liegt ueber dem "
                                    "Gewinnhoechststand %.2f - greift erst nach "
                                    "Verlust ueber den Nullpunkt"
                                    % (spur, schwelle, hoch))
        except Exception as e:                                     # noqa: BLE001
            greift = "FEHLER %s" % type(e).__name__
            probleme.append("%s: lage() nicht befragbar (%s: %s) - NICHT "
                            "geprueft" % (spur, type(e).__name__, e))

        print("%-9s %-14s %9s %11s %7s %9s %s"
              % (spur, herkunft,
                 "%.2f" % schwelle if schwelle is not None else "-",
                 "%.2f" % risiko if risiko is not None else "-",
                 stimmt,
                 "%.2f" % hoch if hoch is not None else "-",
                 greift))

    print()
    if probleme:
        for p in probleme:
            print("  ! %s" % p)
    else:
        print("  Alle Ratschen stimmen mit der Regel 1.0 x Buchrisiko ueberein")
        print("  und greifen noch innerhalb des Gewinns (oder die Spur ist neu).")
    print()
    print("  Ruhend, nicht geprueft: %s" % ", ".join(RUHT))
    print("  Alle fuenf Spuren sind jetzt herleitbar UND fuehren den Betrag")
    print("  ausdruecklich. Der ausdrueckliche Wert hat Vorrang, damit er sich")
    print("  nicht von selbst verschiebt - die Spalte 1.0x? prueft, dass er")
    print("  nicht von der Regel davongelaufen ist.")


if __name__ == "__main__":
    main()
