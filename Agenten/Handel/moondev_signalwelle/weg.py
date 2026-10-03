"""OKX-Orderweg fuer moondev_signalwelle.

WARUM EIGENTLICH EIN EIGENER ADAPTER
------------------------------------
`spur_buch.orderweg()` kennt fuer die Buerochse `okx` bereits
`mosaic/okx_spot` - eine vollstaendige Schnittstelle mit denselben
Funktionsnamen. Fuer eine Spur mit fester Instrumentliste waere das
genug. signalwelle ist aber die einzige Spur des Hauses, die ihre
Instrumente LAUFEND neu waehlt: sie kommt aus der CoinGecko-Top-Mover-
Liste, also aus allem, was gerade steigt.

GEMESSEN am 03.10.2026 ueber die oeffentliche Instrumentliste
(1143 OKX-Spotpaare): von den 16 Instrumenten aus dem Journal haben 9
einen OKX-Markt (AI, AR, ARB, CARDS, CRV, ICP, NEAR, NIGHT, STX - jeweils
USDC, USDT und EUR) und 7 keinen (BTW, CASHCAT, DRV, FARTCOIN, GENIUS,
MARSCOIN, XDC). Genau diese 7 sind die, bei denen ein Orderweg ohne
Marktpruefung zur naechstgelegenen_gen Hand faehrt.

DESWEGEN DER KERNTEST
---------------------
`markt()` wird VOR jeder Order gerufen und wirft `Meldend`, wenn das
Instrument an der Boerse nicht existiert. Nicht: auf ein aehnliches Paar
ausweichen. Ein stilles Ersetzen waere der teuerste Fehler, den ein
Orderweg machen kann - die Spur wuerde eine Position in etwas anderem
fuehren als das, was sie geprueft hat, und die Basislinie im Audit
bezoge sich auf ein Instrument, das sie nie gehandelt hat.

Die Marktliste wird einmal je Prozess geholt und dann gepuffert; sie
aendert sich unter einem Lauf nicht, und ein Abruf je Order waere der
teuerste Teil eines 15-Minuten-Takts.

WAS DIESER WEG NICHT TUT
-----------------------
Er schaltet nichts frei. `handel_erlaubt` und `freigabe.erfuellt` bleiben
false, der Weg wird nicht benutzt, solange die Spur Papier laeuft. Er ist
der Anschluss, nicht die Freigabe - die beiden Schalter bleiben getrennt,
sonst waere ein gebauter Weg eine scharfschaltung.
"""

import importlib.util
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)

_spec = importlib.util.spec_from_file_location(
    "okx_spot_signalwelle", os.path.join(HANDEL, "mosaic", "okx_spot.py"))
okx = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = okx
_spec.loader.exec_module(okx)


class Meldend(RuntimeError):
    """Das Instrument hat an der Boerse keinen Markt - es wird nicht ersetzt."""


_MAERKTE = [None]          # None = noch nicht geholt
_QUOTEN = ("USDC", "USDT", "EUR")


def maerkte():
    """Die Instrumentliste der Boerse, einmal je Prozess."""
    if _MAERKTE[0] is None:
        try:
            daten = okx._roh("GET", "/api/v5/public/instruments?instType=SPOT")
        except Exception:
            daten = []
        if isinstance(daten, dict):
            daten = daten.get("data") or []
        _MAERKTE[0] = {d.get("instId") for d in (daten or []) if d.get("instId")}
    return _MAERKTE[0]


def markt(inst, boerse_inst):
    """True, wenn es das Paar gibt. Wirft, wenn die Liste nicht lesbar war.

    Eine leere Liste ist kein Beweis fuer "kein Markt" - sie ist ein
    Ausfall. Beides unterscheidet man hier, statt beide als Ablehnung zu
    behandeln und die Spur stillstehen zu lassen.
    """
    if not maerkte():
        raise Meldend("OKX-Instrumentliste nicht lesbar - kein Einstieg, "
                      "solange der Markt nicht bekannt ist")
    return boerse_inst in _MAERKTE[0]


def boersenpaar(inst):
    """Das Paar, auf das die Spur ihre Kurse bezieht, oder None.

    Reihenfolge USDC vor USDT vor EUR: USDC ist die Quote, in der das
    Konto liegt (0,00 USDT auf dem EEA-Konto, gemessen 02.10.2026).
    """
    for q in _QUOTEN:
        kandidat = "%s-%s" % (inst, q)
        if maerkte() and kandidat in _MAERKTE[0]:
            return kandidat
    return None


# --- Die Schnittstelle von spur_buch.orderweg() ----------------------------

def schluessel_vorhanden():
    return okx.schluessel_vorhanden()


def demo_modus():
    return okx.demo_modus()


def guthaben_waehrung(waehrung="USDC"):
    return okx.guthaben(waehrung)


def letzter_kurs(inst):
    return okx.letzter_kurs(inst)


def menge_fuer(inst, betrag, kurs):
    return okx.menge_fuer(inst, betrag, kurs)


def markt_kauf(inst, menge):
    paar = boersenpaar(inst)
    if paar is None:
        raise Meldend("%s hat an der OKX keinen Spotmarkt - die Spur wird "
                      "nicht auf ein anderes Paar umgeschrieben" % inst)
    return okx.markt_kauf(paar, menge)


def markt_verkauf(inst, menge):
    paar = boersenpaar(inst)
    if paar is None:
        raise Meldend("%s hat an der OKX keinen Spotmarkt - VERKAUF "
                      "verweigert; das ist genau der Fall, in dem eine "
                      "Position ohne Weg bliebe" % inst)
    return okx.markt_verkauf(paar, menge)


def algo_stop_setzen(inst, menge, seite, stop):
    paar = boersenpaar(inst) or "%s-USDC" % inst
    return okx.algo_stop_setzen(paar, menge, seite, stop)


def algo_stornieren(inst, order_id):
    return okx.algo_stornieren(order_id)


def stop_nachziehen(order_id, inst, menge, stop_preis):
    """IMMER echt - ein Trockenlauf liefert eine Kennung, die wie eine echte
    Order aussieht. Vergleiche omnitrade_futures/weg.py."""
    paar = boersenpaar(inst) or "%s-USDC" % inst
    return okx.stop_nachziehen(order_id, paar, menge, stop_preis, echt=True)


def gefuellte_menge(order_id):
    return okx.gefuellte_menge(order_id)