# MoonDev-Spuren auf historischen Daten — Implementierungsplan

**Ziel:** Vier MoonDev-Spuren (`moondev_topmovers`, `moondev_marktlage`,
`moondev_signalwelle`, `moondev_funding`) werden auf 2021–2026 nachrechenbar;
ihre Stichprobe waechst von 8–23 Live-Runden auf vierstellige Rundenzahlen.

**Architektur:** Eine Datenschicht (`moondev_historie.py`) baut aus
Binance-Kerzen den Marktquerschnitt, den die Spuren sonst von CoinGecko holen,
und aus Binance-Futures die Funding-Reihen. Der bestehende Kern `replay.py`
bekommt zwei neue Laeufe: `lauf_feed` (Familie B ueber Tages- oder
Stundenschritte) und `lauf_c` (Spur mit eigenem `lauf()`, Familie C). Die
Spuren selbst werden NICHT veraendert — angeschlossen wird an ihren
vorhandenen Nahten (`quelle(w)` als Argument, `funding_quelle` als Modulnaht).

**Tech-Stack:** Python 3 (Standardbibliothek, `urllib`), `unittest`,
vorhandenes `historie_binance.py` (Kerzenabruf), `spur_buch.zyklus`,
`kosten_wendepunkt.runden_aus_journal`. Keine neuen Abhaengigkeiten.

**Projektweite Anforderungen** (gelten fuer jede Aufgabe implizit):
- Kein Schreibzugriff ausserhalb `Agenten/Handel/daten/` und `docs/` — die
  Spurenordner, jede `wachen.json`, `Q:\Handel_Journal` und
  `daten.bak-20260919` bleiben unberuehrt.
- Jede Ausgabe traegt `kerzenquelle: "binance"`.
- Kein stiller Ersatz: ein fehlendes Symbol oder Paar ist ein gemeldeter
  Grund, nie ein Ersatzwert.
- Tests laufen aus `Agenten/Handel` heraus: `python -m unittest tests.test_x`
  (aus `tests/` heraus scheitert `discover`).
- Nur eigene Pfade stagen (parallele Sitzung im selben Baum), nie
  `git add -A`.
- Die Spuren werden nicht nachgebaut: gerufen wird immer ihre eigene
  `signal()`/`pruefe_einstieg()`.

## Dateistruktur

| Datei | Verantwortung |
|---|---|
| `moondev_historie.py` (neu) | Universum, Feed-Kerzen mit Quote-Volumen, `Bestand`, Tafel, Funding-Reihen, Quellen-Adapter |
| `tests/test_moondev_historie.py` (neu) | Datenschicht allein, ohne Netz (Attrappe ueber `abruf_json`) |
| `replay.py` (aendern) | `lauf_feed`, `lauf_c`, erweiterte Verweigerungsliste, `SPUREN_TEIL_C` |
| `tests/test_replay_feed.py` (neu) | Adapter-Felder, Kandidaten/Kurse-Trennung, kein Schreibzugriff nach aussen |
| `historie_binance.py` (aendern) | nur `PAARE`: bare Namen `BTC`/`ETH`/`SOL` ergaenzen |
| `auswertung_alle.py` (aendern) | Backtest-Zeile zaehlt die neuen Laeufe mit |
| `MaxHirn/Wiki/Handel/Backtest-Fundament.md` | Ergebnisse, Grenzen, Lektionen |
| `MaxHirn/Archiv/TASKS.md` | T-096 schliessen, neue Aufgaben anlegen |

---

## Aufgabe 1: Datenschicht I — Universum und Feed-Kerzen

**Dateien:**
- Neu: `Agenten/Handel/moondev_historie.py`
- Test: `Agenten/Handel/tests/test_moondev_historie.py`

**Interfaces:**
- Konsumiert: `historie_binance._hole(url)`, `historie_binance._BASIS`, `historie_binance._GRENZE`
- Produziert: `ORDNER`, `TAKTE`, `universum(anzahl)`, `basis_von(sym)`,
  `normalisiere_feed(roh)`, `lade_feed(sym, takt)`, `speichere_feed(sym, takt, reihen)`,
  `hole_feed(sym, takt, von_ms, bis_ms)`, `auffuellen(symbole, takt, ...)`, `stand()`

- [ ] **Schritt 1: Testmodul anlegen — Universum, Kerzenform, Ablage**

```python
# tests/test_moondev_historie.py
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import moondev_historie as mh


class Attrappe:
    """Ersetzt den Netzabruf. Kein Test dieses Moduls darf ins Netz."""

    def __init__(self, antworten):
        self.antworten = antworten
        self.aufrufe = []

    def __call__(self, url):
        self.aufrufe.append(url)
        for teil, antwort in self.antworten.items():
            if teil in url:
                return antwort
        raise AssertionError("unerwarteter Abruf: %s" % url)


TICKER = [{"symbol": "AAAUSDT", "quoteVolume": "900"},
          {"symbol": "BBBUSDT", "quoteVolume": "100"},
          {"symbol": "CCCUSDT", "quoteVolume": "500"},
          {"symbol": "DDDETH", "quoteVolume": "9999"}]

INFO = {"symbols": [
    {"symbol": "AAAUSDT", "status": "TRADING", "baseAsset": "AAA", "quoteAsset": "USDT"},
    {"symbol": "BBBUSDT", "status": "TRADING", "baseAsset": "BBB", "quoteAsset": "USDT"},
    {"symbol": "CCCUSDT", "status": "BREAK", "baseAsset": "CCC", "quoteAsset": "USDT"},
    {"symbol": "DDDETH", "status": "TRADING", "baseAsset": "DDD", "quoteAsset": "ETH"}]}


class DatenschichtTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mh_")
        self.alt_ordner = mh.ORDNER
        mh.ORDNER = self.tmp
        self.alt_abruf = mh.abruf_json
        mh.abruf_json = Attrappe({"/ticker/24hr": TICKER, "/exchangeInfo": INFO})

    def tearDown(self):
        mh.ORDNER = self.alt_ordner
        mh.abruf_json = self.alt_abruf


class UniversumTest(DatenschichtTest):
    def test_nur_handelbare_usdt_paare(self):
        """Ein Paar mit status BREAK oder Quote ETH gehoert nicht ins Universum."""
        u = mh.universum(anzahl=10)
        self.assertEqual(["AAAUSDT", "BBBUSDT"], u)

    def test_rang_nach_quote_volumen(self):
        self.assertEqual(["AAAUSDT", "BBBUSDT"], mh.universum(anzahl=2))

    def test_anzahl_wird_eingehalten(self):
        self.assertEqual(1, len(mh.universum(anzahl=1)))

    def test_leeres_universum_wird_gemeldet_statt_still_gelassen(self):
        """Eine leere Antwort darf nicht als 'keine Kandidaten' durchgehen."""
        mh.abruf_json = Attrappe({"/ticker/24hr": [], "/exchangeInfo": INFO})
        with self.assertRaises(RuntimeError):
            mh.universum(anzahl=10)

    def test_basis_ist_der_base_asset_nicht_abgeschnitten(self):
        mh.universum(anzahl=10)
        self.assertEqual("AAA", mh.basis_von("AAAUSDT"))
        self.assertEqual("DDD", mh.basis_von("DDDETH"))


KERZEN = [[1609459200000, "100", "110", "90", "105", "7", 1609545599999, "735.5"],
          [1609545600000, "105", "120", "104", "118", "9", 1609631999999, "1006.25"]]


class KerzenformTest(DatenschichtTest):
    def test_sechstes_feld_ist_das_quote_volumen(self):
        """735.5 (Feld 7, USD) - NICHT 7 (Feld 5, Basis).

        Die Movers-Spur prueft gegen `mindest_volumen_usd` (20 Mio USD). Mit
        Basisvolumen waere die Schwelle um den Faktor Kurs verfehlt und die
        Spur haette nie gehandelt.
        """
        r = mh.normalisiere_feed(KERZEN)
        self.assertEqual([1609459200000, 100.0, 110.0, 90.0, 105.0, 735.5], r[0])
        self.assertEqual(1006.25, r[1][5])
        self.assertEqual(int, type(r[0][0]))
        self.assertEqual(float, type(r[0][5]))

    def test_speichern_haengt_an_und_entdoppelt(self):
        mh.speichere_feed("AAAUSDT", "1D", mh.normalisiere_feed(KERZEN))
        mh.speichere_feed("AAAUSDT", "1D", mh.normalisiere_feed(KERZEN))
        self.assertEqual(2, len(mh.lade_feed("AAAUSDT", "1D")))

    def test_kuerzere_antwort_ersetzt_die_historie_nicht(self):
        mh.speichere_feed("AAAUSDT", "1D", mh.normalisiere_feed(KERZEN))
        mh.speichere_feed("AAAUSDT", "1D", mh.normalisiere_feed([KERZEN[0]]))
        self.assertEqual(2, len(mh.lade_feed("AAAUSDT", "1D")))

    def test_eigener_ordner_und_eigenes_namensschema(self):
        """Die Feed-Kerze darf nie als gewoehnliche Kerze gelesen werden."""
        pfad = mh.datei("AAAUSDT", "1D")
        self.assertIn(os.path.join("historie", "feed"), pfad)
        self.assertTrue(os.path.basename(pfad).startswith("AAAUSDT_"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && python -m unittest tests.test_moondev_historie -v`
  Erwartet: FAIL — `ModuleNotFoundError: No module named 'moondev_historie'`

