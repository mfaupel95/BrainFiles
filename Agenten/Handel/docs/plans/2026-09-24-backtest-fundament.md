# Backtest-Fundament — Implementierungsplan

> **Für agentische Arbeiter:** ERFORDERLICHE SUB-SKILL: `superpowers:subagent-driven-development`
> (empfohlen) oder `superpowers:executing-plans`, um diesen Plan Aufgabe für
> Aufgabe umzusetzen. Die Schritte nutzen Checkbox-Syntax (`- [ ]`).

**Ziel:** Aus historischen Kursdaten mehrere hundert Handelsrunden je Spur
gewinnen, damit Trefferquote, Erwartungswert und `f_max` belastbar werden —
ohne eine einzige echte Spurendatei anzufassen.

**Architektur:** Drei Einheiten. `historie.py` holt und speichert mehrjährige
Kerzen und Funding-Sätze von Binance (offen, ohne Schlüssel) in demselben
Format, das `backtest_prognose.kerzen_holen()` heute liefert. `replay.py`
bügelt einen Backtest-Ordner unter `daten/backtest/<spur>/` über die Spur und
lässt ihre **eigenen** Entscheidungsfunktionen laufen — der Replay liefert nur
Zeit und Daten, entscheiden tut die Spur. `optimieren.py` sucht Parameter auf
demselben Fundament mit Walk-Forward. Kennzahlen werden nicht neu gebaut: der
Backtest schreibt ein Journal in der Spaltenform von `spur_buch.SPALTEN` und
übergibt es an `kosten_wendepunkt.runden_aus_journal()`.

**Tech-Stack:** Python 3 (Standardbibliothek: `json`, `csv`, `urllib`,
`argparse`, `importlib`), Testrahmen `unittest`. **Kein `pytest`** — es steht
nicht in `requirements.txt`.

**Spec:** `docs/design/2026-09-24-backtest-fundament-design.md`

**Nicht in diesem Plan:** der Umbau der vier Kern-Spuren `scanner`, `xperp`
(Perp-Zweig), `swap`, `kraken` — sie haben keine Kerzen-Naht und bekommen einen
eigenen Design-Zyklus. Ebenso nicht: Beschaffung kostenpflichtiger Historien,
Änderung von `Wissen/Handelsregeln.md`.

## Globale Vorgaben

- **Arbeitsverzeichnis:** `C:\Users\faupe\Documents\BrainFiles\Agenten\Handel`
- **Zahlen gehören in JSON, nicht in den Code.** Neue Schwellen je Spur in
  `wachen.json`, Suchbereiche in `spur_opt.json`.
- **Kein Test schreibt in ein echtes Ziel.** Jeder Test arbeitet in einem
  Temp-Ordner, den er über die Modulvariable umbiegt. `journal_zweitziel` und
  `Q:\Handel_Journal\…` werden von keinem Test berührt.
- **Nie `git add -A`** — es läuft zeitweise eine zweite Sitzung auf demselben
  Baum. Nur eigene Pfade stagen. Nach jeder Textänderung `git diff --numstat`
  je Datei prüfen (eine gewollte Zeile = 1 insertion/1 deletion).
- **Kerzenform auf Platte:** `[int ts_ms, float o, float h, float l, float c, float v]`,
  aufsteigend. Genau diese Form liefert `scanner/okx.kerzen()` (Zeile 215:
  `[[int(r[0])] + [float(x) for x in r[1:6]] for r in roh]`).
- **.gitignore:** `historie.py`, `replay.py`, `optimieren.py`, `spur_opt.json`
  und die Tests werden freigegeben; `daten/historie/` und `daten/backtest/`
  bleiben gesperrt. Gegenprobe nach jeder Anlage mit `git check-ignore -v` UND
  `git ls-files`.
- **Spurenfamilien (gemessen, nicht geraten):**
  - **Familie A** — eigenes Buch im Modul (`lade_wachen()`, `lade_zustand()`,
    `schreibe_zustand()`, `journal()`, `pruefe_einstieg()`, `pruefe_ausstiege()`),
    Datennahrung über eine `*_quelle`-Naht: `squeeze`, `wavetrend`, `macd_mtf`,
    `supertrend`, `gitter`, `orb`, `orbk`, `mosaic`, `moondev_funding`.
  - **Familie B** — Buch über `spur_buch.zyklus(ordner, quelle, signal, …)`,
    `quelle` und `signal` werden **als Argumente** übergeben: `trendwende_btc`,
    `liq_wand`, `iv_waelle`, `robinhood_radar` und sieben `moondev_*`.

## Dateistruktur

| Datei | Verantwortung |
|---|---|
| `Agenten/Handel/historie.py` (neu) | Binance-Abruf, Kursnamen-Mapping, Speicher `daten/historie/`, `--stand`, `--auffuellen` |
| `Agenten/Handel/replay.py` (neu) | Backtest-Ordner, Schreibschutz, Walk über die Historie, beide Spurenfamilien, Gebühren |
| `Agenten/Handel/optimieren.py` (neu) | Walk-Forward-Parametersuche, Urteil, Vorschlagsdatei |
| `Agenten/Handel/spur_opt.json` (neu) | Suchbereiche je Spur (Zahlen, nicht Code) |
| `Agenten/Handel/tests/test_historie.py` (neu) | Mapping, Speicherform, Append-Verhalten, Abruf-Attrappe |
| `Agenten/Handel/tests/test_replay.py` (neu) | Modulwächter, Backtest-Ordner, Familien, Gebühren, Gegenprobe |
| `Agenten/Handel/tests/test_optimieren.py` (neu) | Fensterbildung, Urteil, kein Schreiben in `wachen.json` |
| `Agenten/Handel/auswertung_alle.py` (ändern) | eine Zeile je Spur: Backtest-Runden / Live-Runden |
| `.gitignore` (ändern) | Freigabe der neuen Dateien |

### Interfaces (gelten für alle Aufgaben)

```python
# historie.py
HIER   = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(HIER, "daten", "historie")

PAARE = {                       # OKX/Kraken-Name -> Binance-Symbol
    "BTC-USDC": "BTCUSDT", "BTC-USDT": "BTCUSDT", "BTC-USDT-SWAP": "BTCUSDT",
    "ETH-USDC": "ETHUSDT", "ETH-USDT": "ETHUSDT", "SOL-USDC": "SOLUSDT",
    "XBT/USD":  "BTCUSDT",
    # ... vollstaendig in Aufgabe 1, Schritt 3
}
TAKTE = {"1H": "1h", "4H": "4h", "1D": "1d"}

def symbol(inst: str) -> str: ...                  # wirft KeyError mit bekannter Liste
def reihen_normalisieren(roh: list) -> list: ...    # Binance-JSON -> [int, float x5]
def datei(inst: str, takt: str) -> str: ...         # daten/historie/<SYM>_<takt>.json
def lade(inst: str, takt: str) -> list: ...         # aufsteigend, [] wenn keine Datei
def speichere(inst: str, takt: str, reihen: list) -> int: ...    # appendend
def von_binance(inst: str, takt: str, von_ms: int, bis_ms: int,
                pause: float = 0.25) -> list: ...
def funding(inst: str, von_ms: int, bis_ms: int) -> list: ...    # [(ts_ms, rate)]
def auffuellen(insts, takte, von_ms=None, bis_ms=None) -> dict: ...
def stand() -> dict: ...                            # Inhalt von _stand.json

# Naht für Tests: None -> echtes Netz
abruf_json = None        # def abruf_json(url: str) -> object
```

```python
# replay.py
SPUREN_TEIL_A = ("squeeze", "wavetrend", "macd_mtf", "supertrend", "gitter",
                 "orb", "orbk", "mosaic", "moondev_funding")
SPUREN_TEIL_B = ("trendwende_btc", "liq_wand", "iv_waelle", "robinhood_radar",
                 "moondev_listingarb", "moondev_topmovers", "moondev_marktlage",
                 "moondev_sniper", "moondev_signalwelle", "moondev_whale",
                 "moondev_liquidation", "moondev_sentiment")

NICHT_NACHRECHENBAR = {}   # Spur -> Grund, vollstaendig in Aufgabe 3, Schritt 3

def spur_modul(spur: str): ...                      # importlib über den Pfad
def buch_ordner(spur: str, lauf: str) -> str: ...   # daten/backtest/<spur>/<lauf>/ (Kopie der wachen.json)
def schuetze(modul, ordner) -> None: ...            # SCHREIBEN=False, journal/spiegeln abfangen
def kerzen_fuer(spur: str, w: dict, bis_ms: int) -> dict: ...   # {inst: [...]}
def lauf_a(spur: str, gebuehr_pct: float, lauf: str, bis_ms: int = None,
           wachen_patch: dict = None) -> tuple: ...   # (runden, offen)
def _feld(w: dict, *namen, vorgabe=None): ...       # erster gesetzter Name gewinnt
def _instrumente(w: dict) -> list: ...
def _takt(w: dict) -> str: ...
def lauf_b(spur: str, gebuehr_pct: float, lauf: str) -> tuple: ...
def gebuehr_fuer(spur: str, w: dict) -> float: ...  # Prozent je Seite
def kennzahlen(journal_pfad: str) -> dict: ...      # über kosten_wendepunkt

# Naht für Tests
verzeichnis = None       # def verzeichnis() -> str   (Wurzel fuer daten/backtest)
```

---

### Aufgabe 1: Kursnamen-Mapping und Speicherform

**Dateien:**
- Neu: `Agenten/Handel/historie.py`
- Test: `Agenten/Handel/tests/test_historie.py`

