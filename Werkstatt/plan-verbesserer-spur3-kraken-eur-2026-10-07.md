# Verbesserer Ausbaustufe 2a (Spur 3, Kraken-EUR) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den woechentlichen Verbesserer-Zyklus auf Spur 3 (Kraken, live,
mehrwaehrungsfaehig) ausweiten, ohne den Simulationskern fuer Spur 1 zu
veraendern — ueber ein Kostenmodell-Plugin, das auch Spur 2 (XPERP) spaeter
bedienen kann.

**Architecture:** `ruecktest.simuliere()`/`walk_forward()`/`holdout()`
bekommen einen optionalen `modell`-Parameter (vier Hooks: `gebuehr_pct`,
`pruefe_ausstieg`, `laufende_kosten`, `in_basiswaehrung`), Default
`SPOT_MODELL` reproduziert das heutige Verhalten exakt. Spur 3 liefert ein
`KrakenModell` (Gebuehr live aus `wachen.json`, Waehrungsumrechnung ueber
Kraken-FX-Tageskurse). Eine neue Kerzenquelle (`kraken_kerzen.py`) und ein
Dispatch je Spur in `lauf.py` runden das ab; `suche.py` bekommt einen
Gewichte-Schalter und eine Denylist-Erweiterung.

**Tech Stack:** Python 3 Standardbibliothek, `unittest`. Venv:
`Agenten/Handel/scanner/.venv`.

**Spec:** `Werkstatt/spec-verbesserer-spur3-kraken-eur-2026-10-07.md`
(abgenommen, Commit `6fc8ff9f`). Vorgaenger-Stand: Ausbaustufe 1.5,
Commits `a0f4d6ad`..`b815a197`, 122 Modul-Tests gruen.

## Global Constraints

- **Bereich `handel`** (`Agenten/Handel/verbesserer/`). Task 6 legt
  `spuren.json["spur3"]` an — Lesezugriff auf `Agenten/Handel/kraken/` (fremder
  Code, nicht Bereich `handel`, aber nur lesend: BEFUND nicht noetig, es wird
  nichts dort geschrieben).
- **`kennzahlen()` bleibt waehrungsblind und unveraendert** — Waehrungsumrechnung
  passiert in `simuliere()`, bevor eine Runde in die Liste kommt, die
  `kennzahlen()` sieht.
- **`SPOT_MODELL` ist der Default ueberall** — kein Aufrufer, der `modell`
  nicht explizit angibt, darf ein anderes Verhalten sehen. Jede Aenderung in
  Task 1 ist ein reiner Regressionstest gegen den bestehenden Bestand (122
  Tests), bevor irgendein Kraken-Code entsteht.
- **Keine Gewichte aus Spur 3s Suchraum** — `gewichte_durchsuchbar: false` in
  Spur 3s Konfig-Override; Default `true` fuer Bestandsspuren.
- **`suche.DENYLIST`/`basis_kandidat()`-Deckel-Mapping**: die *candidate-internen*
  Schluessel `max_pro_trade_usd`/`max_gesamt_usd` bleiben als generische
  Namenskonvention in `ruecktest.py`/`suche.py` unveraendert (sie bedeuten
  "Geld-Deckel", nicht "US-Dollar") — nur `basis_kandidat()`s *Lesequelle*
  aus `wachen.json` wird je Spur konfigurierbar.
- **Alle bestehenden 122 Modul-Tests bleiben gruen.** Testlauf:
  `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover
  -s verbesserer/tests`.
- **`git add` immer namentlich**, je Task ein eigener Commit. Commit-Footer:
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` +
  `Claude-Session: https://claude.ai/code/session_01ABNAZC2GQrdDhNjqijQL8M`.
- **`handel_erlaubt`, `freigabe`, `stillgelegt`, `bedingung_5_aktiv`,
  `trigger_modus`, `quote_vorrang`, `mindest_guthaben_je_quote` nie in
  `spuren.json["spur3"]["aenderbar"]` aufnehmen.**
- **Versionierte Textdateien nur per gezieltem Ersatz (Edit), nie Rewrite** —
  `ruecktest.py`, `suche.py`, `lauf.py` sind ASCII, `konfig.json`/
  `spuren.json` sind JSON. Vor jedem Edit frisch lesen.

## Review Focus

- **`modell=None` an allen drei Funktionen** (`simuliere`/`walk_forward`/
  `holdout`) muss zuverlaessig auf `SPOT_MODELL` fallen — ein vergessenes
  `modell or SPOT_MODELL` an einer der drei Stellen wuerde `None["gebuehr_pct"]`
  werfen, sobald irgendein Aufrufer ohne `modell` durchreicht. Abgedeckt in
  Task 1.
- **`gebuehr_pct` wird am Ausstiegstag gelesen, nicht am Einstiegstag** — bei
  einer Spur mit variabler Gebuehr (Kraken) wirkt sich das auf beide
  Transaktionsseiten gleich aus; das ist eine bewusste Naeherung (siehe Spec
  Risiken), aber ein Test muss zeigen, DASS sie das tut, nicht nur, dass die
  Zahl irgendwie passt. Abgedeckt in Task 1/Task 3.
- **`in_basiswaehrung` wirkt auf `gv`, `einsatz` UND `erloes` gleichzeitig**,
  nicht nur auf `gv` allein — sonst stimmen `summe_gv`/`einsatz`-Summen in
  Folgeberichten nicht zusammen. Abgedeckt in Task 1 (Hook-Vertrag) und
  Task 3 (echte Umrechnung).
- **Fehlender FX-Tageskurs** (USDC/EURC-Luecke) darf nicht mit 1,0
  aufgefuellt werden — `in_basiswaehrung` muss in diesem Fall erkennbar
  scheitern/melden, nicht stillschweigend durchrechnen. Abgedeckt in Task 3.
- **`gewichte_durchsuchbar=false` darf `nachbarn()`s Gate-/Sizing-/
  Watchlist-Nachbarn nicht mitabschalten** — nur die Gewichts-Schleife fehlt,
  alles andere bleibt wie heute. Abgedeckt in Task 4.

---

## Dateistruktur

| Datei | Verantwortung | Aenderung |
|---|---|---|
| `verbesserer/ruecktest.py` | Walk-Forward-Backtest | `SPOT_MODELL` + `modell`-Parameter in `simuliere()`/`walk_forward()`/`holdout()` |
| `verbesserer/kraken_kerzen.py` | neu | Kraken-OHLC, Shape wie `kerzen.py` |
| `verbesserer/kraken_modell.py` | neu | `KrakenModell`: Gebuehr live, Waehrungsumrechnung |
| `verbesserer/suche.py` | Kandidatenraum + Suche | `gewichte_durchsuchbar`-Schalter in `nachbarn()`, DENYLIST-Erweiterung, `basis_kandidat()` mit `deckel_felder` |
| `verbesserer/konfig.json` | Modulparameter | `gewichte_durchsuchbar: true` (Default) |
| `verbesserer/spuren.json` | Spur-Konfiguration | `spur3`-Eintrag |
| `verbesserer/lauf.py` | Orchestrator | Kerzenquelle + `modell` je Spur dispatchen |
| `verbesserer/tests/test_ruecktest_modell.py` | neu | Task 1 |
| `verbesserer/tests/test_kraken_kerzen.py` | neu | Task 2 |
| `verbesserer/tests/test_kraken_modell.py` | neu | Task 3 |
| `verbesserer/tests/test_suche_raum.py` | Bestand | Task 4/5 Erweiterungen |
| `verbesserer/tests/test_lauf.py` | Bestand | Task 6 Erweiterung (End-to-End Spur 3) |

---

## Task 1: Kostenmodell-Hooks in `ruecktest.py`

**Files:**
- Modify: `verbesserer/ruecktest.py` (`simuliere()`, `walk_forward()`, `holdout()`)
- Test: `verbesserer/tests/test_ruecktest_modell.py` (neu)

