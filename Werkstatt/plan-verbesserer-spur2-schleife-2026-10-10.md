# Verbesserer Spur 2 (XPERP) - woechentliche Optimierungsschleife - Implementierungsplan

> **Fuer agentische Ausfuehrer:** PFLICHT-SKILL: `superpowers:subagent-driven-development` (empfohlen) oder `superpowers:executing-plans`, Task fuer Task. Schritte mit Checkboxen (`- [ ]`).

**Ziel:** Eine woechentliche, rein deterministische Schleife sucht im engen Parameterraum der `xperp/wachen.json` einen Satz Werte, der die heutigen im Walk-Forward schlaegt, prueft ihn auf einem nie gesehenen Holdout und legt genau einen Vorschlag ab, den Max per Telegram `/ja` freigibt.

**Architektur:** Drei neue Module neben `xperp_ruecktest.py`: `xperp_merkmale.py` (gecachte Rangliste je 4H-Schritt, die teure Stelle), `xperp_suche.py` (Nachbarn, Sieb, Koordinatenabstieg, Holdout-Entscheidung - alles rein), `xperp_lauf.py` (Orchestrator, Berichte). Die Engine bekommt zwei kleine Schalter (`trailing_aktiv`, `werte_cache`). `anwenden.py` lernt eine Spur ohne Bewertungsdatei und eine breitere Denylist. Spur 1 und 3 (`suche.py`, `lauf.py`) bleiben unberuehrt.

**Tech Stack:** Python 3 (nur Standardbibliothek), `unittest`, PowerShell-Routine.

**Spec:** `Werkstatt/spec-verbesserer-spur2-schleife-2026-10-09.md` (Zweig `claude/verbesserer-spur2-schleife`, Commit `aa71a8ab` und neuer). Vorgaenger: Spec A `spec-verbesserer-spur2-xperp-ruecktest-2026-10-07.md`. Atlas-Quellen der Verifikations- und Wiederherstellungsentscheidungen stehen in der Spec.

## Abweichungen von der Spec (bitte vor der Ausfuehrung lesen)

Beim Code-Lesen fielen vier Punkte auf, in denen die Spec so nicht umsetzbar ist. Der Plan setzt die rechte Spalte um; Task 4 schreibt sie in die Spec.

| Spec sagt | Befund im Code | Plan setzt um |
|---|---|---|
| Suchraum enthaelt `vola_tor_pa` (Krypto, `familien.krypto`) und `min_umsatz_24h_usd` | `xperp_ruecktest.kandidaten_schritt` nimmt das Vola-Tor aus `auswahl.KATEGORIEN` (fest im Code), nicht aus der Wache; `min_umsatz_24h_usd` greift nur als Rueckfall, die Krypto-Familie traegt ein eigenes `umsatz_bezug_usd`. Beide Schluessel aendern den Rücktest also nicht. `vola_tor_pa` unter `familien` waere ausserdem ein verschachtelter Schluessel, den die Denylist (`familien`) sperrt. | Beide Schluessel entfallen. Suchraum = die 8 wirksamen Schluessel (Stop, Ziel, Einstiegsabschlag, 5 Trailing-Werte). |
| Walk-Forward mit `oos_training_tage`/`oos_test_tage`/`oos_schritt_tage` aus `konfig.json` (120/30/30) | Nach 60 Tagen Warmup bleiben ca. 90 Tage. 120 Trainingstage gibt es nicht; mit 30er-Fenstern und 20 Tagen Holdout bliebe hoechstens 1 Fenster, die Sperre verlangt 3. | Eigener Block `spur2` in `konfig.json`: 90 Tage Rueckblick, 15er-Fenster im 15er-Schritt, 20 Tage Holdout -> 4 Fenster. **Werte sind Entwurfsannahmen, Task 7 misst sie gegen den echten Cache.** |
| Fehlt ein Cache, bricht der Lauf ab; jeder Lauf endet mit einem Berichtsordner | Beides zugleich geht nur, wenn der Abbruch selbst einen Bericht schreibt | Abbruch schreibt `bericht.md` mit Grund, aber kein `commit.txt` (damit nie ein Vorschlag daraus wird), Exitcode 1. |
| Fehlt irgendein Cache, Abbruch | Ein einzelnes ausgelistetes Instrument soll die Woche nicht blockieren | Instrumente ohne vollstaendigen Cache werden ausgelassen und im Bericht benannt; unter 3 verbleibenden Instrumenten Abbruch. |

## Globale Randbedingungen

- Nur Standardbibliothek; Tests mit `unittest`, direkt ausfuehrbar. Neue Dateien LF. Das `.ps1` bekommt CRLF wie `Routinen/verbesserer.ps1`.
- Versionierte Textdateien nie per Komplett-Rewrite aendern; nur gezielter Ersatz (`xperp_ruecktest.py`, `anwenden.py`, `spuren.json`, `konfig.json` sind LF; `anwenden.py` ist ASCII - keine Umlaute einfuegen).
- Spur 1 und 3: `suche.py`, `lauf.py`, deren Tests und `vorschlag.py` werden **nicht** veraendert.
- Der Arbeitsbaum ist `.worktrees/spur2-schleife` auf Zweig `claude/verbesserer-spur2-schleife`. Kein `git stash`, nichts nach `master` schieben, gemergt wird erst per PR (siehe Wurzel-`CLAUDE.md`, Abschnitt Zweige). `git add` immer namentlich.
- Bereich `handel` (`Agenten/Handel/`) gehoert dieser Arbeit. `Agenten/Routinen/` ist frei. `MaxHirn/Wissen/` gehoert dem Bereich `wissen`: Schreiben dort vorher melden (`python Agenten/Werkzeuge/bereiche.py --aufrufer handel --pfad MaxHirn/Wissen/Verbesserer.md`, Exitcode 1 = Konflikt = als BEFUND in den Abschlussbericht).
- Testlauf: im Arbeitsbaum liegt keine venv. Python des Hauptbaums nehmen (`PY` = `<Hauptbaum>/Agenten/Handel/scanner/.venv/Scripts/python.exe`) oder ein anderes Python 3. Alle Aufrufe `cd Agenten/Handel && "$PY" -m unittest ...`.
- Basislinie vor Task 1: `cd Agenten/Handel && "$PY" -m unittest discover -s verbesserer/tests` muss gruen sein (Spec nennt 246 Tests). Weicht die Zahl ab, hier notieren und weiterarbeiten; rot = erst klaeren.

## Review Focus

Eingabeklassen, die die Spec nahelegt, aber keine Aufgabe von sich aus pruefen wuerde (jede Zeile hat ihren Test in der genannten Task):

1. **wachen.json hat sich seit dem Lauf geaendert** (z. B. Kill-Switch setzt `handel_erlaubt: false`). Ein spaeteres `/ja` darf diese Aenderung nicht mit dem alten Vorschlag ueberschreiben, sondern muss verweigern. (Task 4)
2. **Kein Kerzen-/Universums-Cache.** Erwartet: Abbruch-Bericht mit Grund, kein `commit.txt`, Exitcode 1, kein Absturz mit Traceback. (Task 5)
3. **`FundingLuecke` mitten in der Suche.** Erwartet: Abbruch-Bericht, kein Vorschlag, kein Auffuellen mit 0.0. (Task 5)
4. **Zu wenig Historie fuer die Mindestzahl Fenster.** Erwartet: Bericht „zu wenig Historie", kein Vorschlag, kein Absturz. (Task 5)
5. **Das Ersetzen im Rohtext der echten `xperp/wachen.json`** (lange `_`-Kommentarfelder, verschachtelter Block `familien` mit eigenem `vola_tor_pa`). Erwartet: nach dem Ersetzen aller 8 Suchschluessel unterscheidet sich die Datei in genau diesen 8 Schluesseln, sonst in nichts. (Task 5)

---

### Task 1: Engine-Schalter `trailing_aktiv` und `werte_cache`

**Files:**
- Modify: `Agenten/Handel/verbesserer/xperp_ruecktest.py` (`pruefe_ausstieg_1h`, `simuliere`)
- Test: `Agenten/Handel/verbesserer/tests/test_xperp_engine_schalter.py` (neu)

**Interfaces:**
- Consumes: bestehende `rt.pruefe_ausstieg_1h(p, kerze_1h, w)`, `rt.simuliere(...)`, `rt.rangliste_schritt(...)`.
- Produces: `pruefe_ausstieg_1h` zieht nur nach, wenn `w.get("trailing_aktiv", True)` wahr ist (fehlender Schluessel = an, damit alle Bestandstests unveraendert bleiben). `simuliere(..., end_ms, werte_cache=None)`: ist `werte_cache` ein dict `{stand_ms: werte}`, kommt die Rangliste je Schritt von dort (`werte_cache[stand]`, fehlender Stand = `KeyError`, laut); `None` = Verhalten wie bisher.

- [x] **Schritt 1: Fehlschlagenden Test schreiben**

Datei `Agenten/Handel/verbesserer/tests/test_xperp_engine_schalter.py`:

```python
import sys
import unittest
from pathlib import Path
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_ruecktest as rt  # noqa: E402

H = 3_600_000
VIER_H = 4 * H
IID = "AAA-USD_UM_XPERP-310620"
INSTR = {"instId": IID, "ctVal": "1", "lotSz": "1", "minSz": "1",
         "tickSz": "0.01", "lever": "20"}
UNIVERSUM = [{"instId": IID, "basis": "AAA", "kategorie": "krypto"}]
N4 = 160

W = {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
     "einstieg_atr_abschlag": 0.0, "wartungsmarge": 0.005,
     "max_margin_je_anlauf_usd": 80.0, "max_margin_gesamt_usd": 600.0,
     "max_hebel": 5, "risiko_je_anlauf_usd": 7.5, "max_offene_anlaeufe": 4,
     "gebuehr_taker": 0.0005, "trigger_modus": "signal",
     "abklingzeit_tage": 3, "freitag_stopp_utc": None, "familien": {},
     "min_umsatz_24h_usd": 3_000_000.0,
     "trailing_stop_prozent": 0.4, "trailing_trigger_r": 1.0,
     "trailing_abstand_floor_pct": 0.25, "trailing_min_hub_r": 0.25,
     "trailing_max_halten_pct": 5.0}

WERTE = [{"basis": "AAA", "instId": IID, "kategorie": "krypto",
          "punkte": {"long": 90.0, "short": 10.0, "grid": 0.0},
          "vola": 0.5, "vola_tor": 1.2, "umsatz": 5e6, "mae_long": 0.03,
          "mae_short": 0.03}]


def _long_pos():
    return {"inst": "AAA-X", "seite": "long", "einstieg": 100.0,
            "stop": 90.0, "ziel": 200.0, "liq": 80.0, "stop_id": "ruecktest",
            "kontrakte": 1}


class TestTrailingSchalter(unittest.TestCase):
    KERZE = [0, 109.0, 111.0, 108.0, 110.0, 1.0]

    def test_aus_zieht_den_stop_nicht_nach(self):
        p = _long_pos()
        rt.pruefe_ausstieg_1h(p, self.KERZE, {**W, "trailing_aktiv": False})
        self.assertEqual(p["stop"], 90.0)
        self.assertNotIn("stop_nachgezogen", p)

    def test_an_zieht_den_stop_nach(self):
        p = _long_pos()
        rt.pruefe_ausstieg_1h(p, self.KERZE, {**W, "trailing_aktiv": True})
        self.assertGreater(p["stop"], 90.0)

    def test_ohne_schluessel_wie_bisher_an(self):
        p = _long_pos()
        rt.pruefe_ausstieg_1h(p, self.KERZE, W)
        self.assertGreater(p["stop"], 90.0)


def _k4():
    return [[i * VIER_H, 100.0, 101.0, 99.0, 100.0, 1000.0] for i in range(N4)]


def _k1d():
    return [[i * 86_400_000, 100.0, 101.0, 99.0, 100.0, 1000.0]
            for i in range(60)]


def _k1h(ab_stunde, kurs_danach):
    aus = []
    for i in range(N4 * 4):
        p = 100.0 if i < ab_stunde else kurs_danach
        aus.append([i * H, 100.0, max(p, 100.0) + 0.01, min(p, 100.0) - 0.01,
                    p, 250.0])
    return aus


def _raster(satz):
    return {IID: [[h * H, satz] for h in range(0, N4 * 4, 4)]}


class TestWerteCache(unittest.TestCase):
    def setUp(self):
        self.aufrufe = []

        def fake_rangliste(*args, **kwargs):
            self.aufrufe.append(args[4])        # der Stand (zeit_ms)
            return WERTE

        for p in (
                mock.patch.object(rt.okxf, "auf_tick",
                                  side_effect=lambda i, x: x),
                mock.patch.object(rt, "rangliste_schritt",
                                  side_effect=fake_rangliste),
                mock.patch.object(
                    rt.indikatoren, "lage",
                    return_value={"signal": "long", "grund": "T",
                                  "atr": 2.0, "kurs": 100.0}),
                mock.patch.object(rt.bot, "pruefpflicht",
                                  return_value={"traegt": True,
                                                "hebel_traegt": True})):
            p.start()
            self.addCleanup(p.stop)

    def _lauf(self, **kw):
        return rt.simuliere(
            UNIVERSUM, {IID: _k4()}, {IID: _k1h(402, 115.0)},
            {IID: _k1d()}, _raster(0.0001), {IID: 5e6}, {"AAA": INSTR}, W,
            start_ms=100 * VIER_H, end_ms=104 * VIER_H, **kw)

    def test_cache_liefert_dieselben_runden_ohne_neuberechnung(self):
        ohne = self._lauf()
        self.assertEqual(len(self.aufrufe), 5)           # Schritte 100..104
        cache = {(t - 1) * VIER_H: WERTE for t in range(100, 105)}
        self.aufrufe.clear()
        mit = self._lauf(werte_cache=cache)
        self.assertEqual(mit, ohne)
        self.assertEqual(self.aufrufe, [])               # nichts neu gerechnet

    def test_fehlender_stand_im_cache_ist_laut(self):
        with self.assertRaises(KeyError):
            self._lauf(werte_cache={})


if __name__ == "__main__":
    unittest.main()
```

- [x] **Schritt 2: Test laufen lassen, Fehlschlag pruefen**

