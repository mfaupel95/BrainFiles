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
import bisect
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import historie_binance

HIER = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(HIER, "daten", "historie", "feed")

TAKTE = {"1D": "1d", "1H": "1h"}
_FEED_ZEITEN = {}    # (sym, takt) -> [ts, ...] fuer die Bisektion
BAR_MS = {"1D": 86400000, "1H": 3600000}        # Laenge einer Kerze in ms
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

# Nur Ziffern und Grossbuchstaben sind abrufbar. Binance fuehrt daneben Paare
# mit chinesischen Namen (beobachtet 29.09.2026: 币安人生USDT, 牛来USDT unter den
# 496 USDT-Paaren) - urllib kann so eine Adresse nicht kodieren, EIN solches
# Paar reisst den ganzen Abruf mit ("'ascii' codec can't encode characters").
# Sie fliegen raus, aber nicht still: `verworfen` nennt sie im Stand.
ABRUFBAR = re.compile(r"^[A-Z0-9]+$")

_basis = {}                             # Binance-Symbol -> Basiswert
_universum = []                         # Binance-Symbole in Rangfolge
_verworfen = []                         # nicht abrufbare Symbole (Begruendung)


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
    _verworfen.clear()
    for s in info.get("symbols", []):
        if s.get("status") != "TRADING" or s.get("quoteAsset") != "USDT":
            continue
        sym = s.get("symbol") or ""
        if not ABRUFBAR.match(sym):
            _verworfen.append(sym)
            continue
        handelbar[sym] = s.get("baseAsset") or sym[:-4]
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
    _schreibe_stand()
    return gewaehlt


# Laengste Quote zuerst pruefen (USDT vor USD), sonst bliebe bei "BTCUSDT"
# nichts uebrig. Reihenfolge in der Liste ist die Pruefreihenfolge.
QUOTEN = ("USDT", "USDC", "FDUSD", "TUSD", "BUSD", "EUR", "TRY", "BTC", "ETH")


def basis_von(sym):
    """Basiswert eines Binance-Symbols.

    Zuerst aus exchangeInfo: dort steht der ECHTE Basiswert eines Paares.
    Ohne exchangeInfo - im Test oder in einem Ruecklauf ohne Netz - wird die
    Quote abgeschnitten. Das ist ausdruecklich der Rueckfall und nicht die
    Regel: Binance notiert dieselbe Muenze mal als "SHIB", mal als "1000SHIB";
    exchangeInfo kennt nur die zweite Schreibweise, das Abschneiden erfindet
    "1000SHIB" als eigenen Basiswert.

    04.10.2026: `if not _basis` liest den Cache nur, solange er LEER ist. Ein
    frueherer Abruf (echtes Universum, 300 Eintraege) blieb fuer den ganzen
    Prozess stehen, und jeder folgende Lauf - auch einer mit umgebogenem
    `ORDNER` und eigenen Attrappen - bekam die alte Liste. `basis_von` entdeckt
    sein Symbol darin nicht, `rng` lieferte nichts, die Spur buchte 0 Positionen
    und der Test meldete "Journal ohne eine Buchung". Der Cache wird darum
    nicht mehr als Vorbedingung, sondern als Frage behandelt: das Symbol wird
    IMMER zuerst in der Datei gesucht, die zum aktuellen ORDNER gehoert.
    """
    geladen = _lade_universum()
    if sym in _basis:
        return _basis[sym]
    if sym not in geladen and os.path.isdir(ORDNER):
        # Der Ordner hat sich geaendert (Test, neue Daten): neu einlesen.
        _lade_universum()
        if sym in _basis:
            return _basis[sym]
    s = str(sym or "").upper()
    for q in QUOTEN:
        if s.endswith(q) and len(s) > len(q):
            return s[:-len(q)]
    return s or None


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
    _FEED_ZEITEN.pop((sym, takt), None)     # Zeitsprung-Cache verwerfen
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


def _startpunkt(sym, takt, von_ms):
    """Wo der Nachlauf einsetzt.

    Reicht die gespeicherte Reihe bis an den Fensteranfang, wird am letzten
    Stand fortgesetzt (ein zweiter Lauf holt dann nur das Neue). Fehlt vorn
    Geschichte - etwa weil das Paar spaeter gelistet wurde - wird das ganze
    Fenster geholt, sonst bliebe die Luecke fuer immer.
    """
    reihe = lade_feed(sym, takt)
    if not reihe:
        return int(von_ms)
    if reihe[0][0] > int(von_ms) + 2 * BAR_MS[takt]:
        return int(von_ms)
    return reihe[-1][0] + 1


