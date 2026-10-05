"""OKX-Futures-Orderweg fuer die Mosaic-Spur (gehebelt).

Schwester von `okx_spot.py`, aber gehebelt. Sie stellt GENAU dieselben
Funktionsnamen bereit, damit `handeln.py` unveraendert bleibt - die BOERSEN-
Tabelle in handeln.py kennt beide Wege und der Rest der Spur merkt keinen
Unterschied.

WARUM EIN EIGENES MODUL und nicht okxf.py von xperp
----------------------------------------------------
xperp/okxf.py ist der volle XPERP-Weg mit Positionen, Wartenden Auftraegen,
Stops in ueber fuenf OrdTypen und Fremdpositionen. Mosaic braucht daraus
fuenf Funktionen. Ein eigener Weg haelt die Mosaic-Regeln (Long-only,
reduceOnly beim Verkauf, Pflicht-Stop in derselben Sekunde) an EINER Datei
und laesst xperp unangetastet - ein Fehler hier faellt nicht auf die Spur mit
81 Runden. Signierung, Takt und Schlüssel holt der Weg UEBER xperp/okxf.py
per Pfad: eine zweite Signatur im Haus waere eine zweite Fehlerquelle.

DIE ZWEI UNTERSCHIEDE, DIE ZAEHLEN
  - `tdMode` ist "isolated", nicht "cash". Kein `posSide`, weil das Konto auf
    `posMode=net_mode` steht (am 05.10.2026 gemessen) - eine posSide-Angabe
    wuerde dort abgelehnt.
  - Mengen sind KONTRAKTE, keine Basiseinheiten. ctVal des XPERP ist
    0.0001 BTC (BTC-USD_UM_XPERP-310404), 0.001 ETH, 0.01 SOL. Ein Kauf ueber
    600 USD Nominal ist bei BTC rund 86 Kontrakte.
  - Der Hebel wird VOR der Order gesetzt und ist ein Deckel, kein Ziel.

HEBEL UND LIQUIDATION
---------------------
`hebel_setzen()` allein reicht nicht: eine gehebelte Position laeuft bis zur
Liquidation, wenn der Rechner ausfaellt (Kernel-Power-41 aus
Wissen/Hardware.md). `stop_vor_liq()` ist deshalb Teil jedeskaufs - es
prueft, ob der Pflicht-Stop VOR der Liquidationsmarke liegt, und verweigert
den Einstieg, wenn nicht. Bei 6x liegt die Liquidation rund 16 % entfernt,
der Stop der Spur 5-12 %: das ist die Rechnung, die vor dem ersten Order
gelaufen sein muss.

Das Modul erfindet kein Signal und hebt keine Grenze. Es kann nur ablehnen.
"""

import math
import os
import sys
import urllib.parse
from importlib.util import module_from_spec, spec_from_file_location

_HIER = os.path.dirname(os.path.abspath(__file__))
_XPERP = os.path.join(os.path.dirname(_HIER), "xperp")

# Schlüssel, HTTP und Takt kommen aus xperp/okxf.py - EINE Signatur im Haus.
if _XPERP not in sys.path:
    sys.path.insert(0, _XPERP)
okxf = sys.modules.get("okxf")
if okxf is None:
    _spec = spec_from_file_location("okxf", os.path.join(_XPERP, "okxf.py"))
    okxf = module_from_spec(_spec)
    sys.modules["okxf"] = okxf
    _spec.loader.exec_module(okxf)

OKXFehler = okxf.OKXFehler

# Die Wartungsmarge, mit der die Liquidationsmarke gerechnet wird. Gleicher
# Wert wie in xperp/okxf.py und xperp/wachen.json - eine zweite Zahl waere eine
# zweite Wahrheit ueber dieselbe Groesse.
WARTUNGSMARGE = 0.005


# --- Schluessel -------------------------------------------------------------

def schluessel_vorhanden():
    """Der Name bleibt derselbe wie in okx_spot: beide Wege lesen denselben
    OKX-Schluesselsatz (OKX_API_KEY / _SECRET / _PASSPHRASE)."""
    return okxf.schluessel_vorhanden()


def demo_modus():
    return okxf.demo_modus()


# --- Instrument -------------------------------------------------------------

def _alle_futures():
    return okxf._mit_wiederholung("/api/v5/public/instruments?instType=FUTURES")


