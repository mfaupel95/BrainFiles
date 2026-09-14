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
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

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
    return bool(_variable("KRAKEN_API_KEY") and _variable("KRAKEN_API_SECRET"))


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
    schluessel = _variable("KRAKEN_API_KEY")
    geheim = _variable("KRAKEN_API_SECRET")
    if not (schluessel and geheim):
        raise RuntimeError("KRAKEN_API_KEY / KRAKEN_API_SECRET fehlen")

    pfad = "/0/private/%s" % methode
    daten = {"nonce": str(int(time.time() * 1_000_000))}
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
            print("  Kraken-Transportfehler %d/%d: %s" % (fehler, MAX_FEHLER, e),
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

def guthaben(waehrung="ZEUR"):
    d = _mit_wiederholung(_roh_privat, "Balance")
    return float(d.get(waehrung, 0.0) or 0.0)


def _add_order(paar, seite, menge, ordertyp="market", preis=None, echt=False):
    """Eine Order. echt=False laesst Kraken sie nur durchrechnen (validate) -
    sie landet dann nicht im Buch. handeln.py setzt echt=True ausschliesslich
    im Live-Zweig, wenn alle Sperren offen sind."""
    p = {"pair": paar, "type": seite, "ordertype": ordertyp,
         "volume": ("%.10f" % menge).rstrip("0").rstrip(".")}
    if preis is not None:
        p["price"] = str(preis)
    if not echt:
        p["validate"] = "true"
    d = _roh_privat("AddOrder", **p)
    txids = d.get("txid") or []
    return txids[0] if txids else None


def markt_kauf(paar, menge, echt=False):
    return _add_order(paar, "buy", menge, "market", echt=echt)


def markt_verkauf(paar, menge, echt=False):
    return _add_order(paar, "sell", menge, "market", echt=echt)


def stop_setzen(paar, menge, stop_preis, echt=False):
    """Notausstieg als Stop-Loss-Order im Buch. Sie ueberlebt einen Neustart
    des Rechners - das ist der Sinn: eine Position, die nur ein laufendes
    Skript bewacht, ist unbewacht (Bedingung 3)."""
    return _add_order(paar, "sell", menge, "stop-loss", preis=stop_preis,
                      echt=echt)


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


def gefuellte_menge(txid):
    """Wieviel wurde tatsaechlich ausgefuehrt? vol_exec, nicht vol - eine
    teilweise gefuellte Order verkauft sonst mehr, als sie gekauft hat."""
    return float(order_details(txid).get("vol_exec", 0) or 0)


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
