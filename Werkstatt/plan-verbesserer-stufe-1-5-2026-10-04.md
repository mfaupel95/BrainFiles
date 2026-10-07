# Verbesserer Stufe 1.5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zwei bekannte Schwaechen der woechentlichen Scanner-Suche (Spur 1) beheben: Kerzen werden ueber Kalendertage statt Listenindex ausgerichtet (F7), und der Sieger der Suche muss einen Holdout-Block bestehen, den die Suche nie gesehen hat (F4).

**Architecture:** Zwei neue, injizierbare Funktionen in `ruecktest.py` (`ausrichten`, `holdout`). `walk_forward()` ruft `ausrichten()` selbst am Anfang auf (idempotent). `suche()` richtet einmal aus, schneidet die letzten `holdout_tage` Tage fuer Suche und Walk-Forward ab und misst Sieger und Basis danach genau einmal auf demselben Holdout — eine **zusaetzliche** Sperre neben den bestehenden. `lauf.py` meldet die Ausrichtungs-Hinweise und zieht 60 Tage mehr Historie; `digest.py` annotiert einen abgelehnten `fast_kandidat`.

**Tech Stack:** Python 3 (Standardbibliothek), `unittest`. Venv: `Agenten/Handel/scanner/.venv`. Keine neuen Abhaengigkeiten.

**Spec:** `Werkstatt/spec-verbesserer-stufe-1-5-2026-10-04.md` (abgenommen, Commit `02d8251e`). Uebergabe mit allen Planentscheidungen: `Werkstatt/uebergabe-verbesserer-stufe-1-5-2026-10-06.md`.

## Global Constraints

- **Bereich `handel`** (`Agenten/Handel/verbesserer/`). Vor jedem schreibenden Zugriff in einen fremden Bereich: BEFUND melden (`python Agenten/Werkzeuge/bereiche.py --aufrufer handel --pfad <pfad>`). Task 5 schreibt in Bereich `wissen` (`MaxHirn/Wissen/`) — dort BEFUND melden.
- **Nie `auto_anwenden`, die Denylist oder `anwenden.py` anfassen.** Denylist: `handel_erlaubt`, `freigabe`, `drawdown_halbierung_prozent`, `kill_switch_gesamt_usd`, `herzschlag_max_minuten`, `journal_zweitziel`, `max_pro_trade_usd`, `max_gesamt_usd`, `max_offene_positionen`. `auto_anwenden` bleibt `false`.
- **Fensterlogik unveraendert:** `oos_training_tage`/`oos_test_tage`/`oos_schritt_tage` werden nicht geaendert.
- **Versionierte Textdateien nur per gezieltem Ersatz (Edit), nie Rewrite** — `ruecktest.py`, `suche.py`, `lauf.py`, `digest.py` sind ASCII, `konfig.json` ist JSON. CRLF/LF-Umstellung vermeiden. Vor jedem Edit frisch lesen.
- **Alle 100 bestehenden Modul-Tests muessen gruen bleiben.** Testlauf: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests`.
- **`git add` immer namentlich**, je Task ein eigener Commit. Commit-Footer:
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` + `Claude-Session: https://claude.ai/code/session_01ABNAZC2GQrdDhNjqijQL8M`.
- **Nur Spur 1.** Spur 2 (XPERP) und Spur 3 (Kraken-EUR) sind nicht Teil dieser Stufe.

## Review Focus