- [ ] **Schritt 3: Minimale Implementierung — Kopf, Universum, Kerzenform**

```python
"""Marktquerschnitt und Funding fuer die MoonDev-Spuren.

Die Spuren holen ihre Daten im Betrieb von CoinGecko (Top Mover, Marktbreite,
1h-Aenderung) und vom MoonDev-Bot (Funding). Beides ist historisch nicht
abrufbar - dieser Modul baut DIESELBEN Felder aus Binance-Daten:

  * `Bestand` haelt je Takt alle Reihen der liquidesten USDT-Paare im
    Speicher und schneidet daraus die Tafel eines Tages oder einer Stunde.
  * der Tages-Rang entsteht aus dem Quote-Volumen DIESES Tages, nicht aus
    einer einmal festgelegten Liste.
  * Funding kommt aus Binance-Futures (frei, 8h-Punkte, paginiert).

ABLAGE: daten/historie/feed/<SYMBOL>_<TAKT>.json, Reihen
[ts_ms, o, h, l, c, volumen_quote] - das sechste Feld ist das QUOTE-Volumen
(Binance-Feld 7, USD), NICHT das Basisvolumen wie in historie_binance.py. Wer eine
Feed-Kerze gegen `mindest_volumen_usd` prueft, braucht genau diese Zahl.

Jedes Ergebnis traegt `kerzenquelle: "binance"` - Binance ist ein ausgewiesener
Ersatz fuer die Boersen der Spuren, kein OKX- oder Kraken-Preis.

Aufruf:
    python moondev_historie.py --universum 300 --takt 1D
    python moondev_historie.py --stunden 40
    python moondev_historie.py --funding BTC,ETH,SOL,HYPE,FIL,ZEC
    python moondev_historie.py --stand
"""

import json
import os
import time

import historie

HIER = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(HIER, "daten", "historie", "feed")

TAKTE = {"1D": "1d", "1H": "1h"}
KENNUNG = "feed"

_BASIS = historie_binance._BASIS
_FUTURES = historie_binance._FUTURES
_GRENZE = historie_binance._GRENZE          # Binance liefert hoechstens 1000 je Abruf

# Naht fuer Tests: None -> echtes Netz (siehe historie_binance._hole).
abruf_json = None

_basis = {}                          # Binance-Symbol -> Basiswert ("AAAUSDT" -> "AAA")
_universum = []                      # Binance-Symbole in Rangfolge


def _hole(url):
    if abruf_json is not None:
        return abruf_json(url)
    return historie_binance._hole(url)


def universum(anzahl=300):
    """Die liquidesten USDT-Spot-Paare als Binance-Symbole.

    Die Auswahl ist der Stand JETZT (gemessen wird das Quote-Volumen der
    letzten 24 h). Das ist die eine Grenze, die dieses Verfahren nicht
    aufloesen kann: Paare, die vor heute delistet wurden, fehlen. Der Rang
    INNERHALB des geladenen Universums entsteht spaeter je Tag neu.
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
    Bewusst NICHT `historie_binance.reihen_normalisieren`: das nimmt [1:6] und traegt
    damit das Basisvolumen.
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
    "keine neuen Zeitstempel" - gegen eine Attrappe, die dieselbe Seite
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
```

- [ ] **Schritt 4: Auffuellen, Stand, Universumsdatei nachtragen**

```python
def auffuellen(symbole, takt="1D", von_ms=None, bis_ms=None):
    """Feed-Kerzen nachladen. Bericht je Symbol: neu/gesamt."""
    von_ms = von_ms or int(time.mktime(time.strptime("2021-01-01", "%Y-%m-%d"))) * 1000
    bis_ms = bis_ms or int(time.time() * 1000)
    bericht = {}
    for sym in symbole:
        neu = hole_feed(sym, takt, von_ms, bis_ms)
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
```

- [ ] **Schritt 5: Test laufen lassen, PASS verifizieren**
  Run: `python -m unittest tests.test_moondev_historie -v`
  Erwartet: 9 Tests, OK

- [ ] **Schritt 6: `PAARE` in `historie_binance.py` um die bare Namen ergaenzen**

In `Agenten/Handel/historie_binance.py`, im Dict `PAARE` (Zeile 33 ff.) hinter
`"BTC-USDC": "BTCUSDT",`:

```python
    # Bare Namen: so heissen die Instrumente der Funding-Spur
    # (moondev_funding/wachen.json: BTC, ETH, SOL, HYPE, FIL, ZEC).
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
```

Test dafuer (in `tests/test_moondev_historie.py` anhaengen):

```python
class PaareTest(unittest.TestCase):
    def test_bare_namen_der_funding_spur(self):
        """Ohne diese Namen faellt die Funding-Spur auf einen KeyError."""
        for inst, sym in (("BTC", "BTCUSDT"), ("ETH", "ETHUSDT"), ("SOL", "SOLUSDT")):
            self.assertEqual(sym, historie_binance.symbol(inst))
```

- [ ] **Schritt 7: Committen**

```
git add Agenten/Handel/moondev_historie.py Agenten/Handel/tests/test_moondev_historie.py Agenten/Handel/historie_binance.py
git commit -m "Datenschicht: Universum und Feed-Kerzen mit Quote-Volumen"
```

---

## Aufgabe 2: Datenschicht II — Bestand und Tafel

**Dateien:**
- Aendern: `Agenten/Handel/moondev_historie.py`
- Test: `Agenten/Handel/tests/test_moondev_historie.py`

**Interfaces:**
- Konsumiert: `lade_feed`, `basis_von` (Aufgabe 1)
- Produziert: `Bestand.laden(takt, symbole=None)`, `Bestand.schritte(mindest_symbole, von_ms, bis_ms)`,
  `Bestand.tafel(ts, top=None)`, `Bestand.kurse(ts)`, `Bestand.breite(ts, top=None)`,
  `Bestand.basis(sym)`

- [ ] **Schritt 1: Fehlschlagende Tests schreiben**