Lauf: `cd Agenten/Handel && "$PY" -m unittest verbesserer.tests.test_xperp_engine_schalter -v` (bzw. `cd Agenten/Handel/verbesserer && "$PY" tests/test_xperp_engine_schalter.py`)
Erwartet: `test_aus_zieht_den_stop_nicht_nach` FAIL (Stop wird nachgezogen), beide Cache-Tests ERROR (`unexpected keyword argument 'werte_cache'`).

- [x] **Schritt 3: Minimal implementieren**

In `xperp_ruecktest.py`, `pruefe_ausstieg_1h`: den Block

```python
    trailing_modul.erst_hoch(p, schluss)
    kand, _grund = trailing_modul.kandidat(p, schluss, w, liq=p.get("liq"))
```

ersetzen durch

```python
    if not w.get("trailing_aktiv", True):
        return None, None
    trailing_modul.erst_hoch(p, schluss)
    kand, _grund = trailing_modul.kandidat(p, schluss, w, liq=p.get("liq"))
```

In `simuliere` die Signatur

```python
def simuliere(universum, k4_je_inst, k1h_je_inst, k1d_je_inst,
              saetze_je_inst, umsatz_je_inst, instr_je_basis, w,
              start_ms, end_ms):
```

ersetzen durch

```python
def simuliere(universum, k4_je_inst, k1h_je_inst, k1d_je_inst,
              saetze_je_inst, umsatz_je_inst, instr_je_basis, w,
              start_ms, end_ms, werte_cache=None):
```

den Satz im Docstring `noch nicht bekannt. Zum Ende offene Positionen werden nicht bewertet.` um eine Zeile ergaenzen:

```python
    noch nicht bekannt. Zum Ende offene Positionen werden nicht bewertet.
    ``werte_cache`` ({stand_ms: Rangliste}) ersetzt die Rangliste je Schritt
    durch vorgerechnete Werte; ein fehlender Stand ist ein KeyError (laut).
```

und den Aufruf

```python
        werte = rangliste_schritt(universum, k4_je_inst, k1d_je_inst,
                                  umsatz_je_inst, stand,
                                  ctval_je_inst=ctval_je_inst)
```

ersetzen durch

```python
        if werte_cache is not None:
            werte = werte_cache[stand]
        else:
            werte = rangliste_schritt(universum, k4_je_inst, k1d_je_inst,
                                      umsatz_je_inst, stand,
                                      ctval_je_inst=ctval_je_inst)
```

- [x] **Schritt 4: Test laufen lassen, Erfolg pruefen**

Lauf wie Schritt 2. Erwartet: alle 5 Tests PASS. Danach die Engine-Bestandstests: `cd Agenten/Handel && "$PY" -m unittest discover -s verbesserer/tests -p "test_xperp_ruecktest*.py"` -> alle gruen.

- [x] **Schritt 5: Commit**

```bash
git add Agenten/Handel/verbesserer/xperp_ruecktest.py Agenten/Handel/verbesserer/tests/test_xperp_engine_schalter.py
git commit -m "xperp-ruecktest: trailing_aktiv-Schalter und werte_cache fuer simuliere

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Merkmals-Cache `xperp_merkmale.py`

**Files:**
- Create: `Agenten/Handel/verbesserer/xperp_merkmale.py`
- Test: `Agenten/Handel/verbesserer/tests/test_xperp_merkmale.py` (neu)

**Interfaces:**
- Consumes: `rt.rangliste_schritt(universum, k4_je_inst, k1d_je_inst, umsatz_je_inst, zeit_ms, ctval_je_inst=...)`, `rt.SCHRITT_MS`.
- Produces:
  - `staende(von_ms: int, bis_ms: int) -> list[int]` - Entscheidungsstaende `t - 4H` fuer jeden 4H-Schritt `t` in `[von_ms, bis_ms]`.
  - `ctval_je_inst(universum, instr_je_basis) -> dict` - `{instId: float(ctVal)}` wie in `simuliere`.
  - `daten_hash(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste) -> str`
  - `baue(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste) -> dict[int, list]`
  - `speichern(pfad, hash_, matrix)`, `laden(pfad, hash_) -> dict[int, list] | None`
  - `hole_oder_baue(pfad, universum, k4_je_inst, k1d_je_inst, ctval, stand_liste) -> (matrix, aus_cache: bool)`

- [x] **Schritt 1: Fehlschlagenden Test schreiben**

Datei `Agenten/Handel/verbesserer/tests/test_xperp_merkmale.py`:

```python
import json
import sys
import unittest
from pathlib import Path
from tempfile import mkdtemp
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_merkmale as xm  # noqa: E402
import xperp_ruecktest as rt  # noqa: E402

S = rt.SCHRITT_MS
UNI = [{"instId": "A-X", "basis": "A", "kategorie": "krypto"}]
K4 = {"A-X": [[i * S, 1.0, 2.0, 0.5, 1.5, 10.0] for i in range(10)]}
K1D = {"A-X": [[i * 86_400_000, 1.0, 2.0, 0.5, 1.5, 10.0] for i in range(5)]}
CT = {"A-X": 1.0}
WERT = [{"instId": "A-X", "punkte": {"long": 1.0, "short": 2.0},
         "mae_long": 0.03}]


class TestStaende(unittest.TestCase):
    def test_raster_ist_t_minus_vier_stunden(self):
        self.assertEqual(xm.staende(10 * S, 12 * S),
                         [9 * S, 10 * S, 11 * S])

    def test_ein_schritt(self):
        self.assertEqual(xm.staende(5 * S, 5 * S), [4 * S])


class TestHash(unittest.TestCase):
    def test_gleiche_daten_gleicher_hash(self):
        a = xm.daten_hash(UNI, K4, K1D, CT, [1, 2])
        b = xm.daten_hash(UNI, K4, K1D, CT, [1, 2])
        self.assertEqual(a, b)

    def test_neue_kerze_andert_den_hash(self):
        k4 = {"A-X": K4["A-X"] + [[10 * S, 1.0, 2.0, 0.5, 1.5, 10.0]]}
        self.assertNotEqual(xm.daten_hash(UNI, K4, K1D, CT, [1, 2]),
                            xm.daten_hash(UNI, k4, K1D, CT, [1, 2]))

    def test_anderer_schlusskurs_andert_den_hash(self):
        k4 = {"A-X": K4["A-X"][:-1] + [[9 * S, 1.0, 2.0, 0.5, 9.9, 10.0]]}
        self.assertNotEqual(xm.daten_hash(UNI, K4, K1D, CT, [1, 2]),
                            xm.daten_hash(UNI, k4, K1D, CT, [1, 2]))

    def test_anderes_raster_andert_den_hash(self):
        self.assertNotEqual(xm.daten_hash(UNI, K4, K1D, CT, [1, 2]),
                            xm.daten_hash(UNI, K4, K1D, CT, [1, 2, 3]))

    def test_leeres_instrument_stuerzt_nicht(self):
        xm.daten_hash(UNI, {"A-X": []}, {"A-X": []}, CT, [1])


class TestSpeicher(unittest.TestCase):
    def setUp(self):
        self.pfad = Path(mkdtemp()) / "m.json"

    def test_rundreise_mit_ganzzahligen_schluesseln(self):
        xm.speichern(self.pfad, "h1", {5: WERT, 9: WERT})
        self.assertEqual(xm.laden(self.pfad, "h1"), {5: WERT, 9: WERT})

    def test_falscher_hash_ist_ein_fehlschlag(self):
        xm.speichern(self.pfad, "h1", {5: WERT})
        self.assertIsNone(xm.laden(self.pfad, "h2"))

    def test_fehlende_datei(self):
        self.assertIsNone(xm.laden(self.pfad, "h1"))

    def test_kaputte_datei_ist_ein_fehlschlag_kein_absturz(self):
        self.pfad.write_text("{kaputt", "utf-8")
        self.assertIsNone(xm.laden(self.pfad, "h1"))


class TestHoleOderBaue(unittest.TestCase):
    def setUp(self):
        self.pfad = Path(mkdtemp()) / "m.json"
        self.aufrufe = []

        def fake(universum, k4, k1d, umsatz, stand, ctval_je_inst=None):
            self.aufrufe.append(stand)
            return WERT

        p = mock.patch.object(rt, "rangliste_schritt", side_effect=fake)
        p.start()
        self.addCleanup(p.stop)

    def test_zweiter_aufruf_kommt_aus_dem_cache(self):
        staende = [2 * S, 3 * S]
        m1, aus1 = xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT, staende)
        self.assertFalse(aus1)
        self.assertEqual(self.aufrufe, staende)
        self.aufrufe.clear()
        m2, aus2 = xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT, staende)
        self.assertTrue(aus2)
        self.assertEqual(self.aufrufe, [])
        self.assertEqual(m1, m2)

    def test_neue_daten_bauen_neu(self):
        xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT, [2 * S])
        self.aufrufe.clear()
        k4 = {"A-X": K4["A-X"] + [[10 * S, 1.0, 2.0, 0.5, 1.5, 10.0]]}
        _, aus = xm.hole_oder_baue(self.pfad, UNI, k4, K1D, CT, [2 * S])
        self.assertFalse(aus)
        self.assertEqual(self.aufrufe, [2 * S])

    def test_cache_ohne_alle_staende_wird_neu_gebaut(self):
        xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT, [2 * S])
        self.aufrufe.clear()
        _, aus = xm.hole_oder_baue(self.pfad, UNI, K4, K1D, CT,
                                   [2 * S, 3 * S])
        self.assertFalse(aus)


class TestCtval(unittest.TestCase):
    def test_ctval_je_instrument(self):
        self.assertEqual(
            xm.ctval_je_inst(UNI, {"A": {"ctVal": "0.1"}}), {"A-X": 0.1})

    def test_instrument_ohne_stammdaten_wird_ausgelassen(self):
        self.assertEqual(xm.ctval_je_inst(UNI, {}), {})


if __name__ == "__main__":
    unittest.main()
```

- [x] **Schritt 2: Test laufen lassen, Fehlschlag pruefen**

Lauf: `cd Agenten/Handel/verbesserer && "$PY" tests/test_xperp_merkmale.py`
Erwartet: `ModuleNotFoundError: No module named 'xperp_merkmale'`.

- [x] **Schritt 3: Modul schreiben**

Datei `Agenten/Handel/verbesserer/xperp_merkmale.py`:

```python
"""Merkmals-Cache fuer die Spur-2-Schleife.

Die Rangliste je 4H-Schritt (Kennzahlen, Lage, Hebel-Deckel-Merkmale) haengt
nicht von der Wache ab, nur von den Kerzen. Sie ist die teure Stelle eines
Rücktests (20-35 min) und wird deshalb einmal je Datenstand gerechnet und mit
einem Hash ueber die Eingangsdaten abgelegt. Aendern sich Kerzen, Universum
oder Raster, passt der Hash nicht mehr und der Cache wird neu gebaut - nie
stillschweigend mit altem Stand weitergearbeitet.

Nur Standardbibliothek.
"""

import hashlib
import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
for _p in (WURZEL, WURZEL.parent / "xperp"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import xperp_ruecktest as rt  # noqa: E402


def staende(von_ms, bis_ms):
    """Alle Entscheidungsstaende (t - 4H) fuer jeden 4H-Schritt t in
    [von_ms, bis_ms]. simuliere() entscheidet bei t nur mit Kerzen bis t - 4H.
    """
    return list(range(von_ms - rt.SCHRITT_MS, bis_ms - rt.SCHRITT_MS + 1,
                      rt.SCHRITT_MS))


def ctval_je_inst(universum, instr_je_basis):
    """Kontraktwert je Instrument - dieselbe Zeile wie in simuliere()."""
    return {x["instId"]: float(instr_je_basis[x["basis"]]["ctVal"])
            for x in universum if x["basis"] in instr_je_basis}


def _reihe(kerzen):
    return ([len(kerzen), kerzen[0][0], kerzen[-1][0], kerzen[-1][4]]
            if kerzen else [0])


def daten_hash(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste):
    """Hash ueber alles, wovon die Matrix abhaengt: Universum, je Instrument
    Anzahl/erste/letzte Zeit/letzter Schlusskurs der 4H- und 1D-Reihe,
    Kontraktwerte und das Stand-Raster."""
    kopf = {
        "universum": [[x["instId"], x["basis"], x["kategorie"]]
                      for x in universum],
        "k4": {i: _reihe(k4_je_inst[i]) for i in sorted(k4_je_inst)},
        "k1d": {i: _reihe(k1d_je_inst[i]) for i in sorted(k1d_je_inst)},
        "ctval": {i: ctval[i] for i in sorted(ctval)},
        "staende": ([stand_liste[0], stand_liste[-1], len(stand_liste)]
                    if stand_liste else []),
    }
    return hashlib.sha256(
        json.dumps(kopf, sort_keys=True).encode("utf-8")).hexdigest()


def baue(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste):
    """{stand_ms: Rangliste} - genau das, was simuliere(werte_cache=...)
    erwartet."""
    return {s: rt.rangliste_schritt(universum, k4_je_inst, k1d_je_inst, {}, s,
                                    ctval_je_inst=ctval)
            for s in stand_liste}


def speichern(pfad, hash_, matrix):
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps(
        {"hash": hash_, "werte": {str(s): w for s, w in matrix.items()}}),
        "utf-8")
    tmp.replace(pfad)


def laden(pfad, hash_):
    """Die Matrix, wenn Datei und Hash passen - sonst None."""
    pfad = Path(pfad)
    if not pfad.is_file():
        return None
    try:
        d = json.loads(pfad.read_text("utf-8"))
        if d.get("hash") != hash_:
            return None
        return {int(s): w for s, w in d["werte"].items()}
    except (OSError, ValueError, KeyError, AttributeError):
        return None


def hole_oder_baue(pfad, universum, k4_je_inst, k1d_je_inst, ctval,
                   stand_liste):
    """(matrix, aus_cache). Aus dem Cache nur, wenn der Hash passt UND alle
    gebrauchten Staende enthalten sind."""
    h = daten_hash(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste)
    matrix = laden(pfad, h)
    if matrix is not None and set(stand_liste) <= set(matrix):
        return matrix, True
    matrix = baue(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste)
    speichern(pfad, h, matrix)
    return matrix, False