def perp_fuer(inst):
    """Der lebende XPERP-Kontrakt zu einem Mosaic-Namen ('BTC-USDC').

    Die Wachen nennen die Instrumente in OKX-SPOT-Namen, weil die Kerzen und
    das Papierbuch dort bleiben. Fuer die Order wird daraus der gehebelte
    Kontrakt - derselbe Basiswert, anderes Produkt. Deshalb wird NIE der
    SPOT-Markt geordert, nur weil er der gleiche Name ist.

    Ein unbekannter Basiswert ist ein Fehler, kein Rueckfall: still ein
    anderes Instrument zu handeln waere der teuerste Fehler dieser Datei.
    """
    basis = str(inst or "").split("-")[0].strip().upper()
    if not basis:
        raise OKXFehler("leeres Instrument %r" % (inst,))
    treffer = [x for x in _alle_futures()
               if x.get("ruleType") == "xperp"
               and x.get("state") == "live"
               and str(x["instId"]).split("-")[0].upper() == basis]
    if not treffer:
        raise OKXFehler("kein gehebelter OKX-Kontrakt zu %r "
                        "(Basiswert wird nicht als XPERP gefuehrt)" % (inst,))
    # Der juengste Kontrakt: OKX legt einen XPERP mit neuem instId auf, wenn
    # der alte ausläuft. Der mit dem spaetesten CTVal-Ablauf ist der aktuelle.
    treffer.sort(key=lambda x: str(x.get("expTime") or ""))
    return treffer[-1]


def ct_val(info):
    """Wie viele Basiseinheiten EIN Kontrakt ist."""
    return float(info["ctVal"])


def kurs_und_instrument(inst):
    """(kontrakt-info, kurs) - beides geholt, die Kursbasis ist der Kontrakt."""
    info = perp_fuer(inst)
    return info, float(okxf.letzter_kurs(info["instId"]))


def letzter_kurs(inst):
    """Lebender Kurs des KONZRAKTS (nicht des Spot-Paars mit gleichem Namen).

    `venue_binden()` bindet `live_kurs_quelle` auf genau diesen Namen - ohne
    die Funktion bricht der Live-Zweig der Spur beim ersten Kursabruf. Der
    Test `test_hauptfunktionen_vorhanden` fand die Luecke: sie war beim
    Bauen des Weges entstanden und beim Lesen des Codes nicht aufgefallen.
    """
    return float(okxf.letzter_kurs(perp_fuer(inst)["instId"]))


# --- Groesse ----------------------------------------------------------------

def menge_fuer(inst, nominal_usd, kurs, info=None):
    """Kontrakte, die 'nominal_usd' Nennwert wert sind. Gibt (n, fehler).

    Bei einem gehebelten Weg ist der Betrag der NOMINALWERT, nicht die
    Margin: das ist der Unterschied zu okx_spot.menge_fuer(), wo derselbe
    Aufruf die Margin meint. Wer das verwechselt, kauft mit 600 USD Margin
    600 USD Nominal und haelt eine 6-fache Wette.
    """
    try:
        info = info or perp_fuer(inst)
    except OKXFehler as e:
        return 0.0, "Kontrakt nicht abrufbar (%s)" % e
    if kurs <= 0:
        return 0.0, "Kurs %r ungueltig" % kurs
    ct = ct_val(info)
    if ct <= 0:
        return 0.0, "ctVal %r unbrauchbar" % ct
    roh = nominal_usd / kurs / ct
    lot = float(info.get("lotSz") or 1)
    minsz = float(info.get("minSz") or 1)
    n = int(roh / lot) * lot
    if n <= 0:
        return 0.0, ("Nennwert %.2f USD ergibt bei Kurs %.6f und ctVal %s "
                     "0 Kontrakte" % (nominal_usd, kurs, ct))
    if n < minsz:
        return 0.0, ("%.4f Kontrakte unter der Mindestmenge %.4f"
                     % (n, minsz))
    return float(n), None


def liquidationspreis(einstieg, hebel, seite):
    """Liquidationsmarke fuer die GELEBTE Long/Short-Position.

    Long: rund 1/hebel unter dem Einstieg. Short: rund 1/hebel darueber.
    Die Wartungsmarge kommt obendrauf, deshalb liegt die Marke etwas
    weiter weg als die reine 1/hebel-Rechnung.
    """
    h = max(1.0, float(hebel))
    if seite == "long":
        return einstieg * (1.0 - 1.0 / h + WARTUNGSMARGE)
    return einstieg * (1.0 + 1.0 / h - WARTUNGSMARGE)