**Interfaces:**
- Produces: `SPOT_MODELL: dict` mit Schluesseln `"gebuehr_pct"`,
  `"pruefe_ausstieg"`, `"laufende_kosten"`, `"in_basiswaehrung"` (je ein
  Callable). `simuliere(matrix, kerzen_je_inst, kandidat, start_tag, end_tag,
  modell=None)`, `walk_forward(kerzen_je_inst, kandidat, konfig, modell=None)`,
  `holdout(kerzen_je_inst, kandidat, holdout_tage, modell=None)` — `None`
  faellt in allen drei Funktionen auf `SPOT_MODELL` zurueck.
  - `gebuehr_pct(inst: str, tag: int) -> float`
  - `pruefe_ausstieg(position: dict, kerze: list) -> (grund: str, trigger: float) | None`
  - `laufende_kosten(position: dict, tag: int) -> float` (Gesamtkosten in
    Positionswaehrung bis `tag`, nicht je Tag — der Hook rechnet selbst, wie
    er akkumuliert)
  - `in_basiswaehrung(betrag: float, inst: str, tag: int) -> float`
- Consumes: nichts Neues (reiner Umbau bestehender Logik).

- [ ] **Step 1: Failing test schreiben** — `verbesserer/tests/test_ruecktest_modell.py`

```python
"""modell-Parameter in simuliere()/walk_forward()/holdout(): SPOT_MODELL
reproduziert das Bestandsverhalten exakt (Regression), ein Fake-Modell
zeigt, dass alle vier Hooks tatsaechlich aufgerufen werden."""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import ruecktest  # noqa: E402


def _flat_dann_hoch(n):
    k = []
    for i in range(n):
        p = 100.0 if i < 122 else 100.0 + (i - 122) * 6.0
        k.append([i * 86400000, p, p * 1.001, p * 0.999, p, 1000.0])
    return k


KAND = {
    "gates": {"mindest_score": 0.0, "max_volatilitaet_pa": 9.0,
              "mindest_chance_risiko": 0.0, "stop_min": 4.0, "stop_max": 12.0,
              "abklingzeit_tage": 3, "max_offene_positionen": 4,
              "max_gesamt_usd": 200.0, "max_pro_trade_usd": 50.0},
    "gewichte": None, "watchlist": ["AAA"], "sizing": "flach",
}


class TestModellDefault(unittest.TestCase):
    def setUp(self):
        self.kerzen = {"AAA": _flat_dann_hoch(140)}
        self.m = ruecktest.merkmals_matrix(self.kerzen)

    def test_ohne_modell_gleich_mit_spot_modell(self):
        a = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125)
        b = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125,
                                modell=ruecktest.SPOT_MODELL)
        self.assertEqual(a, b)

    def test_spot_modell_gebuehr_ist_kosten_konstante(self):
        self.assertEqual(ruecktest.SPOT_MODELL["gebuehr_pct"]("AAA", 120),
                         ruecktest.GEBUEHR_PCT)

    def test_spot_modell_laufende_kosten_null(self):
        self.assertEqual(
            ruecktest.SPOT_MODELL["laufende_kosten"]({"einstieg_tag": 120}, 124),
            0.0)

    def test_spot_modell_in_basiswaehrung_identitaet(self):
        self.assertEqual(
            ruecktest.SPOT_MODELL["in_basiswaehrung"](42.0, "AAA", 120), 42.0)


class TestModellHooksWerdenAufgerufen(unittest.TestCase):
    def setUp(self):
        self.kerzen = {"AAA": _flat_dann_hoch(140)}
        self.m = ruecktest.merkmals_matrix(self.kerzen)
        self.gerufen = {"gebuehr_pct": 0, "pruefe_ausstieg": 0,
                        "laufende_kosten": 0, "in_basiswaehrung": 0}

    def _fake_modell(self, gebuehr=0.0005):
        def _gebuehr(inst, tag):
            self.gerufen["gebuehr_pct"] += 1
            return gebuehr

        def _pruefe(position, kerze):
            self.gerufen["pruefe_ausstieg"] += 1
            hoch, tief = kerze[2], kerze[3]
            if tief <= position["stop"]:
                return "stop", position["stop"]
            if hoch >= position["ziel"]:
                return "ziel", position["ziel"]
            return None

        def _laufend(position, tag):
            self.gerufen["laufende_kosten"] += 1
            return 0.0

        def _basis(betrag, inst, tag):
            self.gerufen["in_basiswaehrung"] += 1
            return betrag * 2.0  # erkennbare, falsche "Umrechnung"

        return {"gebuehr_pct": _gebuehr, "pruefe_ausstieg": _pruefe,
                "laufende_kosten": _laufend, "in_basiswaehrung": _basis}

    def test_alle_vier_hooks_werden_gerufen(self):
        modell = self._fake_modell()
        runden = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125,
                                     modell=modell)
        self.assertEqual(len(runden), 1)
        self.assertGreater(self.gerufen["gebuehr_pct"], 0)
        self.assertGreater(self.gerufen["pruefe_ausstieg"], 0)
        self.assertGreater(self.gerufen["laufende_kosten"], 0)
        self.assertGreater(self.gerufen["in_basiswaehrung"], 0)

    def test_in_basiswaehrung_wirkt_auf_gv_einsatz_und_erloes(self):
        modell = self._fake_modell()
        ohne = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125)[0]
        mit = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125,
                                  modell=modell)[0]
        self.assertAlmostEqual(mit["gv"], ohne["gv"] * 2.0, places=6)
        self.assertAlmostEqual(mit["einsatz"], ohne["einsatz"] * 2.0, places=6)
        self.assertAlmostEqual(mit["erloes"], ohne["erloes"] * 2.0, places=6)

    def test_gebuehr_pct_wird_mit_ausstiegstag_gerufen(self):
        gesehen = []

        def _gebuehr(inst, tag):
            gesehen.append(tag)
            return 0.0005

        modell = self._fake_modell()
        modell["gebuehr_pct"] = _gebuehr
        ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125, modell=modell)
        # Ziel-Treffer liegt bei Tag 124 (siehe Fixture) - der Hook sieht den
        # Ausstiegstag, nicht den Einstiegstag (120).
        self.assertIn(124, gesehen)
        self.assertNotIn(120, gesehen)


class TestWalkForwardUndHoldoutReichenModellDurch(unittest.TestCase):
    def test_walk_forward_ohne_modell_unveraendert(self):
        kerzen = {"AAA": _flat_dann_hoch(240)}
        konf = {"oos_training_tage": 120, "oos_test_tage": 30,
                "oos_schritt_tage": 30}
        a = ruecktest.walk_forward(kerzen, KAND, konf)
        b = ruecktest.walk_forward(kerzen, KAND, konf,
                                   modell=ruecktest.SPOT_MODELL)
        self.assertEqual(a, b)

    def test_holdout_ohne_modell_unveraendert(self):
        kerzen = {"AAA": _flat_dann_hoch(240)}
        a = ruecktest.holdout(kerzen, KAND, 60)
        b = ruecktest.holdout(kerzen, KAND, 60, modell=ruecktest.SPOT_MODELL)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen, Fehlschlag bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_ruecktest_modell.py`
Expected: FAIL mit `AttributeError: module 'ruecktest' has no attribute 'SPOT_MODELL'`

- [ ] **Step 3: `SPOT_MODELL` + Hook-Funktionen definieren** — in `ruecktest.py`, nach der `GEBUEHR_PCT`-Zeile (nach `GEBUEHR_PCT = kosten.GEBUEHR_PCT`) einfuegen