- **Leeres / winziges `kerzen_je_inst`:** `ausrichten({})` und `holdout` auf leeren Reihen duerfen nicht per `min()`/`set.intersection()` werfen. Abgedeckt in Task 1 (Step „leere Eingabe") und Task 2 (Historie-Guard).
- **Alle Instrumente unter `min_anteil`:** bleibt `behalten` leer, muss `ausrichten` `({}, hinweise)` liefern statt an `set.intersection(*[])` zu werfen. Abgedeckt in Task 1.
- **Doppelte Kerze am selben Kalendertag:** zwei Kerzen mit gleichem `ts // 86400000` duerfen die Reihen nicht gegeneinander verschieben — eine Kerze je Tag (die spaetere). Abgedeckt in Task 1.
- **Holdout genau an der Grenze (`n == holdout_min_runden`):** `>=` muss bestehen lassen, `n-1` ablehnen. Abgedeckt in Task 3.
- **Bestandstests mit `KONF` ohne `holdout_tage`:** `konfig.get("holdout_tage", 0) == 0` schaltet den gesamten Holdout-Pfad (inkl. Ausrichten/Abschneiden) in `suche()` ab; `test_suche_lauf.py` bleibt unveraendert gruen. Abgedeckt in Task 3.

---

## Dateistruktur

| Datei | Verantwortung | Aenderung |
|---|---|---|
| `verbesserer/ruecktest.py` | Walk-Forward-Backtest | `ausrichten()` neu, `walk_forward()` ruft sie auf; `holdout()` neu |
| `verbesserer/suche.py` | Koordinatenabstieg + Sperren | `suche()` um Ausrichten/Abschneiden/Holdout-Sperre erweitert, neuer Param `holdout_fn` |
| `verbesserer/konfig.json` | Modulparameter | `holdout_tage: 60`, `holdout_min_runden: 8`, Erklaertext `_oos_fenster_ziel` 480→540 |
| `verbesserer/lauf.py` | Orchestrator | Ausrichten + Hinweise melden, `tage` + `holdout_tage`, `fast_kandidat` an digest |
| `verbesserer/digest.py` | LLM-Annotation | `erzeuge`/`_prompt` optionaler `fast_kandidat` |
| `verbesserer/tests/test_ausrichten.py` | neu | F7-Tests |
| `verbesserer/tests/test_holdout.py` | neu | F4-Tests (`ruecktest.holdout` + `suche()`-Integration) |
| `MaxHirn/Wissen/Verbesserer.md`, `MaxHirn/Wissen/INDEX.md` | Wissen | F7/F4 nachziehen |

---

## Task 1: F7 — `ausrichten()` in `ruecktest.py` + Einhaengen in `walk_forward()` und `lauf.py`

**STATUS: ERLEDIGT** (Commit `a0f4d6ad`, 108/108 Tests gruen, Ledger `.superpowers/sdd/plan-verbesserer-stufe-1-5-2026-10-04/progress.md`).

---

## Task 2: F4 — `holdout()` in `ruecktest.py`

**Files:**
- Modify: `verbesserer/ruecktest.py` (neue Funktion `holdout`, nach `walk_forward()`)
- Test: `verbesserer/tests/test_holdout.py` (neu — Teil 1: die Funktion)

**Interfaces:**
- Consumes: `ausrichten` (Task 1), `merkmals_matrix`, `simuliere`, `kennzahlen` (Bestand).
- Produces: `holdout(kerzen_je_inst, kandidat, holdout_tage) -> dict` (das `kennzahlen()`-Dict eines einzelnen Blocks `simuliere(matrix, ..., L - holdout_tage, L)`, `L = min(len(k))` der — als bereits ausgerichtet erwarteten — Reihen).

- [ ] **Step 1: Failing test schreiben** — `verbesserer/tests/test_holdout.py` (Teil 1)

```python
"""F4: holdout() misst einen Kandidaten auf einem einzelnen Endblock, und
suche() lehnt einen Sieger ab, der den Holdout nicht besteht."""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import bewertung  # noqa: E402
import ruecktest  # noqa: E402
import suche  # noqa: E402


def _kerzen(n):
    """Saegezahn wie test_ruecktest_wf, lueckenlose Tage."""
    k, p = [], 100.0
    for i in range(n):
        p *= 1.0 + (0.01 if (i // 5) % 2 else -0.009)
        k.append([i * 86400000, p, p * 1.03, p * 0.97, p, 1000.0])
    return k


KAND = {
    "gates": {"mindest_score": 0.0, "max_volatilitaet_pa": 9.0,
              "mindest_chance_risiko": 0.0, "stop_min": 4.0, "stop_max": 12.0,
              "abklingzeit_tage": 3, "max_offene_positionen": 4,
              "max_gesamt_usd": 200.0, "max_pro_trade_usd": 50.0},
    "gewichte": None, "watchlist": ["AAA"], "sizing": "flach",
}


class TestHoldoutFunktion(unittest.TestCase):
    def test_holdout_liefert_kennzahlen_des_endblocks(self):
        kz = ruecktest.holdout({"AAA": _kerzen(240)}, KAND, 60)
        # kennzahlen()-Form: n und netto_gv_je_runde sind vorhanden.
        self.assertIn("n", kz)
        self.assertIn("netto_gv_je_runde", kz)

    def test_holdout_block_ist_nur_die_letzten_H_tage(self):
        # Ein Kandidat ohne moeglichen Einstieg (mindest_score unerreichbar)
        # liefert n == 0 - der Block rechnet, wirft nicht.
        stumm = {**KAND, "gates": {**KAND["gates"], "mindest_score": 999.0}}
        kz = ruecktest.holdout({"AAA": _kerzen(240)}, stumm, 60)
        self.assertEqual(kz["n"], 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen, Fehlschlag bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_holdout.py`
Expected: FAIL mit `AttributeError: module 'ruecktest' has no attribute 'holdout'`

- [ ] **Step 3: `holdout()` implementieren** — in `ruecktest.py`, direkt nach `walk_forward()` einfuegen

```python
def holdout(kerzen_je_inst, kandidat, holdout_tage):
    """Ein einzelner OOS-Block ueber die letzten ``holdout_tage`` Tage.

    Erwartet bereits ausgerichtete Reihen (alle gleich lang; ``suche`` richtet
    einmal aus). Rechnet ``simuliere()`` ueber ``[L - holdout_tage, L)`` mit
    ``L = min(len(k))`` und gibt ``kennzahlen()`` zurueck. ``kennzahlen([])``
    ist sicher (n = 0), ein leerer Block scheitert also sauber an der
    ``holdout_min_runden``-Pruefung in ``suche``.
    """
    laenge = min((len(k) for k in kerzen_je_inst.values()), default=0)
    matrix = merkmals_matrix(kerzen_je_inst)
    runden = simuliere(matrix, kerzen_je_inst, kandidat,
                       laenge - holdout_tage, laenge)
    return kennzahlen(runden)
```

- [ ] **Step 4: Test laufen, gruen bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_holdout.py`
Expected: PASS (2 Tests)

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/verbesserer/ruecktest.py Agenten/Handel/verbesserer/tests/test_holdout.py
git commit
```
Botschaft: `Verbesserer F4: holdout() - einzelner OOS-Endblock`

---

## Task 3: F4 — Holdout-Sperre in `suche.suche()` + `konfig.json` + `lauf.py`-Historie

**Files:**
- Modify: `verbesserer/suche.py` (`suche()`, Signatur + Docstring + Rumpf + Rueckgabe)
- Modify: `verbesserer/konfig.json` (zwei Schluessel, ein Erklaertext)
- Modify: `verbesserer/lauf.py` (`tage`-Berechnung)
- Test: `verbesserer/tests/test_holdout.py` (Teil 2 — `suche()`-Integration, an die Datei aus Task 2 anhaengen)

**Interfaces:**
- Consumes: `ruecktest.ausrichten`, `ruecktest.holdout` (Tasks 1/2); `konfig["holdout_tage"]`, `konfig["holdout_min_runden"]`.
- Produces: `suche(basis, kerzen_je_inst, konfig, grenzen, bewerte=None, holdout_fn=None)`. Neue Rueckgabe-Felder: `holdout_basis`, `holdout_kandidat` (kennzahlen-Dict oder `None`), `fast_kandidat` (abgelehnter Sieger-Kandidat oder `None`). Bei Holdout-Fehlschlag: `kandidat=None`, `grund="Holdout nicht bestanden"`, `fast_kandidat` gesetzt, `kandidat_wf=None`, `aenderungen={}`. Bei zu wenig Historie: `kandidat=None`, `grund="zu wenig Historie fuer Holdout"`. Alte Felder bleiben unveraendert; bei `holdout_tage == 0` sind die drei neuen Felder `None`.

- [ ] **Step 1: Failing tests schreiben** — an `verbesserer/tests/test_holdout.py` anhaengen (vor `if __name__`)

```python
WACHEN = {"mindest_score": 60, "max_volatilitaet_pa": 1.2,
          "mindest_chance_risiko": 1.5, "pflicht_stop_prozent_min": 4.0,
          "pflicht_stop_prozent_max": 12.0, "abklingzeit_tage": 3,
          "max_pro_trade_usd": 50, "max_gesamt_usd": 200,
          "max_offene_positionen": 4,
          "watchlist": ["BTC-USDT", "ETH-USDT", "SOL-USDT"]}
GRENZEN = {"mindest_score": [55, 75], "max_volatilitaet_pa": [0.9, 1.4],
           "mindest_chance_risiko": [1.3, 2.2], "stop_min": [4, 8],
           "stop_max": [8, 15], "abklingzeit_tage": [2, 5], "watchlist": "liste"}
# Holdout aktiv; Historie reicht (240 - 60 = 180 >= 120 + 3*30 = 210? nein ->
# darum oos_test_tage klein halten fuer den Historie-Test unten gesondert).
KONF_HOLDOUT = {"such_budget": 50, "overfit_min_runden": 20,
                "overfit_min_fenster": 3, "oos_training_tage": 120,
                "oos_test_tage": 30, "oos_schritt_tage": 30,
                "holdout_tage": 60, "holdout_min_runden": 8}


def _wf(gv_je_runde, n=30, fenster_besser=0, basis_gv=0.0, fenster_anz=5):
    fenster = []
    for i in range(fenster_anz):
        g = gv_je_runde if i < fenster_besser else basis_gv
        fenster.append({"von_tag": 120 + 30 * i, "bis_tag": 150 + 30 * i,
                        "kennzahlen": {"n": n // fenster_anz,
                                       "netto_gv_je_runde": g}})
    return {"fenster": fenster, "fenster_anzahl": fenster_anz,
            "gesamt": {"n": n, "netto_gv_je_runde": gv_je_runde}}


def _kz(netto, n):
    return {"n": n, "netto_gv_je_runde": netto}


class TestHoldoutInSuche(unittest.TestCase):
    def setUp(self):
        self.basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)
        # Genug Historie: ein Instrument, L = 400 Tage > 60 + 210.
        self.kerzen = {"AAA": _kerzen(400)}

    def _sieger_fake(self):
        """bewerte: Basis schlecht, jeder Nachbar schlaegt sie in 4/5 Fenstern
        und hat >= 20 Runden -> ein Sieger kommt durch alle Altsperren."""
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=30, fenster_besser=0)
            return _wf(1.0, n=30, fenster_besser=4)
        return fake

    def test_holdout_verlust_wird_abgelehnt_fast_kandidat_gesetzt(self):
        # Sieger gewinnt die Suche, verliert aber im Holdout (Kandidat <= Basis).
        def hold(kerzen, kand, h):
            return _kz(-0.5, 12) if kand != self.basis else _kz(0.0, 12)
        r = suche.suche(self.basis, self.kerzen, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=hold)
        self.assertIsNone(r["kandidat"])
        self.assertEqual(r["grund"], "Holdout nicht bestanden")
        self.assertIsNotNone(r["fast_kandidat"])
        self.assertIsNone(r["kandidat_wf"])

    def test_echter_gewinn_laeuft_durch(self):
        def hold(kerzen, kand, h):
            return _kz(2.0, 12) if kand != self.basis else _kz(0.0, 12)
        r = suche.suche(self.basis, self.kerzen, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=hold)
        self.assertIsNotNone(r["kandidat"])
        self.assertIsNone(r["fast_kandidat"])
        self.assertEqual(r["holdout_kandidat"]["netto_gv_je_runde"], 2.0)

    def test_zu_wenige_runden_im_holdout_wird_abgelehnt(self):
        # Kandidat besser, aber n < holdout_min_runden (8).
        def hold(kerzen, kand, h):
            return _kz(2.0, 7) if kand != self.basis else _kz(0.0, 7)
        r = suche.suche(self.basis, self.kerzen, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=hold)
        self.assertIsNone(r["kandidat"])
        self.assertEqual(r["grund"], "Holdout nicht bestanden")

    def test_grenze_genau_min_runden_besteht(self):
        def hold(kerzen, kand, h):
            return _kz(2.0, 8) if kand != self.basis else _kz(0.0, 8)
        r = suche.suche(self.basis, self.kerzen, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=hold)
        self.assertIsNotNone(r["kandidat"])

    def test_zu_wenig_historie(self):
        # L = 150 Tage: 150 - 60 = 90 < 120 + 3*30 = 210 noetig.
        r = suche.suche(self.basis, {"AAA": _kerzen(150)}, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=lambda *a: _kz(0, 0))
        self.assertIsNone(r["kandidat"])
        self.assertEqual(r["grund"], "zu wenig Historie fuer Holdout")
```

- [ ] **Step 2: Test laufen, Fehlschlag bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_holdout.py`
Expected: FAIL — `suche()` nimmt `holdout_fn` noch nicht bzw. liefert die neuen Felder/Gruende nicht.

- [ ] **Step 3: `suche()`-Signatur und frühen Holdout-Block einbauen**

Signatur ersetzen:
```python
def suche(basis, kerzen_je_inst, konfig, grenzen, bewerte=None):
```
durch:
```python
def suche(basis, kerzen_je_inst, konfig, grenzen, bewerte=None, holdout_fn=None):
```

Direkt nach dem `bewerte`-Default-Block (`bewerte = ruecktest.walk_forward`) einfuegen:
```python
    holdout_tage = konfig.get("holdout_tage", 0)
    kerzen_holdout = kerzen_je_inst
    zu_wenig_historie = False
    if holdout_tage > 0:
        import ruecktest
        if holdout_fn is None:
            holdout_fn = ruecktest.holdout
        kerzen_je_inst, _hinw = ruecktest.ausrichten(kerzen_je_inst)
        kerzen_holdout = kerzen_je_inst
        laenge = min((len(k) for k in kerzen_je_inst.values()), default=0)
        noetig = (konfig["oos_training_tage"]
                  + konfig["overfit_min_fenster"] * konfig["oos_test_tage"])
        if laenge - holdout_tage < noetig:
            zu_wenig_historie = True
        else:
            kerzen_je_inst = {inst: k[:laenge - holdout_tage]
                              for inst, k in kerzen_je_inst.items()}
```
(Alle folgenden `bewerte(kerzen_je_inst, ...)`-Aufrufe im Abstieg nutzen damit die abgeschnittene Reihe; der Holdout-Block misst spaeter auf `kerzen_holdout`. Bei `holdout_tage == 0` bleibt `kerzen_je_inst` unveraendert — Bestandsverhalten.)

- [ ] **Step 4: Historie-Abbruch vor dem Abstieg behandeln** — unmittelbar nach dem Block aus Step 3

```python
    if zu_wenig_historie:
        return {
            "kandidat": None, "basis_wf": None, "kandidat_wf": None,
            "auswertungen": 0, "grund": "zu wenig Historie fuer Holdout",
            "aenderungen": {}, "holdout_basis": None, "holdout_kandidat": None,
            "fast_kandidat": None,
        }
```

- [ ] **Step 5: Holdout-Sperre nach den Altsperren + Rueckgabe erweitern**

Den bestehenden `else:`-Zweig (der den Kandidaten annimmt) und die anschliessende `return`-Anweisung ersetzen.

Alt:
```python
    else:
        kandidat = bestes
        grund = (f"Vorschlag: schlaegt Basis im Aggregat und in {k_fenster} "
                 f"Fenstern ({n_runden} OOS-Runden)")

    return {
        "kandidat": kandidat,
        "basis_wf": basis_wf,
        "kandidat_wf": bestes_wf if kandidat is not None else None,
        "auswertungen": auswertungen,
        "grund": grund,
        "aenderungen": _aenderungen(kandidat, basis) if kandidat is not None else {},
    }
```
Neu:
```python
    else:
        kandidat = bestes
        grund = (f"Vorschlag: schlaegt Basis im Aggregat und in {k_fenster} "
                 f"Fenstern ({n_runden} OOS-Runden)")

    # Zusaetzliche Sperre: der Sieger muss einen Block bestehen, den die Suche
    # nie gesehen hat. Kandidat und Basis auf demselben Holdout.
    holdout_basis = None
    holdout_kandidat = None
    fast_kandidat = None
    if kandidat is not None and holdout_tage > 0:
        holdout_basis = holdout_fn(kerzen_holdout, basis, holdout_tage)
        holdout_kandidat = holdout_fn(kerzen_holdout, kandidat, holdout_tage)
        bestanden = (holdout_kandidat["netto_gv_je_runde"]
                     > holdout_basis["netto_gv_je_runde"]
                     and holdout_kandidat["n"]
                     >= konfig.get("holdout_min_runden", 0))
        if not bestanden:
            fast_kandidat = kandidat
            kandidat = None
            grund = "Holdout nicht bestanden"

    return {
        "kandidat": kandidat,
        "basis_wf": basis_wf,
        "kandidat_wf": bestes_wf if kandidat is not None else None,
        "auswertungen": auswertungen,
        "grund": grund,
        "aenderungen": _aenderungen(kandidat, basis) if kandidat is not None else {},
        "holdout_basis": holdout_basis,
        "holdout_kandidat": holdout_kandidat,
        "fast_kandidat": fast_kandidat,
    }
```

- [ ] **Step 6: Docstring in `suche()` anpassen**

Den Satz „Auswahl und Pruefung teilen sich dieselbe Kennzahl ueber dieselben Fenster - ein echter Train/Test-Split fehlt, die Sperre ist entsprechend schwach." ersetzen durch:
```
    Mit ``holdout_tage > 0`` kommt eine weitere Sperre hinzu: die letzten
    ``holdout_tage`` Tage werden vor Suche und Walk-Forward abgeschnitten, und
    der Sieger muss die Basis auf diesem nie gesehenen Block schlagen
    (``netto_gv_je_runde`` hoeher, ``n >= holdout_min_runden``). Sonst
    ``kandidat=None``, ``grund="Holdout nicht bestanden"`` und ``fast_kandidat``
    gesetzt. Reicht ``L - holdout_tage`` nicht fuer ``oos_training_tage`` plus
    ``overfit_min_fenster`` Testfenster: ``grund="zu wenig Historie fuer
    Holdout"``.
```
Und den Rueckgabe-Satz um die drei neuen Felder ergaenzen:
```
    Rueckgabe: ``{"kandidat", "basis_wf", "kandidat_wf", "auswertungen",
    "grund", "aenderungen", "holdout_basis", "holdout_kandidat",
    "fast_kandidat"}``. ``bewerte`` ersetzt ``ruecktest.walk_forward`` und
    ``holdout_fn`` ersetzt ``ruecktest.holdout`` (fuer Tests); ohne werden sie
    traege importiert.
```

- [ ] **Step 7: `konfig.json` ergänzen** — gezielter Edit, nie Rewrite (JSON, CRLF/LF schonen)

Nach der Zeile `"overfit_min_fenster": 3,` einfuegen:
```json
  "holdout_tage": 60,
  "holdout_min_runden": 8,
```
Und den Erklaertext `_oos_fenster_ziel` anpassen: `(~480 Tageskerzen)` → `(~540 Tageskerzen, davon 60 Holdout)`.

- [ ] **Step 8: `lauf.py` zieht 60 Tage mehr Historie**

Alt:
```python
    tage = (konfig["oos_training_tage"]
            + konfig.get("oos_fenster_ziel", 12) * konfig["oos_test_tage"])
```
Neu:
```python
    tage = (konfig["oos_training_tage"]
            + konfig.get("oos_fenster_ziel", 12) * konfig["oos_test_tage"]
            + konfig.get("holdout_tage", 0))
```
(120 + 12·30 + 60 = 540.)

- [ ] **Step 9: Holdout-Tests laufen, gruen bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_holdout.py`
Expected: PASS (7 Tests: 2 aus Task 2 + 5 neu)

- [ ] **Step 10: Gesamte Suite laufen** — besonders `test_suche_lauf.py` (KONF ohne `holdout_tage`) und `test_konfig.py`

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests`
Expected: PASS (alle). `test_suche_lauf.py` bleibt gruen, weil `holdout_tage` dort fehlt → Pfad aus.

- [ ] **Step 11: Commit**

```bash
git add Agenten/Handel/verbesserer/suche.py Agenten/Handel/verbesserer/konfig.json Agenten/Handel/verbesserer/lauf.py Agenten/Handel/verbesserer/tests/test_holdout.py
git commit
```
Botschaft: `Verbesserer F4: Holdout-Sperre in suche() + konfig + Historie`

---

## Task 4: F4 — `fast_kandidat` im Digest

**Files:**
- Modify: `verbesserer/digest.py` (`_prompt`, `erzeuge`)
- Modify: `verbesserer/lauf.py` (`digest.erzeuge`-Aufruf)
- Test: `verbesserer/tests/test_digest.py` (ein Test anhaengen)

**Interfaces:**
- Consumes: `suche()`-Rueckgabefeld `fast_kandidat` (Task 3).
- Produces: `erzeuge(befund, basis_wf, kandidat_wf, aenderungen, llm_konf, ruf=None, fast_kandidat=None)`; `_prompt(..., fast_kandidat=None)`. Abwaertskompatibel (neuer Parameter keyword-only am Ende; alle Bestandsaufrufe positional bleiben gueltig).

- [ ] **Step 1: Failing test schreiben** — an `test_digest.py` anhaengen

```python
    def test_fast_kandidat_im_prompt(self):
        gesehen = {}

        def ruf(prompt, konf):
            gesehen["prompt"] = prompt
            return "1. ok\n\nLEHREN: ok."
        digest.erzeuge(BEFUND, BASIS, None, {}, {"modus": "ollama"},
                       ruf=ruf, fast_kandidat={"gates": {}})
        self.assertIn("Holdout", gesehen["prompt"])

    def test_ohne_fast_kandidat_kein_holdout_hinweis(self):
        gesehen = {}

        def ruf(prompt, konf):
            gesehen["prompt"] = prompt
            return "1. ok\n\nLEHREN: ok."
        digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "ollama"}, ruf=ruf)
        self.assertNotIn("Holdout", gesehen["prompt"])