def stop_vor_liq(stop, einstieg, hebel, seite):
    """(ok, grund) - feuert der Stop, BEVOR die Liquidationsmarke?

    Das ist die eine Pruefung, die es bei Spot nicht gibt und die ein
    gehebelter Einstieg braucht.

    DIE RICHTUNG IST DER GANZE UNTERSCHIED, und sie ist leicht verkehrt
    herum zu lesen: ein Long verliert, wenn der Kurs FALLT - er trifft
    zuerst den naeher am Einstieg liegenden Stop und erst danach die
    tiefer liegende Liquidationsmarke. Ein Stop muss also ZWISCHEN beiden
    liegen, naeher am Einstieg: liq < stop < einstieg. Ein Stop unter der
    Liquidationsmarke kommt nie, weil die Liquidation vorher da ist. Beim
    Short ist es spiegelbildlich: einstieg < stop < liq.

    Gemessen am 05.10.2026: bei 6x liegt die Liquidation 16,17 % entfernt, der
    Stop der Mosaic-Spur bei 5-12 % - er feuert also immer zuerst. Die Grenze
    liegt bei rund 12x (Liquidation ~7,8 %), dort wuerde ein 5-%-Stop zu weit
    hinten liegen und nie kommen.

    Zwei Preise werden verweigert statt geraten: ein Stop auf/ueber dem Kurs
    (verkauft sofort) und einer jenseits der Liquidationsmarke (kaeme nie).
    """
    liq = liquidationspreis(einstieg, hebel, seite)
    if seite == "long":
        if stop >= einstieg:
            return False, ("long-Stop %.6f liegt auf/ueber dem Kurs %.6f - "
                           "verkauft sofort" % (stop, einstieg))
        if stop <= liq:
            abstand = abs(einstieg - liq) / einstieg * 100.0
            return False, ("long-Stop %.6f liegt auf/unter der "
                           "Liquidationsmarke %.6f (Hebel %s, %.2f %% entfernt)"
                           " - der Stop kaeme nie"
                           % (stop, liq, hebel, abstand))
    else:
        if stop <= einstieg:
            return False, ("short-Stop %.6f liegt auf/unter dem Kurs %.6f - "
                           "kauft sofort" % (stop, einstieg))
        if stop >= liq:
            abstand = abs(einstieg - liq) / einstieg * 100.0
            return False, ("short-Stop %.6f liegt auf/ueber der "
                           "Liquidationsmarke %.6f (Hebel %s, %.2f %% entfernt)"
                           " - der Stop kaeme nie"
                           % (stop, liq, hebel, abstand))
    return True, None


# --- Preise -----------------------------------------------------------------

def preis_gerundet(inst, preis, richtung="auf"):
    """Preis auf die Tick-Groesse des KONZRAKTS (nicht des Spot-Paars).

    Richting "auf": der Stop eines Long liegt nie tiefer als gerechnet - das
    Risiko wird nicht groesser als die Wache erlaubt.
    """
    if richtung not in ("auf", "ab"):
        raise ValueError("richtung muss 'auf' oder 'ab' sein")
    try:
        tick = float(perp_fuer(inst)["tickSz"])
    except Exception as e:                                          # noqa: BLE001
        print("  tickSz fuer %s nicht abrufbar (%s) - Preis ungerundet"
              % (inst, e), file=sys.stderr)
        return str(preis)
    if tick <= 0:
        return str(preis)
    stellen = max(0, len(("%.10f" % tick).rstrip("0").split(".")[1]))
    faktor = 10 ** stellen
    x = round(float(preis) * faktor, 6)
    ganz = math.ceil(x) if richtung == "auf" else math.floor(x)
    return "%.*f" % (stellen, ganz / faktor)


# --- Konto ------------------------------------------------------------------

def guthaben_waehrung(ccy="USDC"):
    """Freies Margin-Guthaben einer Waehrung.

    DIE WAEHRUNG STEHT IN `details`, NICHT auf der obersten Ebene (gemessen am
    05.10.2026): /api/v5/account/balance?ccy=USDC liefert oben
    availEq=''/availBal=None/eq=None und erst im Element details[0] die
    Zahlen. Wer die oberen Felder liest, bekommt 0.00 - das sieht wie ein
    leeres Konto aus und sperrt jede Spur an einem Guthaben-Tor, das
    eigentlich offen ist. okx_spot.guthaben_waehrung() liest `details[0]`
    richtig; diese Datei tat es zuerst nicht.

    Die Futures-Margin des Kontos ist USDC. `availEq` ist die freie Margin,
    `eq` enthaelt auch das in Positionen und Staking gebundene Geld.
    """
    d = okxf._mit_wiederholung("/api/v5/account/balance?ccy=" + ccy,
                              signiert=True)
    if not d:
        return 0.0
    z = d[0]
    kandidaten = list(z.get("details") or []) + [z]
    for zeile in kandidaten:
        for feld in ("availEq", "availBal", "cashBal", "eq"):
            wert = str((zeile or {}).get(feld) or "").strip()
            if wert:
                return float(wert)
    return 0.0


def guthaben_usdt():
    """Altname wie in okx_spot."""
    return guthaben_waehrung()


# --- Orders (bewegen Geld) --------------------------------------------------

