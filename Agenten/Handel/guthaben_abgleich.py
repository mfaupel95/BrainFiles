"""Buchbilanz gegen Kontostand - nur fuer die drei Spuren mit Boersenzugang.

Ziel ist nicht Uebereinstimmung. Bei offenen Positionen kann es sie nicht
geben. Ziel ist die Erklaerbarkeit der Differenz: Bilanz plus gebundener
Einsatz sollte den Kontostand ergeben. Was uebrig bleibt, ist der Fund - eine
systematisch danebenliegende Kostenformel zeigt sich hier als wachsender Rest
und sonst nirgends.

Fuer die uebrigen Papierspuren gibt es nichts abzugleichen. Ein "Abgleich"
gegen ein leeres Konto waere eine Zahl, die Vertrauen erzeugt, ohne etwas zu
pruefen.

Abruf nur beim Wochenbericht, nie beim Tagesbericht: der darf nicht am Netz
haengen. Das Modul ist strikt lesend - es ruft nur Kontostaende ab, es
platziert keine Order, storniert nichts und schreibt keinen Kontostand.
"""
import os
import sys

import auswertung_alle
import lage
import zeitfenster

HIER = os.path.dirname(os.path.abspath(__file__))

LIVE = ("scanner", "kraken", "xperp")
WAEHRUNG = {"scanner": "USD", "kraken": "EUR", "xperp": "USD"}


def _konto_fn(spur):
    """Der Kontostandabruf der Spur. Import erst beim Aufruf - ein fehlendes
    Boersenmodul darf den Bericht nicht am Laden hindern."""
    def hole():
        sys.path.insert(0, os.path.join(HIER, spur))
        if spur == "kraken":
            import kraken                                # noqa: PLC0415
            return float(kraken.guthaben("ZEUR"))
        if spur == "scanner":
            import okx                                   # noqa: PLC0415
            return float(okx.guthaben_usdt())
        import okxf                                      # noqa: PLC0415
        return float(okxf.guthaben_usdt())
    return hole


def _gebunden(spur):
    """Was gerade in offenen Positionen steckt."""
    for e in lage.erhebe(mit_xperp=False):
        if e["schluessel"] == spur:
            return sum(p.get("wert") or 0 for p in e["positionen"])
    return 0.0


def abgleich(spur, konto=None, bilanz=None, gebunden=None):
    """Ein Abgleich. Alle drei Groessen sind uebergebbar - fuer Tests, und
    damit der Abruf an genau einer Stelle scheitern kann."""
    fehler = None
    if callable(konto):
        try:
            konto = konto()
        except Exception as e:                           # noqa: BLE001
            fehler = "%s: %s" % (type(e).__name__, e)
            konto = None
    elif konto is None:
        try:
            konto = _konto_fn(spur)()
        except Exception as e:                           # noqa: BLE001
            fehler = "%s: %s" % (type(e).__name__, e)
    if bilanz is None:
        von, bis = zeitfenster.fenster()
        k = auswertung_alle.kennzahlen_fuer(spur, von=von, bis=bis)
        bilanz = (k or {}).get("ergebnis", 0.0)
    if gebunden is None:
        gebunden = _gebunden(spur)
    rest = None if fehler else konto - bilanz - gebunden
    return {"spur": spur, "konto": konto, "bilanz": bilanz,
            "gebunden": gebunden, "rest": rest,
            "waehrung": WAEHRUNG[spur], "fehler": fehler}


def text(abgleiche=None):
    """Der Abschnitt fuer den Wochenbericht."""
    if abgleiche is None:
        abgleiche = [abgleich(s) for s in LIVE]
    t = ["<b>Guthabenabgleich</b>"]
    for a in abgleiche:
        if a["fehler"]:
            t.append("  %-8s Abruf ausgefallen: %s"
                     % (a["spur"], a["fehler"][:80]))
            continue
        t.append("  %-8s Konto %.2f %s = Bilanz %+.2f + gebunden %.2f "
                 "+ Rest %+.2f"
                 % (a["spur"], a["konto"], a["waehrung"], a["bilanz"],
                    a["gebunden"], a["rest"]))
    t.append("  Die uebrigen Spuren fuehren ein Papierbuch - nichts abzugleichen.")
    t.append("  Ein wachsender Rest ist der Fund, nicht die Uebereinstimmung.")
    return "\n".join(t)