```python

def _spot_gebuehr_pct(inst, tag):
    return GEBUEHR_PCT


def _spot_pruefe_ausstieg(position, kerze):
    """Stop am Tagestief vor Ziel am Tageshoch - die heutige, feste Regel."""
    hoch, tief = kerze[2], kerze[3]
    if tief <= position["stop"]:
        return "stop", position["stop"]
    if hoch >= position["ziel"]:
        return "ziel", position["ziel"]
    return None


def _spot_laufende_kosten(position, tag):
    return 0.0


def _spot_in_basiswaehrung(betrag, inst, tag):
    return betrag


# Default-Kostenmodell: eine Waehrung, keine laufenden Kosten, Gebuehr aus
# kosten.GEBUEHR_PCT - reproduziert exakt das bisherige simuliere()-Verhalten.
# Spur 3 (Kraken) und spaeter Spur 2 (XPERP) liefern eigene Modelle mit
# denselben vier Schluesseln.
SPOT_MODELL = {
    "gebuehr_pct": _spot_gebuehr_pct,
    "pruefe_ausstieg": _spot_pruefe_ausstieg,
    "laufende_kosten": _spot_laufende_kosten,
    "in_basiswaehrung": _spot_in_basiswaehrung,
}
```

- [ ] **Step 4: `simuliere()` auf die Hooks umstellen**

Signatur ersetzen:
```python
def simuliere(matrix, kerzen_je_inst, kandidat, start_tag, end_tag):
```
durch:
```python
def simuliere(matrix, kerzen_je_inst, kandidat, start_tag, end_tag, modell=None):
```

Am Anfang des Funktionskoerpers (nach dem Docstring, vor `g = kandidat["gates"]`)
einfuegen:
```python
    modell = modell or SPOT_MODELL
```

Den Ausstiegs-Block ersetzen. Alt:
```python
        behalten = []
        for p in offen:
            kerze = kerzen_je_inst[p["inst"]][t]
            hoch, tief = kerze[2], kerze[3]
            if tief <= p["stop"]:
                grund, trigger = "stop", p["stop"]
                frei_ab[p["inst"]] = t + g["abklingzeit_tage"]
            elif hoch >= p["ziel"]:
                grund, trigger = "ziel", p["ziel"]
            else:
                behalten.append(p)
                continue
            erloes = p["einsatz"] * trigger / p["einstieg_kurs"] * (1.0 - GEBUEHR_PCT)
            einsatz_mit_gebuehr = p["einsatz"] * (1.0 + GEBUEHR_PCT)
            runden.append({
                "inst": p["inst"],
                "einstieg_tag": p["einstieg_tag"],
                "ausstieg_tag": t,
                "einstieg_kurs": p["einstieg_kurs"],
                "ausstieg_kurs": trigger,
                "einsatz": p["einsatz"],
                "erloes": erloes,
                "gv": erloes - einsatz_mit_gebuehr,
                "grund": grund,
                "score": p["score"],
                "vola_pa": p["vola_pa"],
                "verhaeltnis": p["verhaeltnis"],
            })
        offen = behalten
```
Neu:
```python
        behalten = []
        for p in offen:
            kerze = kerzen_je_inst[p["inst"]][t]
            ausstieg = modell["pruefe_ausstieg"](p, kerze)
            if ausstieg is None:
                behalten.append(p)
                continue
            grund, trigger = ausstieg
            if grund == "stop":
                frei_ab[p["inst"]] = t + g["abklingzeit_tage"]
            gebuehr = modell["gebuehr_pct"](p["inst"], t)
            erloes = p["einsatz"] * trigger / p["einstieg_kurs"] * (1.0 - gebuehr)
            einsatz_mit_gebuehr = p["einsatz"] * (1.0 + gebuehr)
            laufend = modell["laufende_kosten"](p, t)
            gv = erloes - einsatz_mit_gebuehr - laufend
            runden.append({
                "inst": p["inst"],
                "einstieg_tag": p["einstieg_tag"],
                "ausstieg_tag": t,
                "einstieg_kurs": p["einstieg_kurs"],
                "ausstieg_kurs": trigger,
                "einsatz": modell["in_basiswaehrung"](p["einsatz"], p["inst"], t),
                "erloes": modell["in_basiswaehrung"](erloes, p["inst"], t),
                "gv": modell["in_basiswaehrung"](gv, p["inst"], t),
                "grund": grund,
                "score": p["score"],
                "vola_pa": p["vola_pa"],
                "verhaeltnis": p["verhaeltnis"],
            })
        offen = behalten
```

(Der Docstring von `simuliere()` bleibt inhaltlich richtig — die Regel heisst
jetzt `modell["pruefe_ausstieg"]`, Default ist weiter "Stop am Tagestief vor
Ziel am Tageshoch". Einen Satz dazu ergaenzen: `"modell` (Default
``SPOT_MODELL``) liefert Gebuehr, Ausstiegslogik, laufende Kosten und
Waehrungsumrechnung - austauschbar fuer andere Spuren."` an den Docstring
anhaengen.)

- [ ] **Step 5: `walk_forward()` und `holdout()` reichen `modell` durch**

`walk_forward()`-Signatur:
```python
def walk_forward(kerzen_je_inst, kandidat, konfig):
```
durch:
```python
def walk_forward(kerzen_je_inst, kandidat, konfig, modell=None):
```
und den `simuliere(...)`-Aufruf darin:
```python
        runden = simuliere(matrix, kerzen_je_inst, kandidat, start, bis)
```
durch:
```python
        runden = simuliere(matrix, kerzen_je_inst, kandidat, start, bis, modell)
```

`holdout()`-Signatur:
```python
def holdout(kerzen_je_inst, kandidat, holdout_tage):
```
durch:
```python
def holdout(kerzen_je_inst, kandidat, holdout_tage, modell=None):
```
und den `simuliere(...)`-Aufruf darin:
```python
    runden = simuliere(matrix, kerzen_je_inst, kandidat,
                       laenge - holdout_tage, laenge)
```
durch:
```python
    runden = simuliere(matrix, kerzen_je_inst, kandidat,
                       laenge - holdout_tage, laenge, modell)
```

- [ ] **Step 6: Test laufen, gruen bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_ruecktest_modell.py`
Expected: PASS (9 Tests)

- [ ] **Step 7: Gesamte Suite laufen** — Regression gegen alle 122 Bestandstests

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests`
Expected: PASS (131 Tests — 122 Bestand + 9 neu). Kein bestehender Test darf
sich aendern, da `modell=None -> SPOT_MODELL` exakt das alte Verhalten
reproduziert.

- [ ] **Step 8: Commit**

```bash
git add Agenten/Handel/verbesserer/ruecktest.py Agenten/Handel/verbesserer/tests/test_ruecktest_modell.py
git commit
```
Botschaft: `Verbesserer: Kostenmodell-Hooks in simuliere() - SPOT_MODELL als Default`

---

## Task 2: `kraken_kerzen.py` — Kraken-OHLC-Quelle

**Files:**
- Create: `verbesserer/kraken_kerzen.py`
- Test: `verbesserer/tests/test_kraken_kerzen.py` (neu)

**Interfaces:**
- Consumes: `Agenten/Handel/kraken/kraken.py` — Funktion
  `kerzen(paar, intervall=1440, anzahl=720) -> [[ts_ms, o, h, l, c, vol], ...]`
  (bereits vorhanden, aufsteigend sortiert, bis zu 720 Tageskerzen je Abruf).
- Produces: `hole(paar, tage, cache_dir=CACHE) -> kerzen` (Liste, dieselbe
  Zeilenform wie `kerzen.hole()`), `laden(paar, cache_dir=CACHE) -> (kerzen,
  alter_tage | None)` — Signatur identisch zu `kerzen.py`, damit `lauf.py`
  beide Module austauschbar per Namen aufrufen kann (Task 6).

- [ ] **Step 1: Failing test schreiben** — `verbesserer/tests/test_kraken_kerzen.py`