```python
class TafelTest(DatenschichtTest):
    def setUp(self):
        super().setUp()
        # Drei Symbole, vier Tage. CCC hat ab Tag 3 das groesste Volumen.
        self.reihen = {
            "AAAUSDT": [[0, 10, 10, 10, 10, 100],
                        [86400000, 10, 10, 10, 12, 100],
                        [172800000, 12, 12, 12, 12, 50],
                        [259200000, 12, 12, 12, 13, 50]],
            "BBBUSDT": [[0, 5, 5, 5, 5, 200],
                        [86400000, 5, 5, 5, 4, 200],
                        [172800000, 4, 4, 4, 4, 300],
                        [259200000, 4, 4, 4, 3, 300]],
            "CCCUSDT": [[172800000, 1, 1, 1, 1, 900],
                        [259200000, 1, 1, 1, 2, 900]],
        }
        for sym, k in self.reihen.items():
            mh.speichere_feed(sym, "1D", k)
        self.b = mh.Bestand.laden("1D")

    def test_aenderung_24h_ist_schluss_gegen_vortagesschluss(self):
        t = self.b.tafel(86400000)
        aaa = [z for z in t if z["symbol"] == "AAAUSDT"][0]
        self.assertAlmostEqual(20.0, aaa["aenderung_24h"], places=6)   # 12/10
        bbb = [z for z in t if z["symbol"] == "BBBUSDT"][0]
        self.assertAlmostEqual(-20.0, bbb["aenderung_24h"], places=6)  # 4/5

    def test_rang_entsteht_je_tag_aus_dem_volumen_dieses_tages(self):
        """Am Tag 3 fuehrt CCC (900), obwohl es am Tag 1 gar nicht existierte."""
        self.assertEqual("CCCUSDT", self.b.tafel(259200000)[0]["symbol"])

    def test_erster_tag_einer_reihe_hat_keine_aenderung(self):
        """Ohne Vortagesschliessung kein geschaetzter Wert - kein Eintrag.

        CCC beginnt am Tag 3 (Index 2). An seinem ERSTEN Tag hat es keine
        Vortagesschliessung und darf nicht in der Tafel stehen; am Tag 4 steht
        es drin.
        """
        self.assertNotIn("CCCUSDT",
                         [z["symbol"] for z in self.b.tafel(172800000)])
        self.assertIn("CCCUSDT",
                      [z["symbol"] for z in self.b.tafel(259200000)])

    def test_top_schneidet_ab_und_setzt_den_rang(self):
        t = self.b.tafel(259200000, top=2)
        self.assertEqual(["CCCUSDT", "AAAUSDT"], [z["symbol"] for z in t])
        self.assertEqual([1, 2], [z["rang"] for z in t])

    def test_kurse_umfassen_ALLE_geladenen_symbole(self):
        """Ein offenes Symbol ausserhalb der Top N muss einen Kurs haben.

        `spur_buch.pruefe_ausstiege` arbeitet ueber `kurse`. Fehlt dort ein
        Symbol, schliesst die Position NIE - der Backtest liefe mit einer
        Leiche im Buch und meldete weniger Runden, als es gab.
        """
        k = self.b.kurse(259200000)
        self.assertEqual({"AAAUSDT", "BBBUSDT", "CCCUSDT"}, set(k))
        self.assertAlmostEqual(13.0, k["AAAUSDT"])

    def test_breite_ist_der_anteil_positiver_aenderungen(self):
        """Tag 2: AAA +20 %, BBB -20 % -> 0.5. CCC hat noch keine Aenderung."""
        self.assertAlmostEqual(0.5, self.b.breite(86400000), places=6)

    def test_schritte_respektieren_die_mindestzahl_symbole(self):
        s = self.b.schritte(mindest_symbole=3)
        self.assertEqual([259200000], s)
        s2 = self.b.schritte(mindest_symbole=2)
        self.assertEqual([86400000, 172800000, 259200000], s2)
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `python -m unittest tests.test_moondev_historie.TafelTest -v`
  Erwartet: FAIL — `AttributeError: module 'moondev_historie' has no attribute 'Bestand'`

- [ ] **Schritt 3: Bestand und Tafel implementieren**

```python
class Bestand:
    """Alle Feed-Reihen EINES Taktes im Speicher, mit Zeitindex je Symbol.

    Der Walk fragt bei JEDEM Schritt nach der Tafel. 300 Symbole je Schritt von
    der Platte zu lesen waere bei 2.000 Tagen eine halbe Million Dateizugriffe;
    deshalb wird EINMAL geladen und danach aus dem Speicher geschnitten.
    """

    def __init__(self, takt, reihen):
        self.takt = takt
        self.reihen = reihen
        self.index = {s: {r[0]: i for i, r in enumerate(k)}
                      for s, k in reihen.items()}
        self.anzahl_je_ts = {}
        for k in reihen.values():
            for r in k:
                self.anzahl_je_ts[r[0]] = self.anzahl_je_ts.get(r[0], 0) + 1

    @classmethod
    def laden(cls, takt="1D", symbole=None):
        if symbole is None:
            symbole = _lade_universum() or _symbole_auf_der_platte(takt)
        reihen = {}
        for sym in symbole:
            k = lade_feed(sym, takt)
            if k:
                reihen[sym] = k
        if not reihen:
            raise RuntimeError("keine Feed-Kerzen - erst "
                               "'python moondev_historie.py --universum 300 --takt %s'"
                               % takt)
        return cls(takt, reihen)

    def basis(self, sym):
        return basis_von(sym) or sym

    def schritte(self, mindest_symbole=30, von_ms=None, bis_ms=None):
        """Zeitstempel, an denen mindestens `mindest_symbole` eine Kerze haben.

        Die Mindestzahl ist kein Schmuck: an einem Tag mit drei Reihen waere
        die Marktbreite eine Aussage ueber drei Coins.
        """
        aus = []
        for ts in sorted(self.anzahl_je_ts):
            if von_ms and ts < int(von_ms):
                continue
            if bis_ms and ts > int(bis_ms):
                continue
            if self.anzahl_je_ts[ts] >= int(mindest_symbole):
                aus.append(ts)
        return aus

    def tafel(self, ts, top=None):
        """Marktquerschnitt EINES Zeitpunkts, absteigend nach Quote-Volumen.

        Der Rang entsteht aus dem Volumen DIESES Zeitpunkts - eine einmal
        festgelegte Liste wuerde die Gegenwart in die Vergangenheit tragen.
        """
        zeilen = []
        for sym, k in self.reihen.items():
            i = self.index[sym].get(ts)
            if i is None or i < 1:
                continue                      # erster Tag: keine Aenderung
            c, vor = float(k[i][4]), float(k[i - 1][4])
            if not vor:
                continue
            zeilen.append({"symbol": sym, "basis": self.basis(sym), "kurs": c,
                           "aenderung_24h": (c / vor - 1.0) * 100.0,
                           "volumen_24h": float(k[i][5])})
        zeilen.sort(key=lambda z: (-z["volumen_24h"], z["symbol"]))
        for n, z in enumerate(zeilen, 1):
            z["rang"] = n
        return zeilen[:int(top)] if top else zeilen

    def kurse(self, ts):
        """Kurs JEDES Symbols, das an diesem Zeitpunkt eine Kerze hat."""
        aus = {}
        for sym, k in self.reihen.items():
            i = self.index[sym].get(ts)
            if i is not None:
                aus[sym] = float(k[i][4])
        return aus

    def breite(self, ts, top=None):
        """Anteil positiver 24h-Aenderungen unter den Top `top`."""
        zeilen = self.tafel(ts, top)
        if not zeilen:
            return None
        return sum(1 for z in zeilen if z["aenderung_24h"] > 0) / float(len(zeilen))
```

`_symbole_auf_der_platte(takt)` als Rueckfall, wenn `_universum.json` fehlt:

```python
def _symbole_auf_der_platte(takt="1D"):
    """Rueckfall: was liegt. Der Stand ist dann der Abrufzeitpunkt der Dateien."""
    if not os.path.isdir(ORDNER):
        return []
    aus = []
    for name in sorted(os.listdir(ORDNER)):
        if name.startswith("_") or not name.endswith("_%s.json" % takt):
            continue
        aus.append(name[:-(len(takt) + 6)])
    return aus
