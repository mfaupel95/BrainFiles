"""Marktquerschnitt und Funding fuer die MoonDev-Spuren.

Die Spuren holen ihre Daten im Betrieb von CoinGecko (Top Mover, Marktbreite,
1h-Aenderung) und vom MoonDev-Bot (Funding). Beides ist historisch nicht
abrufbar - dieses Modul baut DIESELBEN Felder aus Binance-Daten:

  * `Bestand` haelt je Takt alle Reihen der liquidesten USDT-Paare im
    Speicher und schneidet daraus die Tafel eines Tages oder einer Stunde.
  * der Tages-Rang entsteht aus dem Quote-Volumen DIESES Tages, nicht aus
    einer einmal festgelegten Liste.
  * Funding kommt aus Binance-Futures (frei, 8h-Punkte, paginiert).

ABLAGE: daten/historie/feed/<SYMBOL>_<TAKT>.json, Reihen
[ts_ms, o, h, l, c, volumen_quote] - das sechste Feld ist das QUOTE-Volumen
(Binance-Feld 7, USD), NICHT das Basisvolumen wie in historie_binance.py. Wer
eine Feed-Kerze gegen `mindest_volumen_usd` prueft, braucht genau diese Zahl.

Eigener Ordner, eigener Name: die Feed-Kerze darf nie mit der
gewoehnlichen Kerze verwechselt werden - dort steht das Basisvolumen.

Jedes Ergebnis traegt `kerzenquelle: "binance"` - Binance ist ein ausgewiesener
Ersatz fuer die Boersen der Spuren, kein OKX- oder Kraken-Preis.

Aufruf:
    python moondev_historie.py --universum 300 --takt 1D
    python moondev_historie.py --stunden 40
    python moondev_historie.py --funding BTC,ETH,SOL,HYPE,FIL,ZEC
    python moondev_historie.py --stand
"""

import argparse
import json
import os
import time

import historie_binance

HIER = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(HIER, "daten", "historie", "feed")

TAKTE = {"1D": "1d", "1H": "1h"}
KENNUNG = "feed"
VON_TAG = "2021-01-01"

# Die Instrumente der Funding-Spur. Ihre Stundenkerzen werden IMMER
# mitgeladen, auch wenn sie nicht unter den liquidesten Paaren stehen: der
# Mark-Preis im Funding-Lauf kommt aus derselben Reihe, ein fehlendes Symbol
# waere dort ein fehlender Kurs.
FUNDING_INSTRUMENTE = ("BTC", "ETH", "SOL", "HYPE", "FIL", "ZEC")

_BASIS = historie_binance._BASIS
_FUTURES = historie_binance._FUTURES
_GRENZE = historie_binance._GRENZE      # Binance liefert hoechstens 1000 je Abruf

# Naht fuer Tests: None -> echtes Netz (siehe historie_binance._hole).
abruf_json = None

_basis = {}                             # Binance-Symbol -> Basiswert
_universum = []                         # Binance-Symbole in Rangfolge


def _hole(url):
    if abruf_json is not None:
        return abruf_json(url)
    return historie_binance._hole(url)


def universum(anzahl=300):
    """Die liquidesten USDT-Spot-Paare als Binance-Symbole.

    Die Auswahl ist der Stand JETZT (gemessen wird das Quote-Volumen der letzten
    24 h). Das ist die eine Grenze, die dieses Verfahren nicht aufloest: Paare,
    die vor heute delistet wurden, fehlen. Der Rang INNERHALB des geladenen
    Universums entsteht spaeter je Tag neu.
    """
    ticker = _hole("%s/api/v3/ticker/24hr" % _BASIS)
    info = _hole("%s/api/v3/exchangeInfo" % _BASIS)
    handelbar = {}
    for s in info.get("symbols", []):
        if s.get("status") == "TRADING" and s.get("quoteAsset") == "USDT":
            handelbar[s["symbol"]] = s.get("baseAsset") or s["symbol"][:-4]
    zeilen = []
    for t in ticker:
        sym = t.get("symbol")
        if sym not in handelbar:
            continue
        try:
            vol = float(t.get("quoteVolume") or 0.0)
        except (TypeError, ValueError):
            continue
        if vol > 0:
            zeilen.append((vol, sym))
    if not zeilen:
        raise RuntimeError("kein handelbares USDT-Paar in der Antwort - "
                           "Abruf oder Attrappe pruefen")
    zeilen.sort(key=lambda z: (-z[0], z[1]))
    gewaehlt = [sym for _, sym in zeilen[:int(anzahl)]]
    global _universum
    _universum = gewaehlt
    _basis.clear()
    _basis.update(handelbar)
    _schreibe_universum(zeilen[:int(anzahl)])
    return gewaehlt