```python
"""kraken_kerzen.py: dieselbe hole()/laden()-Form wie kerzen.py, aber ueber
kraken.kerzen() statt OKX history-candles."""

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "kraken"))
import kraken_kerzen  # noqa: E402


def _reihen(n):
    return [[i * 86400000, 1.0 + i, 1.0 + i, 1.0 + i, 1.0 + i, 9.0]
            for i in range(n)]


class TestKrakenKerzen(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_hole_schreibt_cache_und_liefert_kerzen(self):
        with mock.patch.object(kraken_kerzen.kraken, "kerzen",
                               return_value=_reihen(5)):
            k = kraken_kerzen.hole("XXBTZEUR", 5, cache_dir=self.dir)
        self.assertEqual(len(k), 5)
        d = json.loads((self.dir / "XXBTZEUR.json").read_text("utf-8"))
        self.assertEqual(len(d["kerzen"]), 5)
        self.assertIn("geholt", d)

    def test_laden_ohne_cache(self):
        self.assertEqual(kraken_kerzen.laden("XXX", cache_dir=self.dir),
                         ([], None))

    def test_laden_gibt_alter(self):
        with mock.patch.object(kraken_kerzen.kraken, "kerzen",
                               return_value=_reihen(5)):
            kraken_kerzen.hole("XXBTZEUR", 5, cache_dir=self.dir)
        k, alter = kraken_kerzen.laden("XXBTZEUR", cache_dir=self.dir)
        self.assertEqual(len(k), 5)
        self.assertLess(alter, 1.0)

    def test_hole_leere_antwort_behaelt_cache(self):
        vorhanden = _reihen(3)
        (self.dir / "XXBTZEUR.json").write_text(json.dumps(
            {"geholt": "2020-01-01T00:00:00+00:00", "kerzen": vorhanden}),
            "utf-8")
        with mock.patch.object(kraken_kerzen.kraken, "kerzen",
                               return_value=[]):
            k = kraken_kerzen.hole("XXBTZEUR", 5, cache_dir=self.dir)
        self.assertEqual(k, vorhanden)

    def test_hole_ruft_kraken_mit_intervall_1440(self):
        with mock.patch.object(kraken_kerzen.kraken, "kerzen",
                               return_value=_reihen(5)) as m:
            kraken_kerzen.hole("XXBTZEUR", 5, cache_dir=self.dir)
        m.assert_called_once_with("XXBTZEUR", intervall=1440, anzahl=5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen, Fehlschlag bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_kraken_kerzen.py`
Expected: FAIL mit `ModuleNotFoundError: No module named 'kraken_kerzen'`

- [ ] **Step 3: `kraken_kerzen.py` implementieren**

```python
"""Kraken-Tageshistorie holen und lokal cachen - dieselbe hole()/laden()-Form
wie kerzen.py (OKX), damit lauf.py beide Quellen per Namen austauschen kann.

kraken.kerzen() liefert bereits bis zu 720 Tageskerzen in einem Abruf (kein
Blaettern wie bei OKX history-candles noetig). Faellt der Abruf leer aus,
arbeitet laden() mit dem Cache weiter - wie kerzen.py.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
if str(HIER.parent / "kraken") not in sys.path:
    sys.path.insert(0, str(HIER.parent / "kraken"))

import kraken  # Agenten/Handel/kraken/kraken.py

CACHE = HIER / "kraken_kerzen"


def hole(paar, tage, cache_dir=CACHE):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    reihen = kraken.kerzen(paar, intervall=1440, anzahl=tage)
    if not reihen:
        # Leerer, aber erfolgreicher Abruf - Cache nicht ueberschreiben.
        return laden(paar, cache_dir)[0]
    (cache_dir / (paar + ".json")).write_text(json.dumps(
        {"geholt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "kerzen": reihen}, ensure_ascii=False), "utf-8")
    return reihen


def laden(paar, cache_dir=CACHE):
    p = Path(cache_dir) / (paar + ".json")
    if not p.exists():
        return [], None
    d = json.loads(p.read_text("utf-8"))
    t = datetime.fromisoformat(d["geholt"])
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    alter = (datetime.now(timezone.utc) - t).total_seconds() / 86400.0
    return d["kerzen"], alter
```

- [ ] **Step 4: Test laufen, gruen bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_kraken_kerzen.py`
Expected: PASS (5 Tests)

- [ ] **Step 5: Gesamte Suite laufen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests`
Expected: PASS (136 Tests)

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/verbesserer/kraken_kerzen.py Agenten/Handel/verbesserer/tests/test_kraken_kerzen.py
git commit
```
Botschaft: `Verbesserer: kraken_kerzen.py - Kraken-OHLC-Quelle fuer Spur 3`

---

## Task 3: `kraken_modell.py` — `KrakenModell` (Gebuehr live, Waehrungsumrechnung)

**Files:**
- Create: `verbesserer/kraken_modell.py`
- Test: `verbesserer/tests/test_kraken_modell.py` (neu)

**Interfaces:**
- Consumes: `kraken_kerzen.hole`/`laden` (Task 2) fuer die FX-Kursreihen;
  `ruecktest.SPOT_MODELL`-Hook-Vertrag (Task 1).
- Produces: `erzeuge(wachen, fx_kerzen_eur_usdc, fx_kerzen_eur_eurc) -> modell:
  dict` — dieselben vier Schluessel wie `SPOT_MODELL`. `wachen` ist das
  geladene `kraken/wachen.json`-Dict (Quelle fuer `gebuehr_taker`).
  `fx_kerzen_eur_usdc`/`fx_kerzen_eur_eurc` sind Kerzenlisten (Form wie
  `kraken_kerzen.hole()`), **vorab ausgerichtet** auf dieselben Kalendertage
  wie das Hauptuniversum (der Aufrufer in Task 6 ruft `ruecktest.ausrichten()`
  gemeinsam mit den Instrumentenreihen auf).

- [ ] **Step 1: Failing test schreiben** — `verbesserer/tests/test_kraken_modell.py`

```python
"""KrakenModell: Gebuehr live aus wachen.json, USDC/EURC nach EUR am
Tagesschlusskurs - kein 1:1, keine stille Luecken-Fuellung."""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import kraken_modell  # noqa: E402


def _fx(tag_kurs):
    """{tag: schlusskurs} -> Kerzenliste, Form [ts, o, h, l, c, vol]."""
    return [[tag * 86400000, k, k, k, k, 1.0] for tag, k in tag_kurs.items()]


WACHEN = {"gebuehr_taker": 0.006}


class TestGebuehrLive(unittest.TestCase):
    def test_gebuehr_pct_liest_wachen_live(self):
        m = kraken_modell.erzeuge(WACHEN, [], [])
        self.assertEqual(m["gebuehr_pct"]("XXBTZEUR", 100), 0.006)

    def test_gebuehr_pct_folgt_wachen_aenderung(self):
        # Keine Kopie zur Erzeugungszeit - dieselbe Referenz wird gelesen.
        w = dict(WACHEN)
        m = kraken_modell.erzeuge(w, [], [])
        w["gebuehr_taker"] = 0.001
        self.assertEqual(m["gebuehr_pct"]("XXBTZEUR", 100), 0.001)


