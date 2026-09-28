"""Kraken als Orderweg fuer mosaic - dieselbe Oberflaeche wie okx_spot.

WARUM EINE ZWEITE DATEI: mosaic/handeln.py bindet seinen Live-Weg an
Funktionsnamen (`op_kauf`, `op_verkauf`, `op_stop`, ...). Diese Datei stellt
genau diese Namen auf Kraken bereit, damit die Strategie unveraendert bleibt und
nur die Boerse wechselt. Die Bindung passiert in `handeln.py` ueber das Feld
`boerse` der wachen.json.

WAS KRAKEN ANDERS MACHT
  - Der Kurs kommt aus `Ticker` (letzter Handel), die Order aus `AddOrder`.
  - `AddOrder` kennt `validate=true`: eine Order wird dann nur DURCHGERECHNET und
    landet nicht im Buch. kraken.py hat dafuer das Flag `echt`. Hier steht es
    hart auf `echt=True` - diese Datei wird ausschliesslich aus dem Live-Zweig
    aufgerufen, der vorher die ganze Sperrenkette passiert (handel_erlaubt,
    freigabe.erfuellt, Herzschlag, Fenster, Guthaben).
  - Der Notausstieg ist eine echte Stop-Loss-Order im Boersenbuch
    (`ordertype=stop-loss`). Sie ueberlebt einen Neustart des Rechners - eine
    Position, die nur ein laufendes Skript bewacht, ist unbewacht.
  - Kraken hat kein Demo-Konto in diesem Sinn: `demo_modus()` ist immer False.
    (Der Papierlauf von mosaic laeuft ueber den Papierzweig, nicht ueber diese
    Datei.)
  - Die Waehrung des Kontos ist EUR (Kraken-Spot), nicht USDC wie bei OKX.

Paarnamen: Kraken fuehrt BTC/EUR als `XXBTZEUR`, ETH/EUR als `XETHZEUR`,
SOL/EUR als `SOLEUR`. Das steht in der wachen.json (`instrumente`).

Preisregeln: jede Boerse laesst nur eine bestimmte Zahl von Nachkommastellen
zu - Kraken je Paar (pair_decimals: SOLEUR 2, XXBTZEUR 1), OKX je Instrument
(tickSz). `kraken.stop_setzen` rundet den Stop-Preis ueber
`kraken.preis_gerundet` auf, `mosaic/okx_spot.algo_stop_setzen` ueber sein
eigenes `preis_gerundet`. Ein roher Rechenwert wird abgelehnt ("SOL/EUR price
can only be specified up to 2 decimals"), und dann fehlt der Notausstieg
(22.09.2026: Position wurde zurueckverkauft).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent

# kraken.py ueber den PFAD laden, nicht ueber sys.path: ein Eintrag auf
# Handel/kraken/ koennte gleichnamige Module verdecken (dieselbe Falle wie bei
# ratschen.py).
_PFAD = HANDEL / "kraken" / "kraken.py"
_spec = importlib.util.spec_from_file_location("mosaic_kraken", _PFAD)
kraken = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kraken)

# EINE Paar-Tabelle fuer alle Kraken-Nutzer im Haus. Die Quote ist eine
# Konfigurationsfrage (wachen: "kraken_quote", EUR ist Vorgabe) - EUR und USDC
# sind beide geprueft. Ohne setze_quote() bleibt es bei EUR, also beim alten
# Verhalten.
_kp_spec = importlib.util.spec_from_file_location(
    "kraken_paare", HANDEL / "kraken_paare.py")
kraken_paare = importlib.util.module_from_spec(_kp_spec)
_kp_spec.loader.exec_module(kraken_paare)

QUOTE = "EUR"


def setze_quote(quote):
    """Quote dieser Spur setzen ('EUR'/'USDC'). Unbekannt = ValueError."""
    global QUOTE
    QUOTE = kraken_paare.quote_aus_wachen({"kraken_quote": quote})
    return QUOTE


# --- Paar-Abbildung ---------------------------------------------------------
#
# mosaic rechnet in OKX-Namen (BTC-USDC, ETH-USDC, SOL-USDC); Kraken fuehrt
# dieselben Maerkte unter eigenen Namen (XXBTZEUR, XETHZEUR, SOLEUR), und zwar
# gegen EUR, weil das Kraken-Konto in EUR rechnet. Die Abbildung steht EINMAL
# hier: die Strategie, ihr Buch und ihre Kerzen bleiben unveraendert, nur die
# Order geht an die andere Boerse. Ein unbekanntes Paar ist ein Fehler und keine
# stille Ersatzwahl - sonst landet eine Order im falschen Markt.
PAARE = {
    "BTC-USDC": "XXBTZEUR",
    "BTC-USDT": "XXBTZEUR",
    "ETH-USDC": "XETHZEUR",
    "ETH-USDT": "XETHZEUR",
    "SOL-USDC": "SOLEUR",
    "SOL-USDT": "SOLEUR",
    # Listing-Arb-Paare (moondev_listingarb, 22.09.2026):
    # Kraken fuehrt diese Coins gegen EUR mit eigenen Kurzbezeichnungen.
    # Quelle: GET /0/public/AssetPairs, geprueft am 22.09.2026.
    "AKE-EUR":  "AKEEUR",
    "DAI-EUR":  "DAIEUR",
    "HYPE-EUR": "HYPEEUR",
    "KAS-EUR":  "KASEUR",
    "LIT-EUR":  "LITEUR",
    "MNT-EUR":  "MNTEUR",
    "VVV-EUR":  "VVVEUR",
    "WBT-EUR":  "WBTEUR",
    "XMR-EUR":  "XXMRZEUR",  # Kraken-Sonderform: X-Prefix + Z-Quote
}


def paar_fuer(inst):
    """Kraken-Paar zu einem OKX-Instrument. Unbekannt = klarer Fehler.

    Mit der Quote EUR (Vorgabe) gilt zuerst die Tabelle unten - sie traegt die
    Listing-Arb-Sonderfaelle - und danach die gemeinsame Tabelle. Mit einer
    anderen Quote (USDC) gilt NUR die gemeinsame Tabelle: ein USDC-Lauf darf
    nie still in einem EUR-Markt landen.
    """
    schluessel = str(inst).strip().upper()
    if QUOTE != "EUR":
        return kraken_paare.paar_fuer(schluessel, QUOTE)
    name = PAARE.get(schluessel)
    if name:
        return name
    try:
        return kraken_paare.paar_fuer(schluessel, QUOTE)
    except ValueError:
        raise ValueError("kein Kraken-Paar fuer %s hinterlegt (PAARE in "
                         "mosaic/kraken_spot.py, kraken_paare.PAARE)" % inst)


# --- Schluessel und Modus ---------------------------------------------------

def schluessel_vorhanden() -> bool:
    return bool(kraken.schluessel_vorhanden())


def demo_modus() -> bool:
    """Kraken hat kein Demo-Konto - der Papierlauf laeuft ueber den Papierzweig."""
    return False


# --- Kurse und Mengen -------------------------------------------------------

def letzter_kurs(inst):
    return float(kraken.letzter_kurs(paar_fuer(inst)))


def menge_fuer(inst, betrag, kurs, paar=None):
    """Menge zu einem Betrag in der Kontowaehrung - mit den Handelsregeln des
    Paares. Rueckgabe (menge, fehler): fehler ist None, wenn die Order
    durchgeht; sonst der Grund (Mindestmenge/Mindestwert), damit der Aufrufer
    NICHT raten muss."""
    kpaar = paar or paar_fuer(inst)
    info = kraken.paar_info(kpaar)
    if not kurs:
        return 0.0, "kein Kurs"
    roh = float(betrag) / float(kurs)
    stellen = info["mengen_stellen"]
    menge = float(("%%.%df" % stellen) % roh)
    if menge <= 0:
        return 0.0, "Betrag zu klein fuer %s" % info["name"]
    if info["mindestmenge"] and menge < info["mindestmenge"]:
        # Kein %-Operator hinter .format(): die Vorlage wird EINMAL gefuellt.
        return 0.0, ("%.{0}f unter der Mindestmenge {1:.8g} von {2}".format(
            stellen, menge, info["mindestmenge"]) + " (%s)" % info["name"])
    wert = menge * float(kurs)
    if info["mindestwert"] and wert < info["mindestwert"]:
        return 0.0, ("%.2f unter dem Mindestwert %.2f von %s"
                     % (wert, info["mindestwert"], info["name"]))
    return menge, None


def guthaben_waehrung(ccy="EUR"):
    """Freies Guthaben der Handelswaehrung. Kraken fuehrt EUR als ZEUR."""
    name = {"EUR": "ZEUR", "USD": "ZUSD", "USDC": "USDC", "BTC": "XXBT"}.get(ccy, ccy)
    return float(kraken.guthaben(name))


# --- Ordern (nur Live-Zweig) ------------------------------------------------

def markt_kauf(inst, menge):
    return kraken.markt_kauf(paar_fuer(inst), menge, echt=True)


def markt_verkauf(inst, menge):
    return kraken.markt_verkauf(paar_fuer(inst), menge, echt=True)


def algo_stop_setzen(inst, menge, seite, trigger):
    """Notausstieg als Stop-Loss im Boersenbuch (ueberlebt Neustarts)."""
    if seite not in ("long", "short"):
        raise ValueError("seite muss long oder short sein")
    if seite == "short":
        raise ValueError("Kraken-Spot kennt keinen Short-Notausstieg hier")
    return kraken.stop_setzen(paar_fuer(inst), menge, trigger, echt=True)


def algo_stornieren(inst, algo_id):
    return kraken.order_stornieren(algo_id)


def gefuellte_menge(inst, ord_id):
    return float(kraken.gefuellte_menge(ord_id))
