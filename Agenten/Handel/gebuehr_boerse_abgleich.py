"""Gebuehr gegen die AKTIVE Boerse - der Abgleich, den es vorher nicht gab (T-330).

DIE LUECKE
----------
`gebuehren_setzen.py` prueft die EINHEIT (Bruch statt Prozent) und faehrt eine
AENDERUNGSTABELLE ab. Beides kann gruen sein, waehrend eine Runde sechsfach zu
teuer gerechnet wird: T-329 war genau das - mosaics Kraken-Satz 0,006 stand
noch in der Wache, nachdem Kraken aus `boersen` herausgegangen war und die Spur
ueber OKX handelte (1,2 % je Runde statt der gemessenen 0,2 %).

Zwei Pruefungen konnten das nicht sehen, weil sie an der falschen Frage
standen:
  * die Einheitenpruefung fragt "ist 0,006 ein Bruch oder ein Prozent?"
  * die Aenderungstabelle fragt "steht in DIESER Liste der richtige Wert?"

Die dritte Frage fehlte: "traegt die Wache den Satz ihrer EIGENEN aktiven
Boerse?" Eine Spur kann ihre Boerse wechseln und den Satz behalten - es
geschah zweimal (Kraken raus aus mosaic am 30.09.2026, omniquant auf
kraken_futures am 01.10.2026).

DAS WERKZEUG
------------
Je Wachen: die aktive Boerse bestimmen (Vorragliste `boersen[0]`, sonst
`boerse`/`venue`), den GEMESSENEN Satz daraus ableiten und mit dem Wert in der
Datei vergleichen. Abweichung melden. Schreiben nur mit `--anwenden`, dann
mit Sicherung `.bak-JJJJMMTT`.

NICHTS BEHAUPTET: eine Wache ohne ableitbaren Satz (Onchain, Paper ohne
Boerse) wird gezaehlt, aber nicht beanstandet - das ist eine Modellannahme,
kein Fehler.

Aufruf (aus Agenten/Handel):
    ../../scanner/.venv/Scripts/python.exe gebuehr_boerse_abgleich.py
    ... --anwenden      # schreibt mit Sicherung
    ... --json          # fuer einen Wächter
Exit 1, wenn mindestens eine Abweichung offen ist (Watchdog-Muster).
"""
import argparse
import datetime as dt
import json
import os
import shutil
import sys

