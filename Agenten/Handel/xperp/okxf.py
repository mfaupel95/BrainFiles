"""Zugang zu den OKX-XPERP-Kontrakten (instType=FUTURES, ruleType=xperp).

Schwesterdatei zu scanner/okx.py, aber fuer Futures statt Spot. Die
Unterschiede, die zaehlen:

  - XPERP liegen unter instType=FUTURES, nicht SWAP. Der instId sieht aus wie
    "RE-USD_UM_XPERP-310620" und traegt ein Ablaufdatum weit in der Zukunft
    (hier 2031). Wer nach "REUSD" sucht, findet nichts - der Bindestrich in
    "RE-USD" gehoert zum Namen.
  - Gehandelt werden Kontrakte, nicht Muenzen. ctVal sagt, wieviel Basiswert in
    einem Kontrakt steckt (RE: 10). Groessen sind ganzzahlige Vielfache von
    lotSz. Wer das uebergeht, bekommt eine andere Position als gerechnet -
    genau die Falle aus Wissen/Handelsbots.md ("570 $ Nominal statt 651 $").
  - tdMode ist "isolated" oder "cross", nie "cash". Dazu posSide bei
    Hedge-Modus. Der Hebel wird vor der Order gesetzt, nicht mit ihr.

Die beiden Fallen aus scanner/okx.py gelten unveraendert:
  - OKX antwortet ohne User-Agent mit HTTP 403.
  - Fehlversuche zaehlen, sonst haengt eine Schleife bei einem Ausfall endlos.

Schluessel kommen aus der Prozessumgebung, ersatzweise aus der
Windows-Registry (HKCU\\Environment) - ein von Claude gestarteter Prozess erbt
die Benutzervariablen nicht.

WICHTIG: Seit dem 01.09.2026 ist Hebel nicht mehr grundsaetzlich verboten
(Wissen/Handelsregeln.md, Spur 2) - verboten bleibt, ihn ohne ausdrueckliche
Anweisung zu nehmen. Eine gueltige Anweisung nennt Kontrakt, Richtung, Hebel,
Einsatz und Stop; fehlt eine Angabe, wird danach gefragt statt geraten.

Fuer die Order-Funktionen unten heisst das: Sie existieren, damit ein Mensch
oder ein angewiesenes Skript sie aufruft. Kein Skript in diesem Ordner ruft
sie von selbst auf, und aus einem Zeitplan heraus wird nie scharf gehandelt.
Vor einer gehebelten Order gehoeren die vier Zahlen der Pruefpflicht vorgelegt
- bot.pruefpflicht() rechnet sie.

(Bis zum 01.09.2026 stand hier das pauschale Verbot "nur Spot, nur Long, kein
Hebel". Es galt fuer scanner/handeln.py und stellte diesen Ordner in einen
Graubereich; genau das war der Anlass, die Regel zu aendern.)
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
from datetime import datetime, timezone

BASIS = "https://www.okx.com"
# API-Schluessel vom EEA-Portal (my.okx.com / eea.okx.com) sind NICHT auf der
# globalen Infrastruktur www.okx.com gueltig - dort '50119 API key doesn't
# exist' bzw. '50111 Invalid OK-ACCESS-KEY'. Deutsche Konten liegen meist im
# EEA-Bereich. OKX_BASE ueberschreibt den Host, z.B. https://eea.okx.com.
#
# RUBIK_BASIS ist davon getrennt: die Statistik-Endpunkte unter /rubik/ mit
# instId liefern nur auf dem globalen Host Daten. my.okx.com und eea.okx.com
# antworten dort mit code 0 und LEERER Liste - kein Fehler, nur nichts
# (13.09.2026 geprueft, /rubik/stat/taker-volume-contract). Ein stiller
# Leerlauf ist schlimmer als ein Fehler, darum hat dieser oeffentliche,
# nicht kontogebundene Abruf seinen eigenen Host. OKX_BASE_RUBIK ueberschreibt
# ihn, ohne den Handelspfad anzufassen.
RUBIK_BASIS = "https://www.okx.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
MAX_FEHLER = 6

# instCategory trennt die XPERP-Familien - geprueft am 01.09.2026:
#   1 = Krypto (111 Werte), 3 = Aktien (46), 4 = Rohstoffe (4)
KRYPTO = "1"
AKTIE = "3"
ROHSTOFF = "4"


class OKXFehler(RuntimeError):
    """Fachlicher Fehler aus einer gueltigen OKX-Antwort (code != 0).
    Wird NICHT wiederholt - ein falscher instId existiert auch beim zehnten
    Versuch nicht."""


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
    return all(_variable(n) for n in
               ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE"))


# --- HTTP ------------------------------------------------------------------

def demo_modus():
    """True, wenn OKX_SIMULATED / OKX_DEMO gesetzt ist (1/true/ja).

    OKX-Demo-Keys existieren auf dem Live-Endpunkt nicht ('50119 API key
    doesn't exist'). Sie brauchen denselben Host, aber den Header
    'x-simulated-trading: 1'. Ein Demo-Lauf ist zugleich der Papierlauf, den
    Wissen/Handelsregeln.md (Spur 2) fuer eine neue Strategie verlangt.
    """
    v = (_variable("OKX_SIMULATED") or _variable("OKX_DEMO") or "").strip().lower()
    return v in ("1", "true", "yes", "ja", "y")


def _roh(pfad, methode="GET", body=None, signiert=False, basis=None):
    url = (basis or _variable("OKX_BASE") or BASIS).rstrip("/") + pfad
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
    try:
        with urllib.request.urlopen(req, timeout=20) as antwort:
            d = json.loads(antwort.read().decode())
    except urllib.error.HTTPError as e:
        # OKX legt auch bei 4xx eine JSON-Antwort mit code/msg bei. 401/403 auf
        # eine signierte Abfrage ist ein Schluesselproblem (falsche Passphrase,
        # falsches Secret, Key inaktiv, IP nicht freigegeben, Uhr verstellt) -
        # das heilt kein Wiederholen. Als OKXFehler werfen, damit der Code
        # sichtbar wird statt eines nackten "HTTP Error 401".
        if signiert and e.code in (401, 403):
            try:
                f = json.loads(e.read().decode())
                raise OKXFehler(
                    "OKX %s: %s (HTTP %d - Key/Secret/Passphrase/IP/Uhr pruefen)"
                    % (f.get("code"), f.get("msg") or f, e.code)) from None
            except (ValueError, AttributeError):
                raise OKXFehler("OKX HTTP %d auf signierte Abfrage - "
                                "Key/Secret/Passphrase/IP/Uhr pruefen" % e.code) from None
        raise
    if d.get("code") not in ("0", 0):
        raise OKXFehler("OKX %s: %s" % (d.get("code"), d.get("msg") or d))
    return d.get("data", [])


def _mit_wiederholung(*a, **kw):
    fehler = 0
    while True:
        try:
            return _roh(*a, **kw)
        except OKXFehler:
            raise  # fachlich, nicht durch Wiederholen zu heilen
        except Exception as e:  # noqa: BLE001 - Transportfehler, wird gezaehlt
            fehler += 1
            if fehler >= MAX_FEHLER:
                raise
            print("  OKX-Transportfehler %d/%d: %s" % (fehler, MAX_FEHLER, e),
                  file=sys.stderr)
            time.sleep(1.5 * fehler)


# --- oeffentlich: Instrumente ----------------------------------------------

def instrumente(kategorie=KRYPTO):
    """Alle lebenden XPERP-Kontrakte einer instCategory, nach Basiswert sortiert."""
    d = _mit_wiederholung("/api/v5/public/instruments?instType=FUTURES")
    xp = [x for x in d
          if x.get("ruleType") == "xperp"
          and x.get("state") == "live"
          and (kategorie is None or x.get("instCategory") == kategorie)]
    return sorted(xp, key=lambda x: x["instId"])


def swap_instrument(inst_id):
    """Ein gewoehnlicher Perpetual (instType=SWAP) anhand des vollen instId.

    Der XPERP-Zweig oben findet nur ruleType=xperp unter FUTURES. Der normale
    Perp - CHIP-USDT-SWAP mit 24x mehr Umsatz als der CHIP-XPERP - liegt unter
    SWAP und wird hier direkt geholt. ctVal/lotSz/tickSz haben dieselbe Form,
    kontrakte_aus_nominal() und auf_tick() rechnen unveraendert.
    """
    d = _mit_wiederholung(
        "/api/v5/public/instruments?instType=SWAP&instId=" + inst_id)
    for x in d:
        if x.get("state") == "live":
            return x
    raise OKXFehler("kein lebender SWAP-Kontrakt %r" % inst_id)


def instrument(basis):
    """Ein Kontrakt anhand des Basiswerts ('RE') oder des vollen instId.

    'REUSD' wird mit angenommen - so liest sich 'RE-USD' ohne Bindestrich, und
    genau daran ist die Suche am 01.09.2026 einmal gescheitert. Endet die
    Eingabe auf '-SWAP', ist ein gewoehnlicher Perpetual gemeint, kein XPERP.
    """
    if basis.upper().endswith("-SWAP"):
        return swap_instrument(basis.upper())

    alle = instrumente(kategorie=None)
    b = basis.upper()
    for x in alle:                                    # voller instId
        if x["instId"].upper() == b:
            return x
    for x in alle:                                    # Basiswert, z.B. 'RE'
        if x["instId"].split("-")[0].upper() == b:
            return x
    for x in alle:                                    # 'REUSD' -> 'RE-USD_...'
        if x["instId"].upper().replace("-", "").startswith(b):
            return x
    raise OKXFehler("kein XPERP-Kontrakt zu %r" % basis)


# --- oeffentlich: Kurse -----------------------------------------------------

def kerzen(inst, bar="1H", anzahl=300):
    """Kerzen aufsteigend als [ts, offen, hoch, tief, schluss, volumen]."""
    pfad = "/api/v5/market/candles?" + urllib.parse.urlencode(
        {"instId": inst, "bar": bar, "limit": min(anzahl, 300)})
    roh = _mit_wiederholung(pfad)
    reihen = [[int(r[0])] + [float(x) for x in r[1:6]] for r in roh]
    reihen.sort(key=lambda r: r[0])
    return reihen


def kerzen_lang(inst, bar="1H", seiten=5):
    """Mehr als 300 Kerzen, rueckwaerts geblaettert ueber history-candles."""
    alle, after = [], ""
    for _ in range(seiten):
        p = "/api/v5/market/history-candles?" + urllib.parse.urlencode(
            {"instId": inst, "bar": bar, "limit": 100})
        if after:
            p += "&after=" + after
        d = _mit_wiederholung(p)
        if not d:
            break
        r = [[int(x[0])] + [float(v) for v in x[1:6]] for x in d]
        alle += r
        after = str(min(x[0] for x in r))
    alle.sort(key=lambda r: r[0])
    return alle


def letzter_kurs(inst):
    d = _mit_wiederholung("/api/v5/market/ticker?instId=" + inst)
    return float(d[0]["last"])


def letzter_kurs_mit_fallback(inst, basis=None):
    """Kurs eines Kontrakts, der einen Rollover ueberlebt.

    XPERP-Kontrakte wechseln ihren instId: OKX legt den Kontrakt neu auf,
    der alte antwortet mit 51001 'Instrument ID doesn't exist' (am
    14.09.2026 bei XAU und BZ gesehen). Eine offene Position auf dem alten
    Kontrakt bliebe ohne diese Funktion ewig ohne Kurs - Stop und Ziel
    wuerden nie geprueft, der Papierbestand friert. Fallback: den lebenden
    Kontrakt desselben Basiswerts aufloesen und DESSEN Kurs nehmen. ctVal
    bleibt beim Rollover gleich (geprueft: XAU 0.001, BZ 0.01), die
    Positionsgroesse bleibt also gueltig.

    Rueckgabe: (inst_effektiv, kurs). inst_effektiv == inst, solange der
    Kontrakt nicht gewechselt hat. Jeder andere Fehler wird durchgereicht.
    """
    try:
        return inst, float(_mit_wiederholung(
            "/api/v5/market/ticker?instId=" + inst)[0]["last"])
    except OKXFehler as e:
        if not basis or "51001" not in str(e):
            raise
        neu = instrument(basis)
        if neu["instId"] == inst:
            raise
        d = _mit_wiederholung("/api/v5/market/ticker?instId=" + neu["instId"])
        return neu["instId"], float(d[0]["last"])


def tickers(inst_type="FUTURES"):
    """Alle Ticker eines Typs in einem Aufruf - Umsatz je Wert ohne 460 Anfragen.

    inst_type="SWAP" fuer die gewoehnlichen Perpetuals; Standard bleibt FUTURES
    (die XPERP).
    """
    d = _mit_wiederholung("/api/v5/market/tickers?instType=" + inst_type)
    return {x["instId"]: x for x in d}


def funding(inst):
    """Aktuelle Funding-Rate. Positiv = Long zahlt an Short."""
    try:
        d = _mit_wiederholung("/api/v5/public/funding-rate?instId=" + inst)
        return float(d[0].get("fundingRate") or 0.0)
    except (OKXFehler, IndexError, ValueError):
        return None


def rubik_basis():
    """Der Host fuer die Rubik-Statistikabrufe - siehe RUBIK_BASIS oben.

    Eigene Funktion, damit Aufrufer den Grund einer leeren Antwort nennen
    koennen (cvd.py tut das): 'leer' ohne Hostangabe laesst sich nicht deuten.
    """
    return (_variable("OKX_BASE_RUBIK") or RUBIK_BASIS).rstrip("/")


def taker_volumen(inst, period="4H"):
    """Aggressives Verkaufs- und Kaufvolumen je Zeit-Eimer, aufsteigend.

    Rueckgabe: [[ts, Verkaufsvolumen, Kaufvolumen], ...] - genau die Groesse,
    aus der eine CVD-Rechnung entsteht (kumulierte Differenz). period ist 5m,
    15m, 30m, 1H, 4H oder 1D; OKX liefert 100 Eimer je Anfrage, bei 4H also
    rund 16 Tage Tiefe. Einheit ist das Kontraktvolumen, so wie es auch in den
    Kerzen steht (die Summe beider Seiten eines Eimers deckt sich mit dem
    Volumen der entsprechenden Kerze - am 13.09.2026 nachgerechnet).

    Warum nicht das rohe Tape: /api/v5/market/history-trades liefert 100
    Trades je Anfrage, und 100 Trades sind bei BTC-USDT-SWAP 28 Sekunden
    (13.09.2026 gemessen, bei CHIP und WLFI dasselbe). Vier Stunden waeren
    rund 4000 Anfragen fuer einen einzigen Wert. Dieser Endpunkt ist derselbe
    Inhalt, von der Boerse bereits aggregiert.

    Zwei Fallen, beide echt erlebt:
      - Der Host: der Abruf geht ueber rubik_basis(), NICHT ueber OKX_BASE.
        Auf my.okx.com und eea.okx.com kommt code 0 mit leerer Liste zurueck.
      - Rubik drosselt strenger als der Marktdatenpfad. Ein 429 kommt als
        OKXFehler('50011 Too Many Requests'), und OKXFehler wird NICHT
        wiederholt. Aufrufer im Signalpfad fangen ihn und fallen auf "kein
        Signal" zurueck (Vorbild xperp/cvd.py).
    """
    d = _mit_wiederholung(
        "/api/v5/rubik/stat/taker-volume-contract?" +
        urllib.parse.urlencode({"instId": inst, "period": period}),
        basis=rubik_basis())
    reihen = [[int(r[0]), float(r[1]), float(r[2])] for r in d
              if len(r) >= 3]
    reihen.sort(key=lambda r: r[0])
    return reihen


# --- Kontraktgroessen -------------------------------------------------------

def kontrakte_aus_nominal(instr, nominal_usd, kurs):
    """Wieviele ganze Kontrakte ergeben rund 'nominal_usd' Positionswert?

    Gibt (kontrakte, echtes_nominal) zurueck. Das echte Nominal weicht ab -
    das ist keine Ungenauigkeit, sondern die Rundung auf lotSz, und sie gehoert
    in jede Rechnung uebernommen statt geschaetzt.
    """
    ctval = float(instr["ctVal"])
    lot = float(instr["lotSz"])
    minsz = float(instr["minSz"])
    je_kontrakt = ctval * kurs
    if je_kontrakt <= 0:
        return 0, 0.0
    roh = nominal_usd / je_kontrakt
    k = int(roh / lot) * lot
    if k < minsz:
        return 0, 0.0
    return k, k * je_kontrakt


def auf_tick(instr, preis):
    """Preis auf das Raster des Kontrakts runden."""
    tick = float(instr["tickSz"])
    if tick <= 0:
        return preis
    stellen = max(0, len(("%.10f" % tick).rstrip("0").split(".")[1]))
    return round(round(preis / tick) * tick, stellen)


# --- signiert: Konto --------------------------------------------------------

def guthaben_usdt():
    d = _mit_wiederholung("/api/v5/account/balance?ccy=USDT", signiert=True)
    if not d or not d[0].get("details"):
        return 0.0
    return float(d[0]["details"][0].get("availBal") or 0.0)


def positionen(inst=None):
    p = "/api/v5/account/positions?instType=FUTURES"
    if inst:
        p += "&instId=" + inst
    return _mit_wiederholung(p, signiert=True)


# --- signiert: Orders -------------------------------------------------------
#
# Diese Funktionen bewegen Geld. Sie werden von keinem Skript in diesem Ordner
# selbsttaetig aufgerufen - siehe Modulkopf.

def hebel_setzen(inst, hebel, tdmode="isolated", posside=None):
    body = {"instId": inst, "lever": str(hebel), "mgnMode": tdmode}
    if posside:
        body["posSide"] = posside
    return _roh("/api/v5/account/set-leverage", "POST", body, signiert=True)


def order_limit(inst, seite, kontrakte, preis, tdmode="isolated",
                posside=None, tp=None, sl=None, reduce_only=False):
    """Limit-Order mit angehaengtem Take-Profit und Stop-Loss.

    tp/sl werden als Ausloesepreise mitgegeben und als Market ausgefuehrt
    (ordPx -1). Ein Stop, der selbst ein Limit ist, fuellt im Absturz nicht.
    """
    body = {"instId": inst, "tdMode": tdmode, "side": seite,
            "ordType": "limit", "px": str(preis), "sz": str(kontrakte)}
    if posside:
        body["posSide"] = posside
    if reduce_only:
        body["reduceOnly"] = True
    anhang = {}
    if tp is not None:
        anhang["tpTriggerPx"] = str(tp)
        anhang["tpOrdPx"] = "-1"
    if sl is not None:
        anhang["slTriggerPx"] = str(sl)
        anhang["slOrdPx"] = "-1"
    if anhang:
        body["attachAlgoOrds"] = [anhang]
    d = _roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def markt_schliessen(inst, kontrakte, seite, tdmode="isolated", posside=None):
    """Eine offene Position sofort glattstellen - Market, reduceOnly.

    Gegenrichtung der Position: Ein Long wird verkauft, ein Short gekauft.
    reduceOnly verhindert, dass aus einem Tippfehler in der Richtung eine
    neue Position in die Gegenrichtung wird statt einer Schliessung.

    Market und nicht Limit, weil das hier der Notausstieg ist: Ein Limit, das
    im Absturz nicht fuellt, ist kein Ausstieg. Denselben Grund nennt schon
    order_limit() fuer seine Stop-Anhaenge.
    """
    gegen = "sell" if seite == "long" else "buy"
    body = {"instId": inst, "tdMode": tdmode, "side": gegen,
            "ordType": "market", "sz": str(kontrakte), "reduceOnly": True}
    if posside:
        body["posSide"] = posside
    d = _roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def order_stornieren(inst, ord_id):
    body = {"instId": inst, "ordId": ord_id}
    return _roh("/api/v5/trade/cancel-order", "POST", body, signiert=True)


def offene_orders(inst=None):
    p = "/api/v5/trade/orders-pending?instType=FUTURES"
    if inst:
        p += "&instId=" + inst
    return _mit_wiederholung(p, signiert=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    basis = sys.argv[1] if len(sys.argv) > 1 else "RE"
    x = instrument(basis)
    kurs = letzter_kurs(x["instId"])
    print("%s  (Basiswert %s)" % (x["instId"], x["uly"]))
    print("  Kurs %.6f   max. Hebel %s   Kontrakt %s %s   Tick %s   minSz %s" % (
        kurs, x["lever"], x["ctVal"], x["ctValCcy"], x["tickSz"], x["minSz"]))
    k, nom = kontrakte_aus_nominal(x, 250.0, kurs)
    print("  250 USD Nominal -> %g Kontrakte = %.2f USD (Rundung auf lotSz)" % (k, nom))
    print("  Funding %s   Schluessel gesetzt: %s" % (funding(x["instId"]),
                                                     schluessel_vorhanden()))
