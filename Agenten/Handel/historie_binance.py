"""Historische Kerzen und Funding-Saetze fuer den Backtest.

Quelle ist Binance (offen, kein Schluessel, 1000 Kerzen je Abruf, 1H zurueck
bis 2017-08-17). Binance ist ein PROXY fuer die Boersen der Spuren (OKX,
Kraken): die Kerzen sind nicht der Kurs der Spur, und jedes Ergebnis traegt
deshalb `kerzenquelle: binance`.

Ablage: daten/historie/<SYM>_<takt>.json, Reihen [ts_ms, o, h, l, c, v],
aufsteigend, ts als int und die fuenf Werte als float - GENAU die Form, die
scanner/okx.kerzen() liefert. Nur so passen die Kerzen ohne Adapter in die
Naehte der Spuren.

Gesperrt in .gitignore: daten/historie/ ist reproduzierbar und gross.

Aufruf:
    python historie.py --auffuellen --instrumente BTC-USDC,ETH-USDC --takte 1H,4H
    python historie.py --stand
"""

import json
import os
import time
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(HIER, "daten", "historie")

TAKTE = {"5M": "5m", "15M": "15m", "30M": "30m", "1H": "1h", "4H": "4h", "1D": "1d"}


class HistorieKaputt(Exception):
    """Die Datei ist da, aber kein gueltiges JSON.

    Getrennt von OSError/ValueError, weil beides etwas anderes bedeutet:
    OSError = fehlt (dann ist [] richtig), HistorieKaputt = da, aber unlesbar
    (dann ist [] eine Falschaussage und der Aufrufer muss es erfahren).
    """