```

- [ ] **Step 2: Test laufen, Fehlschlag bestaetigen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests -p test_digest.py`
Expected: FAIL — `erzeuge` kennt `fast_kandidat` nicht (`TypeError: unexpected keyword argument`).

- [ ] **Step 3: `_prompt` um den Hinweis erweitern**

Signatur ersetzen:
```python
def _prompt(befund, basis_wf, kandidat_wf, aenderungen):
```
durch:
```python
def _prompt(befund, basis_wf, kandidat_wf, aenderungen, fast_kandidat=None):
```
Vor `return "\n".join(zeilen)` einfuegen:
```python
    if fast_kandidat:
        zeilen.append(
            "Hinweis: Ein Kandidat schlug die Basis in der Suche, fiel aber im "
            "Holdout durch - deshalb kein Vorschlag. Nur annotieren, nicht "
            "anwenden.")
```

- [ ] **Step 4: `erzeuge` den Parameter durchreichen**

Signatur ersetzen:
```python
def erzeuge(befund, basis_wf, kandidat_wf, aenderungen, llm_konf, ruf=None):
```
durch:
```python
def erzeuge(befund, basis_wf, kandidat_wf, aenderungen, llm_konf, ruf=None,
            fast_kandidat=None):
```
`_prompt`-Aufruf ersetzen:
```python
        text = ruf(_prompt(befund, basis_wf, kandidat_wf, aenderungen),
                   llm_konf)
```
durch:
```python
        text = ruf(_prompt(befund, basis_wf, kandidat_wf, aenderungen,
                           fast_kandidat), llm_konf)
```