**Interfaces:**
- Produziert: `PAARE`, `TAKTE`, `symbol()`, `reihen_normalisieren()`, `datei()`,
  `lade()`, `speichere()` — genau die Signaturen aus dem Abschnitt „Interfaces".

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
"""Naht-Tests fuer historie.py - kein Netz, kein echter Zielpfad."""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))

import historie                                                   # noqa: E402


class MappingTest(unittest.TestCase):
    def test_okx_und_kraken_namen_landen_auf_demselben_symbol(self):
        for name in ("BTC-USDC", "BTC-USDT", "BTC-USDT-SWAP", "XBT/USD"):
            self.assertEqual("BTCUSDT", historie.symbol(name))

    def test_unbekanntes_paar_wirft_mit_liste(self):
        with self.assertRaises(KeyError) as ctx:
            historie.symbol("WUNDERKERZE-USDT")
        # Die Meldung nennt die bekannten Namen, damit niemand raten muss.
        self.assertIn("BTC-USDC", str(ctx.exception))

    def test_symbol_ist_gross_klein_unabhaengig(self):
        self.assertEqual("BTCUSDT", historie.symbol("btc-usdc"))


class SpeicherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = historie.ORDNER
        historie.ORDNER = self.tmp.name

    def tearDown(self):
        historie.ORDNER = self.alt
        self.tmp.cleanup()

    @staticmethod
    def reihe(ts, kurs):
        return [ts, kurs, kurs + 1.0, kurs - 1.0, kurs + 0.5, 12.0]

    def test_normalisieren_macht_int_und_float(self):
        roh = [["1502942400000", "4261.48", "4313.62", "4261.32", "4308.83",
                "47.18100900"]]
        r = historie.reihen_normalisieren(roh)
        self.assertEqual([int, float, float, float, float, float],
                         [type(x) for x in r[0]])
        self.assertEqual(1502942400000, r[0][0])

    def test_speichere_haengt_an_und_entdoppelt(self):
        a = [self.reihe(1000, 10.0), self.reihe(2000, 11.0)]
        b = [self.reihe(2000, 11.0), self.reihe(3000, 12.0)]   # 2000 doppelt
        self.assertEqual(2, historie.speichere("BTC-USDC", "1H", a))
        self.assertEqual(3, historie.speichere("BTC-USDC", "1H", b))
        reihen = historie.lade("BTC-USDC", "1H")
        self.assertEqual([1000, 2000, 3000], [r[0] for r in reihen])

    def test_lade_sortiert_aufsteigend_auch_bei_wirrem_bestand(self):
        historie.speichere("ETH-USDC", "1H",
                           [self.reihe(3000, 12.0), self.reihe(1000, 10.0)])
        self.assertEqual([1000, 3000],
                         [r[0] for r in historie.lade("ETH-USDC", "1H")])

    def test_lade_ohne_datei_ist_leer_und_wirft_nicht(self):
        self.assertEqual([], historie.lade("SOL-USDC", "1H"))

    def test_unbekannter_takt_wird_abgelehnt(self):
        with self.assertRaises(KeyError):
            historie.datei("BTC-USDC", "7M")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd Agenten/Handel && python tests/test_historie.py`
  Erwartet: FAIL mit `ModuleNotFoundError: No module named 'historie'`

- [ ] **Schritt 3: Minimale Implementierung** — Teil 1 von `historie.py`

```python
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
"""

import json
import os
import time
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(HIER, "daten", "historie")

TAKTE = {"1H": "1h", "4H": "4h", "1D": "1d"}

# OKX- und Kraken-Namen der Spuren -> Binance-Symbol. EIN Ort, damit nicht
# jede Spur ihr eigenes Mapping erfindet. Gemessen 2026-09-24: 19 von 20
# geprueften Instrumenten haben ein Binance-USDT-Paar; MATIC fehlt (heute POL).
PAARE = {
    "BTC-USDC": "BTCUSDT", "BTC-USDT": "BTCUSDT", "BTC-USDT-SWAP": "BTCUSDT",
    "XBT/USD": "BTCUSDT", "BTC/USD": "BTCUSDT", "BTC_USDT": "BTCUSDT",
    "ETH-USDC": "ETHUSDT", "ETH-USDT": "ETHUSDT", "ETH_USDT": "ETHUSDT",
    "SOL-USDC": "SOLUSDT", "SOL-USDT": "SOLUSDT",
    "HYPE": "HYPEUSDT", "FIL": "FILUSDT", "ZEC": "ZECUSDT", "UNI": "UNIUSDT",
    "ARB": "ARBUSDT", "DOGE": "DOGEUSDT", "XRP": "XRPUSDT", "APT": "APTUSDT",
    "STRK": "STRKUSDT", "DOT": "DOTUSDT", "HBAR": "HBARUSDT",
    "NEAR": "NEARUSDT", "AVAX": "AVAXUSDT", "BNB": "BNBUSDT",
    "LINK": "LINKUSDT", "ADA": "ADAUSDT",
}

_BASIS = "https://api.binance.com"


def symbol(inst):
    """Binance-Symbol zu einem Spur-Instrument.

    Ein unbekanntes Paar ist ein HARTEr Fehler, kein stiller Ersatz: wer hier
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
    """Gespeicherte Kerzen, aufsteigend. Fehlende Datei ist kein Fehler."""
    try:
        with open(datei(inst, takt), encoding="utf-8") as f:
            reihen = json.load(f)
    except (OSError, ValueError):
        return []
    return sorted(reihen, key=lambda r: r[0])


def speichere(inst, takt, reihen):
    """Anhaengen, entdoppelt ueber den Zeitstempel. Gibt den Gesamtbestand.

    Appendend, weil ein zweiter Lauf nur die neuen Kerzen mitbringt: die
    HISTORIE darf nie durch eine kuerzere Antwort ersetzt werden (fuer den
    Betrieb waere 'nur die letzten N' richtig, fuer den Backtest falsch).
    """
    os.makedirs(ORDNER, exist_ok=True)
    bestand = {r[0]: r for r in lade(inst, takt)}
    roh = (reihen_normalisieren(reihen) if reihen and isinstance(reihen[0][0], str)
           else reihen)
    for r in roh:
        bestand[r[0]] = r
    pfad = datei(inst, takt)
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump([bestand[t] for t in sorted(bestand)], f)
    return len(bestand)
```

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cd Agenten/Handel && python tests/test_historie.py`
  Erwartet: `OK` (7 Tests)

- [ ] **Schritt 5: Committen**
  `git add Agenten/Handel/historie.py Agenten/Handel/tests/test_historie.py`
  `git commit -m "historie: Kursnamen-Mapping und Kerzenspeicher fuer den Backtest"`

---

### Aufgabe 2: Binance-Abruf, Funding und Stand

**Dateien:**
- Ändern: `Agenten/Handel/historie.py`
- Test: `Agenten/Handel/tests/test_historie.py`

**Interfaces:**
- Konsumiert: `symbol()`, `datei()`, `lade()`, `speichere()` aus Aufgabe 1.
- Produziert: `von_binance()`, `funding()`, `auffuellen()`, `stand()`, `abruf_json`
  (Naht für Tests) — die späteren Aufgaben rufen nur `lade()` und `funding()`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben** — an `test_historie.py` anhängen

```python
class AbrufTest(unittest.TestCase):
    """Der Abruf wird ueber die Naht `abruf_json` gefaelscht - kein Netz."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_o, self.alt_a = historie.ORDNER, historie.abruf_json
        historie.ORDNER = self.tmp.name
        self.aufrufe = []

        def fake(url):
            self.aufrufe.append(url)
            seite = "/klines" in url or "/fundingRate" in url
            if "/klines" in url and "startTime=1000" in url:
                return [["1000", "10", "11", "9", "10.5", "5"],
                        ["2000", "10.5", "12", "10", "11.5", "6"]]
            if "/klines" in url:                       # zweite Seite
                return [["3000", "11.5", "13", "11", "12.5", "7"]]
            return [{"fundingTime": 1000, "fundingRate": "0.0003"},
                    {"fundingTime": 2000, "fundingRate": "-0.0001"}]
        historie.abruf_json = fake

    def tearDown(self):
        historie.ORDNER, historie.abruf_json = self.alt_o, self.alt_a
        self.tmp.cleanup()

    def test_von_binance_blaettert_und_normalisiert(self):
        r = historie.von_binance("BTC-USDC", "1H", 1000, 4000)
        self.assertEqual([1000, 2000, 3000], [x[0] for x in r])
        self.assertEqual(float, type(r[0][4]))
        self.assertEqual(3, len(self.aufrufe))   # zwei Nutzseiten + Abbruchruf

    def test_von_binance_haelt_von_und_bis_ein(self):
        r = historie.von_binance("BTC-USDC", "1H", 1000, 2500)
        self.assertEqual([1000, 2000], [x[0] for x in r])

    def test_funding_liefert_paare_aus_zeit_und_satz(self):
        f = historie.funding("BTC-USDC", 0, 5000)
        self.assertEqual([(1000, 0.0003), (2000, -0.0001)], f)

    def test_auffuellen_schreibt_und_stand_zaehlt(self):
        bericht = historie.auffuellen(["BTC-USDC"], ["1H"], von_ms=1000, bis_ms=4000)
        self.assertEqual(3, bericht["BTC-USDC"]["1H"]["kerzen"])
        self.assertEqual(3, historie.stand()["reihen"]["BTCUSDT_1H"]["kerzen"])
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd Agenten/Handel && python tests/test_historie.py`
  Erwartet: FAIL — `AttributeError: module 'historie' has no attribute 'abruf_json'`

