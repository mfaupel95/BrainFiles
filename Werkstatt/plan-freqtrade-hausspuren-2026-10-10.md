# Haus-Spuren als Freqtrade-Bots — Umsetzungsplan (Phase 1 + Gleichheitsrahmen)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 17 Haus-Spuren laufen als Freqtrade-Dry-Run-Bots über eine einzige Adapter-Strategie `HausSpur`, und der Leitstand zeigt alle Bots samt Backtest-Urteil in einem eigenen Reiter.

**Architecture:** Die Signal-Logik bleibt im Haus: `Agenten/Handel/hausspur_regeln.py` macht aus jeder Spur dieselbe Schnittstelle (`einstieg`, `ausstieg`, `stop_prozent`, `ziel_prozent`) und rechnet je Kerze über ein gleitendes Fenster — ohne Freqtrade-Abhängigkeit, auf dem Host testbar. `HausSpur.py` im Container ist ein dünner Übersetzer DataFrame → Kerzenliste → Spalten; der Haus-Code kommt über einen read-only-Mount `/agenten`. Der Leitstand bekommt `leitstand_freqtrade.py`, das `freqtrade_bridge.uebersicht()` im Hintergrund-Thread liest.

**Tech Stack:** Python 3 (Handel-.venv, unittest), Freqtrade `freqtradeorg/freqtrade:stable` in Docker (futures, Binance, dry_run), tkinter/ttk.

**Spec:** `Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md`

**Phase 2 (Ansatz B)** ist hier nur mit dem Gleichheitsrahmen (Task 9) enthalten. Die vektorisierten Einzelstrategien bekommen je Spur einen eigenen kurzen Plan, sobald Phase 1 läuft — sie hängen an Indikator-Interna (`ti_indikatoren.macd_mtf`, `squeeze_momentum`), deren Nachbau erst gegen echte Adapter-Signale geprüft werden kann.

## Global Constraints

- Alle Bots `dry_run: true`; kein Live-Handel, kein `forceenter`/`forceexit`; `freqtrade_bridge.py` bleibt rein lesend (nur `ERLAUBT`).
- `trading_mode: futures`, `margin_mode: isolated`, Hebel 1, Börse `binance`, Paare `BASIS/USDT:USDT`.
- Ports der neuen Bots: 8084–8100, Bind nur `127.0.0.1`. Container-Speichergrenze `--memory 700m`.
- Haus-Code im Container: `Agenten/` read-only nach `/agenten` (`:ro`). Keine Kopie der Regeln in die Strategie („importiert, nicht nachgebaut“).
- Containerstart (`bots.py start` für die 17 neuen Bots) **erst nach ausdrücklicher Freigabe durch Max** (≈ 10 GB RAM).
- Zweig `claude/freqtrade-hausspuren`, Arbeitsbaum `.worktrees/freqtrade-hausspuren`, `BRAINFILES_BEREICH=handel`. Kein `git stash`. Kein Push ohne Anweisung.
- Versionierte Textdateien nur per gezieltem Edit ändern (CRLF/LF erhalten), nie per Python-Rewrite. `bots.json` also per Edit, nicht per `json.dump`.
- Interpreter: `PY=C:/Users/faupe/Documents/BrainFiles/Agenten/Handel/.venv/Scripts/python.exe` (Handel-.venv des Hauptbaums; der Arbeitsbaum hat kein venv). Alle Läufe `$PY <datei>`, Tests direkt ausführbar wie die vorhandenen.
- Alle Texte/Kommentare deutsch, Bezeichner wie im Haus (deutsch, snake_case).

## Review Focus

1. **Zu kurze Historie** (frisch gestarteter Bot, < `mindest_kerzen`): kein Signal, keine Ausnahme — Test in Task 1 (`test_zu_wenig_kerzen_kein_signal`).
2. **Regel wirft** (z. B. Division durch 0 bei flachen Kerzen): Kerze ohne Signal, Bot läuft weiter — Test in Task 1 (`test_regel_wirft_kein_absturz`).
3. **Mount fehlt / falscher Spurname** im Container: Strategie lädt nicht und nennt den Grund — Test in Task 3 (`test_unbekannte_spur_nennt_namen`) und Probe in Task 3 Step 6.
4. **Bot antwortet nicht / hängt** im Leitstand: Reiter blockiert den Rahmen nicht, Zeile „taub“ mit Grund — Test in Task 6 (`test_taube_bots_mit_grund`, `test_refresh_blockiert_nicht`).
5. **`urteile.json` fehlt oder ist kaputt**: Reiter zeigt „—“, kein Absturz — Test in Task 6 (`test_urteile_fehlen_oder_kaputt`).

---

### Task 0: Arbeitsbaum anlegen

**Files:** keine

- [ ] **Step 1: Arbeitsbaum und Zweig**

```bash
cd C:/Users/faupe/Documents/BrainFiles && git worktree add .worktrees/freqtrade-hausspuren -b claude/freqtrade-hausspuren master
```

Alle weiteren Pfade in diesem Plan sind relativ zu `.worktrees/freqtrade-hausspuren/`. Für Läufe, die Kerzendaten, venv oder Docker-Mounts brauchen (Tasks 3, 5, 8), gilt: `user_data/data`, `.venv` und `freqtrade/.venv` liegen nur im Hauptbaum (nicht versioniert). Tests in den Tasks 1–4, 6, 9 laufen mit `$PY` (siehe Global Constraints) aus `Agenten/Handel` des Arbeitsbaums. Docker-Läufe mit Kerzendaten (Task 5 Step 4, Task 8) laufen nach dem Merge aus dem Hauptbaum.

- [ ] **Step 2: Bereich setzen** — in jeder Shell dieses Plans: `$env:BRAINFILES_BEREICH='handel'` (PowerShell) bzw. `export BRAINFILES_BEREICH=handel`.

---

### Task 1: `hausspur_regeln.py` — Register und Fensterrechnung (16 Spuren ohne ORB)

**Files:**
- Create: `Agenten/Handel/hausspur_regeln.py`
- Test: `Agenten/Handel/tests/test_hausspur_regeln.py`

**Interfaces:**
- Produces:
  - `KLASSIK: tuple[str, ...]` (11 Namen), `INDIKATOR = ("macd_mtf", "squeeze", "wavetrend", "supertrend")`, `ALLE: tuple[str, ...]` (17 inkl. `trendwende_btc`, `orb`)
  - `@dataclass(frozen=True) class Spur: name: str; einstieg: Callable[[list, dict], str|None]; ausstieg: Callable[[list, str, dict], str|None]; stop_prozent: Callable[[list, dict], float]; ziel_prozent: Callable[[list, dict, str, float], float]`
  - `wachen(name: str) -> dict`
  - `spur(name: str) -> Spur` (KeyError mit Namen bei Unbekanntem)
  - `fenster(w: dict) -> int`
  - `zeitrahmen(name: str) -> str` (Freqtrade-Schreibweise, z. B. `"4h"`)
  - `paare(name: str) -> list[str]` (`"BTC/USDT:USDT"`)
  - `signale(kerzen: list, name: str, w: dict|None = None, paar: str|None = None, ab: int = 0) -> list[dict|None]` — je Kerze `{"einstieg": "long"|"short"|None, "aus_long": str|None, "aus_short": str|None, "stop": float, "ziel": float}`, vor `ab` und unter `mindest_kerzen` `None`.
- Kerzenformat überall: `[ts_ms, o, h, l, c, v]` (wie OKX, `klassik_regeln`).

- [ ] **Step 1: Failing test schreiben**