```

- [x] **Schritt 4: Test laufen lassen, Erfolg pruefen**

Lauf wie Schritt 2. Erwartet: alle Tests PASS.

- [x] **Schritt 5: Commit**

```bash
git add Agenten/Handel/verbesserer/xperp_merkmale.py Agenten/Handel/verbesserer/tests/test_xperp_merkmale.py
git commit -m "verbesserer: xperp_merkmale - gehashter Merkmals-Cache fuer die Spur-2-Schleife

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Suche, Sieb und Holdout-Entscheidung `xperp_suche.py`

**Files:**
- Create: `Agenten/Handel/verbesserer/xperp_suche.py`
- Test: `Agenten/Handel/verbesserer/tests/test_xperp_suche.py` (neu)

**Interfaces:**
- Consumes: `rt.bericht(runden)` (Felder `anzahl_runden`, `gv_gesamt`, `liquidationsanteil`, `groesster_ruecklauf_usd`).
- Produces (alle rein, ohne Netz und Dateien):
  - `SCHRITT: dict[str, float]` - Schrittweite je Suchschluessel (8 Schluessel).
  - `basis_werte(wachen: dict) -> dict` - die 8 Suchschluessel aus der Wache; `KeyError`, wenn einer fehlt.
  - `nachbarn(werte, grenzen) -> list[dict]` - ein Schluessel, ein Schritt, innerhalb `grenzen[key] = [lo, hi]`, `ziel/stop >= 1.5`.
  - `fenster_grenzen(ende_ms, konf) -> (list[(von, bis)], (holdout_von, holdout_bis))`.
  - `kennzahlen(runden) -> {"n","gv","je_runde","liquidationsanteil","ruecklauf"}`.
  - `bewerte_fenster(simulieren, w, fenster) -> {"fenster": [kennzahlen...], "gesamt": kennzahlen}`; `simulieren(w, von_ms, bis_ms) -> runden`.
  - `sieb_regeln(basis_ev, kand_ev, konf) -> list[{"regel","text","ist","soll","ok"}]` (Regeln a-e); `sieb(...) -> Liste der nicht bestandenen`.
  - `abstieg(basis, bewerte, grenzen, budget) -> {"basis_ev","bestes","bestes_ev","auswertungen"}`; `bewerte(werte) -> ev`.
  - `entscheide(basis, bewerte, holdout, grenzen, konf) -> dict` mit `kandidat`, `fast_kandidat`, `grund`, `regeln`, `basis_ev`, `kandidat_ev`, `holdout_basis`, `holdout_kandidat`, `auswertungen`, `basis_werte`; `holdout(werte) -> kennzahlen`.

- [x] **Schritt 1: Fehlschlagenden Test schreiben**

Datei `Agenten/Handel/verbesserer/tests/test_xperp_suche.py`:

```python
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_suche as xs  # noqa: E402

TAG = 86_400_000
GRENZEN = {
    "stop_atr_faktor": [1.0, 2.5], "ziel_atr_faktor": [2.0, 4.5],
    "einstieg_atr_abschlag": [0.0, 0.5], "trailing_trigger_r": [0.5, 2.0],
    "trailing_stop_prozent": [0.2, 1.0],
    "trailing_abstand_floor_pct": [0.15, 0.6],
    "trailing_min_hub_r": [0.1, 0.6], "trailing_max_halten_pct": [3.0, 8.0],
}
BASIS = {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
         "einstieg_atr_abschlag": 0.25, "trailing_trigger_r": 1.0,
         "trailing_stop_prozent": 0.4, "trailing_abstand_floor_pct": 0.25,
         "trailing_min_hub_r": 0.25, "trailing_max_halten_pct": 5.0}
KONF = {"such_budget": 60, "such_tage": 90, "test_tage": 15,
        "schritt_tage": 15, "holdout_tage": 20, "holdout_min_runden": 6,
        "overfit_min_fenster": 3, "overfit_min_runden": 20}


def _kz(je_runde, n=30, liq=0.0, ruecklauf=10.0):
    return {"n": n, "gv": je_runde * n, "je_runde": je_runde,
            "liquidationsanteil": liq, "ruecklauf": ruecklauf}


def _ev(fenster_je_runde, gesamt_je_runde=None, **kw):
    gesamt = (gesamt_je_runde if gesamt_je_runde is not None
              else sum(fenster_je_runde) / len(fenster_je_runde))
    return {"fenster": [_kz(x) for x in fenster_je_runde],
            "gesamt": _kz(gesamt, **kw)}


class TestBasisWerte(unittest.TestCase):
    def test_zieht_die_acht_schluessel(self):
        w = {**BASIS, "max_hebel": 5, "handel_erlaubt": True}
        self.assertEqual(xs.basis_werte(w), BASIS)

    def test_fehlender_schluessel_ist_laut(self):
        w = dict(BASIS)
        del w["trailing_min_hub_r"]
        with self.assertRaises(KeyError):
            xs.basis_werte(w)


class TestNachbarn(unittest.TestCase):
    def test_jeder_nachbar_aendert_genau_einen_schluessel_um_einen_schritt(self):
        for n in xs.nachbarn(BASIS, GRENZEN):
            diff = [k for k in BASIS if n[k] != BASIS[k]]
            self.assertEqual(len(diff), 1)
            k = diff[0]
            self.assertAlmostEqual(abs(n[k] - BASIS[k]), xs.SCHRITT[k])

    def test_alle_nachbarn_liegen_in_den_grenzen(self):
        for n in xs.nachbarn(BASIS, GRENZEN):
            for k, (lo, hi) in GRENZEN.items():
                self.assertGreaterEqual(n[k], lo)
                self.assertLessEqual(n[k], hi)

    def test_am_rand_gibt_es_nur_eine_richtung(self):
        rand = {**BASIS, "stop_atr_faktor": 1.0, "ziel_atr_faktor": 2.5}
        stops = [n["stop_atr_faktor"] for n in xs.nachbarn(rand, GRENZEN)
                 if n["stop_atr_faktor"] != 1.0]
        self.assertEqual(stops, [1.25])

    def test_zusatzbedingung_ziel_durch_stop_mindestens_1_5(self):
        eng = {**BASIS, "stop_atr_faktor": 2.0, "ziel_atr_faktor": 3.0}
        for n in xs.nachbarn(eng, GRENZEN):
            self.assertGreaterEqual(
                n["ziel_atr_faktor"] / n["stop_atr_faktor"], 1.5 - 1e-9)
        # stop 2.25 -> 3.0/2.25 = 1.33 -> darf nicht vorkommen
        self.assertNotIn(2.25, [n["stop_atr_faktor"]
                                for n in xs.nachbarn(eng, GRENZEN)])

    def test_keine_gleitkommadrift(self):
        werte = dict(BASIS)
        for _ in range(5):
            werte = [n for n in xs.nachbarn(werte, GRENZEN)
                     if n["einstieg_atr_abschlag"]
                     > werte["einstieg_atr_abschlag"]][0]
        self.assertEqual(werte["einstieg_atr_abschlag"], 0.5)


class TestFenster(unittest.TestCase):
    def test_vier_fenster_und_holdout(self):
        ende = 1000 * TAG
        fenster, holdout = xs.fenster_grenzen(ende, KONF)
        self.assertEqual(len(fenster), 4)
        self.assertEqual(fenster[0], (910 * TAG, 925 * TAG))
        self.assertEqual(fenster[-1], (955 * TAG, 970 * TAG))
        self.assertEqual(holdout, (980 * TAG, 1000 * TAG))

    def test_fenster_beruehren_den_holdout_nicht(self):
        fenster, holdout = xs.fenster_grenzen(1000 * TAG, KONF)
        self.assertLessEqual(fenster[-1][1], holdout[0])

    def test_zu_wenig_rueckblick_gibt_keine_fenster(self):
        fenster, _ = xs.fenster_grenzen(
            1000 * TAG, {**KONF, "such_tage": 30})
        self.assertEqual(fenster, [])


class TestKennzahlen(unittest.TestCase):
    def _runde(self, ts, gv, grund="ziel"):
        return {"geschlossen_ts": ts, "gv": gv, "grund": grund,
                "kategorie": "krypto", "funding_summe": 0.0}

    def test_leer(self):
        self.assertEqual(xs.kennzahlen([]), _kz(0.0, n=0, ruecklauf=0.0))

    def test_werte(self):
        k = xs.kennzahlen([self._runde(1, 10.0),
                           self._runde(2, -4.0, "LIQUIDATION")])
        self.assertEqual(k["n"], 2)
        self.assertAlmostEqual(k["je_runde"], 3.0)
        self.assertAlmostEqual(k["liquidationsanteil"], 0.5)
        self.assertAlmostEqual(k["ruecklauf"], 4.0)

    def test_bewerte_fenster_ruft_je_fenster_und_fasst_zusammen(self):
        aufrufe = []

        def sim(w, von, bis):
            aufrufe.append((von, bis))
            return [self._runde(bis, 2.0)]

        ev = xs.bewerte_fenster(sim, {"x": 1}, [(0, 10), (10, 20)])
        self.assertEqual(aufrufe, [(0, 10), (10, 20)])
        self.assertEqual(len(ev["fenster"]), 2)
        self.assertEqual(ev["gesamt"]["n"], 2)
        self.assertAlmostEqual(ev["gesamt"]["je_runde"], 2.0)


class TestSieb(unittest.TestCase):
    def _regeln(self, basis, kand):
        return {r["regel"]: r for r in xs.sieb_regeln(basis, kand, KONF)}

    def setUp(self):
        self.basis = _ev([1.0, 1.0, 1.0, 1.0], liq=0.1, ruecklauf=100.0)

    def test_alles_bestanden(self):
        kand = _ev([2.0, 2.0, 2.0, 0.5], liq=0.1, ruecklauf=105.0)
        self.assertEqual(xs.sieb(self.basis, kand, KONF), [])

    def test_a_aggregat_nicht_besser(self):
        kand = _ev([2.0, 2.0, 2.0, 0.0], gesamt_je_runde=1.0, liq=0.1,
                   ruecklauf=100.0)
        self.assertFalse(self._regeln(self.basis, kand)["a"]["ok"])

    def test_b_nur_die_haelfte_der_fenster_reicht_nicht(self):
        kand = _ev([2.0, 2.0, 0.5, 0.5], gesamt_je_runde=1.5, liq=0.1,
                   ruecklauf=100.0)
        self.assertFalse(self._regeln(self.basis, kand)["b"]["ok"])

    def test_b_mindestens_overfit_min_fenster(self):
        basis = _ev([1.0, 1.0], liq=0.1, ruecklauf=100.0)
        kand = _ev([2.0, 2.0], liq=0.1, ruecklauf=100.0)   # 2 > 1, aber < 3
        self.assertFalse(self._regeln(basis, kand)["b"]["ok"])

    def test_c_zu_wenige_runden(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        kand["gesamt"]["n"] = 19
        self.assertFalse(self._regeln(self.basis, kand)["c"]["ok"])

    def test_d_mehr_liquidationen_als_die_basis(self):
        kand = _ev([2.0] * 4, liq=0.2, ruecklauf=100.0)
        self.assertFalse(self._regeln(self.basis, kand)["d"]["ok"])

    def test_e_ruecklauf_mehr_als_zehn_prozent_ueber_basis(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=110.5)
        self.assertFalse(self._regeln(self.basis, kand)["e"]["ok"])

    def test_e_basis_ohne_ruecklauf_und_kandidat_mit(self):
        basis = _ev([1.0] * 4, liq=0.1, ruecklauf=0.0)
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=1.0)
        self.assertFalse(self._regeln(basis, kand)["e"]["ok"])

    def test_jede_regel_traegt_ist_und_soll_fuer_den_bericht(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        regeln = xs.sieb_regeln(self.basis, kand, KONF)
        self.assertEqual([r["regel"] for r in regeln],
                         ["a", "b", "c", "d", "e"])
        for r in regeln:
            self.assertTrue(r["ist"] and r["soll"] and r["text"])


class TestAbstieg(unittest.TestCase):
    @staticmethod
    def _bewerter(zaehler):
        def bewerte(werte):
            zaehler.append(dict(werte))
            je = -abs(werte["stop_atr_faktor"] - 1.0)
            return _ev([je] * 4)
        return bewerte

    def test_steigt_zum_besseren_stop_ab(self):
        z = []
        erg = xs.abstieg(BASIS, self._bewerter(z), GRENZEN, 60)
        self.assertEqual(erg["bestes"]["stop_atr_faktor"], 1.0)
        self.assertGreater(erg["bestes_ev"]["gesamt"]["je_runde"],
                           erg["basis_ev"]["gesamt"]["je_runde"])

    def test_budget_deckelt_die_auswertungen(self):
        z = []
        erg = xs.abstieg(BASIS, self._bewerter(z), GRENZEN, 5)
        self.assertLessEqual(erg["auswertungen"], 5)
        self.assertEqual(len(z), erg["auswertungen"])

    def test_kein_satz_wird_zweimal_bewertet(self):
        z = []
        xs.abstieg(BASIS, self._bewerter(z), GRENZEN, 200)
        gesehen = [tuple(sorted(w.items())) for w in z]
        self.assertEqual(len(gesehen), len(set(gesehen)))

    def test_basis_bleibt_wenn_nichts_besser_ist(self):
        def bewerte(werte):
            return _ev([1.0 if werte == BASIS else 0.0] * 4)
        erg = xs.abstieg(BASIS, bewerte, GRENZEN, 60)
        self.assertEqual(erg["bestes"], BASIS)


class TestEntscheide(unittest.TestCase):
    def _lauf(self, kand_ev, holdout_basis, holdout_kand):
        besser = {**BASIS, "stop_atr_faktor": 1.25}

        def bewerte(werte):
            return kand_ev if werte == besser else _ev(
                [1.0] * 4, liq=0.1, ruecklauf=100.0)

        def holdout(werte):
            return holdout_kand if werte == besser else holdout_basis

        # Nachbarn von BASIS: nur 'besser' liefert mehr als die Basis.
        return xs.entscheide(BASIS, bewerte, holdout, GRENZEN, KONF), besser

    def test_kein_besserer_kandidat(self):
        def bewerte(werte):
            return _ev([1.0] * 4)
        erg = xs.entscheide(BASIS, bewerte, lambda w: _kz(1.0), GRENZEN, KONF)
        self.assertIsNone(erg["kandidat"])
        self.assertIsNone(erg["fast_kandidat"])
        self.assertEqual(erg["grund"], "kein besserer Kandidat gefunden")
        self.assertIsNone(erg["holdout_basis"])

    def test_sieb_nicht_bestanden_fasst_den_holdout_nicht_an(self):
        # Aggregat besser, aber nur 2 von 4 Fenstern.
        kand = _ev([3.0, 3.0, 0.5, 0.5], gesamt_je_runde=1.75, liq=0.1,
                   ruecklauf=100.0)
        erg, _ = self._lauf(kand, _kz(1.0), _kz(2.0))
        self.assertIsNone(erg["kandidat"])
        self.assertTrue(erg["grund"].startswith("Sieb nicht bestanden"))
        self.assertIn("b", erg["grund"])
        self.assertIsNone(erg["holdout_basis"])
        self.assertTrue(any(not r["ok"] for r in erg["regeln"]))

    def test_holdout_nicht_bestanden_gibt_fast_kandidat(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        erg, besser = self._lauf(kand, _kz(1.0, n=10), _kz(0.5, n=10))
        self.assertIsNone(erg["kandidat"])
        self.assertEqual(erg["fast_kandidat"], besser)
        self.assertEqual(erg["grund"], "Holdout nicht bestanden")
        self.assertIsNotNone(erg["holdout_basis"])

    def test_holdout_mit_zu_wenigen_runden_scheitert(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        erg, _ = self._lauf(kand, _kz(1.0, n=10), _kz(5.0, n=5))   # < 6
        self.assertIsNone(erg["kandidat"])
        self.assertEqual(erg["grund"], "Holdout nicht bestanden")

    def test_alles_bestanden_gibt_den_vorschlag(self):
        kand = _ev([2.0] * 4, liq=0.1, ruecklauf=100.0)
        erg, besser = self._lauf(kand, _kz(1.0, n=10), _kz(2.0, n=10))
        self.assertEqual(erg["kandidat"], besser)
        self.assertIsNone(erg["fast_kandidat"])
        self.assertTrue(erg["grund"].startswith("Vorschlag"))
        self.assertEqual(erg["basis_werte"], BASIS)


if __name__ == "__main__":
    unittest.main()
```