# OKX- und Kraken-Namen der Spuren -> Binance-Symbol. EIN Ort, damit nicht
# jede Spur ihr eigenes Mapping erfindet. Gemessen 2026-09-24: 19 von 20
# geprueften Instrumenten haben ein Binance-USDT-Paar; MATIC fehlt (heute POL).
#
# 03.10.2026 (T-322/spur_audit): die Tabelle kannte nur 30 NAMES und damit
# nur drei BISWERTEN - BTC, ETH, SOL. Deshalb war eine ehrliche Edge-Messung
# fuer jede andere Spur nicht moeglich: die Basislinie fehlte schlicht. Der
# Befund, der das aufdeckte, war nicht die Messung, sondern ihre Abwesenheit.
# `basisform()` in spur_audit.py leitet den Basiswert aus jedem
# OKX-Kontraktnamen ab, deshalb genuegt hier der Basiswert je Name.
# Nachgetragen (Binance-klines gegen jeden Kandidaten geprueft, 42 von 58 mit
# USDT-Paar): AAVE ADA AERO AI ALGO APT ARB AVAX BONK CRV DRV ETC GRT
# HYPE ICP INJ IOST LIT MAGIC MARSCOIN NIGHT ONDO QNT RENDER STX TRX UNI
# WLFI XLM ZRO FF 2Z
#
# Was hier FEHLT und auch fehlen bleibt, ist Absicht: CL, BZ, CRCL, XAU, XAG,
# META, MSTR, UNITREE, VVV, CARDS, CASHCAT, FARTCOIN, BTW, BP, GRASS,
# OKB, XDC, DRV-Marktplaetze sind Aktien-ETPs oder Pump-Token ohne
# belastbare USDT-Historie. Sie bekommen KEIN Ersatzinstrument - eine
# Basislinie aus einem aehnlichen Markt waere eine erfundene.
# 07.10.2026 (T-338): QQQ ist seit dem 07.10.2026 EXPLIZIT EINGESCHLOSSEN -
# Binance fuehrt QQQBUSDT (gemessen an /api/v3/klines am 07.10.2026), die
# Rotation QQQ/BTC/Cash (T-210) ist damit auf eigenen Daten messbar.
PAARE = {
    "BTC-USDC": "BTCUSDT", "BTC-USDT": "BTCUSDT", "BTC-USDT-SWAP": "BTCUSDT",
    "XBT/USD": "BTCUSDT", "BTC/USD": "BTCUSDT", "BTC_USDT": "BTCUSDT",
    "ETH-USDC": "ETHUSDT", "ETH-USDT": "ETHUSDT", "ETH_USDT": "ETHUSDT",
    "SOL-USDC": "SOLUSDT", "SOL-USDT": "SOLUSDT",
    # Die bare Form der drei grossen - die Funding-Spur fuehrt "BTC"/"ETH"/"SOL"
    # so, und ohne diese Zeilen faellt sie beim Laden mit KeyError um.
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "HYPE": "HYPEUSDT", "FIL": "FILUSDT", "ZEC": "ZECUSDT", "UNI": "UNIUSDT",
    "ARB": "ARBUSDT", "DOGE": "DOGEUSDT", "XRP": "XRPUSDT", "APT": "APTUSDT",
    "STRK": "STRKUSDT", "DOT": "DOTUSDT", "HBAR": "HBARUSDT",
    "NEAR": "NEARUSDT", "AVAX": "AVAXUSDT", "BNB": "BNBUSDT",
    "LINK": "LINKUSDT", "ADA": "ADAUSDT", "SUI": "SUIUSDT",
    "LTC": "LTCUSDT", "ATOM": "ATOMUSDT", "OP": "OPUSDT",
    "AAVE": "AAVEUSDT", "AERO": "AEROUSDT", "AI": "AIUSDT",
    "ALGO": "ALGOUSDT", "BONK": "BONKUSDT", "CRV": "CRVUSDT",
    "ETC": "ETCUSDT", "GRT": "GRTUSDT", "ICP": "ICPUSDT",
    "INJ": "INJUSDT", "IOST": "IOSTUSDT", "LIT": "LITUSDT",
    "MAGIC": "MAGICUSDT", "MARSCOIN": "MARSCOINUSDT",
    "NIGHT": "NIGHTUSDT", "ONDO": "ONDOUSDT", "QNT": "QNTUSDT",
    "RENDER": "RENDERUSDT", "STX": "STXUSDT", "TRX": "TRXUSDT",
    "WLFI": "WLFIUSDT", "XLM": "XLMUSDT", "ZRO": "ZROUSDT",
    "FF": "FFUSDT", "2Z": "2ZUSDT",
    # 07.10.2026 (T-338): QQQ explizit eingeschlossen - Binance fuehrt das
    # Paar QQQBUSDT (gemessen), der Aktien-ETP-Ausschluss oben ist fuer QQQ
    # aufgehoben. Gespeichert wird damit QQQBUSDT_1D.json.
    "QQQ": "QQQBUSDT",
}

_BASIS = "https://api.binance.com"
_FUTURES = "https://fapi.binance.com"
_GRENZE = 1000                     # Binance liefert hoechstens 1000 je Abruf


def symbol(inst):
    """Binance-Symbol zu einem Spur-Instrument.

    Ein unbekanntes Paar ist ein HARTER Fehler, kein stiller Ersatz: wer hier
    ersatzweise handelt, backtestet ein anderes Instrument als die Spur.
    """
    s = PAARE.get(str(inst).strip().upper())
    if not s:
        raise KeyError("kein Binance-Paar fuer %r - bekannte Namen: %s"
                       % (inst, ", ".join(sorted(PAARE))))
    return s


def reihen_normalisieren(roh):
    """Binance-JSON -> [[int, float, float, float, float, float], ...]."""
    return [[int(r[0])] + [float(x) for x in r[1:6]] for r in roh]


def datei(inst, takt):
    if takt not in TAKTE:
        raise KeyError("unbekannter Takt %r - bekannt: %s"
                       % (takt, ", ".join(sorted(TAKTE))))
    return os.path.join(ORDNER, "%s_%s.json" % (symbol(inst), takt))