def hebel_setzen(inst, hebel, tdmode="isolated"):
    """Hebel je Kontrakt setzen. Muss VOR der Order stehen."""
    info = perp_fuer(inst)
    return okxf._roh("/api/v5/account/set-leverage", "POST",
                     {"instId": info["instId"], "lever": str(hebel),
                      "mgnMode": tdmode}, signiert=True)


def markt_kauf(inst, kontrakte, hebel=6):
    """Market-Kauf in einen gehebelten Long. Gibt die ordId zurueck.

    `hebel` wird gesetzt, bevor die Order rausgeht - ein Kauf auf einem
    Kontrakt mit einem anderen Hebel waere eine Wette, die niemand bestellt
    hat.
    """
    info = perp_fuer(inst)
    hebel_setzen(inst, hebel)
    body = {"instId": info["instId"], "tdMode": "isolated", "side": "buy",
            "ordType": "market", "sz": str(kontrakte)}
    d = okxf._roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def markt_verkauf(inst, kontrakte):
    """Market-Verkauf, reduceOnly - nie eine Short-Position oeffnen.

    Mosaic ist Long-only. Ein Tippfehler in der Richtung darf nie in eine
    neue Gegenposition umkippen, sondern muss ein Schliessen bleiben.
    """
    info = perp_fuer(inst)
    body = {"instId": info["instId"], "tdMode": "isolated", "side": "sell",
            "ordType": "market", "sz": str(kontrakte), "reduceOnly": True}
    d = okxf._roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def algo_stop_setzen(inst, kontrakte, seite, trigger):
    """Bedingter Stop an der Boerse - ueberlebt jeden Neustart.

    `seite` ist die Seite der SCHLIESSUNG: fuer eine offene Long also 'sell'.
    Ausgeloest wird als Market (slOrdPx=-1), damit der Stop im Absturz fuellt
    und nicht als Limit haengen bleibt.
    """
    info = perp_fuer(inst)
    gegen = "sell" if seite == "long" else "buy"
    body = {"instId": info["instId"], "tdMode": "isolated", "side": gegen,
            "ordType": "conditional", "sz": str(kontrakte),
            "reduceOnly": True,
            "slTriggerPx": preis_gerundet(inst, trigger, "auf"),
            "slOrdPx": "-1"}
    d = okxf._roh("/api/v5/trade/order-algo", "POST", body, signiert=True)
    return d[0]["algoId"] if d else None


def algo_stornieren(inst, algo_id):
    """Stop abbestellen. `instId` ist Pflicht (ohne: OKX 50014)."""
    info = perp_fuer(inst)
    body = {"instId": info["instId"], "algoId": algo_id}
    return okxf._roh("/api/v5/trade/cancel-algos", "POST", body, signiert=True)


def gefuellte_menge(inst, ord_id):
    """Gefuellte Menge einer Order (0, wenn unklar)."""
    info = perp_fuer(inst)
    try:
        d = okxf._mit_wiederholung(
            "/api/v5/trade/order?instId=%s&ordId=%s"
            % (urllib.parse.quote(info["instId"]), ord_id), signiert=True)
    except Exception:                                              # noqa: BLE001
        return 0.0
    if not d:
        return 0.0
    try:
        return float(d[0].get("accFillSz") or d[0].get("fillSz") or 0.0)
    except (KeyError, ValueError):
        return 0.0


def offene_stops(inst):
    """Offene Schutzauftraege zum Kontrakt - fuer den Abgleich Buch/Borse."""
    info = perp_fuer(inst)
    d = okxf.schutz_stops(info["instId"])
    return [x for x in (d or [])
            if okxf.ist_schutz_stop(x)]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("OKX-Futures-Weg (gehebelt). Kontrakte:")
    for name in ("BTC-USDC", "ETH-USDC", "SOL-USDC"):
        try:
            i, k = kurs_und_instrument(name)
            n, f = menge_fuer(name, 600.0, k, info=i)
            liq = liquidationspreis(k, 6, "long")
            ok, g = stop_vor_liq(k * 0.95, k, 6, "long")
            print("  %-9s -> %-28s Kurs %-12.8g ctVal %-8s "
                  "600 USD -> %.4f %s"
                  % (name, i["instId"], k, i["ctVal"], n, ("[%s]" % f) if f else ""))
            print("            liq@6x long %.6f (%.2f%%), Stop -5%% %s"
                  % (liq, (liq / k - 1) * 100,
                     "vor liq" if ok else "ZU SPAET: %s" % g))
        except Exception as e:                                      # noqa: BLE001
            print("  %-9s nicht abrufbar: %s" % (name, e))
    print("  Schluessel gesetzt: %s  (Demo: %s)  USDC frei: %.2f"
          % (schluessel_vorhanden(), demo_modus(), guthaben_waehrung()))