def auffuellen(symbole, takt="1D", von_ms=None, bis_ms=None, pause=0.2, faeden=4):
    """Feed-Kerzen nachladen. Bericht je Symbol: neu/gesamt.

    `faeden`: mehrere Symbole GLEICHZEITIG holen. Der Engpass ist die Latenz,
    nicht das Limit - Binance erlaubt rund 600 Kerzenabrufe je Minute, ein
    einzelner Faden schafft etwa 24. Innerhalb eines Symbols bleibt die
    Reihenfolge sequenziell und die Datei je Symbol getrennt, damit sich zwei
    Faeden nie in dieselbe Datei schreiben.
    """
    von_ms = von_ms if von_ms is not None else _zeitpunkt(VON_TAG)
    bis_ms = bis_ms if bis_ms is not None else int(time.time() * 1000)

    def _eins(sym):
        start = _startpunkt(sym, takt, von_ms)
        neu = hole_feed(sym, takt, start, bis_ms, pause=pause)
        return sym, {"neu": len(neu), "kerzen": speichere_feed(sym, takt, neu)}

    if faeden and int(faeden) > 1 and len(symbole) > 1:
        with ThreadPoolExecutor(max_workers=int(faeden)) as pool:
            bericht = dict(pool.map(_eins, symbole))
    else:
        bericht = dict(_eins(s) for s in symbole)
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
    """Universum UND Basis-Mapping aus `_universum.json` - immer frisch.

    04.10.2026 (Befund, nicht Vermutung): `_basis` war ein reiner
    Modul-Cache. Ein Test, der einmal das echte Universum geladen hatte,
    hinterliess 300 Eintraege fuer ALLE folgenden Tests desselben Prozesses.
    Der naechste Test legte seine Attrappen in einen Temp-Ordner, `basis_von`
    fand seine Symbole aber im alten Cache nicht, `rng` leerte und die Spur
    erzeugte 0 Buchungen - der Test meldete "Journal ohne eine einzige
    Buchung", ohne dass irgendwo ein Fehler stand. Der Test allein war nicht
    schuld; er war das Opfer eines Caches, der keine Zuruecksetzung kennt.

    Deshalb wird der Cache nicht mehr als Wahrheit behandelt, sondern nur
    noch innerhalb EINES Aufrufs: `universum()` fuellt ihn nach einem echten
    Abruf, und jeder Lesezugriff auf `_universum.json` baut ihn neu auf. Ein
    umgebogener `ORDNER` sieht damit sofort die Attrappen - die Regel ist
    "die Platte ist die Wahrheit, der Cache ist ein Komfort".
    """
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
    # `verworfen` wird aus dem alten Stand uebernommen, wenn dieser Lauf keine
    # eigene Auswahl getroffen hat: `universum()` fuellt die Liste, das
    # Nachladen (speichere_feed) schreibt denselben Stand neu - ohne die
    # Uebernahme waere die Begruendung nach dem ersten Nachladen wieder weg.
    alt = {}
    try:
        with open(os.path.join(ORDNER, "_stand.json"), encoding="utf-8") as f:
            alt = json.load(f)
    except (OSError, ValueError):
        alt = {}
    stan = {"reihen": reihen, "kennung": KENNUNG, "takte": dict(TAKTE),
            "universum": _lade_universum(),
            "verworfen": list(_verworfen) or list(alt.get("verworfen") or [])}
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


def quantil(reihe, anteil):
    """Der Wert an der Stelle `anteil` (0..1) der SORTIERTEN Reihe.

    Ohne Interpolation: die Zahl ist zum Vergleichen gedacht (Regime, Streuung),
    nicht als Median. Leere Reihe -> None, nicht 0.
    """
    if not reihe:
        return None
    s = sorted(reihe)
    i = int(round(anteil * (len(s) - 1)))
    i = max(0, min(len(s) - 1, i))
    return s[i]


