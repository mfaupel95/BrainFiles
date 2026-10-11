"""Kraken-FUTURES-REST-Orderweg (derivatives/api/v3) fuer nautilus_kraken_futures.

Gegenstueck zu kraken/kraken.py - aber eine ANDERE Schnittstelle: Kraken
Futures ist nicht die Spot-API mit anderem Host, sondern ein eigener Dienst
mit eigener Signatur:

  * Basis  https://futures.kraken.com/derivatives/api/v3
  * Kopf   APIKey, Nonce, Authent
  * Authent = base64(HMAC-SHA512(base64decode(secret),
                      SHA256(postData + nonce + "/api/v3" + pfad)))
    Der Signaturpfad traegt KEIN "/derivatives" - gemessen am 24.09.2026:
    mit "/derivatives/api/v3/..." antwortet Kraken "Authentication error".
  * Zugangsdaten KRAKEN_FUTURE_API_KEY/SECRET aus HKCU\\Environment
    (eigener Schluesselsatz; die Spot-Keys gelten hier nicht und umgekehrt).

Einheiten: Die Futures-Order nimmt KONTRAKTE. Bei PF_XBTUSD ist
contractSize 1, also 1 Kontrakt = 1 USD Nominal. Der Live-Zweig von
handeln.py uebergibt aber die Menge der Kopier-Spur in BTC - deshalb
rechnet markt_kauf/markt_verkauf hier um (BTC x Kurs -> Kontrakte).

Nur Standardbibliothek. Kein Nautilus-Orderpfad (Adapter liest keine Fills,
postxid-Bug 24.09.2026).
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

BASIS = "https://futures.kraken.com/derivatives/api/v3"
SIGNATUR_PRAEFIX = "/api/v3"
KEY_NAME = "KRAKEN_FUTURE_API_KEY"
SECRET_NAME = "KRAKEN_FUTURE_API_SECRET"

_instrument_cache = {}
_hebel_cache = {"zeit": None, "werte": None}
HEBEL_CACHE_SEKUNDEN = 60.0


class KrakenFuturesFehler(RuntimeError):
    pass


def _env(name):
    """Windows-Benutzervariable, mit Registry-Rueckfall (Hausmuster).

    Ein Kindprozess, der die Umgebung nicht geerbt hat, findet den Schluessel
    sonst nicht - und ein Schluessel ohne Host (oder umgekehrt) ist der halbe
    Zugang (Lektion aus dem OKX-50119-Fall).
    """
    wert = os.environ.get(name)
    if wert:
        return wert
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def schluessel_vorhanden():
    return bool(_env(KEY_NAME) and _env(SECRET_NAME))


def _nonce():
    """Millisekunden. Kraken Futures kennt je Schluessel nur STEIGENDE Werte."""
    return str(int(time.time() * 1000))


def _signatur(pfad, post_data, nonce):
    nachricht = (post_data + nonce + SIGNATUR_PRAEFIX + pfad).encode()
    abschnitt = hashlib.sha256(nachricht).digest()
    mac = hmac.new(base64.b64decode(_env(SECRET_NAME)), abschnitt, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode()


def _roh(pfad, werte=None, signiert=True, post=False, methode=None,
         fehler_erlauben=False):
    """Ein Aufruf. `werte` als Dict = POST mit Formkoerper (Reihenfolge zaehlt!).

    Die Reihenfolge der Felder muss der Signatur entsprechen, deshalb wird der
    Koerper EINMAL gebaut und unveraendert gesendet (nicht neu formatiert).
    Lesende Aufrufe (/accounts, /openpositions) sind GET - ein GET-Koerper
    waere ein POST und lief 24.09.2026 in HTTP 404 NOT_FOUND.
    `methode` erzwingt ein anderes Verfahren (PUT bei /leveragepreferences,
    GEMESSEN 01.10.2026: die Parameter muessen dort als FORMKOEPRER rein - als
    Query-String antwortet dieselbe Signatur mit authenticationError).

    `fehler_erlauben=True` (NUR fuer Order-Aufrufe): Kraken antwortet bei
    /sendorder und /transfer gelegentlich mit `result: "error"` und
    `authenticationError`, obwohl die Order GEFUELLT wurde (gemessen 01.10.2026,
    zwei Probe-Kaeufe). Die Antwort wird dann zurueckgegeben statt geworfen,
    damit der Aufrufer die echte sendStatus lesen kann. Ein ECHTER Fehler
    (keine sendStatus mit placed) wird weiterhin laut erhoben.
    """
    post_data = urllib.parse.urlencode(werte) if werte else ""
    kopf = {"User-Agent": "BrainFiles/1.0"}
    daten = None
    if signiert:
        if not schluessel_vorhanden():
            raise KrakenFuturesFehler(
                "KRAKEN_FUTURE_API_KEY/SECRET fehlen (%s)" % KEY_NAME)
        nonce = _nonce()
        kopf.update({"APIKey": _env(KEY_NAME), "Nonce": nonce,
                     "Authent": _signatur(pfad, post_data, nonce)})
        if post or methode:
            kopf["Content-Type"] = "application/x-www-form-urlencoded"
            daten = post_data.encode()
    verfahren = methode or ("POST" if daten is not None else "GET")
    req = urllib.request.Request(BASIS + pfad, data=daten, headers=kopf,
                                 method=verfahren)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            antwort = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        text = e.read().decode(errors="replace")
        raise KrakenFuturesFehler("HTTP %s: %s" % (e.code, text[:300])) from None
    if isinstance(antwort, dict) and antwort.get("result") == "error":
        if fehler_erlauben:
            return antwort
        fehler = antwort.get("errors") or antwort.get("error")
        raise KrakenFuturesFehler("Kraken Futures meldet: %s" % (fehler,))
    return antwort


# --- oeffentlich ------------------------------------------------------------

def instrument(symbol):
    """Kontraktdaten (tickSize, contractSize, pair) - einmal je Lauf geholt."""
    if symbol not in _instrument_cache:
        daten = _roh("/instruments", signiert=False)
        for i in daten.get("instruments", []):
            _instrument_cache[i.get("symbol")] = i
    return _instrument_cache.get(symbol) or {}


def letzter_kurs(symbol):
    """Letzter Handelspreis (oeffentlich, /tickers)."""
    daten = _roh("/tickers", signiert=False)
    for t in daten.get("tickers", []):
        if t.get("symbol") == symbol:
            kurs = t.get("last")
            if kurs in (None, 0, 0.0):
                raise KrakenFuturesFehler("kein Kurs fuer %s" % symbol)
            return float(kurs)
    raise KrakenFuturesFehler("Symbol %s nicht in /tickers" % symbol)


def _stellen_aus_tick(tick):
    """Nachkommastellen aus dem tickSize - auch bei 1e-05.

    ANLASS (gemessen 02.10.2026, T-282): Die alte Fassung las die Stellen aus
    `str(tick)` und suchte einen Punkt. Kleine Werte schreibt Python aber in
    Exponentialschreibweise - `str(1e-05)` ist "1e-05", OHNE Punkt. Ergebnis:
    0 Stellen, und aus dem HBAR-Stop 0.090693 wurde die Zeichenkette "0". Die
    Boerse wies die Order mit `invalidArgument` ab; die Spur kaufte und rollte
    jeden Zyklus zurueck (echte Gebuehren, kein Einstieg).
    Decimal kennt die Exponentialform und liefert den Exponenten direkt.
    """
    try:
        from decimal import Decimal, InvalidOperation
        exponent = Decimal(str(tick)).normalize().as_tuple().exponent
        return max(0, -int(exponent))
    except (ArithmeticError, InvalidOperation, TypeError, ValueError):
        return 0


def preis_gerundet(symbol, preis, richtung="auf"):
    """Auf tickSize runden und als Text zurueckgeben.

    Ein roher Rechenwert wird abgelehnt - im Spot-Zweig kostete das den
    Notausstieg ('price can only be specified up to N decimals'). 'auf'
    rundet von der Null weg (Long-Stop nie tiefer als gerechnet), 'ab'
    zur Null hin. tickSize 1 bei PF_XBTUSD.

    Ein gerundeter Preis von 0 ist ein FEHLER, keine Order: er entstuende nur
    aus einer falsch gelesenen Stellenzahl und waere an der Boerse ungueltig.
    Lieber laut abbrechen als eine Null senden.
    """
    tick = float(instrument(symbol).get("tickSize") or 1.0)
    if tick <= 0:
        tick = 1.0
    schritte = float(preis) / tick
    ganz = int(schritte) if richtung == "ab" else int(schritte + 0.999999999)
    stellen = _stellen_aus_tick(tick)
    wert = ganz * tick
    if wert <= 0 and float(preis) > 0:
        raise KrakenFuturesFehler(
            "gerundeter Preis ist 0 (Preis %r, tickSize %r) - diese Order "
            "waere ungueltig" % (preis, tick))
    return ("%%.%df" % stellen) % wert


def kontrakte(symbol, menge, kurs=None):
    """Menge in BASIS-Einheiten -> Kontraktzahl.

    GEMESSEN 25.09.2026 (nicht aus der Doku geschlossen): **1 Kontrakt ist EINE
    Einheit der Basiswaehrung.** Belege aus einem echten Handel:
      * 1 Kontrakt PF_NEARUSD gefuellt bei 4,5517 USD belegte 0,4548 USD Marge
        (10 % Einschuss nach `marginSchedules.europa.retail`, also 10 % von
        4,5517) - nicht 1 USD Nennwert.
      * 1 Kontrakt PF_XBTUSD wurde mit 141,59 USD freiem Guthaben abgelehnt
        (`insufficientAvailableFunds`): 1 Kontrakt = 1 BTC = rund 84.500 USD,
        Einschuss 10 % = rund 8.450 USD.
    `contractSize` im Instrumentenrecod ist bei ALLEN PF_-Maerkten 1 und sagt
    ueber die Groesse nichts - die Margenstufe (`marginSchedules`) und die
    Basiswaehrung (`base`) sind die Quelle.

    Folge fuer die Spuren: der kleinste handelbare Satz ist 1 Kontrakt, und der
    kostet bei PF_XBTUSD rund 1 BTC. Eine BTC-Menge aus einem Kopiersignal
    (0,0001 BTC) ist damit NICHT abbildbar - wer BTC handeln will, braucht ein
    Konto in der Groessenordnung der Mindestmarge (siehe `einschuss()`).

    Mindestens 1 Kontrakt: eine 0 waere keine Order.
    """
    del kurs                                     # nur aus Vertraeglichkeit
    return max(1, int(round(float(menge))))


def einschuss(symbol, kontrakte, kurs=None, hebel=None):
    """Einschuss (USD) fuer N Kontrakte - das STRENGERE von Plan und Hebel.

    Reihenfolge: `marginSchedules.europa.retail` (unser Konto ist EEA), erster
    Abschnitt mit `numNonContractUnits` 0; fehlt der Plan, wird der hoechste
    Satz genommen (konservativ). Nennwert = kontrakte x kurs (1 Kontrakt = 1
    Einheit der Basiswaehrung).

    Der PLAN allein ist zu wenig (Befund T-285, 01.10.2026): er sagt, was die
    Boerse ohne eigene Hebel-Obergrenze verlangt (EEA retail 10 %). Der Hebel
    dieses Kontos steht in `/leveragepreferences` JE KONTRAKT - und dort steht
    die Margin, die wirklich gebunden wird (Margin = Nennwert / Hebel).
    Gemessen: PF_SOLUSD laeuft mit 7x, also 16,88 USD je Kontrakt statt der
    11,81 USD aus dem Plan; PF_CSPRUSD mit 3,09x, also 32 % statt 10 % - der
    Plan unterschaetzte hier um Faktor 3. Genommen wird deshalb das Maximum:
    eine zu kleine Reserve scheitert erst am Konto, eine zu grosse kostet nur
    einen Platz, den die Sperrenkette ohnehin prueft.
    """
    if kurs is None:
        kurs = letzter_kurs(symbol)
    daten = instrument(symbol)
    plan = ((daten.get("marginSchedules") or {}).get("europa") or {}).get("retail")
    if not plan:                                  # anderer Markt / aeltere Form
        plan = daten.get("retailMarginLevels") or daten.get("marginLevels") or []
    satz = None
    for stufe in plan:
        if float(stufe.get("numNonContractUnits") or 0.0) == 0.0:
            satz = float(stufe.get("initialMargin") or 0.0)
            break
    if satz is None:
        satz = max((float(s.get("initialMargin") or 0.0) for s in plan), default=0.0)
    if hebel is None:
        hebel = hebel_je_kontrakt(symbol)
    try:
        if hebel and float(hebel) > 0:
            satz = max(satz, 1.0 / float(hebel))
    except (TypeError, ValueError):
        pass                                      # unlesbarer Hebel = Plan gilt
    return kontrakte * float(kurs) * satz


def handelbar(symbol, kontrakte=1, frei=None):
    """Reicht das freie Guthaben fuer den kleinsten Satz? (Grund oder None)"""
    if frei is None:
        frei = guthaben("usd")
    noetig = einschuss(symbol, kontrakte)
    if frei < noetig:
        return ("1 Kontrakt %s braucht %.2f USD Einschuss, frei sind %.2f USD"
                % (symbol, noetig, frei))
    return None


# --- signiert ---------------------------------------------------------------

def guthaben(waehrung="usd"):
    """Freies Guthaben im Futures-Konto.

    ZWEI KONTENFORMEN, gemessen 25.09.2026: ein multiCollateral-Konto legt das
    Geld in den Block 'flex' (availableMargin, currencies.<CCY>.available) und
    laesst 'cash.balances' auf 0,0 stehen. Die alte Lesart - nur cash - meldete
    deshalb 0,0, obwohl 141,59 USD verfuegbar waren: das Guthaben-Tor der Spur
    war dauerhaft zu, ohne dass es auffiel. Reihenfolge deshalb: flex zuerst,
    sonst cash (reines Cash-Konto, z. B. Demo).
    """
    w = str(waehrung).lower()
    konten = _roh("/accounts").get("accounts") or {}
    flex = konten.get("flex") or {}
    if flex:
        if w == "usd":
            wert = flex.get("availableMargin")
            if wert is None:
                wert = ((flex.get("currencies") or {}).get("USD") or {}).get(
                    "available")
            return float(wert or 0.0)
        return float(((flex.get("currencies") or {}).get(w.upper()) or {}).get(
            "available") or 0.0)
    cash = konten.get("cash") or {}
    bal = (cash.get("balances") or {}).get(w)
    return float(bal or 0.0)


def offene_positionen(symbol=None):
    daten = _roh("/openpositions")
    liste = daten.get("openPositions") or []
    if symbol:
        liste = [p for p in liste if p.get("symbol") == symbol]
    return liste


def offene_orders(symbol=None):
    daten = _roh("/openorders")
    liste = daten.get("openOrders") or []
    if symbol:
        liste = [o for o in liste if o.get("symbol") == symbol]
    return liste


def gefuellte_menge(order_id, sekunden=30.0, abstand=3.0):
    """Gefuellte Kontrakte zu einer OrderKennung (ueber /fills), mit Warten.

    Zwei Fehler, beide am 01.10.2026 mit Geldfolge (T-306):

    1. `/fills` ist beim Kauf noch nicht gefuellt. Ein sofortiges Lesen gab 0
       bzw. einen Bruchteilwert; der Aufrufer rechnete `int(0.4)` = 0 und
       bestellte einen Stop mit `size: 0`. Kraken antwortete
       `invalidArgument: 0`, und die "Rueckdrehung" wurde ebenfalls mit
       Groesse 0 abgeschickt - sie blieb wirkungslos, wurde aber als
       Erfolg gemeldet. 5706 Kontrakte standen danach ohne Schutz an der
       Boerse.
    2. 0 ist hier ein echter Messwert, wird aber als "unbekannt" gelesen.
       Deshalb: `standard=None` unterscheidet "nicht lesbar" von "0".

    Rueckgabe: (kontrakte, bestaetigt). `bestaetigt=False` heisst: die Boerse
    hat die Fuellung nicht bestaetigt - der Aufrufer MUSS dann mit der
    bestellten Groesse weiterarbeiten und die Bestaetigung offen melden, NICHT
    mit 0.
    """
    ende = time.time() + max(0.0, sekunden)
    while True:
        try:
            daten = _roh("/fills?lastFillTime=1970-01-01T00:00:00Z")
        except KrakenFuturesFehler as e:
            print("  Fuellungsabfrage nicht lesbar: %s" % e, file=sys.stderr)
            daten = {}
        menge = 0.0
        for f in daten.get("fills") or []:
            if f.get("order_id") == order_id:
                menge += float(f.get("size") or 0.0)
        if menge > 0:
            # GANZZAHL, und mindestens 1: ein Kontrakt ist die kleinste
            # handelbare Einheit. `int(0.4)` == 0 war der Ausloeser.
            return max(1, int(round(menge))), True
        if time.time() >= ende:
            return 0, False
        time.sleep(abstand)


def order_stornieren(order_id):
    return _roh("/cancelorder", {"order_id": order_id}, post=True)


def _order_aufgeben(werte):
    """Order senden und die Kennung zurueckgeben.

    Kraken antwortet zweistufig: result=success, sendStatus.status=placed,
    sendStatus.order_id. Steht dort ein Fehler, wird er laut erhoben -
    ein stilles 'success' ohne Order waere die gefaehrlichste Form.

    GEMESSEN 01.10.2026: /sendorder kann `result: "error"` mit
    `authenticationError` zurueckgeben, obwohl die Order GEFUELLT wurde (zwei
    Probe-Kaeufe). Deshalb `fehler_erlauben=True`: die Antwort wird gelesen,
    und die sendStatus entscheidet - steht dort 'placed', ist die Order da,
    egal was result sagt. Ein ECHTER Fehler (keine placed-sendStatus) wird
    weiterhin laut erhoben.
    """
    antwort = _roh("/sendorder", werte, post=True, fehler_erlauben=True)
    status = antwort.get("sendStatus") or {}
    if status.get("status") not in ("placed", None):
        grund = status.get("status") or status.get("reason") \
            or antwort.get("errors") or antwort.get("error")
        raise KrakenFuturesFehler("Order nicht angenommen: %s" % grund)
    kennung = status.get("order_id") or (status.get("orderEvents") or [{}])[0].get("orderId")
    if not kennung:
        raise KrakenFuturesFehler("Kraken nennt keine Orderkennung: %s" % antwort)
    return kennung


def markt_kauf(symbol, menge, echt=False, leverage=None):
    """Kaufen (long). `menge` ist die BTC-Menge der Kopier-Spur.

    `leverage` (optional) geht als leverage-Parameter an /sendorder - ohne ihn
    setzt die Boerse den hoechstmoeglichen Hebel des Margenplans, nicht 1x.
    """
    if not echt:
        return "TROCKENLAUF-kauf-%s-%s" % (symbol, menge)
    groesse = kontrakte(symbol, menge)
    werte = {"orderType": "mkt", "symbol": symbol,
             "side": "buy", "size": groesse}
    if leverage:
        werte["leverage"] = "%g" % float(leverage)
    return _order_aufgeben(werte)


def markt_verkauf(symbol, menge, echt=False):
    """Verkaufen (Ausstieg). Gegen eine bestehende Long-Position reduceOnly.

    reduceOnly verhindert, dass ein Ausstieg versehentlich eine neue
    Short-Position aufmacht, wenn der Bestand inzwischen kleiner ist.
    """
    if not echt:
        return "TROCKENLAUF-verkauf-%s-%s" % (symbol, menge)
    groesse = kontrakte(symbol, menge)
    werte = {"orderType": "mkt", "symbol": symbol, "side": "sell",
             "size": groesse}
    hat_long = any(p.get("side") == "long" for p in offene_positionen(symbol))
    if hat_long:
        werte["reduceOnly"] = "true"
    return _order_aufgeben(werte)


def stop_setzen(symbol, menge, stop_preis, echt=False, leverage=None):
    """Schutz-Stop als eigene Order an der Boerse (ueberlebt Neustarts).

    orderType 'stp', Gegenseite der Position, reduceOnly: Die Order schliesst
    nur, sie eroeffnet nie. Bei PF_XBTUSD rundet tickSize auf ganze USD.
    """
    if not echt:
        return "TROCKENLAUF-stop-%s-%s" % (symbol, stop_preis)
    groesse = kontrakte(symbol, menge)
    seite = "sell"
    for p in offene_positionen(symbol):
        if p.get("side") == "short":
            seite = "buy"
            break
    return _order_aufgeben({"orderType": "stp", "symbol": symbol,
                            "side": seite, "size": groesse,
                            "stopPrice": preis_gerundet(symbol, stop_preis),
                            "reduceOnly": "true", "triggerSignal": "mark"})


def hebel_preference_lesen():
    """Alle leverage-Preferences je Kontrakt: [(symbol, maxLeverage)]."""
    try:
        r = _roh("/leveragepreferences", post=False)
    except KrakenFuturesFehler:
        return []
    return [(p.get("symbol"), p.get("maxLeverage"))
            for p in (r.get("leveragePreferences") or []) if p.get("symbol")]


def hebel_je_kontrakt(symbol=None, jetzt=None):
    """Die Hebel-Obergrenze JE KONTRAKT aus /leveragepreferences (lesend).

    Ohne `symbol` kommt das ganze Verzeichnis zurueck, mit `symbol` der Wert
    dieses Kontrakts oder None. Das Ergebnis wird HEBEL_CACHE_SEKUNDEN lang
    gehalten: `einschuss()`/`handelbar()` fragen im Zyklus mehrfach, und jede
    Abfrage ist ein signierter Aufruf an die Boerse.

    GEMESSEN 01.10.2026 am echten Konto: die Preferences sind je Kontrakt
    verschieden (PF_SOLUSD 7, PF_HBARUSD 10, PF_CSPRUSD 3,09) - es gibt keine
    Kontoeinstellung "Hebel", sondern nur diese Tabelle. Ein Kontrakt ohne
    Eintrag laeuft mit dem Margenplan des Marktes.
    """
    jetzt = time.monotonic() if jetzt is None else float(jetzt)
    frisch = (_hebel_cache["werte"] is None
              or _hebel_cache["zeit"] is None
              or jetzt - _hebel_cache["zeit"] > HEBEL_CACHE_SEKUNDEN)
    if frisch:
        try:
            werte = {s: float(h) for s, h in hebel_preference_lesen() if h}
        except Exception:                                         # noqa: BLE001
            werte = _hebel_cache["werte"] or {}
        _hebel_cache["werte"] = werte
        _hebel_cache["zeit"] = jetzt
    werte = _hebel_cache["werte"] or {}
    if symbol is None:
        return dict(werte)
    return werte.get(symbol)


def hebel_preference_setzen(symbol, hebel):
    """Hebel-Obergrenze je Kontrakt setzen (isolated margin).

    GEMESSEN 01.10.2026 am echten Konto: der `leverage`-Parameter der
    /sendorder-Order wird ignoriert - der Hebel steht AUSSERHALB der Order, in
    /leveragepreferences (PUT, Parameter als FORMKOEPRER; als Query-String
    antwortet dieselbe Signatur mit authenticationError). Wirkung belegt:
    Margin je Kontrakt PF_SOLUSD 11,79 USD (10 %) -> 16,80 USD = Nominal/7.
    """
    if not (1.0 <= float(hebel)):
        raise KrakenFuturesFehler("Hebel %r unter 1 - nicht setzen" % hebel)
    _roh("/leveragepreferences", {"symbol": symbol, "maxLeverage": "%g" % float(hebel)},
         post=False, methode="PUT")
    gesetzt = dict(hebel_preference_lesen()).get(symbol)
    if not gesetzt or float(gesetzt) < float(hebel) - 1e-9:
        raise KrakenFuturesFehler(
            "Preference nicht gesetzt: %s = %r (Wunsch %s)" % (symbol, gesetzt, hebel))
    return float(gesetzt)


def stop_nachziehen(order_id, symbol, menge, stop_preis, echt=False):
    """Schutz-Stop auf einen neuen Preis ziehen (/editorder).

    Trailing-Stop an der Boerse: der alte Preis bleibt stehen, bis die
    geaenderte Order angenommen ist - kein Fenster ohne Schutz. `size` geht mit,
    weil /editorder die Groesse der Order neu setzt und nur orderId Pflicht ist;
    der Aufrufer reicht die Menge der Position durch.
    """
    if not echt:
        return "TROCKENLAUF-edit-%s-%s" % (order_id, stop_preis)
    groesse = kontrakte(symbol, menge)
    return _order_aufgeben({"orderId": str(order_id), "symbol": symbol,
                            "size": groesse,
                            "stopPrice": preis_gerundet(symbol, stop_preis)})