def basis_von(sym):
    """Basiswert eines Binance-Symbols - aus exchangeInfo, nicht abgeschnitten."""
    if not _basis:
        _lade_universum()
    return _basis.get(sym)


def normalisiere_feed(roh):
    """Binance-JSON -> [[int, float, float, float, float, float], ...].

    Felder: [0] Open-Time, [1..4] o/h/l/c, [7] QUOTE-Volumen in USD.
    Bewusst NICHT `historie_binance.reihen_normalisieren`: das nimmt [1:6] und
    traegt damit das Basisvolumen.
    """
    return [[int(r[0])] + [float(r[i]) for i in (1, 2, 3, 4, 7)] for r in roh]


def datei(sym, takt):
    if takt not in TAKTE:
        raise KeyError("unbekannter Takt %r - bekannt: %s"
                       % (takt, ", ".join(sorted(TAKTE))))
    return os.path.join(ORDNER, "%s_%s.json" % (sym, takt))


def lade_feed(sym, takt="1D"):
    """Gespeicherte Feed-Kerzen, aufsteigend. Fehlende Datei ist kein Fehler."""
    try:
        with open(datei(sym, takt), encoding="utf-8") as f:
            reihen = json.load(f)
    except (OSError, ValueError):
        return []
    return sorted(reihen, key=lambda r: r[0])


def speichere_feed(sym, takt, reihen):
    """Anhaengen, entdoppelt ueber den Zeitstempel - die Historie wird nie kuerzer."""
    bestand = {r[0]: r for r in lade_feed(sym, takt)}
    for r in reihen:
        bestand[r[0]] = r
    os.makedirs(ORDNER, exist_ok=True)
    with open(datei(sym, takt), "w", encoding="utf-8") as f:
        json.dump([bestand[t] for t in sorted(bestand)], f)
    return len(bestand)


def hole_feed(sym, takt, von_ms, bis_ms, pause=0.2):
    """Feed-Kerzen von Binance, aufsteigend, auf [von_ms, bis_ms] beschnitten.

    Paginiert mit `startTime` (letzter Zeitstempel + 1 ms). Abbruch ueber
    'keine neuen Zeitstempel' - gegen eine Attrappe, die dieselbe Seite
    wiederholt, waere jede andere Bedingung eine Endlosschleife.
    """
    bar, reihen, cur = TAKTE[takt], [], int(von_ms)
    while cur <= int(bis_ms):
        url = ("%s/api/v3/klines?symbol=%s&interval=%s&limit=%d&startTime=%d"
               % (_BASIS, sym, bar, _GRENZE, cur))
        seite = _hole(url)
        if not seite:
            break
        neu = normalisiere_feed(seite)
        if reihen and neu[-1][0] <= reihen[-1][0]:
            break
        reihen += neu
        cur = reihen[-1][0] + 1
        if cur > int(bis_ms):
            break
        time.sleep(pause)
    return [r for r in reihen if int(von_ms) <= r[0] <= int(bis_ms)]


def _zeitpunkt(text):
    """'2021-01-01' -> Millisekunden (lokal, wie die Hausuhr)."""
    return int(time.mktime(time.strptime(text, "%Y-%m-%d"))) * 1000


def auffuellen(symbole, takt="1D", von_ms=None, bis_ms=None, pause=0.2):
    """Feed-Kerzen nachladen. Bericht je Symbol: neu/gesamt."""
    von_ms = von_ms if von_ms is not None else _zeitpunkt(VON_TAG)
    bis_ms = bis_ms if bis_ms is not None else int(time.time() * 1000)
    bericht = {}
    for sym in symbole:
        neu = hole_feed(sym, takt, von_ms, bis_ms, pause=pause)
        bericht[sym] = {"neu": len(neu), "kerzen": speichere_feed(sym, takt, neu)}
    _schreibe_stand()
    return bericht


