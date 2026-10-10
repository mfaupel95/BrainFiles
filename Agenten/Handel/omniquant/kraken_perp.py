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
Omniquant fuehrt OKX-Namen, Kraken Futures PF_-Namen - und zwei der Basen
tragen dort einen ANDEREN Namen: BTC wird zu XBT gefuehrt, CT (Bestaendigen)
zu CTSI. Beide Umbenennungen sind am 05.10.2026 gemessen und unten als
gepruefte Tabelleneintraege eingetragen; **XMSTR und MAGIC haben keinen
PF_-Markt** und werden mit einem lauten Fehler abgewiesen - nie still
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

    # --- GEMESSENE BASIS-UMBENENNUNGEN (05.10.2026, Auftrag Max
    #     "dann auf kraken anbinden") --------------------------------
    # Zwei Omniquant-Basen tragen am Zielmarkt einen ANDEREN Namen.
    # Ohne diese Zeilen baute `ableitung()` ein Symbol, das es nicht
    # gibt, und die Spur meldete "gibt es am Zielmarkt nicht" fuer ein
    # Instrument, das sehr wohl handelbar ist - ein toter Markt im
    # Haus sieht genauso aus wie ein echter Fehlstand.
    #
    # Belege (GET /derivatives/api/v3/instruments, 204 tradeable
    # PF_-Maerkte, 05.10.2026):
    #     PF_BTCUSD  -> nicht vorhanden;  PF_XBTUSD   -> vorhanden
    #     PF_CTUSD   -> nicht vorhanden;  PF_CTSIUSD  -> vorhanden
    # Kraken schreibt Bitcoin XBT (Hausregel: XBT ist BTC). "CT" ist
    # die OKX-Schreibweise von CTSI, dem Bestaendigen-Ableger.
    #
    # Es sind bewusst GEPRUEFTE Tabelleneintraege und kein Sonderfall
    # im Code: ein Eintrag umgeht weder die Marktliste noch das Tor
    # `live_pf_ableitung` - er beantwortet nur die Frage "welches
    # Symbol", mit einer geprueften Antwort statt einer abgeleiteten.
    "BTC-USDC": "PF_XBTUSD",
    "BTC-USDT": "PF_XBTUSD",
    "CT-USDC": "PF_CTSIUSD",
    "CT-USDT": "PF_CTSIUSD",
}

# Ohne PF_-Markt - namentlich, damit der Fehler den Grund nennt statt "unbekannt".
# GEMESSEN am 05.10.2026: weder PF_MAGICUSD noch PF_XMSTRUSD stehen in
# der Marktliste (204 tradeable Maerkte). Beide bleiben deshalb laut
# Papier - eine stille Ersatzbasis waere ein Handel im falschen Markt.
KEIN_MARKT = {
    "MAGIC-USDC", "MAGIC-USDT",
    "XMSTR-USDC", "XMSTR-USDT",
}

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


def pf_markt(inst, fuer_ausstieg=False):
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
            "bleibt Papier (gemessen 05.10.2026 gegen /instruments)" % name)
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
        if not (ABLEITUNG_ERLAUBT or fuer_ausstieg):
            # WICHTIG: `fuer_ausstieg` hebt NUR die Freigabepflicht auf, NICHT
            # die Pruefung gegen /instruments. Das Gate `live_pf_ableitung`
            # gilt fuer den EINSTIEG ("die Ableitung kostet echtes Geld bei
            # einem Instrument, das der Mensch nie gesehen hat"). Eine bereits
            # OFFENE Position muss sich aber jederzeit schliessen lassen -
            # am 01.10.2026 stand eine Live-Position 2 Stunden da, weil der
            # Ausstieg am selben Gate scheiterte, das nur den Einstieg sperren
            # soll (T-306).
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


def letzter_kurs(inst, fuer_ausstieg=False):
    return _kf().letzter_kurs(paar_fuer(inst, fuer_ausstieg))


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


def markt_verkauf(inst, kontrakte, fuer_ausstieg=True):
    """Verkauf. VORGABE: das Gate wird umgangen - ein Ausstieg ist nie eine
    neue Marktwahl (T-306)."""
    return _kf().markt_verkauf(paar_fuer(inst, fuer_ausstieg), kontrakte, echt=True)