```

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `python -m unittest tests.test_moondev_historie -v`
  Erwartet: 16 Tests, OK

- [ ] **Schritt 5: Committen**

```
git add Agenten/Handel/moondev_historie.py Agenten/Handel/tests/test_moondev_historie.py
git commit -m "Datenschicht: Bestand und Tafel, Rang je Tag aus dem Tagesvolumen"
```

---

## Aufgabe 3: Datenschicht III — Stundentafel und Funding-Reihen

**Dateien:**
- Aendern: `Agenten/Handel/moondev_historie.py`
- Test: `Agenten/Handel/tests/test_moondev_historie.py`

**Interfaces:**
- Konsumiert: `Bestand` (Aufgabe 2), `historie_binance.funding`, `historie_binance.symbol`, `historie_binance.lade`
- Produziert: `Bestand.tafel_stunde(ts, top=None)`, `hole_funding(inst, von_ms, bis_ms)`,
  `lade_funding(inst)`, `speichere_funding(inst, reihen)`, `funding_zu(reihe, ts)`,
  `mark_preis(inst, ts)`, `funding_stand()`, `funding_dict(inst, ts)`

- [ ] **Schritt 1: Fehlschlagende Tests schreiben**

```python
class StundentafelTest(DatenschichtTest):
    def setUp(self):
        super().setUp()
        # 26 Stundenkerzen: Kurs steigt von 100 auf 125, je Stunde +1.
        k = []
        for i in range(26):
            c = 100.0 + i
            k.append([i * 3600000, c, c, c, c, 10.0])
        mh.speichere_feed("AAAUSDT", "1H", k)
        mh.speichere_feed("BBBUSDT", "1H", k)
        self.b = mh.Bestand.laden("1H")

    def test_aenderung_1h_ist_schluss_gegen_vorstunde(self):
        t = self.b.tafel_stunde(25 * 3600000)
        z = [x for x in t if x["symbol"] == "AAAUSDT"][0]
        self.assertAlmostEqual((125.0 / 124.0 - 1.0) * 100.0,
                               z["aenderung_1h"], places=6)

    def test_aenderung_24h_geht_24_kerzen_zurueck(self):
        t = self.b.tafel_stunde(25 * 3600000)
        z = [x for x in t if x["symbol"] == "AAAUSDT"][0]
        self.assertAlmostEqual((125.0 / 101.0 - 1.0) * 100.0,
                               z["aenderung_24h"], places=6)

    def test_ohne_24_kerzen_vorlauf_kein_eintrag(self):
        """Ein Wert aus 3 Kerzen waere keine 24h-Aenderung."""
        t = self.b.tafel_stunde(5 * 3600000)
        self.assertEqual([], t)

    def test_volumen_24h_ist_die_summe_der_letzten_24_kerzen(self):
        t = self.b.tafel_stunde(25 * 3600000)
        z = [x for x in t if x["symbol"] == "AAAUSDT"][0]
        self.assertAlmostEqual(240.0, z["volumen_24h"], places=6)


class FundingTest(DatenschichtTest):
    def test_funding_zu_nimmt_den_letzten_satz_DVOR_dem_zeitpunkt(self):
        """Nie den naechsten: das waere ein Blick in die Zukunft."""
        reihe = [[0, 0.0001], [28800000, 0.0002], [57600000, 0.0003]]
        self.assertEqual(0.0002, mh.funding_zu(reihe, 40000000))
        self.assertEqual(0.0002, mh.funding_zu(reihe, 28800000))

    def test_vor_dem_ersten_satz_gibt_es_keinen_wert(self):
        self.assertIsNone(mh.funding_zu([[28800000, 0.0002]], 1000))

    def test_funding_wird_entdoppelt_gespeichert(self):
        mh.speichere_funding("BTCUSDT", [[0, 0.0001]])
        mh.speichere_funding("BTCUSDT", [[0, 0.0001], [28800000, 0.0002]])
        self.assertEqual(2, len(mh.lade_funding("BTCUSDT")))

    def test_mark_preis_kommt_aus_der_stundenkerze(self):
        mh.speichere_feed("BTCUSDT", "1H", [[0, 1, 1, 1, 50000.0, 10]],
                          )
        self.assertEqual(50000.0, mh.mark_preis("BTCUSDT", 0))
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `python -m unittest tests.test_moondev_historie.StundentafelTest tests.test_moondev_historie.FundingTest -v`
  Erwartet: FAIL — `AttributeError ... 'tafel_stunde'`

- [ ] **Schritt 3: Implementieren**

```python
    def tafel_stunde(self, ts, top=None):
        """Stundenquerschnitt mit 1h- und 24h-Aenderung.

        Fuer `moondev_signalwelle`: ihre Regel liest `aenderung_1h`, das laesst
        sich aus Tageskerzen nicht ehrlich bilden. Verlangt 24 Kerzen Vorlauf -
        ein Wert aus drei Kerzen waere keine 24h-Aenderung.
        """
        zeilen = []
        for sym, k in self.reihen.items():
            i = self.index[sym].get(ts)
            if i is None or i < 24:
                continue
            c = float(k[i][4])
            c_vor, c_tag = float(k[i - 1][4]), float(k[i - 24][4])
            if not c_vor or not c_tag:
                continue
            zeilen.append({"symbol": sym, "basis": self.basis(sym), "kurs": c,
                           "aenderung_1h": (c / c_vor - 1.0) * 100.0,
                           "aenderung_24h": (c / c_tag - 1.0) * 100.0,
                           "volumen_24h": sum(float(k[j][5])
                                              for j in range(i - 23, i + 1))})
        zeilen.sort(key=lambda z: (-z["volumen_24h"], z["symbol"]))
        for n, z in enumerate(zeilen, 1):
            z["rang"] = n
        return zeilen[:int(top)] if top else zeilen
```

```python
# --- Funding ---------------------------------------------------------------

def funding_datei(inst):
    return os.path.join(ORDNER, "funding_%s.json" % historie_binance.symbol(inst))


def lade_funding(inst):
    """[[ts_ms, rate], ...] aufsteigend. Fehlende Datei ist kein Fehler."""
    try:
        with open(funding_datei(inst), encoding="utf-8") as f:
            reihen = json.load(f)
    except (OSError, ValueError):
        return []
    return sorted([[int(a), float(b)] for a, b in reihen], key=lambda r: r[0])


def speichere_funding(inst, reihen):
    bestand = {int(r[0]): [int(r[0]), float(r[1])] for r in lade_funding(inst)}
    for r in reihen:
        bestand[int(r[0])] = [int(r[0]), float(r[1])]
    os.makedirs(ORDNER, exist_ok=True)
    with open(funding_datei(inst), "w", encoding="utf-8") as f:
        json.dump([bestand[t] for t in sorted(bestand)], f)
    return len(bestand)


def hole_funding(inst, von_ms, bis_ms):
    """Funding-Saetze von Binance-Futures (8h-Punkte), paginiert."""
    return [[int(t), float(r)] for t, r in historie_binance.funding(inst, von_ms, bis_ms)]


def funding_zu(reihe, ts):
    """Der letzte Satz VOR `ts` - nie der naechste.

    Ein Funding-Satz gilt ab seinem Zeitstempel bis zum naechsten; wer den
    naechsten nimmt, handelt auf einer Zahl, die es damals noch nicht gab.
    """
    treffer = None
    for t, r in reihe:
        if t > int(ts):
            break
        treffer = r
    return treffer


def mark_preis(sym, ts):
    """Schlusskurs der Stundenkerze zu `ts` - Ersatz fuer den Mark-Preis.

    Aus der FEED-Reihe, nicht aus `historie_binance.lade()`: der ganze Backtest liest
    aus EINER Ablage, und nur die Feed-Reihe laesst sich im Test umbiegen. Ein
    zweiter Datenweg waere ausserdem ein zweiter Stand.

    Binance-Symbol, NICHT der Instrumentname: die Funding-Reihen liegen unter
    dem Symbol, die Spuren fragen mit ihrem Instrumentnamen.
    """
    k = lade_feed(sym, "1H")
    treffer = None
    for r in k:
        if r[0] > int(ts):
            break
        treffer = r[4]
    return treffer


def funding_dict(inst, ts):
    """Genau die Form, die `moondev_funding.pruefe_einstieg` liest."""
    rate = funding_zu(lade_funding(inst), ts)
    if rate is None:
        return None
    kurs = mark_preis(historie_binance.symbol(inst), ts)
    if not kurs:
        return None
    return {"funding_rate": rate, "mark_price": float(kurs)}


def funding_stand():
    aus = {}
    for name in sorted(os.listdir(ORDNER)) if os.path.isdir(ORDNER) else []:
        if not name.startswith("funding_") or not name.endswith(".json"):
            continue
        reihe = lade_funding(name[len("funding_"):-len(".json")])
        aus[name[len("funding_"):-len(".json")]] = {
            "saetze": len(reihe),
            "von": reihe[0][0] if reihe else None,
            "bis": reihe[-1][0] if reihe else None}
    return aus
```

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `python -m unittest tests.test_moondev_historie -v`
  Erwartet: 24 Tests, OK

- [ ] **Schritt 5: Committen**

