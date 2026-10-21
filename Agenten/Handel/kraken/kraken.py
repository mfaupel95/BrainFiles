"""Zugang zu Kraken - oeffentliche Kursdaten und (optional) signierte Orders.

Vorbild und Gegenstueck: scanner/okx.py. Gleiche Aufgabenteilung, andere
Boerse. Nur Standardbibliothek, damit dieser Ordner kein eigenes .venv
braucht.

Diese Datei ist NICHT der Kraken-MCP-Server. Der liegt unter
../../MCP-Server/kraken/ und bleibt lesend: seine beiden schreibenden
Werkzeuge sind in Wissen/Handelsregeln.md ausdruecklich verboten, weil eine
Chat-Sitzung keine Wachen mitbringt. Die Order der dritten Spur laeuft
ausschliesslich hier durch - durch ein Skript, das wachen.json liest, ein
Journal schreibt und einen Herzschlag hinterlaesst.

Drei Fallen, aus MCP-Server/kraken/README.md:
  - Der Secret ist base64-kodiert und muss vor dem HMAC dekodiert werden.
    Sonst antwortet Kraken "Invalid key" - was wie ein falscher Schluessel
    aussieht und keiner ist.
  - "EGeneral:Permission denied" heisst: dem Schluessel fehlt ein Recht.
  - Die Nonce muss je Schluessel streng steigen. Hier Mikrosekunden. Laeuft
    gleichzeitig der MCP-Server mit demselben Schluessel, kann es trotzdem
    klemmen - dann den Lauf wiederholen, nicht den Schluessel tauschen.

Kein Auszahlungsweg. Es gibt hier keine Funktion dafuer, und der Schluessel
hat das Recht "Withdraw Funds" bewusst nicht.
"""

import base64
import hashlib
import hmac
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Gemeinsamer nonce-Pool mit dem Kraken-MCP-Server (siehe Modul-Docstring).
try:
    from nonce_pool import monotone_nonce as _monotone_nonce
    from nonce_pool import vorwaerts as _vorwaerts
except ImportError:                                   # pragma: no cover
    # Fallback, falls der Ordner nicht im sys.path liegt: gleicher Ordner.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from nonce_pool import monotone_nonce as _monotone_nonce
    from nonce_pool import vorwaerts as _vorwaerts

BASIS = "https://api.kraken.com"
HEADERS = {"User-Agent": "MaxHirn-Handel/1.0"}
MAX_FEHLER = 6


class KrakenFehler(RuntimeError):
    """Fachlicher Fehler aus einer gueltigen Kraken-Antwort (error-Liste).
    Wird NICHT wiederholt - ein unbekanntes Paar existiert beim zehnten
    Versuch auch nicht."""


# --- Schluessel -------------------------------------------------------------

def _aus_registry(name):
    """Der Umweg ueber HKCU\\Environment. Ein von Claude oder einer geplanten
    Aufgabe gestarteter Prozess erbt neu gesetzte Benutzervariablen nicht -
    gemessen 19.08.2026 am MCP-Server."""
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            wert, _ = winreg.QueryValueEx(k, name)
            return str(wert).strip() or None
    except OSError:
        return None


def _variable(name):
    return (os.environ.get(name) or "").strip() or _aus_registry(name)


def schluessel_vorhanden():
    return bool(_variable("KRAKEN_SPOT_API_KEY") and _variable("KRAKEN_SPOT_API_SECRET"))


# --- HTTP ------------------------------------------------------------------

def _auswerten(nutzlast):
    fehler = nutzlast.get("error") or []
    if fehler:
        raise KrakenFehler("Kraken meldet: " + "; ".join(fehler))
    return nutzlast.get("result") or {}


def _roh_oeffentlich(methode, **parameter):
    url = "%s/0/public/%s" % (BASIS, methode)
    if parameter:
        url += "?" + urllib.parse.urlencode(parameter)
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=20) as antwort:
        return _auswerten(json.loads(antwort.read().decode()))