Hinweis fuer den Ausfuehrer: In `TestEntscheide._lauf` ist `besser` (Stop 1.25) der einzige Nachbar, der das Aggregat der Basis (1.0) uebertrifft; alle anderen Nachbarn liefern die Basiswerte (1.0) und gewinnen nicht (strikt groesser verlangt).

- [x] **Schritt 2: Test laufen lassen, Fehlschlag pruefen**

Lauf: `cd Agenten/Handel/verbesserer && "$PY" tests/test_xperp_suche.py`
Erwartet: `ModuleNotFoundError: No module named 'xperp_suche'`.

- [x] **Schritt 3: Modul schreiben**

Datei `Agenten/Handel/verbesserer/xperp_suche.py`:

```python
"""Suchraum, Nachbarn, Sieb und Koordinatenabstieg fuer Spur 2 (XPERP).

Alles hier ist rein: keine Dateien, kein Netz. Die Grenzen je Schluessel kommen
aus der Whitelist in spuren.json (eine Wahrheit); hier stehen nur die
Schrittweiten. Die Verifikation ist bewusst von der Suche getrennt: das Sieb
und der Holdout sind eigene Stufen, die der Abstieg nie sieht (Spec,
Abschnitt 'Verifikation und Freigabe').

Nur Standardbibliothek (ausser xperp_ruecktest.bericht fuer die Kennzahlen).
"""

import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
for _p in (WURZEL, WURZEL.parent / "xperp"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import xperp_ruecktest as rt  # noqa: E402

TAG_MS = 86_400_000
MIN_ZIEL_DURCH_STOP = 1.5
RUECKLAUF_TOLERANZ = 1.10           # Regel e: hoechstens 10 % ueber der Basis

# Schrittweite je Suchschluessel. Ein Nachbar bewegt genau einen Schluessel
# um genau einen Schritt. vola_tor_pa und min_umsatz_24h_usd fehlen absichtlich:
# der Ruecktest liest sie nicht (siehe Plan, Abweichungen von der Spec).
SCHRITT = {
    "stop_atr_faktor": 0.25,
    "ziel_atr_faktor": 0.25,
    "einstieg_atr_abschlag": 0.05,
    "trailing_trigger_r": 0.25,
    "trailing_stop_prozent": 0.1,
    "trailing_abstand_floor_pct": 0.05,
    "trailing_min_hub_r": 0.05,
    "trailing_max_halten_pct": 1.0,
}


def basis_werte(wachen):
    """Die Suchschluessel aus der Wache; fehlt einer, ist das ein KeyError."""
    return {k: wachen[k] for k in SCHRITT}


def nachbarn(werte, grenzen):
    """Alle Saetze, die sich in genau einem Schluessel um genau einen Schritt
    unterscheiden, innerhalb ``grenzen[key] = [lo, hi]`` und mit
    ziel/stop >= 1.5."""
    aus = []
    for key in sorted(SCHRITT):
        lo, hi = grenzen[key]
        for vz in (-1, 1):
            neu = round(werte[key] + vz * SCHRITT[key], 4)
            if neu < lo - 1e-9 or neu > hi + 1e-9:
                continue
            kand = {**werte, key: neu}
            if (kand["ziel_atr_faktor"] / kand["stop_atr_faktor"]
                    < MIN_ZIEL_DURCH_STOP - 1e-9):
                continue
            aus.append(kand)
    return aus


def fenster_grenzen(ende_ms, konf):
    """([(von, bis), ...], (holdout_von, holdout_bis)).

    Der Holdout sind die letzten ``holdout_tage`` Tage; die Testfenster decken
    ``such_tage`` Rueckblick ab, enden vor dem Holdout und ruecken um
    ``schritt_tage`` vor. Zu wenig Rueckblick -> leere Fensterliste."""
    holdout_von = ende_ms - konf["holdout_tage"] * TAG_MS
    fenster = []
    von = ende_ms - konf["such_tage"] * TAG_MS
    while von + konf["test_tage"] * TAG_MS <= holdout_von:
        fenster.append((von, von + konf["test_tage"] * TAG_MS))
        von += konf["schritt_tage"] * TAG_MS
    return fenster, (holdout_von, ende_ms)


def kennzahlen(runden):
    b = rt.bericht(runden)
    n = b["anzahl_runden"]
    return {"n": n, "gv": b["gv_gesamt"],
            "je_runde": (b["gv_gesamt"] / n) if n else 0.0,
            "liquidationsanteil": b["liquidationsanteil"],
            "ruecklauf": b["groesster_ruecklauf_usd"]}


def bewerte_fenster(simulieren, w, fenster):
    """Auswertung eines Satzes: Kennzahlen je Fenster und im Aggregat.
    ``simulieren(w, von_ms, bis_ms)`` gibt die Runden des Fensters zurueck."""
    je_fenster, alle = [], []
    for von, bis in fenster:
        runden = simulieren(w, von, bis)
        je_fenster.append(kennzahlen(runden))
        alle.extend(runden)
    return {"fenster": je_fenster, "gesamt": kennzahlen(alle)}


def sieb_regeln(basis_ev, kand_ev, konf):
    """Die fuenf Siebregeln a-e als benannte Ausgaben. Urteilt nicht ueber
    das Ganze und korrigiert nichts."""
    b, k = basis_ev["gesamt"], kand_ev["gesamt"]
    paare = list(zip(kand_ev["fenster"], basis_ev["fenster"]))
    anz = sum(1 for kf, bf in paare if kf["je_runde"] > bf["je_runde"])
    fenster = len(paare)
    mehrheit = fenster // 2
    min_fenster = konf["overfit_min_fenster"]
    ruecklauf_grenze = b["ruecklauf"] * RUECKLAUF_TOLERANZ
    return [
        {"regel": "a", "text": "Aggregat schlaegt die Basis",
         "ist": "%.4f" % k["je_runde"], "soll": "> %.4f" % b["je_runde"],
         "ok": k["je_runde"] > b["je_runde"]},
        {"regel": "b", "text": "Mehrheit der Fenster besser",
         "ist": "%d von %d" % (anz, fenster),
         "soll": "> %d und >= %d" % (mehrheit, min_fenster),
         "ok": anz > mehrheit and anz >= min_fenster},
        {"regel": "c", "text": "genug Runden",
         "ist": str(k["n"]), "soll": ">= %d" % konf["overfit_min_runden"],
         "ok": k["n"] >= konf["overfit_min_runden"]},
        {"regel": "d", "text": "Liquidationsanteil nicht ueber der Basis",
         "ist": "%.1f %%" % (100 * k["liquidationsanteil"]),
         "soll": "<= %.1f %%" % (100 * b["liquidationsanteil"]),
         "ok": k["liquidationsanteil"] <= b["liquidationsanteil"]},
        {"regel": "e", "text": "groesster Ruecklauf hoechstens 10 % ueber Basis",
         "ist": "%.2f" % k["ruecklauf"], "soll": "<= %.2f" % ruecklauf_grenze,
         "ok": k["ruecklauf"] <= ruecklauf_grenze},
    ]


def sieb(basis_ev, kand_ev, konf):
    """Die nicht bestandenen Regeln; leer = Sieb bestanden."""
    return [r for r in sieb_regeln(basis_ev, kand_ev, konf) if not r["ok"]]


def _schluessel(werte):
    return tuple(sorted(werte.items()))


def abstieg(basis, bewerte, grenzen, budget):
    """Koordinatenabstieg von ``basis``. ``bewerte(werte) -> Auswertung``.
    Wie Spur 1: die Basis zaehlt in das Budget; ein schon bewerteter Satz
    wird nicht noch einmal gerechnet und kostet kein Budget."""
    gesehen = {}

    def auswerten(werte):
        k = _schluessel(werte)
        if k not in gesehen:
            gesehen[k] = bewerte(werte)
        return gesehen[k]

    basis_ev = auswerten(basis)
    bestes, bestes_ev = basis, basis_ev
    while len(gesehen) < budget:
        bester = bester_ev = None
        for kand in nachbarn(bestes, grenzen):
            if _schluessel(kand) not in gesehen and len(gesehen) >= budget:
                break
            ev = auswerten(kand)
            if (bester_ev is None
                    or ev["gesamt"]["je_runde"]
                    > bester_ev["gesamt"]["je_runde"]):
                bester, bester_ev = kand, ev
        if (bester_ev is None or not bester_ev["gesamt"]["je_runde"]
                > bestes_ev["gesamt"]["je_runde"]):
            break
        bestes, bestes_ev = bester, bester_ev
    return {"basis_ev": basis_ev, "bestes": bestes, "bestes_ev": bestes_ev,
            "auswertungen": len(gesehen)}


def entscheide(basis, bewerte, holdout, grenzen, konf):
    """Abstieg -> Sieb -> Holdout. ``holdout(werte) -> kennzahlen`` wird nur
    aufgerufen, wenn das Sieb bestanden ist, und genau einmal je Satz."""
    erg = abstieg(basis, bewerte, grenzen, konf["such_budget"])
    res = {"kandidat": None, "fast_kandidat": None, "grund": "",
           "regeln": [], "basis_ev": erg["basis_ev"],
           "kandidat_ev": erg["bestes_ev"], "holdout_basis": None,
           "holdout_kandidat": None, "auswertungen": erg["auswertungen"],
           "basis_werte": basis, "bestes": erg["bestes"]}
    if erg["bestes"] == basis:
        res["grund"] = "kein besserer Kandidat gefunden"
        return res

    res["regeln"] = sieb_regeln(erg["basis_ev"], erg["bestes_ev"], konf)
    verstoesse = [r["regel"] for r in res["regeln"] if not r["ok"]]
    if verstoesse:
        res["grund"] = "Sieb nicht bestanden: Regel " + ", ".join(verstoesse)
        return res

    res["holdout_basis"] = holdout(basis)
    res["holdout_kandidat"] = holdout(erg["bestes"])
    hb, hk = res["holdout_basis"], res["holdout_kandidat"]
    if not (hk["je_runde"] > hb["je_runde"]
            and hk["n"] >= konf["holdout_min_runden"]):
        res["fast_kandidat"] = erg["bestes"]
        res["grund"] = "Holdout nicht bestanden"
        return res

    res["kandidat"] = erg["bestes"]
    res["grund"] = ("Vorschlag: Sieb a-e und Holdout bestanden "
                    "(%d Auswertungen)" % erg["auswertungen"])
    return res
```

- [x] **Schritt 4: Test laufen lassen, Erfolg pruefen**

Lauf wie Schritt 2. Erwartet: alle Tests PASS. Schlaegt `test_budget_deckelt_die_auswertungen` fehl, ist die Budget-Pruefung im Nachbarn-Loop zu korrigieren (nur NEUE Saetze kosten Budget).

- [x] **Schritt 5: Commit**

```bash
git add Agenten/Handel/verbesserer/xperp_suche.py Agenten/Handel/verbesserer/tests/test_xperp_suche.py
git commit -m "verbesserer: xperp_suche - Nachbarn, Sieb a-e, Abstieg und Holdout-Entscheidung

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Konfiguration, Whitelist, Denylist und `anwenden` fuer Spur 2

**Files:**
- Modify: `Agenten/Handel/verbesserer/spuren.json` (Eintrag `spur2`)
- Modify: `Agenten/Handel/verbesserer/konfig.json` (Block `spur2`)
- Modify: `Agenten/Handel/verbesserer/anwenden.py` (`_GESPERRTE_PRAEFIXE`, optionale Bewertungsdatei)
- Modify: `Werkstatt/spec-verbesserer-spur2-schleife-2026-10-09.md` (Abweichungen eintragen)
- Test: `Agenten/Handel/verbesserer/tests/test_xperp_anwenden.py` (neu)

**Interfaces:**
- Consumes: `anwenden.anwenden(ordner, spur, repo)` (Rueckgabe `{"ok","grund","commit"}`), `anwenden.denylist_ok(schluessel)`.
- Produces: `spuren.json["spur2"]` mit `wachen` (`../xperp/wachen.json`), `berichte`, `aenderbar["wachen.json"]` (8 Schluessel mit `[lo, hi]`), **ohne** `bewertung_datei`. `konfig.json["spur2"]` mit `such_budget`, `such_tage`, `test_tage`, `schritt_tage`, `holdout_tage`, `holdout_min_runden`, `holdout_max_nutzungen`, `overfit_min_fenster`, `overfit_min_runden`. `anwenden.anwenden` toleriert eine Spur ohne `bewertung_datei`.

- [x] **Schritt 1: Fehlschlagenden Test schreiben**

Datei `Agenten/Handel/verbesserer/tests/test_xperp_anwenden.py`:

```python
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import mkdtemp

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import anwenden  # noqa: E402
import xperp_suche  # noqa: E402

