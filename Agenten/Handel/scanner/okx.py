"""Zugang zu OKX - oeffentliche Kursdaten und (optional) signierte Orders.

Oeffentliche Endpunkte brauchen keinen Schluessel. Die signierten kommen erst
zum Einsatz, wenn handeln.py mit --live laeuft UND wachen.json handel_erlaubt
auf true steht UND die drei Schluessel gesetzt sind.

Zwei Fallen, aus Wissen/Handelsbots.md:
  - OKX antwortet ohne User-Agent mit HTTP 403. Deshalb HEADERS.
  - Fehlversuche zaehlen, sonst haengt eine Schleife bei einem Ausfall endlos.

Schluessel werden aus der Prozessumgebung gelesen, ersatzweise direkt aus der
Windows-Registry (HKCU\\Environment) - genauso wie es der Kraken-MCP macht,
weil ein von Claude gestarteter Prozess die Benutzervariablen nicht geerbt
bekommt (siehe Wissen/Verbindungen.md).
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


def _env(name):
    return os.environ.get(name) or None


def _live_basis():
    """Host fuer echte Orders: OKX_BASE (EEA/global), sonst www.okx.com.

    Wichtig: wie bei den Schluesseln mit REGISTRY-RUECKFALL (siehe _variable).
    Der Prozess erbt die Windows-Benutzervariablen naemlich nicht immer - aus
    einem MCP-Server oder einer geplanten Aufgabe gestartet fehlen sie. Dann
    fand der Schluessel ueber die Registry, der HOST aber fiel auf
    www.okx.com zurueck, und OKX antwortete mit 50119 "API key doesn't exist":
    gemessen am 23.09.2026, daran scheiterte der Verkauf ZEC-USDC. xperp und
    mosaic haben diesen Rueckfall seit laengerem - der scanner fehlte.
    """
    return (_variable("OKX_BASE") or "https://www.okx.com").rstrip("/")


# Echte Orders nutzen den LIVE-Key (OKX_LIVE_API_*), nie den DEMO-Key.
# Der Scanner hat keinen Demo-/Live-Schalter je Aufruf: paper rechnet einfach
# nur lokal, live signiert. Deshalb liest diese Datei fuer signierte Calls
# IMMER den Live-Key und den Basis-Host aus OKX_BASE.
LI = ("OKX_LIVE_API_KEY", "OKX_LIVE_API_SECRET", "OKX_LIVE_API_PASSPHRASE")

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
MAX_FEHLER = 6
# Wie oft eine Drosselung je Aufruf geheilt wird, bevor sie
# doch ein Fehler bleibt. OKX gibt das Zeitfenster frei, der
# Takt verhindert die naechste; danach ist die Spur fuer diesen
# Zyklus lahm, aber nicht tot - und das ist der Unterschied zu
# vorher, wo ein einzelner 429 den Zyklus beendete.
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
    """Fachlicher Fehler aus einer gueltigen OKX-Antwort (code != 0).
    Wird NICHT wiederholt - ein falscher instId wird beim zehnten Versuch
    auch nicht existieren."""


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
    # Fuer echte Orders massgeblich: der LIVE-Key. Der DEMO-Key genuegt nicht.
    return all(_variable(n) for n in LI)


# --- HTTP ------------------------------------------------------------------

def _roh(pfad, methode="GET", body=None, signiert=False):
    url = _live_basis() + pfad
    daten = json.dumps(body) if body else ""
    kopf = dict(HEADERS)

    if signiert:
        key = _variable(LI[0])
        secret = _variable(LI[1])
        pw = _variable(LI[2])
        if not (key and secret and pw):
            raise RuntimeError("OKX-LIVE-Schluessel fehlen (Key/Secret/Passphrase)")
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
        # OKX legt auch bei 4xx eine JSON-Antwort mit code/msg bei. Diese
        # Meldung ist die eigentliche Auskunft ("Order-Menge zu klein",
        # "Instrument ausgesetzt", ...) - ohne sie steht im Journal nur
        # "HTTP Error 400: Bad Request", und niemand weiss, was zu tun ist.
        #
        # ALLE 4xx als OKXFehler werfen, nicht nur 401/403: ein 400 ist eine
        # fachliche Ablehnung und heilt durch Wiederholen nicht. Vorher fiel
        # er durch und wurde von _mit_wiederholung als Transportfehler
        # dreimal erneut gesendet - bei einer Verkaufsorder ist das
        # gefaehrlich, weil jeder Versuch eine echte Order sein kann.
        if 400 <= e.code < 500:
            try:
                f = json.loads(e.read().decode())
            except (ValueError, AttributeError):
                f = {}
            # Einzelne Orderfehler stehen in data[0], nicht oben.
            erste = (f.get("data") or [{}])[0]
            oben_code = str(f.get("code") or "")
            tief_code = str(erste.get("sCode") or "")
            hinweis = ""
            if e.code in (401, 403):
                hinweis = " - Schluessel/Passphrase/IP pruefen"
            if "50119" in (oben_code, tief_code) or "50101" in (oben_code, tief_code):
                # 50119 "API key doesn't exist" / 50101 "does not match current
                # environment": der haeufigste Grund ist NICHT ein toter
                # Schluessel, sondern der falsche HOST - ein EEA-Schluessel am
                # globalen Host (siehe _live_basis).
                hinweis = (" - Schluessel/Host passen nicht zusammen. Dieser Prozess "
                           "spricht %s an, OKX_BASE aus der Registry ist %s. Ein "
                           "EEA-Schluessel am globalen Host gibt genau diesen Code."
                           % (_live_basis(), _variable("OKX_BASE") or "NICHT GESETZT"))
            if oben_code or f.get("msg"):
                detail = erste.get("sMsg") or f.get("msg") or ""
                code = tief_code or oben_code or "?"
                raise OKXFehler("OKX %s: %s (HTTP %d%s)"
                                % (code, detail, e.code, hinweis)) from None
            raise OKXFehler("OKX HTTP %d ohne Auskunft%s"
                            % (e.code, hinweis)) from None
        raise
    if d.get("code") not in ("0", 0):
        # OKX meldet Orderfehler mit HTTP 200 und code="1"; die eigentliche
        # Auskunft steht in data[0].sMsg ("Your order amount does not meet
        # the minimum order amount"), waehrend das aeussere msg nur "All
        # operations failed" sagt. Ohne sMsg steht im Journal eine Meldung,
        # aus der niemand ablesen kann, was zu tun ist.
        erste = (d.get("data") or [{}])[0]
        detail = erste.get("sMsg")
        code = erste.get("sCode") or d.get("code")
        if detail:
            raise OKXFehler("OKX %s: %s" % (code, detail))
        raise OKXFehler("OKX %s: %s" % (d.get("code"), d.get("msg") or d))
    return d.get("data", [])


def _mit_wiederholung(*a, **kw):
    """Drei Fehlerarten, drei Behandlungen.

    - OKXFehler MIT 50011/429: DROSSELUNG. Der einzige Fehler, der sich durch
      Warten heilt, darum wird er hier gefangen statt nach oben gegeben - vorher
      tötete er den ganzen Zyklus (43 Abbruche im Bus-Journal, 40 davon der
      scanner: 19.-20.09., 26.-29.09., 2.-5.10.). Der Aufrufer sieht statt
      eines Abbruchs die Daten, die es vor der Drosselung gab, oder eben keine.
    - OKXFehler OHNE 429: fachlich (falscher instId, zu kleine Menge). Ein
      zehnter Versuch aendert daran nichts, darum sofort werfen. Fuer eine
      Verkaufsorder ist Wiederholen sogar gefaehrlich: jeder Versuch kann eine
      echte Order sein.
    - alles andere: Transportfehler, wird gezaehlt und mit wachsender Pause
      wiederholt.

    Wichtig: der Wiederholpfad unterscheidet NICHT, ob geschrieben wird. Er
    heilt nur LESEabrufe gefahrlos. Beim Schreiben bleibt eine Drosselung ein
    Fehler - eine Order, die nicht abgesetzt wurde, wird nicht erfunden.
    """
    fehler = 0
    gedrosselt = 0
    while True:
        try:
            return _roh(*a, **kw)
        except OKXFehler as e:
            if not okx_takt.ist_429(e):
                raise              # fachlich, nicht durch Wiederholen zu heilen
            gedrosselt += 1
            if gedrosselt >= MAX_429:
                raise
            warten = okx_takt.warte_s(gedrosselt)
            print("  OKX gedrosselt (%d/%d) - warte %.1f s, kein Ausfall"
                  % (gedrosselt, MAX_429, warten),
                  file=sys.stderr)
            time.sleep(warten)
        except Exception as e:  # noqa: BLE001 - Transportfehler, wird gezaehlt
            fehler += 1
            if fehler >= MAX_FEHLER:
                raise
            print("  OKX-Transportfehler %d/%d: %s - wird wiederholt, kein Ausfall"
                  % (fehler, MAX_FEHLER, e),
                  file=sys.stderr)
            time.sleep(1.5 * fehler)


# --- oeffentlich ---------------------------------------------------------------

def kerzen(inst, bar="1D", anzahl=300):
    """Kerzen, aufsteigend sortiert als [ts, open, high, low, close, vol].

    OKX gibt hoechstens 300 je Abruf heraus. Wer mehr braucht, bekommt sie
    hier trotzdem: ueber `anzahl` groesser 300 blaettert die Funktion mit
    `after` rueckwaerts nach (aelter als der aelteste Stempel der Vorseite).

    Warum das noetig war: der MACD ueber mehrere Zeitrahmen braucht fuer den
    16er-Rahmen 34 Balken, also rund 544 Basiskerzen - mit 300 war dessen
    Ausrichtung IMMER None, die Bedingung "alle einig" also nie erfuellt und
    die Spur konnte nie handeln. Die Grenze lag nicht am Indikator, sondern
    am Abruf.
    """
    anzahl = max(1, int(anzahl))
    reihen, grenze = [], None
    while len(reihen) < anzahl:
        werte = {"instId": inst, "bar": bar, "limit": str(min(300, anzahl))}
        if grenze:
            werte["after"] = str(grenze)
        roh = _mit_wiederholung("/api/v5/market/candles?"
                                + urllib.parse.urlencode(werte))
        if not roh:
            break
        seite = [[int(r[0])] + [float(x) for x in r[1:6]] for r in roh]
        reihen += seite
        neu = min(int(r[0]) for r in seite)
        if grenze is not None and neu >= grenze:
            break                       # keine neuen Kerzen mehr
        grenze = neu
    # Doppelte Stempel weg (die Seitengrenze kann eine Kerze zweimal liefern)
    reihen = sorted({r[0]: r for r in reihen}.values(), key=lambda r: r[0])
    return reihen[-anzahl:]


def alle_paare(quote=None, min_volumen_usd=0.0):
    """Alle handelbaren Spot-Paare mit 24-h-Umsatz, absteigend nach Umsatz.

    Eine Abfrage fuer den ganzen Markt statt einer je Paar: die Prognose
    laeuft ueber hunderte Werte, und market/tickers liefert sie auf einmal.
    quote: Liste erlaubter Quote-Waehrungen (z. B. ["USDT"]), None = alle.
    Rueckgabe: [(instId, umsatz)], absteigend. Bei SPOT ist volCcy24h der
    Umsatz in der Quote-Waehrung - also bereits die Zahl, die zaehlt.
    """
    roh = _mit_wiederholung("/api/v5/market/tickers?instType=SPOT")
    aus = []
    for t in roh:
        inst = t.get("instId") or ""
        if "-" not in inst:
            continue
        q = inst.rsplit("-", 1)[1]
        if quote and q not in quote:
            continue
        try:
            umsatz = float(t.get("volCcy24h") or 0.0)
        except (TypeError, ValueError):
            continue
        if umsatz >= min_volumen_usd:
            aus.append((inst, umsatz))
    aus.sort(key=lambda x: x[1], reverse=True)
    return aus


def letzter_kurs(inst):
    pfad = "/api/v5/market/ticker?instId=" + inst
    d = _mit_wiederholung(pfad)
    return float(d[0]["last"])


# --- signiert (nur mit Schluessel + --live) --------------------------------

def guthaben(ccy="USDC"):
    """Frei verfuegbare Quote-Waehrung des Kontos.

    WAEHRUNG ist ein Parameter, weil der Kontostand und der Markt getrennt
    zu lesen sind: das Konto hatte am 02.10.2026 438 USDC und 0,00 USDT, waehrend
    die Wachen bis dahin "USDT" abfragten - die Antwort war 0,0 und sah wie
    ein leeres Konto aus. Ein Abruf, der eine Waehrung nennt, die es nicht
    gibt, ist kein leeres Konto, sondern ein falscher Abruf.

    Der Standard ist USDC, weil das die Quote ist, in der die Spur handelt
    (wachen.json: universum.quotes). EURC steht auf dem Konto, hat bei OKX
    aber keinen einzigen Spotmarkt (gemessen 02.10.2026: 0 Paare) - eine
    Waehrung ohne Markt ist kein Handelsweg.
    """
    d = _mit_wiederholung("/api/v5/account/balance?ccy=" + str(ccy), signiert=True)
    if not d or not d[0].get("details"):
        return 0.0
    return float(d[0]["details"][0].get("availBal") or 0.0)


def quote(inst):
    """Basiswaehrung eines Instruments aus seinem Namen ('BTC-USDC' -> USDC)."""
    teile = str(inst or "").split("-")
    return teile[-1] if len(teile) > 1 else ""


def guthaben_usdt():
    """Altnname. Liest USDT - auf Max' Konto 0,0, weil es kein USDT gibt.

    Bleibt erhalten, damit alte Aufrufer (guthaben_abgleich.py, Testattrappen)
    nicht brechen; wer eine Zahl fuer das echte Handelsguthaben braucht, ruft
    guthaben() mit der Quote der Wachen.
    """
    return guthaben("USDT")


def bestand(inst):
    """(eq, frei) des BESTANDS in der Basiswaehrung eines Paares.

    Fuer den Abgleich Buch <-> Boerse und fuer die Groesse eines Notausstiegs:
    eine conditional-Verkaufsorder darf nur ueber den wirklich gehaltenen
    Bestand laufen. Gelesen wird die Basiswaehrung aus dem Instrumentennamen
    ('BTC-USDC' -> 'BTC'); ein Fehler beim Lesen wirft - der Aufrufer
    entscheidet, ob er ohne die Zahl weitermacht. Am 26.09.2026 standen vier
    Live-Positionen ohne Stop, weil niemand den Bestand je nachgelesen hat.
    """
    ccy = inst.split("-")[0]
    d = _mit_wiederholung("/api/v5/account/balance?ccy=" + ccy, signiert=True)
    if not d or not d[0].get("details"):
        return 0.0, 0.0
    det = d[0]["details"][0]
    return (float(det.get("eq") or 0.0), float(det.get("availBal") or 0.0))


_REGELN = {}


def instrument_regeln(inst):
    """lotSz/tickSz/minSz eines Instruments (einmal je Lauf geholt)."""
    if inst not in _REGELN:
        typ = "SPOT" if "-" in inst and inst.count("-") == 1 else "SWAP"
        d = _mit_wiederholung("/api/v5/public/instruments?instType=%s&instId=%s"
                              % (typ, inst))
        _REGELN[inst] = d[0] if d else {}
    return _REGELN[inst]


def menge_gerundet(inst, menge):
    """Menge auf lotSz ABgerundet - eine Order ueber mehr als den Bestand
    lehnt OKX ab."""
    r = instrument_regeln(inst)
    lot = float(r.get("lotSz") or 0.0)
    if not lot:
        return round(menge, 8)
    stellen = max(0, len(("%.10f" % lot).rstrip("0").split(".")[-1]))
    return round(int(menge / lot) * lot, stellen)


def letzte_fuellung(inst, seite="sell"):
    """Juengste GEFUELLTE Order einer Seite ('buy'/'sell') oder None.

    Quelle fuer den ECHTEN Ausstiegspreis, wenn der Boersen-Stop ausgeloest
    hat oder von Hand verkauft wurde. Ohne diese Zahl wird nichts gebucht -
    ein geratener Kurs waere ein erfundenes Ergebnis.
    """
    d = _mit_wiederholung("/api/v5/trade/orders-history?instType=SPOT&instId=%s"
                          "&limit=50" % inst, signiert=True)
    treffer = [o for o in (d or [])
               if o.get("side") == seite
               and float(o.get("accFillSz") or 0) > 0]
    if not treffer:
        return None
    treffer.sort(key=lambda o: int(o.get("cTime") or 0), reverse=True)
    return treffer[0]


def markt_kauf(inst, usd):
    """Market-Kauf ueber einen festen Betrag in der Quote-Waehrung des Paares.

    T-311: Der Parameter hieß `usdt`, war aber ein Nominal in der Quote des
    Paares (tgtCcy quote_ccy). Auf dem EEA-Konto heisst die Quote USDC, nicht
    USDT - der Name war falsch und verwirrte bei der USDC-Umstellung.
    """
    body = {"instId": inst, "tdMode": "cash", "side": "buy",
            "ordType": "market", "sz": str(usd), "tgtCcy": "quote_ccy"}
    d = _roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def order_details(inst, ord_id):
    pfad = "/api/v5/trade/order?" + urllib.parse.urlencode(
        {"instId": inst, "ordId": ord_id})
    return _mit_wiederholung(pfad, signiert=True)[0]


def markt_verkauf(inst, basismenge):
    body = {"instId": inst, "tdMode": "cash", "side": "sell",
            "ordType": "market", "sz": str(basismenge)}
    d = _roh("/api/v5/trade/order", "POST", body, signiert=True)
    return d[0]["ordId"]


def stop_setzen(inst, basismenge, stop_preis):
    """Conditional-Order als Notausstieg. Loest als Market aus (slOrdPx -1)."""
    body = {"instId": inst, "tdMode": "cash", "side": "sell",
            "ordType": "conditional", "sz": str(basismenge),
            "slTriggerPx": str(stop_preis), "slOrdPx": "-1"}
    d = _roh("/api/v5/trade/order-algo", "POST", body, signiert=True)
    return d[0]["algoId"]


def stop_stornieren(algo_id, inst=None):
    """Den Notausstieg beim Handelsplatz abbestellen.

    Muss zu JEDEM Ausstieg gehoeren: eine Algo-Order, die keiner mehr kennt,
    bleibt im Buch und kann eine spaetere Position desselben Instruments zum
    alten Stoppreis verkaufen.

    ``inst`` ist PFLICHT - OKX verlangt bei ``cancel-algos`` das Feld instId
    und antwortet ohne es mit ``50014: Parameter instId can not be empty``
    (gemessen am 23.09.2026, mit instId kommt fuer dieselbe Order die richtige
    Auskunft). Deshalb geben ALLE Aufrufer das Instrument mit; fehlt es, holt
    :func:`stop_inst` es lesend nach.

    Ein Stop, den es nicht mehr gibt (OKX 51400: schon gefuellt, storniert oder
    nie existent), gilt als erledigt und wird NICHT als Fehler geworfen - sonst
    bliebe der Eintrag fuer immer in ``zustand.json`` liegen. Rueckgabe: die
    algoId, wenn wirklich storniert wurde, sonst None.
    """
    body = {"algoId": algo_id}
    if inst:
        body["instId"] = inst
    try:
        d = _roh("/api/v5/trade/cancel-algos", "POST", [body], signiert=True)
    except OKXFehler as e:
        if "51400" in str(e):
            return None                 # es gibt nichts mehr zu stornieren
        raise
    return (d[0].get("algoId") if d else None)


def stop_inst(algo_id):
    """Instrument einer Algo-Order, lesend erfragt.

    Fuer Alteintraege in ``zustand.json``, die noch kein ``inst`` tragen: ohne
    instId ist das Storno nicht moeglich (50014). Rueckgabe: instId oder None.
    """
    try:
        return (stop_details(algo_id) or {}).get("instId") or None
    except Exception:  # noqa: BLE001 - Leseprobe, kein Grund abzubrechen
        return None


def stop_details(algo_id):
    """Zustand einer Algo-Order (state, accFillSz).

    Der Pfad traegt die Abfrage im Query-String - OKX signiert genau diesen
    Pfad, deshalb geht die Abfrage durch dieselbe Signatur wie die Order.
    """
    d = _roh("/api/v5/trade/order-algo?algoId=%s" % algo_id, "GET", signiert=True)
    return (d[0] if d else {})


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    inst = sys.argv[1] if len(sys.argv) > 1 else "BTC-USDT"
    k = kerzen(inst)
    print("%s: %d Tageskerzen, %s bis %s" % (
        inst, len(k),
        time.strftime("%Y-%m-%d", time.localtime(k[0][0] / 1000)),
        time.strftime("%Y-%m-%d", time.localtime(k[-1][0] / 1000))))
    print("letzter Schluss: %.4f" % k[-1][4])
    print("Schluessel gesetzt:", schluessel_vorhanden())