- [ ] **Schritt 3: Minimale Implementierung** — Teil 2 an `historie.py` anhängen

```python
# Naht fuer Tests: None -> echtes Netz.
abruf_json = None

_GRENZE = 1000                     # Binance liefert hoechstens 1000 je Abruf


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
    raise RuntimeError("Abruf scheiterte nach %d Versuchen: %s" % (versuche, letzter))


def von_binance(inst, takt, von_ms, bis_ms, pause=0.25):
    """Kerzen von Binance, aufsteigend, auf [von_ms, bis_ms] beschnitten.

    Paginiert mit `startTime` (der letzten gelieferten Kerze + 1 ms), weil nur
    diese Richtung vorwaerts blaettert. OKX blaettert mit `after` rueckwaerts -
    die Richtung haengt an der Boerse, nicht am Werkzeug.
    """
    sym, bar = symbol(inst), TAKTE[takt]
    reihen, cur = [], int(von_ms)
    while cur < int(bis_ms):
        url = ("%s/api/v3/klines?symbol=%s&interval=%s&limit=%d&startTime=%d"
               % (_BASIS, sym, bar, _GRENZE, cur))
        seite = _hole(url)
        if not seite:
            break
        neu = reihen_normalisieren(seite)
        if reihen and neu[-1][0] <= reihen[-1][0]:
            break              # keine neuen Kerzen - Abbruch statt Endlosschleife
        reihen += neu
        cur = reihen[-1][0] + 1
        if cur > int(bis_ms):
            break
        time.sleep(pause)
    return [r for r in reihen if int(von_ms) <= r[0] <= int(bis_ms)]


def funding(inst, von_ms, bis_ms):
    """[(ts_ms, rate)] von Binance-Futures. Frei ab 2020-08-01."""
    sym = symbol(inst)
    aus, cur = [], int(von_ms)
    while cur < int(bis_ms):
        url = ("https://fapi.binance.com/fapi/v1/fundingRate?symbol=%s&limit=%d"
               "&startTime=%d" % (sym, _GRENZE, cur))
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
    """Kerzen (und fuer Krypto-Futures Funding) nachladen und speichern."""
    von_ms = von_ms or int(time.mktime(time.strptime("2021-01-01", "%Y-%m-%d"))) * 1000
    bis_ms = bis_ms or int(time.time() * 1000)
    bericht = {}
    for inst in insts:
        for takt in takte:
            neu = von_binance(inst, takt, von_ms, bis_ms)
            gesamt = speichere(inst, takt, neu)
            bericht[inst] = bericht.get(inst, {})
            bericht[inst][takt] = {"neu": len(neu), "kerzen": gesamt}
    _schreibe_stand()
    return bericht


def _schreibe_stand():
    reihen = {}
    for name in sorted(os.listdir(ORDNER)) if os.path.isdir(ORDNER) else []:
        if not name.endswith(".json") or name == "_stand.json":
            continue
        pfad = os.path.join(ORDNER, name)
        try:
            with open(pfad, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        reihen[name[:-5]] = {"kerzen": len(d),
                             "von": d[0][0] if d else None,
                             "bis": d[-1][0] if d else None,
                             "herkunft": "binance", "stand_ms": int(time.time() * 1000)}
    stan = {"reihen": reihen, "tapte": dict(TAKTE)}
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

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cd Agenten/Handel && python tests/test_historie.py`
  Erwartet: `OK` (11 Tests)

- [ ] **Schritt 5: Echten Lauf und Beleg** — die Behauptung der Spec prüfen

```bash
cd Agenten/Handel
python historie.py --auffuellen --instrumente BTC-USDC,ETH-USDC,SOL-USDC --takte 1H,4H
python historie.py --stand
```
  Erwartet: je Reihe ein Zeitraum ab 2021-01-01, Kerzenzahl über 40.000 für 1H auf
  fünf Jahren. Die Abrufzeit wird mitgeschrieben (`_stand.json.stand_ms`).

- [ ] **Schritt 6: CLI anschließen und committen**

```python
def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--auffuellen", action="store_true")
    ap.add_argument("--stand", action="store_true")
    ap.add_argument("--instrumente", default="BTC-USDC,ETH-USDC,SOL-USDC")
    ap.add_argument("--takte", default="1H,4H")
    ap.add_argument("--von", default="2021-01-01")
    a = ap.parse_args()
    if a.stand:
        print(json.dumps(stand(), indent=2, ensure_ascii=False))
        return
    von = int(time.mktime(time.strptime(a.von, "%Y-%m-%d"))) * 1000
    b = auffuellen([x for x in a.instrumente.split(",") if x],
                   [x for x in a.takte.split(",") if x], von_ms=von)
    print(json.dumps(b, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

`git add Agenten/Handel/historie.py Agenten/Handel/tests/test_historie.py`
`git commit -m "historie: Binance-Abruf mit Pagination, Funding und Stand-Datei"`

---

### Aufgabe 3: Replay-Kern mit Schreibschutz (Familie A)

**Dateien:**
- Neu: `Agenten/Handel/replay.py`
- Test: `Agenten/Handel/tests/test_replay.py`

**Interfaces:**
- Konsumiert: `historie.lade()`, `historie.funding()` (Aufgabe 2).
- Produziert: `spur_modul()`, `buch_ordner()`, `schuetze()`, `lauf_a()`,
  `verzeichnis` (Naht für Tests). `lauf_a()` gibt `(runden, offen)` in genau der
  Form zurück, die `backtest_prognose.lauf()` liefert — damit die Gegenprobe in
  Aufgabe 4 ein echter Vergleich ist und keine Umrechnung.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben** — `tests/test_replay.py`

```python
"""Schreibschutz und Backtest-Ordner des Replay-Kerns.

Der wichtigste Test dieser Datei ist `NichtsAusserhalbTest`: er vergleicht
Dateiliste und Groessen des ECHTEN Spurenordners und der Q:-Spiegelung vor und
nach einem Replay-Lauf. Ein Test, der in ein echtes Ziel schreibt, hat hier
nichts zu suchen (Lehre vom 14.09.2026, TEST-Q:-FALLE).
"""

import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import replay                                                     # noqa: E402


def _inventar(ordner):
    """{pfad: groesse} eines Ordners, ohne __pycache__."""
    aus = {}
    for wurzel, _, dateien in os.walk(ordner):
        if "__pycache__" in wurzel:
            continue
        for d in dateien:
            p = os.path.join(wurzel, d)
            try:
                aus[p] = os.path.getsize(p)
            except OSError:
                aus[p] = -1
    return aus


class NichtsAusserhalbTest(unittest.TestCase):
    def test_replay_ruehrt_den_echten_spurenordner_nicht_an(self):
        spur = os.path.join(HANDEL, "supertrend")
        vorher = _inventar(spur)
        replay.lauf_a("supertrend", gebuehr_pct=0.1, lauf="test")
        self.assertEqual(vorher, _inventar(spur))

    def test_replay_schreibt_in_den_backtest_ordner(self):
        runden, offen = replay.lauf_a("supertrend", gebuehr_pct=0.1, lauf="test")
        ordner = replay.buch_ordner("supertrend", "test")
        self.assertTrue(os.path.isfile(os.path.join(ordner, "handelsjournal.csv")))
        self.assertGreater(len(runden), 0)


class BuchOrdnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = replay.verzeichnis
        replay.verzeichnis = lambda: self.tmp.name

    def tearDown(self):
        replay.verzeichnis = self.alt
        self.tmp.cleanup()

    def test_wachen_kopie_zeigt_nach_innen(self):
        import json
        ordner = replay.buch_ordner("supertrend", "a")
        with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        # Die Kopie darf NIE nach Q: spiegeln - auch nicht aus Versehen.
        self.assertNotIn("Q:", str(w.get("journal_zweitziel")))
        self.assertTrue(ordner.startswith(self.tmp.name))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd Agenten/Handel && python tests/test_replay.py`
  Erwartet: FAIL — `ModuleNotFoundError: No module named 'replay'`

- [ ] **Schritt 3: Minimale Implementierung** — Teil 1 von `replay.py`

```python
"""Backtest-Kern: die Spur entscheidet, der Replay liefert nur Zeit und Daten.

Zwei Spurenfamilien (gemessen 2026-09-24):

  Familie A fuehrt ihr Buch im eigenen Modul (lade_wachen, lade_zustand,
  schreibe_zustand, journal, pruefe_einstieg, pruefe_ausstiege) und holt ihre
  Daten ueber eine *_quelle-Naht.

  Familie B fuehrt das Buch ueber spur_buch.zyklus(ordner, quelle, signal, ...)
  und bekommt `quelle` und `signal` ALS ARGUMENTE - der Replay schiebt dort
  eine historische Quelle unter, ohne die Spur zu veraendern.

Geschrieben wird ausschliesslich unter daten/backtest/<spur>/<lauf>/. Der echte
Spurenordner und Q:\\Handel_Journal werden nie beruehrt; der Test
`NichtsAusserhalbTest` vergleicht das Inventar vor und nach dem Lauf.
"""

import datetime as dt
import importlib.util
import json
import os

HIER = os.path.dirname(os.path.abspath(__file__))
import historie                                                   # noqa: E402

# Spuren mit eigenem Buch im Modul (Familie A).
SPUREN_TEIL_A = ("squeeze", "wavetrend", "macd_mtf", "supertrend", "gitter",
                 "orb", "orbk", "mosaic", "moondev_funding")