class Bestand:
    """Alle Reihen eines Takts im Speicher, Zugriff ueber den Zeitstempel.

    Der Kern jeder Feed-Spur ist ein Marktquerschnitt: welcher Kurs gilt JETZT,
    wie hat er sich zum Vortag geaendert, welches Volumen hatte er. `tafel`
    liefert genau das fuer EINEN Zeitpunkt, `rang` die Reihenfolge nach
    Volumen und `kurse` die Preise ALLER geladenen Symbole.

    `kurse` ist kein Beiwerk: `spur_buch.pruefe_ausstiege` liest die Preise
    daraus, und ein Symbol, das dort fehlt, schliesst seine Position nie.
    """

    def __init__(self):
        self._reihen = {}
        self._tafel = {}
        self._kurse = {}

    def laden(self, takt="1D"):
        """Alle Reihen dieses Takts von der Platte. Rueckgabe: die Symbole."""
        self._reihen = {}
        for sym in _symbole_auf_der_platte(takt):
            r = lade_feed(sym, takt)
            if r:
                self._reihen[sym] = r
        self._tafel.clear()
        self._kurse.clear()
        return sorted(self._reihen)

    def symbole(self):
        return sorted(self._reihen)

    def schritte(self, mindest_symbole=30, von_ms=None, bis_ms=None):
        """Zeitpunkte, an denen mindestens `mindest_symbole` Reihen liegen.

        Ein Tag mit drei Reihen waere keine Marktbreite, sondern ein Zufall.
        Deshalb faellt ein Zeitpunkt ganz weg, statt mit dem halben Universum
        in die Messung zu gehen.
        """
        zaehler = {}
        for k in self._reihen.values():
            for r in k:
                t = r[0]
                if von_ms is not None and t < von_ms:
                    continue
                if bis_ms is not None and t > bis_ms:
                    continue
                zaehler[t] = zaehler.get(t, 0) + 1
        return sorted(t for t, n in zaehler.items() if n >= int(mindest_symbole))

    def reihe(self, sym):
        return self._reihen.get(sym, [])

    def _i(self, sym, ts):
        """Index der Kerze, die bei `ts` laeuft (letzte mit zeit <= ts).

        Bisektion, weil die Reihen lang sind und je Tag jedes Symbol gefragt
        wird.
        """
        r = self._reihen.get(sym)
        if not r:
            return None
        lo, hi, treffer = 0, len(r) - 1, None
        while lo <= hi:
            m = (lo + hi) // 2
            if r[m][0] <= ts:
                treffer = m
                lo = m + 1
            else:
                hi = m - 1
        return treffer

    def kerze(self, sym, ts):
        i = self._i(sym, ts)
        return None if i is None else self._reihen[sym][i]

    def kurs(self, sym, ts):
        k = self.kerze(sym, ts)
        return None if k is None else k[4]

    def volumen_usd(self, sym, ts):
        k = self.kerze(sym, ts)
        return None if k is None else k[5]

    def aenderung_pct(self, sym, ts, zurueck=1):
        """Aenderung gegen die Kerze `zurueck` Stellen davor, in Prozent.

        Ohne Vorzeile None - eine fehlende Vorzeile ist keine Nullbewegung.
        """
        i = self._i(sym, ts)
        if i is None or i - zurueck < 0:
            return None
        alt = self._reihen[sym][i - zurueck][4]
        neu = self._reihen[sym][i][4]
        if not alt:
            return None
        return (neu / alt - 1.0) * 100.0

    def rang(self, ts, top=None):
        """Symbole nach Quote-Volumen DIESES Zeitpunkts, groesstes zuerst."""
        paare = []
        for sym in self._reihen:
            v = self.volumen_usd(sym, ts)
            if v:
                paare.append((v, sym))
        paare.sort(key=lambda z: (-z[0], z[1]))
        namen = [sym for _, sym in paare]
        return namen[:int(top)] if top else namen

    def tafel(self, ts, top=None):
        """Marktquerschnitt: {symbol: {kurs, aenderung_pct, ...}}."""
        if ts in self._tafel:
            t = self._tafel[ts]
        else:
            t = {}
            for sym in self._reihen:
                kurs = self.kurs(sym, ts)
                if kurs is None:
                    continue
                t[sym] = {"kurs": kurs,
                          "aenderung_pct": self.aenderung_pct(sym, ts, 1),
                          "aenderung_pct_7d": self.aenderung_pct(sym, ts, 7),
                          "volumen_usd": self.volumen_usd(sym, ts),
                          "basis": basis_von(sym)}
            self._tafel[ts] = t
        if top:
            erlaubt = set(self.rang(ts, top))
            return {s: v for s, v in t.items() if s in erlaubt}
        return t

    def kurse(self, ts):
        """Preis JEDES geladenen Symbols zu diesem Zeitpunkt.

        Bewusst ALLE, nicht nur die der Tafel: der Kursweg der Buchhaltung
        braucht jede offene Position, auch eine, die heute kein Volumen hat.
        """
        if ts not in self._kurse:
            self._kurse[ts] = {sym: k for sym in self._reihen
                               if (k := self.kurs(sym, ts)) is not None}
        return self._kurse[ts]

    def tafel_stunde(self, ts, top=None):
        """Stundenquerschnitt mit 1h- und 24h-Aenderung.

        Fuer `moondev_signalwelle`: ihre Regel liest `aenderung_1h` (3-15 %) und
        `volumen_24h` (>= 20 Mio USD), das laesst sich aus Tageskerzen nicht
        ehrlich bilden. Verlangt 24 Kerzen Vorlauf - ein Wert aus drei Kerzen
        waere keine 24h-Aenderung, sondern eine 3h-Aenderung mit falschem Namen.

        Rueckgabe als LISTE (mit `rang`), nicht als Dict: die Spur liest die
        Kandidaten als geordnete Folge.
        """
        zeilen = []
        for sym in self._reihen:
            i = self._i(sym, ts)
            if i is None or i < 24:
                continue
            k = self._reihen[sym]
            c, c_vor, c_tag = float(k[i][4]), float(k[i - 1][4]), float(k[i - 24][4])
            if not c_vor or not c_tag:
                continue
            zeilen.append({
                "symbol": sym, "basis": basis_von(sym), "kurs": c,
                "aenderung_1h": (c / c_vor - 1.0) * 100.0,
                "aenderung_24h": (c / c_tag - 1.0) * 100.0,
                "volumen_24h": sum(float(k[j][5]) for j in range(i - 23, i + 1))})
        zeilen.sort(key=lambda z: (-z["volumen_24h"], z["symbol"]))
        for n, z in enumerate(zeilen, 1):
            z["rang"] = n
        return zeilen[:int(top)] if top else zeilen

    def breite(self, ts, top=None):
        """Anteil der Symbole mit positiver Tagesaenderung.

        Rueckgabe als Dict, nicht als nackte Zahl: `anteil` allein verschweigt,
        ob 3 oder 300 Symbole gemessen wurden. `anteil` ist None, wenn kein
        einziges Symbol eine Kerze hat - 0.0 waere die Aussage 'keiner steigt'.
        """
        t = self.tafel(ts, top)
        gemessen = [v["aenderung_pct"] for v in t.values()
                    if v["aenderung_pct"] is not None]
        ohne = len(t) - len(gemessen)
        return {"anteil": (sum(1 for a in gemessen if a > 0) / len(gemessen))
                if gemessen else None,
                "gemessen": len(gemessen),
                "ohne_kerze": ohne}


