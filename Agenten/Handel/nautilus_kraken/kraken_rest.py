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
KRAKEN_PY = os.path.join(HIER, os.pardir, "kraken", "kraken.py")


def _lade_kraken():
    spec = importlib.util.spec_from_file_location("kraken_rest_quelle", KRAKEN_PY)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_kraken = _lade_kraken()


def schluessel_vorhanden():
    """Hat der Key Trade-Permission? (Kraken: schluessel_vorhanden)."""
    return _kraken.schluessel_vorhanden()


def guthaben(waehrung="ZEUR"):
    return _kraken.guthaben(waehrung)


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