# Spuren ueber spur_buch (Familie B).
SPUREN_TEIL_B = ("trendwende_btc", "liq_wand", "iv_waelle", "robinhood_radar",
                 "moondev_listingarb", "moondev_topmovers", "moondev_marktlage",
                 "moondev_sniper", "moondev_signalwelle", "moondev_whale",
                 "moondev_liquidation", "moondev_sentiment")

# Spuren, deren Datenquelle sich historisch nicht beschaffen laesst. Sie
# bekommen einen Vermerk statt einer geschaetzten Zahl.
NICHT_NACHRECHENBAR = {
    "moondev_whale": "OKX-OI-Historie antwortet 50030 Illegal time range",
    "moondev_liquidation": "keine frei abrufbare Liquidationshistorie",
    "moondev_sentiment": "RSS-Titel von damals nicht archiviert",
    "liq_wand": "keine frei abrufbare Liquidationshistorie",
    "iv_wand": "Strike-OI-Historie (Deribit) nicht abrufbar",
    "iv_waelle": "Strike-OI-Historie (Deribit) nicht abrufbar",
    "robinhood_radar": "fremde SQLite haelt nur den Sammelzeitraum",
}

# Naht fuer Tests: None -> HIER/daten/backtest.
verzeichnis = None


def wurzel():
    return (verzeichnis() if verzeichnis
            else os.path.join(HIER, "daten", "backtest"))