def _reihen_zeiten(sym, takt):
    """Zeitspalte einer Reihe, einmal je (Symbol, Takt) - fuer die Bisektion.

    Ohne diesen Cache waere jeder Kursabruf ein linearer Durchlauf ueber 50 000
    Stundenkerzen, und die Funding-Spur fragt das je Schritt.
    """
    schluessel = (sym, takt)
    if schluessel not in _FEED_ZEITEN:
        _FEED_ZEITEN[schluessel] = [r[0] for r in lade_feed(sym, takt)]
    return _FEED_ZEITEN[schluessel]


class Funding:
    """Eine Funding-Reihe mit Zugriff auf den letzten Satz VOR einem Zeitpunkt.

    Der Satz gilt ab seinem Zeitstempel bis zum naechsten; wer den naechsten
    nimmt, handelt auf einer Zahl, die es damals noch nicht gab.
    """

    def __init__(self, inst):
        self.inst = inst
        self.reihe = lade_funding(inst)
        self._zeiten = [r[0] for r in self.reihe]

    def zu(self, ts):
        i = bisect.bisect_right(self._zeiten, int(ts)) - 1
        return self.reihe[i][1] if i >= 0 else None

    def stand(self):
        return {"saetze": len(self.reihe),
                "von": self.reihe[0][0] if self.reihe else None,
                "bis": self.reihe[-1][0] if self.reihe else None}

    def dict_zu(self, ts):
        """Genau die Form, die `moondev_funding.pruefe_einstieg` liest."""
        rate = self.zu(ts)
        if rate is None:
            return None
        kurs = mark_preis(historie_binance.symbol(self.inst), ts)
        if not kurs:
            return None
        return {"funding_rate": rate, "mark_price": float(kurs)}