SPUREN = json.loads((WURZEL / "spuren.json").read_text("utf-8"))
KONFIG = json.loads((WURZEL / "konfig.json").read_text("utf-8"))
CO = "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
WACHEN_ALT = ('{\n  "max_hebel": 5,\n  "handel_erlaubt": true,\n'
              '  "stop_atr_faktor": 1.5,\n  "ziel_atr_faktor": 3.0\n}\n')


def _git(repo, *a):
    return subprocess.run(["git", *a], cwd=repo, capture_output=True,
                          text=True, check=True)


class TestKonfig(unittest.TestCase):
    def test_spur2_eintrag_hat_acht_schluessel_ohne_bewertungsdatei(self):
        s = SPUREN["spur2"]
        self.assertNotIn("bewertung_datei", s)
        self.assertEqual(set(s["aenderbar"]["wachen.json"]),
                         set(xperp_suche.SCHRITT))

    def test_basiswerte_der_echten_wache_liegen_in_den_grenzen(self):
        wachen = json.loads(
            (WURZEL.parent / "xperp" / "wachen.json").read_text("utf-8"))
        grenzen = SPUREN["spur2"]["aenderbar"]["wachen.json"]
        for k, v in xperp_suche.basis_werte(wachen).items():
            lo, hi = grenzen[k]
            self.assertTrue(lo <= v <= hi, "%s=%s ausserhalb [%s, %s]"
                            % (k, v, lo, hi))

    def test_spur2_konfig_vollstaendig(self):
        k = KONFIG["spur2"]
        for feld in ("such_budget", "such_tage", "test_tage", "schritt_tage",
                     "holdout_tage", "holdout_min_runden",
                     "holdout_max_nutzungen", "overfit_min_fenster",
                     "overfit_min_runden"):
            self.assertIn(feld, k)
        self.assertEqual(k["holdout_max_nutzungen"], 8)

    def test_konfig_ergibt_mindestens_die_geforderte_fensterzahl(self):
        fenster, _ = xperp_suche.fenster_grenzen(10**12, KONFIG["spur2"])
        self.assertGreaterEqual(len(fenster),
                                KONFIG["spur2"]["overfit_min_fenster"])


class TestDenylist(unittest.TestCase):
    GESPERRT = ["max_hebel", "max_margin_je_anlauf_usd",
                "max_margin_gesamt_usd", "max_offene_anlaeufe",
                "risiko_je_anlauf_usd", "kill_switch_gesamt_usd",
                "drawdown_halbierung_usd", "freigabe", "herzschlag_max_minuten",
                "handel_erlaubt", "trailing_aktiv", "llm_aktiv", "llm_modell",
                "papier_faktor", "familien", "grid_stufen", "grid_spanne_atr"]

    def test_jeder_gesperrte_schluessel_wird_abgelehnt(self):
        for k in self.GESPERRT:
            self.assertFalse(anwenden.denylist_ok({k})[0], k)

    def test_alle_suchschluessel_sind_frei(self):
        self.assertTrue(anwenden.denylist_ok(set(xperp_suche.SCHRITT))[0])

    def test_whitelisten_von_spur1_und_spur3_bleiben_frei(self):
        for name in ("spur1", "spur3"):
            schluessel = set(SPUREN[name]["aenderbar"]["wachen.json"])
            self.assertTrue(anwenden.denylist_ok(schluessel)[0], name)


class TestAnwendenSpur2(unittest.TestCase):
    def setUp(self):
        self._orig = anwenden.WURZEL
        anwenden.WURZEL = Path(mkdtemp())
        self.addCleanup(setattr, anwenden, "WURZEL", self._orig)
        self.repo = Path(mkdtemp())
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "t@t")
        _git(self.repo, "config", "user.name", "t")
        _git(self.repo, "config", "commit.gpgsign", "false")
        (self.repo / "xperp").mkdir()
        self.wachen = self.repo / "xperp" / "wachen.json"
        self.wachen.write_text(WACHEN_ALT, "utf-8", newline="")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")
        self.spur = {
            "wachen": str(self.wachen),
            "aenderbar": {"wachen.json": {
                "stop_atr_faktor": [1.0, 2.5],
                "ziel_atr_faktor": [2.0, 4.5]}}}

    def _vorschlag(self, neu_text):
        ordner = self.repo / "v"
        ordner.mkdir()
        (ordner / "wachen.neu.json").write_text(neu_text, "utf-8", newline="")
        (ordner / "commit.txt").write_text(
            "verbesserer: spur2 Test\n\n" + CO + "\n", "utf-8")
        return ordner

    def test_vorschlag_ohne_bewertungsdatei_wird_angewandt(self):
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"stop_atr_faktor": 1.5',
                               '"stop_atr_faktor": 1.75'))
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertTrue(r["ok"], r["grund"])
        self.assertIn('"stop_atr_faktor": 1.75', self.wachen.read_text("utf-8"))
        geaendert = _git(self.repo, "show", "--name-only",
                         "--format=", "HEAD").stdout.split()
        self.assertEqual(geaendert, ["xperp/wachen.json"])

    def test_denylist_blockt_max_hebel(self):
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"max_hebel": 5', '"max_hebel": 8'))
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertFalse(r["ok"])
        self.assertIn("max_hebel", r["grund"])
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_ALT)

    def test_wert_ausserhalb_des_bereichs_wird_abgelehnt(self):
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"stop_atr_faktor": 1.5',
                               '"stop_atr_faktor": 3.0'))
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertFalse(r["ok"])
        self.assertIn("ausserhalb", r["grund"])

    def test_veraltete_wache_wird_nicht_ueberschrieben(self):
        # Review Focus 1: Vorschlag stammt vom alten Stand; inzwischen hat der
        # Kill-Switch handel_erlaubt auf false gesetzt und committet.
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"stop_atr_faktor": 1.5',
                               '"stop_atr_faktor": 1.75'))
        self.wachen.write_text(
            WACHEN_ALT.replace('"handel_erlaubt": true',
                               '"handel_erlaubt": false'), "utf-8", newline="")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "kill-switch")
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertFalse(r["ok"])
        self.assertIn("handel_erlaubt", r["grund"])
        self.assertIn('"handel_erlaubt": false', self.wachen.read_text("utf-8"))

    def test_patch_ohne_bewertungsdatei_wird_abgelehnt(self):
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"stop_atr_faktor": 1.5',
                               '"stop_atr_faktor": 1.75'))
        (ordner / "bewertung.patch").write_text(
            "--- a/b.py\n+++ b/b.py\n@@ -1 +1 @@\n-x\n+y\n", "utf-8")
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertFalse(r["ok"])
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_ALT)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Schritt 2: Test laufen lassen, Fehlschlag pruefen**

Lauf: `cd Agenten/Handel/verbesserer && "$PY" tests/test_xperp_anwenden.py`
Erwartet: `KeyError: 'spur2'` in `TestKonfig`, Denylist-Tests FAIL (`max_hebel` u. a. nicht gesperrt), `TestAnwendenSpur2` ERROR (`KeyError: 'bewertung_datei'`).

- [x] **Schritt 3: Konfiguration eintragen**

`spuren.json` - den Schluss

```json
        "watchlist": "liste"
      }
    }
  }
}
```

ersetzen durch

```json
        "watchlist": "liste"
      }
    }
  },
  "spur2": {
    "name": "spur2",
    "_name": "XPERP/OKX Perpetuals (Trend-Modus, ohne LLM-Filter, Ruecktest xperp_ruecktest.py)",
    "wachen": "../xperp/wachen.json",
    "berichte": "berichte",
    "waehrung": "USD",
    "aenderbar": {
      "wachen.json": {
        "stop_atr_faktor": [1.0, 2.5],
        "ziel_atr_faktor": [2.0, 4.5],
        "einstieg_atr_abschlag": [0.0, 0.5],
        "trailing_trigger_r": [0.5, 2.0],
        "trailing_stop_prozent": [0.2, 1.0],
        "trailing_abstand_floor_pct": [0.15, 0.6],
        "trailing_min_hub_r": [0.1, 0.6],
        "trailing_max_halten_pct": [3.0, 8.0]
      }
    }
  }
}
```


`konfig.json` - nach der Zeile `  "gebuehr_umstellung_datum": "2026-09-06",` einfuegen:

```json
  "spur2": {
    "_zweck": "Spur 2 (XPERP). Eigene Fenster, weil die aeltesten XPERP erst seit Mai 2026 laufen: nach 60 Tagen Warmup bleiben ca. 90 Tage. 90 Tage Rueckblick = 4 Testfenster a 15 Tage (Schritt 15) + 20 Tage Holdout. ENTWURFSWERTE - in Task 7 gegen den echten Cache messen.",
    "such_budget": 60,
    "such_tage": 90,
    "test_tage": 15,
    "schritt_tage": 15,
    "holdout_tage": 20,
    "holdout_min_runden": 6,
    "holdout_max_nutzungen": 8,
    "overfit_min_fenster": 3,
    "overfit_min_runden": 20
  },
```

- [x] **Schritt 4: `anwenden.py` anpassen**

(a) `_GESPERRTE_PRAEFIXE`:

```python
_GESPERRTE_PRAEFIXE = ("freigabe", "drawdown", "kill_switch", "herzschlag")
```

ersetzen durch

```python
_GESPERRTE_PRAEFIXE = (
    "freigabe", "drawdown", "kill_switch", "herzschlag",
    # Spur 2 (XPERP): Deckel, Hebel, Risiko, LLM-Filter, Papierfaktor,
    # Familien-Block, Grid und der Trailing-Hauptschalter sind nie Sache eines
    # Vorschlags - auch dann nicht, wenn jemand sie in spuren.json freigibt.
    "max_hebel", "max_margin", "max_offene_anlaeufe", "risiko_je_anlauf",
    "llm_", "papier_faktor", "familien", "grid_", "trailing_aktiv")
```

(b) Kopf von `anwenden()`:

```python
    wachen_pfad = Path(spur["wachen"]).resolve()
    bewertung_pfad = Path(spur["bewertung_datei"]).resolve()
    pfade = [str(wachen_pfad), str(bewertung_pfad)]
```

ersetzen durch

```python
    wachen_pfad = Path(spur["wachen"]).resolve()
    # Spur 2 (XPERP) hat keine Bewertungsdatei: nur wachen.json wird angefasst.
    bewertung_pfad = (Path(spur["bewertung_datei"]).resolve()
                      if spur.get("bewertung_datei") else None)
    ziele = [p for p in (wachen_pfad, bewertung_pfad) if p is not None]
    pfade = [str(p) for p in ziele]
```

(c) Sicherung:

```python
        shutil.copy2(wachen_pfad, bak / wachen_pfad.name)
        shutil.copy2(bewertung_pfad, bak / bewertung_pfad.name)
```

ersetzen durch

```python
        for ziel in ziele:
            shutil.copy2(ziel, bak / ziel.name)
```

(d) Patch-Schritt:

```python
        if (patch_datei.exists()
                and patch_datei.read_text(encoding="utf-8").strip()):
            fremd = _patch_fremde_pfade(patch_datei, bewertung_pfad, repo)
```

ersetzen durch

```python
        if (patch_datei.exists()
                and patch_datei.read_text(encoding="utf-8").strip()):
            if bewertung_pfad is None:
                raise _PatchFremd(patch_datei.name)
            fremd = _patch_fremde_pfade(patch_datei, bewertung_pfad, repo)
```

(e) Commit-Schritt:

```python
        subprocess.run(["git", "add", str(wachen_pfad), str(bewertung_pfad)],
                       cwd=repo, check=True)
```

ersetzen durch

```python
        subprocess.run(["git", "add", *pfade], cwd=repo, check=True)
```

(f) `_wiederherstellen`:

```python
    for pfad in (wachen_pfad, bewertung_pfad):
        quelle = bak / pfad.name
```

ersetzen durch

```python
    ziele = [p for p in (wachen_pfad, bewertung_pfad) if p is not None]
    for pfad in ziele:
        quelle = bak / pfad.name
```

und

```python
            ["git", "reset", "--", str(wachen_pfad), str(bewertung_pfad)],
```

durch

```python
            ["git", "reset", "--", *[str(p) for p in ziele]],
```

Docstring von `_wiederherstellen` von „Beide Zieldateien" auf „Die Zieldateien" aendern. Danach `grep -n "bewertung_pfad" Agenten/Handel/verbesserer/anwenden.py` - jede verbleibende Stelle muss `None` vertragen.

- [x] **Schritt 5: Test laufen lassen, Erfolg pruefen**

Lauf wie Schritt 2. Erwartet: alle PASS. Dann die Bestandstests, die `anwenden`, Konfiguration und Denylist beruehren: `cd Agenten/Handel && "$PY" -m unittest discover -s verbesserer/tests -p "test_anwenden.py"` und `-p "test_konfig.py"` -> gruen.

- [x] **Schritt 6: Spec nachziehen**

In `Werkstatt/spec-verbesserer-spur2-schleife-2026-10-09.md`:
- Tabelle „Suchraum": die Zeilen `vola_tor_pa` und `min_umsatz_24h_usd` streichen; unter der Tabelle einen Satz ergaenzen: „`vola_tor_pa` und `min_umsatz_24h_usd` sind nicht im Suchraum: der Ruecktest liest das Vola-Tor aus `auswahl.KATEGORIEN`, und die Krypto-Familie ueberschreibt den Umsatz-Bezug - eine Aenderung haette keine Wirkung."
- Abschnitt „Bewertung und Sieb", Zeile „Maß": `oos_training_tage/...aus konfig.json` ersetzen durch „Fenster aus dem Block `spur2` in `konfig.json` (`such_tage`, `test_tage`, `schritt_tage`, `holdout_tage`)".
- Abschnitt „Fehlerverhalten": ergaenzen „Ein Abbruch schreibt einen Berichtsordner mit dem Grund, aber kein `commit.txt`. Instrumente ohne vollstaendigen Cache werden ausgelassen und im Bericht benannt; unter 3 verbleibenden Instrumenten Abbruch."
Gezielt per Edit, danach `git diff` ansehen (LF bleibt).

