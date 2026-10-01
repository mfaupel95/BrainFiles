"""Omniquants Orderweg auf Kraken FUTURES (PF_-Maerkte), Hebel als Sizing.

Warum dieses Modul
------------------
Bis zum 01.10.2026 hatte omniquant keinen Orderpfad (`--live` verweigerte).
Auftrag Max: "Omniquant Handel Freigabe auf kraken live" - nachgemeldet
"aber mit perp und hebel x6". Damit ist die Zielboerse nicht der Spot-Markt,
sondern Kraken Futures (Dienst https://futures.kraken.com/derivatives/api/v3).

Es baut NICHTS nach: die Signatur, die Nonce, das flex-Konto und die
Kontraktgroesse liegen in `nautilus_kraken/kraken_futures.py` - hier steht nur
die Uebersetzung Omniquant-Name -> PF_-Symbol und das Sizing. Geladen wird
ueber den PFAD (die Spur hat ihren eigenen Ordner als sys.path[0], ein
sys.path-Eintrag auf Handel/ koennte gleichnamige Spurenmodule verdecken).

Was GEMESSEN ist (01.10.2026, GET /derivatives/api/v3/instruments)
-----------------------------------------------------------------
Alle PF_-Maerkte tragen `contractSize: 1` - das sagt nichts. Verbindlich ist
die Messung aus kraken_futures.py: **1 Kontrakt = 1 Einheit der Basiswaehrung.**
Neun von Omniquants zehn Instrumenten haben einen PF_-Markt; **MAGIC-USDT hat
keinen** und wird hier mit einem lauten Fehler abgewiesen - nie still
ersatzweise handeln (sonst landet die Order im falschen Markt).

Was HEBEL hier heisst
---------------------
Kraken Futures kennt keinen Hebel-Schalter je Order: der Einschuss ist der
Margenplan des Marktes (EEA retail 10 %). "Hebel x6" ist deshalb eine
SIZING-Regel: der Nennwert ist das Sechsfache des Einsatzes

    nennwert = einsatz_usd * hebel        kontrakte = nennwert / kurs

und die Boerse fordert davon nur ihre 10 % an. Der Rest des Einsatzes bleibt
freie Margin - das ist der Sicherheitspuffer, nicht die Gebuehr. Ein Stop von
x % kostet bei Hebel 6 rund 6x % des Einsatzes; wer den Hebel erhoeht, erhoeht
den Verlust JE POSITION, nicht die Trefferchance.

Aufruf (immer aus dem omniquant-Ordner):
    ../scanner/.venv/Scripts/python.exe -c "import kraken_perp; print(kraken_perp.uebersicht())"
"""

import json
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)

# Omniquant fuehrt OKX-Namen (STRK-USDT). Die Zielboerse fuehrt PF_<BASE>USD.
# Geprueft am 01.10.2026 gegen /instruments (Feld symbol, tradeable).
# MAGIC-USDT fehlt bewusst - kein Markt.
PAARE = {
    "STRK-USDT": "PF_STRKUSD",
    "DOGE-USDT": "PF_DOGEUSD",
    "XRP-USDC": "PF_XRPUSD",
    "XRP-USDT": "PF_XRPUSD",
    "W-USDT": "PF_WUSD",
    "FIL-USDT": "PF_FILUSD",
    "ETC-USDT": "PF_ETCUSD",
    "WLD-USDT": "PF_WLDUSD",
    "ZEC-USDC": "PF_ZECUSD",
    "ZEC-USDT": "PF_ZECUSD",
    "ORDI-USDT": "PF_ORDIUSD",
}

# Ohne PF_-Markt - namentlich, damit der Fehler den Grund nennt statt "unbekannt".
KEIN_MARKT = {"MAGIC-USDT"}

HEBEL_VORGABE = 6.0