class TestWaehrungsumrechnung(unittest.TestCase):
    def test_eur_paar_bleibt_identitaet(self):
        m = kraken_modell.erzeuge(WACHEN, _fx({100: 1.08}), _fx({100: 1.0}))
        self.assertEqual(m["in_basiswaehrung"](50.0, "XXBTZEUR", 100), 50.0)

    def test_usdc_paar_wird_nach_eur_umgerechnet(self):
        # 1 EUR = 1.08 USD; 54 USDC -> 50 EUR.
        m = kraken_modell.erzeuge(WACHEN, _fx({100: 1.08}), _fx({100: 1.0}))
        self.assertAlmostEqual(
            m["in_basiswaehrung"](54.0, "XBTUSDC", 100), 50.0, places=4)

    def test_eurc_paar_wird_mit_gemessenem_kurs_umgerechnet(self):
        m = kraken_modell.erzeuge(WACHEN, _fx({100: 1.08}), _fx({100: 1.002}))
        self.assertAlmostEqual(
            m["in_basiswaehrung"](50.1, "XBTEURC", 100), 50.0, places=4)

    def test_fehlender_fx_tag_wirft_statt_eins_zu_eins_anzunehmen(self):
        m = kraken_modell.erzeuge(WACHEN, _fx({100: 1.08}), _fx({100: 1.0}))
        with self.assertRaises(kraken_modell.FXLuecke):
            m["in_basiswaehrung"](54.0, "XBTUSDC", 999)

    def test_laufende_kosten_null_wie_spot(self):
        m = kraken_modell.erzeuge(WACHEN, [], [])
        self.assertEqual(m["laufende_kosten"]({"einstieg_tag": 1}, 5), 0.0)

    def test_pruefe_ausstieg_unveraendert_wie_spot(self):
        import ruecktest
        m = kraken_modell.erzeuge(WACHEN, [], [])
        position = {"stop": 90.0, "ziel": 110.0}
        kerze = [0, 100.0, 95.0, 85.0, 92.0, 1.0]  # tief 85 <= stop 90
        self.assertEqual(m["pruefe_ausstieg"](position, kerze),
                         ruecktest.SPOT_MODELL["pruefe_ausstieg"](position, kerze))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen, Fehlschlag bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_kraken_modell.py`
Expected: FAIL mit `ModuleNotFoundError: No module named 'kraken_modell'`

- [ ] **Step 3: `kraken_modell.py` implementieren**

```python
"""KrakenModell: das Kostenmodell-Plugin (siehe ruecktest.SPOT_MODELL) fuer
Spur 3 (Kraken, Mehrwaehrung).

Zwei Abweichungen vom Spot-Default:

* gebuehr_pct liest gebuehr_taker LIVE aus dem uebergebenen wachen-Dict -
  die Kraken-Gebuehr hat sich seit 03.09.2026 mehrfach geaendert (siehe
  Spec-Risiken), ein zweiter hartcodierter Wert wie kosten.GEBUEHR_PCT waere
  dieselbe Falle, die Spur 1 schon einmal brauchte test_kosten_gleich.py zu
  vermeiden.
* in_basiswaehrung rechnet USDC-/EURC-Betraege am Tagesschlusskurs nach EUR.
  Ein fehlender FX-Tag ist ein Fehler (FXLuecke), kein 1,0-Naeherungswert -
  dieselbe Haltung wie ausrichten() gegenueber Kerzenluecken.

pruefe_ausstieg/laufende_kosten bleiben Spot-Verhalten (Kraken hat keine
Margin/Funding) - fuer Spur 2 (XPERP) wird eine eigene erzeuge()-Variante
mit abweichenden Hooks entstehen, eigene Spec.
"""

import ruecktest

_USDC_PRAEFIX_SUFFIX = "USDC"
_EURC_PRAEFIX_SUFFIX = "EURC"


class FXLuecke(Exception):
    """Kein Umrechnungskurs fuer diesen Tag - nicht mit 1,0 auffuellen."""