```python
"""hausspur_regeln: eine Schnittstelle fuer alle Haus-Spuren (Freqtrade-Adapter).

Geprueft wird die Zusage, auf der der ganze Adapter steht: dieselbe Kerze gibt
dasselbe Signal wie die Spur selbst - fuer klassik_* ueber REGELN, fuer die
Indikatorspuren ueber ihr handeln.signal(k, idx, w).

Direkt ausfuehrbar:  python tests/test_hausspur_regeln.py
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hausspur_regeln as hr                                   # noqa: E402
import klassik_regeln as kr                                    # noqa: E402


def reihe(n=900, start=100.0):
    """Deterministische Kerzen mit Trends und Wenden, 1h-Abstand."""
    k, c = [], start
    for i in range(n):
        o = c
        c = start * (1 + 0.15 * math.sin(i / 37.0) + 0.05 * math.sin(i / 7.0))
        h = max(o, c) * 1.004
        l = min(o, c) * 0.996
        k.append([1_700_000_000_000 + i * 3_600_000, o, h, l, c, 1000 + i % 50])
    return k


class Register(unittest.TestCase):
    def test_alle_siebzehn(self):
        self.assertEqual(len(hr.ALLE), 17)
        for name in hr.ALLE:
            self.assertEqual(hr.spur(name).name, name)

    def test_unbekannt_nennt_namen(self):
        with self.assertRaises(KeyError) as cm:
            hr.spur("gibtsnicht")
        self.assertIn("gibtsnicht", str(cm.exception))

    def test_zeitrahmen_und_paare(self):
        self.assertEqual(hr.zeitrahmen("klassik_ema"), "4h")
        self.assertEqual(hr.zeitrahmen("macd_mtf"), "1h")
        self.assertEqual(hr.zeitrahmen("supertrend"), "4h")
        self.assertEqual(hr.zeitrahmen("orb"), "15m")
        self.assertEqual(hr.paare("klassik_ema"),
                         ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"])
        self.assertEqual(hr.paare("macd_mtf"), ["BTC/USDT:USDT", "ETH/USDT:USDT"])
        self.assertEqual(hr.paare("trendwende_btc"), ["BTC/USDT:USDT"])
        self.assertEqual(hr.paare("orb"), ["BTC/USDT:USDT", "ETH/USDT:USDT"])


class GleichesSignal(unittest.TestCase):
    def test_klassik_wie_regeln(self):
        k = reihe()
        for name in hr.KLASSIK:
            w = hr.wachen(name)
            ein, _aus = kr.REGELN[name]
            fe = hr.fenster(w)
            s = hr.signale(k, name, w)
            for i in range(len(k)):
                fenster = k[max(0, i + 1 - fe):i + 1]
                if len(fenster) < int(w.get("mindest_kerzen", 210)):
                    self.assertIsNone(s[i], (name, i))
                    continue
                erwartet = ein(fenster, w)
                if erwartet == "short" and w.get("nur_long"):
                    erwartet = None
                self.assertEqual(s[i]["einstieg"], erwartet, (name, i))

    def test_indikator_wie_handeln(self):
        k = reihe()
        for name in hr.INDIKATOR:
            w = hr.wachen(name)
            modul = hr._modul(name)
            fe = hr.fenster(w)
            s = hr.signale(k, name, w, ab=len(k) - 60)
            for i in range(len(k) - 60, len(k)):
                fenster = k[max(0, i + 1 - fe):i + 1]
                roh = modul.signal(fenster, len(fenster) - 1, w)
                erwartet = roh[0] if isinstance(roh, tuple) else roh
                self.assertEqual(s[i]["einstieg"], erwartet, (name, i))


class Grenzen(unittest.TestCase):
    def test_zu_wenig_kerzen_kein_signal(self):
        k = reihe(30)
        for name in hr.ALLE:
            self.assertTrue(all(x is None for x in hr.signale(k, name)), name)

    def test_regel_wirft_kein_absturz(self):
        flach = [[1_700_000_000_000 + i * 3_600_000, 1.0, 1.0, 1.0, 1.0, 0.0]
                 for i in range(700)]
        for name in hr.ALLE:
            s = hr.signale(flach, name, paar="BTC/USDT:USDT", ab=650)
            self.assertEqual(len(s), 700, name)

    def test_ab_spart_rechnung(self):
        s = hr.signale(reihe(), "klassik_ema", ab=890)
        self.assertTrue(all(x is None for x in s[:890]))
        self.assertTrue(all(x is not None for x in s[890:]))

    def test_stop_und_ziel(self):
        k = reihe()
        s = hr.signale(k, "klassik_ema", ab=len(k) - 1)[-1]
        self.assertEqual(s["stop"], 2.5)
        self.assertEqual(s["ziel"], 5.0)          # ziel_r_vielfaches 2.0 x 2.5
        m = hr.signale(k, "macd_mtf", ab=len(k) - 1)[-1]
        self.assertGreaterEqual(m["stop"], 5.0)   # ATR, in [5, 12] gezwungen
        self.assertLessEqual(m["stop"], 12.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen lassen, muss scheitern**

Run: `cd Agenten/Handel && $PY tests/test_hausspur_regeln.py` (aus dem Arbeitsbaum; der Interpreter liegt im Hauptbaum)
Expected: FAIL — `ModuleNotFoundError: No module named 'hausspur_regeln'`

- [ ] **Step 3: Implementierung**

```python
"""Haus-Spuren als EINE Signal-Schnittstelle - fuer den Freqtrade-Adapter.

WARUM DIESE DATEI EXISTIERT
---------------------------
Auftrag Max 10.10.2026: moeglichst viele Spuren als Freqtrade-Dry-Run-Bots
(Spec: Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md). Die Regeln leben im
Haus - in klassik_regeln.REGELN und in den handeln.py der Indikatorspuren.
Diese Datei macht daraus eine gemeinsame Form, damit die Freqtrade-Strategie
`HausSpur` nichts nachbauen muss: importiert, nicht nachgebaut.

Je Kerze wird die Regel auf DEMSELBEN Fenster gerechnet wie im Haus
(`kerzen_anzahl`, mindestens `mindest_kerzen`) - ein laengeres Fenster
veraendert EMA-Startwerte und damit Signale.

Kein Freqtrade, kein pandas: auf dem Host mit unittest pruefbar.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HANDEL = Path(__file__).resolve().parent

KLASSIK = ("klassik_sma", "klassik_ema", "klassik_macd", "klassik_bollinger",
           "klassik_donchian", "klassik_rsi", "klassik_rsi2",
           "klassik_donchian_trend", "klassik_sr_breaks", "klassik_pmax",
           "klassik_supertrend")
INDIKATOR = ("macd_mtf", "squeeze", "wavetrend", "supertrend")
ALLE = KLASSIK + INDIKATOR + ("trendwende_btc", "orb")

STOP_VORGABE = 6.0          # wie die Moon-Dev-Bots, wenn die Spur keinen nennt


@dataclass(frozen=True)
class Spur:
    name: str
    einstieg: Callable      # (k, w) -> "long" | "short" | None
    ausstieg: Callable      # (k, seite, w) -> Grund | None
    stop_prozent: Callable  # (k, w) -> float
    ziel_prozent: Callable  # (k, w, seite, stop) -> float


# --- Laden -------------------------------------------------------------------

_MODULE: dict = {}


def _lade(pfad: Path, modulname: str):
    if modulname in _MODULE:
        return _MODULE[modulname]
    spec = importlib.util.spec_from_file_location(modulname, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    _MODULE[modulname] = modul
    return modul


def _modul(name: str):
    """handeln.py der Spur `name` (Indikatorspuren, trendwende_btc, orb)."""
    return _lade(HANDEL / name / "handeln.py", "hausspur_%s" % name)


def wachen(name: str) -> dict:
    with (HANDEL / name / "wachen.json").open(encoding="utf-8") as f:
        return json.load(f)


def fenster(w: dict) -> int:
    return max(int(w.get("kerzen_anzahl") or 400), int(w.get("mindest_kerzen") or 0))


def zeitrahmen(name: str) -> str:
    if name == "orb":
        return "15m"                       # orb/handeln.py holt M15-Kerzen
    w = wachen(name)
    roh = w.get("kerzen_zeitrahmen") or w.get("kerzen_takt") or "1H"
    return roh.lower()


def _paar(inst: str) -> str:
    basis = inst.replace("_", "-").split("-")[0]
    return "%s/USDT:USDT" % basis


def paare(name: str) -> list[str]:
    w = wachen(name)
    roh = w.get("instrumente") or [w.get("instrument", "BTC-USDT-SWAP")]
    if isinstance(roh, dict):
        roh = list(roh)
    aus: list[str] = []
    for inst in roh:
        p = _paar(inst)
        if p not in aus:
            aus.append(p)
    return aus


# --- Bausteine ---------------------------------------------------------------

def _kein_ausstieg(_k, _seite, _w):
    return None


def _fester_stop(_k, w):
    return float(w.get("stop_prozent") or STOP_VORGABE)


def _ziel_r(_k, w, _seite, stop):
    return float(w.get("ziel_r_vielfaches") or 2.0) * stop


def _atr_stop(modul):
    """Stop wie in pruefe_einstieg der Indikatorspuren: ATR, in [min, max]."""
    def stop(k, w):
        idx = len(k) - 1
        atr = modul.atr_abs(k, idx, int(w.get("atr_n", 14)))
        unten = float(w.get("pflicht_stop_prozent_min", 5.0))
        if not atr or atr <= 0:
            return unten
        pct = max(atr / float(k[idx][4]) * 100.0, unten)
        return min(pct, float(w.get("pflicht_stop_prozent_max", 12.0)))
    return stop


def _klassik(name: str) -> Spur:
    kr = _lade(HANDEL / "klassik_regeln.py", "hausspur_klassik_regeln")
    ein, aus = kr.REGELN[name]

    def ausstieg(k, seite, w):
        if not w.get("ausstieg_bei_regel", True):
            return None
        return aus(k, seite, w)
    return Spur(name, ein, ausstieg, _fester_stop, _ziel_r)


def _indikator(name: str) -> Spur:
    modul = _modul(name)

    def einstieg(k, w):
        s = modul.signal(k, len(k) - 1, w)
        return s[0] if isinstance(s, tuple) else s

    ausstieg = _kein_ausstieg
    if name == "supertrend":
        def ausstieg(k, seite, w):
            linie, richtung = modul.supertrend_indikator(k, w)
            return modul.trailing_ausstieg({"seite": seite}, k, linie, richtung)
    return Spur(name, einstieg, ausstieg, _atr_stop(modul), _ziel_r)


def _trendwende() -> Spur:
    modul = _modul("trendwende_btc")

    def einstieg(k, w):
        return modul.signal({"kerzen": k}, w)

    def ausstieg(k, seite, w):
        # Dieselbe Rechnung wie trend_richtung() - nur ohne Netzabruf, auf
        # den Kerzen, die Freqtrade schon hat (alle abgeschlossen).
        if seite != "short" or not w.get("ausstieg_bei_rueckdreh", True):
            return None
        _, richtung = modul.xi.supertrend(
            k, n=int(w.get("supertrend_n", 10)),
            faktor=float(w.get("supertrend_faktor", 3.0)))
        return "rueckdreh" if richtung and richtung[-1] == 1 else None
    return Spur("trendwende_btc", einstieg, ausstieg, _fester_stop, _ziel_r)


def _baue(name: str) -> Spur:
    if name in KLASSIK:
        return _klassik(name)
    if name in INDIKATOR:
        return _indikator(name)
    if name == "trendwende_btc":
        return _trendwende()
    if name == "orb":
        return _orb()
    raise KeyError("unbekannte Haus-Spur: %r (bekannt: %s)" % (name, ", ".join(ALLE)))


_SPUREN: dict = {}


def spur(name: str) -> Spur:
    if name not in ALLE:
        raise KeyError("unbekannte Haus-Spur: %r (bekannt: %s)" % (name, ", ".join(ALLE)))
    if name not in _SPUREN:
        _SPUREN[name] = _baue(name)
    return _SPUREN[name]


def _orb() -> Spur:
    raise KeyError("orb folgt in Task 2")


# --- Rechnung je Kerze ---------------------------------------------------------

def _sicher(fn, *args):
    """Eine Regel, die wirft, gibt kein Signal - wie klassik_regeln.bauen."""
    try:
        return fn(*args)
    except Exception as e:                                     # noqa: BLE001
        print("  hausspur: Regel nicht rechenbar (%s)" % e, file=sys.stderr)
        return None


def signale(kerzen: list, name: str, w: dict | None = None,
            paar: str | None = None, ab: int = 0) -> list:
    s = spur(name)
    w = dict(w if w is not None else wachen(name))
    if paar:
        w["_paar"] = paar.split(":")[0].replace("/", "_")   # "BTC_USDT"
    fe = fenster(w)
    mindest = int(w.get("mindest_kerzen", 210))
    aus: list = [None] * len(kerzen)
    for i in range(max(0, ab), len(kerzen)):
        k = kerzen[max(0, i + 1 - fe):i + 1]
        if len(k) < mindest:
            continue
        seite = _sicher(s.einstieg, k, w)
        if seite not in ("long", "short"):
            seite = None
        if seite == "short" and w.get("nur_long"):
            seite = None
        stop = _sicher(s.stop_prozent, k, w) or STOP_VORGABE
        ziel = _sicher(s.ziel_prozent, k, w, seite or "long", stop) or 2.0 * stop
        aus[i] = {"einstieg": seite,
                  "aus_long": _sicher(s.ausstieg, k, "long", w),
                  "aus_short": _sicher(s.ausstieg, k, "short", w),
                  "stop": float(stop), "ziel": float(ziel)}
    return aus
```

Hinweis zu `mindest_kerzen`: die Indikatorspuren tragen 300/600; `klassik_*` 40–230. Fehlt der Schlüssel, gilt 210 wie in `klassik_regeln.bauen`.

- [ ] **Step 4: Tests laufen lassen**

Run: wie Step 2.
Expected: alle Tests außer denen, die `orb` berühren (`test_alle_siebzehn`, `test_zeitrahmen_und_paare` — orb-Zeilen, `test_zu_wenig_kerzen_kein_signal`, `test_regel_wirft_kein_absturz`), PASS. Die orb-Fälle scheitern mit „orb folgt in Task 2“ — das ist der Übergang zu Task 2. Läuft `test_indikator_wie_handeln` wegen eines Importfehlers in einem `handeln.py` rot (fehlendes Modul aus `Agenten/Bus`), Fehlermeldung lesen und den fehlenden Pfad prüfen — **nicht** die Spur-Datei ändern.

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/hausspur_regeln.py Agenten/Handel/tests/test_hausspur_regeln.py && git commit -m "hausspur_regeln: Haus-Spuren als eine Signal-Schnittstelle fuer Freqtrade (16 Spuren)"
```

---

### Task 2: ORB im Register

**Files:**
- Modify: `Agenten/Handel/hausspur_regeln.py` (Funktion `_orb` ersetzen)
- Test: `Agenten/Handel/tests/test_hausspur_regeln.py` (Klasse `Orb` anhängen)

**Interfaces:**
- Consumes: `Spur`, `_modul`, `_lade`, `signale` aus Task 1; `orb/wachen_orb.range_ok(range_punkte, inst_key, w)`.
- Produces: `spur("orb")` mit Regel: Range = Hoch/Tief der ersten zwei 15-min-Kerzen des UTC-Tages; Einstieg = erste Kerze danach, die außerhalb schließt; kein Einstieg ab `letzter_einstieg_min_vor_schluss` vor 24:00 UTC; Stop = Gegenseite der Range; Ziel = `ziel_k` × Range-Höhe; Ausstieg `"session_ende"` auf der letzten Kerze des Tages (23:45).

- [ ] **Step 1: Failing test anhängen** (vor `if __name__ == "__main__":`)

```python
def orb_tag(ausbruch_bei=5, richtung=1, tag_ms=1_760_054_400_000):
    """Ein UTC-Tag in 15-min-Kerzen; Range 100..110, Ausbruch an Kerze `ausbruch_bei`.

    tag_ms = 2025-10-10 00:00 UTC. Vorlauf: 300 Kerzen vom Vortag, damit
    mindest_kerzen erfuellt ist.
    """
    k = []
    for i in range(-300, 96):
        ts = tag_ms + i * 900_000
        o, h, l, c = 105.0, 110.0, 100.0, 105.0
        if i == ausbruch_bei:
            c = 112.0 if richtung > 0 else 98.0
            h, l = max(h, c), min(l, c)
        k.append([ts, o, h, l, c, 10.0])
    return k


class Orb(unittest.TestCase):
    PAAR = "ETH/USDT:USDT"

    def test_erster_ausbruch_long(self):
        k = orb_tag(5, +1)
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        idx = 300 + 5
        self.assertEqual(s[idx]["einstieg"], "long")
        self.assertTrue(all(x["einstieg"] is None for x in s[300:idx]))
        self.assertAlmostEqual(s[idx]["stop"], (112.0 - 100.0) / 112.0 * 100.0)
        w = hr.wachen("orb")
        self.assertAlmostEqual(s[idx]["ziel"], w["ziel_k"] * 10.0 / 112.0 * 100.0)

    def test_short(self):
        k = orb_tag(7, -1)
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertEqual(s[307]["einstieg"], "short")

    def test_nur_ein_einstieg_je_tag(self):
        k = orb_tag(5, +1)
        k[300 + 9][4] = 113.0                     # zweiter Ausbruch spaeter
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertIsNone(s[309]["einstieg"])

    def test_kein_einstieg_kurz_vor_schluss(self):
        k = orb_tag(93, +1)                       # 23:15 UTC
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertIsNone(s[393]["einstieg"])

    def test_session_ende(self):
        k = orb_tag(5, +1)
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertEqual(s[-1]["aus_long"], "session_ende")
        self.assertIsNone(s[-2]["aus_long"])
```

- [ ] **Step 2: Test laufen lassen, muss scheitern** — Expected: `KeyError: 'orb folgt in Task 2'`.

- [ ] **Step 3: `_orb` ersetzen**

```python
def _orb() -> Spur:
    """ORB wie orb/handeln.py, auf Kerzen statt Netzabruf.

    Range = die ersten ZWEI M15-Kerzen ab 00:00 UTC (opening_range in
    handeln.py nimmt `im_fenster[:2]`). Ein Trade je Tag: nur die ERSTE
    Kerze, die ausserhalb schliesst. range_ok kommt aus wachen_orb.py -
    dieselbe Pruefung wie im Haus.
    """
    wo = _lade(HANDEL / "orb" / "wachen_orb.py", "hausspur_wachen_orb")

    def _tag(ts):
        return datetime.fromtimestamp(ts / 1000, timezone.utc)

    def _heute(k):
        tag = _tag(k[-1][0]).date()
        i = len(k) - 1
        while i > 0 and _tag(k[i - 1][0]).date() == tag:
            i -= 1
        heute = k[i:]
        if _tag(heute[0][0]).hour != 0 or _tag(heute[0][0]).minute != 0:
            return None                    # Tagesanfang fehlt im Fenster
        return heute

    def _range(k, w):
        heute = _heute(k)
        if not heute or len(heute) < 3:
            return None
        hoch = max(heute[0][2], heute[1][2])
        tief = min(heute[0][3], heute[1][3])
        if not wo.range_ok(hoch - tief, w.get("_paar") or w.get("instrument_aktiv"), w):
            return None
        return heute, hoch, tief

    def einstieg(k, w):
        r = _range(k, w)
        if not r:
            return None
        heute, hoch, tief = r
        jetzt = _tag(heute[-1][0])
        schluss_min = 24 * 60 - int(w.get("letzter_einstieg_min_vor_schluss", 60))
        if jetzt.hour * 60 + jetzt.minute >= schluss_min:
            return None
        for z in heute[2:-1]:
            if z[4] > hoch or z[4] < tief:
                return None                # heute schon ausgebrochen
        c = heute[-1][4]
        if c > hoch:
            return "long"
        if c < tief:
            return "short"
        return None

    def stop(k, w):
        r = _range(k, w)
        c = float(k[-1][4])
        if not r:
            return STOP_VORGABE
        _, hoch, tief = r
        abstand = (c - tief) if c >= hoch else (hoch - c)
        return max(abstand, 1e-9) / c * 100.0

    def ziel(k, w, _seite, stop_pct):
        r = _range(k, w)
        if not r:
            return 2.0 * stop_pct
        _, hoch, tief = r
        return float(w.get("ziel_k", 1.5)) * (hoch - tief) / float(k[-1][4]) * 100.0

    def ausstieg(k, _seite, _w):
        t = _tag(k[-1][0])
        return "session_ende" if (t.hour, t.minute) == (23, 45) else None

    return Spur("orb", einstieg, ausstieg, stop, ziel)
```

Vor dem Einbau prüfen: `grep -n "def range_ok" -A15 Agenten/Handel/orb/wachen_orb.py` — erwartet `range_ok(range_punkte, inst_key, w) -> bool` mit `mindest_range_punkte`/`max_range_punkte` je Schlüssel `"BTC_USDT"`/`"ETH_USDT"`. Gibt sie ein Tupel `(ok, grund)` zurück, `wo.range_ok(...)[0]` verwenden. In `orb_tag` ist die Range 10 Punkte; liegt `mindest_range_punkte["ETH_USDT"]` (5) darunter, passt der Test. Hat `orb/wachen.json` kein `mindest_kerzen`, greift die Vorgabe 210 — die 300 Vorlaufkerzen reichen.

- [ ] **Step 4: Alle Tests der Datei laufen lassen** — Expected: PASS (inkl. der Task-1-Fälle mit orb).

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/hausspur_regeln.py Agenten/Handel/tests/test_hausspur_regeln.py && git commit -m "hausspur_regeln: ORB (Range der ersten 30 min, ein Ausbruch je UTC-Tag)"
```

---

### Task 3: Strategie `HausSpur` und `bots.py` (Mount, Futures, Speichergrenze)

**Files:**
- Create: `Agenten/Handel/freqtrade/user_data/strategies/HausSpur.py`
- Modify: `Agenten/Handel/freqtrade/bots.py` (`config_fuer`, `_daten_fenster`, `cmd_daten`, `cmd_backtest`, `cmd_start`, neue Funktion `mounts`)
- Test: `Agenten/Handel/freqtrade/tests/test_bots_hausspur.py`

**Interfaces:**
- Consumes: `hausspur_regeln.spur`, `wachen`, `signale` (Tasks 1–2).
- Produces:
  - `bots.HAUS = HIER.parent.parent` (= `Agenten/`), `bots.HAUS_IM_CONTAINER = "/agenten"`
  - `bots.mounts(bot: dict) -> list[str]` — `["-v", "<user_data>:/freqtrade/user_data"]`, plus `["-v", "<Agenten>:/agenten:ro"]` wenn `bot.get("hausspur")`
  - `config_fuer(bot)` ergänzt bei `hausspur`: `"trading_mode": "futures"`, `"margin_mode": "isolated"`, `"hausspur": {"name": bot["hausspur"], "pfad": "/agenten/Handel"}`
  - Strategieklasse `HausSpur(IStrategy)`, Config-Schlüssel `hausspur.name`, `hausspur.pfad`, `hausspur.nachrechnen` (Vorgabe 3).

- [ ] **Step 1: Failing test**

```python
"""bots.py fuer HausSpur-Bots: Mount, Futures, Speichergrenze.