- [ ] **Step 5: `lauf.py` gibt `fast_kandidat` weiter**

Alt:
```python
    d = digest.erzeuge(befund, ergebnis["basis_wf"], ergebnis["kandidat_wf"],
                       ergebnis.get("aenderungen", {}), konfig["llm"])
```
Neu:
```python
    d = digest.erzeuge(befund, ergebnis["basis_wf"], ergebnis["kandidat_wf"],
                       ergebnis.get("aenderungen", {}), konfig["llm"],
                       fast_kandidat=ergebnis.get("fast_kandidat"))
```

- [ ] **Step 6: Digest-Tests + gesamte Suite laufen**

Run: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests`
Expected: PASS (alle; `test_digest.py` jetzt mit 2 neuen Tests).

- [ ] **Step 7: Commit**

```bash
git add Agenten/Handel/verbesserer/digest.py Agenten/Handel/verbesserer/lauf.py Agenten/Handel/verbesserer/tests/test_digest.py
git commit
```
Botschaft: `Verbesserer F4: Digest annotiert abgelehnten fast_kandidat`

---

## Task 5: Wissen nachziehen — `Verbesserer.md` + `INDEX.md`

**Files:**
- Modify: `MaxHirn/Wissen/Verbesserer.md` (Bereich `wissen` — BEFUND melden)
- Modify: `MaxHirn/Wissen/INDEX.md` (falls Verbesserer-Eintrag Stand/Beschreibung traegt)

**Interfaces:** keine (reine Doku).

- [ ] **Step 1: `Verbesserer.md` lesen** — aktuellen Stand und Abschnittsstruktur erfassen

- [ ] **Step 2: Bereichs-Konflikt melden** (schreibender Zugriff in Bereich `wissen`)

Run: `python Agenten/Werkzeuge/bereiche.py --aufrufer handel --pfad MaxHirn/Wissen/Verbesserer.md`
(Exitcode 1 = BEFUND, wird gemeldet, nicht blockiert.)

- [ ] **Step 3: F7/F4 als erledigt eintragen** — gezielter Ersatz (CRLF/LF der Datei beachten)

Inhaltlich zu ergaenzen (knapp, Hausstil):
- **F7:** Kerzen werden in `ruecktest.ausrichten()` ueber den Kalendertag (`ts // 86400000`) ausgerichtet; `walk_forward()` ruft sie selbst auf (idempotent), `lauf.py` meldet die Hinweise und bricht unter 3 Instrumenten ab. Ein zu junges Listing (< 90 % der Tage des laengsten) faellt mit Hinweis heraus statt die Watchlist zu kuerzen.
- **F4:** `suche()` schneidet mit `holdout_tage: 60` die letzten 60 Tage vor Suche und Walk-Forward ab und misst Sieger und Basis genau einmal auf diesem Holdout-Block; Bestehen verlangt hoeheres `netto_gv_je_runde` und `n >= holdout_min_runden` (8). Fehlschlag → kein Vorschlag, `fast_kandidat` nur im Digest annotiert. `lauf.py` zieht dafuer 540 statt 480 Tageskerzen.
- Falls ein „vertagt"-Block existiert: F7 und F4 dort als erledigt markieren (Datum 2026-10-07), Spur 2/3 bleibt offen.

- [ ] **Step 4: `INDEX.md` abgleichen** — nur wenn der Verbesserer-Eintrag einen Stand/Datum oder eine Kurzbeschreibung traegt, die sich geaendert hat. Sonst unveraendert lassen.

- [ ] **Step 5: Index-/Vault-Pruefung**

Run: `pwsh Agenten/Routinen/wissen-index-pruefen.ps1`
Expected: keine Fehler zu `Verbesserer.md`.

- [ ] **Step 6: Commit**

```bash
git add MaxHirn/Wissen/Verbesserer.md MaxHirn/Wissen/INDEX.md
git commit
```
Botschaft: `Wissen: Verbesserer F7/F4 (Stufe 1.5) erledigt`

---

## Danach (nicht Teil dieses Plans)

Ausbaustufe 2 (Spur 2 XPERP: Margin/Funding/Liquidation; Spur 3 Kraken-EUR, 0,80 % je Runde) als eigenes Brainstorming mit eigener Spec.