```
git add Agenten/Handel/moondev_historie.py Agenten/Handel/tests/test_moondev_historie.py
git commit -m "Datenschicht: Stundentafel und Funding-Reihen mit Vorwaertsschnitt"
```

---

## Aufgabe 4: Quellen-Adapter je Spur

**Dateien:**
- Aendern: `Agenten/Handel/moondev_historie.py`
- Test: `Agenten/Handel/tests/test_replay_feed.py` (neu)

**Interfaces:**
- Konsumiert: `Bestand.tafel`, `Bestand.tafel_stunde`, `Bestand.kurse` (Aufgaben 2, 3)
- Produziert: `QUELLEN` (Dict Spurname -> Funktion), `quelle_topmovers(bestand, ts, w)`,
  `quelle_marktlage(bestand, ts, w)`, `quelle_signalwelle(bestand, ts, w)`,
  `FELDER` (Dict Spurname -> Felder, die ihre Entscheidung liest)

- [ ] **Schritt 1: Fehlschlagende Tests schreiben**

```python
# tests/test_replay_feed.py
"""Der Adapter muss GENAU die Felder liefern, die die Spur entscheidet.

Ein Adapter mit falschen Feldern laesst die Spur still ohne Signal laufen und
erzeugt eine Zahl, die wie ein Messwert aussieht. Deshalb wird hier gegen den
QUELLTEXT der Spur geprueft, nicht gegen eine gepflegte Liste: wer die Spur
umbaut, soll hier einen roten Test bekommen.
"""
import inspect
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import moondev_historie as mh
import replay


SPUREN = ("moondev_topmovers", "moondev_marktlage", "moondev_signalwelle")


class ModulwaechterMixin:
    """Kein Test darf ausserhalb von daten/ schreiben."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.tmp = tempfile.mkdtemp(prefix="feed_")
        cls.alt = mh.ORDNER
        mh.ORDNER = cls.tmp

    @classmethod
    def tearDownClass(cls):
        mh.ORDNER = cls.alt


class FeldTest(ModulwaechterMixin, unittest.TestCase):
    def test_adapter_liefert_was_die_entscheidung_liest(self):
        """Quelltext der Spur gegen die Felder des Adapters."""
        for spur in SPUREN:
            quelle = inspect.getsource(replay.spur_modul(spur).quelle)
            for feld in mh.FELDER[spur]:
                self.assertIn(feld, quelle,
                              "%s: Adapter liefert %r, die Spur liest es nicht"
                              % (spur, feld))
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `python -m unittest tests.test_replay_feed -v`
  Erwartet: FAIL — `AttributeError ... 'FELDER'`

- [ ] **Schritt 3: Adapter implementieren**

```python
# --- Quellen je Spur -------------------------------------------------------
# Jede Funktion liefert GENAU die Form, die `quelle(w)` der Spur zurueckgibt:
# (daten, kurse, fehler). `daten` sind die Kandidaten (Top N), `kurse` traegt
# ALLE geladenen Symbole - ein offenes Symbol ausserhalb der Top N muss einen
# Kurs haben, sonst schliesst seine Position nie (spur_buch.pruefe_ausstiege
# arbeitet ueber `kurse`).

FELDER = {
    "moondev_topmovers": ("name", "aenderung_24h", "volumen_24h", "kurs"),
    "moondev_marktlage": ("name", "btc_aenderung_24h", "breite", "kurs"),
    "moondev_signalwelle": ("name", "aenderung_1h", "aenderung_24h",
                            "volumen_24h", "kurs"),
}


def _kurse_mit_basis(bestand, ts, fremde=None):
    """Kurse auf Basiswerte umschluesseln - die Spuren sprechen CoinGecko-Namen.

    `fremde` traegt Symbole offener Positionen, die im Bestand fehlen (delistet
    oder ausserhalb des Universums). Sie bekommen keinen erfundenen Kurs: sie
    fehlen und werden gemeldet.
    """
    kurse, fehlen = {}, []
    for sym, kurs in bestand.kurse(ts).items():
        kurse[bestand.basis(sym)] = kurs
    for s in (fremde or ()):
        if s not in kurse:
            fehlen.append("%s: kein Kurs am Zeitpunkt" % s)
    return kurse, fehlen


def quelle_topmovers(bestand, ts, w):
    """Top-Mover: 24h-Aenderung und Volumen ueber die Top `anzahl_coins`."""
    zeilen = bestand.tafel(ts, top=int(w.get("anzahl_coins", 250)))
    aus = {}
    for z in zeilen:
        aus[z["basis"]] = {"name": z["basis"],
                           "aenderung_24h": z["aenderung_24h"],
                           "volumen_24h": z["volumen_24h"],
                           "kurs": z["kurs"]}
    kurse, fehler = _kurse_mit_basis(bestand, ts)
    return aus, kurse, fehler


def quelle_marktlage(bestand, ts, w):
    """BTC-Aenderung plus Marktbreite aus den Top 100."""
    top = int(w.get("anzahl_coins", 100) or 100)
    breite = bestand.breite(ts, top=top)
    zeilen = bestand.tafel(ts, top=top)
    btc = [z for z in zeilen if z["basis"] == "BTC"]
    if not btc or breite is None:
        return {}, {}, ["BTC oder Breite fehlt am Zeitpunkt"]
    z = btc[0]
    kurse, fehler = _kurse_mit_basis(bestand, ts)
    return ({"BTC": {"name": "Bitcoin", "btc_aenderung_24h": z["aenderung_24h"],
                     "breite": breite, "kurs": z["kurs"]}}, kurse, fehler)


def quelle_signalwelle(bestand, ts, w):
    """Signalwelle: 1h-Aenderung und 24h-Volumen (Stundenbestand)."""
    zeilen = bestand.tafel_stunde(ts, top=int(w.get("anzahl_coins", 250)))
    aus = {}
    for z in zeilen:
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
```

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `python -m unittest tests.test_replay_feed -v`
  Erwartet: OK

- [ ] **Schritt 5: Committen**

```
git add Agenten/Handel/moondev_historie.py Agenten/Handel/tests/test_replay_feed.py
git commit -m "Quellen-Adapter: drei Feed-Spuren an den historischen Querschnitt"
```

---

## Aufgabe 5: `lauf_feed` — Familie B ueber Tages- und Stundenschritte

**Dateien:**
- Aendern: `Agenten/Handel/replay.py`
- Test: `Agenten/Handel/tests/test_replay_feed.py`

**Interfaces:**
- Konsumiert: `moondev_historie.Bestand`, `moondev_historie.QUELLEN`, `buch_ordner`, `kennzahlen`, `_kein_bus`
- Produziert: `lauf_feed(spur, gebuehr_pct, lauf, takt="1D", mindest_symbole=30, von_ms=None, bis_ms=None, still=True)`

- [ ] **Schritt 1: Fehlschlagende Tests schreiben**

```python
class LaufFeedTest(ModulwaechterMixin, unittest.TestCase):
    def test_adapter_sieht_den_stand_des_schritts_nicht_den_letzten(self):
        """Zwei Zeitpunkte muessen zwei verschiedene Tafeln ergeben.

        Waere der Zeitpunkt fest verdrahtet, saehe jeder Schritt denselben
        Markt - und der Lauf saehe wie eine Messung aus.
        """
        mh.speichere_feed("AAAUSDT", "1D", [[0, 1, 1, 1, 1, 10],
                                            [86400000, 1, 1, 1, 2, 10]])
        mh.speichere_feed("BBBUSDT", "1D", [[0, 1, 1, 1, 5, 20],
                                            [86400000, 1, 1, 1, 9, 20]])
        b = mh.Bestand.laden("1D")
        w = {"anzahl_coins": 10}
        frueh = mh.QUELLEN["moondev_topmovers"](b, 86400000, w)[0]
        self.assertAlmostEqual(100.0, frueh["AAAUSDT"]["aenderung_24h"], places=6)
        self.assertAlmostEqual(80.0, frueh["BBBUSDT"]["aenderung_24h"], places=6)

    def test_unbekannte_spur_wird_gemeldet(self):
        with self.assertRaises(KeyError):
            replay.lauf_feed("diegibtesnicht", 0.05, "t")

    def test_verweigerte_spur_wird_nicht_geraten(self):
        with self.assertRaises(RuntimeError):
            replay.lauf_feed("moondev_sniper", 0.05, "t")
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `python -m unittest tests.test_replay_feed.LaufFeedTest -v`
  Erwartet: FAIL — `AttributeError ... 'lauf_feed'`