def _kurs_je_tag(fx_kerzen):
    return {k[0] // 86400000: k[4] for k in fx_kerzen}


def erzeuge(wachen, fx_kerzen_eur_usdc, fx_kerzen_eur_eurc):
    """``modell``-Dict fuer Spur 3. ``wachen`` ist das geladene
    kraken/wachen.json-Dict (dieselbe Referenz, nicht kopiert - ein spaeteres
    Neuladen von wachen aktualisiert die Gebuehr automatisch). Die beiden
    FX-Kerzenlisten sind Form wie kraken_kerzen.hole() (EUR/USDC bzw.
    EUR/EURC Tagesschlusskurse)."""
    eur_je_usdc = _kurs_je_tag(fx_kerzen_eur_usdc)
    eur_je_eurc = _kurs_je_tag(fx_kerzen_eur_eurc)

    def gebuehr_pct(inst, tag):
        return wachen["gebuehr_taker"]

    def in_basiswaehrung(betrag, inst, tag):
        if inst.endswith(_USDC_PRAEFIX_SUFFIX):
            kurs = eur_je_usdc.get(tag)
        elif inst.endswith(_EURC_PRAEFIX_SUFFIX):
            kurs = eur_je_eurc.get(tag)
        else:
            return betrag  # EUR-Paar - keine Umrechnung.
        if kurs is None:
            raise FXLuecke(
                "kein EUR-Umrechnungskurs fuer %s an Tag %d" % (inst, tag))
        return betrag * kurs

    return {
        "gebuehr_pct": gebuehr_pct,
        "pruefe_ausstieg": ruecktest.SPOT_MODELL["pruefe_ausstieg"],
        "laufende_kosten": ruecktest.SPOT_MODELL["laufende_kosten"],
        "in_basiswaehrung": in_basiswaehrung,
    }
```

- [ ] **Step 4: Test laufen, gruen bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_kraken_modell.py`
Expected: PASS (8 Tests)

- [ ] **Step 5: Gesamte Suite laufen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests`
Expected: PASS (144 Tests)

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/verbesserer/kraken_modell.py Agenten/Handel/verbesserer/tests/test_kraken_modell.py
git commit
```
Botschaft: `Verbesserer: kraken_modell.py - Gebuehr live, Waehrungsumrechnung EUR`

---

## Task 4: `gewichte_durchsuchbar`-Schalter in `suche.nachbarn()`

**Files:**
- Modify: `verbesserer/suche.py` (`nachbarn()`)
- Modify: `verbesserer/konfig.json`
- Test: `verbesserer/tests/test_suche_raum.py` (Erweiterung)

**Interfaces:**
- Produces: `nachbarn(kandidat, grenzen, gewichte_durchsuchbar=True)` — bei
  `False` entstehen keine Gewichts-Nachbarn, Gate-/Sizing-/Watchlist-Nachbarn
  bleiben unveraendert.

- [ ] **Step 1: Failing test schreiben** — an `verbesserer/tests/test_suche_raum.py` anhaengen (vor `if __name__`)

```python
class TestGewichteSchalter(unittest.TestCase):
    def setUp(self):
        self.basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)

    def test_gewichte_durchsuchbar_false_erzeugt_keine_gewichts_nachbarn(self):
        nb = suche.nachbarn(self.basis, GRENZEN, gewichte_durchsuchbar=False)
        for kandidat in nb:
            self.assertEqual(kandidat["gewichte"], self.basis["gewichte"])

    def test_gewichte_durchsuchbar_false_laesst_andere_nachbarn_unberuehrt(self):
        mit = suche.nachbarn(self.basis, GRENZEN, gewichte_durchsuchbar=True)
        ohne = suche.nachbarn(self.basis, GRENZEN, gewichte_durchsuchbar=False)
        # Gate-/Sizing-/Watchlist-Nachbarn sind identisch; nur die
        # Gewichts-Nachbarn fehlen bei ohne.
        gates_mit = [n["gates"] for n in mit if n["gewichte"] == self.basis["gewichte"]]
        self.assertEqual(gates_mit, [n["gates"] for n in ohne])

    def test_default_ist_true_bestandsverhalten(self):
        self.assertEqual(suche.nachbarn(self.basis, GRENZEN),
                         suche.nachbarn(self.basis, GRENZEN,
                                        gewichte_durchsuchbar=True))
```

Zusaetzlich `test_denylist_vollstaendig` erweitern (EUR-Deckel aus Task 5
vorwegnehmen wuerde hier zu frueh greifen — **nicht in diesem Task aendern**,
das passiert in Task 5).

- [ ] **Step 2: Test laufen, Fehlschlag bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_suche_raum.py`
Expected: FAIL mit `TypeError: nachbarn() got an unexpected keyword argument 'gewichte_durchsuchbar'`

- [ ] **Step 3: `nachbarn()` um den Schalter erweitern**

Signatur ersetzen:
```python
def nachbarn(kandidat, grenzen):
```
durch:
```python
def nachbarn(kandidat, grenzen, gewichte_durchsuchbar=True):
```

Den Gewichte-Block umschliessen. Alt (Einrueckung bleibt, nur die erste Zeile
bekommt eine Bedingung davor):
```python
    # --- Gewichte ---------------------------------------------------------
    # Ein Gewicht um +-0,05 verschieben, auf [0, 0.5] klemmen, dann die
    # Gruppe renormieren. Die Renormierung (Teilen durch ~1,05 bzw. ~0,95)
    # kann ein ohnehin hohes Gewicht knapp ueber 0,5 heben - solche Nachbarn
    # liegen nicht mehr im Rahmen und werden verworfen, damit jeder von
    # nachbarn() gelieferte Kandidat im_rahmen() erfuellt.
    for gruppe in ("chance", "risiko"):
```
Neu:
```python
    # --- Gewichte ---------------------------------------------------------
    # Ein Gewicht um +-0,05 verschieben, auf [0, 0.5] klemmen, dann die
    # Gruppe renormieren. Die Renormierung (Teilen durch ~1,05 bzw. ~0,95)
    # kann ein ohnehin hohes Gewicht knapp ueber 0,5 heben - solche Nachbarn
    # liegen nicht mehr im Rahmen und werden verworfen, damit jeder von
    # nachbarn() gelieferte Kandidat im_rahmen() erfuellt.
    #
    # gewichte_durchsuchbar=False (Spur 3): bewertung.py ist mit Spur 1
    # geteilt, ein Kraken-Befund darf dessen Live-Scoring nicht mitaendern.
    for gruppe in ("chance", "risiko") if gewichte_durchsuchbar else ():
```

(Die Docstring-Zeile ``* Je Gewichtsgruppe und Gewicht ein Nachbar...`` um
einen Halbsatz ergaenzen: `" (nur wenn gewichte_durchsuchbar)"`.)

- [ ] **Step 4: `konfig.json` ergaenzen** — gezielter Edit, nie Rewrite

Nach `"holdout_min_runden": 8,` einfuegen:
```json
  "gewichte_durchsuchbar": true,
```

- [ ] **Step 5: Test laufen, gruen bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_suche_raum.py`
Expected: PASS

- [ ] **Step 6: Gesamte Suite laufen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests`
Expected: PASS (147 Tests)

- [ ] **Step 7: Commit**

```bash
git add Agenten/Handel/verbesserer/suche.py Agenten/Handel/verbesserer/konfig.json Agenten/Handel/verbesserer/tests/test_suche_raum.py
git commit
```
Botschaft: `Verbesserer: gewichte_durchsuchbar-Schalter - Spur 3 haelt bewertung.py fest`

---

## Task 5: DENYLIST-Erweiterung + `basis_kandidat()`-Deckel-Mapping

**Files:**
- Modify: `verbesserer/suche.py` (`DENYLIST`, `basis_kandidat()`)
- Test: `verbesserer/tests/test_suche_raum.py` (Erweiterung)

**Interfaces:**
- Produces: `basis_kandidat(wachen, chance_g, risiko_g, deckel_felder=None)`.
  `deckel_felder` ist ein Dict `{"max_pro_trade_usd": <wachen-Feldname>,
  "max_gesamt_usd": <wachen-Feldname>}`, Default
  `{"max_pro_trade_usd": "max_pro_trade_usd", "max_gesamt_usd":
  "max_gesamt_usd"}` (Bestandsverhalten fuer Spur 1). Die candidate-internen
  Schluessel `gates["max_pro_trade_usd"]`/`gates["max_gesamt_usd"]` bleiben
  IMMER so benannt — nur die Lesequelle aus `wachen` aendert sich.
- `DENYLIST` erweitert um `max_pro_trade_eur`, `max_gesamt_eur`,
  `drawdown_halbierung_usd`, `kill_switch_gesamt_eur`.

- [ ] **Step 1: Failing test schreiben** — an `test_suche_raum.py` anhaengen

```python
class TestDeckelMapping(unittest.TestCase):
    def test_default_liest_usd_feldnamen(self):
        basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)
        self.assertEqual(basis["gates"]["max_pro_trade_usd"], 50)
        self.assertEqual(basis["gates"]["max_gesamt_usd"], 200)

    def test_eur_mapping_liest_eur_feldnamen_in_dieselben_gate_schluessel(self):
        wachen_eur = {**WACHEN, "max_pro_trade_eur": 50, "max_gesamt_eur": 200}
        del wachen_eur["max_pro_trade_usd"], wachen_eur["max_gesamt_usd"]
        basis = suche.basis_kandidat(
            wachen_eur, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE,
            deckel_felder={"max_pro_trade_usd": "max_pro_trade_eur",
                           "max_gesamt_usd": "max_gesamt_eur"})
        # candidate-interner Schluessel bleibt "_usd", Wert kommt aus "_eur".
        self.assertEqual(basis["gates"]["max_pro_trade_usd"], 50)
        self.assertEqual(basis["gates"]["max_gesamt_usd"], 200)


class TestDenylistEurErweiterung(unittest.TestCase):
    def test_eur_deckel_in_denylist(self):
        for feld in ("max_pro_trade_eur", "max_gesamt_eur",
                     "drawdown_halbierung_usd", "kill_switch_gesamt_eur"):
            self.assertIn(feld, suche.DENYLIST)
```

- [ ] **Step 2: Test laufen, Fehlschlag bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_suche_raum.py`
Expected: FAIL — `basis_kandidat()` kennt `deckel_felder` noch nicht;
`max_pro_trade_eur` fehlt in `DENYLIST`.

- [ ] **Step 3: `DENYLIST` erweitern**

Alt:
```python
DENYLIST = frozenset({
    "handel_erlaubt", "freigabe", "drawdown_halbierung_prozent",
    "kill_switch_gesamt_usd", "herzschlag_max_minuten", "journal_zweitziel",
    "max_pro_trade_usd", "max_gesamt_usd", "max_offene_positionen",
})
```
Neu:
```python
DENYLIST = frozenset({
    "handel_erlaubt", "freigabe", "drawdown_halbierung_prozent",
    "kill_switch_gesamt_usd", "herzschlag_max_minuten", "journal_zweitziel",
    "max_pro_trade_usd", "max_gesamt_usd", "max_offene_positionen",
    # Spur 3 (Kraken) nennt dieselben Deckel mit EUR-Endung (teils
    # historisch falsch "_usd", siehe kraken/wachen.json-Kommentar) - zweite
    # Verteidigungslinie zusaetzlich zur Whitelist in spuren.json.
    "max_pro_trade_eur", "max_gesamt_eur", "drawdown_halbierung_usd",
    "kill_switch_gesamt_eur",
})
```

- [ ] **Step 4: `basis_kandidat()` um `deckel_felder` erweitern**