def _stunden_symbole(anzahl):
    """Top `anzahl` aus dem Tages-Universum PLUS die Funding-Instrumente."""
    u = _lade_universum() or universum(anzahl)
    aus = list(u[:int(anzahl)])
    for inst in FUNDING_INSTRUMENTE:
        sym = historie_binance.symbol(inst)
        if sym and sym not in aus:
            aus.append(sym)
    # Fuer die Symbole ausserhalb des Tages-Universums fehlt der Basiswert -
    # ohne ihn stuende im Marktquerschnitt 'basis: None'.
    fehlend = [s for s in aus if s not in _basis]
    if fehlend:
        info = _hole("%s/api/v3/exchangeInfo" % _BASIS)
        for s in info.get("symbols", []):
            if s.get("symbol") in fehlend:
                _basis[s["symbol"]] = s.get("baseAsset") or s["symbol"][:-4]
    return aus


# --- Quellen je Spur -------------------------------------------------------
# Jede Funktion liefert GENAU die Form, die `quelle(w)` der Spur zurueckgibt:
# (daten, kurse, fehler). `daten` sind die Kandidaten, `kurse` traegt ALLE
# geladenen Symbole - ein offenes Symbol ausserhalb der Top N muss einen Kurs
# haben, sonst schliesst seine Position nie (spur_buch.pruefe_ausstiege
# arbeitet ueber `kurse`).
#
# Die Spuren sprechen CoinGecko-Namen, die Ablage spricht Binance-Symbole: der
# Adapter uebersetzt. Die Feldnamen stammen aus den Spuren selbst und stehen in
# FELDER - tests/test_replay_feed.py prueft sie gegen den Quelltext, damit ein
# Umbau der Spur hier einen roten Test gibt statt einen stillen Nullauf.

FELDER = {
    "moondev_topmovers": ("name", "aenderung_24h", "volumen_24h", "kurs"),
    "moondev_marktlage": ("name", "btc_aenderung_24h", "breite", "kurs"),
    "moondev_signalwelle": ("name", "aenderung_1h", "aenderung_24h",
                            "volumen_24h", "kurs"),
}


def _kurse_mit_basis(bestand, ts, fremde=None):
    """Kurse auf Basiswerte umschluesseln.

    `fremde` traegt Symbole offener Positionen, die im Bestand fehlen (delistet
    oder ausserhalb des Universums). Sie bekommen keinen erfundenen Kurs: sie
    fehlen und werden gemeldet.

    Teilen sich zwei Symbole einen Basiswert (SHIB und 1000SHIB), gewinnt der
    erste Eintrag - der zweite waere derselbe Preis in anderer Skalierung.
    """
    kurse, fehlen = {}, []
    for sym, kurs in bestand.kurse(ts).items():
        basis = basis_von(sym)
        if basis and basis not in kurse:
            kurse[basis] = kurs
    for s in (fremde or ()):
        if s not in kurse:
            fehlen.append("%s: kein Kurs am Zeitpunkt" % s)
    return kurse, fehlen


def quelle_topmovers(bestand, ts, w):
    """Top-Mover: 24h-Aenderung und Volumen ueber die Top `anzahl_coins`."""
    top = int(w.get("anzahl_coins", 250) or 250)
    aus = {}
    for z in bestand.tafel(ts, top=top).values():
        if not z["basis"]:
            continue
        aus[z["basis"]] = {"name": z["basis"],
                           "aenderung_24h": z["aenderung_pct"],
                           "volumen_24h": z["volumen_usd"],
                           "kurs": z["kurs"]}
    kurse, fehler = _kurse_mit_basis(bestand, ts)
    return aus, kurse, fehler