- [ ] **Schritt 3: Implementieren**

```python
def lauf_feed(spur, gebuehr_pct, lauf, takt="1D", mindest_symbole=30,
              von_ms=None, bis_ms=None, still=True):
    """Familie B ueber den Marktquerschnitt: ein `spur_buch.zyklus` je Schritt.

    Der Unterschied zu `lauf_b`: dort ist eine Kerze ein Schritt je
    Instrument, hier ist ein ZEITPUNKT ein Schritt ueber alle Kandidaten - die
    Feed-Spuren entscheiden ueber einen Marktquerschnitt, nicht ueber eine
    Reihe. Die Tafel liefert genau die Felder, die ihre `quelle()` sonst von
    CoinGecko holt.

    `schritte` kommt aus dem Bestand (Zeitstempel mit mindestens
    `mindest_symbole` Reihen): ein Tag mit drei Reihen waere keine
    Marktbreite. Stilllegung wie in `lauf_b` - `ereignis.lauf`,
    `spur_buch.spiegeln` und die Risikostufe.
    """
    import contextlib
    import io

    import moondev_historie
    import spur_buch
    import ereignis

    if spur in NICHT_NACHRECHENBAR:
        raise RuntimeError("%s ist nicht nachrechenbar: %s"
                           % (spur, NICHT_NACHRECHENBAR[spur]))
    if spur not in moondev_historie.QUELLEN:
        raise KeyError("kein Quellen-Adapter fuer %r - bekannt: %s"
                       % (spur, ", ".join(sorted(moondev_historie.QUELLEN))))

    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf)
    with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)
    bestand = moondev_historie.Bestand.laden(takt)
    schritte = bestand.schritte(mindest_symbole, von_ms, bis_ms)
    if not schritte:
        raise RuntimeError("keine Schritte mit mindestens %d Reihen - "
                           "Universum zu klein oder Zeitraum falsch"
                           % mindest_symbole)

    quelle_adapter = moondev_historie.QUELLEN[spur]
    alt_schreiben, alt_zeit = spur_buch.SCHREIBEN, spur_buch.zeit_quelle
    alt_spiegeln, alt_lauf = spur_buch.spiegeln, ereignis.lauf
    alt_risiko = os.environ.pop("HANDEL_RISIKO", None)
    puffer = io.StringIO()
    try:
        spur_buch.SCHREIBEN = True          # ins BACKTEST-Journal
        spur_buch.spiegeln = lambda *a, **k: None
        ereignis.lauf = _kein_bus
        with contextlib.redirect_stdout(puffer if still else sys.stdout):
            for ts in schritte:
                daten, kurse, fehler = quelle_adapter(bestand, ts, w)
                if not daten:
                    continue
                quelle = (lambda _w, _d=daten, _k=kurse, _f=fehler:
                          (_d, _k, _f))
                spur_buch.zeit_quelle = lambda _t=ts: dt.datetime.fromtimestamp(
                    _t / 1000.0, dt.timezone.utc).isoformat(timespec="seconds")
                spur_buch.zyklus(ordner, quelle, modul.signal, "papier",
                                 "handel/" + spur)
    finally:
        spur_buch.SCHREIBEN, spur_buch.zeit_quelle = alt_schreiben, alt_zeit
        spur_buch.spiegeln, ereignis.lauf = alt_spiegeln, alt_lauf
        if alt_risiko is not None:
            os.environ["HANDEL_RISIKO"] = alt_risiko
    journal = os.path.join(ordner, "handelsjournal.csv")
    k = kennzahlen(journal)
    k["schritte"] = len(schritte)
    k["takt"] = takt
    k["universum"] = len(bestand.reihen)
    k["kerzenquelle"] = "binance"
    return k, len(puffer.getvalue().splitlines())
```

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `python -m unittest tests.test_replay_feed -v`
  Erwartet: OK

- [ ] **Schritt 5: Committen**

```
git add Agenten/Handel/replay.py Agenten/Handel/tests/test_replay_feed.py
git commit -m "replay: lauf_feed faehrt Feed-Spuren ueber den Marktquerschnitt"
```

---

## Aufgabe 6: `lauf_c` — `moondev_funding` mit eigenem `lauf()`

**Dateien:**
- Aendern: `Agenten/Handel/replay.py`
- Test: `Agenten/Handel/tests/test_replay_feed.py`

**Interfaces:**
- Konsumiert: `moondev_historie.lade_funding`, `funding_dict`, `funding_stand`, `buch_ordner`, `kennzahlen`
- Produziert: `SPUREN_TEIL_C`, `lauf_c(spur, gebuehr_pct, lauf, von_ms=None, bis_ms=None, still=True)`

- [ ] **Schritt 1: Fehlschlagende Tests schreiben**

```python
class LaufCTest(ModulwaechterMixin, unittest.TestCase):
    def test_funding_ist_eigene_familie_und_nicht_teil_a(self):
        self.assertIn("moondev_funding", replay.SPUREN_TEIL_C)
        self.assertNotIn("moondev_funding", replay.SPUREN_TEIL_A)

    def test_jede_spur_hat_einen_boersensatz(self):
        for spur in replay.SPUREN_TEIL_A + replay.SPUREN_TEIL_C:
            self.assertGreater(replay.gebuehr_fuer(spur, {}), 0.0)

    def test_schrittweite_ist_der_funding_takt(self):
        """Acht Stunden - der Takt, in dem sich ein Funding-Satz aendert."""
        self.assertEqual(8, replay.FUNDING_STUNDEN)


class KandidatenKurseTest(ModulwaechterMixin, unittest.TestCase):
    def test_offenes_symbol_ausserhalb_der_top_n_hat_trotzdem_einen_kurs(self):
        """Sonst schliesst die Position nie (pruefe_ausstiege geht ueber kurse)."""
        for sym in ("AAAUSDT", "BBBUSDT", "CCCUSDT"):
            mh.speichere_feed(sym, "1D", [[172800000, 1, 1, 1, 1, 10],
                                          [259200000, 1, 1, 1, 2, 10]])
        b = mh.Bestand.laden("1D")
        daten, kurse, _ = mh.QUELLEN["moondev_topmovers"](b, 259200000,
                                                          {"anzahl_coins": 1})
        self.assertEqual(1, len(daten))
        self.assertEqual(3, len(kurse))
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `python -m unittest tests.test_replay_feed -v`
  Erwartet: FAIL — `AttributeError ... 'SPUREN_TEIL_C'`

- [ ] **Schritt 3: Implementieren**

In `replay.py` den Kopf ergaenzen:

```python
# Spuren mit eigenem `lauf(modus)` und eigenen Nahtnamen (Familie C). Sie
# fuehren kein Kerzenbuch: `moondev_funding` liest einen Funding-Satz je
# Symbol und haelt ihren Zustand selbst.
SPUREN_TEIL_C = ("moondev_funding",)