# --- Zielmarkt-Auskunft (T-282, 01.10.2026) ---------------------------------
# Die Tabelle oben ist der GEPRUEFTE Kern. Sie ist aber nicht vollstaendig -
# und kann es nicht sein: Omniquants Kandidaten kommen aus dem Prognose-Bericht
# ueber OKX-Paare und koennen jederzeit ein Instrument nennen, das hier noch
# nicht steht. GEMESSEN am 01.10.2026: der weite Bericht lieferte HBAR-USDT und
# ONDO-USDT, BEIDE am Zielmarkt handelbar (PF_HBARUSD, PF_ONDOUSD, gegen
# /instruments geprueft) - nur nicht eingetragen. Folge: jeder Live-Zyklus
# schrieb eine Fehlerzeile "unbekanntes Instrument" und konnte nichts
# eroeffnen, waehrend das Margin-Tor offen war. Dieselbe Klasse wie eine
# "armlose" Live-Spur.
#
# Deshalb wird abgeleitet UND GEPRUEFT: PF_<BASE>USD, nachgeschlagen in der
# Marktliste der Boerse. Drei Regeln:
#   * abgeleitet wird nur, wenn der Name wie <BASE>-<QUOTE> aussieht
#   * ohne Markt in der Liste bleibt es ein lauter Fehler (nie ersatzweise
#     in einen anderen Markt handeln)
#   * die Ableitung ist NICHT von selbst scharf: sie kostet echtes Geld bei
#     einem Instrument, das der Mensch nie gesehen hat. `setze_ableitung()`
#     gibt sie frei, `live_perp.kaufe()` tut das aus wachen.json
#     (`live_pf_ableitung`). Ohne Aufruf gilt der sichere Zustand: aus.
_MARKT_CACHE = None
ABLEITUNG_ERLAUBT = False


def setze_ableitung(erlaubt):
    """Ableitung fremder Instrumente freigeben (nur live_perp, aus den Wachen)."""
    global ABLEITUNG_ERLAUBT
    ABLEITUNG_ERLAUBT = bool(erlaubt)


def merke_maerkte(symbole):
    """Marktliste setzen - die Naht fuer Tests, ohne Netz."""
    global _MARKT_CACHE
    _MARKT_CACHE = set(symbole)


def maerkte():
    """Die zuletzt GELADENE Marktliste (leer, solange nichts geladen ist).

    Bewusst ohne eigene Abfrage: `pf_markt` ist der heisse Pfad jeder
    Instrument-Aufloesung und darf keine Netzfrage ausloesen. Wer die Liste
    braucht, ruft `lade_maerkte()` - das tut der Live-Zweig einmal je Lauf.
    """
    return set(_MARKT_CACHE or ())


def lade_maerkte():
    """Marktliste der Boerse holen und merken. Rueckgabe: Anzahl der Maerkte."""
    global _MARKT_CACHE
    daten = _kf()._roh("/instruments")
    liste = daten.get("instruments") or []
    _MARKT_CACHE = {str(i.get("symbol")) for i in liste
                    if str(i.get("symbol") or "").startswith("PF_")
                    and i.get("tradeable") is not False}
    return len(_MARKT_CACHE)


def ableitung(inst):
    """PF_-Symbol aus einem Omniquant-Namen - ungeprueft, None wenn unbrauchbar."""
    teile = [t for t in str(inst or "").split("-") if t]
    if len(teile) != 2:
        return None
    basis = teile[0].strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{1,12}", basis or ""):
        return None
    return "PF_%sUSD" % basis


def eingetragen(inst):
    """Steht das Instrument in der geprueften Tabelle (ohne Netzfrage)?"""
    return str(inst or "").strip().upper() in PAARE