def _schreibe_universum(zeilen):
    """Herkunft und Rangfolge mitschreiben - ein Lauf ohne Beleg ist keiner."""
    os.makedirs(ORDNER, exist_ok=True)
    daten = {"stand_ms": int(time.time() * 1000), "herkunft": "binance",
             "kennung": KENNUNG,
             "symbole": [{"symbol": sym, "basis": _basis.get(sym),
                          "quote_volumen_usd": vol} for vol, sym in zeilen]}
    with open(os.path.join(ORDNER, "_universum.json"), "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return daten


def _lade_universum():
    try:
        with open(os.path.join(ORDNER, "_universum.json"), encoding="utf-8") as f:
            daten = json.load(f)
    except (OSError, ValueError):
        return []
    _basis.clear()
    _basis.update({z["symbol"]: z["basis"] for z in daten.get("symbole", [])})
    return [z["symbol"] for z in daten.get("symbole", [])]


def _symbole_auf_der_platte(takt="1D"):
    """Rueckfall: was liegt. Der Stand ist dann der Abrufzeitpunkt der Dateien."""
    if not os.path.isdir(ORDNER):
        return []
    endung = "_%s.json" % takt
    aus = []
    for name in sorted(os.listdir(ORDNER)):
        if name.startswith("_") or not name.endswith(endung):
            continue
        aus.append(name[:-len(endung)])
    return aus


def _schreibe_stand():
    namen = sorted(os.listdir(ORDNER)) if os.path.isdir(ORDNER) else []
    reihen = {}
    for name in namen:
        if not name.endswith(".json") or name.startswith("_"):
            continue
        try:
            with open(os.path.join(ORDNER, name), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        reihen[name[:-5]] = {"kerzen": len(d),
                             "von": d[0][0] if d else None,
                             "bis": d[-1][0] if d else None,
                             "herkunft": "binance"}
    stan = {"reihen": reihen, "kennung": KENNUNG, "takte": dict(TAKTE),
            "universum": _lade_universum()}
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


def _stunden_symbole(anzahl):
    """Top `anzahl` aus dem Tages-Universum PLUS die Funding-Instrumente."""
    u = _lade_universum() or universum(anzahl)
    aus = list(u[:int(anzahl)])
    for inst in FUNDING_INSTRUMENTE:
        sym = historie_binance.symbol(inst)
        if sym and sym not in aus:
            aus.append(sym)
    return aus


def main():
    p = argparse.ArgumentParser(description="Historische Daten der MoonDev-Spuren")
    p.add_argument("--universum", type=int, default=None,
                   help="Top-N USDT-Paare holen (1D)")
    p.add_argument("--takt", default="1D", choices=sorted(TAKTE))
    p.add_argument("--stunden", type=int, default=None,
                   help="Top-N PLUS Funding-Instrumente stuendlich holen")
    p.add_argument("--von", default=VON_TAG)
    p.add_argument("--stand", action="store_true")
    a = p.parse_args()

    if a.stand:
        print(json.dumps(stand(), indent=2, ensure_ascii=False)[:4000])
        return
    if a.universum:
        sym = universum(a.universum)
        print("%d Symbole im Universum, hole %s ..." % (len(sym), a.takt))
        bericht = auffuellen(sym, a.takt, _zeitpunkt(a.von))
        fertig = [s for s, b in bericht.items() if b["kerzen"]]
        print("%d Reihen geschrieben, %d ohne Kerzen" % (len(fertig),
                                                         len(bericht) - len(fertig)))
        return
    if a.stunden:
        sym = _stunden_symbole(a.stunden)
        print("%d Symbole (Top %d + Funding-Instrumente), hole 1H ..."
              % (len(sym), a.stunden))
        bericht = auffuellen(sym, "1H", _zeitpunkt(a.von))
        fertig = [s for s, b in bericht.items() if b["kerzen"]]
        print("%d Reihen geschrieben, %d ohne Kerzen" % (len(fertig),
                                                         len(bericht) - len(fertig)))
        return
    p.print_help()


if __name__ == "__main__":
    main()