def lade(inst, takt):
    """Gespeicherte Kerzen, aufsteigend. Fehlende Datei ist kein Fehler.

    Eine UNVOLLSTAENDIGE Datei ist seit dem 05.10.2026 auch kein "keine
    Daten" mehr: sie wird als [] gelesen und der Aufrufer rechnet mit leeren
    Kerzen weiter, statt zu sehen, dass gerade geschrieben wird. Deshalb wird
    hier nicht mehr geschluckt, was man nicht deuten kann - der Leser soll
    wissen, was er vor sich hat (T-297: atomar schreiben, und wenn es
    trotzdem passiert, benennen statt verdecken).
    """
    try:
        with open(datei(inst, takt), encoding="utf-8") as f:
            roh = f.read()
    except FileNotFoundError:
        return []
    except OSError:
        return []
    if not roh.strip():
        return []
    try:
        reihen = json.loads(roh)
    except json.JSONDecodeError:
        # Entweder eine laedende Datei (dann kommt der naechste Lauf) oder
        # eine kaputte (dann ist eine Meldung Pflicht, kein []).
        raise HistorieKaputt(
            "%s ist keine gueltige JSON-Datei (%d Zeichen gelesen) - "
            "entweder wird gerade geschrieben oder die Datei ist kaputt"
            % (datei(inst, takt), len(roh)))
    return sorted(reihen, key=lambda r: r[0])


def speichere(inst, takt, reihen):
    """Anhaengen, entdoppelt ueber den Zeitstempel. Gibt den Gesamtbestand.

    Appendend, weil ein zweiter Lauf nur die neuen Kerzen mitbringt: die
    HISTORIE darf nie durch eine kuerzere Antwort ersetzt werden (fuer den
    Betrieb waere "nur die letzten N" richtig, fuer den Backtest falsch).
    """
    bestand = {r[0]: r for r in lade(inst, takt)}
    roh = (reihen_normalisieren(reihen)
           if reihen and isinstance(reihen[0][0], str) else reihen)
    for r in roh:
        bestand[r[0]] = r
    os.makedirs(ORDNER, exist_ok=True)
    # ATOMAR (05.10.2026): vorher stand hier ein blosses open(..., "w").
    # Ein Leser, der im Betrieb genau dann laed (spur_audit, ein Backtest,
    # die Handelszentrale), sah eine HALBE Datei - json.load warf
    # JSONDecodeError, `lade()` deutete den als ValueError und gab
    # `[]` zurueck. Der Leser meldete daraufhin "keine Historie" und
    # rechnete mit leeren Kerzen weiter, statt zu sagen "da wird gerade
    # geschrieben". Das ist die Fehlerklasse aus T-297 (Datei atomar
    # schreiben), hier an einer Stelle, die sie nie hatte.
    ziel = datei(inst, takt)
    tmp = ziel + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump([bestand[t] for t in sorted(bestand)], f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ziel)          # Windows: ersetzt atomar, auch wenn
    return len(bestand)            # der Leser die alte Datei offen haelt


# Naht fuer Tests: None -> echtes Netz.
abruf_json = None


def _hole(url, versuche=3):
    if abruf_json is not None:
        return abruf_json(url)
    letzter = None
    for i in range(versuche):
        try:
            with urllib.request.urlopen(url, timeout=30) as a:
                return json.loads(a.read().decode("utf-8"))
        except Exception as e:                                 # noqa: BLE001
            letzter = e
            time.sleep(1.0 + i)
    raise RuntimeError("Abruf scheiterte nach %d Versuchen: %s"
                       % (versuche, letzter))


def von_binance(inst, takt, von_ms, bis_ms, pause=0.25):
    """Kerzen von Binance, aufsteigend, auf [von_ms, bis_ms] beschnitten.

    Paginiert mit `startTime` (letzter Zeitstempel + 1 ms), weil nur diese
    Richtung vorwaerts blaettert. OKX blaettert mit `after` rueckwaerts - die
    Richtung haengt an der Boerse, nicht am Werkzeug.

    Abbruch ueber "keine neuen Zeitstempel": gegen eine Attrappe, die dieselbe
    Seite wiederholt, waere jede andere Bedingung eine Endlosschleife.
    """
    sym, bar = symbol(inst), TAKTE[takt]
    reihen, cur = [], int(von_ms)
    while cur <= int(bis_ms):
        url = ("%s/api/v3/klines?symbol=%s&interval=%s&limit=%d&startTime=%d"
               % (_BASIS, sym, bar, _GRENZE, cur))
        seite = _hole(url)
        if not seite:
            break
        neu = reihen_normalisieren(seite)
        if reihen and neu[-1][0] <= reihen[-1][0]:
            break
        reihen += neu
        cur = reihen[-1][0] + 1
        if cur > int(bis_ms):
            break
        time.sleep(pause)
    return [r for r in reihen if int(von_ms) <= r[0] <= int(bis_ms)]