Direkt ausfuehrbar:  python freqtrade/tests/test_bots_hausspur.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bots                                                    # noqa: E402

HAUSBOT = {"name": "klassik-ema", "container": "freqtrade-klassik-ema",
           "strategie": "HausSpur", "hausspur": "klassik_ema", "port": 8085,
           "zeitrahmen": "4h", "max_open_trades": 3,
           "whitelist": ["BTC/USDT:USDT"]}
MOONBOT = {"name": "trading-agent", "container": "freqtrade-trading-agent",
           "strategie": "MoonDevTradingAgent", "port": 8081,
           "zeitrahmen": "1h", "whitelist": ["BTC/USDT"]}


class Config(unittest.TestCase):
    def test_hausspur_ist_futures_mit_name(self):
        c = bots.config_fuer(HAUSBOT)
        self.assertEqual(c["trading_mode"], "futures")
        self.assertEqual(c["margin_mode"], "isolated")
        self.assertEqual(c["hausspur"], {"name": "klassik_ema",
                                         "pfad": "/agenten/Handel"})
        self.assertTrue(c["dry_run"])

    def test_moondev_bleibt_spot(self):
        c = bots.config_fuer(MOONBOT)
        self.assertEqual(c["trading_mode"], "spot")
        self.assertNotIn("hausspur", c)