Alt:
```python
def basis_kandidat(wachen, chance_g, risiko_g):
    """Start-Kandidat aus ``wachen.json`` plus den Gewichtskonstanten.

    Die Stop-Grenzen heissen in ``wachen.json`` ``pflicht_stop_prozent_min`` /
    ``pflicht_stop_prozent_max``; im Kandidat und in ``grenzen`` heissen sie
    ``stop_min`` / ``stop_max`` (dieselbe Umbenennung nimmt der Orchestrator in
    Task 9 aus ``spuren.json`` vor). Die uebrigen Gates und die Deckel werden
    unveraendert uebernommen.
    """
    gates = {
        "mindest_score": wachen["mindest_score"],
        "max_volatilitaet_pa": wachen["max_volatilitaet_pa"],
        "mindest_chance_risiko": wachen["mindest_chance_risiko"],
        "stop_min": wachen["pflicht_stop_prozent_min"],
        "stop_max": wachen["pflicht_stop_prozent_max"],
        "abklingzeit_tage": wachen["abklingzeit_tage"],
        "max_offene_positionen": wachen["max_offene_positionen"],
        "max_gesamt_usd": wachen["max_gesamt_usd"],
        "max_pro_trade_usd": wachen["max_pro_trade_usd"],
    }
```
Neu:
```python
_DECKEL_FELDER_DEFAULT = {
    "max_pro_trade_usd": "max_pro_trade_usd",
    "max_gesamt_usd": "max_gesamt_usd",
}


def basis_kandidat(wachen, chance_g, risiko_g, deckel_felder=None):
    """Start-Kandidat aus ``wachen.json`` plus den Gewichtskonstanten.

    Die Stop-Grenzen heissen in ``wachen.json`` ``pflicht_stop_prozent_min`` /
    ``pflicht_stop_prozent_max``; im Kandidat und in ``grenzen`` heissen sie
    ``stop_min`` / ``stop_max`` (dieselbe Umbenennung nimmt der Orchestrator
    aus ``spuren.json`` vor). Die uebrigen Gates werden unveraendert
    uebernommen.

    ``deckel_felder`` mappt die candidate-internen Deckel-Schluessel
    (``max_pro_trade_usd``/``max_gesamt_usd`` - eine Namenskonvention fuer
    "Geld-Deckel", nicht woertlich US-Dollar) auf den tatsaechlichen
    ``wachen.json``-Feldnamen der Spur. Default liest dieselben Namen
    (Spur 1); Spur 3 (Kraken, EUR) uebergibt z. B. ``{"max_pro_trade_usd":
    "max_pro_trade_eur", "max_gesamt_usd": "max_gesamt_eur"}``.
    """
    deckel_felder = deckel_felder or _DECKEL_FELDER_DEFAULT
    gates = {
        "mindest_score": wachen["mindest_score"],
        "max_volatilitaet_pa": wachen["max_volatilitaet_pa"],
        "mindest_chance_risiko": wachen["mindest_chance_risiko"],
        "stop_min": wachen["pflicht_stop_prozent_min"],
        "stop_max": wachen["pflicht_stop_prozent_max"],
        "abklingzeit_tage": wachen["abklingzeit_tage"],
        "max_offene_positionen": wachen["max_offene_positionen"],
        "max_gesamt_usd": wachen[deckel_felder["max_gesamt_usd"]],
        "max_pro_trade_usd": wachen[deckel_felder["max_pro_trade_usd"]],
    }
```

- [ ] **Step 5: Test laufen, gruen bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_suche_raum.py`
Expected: PASS

- [ ] **Step 6: Gesamte Suite laufen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests`
Expected: PASS (150 Tests)

- [ ] **Step 7: Commit**

```bash
git add Agenten/Handel/verbesserer/suche.py Agenten/Handel/verbesserer/tests/test_suche_raum.py
git commit
```
Botschaft: `Verbesserer: Denylist um EUR-Deckel erweitert, basis_kandidat() mit Deckel-Mapping`

---

## Task 6: `spuren.json["spur3"]` + `lauf.py`-Dispatch + End-to-End

**Files:**
- Modify: `verbesserer/spuren.json`
- Modify: `verbesserer/lauf.py`
- Test: `verbesserer/tests/test_lauf.py` (Erweiterung)

**Interfaces:**
- Consumes: `kraken_kerzen` (Task 2), `kraken_modell.erzeuge` (Task 3),
  `suche.basis_kandidat(..., deckel_felder=...)` (Task 5), `suche.suche(...,
  bewerte=, holdout_fn=)` (Bestand, injizierbar seit Stufe 1.5).
- Produces: `lauf.einmal("spur3", ...)` nutzt `kraken_kerzen` statt `kerzen`
  und ein `KrakenModell` statt `SPOT_MODELL` — ohne dass `suche.py` selbst
  etwas von `modell` wissen muss (Verdrahtung ueber `functools.partial` auf
  die bestehenden `bewerte`/`holdout_fn`-Injektionspunkte).

- [ ] **Step 1: Failing test schreiben** — an `verbesserer/tests/test_lauf.py` anhaengen

```python
class TestLaufSpur3(unittest.TestCase):
    """End-to-End: lauf.einmal('spur3') nutzt kraken_kerzen statt kerzen und
    ein KrakenModell statt SPOT_MODELL, ohne spur1 zu beruehren."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._berichte_alt = lauf.BERICHTE
        lauf.BERICHTE = Path(self._tmp.name)
        self.addCleanup(setattr, lauf, "BERICHTE", self._berichte_alt)

        # spuren.json liefert fuer spur3 echte Pfade (Task 6 legt sie an) -
        # hier nur kraken_kerzen.laden faken, damit der Test ohne Netz und
        # ohne echtes kraken/wachen.json laeuft.
        import kraken_kerzen
        p = mock.patch.object(
            kraken_kerzen, "laden",
            side_effect=lambda inst, cache_dir=None: (
                [[i * 86400000, 1.0, 1.0, 1.0, 1.0, 1.0] for i in range(5)],
                1.0))
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.auswerter, "befund",
            side_effect=lambda spur, konfig, ordner: {"befunde": [],
                                                      "runden_gesamt": 0})
        p.start(); self.addCleanup(p.stop)
        p = mock.patch.object(
            lauf.digest, "erzeuge",
            side_effect=lambda *a, **k: {"empfehlungen": "", "lehren": "",
                                        "uebersprungen": "LLM-Modus aus"})
        p.start(); self.addCleanup(p.stop)

    def test_spur3_laeuft_ohne_absturz_und_nutzt_kraken_kerzen(self):
        ordner = lauf.einmal("spur3", kerzen_holen=False)
        self.assertIsNotNone(ordner)
        self.assertTrue((ordner / "bericht.md").exists())

    def test_spur1_unveraendert_nutzt_weiter_kerzen_modul(self):
        # Regression: spur1 ohne kerzen_modul-Schluessel laeuft weiter ueber
        # das oben schon gemockte lauf.kerzen (Bestandsmock in setUp der
        # Nachbarklassen) - hier nur die Modulauswahl selbst pruefen.
        self.assertIs(lauf._kerzen_modul({"name": "spur1"}), lauf.kerzen)

    def test_spur3_waehlt_kraken_kerzen_modul(self):
        import kraken_kerzen
        self.assertIs(lauf._kerzen_modul({"kerzen_modul": "kraken_kerzen"}),
                     kraken_kerzen)
```

- [ ] **Step 2: Test laufen, Fehlschlag bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_lauf.py`
Expected: FAIL — `spuren.json` hat noch kein `"spur3"`, `lauf._kerzen_modul`
existiert noch nicht.

- [ ] **Step 3: `spuren.json["spur3"]` anlegen** — gezielter Edit, nie Rewrite

Nach dem schliessenden `}` von `"spur1"` (vor dem letzten `}` der Datei)
einfuegen:
```json
  ,
  "spur3": {
    "name": "spur3",
    "_name": "Kraken/EUR",
    "journal": "../kraken/handelsjournal.csv",
    "zustand": "../kraken/zustand.json",
    "wachen": "../kraken/wachen.json",
    "berichte": "../kraken/berichte",
    "bewertung_datei": "../scanner/bewertung.py",
    "waehrung": "EUR",
    "kerzen_modul": "kraken_kerzen",
    "deckel_felder": {
      "max_pro_trade_usd": "max_pro_trade_eur",
      "max_gesamt_usd": "max_gesamt_eur"
    },
    "aenderbar": {
      "wachen.json": {
        "mindest_score": [55, 75],
        "max_volatilitaet_pa": [1.5, 2.5],
        "mindest_chance_risiko": [1.5, 2.5],
        "pflicht_stop_prozent_min": [5, 8],
        "pflicht_stop_prozent_max": [8, 15],
        "abklingzeit_tage": [2, 5],
        "watchlist": "liste"
      }
    }
  }