def spur_modul(spur):
    """Ein Spurenmodul ueber den PFAD laden, nicht ueber sys.path.

    sys.path waere falsch: die Spuren haben gleichnamige Module (gitter/grid.py
    und Handel/grid.py, dazu in jeder Spur ein handeln.py) - eine Reihenfolge
    entscheidet dann, welche Fassung geladen wird. Ueber den Pfad gibt es die
    Frage nicht.
    """
    pfad = os.path.join(HIER, spur, "handeln.py")
    if not os.path.isfile(pfad):
        raise FileNotFoundError("Spur %r hat kein handeln.py: %s" % (spur, pfad))
    s = importlib.util.spec_from_file_location("bt_" + spur, pfad)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def buch_ordner(spur, lauf):
    """Der Backtest-Ordner einer Spur: Kopie der Wachen, sonst nichts.

    Die Wachen-KOPIE ist der Punkt: `journal_zweitziel` wird auf den
    Backtest-Ordner gebogen, damit selbst ein vergessener Spiegelungsaufruf
    nach innen kopiert und nie nach Q:.
    """
    ziel = os.path.join(wurzel(), spur, lauf)
    os.makedirs(ziel, exist_ok=True)
    quelle = os.path.join(HIER, spur, "wachen.json")
    if os.path.isfile(quelle):
        with open(quelle, encoding="utf-8") as f:
            w = json.load(f)
        w["journal_zweitziel"] = ziel
        w["handel_erlaubt"] = False          # im Backtest gibt es kein live
        with open(os.path.join(ziel, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(w, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return ziel


def schuetze(modul, ordner):
    """Alle Schreibwege einer Spur lahmlegen.

    `SCHREIBEN=False` allein reicht NICHT: es sichert nur `journal()`. Eine Spur
    schreibt auch Zustand und spiegelt - beides muss ebenfalls ins Leere
    laufen, sonst landet ein Backtest im Betriebsstand.
    """
    if hasattr(modul, "SCHREIBEN"):
        modul.SCHREIBEN = False
    if hasattr(modul, "journal"):
        modul.journal = lambda **f: None
    if hasattr(modul, "schreibe_zustand"):
        modul.schreibe_zustand = lambda *a, **k: None
    if hasattr(modul, "spiegeln"):
        modul.spiegeln = lambda *a, **k: None
    for name in ("WACHEN", "ZUSTAND", "JOURNAL"):
        if hasattr(modul, name):
            setattr(modul, name, os.path.join(
                ordner, {"WACHEN": "wachen.json", "ZUSTAND": "zustand.json",
                         "JOURNAL": "handelsjournal.csv"}[name]))
```

- [ ] **Schritt 4: Test laufen lassen — der Bestands-Test darf noch scheitern**
  Run: `cd Agenten/Handel && python tests/test_replay.py`
  Erwartet: `BuchOrdnerTest` PASS, `NichtsAusserhalbTest` FAIL
  (`lauf_a` fehlt noch). Das ist der Zwischenstand dieser Aufgabe.

- [ ] **Schritt 5: `lauf_a()` ergänzen** — der Walk über die Historie

```python
def _feld(w, *namen, vorgabe=None):
    """Den ERSTEN gesetzten Namen nehmen.

    Die Spuren benennen dieselbe Sache verschieden (`kerzen_takt`,
    `kerzen_zeitrahmen`, `instrumente` als Liste ODER als Dict). Wer hier einen
    Namen fest verdrahtet, laesst eine Spur still ohne Kerzen laufen.
    """
    for n in namen:
        if w.get(n) not in (None, "", [], {}):
            return w[n]
    return vorgabe


def _instrumente(w):
    i = _feld(w, "instrumente", "instrument", "paare", vorgabe=[])
    if isinstance(i, dict):
        return list(i)
    if isinstance(i, str):
        return [x.strip() for x in i.split(",") if x.strip()]
    return list(i)


def _takt(w):
    return _feld(w, "kerzen_takt", "kerzen_zeitrahmen", "takt", "intervall",
                 vorgabe="1H")


def kerzen_fuer(spur, w, bis_ms=None):
    """{inst: [kerzen]} aus der eigenen Historie, aufsteigend.

    Fehlt eine Reihe, wird sie GEMELDET und das Instrument faellt aus dem Lauf
    - nie still durch ein anderes Instrument ersetzt.
    """
    insts = _instrumente(w)
    takt = _takt(w)
    aus, fehlen = {}, []
    for inst in insts:
        reihen = historie.lade(inst, takt)
        if bis_ms:
            reihen = [r for r in reihen if r[0] <= bis_ms]
        if len(reihen) < int(w.get("mindest_kerzen", 300)) + 20:
            fehlen.append("%s (%d Kerzen)" % (inst, len(reihen)))
            continue
        aus[inst] = reihen
    if fehlen:
        print("  ohne Historie: %s" % ", ".join(fehlen))
    return aus


def lauf_a(spur, gebuehr_pct, lauf, bis_ms=None, wachen_patch=None):
    """Familie A ueber die Historie. Rueckgabe wie backtest_prognose.lauf().

    `wachen_patch` ueberschreibt einzelne Wachen-Werte - so setzt der Optimierer
    seine Kandidaten, ohne eine wachen.json anzufassen (Muster:
    `backtest_prognose.fahre(wachen_patch=...)`).
    """
    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf)
    schuetze(modul, ordner)
    w = dict(modul.lade_wachen()) if hasattr(modul, "lade_wachen") else {}
    if wachen_patch:
        w.update(wachen_patch)
    kerzen = kerzen_fuer(spur, w, bis_ms)
    if not kerzen:
        raise RuntimeError("keine Historie fuer %s - erst "
                           "'python historie.py --auffuellen'" % spur)

    runden, offen, gesammelt = [], {}, []
    modul.journal = lambda **f: gesammelt.append(f)
    z = {"positionen": [], "modus": "papier", "letzter_lauf": None,
         "verluste_usd": 0.0}
    laenge = min(len(k) for k in kerzen.values())
    mindest = int(w.get("mindest_kerzen", 300))

    for i in range(mindest, laenge):
        for inst, alle in kerzen.items():
            k = alle[:i + 1]
            vorher = {id(p): p for p in z["positionen"]}
            modul.pruefe_ausstiege(z, k, w, nur=inst)
            nachher = {id(p) for p in z["positionen"]}
            for pid, p in vorher.items():
                if pid not in nachher and pid in offen:
                    e = offen.pop(pid)
                    kurs = k[-1][4]
                    vz = 1 if e["seite"] == "long" else -1
                    roh = (kurs - e["einstieg"]) / e["einstieg"] * 100.0 * vz
                    runden.append({
                        "inst": inst, "seite": e["seite"],
                        "einstieg": e["einstieg"], "ausstieg": kurs,
                        "nominal": e["nominal"], "stop_pct": e["stop_pct"],
                        "brutto_pct": roh, "netto_pct": roh - 2 * gebuehr_pct,
                        "gv_brutto": e["nominal"] * roh / 100.0,
                        "gv_netto": e["nominal"] * (roh - 2 * gebuehr_pct) / 100.0,
                        "ein_ts": e["ts"], "aus_ts": k[-1][0],
                        "stunden": (k[-1][0] - e["ts"]) / 3600000.0})
            vor_ids = {id(p) for p in z["positionen"]}
            modul.pruefe_einstieg(inst, k, z, w, 1.0)
            for p in z["positionen"]:
                if id(p) not in vor_ids:
                    offen[id(p)] = {"seite": p["seite"], "einstieg": p["einstieg"],
                                    "nominal": p["nominal"],
                                    "stop_pct": p["stop_pct"], "ts": k[-1][0]}
    _journal_schreiben(ordner, runden, gebuehr_pct)
    return runden, len(z["positionen"])
```

- [ ] **Schritt 6: `_journal_schreiben()` ergänzen** — eine Spaltenform für alle

```python
def _journal_schreiben(ordner, runden, gebuehr_pct):
    """Das Backtest-Journal in der Spaltenform von spur_buch.SPALTEN.

    Diese Form ist Absicht: `kosten_wendepunkt.runden_aus_journal()` liest sie
    direkt, also gibt es fuer Backtest und Betrieb EINE Kennzahlenrechnung.
    """
    import csv
    spalten = ["zeit", "modus", "aktion", "inst", "seite", "preis",
               "einsatz_usd", "stop", "ziel", "stop_pct", "grund"]
    pfad = os.path.join(ordner, "handelsjournal.csv")
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=spalten)
        w.writeheader()
        for r in runden:
            w.writerow({"zeit": r["aus_ts"], "modus": "papier",
                        "aktion": "verkauf", "inst": r["inst"],
                        "seite": r["seite"], "preis": "%.8f" % r["ausstieg"],
                        "einsatz_usd": "%.2f" % r["nominal"],
                        "stop_pct": "%.2f" % r["stop_pct"],
                        "grund": "backtest"})


def kennzahlen(journal_pfad):
    """Kennzahlen aus dem Backtest-Journal - EINE Rechnung fuer beide Welten.

    Gerufen wird `kosten_wendepunkt.runden_aus_journal()`: dieselbe Funktion,
    die der Betrieb fuer die echten Journale benutzt. Eine zweite Kennzahlen-
    rechnung im Backtest waere eine zweite Wahrheit.
    """
    import kosten_wendepunkt                                       # noqa: PLC0415
    from pathlib import Path                                       # noqa: PLC0415
    runden, zwang = kosten_wendepunkt.runden_aus_journal(Path(journal_pfad))
    if not runden:
        return {"runden": 0, "zwang": len(zwang)}
    k = dict(kosten_wendepunkt.wendepunkt(runden) or {})
    k["zwang"] = len(zwang)
    return k
```

- [ ] **Schritt 7: Test laufen lassen, PASS verifizieren**
  Run: `cd Agenten/Handel && python tests/test_replay.py`
  Erwartet: `OK` (4 Tests). **Voraussetzung:** die Historie für supertrend liegt
  (Aufgabe 2, Schritt 5). Fehlt sie, meldet der Test das mit genau dieser Zeile
  und ist damit kein Fehlschlag, sondern eine Anweisung.

- [ ] **Schritt 8: Committen**
  `git add Agenten/Handel/replay.py Agenten/Handel/tests/test_replay.py`
  `git commit -m "replay: Backtest-Kern mit Schreibschutz und Journal in Hausform"`

---

### Aufgabe 4: Gegenprobe gegen `backtest_prognose.py`

**Dateien:**
- Ändern: `Agenten/Handel/replay.py` (Funktion `gegenprobe`)
- Ändern: `Agenten/Handel/tests/test_replay.py`

**Interfaces:**
- Konsumiert: `lauf_a()` (Aufgabe 3), `backtest_prognose.lauf()` (bestehend).
- Produziert: `gegenprobe(spur, gebuehr_pct) -> dict` mit `gleich: bool` und
  `abweichungen: list`. Dies ist das Abnahmekriterium 2 der Spec.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
class GegenprobeTest(unittest.TestCase):
    """Der neue Kern muss dasselbe rechnen wie der alte - sonst luegt er."""

    def test_squeeze_stimmt_mit_backtest_prognose_ueberein(self):
        ergebnis = replay.gegenprobe("squeeze", gebuehr_pct=0.1)
        self.assertTrue(ergebnis["gleich"],
                        "Abweichungen: %s" % ergebnis["abweichungen"][:3])
        self.assertGreater(ergebnis["runden"], 0)
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd Agenten/Handel && python tests/test_replay.py`
  Erwartet: FAIL — `AttributeError: module 'replay' has no attribute 'gegenprobe'`

- [ ] **Schritt 3: Implementierung** — an `replay.py` anhängen

```python
def gegenprobe(spur, gebuehr_pct, lauf="gegenprobe"):
    """Dieselben Kerzen durch beide Rechenwege, Runde fuer Runde verglichen.

    Verglichen werden Anzahl, Instrument, Seite, Einstieg und Bruttoprozente -
    die Felder, die beide Wege unabhaengig voneinander bilden. Ein Unterschied
    ist ein Fehler im neuen Kern, nicht im alten: `backtest_prognose.py` faehrt
    seit 21.09.2026 im Betrieb.
    """
    import backtest_prognose                                       # noqa: PLC0415

    neu, _ = lauf_a(spur, gebuehr_pct, lauf)
    alt_modul = spur_modul(spur)
    w = dict(alt_modul.lade_wachen())
    kerzen = kerzen_fuer(spur, w)
    alt, _ = backtest_prognose.lauf(spur, kerzen, w, gebuehr_pct,
                                    modul=alt_modul)
    abw = []
    if len(neu) != len(alt):
        abw.append("Rundenzahl: neu %d, alt %d" % (len(neu), len(alt)))
    for i, (a, b) in enumerate(zip(neu, alt)):
        for feld in ("inst", "seite"):
            if a[feld] != b[feld]:
                abw.append("Runde %d %s: %r != %r" % (i, feld, a[feld], b[feld]))
        for feld in ("einstieg", "brutto_pct"):
            if abs(float(a[feld]) - float(b[feld])) > 1e-9:
                abw.append("Runde %d %s: %.10f != %.10f"
                           % (i, feld, a[feld], b[feld]))
    return {"gleich": not abw, "abweichungen": abw,
            "runden": len(neu), "runden_alt": len(alt)}
```

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cd Agenten/Handel && python tests/test_replay.py`
  Erwartet: `OK` (5 Tests). **Passiert der Test nicht**, ist die Ursache im
  neuen Kern zu suchen (Kerzenschnitt, Index, Reihenfolge), nicht im alten.

- [ ] **Schritt 5: Committen**
  `git add Agenten/Handel/replay.py Agenten/Handel/tests/test_replay.py`
  `git commit -m "replay: Gegenprobe gegen backtest_prognose (Abnahmekriterium 2)"`

---

### Aufgabe 5: Familie B — Spuren über `spur_buch`

**Dateien:**
- Ändern: `Agenten/Handel/replay.py` (`lauf_b`, `historische_quelle`)
- Ändern: `Agenten/Handel/tests/test_replay.py`

**Interfaces:**
- Konsumiert: `spur_buch.zyklus()`, `spur_buch.SCHREIBEN`, `spur_buch.zeit_quelle`.
- Produziert: `lauf_b(spur, gebuehr_pct, lauf, bis_ms=None) -> (runden, offen)`,
  `historische_quelle(modul, spur, zugriff) -> Quelle`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
class FamilieBTest(unittest.TestCase):
    """Eine nachgebaute Buch-Spur im Temp-Ordner: nichts geht nach aussen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = replay.verzeichnis
        replay.verzeichnis = lambda: self.tmp.name

    def tearDown(self):
        replay.verzeichnis = self.alt
        self.tmp.cleanup()

    def test_lauf_b_schreibt_nur_in_den_backtest_ordner(self):
        runden, offen = replay.lauf_b("trendwende_btc", gebuehr_pct=0.05,
                                      lauf="test", bis_ms=None)
        ordner = replay.buch_ordner("trendwende_btc", "test")
        self.assertTrue(os.path.isfile(os.path.join(ordner, "handelsjournal.csv")))
        # Das ECHTE Q:-Ziel steht weiter in der echten Wachen und wurde nicht
        # beschrieben - der Vergleich ueber das Inventar beweist es.
        echt = os.path.join(HANDEL, "trendwende_btc")
        self.assertNotIn(os.path.join(ordner, "handelsjournal.csv"),
                         _inventar(echt))

    def test_zeit_quelle_wird_zurueckgesetzt(self):
        import spur_buch
        vorher = spur_buch.zeit_quelle
        replay.lauf_b("trendwende_btc", gebuehr_pct=0.05, lauf="test2")
        self.assertIs(vorher, spur_buch.zeit_quelle)
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd Agenten/Handel && python tests/test_replay.py`
  Erwartet: FAIL — `AttributeError: module 'replay' has no attribute 'lauf_b'`

- [ ] **Schritt 3: Implementierung** — an `replay.py` anhängen

```python
def historische_quelle(modul, spur, zugriff):
    """Eine `quelle(w)`-Funktion, die aus der Historie speist statt zu laden.

    `zugriff` ist ein Dict mit dem Stand des Walks: {"bis_ms": ..., "index": ...}.
    Die Funktion wird bei JEDEM Schritt gerufen und schneidet die Kerzen auf den
    aktuellen Stand - die Spur sieht also nie die Zukunft, genau wie im Betrieb.

    Spuren mit reicheren Daten (Funding, Top-Mover, Volumen) bauen ihre Felder
    aus demselben Schnitt; was sich historisch nicht beschaffen laesst, steht in
    NICHT_NACHRECHENBAR und wird hier gar nicht erst angeboten.
    """
    def quelle(w):
        insts = _instrumente(w)
        takt = _takt(w)
        daten, kurse, fehler = {}, {}, []
        for inst in insts:
            reihen = [r for r in historie.lade(inst, takt)
                      if r[0] <= zugriff["bis_ms"]]
            if not reihen:
                fehler.append("%s: keine Historie" % inst)
                continue
            daten[inst] = {"kerzen": reihen, "bar": takt}
            kurse[inst] = float(reihen[-1][4])
        return daten, kurse, fehler
    return quelle


def lauf_b(spur, gebuehr_pct, lauf, bis_ms=None):
    """Familie B ueber die Historie: ein `spur_buch.zyklus` je Kerze."""
    import spur_buch                                               # noqa: PLC0415

    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf)
    with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)
    takt = _takt(w)
    alle = {i: historie.lade(i, takt) for i in _instrumente(w)
            if historie.lade(i, takt)}
    if not alle:
        raise RuntimeError("keine Historie fuer %s" % spur)

    alt_schreiben, alt_zeit = spur_buch.SCHREIBEN, spur_buch.zeit_quelle
    alt_spiegeln = spur_buch.spiegeln
    zugriff = {"bis_ms": 0}
    try:
        spur_buch.SCHREIBEN = True          # ins BACKTEST-Journal, nicht ins echte
        spur_buch.spiegeln = lambda *a, **k: None
        quelle = historische_quelle(modul, spur, zugriff)
        laenge = min(len(k) for k in alle.values())
        for i in range(int(w.get("mindest_kerzen", 300)), laenge):
            ts = max(k[i][0] for k in alle.values())
            zugriff["bis_ms"] = ts
            spur_buch.zeit_quelle = lambda _t=ts: dt.fromtimestamp(
                _t / 1000.0, dt.timezone.utc).isoformat(timespec="seconds")
            spur_buch.zyklus(ordner, quelle, modul.signal, "papier",
                             "handel/" + spur)
    finally:
        spur_buch.SCHREIBEN, spur_buch.zeit_quelle = alt_schreiben, alt_zeit
        spur_buch.spiegeln = alt_spiegeln
    return kennzahlen(os.path.join(ordner, "handelsjournal.csv")), 0
```

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cd Agenten/Handel && python tests/test_replay.py`
  Erwartet: `OK` (7 Tests)

- [ ] **Schritt 5: Committen**
  `git add Agenten/Handel/replay.py Agenten/Handel/tests/test_replay.py`
  `git commit -m "replay: Familie B ueber spur_buch, historische Quelle und Zeituhr"`

---

### Aufgabe 6: Gebühr je Spur — wahr statt pauschal

**Dateien:**
- Ändern: `Agenten/Handel/replay.py` (`gebuehr_fuer`)
- Ändern: `Agenten/Handel/tests/test_replay.py`
- Ändern: `wachen.json` der nachrechenbaren Spuren (Wert `gebuehr_taker`)

**Interfaces:**
- Produziert: `gebuehr_fuer(spur, w) -> float` (Prozent je Seite),
  `kennzahlen(journal_pfad) -> dict` über `kosten_wendepunkt`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
class GebuehrTest(unittest.TestCase):
    def test_wachen_wert_hat_vorrang(self):
        self.assertEqual(0.6, replay.gebuehr_fuer("kraken", {"gebuehr_taker": 0.006}))
        self.assertEqual(0.05, replay.gebuehr_fuer("xperp", {"gebuehr_taker": 0.0005}))

    def test_fehlender_wert_faellt_auf_den_boersensatz_der_spur(self):
        # OKX Spot (scanner, squeeze, wavetrend, macd_mtf, supertrend)
        self.assertEqual(0.1, replay.gebuehr_fuer("squeeze", {}))
        # OKX Perp (Perp-Spuren ohne eigenen Wert)
        self.assertEqual(0.05, replay.gebuehr_fuer("liq_wand", {}))
        # Kraken Spot (orbk)
        self.assertEqual(0.6, replay.gebuehr_fuer("orbk", {}))

    def test_kein_stiller_pauschalwert_mehr(self):
        # Die alte 0,10 %-Pauschale darf nirgends mehr als Ersatz auftauchen.
        for spur in replay.SPUREN_TEIL_A:
            self.assertIsNotNone(replay.gebuehr_fuer(spur, {}))
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd Agenten/Handel && python tests/test_replay.py`
  Erwartet: FAIL — `AttributeError: module 'replay' has no attribute 'gebuehr_fuer'`

- [ ] **Schritt 3: Implementierung**

```python
# Boersensatz je Spur, wenn die wachen.json keine Gebuehr traegt. Prozent je
# Seite. Quelle der Saetze: die Boersenseiten und die eigenen Fuellungen
# (Kraken SOLEUR vom 22.09.2026: 0,30012 EUR auf 50,01954 EUR = 0,6000 %).
BOERSENSAETZE = {
    "okx_spot": 0.10,        # scanner, squeeze, wavetrend, macd_mtf, supertrend
    "okx_perp": 0.05,        # liq_wand, trendwende_btc, swap, xperp
    "kraken": 0.60,          # orbk, kraken, mosaic, moondev_marktlage
}

SPUR_BOERSE = {
    "scanner": "okx_spot", "squeeze": "okx_spot", "wavetrend": "okx_spot",
    "macd_mtf": "okx_spot", "supertrend": "okx_spot", "orb": "okx_spot",
    "gitter": "okx_perp", "liq_wand": "okx_perp", "trendwende_btc": "okx_perp",
    "swap": "okx_perp", "xperp": "okx_perp",
    "orbk": "kraken", "kraken": "kraken", "mosaic": "kraken",
    "moondev_marktlage": "kraken",
}


def gebuehr_fuer(spur, w):
    """Gebuehr je Seite in Prozent.

    Reihenfolge: eigener Wert aus der wachen.json -> Boersensatz der Spur.
    Einen pauschalen Ersatz gibt es NICHT: fuer eine Perp-Spur waere die alte
    0,10-%-Annahme der zwanzigfache Satz und jedes Nettoergebnis zu schlecht.
    """
    wert = w.get("gebuehr_taker")
    if wert is not None:
        return round(float(wert) * 100.0, 4)
    satz = SPUR_BOERSE.get(spur)
    if satz is None:
        raise KeyError("kein Boersensatz fuer %r - bitte gebuehr_taker in die "
                       "wachen.json eintragen" % spur)
    return BOERSENSAETZE[satz]


```

`kennzahlen()` wird hier NICHT neu geschrieben - es steht schon in Aufgabe 3
und ist die einzige Kennzahlenrechnung des Backtests.

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cd Agenten/Handel && python tests/test_replay.py`
  Erwartet: `OK` (10 Tests)

- [ ] **Schritt 5: Die fehlenden Werte in die `wachen.json` eintragen**
  Für jede nachrechenbare Spur ohne `gebuehr_taker` den Börsensatz eintragen,
  mit datiertem Vermerk, damit die Zahl nicht als geraten gelesen wird:
  `"gebuehr_taker": 0.001, "_gebuehr_vermerk": "OKX Spot Taker, eingetragen 2026-09-24 (Backtest-Fundament)"`.
  Kein `git add -A`; nur die berührten `wachen.json`.
  **Gegenprobe:** `git diff --numstat` je Datei — genau eine Zeile hinzugefügt.

- [ ] **Schritt 6: Committen**
  `git commit -m "replay: Gebuehr je Spur aus wachen.json, Boersensatz als Rueckfall"`

---

### Aufgabe 7: Optimierer — Fenster und Suchtabelle

**Dateien:**
- Neu: `Agenten/Handel/spur_opt.json`
- Neu: `Agenten/Handel/optimieren.py`
- Test: `Agenten/Handel/tests/test_optimieren.py`

**Interfaces:**
- Konsumiert: `replay.lauf_a()`.
- Produziert: `suchtabelle(spur) -> dict`, `fenster(laenge, n_fenster, teil) -> list`,
  `suche(spur, gebuehr_pct) -> dict`.

- [ ] **Schritt 1: `spur_opt.json` anlegen** (Zahlen, nicht Code)

```json
{
  "_hinweis": "Suchbereiche je Spur. Der Code kennt keine Zahlen. 'raster' sind die Werte, die durchprobiert werden; 'schluessel' ist der Name in der wachen.json, den der Replay ueberschreibt.",
  "squeeze": {
    "schluessel": ["squeeze_mindest_momentum", "stop_pct", "ziel_r"],
    "raster": {
      "squeeze_mindest_momentum": [0.5, 1.0, 1.5, 2.0],
      "stop_pct": [2.0, 3.0, 4.0],
      "ziel_r": [1.5, 2.0, 3.0]
    },
    "mindest_runden_je_fenster": 8
  },
  "supertrend": {
    "schluessel": ["supertrend_n", "supertrend_faktor", "stop_pct", "ziel_r"],
    "raster": {
      "supertrend_n": [7, 10, 14],
      "supertrend_faktor": [2.0, 3.0, 4.0],
      "stop_pct": [2.0, 4.0],
      "ziel_r": [1.5, 2.0]
    },
    "mindest_runden_je_fenster": 8
  },
  "trendwende_btc": {
    "schluessel": ["stop_pct", "ziel_r"],
    "raster": {"stop_pct": [3.0, 4.0, 5.0], "ziel_r": [1.5, 2.0, 3.0]},
    "mindest_runden_je_fenster": 5
  }
}
```

- [ ] **Schritt 2: Fehlschlagenden Test schreiben**

```python
"""Fensterbildung und Urteil des Optimierers - ohne Netz, ohne echten Lauf."""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))