class Mounts(unittest.TestCase):
    def test_haus_nur_lesend_bei_hausspur(self):
        m = bots.mounts(HAUSBOT)
        self.assertIn(f"{bots.HAUS.resolve().as_posix()}:/agenten:ro", m)
        self.assertNotIn("/agenten", " ".join(bots.mounts(MOONBOT)))

    def test_start_mit_speichergrenze_und_mount(self):
        aufrufe = []

        def falsch_docker(args):
            aufrufe.append(args)

            class R:
                returncode, stdout, stderr = 0, "", ""
            return R()
        with patch.object(bots, "docker", falsch_docker), \
                patch.object(bots, "container_laeuft", lambda n: False), \
                patch.object(Path, "exists", lambda self: True), \
                patch.object(bots, "ausgewaehlt", lambda a: [HAUSBOT]):
            bots.cmd_start(["klassik-ema"])
        run = [a for a in aufrufe if a and a[0] == "run"][0]
        self.assertIn("--memory", run)
        self.assertEqual(run[run.index("--memory") + 1], "700m")
        self.assertIn(f"{bots.HAUS.resolve().as_posix()}:/agenten:ro", run)
        self.assertIn("127.0.0.1:8085:8085", run)


class Strategie(unittest.TestCase):
    QUELLE = (Path(bots.STRATEGIEN) / "HausSpur.py")

    def test_datei_da_und_ohne_regelkopie(self):
        text = self.QUELLE.read_text(encoding="utf-8")
        self.assertIn("class HausSpur(IStrategy)", text)
        self.assertIn("hausspur_regeln", text)
        for verboten in ("def einstieg_", "ta.EMA", "rolling("):
            self.assertNotIn(verboten, text)

    def test_unbekannte_spur_nennt_namen(self):
        text = self.QUELLE.read_text(encoding="utf-8")
        self.assertIn("OperationalException", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Laufen lassen, muss scheitern** — Run: `cd Agenten/Handel/freqtrade && $PY tests/test_bots_hausspur.py` — Expected: FAIL (`KeyError: 'trading_mode'` bzw. `AttributeError: mounts`).

- [ ] **Step 3: `bots.py` ändern**

Nach `IM_CONTAINER = "/freqtrade/user_data"` einfügen:

```python
# Haus-Code fuer HausSpur-Bots: Agenten/ read-only im Container. Die Regeln
# werden importiert, nicht in die Strategie kopiert (Spec 10.10.2026).
HAUS = HIER.parent.parent
HAUS_IM_CONTAINER = "/agenten"
SPEICHER = "700m"
```

Nach `mount_pfad()` einfügen:

```python
def mounts(bot: dict) -> list[str]:
    """Die -v-Argumente fuer docker: user_data immer, Agenten/ bei HausSpur."""
    m = ["-v", f"{mount_pfad()}:{IM_CONTAINER}"]
    if bot.get("hausspur"):
        m += ["-v", f"{HAUS.resolve().as_posix()}:{HAUS_IM_CONTAINER}:ro"]
    return m
```

In `config_fuer` das `return {...}` in `cfg = {...}` umbenennen und vor dem Ende anfügen:

```python
    if bot.get("hausspur"):
        cfg["trading_mode"] = "futures"
        cfg["margin_mode"] = "isolated"
        cfg["hausspur"] = {"name": bot["hausspur"],
                           "pfad": f"{HAUS_IM_CONTAINER}/Handel"}
    return cfg
```

`_daten_fenster(paare, zeitrahmen)` → `_daten_fenster(paare, zeitrahmen, futures=False, haus=False)`; im Rückgabewert `"-v", f"{mount_pfad()}:{IM_CONTAINER}",` ersetzen durch `*mounts({"hausspur": haus}),` und vor `"--days", "400",` die Liste `*(["--trading-mode", "futures"] if futures else []),` einfügen; `"--days", "400"` → `"--days", "740"` (zwei Jahre Backtest plus Anlauf).

`cmd_daten`: Gruppierung nach `(zeitrahmen, futures)`:

```python
def cmd_daten(argumente: list[str]) -> int:
    """Kerzen laden, die der Backtest der Bots braucht - je Zeitrahmen und Modus."""
    gruppen: dict[tuple[str, bool], list[str]] = {}
    for b in ausgewaehlt(argumente):
        schluessel = (b.get("zeitrahmen", "1h"), bool(b.get("hausspur")))
        liste = gruppen.setdefault(schluessel, [])
        for p in [*b["whitelist"], *b.get("breite_paare", [])]:
            if p not in liste:
                liste.append(p)
    rc = 0
    for (tf, futures), paare in sorted(gruppen.items()):
        print(f"{len(paare)} Paare, {tf}, {'futures' if futures else 'spot'}")
        rc |= einweglauf(_daten_fenster(paare, tf, futures, futures),
                         f"download-data {tf}")
    return rc
```

`cmd_backtest` und `cmd_start`: jeweils `"-v", f"{mount_pfad()}:{IM_CONTAINER}",` ersetzen durch `*mounts(b),`. In `cmd_start` zusätzlich nach `"--restart", "unless-stopped",` einfügen: `"--memory", SPEICHER,`.

- [ ] **Step 4: Strategie schreiben** — `Agenten/Handel/freqtrade/user_data/strategies/HausSpur.py`:

```python
# pragma pylint: disable=missing-docstring, invalid-name
# flake8: noqa: F401
# isort: skip_file
"""HausSpur - EINE Freqtrade-Strategie fuer alle Haus-Spuren.

Welche Spur, steht in der Bot-Konfiguration: `"hausspur": {"name": "klassik_ema",
"pfad": "/agenten/Handel"}`. Die Regel kommt aus Agenten/Handel/hausspur_regeln.py
(read-only gemountet, siehe bots.py mounts) - hier steht KEINE Regel, nur die
Uebersetzung DataFrame -> Kerzenliste -> Spalten. Spec:
Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md.

Stop und Ziel je Trade kommen aus der Signalkerze (Spalten hs_stop, hs_ziel):
fester Prozentsatz der Spur, ATR-Stop der Indikatorspuren, Range bei ORB.
"""

import sys
from datetime import timedelta
from pathlib import Path

from pandas import DataFrame

from freqtrade.exceptions import OperationalException
from freqtrade.strategy import IStrategy, stoploss_from_open


class HausSpur(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "1h"                 # die Bot-Konfiguration setzt den echten
    stoploss = -0.99                 # echter Stop in custom_stoploss
    use_custom_stoploss = True
    minimal_roi = {"0": 100.0}       # echtes Ziel in custom_exit
    use_exit_signal = True
    exit_profit_only = False
    process_only_new_candles = True
    startup_candle_count = 600       # groesstes Haus-Fenster (macd_mtf)

    def bot_start(self, **kwargs) -> None:
        hs = self.config.get("hausspur") or {}
        name = hs.get("name")
        pfad = Path(hs.get("pfad", "/agenten/Handel"))
        if not (pfad / "hausspur_regeln.py").exists():
            raise OperationalException(
                f"HausSpur: {pfad}/hausspur_regeln.py fehlt - Mount von Agenten/ "
                f"nach /agenten (bots.py mounts) fehlt?")
        if str(pfad) not in sys.path:
            sys.path.insert(0, str(pfad))
        import hausspur_regeln as hr
        try:
            hr.spur(name)
        except KeyError as e:
            raise OperationalException(f"HausSpur: {e}") from e
        self.hr = hr
        self.hs_name = name
        self.hs_wachen = hr.wachen(name)
        self.nachrechnen = int(hs.get("nachrechnen", 3))

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        kerzen = [[int(d.timestamp() * 1000), o, h, l, c, v] for d, o, h, l, c, v in zip(
            dataframe["date"], dataframe["open"], dataframe["high"],
            dataframe["low"], dataframe["close"], dataframe["volume"])]
        laufend = self.dp.runmode.value in ("live", "dry_run")
        ab = max(0, len(kerzen) - self.nachrechnen) if laufend else 0
        werte = self.hr.signale(kerzen, self.hs_name, self.hs_wachen,
                                paar=metadata["pair"], ab=ab)
        dataframe["hs_ein"] = [x["einstieg"] if x else None for x in werte]
        dataframe["hs_aus_long"] = [bool(x and x["aus_long"]) for x in werte]
        dataframe["hs_aus_short"] = [bool(x and x["aus_short"]) for x in werte]
        dataframe["hs_stop"] = [x["stop"] if x else None for x in werte]
        dataframe["hs_ziel"] = [x["ziel"] if x else None for x in werte]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["hs_ein"] == "long", ["enter_long", "enter_tag"]] = (1, self.hs_name)
        dataframe.loc[dataframe["hs_ein"] == "short", ["enter_short", "enter_tag"]] = (1, self.hs_name)
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["hs_aus_long"], "exit_long"] = 1
        dataframe.loc[dataframe["hs_aus_short"], "exit_short"] = 1
        return dataframe

    def _signalwerte(self, pair, trade):
        """(stop %, ziel %) der Signalkerze, einmal je Trade gemerkt."""
        stop = trade.get_custom_data("hs_stop")
        ziel = trade.get_custom_data("hs_ziel")
        if stop is not None and ziel is not None:
            return float(stop), float(ziel)
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        vorher = df[df["date"] < trade.open_date_utc]
        zeile = vorher.iloc[-1] if len(vorher) else None
        stop = float(zeile["hs_stop"]) if zeile is not None and zeile["hs_stop"] == zeile["hs_stop"] else 6.0
        ziel = float(zeile["hs_ziel"]) if zeile is not None and zeile["hs_ziel"] == zeile["hs_ziel"] else 2 * stop
        trade.set_custom_data("hs_stop", stop)
        trade.set_custom_data("hs_ziel", ziel)
        return stop, ziel

    def custom_stoploss(self, pair, trade, current_time, current_rate,
                        current_profit, after_fill, **kwargs):
        stop, _ = self._signalwerte(pair, trade)
        return stoploss_from_open(-stop / 100.0, current_profit,
                                  is_short=trade.is_short, leverage=trade.leverage)

    def custom_exit(self, pair, trade, current_time, current_rate,
                    current_profit, **kwargs):
        _, ziel = self._signalwerte(pair, trade)
        if current_profit >= ziel / 100.0:
            return "ziel"
        return None

    def leverage(self, pair, current_time, current_rate, proposed_leverage,
                 max_leverage, entry_tag, side, **kwargs) -> float:
        return 1.0
```

Danach die `protections`-Eigenschaft **wörtlich** aus `moondev_basis.py` übernehmen: `grep -n "def protections" -A40 Agenten/Handel/freqtrade/user_data/strategies/moondev_basis.py`, den Block (inkl. `@property`) unverändert in die Klasse kopieren. Stehen die Schutzzahlen dort in der Config statt in der Strategie, diesen Schritt auslassen und im Commit vermerken.

- [ ] **Step 5: Tests laufen lassen** — Run wie Step 2, plus bestehende Bot-/Bridge-Tests: `cd Agenten/Handel && $PY tests/test_freqtrade_bridge.py && $PY freqtrade/tests/test_frequenzbremse.py`. Expected: PASS.

- [ ] **Step 6: Container-Probe (Import + Laden der Strategie)** — aus dem **Arbeitsbaum** (Haus-Code des Zweigs):

```bash
docker run --rm -v "$(pwd -W)/Agenten:/agenten:ro" --entrypoint python freqtradeorg/freqtrade:stable -c "import sys; sys.path.insert(0,'/agenten/Handel'); import hausspur_regeln as hr; [hr.spur(n) for n in hr.ALLE]; print('ok', len(hr.ALLE))"
```

Expected: `ok 17`. Scheitert ein Import (z. B. ein Modul aus `Agenten/Bus` braucht ein Paket, das das Image nicht hat), **stoppen und Max melden** mit Modulname und Spur — nicht die Spur umbauen.

- [ ] **Step 7: Commit**

```bash
git add Agenten/Handel/freqtrade/bots.py Agenten/Handel/freqtrade/user_data/strategies/HausSpur.py Agenten/Handel/freqtrade/tests/test_bots_hausspur.py && git commit -m "freqtrade: Strategie HausSpur + bots.py (Haus-Mount ro, futures, 700m)"
```

Vorher prüfen, dass `user_data/strategies/HausSpur.py` nicht von `.gitignore` geschluckt wird: `git check-ignore -v Agenten/Handel/freqtrade/user_data/strategies/HausSpur.py` — meldet es eine Regel, analog zu `MoonDevTradingAgent.py` eine Freigabezeile `!…/HausSpur.py` in die Wurzel-`.gitignore` per Edit ergänzen.

---

### Task 4: 17 Bots in `bots.json` + Urteile

**Files:**
- Modify: `Agenten/Handel/freqtrade/bots.json` (per Edit: 17 Einträge in `bots`, 7 Absagen in `nicht_portierbar`, `_stand`)
- Modify: `Agenten/Handel/freqtrade/bots.py` (`urteil_aus_ergebnis`, `urteil_merken`, `cmd_urteile`, `cmd_backtest` merkt Urteil, `haupt` kennt `urteile`)
- Test: `Agenten/Handel/freqtrade/tests/test_bots_hausspur.py` (Klassen `Manifest`, `Urteile` anhängen)

**Interfaces:**
- Consumes: `hausspur_regeln.ALLE`, `zeitrahmen`, `paare`; `bots.bots()`.
- Produces:
  - `bots.URTEILE = HIER / "urteile.json"` (nicht versioniert; `.gitignore` prüfen wie in Task 3)
  - `bots.urteil_aus_ergebnis(daten: dict, strategie: str) -> dict` → `{"runden": int, "netto_prozent": float, "max_ruecklauf_prozent": float, "zeitraum": "JJJJ-MM-TT..JJJJ-MM-TT"}`
  - `bots.urteil_merken(name: str, urteil: dict, pfad: Path = URTEILE) -> None` (setzt `"stand"` = ISO-Zeit UTC)
  - `urteile.json`: `{"<botname>": {"stand", "runden", "netto_prozent", "max_ruecklauf_prozent", "zeitraum"}}`

Namen und Ports (fest):

| Bot | hausspur | Port |
|---|---|---|
| klassik-sma | klassik_sma | 8084 |
| klassik-ema | klassik_ema | 8085 |
| klassik-macd | klassik_macd | 8086 |
| klassik-bollinger | klassik_bollinger | 8087 |
| klassik-donchian | klassik_donchian | 8088 |
| klassik-rsi | klassik_rsi | 8089 |
| klassik-rsi2 | klassik_rsi2 | 8090 |
| klassik-donchian-trend | klassik_donchian_trend | 8091 |
| klassik-sr-breaks | klassik_sr_breaks | 8092 |
| klassik-pmax | klassik_pmax | 8093 |
| klassik-supertrend | klassik_supertrend | 8094 |
| macd-mtf | macd_mtf | 8095 |
| squeeze | squeeze | 8096 |
| wavetrend | wavetrend | 8097 |
| supertrend | supertrend | 8098 |
| trendwende-btc | trendwende_btc | 8099 |
| orb | orb | 8100 |

- [ ] **Step 1: Failing tests anhängen**

```python
HANDEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HANDEL))
import hausspur_regeln as hr                                   # noqa: E402


class Manifest(unittest.TestCase):
    def setUp(self):
        self.alle = bots.bots()
        self.haus = [b for b in self.alle if b.get("hausspur")]

    def test_siebzehn_hausspuren(self):
        self.assertEqual(sorted(b["hausspur"] for b in self.haus), sorted(hr.ALLE))

    def test_ports_und_container_eindeutig(self):
        ports = [b["port"] for b in self.alle]
        self.assertEqual(len(ports), len(set(ports)))
        self.assertEqual(sorted(b["port"] for b in self.haus), list(range(8084, 8101)))
        self.assertEqual(len({b["container"] for b in self.alle}), len(self.alle))

    def test_zeitrahmen_und_paare_wie_wachen(self):
        for b in self.haus:
            self.assertEqual(b["zeitrahmen"], hr.zeitrahmen(b["hausspur"]), b["name"])
            self.assertEqual(b["whitelist"], hr.paare(b["hausspur"]), b["name"])
            self.assertEqual(b["strategie"], "HausSpur")
            self.assertEqual(b["max_open_trades"], len(b["whitelist"]))


ERGEBNIS = {"strategy": {"HausSpur": {
    "total_trades": 42, "profit_total": -0.0312, "max_drawdown_account": 0.081,
    "backtest_start": "2024-10-01 00:00:00", "backtest_end": "2026-10-01 00:00:00"}}}


class Urteile(unittest.TestCase):
    def test_aus_ergebnis(self):
        u = bots.urteil_aus_ergebnis(ERGEBNIS, "HausSpur")
        self.assertEqual(u, {"runden": 42, "netto_prozent": -3.12,
                             "max_ruecklauf_prozent": 8.1,
                             "zeitraum": "2024-10-01..2026-10-01"})

    def test_merken_ergaenzt(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "urteile.json"
            bots.urteil_merken("a", {"runden": 1}, p)
            bots.urteil_merken("b", {"runden": 2}, p)
            import json
            daten = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(set(daten), {"a", "b"})
            self.assertIn("stand", daten["a"])
```

- [ ] **Step 2: Laufen lassen, muss scheitern** — Expected: `test_siebzehn_hausspuren` FAIL (leere Liste), `AttributeError: urteil_aus_ergebnis`.

- [ ] **Step 3: `bots.json` per Edit ergänzen.** Vor dem `]` der `bots`-Liste (nach dem Eintrag `marktlage-regime`) 17 Objekte einfügen. Paare und Zeitrahmen **aus dem Test-Orakel ablesen**, nicht raten:

```bash
cd Agenten/Handel && $PY -c "import hausspur_regeln as hr; [print(n, hr.zeitrahmen(n), hr.paare(n)) for n in hr.ALLE]"
```

Form je Eintrag (Beispiel klassik-ema; Einrückung wie die vorhandenen Einträge der Datei):

```json
  {
   "name": "klassik-ema",
   "container": "freqtrade-klassik-ema",
   "strategie": "HausSpur",
   "hausspur": "klassik_ema",
   "port": 8085,
   "zeitrahmen": "4h",
   "max_open_trades": 3,
   "quelle": "Agenten/Handel/klassik_regeln.py (REGELN)",
   "regel": "Haus-Regel der Spur klassik_ema, importiert ueber hausspur_regeln.py.",
   "whitelist": ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"],
   "beschreibung": "Haus-Spur als Dry-Run-Bot (Auftrag Max 10.10.2026: Breite)."
  }
```

`quelle` je Gruppe: `klassik_*` → `Agenten/Handel/klassik_regeln.py (REGELN)`; Indikatorspuren, `trendwende_btc`, `orb` → `Agenten/Handel/<spur>/handeln.py`. In `nicht_portierbar` sieben Objekte anhängen, je `{"agent": "<spur> (Haus-Spur)", "hindernis": "...", "grund": "..."}`: `prophet_signal` (Prophet-Modell, eigene Abhängigkeit), `iv_wand`/`iv_waelle` (implizite Volatilität, Fremddaten), `liq_wand` (Zwangsschlüsse, Fremddaten), `gitter` (Gitterleiter statt Ein-/Ausstiegssignal), `mosaic`, `xperp`/`kraken`/`omniquant` (eigene Live-Pfade, keine übertragbare Signalregel). `_stand` → `"2026-10-10"`. Danach Gültigkeit prüfen: `python -c "import json;json.load(open('Agenten/Handel/freqtrade/bots.json',encoding='utf-8'))"`.

- [ ] **Step 4: Urteile in `bots.py`** — nach `cmd_backtest` einfügen:

```python
URTEILE = HIER / "urteile.json"


def urteil_aus_ergebnis(daten: dict, strategie: str) -> dict:
    s = daten["strategy"][strategie]
    return {"runden": int(s.get("total_trades", 0)),
            "netto_prozent": round(float(s.get("profit_total", 0.0)) * 100, 2),
            "max_ruecklauf_prozent": round(float(s.get("max_drawdown_account", 0.0)) * 100, 2),
            "zeitraum": "%s..%s" % (str(s.get("backtest_start", ""))[:10],
                                    str(s.get("backtest_end", ""))[:10])}


def urteil_merken(name: str, urteil: dict, pfad: Path = URTEILE) -> None:
    import datetime as _dt
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        daten = {}
    daten[name] = dict(urteil, stand=_dt.datetime.now(_dt.timezone.utc)
                       .isoformat(timespec="seconds"))
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def letztes_ergebnis() -> dict:
    """Die Ergebnis-JSON des letzten Backtests (Zip aus backtest_results)."""
    import zipfile
    ordner = USER_DATA / "backtest_results"
    zeiger = json.loads((ordner / ".last_result.json").read_text(encoding="utf-8"))
    zip_pfad = ordner / zeiger["latest_backtest"]
    with zipfile.ZipFile(zip_pfad) as z:
        name = next(n for n in z.namelist()
                    if n.endswith(".json") and "_config" not in n and "_market" not in n)
        return json.loads(z.read(name))


def cmd_urteile() -> int:
    try:
        daten = json.loads(URTEILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("  noch keine Urteile - erst 'python bots.py backtest'")
        return 1
    for name, u in sorted(daten.items()):
        print(f"  {name:24} {u['runden']:5d} Runden  {u['netto_prozent']:+8.2f} %  "
              f"Ruecklauf {u['max_ruecklauf_prozent']:6.2f} %  {u['zeitraum']}")
    return 0
```

In `cmd_backtest` direkt nach `rc |= einweglauf(fenster, f"backtesting {b['name']}")` einfügen (nur Normallauf, nicht Varianten):

```python
        if signal is None and b.get("hausspur"):
            try:
                urteil_merken(b["name"], urteil_aus_ergebnis(letztes_ergebnis(), b["strategie"]))
            except (OSError, ValueError, KeyError, StopIteration) as e:
                print(f"  ! Urteil {b['name']} nicht lesbar: {e}")
```

In `haupt` den Zweig `urteile` → `cmd_urteile()` ergänzen (Form wie `status`) und die Kommandozeile `python bots.py urteile` in den Modul-Docstring aufnehmen. `.gitignore`: `git check-ignore -v Agenten/Handel/freqtrade/urteile.json` — wird sie **nicht** ignoriert, ist das korrekt nur, wenn Messergebnisse im Haus versioniert werden (vgl. `backtest_urteile.json` im Handel-Ordner: versioniert). Gleich behandeln wie `backtest_urteile.json`.

- [ ] **Step 5: Tests** — Run wie Task 3 Step 2. Expected: PASS.

- [ ] **Step 6: Bereichs-Prüfung und Commit**

```bash
python Agenten/Werkzeuge/bereiche.py --aufrufer handel --pfad Agenten/Handel/freqtrade/bots.json && git add Agenten/Handel/freqtrade/bots.json Agenten/Handel/freqtrade/bots.py Agenten/Handel/freqtrade/tests/test_bots_hausspur.py && git commit -m "freqtrade: 17 Haus-Spur-Bots in bots.json, Backtest-Urteile nach urteile.json"
```

---

### Task 5: Daten, Backtests, Urteile (Messlauf, kein Containerstart)

**Files:** erzeugt `freqtrade/config.<bot>.json` (nicht versioniert), `freqtrade/urteile.json`, Kerzen unter `user_data/data/binance/futures/`.

Der volle Lauf (Step 4) geschieht nach dem Merge im Hauptbaum. Vorher (Steps 1–3) genau ein Probe-Backtest aus dem Arbeitsbaum, damit die PR einen belegten Lauf trägt; der Arbeitsbaum lädt dafür seine eigenen Kerzen (nur klassik-ema, wenige MB).

- [ ] **Step 1: Configs + Daten (Arbeitsbaum, nur klassik-ema)**

```bash
cd Agenten/Handel/freqtrade && $PY bots.py configs klassik-ema && $PY bots.py daten klassik-ema
```

Expected: `config.klassik-ema.json` mit `"trading_mode": "futures"`; Download endet ohne Fehler.

- [ ] **Step 2: Probe-Backtest** — `$PY bots.py backtest klassik-ema` — Expected: Freqtrade-Ergebnistabelle mit `HausSpur`, Zeile `klassik-ema` in `urteile.json`. Laufzeit notieren (für die Schätzung aller 17).

- [ ] **Step 3: Gegenprobe Signale** — Runden aus dem Backtest gegen die Haus-Spur halten: in `Agenten/Handel/backtest_laeufe/` bzw. `klassik_ema/handelsjournal.csv` nachsehen, ob die Größenordnung der Einstiege je Monat passt. Weicht sie um mehr als Faktor 2 ab, **stoppen** und Ursache klären (Fenster, `nur_long`, Zeitrahmen) — nicht weiter ausrollen.

- [ ] **Step 4: Nach dem Merge (Hauptbaum), alle 17**

```bash
cd Agenten/Handel/freqtrade && $PY bots.py configs && $PY bots.py daten && $PY bots.py backtest klassik-sma klassik-ema klassik-macd klassik-bollinger klassik-donchian klassik-rsi klassik-rsi2 klassik-donchian-trend klassik-sr-breaks klassik-pmax klassik-supertrend macd-mtf squeeze wavetrend supertrend trendwende-btc orb && $PY bots.py urteile
```

Expected: 17 Zeilen. Lange Laufzeit → `run_in_background`. `configs` ohne Namen schreibt alle Configs neu — die drei Moon-Dev-Bots bekommen dabei neue Zufalls-JWT; ihre laufenden Container lesen die Config nur beim Start, also unschädlich; bei Zweifel `configs` mit den 17 Namen aufrufen.

- [ ] **Step 5: Commit der Urteile** (falls versioniert, siehe Task 4 Step 4): `git add Agenten/Handel/freqtrade/urteile.json && git commit -m "freqtrade: Backtest-Urteile der 17 Haus-Spur-Bots (2 Jahre)"`

---

### Task 6: Leitstand-Reiter „FreqTrade“

**Files:**
- Create: `Agenten/Handel/leitstand_freqtrade.py`
- Modify: `Agenten/Handel/leitstand.py` (Import, `REITER`, `KUERZEL`, `TAKT_SICHTBAR`, Docstring „Strg+1..8“)
- Test: `Agenten/Handel/tests/test_leitstand_freqtrade.py`

**Interfaces:**
- Consumes: `freqtrade_bridge.uebersicht(zeitgrenze, bot_liste) -> list[dict]` (Schlüssel `name, port, strategie, zeitrahmen, max, erreichbar, dry_run, zustand, offen, trades, gewinn, fehler`), `freqtrade_bridge.bots()`, `zugang_fuer(port)`, `offene_trades(zugang)`, `trades(anzahl, zugang)`; `handelszentrale.freqtrade_offen_zeile(t)` (7 Werte), `handelszentrale.freqtrade_zu_zeilen(antwort, anzahl)` (7 Werte); `bots.URTEILE`-Pfad = `Agenten/Handel/freqtrade/urteile.json`.
- Produces:
  - `URTEILE: Path`
  - `lade_urteile(pfad: Path = URTEILE) -> dict`
  - `zeilen(uebersicht: list[dict], bot_liste: list[dict], urteile: dict) -> list[tuple]` — je Bot `(name, spur, zustand_text, offen, runden, gewinn_text, backtest_text)`
  - `titel(uebersicht) -> str` — `" (n/m)"`; leer bei leerer Liste
  - `status_text(uebersicht) -> str` — `"FreqTrade: k taub (a, b)"` oder `""`
  - `class FreqtradeReiter(ttk.Frame)` mit `__init__(eltern, leitstand, quelle=None, bot_quelle=None, urteile_pfad=None)`, `refresh()`, `titel_zusatz()`, `status()`

- [ ] **Step 1: Failing test**

```python
"""FreqTrade-Reiter im Leitstand: Tabelle aller Bots, nur lesend, blockiert nie.

Direkt ausfuehrbar:  python tests/test_leitstand_freqtrade.py
"""

import json
import sys
import tempfile
import threading
import time
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand as lst                                        # noqa: E402
import leitstand_freqtrade as lf                               # noqa: E402

BOTS = [{"name": "klassik-ema", "port": 8085, "hausspur": "klassik_ema"},
        {"name": "trading-agent", "port": 8081}]
UEB = [{"name": "klassik-ema", "port": 8085, "erreichbar": True, "dry_run": True,
        "zustand": "running", "offen": 1, "trades": 12, "gewinn": -3.5, "fehler": ""},
       {"name": "trading-agent", "port": 8081, "erreichbar": False, "dry_run": None,
        "zustand": "?", "offen": None, "trades": None, "gewinn": None,
        "fehler": "Verbindung abgelehnt"}]


class Reinfunktionen(unittest.TestCase):
    def test_zeilen(self):
        z = lf.zeilen(UEB, BOTS, {"klassik-ema": {"runden": 40, "netto_prozent": -2.5,
                                                  "stand": "2026-10-10T20:00:00+00:00"}})
        self.assertEqual(z[0], ("klassik-ema", "klassik_ema", "läuft", "1", "12",
                                "-3.50", "-2.50 % / 40 R (10.10.)"))
        self.assertEqual(z[1][1], "MoonDev")

    def test_taube_bots_mit_grund(self):
        z = lf.zeilen(UEB, BOTS, {})
        self.assertEqual(z[1][2], "taub: Verbindung abgelehnt")
        self.assertEqual(lf.status_text(UEB), "FreqTrade: 1 taub (trading-agent)")
        self.assertEqual(lf.titel(UEB), " (1/2)")
        self.assertEqual(lf.titel([]), "")

    def test_urteile_fehlen_oder_kaputt(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(lf.lade_urteile(Path(d) / "fehlt.json"), {})
            kaputt = Path(d) / "kaputt.json"
            kaputt.write_text("{nicht json", encoding="utf-8")
            self.assertEqual(lf.lade_urteile(kaputt), {})
        self.assertEqual(lf.zeilen(UEB, BOTS, {})[0][6], "—")


class Reiter(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_refresh_blockiert_nicht(self):
        freigabe = threading.Event()

        def langsam(**_kw):
            freigabe.wait(5)
            return UEB
        r = lf.FreqtradeReiter(self.root, None, quelle=langsam,
                               bot_quelle=lambda: BOTS,
                               urteile_pfad=Path("gibtsnicht.json"))
        t0 = time.monotonic()
        r.refresh()
        self.assertLess(time.monotonic() - t0, 0.5)
        freigabe.set()
        ende = time.monotonic() + 5
        while time.monotonic() < ende and not r.tabelle.get_children():
            self.root.update()
            time.sleep(0.02)
        self.assertEqual(len(r.tabelle.get_children()), 2)
        self.assertEqual(r.titel_zusatz(), " (1/2)")

    def test_im_leitstand_eingetragen(self):
        titel = [t for t, _k in lst.REITER]
        self.assertIn("FreqTrade", titel)
        self.assertIn("FreqTrade", lst.TAKT_SICHTBAR)
        self.assertIn("<Control-Key-8>", lst.KUERZEL)

    def test_schreibt_und_startet_nichts(self):
        quelle = Path(lf.__file__).read_text(encoding="utf-8")
        for verboten in ("forceenter", "forceexit", "subprocess", "bots.py start",
                         ".write_text(", "open(", "docker"):
            self.assertNotIn(verboten, quelle, verboten)


if __name__ == "__main__":
    unittest.main()
```

Hinweis: `open(` ist verboten, damit Lesen nur über `Path.read_text` läuft — `lade_urteile` nutzt `read_text`.

- [ ] **Step 2: Laufen lassen, muss scheitern** — Run: `cd Agenten/Handel && $PY tests/test_leitstand_freqtrade.py` — Expected: `ModuleNotFoundError: leitstand_freqtrade`.

- [ ] **Step 3: `leitstand_freqtrade.py`**

```python
"""FreqTrade-Reiter des Leitstands: alle Bots aus freqtrade/bots.json auf einen Blick.

Auftrag Max 10.10.2026 (Spec Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md):
die Haus-Spur-Bots sollen im Leitstand sichtbar sein - mit ihrem Backtest-Urteil
daneben, damit Breite nicht mit Kante verwechselt wird.

Nur lesend: alles geht ueber freqtrade_bridge (nur GET). Die Abfrage laeuft in
einem Hintergrund-Thread; 20 Bots x 4 s Zeitgrenze duerfen den Rahmen nicht
einfrieren. Tk wird nur im Hauptthread angefasst (after-Schleife).
"""

import json
import threading
from pathlib import Path
from tkinter import ttk

import freqtrade_bridge as fb
import handelszentrale as hz
import leitstand_stil as stil

URTEILE = Path(__file__).resolve().parent / "freqtrade" / "urteile.json"
SPALTEN = (("bot", "Bot", 170), ("spur", "Spur", 150), ("zustand", "Zustand", 190),
           ("offen", "offen", 50), ("runden", "Runden", 60),
           ("gv", "G/V geschl.", 90), ("bt", "Backtest 2 J.", 170))
OFFEN_SPALTEN = ("Paar", "Seite", "seit", "Einstieg", "aktuell", "Einsatz", "G/V %")
ZU_SPALTEN = ("Paar", "auf", "zu", "G/V %", "G/V", "Grund", "")
ABHOLEN_MS = 150


def lade_urteile(pfad: Path = URTEILE) -> dict:
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def _backtest_text(u):
    if not u:
        return "—"
    stand = str(u.get("stand", ""))
    datum = "%s.%s." % (stand[8:10], stand[5:7]) if len(stand) >= 10 else "?"
    return "%+.2f %% / %d R (%s)" % (float(u.get("netto_prozent", 0.0)),
                                     int(u.get("runden", 0)), datum)


def zeilen(uebersicht, bot_liste, urteile):
    spur_je_bot = {b["name"]: (b.get("hausspur") or "MoonDev") for b in bot_liste}
    aus = []
    for z in uebersicht:
        if z.get("erreichbar"):
            zustand = "läuft" if z.get("zustand") == "running" else str(z.get("zustand"))
            if z.get("dry_run") is False:
                zustand = "LIVE! " + zustand
        else:
            zustand = "taub: %s" % (z.get("fehler") or "?")
        gv = z.get("gewinn")
        aus.append((z["name"], spur_je_bot.get(z["name"], "?"), zustand,
                    "" if z.get("offen") is None else str(z["offen"]),
                    "" if z.get("trades") is None else str(z["trades"]),
                    "" if gv is None else "%+.2f" % float(gv),
                    _backtest_text(urteile.get(z["name"]))))
    return aus


def titel(uebersicht):
    if not uebersicht:
        return ""
    return " (%d/%d)" % (sum(1 for z in uebersicht if z.get("erreichbar")), len(uebersicht))


def status_text(uebersicht):
    taub = [z["name"] for z in uebersicht if not z.get("erreichbar")]
    if not taub:
        return ""
    return "FreqTrade: %d taub (%s)" % (len(taub), ", ".join(taub))


class FreqtradeReiter(ttk.Frame):
    def __init__(self, eltern, leitstand, quelle=None, bot_quelle=None, urteile_pfad=None):
        super().__init__(eltern, padding=stil.ABSTAND_GROSS)
        self.ls = leitstand
        self.quelle = quelle or fb.uebersicht
        self.bot_quelle = bot_quelle or fb.bots
        self.urteile_pfad = urteile_pfad or URTEILE
        self._uebersicht = []
        self._bots = []
        self._ergebnis = None
        self._detail = None
        self._laeuft = False

        self.kopf = ttk.Label(self, text="FreqTrade: wird abgefragt …", anchor="w")
        self.kopf.pack(fill="x")
        self.tabelle = ttk.Treeview(self, columns=[s[0] for s in SPALTEN],
                                    show="headings", height=12, selectmode="browse")
        for schluessel, text, breite in SPALTEN:
            self.tabelle.heading(schluessel, text=text)
            self.tabelle.column(schluessel, width=breite, anchor="w")
        self.tabelle.pack(fill="both", expand=True, pady=(6, 6))
        self.tabelle.bind("<<TreeviewSelect>>", self._gewaehlt)
        self.offen = self._liste(OFFEN_SPALTEN, 5)
        self.zu = self._liste(ZU_SPALTEN, 8)

    def _liste(self, spalten, hoehe):
        t = ttk.Treeview(self, columns=list(range(len(spalten))), show="headings",
                         height=hoehe)
        for i, text in enumerate(spalten):
            t.heading(i, text=text)
            t.column(i, width=95, anchor="w")
        t.pack(fill="both", expand=True, pady=(0, 6))
        return t

    # --- Hintergrund ----------------------------------------------------
    def _im_hintergrund(self, arbeit, fertig):
        def lauf():
            try:
                self._ergebnis = (fertig, arbeit(), None)
            except Exception as e:                             # noqa: BLE001
                self._ergebnis = (fertig, None, e)
        threading.Thread(target=lauf, daemon=True).start()
        self.after(ABHOLEN_MS, self._abholen)

    def _abholen(self):
        if self._ergebnis is None:
            self.after(ABHOLEN_MS, self._abholen)
            return
        fertig, wert, fehler = self._ergebnis
        self._ergebnis = None
        fertig(wert, fehler)

    # --- Reiter-Schnittstelle --------------------------------------------
    def refresh(self):
        if self._laeuft:
            return
        self._laeuft = True

        def arbeit():
            bots = self.bot_quelle()
            return bots, self.quelle(zeitgrenze=4, bot_liste=bots)
        self._im_hintergrund(arbeit, self._uebersicht_da)

    def _uebersicht_da(self, wert, fehler):
        self._laeuft = False
        if fehler is not None:
            self.kopf.configure(text="⚠ FreqTrade-Abfrage gescheitert: %s" % fehler)
            return
        self._bots, self._uebersicht = wert
        gewaehlt = self.tabelle.selection()
        self.tabelle.delete(*self.tabelle.get_children())
        for z in zeilen(self._uebersicht, self._bots, lade_urteile(self.urteile_pfad)):
            self.tabelle.insert("", "end", iid=z[0], values=z)
        if gewaehlt and self.tabelle.exists(gewaehlt[0]):
            self.tabelle.selection_set(gewaehlt[0])
        self.kopf.configure(text="FreqTrade: %d Bots%s  %s" % (
            len(self._uebersicht), titel(self._uebersicht), status_text(self._uebersicht)))

    def _gewaehlt(self, _ereignis=None):
        sel = self.tabelle.selection()
        bot = next((b for b in self._bots if sel and b["name"] == sel[0]), None)
        if bot is None or self._detail == "läuft":
            return
        self._detail = "läuft"

        def arbeit():
            zugang = fb.zugang_fuer(bot["port"])
            return fb.offene_trades(zugang), fb.trades(50, zugang)
        self._im_hintergrund(arbeit, self._detail_da)

    def _detail_da(self, wert, fehler):
        self._detail = None
        self.offen.delete(*self.offen.get_children())
        self.zu.delete(*self.zu.get_children())
        if fehler is not None or wert is None:
            return
        offen, zu = wert
        for t in (offen if isinstance(offen, list) else []):
            self.offen.insert("", "end", values=hz.freqtrade_offen_zeile(t))
        for z in hz.freqtrade_zu_zeilen(zu, 20):
            self.zu.insert("", "end", values=z)

    def titel_zusatz(self):
        return titel(self._uebersicht)

    def status(self):
        return status_text(self._uebersicht)
```

Prüfen, dass `ZU_SPALTEN` zur Länge von `hz.freqtrade_zu_zeilen` passt: das Tupel hat 7 Werte (Paar, auf, zu, G/V %, G/V abs, Grund — zählen in `handelszentrale.py` ab Zeile 970). Hat es 6, den leeren letzten Spaltentitel streichen.

- [ ] **Step 4: `leitstand.py` per Edit**

- Import nach `from leitstand_freigaben import FreigabenReiter`: `from leitstand_freqtrade import FreqtradeReiter`
- In `KUERZEL` nach `"<Control-Key-7>": ("reiter", 6),`: `"<Control-Key-8>": ("reiter", 7),`
- `TAKT_SICHTBAR = {"Markt", "Omniquant", "Nautilus", "Prozesse", "FreqTrade"}`
- In `REITER` nach `("Prozesse", ProzessReiter)` (Komma ergänzen): `("FreqTrade", FreqtradeReiter)`
- Docstring: `Strg+1..7` → `Strg+1..8`

Prüfen, ob `TAKT_SICHTBAR` über den Titel mit Zusatz (`"FreqTrade (1/2)"`) oder den Grundtitel abgleicht: `grep -n "TAKT_SICHTBAR\|TAKT_IMMER" Agenten/Handel/leitstand.py`. Gleicht er den angezeigten Titel ab, muss der Abgleich den Grundtitel nehmen — wie bei „Freigaben (n)“ in `TAKT_IMMER` bereits gelöst; dieselbe Stelle benutzen, nichts Neues bauen.

- [ ] **Step 5: Tests** — Run: `tests/test_leitstand_freqtrade.py`, danach die ganze Leitstand-Familie:

```bash
cd Agenten/Handel && for t in tests/test_leitstand*.py tests/test_handelszentrale_freqtrade.py tests/test_freqtrade_bridge.py; do $PY $t || echo "ROT: $t"; done
```

Expected: kein „ROT“. Schlägt ein Bestandstest wegen der neuen Reiterzahl fehl (z. B. ein Kürzel-Zähler), den Test nur dort anpassen, wo er die Zahl 7 fest annimmt — mit Verweis auf diesen Plan im Kommentar.

- [ ] **Step 6: Sichtprobe** — `cd Agenten/Handel && $PY leitstand.py`, Strg+8: Tabelle mit den drei laufenden Moon-Dev-Bots (die 17 neuen erscheinen als „taub: …“, solange sie nicht gestartet sind — gewollt). Zeile anklicken → offene/geschlossene Trades. Fenster schließen.

- [ ] **Step 7: Commit**

```bash
git add Agenten/Handel/leitstand_freqtrade.py Agenten/Handel/leitstand.py Agenten/Handel/tests/test_leitstand_freqtrade.py && git commit -m "Leitstand: Reiter FreqTrade (alle Bots, Backtest-Urteil, nur lesend, Strg+8)"
```

---

### Task 7: Wissen nachziehen, PR vorbereiten

**Files:**
- Modify: `MaxHirn/Wissen/Handelsbots.md` (neuer Abschnitt „Haus-Spuren als Freqtrade-Bots“) — Bereich `wissen`: als BEFUND melden (`bereiche.py --aufrufer handel --pfad MaxHirn/Wissen/Handelsbots.md`), nicht blockiert.
- Modify: `Agenten/Handel/README.md` (Zeile zu `hausspur_regeln.py`, `HausSpur`, Reiter FreqTrade)

- [ ] **Step 1: Abschnitt schreiben** (gezielter Edit, ≤ 25 Zeilen): Zweck, Schnittstelle `hausspur_regeln.signale`, Mount `/agenten:ro`, Port-Tabelle-Verweis auf `bots.json`, wie man einen Bot ergänzt (Spur in `ALLE` + Eintrag in `bots.json`, Test `Manifest` prüft Konsistenz), Hinweis „Backtest-Urteil steht im Reiter daneben; Breite ≠ Kante“, Datum 10.10.2026.

- [ ] **Step 2: Gesamtlauf aller neuen und berührten Tests** (Befehle aus Tasks 1–6). Expected: PASS.

- [ ] **Step 3: Commit; PR erst nach Max' Anweisung** (Regel „Nicht pushen“). Beschreibung vorbereiten in `Werkstatt/pr-freqtrade-hausspuren-2026-10-10.md` mit Testausgaben und Probe-Backtest aus Task 5 Step 2, endet mit `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
git add MaxHirn/Wissen/Handelsbots.md Agenten/Handel/README.md && git commit -m "Wissen: Haus-Spuren als Freqtrade-Bots (hausspur_regeln, HausSpur, Reiter)"
```

---

### Task 8: Start der 17 Bots — NUR nach Freigabe durch Max

**Files:** keine

- [ ] **Step 1: Freigabe einholen** — Max fragen: „17 Container × ~600 MB ≈ 10 GB RAM, Ports 8084–8100, dry_run. Starten?“ Ohne ausdrückliches Ja: Task endet hier.

- [ ] **Step 2: Start (Hauptbaum, nach Merge)**

```bash
cd Agenten/Handel/freqtrade && $PY bots.py start klassik-sma klassik-ema klassik-macd klassik-bollinger klassik-donchian klassik-rsi klassik-rsi2 klassik-donchian-trend klassik-sr-breaks klassik-pmax klassik-supertrend macd-mtf squeeze wavetrend supertrend trendwende-btc orb && $PY bots.py status
```

Expected: 17 × „✓ gestartet“, `status` zeigt alle mit Antwort. Taube Bots: `docker logs freqtrade-<name> --tail 40` lesen (häufig: fehlende Futures-Daten, Mount) und melden.

- [ ] **Step 3: Leitstand Strg+8** — 20 Zeilen, 20/20 erreichbar.

---

### Task 9: Gleichheitsrahmen für Phase 2 (Ansatz B)

**Files:**
- Create: `Agenten/Handel/freqtrade/gleichheit.py`
- Test: `Agenten/Handel/freqtrade/tests/test_gleichheit.py`

**Interfaces:**
- Consumes: `hausspur_regeln.signale` (Referenz A).
- Produces: `gleichheit.vergleiche(kerzen: list, name: str, b_einstieg: list[str|None], ab: int = 0) -> list[tuple[int, str|None, str|None]]` — Liste der Abweichungen `(index, a, b)`; leer = gleich. Jede künftige B-Strategie liefert ihre Einstiegsspalte als Liste und muss hier leer zurückgeben, bevor `bots.json` umgestellt wird.

- [ ] **Step 1: Failing test**

```python
"""Gleichheitsrahmen: B-Strategie gegen Adapter A, Kerze fuer Kerze."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))

import gleichheit                                              # noqa: E402
import hausspur_regeln as hr                                   # noqa: E402
from test_hausspur_regeln import reihe                         # noqa: E402


class Gleichheit(unittest.TestCase):
    def test_a_gegen_sich_selbst_ist_gleich(self):
        k = reihe()
        a = [x["einstieg"] if x else None for x in hr.signale(k, "klassik_ema")]
        self.assertEqual(gleichheit.vergleiche(k, "klassik_ema", a), [])

    def test_abweichung_wird_gemeldet(self):
        k = reihe()
        a = [x["einstieg"] if x else None for x in hr.signale(k, "klassik_ema")]
        b = list(a)
        b[-1] = "short" if a[-1] != "short" else None
        self.assertEqual(gleichheit.vergleiche(k, "klassik_ema", b),
                         [(len(k) - 1, a[-1], b[-1])])

    def test_laenge_muss_passen(self):
        with self.assertRaises(ValueError):
            gleichheit.vergleiche(reihe(), "klassik_ema", [None])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Laufen lassen, muss scheitern** — Expected: `ModuleNotFoundError: gleichheit`.

- [ ] **Step 3: Implementierung**

```python
"""Gleichheitsrahmen fuer Phase 2 (Ansatz B, Spec 10.10.2026).

Eine vektorisierte Strategie darf eine Spur erst dann in bots.json ersetzen,
wenn sie auf derselben Kerzenreihe JEDE Kerze gleich entscheidet wie der
Adapter (hausspur_regeln.signale). Der Adapter ist die Referenz, weil er die
Haus-Regel importiert statt sie nachzubauen.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hausspur_regeln as hr                                   # noqa: E402


def vergleiche(kerzen, name, b_einstieg, ab=0):
    if len(b_einstieg) != len(kerzen):
        raise ValueError("B liefert %d Werte fuer %d Kerzen" % (len(b_einstieg), len(kerzen)))
    a = hr.signale(kerzen, name, ab=ab)
    return [(i, (a[i] or {}).get("einstieg"), b_einstieg[i])
            for i in range(ab, len(kerzen))
            if (a[i] or {}).get("einstieg") != b_einstieg[i]]
```

- [ ] **Step 4: Tests** — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/freqtrade/gleichheit.py Agenten/Handel/freqtrade/tests/test_gleichheit.py && git commit -m "freqtrade: Gleichheitsrahmen A gegen B fuer vektorisierte Haus-Spuren"
```

Danach: je B-Strategie (zuerst `macd_mtf`, dann `squeeze`) ein eigener Kurzplan in `Werkstatt/plan-freqtrade-b-<spur>-<datum>.md`, der die Indikatorrechnung aus `ti_indikatoren.py` vektorisiert und mit `gleichheit.vergleiche` auf 2 Jahren echter Kerzen (`user_data/data/binance/futures`) leer abschließt.