def funding(inst, von_ms, bis_ms, pause=0.25):
    """[(ts_ms, rate)] von Binance-Futures. Frei ab 2020-08-01."""
    sym = symbol(inst)
    aus, cur = [], int(von_ms)
    while cur <= int(bis_ms):
        url = ("%s/fapi/v1/fundingRate?symbol=%s&limit=%d&startTime=%d"
               % (_FUTURES, sym, _GRENZE, cur))
        seite = _hole(url)
        if not seite:
            break
        neu = [(int(r["fundingTime"]), float(r["fundingRate"])) for r in seite]
        if aus and neu[-1][0] <= aus[-1][0]:
            break
        aus += neu
        cur = aus[-1][0] + 1
        if cur > int(bis_ms):
            break
        time.sleep(pause)
    return [r for r in aus if int(von_ms) <= r[0] <= int(bis_ms)]


def auffuellen(insts, takte, von_ms=None, bis_ms=None):
    """Kerzen nachladen und speichern. Der Bericht nennt je Reihe neu/gesamt."""
    von_ms = von_ms or int(time.mktime(time.strptime("2021-01-01", "%Y-%m-%d"))) * 1000
    bis_ms = bis_ms or int(time.time() * 1000)
    bericht = {}
    for inst in insts:
        for takt in takte:
            neu = von_binance(inst, takt, von_ms, bis_ms)
            gesamt = speichere(inst, takt, neu)
            bericht.setdefault(inst, {})[takt] = {"neu": len(neu), "kerzen": gesamt}
    _schreibe_stand()
    return bericht


def _schreibe_stand():
    reihen = {}
    namen = sorted(os.listdir(ORDNER)) if os.path.isdir(ORDNER) else []
    for name in namen:
        if not name.endswith(".json") or name == "_stand.json":
            continue
        try:
            with open(os.path.join(ORDNER, name), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        # Nur echte Kerzenreihen: in diesem Ordner liegen auch Berichte
        # (okx_probe.json, coingecko_probe.json) - ein Dict ist keine Reihe,
        # und `d[0][0]` brach daran mit KeyError ab (gefunden 01.10.2026).
        if not isinstance(d, list) or not d or not isinstance(d[0], list):
            continue
        reihen[name[:-5]] = {"kerzen": len(d),
                             "von": d[0][0] if d else None,
                             "bis": d[-1][0] if d else None,
                             "herkunft": "binance",
                             "stand_ms": int(time.time() * 1000)}
    stan = {"reihen": reihen, "takte": dict(TAKTE)}
    os.makedirs(ORDNER, exist_ok=True)
    with open(os.path.join(ORDNER, "_stand.json"), "w", encoding="utf-8") as f:
        json.dump(stan, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return stan


def stand():
    try:
        with open(os.path.join(ORDNER, "_stand.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"reihen": {}}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auffuellen", action="store_true")
    ap.add_argument("--stand", action="store_true")
    ap.add_argument("--instrumente", default="BTC-USDC,ETH-USDC,SOL-USDC")
    ap.add_argument("--takte", default="1H,4H")
    ap.add_argument("--von", default="2021-01-01")
    a = ap.parse_args()
    if a.stand:
        print(json.dumps(stand(), indent=2, ensure_ascii=False))
        return
    if not a.auffuellen:
        ap.print_help()
        return
    von = int(time.mktime(time.strptime(a.von, "%Y-%m-%d"))) * 1000
    b = auffuellen([x for x in a.instrumente.split(",") if x],
                   [x for x in a.takte.split(",") if x], von_ms=von)
    print(json.dumps(b, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
