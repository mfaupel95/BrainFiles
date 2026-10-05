"""Eigener OKX-Spot-Orderweg fuer die Mosaic-Spur (Los: Stufe A 2026-09-19).

Schwester von xperp/okxf.py, aber fuer SPOT statt XPERP-Futures. Bewusst ein
EIGENES Modul, kein gemeinsamer Buchkern: nur Mosaic soll diesen Weg anfassen,
damit kein OKX-Bot-Spur-Pfad (spur_buch.py) still live-faehig wird. Es folgt
den erprobten Konventionen von okxf.py (Signatur, Wiederholungen, OKXFehler,
Key aus Umgebung/Registry) in schlanker Form.

SPOT- vs.-Futures-Unterschiede, die zaehlen:
  - tdMode ist immer "cash", nie isolated/cross. kein Hebel, keine posSide.
  - Mengen sind Betraege der BASIS-Waehrung (BTC bei BTC-USDC), nicht
    Kontrakte. Fuer einen 10-USDC-Kauf also menge = usdc / kurs, auf lotSz
    abgerundet (Aufrunden ueberschreitet den Rahmen), minSz geprueft.
  - Ein Stop-Loss wird als Bedingte Order (ordType=conditional) an der Boerse
    gelegt und ueberlebt damit einen Neustart dieses Skripts - kein
    skript-bewachtes Stop-Bewachen.

Schluessel: OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE aus der
Prozessumgebung, ersatzweise aus HKCU\\Environment (ein von Claude gestarteter
Prozess erbt die Benutzervariablen nicht). OKX_BASE ersetzt den Host (z.B.
https://eea.okx.com fuer EEA-Portal-Keys).

Hinweis aus okxf.py: API-Schluessel vom EEA-Portal (my.okx.com / eea.okx.com)
sind auf der globalen Infrastruktur www.okx.com NICHT gueltig ('50119' /
'50111'). Deutsche Konten liegen meist im EEA-Bereich.

Diese Datei bewegt Geld, wenn sie mit echten Keys aufgerufen wird. Kein Skript
in diesem Ordner ruft sie von selbst mit echten Orders auf - der Live-Pfad von
mosaic/handeln.py laeuft nur, wenn die gesamte Sperrenkette offen ist.
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
from datetime import datetime, timezone

BASIS = "https://www.okx.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
MAX_FEHLER = 6
# Wie oft eine Drosselung je Aufruf geheilt wird, bevor sie doch ein
# Fehler bleibt (Einordnung wie in scanner/okx.py).
MAX_429 = 4


# Die Haus-Bremse gegen OKX-Drosselung (okx_takt.py, eine Ebene hoeber).
# Gemessen 05.10.2026: 120 Abrufe nacheinander -> 0 Fehler, 6 Threads
# gleichzeitig -> 93x "OKX 50011: Too Many Requests (HTTP 429)". Der
# Ausloeser ist die Parallelitaet, nicht die Menge - drei Dauerlauf-Stufen,
# die Handelszentrale und die Wachen laufen als eigene Prozesse gegen
# dieselbe IP. Der Handel-Ordner wird ANGEHAENGT (nicht vorn eingefuegt):
# sys.path[0] ist der eigene Spur-Ordner, sonst wuerde hier das falsche
# okx-Modul eines anderen Ordners gewinnen.
_HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HANDEL not in sys.path:
    sys.path.append(_HANDEL)
import okx_takt  # noqa: E402

class OKXFehler(RuntimeError):
    """Fachlicher Fehler aus einer gueltigen OKX-Antwort (code != 0)."""


# --- Schluessel -------------------------------------------------------------

def _aus_registry(name):
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            wert, _ = winreg.QueryValueEx(k, name)
            return wert or None
    except OSError:
        return None


def _variable(name):
    return os.environ.get(name) or _aus_registry(name)


def schluessel_vorhanden():
    return all(_variable(n)
               for n in ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE"))


def demo_modus():
    """True, wenn OKX_SIMULATED / OKX_DEMO gesetzt ist (1/true/ja)."""
    v = (_variable("OKX_SIMULATED") or _variable("OKX_DEMO") or "").strip().lower()
    return v in ("1", "true", "yes", "ja", "y")


# --- HTTP -------------------------------------------------------------------

def _roh(pfad, methode="GET", body=None, signiert=False):
    basis = (_variable("OKX_BASE") or BASIS).rstrip("/")
    url = basis + pfad
    daten = json.dumps(body) if body else ""
    kopf = dict(HEADERS)
    if demo_modus():
        kopf["x-simulated-trading"] = "1"
    if signiert:
        key = _variable("OKX_API_KEY")
        secret = _variable("OKX_API_SECRET")
        pw = _variable("OKX_API_PASSPHRASE")
        if not (key and secret and pw):
            raise RuntimeError("OKX-Schluessel fehlen (Key/Secret/Passphrase)")
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        ts = ts.replace("+00:00", "Z")
        vortext = ts + methode + pfad + daten
        sig = base64.b64encode(
            hmac.new(secret.encode(), vortext.encode(), hashlib.sha256).digest()
        ).decode()
        kopf.update({
            "OK-ACCESS-KEY": key,
            "OK-ACCESS-SIGN": sig,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": pw,
        })
    req = urllib.request.Request(
        url, data=daten.encode() if daten else None, headers=kopf, method=methode)
    # Haus-Bremse: begrenzt die Zahl der VERSUCHE, nicht nur der Antworten.
    okx_takt.reserviere()
    try:
        with urllib.request.urlopen(req, timeout=20) as antwort:
            d = json.loads(antwort.read().decode())
    except urllib.error.HTTPError as e:
        if signiert and e.code in (401, 403):
            try:
                f = json.loads(e.read().decode())
                raise OKXFehler(
                    "OKX %s: %s (HTTP %d - Key/Secret/Passphrase/IP/Uhr pruefen)"
                    % (f.get("code"), f.get("msg") or f, e.code)) from None
            except (ValueError, AttributeError):
                raise OKXFehler(
                    "OKX HTTP %d auf signierte Abfrage - Key/Secret/Passphrase/"
                    "IP/Uhr pruefen" % e.code) from None
        raise
    if d.get("code") not in ("0", 0):
        raise OKXFehler("OKX %s: %s" % (d.get("code"), d.get("msg") or d))
    return d.get("data", [])


def _mit_wiederholung(*a, **kw):
    """Drei Fehlerarten, drei Behandlungen (siehe scanner/okx.py).

    50011/429 ist DROSSELUNG und der einzige Fehler, der sich durch Warten
    heilt: gemessen am 05.10.2026 loest Parallelitaet ihn aus (6 Threads ->
    93 Fehler, nacheinander 120 Abrufe -> 0 Fehler). Er wird deshalb gefangen
    statt nach oben gegeben - vorher beendete er den Zyklus. Fachliche Fehler
    (falscher instId, zu kleine Menge) werden sofort geworfen: Wiederholen
    aendert daran nichts, und beim Schreiben kann jeder Versuch eine echte
    Order sein.
    """
    fehler = 0
    gedrosselt = 0
    while True:
        try:
            return _roh(*a, **kw)
        except OKXFehler as e:
            if not okx_takt.ist_429(e):
                raise
            gedrosselt += 1
            if gedrosselt >= MAX_429:
                raise
            warten = okx_takt.warte_s(gedrosselt)
            print("  OKX-Spot gedrosselt (%d/%d) - warte %.1f s, kein Ausfall"
                  % (gedrosselt, MAX_429, warten), file=sys.stderr)
            time.sleep(warten)
        except Exception as e:  # noqa: BLE001 - Transportfehler, wird gezaehlt
            fehler += 1
            if fehler >= MAX_FEHLER:
                raise
            print("  OKX-Spot-Transportfehler %d/%d: %s - wird wiederholt, kein Ausfall"
                  % (fehler, MAX_FEHLER, e), file=sys.stderr)
            time.sleep(1.5 * fehler)


# --- oeffentlich: Instrument & Kurs ----------------------------------------

def spot_instrument(inst):
    """Instrument-Daten des Spot-Paares (lotSz, minSz, tickSz)."""
    d = _mit_wiederholung(
        "/api/v5/public/instruments?instType=SPOT&instId="
        + urllib.parse.quote(inst))
    for x in d:
        if x.get("state") == "live":
            return x
    raise OKXFehler("kein lebendes SPOT-Instrument %r" % inst)


def letzter_kurs(inst):
    d = _mit_wiederholung("/api/v5/market/ticker?instId=" + urllib.parse.quote(inst))
    return float(d[0]["last"])


def menge_fuer(inst, usdt, kurs):
    """Menge in Basiswaehrung, die 'usdt' wert ist, auf lotSz abgerundet.

    Gibt (menge, fehler) zurueck. Aufrunden wuerde den Betragsrahmen
    ueberschreiten; unter minSz abzurunden hiesse eine Order, die OKX
    ablehnt. Beide Faelle sind ein Fehler, bevor die Order Geld kostet.
    """
    try:
        info = spot_instrument(inst)
    except OKXFehler as e:
        return 0.0, "Instrument nicht abrufbar (%s)" % e
    lot = float(info["lotSz"])
    minsz = float(info["minSz"])
    if kurs <= 0:
        return 0.0, "Kurs %r ungueltig" % kurs
    roh = usdt / kurs
    menge = int(roh / lot) * lot
    if menge <= 0:
        return 0.0, ("Menge %.8f ist 0 (Betrag %.2f USDT bei Kurs %s)"
                     % (roh, usdt, kurs))
    if menge < minsz:
        return 0.0, ("Menge %.8f unter Mindestmenge %.8f" % (menge, minsz))
    # Stellen-Zahl aus lotSz fuer die Rueckgabe (lotSz z.B. 1e-8 -> 8)
    stellen = max(0, len(("%.10f" % lot).rstrip("0").split(".")[1]))
    return round(menge, stellen), None


# --- signiert: Konto --------------------------------------------------------

def guthaben_waehrung(ccy="USDC"):
    """Freies Guthaben einer Waehrung (availBal).

    Standard ist USDC: die Mosaic-Spur handelt seit dem 21.09.2026 auf
    USDC-Paaren (Max: "Auf okx usdc nehmen!") - vorher USDT, wovon im Konto
    nichts frei lag, waehrend USDC reichlich vorhanden ist. Der Wert 0.0 ist
    kein Fehler, sondern ein leeres Guthaben.
    """
    d = _mit_wiederholung("/api/v5/account/balance?ccy=" + ccy, signiert=True)
    if not d or not d[0].get("details"):
        return 0.0
    return float(d[0]["details"][0].get("availBal") or 0.0)


def guthaben_usdt():
    """Altname - liefert dieselbe Zahl wie guthaben_waehrung()."""
    return guthaben_waehrung()


# --- signiert: Orders (bewegen Geld) ---------------------------------------

def markt_kauf(inst, menge):
    """Spot-Market-Kauf. Gibt die ordId zurueck."""
    body = {"instId": inst, "tdMode": "cash", "side": "buy",
            "ordType": "market", "sz": str(menge)}
    d = _roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def markt_verkauf(inst, menge):
    """Spot-Market-Verkauf, reduceOnly - nie eine Short-Position oeffnen.

    Mosaic ist Long-only. Ein Tippfehler in der Richtung darf nie in eine
    neue Gegenposition umkippen, sondern muss ein Schliessen bleiben.
    """
    body = {"instId": inst, "tdMode": "cash", "side": "sell",
            "ordType": "market", "sz": str(menge), "reduceOnly": True}
    d = _roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def preis_gerundet(inst, preis, richtung="auf"):
    """Einen Preis auf die Tick-Groesse des Instruments bringen (tickSz).

    OKX lehnt eine Order ab, deren Preis kein Vielfaches von tickSz ist
    ("Order price must be a multiple of the tick size"). Der Stop-Preis kommt
    aus einer Rechnung (Einstieg x (1 - stop_pct)) und hat damit praktisch
    immer zu viele Stellen. Derselbe Fehler ist bei Kraken am 22.09.2026
    aufgetreten ("SOL/EUR price can only be specified up to 2 decimals") und
    liess den Notausstieg ausfallen - hier wird er vermieden.

    Richtung "auf": der Stop eines LONG liegt nie tiefer als gerechnet, das
    Risiko wird also nicht groesser als die Wache erlaubt. Laesst sich tickSz
    nicht abrufen, wird der rohe Wert gesendet und gewarnt - das ist genau
    das Verhalten von vorher, kein neuer stiller Fehler.
    """
    if richtung not in ("auf", "ab"):
        raise ValueError("richtung muss 'auf' oder 'ab' sein")
    try:
        tick = float(spot_instrument(inst)["tickSz"])
    except Exception as e:  # noqa: BLE001
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


def algo_stop_setzen(inst, menge, seite, trigger):
    """Bedingte Stop-Loss-Order an der Boerse (ueberlebt Neustart).

    seite ist die SEITE DER SCHLIESSUNG: fuer eine offene Long-Position also
    'sell'. ordType=conditional, Ausloese-Schutzmarkt (slOrdPx=-1), damit die
    Order im Absturz fuellt und nicht als Limit haengen bleibt.
    """
    gegen = "sell" if seite == "long" else "buy"
    body = {"instId": inst, "tdMode": "cash", "side": gegen,
            "ordType": "conditional", "sz": str(menge),
            "slTriggerPx": preis_gerundet(inst, trigger, "auf"),
            "slOrdPx": "-1"}
    d = _roh("/api/v5/trade/order-algo", "POST", body, signiert=True)
    return d[0]["algoId"]


def algo_stornieren(inst, algo_id):
    body = {"instId": inst, "algoId": algo_id}
    return _roh("/api/v5/trade/cancel-algos", "POST", body, signiert=True)


def gefuellte_menge(inst, ord_id):
    """Gefuellte Menge einer Order (0, wenn keine Fuellung/Order-Stand unklar)."""
    d = _mit_wiederholung(
        "/api/v5/trade/order?instId=" + urllib.parse.quote(inst)
        + "&ordId=" + ord_id, signiert=True)
    if not d:
        return 0.0
    try:
        return float(d[0].get("fillSz") or 0.0)
    except (KeyError, ValueError):
        return 0.0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("OKX-Spot-Modul. Kurse:")
    for inst in ("BTC-USDC", "ETH-USDC", "SOL-USDC"):
        k = letzter_kurs(inst)
        m, f = menge_fuer(inst, 10.0, k)
        print("  %-9s Kurs %-10.7g  10 USDC -> %.10g %s"
              % (inst, k, m, ("[%s]" % f) if f else ""))
    print("  Schluessel gesetzt: %s  (Demo-Modus: %s)"
          % (schluessel_vorhanden(), demo_modus()))