def _kf():
    """kraken_futures ueber den PFAD laden - nicht per sys.path-Eintrag."""
    from importlib.util import spec_from_file_location, module_from_spec
    datei = os.path.join(HANDEL, "nautilus_kraken", "kraken_futures.py")
    if not os.path.isfile(datei):
        raise RuntimeError("kraken_futures.py nicht gefunden: %s" % datei)
    spec = spec_from_file_location("omniquant_kraken_futures", datei)
    modul = module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def pf_markt(inst):
    """PF_-Symbol zu einem Omniquant-Instrument - oder lauter Fehler.

    Reihenfolge: gepruefte Tabelle -> kein Markt (namentlich) -> Ableitung mit
    Pruefung gegen /instruments. Ein Name, der nirgends passt, ist ein FEHLER
    und keine stille Ersatzwahl (sonst landet eine Order im falschen Markt,
    Hausregel kraken_paare.py).
    """
    name = (inst or "").strip().upper()
    if name in KEIN_MARKT:
        raise ValueError(
            "Kraken Futures fuehrt keinen Markt fuer %s - dieses Instrument "
            "bleibt Papier (gemessen 01.10.2026 gegen /instruments)" % name)
    if name in PAARE:
        return PAARE[name]
    kandidat = ableitung(name)
    if kandidat:
        if not maerkte():
            raise ValueError(
                "unbekanntes Instrument fuer Kraken Futures: %r (Marktliste "
                "nicht geladen - Ableitung moeglich, aber nicht geprueft; "
                "geprueft eingetragen: %s)"
                % (inst, ", ".join(sorted(PAARE))))
        if kandidat not in maerkte():
            raise ValueError(
                "unbekanntes Instrument fuer Kraken Futures: %r (%s gibt es "
                "am Zielmarkt nicht; geprueft eingetragen: %s)"
                % (inst, kandidat, ", ".join(sorted(PAARE))))
        if not ABLEITUNG_ERLAUBT:
            raise ValueError(
                "%s ist am Zielmarkt handelbar (%s, gegen /instruments "
                "geprueft), aber nicht freigegeben: wachen.json "
                "live_pf_ableitung=false" % (name, kandidat))
        return kandidat
    raise ValueError(
        "unbekanntes Instrument fuer Kraken Futures: %r (kein PF_-Markt, "
        "geprueft gegen /instruments; geprueft eingetragen: %s)"
        % (inst, ", ".join(sorted(PAARE))))


# Alter Name bleibt - er steht in jedem Aufrufer dieser Spur.
paar_fuer = pf_markt


def hebel(w):
    """Hebel aus der wachen.json - eine Zahl im Modul waere eine zweite Wahrheit."""
    return float((w or {}).get("hebel", HEBEL_VORGABE))


def einsatz_usd(w, live=False):
    """Einsatz (Margin) je Position. Live liest `live_einsatz_usd`."""
    if live:
        return float(w.get("live_einsatz_usd",
                           w.get("max_einsatz_je_position_usd", 50)))
    return float(w.get("max_einsatz_je_position_usd", 50))


def kontrakte_fuer(inst, einsatz, kurs, w=None):
    """Kontraktzahl fuer einen Einsatz bei gegebenem Hebel.

    nennwert = einsatz * hebel; 1 Kontrakt = 1 Einheit der Basiswaehrung.
    Mindestens 1 Kontrakt - eine 0 waere keine Order (kraken_futures.kontrakte).
    """
    h = hebel(w)
    if kurs <= 0:
        raise ValueError("Kurs muss positiv sein, war %r" % kurs)
    return max(1, int(round(einsatz * h / kurs)))


def nennwert_usd(inst, kontrakte, kurs):
    """Nennwert der Position in USD (kontrakte x kurs, 1 Kontrakt = 1 Einheit)."""
    return float(kontrakte) * float(kurs)


def effektiver_hebel(inst, kontrakte, kurs, einsatz):
    """Was der Hebel WIRKLICH ist, nachdem auf ganze Kontrakte gerundet wurde."""
    if not einsatz:
        return 0.0
    return nennwert_usd(inst, kontrakte, kurs) / float(einsatz)


# Aufrunden auf ganze Kontrakte darf den Hebel nicht sprengen. 25 % Luft, weil
# der Kurs zwischen Sizing und Fuellung laeuft.
HEBEL_TOLERANZ = 1.25