def stop_setzen(inst, kontrakte, stop_preis, fuer_ausstieg=True):
    """Schutz-Stop setzen. VORGABE: das Gate wird umgangen - ein Nachsatz
    fuer eine OFFENE Position ist nie eine neue Marktwahl (T-306). Ohne
    `fuer_ausstieg` wuerde eine abgeleitete Position (z. B. NEAR-USDC) ihren
    Notausstieg nicht nachsetzen koennen, sobald der Prozess neu startet
    (ABLEITUNG_ERLAUBT ist prozesslokal und nur beim Einstieg gesetzt)."""
    return _kf().stop_setzen(paar_fuer(inst, fuer_ausstieg), kontrakte, stop_preis, echt=True)


def offene_positionen(inst=None, fuer_ausstieg=True):
    """Was die BOERSE fuehrt. Umgeht das Einstiegs-Gate - Abgleich und
    Rueckdrehung duerfen nie an einem Ausstiegs-Gate scheitern (T-306)."""
    return _kf().offene_positionen(paar_fuer(inst, fuer_ausstieg) if inst else None)


def offene_auftraege(inst=None, fuer_ausstieg=True):
    """Offene Orders der BOERSE (Endpoint `/openorders`).

    GEMESSEN 05.10.2026, 1:20 Uhr: der Schutz-Stop der ersten echten
    NEAR-Position war an der Boerse vorhanden - `PF_NEARUSD sell 61
    @ 4.2856, reduceOnly=true` - aber ueber `/editorder` NICHT lesbar.
    `/editorder` ist der SPOT-Endpunkt und antwortet in jeder Variante
    (ohne Parameter, mit `orderStatus`, mit `symbol`, als GET mit Query
    und als POST mit Koerper) mit `requiredArgumentMissing`. Der
    Futures-Dienst nennt den Weg `/openorders`, und
    `kraken_futures.offene_orders()` kannte ihn die ganze Zeit - es
    fehlte nur die Durchreiche an dieser Spur.

    Deshalb steht der Unterschied hier, damit ihn niemand zum dritten
    Mal sucht: **`/openorders`, nicht `/editorder`**.

    Rueckgabe: die rohen Order-Dicts (`symbol`, `side`, `orderType`,
    `unfilledSize`/`size`, `stopPrice`, `reduceOnly`, `order_id`).
    """
    return _kf().offene_orders(paar_fuer(inst, fuer_ausstieg) if inst else None)


def schutzstop_vorhanden(inst, kontrakte=None, fuer_ausstieg=True):
    """Deckt die offene Position eines Symbols ein SCHUTZ-Stop? (bool)

    Ein Long braucht einen `sell`, ein Short einen `buy`, und es muss
    `reduceOnly` sein - eine Order, die eroeffnen kann, schuetzt nicht.
    Zusaetzlich zaehlt die MENGE: T-323 belegte, dass eine Position mit
    145 Kontrakten und einem Stop ueber 126 Kontrakte an der Boerse
    19 Kontrakte ungeschuetzt laesst, ohne dass irgendein Abruf das
    anzeigt. Deshalb wird hier die MENGE verglichen und nicht nur
    "irgendein Treffer" gezaehlt.

    `kontrakte=None` vergleicht nur Seite und reduceOnly - das ist die
    schwache Form und sie wird im Bericht als solche benannt.
    """
    symbol = paar_fuer(inst, fuer_ausstieg)
    try:
        pos = _kf().offene_positionen(symbol)
    except Exception:                                         # noqa: BLE001
        return False
    seite_long = True
    for p in (pos or []):
        if str(p.get("side", "")).lower() == "short":
            seite_long = False
    gewuenschte_seite = "sell" if seite_long else "buy"
    gedeckt = 0.0
    try:
        orders = _kf().offene_orders(symbol)
    except Exception:                                         # noqa: BLE001
        return False
    for o in orders or []:
        if str(o.get("side", "")).lower() != gewuenschte_seite:
            continue
        if o.get("reduceOnly") not in (True, "true", "True"):
            continue
        typ = str(o.get("orderType", "")).lower()
        # Als Schutz zaehlt ein Stop oder ein TP mit Stoppreis. Ein
        # reines Limit ohne Stoppreis schuetzt nicht.
        if typ not in ("stop", "stp", "take_profit") and not o.get("stopPrice"):
            continue
        gedeckt += float(o.get("unfilledSize") or o.get("size") or 0)
    if kontrakte is None:
        return gedeckt > 0
    return gedeckt + 1e-9 >= float(kontrakte)


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