- [x] **Schritt 7: Commit**

```bash
git add Agenten/Handel/verbesserer/spuren.json Agenten/Handel/verbesserer/konfig.json Agenten/Handel/verbesserer/anwenden.py Agenten/Handel/verbesserer/tests/test_xperp_anwenden.py Werkstatt/spec-verbesserer-spur2-schleife-2026-10-09.md
git commit -m "verbesserer: Spur 2 in spuren.json/konfig.json, Denylist erweitert, anwenden ohne Bewertungsdatei

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Orchestrator `xperp_lauf.py` und Berichte

**Files:**
- Create: `Agenten/Handel/verbesserer/xperp_lauf.py`
- Test: `Agenten/Handel/verbesserer/tests/test_xperp_lauf.py` (neu)

**Interfaces:**
- Consumes: `xs.*` (Task 3), `xm.hole_oder_baue`, `xm.staende`, `xm.ctval_je_inst` (Task 2), `rt.simuliere(..., werte_cache=...)`, `rt.FundingLuecke`, `rt.zeitfenster`-Konstanten `rt.WARMUP_TAGE`, `vorschlag.wachen_neu_text(alt_text, aenderungen)`, `xk.laden_universum/laden/laden_funding/hole*`, `rt.okxf.instrumente`, `rt.bot.wachen()`.
- Produces:
  - `einmal(*, kerzen_holen=True, jetzt=None, konf=None, spur=None, basis_w=None, wachen_pfad=None, berichte=BERICHTE, cache_dir=None, merkmale_pfad=MERKMALE, zaehler_pfad=HOLDOUT_ZAEHLER) -> (Path, status)` mit `status` in `"vorschlag" | "kein_vorschlag" | "abbruch"`.
  - Dateien im Berichtsordner `berichte/<datum>-spur2/`: immer `bericht.md`; bei Vorschlag zusaetzlich `wachen.neu.json` und `commit.txt` (Format kompatibel mit `anfrage.text`: Zeilen `Geaenderte Schluessel:` und `OOS netto_gv_je_runde:`).
  - `zaehler_lesen(pfad) -> int`, `zaehler_erhoehen(pfad, datum) -> int`.
  - Hilfsfunktionen, die Tests patchen: `_daten_laden(universum, tage, kerzen_holen, cache_dir)` und `_instrumente()`.
  - CLI: `python xperp_lauf.py [--ohne-kerzen-abruf]`, Exitcode 0 bei Vorschlag/Kein-Vorschlag, 1 bei Abbruch.

- [x] **Schritt 1: Fehlschlagenden Test schreiben**

Datei `Agenten/Handel/verbesserer/tests/test_xperp_lauf.py`:

```python
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import mkdtemp
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import xperp_lauf as lauf  # noqa: E402
import xperp_suche as xs  # noqa: E402

S = lauf.rt.SCHRITT_MS
TAG = 86_400_000
ENDE = 1000 * TAG
JETZT = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
SPUR = json.loads((WURZEL / "spuren.json").read_text("utf-8"))["spur2"]
KONF = dict(json.loads((WURZEL / "konfig.json").read_text("utf-8"))["spur2"])
ECHTE_WACHE = WURZEL.parent / "xperp" / "wachen.json"
UNI = [{"instId": "%s-X" % c, "basis": c, "kategorie": "krypto"}
       for c in "ABC"]
BASIS_W = {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
           "einstieg_atr_abschlag": 0.25, "trailing_trigger_r": 1.0,
           "trailing_stop_prozent": 0.4, "trailing_abstand_floor_pct": 0.25,
           "trailing_min_hub_r": 0.25, "trailing_max_halten_pct": 5.0,
           "trailing_aktiv": True}


def _runde(ts, gv, grund="ziel"):
    return {"geschlossen_ts": ts, "gv": gv, "grund": grund,
            "kategorie": "krypto", "funding_summe": 0.0}


def _sim_besser_bei_engem_stop(w, von, bis):
    """Je Fenster 8 Runden; ein engerer Stop (<= 1.25) ist klar besser."""
    gv = 3.0 if w["stop_atr_faktor"] <= 1.25 else 1.0
    return [_runde(von + i + 1, gv) for i in range(8)]


def _daten(_universum, _tage, _holen, _dir):
    k = {u["instId"]: [[ENDE - 10 * S, 1, 1, 1, 1, 1], [ENDE, 1, 1, 1, 1, 1]]
         for u in UNI}
    return k, dict(k), dict(k), {u["instId"]: [[0, 0.0]] for u in UNI}, []


class Basis(unittest.TestCase):
    def setUp(self):
        self.dir = Path(mkdtemp())
        self.berichte = self.dir / "berichte"
        self.wachen = self.dir / "wachen.json"
        self.wachen.write_text(ECHTE_WACHE.read_text("utf-8"), "utf-8",
                               newline="")
        for p in (
                mock.patch.object(lauf.xk, "laden_universum",
                                  return_value=UNI),
                mock.patch.object(lauf, "_daten_laden", side_effect=_daten),
                mock.patch.object(lauf, "_instrumente",
                                  return_value={"A": {"ctVal": "1"},
                                                "B": {"ctVal": "1"},
                                                "C": {"ctVal": "1"}}),
                mock.patch.object(lauf.xm, "hole_oder_baue",
                                  side_effect=lambda pfad, u, k4, k1d, ct,
                                  st: ({s: [] for s in st}, False)),
                mock.patch.object(lauf.rt, "simuliere",
                                  side_effect=lambda *a, **k:
                                  _sim_besser_bei_engem_stop(a[7], a[8], a[9])
                                  )):
            p.start()
            self.addCleanup(p.stop)

    def einmal(self, **kw):
        args = dict(kerzen_holen=False, jetzt=JETZT, konf=dict(KONF),
                    spur=SPUR, basis_w=dict(BASIS_W),
                    wachen_pfad=self.wachen, berichte=self.berichte,
                    cache_dir=self.dir / "cache",
                    merkmale_pfad=self.dir / "m.json",
                    zaehler_pfad=self.dir / "z.json")
        args.update(kw)
        return lauf.einmal(**args)


class TestVorschlag(Basis):
    def test_vorschlag_schreibt_die_drei_dateien(self):
        ordner, status = self.einmal()
        self.assertEqual(status, "vorschlag")
        self.assertEqual(ordner.name, "2026-10-12-spur2")
        for name in ("bericht.md", "wachen.neu.json", "commit.txt"):
            self.assertTrue((ordner / name).is_file(), name)

    def test_commit_txt_ist_fuer_telegram_lesbar(self):
        ordner, _ = self.einmal()
        text = (ordner / "commit.txt").read_text("utf-8")
        self.assertTrue(text.startswith("verbesserer: spur2"))
        self.assertIn("Geaenderte Schluessel:", text)
        self.assertIn("stop_atr_faktor", text)
        self.assertIn("OOS netto_gv_je_runde:", text)
        self.assertIn("Co-Authored-By: Claude Sonnet 5.5", text)

    def test_wachen_neu_aendert_nur_die_gefundenen_schluessel(self):
        # Review Focus 5 (echte Wache, Rohtext-Ersetzung)
        ordner, _ = self.einmal()
        alt = json.loads(self.wachen.read_text("utf-8"))
        neu = json.loads((ordner / "wachen.neu.json").read_text("utf-8"))
        diff = {k for k in set(alt) | set(neu) if alt.get(k) != neu.get(k)}
        self.assertTrue(diff)
        self.assertLessEqual(diff, set(xs.SCHRITT))
        self.assertIn("stop_atr_faktor", diff)

    def test_bericht_zeigt_fenster_regeln_holdout_und_nicht_geprueft(self):
        ordner, _ = self.einmal()
        b = (ordner / "bericht.md").read_text("utf-8")
        for stichwort in ("Fenster", "Siebregeln", "Holdout",
                          "Nicht geprueft", "Holdout-Nutzung: 1 von 8"):
            self.assertIn(stichwort, b)

    def test_holdout_zaehler_steigt_nur_wenn_der_holdout_lief(self):
        self.einmal()
        self.assertEqual(lauf.zaehler_lesen(self.dir / "z.json"), 1)
        self.einmal()
        self.assertEqual(lauf.zaehler_lesen(self.dir / "z.json"), 2)

    def test_verbrauchter_holdout_wird_im_bericht_gemeldet(self):
        konf = {**KONF, "holdout_max_nutzungen": 1}
        self.einmal(konf=konf)
        ordner, _ = self.einmal(konf=konf)
        self.assertIn("verbraucht",
                      (ordner / "bericht.md").read_text("utf-8"))

    def test_zweiter_lauf_am_selben_tag_raeumt_altlasten(self):
        ordner, _ = self.einmal()
        (ordner / "alt.txt").write_text("x", "utf-8")
        ordner2, _ = self.einmal()
        self.assertEqual(ordner, ordner2)
        self.assertFalse((ordner2 / "alt.txt").exists())


class TestKeinVorschlag(Basis):
    def test_ohne_verbesserung_kein_commit_txt(self):
        with mock.patch.object(
                lauf.rt, "simuliere",
                side_effect=lambda *a, **k: [_runde(a[8] + 1, 1.0)] * 8):
            ordner, status = self.einmal()
        self.assertEqual(status, "kein_vorschlag")
        self.assertFalse((ordner / "commit.txt").exists())
        self.assertIn("kein besserer Kandidat",
                      (ordner / "bericht.md").read_text("utf-8"))

    def test_zu_wenig_historie_fuer_die_fenster(self):
        # Review Focus 4
        konf = {**KONF, "such_tage": 30}
        ordner, status = self.einmal(konf=konf)
        self.assertEqual(status, "kein_vorschlag")
        self.assertIn("zu wenig Historie",
                      (ordner / "bericht.md").read_text("utf-8"))
        self.assertFalse((ordner / "commit.txt").exists())


class TestAbbruch(Basis):
    def test_kein_universum_cache(self):
        # Review Focus 2
        with mock.patch.object(lauf.xk, "laden_universum", return_value=[]):
            ordner, status = self.einmal()
        self.assertEqual(status, "abbruch")
        self.assertIn("Universum", (ordner / "bericht.md").read_text("utf-8"))
        self.assertFalse((ordner / "commit.txt").exists())

    def test_zu_wenige_instrumente_mit_vollstaendigem_cache(self):
        def daten(u, t, h, d):
            k = {"A-X": [[ENDE, 1, 1, 1, 1, 1]]}
            return k, dict(k), dict(k), {"A-X": [[0, 0.0]]}, ["B-X", "C-X"]
        with mock.patch.object(lauf, "_daten_laden", side_effect=daten):
            ordner, status = self.einmal()
        self.assertEqual(status, "abbruch")
        b = (ordner / "bericht.md").read_text("utf-8")
        self.assertIn("B-X", b)
        self.assertFalse((ordner / "commit.txt").exists())

    def test_ausgelassene_instrumente_stehen_im_bericht(self):
        def daten(u, t, h, d):
            k, k1h, k1d, s, _ = _daten(u, t, h, d)
            return k, k1h, k1d, s, ["Z-X"]
        with mock.patch.object(lauf, "_daten_laden", side_effect=daten):
            ordner, status = self.einmal()
        self.assertEqual(status, "vorschlag")
        self.assertIn("Z-X", (ordner / "bericht.md").read_text("utf-8"))

    def test_funding_luecke_bricht_ab_ohne_vorschlag(self):
        # Review Focus 3
        def sim(*a, **k):
            raise lauf.rt.FundingLuecke("kein Funding-Satz vor 123")
        with mock.patch.object(lauf.rt, "simuliere", side_effect=sim):
            ordner, status = self.einmal()
        self.assertEqual(status, "abbruch")
        b = (ordner / "bericht.md").read_text("utf-8")
        self.assertIn("kein Funding-Satz vor 123", b)
        self.assertFalse((ordner / "commit.txt").exists())
        self.assertFalse((ordner / "wachen.neu.json").exists())

    def test_okx_instrumente_nicht_abrufbar(self):
        with mock.patch.object(lauf, "_instrumente",
                               side_effect=OSError("offline")):
            ordner, status = self.einmal()
        self.assertEqual(status, "abbruch")
        self.assertIn("offline", (ordner / "bericht.md").read_text("utf-8"))


class TestZaehler(unittest.TestCase):
    def test_lesen_ohne_datei_und_mit_kaputter_datei(self):
        d = Path(mkdtemp())
        self.assertEqual(lauf.zaehler_lesen(d / "z.json"), 0)
        (d / "z.json").write_text("{kaputt", "utf-8")
        self.assertEqual(lauf.zaehler_lesen(d / "z.json"), 0)

    def test_erhoehen(self):
        d = Path(mkdtemp()) / "z.json"
        self.assertEqual(lauf.zaehler_erhoehen(d, "2026-10-12"), 1)
        self.assertEqual(lauf.zaehler_erhoehen(d, "2026-10-19"), 2)
        self.assertEqual(lauf.zaehler_lesen(d), 2)


if __name__ == "__main__":
    unittest.main()
