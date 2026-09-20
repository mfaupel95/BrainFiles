"""Der Wochenbericht - montags, aus derselben Erhebung wie der Tagesbericht.

Der Verlauf ist n-mal derselbe Aufruf mit verschobenem Fenster. Keine neue
Rechnung: waere es eine, gaebe es zwei Formeln fuer dieselbe Frage, und die
beiden liefen auseinander.
"""
import argparse
import datetime as dt
import os
import sys

import auswertung_alle
import gesamtbilanz
import lage
import melder
import zeitfenster

HIER = os.path.dirname(os.path.abspath(__file__))

# Vier Wochen nebeneinander. Darstellungsgroesse, keine Handelsgroesse.
FENSTER_ANZAHL = 4
FENSTER_TAGE = lage.FENSTER_TAGE  # dieselbe Fensterbreite wie im Tagesbericht


def verlauf(spur, anzahl=FENSTER_ANZAHL, tage=FENSTER_TAGE, kennzahlen_fn=None):
    """Die letzten 'anzahl' Fenster, juengstes zuerst."""
    hole = kennzahlen_fn or auswertung_alle.kennzahlen_fuer
    jetzt = zeitfenster.jetzt()
    aus = []
    for i in range(anzahl):
        bis = jetzt - dt.timedelta(days=tage * i)
        von = bis - dt.timedelta(days=tage)
        aus.append(hole(spur, von=von, bis=bis))
    return aus


def verlaufszeile(spur, werte):
    """Eine Zeile je Spur: vier Fenster nebeneinander."""
    teile = []
    for k in werte:
        if not k or not k.get("n"):
            teile.append("    -   ")
        elif auswertung_alle.belastbar(k):
            teile.append("%+7.2f" % k["ergebnis"])
        else:
            teile.append("  n=%-2d " % k["n"])
    return "  %-20s %s" % (spur, " ".join(teile))


def bilanzteil(posten):
    """Die Gesamtbilanz, getrennt nach Waehrung und Papier/Live."""
    s = gesamtbilanz.summe(posten)
    zeilen = []
    for (waehrung, live), t in sorted(s.items()):
        zeilen.append("  %-4s %-7s %4d Runden  %+10.2f  Treffer %d%%"
                      % (waehrung, "Live" if live else "Papier", t["n"],
                         t["ergebnis"],
                         round(100.0 * t["treffer"] / t["n"]) if t["n"] else 0))
    if not zeilen:
        zeilen.append("  Keine belastbare Spur in diesem Fenster.")
    return "\n".join(zeilen)


def baue():
    """Der Wochenbericht als Text. Mantel um _baue(): siehe dort.

    Die Erhebung wohnt in lage.py und liest ihre Ordner ueber `lage.HIER`.
    Wer `wochenbericht.HIER` auf einen Datenordner umbiegt - Tests tun genau
    das -, meint auch die Erhebung. Dasselbe Muster wie
    `tagesbericht.baue()`/`tagesbericht._baue()`.
    """
    alt = lage.HIER
    lage.HIER = HIER
    try:
        return _baue()
    finally:
        lage.HIER = alt


def _baue():
    """Der eigentliche Bericht - siehe baue() fuer die HIER-Bindung."""
    heute = dt.datetime.now()
    t = ["<b>Handel - Woche  %s</b>" % heute.strftime("%d.%m.%Y")]

    t.append("\n<b>Verlauf</b>  (vier Fenster a %d Tage, juengstes links)"
             % FENSTER_TAGE)
    erhebung = lage.erhebe(mit_xperp=False)
    for e in erhebung:
        if not e["schluessel"]:
            continue
        # Je Spur gekapselt wie lage.erhebe() je Holer: eine kaputte Spur
        # (z. B. ein beschaedigtes Journal) kostet eine Fehlzeile, nicht den
        # gesamten Wochenbericht.
        try:
            t.append(verlaufszeile(e["schluessel"], verlauf(e["schluessel"])))
        except Exception as fehler:                        # noqa: BLE001
            t.append("  %-20s Verlauf ausgefallen: %s: %s"
                     % (e["schluessel"], type(fehler).__name__, fehler))
    t.append("  n=<Zahl> heisst: zu wenige Runden fuer eine Aussage.")

    von, bis = zeitfenster.fenster(tage=FENSTER_TAGE * FENSTER_ANZAHL)
    posten = gesamtbilanz.posten(von=von, bis=bis)
    t.append("\n<b>Gesamtbilanz</b>  (%d Tage)" % (FENSTER_TAGE * FENSTER_ANZAHL))
    t.append(bilanzteil(posten))

    ohne_buch = sorted(e["schluessel"] for e in erhebung
                       if e["buchlage"] == "kein_buch" and e["schluessel"])
    if ohne_buch:
        t.append("\n<b>Kein Buch</b>")
        for name in ohne_buch:
            t.append("  %s" % name)
        t.append("  Eine laufende Spur ohne Journal ist ein Betriebsfehler.")

    try:
        import guthaben_abgleich                          # noqa: PLC0415
        t.append("\n" + guthaben_abgleich.text())
    except Exception as e:                                # noqa: BLE001
        t.append("\nGuthabenabgleich nicht verfuegbar: %s" % e)

    return "\n".join(t)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--senden", action="store_true",
                   help="zusaetzlich per Telegram schicken")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = baue()
    print(text.replace("<b>", "").replace("</b>", ""))
    if a.senden and not melder.sende(text):
        print("\n-> nicht gesendet: %s fehlt" % melder.fehlt())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