import optimieren                                                 # noqa: E402


class FensterTest(unittest.TestCase):
    def test_fenster_ueberlappen_nicht_und_decken_die_zeit(self):
        f = optimieren.fenster(1000, 4)
        self.assertEqual(4, len(f))
        self.assertEqual(0, f[0][0])
        self.assertEqual(1000, f[-1][1])
        # jedes Fenster hat eine Such- und eine Pruefhaelfte
        for such, pruef in f:
            self.assertLess(such[0], such[1])
            self.assertLessEqual(such[1], pruef[0])
            self.assertEqual(such[1] + 1, pruef[0])   # lueckenlos

    def test_fenster_lehnt_zu_kurze_reihen_ab(self):
        with self.assertRaises(ValueError):
            optimieren.fenster(10, 4)


class UrteilTest(unittest.TestCase):
    def test_kandidat_ohne_prueffenster_vorteil_ist_kein_hebel(self):
        u = optimieren.urteil_aus([{"runden": 20, "netto_pct_mittel": 0.5}],
                                  {"runden": 20, "netto_pct_mittel": 0.5}, [])
        self.assertFalse(u["ueberlebt"])
        self.assertIn("kein Hebel", u["grund"])

    def test_zu_wenige_runden_ist_ein_befund_keine_messung(self):
        u = optimieren.urteil_aus([{"runden": 4, "netto_pct_mittel": 3.0}],
                                  {"runden": 4, "netto_pct_mittel": 3.0}, [])
        self.assertFalse(u["ueberlebt"])
        self.assertIn("Befund", u["grund"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 3: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd Agenten/Handel && python tests/test_optimieren.py`
  Erwartet: FAIL — `ModuleNotFoundError: No module named 'optimieren'`

- [ ] **Schritt 4: Implementierung** — Teil 1 von `optimieren.py`

```python
"""Parametersuche je Spur auf dem Backtest-Fundament (Walk-Forward).

Verfahren: Die Zeitreihe wird in ueberlappungsfreie Fenster geteilt; jedes
Fenster hat eine Such- und eine PRUEFHAELFTE, die die Suche nie gesehen hat.
Uebernommen wird nur, was in der Pruefhaelfte UND im rollierenden Mittel besser
ist. Ein Kandidat, der in der Pruefhaelfte verliert, ist "kein Hebel" - das ist
ein Ergebnis, kein Fehlschlag. (Gitter-Befund 15.09.2026: 42 Kombinationen
spannten 0,17 bis 2,23 % - der Parameter ist selten der Hebel.)

Geschrieben wird NIE in eine wachen.json. Ausgabe ist eine Vorschlagsdatei
daten/backtest/<spur>/optimierung.json; die Uebernahme entscheidet Max.
"""

import itertools
import json
import os

HIER = os.path.dirname(os.path.abspath(__file__))
OPT_PFAD = os.path.join(HIER, "spur_opt.json")

MINDEST_KERZEN_JE_FENSTER = 800      # sonst ist ein Fenster keine Stichprobe


def suchtabelle(spur):
    with open(OPT_PFAD, encoding="utf-8") as f:
        d = json.load(f)
    if spur not in d:
        raise KeyError("kein Suchbereich fuer %r in spur_opt.json" % spur)
    return d[spur]


def fenster(laenge, n_fenster):
    """[(such, pruef)] - Zeitabschnitte als (von, bis) in Kerzenindizes.

    Lueckenlos und ueberlappungsfrei: die Pruefhaelfte eines Fensters endet
    dort, wo die Suchhaelfte des naechsten beginnt. So sieht die Suche nie eine
    Kerze, die sie spaeter pruefen soll.
    """
    laenge = int(laenge)
    if laenge < n_fenster * MINDEST_KERZEN_JE_FENSTER:
        raise ValueError("Reihe zu kurz: %d Kerzen fuer %d Fenster (mindestens %d)"
                         % (laenge, n_fenster, n_fenster * MINDEST_KERZEN_JE_FENSTER))
    breite = laenge // n_fenster
    aus = []
    for i in range(n_fenster):
        von = i * breite
        bis = von + breite
        mitte = von + breite // 2
        aus.append(((von, mitte), (mitte + 1, bis)))
    return aus


def urteil_aus(such, pruef, weitere):
    """Ueberlebt ein Kandidat? `weitere` sind die uebrigen Fensterpruefungen."""
    if pruef.get("runden", 0) < 8 or any(s.get("runden", 0) < 8 for s in such):
        return {"ueberlebt": False,
                "grund": "unter 8 Runden - ein Befund, keine Messung"}
    if not pruef.get("runden"):
        return {"ueberlebt": False, "grund": "kein Hebel: Prueffenster ohne Runde"}
    if pruef["netto_pct_mittel"] <= such[0]["netto_pct_mittel"]:
        return {"ueberlebt": False, "grund": "kein Hebel: Prueffenster nicht besser"}
    mittel_pruef = (pruef["netto_pct_mittel"] + sum(w["netto_pct_mittel"]
                                                    for w in weitere)) / (1 + len(weitere))
    if mittel_pruef <= 0:
        return {"ueberlebt": False,
                "grund": "kein Hebel: rollierendes Mittel nicht positiv"}
    return {"ueberlebt": True, "grund": "Prueffenster und rollierendes Mittel besser"}
```

- [ ] **Schritt 5: Test laufen lassen, PASS verifizieren**
  Run: `cd Agenten/Handel && python tests/test_optimieren.py`
  Erwartet: `OK` (4 Tests)

- [ ] **Schritt 6: Committen**
  `git add Agenten/Handel/optimieren.py Agenten/Handel/spur_opt.json Agenten/Handel/tests/test_optimieren.py`
  `git commit -m "optimieren: Walk-Forward-Fenster und Urteil, Suchbereiche in JSON"`

---

### Aufgabe 8: Optimierer — Suche fahren und Vorschlag schreiben

**Dateien:**
- Ändern: `Agenten/Handel/optimieren.py` (`suche`, `main`)
- Ändern: `Agenten/Handel/tests/test_optimieren.py`

**Interfaces:**
- Konsumiert: `fenster()`, `urteil_aus()`, `replay.lauf_a()`.
- Produziert: `suche(spur, gebuehr_pct, n_fenster=4) -> dict`, geschrieben nach
  `daten/backtest/<spur>/optimierung.json`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
class SchreibenTest(unittest.TestCase):
    def test_suche_schreibt_nie_in_die_wachen_json(self):
        import hashlib
        import replay
        echt = os.path.join(os.path.dirname(HIER), "supertrend", "wachen.json")
        vorher = hashlib.sha256(open(echt, "rb").read()).hexdigest()
        optimieren.suche("supertrend", gebuehr_pct=0.1, n_fenster=2)
        nachher = hashlib.sha256(open(echt, "rb").read()).hexdigest()
        self.assertEqual(vorher, nachher)

    def test_suche_legt_eine_vorschlagsdatei_an(self):
        import replay
        ergebnis = optimieren.suche("trendwende_btc", gebuehr_pct=0.05, n_fenster=2)
        pfad = os.path.join(os.path.dirname(replay.buch_ordner("trendwende_btc", "x")),
                            "optimierung.json")
        self.assertTrue(os.path.isfile(pfad))
        self.assertIn("kandidaten", ergebnis)
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd Agenten/Handel && python tests/test_optimieren.py`
  Erwartet: FAIL — `AttributeError: module 'optimieren' has no attribute 'suche'`

- [ ] **Schritt 3: Implementierung**

```python
def _kombinationen(raster):
    namen = sorted(raster)
    for werte in itertools.product(*(raster[n] for n in namen)):
        yield dict(zip(namen, werte))


def suche(spur, gebuehr_pct, n_fenster=4):
    """Rastersuche ueber alle Fenster. Gibt das Urteil je Kandidat zurueck."""
    import replay                                                  # noqa: PLC0415

    t = suchtabelle(spur)
    w_modul = replay.spur_modul(spur)
    w = dict(w_modul.lade_wachen())
    takt = w.get("kerzen_takt", "1H")
    insts = w.get("instrumente") or []
    if isinstance(insts, dict):
        insts = list(insts)
    import historie                                                # noqa: PLC0415
    laenge = min((len(historie.lade(i, takt)) for i in insts), default=0)
    if not laenge:
        raise RuntimeError("keine Historie fuer %s" % spur)
    abschnitte = fenster(laenge, n_fenster)

    kandidaten = []
    for werte in _kombinationen(t["raster"]):
        je_fenster = []
        for such, pruef in abschnitte:
            runden, _ = replay.lauf_a(spur, gebuehr_pct,
                                      lauf="opt_%s" % "_".join(
                                          "%s%s" % (k, werte[k]) for k in sorted(werte)),
                                      wachen_patch=werte, bis_ms=pruef[1])
            je_fenster.append(replay.kennzahlen(
                os.path.join(replay.buch_ordner(spur, "opt_%s" % "_".join(
                    "%s%s" % (k, werte[k]) for k in sorted(werte))),
                    "handelsjournal.csv")))
        if not je_fenster:
            continue
        u = urteil_aus([je_fenster[0]], je_fenster[-1], je_fenster[1:-1])
        kandidaten.append({"werte": werte, "je_fenster": je_fenster, **u})

    kandidaten.sort(key=lambda k: (k["ueberlebt"], k.get("je_fenster", [{}])[-1].get(
        "netto_pct_mittel", 0)), reverse=True)
    aus = {"spur": spur, "n_fenster": n_fenster, "gebuehr_pct": gebuehr_pct,
           "kandidaten": kandidaten,
           "ueberlebt": [k["werte"] for k in kandidaten if k["ueberlebt"]]}
    ziel = os.path.join(replay.wurzel(), spur)
    os.makedirs(ziel, exist_ok=True)
    with open(os.path.join(ziel, "optimierung.json"), "w", encoding="utf-8") as f:
        json.dump(aus, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return aus


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spur", required=True)
    ap.add_argument("--fenster", type=int, default=4)
    ap.add_argument("--gebuehr", type=float, default=None)
    a = ap.parse_args()
    import replay                                                  # noqa: PLC0415
    w = dict(replay.spur_modul(a.spur).lade_wachen())
    g = a.gebuehr if a.gebuehr is not None else replay.gebuehr_fuer(a.spur, w)
    aus = suche(a.spur, g, a.fenster)
    print(json.dumps({k: v for k, v in aus.items() if k != "kandidaten"},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `cd Agenten/Handel && python tests/test_optimieren.py`
  Erwartet: `OK` (6 Tests)

- [ ] **Schritt 5: Echten Lauf zeigen und committen**
  `python optimieren.py --spur supertrend --fenster 4`
  Erwartet: eine Ausgabe mit den überlebenden Kandidaten oder der ehrlichen
  Meldung „kein Hebel" — beides ist ein Ergebnis.
  `git commit -m "optimieren: Rastersuche mit Walk-Forward und Vorschlagsdatei"`

---

### Aufgabe 9: Verdrahtung, .gitignore, Doku und Task-Eintrag

**Dateien:**
- Ändern: `Agenten/Handel/auswertung_alle.py`
- Ändern: `.gitignore`
- Neu: `MaxHirn/Wiki/Handel/Backtest-Fundament.md`
- Ändern: `MaxHirn/Archiv/TASKS.md`

**Interfaces:**
- Konsumiert: `replay.kennzahlen()`, `replay.NICHT_NACHRECHENBAR`.

- [ ] **Schritt 1: Freigabe in `.gitignore`** — neben den bestehenden Handels-Zeilen

**Gemessen 2026-09-25 (Aufgabe 1+2 gebaut):** `.py`-Dateien brauchen **keine**
eigenen Zeilen — die generischen Muster `!Agenten/Handel/*.py` (Zeile 75) und
`!Agenten/Handel/tests/*.py` (Zeile 87) decken `historie.py`, `replay.py`,
`optimieren.py` und alle Tests schon ab. Zu prüfen bleibt nur `spur_opt.json`.

```
!Agenten/Handel/spur_opt.json    # gemessen: git check-ignore meldet ihn, die Zeile IST noetig
```
  **Gegenprobe (Hausregel, drei Fälle sind am 15.–17.09. schiefgegangen):**
```bash
git check-ignore -v Agenten/Handel/replay.py        # leer = freigegeben
git check-ignore -v Agenten/Handel/spur_opt.json
git check-ignore -v Agenten/Handel/daten/historie/BTCUSDT_1H.json   # MUSS greifen
git ls-files Agenten/Handel/daten/                  # MUSS leer sein
```

- [ ] **Schritt 2: Eine Zeile je Spur in `auswertung_alle.py`**
  In der Tabelle je Spur zwei Spalten ergänzen, die aus dem Backtest-Journal
  kommen — mit derselben Rechnung (`replay.kennzahlen` → `kosten_wendepunkt`):

```python
def backtest_zeile(spur, journal_pfad):
    """'Backtest: 143 Runden, 52 % Treffer' oder der Grund, warum nicht."""
    if spur in replay.NICHT_NACHRECHENBAR:
        return "nicht nachrechenbar (%s)" % replay.NICHT_NACHRECHENBAR[spur]
    k = replay.kennzahlen(journal_pfad)
    if not k.get("runden"):
        return "kein Backtest-Lauf"
    return "Backtest: %d Runden, %.0f %% Treffer" % (k["runden"], 100 * k["p"])
```

- [ ] **Schritt 3: Wiki-Seite schreiben**
  `MaxHirn/Wiki/Handel/Backtest-Fundament.md` mit: Zweck, die drei Einheiten,
  Spurenfamilien A/B, was nicht nachrechenbar ist und warum, wie man einen Lauf
  startet, und die Regel **„Backtest-Runden zählen nicht für die Freigabe"**.
  Eintrag in `MaxHirn/Wiki/INDEX.md` ergänzen.

- [ ] **Schritt 4: Nicht angefasstes als Task eintragen** (stehende Regel von Max)
  In `MaxHirn/Archiv/TASKS.md` unter `## Offen`, neueste zuerst, fortlaufende ID:
  Kern-Spuren ohne Kerzen-Naht; kostenpflichtige Historien (Deribit-Strike-OI);
  `xperps` Tageszweig als eigener Backtest; `moondev_whale`/`-liquidation`/
  `-sentiment` als nicht nachrechenbar vermerkt; `robinhood_radar` braucht
  längeren Sammelzeitraum.

- [ ] **Schritt 5: Voller Nachweis und Commit**
```bash
cd Agenten/Handel
python tests/test_historie.py && python tests/test_replay.py && python tests/test_optimieren.py
python spiegelstand.py                 # MUSS 32/32 byte-gleich melden
cd ../Bus && python tests/test_ende_zu_ende.py   # MUSS 'Ende-zu-Ende bestanden' melden
```
  `git add <eigene Pfade>` · `git commit -m "Backtest-Fundament: Verdrahtung, Doku, Tasks"`

---

---

## Nachträge aus der Umsetzung (Aufgabe 3+4 gebaut, 2026-09-25)

Vier Stellen des Plans waren falsch. Sie sind im gebauten Code korrigiert; hier
stehen sie, damit der nächste Leser nicht über dieselben Annahmen stolpert.

1. **Das Journal muss die Zeilen der SPUR enthalten, nicht nachgebaute.**
   Der Plan schrieb nur Ausstiegszeilen (`aktion=verkauf`). `kosten_wendepunkt.
   runden_aus_journal()` paart aber Einstieg ↔ Ausstieg je Instrument — ein
   Journal ohne Einstiegszeilen hätte **0 Runden** ergeben und jede Kennzahl
   wäre 0 gewesen. Richtig: die Journalzeilen der Spur werden abgefangen
   (`journal()`-Naht) und so geschrieben, wie die Spur sie gebildet hat
   (`kauf` MIT `stop`/`ziel`, `verkauf` mit Endpreis). Gemessen: Positionen
   tragen `stop` **und** `ziel` (`squeeze/handeln.py:244-248`).
2. **Ein rollierendes Fenster statt wachsendem Präfix** (`fenster=`).
   Der Plan ließ die Spur je Schritt den ganzen Zeitraum bis hierher sehen.
   Zwei Fehler auf einmal: (a) **untreu** — im Betrieb fordert jede Spur eine
   feste `kerzen_anzahl` an, sie sieht nie die ganze Geschichte; (b) **O(n²)** —
   gemessen 900 Schritte über 1.200 Kerzen = 20 s, hochgerechnet auf die volle
   1H-Historie (50.223 Kerzen) ≈ **16 Stunden**. Mit Fenster bleibt der Schritt
   konstant und die ganze Historie läuft in Minuten.
3. **`max_kerzen=`** für kurze Läufe (Tests, Gegenprobe) — ohne ihn hätte die
   Testsuite Stunden gebraucht.
4. **Aufgabe 6 (Gebühr) wird zur Voraussetzung, nicht zur Nacharbeit.** Die
   vier Indikator-Spuren tragen keine `gebuehr_taker`; bis sie sie tragen,
   laufen Backtest-Läufe mit `--gebuehr 0.1` von Hand. Das ist ein
   Zwischenstand, kein Endzustand.

**Was die Gegenprobe beweist:** `squeeze` liefert über den neuen Kern exakt
dieselben Runden wie `backtest_prognose.py` (gleiche Kerzen, beide Wege) — der
neue Kern erfindet nichts, er macht denselben Walk über eine andere Datenquelle
und um ein Vielfaches schneller.

## Self-Review dieses Plans

- **Spezifikations-Abdeckung:** Datenschicht → Aufgaben 1–2. Replay-Kern →
  3–5. Kostenwahrheit → 6. Optimierer → 7–8. Kern-Spuren → ausdrücklich außen
  vor (Spec-Abschnitt „zweites Teilprojekt"). Abnahmekriterien 1 und 2 →
  Aufgaben 2.5 und 4. Kriterium 3 → `NichtsAusserhalbTest` (Aufgabe 3).
  Kriterium 4 → Aufgabe 9.5. Kriterien 5/6 → Aufgabe 8.5 und 9.5.
- **Typ-Konsistenz (gefunden und inline behoben):** `lauf_a()` bekommt den
  optionalen Parameter `wachen_patch=None` (legt ihn über die geladene Wachen,
  wie `backtest_prognose.fahre()`) — ohne ihn könnte der Optimierer seine
  Kandidaten nicht setzen.
- **Weitere inline behobene Planfehler:** (1) `speichere()` hatte eine
  ungültige `for`-Bedingung (bedingter Ausdruck ohne Klammern) — jetzt über eine
  Zwischenvariable. (2) `von_binance()`/`funding()` brachen bei einer kurzen
  Seite ab und liefen gegen eine Attrappe in eine Endlosschleife — jetzt Abbruch
  über „keine neuen Zeitstempel" plus Grenze `bis_ms`. (3) `kennzahlen()` wurde
  in Aufgabe 6 definiert, aber schon in Aufgabe 5 gerufen — jetzt Teil von
  Aufgabe 3. (4) Feldnamen (`kerzen_takt` / `kerzen_zeitrahmen`, `instrumente`
  als Liste ODER Dict) waren fest verdrahtet — jetzt `_feld()`, `_instrumente()`,
  `_takt()`.
- **Urteil-Signatur:** `urteil_aus(such, pruef, weitere)` nimmt Listen, weil der
  Test sie so übergibt; `suche()` reicht `[je_fenster[0]]` und `je_fenster[1:-1]`
  — konsistent.
- **Platzhalter:** keine. Jeder Code-Schritt zeigt den Code, den er meint.