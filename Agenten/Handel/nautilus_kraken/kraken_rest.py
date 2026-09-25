"""Kraken-REST-Orderweg der nautilus_kraken-Spur.

Laedt die bestehende kraken/kraken.py (REST-API-Client des Hauses) ueber den
PFAD und stellt die Order-Funktionen bereit, die der Live-Pfad von handeln.py
braucht. Kein Nautilus-Orderpfad: Der Nautilus-Adapter (1.231.0) kann Fills
nicht lesen (postxid-Bug, 24.09.2026) und 2.0.0rc5 hat einen neuen Parse-Bug
('stop market') plus eine komplett umgebaute API. Die Order laeuft deshalb
direkt ueber die Kraken-REST-API - wie die bestehende kraken-Spur, die
live-faehig ist.

Nur Standardbibliothek. Die kraken.py liest KRAKEN_SPOT_API_KEY/SECRET aus
HKCU\\Environment (die GUELTIGEN Keys - KRAKEN_API_KEY/SECRET sind ungueltig,
Kraken antwortet 'EAPI:Invalid key').
"""

import importlib.util
import os

HIER = os.path.dirname(os.path.abspath(__file__))

# Zwei Boersen, EINE Anschlussstelle: Der Live-Zweig ruft kraken_rest.
# Welche Schnittstelle dahinter liegt, entscheidet KRAKEN_PRODUKT (der
# Futures-Launcher setzt 'futures'). Spot und Futures sind bei Kraken
# getrennte Dienste mit getrennter Signatur und getrennten Schluesseln -
# 'gleicher Weg, anderer Host' waere falsch.
PRODUKT = (os.environ.get("KRAKEN_PRODUKT") or "spot").lower()
KRAKEN_PY = os.path.join(HIER, os.pardir, "kraken", "kraken.py")


def _lade(dateiname):
    pfad = os.path.join(HIER, dateiname)
    spec = importlib.util.spec_from_file_location("kraken_rest_quelle_" + dateiname, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _lade_quelle():
    if PRODUKT == "futures":
        return _lade("kraken_futures.py")
    return _lade(os.path.join(os.pardir, "kraken", "kraken.py"))


_kraken = _lade_quelle()


def produkt():
    """Welche Schnittstelle haengt dran ('spot' oder 'futures')."""
    return PRODUKT


def schluessel_vorhanden():
    """Hat der Key Trade-Permission? (Kraken: schluessel_vorhanden)."""
    return _kraken.schluessel_vorhanden()


GUTHABEN_WAEHRUNG = "usd" if PRODUKT == "futures" else "ZEUR"


def guthaben(waehrung=None):
    return _kraken.guthaben(waehrung or GUTHABEN_WAEHRUNG)


def einschuss(paar, kontrakte=1, kurs=None):
    """Einschuss (USD) fuer N Kontrakte - nur Futures, sonst None.

    Futures notiert in KONTRAKTEN, und 1 Kontrakt ist EINE Einheit der
    Basiswaehrung (gemessen 25.09.2026, siehe kraken_futures.einschuss).
    Der Live-Pfad muss das wissen: eine Menge, die kleiner als ein Kontrakt
    ist, wird sonst still auf 1 aufgerundet - mit dem Zehnfachen des
    gedachten Einsatzes.
    """
    if not hasattr(_kraken, "einschuss"):
        return None
    return _kraken.einschuss(paar, kontrakte, kurs=kurs)


def handelbar(paar, kontrakte=1, frei=None):
    """Reicht das Guthaben fuer den kleinsten Satz? Grund oder None."""
    if not hasattr(_kraken, "handelbar"):
        return None
    return _kraken.handelbar(paar, kontrakte, frei=frei)


def kontrakte(paar, menge, kurs=None):
    """Basis-Menge -> Kontraktzahl (Futures) bzw. die Menge selbst (Spot)."""
    if not hasattr(_kraken, "kontrakte"):
        return menge
    return _kraken.kontrakte(paar, menge, kurs=kurs)


def markt_kauf(paar, menge, echt=False):
    return _kraken.markt_kauf(paar, menge, echt=echt)


def markt_verkauf(paar, menge, echt=False):
    return _kraken.markt_verkauf(paar, menge, echt=echt)


def stop_setzen(paar, menge, stop_preis, echt=False, leverage=None):
    return _kraken.stop_setzen(paar, menge, stop_preis, echt=echt,
                               leverage=leverage)


def offene_orders():
    return _kraken.offene_orders()


def order_stornieren(txid):
    return _kraken.order_stornieren(txid)


def gefuellte_menge(txid):
    return _kraken.gefuellte_menge(txid)


def letzter_kurs(paar):
    return _kraken.letzter_kurs(paar)


def preis_gerundet(paar, preis, richtung="auf"):
    return _kraken.preis_gerundet(paar, preis, richtung=richtung)