def hebel_grund(inst, einsatz, kurs, w=None):
    """Grund oder None: laesst sich dieser Einsatz bei diesem Hebel abbilden?

    1 Kontrakt ist die kleinste Order. Liegt schon DER ueber dem Hebel-Budget,
    wird gesperrt statt aufgerundet (Hausregel: ein Einsatz unter der
    Mindestmenge des Instruments wird gesperrt). Gemessen am 01.10.2026:
    ZEC kostet 1 Kontrakt = 1436,99 USD Nennwert - bei 50 USD Einsatz also
    Hebel 28,7 statt 6. Ohne diese Sperre waere das die groesste Position im
    Buch und niemand haette es am Hebel gesehen.
    """
    h = hebel(w)
    k = kontrakte_fuer(inst, einsatz, kurs, w)
    ist = effektiver_hebel(inst, k, kurs, einsatz)
    if ist > h * HEBEL_TOLERANZ:
        return ("1 Kontrakt %s ist %.2f USD Nennwert (Hebel %.1f bei %.2f USD "
                "Einsatz) - bei Hebel %g nicht abbildbar"
                % (inst, nennwert_usd(inst, k, kurs), ist, einsatz, h))
    return None


# --- Durchreichen an den Hausweg -------------------------------------------

def schluessel_vorhanden():
    return _kf().schluessel_vorhanden()


def demo_modus():
    """Kraken Futures hat keinen Demo-Schalter (anders als OKX).

    Immer False - der Wert existiert, damit die Sperrenkette dieselbe Form hat
    wie bei den anderen Spuren. Wer hier je True zurueckgibt, muss den Grund
    daneben schreiben.
    """
    return False


def letzter_kurs(inst):
    return _kf().letzter_kurs(paar_fuer(inst))


def guthaben_usd():
    """Freie Margin im Futures-Konto (flex-Konto, availableMargin)."""
    return _kf().guthaben("usd")


def einschuss_usd(inst, kontrakte, kurs=None):
    """Was die BOERSE als Einschuss verlangt (Marktplan, EEA 10 %)."""
    return _kf().einschuss(paar_fuer(inst), kontrakte, kurs)


def handelbar(inst, kontrakte=1, frei=None):
    """(Grund oder None) - reicht die freie Margin fuer diesen Satz?"""
    return _kf().handelbar(paar_fuer(inst), kontrakte, frei)


def markt_kauf(inst, kontrakte):
    """Echter Marktkauf (long). Ohne `echt=True` waere es ein Trockenlauf."""
    return _kf().markt_kauf(paar_fuer(inst), kontrakte, echt=True)


def markt_verkauf(inst, kontrakte):
    return _kf().markt_verkauf(paar_fuer(inst), kontrakte, echt=True)


def stop_setzen(inst, kontrakte, stop_preis):
    return _kf().stop_setzen(paar_fuer(inst), kontrakte, stop_preis, echt=True)


def offene_positionen(inst=None):
    return _kf().offene_positionen(paar_fuer(inst) if inst else None)


def gefuellte_menge(order_id):
    return _kf().gefuellte_menge(order_id)


def preis_gerundet(inst, preis, richtung="auf"):
    return _kf().preis_gerundet(paar_fuer(inst), preis, richtung)


# --- Selbstauskunft ---------------------------------------------------------

def uebersicht(w=None):
    """Was das Modul kann und was es kostet - ohne Order, ohne Schluessel."""
    w = w or {}
    zeilen = ["Omniquant auf Kraken Futures - Hebel %g" % hebel(w),
              "Einsatz je Position: %.2f USD (Papier), live %.2f USD"
              % (einsatz_usd(w, False), einsatz_usd(w, True)),
              ""]
    for inst in sorted(PAARE):
        try:
            kurs = letzter_kurs(inst)
            k = kontrakte_fuer(inst, einsatz_usd(w, True), kurs, w)
            zeilen.append("  %-10s -> %-13s kurs=%-12.6g kontrakte=%-8d "
                          "nennwert=%.2f einschuss=%.2f hebel_ist=%.2f"
                          % (inst, paar_fuer(inst), kurs, k,
                             nennwert_usd(inst, k, kurs),
                             einschuss_usd(inst, k, kurs),
                             effektiver_hebel(inst, k, kurs,
                                              einsatz_usd(w, True))))
        except Exception as e:                       # noqa: BLE001
            zeilen.append("  %-10s FEHLER: %s" % (inst, e))
    for inst in sorted(KEIN_MARKT):
        zeilen.append("  %-10s kein PF_-Markt - bleibt Papier" % inst)
    return "\n".join(zeilen)


if __name__ == "__main__":
    print(uebersicht())
    print()
    print("freie Margin: %.2f USD" % guthaben_usd())