def quelle_marktlage(bestand, ts, w):
    """BTC-Aenderung plus Marktbreite.

    `breite` ist ein ANTEIL (0.60/0.40 in der wachen), kein Prozentwert - die
    beiden zu vertauschen waere ein stiller Fehlschlag: 0.6 statt 60 faellt
    immer unter die Schwelle, die Spur handelte nie.
    """
    top = int(w.get("anzahl_coins", 100) or 100)
    b = bestand.breite(ts, top=top)
    btc = None
    for z in bestand.tafel(ts, top=top).values():
        if z["basis"] == "BTC":
            btc = z
            break
    if btc is None or b["anteil"] is None or btc["aenderung_pct"] is None:
        return {}, {}, ["BTC oder Breite fehlt am Zeitpunkt"]
    kurse, fehler = _kurse_mit_basis(bestand, ts)
    return ({"BTC": {"name": "Bitcoin",
                     "btc_aenderung_24h": btc["aenderung_pct"],
                     "breite": b["anteil"], "kurs": btc["kurs"]}},
            kurse, fehler)


def quelle_signalwelle(bestand, ts, w):
    """Signalwelle: 1h-Aenderung und 24h-Volumen aus dem STUNDENbestand."""
    top = int(w.get("anzahl_coins", 250) or 250)
    aus = {}
    for z in bestand.tafel_stunde(ts, top=top):
        if not z["basis"]:
            continue
        aus[z["basis"]] = {"name": z["basis"],
                           "aenderung_1h": z["aenderung_1h"],
                           "aenderung_24h": z["aenderung_24h"],
                           "volumen_24h": z["volumen_24h"],
                           "kurs": z["kurs"]}
    kurse, fehler = _kurse_mit_basis(bestand, ts)
    return aus, kurse, fehler


QUELLEN = {
    "moondev_topmovers": quelle_topmovers,
    "moondev_marktlage": quelle_marktlage,
    "moondev_signalwelle": quelle_signalwelle,
}


# --- Funding ---------------------------------------------------------------

def funding_datei_sym(sym):
    """Ablage unter dem BINANCE-SYMBOL (BTCUSDT), nicht unter dem Instrument.

    Getrennt vom Instrumentnamen, damit der Weg aus einem Dateinamen
    (funding_stand) nicht durch die Uebersetzung muss - und damit ein
    unbekannter Instrumentname weiter laut scheitert statt still ins Leere
    zu greifen.
    """
    return os.path.join(ORDNER, "funding_%s.json" % sym)


def funding_datei(inst):
    return funding_datei_sym(historie_binance.symbol(inst))


def lade_funding_sym(sym):
    """[[ts_ms, rate], ...] aufsteigend. Fehlende Datei ist kein Fehler."""
    try:
        with open(funding_datei_sym(sym), encoding="utf-8") as f:
            reihen = json.load(f)
    except (OSError, ValueError):
        return []
    return sorted([[int(a), float(b)] for a, b in reihen], key=lambda r: r[0])


def lade_funding(inst):
    return lade_funding_sym(historie_binance.symbol(inst))


def speichere_funding(inst, reihen):
    """Entdoppelt ueber den Zeitstempel - ein zweiter Lauf ist gefahrlos."""
    bestand = {int(r[0]): [int(r[0]), float(r[1])] for r in lade_funding(inst)}
    for r in reihen:
        bestand[int(r[0])] = [int(r[0]), float(r[1])]
    os.makedirs(ORDNER, exist_ok=True)
    with open(funding_datei(inst), "w", encoding="utf-8") as f:
        json.dump([bestand[t] for t in sorted(bestand)], f)
    return len(bestand)


def funding_instrumente(wert):
    """'spur' nimmt die Instrumente der Funding-Spur - sonst eine Liste.

    Der Bezug auf die wachen ist Absicht: wer die Instrumente der Spur
    aendert, soll nicht vergessen koennen, die Reihen nachzuholen.
    """
    if str(wert).strip().lower() in ("spur", "moondev_funding"):
        pfad = os.path.join(HIER, "moondev_funding", "wachen.json")
        with open(pfad, encoding="utf-8") as f:
            w = json.load(f)
        return [str(i).upper() for i in (w.get("instrumente") or [])]
    return [t.strip().upper() for t in str(wert).split(",") if t.strip()]


def hole_funding(inst, von_ms, bis_ms):
    """Funding-Saetze von Binance-Futures (8h-Punkte), paginiert."""
    return [[int(t), float(r)]
            for t, r in historie_binance.funding(inst, von_ms, bis_ms)]


