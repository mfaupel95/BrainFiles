# Selbstverbessernder Handelsagent — Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine wöchentliche Schleife, die aus Handelsjournal und Kurshistorie begründete, out-of-sample geprüfte Vorschläge für bessere Scanner-Parameter erzeugt und sie nach `/ja` per Telegram anwendet und committet.

**Architecture:** Eigenständiges Modul `Agenten/Handel/verbesserer/` (stdlib-only venv). Kette: Kerzen holen → Auswerter (Journal-Segmente) → Walk-Forward-Backtest mit vorberechneter Merkmals-Matrix → Koordinatenabstieg mit Overfitting-Sperre → Vorschlags-Artefakte → LLM-Digest → `dauerlauf.py` fragt per Telegram → `anwenden.py` prüft Denylist, sichert `.bak`, wendet CRLF-schonend an, committet einzeln.

**Tech Stack:** Python 3.13, nur Standardbibliothek (`urllib`, `json`, `csv`, `difflib`, `subprocess`, `unittest`). PowerShell für die Routine. Git für die Anwendung.

**Spec:** `Werkstatt/spec-selbstverbessernder-handelsagent-2026-09-06.md`

## Global Constraints

- **Kein Deckel wird angehoben.** `max_pro_trade_usd`, `max_gesamt_usd`, `max_offene_positionen` sind nie im Suchraum und stehen auf der Denylist.
- **Denylist (fest im Code von `anwenden.py`, schlägt jede Whitelist):** `handel_erlaubt`, `freigabe`, `drawdown_halbierung_prozent`, `kill_switch_gesamt_usd`, `herzschlag_max_minuten`, `journal_zweitziel`, `max_pro_trade_usd`, `max_gesamt_usd`, `max_offene_positionen`.
- **Das Modul schreibt `wachen.json` nie per `json.dump`.** Nur gezielte Text-Ersetzung des betroffenen Werts, damit CRLF erhalten bleibt (Vault-Regel, Memory `crlf-im-vault`).
- **Jede angewandte Änderung ist ein eigener Commit** — nur die betroffenen Dateien gestaged, nie mit anderer Arbeit gebündelt, die vier Pflichtzahlen in der Nachricht.
- **Commit-Nachrichten enden mit** `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
- **`auto_anwenden` bleibt `false`.** Der autonome Zweig wird nicht scharf geschaltet und nicht getestet.
- **`GEBUEHR_PCT = 0.0005`** (OKX Taker, gemessen 02.09.2026) — je Handelsseite, identisch in `scanner/handeln.py` und `verbesserer/kosten.py`.
- **Tests laufen mit** `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v`.
- **Alle neuen Dateien tragen deutsche Namen und Kommentare**, wie die übrigen Handelsmodule.

---

## Dateistruktur

| Datei | Verantwortung |
|---|---|
| `Agenten/Handel/verbesserer/konfig.json` | Modulweite Parameter (OOS-Fenster, Budget, LLM, Overfitting-Schwellen) |
| `Agenten/Handel/verbesserer/spuren.json` | Je Spur: Pfade + Whitelist änderbarer Schlüssel mit Wertebereichen |
| `Agenten/Handel/verbesserer/kosten.py` | Nur die Konstante `GEBUEHR_PCT` |
| `Agenten/Handel/verbesserer/kerzen.py` | OKX-Tageshistorie paginiert holen, Cache unter `kerzen/` |
| `Agenten/Handel/verbesserer/auswerter.py` | Geschlossene Runden aus dem Journal segmentieren, Permutationstest, Befund-JSON |
| `Agenten/Handel/verbesserer/ruecktest.py` | Merkmals-Matrix, Kandidaten-Simulation, Walk-Forward-Aggregation |
| `Agenten/Handel/verbesserer/suche.py` | Kandidatenraum + Grenzen, Koordinatenabstieg, Overfitting-Sperre |
| `Agenten/Handel/verbesserer/vorschlag.py` | `bericht.md`, `wachen.neu.json`, `bewertung.patch`, `commit.txt` bauen |
| `Agenten/Handel/verbesserer/digest.py` | Wöchentlicher LLM-Aufruf, Bericht annotieren, Lehren anhängen |
| `Agenten/Handel/verbesserer/anwenden.py` | Denylist-Prüfung, `.bak`, CRLF-schonendes Anwenden, Einzel-Commit, Ablehnen |
| `Agenten/Handel/verbesserer/lauf.py` | Orchestrator, `--spur spur1` |
| `Agenten/Handel/verbesserer/README.md` | Wie die anderen Modul-READMEs |
| `Agenten/Handel/verbesserer/tests/*.py` | unittest je Modul |
| `Agenten/Handel/scanner/bewertung.py` | *(ändern)* optionaler `gewichte`-Parameter + `roh_komponenten()` |
| `Agenten/Handel/scanner/handeln.py` | *(ändern)* `GEBUEHR_PCT` im Papierpfad |
| `Agenten/Handel/dauerlauf.py` | *(ändern)* Anfrage-Typ `verbesserung` |
| `Agenten/Routinen/verbesserer.ps1` | Wöchentliche Routine |
| `.gitignore` | *(ändern)* Whitelist-Zeilen fürs Modul |

---

## Task 0: Modul-Gerüst, venv, Konfig, .gitignore

**Files:**
- Create: `Agenten/Handel/verbesserer/konfig.json`
- Create: `Agenten/Handel/verbesserer/spuren.json`
- Create: `Agenten/Handel/verbesserer/kosten.py`
- Create: `Agenten/Handel/verbesserer/requirements.txt` (leer bis auf Kommentar — nur stdlib)
- Create: `Agenten/Handel/verbesserer/tests/__init__.py` (leer)
- Create: `Agenten/Handel/verbesserer/tests/test_konfig.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `konfig.json` und `spuren.json` mit den unten festgelegten Schlüsseln; `kosten.GEBUEHR_PCT: float`.

- [ ] **Step 1: venv anlegen**

```bash
cd "Agenten/Handel/verbesserer" && py -3.13 -m venv .venv
```
Erwartet: Ordner `.venv/Scripts/python.exe` existiert. (Fällt `py -3.13` aus, `python -m venv .venv` mit der Version, die `scanner/.venv` nutzt.)

- [ ] **Step 2: `kosten.py` schreiben**

```python
"""Die eine Gebuehrenzahl fuer Backtest und Angleichung von handeln.py.

0,05 % OKX Taker bei Volumen < 10.000, gemessen 02.09.2026 (Handelsregeln.md).
Identisch in scanner/handeln.py - test_kosten_gleich.py prueft das.
"""

GEBUEHR_PCT = 0.0005
```

- [ ] **Step 3: `konfig.json` schreiben**

```json
{
  "_zweck": "Modulweite Parameter des Verbesserers. Von Hand geaendert.",
  "auto_anwenden": false,
  "_auto_anwenden": "false = jeder Vorschlag geht per Telegram an Max. true braucht eine Aenderung an Handelsregeln.md und ist nicht gebaut.",
  "such_budget": 300,
  "oos_training_tage": 120,
  "oos_test_tage": 30,
  "oos_schritt_tage": 30,
  "segment_mindest_n": 8,
  "overfit_min_runden": 20,
  "overfit_min_fenster": 3,
  "gebuehr_umstellung_datum": "2026-09-06",
  "llm": {
    "modus": "aus",
    "_modus": "aus | ollama | cliproxy",
    "timeout_s": 60,
    "ollama": { "url": "http://localhost:11434", "modell": "llama3.1:8b" },
    "cliproxy": { "base_url_env": "CLIPROXY_BASE_URL", "schluessel_env": "CLIPROXY_API_KEY", "modell": "claude-sonnet-5" }
  }
}
```

- [ ] **Step 4: `spuren.json` schreiben**

```json
{
  "_zweck": "Je Spur: Pfade zu ihren Dateien und die Whitelist der Schluessel, die ein Vorschlag anfassen darf - mit erlaubtem Wertebereich. Deckel stehen NICHT hier, sie sind in anwenden.py fest gesperrt.",
  "spur1": {
    "name": "Scanner/OKX",
    "journal": "../scanner/handelsjournal.csv",
    "zustand": "../scanner/zustand.json",
    "wachen": "../scanner/wachen.json",
    "berichte": "../scanner/berichte",
    "bewertung_datei": "../scanner/bewertung.py",
    "waehrung": "USD",
    "aenderbar": {
      "wachen.json": {
        "mindest_score": [55, 75],
        "max_volatilitaet_pa": [0.9, 1.4],
        "mindest_chance_risiko": [1.3, 2.2],
        "pflicht_stop_prozent_min": [4, 8],
        "pflicht_stop_prozent_max": [8, 15],
        "abklingzeit_tage": [2, 5],
        "watchlist": "liste"
      },
      "bewertung.py": {
        "CHANCE_GEWICHTE": [0.0, 0.5],
        "RISIKO_GEWICHTE": [0.0, 0.5]
      }
    }
  }
}
```

- [ ] **Step 5: `requirements.txt` schreiben**

```
# Nur Standardbibliothek. Eigenes venv, damit die Python-Version an ihren
# Pfad gebunden ist - wie scanner/.venv. Siehe Wissen/Python-Versionen.md.
```

- [ ] **Step 6: Failing test schreiben** — `tests/test_konfig.py`

```python
import json
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parents[1]


class TestKonfig(unittest.TestCase):
    def test_konfig_hat_pflichtschluessel(self):
        k = json.loads((HIER / "konfig.json").read_text("utf-8"))
        for s in ("auto_anwenden", "such_budget", "oos_training_tage",
                  "oos_test_tage", "oos_schritt_tage", "segment_mindest_n",
                  "overfit_min_runden", "overfit_min_fenster",
                  "gebuehr_umstellung_datum", "llm"):
            self.assertIn(s, k)
        self.assertIs(k["auto_anwenden"], False)
        self.assertEqual(k["oos_training_tage"], 120)
        self.assertEqual(k["oos_test_tage"], 30)

    def test_spuren_spur1_vollstaendig(self):
        s = json.loads((HIER / "spuren.json").read_text("utf-8"))["spur1"]
        for p in ("journal", "zustand", "wachen", "berichte", "bewertung_datei"):
            self.assertIn(p, s)
        self.assertIn("watchlist", s["aenderbar"]["wachen.json"])

    def test_gebuehr_konstante(self):
        import sys
        sys.path.insert(0, str(HIER))
        import kosten
        self.assertEqual(kosten.GEBUEHR_PCT, 0.0005)
```

- [ ] **Step 7: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v`
Erwartet: FAIL / ERROR — Dateien fehlen noch (falls Steps 2–4 schon geschrieben: PASS; dann Reihenfolge tauschen und Test zuerst rot sehen, indem eine Datei kurz umbenannt wird).

- [ ] **Step 8: `.gitignore` erweitern**

Unter Abschnitt „5) Eigene Programme" nach den `kraken/`-Zeilen einfügen:

```
!Agenten/Handel/verbesserer/*.py
!Agenten/Handel/verbesserer/*.md
!Agenten/Handel/verbesserer/*.json
!Agenten/Handel/verbesserer/requirements.txt
!Agenten/Handel/verbesserer/tests/*.py
```

Unter Abschnitt „8) Rueckausnahmen" nach dem XPERP-Block einfügen:

```
# Verbesserer: laufender Zustand. konfig.json und spuren.json sind oben
# freigegeben (Konfiguration von Hand), diese drei schreibt jeder Lauf.
Agenten/Handel/verbesserer/kerzen/**
Agenten/Handel/verbesserer/berichte/**
Agenten/Handel/verbesserer/bak/**
```

- [ ] **Step 9: Test läuft grün**

Run: wie Step 7
Erwartet: PASS (3 Tests)

- [ ] **Step 10: `git status` prüfen — nur Modul-Dateien und `.gitignore`**

Run: `git status --porcelain`
Erwartet: nur `Agenten/Handel/verbesserer/…` und `.gitignore`. `.venv/` taucht nicht auf (durch `**/.venv/**`).

- [ ] **Step 11: Commit**

```bash
git add .gitignore Agenten/Handel/verbesserer/konfig.json Agenten/Handel/verbesserer/spuren.json Agenten/Handel/verbesserer/kosten.py Agenten/Handel/verbesserer/requirements.txt Agenten/Handel/verbesserer/tests/__init__.py Agenten/Handel/verbesserer/tests/test_konfig.py
git commit -m "$(printf 'verbesserer: Modul-Geruest, Konfig, venv\n\nspuren.json haelt je Spur Pfade und die Whitelist aenderbarer Schluessel\nmit Wertebereichen. konfig.json die OOS-Fenster (120/30/30), das Suchbudget\nund den LLM-Block (modus=aus). auto_anwenden=false.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 1: `bewertung.py` — `gewichte`-Parameter und `roh_komponenten()`

**Files:**
- Modify: `Agenten/Handel/scanner/bewertung.py`
- Create: `Agenten/Handel/verbesserer/tests/test_bewertung_refactor.py`

**Interfaces:**
- Consumes: nichts.
- Produces:
  - `bewertung.CHANCE_GEWICHTE: dict[str,float]` mit Schlüsseln `trend, momentum, ruecksetzer, nicht_ueberkauft, volumen` (Summe 1,0).
  - `bewertung.RISIKO_GEWICHTE: dict[str,float]` mit Schlüsseln `vola, drawdown, extrem_rsi, absturz_momentum` (Summe 1,0).
  - `bewertung.roh_komponenten(kerzen) -> dict` mit Schlüsseln `c_trend, c_momentum, c_ruecksetzer, c_nicht_ueberkauft, c_volumen, r_vola, r_drawdown, r_extrem_rsi, r_absturz_momentum, vola_pa, preis` (alle `float`, ungerundet).
  - `bewertung.bewerten(kerzen, gewichte=None) -> dict` — `gewichte` ist `None` oder `{"chance": {...}, "risiko": {...}}`; `None` nutzt die Modulkonstanten. Rückgabe unverändert zur heutigen Form.

- [ ] **Step 1: Failing test schreiben** — `tests/test_bewertung_refactor.py`

```python
import sys
import unittest
from pathlib import Path

SCANNER = Path(__file__).resolve().parents[2] / "scanner"
sys.path.insert(0, str(SCANNER))
import bewertung  # noqa: E402


def _kerzen(n=160):
    # sanft steigende Reihe mit etwas Zappeln, deterministisch
    k = []
    p = 100.0
    for i in range(n):
        p *= 1.0 + (0.004 if i % 3 else -0.003)
        hoch, tief = p * 1.01, p * 0.99
        k.append([i * 86400000, p * 0.999, hoch, tief, p, 1000.0 + i])
    return k


class TestRefactor(unittest.TestCase):
    def setUp(self):
        self.k = _kerzen()

    def test_gewichte_none_ist_wie_vorher(self):
        self.assertEqual(bewertung.bewerten(self.k),
                         bewertung.bewerten(self.k, gewichte=None))

    def test_konstanten_summieren_auf_eins(self):
        self.assertAlmostEqual(sum(bewertung.CHANCE_GEWICHTE.values()), 1.0, 9)
        self.assertAlmostEqual(sum(bewertung.RISIKO_GEWICHTE.values()), 1.0, 9)

    def test_roh_komponenten_rekombinieren_zum_score(self):
        r = bewertung.roh_komponenten(self.k)
        cg, rg = bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE
        chance = 100.0 * (cg["trend"] * r["c_trend"]
                          + cg["momentum"] * r["c_momentum"]
                          + cg["ruecksetzer"] * r["c_ruecksetzer"]
                          + cg["nicht_ueberkauft"] * r["c_nicht_ueberkauft"]
                          + cg["volumen"] * r["c_volumen"])
        risiko = 100.0 * (rg["vola"] * r["r_vola"]
                          + rg["drawdown"] * r["r_drawdown"]
                          + rg["extrem_rsi"] * r["r_extrem_rsi"]
                          + rg["absturz_momentum"] * r["r_absturz_momentum"])
        score = max(0.0, min(100.0, chance * (1.0 - 0.7 * risiko / 100.0)))
        self.assertAlmostEqual(score, bewertung.bewerten(self.k)["score"], 1)

    def test_andere_gewichte_aendern_score(self):
        g = {"chance": {"trend": 1.0, "momentum": 0.0, "ruecksetzer": 0.0,
                        "nicht_ueberkauft": 0.0, "volumen": 0.0},
             "risiko": dict(bewertung.RISIKO_GEWICHTE)}
        self.assertNotEqual(bewertung.bewerten(self.k, g)["score"],
                            bewertung.bewerten(self.k)["score"])
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k bewertung_refactor`
Erwartet: FAIL — `roh_komponenten` fehlt, `bewerten` nimmt kein `gewichte`.

- [ ] **Step 3: `bewertung.py` umbauen**

Oben die Konstanten einführen (Werte aus dem heutigen Code):

```python
CHANCE_GEWICHTE = {"trend": 0.30, "momentum": 0.28, "ruecksetzer": 0.16,
                   "nicht_ueberkauft": 0.14, "volumen": 0.12}
RISIKO_GEWICHTE = {"vola": 0.42, "drawdown": 0.28, "extrem_rsi": 0.16,
                   "absturz_momentum": 0.14}
```

`roh_komponenten(kerzen)` ist der heutige Rechenweg von `bewerten()` bis
einschließlich `r_absturz_momentum`, gibt aber das dict der elf Rohwerte
zurück statt zu gewichten:

```python
def roh_komponenten(kerzen):
    # ... exakt der bestehende Code von schluss=... bis r_absturz_momentum=... ,
    # KEINE Rundung ...
    return {
        "c_trend": c_trend, "c_momentum": c_momentum,
        "c_ruecksetzer": c_ruecksetzer,
        "c_nicht_ueberkauft": c_nicht_ueberkauft, "c_volumen": c_volumen,
        "r_vola": r_vola, "r_drawdown": r_drawdown,
        "r_extrem_rsi": r_extrem_rsi, "r_absturz_momentum": r_absturz_momentum,
        "vola_pa": vola_pa, "preis": preis,
    }
```

`bewerten()` wird zur dünnen Hülle:

```python
def bewerten(kerzen, gewichte=None):
    r = roh_komponenten(kerzen)
    cg = (gewichte or {}).get("chance") or CHANCE_GEWICHTE
    rg = (gewichte or {}).get("risiko") or RISIKO_GEWICHTE
    chance = 100.0 * (cg["trend"] * r["c_trend"]
                      + cg["momentum"] * r["c_momentum"]
                      + cg["ruecksetzer"] * r["c_ruecksetzer"]
                      + cg["nicht_ueberkauft"] * r["c_nicht_ueberkauft"]
                      + cg["volumen"] * r["c_volumen"])
    risiko = 100.0 * (rg["vola"] * r["r_vola"]
                      + rg["drawdown"] * r["r_drawdown"]
                      + rg["extrem_rsi"] * r["r_extrem_rsi"]
                      + rg["absturz_momentum"] * r["r_absturz_momentum"])
    score = max(0.0, min(100.0, chance * (1.0 - 0.7 * risiko / 100.0)))
    verhaeltnis = chance / max(risiko, 1.0)
    return {
        "preis": round(r["preis"], 6), "chance": round(chance, 1),
        "risiko": round(risiko, 1), "score": round(score, 1),
        "verhaeltnis": round(verhaeltnis, 2),
        "kennzahlen": {
            "trend_ueber_sma": round(r["c_trend"], 2),  # unveraendert zu heute
            # ... restliche kennzahlen wie bisher, aus den Rohwerten ...
        },
    }
```

Hinweis: der `kennzahlen`-Block muss Feld für Feld die heutigen Werte
liefern (`trend_ueber_sma`, `rendite_30t_pct`, `rsi14`, …). Falls ein
Kennzahlwert im heutigen Code aus einer Zwischengröße stammt, die
`roh_komponenten` nicht zurückgibt (z. B. `rsi`, `rendite_30`), diese
Größen ebenfalls ins dict aufnehmen (`_rsi14`, `_rendite_30` o. ä.) und in
`bewerten` verwenden. Der Regressionstest aus Step 1 deckt das ab.

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS (4 Tests)

- [ ] **Step 5: Scanner-Regression prüfen**

Run: `cd Agenten/Handel/scanner && .venv\Scripts\python.exe scan.py --kurz`
Erwartet: Rangliste rechnet ohne Fehler, Zahlen plausibel wie zuvor.

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/scanner/bewertung.py Agenten/Handel/verbesserer/tests/test_bewertung_refactor.py
git commit -m "$(printf 'scanner/bewertung: gewichte-Parameter und roh_komponenten()\n\nGewichte als Modulkonstanten CHANCE_GEWICHTE/RISIKO_GEWICHTE. roh_komponenten()\ngibt die neun ungewichteten Bausteine plus vola_pa/preis zurueck - Grundlage\nfuer die Merkmals-Matrix des Backtests. bewerten(k) unveraendert; bewerten(k,\ngewichte) erlaubt das Durchsuchen anderer Gewichtungen.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 2: `handeln.py` — Gebühr im Papierpfad

**Files:**
- Modify: `Agenten/Handel/scanner/handeln.py`
- Create: `Agenten/Handel/verbesserer/tests/test_handeln_gebuehr.py`
- Create: `Agenten/Handel/verbesserer/tests/test_kosten_gleich.py`

**Interfaces:**
- Consumes: `kosten.GEBUEHR_PCT` (Wert; in `handeln.py` als eigene Konstante gespiegelt, nicht importiert — `handeln.py` soll ohne den Verbesserer lauffähig bleiben).
- Produces: journalisierte Beträge enthalten die Gebühr — Kauf-Zeile `usd = einsatz * (1 + GEBUEHR_PCT)`, Verkauf-Zeile `usd = brutto_erloes * (1 - GEBUEHR_PCT)`. Positionsgröße, Deckel-Rechnung und Live-Pfad unverändert.

- [ ] **Step 1: Failing test schreiben** — `tests/test_handeln_gebuehr.py`

```python
import csv
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCANNER = Path(__file__).resolve().parents[2] / "scanner"
sys.path.insert(0, str(SCANNER))
import handeln  # noqa: E402


class TestGebuehr(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        p = Path(self.tmp.name)
        handeln.JOURNAL = p / "handelsjournal.csv"
        handeln.ZUSTAND = p / "zustand.json"
        # Kurs bleibt konstant -> ohne Gebuehr waere die Runde +-0
        handeln.okx.letzter_kurs = lambda inst: 100.0

    def tearDown(self):
        self.tmp.cleanup()

    def _runde_gv(self):
        z = {"positionen": [], "letzte_stops": {}, "letzter_lauf": None}
        v = {"inst": "BTC-USDT", "score": 70.0, "einstieg": 100.0,
             "stop": 90.0, "stop_pct": 10.0, "ziel": 120.0, "usd": 50.0}
        handeln.pruefe_einstiege(z, [v], handeln.scan.wachen(), live=False)
        # Ziel treffen: Kurs auf 120
        handeln.okx.letzter_kurs = lambda inst: 120.0
        handeln.pruefe_ausstiege(z, live=False)
        runden = []
        offen = {}
        with handeln.JOURNAL.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["aktion"] == "kauf":
                    offen[r["inst"]] = float(r["usd"])
                else:
                    runden.append(float(r["usd"]) - offen[r["inst"]])
        return runden[0]

    def test_runde_traegt_zwei_gebuehren(self):
        gv_ohne_gebuehr = 50.0 * (120.0 / 100.0) - 50.0  # = 10.0
        gv = self._runde_gv()
        erwartete_gebuehr = 50.0 * handeln.GEBUEHR_PCT + 60.0 * handeln.GEBUEHR_PCT
        self.assertAlmostEqual(gv, gv_ohne_gebuehr - erwartete_gebuehr, 4)
```

`tests/test_kosten_gleich.py`:

```python
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
SCANNER = WURZEL.parent / "scanner"
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(SCANNER))


class TestKostenGleich(unittest.TestCase):
    def test_konstante_identisch(self):
        import kosten
        import handeln
        self.assertEqual(kosten.GEBUEHR_PCT, handeln.GEBUEHR_PCT)
```

- [ ] **Step 2: Tests laufen und schlagen fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k gebuehr`
Erwartet: FAIL — `handeln.GEBUEHR_PCT` gibt es nicht; Runde ist +10,0 ohne Abzug.

- [ ] **Step 3: `handeln.py` ändern**

Konstante nach den Importen:

```python
# 0,05 % OKX Taker (Volumen < 10.000), gemessen 02.09.2026 - Handelsregeln.md
# nennt einen Papierlauf ohne Gebuehr einen Fehler. Identisch mit
# verbesserer/kosten.py (dort test_kosten_gleich.py).
GEBUEHR_PCT = 0.0005
```

In `pruefe_einstiege`, wo die Kauf-Zeile ins Journal geht, den journalisierten
Betrag mit Gebühr schreiben (die Positionsgröße `usd` bleibt nominal für
Deckel und P/V-Rechnung):

```python
        journal(_jetzt(), "live" if live else "papier", "kauf", v["inst"],
                "%.6f" % v["einstieg"], "%.2f" % (usd * (1 + GEBUEHR_PCT)),
                "%.6f" % v["stop"], "%.6f" % v["ziel"], "score %.1f" % v["score"])
```

In `pruefe_ausstiege` **und** `flach_stellen`, wo die Verkauf-Zeile geschrieben
wird, den Erlös nach Gebühr:

```python
        erloes = p["usd"] * kurs / p["einstieg"] * (1 - GEBUEHR_PCT)
```

(die `erloes`-Zuweisung dort ist die einzige Stelle; `gv` in derselben
Funktion nutzt sie schon weiter.)

- [ ] **Step 4: Tests laufen grün**

Run: wie Step 2, zusätzlich `-k kosten`
Erwartet: PASS

- [ ] **Step 5: Bestehenden Papierlauf gegenprüfen**

Run: `cd Agenten/Handel/scanner && .venv\Scripts\python.exe handeln.py --vorschau`
Erwartet: läuft; Vorschau unverändert (Gebühr wirkt erst beim Buchen).

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/scanner/handeln.py Agenten/Handel/verbesserer/tests/test_handeln_gebuehr.py Agenten/Handel/verbesserer/tests/test_kosten_gleich.py
git commit -m "$(printf 'scanner/handeln: Gebuehr im Papierpfad (GEBUEHR_PCT je Seite)\n\nKauf-Zeile mit Gebuehr, Verkauf-Zeile nach Gebuehr - wie Spur 3. Damit\nrechnen Papierlauf und der neue Walk-Forward-Backtest gleich. Positionsgroesse,\nDeckel-Rechnung und Live-Pfad unveraendert. wachen_pruefung.runden_aus_journal\nsieht die Gebuehr automatisch in erloes-einsatz.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 3: `kerzen.py` — OKX-Tageshistorie holen und cachen

**Files:**
- Create: `Agenten/Handel/verbesserer/kerzen.py`
- Create: `Agenten/Handel/verbesserer/tests/test_kerzen.py`

**Interfaces:**
- Consumes: `scanner/okx.py` (`HEADERS`, `_mit_wiederholung`) über `sys.path`.
- Produces:
  - `kerzen.hole(inst: str, tage: int, cache_dir: Path) -> list[list]` — Liste `[ts_ms, o, h, l, c, vol]` aufsteigend, Länge ≤ `tage`, schreibt `cache_dir/<inst>.json`.
  - `kerzen.laden(inst: str, cache_dir: Path) -> tuple[list, float | None]` — `(kerzen, alter_in_tagen)`; fehlt der Cache: `([], None)`.
  - `kerzen.CACHE = Path(__file__).resolve().parent / "kerzen"` als Vorgabe.

- [ ] **Step 1: Failing test schreiben** — `tests/test_kerzen.py`

```python
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import kerzen  # noqa: E402


class FakeAntwort:
    def __init__(self, text):
        self._t = text.encode()
    def read(self):
        return self._t
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


class TestKerzen(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        # OKX liefert absteigend, neueste zuerst; zwei Seiten a 2 Kerzen
        self.seiten = [
            '{"code":"0","data":[["1700200000000","4","4","4","4","9"],'
            '["1700100000000","3","3","3","3","9"]]}',
            '{"code":"0","data":[["1700000000000","2","2","2","2","9"],'
            '["1699900000000","1","1","1","1","9"]]}',
            '{"code":"0","data":[]}',
        ]
        self.i = 0
        def fake_urlopen(req, timeout=0):
            s = self.seiten[min(self.i, len(self.seiten) - 1)]
            self.i += 1
            return FakeAntwort(s)
        kerzen.urllib.request.urlopen = fake_urlopen

    def tearDown(self):
        self.tmp.cleanup()

    def test_hole_stitcht_und_sortiert_aufsteigend(self):
        k = kerzen.hole("BTC-USDT", tage=10, cache_dir=self.dir)
        self.assertEqual([r[4] for r in k], [1.0, 2.0, 3.0, 4.0])
        self.assertTrue(all(k[j][0] < k[j + 1][0] for j in range(len(k) - 1)))

    def test_hole_schreibt_cache(self):
        kerzen.hole("BTC-USDT", tage=10, cache_dir=self.dir)
        d = json.loads((self.dir / "BTC-USDT.json").read_text("utf-8"))
        self.assertEqual(len(d["kerzen"]), 4)
        self.assertIn("geholt", d)

    def test_laden_ohne_cache(self):
        self.assertEqual(kerzen.laden("XXX", cache_dir=self.dir), ([], None))

    def test_laden_gibt_alter(self):
        kerzen.hole("BTC-USDT", tage=10, cache_dir=self.dir)
        k, alter = kerzen.laden("BTC-USDT", cache_dir=self.dir)
        self.assertEqual(len(k), 4)
        self.assertLess(alter, 1.0)
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k kerzen`
Erwartet: FAIL — `kerzen` fehlt.

- [ ] **Step 3: `kerzen.py` schreiben**

```python
"""OKX-Tageshistorie holen und lokal cachen.

scanner/okx.kerzen() gibt nur die letzten 300 Kerzen. Der Backtest braucht
mehr - /api/v5/market/history-candles laesst sich ueber den Parameter `after`
(Millisekunden-Zeitstempel) rueckwaerts durchblaettern. OKX liefert je Seite
bis 100 Kerzen, neueste zuerst. Wir blaettern, bis genug zusammen sind oder
eine leere Seite kommt.

Faellt der Abruf aus, arbeitet laden() mit dem Cache weiter und meldet sein
Alter. Kein Cache -> ([], None), der Aufrufer bricht dann ab.
"""

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import okx  # scanner/okx.py ueber sys.path

CACHE = Path(__file__).resolve().parent / "kerzen"
_BASIS = "https://www.okx.com"
_SEITE = 100


def _seite(inst, bar, after_ms):
    q = {"instId": inst, "bar": bar, "limit": _SEITE}
    if after_ms is not None:
        q["after"] = str(after_ms)
    url = _BASIS + "/api/v5/market/history-candles?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers=okx.HEADERS, method="GET")
    fehler = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=20) as a:
                d = json.loads(a.read().decode())
            break
        except Exception as e:  # noqa: BLE001
            fehler += 1
            if fehler >= okx.MAX_FEHLER:
                raise
            time.sleep(1.5 * fehler)
    if d.get("code") not in ("0", 0):
        raise okx.OKXFehler("OKX %s: %s" % (d.get("code"), d.get("msg")))
    return d.get("data", [])


def hole(inst, tage, cache_dir=CACHE):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    roh = []
    after = None
    while len(roh) < tage:
        seite = _seite(inst, "1D", after)
        if not seite:
            break
        roh.extend(seite)
        after = int(seite[-1][0])  # aeltester Zeitstempel dieser Seite
        time.sleep(0.2)
    reihen = [[int(r[0])] + [float(x) for x in r[1:6]] for r in roh]
    reihen.sort(key=lambda r: r[0])
    reihen = reihen[-tage:]
    (cache_dir / (inst + ".json")).write_text(json.dumps(
        {"geholt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "kerzen": reihen}, ensure_ascii=False), "utf-8")
    return reihen


def laden(inst, cache_dir=CACHE):
    p = Path(cache_dir) / (inst + ".json")
    if not p.exists():
        return [], None
    d = json.loads(p.read_text("utf-8"))
    t = datetime.fromisoformat(d["geholt"])
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    alter = (datetime.now(timezone.utc) - t).total_seconds() / 86400.0
    return d["kerzen"], alter
```

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS (4 Tests)

- [ ] **Step 5: Einmal echt gegen OKX prüfen (Netz nötig)**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -c "import sys; sys.path[:0]=['Agenten/Handel/verbesserer','Agenten/Handel/scanner']; import kerzen; k=kerzen.hole('BTC-USDT',400); print(len(k), k[0][0], k[-1][0])"`
Erwartet: ~400 Kerzen, aufsteigende Zeitstempel. (Kein Netz → überspringen, im Plan vermerken.)

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/verbesserer/kerzen.py Agenten/Handel/verbesserer/tests/test_kerzen.py
git commit -m "$(printf 'verbesserer/kerzen: OKX-Tageshistorie paginiert holen und cachen\n\nhistory-candles rueckwaerts ueber after-Parameter geblaettert, aufsteigend\nsortiert, auf `tage` beschnitten, als kerzen/<inst>.json abgelegt. laden()\ngibt (kerzen, alter_in_tagen) oder ([], None) ohne Cache.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 4: `auswerter.py` — Journal-Segmente und Befund (TP1)

**Files:**
- Create: `Agenten/Handel/verbesserer/auswerter.py`
- Create: `Agenten/Handel/verbesserer/tests/test_auswerter.py`
- Create: `Agenten/Handel/verbesserer/tests/fixtures/journal_klein.csv`
- Create: `Agenten/Handel/verbesserer/tests/fixtures/bericht_2026-08-20.json`

**Interfaces:**
- Consumes: `scanner/wachen_pruefung.runden_aus_journal(pfad) -> list[dict]` (Felder `zeit, inst, modus, einsatz, erloes, gv, grund`).
- Produces:
  - `auswerter.anreichern(runden, berichte_dir) -> list[dict]` — je Runde zusätzlich `score, verhaeltnis, vola_pa` (aus dem Tagesbericht des Einstiegstags; `None`, wenn kein Bericht passt) und `wochentag`, `haltedauer_tage`.
  - `auswerter.segmente(runden_angereichert, mindest_n) -> dict` — Struktur `{merkmal: {auspraegung: {n, mittel_gv, trefferquote, ev_delta}}}`. Merkmale: `score_band, verhaeltnis_band, vola_band, haltedauer_band, wochentag, inst, grund`.
  - `auswerter.permutationstest(gruppe, rest, seed=1, runden=2000) -> float` — p-Wert für „mittlerer gv der Gruppe unterscheidet sich vom Rest".
  - `auswerter.befund(spur_konf, konfig, ausgabe_dir) -> dict` — schreibt `ausgabe_dir/<datum>-befund-<spur>.json` mit `{segmente, befunde, runden_gesamt, runden_vor_umstellung, erzeugt}`; `befunde` = Liste der Segmente mit `n >= mindest_n` und `p < 0.05`.

- [ ] **Step 1: Fixtures schreiben**

`fixtures/journal_klein.csv` (Kopf wie `handeln.journal`): 24 Zeilen, 12 geschlossene Runden. Baue sie so, dass Runden mit `grund=stop` im Schnitt klar negativ, `grund=ziel` klar positiv sind, und `inst=DOGE-USDT` (4 Runden) auffällig schlechter als der Rest.

```csv
zeit,modus,aktion,inst,preis,usd,stop,ziel,grund
2026-08-20T10:00:00+00:00,papier,kauf,BTC-USDT,100.000000,50.03,90.0,120.0,score 72.0
2026-08-25T10:00:00+00:00,papier,verkauf,BTC-USDT,120.000000,59.94,,,ziel
2026-08-20T10:00:00+00:00,papier,kauf,ETH-USDT,100.000000,50.03,92.0,116.0,score 68.0
2026-08-23T10:00:00+00:00,papier,verkauf,ETH-USDT,92.000000,45.98,,,stop
2026-08-20T10:00:00+00:00,papier,kauf,DOGE-USDT,100.000000,50.03,95.0,110.0,score 61.0
2026-08-21T10:00:00+00:00,papier,verkauf,DOGE-USDT,95.000000,47.48,,,stop
```
… nach diesem Muster auf 12 Runden erweitern (mind. 8 mit Merkmalswerten aus dem Bericht unten, damit ein Segment `n >= 8` erreichen kann; DOGE 4×, alle `stop`).

`fixtures/bericht_2026-08-20.json` — Form von `scanner/berichte/<datum>.json` (`{"datum": "...", "werte": [{"inst": "...", "score": .., "verhaeltnis": .., "kennzahlen": {"volatilitaet_pa": ..}}, ...]}`), mit Einträgen für jedes Instrument aus dem Journal.

- [ ] **Step 2: Failing test schreiben** — `tests/test_auswerter.py`

```python
import json
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import auswerter  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"


class TestAuswerter(unittest.TestCase):
    def setUp(self):
        import wachen_pruefung as wp
        self.runden = auswerter.anreichern(
            wp.runden_aus_journal(FIX / "journal_klein.csv"), FIX)

    def test_anreichern_setzt_score_aus_bericht(self):
        btc = [r for r in self.runden if r["inst"] == "BTC-USDT"][0]
        self.assertAlmostEqual(btc["score"], 72.0, 1)

    def test_segment_stop_schlechter_als_ziel(self):
        s = auswerter.segmente(self.runden, mindest_n=1)
        self.assertLess(s["grund"]["stop"]["mittel_gv"],
                        s["grund"]["ziel"]["mittel_gv"])

    def test_permutationstest_deterministisch(self):
        doge = [r for r in self.runden if r["inst"] == "DOGE-USDT"]
        rest = [r for r in self.runden if r["inst"] != "DOGE-USDT"]
        p1 = auswerter.permutationstest(doge, rest, seed=1)
        p2 = auswerter.permutationstest(doge, rest, seed=1)
        self.assertEqual(p1, p2)

    def test_befund_nur_ab_mindest_n(self):
        s = auswerter.segmente(self.runden, mindest_n=8)
        # DOGE hat nur 4 Runden -> kein Eintrag als Befund-Kandidat
        self.assertNotIn("DOGE-USDT", s.get("inst", {}))

    def test_befund_schreibt_datei(self, tmp=None):
        import tempfile
        d = Path(tempfile.mkdtemp())
        konf = {"segment_mindest_n": 1, "gebuehr_umstellung_datum": "2026-01-01"}
        spur = {"journal": str(FIX / "journal_klein.csv"),
                "berichte": str(FIX), "_name": "spur1"}
        auswerter.befund(spur, konf, d)
        raus = list(d.glob("*-befund-spur1.json"))
        self.assertEqual(len(raus), 1)
        self.assertIn("segmente", json.loads(raus[0].read_text("utf-8")))
```

- [ ] **Step 3: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k auswerter`
Erwartet: FAIL — `auswerter` fehlt.

- [ ] **Step 4: `auswerter.py` schreiben**

Kernpunkte:
- `anreichern`: je Runde Einstiegsdatum aus `zeit[:10]`, Tagesbericht
  `berichte_dir/<inst-datei>` suchen — Dateiname ist `<datum>.json`
  (nicht `bericht_<datum>.json`; die Fixture heißt so nur zur Klarheit —
  im Test `berichte`-Ordner auf `FIX` zeigen und die Datei
  `2026-08-20.json` nennen). Bericht laden, Wert mit passendem `inst`
  ziehen → `score, verhaeltnis, kennzahlen.volatilitaet_pa`. `wochentag`
  aus `datetime.fromisoformat`. `haltedauer_tage` = Verkaufsdatum −
  Kaufdatum (aus der Runde; `runden_aus_journal` liefert `zeit` der
  Kaufzeile — Verkaufszeit über einen zweiten Durchlauf des Journals
  ergänzen oder `runden_aus_journal` genügt, falls es die Verkaufszeit
  hält; sonst hier selbst FIFO über das Journal laufen).
- Bänder: `score_band` → `"<60" / "60-70" / "70-80" / "80+"`;
  `verhaeltnis_band` → `"<1.5" / "1.5-2" / "2+"`; `vola_band` → Terzile
  über alle vorhandenen `vola_pa` (fehlt der Wert: Ausprägung `"?"`);
  `haltedauer_band` → `"<=2T" / "3-5T" / ">5T"`.
- `segmente`: je Merkmal je Ausprägung `n`, `mittel_gv = mean(gv)`,
  `trefferquote = Anteil gv > 0`, `ev_delta = mittel_gv − Gesamtmittel`.
- `permutationstest`: `random.Random(seed)`; Teststatistik
  `abs(mean(gruppe) − mean(rest))`; `runden`-mal Labels mischen, Anteil
  der gemischten Statistiken ≥ beobachteter = p.
- `befund`: `anreichern` → `segmente(…, konfig["segment_mindest_n"])` →
  für jede Ausprägung mit `n >= mindest_n` den Permutationstest Gruppe vs.
  Rest; `p < 0.05` → in `befunde`. `runden_vor_umstellung` = Anzahl
  Runden mit Kaufdatum `< gebuehr_umstellung_datum`. Datei
  `<heute>-befund-<name>.json` schreiben (`name` aus `spur["_name"]`,
  Vorgabe `"spur1"`).

- [ ] **Step 5: Test läuft grün**

Run: wie Step 3
Erwartet: PASS (5 Tests). Fixtures ggf. anpassen, bis die Segment-Erwartungen halten.

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/verbesserer/auswerter.py Agenten/Handel/verbesserer/tests/test_auswerter.py Agenten/Handel/verbesserer/tests/fixtures/
git commit -m "$(printf 'verbesserer/auswerter: Journal-Segmente und Befund (TP1)\n\nGeschlossene Runden nach Score-/Verhaeltnis-/Vola-/Haltedauer-Band, Wochentag,\nInstrument und Ausstiegsgrund gruppiert. Ein Segment wird Befund, wenn n >=\nsegment_mindest_n und ein Permutationstest gegen den Rest p < 0.05 liefert.\nRunden vor dem Gebuehren-Umstellungsdatum getrennt gezaehlt.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 5: `ruecktest.py` — Merkmals-Matrix (TP2, Teil 1)

**Files:**
- Create: `Agenten/Handel/verbesserer/ruecktest.py`
- Create: `Agenten/Handel/verbesserer/tests/test_ruecktest_matrix.py`

**Interfaces:**
- Consumes: `scanner/bewertung.roh_komponenten(kerzen)` (Task 1).
- Produces:
  - `ruecktest.MINDEST_KERZEN = 120` — vor so vielen Kerzen wird ein Tag nicht bewertet.
  - `ruecktest.merkmals_matrix(kerzen_je_inst: dict[str, list]) -> dict[str, dict[int, dict]]` — `{inst: {tag_index: roh_komponenten(kerzen[:tag_index+1])}}` für jedes `tag_index >= MINDEST_KERZEN`. Die Rohkomponenten-Dicts sind genau die aus `bewertung.roh_komponenten`.

- [ ] **Step 1: Failing test schreiben** — `tests/test_ruecktest_matrix.py`

```python
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import bewertung  # noqa: E402
import ruecktest  # noqa: E402


def _kerzen(n):
    k, p = [], 100.0
    for i in range(n):
        p *= 1.0 + (0.005 if i % 4 else -0.006)
        k.append([i * 86400000, p, p * 1.02, p * 0.98, p, 1000.0 + i % 7])
    return k


class TestMatrix(unittest.TestCase):
    def test_matrix_entspricht_direktem_aufruf(self):
        kerzen = {"BTC-USDT": _kerzen(150)}
        m = ruecktest.merkmals_matrix(kerzen)
        tag = 140
        direkt = bewertung.roh_komponenten(kerzen["BTC-USDT"][:tag + 1])
        self.assertEqual(m["BTC-USDT"][tag], direkt)

    def test_keine_eintraege_vor_mindest_kerzen(self):
        m = ruecktest.merkmals_matrix({"BTC-USDT": _kerzen(150)})
        self.assertTrue(min(m["BTC-USDT"]) >= ruecktest.MINDEST_KERZEN)

    def test_deterministisch(self):
        kerzen = {"X": _kerzen(140)}
        self.assertEqual(ruecktest.merkmals_matrix(kerzen),
                         ruecktest.merkmals_matrix(kerzen))
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k ruecktest_matrix`
Erwartet: FAIL — `ruecktest` fehlt.

- [ ] **Step 3: `ruecktest.py` anlegen (nur Matrix)**

```python
"""Walk-Forward-Backtest fuer den Marktscanner.

Teil 1: merkmals_matrix() rechnet die neun ungewichteten Bausteine je (Wert,
Tag) EINMAL vor. Danach kostet das Bewerten eines Kandidaten nur noch
Gewichtung und Tore - die Gewichtssuche wird fast kostenlos.
"""

import bewertung

MINDEST_KERZEN = 120


def merkmals_matrix(kerzen_je_inst):
    aus = {}
    for inst, kerzen in kerzen_je_inst.items():
        reihe = {}
        for t in range(MINDEST_KERZEN, len(kerzen)):
            reihe[t] = bewertung.roh_komponenten(kerzen[: t + 1])
        aus[inst] = reihe
    return aus
```

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS (3 Tests)

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/verbesserer/ruecktest.py Agenten/Handel/verbesserer/tests/test_ruecktest_matrix.py
git commit -m "$(printf 'verbesserer/ruecktest: Merkmals-Matrix (TP2 Teil 1)\n\nDie neun roh_komponenten je (Wert, Tag) einmal vorberechnet, ab Tag 120.\nGrundlage fuer schnelle Kandidatenbewertung.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 6: `ruecktest.py` — Kandidaten-Simulation (TP2, Teil 2)

**Files:**
- Modify: `Agenten/Handel/verbesserer/ruecktest.py`
- Create: `Agenten/Handel/verbesserer/tests/test_ruecktest_sim.py`

**Interfaces:**
- Consumes: `kosten.GEBUEHR_PCT`; `merkmals_matrix` (Task 5).
- Produces:
  - Kandidat-Form (dict):
    ```python
    {
      "gates": {"mindest_score": float, "max_volatilitaet_pa": float,
                "mindest_chance_risiko": float, "stop_min": float,
                "stop_max": float, "abklingzeit_tage": int,
                "max_offene_positionen": int, "max_gesamt_usd": float,
                "max_pro_trade_usd": float},
      "gewichte": {"chance": {...5...}, "risiko": {...4...}},
      "watchlist": list[str],
      "sizing": "flach" | "score-linear" | "vola-invers",
    }
    ```
    `max_*` sind im Kandidat nur zum Rechnen, **nie** im Suchraum (Task 8).
  - `ruecktest.stop_prozent(vola_pa, stop_min, stop_max) -> float` — `clamp(3 + 6*min(vola,1.5), stop_min, stop_max)`, auf 1 Stelle gerundet (wie `handeln.stop_prozent`).
  - `ruecktest.simuliere(matrix, kerzen_je_inst, kandidat, start_tag, end_tag) -> list[dict]` — geschlossene Runden im Fenster `[start_tag, end_tag)`: `{einstieg_tag, ausstieg_tag, inst, einsatz, erloes, gv, grund, score, vola_pa, verhaeltnis}`. `gv` ist netto nach `GEBUEHR_PCT` je Seite.

- [ ] **Step 1: Failing test schreiben** — `tests/test_ruecktest_sim.py`

```python
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import kosten  # noqa: E402
import ruecktest  # noqa: E402


def _flat_dann_hoch(n):
    """120 Tage flach bei 100, dann steil auf 130 - erzeugt genau einen
    Ziel-Treffer je Wert kurz nach Tag 120."""
    k = []
    for i in range(n):
        p = 100.0 if i < 122 else 100.0 + (i - 122) * 6.0
        k.append([i * 86400000, p, p * 1.001, p * 0.999, p, 1000.0])
    return k


def _basis_kandidat(watchlist):
    return {
        "gates": {"mindest_score": 0.0, "max_volatilitaet_pa": 9.0,
                  "mindest_chance_risiko": 0.0, "stop_min": 4.0,
                  "stop_max": 12.0, "abklingzeit_tage": 3,
                  "max_offene_positionen": 4, "max_gesamt_usd": 200.0,
                  "max_pro_trade_usd": 50.0},
        "gewichte": None, "watchlist": watchlist, "sizing": "flach",
    }


class TestSim(unittest.TestCase):
    def setUp(self):
        self.kerzen = {"AAA": _flat_dann_hoch(140), "BBB": _flat_dann_hoch(140)}
        self.m = ruecktest.merkmals_matrix(self.kerzen)

    def test_stop_prozent_klemmt(self):
        self.assertEqual(ruecktest.stop_prozent(5.0, 4.0, 12.0), 12.0)
        self.assertEqual(ruecktest.stop_prozent(0.0, 4.0, 12.0), 4.0)

    def test_ziel_treffer_gibt_gewinn_nach_gebuehr(self):
        k = _basis_kandidat(["AAA"])
        runden = ruecktest.simuliere(self.m, self.kerzen, k, 120, 140)
        self.assertEqual(len(runden), 1)
        r = runden[0]
        self.assertEqual(r["grund"], "ziel")
        brutto = 50.0 * (r["erloes_kurs"] / r["einstieg_kurs"]) - 50.0 \
            if "erloes_kurs" in r else None
        # einfacher: gv muss kleiner sein als der gebuehrenfreie Gewinn
        gebuehrenfrei = r["einsatz"] * (r["erloes"] / r["einsatz"])  # ~ brutto
        self.assertLess(r["gv"], gebuehrenfrei)
        self.assertGreater(r["gv"], 0.0)

    def test_max_offene_positionen_begrenzt(self):
        k = _basis_kandidat(["AAA", "BBB"])
        k["gates"]["max_offene_positionen"] = 1
        runden = ruecktest.simuliere(self.m, self.kerzen, k, 120, 140)
        # nie mehr als eine Position gleichzeitig -> Einstiege serialisiert
        paare = [(r["einstieg_tag"], r["ausstieg_tag"]) for r in runden]
        for a in range(len(paare)):
            for b in range(a + 1, len(paare)):
                self.assertFalse(paare[a][0] < paare[b][1]
                                 and paare[b][0] < paare[a][1])

    def test_stop_vor_ziel_am_selben_tag(self):
        # Tag mit tief <= stop UND hoch >= ziel -> grund muss "stop" sein
        kerzen = {"AAA": _flat_dann_hoch(140)}
        kerzen["AAA"][125] = [125 * 86400000, 100.0, 200.0, 1.0, 100.0, 1000.0]
        m = ruecktest.merkmals_matrix(kerzen)
        k = _basis_kandidat(["AAA"])
        runden = ruecktest.simuliere(m, kerzen, k, 120, 140)
        getroffen = [r for r in runden if r["einstieg_tag"] <= 125 <= r["ausstieg_tag"]]
        self.assertTrue(all(r["grund"] == "stop" for r in getroffen))
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k ruecktest_sim`
Erwartet: FAIL — `simuliere`/`stop_prozent` fehlen.

- [ ] **Step 3: `simuliere` und `stop_prozent` implementieren**

Logik, exakt an `handeln.py` gehalten:

```python
import kosten

def stop_prozent(vola_pa, stop_min, stop_max):
    roh = 3.0 + 6.0 * min(vola_pa, 1.5)
    return max(stop_min, min(stop_max, round(roh, 1)))


def _score(roh, gewichte):
    b = bewertung.bewerten  # nutzt roh nicht direkt -> eigener Mini-Rechner:
    cg = (gewichte or {}).get("chance") or bewertung.CHANCE_GEWICHTE
    rg = (gewichte or {}).get("risiko") or bewertung.RISIKO_GEWICHTE
    chance = 100.0 * sum(cg[k] * roh["c_" + k] for k in cg)
    risiko = 100.0 * sum(rg[k] * roh["r_" + k] for k in rg)
    score = max(0.0, min(100.0, chance * (1.0 - 0.7 * risiko / 100.0)))
    return score, chance / max(risiko, 1.0)
```

Hinweis: die Schlüssel von `CHANCE_GEWICHTE` (`trend`, `momentum`, …)
entsprechen `roh["c_trend"]` usw. — die `"c_"`/`"r_"`-Präfix-Konvention in
`_score` setzt das voraus; bei Task 1 die dict-Schlüssel entsprechend
wählen (`c_` + Gewichtsschlüssel).

`simuliere`:
- `frei_ab = {inst: tag}` für Abklingzeit; `offen = []` Positionen
  `{inst, einstieg_kurs, stop, ziel, einsatz, einstieg_tag}`.
- Für `t` von `start_tag` bis `end_tag − 1`:
  1. **Ausstiege zuerst** (wie `handeln`): für jede offene Position die
     Kerze `kerzen[inst][t]` prüfen — `tief <= stop` → `grund="stop"`,
     `frei_ab[inst] = t + abklingzeit_tage`; sonst `hoch >= ziel` →
     `grund="ziel"`. Bei Treffer Runde schließen:
     `roh_erloes = einsatz * schluss_or_trigger / einstieg_kurs`. Für den
     Ausführungskurs den **Triggerpreis** nehmen (`stop` bzw. `ziel`),
     nicht den Schlusskurs — konservativ und eindeutig.
     `erloes = roh_erloes * (1 - GEBUEHR_PCT)`;
     `einsatz_mit_gebuehr = einsatz * (1 + GEBUEHR_PCT)`;
     `gv = erloes - einsatz_mit_gebuehr`. Runde anhängen mit den
     Merkmalen aus `matrix[inst][einstieg_tag]` (`score`, `vola_pa`,
     `verhaeltnis` — Letztere beim Einstieg berechnet und mitgeführt).
  2. **Einstiege** (nach Ausstiegen): `t` muss in `matrix[inst]` sein.
     Für jeden `inst` aus `kandidat["watchlist"]`, der nicht offen und
     nicht in Abklingzeit ist: `roh = matrix[inst][t]`;
     `score, verh = _score(roh, kandidat["gewichte"])`;
     `vola = roh["vola_pa"]`. Tore:
     `score >= mindest_score and vola <= max_volatilitaet_pa and verh >= mindest_chance_risiko`.
     `sp = stop_prozent(vola, stop_min, stop_max)`;
     `einstieg_kurs = kerzen[inst][t][4]` (Schluss);
     `stop = einstieg_kurs * (1 - sp/100)`;
     `ziel = einstieg_kurs + 2 * (einstieg_kurs - stop)`.
     `einsatz = _sizing(kandidat["sizing"], score, vola, max_pro_trade_usd)`.
     Deckel: `len(offen) < max_offene_positionen` **und**
     `sum(p["einsatz"] for p in offen) + einsatz <= max_gesamt_usd`.
     Position eröffnen mit `einstieg_tag = t`.
- Am `end_tag` noch offene Positionen werden **nicht** gewertet (nur
  geschlossene Runden zählen — deckt sich mit `runden_aus_journal`).
- `_sizing`: `"flach"` → `max_pro_trade_usd`; `"score-linear"` →
  `max_pro_trade_usd * clamp(score/100, 0.4, 1.0)`; `"vola-invers"` →
  `max_pro_trade_usd * clamp(0.8 / max(vola, 0.4), 0.4, 1.0)`. Ergebnis
  auf 2 Stellen runden.

Den Test `test_ziel_treffer_gibt_gewinn_nach_gebuehr` ggf. auf die im
Code tatsächlich abgelegten Felder anpassen (`einstieg_kurs` ist im dict).

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS (4 Tests)

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/verbesserer/ruecktest.py Agenten/Handel/verbesserer/tests/test_ruecktest_sim.py
git commit -m "$(printf 'verbesserer/ruecktest: Kandidaten-Simulation (TP2 Teil 2)\n\nsimuliere() bildet Ein-/Ausstieg aus handeln.py exakt nach: Ausstiege vor\nEinstiegen, Stop am Tagestief vor Ziel am Tageshoch, Abklingzeit, Deckel fuer\noffene Positionen und gebundenes Kapital. gv netto nach GEBUEHR_PCT je Seite.\nAusfuehrung zum Triggerpreis, konservativ.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 7: `ruecktest.py` — Walk-Forward-Aggregation (TP2, Teil 3)

**Files:**
- Modify: `Agenten/Handel/verbesserer/ruecktest.py`
- Create: `Agenten/Handel/verbesserer/tests/test_ruecktest_wf.py`

**Interfaces:**
- Consumes: `simuliere` (Task 6); `konfig.json`-Werte `oos_training_tage, oos_test_tage, oos_schritt_tage`.
- Produces:
  - `ruecktest.kennzahlen(runden: list[dict]) -> dict` — `{n, netto_gv_je_runde, trefferquote, summe_gv, max_drawdown, gebuehr_runde_pct, noetige_trefferquote, beobachtete_trefferquote, liquidationsabstand, funding_pct}`. Für Spur 1: `liquidationsabstand = None`, `funding_pct = None`. `gebuehr_runde_pct = 2 * GEBUEHR_PCT`. `noetige_trefferquote` aus dem mittleren Gewinn/Verlust je gewonnener/verlorener Runde (`v/(v+g)` mit `g` = mittlerer Gewinn, `v` = mittlerer Verlustbetrag).
  - `ruecktest.walk_forward(kerzen_je_inst, kandidat, konfig) -> dict` — `{fenster: [{von_tag, bis_tag, kennzahlen}], gesamt: kennzahlen(alle_oos_runden), fenster_anzahl}`.

- [ ] **Step 1: Failing test schreiben** — `tests/test_ruecktest_wf.py`

```python
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import ruecktest  # noqa: E402


def _kerzen(n):
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
KONF = {"oos_training_tage": 120, "oos_test_tage": 30, "oos_schritt_tage": 30}


class TestWF(unittest.TestCase):
    def test_fensteranzahl(self):
        wf = ruecktest.walk_forward({"AAA": _kerzen(240)}, KAND, KONF)
        # Testfenster starten bei 120, 150, 180, 210 -> letztes endet 240
        self.assertEqual(wf["fenster_anzahl"], 4)

    def test_gesamt_ist_summe_der_fensterrunden(self):
        wf = ruecktest.walk_forward({"AAA": _kerzen(240)}, KAND, KONF)
        n_fenster = sum(f["kennzahlen"]["n"] for f in wf["fenster"])
        self.assertEqual(wf["gesamt"]["n"], n_fenster)

    def test_kennzahlen_leere_runden(self):
        kz = ruecktest.kennzahlen([])
        self.assertEqual(kz["n"], 0)
        self.assertIsNone(kz["liquidationsabstand"])
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k ruecktest_wf`
Erwartet: FAIL.

- [ ] **Step 3: `kennzahlen` und `walk_forward` implementieren**

- `walk_forward`: `laenge = min(len(k) for k in kerzen_je_inst.values())`.
  `matrix = merkmals_matrix(kerzen_je_inst)` einmal. Fenster:
  `start = oos_training_tage`; solange `start + oos_test_tage <= laenge`:
  `runden = simuliere(matrix, kerzen_je_inst, kandidat, start, start + oos_test_tage)`;
  Fenster ablegen; `start += oos_schritt_tage`. `gesamt` aus allen Runden.
- `max_drawdown`: kumulierte `gv`-Kurve über alle OOS-Runden in zeitlicher
  Reihenfolge (`sorted by einstieg_tag`), `max(hoch − stand)`.
- `kennzahlen` mit `n == 0` → alle Zahlen `0`/`None`, kein `ZeroDivision`.

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS (3 Tests)

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/verbesserer/ruecktest.py Agenten/Handel/verbesserer/tests/test_ruecktest_wf.py
git commit -m "$(printf 'verbesserer/ruecktest: Walk-Forward-Aggregation (TP2 Teil 3)\n\nTraining 120 / Test 30 / Schritt 30. OOS-Runden aller Fenster aggregiert.\nkennzahlen(): Netto-gv je Runde, Trefferquote, max Drawdown auf der\nkonkatenierten OOS-Kurve, Gebuehr je Runde, noetige vs. beobachtete\nTrefferquote. Liquidation/Funding = None fuer Spot.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 8: `suche.py` — Kandidatenraum und Grenzen (TP3, Teil 1)

**Files:**
- Create: `Agenten/Handel/verbesserer/suche.py`
- Create: `Agenten/Handel/verbesserer/tests/test_suche_raum.py`

**Interfaces:**
- Consumes: `spuren.json` → `spur["aenderbar"]`; `scanner/wachen.json`; `scanner/bewertung.CHANCE_GEWICHTE/RISIKO_GEWICHTE`.
- Produces:
  - `suche.DENYLIST: frozenset` — `{"handel_erlaubt", "freigabe", "drawdown_halbierung_prozent", "kill_switch_gesamt_usd", "herzschlag_max_minuten", "journal_zweitziel", "max_pro_trade_usd", "max_gesamt_usd", "max_offene_positionen"}`.
  - `suche.basis_kandidat(wachen: dict, chance_g: dict, risiko_g: dict) -> dict` — Kandidat-Form aus Task 6, `gewichte` aus den übergebenen Konstanten, `max_*` aus `wachen` übernommen.
  - `suche.nachbarn(kandidat: dict, grenzen: dict) -> list[dict]` — bounded: je Gate ±1 Schritt (Schrittweiten unten), je Gewicht ±0,05 mit Renormierung der Gruppe auf 1,0, `sizing` die je anderen zwei Werte, `watchlist` je „ein Wert weniger". Nie ein Wert außerhalb `grenzen`; `max_*` nie verändert.
  - `suche.im_rahmen(kandidat: dict, grenzen: dict, basis: dict) -> bool` — prüft alle Gates gegen `grenzen`, Gewichtssummen == 1,0 (±1e-9), jedes Gewicht in `[0, 0.5]`, `watchlist` ⊆ `basis["watchlist"]`, `max_*` == `basis["max_*"]`.

Schrittweiten: `mindest_score` 2,5; `max_volatilitaet_pa` 0,1; `mindest_chance_risiko` 0,1; `stop_min` 1,0; `stop_max` 1,0; `abklingzeit_tage` 1.

- [ ] **Step 1: Failing test schreiben** — `tests/test_suche_raum.py`

```python
import random
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import bewertung  # noqa: E402
import suche  # noqa: E402

WACHEN = {"mindest_score": 60, "max_volatilitaet_pa": 1.2,
          "mindest_chance_risiko": 1.5, "pflicht_stop_prozent_min": 4.0,
          "pflicht_stop_prozent_max": 12.0, "abklingzeit_tage": 3,
          "max_pro_trade_usd": 50, "max_gesamt_usd": 200,
          "max_offene_positionen": 4,
          "watchlist": ["BTC-USDT", "ETH-USDT", "SOL-USDT"]}
GRENZEN = {"mindest_score": [55, 75], "max_volatilitaet_pa": [0.9, 1.4],
           "mindest_chance_risiko": [1.3, 2.2], "stop_min": [4, 8],
           "stop_max": [8, 15], "abklingzeit_tage": [2, 5],
           "watchlist": "liste"}


class TestRaum(unittest.TestCase):
    def setUp(self):
        self.basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)

    def test_basis_ist_im_rahmen(self):
        self.assertTrue(suche.im_rahmen(self.basis, GRENZEN, self.basis))

    def test_nachbarn_bleiben_im_rahmen(self):
        rng = random.Random(0)
        k = self.basis
        for _ in range(400):
            nb = suche.nachbarn(k, GRENZEN)
            self.assertTrue(nb)
            k = rng.choice(nb)
            self.assertTrue(suche.im_rahmen(k, GRENZEN, self.basis),
                            msg=repr(k))

    def test_gewichtsgruppen_summieren_auf_eins(self):
        for nb in suche.nachbarn(self.basis, GRENZEN):
            for gruppe in ("chance", "risiko"):
                self.assertAlmostEqual(
                    sum(nb["gewichte"][gruppe].values()), 1.0, 9)

    def test_deckel_nie_veraendert(self):
        for nb in suche.nachbarn(self.basis, GRENZEN):
            for feld in ("max_pro_trade_usd", "max_gesamt_usd",
                         "max_offene_positionen"):
                self.assertEqual(nb["gates"][feld], self.basis["gates"][feld])

    def test_denylist_vollstaendig(self):
        for feld in ("handel_erlaubt", "freigabe", "kill_switch_gesamt_usd",
                     "herzschlag_max_minuten", "journal_zweitziel",
                     "max_pro_trade_usd", "max_gesamt_usd",
                     "max_offene_positionen", "drawdown_halbierung_prozent"):
            self.assertIn(feld, suche.DENYLIST)
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k suche_raum`
Erwartet: FAIL — `suche` fehlt.

- [ ] **Step 3: `suche.py` (Raum-Teil) implementieren**

- `basis_kandidat`: `gates.stop_min = wachen["pflicht_stop_prozent_min"]`,
  `gates.stop_max = wachen["pflicht_stop_prozent_max"]`, übrige Gates
  direkt; `gewichte` als tiefe Kopien der Konstanten; `watchlist` Kopie.
- `nachbarn`: Liste bauen. Für jedes Gate im Suchraum je ein Nachbar mit
  `+Schritt` und `−Schritt`, geklemmt an `grenzen`; nur aufnehmen, wenn
  der Wert sich tatsächlich ändert und `stop_min < stop_max` bleibt. Für
  Gewichte: je Gruppe, je Gewicht `g`: `g += 0.05` (bzw. `−0.05`), auf
  `[0, 0.5]` klemmen, dann Gruppe renormieren (`w / sum`), Nachbar
  aufnehmen. `sizing`: die zwei nicht aktuellen Werte. `watchlist`: je
  Instrument ein Nachbar ohne dieses Instrument (nur wenn danach
  `len >= 3`).
- `im_rahmen`: alle Bedingungen aus der Interface-Beschreibung; bei
  Gleitkommavergleich `1e-9` Toleranz.

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS (5 Tests)

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/verbesserer/suche.py Agenten/Handel/verbesserer/tests/test_suche_raum.py
git commit -m "$(printf 'verbesserer/suche: Kandidatenraum und Grenzen (TP3 Teil 1)\n\nbasis_kandidat aus wachen.json + Gewichtskonstanten. nachbarn() erzeugt nur\nbounded Nachbarn: Gate-Schritte an den Grenzen aus spuren.json geklemmt,\nGewichte +-0.05 mit Gruppen-Renormierung, sizing-Alternativen, watchlist-Drops.\nDeckel sind nie im Raum. DENYLIST fest.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 9: `suche.py` — Koordinatenabstieg und Overfitting-Sperre (TP3, Teil 2)

**Files:**
- Modify: `Agenten/Handel/verbesserer/suche.py`
- Create: `Agenten/Handel/verbesserer/tests/test_suche_lauf.py`

**Interfaces:**
- Consumes: `nachbarn`, `im_rahmen` (Task 8); `ruecktest.walk_forward` (Task 7); `konfig.json`-Werte `such_budget, overfit_min_runden, overfit_min_fenster`.
- Produces:
  - `suche.besser(kandidat_wf: dict, basis_wf: dict) -> tuple[bool, int]` — `(schlaegt_aggregat, anzahl_fenster_besser)`; „besser" = höheres `netto_gv_je_runde`.
  - `suche.suche(basis, kerzen_je_inst, konfig, grenzen, bewerte=None) -> dict` — `{"kandidat": dict | None, "basis_wf": dict, "kandidat_wf": dict | None, "auswertungen": int, "grund": str}`. `bewerte` überschreibt `ruecktest.walk_forward` (für Tests). Koordinatenabstieg: von `basis` aus wiederholt den besten Nachbarn nehmen, solange er das aktuelle Beste (nach `netto_gv_je_runde` im Aggregat) verbessert und Budget bleibt. Kandidat nur zurückgeben, wenn Overfitting-Sperre hält:
    - `agg` besser als `basis` **und**
    - in `>= overfit_min_fenster` Einzelfenstern besser **und**
    - `kandidat_wf["gesamt"]["n"] >= overfit_min_runden`.
    Sonst `kandidat=None`, `grund` gesetzt.

- [ ] **Step 1: Failing test schreiben** — `tests/test_suche_lauf.py`

```python
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import bewertung  # noqa: E402
import suche  # noqa: E402

WACHEN = {"mindest_score": 60, "max_volatilitaet_pa": 1.2,
          "mindest_chance_risiko": 1.5, "pflicht_stop_prozent_min": 4.0,
          "pflicht_stop_prozent_max": 12.0, "abklingzeit_tage": 3,
          "max_pro_trade_usd": 50, "max_gesamt_usd": 200,
          "max_offene_positionen": 4,
          "watchlist": ["BTC-USDT", "ETH-USDT", "SOL-USDT"]}
GRENZEN = {"mindest_score": [55, 75], "max_volatilitaet_pa": [0.9, 1.4],
           "mindest_chance_risiko": [1.3, 2.2], "stop_min": [4, 8],
           "stop_max": [8, 15], "abklingzeit_tage": [2, 5], "watchlist": "liste"}
KONF = {"such_budget": 50, "overfit_min_runden": 20, "overfit_min_fenster": 3}


def _wf(gv_je_runde, n=30, fenster_besser=0, basis_gv=0.0):
    fenster = []
    for i in range(5):
        g = gv_je_runde if i < fenster_besser else basis_gv
        fenster.append({"von_tag": 120 + 30 * i, "bis_tag": 150 + 30 * i,
                        "kennzahlen": {"n": n // 5, "netto_gv_je_runde": g,
                                       "max_drawdown": 1.0}})
    return {"fenster": fenster, "fenster_anzahl": 5,
            "gesamt": {"n": n, "netto_gv_je_runde": gv_je_runde,
                       "max_drawdown": 1.0}}


class TestLauf(unittest.TestCase):
    def setUp(self):
        self.basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)

    def test_nur_ein_fenster_besser_wird_abgelehnt(self):
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=30, fenster_besser=5, basis_gv=0.0)
            return _wf(1.0, n=30, fenster_besser=1, basis_gv=0.0)
        r = suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertIsNone(r["kandidat"])
        self.assertIn("Fenster", r["grund"])

    def test_genug_fenster_und_runden_wird_angenommen(self):
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=30, fenster_besser=0, basis_gv=0.0)
            return _wf(1.0, n=30, fenster_besser=4, basis_gv=0.0)
        r = suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertIsNotNone(r["kandidat"])

    def test_budget_wird_eingehalten(self):
        ruf = {"n": 0}
        def fake(kerzen, kand, konf):
            ruf["n"] += 1
            return _wf(0.0)
        suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertLessEqual(ruf["n"], KONF["such_budget"] + 1)

    def test_zu_wenige_runden_wird_abgelehnt(self):
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=10)
            return _wf(1.0, n=10, fenster_besser=5)
        r = suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertIsNone(r["kandidat"])
        self.assertIn("Runden", r["grund"])
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k suche_lauf`
Erwartet: FAIL.

- [ ] **Step 3: `besser` und `suche` implementieren**

- `besser`: `agg = kandidat_wf["gesamt"]["netto_gv_je_runde"] > basis_wf["gesamt"]["netto_gv_je_runde"]`; Fenster paarweise nach Index vergleichen (`min` der Längen), zählen, wo Kandidat `netto_gv_je_runde` höher.
- `suche`: `wf = bewerte or ruecktest.walk_forward`. `basis_wf = wf(kerzen, basis, konfig)`; `bestes = basis`, `bestes_wf = basis_wf`, `auswertungen = 1`. Schleife: `kandidaten = nachbarn(bestes, grenzen)`; für jeden (Budget beachten) `wf(...)`, `auswertungen += 1`; den mit höchstem `gesamt.netto_gv_je_runde` merken. Verbessert der beste Nachbar `bestes_wf`, übernehmen und weiter; sonst Abbruch. Nach der Schleife Overfitting-Sperre gegen `basis_wf` prüfen:
  - `agg, k_fenster = besser(bestes_wf, basis_wf)`
  - `if bestes is basis` → `grund="kein besserer Kandidat gefunden"`, `kandidat=None`
  - `elif not agg` → `grund="Aggregat nicht besser"`, `None`
  - `elif k_fenster < overfit_min_fenster` → `grund=f"nur {k_fenster} Fenster besser (>= {overfit_min_fenster} noetig)"`, `None`
  - `elif bestes_wf["gesamt"]["n"] < overfit_min_runden` → `grund=f"nur {n} OOS-Runden (>= {overfit_min_runden} noetig)"`, `None`
  - sonst `kandidat=bestes`.

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS (4 Tests)

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/verbesserer/suche.py Agenten/Handel/verbesserer/tests/test_suche_lauf.py
git commit -m "$(printf 'verbesserer/suche: Koordinatenabstieg und Overfitting-Sperre (TP3 Teil 2)\n\nAbstieg ueber die besten Nachbarn bis kein Fortschritt oder Budget erschoepft.\nEin Kandidat gilt nur, wenn er das OOS-Aggregat schlaegt UND in >=\noverfit_min_fenster Einzelfenstern UND >= overfit_min_runden OOS-Runden hat -\nsonst kandidat=None mit Grund.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 10: `vorschlag.py` — Artefakte bauen (TP3, Teil 3)

**Files:**
- Create: `Agenten/Handel/verbesserer/vorschlag.py`
- Create: `Agenten/Handel/verbesserer/tests/test_vorschlag.py`

**Interfaces:**
- Consumes: Ergebnis von `suche.suche` (Task 9); Kandidat-Form (Task 6); `spur["aenderbar"]`.
- Produces:
  - `vorschlag.wachen_neu_text(alt_text: str, aenderungen: dict[str, object]) -> str` — ersetzt je Schlüssel den Wert im Rohtext (Regex `"<key>"\s*:\s*<wert>`), lässt Zeilenenden und Formatierung unberührt. `watchlist` (Liste) wird als kompakte JSON-Liste in einer Zeile ersetzt.
  - `vorschlag.bewertung_patch(alt_datei: Path, chance_g: dict, risiko_g: dict) -> str` — Unified-Diff (`difflib.unified_diff`), der `CHANCE_GEWICHTE`/`RISIKO_GEWICHTE` im Quelltext auf die neuen Werte setzt. Leerer String, wenn unverändert.
  - `vorschlag.commit_text(spur_name, basis_wf, kandidat_wf, aenderungen) -> str` — mehrzeilig: Titel `verbesserer: <spur_name> Parameter angepasst`, Leerzeile, Blocktext mit den vier Pflichtzahlen (Gebühr je Runde, nötige vs. beobachtete Trefferquote, Liquidationsabstand `n/a (Spot)`, Funding `n/a (Spot)`), OOS-Delta `netto_gv_je_runde` vorher→nachher, Liste der geänderten Schlüssel, Trailer-Zeile `Co-Authored-By: …`.
  - `vorschlag.baue(ordner: Path, ergebnis: dict, spur: dict, konfig: dict) -> None` — schreibt `ordner/{bericht.md, wachen.neu.json, bewertung.patch, commit.txt}`.
  - `vorschlag.kein_vorschlag(ordner: Path, ergebnis: dict, spur_name: str) -> None` — schreibt `ordner/bericht.md` mit Grund und den Baseline-Kennzahlen; keine weiteren Dateien.

- [ ] **Step 1: Failing test schreiben** — `tests/test_vorschlag.py`

```python
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
import vorschlag  # noqa: E402

WACHEN_TXT = (
    '{\r\n'
    '  "watchlist": ["BTC-USDT", "ETH-USDT"],\r\n'
    '  "mindest_score": 60,\r\n'
    '  "max_volatilitaet_pa": 1.20,\r\n'
    '  "abklingzeit_tage": 3\r\n'
    '}\r\n'
)


class TestVorschlag(unittest.TestCase):
    def test_wachen_neu_erhaelt_crlf(self):
        neu = vorschlag.wachen_neu_text(WACHEN_TXT, {"mindest_score": 65})
        self.assertIn('"mindest_score": 65', neu)
        self.assertNotIn('"mindest_score": 60', neu)
        self.assertEqual(neu.count("\r\n"), WACHEN_TXT.count("\r\n"))
        self.assertNotIn("\n\n", neu.replace("\r\n", "\n"))  # kein LF eingeschleppt

    def test_wachen_neu_ersetzt_liste(self):
        neu = vorschlag.wachen_neu_text(
            WACHEN_TXT, {"watchlist": ["BTC-USDT"]})
        self.assertIn('"watchlist": ["BTC-USDT"]', neu)

    def test_commit_text_hat_vier_pflichtzahlen(self):
        basis = {"gesamt": {"netto_gv_je_runde": -0.10,
                            "beobachtete_trefferquote": 0.40,
                            "noetige_trefferquote": 0.45,
                            "gebuehr_runde_pct": 0.001}}
        kand = {"gesamt": {"netto_gv_je_runde": 0.05,
                           "beobachtete_trefferquote": 0.48,
                           "noetige_trefferquote": 0.45,
                           "gebuehr_runde_pct": 0.001}}
        t = vorschlag.commit_text("Scanner/OKX", basis, kand,
                                  {"mindest_score": 65})
        for stueck in ("Gebuehr", "Trefferquote", "Funding", "Liquidations"):
            self.assertIn(stueck, t)
        self.assertIn("Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>", t)

    def test_baue_schreibt_vier_dateien(self):
        with TemporaryDirectory() as d:
            ordner = Path(d) / "v"
            ordner.mkdir()
            ergebnis = {
                "kandidat": {"gates": {"mindest_score": 65}, "gewichte":
                             {"chance": {}, "risiko": {}},
                             "watchlist": ["BTC-USDT"], "sizing": "flach"},
                "basis_wf": {"gesamt": {"netto_gv_je_runde": -0.1, "n": 30,
                             "beobachtete_trefferquote": 0.4,
                             "noetige_trefferquote": 0.45,
                             "gebuehr_runde_pct": 0.001, "max_drawdown": 2.0},
                             "fenster": []},
                "kandidat_wf": {"gesamt": {"netto_gv_je_runde": 0.05, "n": 30,
                                "beobachtete_trefferquote": 0.48,
                                "noetige_trefferquote": 0.45,
                                "gebuehr_runde_pct": 0.001, "max_drawdown": 2.0},
                                "fenster": []},
                "aenderungen": {"mindest_score": 65}, "grund": "ok",
            }
            spur = {"wachen": str(Path(d) / "wachen.json"),
                    "bewertung_datei": str(Path(d) / "bewertung.py"),
                    "name": "Scanner/OKX"}
            (Path(d) / "wachen.json").write_text(WACHEN_TXT, "utf-8", newline="")
            (Path(d) / "bewertung.py").write_text(
                'CHANCE_GEWICHTE = {"trend": 0.30}\n', "utf-8")
            vorschlag.baue(ordner, ergebnis, spur, {})
            for name in ("bericht.md", "wachen.neu.json", "bewertung.patch",
                         "commit.txt"):
                self.assertTrue((ordner / name).exists(), name)
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k vorschlag`
Erwartet: FAIL.

- [ ] **Step 3: `vorschlag.py` implementieren**

- `wachen_neu_text`: je `(key, wert)` ein `re.sub` mit Muster
  `r'("' + re.escape(key) + r'"\s*:\s*)(\[[^\]]*\]|[^,\n\r}]+)'` und
  Ersatz `r'\g<1>' + _als_json(wert)`. `_als_json(list)` →
  `json.dumps(wert)` (kompakt, Leerzeichen nach Komma über
  `separators=(", ", ": ")`). Zahlen als `repr` ohne Exponent.
  **Nur `count=1`.** Kein Parsen, kein Reserialisieren.
- `bewertung_patch`: Zieltext = Quelltext mit den beiden Konstanten-Zeilen
  ersetzt (die Konstanten stehen je auf einem `{...}`-Literal; per Regex
  `CHANCE_GEWICHTE = {…}` ersetzen). `difflib.unified_diff(alt, neu,
  fromfile=a/…, tofile=b/…)`. Gleich → `""`.
- `commit_text`: f-String mit den Zahlen; Betragsformat `%.4f`/`%.1f%%`.
- `baue`: `aenderungen` = flache Map Schlüssel→neuer Wert (Gates +
  ggf. `watchlist`). `wachen.neu.json` = `wachen_neu_text(alt, aenderungen
  ohne Gewichte)`. `bewertung.patch` aus den Kandidat-Gewichten.
  `commit.txt` = `commit_text(...)`. `bericht.md` = Markdown mit:
  Überschrift, Datum, Tabelle „vorher/nachher" je Fenster + gesamt,
  Abschnitt „Vier Pflichtzahlen", Abschnitt „Warnungen" (Kostenmodell
  strenger als Alt-Journal; Historie ~1–2 Jahre; Survivorship;
  Overfitting-Sperre bestanden mit `k_fenster`/`n`), Abschnitt
  „Geänderte Schlüssel".
- `kein_vorschlag`: nur `bericht.md` mit `ergebnis["grund"]` und der
  Baseline-Kennzahltabelle.

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS (4 Tests)

- [ ] **Step 5: Prüfen, dass nichts unter `scanner/` geschrieben wurde**

Run: `git status --porcelain Agenten/Handel/scanner`
Erwartet: leer.

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/verbesserer/vorschlag.py Agenten/Handel/verbesserer/tests/test_vorschlag.py
git commit -m "$(printf 'verbesserer/vorschlag: Artefakte bauen (TP3 Teil 3)\n\nwachen.neu.json per gezielter Text-Ersetzung (CRLF bleibt). bewertung.patch\nals Unified-Diff der Gewichtskonstanten. commit.txt mit den vier Pflichtzahlen\nund dem OOS-Delta. bericht.md mit Vorher/Nachher und Warnungen. Schreibt nur\nin den Vorschlagsordner, nie nach scanner/.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 11: `anwenden.py` — Denylist, `.bak`, CRLF-Apply, Einzel-Commit (TP4, Teil 1)

**Files:**
- Create: `Agenten/Handel/verbesserer/anwenden.py`
- Create: `Agenten/Handel/verbesserer/tests/test_anwenden.py`

**Interfaces:**
- Consumes: `suche.DENYLIST`; Vorschlagsordner mit `{wachen.neu.json, bewertung.patch, commit.txt}` (Task 10); `spur["wachen"]`, `spur["bewertung_datei"]`.
- Produces:
  - `anwenden.geaenderte_schluessel(alt_text: str, neu_text: str) -> set[str]` — JSON-Schlüssel, deren Wert sich zwischen den beiden Texten unterscheidet (beide Texte werden zum Vergleich geparst; Fehlerfall → `ValueError`).
  - `anwenden.denylist_ok(schluessel: set[str]) -> tuple[bool, str]` — `False` + Name, wenn ein Schlüssel in `DENYLIST` liegt oder mit `freigabe`/`drawdown`/`kill_switch`/`herzschlag` beginnt.
  - `anwenden.baum_sauber(pfade: list[str], repo: Path) -> tuple[bool, str]` — `git status --porcelain -- <pfade>` leer **und** kein Eintrag im Index.
  - `anwenden.anwenden(ordner: Path, spur: dict, repo: Path) -> dict` — `{"ok": bool, "grund": str, "commit": str | None}`. Ablauf exakt: `baum_sauber` → `geaenderte_schluessel` + `denylist_ok` → `.bak` nach `verbesserer/bak/<zeit>/` → `wachen.neu.json` nach `spur["wachen"]` schreiben (Bytes 1:1, **kein** Reserialisieren) → `bewertung.patch` via `git apply` (nur wenn nicht leer) → `git add <wachen> <bewertung>` → `git commit -F commit.txt` → Ordner nach `berichte/erledigt/` → `commit` = kurzer Hash.
  - `anwenden.ablehnen(ordner: Path, grund: str) -> None` — Ordner nach `berichte/abgelehnt/`, `grund` in `ordner/ABGELEHNT.txt`.

- [ ] **Step 1: Failing test schreiben** — `tests/test_anwenden.py`

```python
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import anwenden  # noqa: E402

WACHEN_ALT = '{\r\n  "mindest_score": 60,\r\n  "handel_erlaubt": false\r\n}\r\n'


def _git(repo, *a):
    return subprocess.run(["git", *a], cwd=repo, capture_output=True,
                          text=True, check=True)


def _repo():
    d = Path(TemporaryDirectory().name)
    d.mkdir(parents=True)
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t")
    _git(d, "config", "user.name", "t")
    return d


class TestAnwenden(unittest.TestCase):
    def test_geaenderte_schluessel(self):
        neu = WACHEN_ALT.replace("60", "65")
        self.assertEqual(anwenden.geaenderte_schluessel(WACHEN_ALT, neu),
                         {"mindest_score"})

    def test_denylist_faengt_handel_erlaubt(self):
        ok, name = anwenden.denylist_ok({"mindest_score", "handel_erlaubt"})
        self.assertFalse(ok)
        self.assertEqual(name, "handel_erlaubt")

    def test_denylist_faengt_freigabe_praefix(self):
        ok, _ = anwenden.denylist_ok({"freigabe"})
        self.assertFalse(ok)

    def test_schmutziger_baum_bricht_ab(self):
        repo = _repo()
        wachen = repo / "wachen.json"
        wachen.write_text(WACHEN_ALT, "utf-8", newline="")
        _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "init")
        wachen.write_text(WACHEN_ALT.replace("60", "61"), "utf-8", newline="")
        r = anwenden.anwenden(repo / "v", {"wachen": str(wachen),
                              "bewertung_datei": str(repo / "b.py")}, repo)
        self.assertFalse(r["ok"])
        self.assertIn("Baum", r["grund"])

    def test_erfolg_crlf_bleibt_und_ein_commit(self):
        repo = _repo()
        wachen = repo / "wachen.json"
        bew = repo / "b.py"
        wachen.write_text(WACHEN_ALT, "utf-8", newline="")
        bew.write_text("CHANCE_GEWICHTE = {'trend': 0.30}\n", "utf-8")
        _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "init")
        ordner = repo / "v"; ordner.mkdir()
        (ordner / "wachen.neu.json").write_text(
            WACHEN_ALT.replace('"mindest_score": 60', '"mindest_score": 65'),
            "utf-8", newline="")
        (ordner / "bewertung.patch").write_text("", "utf-8")
        (ordner / "commit.txt").write_text(
            "verbesserer: Test\n\nGebuehr/Trefferquote/Funding/Liquidations n/a\n\n"
            "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\n", "utf-8")
        r = anwenden.anwenden(ordner, {"wachen": str(wachen),
                              "bewertung_datei": str(bew)}, repo)
        self.assertTrue(r["ok"], r["grund"])
        self.assertEqual(wachen.read_bytes().count(b"\r\n"),
                         WACHEN_ALT.count("\r\n"))
        log = _git(repo, "log", "--oneline").stdout.strip().splitlines()
        self.assertEqual(len(log), 2)  # init + ein Vorschlag
        self.assertIn("Co-Authored-By",
                      _git(repo, "log", "-1", "--format=%B").stdout)

    def test_commit_beruehrt_nur_zwei_dateien(self):
        # wie oben, danach:  git show --stat HEAD  -> genau wachen.json (+ b.py)
        pass
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k anwenden`
Erwartet: FAIL — `anwenden` fehlt.

- [ ] **Step 3: `anwenden.py` implementieren**

- `geaenderte_schluessel`: beide Texte `json.loads`; rekursiv oberste
  Ebene vergleichen; Schlüssel mit ungleichem Wert sammeln.
- `denylist_ok`: `for s in schluessel: if s in suche.DENYLIST or
  s.split("_")[0] in {"freigabe","drawdown","kill","herzschlag"} or
  s.startswith(("freigabe","drawdown","kill_switch","herzschlag")): return
  False, s`; sonst `True, ""`.
- `baum_sauber`: `git status --porcelain -- <pfade>`; nicht leer → `False`.
  Zusätzlich `git diff --cached --name-only` — nicht leer → `False`
  („Index nicht leer").
- `anwenden`:
  1. `pfade = [spur["wachen"], spur["bewertung_datei"]]`;
     `ok, g = baum_sauber(pfade, repo)`; `if not ok: return
     {"ok": False, "grund": "Arbeitsbaum nicht sauber: " + g, "commit": None}`.
  2. `alt = Path(spur["wachen"]).read_text("utf-8")`;
     `neu = (ordner / "wachen.neu.json").read_text("utf-8")`;
     `sch = geaenderte_schluessel(alt, neu)`;
     `ok, name = denylist_ok(sch)`; `if not ok: return {... "grund":
     "Denylist: " + name ...}`.
  3. `bak = WURZEL / "bak" / zeitstempel`; `bak.mkdir(parents=True)`;
     beide Zieldateien hineinkopieren (`shutil.copy2`).
  4. `Path(spur["wachen"]).write_bytes((ordner /
     "wachen.neu.json").read_bytes())` — Bytes 1:1.
  5. `patch = (ordner / "bewertung.patch").read_text("utf-8")`;
     `if patch.strip(): subprocess.run(["git","apply",
     str(ordner/"bewertung.patch")], cwd=repo, check=True)`.
  6. `subprocess.run(["git","add", spur["wachen"],
     spur["bewertung_datei"]], cwd=repo, check=True)`.
  7. `subprocess.run(["git","commit","-F", str(ordner/"commit.txt")],
     cwd=repo, check=True)`.
  8. Ordner nach `WURZEL / "berichte" / "erledigt" / ordner.name`
     verschieben.
  9. `commit = subprocess.run(["git","rev-parse","--short","HEAD"], …)`.
- `ablehnen`: `ABGELEHNT.txt` schreiben, Ordner nach
  `berichte/abgelehnt/`.

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/verbesserer/anwenden.py Agenten/Handel/verbesserer/tests/test_anwenden.py
git commit -m "$(printf 'verbesserer/anwenden: Denylist, .bak, CRLF-Apply, Einzel-Commit (TP4 Teil 1)\n\nPrueft zuerst den Arbeitsbaum (sauber + Index leer), dann die geaenderten\nJSON-Schluessel gegen die feste Denylist. Sichert .bak, schreibt wachen.json\nbyteweise (CRLF bleibt), wendet den Gewichts-Patch per git apply an, staged\nnur die zwei Dateien und committet mit der vorbereiteten Nachricht.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 12: `digest.py` — wöchentlicher LLM-Aufruf (TP5)

**Files:**
- Create: `Agenten/Handel/verbesserer/digest.py`
- Create: `Agenten/Handel/verbesserer/tests/test_digest.py`

**Interfaces:**
- Consumes: `konfig["llm"]`; Befund (Task 4); `basis_wf`, `kandidat_wf` (Task 7).
- Produces:
  - `digest.erzeuge(befund: dict, basis_wf: dict, kandidat_wf: dict | None, aenderungen: dict, llm_konf: dict, ruf=None) -> dict` — `{"empfehlungen": str, "lehren": str, "uebersprungen": str | None}`. `ruf` überschreibt den HTTP-Aufruf (Tests). `modus == "aus"` oder jeder Fehler → `uebersprungen` gesetzt, Strings leer.
  - `digest.annotiere_bericht(bericht_pfad: Path, ergebnis: dict) -> None` — fügt `## Priorisierte Empfehlungen (LLM)` mit dem Text (oder der Übersprungen-Notiz) am Anfang nach der ersten Überschrift ein.
  - `digest.haenge_lehren_an(pfad: Path, lehren: str, datum: str) -> None` — hängt einen `## <datum>`-Block an `Werkstatt/handelslehren-eingang.md` an (Datei anlegen, wenn nötig).

- [ ] **Step 1: Failing test schreiben** — `tests/test_digest.py`

```python
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
import digest  # noqa: E402

BEFUND = {"befunde": [{"merkmal": "grund", "auspraegung": "stop",
                       "n": 12, "mittel_gv": -1.2}]}
BASIS = {"gesamt": {"netto_gv_je_runde": -0.1, "n": 30}}
KAND = {"gesamt": {"netto_gv_je_runde": 0.05, "n": 30}}


class TestDigest(unittest.TestCase):
    def test_modus_aus_wird_uebersprungen(self):
        r = digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "aus"})
        self.assertIsNotNone(r["uebersprungen"])
        self.assertEqual(r["empfehlungen"], "")

    def test_ruf_fehler_wird_uebersprungen(self):
        def kaputt(*a, **k):
            raise OSError("keine Verbindung")
        r = digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "ollama"},
                           ruf=kaputt)
        self.assertIn("keine Verbindung", r["uebersprungen"])

    def test_erfolg_liefert_texte(self):
        def ruf(prompt, konf):
            return "1. Stops zu eng\n2. DOGE raus\n\nLEHREN: Enge Stops kosten."
        r = digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "ollama"}, ruf=ruf)
        self.assertIn("Stops", r["empfehlungen"])
        self.assertIsNone(r["uebersprungen"])

    def test_annotiere_bericht_setzt_abschnitt_vorn(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "bericht.md"
            p.write_text("# Vorschlag spur1\n\nInhalt\n", "utf-8")
            digest.annotiere_bericht(p, {"empfehlungen": "Mach X", "uebersprungen": None})
            t = p.read_text("utf-8")
            self.assertLess(t.index("Priorisierte Empfehlungen"), t.index("Inhalt"))

    def test_lehren_anhaengen_legt_datei_an(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "handelslehren-eingang.md"
            digest.haenge_lehren_an(p, "Enge Stops kosten.", "2026-09-13")
            self.assertIn("2026-09-13", p.read_text("utf-8"))

    def test_digest_aendert_wachen_neu_nicht(self):
        with TemporaryDirectory() as d:
            w = Path(d) / "wachen.neu.json"
            w.write_text('{"mindest_score": 65}', "utf-8")
            vorher = w.read_bytes()
            digest.erzeuge(BEFUND, BASIS, KAND, {}, {"modus": "aus"})
            self.assertEqual(w.read_bytes(), vorher)
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k digest`
Erwartet: FAIL.

- [ ] **Step 3: `digest.py` implementieren**

- `erzeuge`: `modus = llm_konf.get("modus", "aus")`. `if modus == "aus":
  return {"empfehlungen": "", "lehren": "", "uebersprungen": "LLM-Modus
  aus"}`. `ruf = ruf or _ruf_http`. `try: text = ruf(_prompt(befund,
  basis_wf, kandidat_wf, aenderungen), llm_konf)` — `except Exception as e:
  return {..., "uebersprungen": "LLM nicht erreichbar: " + str(e)}`.
  Text an `LEHREN:` (oder `## Lehren`) in `empfehlungen` / `lehren`
  aufteilen; keine Marke → alles in `empfehlungen`, `lehren = ""`.
  `uebersprungen = None`.
- `_ruf_http`: `modus == "ollama"` → `POST {url}/api/generate` mit
  `{"model": …, "prompt": …, "stream": false}`, `timeout = konf["timeout_s"]`,
  Antwortfeld `response`. `modus == "cliproxy"` → `POST
  {os.environ[base_url_env]}/v1/chat/completions`,
  `Authorization: Bearer {os.environ[schluessel_env]}`,
  `{"model": …, "messages": [{"role": "user", "content": …}]}`,
  Antwort `choices[0].message.content`. Nur `urllib`.
- `_prompt`: deutsch, knapp; nennt die Befunde, `netto_gv_je_runde`
  vorher/nachher, die geänderten Schlüssel; verlangt „2–4 priorisierte
  Empfehlungen", danach eine Zeile `LEHREN:` mit 1–3 Klartext-Sätzen,
  und einen ausdrücklichen „nicht anfassen"-Hinweis, wenn
  `basis_wf["gesamt"]["n"] < 20`.
- `annotiere_bericht`: Datei lesen, nach der ersten `#`-Zeile den Block
  `\n## Priorisierte Empfehlungen (LLM)\n\n<text oder Notiz>\n` einfügen,
  zurückschreiben.
- `haenge_lehren_an`: `mode="a"`, `f"\n## {datum}\n\n{lehren}\n"`; Datei
  anlegen, falls nicht vorhanden.

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS (6 Tests)

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/verbesserer/digest.py Agenten/Handel/verbesserer/tests/test_digest.py
git commit -m "$(printf 'verbesserer/digest: woechentlicher LLM-Aufruf (TP5)\n\nModus aus/ollama/cliproxy. Jeder Fehler und modus=aus -> uebersprungen, der\nVorschlag bleibt gueltig. Ausgabe: Abschnitt vorn im bericht.md, Lehren datiert\nan Werkstatt/handelslehren-eingang.md. Das Modell annotiert nur - es aendert\nden Diff nie.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 13: `lauf.py` — Orchestrator

**Files:**
- Create: `Agenten/Handel/verbesserer/lauf.py`
- Create: `Agenten/Handel/verbesserer/tests/test_lauf.py`

**Interfaces:**
- Consumes: alle Module oben; `spuren.json`, `konfig.json`.
- Produces:
  - `lauf.einmal(spur_name: str, *, kerzen_holen=True, jetzt=None) -> Path | None` — führt die Kette aus, legt den Vorschlags- oder `kein-vorschlag`-Ordner unter `verbesserer/berichte/<datum>-<spur>/` an und gibt seinen Pfad zurück; `None` bei hartem Abbruch (kein Kerzen-Cache).
  - CLI: `python lauf.py --spur spur1 [--ohne-kerzen-abruf]`.

- [ ] **Step 1: Failing test schreiben** — `tests/test_lauf.py`

```python
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import lauf  # noqa: E402


class TestLauf(unittest.TestCase):
    def test_kein_kerzencache_bricht_ab(self):
        with TemporaryDirectory() as d:
            lauf.KERZEN_DIR = Path(d) / "leer"
            r = lauf.einmal("spur1", kerzen_holen=False)
            self.assertIsNone(r)

    def test_zu_wenig_runden_gibt_kein_vorschlag(self):
        # Journal-Fixture mit < overfit_min_runden Runden + Kerzen-Cache
        # vorbereiten (monkeypatch von auswerter/ruecktest/suche/digest auf
        # Fakes), einmal() laufen lassen:
        p = lauf.einmal("spur1", kerzen_holen=False)
        self.assertTrue((p / "bericht.md").exists())
        self.assertFalse((p / "commit.txt").exists())
```

(Der zweite Test braucht Monkeypatching von `kerzen.laden`, `auswerter.befund`, `suche.suche` → Ergebnis mit `kandidat=None`, `digest.erzeuge`. Als `setUp` mit `unittest.mock.patch` schreiben; Fakes liefern Minimalstrukturen.)

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k test_lauf`
Erwartet: FAIL.

- [ ] **Step 3: `lauf.py` implementieren**

```python
"""Orchestrator: eine Woche Selbstverbesserung fuer eine Spur."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))

import auswerter, digest, kerzen, ruecktest, suche, vorschlag  # noqa: E402
import bewertung  # noqa: E402

KERZEN_DIR = WURZEL / "kerzen"
BERICHTE = WURZEL / "berichte"
LEHREN = WURZEL.parents[2] / "Werkstatt" / "handelslehren-eingang.md"


def _konf():
    return (json.loads((WURZEL / "konfig.json").read_text("utf-8")),
            json.loads((WURZEL / "spuren.json").read_text("utf-8")))


def einmal(spur_name, *, kerzen_holen=True, jetzt=None):
    konfig, spuren = _konf()
    spur = spuren[spur_name]; spur.setdefault("name", spur_name)
    wachen = json.loads((WURZEL / spur["wachen"]).resolve().read_text("utf-8"))
    watchlist = wachen["watchlist"]
    tage = konfig["oos_training_tage"] + 6 * konfig["oos_test_tage"]

    kerzen_je_inst = {}
    for inst in watchlist:
        if kerzen_holen:
            try:
                kerzen.hole(inst, tage, KERZEN_DIR)
            except Exception as e:  # noqa: BLE001
                print("  Kerzen %s: %s - nehme Cache" % (inst, e), file=sys.stderr)
        k, alter = kerzen.laden(inst, KERZEN_DIR)
        if k:
            kerzen_je_inst[inst] = k
    if len(kerzen_je_inst) < 3:
        print("Kein ausreichender Kerzen-Cache - Abbruch.", file=sys.stderr)
        return None

    datum = (jetzt or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    ordner = BERICHTE / ("%s-%s" % (datum, spur_name))
    ordner.mkdir(parents=True, exist_ok=True)

    befund = auswerter.befund(spur, konfig, ordner)
    basis = suche.basis_kandidat(wachen, bewertung.CHANCE_GEWICHTE,
                                 bewertung.RISIKO_GEWICHTE)
    grenzen = spur["aenderbar"]["wachen.json"]
    grenzen = {**grenzen, "stop_min": grenzen.get("pflicht_stop_prozent_min", [4, 8]),
               "stop_max": grenzen.get("pflicht_stop_prozent_max", [8, 15])}
    ergebnis = suche.suche(basis, kerzen_je_inst, konfig, grenzen)

    if ergebnis["kandidat"] is not None:
        vorschlag.baue(ordner, ergebnis, spur, konfig)
    else:
        vorschlag.kein_vorschlag(ordner, ergebnis, spur_name)

    d = digest.erzeuge(befund, ergebnis["basis_wf"], ergebnis["kandidat_wf"],
                       ergebnis.get("aenderungen", {}), konfig["llm"])
    digest.annotiere_bericht(ordner / "bericht.md", d)
    if d["lehren"]:
        digest.haenge_lehren_an(LEHREN, d["lehren"], datum)
    return ordner


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--spur", default="spur1")
    p.add_argument("--ohne-kerzen-abruf", action="store_true")
    a = p.parse_args()
    o = einmal(a.spur, kerzen_holen=not a.ohne_kerzen_abruf)
    print("Abbruch." if o is None else "Ordner: %s" % o)
    sys.exit(0 if o else 1)
```

Pfad-Feinschliff (`spur["wachen"]` ist relativ zu `WURZEL`) beim
Implementieren gegen die echten Dateien prüfen.

- [ ] **Step 4: Test läuft grün**

Run: wie Step 2
Erwartet: PASS

- [ ] **Step 5: Trockenlauf gegen echte Daten (Kerzen-Cache aus Task 3 Step 5)**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe Agenten/Handel/verbesserer/lauf.py --spur spur1 --ohne-kerzen-abruf`
Erwartet: Ordner `berichte/<datum>-spur1/` mit `bericht.md` und Befund-JSON. Bei zu dünner Journal-Historie: „kein Vorschlag" — das ist der erwartete Normalfall am Anfang.

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/verbesserer/lauf.py Agenten/Handel/verbesserer/tests/test_lauf.py
git commit -m "$(printf 'verbesserer/lauf: Orchestrator --spur spur1\n\nKerzen auffrischen -> Auswerter -> Suche (Baseline + Kandidat) -> Vorschlag\noder kein-Vorschlag -> Digest -> Bericht annotieren, Lehren anhaengen. Harter\nAbbruch nur ohne Kerzen-Cache.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 14: `dauerlauf.py` — Anfrage-Typ `verbesserung` (TP4, Teil 2)

**Files:**
- Modify: `Agenten/Handel/dauerlauf.py`
- Create: `Agenten/Handel/verbesserer/anfrage.py`
- Create: `Agenten/Handel/verbesserer/tests/test_anfrage.py`

**Interfaces:**
- Consumes: `verbesserer/berichte/` Ordnerstruktur; `anwenden.anwenden` / `anwenden.ablehnen` (Task 11).
- Produces (`anfrage.py`, damit `dauerlauf.py` nur dünn aufruft):
  - `anfrage.offener_vorschlag(berichte_dir: Path) -> Path | None` — jüngster direkter Unterordner von `berichte_dir` mit `commit.txt`, der **nicht** in `erledigt/` oder `abgelehnt/` liegt und keine Datei `ANGEFRAGT` enthält. `None`, wenn keiner.
  - `anfrage.markiere_angefragt(ordner: Path) -> None` — legt leere Datei `ordner/ANGEFRAGT` an.
  - `anfrage.text(ordner: Path) -> str` — Telegram-Kurztext: Spur, geänderte Schlüssel aus `commit.txt` (erste Blockzeilen), OOS-Delta, Schluss „/ja wendet an und committet, /nein archiviert".
  - `anfrage.wartet(berichte_dir: Path) -> Path | None` — Ordner mit `ANGEFRAGT`, aber noch nicht in `erledigt/`/`abgelehnt/`.

- [ ] **Step 1: `dauerlauf.py` lesen** — `pruefe_anfragen()` (ab Zeile ~189) und den Befehls-Block für `/ja`/`/nein` (ab ~260). Verstehen, wie `self.sende()` und die Kommandozerlegung arbeiten.

- [ ] **Step 2: Failing test schreiben** — `tests/test_anfrage.py`

```python
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
import anfrage  # noqa: E402


class TestAnfrage(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.b = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _mach(self, name):
        o = self.b / name
        o.mkdir(parents=True)
        (o / "commit.txt").write_text(
            "verbesserer: Scanner/OKX Parameter angepasst\n\n"
            "Geaenderte Schluessel: mindest_score\n", "utf-8")
        return o

    def test_offener_vorschlag_findet_neuen(self):
        o = self._mach("2026-09-13-spur1")
        self.assertEqual(anfrage.offener_vorschlag(self.b), o)

    def test_angefragt_wird_uebersprungen(self):
        o = self._mach("2026-09-13-spur1")
        anfrage.markiere_angefragt(o)
        self.assertIsNone(anfrage.offener_vorschlag(self.b))
        self.assertEqual(anfrage.wartet(self.b), o)

    def test_erledigt_wird_ignoriert(self):
        o = self._mach("erledigt/2026-09-01-spur1")
        self.assertIsNone(anfrage.offener_vorschlag(self.b))

    def test_text_nennt_schluessel(self):
        o = self._mach("2026-09-13-spur1")
        self.assertIn("mindest_score", anfrage.text(o))
        self.assertIn("/ja", anfrage.text(o))
```

- [ ] **Step 3: Test läuft und schlägt fehl**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v -k anfrage`
Erwartet: FAIL.

- [ ] **Step 4: `anfrage.py` implementieren** — reine Ordner-/Textlogik nach den Interfaces oben. `erledigt/` und `abgelehnt/` per `part in ("erledigt", "abgelehnt")` in den Pfadteilen ausschließen.

- [ ] **Step 5: Test läuft grün**

Run: wie Step 3
Erwartet: PASS (4 Tests)

- [ ] **Step 6: `dauerlauf.py` anbinden**

Oben bei den Importen (nach `import freigabefenster`):

```python
sys.path.insert(0, str(Path(__file__).resolve().parent / "verbesserer"))
try:
    import anfrage as verbesserer_anfrage
    import anwenden as verbesserer_anwenden
    _VERBESSERER = Path(__file__).resolve().parent / "verbesserer" / "berichte"
except Exception:  # noqa: BLE001 - Modul optional
    verbesserer_anfrage = None
```

In `pruefe_anfragen()` ans Ende (nur wenn `verbesserer_anfrage` da ist und
keine Freigabe-Anfrage offen ist):

```python
        if verbesserer_anfrage and not any(
                freigabefenster.lade(s).anfrage_offen() for s in self.spuren):
            offen = verbesserer_anfrage.offener_vorschlag(_VERBESSERER)
            if offen:
                self.sende(verbesserer_anfrage.text(offen))
                verbesserer_anfrage.markiere_angefragt(offen)
```

Im `/ja`-Zweig, **bevor** die Freigabe-Logik greift, den Verbesserer-Fall
abfangen (nur wenn keine Freigabe-Anfrage offen ist):

```python
        if verbesserer_anfrage:
            wartet = verbesserer_anfrage.wartet(_VERBESSERER)
            if wartet and not freigabefenster.lade(spur).anfrage_offen():
                r = verbesserer_anwenden.anwenden(
                    wartet, self._spur_konf(spur),
                    Path(__file__).resolve().parents[2])
                self.sende("Vorschlag angewandt: %s" % r["commit"]
                           if r["ok"] else "Vorschlag NICHT angewandt: %s"
                           % r["grund"])
                return
```

`/nein`-Zweig analog mit `verbesserer_anwenden.ablehnen(wartet, "per /nein
abgelehnt")`.

`self._spur_konf(spur)` = kleiner Helfer, der `spuren.json` lädt und den
Eintrag mit aufgelösten absoluten Pfaden für `wachen`/`bewertung_datei`
zurückgibt.

- [ ] **Step 7: `dauerlauf.py` startet noch**

Run: `Agenten/Handel/.venv/Scripts/python.exe Agenten/Handel/dauerlauf.py --trocken --takt 1` (einige Sekunden, dann Strg+C)
Erwartet: startet ohne ImportError, ein Zyklus läuft, kein Absturz in `pruefe_anfragen`.

- [ ] **Step 8: Commit**

```bash
git add Agenten/Handel/dauerlauf.py Agenten/Handel/verbesserer/anfrage.py Agenten/Handel/verbesserer/tests/test_anfrage.py
git commit -m "$(printf 'dauerlauf: Anfrage-Typ verbesserung (TP4 Teil 2)\n\nanfrage.py haelt die reine Ordner-/Textlogik, dauerlauf ruft nur auf: pruefe\nanfragen schickt einen offenen Vorschlag per Telegram und markiert ihn\nANGEFRAGT; /ja ruft anwenden.anwenden, /nein anwenden.ablehnen. Eine offene\nFreigabe-Anfrage hat Vorrang.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

---

## Task 15: Routine, README, Abschluss

**Files:**
- Create: `Agenten/Routinen/verbesserer.ps1`
- Create: `Agenten/Handel/verbesserer/README.md`
- Verify: `.gitignore`, gesamte Testsuite

**Interfaces:**
- Consumes: `lauf.py` (Task 13).
- Produces: wöchentliche Routine; Modul-README.

- [ ] **Step 1: `verbesserer.ps1` schreiben**

```powershell
# Woechentliche Selbstverbesserung von Spur 1. Laeuft NACH handel-wachen.ps1.
# Erzeugt nur einen Vorschlag in verbesserer/berichte/ - angewandt wird er
# erst per /ja im Dauerlauf (Handelsregeln: nicht heimlich eingesetzt).
$ErrorActionPreference = "Stop"
$env:MAXHIRN_ROUTINE = "1"
$wurzel = Split-Path -Parent $PSScriptRoot
$py = Join-Path $wurzel "Handel\verbesserer\.venv\Scripts\python.exe"
$lauf = Join-Path $wurzel "Handel\verbesserer\lauf.py"
$log = Join-Path $PSScriptRoot "logs\verbesserer-$(Get-Date -Format yyyy-MM-dd).log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
& $py $lauf --spur spur1 *>&1 | Tee-Object -FilePath $log
exit $LASTEXITCODE
```

- [ ] **Step 2: Syntax-Check der Routine**

Run: `pwsh -NoProfile -Command "[void][ScriptBlock]::Create((Get-Content -Raw Agenten/Routinen/verbesserer.ps1)); 'ok'"`
Erwartet: `ok`

- [ ] **Step 3: `README.md` schreiben** — Aufbau wie `scanner/README.md`: Zweck, „Die Grundlinie kennen" (Verweis auf `Handelsbots.md` und die Overfitting-Sperre), Dateien-Tabelle, Aufrufe (`lauf.py --spur spur1`, Routine), „Was er selbst nicht tut" (nichts anwenden, keine Deckel, `auto_anwenden=false`), Verweis auf die Spec in `Werkstatt/`.

- [ ] **Step 4: Ganze Testsuite grün**

Run: `Agenten/Handel/verbesserer/.venv/Scripts/python.exe -m unittest discover -s Agenten/Handel/verbesserer/tests -v`
Erwartet: alle Tests PASS.

- [ ] **Step 5: `git status` sichten**

Run: `git status --porcelain`
Erwartet: nur die beiden neuen Dateien. Kein `berichte/`, `kerzen/`, `bak/`, `.venv/` (durch `.gitignore`).

- [ ] **Step 6: Scanner-Regression zum Schluss**

Run: `cd Agenten/Handel/scanner && .venv\Scripts\python.exe scan.py --kurz && .venv\Scripts\python.exe handeln.py --wachen`
Erwartet: beide laufen fehlerfrei; `--wachen` zeigt Bedingung 5 wie zuvor.

- [ ] **Step 7: Commit**

```bash
git add Agenten/Routinen/verbesserer.ps1 Agenten/Handel/verbesserer/README.md
git commit -m "$(printf 'verbesserer: woechentliche Routine und README\n\nverbesserer.ps1 laeuft nach handel-wachen.ps1, setzt MAXHIRN_ROUTINE=1 und\nruft lauf.py --spur spur1. Erzeugt nur einen Vorschlag; angewandt wird er per\n/ja im Dauerlauf. README nach dem Muster der anderen Handelsmodule.\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>')"
```

- [ ] **Step 8: Windows-Aufgabenplanung eintragen (manuell, durch Max)**

Kein Code — im Bericht an Max vermerken: wöchentliche Aufgabe für
`Agenten/Routinen/verbesserer.ps1` anlegen, Zeitpunkt nach dem Lauf von
`handel-wachen.ps1`. `/schedule` ist ungeeignet (Cloud-Agent ohne Zugriff
auf die lokalen Dateien) — dieselbe Begründung wie bei den anderen
Handelsroutinen.

---

## Self-Review

**Spec-Abdeckung:**
- Rahmen / Denylist / CRLF / Einzel-Commit → Task 0 (Konfig), Task 8 (`DENYLIST`), Task 10 (`wachen_neu_text`), Task 11 (`anwenden`).
- TP1 Auswerter, Segmente, Permutationstest, Umstellungsdatum → Task 4.
- TP2 Merkmals-Matrix, `bewertung.py`-Refactor, Simulation (Stop-vor-Ziel, Kosten je Seite), Walk-Forward, Pflichtzahlen → Tasks 1, 5, 6, 7.
- TP2 Angleichung `handeln.py` → Task 2.
- TP3 Suchraum + Grenzen, Koordinatenabstieg, Overfitting-Sperre → Tasks 8, 9.
- TP3 Vorschlags-Artefakte (`bericht.md`, `wachen.neu.json`, `bewertung.patch`, `commit.txt`), `kein_vorschlag` → Task 10.
- TP4 `anwenden.py` (Baum sauber, Denylist, `.bak`, Apply, Commit, erledigt/abgelehnt) → Task 11; `dauerlauf.py`-Anbindung → Task 14.
- TP5 Digest (Modi, Skip-Verhalten, Bericht-Annotation, Lehren nach `Werkstatt/`) → Task 12.
- `kerzen.py` (OKX-Historie, Cache, Offline) → Task 3.
- Orchestrator + Fehlerbehandlung (kein Cache → Abbruch, < Runden → kein Vorschlag) → Task 13.
- Wiring (Routine, README, Aufgabenplanung-Hinweis) → Task 15.
- Konfig-Schlüssel (`konfig.json`, `spuren.json`) → Task 0.

**Platzhalter:** keine „TBD"/„TODO"/„später"; Testcode ist ausgeschrieben; große Implementierungen (Simulation, Suche, `anwenden`) als konkrete Schritt-für-Schritt-Logik mit Signaturen.

**Typkonsistenz:** Kandidat-Form in Task 6 definiert, in Tasks 8/9/10/13 unverändert benutzt (`gates`, `gewichte.{chance,risiko}`, `watchlist`, `sizing`). `walk_forward`-Rückgabe (`fenster`, `gesamt`, `fenster_anzahl`) in Tasks 7/9/10 gleich. `anwenden`-Rückgabe (`ok`, `grund`, `commit`) in Tasks 11/14 gleich. `suche.suche`-Rückgabe (`kandidat`, `basis_wf`, `kandidat_wf`, `auswertungen`, `grund`, `aenderungen`) in Tasks 9/10/13 gleich. `GEBUEHR_PCT` in `kosten.py` und `handeln.py`, Gleichheit per Task 2 getestet.