```

Hinweis fuer den Ausfuehrer: `lauf.einmal` ruft `rt.simuliere` positionell mit den 10 Argumenten `(universum, k4, k1h, k1d, saetze, umsatz, instr_je_basis, w, start_ms, end_ms)` plus `werte_cache=` - die Fakes oben lesen `a[7]` (= `w`), `a[8]` (= `start_ms`), `a[9]` (= `end_ms`). Der Orchestrator **muss** daher genau positionell aufrufen.

- [x] **Schritt 2: Test laufen lassen, Fehlschlag pruefen**

Lauf: `cd Agenten/Handel/verbesserer && "$PY" tests/test_xperp_lauf.py`
Erwartet: `ModuleNotFoundError: No module named 'xperp_lauf'`.

- [x] **Schritt 3: Modul schreiben**

Datei `Agenten/Handel/verbesserer/xperp_lauf.py`:

```python
"""Orchestrator: eine Woche Selbstverbesserung fuer Spur 2 (XPERP).

Kette: Universum + Kerzen + Funding aus dem Cache (auf Wunsch vorher
aufgefrischt) -> Merkmals-Cache -> Koordinatenabstieg -> Sieb a-e -> Holdout ->
Bericht und Vorschlagsartefakte.

Jeder Lauf endet mit einem Ordner unter ``berichte/<datum>-spur2/``:
  * Vorschlag:      bericht.md, wachen.neu.json, commit.txt
  * Kein Vorschlag: bericht.md (mit Grund)
  * Abbruch:        bericht.md (mit Grund), nie commit.txt - ein Abbruch kann
                    so nie als Vorschlag bei Max landen.
Angewendet wird nichts: das macht anwenden.anwenden() nach Max' /ja.

Nur Standardbibliothek.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
for _p in (WURZEL, WURZEL.parent / "xperp", WURZEL.parent / "scanner"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import vorschlag  # noqa: E402
import xperp_kerzen as xk  # noqa: E402
import xperp_merkmale as xm  # noqa: E402
import xperp_ruecktest as rt  # noqa: E402
import xperp_suche as xs  # noqa: E402

BERICHTE = WURZEL / "berichte"
MERKMALE = WURZEL / "xperp_merkmale.json"
HOLDOUT_ZAEHLER = WURZEL / "xperp_holdout_nutzung.json"
MIN_INSTRUMENTE = 3

NICHT_GEPRUEFT = [
    "- Wenige Testfenster; Auswahl und Siebregeln a-e nutzen dieselben Fenster "
    "(nur der Holdout ist unabhaengig).",
    "- Nur Trend-Modus, ohne LLM-Filter, CVD-4h neutral - der Vorschlag gilt "
    "fuer die Strategie OHNE LLM-Filter.",
    "- Zum Fensterende offene Positionen werden nicht bewertet.",
    "- Bestanden heisst: der Vertrag aus a-e und Holdout ist erfuellt, nicht, "
    "dass die Wache live besser ist.",
]


# --- Hilfen mit Netz/Platte (Tests ersetzen sie) ------------------------------

def _konf():
    konfig = json.loads((WURZEL / "konfig.json").read_text("utf-8"))
    spuren = json.loads((WURZEL / "spuren.json").read_text("utf-8"))
    return konfig["spur2"], spuren["spur2"]


def _daten_laden(universum, tage, kerzen_holen, cache_dir):
    """(k4, k1h, k1d, saetze, fehlt): je Instrument aus dem Cache, auf Wunsch
    vorher aufgefrischt (best effort - ein Abruffehler faellt auf den Cache
    zurueck). ``fehlt`` nennt Instrumente ohne vollstaendigen Cache."""
    seiten_1h = -(-tage * 24 // 100)
    seiten_4h = -(-tage * 6 // 100)
    seiten_fund = -(-tage * 24 // 100) + 1
    k4, k1h, k1d, saetze, fehlt = {}, {}, {}, {}, []
    for x in universum:
        iid = x["instId"]
        if kerzen_holen:
            try:
                xk.hole(iid, "1H", seiten=seiten_1h, cache_dir=cache_dir)
                xk.hole(iid, "4H", seiten=seiten_4h, cache_dir=cache_dir)
                xk.hole(iid, "1D", cache_dir=cache_dir)
                xk.hole_funding(iid, seiten=seiten_fund, cache_dir=cache_dir)
            except Exception as e:  # noqa: BLE001
                print("  Abruf %s: %s - nehme Cache" % (iid, e),
                      file=sys.stderr)
        a, _ = xk.laden(iid, "4H", cache_dir)
        b, _ = xk.laden(iid, "1H", cache_dir)
        c, _ = xk.laden(iid, "1D", cache_dir)
        s, _ = xk.laden_funding(iid, cache_dir)
        if not (a and b and c and s):
            fehlt.append(iid)
            continue
        k4[iid], k1h[iid], k1d[iid], saetze[iid] = a, b, c, s
    return k4, k1h, k1d, saetze, fehlt


def _instrumente():
    """Instrumentenstamm je Basiswert (ein OKX-Abruf)."""
    return {i["instId"].split("-")[0]: i
            for i in rt.okxf.instrumente(kategorie=None)}


# --- Holdout-Zaehler ------------------------------------------------------------

def zaehler_lesen(pfad):
    try:
        return int(json.loads(Path(pfad).read_text("utf-8"))["nutzungen"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def zaehler_erhoehen(pfad, datum):
    n = zaehler_lesen(pfad) + 1
    Path(pfad).write_text(json.dumps({"nutzungen": n, "zuletzt": datum}),
                          "utf-8")
    return n


# --- Berichte -------------------------------------------------------------------

def _tag(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d")


def _tabelle(kopf, zeilen):
    aus = ["| " + " | ".join(kopf) + " |",
           "|" + "|".join("---" for _ in kopf) + "|"]
    aus += ["| " + " | ".join(str(z) for z in zeile) + " |" for zeile in zeilen]
    return aus


def bericht_text(ctx, res):
    z = ["# Verbesserer Spur 2 (XPERP) - %s" % ctx["datum"], "",
         "**Ergebnis:** %s" % res["grund"], ""]
    zeigen = res["kandidat"] or res["fast_kandidat"]
    if zeigen:
        titel = ("Geaenderte Parameter" if res["kandidat"]
                 else "Fast-Kandidat (Parameter, NICHT vorgeschlagen)")
        z += ["## " + titel, ""]
        z += _tabelle(["Schluessel", "Basis", "Kandidat"],
                      [(k, res["basis_werte"][k], zeigen[k])
                       for k in sorted(xs.SCHRITT)
                       if res["basis_werte"][k] != zeigen[k]])
        z += [""]

    z += ["## Fenster", "",
          "%d Testfenster a %d Tage, Schritt %d Tage; Holdout: %s bis %s." % (
              len(ctx["fenster"]), ctx["konf"]["test_tage"],
              ctx["konf"]["schritt_tage"], _tag(ctx["holdout"][0]),
              _tag(ctx["holdout"][1])), ""]
    kand_fenster = res["kandidat_ev"]["fenster"]
    z += _tabelle(
        ["Fenster", "von", "bis", "Basis je Runde", "n", "Kandidat je Runde",
         "n"],
        [(i + 1, _tag(v), _tag(b), "%.4f" % bf["je_runde"], bf["n"],
          "%.4f" % kf["je_runde"], kf["n"])
         for i, ((v, b), bf, kf) in enumerate(
             zip(ctx["fenster"], res["basis_ev"]["fenster"], kand_fenster))])
    z += [""]

    if res["regeln"]:
        z += ["## Siebregeln", ""]
        z += _tabelle(["Regel", "Pruefung", "Kandidat", "Soll", "Ergebnis"],
                      [(r["regel"], r["text"], r["ist"], r["soll"],
                        "bestanden" if r["ok"] else "NICHT bestanden")
                       for r in res["regeln"]])
        z += [""]

    z += ["## Holdout", ""]
    if res["holdout_basis"] is None:
        z += ["Nicht bewertet (kein Kandidat hat das Sieb erreicht).", ""]
    else:
        hb, hk = res["holdout_basis"], res["holdout_kandidat"]
        z += _tabelle(["", "Runden", "je Runde", "Liquidationsanteil",
                       "Ruecklauf"],
                      [("Basis", hb["n"], "%.4f" % hb["je_runde"],
                        "%.1f %%" % (100 * hb["liquidationsanteil"]),
                        "%.2f" % hb["ruecklauf"]),
                       ("Kandidat", hk["n"], "%.4f" % hk["je_runde"],
                        "%.1f %%" % (100 * hk["liquidationsanteil"]),
                        "%.2f" % hk["ruecklauf"])])
        z += ["", "Mindestrunden im Holdout: %d." % ctx["konf"][
            "holdout_min_runden"], ""]

    z += ["Holdout-Nutzung: %d von %d" % (
        ctx["nutzungen"], ctx["konf"]["holdout_max_nutzungen"])]
    if ctx["nutzungen"] >= ctx["konf"]["holdout_max_nutzungen"]:
        z += ["", "**Der Holdout-Block gilt als verbraucht** - jede Auswertung "
              "gibt dem Vorschlagenden Information preis. Zaehler zuruecksetzen "
              "(Datei xperp_holdout_nutzung.json loeschen), wenn Max den Block "
              "freigibt."]
    z += ["", "## Nicht geprueft", ""] + NICHT_GEPRUEFT
    if ctx["hinweise"]:
        z += ["", "## Hinweise", ""] + ["- " + h for h in ctx["hinweise"]]
    z += [""]
    return "\n".join(z)


def commit_text(ctx, res, aenderungen):
    b, k = res["basis_ev"]["gesamt"], res["kandidat_ev"]["gesamt"]
    hb, hk = res["holdout_basis"], res["holdout_kandidat"]
    return "\n".join([
        "verbesserer: spur2 Parameter angepasst",
        "",
        "Walk-Forward (%d Fenster a %d Tage), Siebregeln a-e bestanden:" % (
            len(ctx["fenster"]), ctx["konf"]["test_tage"]),
        "OOS netto_gv_je_runde: %.4f -> %.4f" % (b["je_runde"], k["je_runde"]),
        "Holdout netto_gv_je_runde: %.4f -> %.4f (n=%d)" % (
            hb["je_runde"], hk["je_runde"], hk["n"]),
        "",
        "Geaenderte Schluessel: " + ", ".join(sorted(aenderungen)),
        "",
        "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>",
        ""])


def _kopf(ordner, titel, grund, zusatz=()):
    text = ["# Verbesserer Spur 2 (XPERP) - %s" % titel, "",
            "**Grund:** %s" % grund, ""] + list(zusatz) + [""]
    (ordner / "bericht.md").write_text("\n".join(text), "utf-8", newline="\n")


def _abbruch(ordner, grund, zusatz=()):
    print("ABBRUCH: %s" % grund, file=sys.stderr)
    _kopf(ordner, "ABBRUCH", grund, zusatz)
    return ordner, "abbruch"


def _ordner(berichte, datum):
    """Ordner des Tages; Reste eines frueheren Laufs weg, sonst wendet ein
    spaeteres /ja einen Mischstand an (wie lauf.py in Spur 1)."""
    ordner = Path(berichte) / ("%s-spur2" % datum)
    if ordner.exists():
        shutil.rmtree(ordner, ignore_errors=True)
        for rest in ordner.glob("*") if ordner.exists() else []:
            if rest.is_file():
                rest.unlink(missing_ok=True)
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner


# --- Der Lauf -------------------------------------------------------------------

def einmal(*, kerzen_holen=True, jetzt=None, konf=None, spur=None,
           basis_w=None, wachen_pfad=None, berichte=BERICHTE, cache_dir=None,
           merkmale_pfad=MERKMALE, zaehler_pfad=HOLDOUT_ZAEHLER):
    """Eine Woche fuer Spur 2. Rueckgabe ``(ordner, status)`` mit status
    ``vorschlag`` | ``kein_vorschlag`` | ``abbruch``."""
    if konf is None or spur is None:
        konf, spur = _konf()
    wachen_pfad = Path(wachen_pfad or (WURZEL / spur["wachen"]).resolve())
    cache_dir = cache_dir or xk.CACHE
    jetzt = jetzt or datetime.now(timezone.utc)
    datum = jetzt.strftime("%Y-%m-%d")
    ordner = _ordner(berichte, datum)
    hinweise = []

    universum = xk.laden_universum(cache_dir)
    if not universum:
        return _abbruch(ordner, "Kein Universum-Cache - einmal ohne "
                                "--ohne-kerzen-abruf starten.")

    k4, k1h, k1d, saetze, fehlt = _daten_laden(
        universum, konf["such_tage"] + rt.WARMUP_TAGE, kerzen_holen,
        cache_dir)
    if fehlt:
        hinweise.append("%d Instrument(e) ohne vollstaendigen Cache "
                        "ausgelassen: %s" % (len(fehlt), ", ".join(fehlt)))
    universum = [x for x in universum if x["instId"] in k4]
    if len(universum) < MIN_INSTRUMENTE:
        return _abbruch(ordner, "weniger als %d Instrumente mit vollstaendigem "
                                "Cache" % MIN_INSTRUMENTE, hinweise)

    try:
        instr_je_basis = _instrumente()
    except Exception as e:  # noqa: BLE001
        return _abbruch(ordner, "OKX-Instrumentenstamm nicht abrufbar: %s" % e,
                        hinweise)

    if basis_w is None:
        basis_w = rt.bot.wachen()
    with open(wachen_pfad, "r", encoding="utf-8", newline="") as f:
        alt_text = f.read()
    basis = xs.basis_werte(basis_w)
    grenzen = spur["aenderbar"]["wachen.json"]

    ende = max(k[-1][0] for k in k4.values())
    fenster, holdout_fenster = xs.fenster_grenzen(ende, konf)
    ctx = {"datum": datum, "konf": konf, "fenster": fenster,
           "holdout": holdout_fenster, "hinweise": hinweise, "nutzungen":
           zaehler_lesen(zaehler_pfad)}
    if len(fenster) < konf["overfit_min_fenster"]:
        res = {"kandidat": None, "fast_kandidat": None,
               "grund": "zu wenig Historie fuer %d Testfenster (vorhanden: %d)"
                        % (konf["overfit_min_fenster"], len(fenster))}
        _kopf(ordner, datum, res["grund"], hinweise)
        return ordner, "kein_vorschlag"

    ctval = xm.ctval_je_inst(universum, instr_je_basis)
    matrix, _aus_cache = xm.hole_oder_baue(
        merkmale_pfad, universum, k4, k1d, ctval,
        xm.staende(fenster[0][0], holdout_fenster[1]))

    def simulieren(w, von, bis):
        return rt.simuliere(universum, k4, k1h, k1d, saetze, {},
                            instr_je_basis, w, von, bis, werte_cache=matrix)

    def bewerte(werte):
        return xs.bewerte_fenster(simulieren, {**basis_w, **werte}, fenster)

    def holdout(werte):
        return xs.kennzahlen(simulieren({**basis_w, **werte},
                                        *holdout_fenster))

    try:
        res = xs.entscheide(basis, bewerte, holdout, grenzen, konf)
    except rt.FundingLuecke as e:
        return _abbruch(ordner, "Funding-Luecke: %s" % e, hinweise)

    if res["holdout_basis"] is not None:
        ctx["nutzungen"] = zaehler_erhoehen(zaehler_pfad, datum)

    (ordner / "bericht.md").write_text(bericht_text(ctx, res), "utf-8",
                                       newline="\n")
    if res["kandidat"] is None:
        return ordner, "kein_vorschlag"

    aenderungen = {k: v for k, v in res["kandidat"].items()
                   if res["basis_werte"][k] != v}
    with open(ordner / "wachen.neu.json", "w", encoding="utf-8",
              newline="") as f:
        f.write(vorschlag.wachen_neu_text(alt_text, aenderungen))
    (ordner / "commit.txt").write_text(commit_text(ctx, res, aenderungen),
                                       "utf-8", newline="\n")
    return ordner, "vorschlag"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ohne-kerzen-abruf", action="store_true")
    a = p.parse_args()
    o, status = einmal(kerzen_holen=not a.ohne_kerzen_abruf)
    print("%s: %s" % (status, o))
    sys.exit(1 if status == "abbruch" else 0)
```

Hinweis fuer den Ausfuehrer: `commit_text` und `bericht_text` setzen voraus, dass `res["kandidat_ev"]["fenster"]` genauso viele Eintraege hat wie `ctx["fenster"]` (stimmt, weil beide aus `bewerte_fenster` mit derselben Fensterliste kommen).

- [x] **Schritt 4: Test laufen lassen, Erfolg pruefen**

Lauf wie Schritt 2. Erwartet: alle Tests PASS. Haeufige Stolperer: (a) `test_zu_wenig_historie...` nutzt `such_tage=30` -> `fenster_grenzen` liefert `[]`; (b) bei `test_verbrauchter_holdout...` zaehlt der Zaehler erst nach der Holdout-Auswertung - mit `holdout_max_nutzungen=1` meldet schon der erste Lauf „verbraucht", der zweite erst recht.

- [x] **Schritt 5: Commit**

```bash
git add Agenten/Handel/verbesserer/xperp_lauf.py Agenten/Handel/verbesserer/tests/test_xperp_lauf.py
git commit -m "verbesserer: xperp_lauf - Orchestrator, Berichte und Holdout-Zaehler fuer Spur 2

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Routine und Dokumentation

**Files:**
- Create: `Agenten/Routinen/verbesserer-spur2.ps1` (CRLF)
- Modify: `MaxHirn/Wissen/Verbesserer.md` (Abschnitt Spur 2)

**Interfaces:**
- Consumes: `Agenten/Handel/verbesserer/xperp_lauf.py` (CLI, Exitcode), Muster von `Routinen/verbesserer.ps1`.
- Produces: eine PowerShell-Routine, die wie `verbesserer.ps1` loggt und den Exitcode weitergibt; eine Wissensnotiz.

- [x] **Schritt 1: Routine schreiben**

Datei `Agenten/Routinen/verbesserer-spur2.ps1` (CRLF-Zeilenenden; Struktur 1:1 wie `verbesserer.ps1`):

```powershell
# Woechentliche Selbstverbesserung von Spur 2 (XPERP). Laeuft NACH
# handel-wachen.ps1 und getrennt von verbesserer.ps1 (Spur 1): der erste Lauf
# rechnet 20-35 Minuten (Merkmals-Cache). Erzeugt nur einen Vorschlag in
# verbesserer/berichte/ - angewandt wird er erst per /ja im Dauerlauf.
$ErrorActionPreference = "Stop"
$env:MAXHIRN_ROUTINE = "1"
$wurzel = Split-Path -Parent $PSScriptRoot
. (Join-Path $wurzel 'Bus\Ereignis.ps1')
$py = Join-Path $wurzel "Handel\verbesserer\.venv\Scripts\python.exe"
$lauf = Join-Path $wurzel "Handel\verbesserer\xperp_lauf.py"
$log = Join-Path $PSScriptRoot "logs\verbesserer-spur2-$(Get-Date -Format yyyy-MM-dd).log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$marke = Melde-Start -Wer 'routine/verbesserer-spur2' `
           -Log ('Agenten/Routinen/logs/verbesserer-spur2-' + (Get-Date -Format yyyy-MM-dd) + '.log')
try {
  & $py $lauf *>&1 | Tee-Object -FilePath $log
  Melde-Ende -Marke $marke -Code $LASTEXITCODE
  exit $LASTEXITCODE
} catch {
  Melde-Ende -Marke $marke -Code 1 -Text "$_"
  throw
}
```

Nach dem Schreiben pruefen: `file Agenten/Routinen/verbesserer-spur2.ps1` muss „CRLF line terminators" nennen (sonst mit `unix2dos` bzw. `sed -i 's/$/\r/'` angleichen). Syntaxpruefung: `powershell -NoProfile -Command "$null = [scriptblock]::Create((Get-Content -Raw Agenten/Routinen/verbesserer-spur2.ps1)); 'ok'"` -> `ok`.

- [x] **Schritt 2: Wissensnotiz ergaenzen**

Vorher melden: `python Agenten/Werkzeuge/bereiche.py --aufrufer handel --pfad MaxHirn/Wissen/Verbesserer.md` (Exitcode 1 = fremder Bereich -> als BEFUND in den Abschlussbericht, nicht blockieren). `MaxHirn/Wissen/Verbesserer.md` frisch lesen, Zeilenenden pruefen (`file`), dann gezielt einen Abschnitt „Spur 2 (XPERP)" anhaengen bzw. den Punkt „TP6: Ausweitung auf Spur 2" ersetzen. Inhalt, knapp: Zweck; Aufruf `xperp_lauf.py`; Suchraum (8 Schluessel) und warum `vola_tor_pa`/`min_umsatz_24h_usd` fehlen; Stufen Sieb a-e -> Holdout -> `/ja`; `holdout_max_nutzungen` 8 und Zaehlerdatei `verbesserer/xperp_holdout_nutzung.json` (loeschen = zuruecksetzen); Rücknahme (`.bak`, `git revert` des Anwende-Commits); Abbruch-Verhalten; Verweis auf die Spec. Kein neuer `INDEX.md`-Eintrag noetig (keine neue Notiz).

- [x] **Schritt 3: Gesamtlauf der Verbesserer-Tests**

Lauf: `cd Agenten/Handel && "$PY" -m unittest discover -s verbesserer/tests` -> alle gruen (Basislinie + die neuen Dateien). Zusaetzlich die xperp-Suite, weil `xperp_ruecktest.py` geaendert wurde: `cd Agenten/Handel/xperp && ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests` (Spec nennt 170 Tests) -> gruen.

- [x] **Schritt 4: Commit**

```bash
git add Agenten/Routinen/verbesserer-spur2.ps1 MaxHirn/Wissen/Verbesserer.md
git commit -m "verbesserer: Routine verbesserer-spur2.ps1 und Wissensnotiz Spur 2

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Abnahmelauf gegen echte Daten (von Hand, mit Max)

**Files:** keine Codeaenderung vorgesehen; ggf. `konfig.json` (Block `spur2`) anpassen.

Dieser Task ist **kein** Unit-Test-Task: Es gibt in diesem Rechner noch keinen XPERP-Kerzen-Cache (`verbesserer/xperp_kerzen/` fehlt), die Entwurfswerte in `konfig.json["spur2"]` sind deshalb ungemessen. Er braucht Netz zu OKX, mehrere Minuten bis Stunden und Max' Okay fuer den Abruf.

- [x] **Schritt 1: Cache holen (einmalig, langsam)** - `cd Agenten/Handel/verbesserer && .venv/Scripts/python.exe xperp_ruecktest.py --tage 180 --kerzen-holen` (legt `xperp_kerzen/` an; Ausgabe ist der Leistungsbericht der heutigen Wache - als Plausibilitaetscheck des Caches ansehen).
- [x] **Schritt 2: Historie messen** - Fuer `4H`-Reihen die Spanne je Instrument ausgeben (frueheste/letzte Zeit, Median in Tagen). Passt `such_tage` 90 / `holdout_tage` 20 / `test_tage` 15? Ergibt `fenster_grenzen` mindestens 3 Fenster, und haben die Fenster plausibel Runden (Basis: `overfit_min_runden` 20 im Aggregat)? Sonst die Werte im Block `spur2` anpassen und im Plan/Spec vermerken - **Max entscheidet**, weil sie bestimmen, wie streng das Sieb ist.
- [x] **Schritt 3: Lauf zeitnehmen** - `.venv/Scripts/python.exe xperp_lauf.py --ohne-kerzen-abruf` zweimal: erster Lauf baut den Merkmals-Cache (20-35 min erwartet), der zweite muss ihn wiederverwenden (deutlich kuerzer). Dauer je Auswertung notieren und `such_budget` entsprechend setzen (Ziel: ein Lauf unter ca. 2 Stunden).
- [ ] **Schritt 4: Bericht lesen** - `berichte/<datum>-spur2/bericht.md` mit Max durchgehen: Fenster-Tabelle, Siebregeln, Holdout, „Nicht geprueft". Ist der Bericht fuer ein ehrliches `/ja` brauchbar? Anpassungswuensche als eigene Tasks aufnehmen.
  - *Befund 10.10.2026 (nach master-Merge):* Neulauf mit der aktuellen Wache ergab nur 6 Runden in 4 Fenstern (vorher 44), Sieb b+c nicht bestanden. Ursache ist nicht der Trailing-Abstand 1,5 %, sondern `familien.rohstoff.max_hebel` 10 (Auftrag Max 08.10.): Der Rücktest verlangt wie live `hebel_deckel >= hebel_grenze`, und bei 10x besteht in 60 Tagen kein Rohstoff mehr. Vorher kamen 53 von 59 Einstiegen aus BZ/CL/XAG/XAU. Die Spur-2-Stichprobe hängt also fast vollständig an den vier Rohstoffen. **Entscheidung Max:** 10x-Regel behalten (dann `overfit_min_runden` senken oder den Rückblick verlängern) oder die Rohstoffe mit dem Deckel handeln lassen.
- [ ] **Schritt 5: Aufgabenplaner** - Die Routine wie `verbesserer.ps1` registrieren (Vorlage und Zeitpunkt in `MaxHirn/Wissen/Routinen.md` nachsehen). Das ist ein Eingriff in den Aufgabenplaner: erst nach Max' ausdruecklichem Okay.
- [ ] **Schritt 6: Abschluss** - PR vom Zweig `claude/verbesserer-spur2-schleife` eroeffnen (Tests gruen, Spec/Plan/Wissensnotiz konsistent); Merge erst nach Freigabe (Wurzel-`CLAUDE.md`, Abschnitt Zweige).

---

## Selbstpruefung

**Spec-Abdeckung:**
- Zweck/Abgrenzung (nur Trend, kein Grid, kein Auto-Anwenden, Spur 1/3 unberuehrt): Task 1-5; `auto_anwenden` bleibt unberuehrt in `konfig.json`.
- Architektur: `xperp_suche.py` (Task 3), `xperp_lauf.py` (Task 5), `xperp_merkmale.py` (Task 2), `spuren.json`-Eintrag (Task 4), Engine-Schalter (Task 1), `anwenden.py` (Task 4). `vorschlag.py` bleibt unveraendert (nur `wachen_neu_text` wird importiert).
- Suchraum/Denylist: Task 3 (`SCHRITT`, Zusatzbedingung), Task 4 (Whitelist, Denylist, Wiederholpruefung beim Anwenden). **Abweichung** (2 Schluessel) steht oben und wird in die Spec geschrieben.
- Sieb a-e: Task 3. Verifikation (Holdout, Bericht mit Fenstern/Abstaenden/„Nicht geprueft", benannte Verstoesse, kein Nachbessern in `anwenden`): Task 3 + 5. Holdout-Budget 8: Task 4 (Konfig) + 5 (Zaehler, Meldung „verbraucht").
- `trailing_aktiv` in der Engine: Task 1.
- Fehlerverhalten (laut, Berichtsordner immer, kein Auffuellen mit 0.0): Task 5 (Review Focus 2-4). Bekannte Luecke „offene Positionen am Fensterende" steht im Bericht unter „Nicht geprueft".
- Wiederherstellung je Stufe (Tor vor Anwenden, Denylist-Pruefung im Anwenden, `.bak`/`git revert`): bestehend in `anwenden.py`, abgesichert durch Review Focus 1 (Task 4).
- Betrieb (Routine, `MAXHIRN_ROUTINE=1`, Log): Task 6; Registrierung im Aufgabenplaner: Task 7, Schritt 5, mit Max.
- Tests der Spec (reine Funktionen, Cache-Hash, Ende-zu-Ende ohne Netz): Task 2, 3, 5. „Bestehende 246/170 Tests gruen": Task 6, Schritt 3.

**Platzhalter-Scan:** keine TBD/TODO. Offen und ausdruecklich benannt sind nur die ungemessenen Konfigurationswerte (Task 7).

**Typkonsistenz:** `bewerte_fenster`/`sieb_regeln`/`entscheide` benutzen dieselben Auswertungsformen (`{"fenster": [kennzahlen], "gesamt": kennzahlen}` mit `n`, `gv`, `je_runde`, `liquidationsanteil`, `ruecklauf`); `xperp_lauf` ruft `simuliere` positionell wie die Test-Fakes lesen; `xm.staende`/`werte_cache` verwenden dieselbe Stand-Definition `t - SCHRITT_MS`.

**Review Focus:** alle fuenf Zeilen haben ihren Test (Task 4: Zeile 1; Task 5: Zeilen 2-5).

**Probelauf des Plan-Codes (10.10.2026):** Die neuen Module und Tests aus Task 2, 3 und 5 sowie die Edits aus Task 1 und 4 wurden in einer Wegwerf-Kopie von `Agenten/Handel` angewandt: die 80 neuen Tests (5 + 16 + 31 + 12 + 16) laufen gruen, die gesamte Verbesserer-Suite zaehlt dort 326 Tests (246 Bestand + 80) und ist gruen; die xperp-Suite zaehlt im unveraenderten Arbeitsbaum 170 und ist gruen. Nicht probiert: Task 6 (PowerShell, Wissensnotiz) und Task 7 (echte Daten, Netz).
