"""Kraken-Futures-Orderweg fuer die omnitrade_futures-Spur.

DIESES MODULE IST EIN ADAPTER
-----------------------------
`spur_buch.orderweg()` erwartet eine Boerse mit DENSELBEN Funktionsnamen wie
`mosaic/okx_spot` und `mosaic/kraken_spot` (markt_kauf, markt_verkauf,
algo_stop_setzen, algo_stornieren, gefuellte_menge, guthaben_waehrung,
letzter_kurs, menge_fuer, schluessel_vorhanden, demo_modus). Hier steht der
Futures-Weg dahinter: `nautilus_kraken/kraken_futures.py` ueber den PFAD
geladen (kein sys.path-Eintrag - der haette gleichnamige Hausmodule verdeckt).

HEBEL
-----
Der Hebel steht in der wachen (`hebel`, Zahl - Hausregel: "kein geratener
Hebel") und wird VOR dem Zyklus mit `setze_hebel()` gesetzt; spur_buch reicht
die wachen nicht in die Orderfunktionen. Er geht mit JEDER Order an die Boerse
(Feld `leverage` in /sendorder) - Margenhohe entscheidet die Boerse, nicht das
Buch. Gemessen ist am 25.09.2026 nur der Einschussplan (EEA retail 10 % = 10x);
ob Kraken den leverage-Parameter annimmt, zeigt der erste echte 1-Kontrakt-Lauf.

MENGE
-----
`menge_fuer` liefert GANZE Kontrakte (1 Kontrakt = 1 Einheit der Basiswaehrung,
gemessen 25.09.2026). Ein Bruchteil waere an der Boerse nicht stellbar - besser
der Einstieg faellt aus, als dass die Spur eine Menge bucht, die es nicht gibt.
"""

import importlib.util
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)

_spec = importlib.util.spec_from_file_location(
    "kraken_futures_pfad",
    os.path.join(HANDEL, "nautilus_kraken", "kraken_futures.py"))
kf = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = kf                     # @dataclass braucht den Eintrag
_spec.loader.exec_module(kf)

# Hebel als Modulzustand, weil spur_buch die wachen nicht in die
# Orderfunktionen reicht. Vorgabe 1.0 = kein Hebel (sicherer Ausfall).
_HEBEL = [1.0]


def setze_hebel(w):
    """Hebel aus der wachen uebernehmen (Zahl, Hausregel)."""
    try:
        wert = float(w.get("hebel") or 1.0)
    except (TypeError, ValueError):
        wert = 1.0
    _HEBEL[0] = max(1.0, wert)
    return _HEBEL[0]


def hebel_vorbereiten(inst, hebel=None):
    """Die Hebel-Obergrenze am Kontrakt pruefen und notfalls setzen.

    GEMESSEN 01.10.2026: der `leverage`-Parameter der Order wird von Kraken
    Futures IGNORIERT - der Hebel steht in /leveragepreferences je Kontrakt
    (isolated margin, Margin = Nominal/Hebel; 7x belegt mit 16,80 USD auf
    117,33 Nominal). Deshalb gehoert das Setzen hierher, nicht in die Order:
    eine Order mit falscher Marginreserve scheitert erst am Konto. Idempotent -
    gelesen wird jedes Mal (ein GET), geschrieben nur bei Abweichung (ein PUT).
    Fehler laufen nicht unter: ohne Bestaetigung wird MELDEND geworfen, die
    Sperrenkette bleibt die naechste Station.
    """
    hebel = float(hebel if hebel is not None else _HEBEL[0])
    if hebel <= 1.0:
        return None
    # `inst` kommt als KONTRAKTNAME (PF_SOLUSD) - der Kontraktname ist die
    # Schluesselgroesse der Preference, nicht das Buch-Instrument.
    gesetzt = dict(kf.hebel_preference_lesen()).get(inst)
    if gesetzt is not None and abs(float(gesetzt) - hebel) < 1e-9:
        return hebel
    return kf.hebel_preference_setzen(inst, hebel)


def hebel():
    return _HEBEL[0]


def _mit_hebel(werte):
    if _HEBEL[0] > 1.0:
        werte["leverage"] = "%g" % _HEBEL[0]
    return werte


# --- Die Schnittstelle von spur_buch.orderweg() ------------------------------

def schluessel_vorhanden():
    return kf.schluessel_vorhanden()


def demo_modus():
    """Kraken Futures kennt keinen Demo-Modus - Papier ist immer NUR das Buch."""
    return False


def guthaben_waehrung(waehrung="USD"):
    """Freies Guthaben im Futures-Konto (flex, availableMargin - NICHT cash)."""
    return kf.guthaben("usd")


def letzter_kurs(inst):
    return kf.letzter_kurs(inst)


def menge_fuer(inst, betrag, kurs):
    """GANZE Kontrakte, die in den Betrag passen. (menge, fehler)."""
    try:
        kurs = float(kurs)
        betrag = float(betrag)
    except (TypeError, ValueError):
        return 0.0, "Kurs oder Einsatz unlesbar"
    if kurs <= 0:
        return 0.0, "Kurs %.2f unbrauchbar" % kurs
    n = int(betrag // kurs)
    if n < 1:
        return 0.0, ("Einsatz %.2f USD kleiner als ein Kontrakt (%.2f USD)"
                     % (betrag, kurs))
    return float(n), ""


def markt_kauf(inst, menge):
    """Long-Eroeffnung, echt - die Spur ordert nur im Live-Modus."""
    return kf.markt_kauf(inst, menge, echt=True, leverage=_HEBEL[0])


def markt_verkauf(inst, menge):
    return kf.markt_verkauf(inst, menge, echt=True)


def algo_stop_setzen(inst, menge, seite, stop):
    """Schutz-Stop an der Boerse. Die Seite leitet stop_setzen aus der
    offenen Position ab (long -> sell, reduceOnly)."""
    return kf.stop_setzen(inst, menge, stop, echt=True, leverage=_HEBEL[0])


def algo_stornieren(inst, order_id):
    return kf.order_stornieren(str(order_id))


def stop_nachziehen(order_id, inst, menge, stop_preis):
    """Der stp-Stop wird auf einen neuen Preis gezogen (/editorder) - IMMER echt.

    spur_buch ruft diese Funktion im Live-Zyklus (T-286); nur nach oben
    entscheidet der Aufrufer. Ein Trockenlauf waere hier gefaehrlich, weil er
    eine Kennung zurueckgibt, die wie eine echte Order aussieht - der Adapter
    ist der Live-Weg, echt ist die Vorgabe.
    """
    return kf.stop_nachziehen(order_id, inst, menge, stop_preis, echt=True)


def gefuellte_menge(order_id):
    return kf.gefuellte_menge(order_id)
