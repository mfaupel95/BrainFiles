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
import json
import os
import sys

import auswertung_alle
import lage
import zeitfenster

HIER = os.path.dirname(os.path.abspath(__file__))

LIVE = ("scanner", "kraken", "xperp")


def _waehrung(spur):
    """Die Waehrung der Zahlen dieser Spur - aus der EINEN Hausquelle.

    T-311: `WAEHRUNG` behauptete "USD" fuer den Scanner. Das Konto (OKX EEA)
    fuehrt kein USDT - gemessen am 05.10.2026: 302,39 USDC frei, 0,00 USDT,
    0,0003 EURC. Eine Tabelle, die eine Waehrung behauptet, die es dort nicht
    gibt, ist schlimmer als keine: sie stellt eine Zahl in eine falsche
    Einheit und der Rest sieht danach wie ein Buchfehler aus.

    Die Regel steht in `auswertung_alle.einheit_fuer()` und wird hier GELESEN,
    nicht wiederholt - dieselbe Quelle wie Tagesbericht, Handelszentrale und
    Strategiekennzahlen. Vier Anzeigen mit vier eigenen Tabellen laufen
    auseinander; das war am 23.09.2026 (Kraken-BTC-Kurs aus der OKX-Tabelle)
    und am 05.10.2026 (dieser Bericht) jeweils der Fall.

    `xperp` bleibt USD: das sind die USDC-Margen auf USD_UM_XPERP, und ihre
    Einheit wird an dieser Stelle NICHT aus dem Buch abgeleitet - das waere
    eine zweite Aussage ueber dieselbe Spur.
    """
    try:
        return auswertung_alle.einheit_fuer(spur)
    except Exception:                                    # noqa: BLE001
        # Berichtsweg nicht lesbar: Zahl zeigen, nicht scheitern - wie in
        # handelszentrale.waehrung_fuer().
        return "USD"


def _scanner_quote():
    """Die Handelswaehrung des Scanners aus seiner Wachen lesen.

    `universum.quotes` ist die EINZIGE Wahrheit darueber, in welcher Waehrung
    die Spur handelt - dieselbe Quelle, aus der `handeln.py` das Guthaben-Tor
    speist. Eine eigene Liste hier waere eine zweite Wahrheit, die genau
    wieder so veraltet wie die fest verdrahtete ('USDT'). Fehlt das Feld,
    gilt USDC: die Quote mit Guthaben UND Markt auf dem EEA-Konto.

    Anlass (T-311): das Konto hat 438 USDC und 0,00 USDT. `guthaben_usdt()`
    lieferte deshalb 0.0, der Wochenbericht wies eine Differenz aus und es sah
    aus wie ein Buch, das nicht zum Konto passt.
    """
    pfad = os.path.join(HIER, "scanner", "wachen.json")
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            wachen = json.load(f)
        quotes = (wachen.get("universum") or {}).get("quotes") or []
        if quotes:
            return str(quotes[0])
    except Exception:                                        # noqa: BLE001
        pass
    return "USDC"


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
            # Die WAEHRUNG aus der Wachen, nicht USDT (T-311): das Konto
            # fuehrt kein USDT, okx.guthaben_usdt() lieferte 0.0 und der
            # Wochenbericht zeigte eine Differenz aus einer Waehrung, die es
            # nicht gibt. Das Guthaben-Tor der Spur liest dieselbe Quelle.
            return float(okx.guthaben(_scanner_quote()))
        import okxf                                      # noqa: PLC0415
        return float(okxf.guthaben_usdt())
    return hole


def _gebunden(spur):
    """Was gerade in offenen Positionen steckt.

    Eigener HIER-Mantel (wie tagesbericht.baue()/wochenbericht.baue()):
    lage.erhebe() liest ueber lage.HIER, und dieser Aufruf darf sich nicht
    heimlich auf den Mantel eines Aufrufers verlassen - bisher lief er nur
    zufaellig richtig, weil text() bislang ausschliesslich innerhalb von
    wochenbericht.baue() gerufen wird."""
    alt = lage.HIER
    lage.HIER = HIER
    try:
        for e in lage.erhebe(mit_xperp=False):
            if e["schluessel"] == spur:
                return sum(p.get("wert") or 0 for p in e["positionen"])
        return 0.0
    finally:
        lage.HIER = alt


def abgleich(spur, konto=None, bilanz=None, gebunden=None):
    """Ein Abgleich. Alle drei Groessen sind uebergebbar - fuer Tests, und
    damit der Abruf an genau einer Stelle scheitern kann.

    Fehlende Daten werden NIE stillschweigend zu 0.0: eine leere
    Boersenantwort (konto bleibt None, ohne Ausnahme) und fehlende
    Kennzahlen (kennzahlen_fuer() liefert None) setzen stattdessen
    konto_unbekannt bzw. bilanz_unbekannt - dieselbe Kennzeichnungs-Idee
    wie lage.py mit "buchlage": "kein_buch". Ein echter Nullstand bleibt
    dadurch von einer fehlenden Antwort unterscheidbar."""
    fehler = None
    konto_unbekannt = False
    bilanz_unbekannt = False
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
    if konto is None and not fehler:
        konto_unbekannt = True
    if bilanz is None:
        von, bis = zeitfenster.fenster()
        k = auswertung_alle.kennzahlen_fuer(spur, von=von, bis=bis)
        if k is None:
            bilanz_unbekannt = True
        else:
            bilanz = k.get("ergebnis", 0.0)
    if gebunden is None:
        gebunden = _gebunden(spur)
    unbekannt = konto_unbekannt or bilanz_unbekannt
    rest = None if (fehler or unbekannt) else konto - bilanz - gebunden
    return {"spur": spur, "konto": konto, "bilanz": bilanz,
            "gebunden": gebunden, "rest": rest,
            "waehrung": _waehrung(spur), "fehler": fehler,
            "konto_unbekannt": konto_unbekannt,
            "bilanz_unbekannt": bilanz_unbekannt}


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
        if a.get("konto_unbekannt") or a.get("bilanz_unbekannt"):
            teile = []
            if a.get("konto_unbekannt"):
                teile.append("Konto unbekannt (leere Boersenantwort)")
            if a.get("bilanz_unbekannt"):
                teile.append("Bilanz unbekannt (keine Kennzahlen)")
            t.append("  %-8s %s" % (a["spur"], ", ".join(teile)))
            continue
        t.append("  %-8s Konto %.2f %s = Bilanz %+.2f + gebunden %.2f "
                 "+ Rest %+.2f"
                 % (a["spur"], a["konto"], a["waehrung"], a["bilanz"],
                    a["gebunden"], a["rest"]))
    t.append("  Die uebrigen Spuren fuehren ein Papierbuch - nichts abzugleichen.")
    t.append("  Ein wachsender Rest ist der Fund, nicht die Uebereinstimmung.")
    return "\n".join(t)