def funding_zu(reihe, ts):
    """Der letzte Satz VOR `ts` - nie der naechste.

    Ohne Cache, fuer Tests und einzelne Abfragen; im Lauf ueber `Funding`.
    """
    treffer = None
    for t, r in reihe:
        if t > int(ts):
            break
        treffer = r
    return treffer


def mark_preis(sym, ts):
    """Schlusskurs der Stundenkerze zu `ts` - Ersatz fuer den Mark-Preis.

    Aus der FEED-Reihe, nicht aus `historie_binance.lade()`: der ganze Backtest
    liest aus EINER Ablage, und nur die Feed-Reihe laesst sich im Test umbiegen.
    Ein zweiter Datenweg waere ausserdem ein zweiter Stand.

    Binance-SYMBOL, nicht der Instrumentname: die Funding-Reihen liegen unter
    dem Symbol, die Spuren fragen mit ihrem Instrumentnamen.
    """
    zeiten = _reihen_zeiten(sym, "1H")
    i = bisect.bisect_right(zeiten, int(ts)) - 1
    if i < 0:
        return None
    return lade_feed(sym, "1H")[i][4]


def funding_dict(inst, ts):
    return Funding(inst).dict_zu(ts)


def funding_stand():
    aus = {}
    if not os.path.isdir(ORDNER):
        return aus
    for name in sorted(os.listdir(ORDNER)):
        if not name.startswith("funding_") or not name.endswith(".json"):
            continue
        sym = name[len("funding_"):-len(".json")]
        reihe = lade_funding_sym(sym)
        aus[sym] = {"saetze": len(reihe),
                    "von": reihe[0][0] if reihe else None,
                    "bis": reihe[-1][0] if reihe else None}
    return aus


def main():
    p = argparse.ArgumentParser(description="Historische Daten der MoonDev-Spuren")
    p.add_argument("--universum", type=int, default=None,
                   help="Top-N USDT-Paare holen (1D)")
    p.add_argument("--takt", default="1D", choices=sorted(TAKTE))
    p.add_argument("--stunden", type=int, default=None,
                   help="Top-N PLUS Funding-Instrumente stuendlich holen")
    p.add_argument("--von", default=VON_TAG)
    p.add_argument("--faeden", type=int, default=4,
                   help="Symbole gleichzeitig holen (Latenz ist der Engpass)")
    p.add_argument("--funding", default=None,
                   help="Funding-Reihen holen: 'spur' (Instrumente der "
                        "Funding-Spur) oder Liste, z. B. BTC,ETH,SOL")
    p.add_argument("--stand", action="store_true")
    a = p.parse_args()

    if a.stand:
        print(json.dumps(stand(), indent=2, ensure_ascii=False)[:4000])
        return
    if a.universum:
        sym = universum(a.universum)
        if _verworfen:
            print("%d Paar(e) mit nicht abrufbarem Namen uebersprungen: %s"
                  % (len(_verworfen), ", ".join(sorted(_verworfen))))
        print("%d Symbole im Universum, hole %s ..." % (len(sym), a.takt))
        bericht = auffuellen(sym, a.takt, _zeitpunkt(a.von), faeden=a.faeden)
        fertig = [s for s, b in bericht.items() if b["kerzen"]]
        print("%d Reihen geschrieben, %d ohne Kerzen" % (len(fertig),
                                                         len(bericht) - len(fertig)))
        return
    if a.funding:
        von = _zeitpunkt(a.von)
        bis = int(time.time() * 1000)
        aus = {}
        for inst in funding_instrumente(a.funding):
            aus[inst] = speichere_funding(inst, hole_funding(inst, von, bis))
        print("Funding geschrieben: %s"
              % ", ".join("%s %d" % (i, n) for i, n in sorted(aus.items())))
        return
    if a.stunden:
        sym = _stunden_symbole(a.stunden)
        print("%d Symbole (Top %d + Funding-Instrumente), hole 1H ..."
              % (len(sym), a.stunden))
        bericht = auffuellen(sym, "1H", _zeitpunkt(a.von), faeden=a.faeden)
        fertig = [s for s, b in bericht.items() if b["kerzen"]]
        print("%d Reihen geschrieben, %d ohne Kerzen" % (len(fertig),
                                                         len(bericht) - len(fertig)))
        return
    p.print_help()


if __name__ == "__main__":
    main()