HIER = os.path.abspath(os.path.dirname(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

# Aus dem Hauswerkzeug importieren, NICHT wiederholen: zwei Gebuehrtabellen
# sind zwei Wahrheiten, und die Abweichung zwischen ihnen waere genau der
# Befund, den dieses Werkzeug sucht.
import gebuehren_setzen as gs                                 # noqa: E402

# Wohin eine Wache ohne `boerse`-Feld handelt. Gespiegelt aus
# `spur_buch.orderweg`: `str(w.get("boerse") or "okx")`. Steht hier eine
# andere Vorgabe, beurteilt das Werkzeug eine andere Börse als der Betrieb.
VORGABE_BOERSE = "okx"

# MARKTYP aus dem Code, wenn die Wache ihn nicht traegt. `boerse: okx` allein
# lasst offen, ob SPOT (0,10 %) oder PERP (0,05 %) gemeint ist - genau diese
# Unklarheit liest `gebuehren_setzen.satz_pct_fuer` aus `instrumente` und
# `moeglich`. Bei 26 Wachen ohne `boerse`-Feld fehlt ihr dieser Nachweis, und
# das Ergebnis war: 6 moondev-Spuren wurden zu Unrecht auf den Spot-Satz
# gestellt (gemessen 0,05 % Perp, Werten unterstellt 0,10 %).
#
# Es wird deshalb der WORTLAUT gelesen, den der Import fuehrt. `okxf` ist das
# Hausmodul der XPERP-Futures (`okxf.markt_kauf` geht an /api/v5/trade/order
# mit `tdMode`), `okx`/`okx_spot` der Spot-Weg.
_CODE_PERP = ("okxf", "xperp", "perpetual")

# DER BOERSENNAME AUS DEM CODE, wenn die Wache schweigt.
#
# GEMESSEN 04.10.2026 (T-330): die Wachen tragen bei 26 von 47 Spuren kein
# `boerse`-Feld. Ein blosser OKX-Default beanstandete daraufhin 16 Spuren zu
# Unrecht - `kraken` handelt ueber `import kraken` (0,60 % Spot), `xperp` und
# `swap` ueber `okxf` (0,05 % Perp), `orbk` ebenfalls ueber `kraken`. Die
# Wache allein sagt es nicht; der IMPORT im handeln.py schon.
#
# Die Reihenfolge ist die Guelle des Ausgleichs: ein Modulname, der die
# Produktart nennt (`kraken_futures`), schlaegt die Börse (`kraken`), weil
# dort 0,05 % gegen 0,60 % gelten.
_CODE_BOERSE = (
    ("kraken_futures", "kraken_futures"),
    ("okxf", "okx_perp"),
    ("kraken_rest", "kraken"),
    ("kraken", "kraken"),
    ("okx_spot", "okx_spot"),
    ("okx", "okx_spot"),
)


def boerse_aus_dem_code(ordner):
    """Der Boersenname, den die Spur wirklich benutzt - oder None.

    Gelesen wird die eigene `handeln.py` der Spur, NICHT das Haus: eine Spur
    kann ein Nachbar-Modul nur als Rechenweg laden (Kerzen, Kurse) und
    trotzdem woanders ordnen. Deshalb zaehlt nur ein Import, dessen Name die
    Boerse traegt, und keine erwaehnte Modul-Zeile.

    Findet sich nichts, bleibt es bei `None` - dann entscheidet der Aufrufer.
    """
    pfad = os.path.join(ordner, "handeln.py")
    if not os.path.isfile(pfad):
        return None
    try:
        with open(pfad, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    import re
    # NUR Importzeilen: `import kraken`, `from ... import okxf`.
    for zeile in text.splitlines():
        if not re.match(r"\s*(import|from)\s", zeile):
            continue
        for name, boerse in _CODE_BOERSE:
            if re.search(r"\b%s\b" % re.escape(name), zeile):
                return boerse
    return None


def aktive_boerse(w, ordner=None):
    """Die Boerse, auf der diese Wache HEUTE handelt.

    Reihenfolge = Guelle des Ausgleichs:
    1. `boersen` als Vorragliste: eine Spur mit zwei Boersen handelt auf der
       ERSTEN (das ist die Hausregel aus `venue_b-bind`),
    2. `boerse`/`venue` allein,
    3. der Import in der eigenen `handeln.py` (der Code luegt nicht),
    4. OKX als Vorgabe aus `spur_buch.orderweg`.

    Schritt 3 ist nicht Kosmetik: 26 von 47 Wachen tragen kein
    `boerse`-Feld. Mit einem blosser OKX-Default wurden daraufhin 16 Spuren
    zu Unrecht beanstandet - `kraken` handelt ueber `import kraken` (0,60 %),
    `xperp` und `swap` ueber `okxf` (0,05 % Perp). Wer diese Stufe
    weglässt, meldet Befunde, die keine sind, und wird bei der ersten
    Gegenprobe abgeschaltet.

    `boersen` kann eine Liste oder ein einzelner String sein (beides steht in
    Spuren-Ordnern). Ein leerer String zaehlt als "keine Angabe".
    """
    liste = w.get("boersen")
    if isinstance(liste, (list, tuple)) and liste:
        return str(liste[0])
    if isinstance(liste, str) and liste.strip():
        return liste.strip()
    for feld in ("boerse", "venue"):
        wert = w.get(feld)
        if isinstance(wert, str) and wert.strip():
            return wert.strip()
    if ordner:
        aus_code = boerse_aus_dem_code(ordner)
        if aus_code:
            return aus_code
    return VORGABE_BOERSE


def _ist_modellannahme(w):
    """Traegt die Wache einen bewusst gesetzten Satz statt eines Boersensatzes?

    BELEGT, nicht geraten (04.10.2026): die Wache von `spiegel` traegt
    `gebuehr_taker: 0.01` mit der Notiz "MODELLANNAHME, NICHT gemessen: 1,0 %
    je Seite fuer Onchain-Handel (DEX-Gebuehr plus Slippage)". Der Satz ist
    nicht veraltet - er ist eine Entscheidung, und er ist DREIMAL so teuer wie
    der Boersatz, weil die Börse gar nicht beteiligt ist. Ein Abgleich, der
    ihn auf 0,10 % zieht, wuerde das Buch um eine Groessenordnung
    schoenrechnen.

    Gleiches gilt fuer `kopier`, `kopier1zu1` und `robinhood_radar`
    (ebenfalls Onchain, ebenfalls mit `MODELLANNAHME` in der Notiz).

    Das Merkmal ist die NOTIZ, nicht der Zahlenwert: eine Wache kann einen
    Boersatz tragen und trotzdem eine Notiz mit dem Wort tragen - dann gewinnt
    die Notiz, denn sie sagt, dass der Zahlenwert absichtlich ist.
    """
    for feld in ("_gebuehr_quelle", "_kosten"):
        text = str(w.get(feld) or "").upper()
        if "MODELLANNAHME" in text:
            return True
    # Onchain ohne Notiz: es gibt keine Boerse, deren Satz man einsetzen
    # koennte. Die Wache traegt das ueber `_zweck`/`_kosten`; ein eigenes
    # Merkmal waere hier geraten.
    for feld in ("_zweck", "_kosten"):
        text = str(w.get(feld) or "").lower()
        if "onchain" in text or "dex" in text or "pump.fun" in text:
            return True
    return False


def befund(w, ordner=None):
    """(soll_pct, hat_pct, schluessel, modellannahme) fuer eine Wachen.

    `modellannahme=True` heisst: die Wache traegt einen bewusst gesetzten
    Satz, der KEIN Boersensatz ist - ein Onchain-Papierbuch (1,0 % DEX plus
    Slippage) oder eine bewusste Null. Solche Werte werden NICHT beanstandet
    und nicht geschrieben; sie zu melden hiesse die getroffene Entscheidung
    mit einem Befund zu ueberschreiben.
    """
    probe = dict(w)
    boerse = aktive_boerse(w, ordner)
    if boerse:
        probe["boerse"] = boerse
        # `satz_pct_fuer` kennt nur `boerse: okx` und entscheidet Spot oder
        # Perp ueber `moeglich`/`instrumente`. Ein aus dem Code ermitteltes
        # "okx_perp" ist dort ein UNBEKANNTER Name und liefert (None, None) -
        # die Spur wuerde stillschweigend nicht beurteilt. Deshalb wird der
        # Perp-Nachweis in das Feld gesetzt, das die Rechnung liest.
        if boerse.endswith("_perp") and boerse.split("_")[0] == "okx":
            probe["boerse"] = "okx"
            probe["moeglich"] = "perp"
    satz, key = gs.satz_pct_fuer(probe)
    hat = gs.gebuehr_pct_der_wachen(w)
    return satz, hat, key, _ist_modellannahme(w)


def _wachen():
    """Jede wachen.json unter Agenten/Handel, als (pfad, daten)."""
    raus = []
    for name in sorted(os.listdir(HIER)):
        ordner = os.path.join(HIER, name)
        if not os.path.isdir(ordner):
            continue
        pfad = os.path.join(ordner, "wachen.json")
        if not os.path.isfile(pfad):
            continue
        try:
            with open(pfad, encoding="utf-8") as fh:
                raus.append((pfad, json.load(fh) or {}))
        except (OSError, ValueError):
            continue
    return raus


def pruefe(schreiben=False):
    zeilen, offen, nicht_beurteilbar = [], 0, 0
    for pfad, w in _wachen():
        ordner = os.path.dirname(pfad)
        soll, hat, key, modell = befund(w, ordner)
        if modell:
            # Bewusster Satz (Onchain, Papier). Wird gezählt, nicht gemeldet.
            nicht_beurteilbar += 1
            continue
        if soll is None:
            nicht_beurteilbar += 1
            continue
        if hat is None:
            # Kein Gebuehrfeld: die Wache rechnet brutto. Das ist eine
            # bewusste Modellannahme, kein Fehler - aber sie wird genannt,
            # weil `gebuehr_taker` 0,0 und "gar nicht gesetzt" leicht
            # verwechselt werden.
            zeilen.append((pfad, key, None, soll, "kein Gebuehrfeld"))
            continue
        if abs(float(hat) - float(soll)) < 1e-9:
            continue
        offen += 1
        zeilen.append((pfad, key, float(hat), float(soll), "ABWEICHUNG"))
        if schreiben:
            _setze(pfad, float(soll) / 100.0)
    return zeilen, offen, nicht_beurteilbar


def _setze(pfad, bruch):
    """gebuehr_taker auf einen Bruch setzen, mit Sicherung.

    Es wird an der WACHE geschrieben, nicht an der Rechnung: die Auswertung
    liest `gebuehr_taker`, und eine zweite Wahrheit daneben (die
    AENDERUNGSTABELLE) waere wieder eine Stelle, an der die Zahl abweichen
    kann.
    """
    roh, d = gs._lesen(pfad)
    alt = d.get("gebuehr_taker")
    sicherung = pfad + ".bak-" + dt.date.today().strftime("%Y%m%d")
    shutil.copy2(pfad, sicherung)
    # `_feld_setzen` liefert (neuer_text, alter_wert) - beide werden gebraucht:
    # der Text zum Schreiben, der alte Wert fuer die Meldung.
    neu, _gelesen_alt = gs._feld_setzen(
        roh, "gebuehr_taker", bruch,
        "gemessen an der aktiven Boerse %s" % aktive_boerse(d))
    # Die Zeilenenden der VORHANDENEN Datei bleiben erhalten: eine
    # Gebuehrenkorrektur darf nicht die ganze Datei umschreiben (git diff
    # zeigt dann 200 Zeilen statt einer).
    eol = gs._eol(roh) or "\n"
    text = neu
    if eol != "\n":
        text = neu.replace("\r\n", "\n").replace("\n", eol)
    with open(pfad, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("  %s: gebuehr_taker %s -> %g (Sicherung %s)"
          % (pfad, alt, bruch, os.path.basename(sicherung)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anwenden", action="store_true",
                    help="Abweichungen schreiben (mit Sicherung)")
    ap.add_argument("--json", action="store_true", help="Maschinen-Ausgabe")
    a = ap.parse_args()

    zeilen, offen, nicht_beurteilbar = pruefe(schreiben=a.anwenden)

    if a.json:
        print(json.dumps({
            "offen": offen,
            "nicht_beurteilbar": nicht_beurteilbar,
            "befunde": [{"datei": p, "boerse": k, "ist": i, "soll": s,
                         "art": a_} for p, k, i, s, a_ in zeilen]},
            ensure_ascii=False, indent=1))
        return 1 if offen else 0

    if zeilen:
        print("%-42s %-15s %-9s %-9s %s"
              % ("Datei", "Boerse", "ist", "soll", "Art"))
        for pfad, key, ist, soll, art in zeilen:
            print("%-42s %-15s %-9s %-9s %s"
                  % (os.path.basename(os.path.dirname(pfad)) +
                     "/wachen.json", key or "-",
                     "-" if ist is None else "%g %%" % ist,
                     "%g %%" % soll, art))
    else:
        print("Alle Wachen tragen den Satz ihrer aktiven Boerse.")
    print("\n%d Abweichung(en), %d Wachen nicht beurteilbar "
          "(keine Boersenangabe)." % (offen, nicht_beurteilbar))
    return 1 if offen else 0


if __name__ == "__main__":
    raise SystemExit(main())