# Ein Funding-Satz aendert sich alle acht Stunden - so weit ist ein Schritt.
FUNDING_STUNDEN = 8
```

`moondev_funding` aus `SPUREN_TEIL_A` entfernen (Zeile 37/38).

```python
def lauf_c(spur, gebuehr_pct, lauf, von_ms=None, bis_ms=None, still=True):
    """Familie C: eine Spur mit eigenem `lauf(modus)` und eigenem Buch.

    Anders als in Familie A wird hier nichts abgefangen: die Spur schreibt ihr
    Journal und ihren Zustand SELBST - nur die DREI PFADE zeigen in den
    Backtest-Ordner. Damit liest `kosten_wendepunkt.runden_aus_journal()`
    dieselbe Zeilenform wie im Betrieb, und es entsteht keine zweite
    Journalform.

    `spiegeln` wird stillgelegt (Bedingung 4 hat im Backtest nichts zu suchen),
    `funding_quelle` und `zeit_quelle` werden gesetzt - genau die Nahten, die
    die Spur fuer ihre Tests schon benutzt.
    """
    import contextlib
    import io

    import moondev_historie

    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf)
    with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)

    instrumente = _instrumente(w)
    reihen = {}
    for inst in instrumente:
        r = moondev_historie.lade_funding(inst)
        if r:
            reihen[inst] = r
    if not reihen:
        raise RuntimeError("keine Funding-Reihen fuer %s - erst "
                           "'python moondev_historie.py --funding %s'"
                           % (spur, ",".join(instrumente)))

    # Der Lauf geht so weit, wie die KUERZESTE Reihe traegt. Ein Instrument mit
    # kurzer Historie (HYPE ab 2025-05-30) wuerde den ganzen Lauf verkuerzen -
    # deshalb wird es benannt und ausgelassen, nicht still mitgerechnet.
    lang = {i: r for i, r in reihen.items() if len(r) >= 1000}
    zu_kurz = sorted(set(reihen) - set(lang))
    if not lang:
        raise RuntimeError("keine Funding-Reihe mit ausreichender Laenge")

    von = von_ms or min(r[0][0] for r in lang.values())
    bis = bis_ms or max(r[-1][0] for r in lang.values())
    schritte = []
    for inst, r in lang.items():
        for t, _ in r:
            if von <= t <= bis:
                schritte.append(t)
    schritte = sorted(set(schritte))

    box = {"ts": schritte[0]}
    zustand = os.path.join(ordner, "zustand.json")
    journal = os.path.join(ordner, "handelsjournal.csv")
    modul.WACHEN = os.path.join(ordner, "wachen.json")
    modul.ZUSTAND = zustand
    modul.JOURNAL = journal
    alt = {"SCHREIBEN": getattr(modul, "SCHREIBEN", None),
           "spiegeln": getattr(modul, "spiegeln", None),
           "funding_quelle": getattr(modul, "funding_quelle", None),
           "zeit_quelle": getattr(modul, "zeit_quelle", None)}
    puffer = io.StringIO()
    kill_gesehen = False
    try:
        modul.SCHREIBEN = True              # ins BACKTEST-Journal
        modul.spiegeln = lambda *a, **k: None
        modul.funding_quelle = lambda inst: moondev_historie.funding_dict(
            inst, box["ts"])
        with contextlib.redirect_stdout(puffer if still else sys.stdout):
            for ts in schritte:
                box["ts"] = ts
                modul.zeit_quelle = lambda _t=ts: dt.datetime.fromtimestamp(
                    _t / 1000.0, dt.timezone.utc).isoformat(timespec="seconds")
                modul.lauf("papier")
                if "Kill-Schwelle" in puffer.getvalue():
                    kill_gesehen = True
    finally:
        for name, wert in alt.items():
            if wert is not None:
                setattr(modul, name, wert)
    k = kennzahlen(journal)
    k.update({"schritte": len(schritte), "takt": "8h",
              "instrumente": sorted(lang), "symbole_zu_kurz": zu_kurz,
              "kill_ausgeloest": kill_gesehen, "kerzenquelle": "binance"})
    return k, len(puffer.getvalue().splitlines())
```

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `python -m unittest tests.test_replay_feed -v`
  Erwartet: OK

- [ ] **Schritt 5: Test `test_replay.py` auf `SPUREN_TEIL_A + SPUREN_TEIL_C` erweitern**

In `tests/test_replay.py`, `test_kein_pauschalwert_und_keine_stille_null`:

```python
        for spur in replay.SPUREN_TEIL_A + replay.SPUREN_TEIL_C:
            self.assertGreater(replay.gebuehr_fuer(spur, {}), 0.0)
```

- [ ] **Schritt 6: Beide Suiten laufen lassen**
  Run: `python -m unittest tests.test_replay tests.test_replay_feed -v`
  Erwartet: OK (test_replay braucht ~6 min — Laufzeit ist normal)

- [ ] **Schritt 7: Committen**

```
git add Agenten/Handel/replay.py Agenten/Handel/tests/test_replay_feed.py Agenten/Handel/tests/test_replay.py
git commit -m "replay: lauf_c fuer Spuren mit eigenem Lauf (moondev_funding)"
```

---

## Aufgabe 7: Daten holen, echte Laeufe fahren, Auswertung anschliessen

**Dateien:**
- Aendern: `Agenten/Handel/replay.py` (Verweigerungsliste, `main`)
- Aendern: `Agenten/Handel/auswertung_alle.py`
- Test: `Agenten/Handel/tests/test_replay_feed.py`

**Interfaces:**
- Konsumiert: alles aus Aufgaben 1–6
- Produziert: `NICHT_NACHRECHENBAR`-Eintraege fuer `moondev_sniper` und `moondev_listingarb`; `replay.main()` kann `--feed` und `--familie-c`

- [ ] **Schritt 1: Verweigerungsliste ergaenzen** (in `replay.py`)

```python
    # Feed-Spuren ohne historisch beschaffbare Quelle. Der GRUND gehoert
    # daneben - eine leere Zeile waere nicht zu deuten.
    "moondev_sniper": "pump.fun-Neulaunches mit Alter in Minuten - nur live",
    "moondev_listingarb": "Marktkapitalisierung frei nicht historisch abrufbar",
```

- [ ] **Schritt 2: Test dafuer schreiben und laufen lassen**

```python
    def test_verweigerte_spuren_nennen_einen_grund(self):
        for spur in ("moondev_sniper", "moondev_listingarb"):
            self.assertIn(spur, replay.NICHT_NACHRECHENBAR)
            self.assertGreater(len(replay.NICHT_NACHRECHENBAR[spur]), 20)
```

Run: `python -m unittest tests.test_replay_feed -v` — Erwartet: OK

- [ ] **Schritt 3: `main()` um die zwei Wege erweitern**

```python
    ap.add_argument("--feed", action="store_true",
                    help="Feed-Spur ueber den Marktquerschnitt (Familie B)")
    ap.add_argument("--familie-c", action="store_true",
                    help="Spur mit eigenem lauf() (moondev_funding)")
    ap.add_argument("--takt", default="1D", choices=("1D", "1H"))
    ap.add_argument("--mindest-symbole", type=int, default=30)
```

und vor dem `lauf_a`-Zweig:

```python
    if a.familie_c:
        k, zeilen = lauf_c(a.spur, replay_gebuehr(a.spur), a.lauf)
        print(json.dumps({"spur": a.spur, "kennzahlen": k, "zeilen": zeilen},
                         indent=2, ensure_ascii=False))
        return
    if a.feed:
        k, zeilen = lauf_feed(a.spur, replay_gebuehr(a.spur), a.lauf,
                              takt=a.takt, mindest_symbole=a.mindest_symbole)
        print(json.dumps({"spur": a.spur, "kennzahlen": k, "zeilen": zeilen},
                         indent=2, ensure_ascii=False))
        return
```

mit

```python
def replay_gebuehr(spur):
    """Gebuehr der Spur aus ihrer WACHEN.json, sonst Boersensatz."""
    try:
        return gebuehr_fuer(spur)
    except KeyError:
        return gebuehr_fuer(spur, {})
```

- [ ] **Schritt 4: Daten holen (echte Abrufe, kein Test)**

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel
python moondev_historie.py --universum 300 --takt 1D     # ~13 min, ~70 MB
python moondev_historie.py --stunden 40                  # ~34 min, ~265 MB
python moondev_historie.py --funding BTC,ETH,SOL,HYPE,FIL,ZEC   # ~15 min
python moondev_historie.py --stand
```

`--stunden 40` laedt die Top 40 **plus die Instrumente der Funding-Spur**
(HYPE/FIL/ZEC sind nicht unter den Top 40): der Mark-Preis im Funding-Lauf
kommt aus derselben Stundenreihe, ein fehlendes Symbol waere dort ein
fehlender Kurs und damit ein Grund statt einer Buchung.

Erwartet im Stand: 300 Reihen 1D von 2021-01-01 an, mindestens 43 Reihen 1H,
sechs Funding-Reihen; HYPE nennt 2025-05-30 als Anfang.

- [ ] **Schritt 5: Die vier Laeufe fahren**

```bash
python replay.py --feed --spur moondev_topmovers  --lauf ganz --takt 1D
python replay.py --feed --spur moondev_marktlage  --lauf ganz --takt 1D
python replay.py --feed --spur moondev_signalwelle --lauf ganz --takt 1H
python replay.py --familie-c --spur moondev_funding --lauf ganz
```