def _roh_privat(methode, **parameter):
    schluessel = _variable("KRAKEN_SPOT_API_KEY")
    geheim = _variable("KRAKEN_SPOT_API_SECRET")
    if not (schluessel and geheim):
        raise RuntimeError("KRAKEN_SPOT_API_KEY / KRAKEN_SPOT_API_SECRET fehlen")

    pfad = "/0/private/%s" % methode

    # "EAPI:Invalid nonce" heisst NICHT, dass unsere nonce nicht steigt: ein
    # fremdes Werkzeug auf demselben Schluessel (die offizielle kraken-cli)
    # setzt einen hoeheren Wert, und Kraken vergleicht gegen den HOECHSTEN.
    # Deshalb bis zu drei Versuche, ab dem zweiten mit vorgeschobenem Zaehler
    # (nonce_pool.vorwaerts schreibt ihn in die gemeinsame Datei, damit die
    # Monotonie erhalten bleibt). Ohne das scheitert JEDER Hausaufruf, bis die
    # Uhr den fremden Wert eingeholt hat - genau der Ausfall vom 22.09.2026.
    letzter_fehler = None
    for versuch in range(3):
        if versuch == 0:
            nonce = _monotone_nonce()
        else:
            nonce = _vorwaerts(versuch)
        daten = {"nonce": str(nonce)}
        daten.update({k: v for k, v in parameter.items() if v is not None})
        formular = urllib.parse.urlencode(daten)

        roh = (daten["nonce"] + formular).encode()
        nachricht = pfad.encode() + hashlib.sha256(roh).digest()
        sig = base64.b64encode(
            hmac.new(base64.b64decode(geheim), nachricht, hashlib.sha512).digest()
        ).decode()

        kopf = dict(HEADERS)
        kopf.update({"API-Key": schluessel, "API-Sign": sig,
                     "Content-Type": "application/x-www-form-urlencoded"})
        req = urllib.request.Request(BASIS + pfad, data=formular.encode(),
                                     headers=kopf, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as antwort:
                return _auswerten(json.loads(antwort.read().decode()))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise KrakenFehler("Kraken HTTP %d auf signierte Abfrage - "
                                   "Schluessel/Rechte pruefen" % e.code) from None
            raise
        except KrakenFehler as e:
            if "Invalid nonce" not in str(e) or versuch == 2:
                raise
            letzter_fehler = e
    raise letzter_fehler


def _mit_wiederholung(fn, *a, **kw):
    fehler = 0
    while True:
        try:
            return fn(*a, **kw)
        except KrakenFehler:
            raise                      # fachlich, heilt kein Wiederholen
        except Exception as e:  # noqa: BLE001 - Transportfehler, wird gezaehlt
            fehler += 1
            if fehler >= MAX_FEHLER:
                raise
            print("  Kraken-Transportfehler %d/%d: %s - wird wiederholt, kein Ausfall"
                  % (fehler, MAX_FEHLER, e),
                  file=sys.stderr)
            time.sleep(1.5 * fehler)


# --- oeffentlich -----------------------------------------------------------

def _erste_reihe(ergebnis, paar):
    """Kraken antwortet unter dem kanonischen Paarnamen, nicht unter dem
    angefragten (XBTEUR -> XXBTZEUR). Deshalb nie ueber den Schluessel
    zugreifen, sondern den einzigen Eintrag nehmen."""
    for name, wert in ergebnis.items():
        if name != "last":
            return wert
    raise KrakenFehler("Kraken lieferte nichts zu %s" % paar)


def kerzen(paar, intervall=1440, anzahl=720):
    """OHLC, aufsteigend, als [ts_ms, open, high, low, close, vol] - dasselbe
    Format wie okx.kerzen, damit bewertung.py beide Boersen bewerten kann.

    Kraken liefert je Abruf hoechstens 720 Kerzen. Fuer Tageskerzen reicht
    das (rund zwei Jahre)."""
    roh = _mit_wiederholung(_roh_oeffentlich, "OHLC", pair=paar,
                            interval=intervall)
    reihen = [[int(r[0]) * 1000] + [float(x) for x in (r[1], r[2], r[3], r[4], r[6])]
              for r in _erste_reihe(roh, paar)]
    reihen.sort(key=lambda r: r[0])
    return reihen[-anzahl:]


def letzter_kurs(paar):
    d = _mit_wiederholung(_roh_oeffentlich, "Ticker", pair=paar)
    return float(_erste_reihe(d, paar)["c"][0])


def paar_info(paar):
    """Die Handelsregeln des Paares: Nachkommastellen fuer Preis und Menge,
    Mindestmenge, Mindestwert. Ohne sie wird eine Order abgelehnt oder still
    gerundet."""
    d = _mit_wiederholung(_roh_oeffentlich, "AssetPairs", pair=paar)
    w = _erste_reihe(d, paar)
    return {
        "name": w.get("altname"),
        "preis_stellen": int(w.get("pair_decimals", 5)),
        "mengen_stellen": int(w.get("lot_decimals", 8)),
        "mindestmenge": float(w.get("ordermin", 0) or 0),
        "mindestwert": float(w.get("costmin", 0) or 0),
        "gegen": w.get("quote"),
    }


# --- signiert (nur mit Schluessel + --live) --------------------------------

def kontostaende():
    """Alle Kontostaende in EINEM Abruf - Schluessel sind die Kraken-Codes
    ('ZEUR', 'USDC', 'XXBT').

    Ein Abruf fuer alle Waehrungen, nicht je Waehrung einer: Kraken kann
    zwischen zwei Aufrufen anders antworten, und das Guthaben-Tor einer Spur
    mit drei Quotewaehrungen wuerde sonst drei verschiedene Staende
    vergleichen. Die Quote aus AssetPairs ist nicht immer derselbe Schluessel
    - siehe quote.guthaben_asset()."""
    return _mit_wiederholung(_roh_privat, "Balance") or {}


def guthaben(waehrung="ZEUR"):
    return float(kontostaende().get(waehrung, 0.0) or 0.0)


def _add_order(paar, seite, menge, ordertyp="market", preis=None, echt=False,
               **zusatz):
    """Eine Order. echt=False laesst Kraken sie nur durchrechnen (validate) -
    sie landet dann nicht im Buch. handeln.py setzt echt=True ausschliesslich
    im Live-Zweig, wenn alle Sperren offen sind."""
    p = {"pair": paar, "type": seite, "ordertype": ordertyp,
         "volume": ("%.10f" % menge).rstrip("0").rstrip(".")}
    if preis is not None:
        p["price"] = str(preis)
    if not echt:
        p["validate"] = "true"
    p.update(zusatz)          # z.B. leverage, close[ordertxid]
    d = _roh_privat("AddOrder", **p)
    txids = d.get("txid") or []
    return txids[0] if txids else None


def markt_kauf(paar, menge, echt=False):
    return _add_order(paar, "buy", menge, "market", echt=echt)


def markt_verkauf(paar, menge, echt=False):
    return _add_order(paar, "sell", menge, "market", echt=echt)


def preis_gerundet(paar, preis, richtung="auf"):
    """Einen Preis auf die Nachkommastellen DIESES Paares bringen.

    Kraken lehnt eine Order ab, deren Preis mehr Stellen hat als das Paar
    zulaesst - "EOrder:Invalid price:SOL/EUR price can only be specified up to
    2 decimals" (gemessen 22.09.2026 an einem Stop auf SOLEUR). Die Order wird
    dabei nicht teilweise ausgefuehrt, sie kommt gar nicht zustande: der
    Notausstieg fehlt dann komplett, und die Spur verkauft die frisch gekaufte
    Position sofort wieder zurueck (Spesen ohne Handel).

    Die Stellenzahl ist JE PAAR verschieden (AssetPairs.pair_decimals, am
    22.09.2026 geprueft: SOLEUR/XETHZEUR 2, XXBTZEUR 1, AKEEUR 8, KASEUR 5) -
    ein fester Formatstring waere fuer jedes andere Paar falsch.

    richtung "auf": der Stop eines LONG wird aufgerundet und liegt damit nie
    TIEFER als gerechnet - das Risiko wird nicht groesser als die Wache
    erlaubt. "ab" ist die Gegenrichtung (Stop eines Short).
    """
    if richtung not in ("auf", "ab"):
        raise ValueError("richtung muss 'auf' oder 'ab' sein")
    stellen = paar_info(paar).get("preis_stellen")
    if stellen is None:
        # Attrappe ohne Preisregeln (Tests): nicht raten, roh weitergeben.
        return str(preis)
    faktor = 10 ** int(stellen)
    # round() vor ceil/floor: 128.995 * 100 ist binaer 12899.499999999998.
    x = round(float(preis) * faktor, 6)
    ganz = math.ceil(x) if richtung == "auf" else math.floor(x)
    # Fertig formatiert zurueckgeben: str(float) wuerde kleine Werte als
    # "1e-08" schreiben, was Kraken ebenfalls ablehnt.
    return "%.*f" % (int(stellen), ganz / faktor)


def stop_setzen(paar, menge, stop_preis, echt=False, leverage=None,
                close_txid=None):
    """Stop-Loss setzen. Fuer eine MARGIN-Position mit close_txid verknuepft.

    close_txid ist die ordertxid der offenen Position (aus OpenPositions). Kraken
    haengt die Order dann an DIESE Position ('close position @ stop loss ...') -
    wird die Position von Hand geschlossen, verschwindet auch der Stop. Ohne die
    Verknuepfung bliebe ein nackter Verkaufsstop stehen, der bei fehlender
    Position einen SHORT eroeffnen wuerde.
    """
    preis = preis_gerundet(paar, stop_preis, "auf")
    felder = {}
    if leverage is not None:
        felder["leverage"] = str(leverage)
    if close_txid:
        felder["close[ordertxid]"] = close_txid
        felder["close[ordertype]"] = "stop-loss"
        felder["close[price]"] = preis
    return _add_order(paar, "sell", menge, "stop-loss", preis=preis,
                      echt=echt, **felder)


def take_profit_setzen(paar, menge, tp_preis, echt=False, leverage=None,
                   close_txid=None):
    """Take-Profit (Ziel) setzen - eine VERKAUFS-Triggerorder (take-profit-market).

    Long-only wie stop_setzen: Kraken-Spot kann kein Short halten, das Ziel
    eines Long ist immer ein Verkauf. `take-profit-market` loest eine
    MARKET-ORDER aus, sobald der letzte Handelspreis den triggenden
    `tp_preis` erreicht - anders als ein Limit raeumt es damit die Position
    garantiert ab (das Ziel soll raus, kein Rest bleiben). Wird der Trigger
    aufgerundet (preis_gerundet richtung='auf'), triggert die Order fruehestens
    beim Ziel - nie davor, das Risiko wird nicht kleiner verkauft als gerechnet.

    Euristisch identisch zu stop_setzen: preis_gerundet, _add_order, und
    close_txid fuer eine MARGIN-Position. echt=False laesst Kraken die Order
    nur durchrechnen (validate) - sie landet nicht im Buch.
    """
    preis = preis_gerundet(paar, tp_preis, "auf")
    felder = {}
    if leverage is not None:
        felder["leverage"] = str(leverage)
    if close_txid:
        felder["close[ordertxid]"] = close_txid
        felder["close[ordertype]"] = "take-profit-market"
        felder["close[price]"] = preis
    return _add_order(paar, "sell", menge, "take-profit-market", preis=preis,
                      echt=echt, **felder)


def offene_orders():
    """Alle offenen Orders des Kontos (lesend, /0/private/OpenOrders).

    Gebraucht wird das fuer den Abgleich BUCH <-> BOERSE: eine Position, die an
    der Boerse einen Schutz-Stop hat, aber im Buch keine Kennung traegt, laesst
    sich spaeter nicht mehr adressieren (der scanner hatte genau so 23 Kopien
    desselben Stops im Zustand, siehe scanner/stops_bereinigen.py).
    Rueckgabe: {ordertxid: {paar, seite, art, menge, preis, eroeffnet}}.
    """
    ergebnis = _mit_wiederholung(_roh_privat, "OpenOrders") or {}
    aus = {}
    for txid, o in (ergebnis.get("open") or {}).items():
        d = o.get("descr") or {}
        aus[txid] = {"paar": d.get("pair"), "seite": d.get("type"),
                     "art": d.get("ordertype"), "menge": o.get("vol"),
                     "preis": d.get("price"), "eroeffnet": o.get("opentm"),
                     "beschreibung": d.get("order")}
    return aus


def stop_gefuellt(txid):
    """Hat der Boersen-Stop schon verkauft?

    Kraken meldet eine ausgeloeste Stop-Loss-Order als status "closed" mit
    vol_exec > 0. Genau daran erkennt handeln.py eine Position, die am Markt
    weg ist, im eigenen Buch aber noch steht.
    """
    if not txid:
        return False
    return float(order_details(txid).get("vol_exec") or 0) > 0


def order_stornieren(txid):
    return _roh_privat("CancelOrder", txid=txid)


def order_details(txid):
    d = _mit_wiederholung(_roh_privat, "QueryOrders", txid=txid)
    return d.get(txid, {})


def gefuellte_menge(txid, standard=0.0):
    """Wieviel wurde tatsaechlich ausgefuehrt? vol_exec, nicht vol - eine
    teilweise gefuellte Order verkauft sonst mehr, als sie gekauft hat.

    `standard` gilt fuer den Fall, dass Kraken die Kennung (noch) NICHT kennt:
    QueryOrders antwortet dann ohne Eintrag. Das ist NICHT dasselbe wie
    "0 ausgefuehrt" - bis zum 30.09.2026 las der Aufrufer beides als 0, buchte
    eine gefuellte Order deshalb nicht, und die Spur kaufte denselben Wert im
    naechsten Zyklus erneut (T-102: FILEUR viermal, ~200 EUR fuer EIN Signal).
    Wer den Unterschied braucht, setzt standard=None.
    """
    d = order_details(txid)
    if not d:
        return standard
    return float(d.get("vol_exec", 0) or 0)


def fuellung_abwarten(txid, sekunden=30.0, abstand=3.0):
    """Auf die Fuellung warten. Gibt (menge, bestaetigt) zurueck.

    bestaetigt=False heisst: innerhalb von `sekunden` war keine ausgefuehrte
    Menge zu sehen - die Boerse kennt die Kennung noch nicht oder die Order ist
    noch offen. WICHTIG: eine Order MIT Kennung existiert, das Geld ist
    gebunden. Der Aufrufer darf daraus nicht "kein Kauf" machen; er bucht die
    BESTELLTE Menge und merkt sie als unbestaetigt.
    """
    ende = time.time() + max(0.0, sekunden)
    while True:
        try:
            menge = gefuellte_menge(txid, standard=None)
        except Exception as e:                                     # noqa: BLE001
            print("  Fuellungsabfrage fehlgeschlagen: %s" % e, file=sys.stderr)
            menge = None
        if menge and menge > 0:
            return float(menge), True
        if time.time() >= ende:
            return float(menge or 0.0), False
        time.sleep(abstand)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    paar = sys.argv[1] if len(sys.argv) > 1 else "XXBTZEUR"
    k = kerzen(paar)
    print("%s: %d Tageskerzen, %s bis %s" % (
        paar, len(k),
        time.strftime("%Y-%m-%d", time.localtime(k[0][0] / 1000)),
        time.strftime("%Y-%m-%d", time.localtime(k[-1][0] / 1000))))
    print("letzter Schluss: %.6g" % k[-1][4])
    print("Paar-Info: %s" % paar_info(paar))
    print("Schluessel gesetzt:", schluessel_vorhanden())