```
(Grenzen um den jeweils aktuellen `kraken/wachen.json`-Wert zentriert, analog
Spur 1s Struktur in `spuren.json`. **Keine** `bewertung.py`-Gewichte in
`aenderbar` — Ruling aus der Spec.)

- [ ] **Step 4: `lauf.py` — Kerzenquelle je Spur dispatchen**

Nach dem bestehenden Import-Block (`import auswerter, digest, kerzen,
ruecktest, suche, vorschlag`) einfuegen:
```python
import importlib

_KERZEN_MODULE = {"kerzen": kerzen}


def _kerzen_modul(spur):
    """Das Kerzen-Modul dieser Spur - Default 'kerzen' (OKX, Spur 1), sonst
    der in spuren.json genannte Name (z. B. 'kraken_kerzen'). Import einmal,
    danach aus dem Cache - damit ein Test, der lauf.kerzen patcht, weiter
    dieselbe Objektidentitaet trifft wie vorher."""
    name = spur.get("kerzen_modul", "kerzen")
    if name not in _KERZEN_MODULE:
        _KERZEN_MODULE[name] = importlib.import_module(name)
    return _KERZEN_MODULE[name]
```

In `einmal()` die Kerzen-Hol-Schleife auf das dispatchete Modul umstellen.
Alt:
```python
    kerzen_je_inst = {}
    for inst in watchlist:
        if kerzen_holen:
            try:
                kerzen.hole(inst, tage, KERZEN_DIR)
            except Exception as e:  # noqa: BLE001
                print("  Kerzen %s: %s - nehme Cache" % (inst, e),
                      file=sys.stderr)
        k, _alter = kerzen.laden(inst, KERZEN_DIR)
        if k:
            kerzen_je_inst[inst] = k
```
Neu:
```python
    km = _kerzen_modul(spur)
    km_dir = KERZEN_DIR if km is kerzen else WURZEL / km.__name__
    kerzen_je_inst = {}
    for inst in watchlist:
        if kerzen_holen:
            try:
                km.hole(inst, tage, km_dir)
            except Exception as e:  # noqa: BLE001
                print("  Kerzen %s: %s - nehme Cache" % (inst, e),
                      file=sys.stderr)
        k, _alter = km.laden(inst, km_dir)
        if k:
            kerzen_je_inst[inst] = k
```

Nach dem Zusammenbau von `basis` (nach `basis = suche.basis_kandidat(wachen,
bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)`) das Deckel-Mapping und
das Kostenmodell je Spur einhaengen. Alt:
```python
    befund = auswerter.befund(spur, konfig, ordner)
    basis = suche.basis_kandidat(wachen, bewertung.CHANCE_GEWICHTE,
                                 bewertung.RISIKO_GEWICHTE)
    grenzen = spur["aenderbar"]["wachen.json"]
    grenzen = {**grenzen,
               "stop_min": grenzen.get("pflicht_stop_prozent_min", [4, 8]),
               "stop_max": grenzen.get("pflicht_stop_prozent_max", [8, 15])}
    ergebnis = suche.suche(basis, kerzen_je_inst, konfig, grenzen)
```
Neu:
```python
    befund = auswerter.befund(spur, konfig, ordner)
    basis = suche.basis_kandidat(wachen, bewertung.CHANCE_GEWICHTE,
                                 bewertung.RISIKO_GEWICHTE,
                                 deckel_felder=spur.get("deckel_felder"))
    grenzen = spur["aenderbar"]["wachen.json"]
    grenzen = {**grenzen,
               "stop_min": grenzen.get("pflicht_stop_prozent_min", [4, 8]),
               "stop_max": grenzen.get("pflicht_stop_prozent_max", [8, 15])}

    modell = None
    if spur_name == "spur3":
        import kraken_modell
        fx_eur_usdc, _ = km.laden("EURUSDC", km_dir)
        fx_eur_eurc, _ = km.laden("EURCEUR", km_dir)
        modell = kraken_modell.erzeuge(wachen, fx_eur_usdc, fx_eur_eurc)
    bewerte = ((lambda k, kand, konf: ruecktest.walk_forward(k, kand, konf, modell))
              if modell else None)
    holdout_fn = ((lambda k, kand, h: ruecktest.holdout(k, kand, h, modell))
                 if modell else None)
    ergebnis = suche.suche(basis, kerzen_je_inst, konfig, grenzen,
                           bewerte=bewerte, holdout_fn=holdout_fn,
                           gewichte_durchsuchbar=konfig.get(
                               "gewichte_durchsuchbar", True))
```

(Die FX-Paarnamen `EURUSDC`/`EURCEUR` sind ein Platzhalter fuer die
tatsaechliche Kraken-Paarbezeichnung — bei der Umsetzung einmal gegen
`AssetPairs` pruefen, wie in der Spec unter "Waehrungsumrechnung" vermerkt;
schlaegt der Abruf fehl, bleiben die FX-Listen leer und
`kraken_modell.erzeuge` wirft `FXLuecke`, sobald ein nicht-EUR-Instrument
tatsaechlich eine Runde abschliesst — kein stiller Fehlschlag.)

`suche.suche()` braucht dafuer `gewichte_durchsuchbar` als durchgereichten
Parameter zum `nachbarn()`-Aufruf. In `suche.py`, Signatur:
```python
def suche(basis, kerzen_je_inst, konfig, grenzen, bewerte=None, holdout_fn=None):
```
durch:
```python
def suche(basis, kerzen_je_inst, konfig, grenzen, bewerte=None, holdout_fn=None,
          gewichte_durchsuchbar=None):
```
und am Anfang des Funktionskoerpers (vor `if bewerte is None:`) einfuegen:
```python
    if gewichte_durchsuchbar is None:
        gewichte_durchsuchbar = konfig.get("gewichte_durchsuchbar", True)
```
und den `nachbarn(bestes, grenzen)`-Aufruf im Abstieg:
```python
        for kand in nachbarn(bestes, grenzen):
```
durch:
```python
        for kand in nachbarn(bestes, grenzen, gewichte_durchsuchbar):
```

- [ ] **Step 5: Test laufen, gruen bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_lauf.py`
Expected: PASS

- [ ] **Step 6: Gesamte Suite laufen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests`
Expected: PASS (153 Tests). Besonders `test_suche_lauf.py` (ruft `suche.suche`
ohne `gewichte_durchsuchbar` — muss ueber `konfig.get(..., True)` weiter
Bestandsverhalten zeigen) und `test_lauf.py`s Bestandsklassen
(`TestLaufKeinVorschlag` usw., die `lauf.kerzen.laden` patchen — muss ueber
`_kerzen_modul` weiter dieselbe Objektidentitaet treffen).

- [ ] **Step 7: Commit**

```bash
git add Agenten/Handel/verbesserer/spuren.json Agenten/Handel/verbesserer/lauf.py Agenten/Handel/verbesserer/suche.py Agenten/Handel/verbesserer/tests/test_lauf.py
git commit
```
Botschaft: `Verbesserer: Spur 3 (Kraken-EUR) verdrahtet - spuren.json, Kerzenquelle+Modell je Spur`

---

## Danach (nicht Teil dieses Plans)

Spur 2 (XPERP: Margin, Hebel, Funding, Liquidation als dritter
Ausstiegsgrund) als eigenes Brainstorming mit eigener Spec — die
Interface-Stelle (`modell`-Parameter) existiert dann schon.