Erwartet: vier Journals unter `daten/backtest/<spur>/ganz/` mit
`runden`, `trefferquote`, `netto_pct_mittel`, `schritte`, `universum`.
Ein Lauf ohne Runden ist ein Befund und wird als solcher berichtet, nicht
geglaettet.

- [ ] **Schritt 6: Auswertung pruefen**

```bash
python auswertung_alle.py --spur moondev_topmovers
python auswertung_alle.py --spur moondev_funding
```

Erwartet: die Sektion „Backtest (historisch)" nennt Runden, Trefferquote,
Prozente und den Zeitraum; die Live-Zeile bleibt davon getrennt.

- [ ] **Schritt 7: Committen**

```
git add Agenten/Handel/replay.py Agenten/Handel/auswertung_alle.py Agenten/Handel/tests/test_replay_feed.py
git commit -m "Feed-Spuren: echte Laeufe ueber 2021-2026, Verweigerungen benannt"
```

---

## Aufgabe 8: Gegenprobe, Wiki, Aufgaben

**Dateien:**
- Aendern: `MaxHirn/Wiki/Handel/Backtest-Fundament.md`
- Aendern: `MaxHirn/Archiv/TASKS.md` (CRLF, byte-genau)
- Test: `Agenten/Handel/tests/test_replay_feed.py`

**Interfaces:**
- Konsumiert: `moondev_historie.Bestand`, `Bestand.tafel`
- Produziert: `tests/test_replay_feed.py::GegenprobeTest`, Wiki-Abschnitt, T-096 zu

- [ ] **Schritt 1: Gegenprobe gegen einen echten CoinGecko-Abzug schreiben**

```python
class GegenprobeTest(unittest.TestCase):
    """Die Tafel gegen einen echten CoinGecko-Abzug desselben Tages.

    Ein Adapter, den niemand gegen die Wirklichkeit gehalten hat, ist eine
    Behauptung. Verglichen wird die GROESSENORDNUNG, nicht die Stelle hinter
    dem Komma: zwei Boersen sind zwei Preise, und CoinGecko mittelt ueber
    viele. Ein Vergleich, der Gleichheit verlangt, waere selbst falsch.
    """

    PROBE = os.path.join(HANDEL, "daten", "historie", "coingecko_probe.json")
    TOLERANZ = 0.25      # 25 % Abweichung je Feld sind erlaubt

    def setUp(self):
        if not os.path.isfile(self.PROBE):
            self.skipTest("kein CoinGecko-Abzug aufgezeichnet: %s" % self.PROBE)

    def test_kurs_und_volumen_in_der_groessenordnung(self):
        with open(self.PROBE, encoding="utf-8") as f:
            probe = json.load(f)
        b = mh.Bestand.laden("1D")
        ts = max(b.anzahl_je_ts)
        tafel = {z["basis"]: z for z in b.tafel(ts)}
        geprueft = 0
        for m in probe["maerkte"]:
            sym = (m.get("symbol") or "").upper()
            if sym not in tafel:
                continue
            soll, ist = float(m["current_price"]), tafel[sym]["kurs"]
            self.assertLess(abs(ist - soll) / soll, self.TOLERANZ,
                            "%s: Binance %.6f gegen CoinGecko %.6f" % (sym, ist, soll))
            geprueft += 1
        self.assertGreater(geprueft, 10, "zu wenige gemeinsame Symbole")
```

- [ ] **Schritt 2: Test laufen lassen**
  Run: `python -m unittest tests.test_replay_feed -v`
  Erwartet: OK oder SKIP (wenn kein Abzug vorliegt — siehe Schritt 3)

- [ ] **Schritt 3: Den Abzug einmal aufzeichnen**

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel
python - <<'PY'
import json, urllib.request, time, os
url = ("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
       "&order=market_cap_desc&per_page=250&page=1"
       "&price_change_percentage=1h,24h")
d = json.load(urllib.request.urlopen(url, timeout=40))
ziel = os.path.join("daten", "historie", "coingecko_probe.json")
with open(ziel, "w", encoding="utf-8") as f:
    json.dump({"stand_ms": int(time.time()*1000), "quelle": url,
               "maerkte": d}, f, indent=1)
print(len(d), "Maerkte ->", ziel)
PY
python -m unittest tests.test_replay_feed.GegenprobeTest -v
```

- [ ] **Schritt 4: Wiki-Abschnitt schreiben**

In `MaxHirn/Wiki/Handel/Backtest-Fundament.md` anhaengen: Tabelle der vier
Feed-Spuren (Runden, Trefferquote, Netto je Runde, Zeitraum), die vier
Grenzen (Ueberlebende, Rang nach Volumen, ein Tag = ein Schritt,
Signalwelle 40 statt 250) und die Lektion, dass ein Adapter mit falschen
Feldern die Spur still nicht handeln laesst.

- [ ] **Schritt 5: `TASKS.md` — T-096 schliessen, neue anlegen**

Byte-genau mit CRLF schreiben (sonst diffed die ganze Datei). T-096 auf
`- [x]` setzen; neue Aufgaben (fortlaufende IDs, vorher die hoechste Zahl
pruefen — eine parallele Sitzung vergibt ebenfalls IDs):

- Signalwelle: 1H fuer weitere Symbole nachladen (40 → 100, ~80 min)
- HYPE im Funding-Backtest eigens rechnen, sobald genug Zeitraum da ist
- `moondev_listingarb`: Paarliste waere baubar, Marktkapital nicht

- [ ] **Schritt 6: Committen**

```
git add Agenten/Handel/tests/test_replay_feed.py MaxHirn/Wiki/Handel/Backtest-Fundament.md MaxHirn/Archiv/TASKS.md
git commit -m "Gegenprobe, Wiki und Aufgaben zu den historischen Feed-Spuren"
```

---

## Self-Review (durchgefuehrt 2026-09-26)

1. **Spezifikations-Abdeckung:** 3.1 → Aufgabe 1; 3.2 → Aufgabe 3; 3.3 →
   Aufgaben 1 und 3; 3.4 → Aufgabe 1 (eigener Ordner, eigener Test); 4 →
   Aufgabe 2; 5 (Anschlusstabelle) → Aufgaben 4, 5, 6; 6 (Grenzen) → Aufgaben
   3 (HYPE), 4 (Universum 40), 7 (Zeitraum); 7 (Verweigerungen) → Aufgabe 7;
   8 (Nachweis) → Aufgaben 4, 5, 6, 8; 9 (Aufwand) → alle.
2. **Platzhalter-Scan:** keine „TBD"/„TODO"; jeder Code-Schritt traegt Code.
3. **Typ-Konsistenz geprueft:** `Bestand.tafel` liefert `basis`/`kurs`/
   `aenderung_24h`/`volumen_24h`/`rang` — die Adapter in Aufgabe 4 lesen genau
   diese Namen; `FELDER` (Aufgabe 4) nennt die Namen, die die Spuren im
   Quelltext lesen (gemessen am 26.09.2026 aus `quelle()` der drei Spuren);
   `funding_dict` (Aufgabe 3) liefert `funding_rate`/`mark_price` — genau das,
   was `hole_kurse`/`pruefe_einstieg` der Funding-Spur liest; `SPUREN_TEIL_C`
   (Aufgabe 6) wird im Test (Aufgabe 6, Schritt 5) und in `gebuehr_fuer`
   mitgeprueft.
4. **Zwei Fehler beim Review gefunden und inline behoben:**
   (a) `moondev_funding` stand in `SPUREN_TEIL_A`, gehoert aber zu Familie C —
   entfernt (Aufgabe 6, Schritt 3).
   (b) `historie_binance.PAARE` kannte die bare Namen `BTC`/`ETH`/`SOL` nicht, die die
   Funding-Spur als Instrumente fuehrt — ergaenzt (Aufgabe 1, Schritt 6).
5. **Eine Falle benannt, die sonst still geblieben waere:** `kurse` muss ALLE
   geladenen Symbole tragen, nicht nur die Kandidaten — `pruefe_ausstiege`
   arbeitet ueber `kurse`, ein fehlendes Symbol liesse die Position nie
   schliessen (Test in Aufgabe 2 und Aufgabe 6).