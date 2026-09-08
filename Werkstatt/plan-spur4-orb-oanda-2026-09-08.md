# Spur 4 — ORB Index-CFD (OANDA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine vierte bewachte Handelsspur bauen — Opening-Range-Breakout auf Index-CFDs über OANDA v20 —, deren Backtest die „81 %"-Behauptung prüft und deren Papierpfad parallel läuft, Live-Schalter aus, bis Backtest **und** 6 Wochen Papier bestehen.

**Architecture:** Ein neuer Ordner `Agenten/Handel/orb/` nach dem Muster von `Agenten/Handel/kraken/` (Spur 3): eine `wachen.json` als einzige Wahrheit, ein API-Modul (`oanda.py`, nur stdlib), ein Zeit-/Session-Modul (`session.py`), ein Backtest (`backtest.py`), der Handelszyklus (`handeln.py` mit `--vorschau|--papier|--live|--wachen`) und die Spur-Bedingungen (`wachen_orb.py`), die die währungsneutrale Rechnung aus `../scanner/wachen_pruefung.py` importieren statt sie abzuschreiben. Ausstiege laufen nie durch das Freigabefenster; Einstiege schon.

**Tech Stack:** Python 3.13, **nur Standardbibliothek** (`urllib`, `json`, `csv`, `zoneinfo`, `datetime`, `hmac` nicht nötig — OANDA nutzt einen Bearer-Token). Tests mit stdlib `unittest`. PowerShell-Wrapper für die Windows-Aufgabenplanung. Kein eigenes `.venv` (wie `kraken.py`).

**Spec:** `Agenten/Handel/orb/SPEC.md` (committet `a2356a3`). Der Plan argumentiert aus dieser Spec; Executor lesen beide.

## Global Constraints

- **Nur Standardbibliothek** im gesamten `orb/`-Ordner. Kein `pip install`, kein eigenes `.venv`. Begründung: OANDA ist REST+JSON, die Backtest-Mathematik ist stdlib (SPEC.md §61).
- **Interpreter für Skript und Tests:** `..\scanner\.venv\Scripts\python.exe` (Python 3.13.15). Dieser existiert bereits und wird von allen Handelsroutinen benutzt. `unittest` ist stdlib — es wird nichts nachinstalliert.
- **`wachen.json` wird gelesen, nie geschrieben** — einzige Ausnahme `wachen_orb.sperre_zu()`, und die legt `handel_erlaubt` **nur** von `true` auf `false` (Schutzregel, SPEC.md §125).
- **Nie auf `complete:false`-Kerzen handeln** — eine laufende M15 ist kein Signal (SPEC.md §156).
- **DST:** Eröffnungszeit je Handelstag in Börsen-Lokalzeit über `zoneinfo` rechnen, nie in fester UTC (SPEC.md §157).
- **Rundung Orders:** `units` ganzzahlig, Vorzeichen = Richtung; Preis-Präzision und `minimumTradeSize` aus den Instrumentdetails; **immer abrunden** (SPEC.md §162).
- **Slippage:** den echten `fillTransaction`-Preis ins Journal, nicht den Wunschpreis (SPEC.md §164).
- **Spread im Journal-Betrag:** Einstieg mit Aufschlag, Ausstieg nach Abzug (SPEC.md §165).
- **Mehrdeutige Kerze** (M15 berührt Stop und TP zugleich) → als **Stop** gezählt (konservativ, SPEC.md §37).
- **Positionsgröße = `risiko_pro_trade_eur / stop_abstand`**, `stop_abstand` = Range-Höhe. Der Hebel fällt aus der Rechnung, wird nur durch `hebel_deckel` gedeckelt — nie als Eingabe (XPERP-Regel, SPEC.md §34).
- **Backtest-Urteil-Schwelle:** Erwartungswert nach Spread **im ganzen Fenster UND im schlechtesten Quartal** positiv, **≥ 10 Verlierer** im Sample (SPEC.md §95). Fällt das aus, bekommt die Spur keine Papierphase — der Plan endet dann bei Task 8 mit einem `Nein`-Urteil in `ORB-Handel.md`.
- **Rechnet in EUR.** Jedes Betragsfeld in `wachen.json` trägt `_eur`; `freigabe.py` zeigt EUR. Muster Spur 3 (SPEC.md §134).
- **Änderungen an `.md`-Dateien in `MaxHirn/Wissen/` nie per Python-Rewrite** — nur mit dem Edit-Werkzeug. Ein Python-Rewrite stellt CRLF auf LF um (Memory `crlf-im-vault`).
- **Commits:** nach jedem Task ein Commit. `git add <pfad>` namentlich, nie `git add -A`. Commit-Nachricht endet mit `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` — außer die Änderung ist ausschließlich in `orb/*` (Handel-Ordner-Konvention: kurze deutsche Betreffzeile, kein Trailer nötig, aber schadet nicht).
- **`MAXHIRN_ROUTINE=1`** setzt jeder Aufgabenplanungs-Wrapper — die ausdrückliche Ansage „hier sitzt niemand am Bildschirm" (kein Freigabefenster, kein scharfer Handel aus dem Zeitplan).

---

## Dateistruktur

Alles Neue unter `Agenten/Handel/orb/`, plus punktuelle Änderungen außerhalb.

| Datei | Verantwortung | Muster |
|---|---|---|
| `orb/wachen.json` | Harte Grenzen, EUR. Einzige Wahrheit. | `kraken/wachen.json` |
| `orb/oanda.py` | OANDA v20 v3: M15-Kerzen (paginiert, Cache), Preise, Instrumentdetails, signierte Orders. `urllib`, ein `Bearer`-Header. Host aus Env/Konfig. `winreg` für `OANDA_TOKEN`/`OANDA_KONTO_ID`. | `kraken/kraken.py` |
| `orb/session.py` | Eröffnungszeit + DST + Opening-Range-Fenster + Zwangsschluss + letzter Einstieg, je Instrument. Reine Funktionen, kein Netz. | neu |
| `orb/backtest.py` | Regel-Engine je Session, Aggregation, Bericht mit Urteil. `--raster` über TP-Modi. | `kraken/scan.py` lose |
| `orb/wachen_orb.py` | Bedingungen dieser Spur; importiert `../scanner/wachen_pruefung.py`. Range-Filter. `sperre_zu` schreibt `orb/wachen.json`. | `kraken/wachen_kraken.py` |
| `orb/handeln.py` | Zyklus: Ausstiege zuerst, dann höchstens ein Einstieg, Journal, Zustand. `--vorschau\|--papier\|--live\|--wachen`. Neun Live-Sperren. | `kraken/handeln.py` |
| `orb/handelsjournal.csv` | jede Aktion, Spread in den Beträgen. Nicht versioniert. | `kraken/handelsjournal.csv` |
| `orb/zustand.json` | offener Bestand, letzter Stop, letzter Lauf (Herzschlag). Nicht versioniert. | `kraken/zustand.json` |
| `orb/daten/*.json` | M15-Kerzen-Cache für den Backtest. Nicht versioniert. | neu |
| `orb/README.md` | tritt nach dem Bau an die Stelle von `SPEC.md`. | `kraken/README.md` |
| `orb/tests/test_*.py` | `unittest.TestCase`-Klassen, netzfrei (HTTP-Seam gemockt). | `verbesserer/tests/` lose |
| `orb/tests/fixtures/*.json` | aufgezeichnete OANDA-Antworten + synthetische Kerzenreihen. | neu |

Änderungen außerhalb (SPEC.md §183):

| Datei | Änderung |
|---|---|
| `.gitignore` | **schon vorhanden** — Zeilen 75–77 (Whitelist `orb/*.py\|*.md\|*.json`) und 145–147 (Blacklist `orb/zustand.json`, `orb/handelsjournal.csv`, `orb/daten/**`). Task 0 verifiziert nur, ergänzt `orb/tests/*.py` + `orb/tests/fixtures/*.json`. |
| `Agenten/Handel/freigabe.py` | Spur `orb` in `WACHEN`, `TITEL`, `BETRAGSFELD`, `RECHNER`, `BEISPIEL`. Nicht `SPOTARTIG` (gehebelt, gerichtet — wie `hebel`). |
| `Agenten/Routinen/orb-papier.ps1` | neu: alle 15 Min im Session-Fenster über die Windows-Aufgabenplanung, `MAXHIRN_ROUTINE=1`, ruft `handeln.py --papier`. |
| `Agenten/Routinen/handel-wachen.ps1` | um einen `orb`-`--wachen`-Lauf erweitern. |
| `MaxHirn/Wissen/ORB-Handel.md` | neue Notiz nach Muster `XPERP-Handel.md`. |
| `MaxHirn/Wissen/Handelsregeln.md` | Spur 4 in Tabelle + Sperrenliste + `related` (Edit). |
| `MaxHirn/Wissen/Routinen.md` | die neue Routine (Edit). |
| `MaxHirn/Wissen/INDEX.md` | Verweis auf `ORB-Handel.md` in der Registry (Edit). |
| `Agenten/Handel/README.md` | Absatz „Spur 4 — ORB Index" mit Aufrufen (Edit). |

**Test-Konvention:** stdlib `unittest`. Lauf aus `orb/`:
`..\scanner\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Einzeln: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_session.TestEroeffnung -v`

**HTTP-Seam:** `oanda.py` schickt jede Anfrage durch **eine** private Funktion
`_roh_json(url, *, method="GET", body=None)`. Tests ersetzen sie
(`oanda._roh_json = fake`). Kein Test geht ins Netz. Die einzigen Netz-Schritte
im ganzen Plan sind ausdrücklich als „(Netz nötig)" markiert und stehen in
eigenen Steps, die ein Mensch mit echtem Practice-Konto ausführt.

---

## Task 0: Ordnergerüst, `wachen.json`, `.gitignore` prüfen

**Files:**
- Create: `Agenten/Handel/orb/wachen.json`
- Create: `Agenten/Handel/orb/tests/__init__.py` (leer)
- Create: `Agenten/Handel/orb/tests/test_wachen_json.py`
- Modify: `.gitignore` (zwei Zeilen ergänzen)

**Interfaces:**
- Produces: `orb/wachen.json` mit allen Feldern aus SPEC.md §132. Alle späteren Tasks lesen daraus. Startwerte: `handel_erlaubt=false`, `instrument_aktiv=null`, `ziel_modus="r_vielfaches"`, `ziel_k=1.5`, `journal_zweitziel=null`, `freigabe.erfuellt=false`.

- [ ] **Step 1: `orb/wachen.json` schreiben**

```json
{
  "_zweck": "Harte Grenzen der vierten Spur (ORB Index-CFD, OANDA, EUR). Eine Datei, eine Wahrheit. Gelesen von backtest.py und handeln.py, nie von ihnen geschrieben - einzige Ausnahme ist wachen_orb.sperre_zu, das handel_erlaubt nur von true auf false legt.",
  "_waehrung": "Das OANDA-Konto rechnet in EUR. Alle Betragsfelder tragen _eur. Fuer die waehrungsneutrale Rechnung traegt jeder Index ein _usd-Aequivalent, Muster Spur 3.",
  "waehrung": "EUR",

  "handel_erlaubt": false,
  "_handel_erlaubt_hinweis": "false = nur Papierhandel, egal welcher Schalter. Auf true erst, wenn die vier Werte in freigabe erfuellt sind, mindest_marge_frei_eur frei ist und journal_zweitziel gesetzt ist. wachen_orb.sperre_zu kippt nur true->false.",

  "instrument_aktiv": null,
  "_instrument_aktiv": "Welcher Index die Papierphase faehrt. null bis der Backtest (Task 8) ein Urteil hat. Danach 'DE30_EUR' oder 'US30_USD' oder 'NAS100_USD'.",

  "instrumente": {
    "DE30_EUR":  {"oanda": "DE30_EUR",  "eroeffnung": "09:00", "zone": "Europe/Berlin", "cash_close": "17:30", "spread_punkte": 1.2, "punkt_wert_eur": 1.0},
    "US30_USD":  {"oanda": "US30_USD",  "eroeffnung": "15:30", "zone": "Europe/Berlin", "cash_close": "22:00", "spread_punkte": 1.6, "punkt_wert_eur": 0.92},
    "NAS100_USD":{"oanda": "NAS100_USD","eroeffnung": "15:30", "zone": "Europe/Berlin", "cash_close": "22:00", "spread_punkte": 1.0, "punkt_wert_eur": 0.92}
  },
  "_instrumente": "eroeffnung/cash_close in Boersen-Lokalzeit (zone). spread_punkte und punkt_wert_eur sind Startannahmen (SPEC.md), im ersten Umsetzungsschritt an echten pricing-Daten geeicht. punkt_wert_eur = Wert einer Indexpunkt-Bewegung je 1 unit, in EUR.",

  "risiko_pro_trade_eur": 20,
  "_risiko_pro_trade_eur": "Risikobetrag je Trade. Positionsgroesse = risiko_pro_trade_eur / (range_hoehe_punkte * punkt_wert_eur).",

  "ziel_modus": "r_vielfaches",
  "ziel_k": 1.5,
  "ziel_punkte": {"DE30_EUR": 40, "US30_USD": 60, "NAS100_USD": 50},
  "_ziel": "ziel_modus=r_vielfaches -> TP = ziel_k * Range-Hoehe. ziel_modus=punkte -> TP = ziel_punkte[instrument] Indexpunkte. Startwerte aus dem Backtest (Task 8).",

  "hebel_deckel": 20,
  "_hebel_deckel": "Obergrenze. Die aus der Positionsrechnung fallende Hebelzahl wird nur gedeckelt, nie gesetzt.",

  "letzter_einstieg_min_vor_schluss": 90,
  "mindest_range_punkte": {"DE30_EUR": 15, "US30_USD": 25, "NAS100_USD": 20},
  "max_range_punkte":     {"DE30_EUR": 120,"US30_USD": 220,"NAS100_USD": 200},
  "_range_filter": "Range unter mindest -> Session aussetzen (Rauschen, Spread frisst TP). Range ueber max -> aussetzen (Stop zu weit, Positionsgroesse unbrauchbar).",

  "mindest_marge_frei_eur": 200,
  "kill_switch_gesamt_eur": 150,
  "drawdown_halbierung_prozent": 15.0,
  "herzschlag_max_minuten": 45,
  "_herzschlag": "Die Papierroutine laeuft alle 15 Min im Session-Fenster. 45 Min faengt einen ausgefallenen Lauf, ein normaler loest nie aus.",

  "journal_zweitziel": null,
  "_journal_zweitziel": "Bedingung 4. Pfad fuer die Journal-Spiegelung nach jedem Zyklus. Nicht G: (gleiches Gehaeuse). null -> Live gesperrt.",

  "freigabe": {
    "erfuellt": false,
    "backtest_bestanden": false,
    "papierlauf_min_wochen": 6,
    "papierlauf_min_sessions": 50,
    "netto_positiv": false,
    "groesster_ruecklauf_papierlauf_eur": null,
    "geprueft_am": null
  },
  "_freigabe": "Sperre 4 aus SPEC.md. handel_erlaubt darf erst true, wenn backtest_bestanden UND (>= papierlauf_min_wochen Papier) UND (>= papierlauf_min_sessions gehandelte Sessions) UND netto_positiv. erfuellt ist der von Hand gesetzte Haken, nachdem alle vier stimmen.",

  "oanda_host_papier": "https://api-fxpractice.oanda.com",
  "oanda_host_live": "https://api-fxtrade.oanda.com"
}
```

- [ ] **Step 2: `orb/tests/__init__.py` anlegen** (leere Datei)

- [ ] **Step 3: Failing test schreiben** — `orb/tests/test_wachen_json.py`

```python
import json
import unittest
from pathlib import Path

WACHEN = Path(__file__).resolve().parent.parent / "wachen.json"


class TestWachenJson(unittest.TestCase):
    def setUp(self):
        self.w = json.loads(WACHEN.read_text(encoding="utf-8"))

    def test_start_gesperrt(self):
        self.assertIs(self.w["handel_erlaubt"], False)
        self.assertIsNone(self.w["instrument_aktiv"])
        self.assertIs(self.w["freigabe"]["erfuellt"], False)
        self.assertIsNone(self.w["journal_zweitziel"])

    def test_pflichtfelder_da(self):
        for schluessel in ("risiko_pro_trade_eur", "ziel_modus", "hebel_deckel",
                           "letzter_einstieg_min_vor_schluss", "mindest_marge_frei_eur",
                           "kill_switch_gesamt_eur", "herzschlag_max_minuten",
                           "oanda_host_papier", "oanda_host_live"):
            self.assertIn(schluessel, self.w)

    def test_drei_instrumente_vollstaendig(self):
        for inst in ("DE30_EUR", "US30_USD", "NAS100_USD"):
            e = self.w["instrumente"][inst]
            for f in ("oanda", "eroeffnung", "zone", "cash_close",
                      "spread_punkte", "punkt_wert_eur"):
                self.assertIn(f, e)
            self.assertIn(inst, self.w["mindest_range_punkte"])
            self.assertIn(inst, self.w["max_range_punkte"])

    def test_ziel_modus_gueltig(self):
        self.assertIn(self.w["ziel_modus"], ("punkte", "r_vielfaches"))
```

- [ ] **Step 4: Test läuft und schlägt fehl** (falls `wachen.json` fehlt oder unvollständig)

Run (aus `Agenten/Handel/orb/`): `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_wachen_json -v`
Expected: FAIL bzw. Error (Datei fehlt) — oder nach Step 1 direkt PASS.

- [ ] **Step 5: `.gitignore` prüfen und Test-Zeilen ergänzen**

Prüfen, dass Zeilen 75–77 und 145–147 unverändert da sind (`orb/*.py|*.md|*.json` freigegeben; `orb/zustand.json`, `orb/handelsjournal.csv`, `orb/daten/**` gesperrt). Direkt **nach** der bestehenden Zeile `!Agenten/Handel/orb/*.json` einfügen:

```
!Agenten/Handel/orb/tests/*.py
!Agenten/Handel/orb/tests/fixtures/*.json
```

- [ ] **Step 6: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_wachen_json -v`
Expected: PASS (4 Tests).

- [ ] **Step 7: `git status` prüfen — nur die neuen orb-Dateien und `.gitignore`**

Run (aus Repo-Wurzel): `git status --porcelain`
Expected: `?? Agenten/Handel/orb/wachen.json`, `?? Agenten/Handel/orb/tests/`, ` M .gitignore` — nichts sonst.

- [ ] **Step 8: Commit**

```bash
git add Agenten/Handel/orb/wachen.json Agenten/Handel/orb/tests/__init__.py Agenten/Handel/orb/tests/test_wachen_json.py .gitignore
git commit -m "Spur 4 (ORB): wachen.json-Geruest und Test-Whitelist"
```

---

## Task 1: `session.py` — Eröffnung, DST, Opening-Range-Fenster, Zwangsschluss

**Files:**
- Create: `Agenten/Handel/orb/session.py`
- Create: `Agenten/Handel/orb/tests/test_session.py`

**Interfaces:**
- Consumes: `orb/wachen.json` → `instrumente[inst]` mit `eroeffnung`, `zone`, `cash_close`.
- Produces:
  - `eroeffnung(inst_konf: dict, tag: datetime.date) -> datetime` — tz-aware, in UTC zurückgegeben
  - `zwangsschluss(inst_konf: dict, tag: date) -> datetime` — tz-aware UTC
  - `opening_range_fenster(inst_konf, tag) -> tuple[datetime, datetime]` — (Start = Eröffnung, Ende = Eröffnung + 30 min), beide UTC
  - `letzter_einstieg(inst_konf, tag, min_vor_schluss: int) -> datetime` — UTC
  - `in_session(inst_konf, moment: datetime) -> bool` — moment tz-aware; True zwischen Eröffnung+30min und Zwangsschluss des zugehörigen Handelstags
  - `handelstag(moment: datetime, zone: str) -> date` — der Börsen-Lokaltag von `moment`

- [ ] **Step 1: Failing test schreiben** — `orb/tests/test_session.py`

```python
import unittest
from datetime import date, datetime, timezone

import session

DE30 = {"eroeffnung": "09:00", "zone": "Europe/Berlin", "cash_close": "17:30"}
US30 = {"eroeffnung": "15:30", "zone": "Europe/Berlin", "cash_close": "22:00"}


class TestEroeffnung(unittest.TestCase):
    def test_de30_sommer_ist_0700_utc(self):
        # 15. Juli: Europe/Berlin = UTC+2 -> 09:00 lokal = 07:00 UTC
        e = session.eroeffnung(DE30, date(2025, 7, 15))
        self.assertEqual(e, datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc))

    def test_de30_winter_ist_0800_utc(self):
        # 15. Januar: Europe/Berlin = UTC+1 -> 09:00 lokal = 08:00 UTC
        e = session.eroeffnung(DE30, date(2025, 1, 15))
        self.assertEqual(e, datetime(2025, 1, 15, 8, 0, tzinfo=timezone.utc))

    def test_us30_sommer_ist_1330_utc(self):
        e = session.eroeffnung(US30, date(2025, 7, 15))
        self.assertEqual(e, datetime(2025, 7, 15, 13, 30, tzinfo=timezone.utc))


class TestFenster(unittest.TestCase):
    def test_opening_range_ist_erste_30_min(self):
        start, ende = session.opening_range_fenster(DE30, date(2025, 7, 15))
        self.assertEqual(start, datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc))
        self.assertEqual(ende, datetime(2025, 7, 15, 7, 30, tzinfo=timezone.utc))

    def test_zwangsschluss_de30_sommer(self):
        z = session.zwangsschluss(DE30, date(2025, 7, 15))
        self.assertEqual(z, datetime(2025, 7, 15, 15, 30, tzinfo=timezone.utc))

    def test_letzter_einstieg_90_min_vor_schluss(self):
        le = session.letzter_einstieg(DE30, date(2025, 7, 15), 90)
        self.assertEqual(le, datetime(2025, 7, 15, 14, 0, tzinfo=timezone.utc))


class TestInSession(unittest.TestCase):
    def test_vor_range_ende_nicht_in_session(self):
        m = datetime(2025, 7, 15, 7, 15, tzinfo=timezone.utc)
        self.assertFalse(session.in_session(DE30, m))

    def test_nach_range_vor_schluss_in_session(self):
        m = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        self.assertTrue(session.in_session(DE30, m))

    def test_nach_zwangsschluss_nicht_in_session(self):
        m = datetime(2025, 7, 15, 16, 0, tzinfo=timezone.utc)
        self.assertFalse(session.in_session(DE30, m))
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_session -v`
Expected: FAIL mit `ModuleNotFoundError: No module named 'session'`

- [ ] **Step 3: `session.py` schreiben**

```python
"""Zeitrechnung der vierten Spur: Eroeffnung, DST, Opening-Range-Fenster,
Zwangsschluss, letzter Einstieg. Reine Funktionen, kein Netz.

Alle Rueckgaben sind tz-aware in UTC. Die Eroeffnung wird JE HANDELSTAG in der
Boersen-Lokalzeit gerechnet (SPEC.md: DST-fest ueber zoneinfo), dann nach UTC
gewandelt - eine feste UTC-Zeit waere im Winter eine Stunde daneben.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

RANGE_MINUTEN = 30  # die ersten zwei M15-Kerzen


def _lokal(inst_konf, tag, hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    zone = ZoneInfo(inst_konf["zone"])
    return datetime.combine(tag, time(h, m), tzinfo=zone)


def eroeffnung(inst_konf, tag):
    return _lokal(inst_konf, tag, inst_konf["eroeffnung"]).astimezone(timezone.utc)


def zwangsschluss(inst_konf, tag):
    return _lokal(inst_konf, tag, inst_konf["cash_close"]).astimezone(timezone.utc)


def opening_range_fenster(inst_konf, tag):
    start = eroeffnung(inst_konf, tag)
    return start, start + timedelta(minutes=RANGE_MINUTEN)


def letzter_einstieg(inst_konf, tag, min_vor_schluss):
    return zwangsschluss(inst_konf, tag) - timedelta(minutes=min_vor_schluss)


def handelstag(moment, zone):
    return moment.astimezone(ZoneInfo(zone)).date()


def in_session(inst_konf, moment):
    """True, wenn moment nach dem Opening-Range-Fenster und vor dem
    Zwangsschluss des zugehoerigen Boersen-Handelstags liegt."""
    tag = handelstag(moment, inst_konf["zone"])
    _, range_ende = opening_range_fenster(inst_konf, tag)
    return range_ende <= moment < zwangsschluss(inst_konf, tag)
```

- [ ] **Step 4: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_session -v`
Expected: PASS (9 Tests). Prüft Sommer/Winter (DST) für DE30 und US30.

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/orb/session.py Agenten/Handel/orb/tests/test_session.py
git commit -m "Spur 4 (ORB): session.py - Eroeffnung, DST, Range-Fenster, Zwangsschluss"
```

---

## Task 2: `oanda.py` — HTTP-Seam, Token/Konto aus Registry, 401-Unterscheidung

**Files:**
- Create: `Agenten/Handel/orb/oanda.py`
- Create: `Agenten/Handel/orb/tests/test_oanda_http.py`

**Interfaces:**
- Produces:
  - `_roh_json(url, *, method="GET", body=None) -> dict` — die **einzige** Netz-Funktion. Setzt `Authorization: Bearer <token>` und `Content-Type: application/json`. Bei `urllib.error.HTTPError` 401 → `OandaAuthFehler` mit unterscheidender Meldung.
  - `_variable(name) -> str | None` — `os.environ` dann `winreg HKCU\Environment` (wortgleich zu `kraken._variable`)
  - `token() -> str | None`, `konto_id() -> str | None`, `zugang_vorhanden() -> bool`
  - `host(live: bool) -> str` — aus `wachen.json` `oanda_host_live` / `oanda_host_papier`
  - `OandaFehler(RuntimeError)` — fachlicher Fehler, wird nicht wiederholt
  - `OandaAuthFehler(OandaFehler)` — 401
- Konsumiert von allen weiteren `oanda.*`-Funktionen (Task 3/4).

- [ ] **Step 1: Failing test schreiben** — `orb/tests/test_oanda_http.py`

```python
import json
import unittest
import urllib.error
import io

import oanda


def _http_error(code, body=b"{}"):
    return urllib.error.HTTPError("u", code, "err", {}, io.BytesIO(body))


class TestZugang(unittest.TestCase):
    def test_zugang_fehlt_ohne_variablen(self):
        alt_t, alt_k = oanda.token, oanda.konto_id
        oanda.token = lambda: None
        oanda.konto_id = lambda: None
        try:
            self.assertFalse(oanda.zugang_vorhanden())
        finally:
            oanda.token, oanda.konto_id = alt_t, alt_k

    def test_host_wechselt_mit_live(self):
        self.assertIn("fxpractice", oanda.host(live=False))
        self.assertIn("fxtrade", oanda.host(live=True))


class Test401(unittest.TestCase):
    def setUp(self):
        self._alt = oanda._oeffne
        oanda.token = lambda: "tok"
        oanda.konto_id = lambda: "kid"

    def tearDown(self):
        oanda._oeffne = self._alt

    def test_401_gegen_practice_meldet_token_abgelaufen(self):
        oanda._oeffne = lambda req, timeout: (_ for _ in ()).throw(_http_error(401))
        with self.assertRaises(oanda.OandaAuthFehler) as ctx:
            oanda._roh_json("https://api-fxpractice.oanda.com/v3/x")
        self.assertIn("abgelaufen", str(ctx.exception).lower())

    def test_401_gegen_live_host_nennt_practice_token_verdacht(self):
        oanda._oeffne = lambda req, timeout: (_ for _ in ()).throw(_http_error(401))
        with self.assertRaises(oanda.OandaAuthFehler) as ctx:
            oanda._roh_json("https://api-fxtrade.oanda.com/v3/x")
        self.assertIn("practice", str(ctx.exception).lower())


class TestRohJson(unittest.TestCase):
    def test_erfolg_gibt_dict(self):
        oanda.token = lambda: "tok"
        oanda._oeffne = lambda req, timeout: io.BytesIO(json.dumps({"ok": 1}).encode())
        try:
            self.assertEqual(oanda._roh_json("https://api-fxpractice.oanda.com/v3/x"),
                             {"ok": 1})
        finally:
            oanda._oeffne = None  # Task setzt in setUp/tearDown der echten Suite zurueck
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_oanda_http -v`
Expected: FAIL `ModuleNotFoundError: No module named 'oanda'`

- [ ] **Step 3: `oanda.py` schreiben (nur Zugang + Seam)**

```python
"""Zugang zu OANDA v20 (REST v3) - Kerzen, Preise, Instrumentdetails,
signierte Orders. Nur Standardbibliothek, ein Bearer-Header, kein eigenes .venv.
Vorbild: kraken/kraken.py (gleiche Aufgabenteilung, andere Boerse, kein HMAC -
OANDA authentifiziert mit einem Personal Access Token).

Practice- und Live-Host stehen in wachen.json, nie hartkodiert. Ein 401 hat
zwei Ursachen und die Meldung unterscheidet sie: Token abgelaufen ODER ein
Practice-Token gegen den Live-Host (SPEC.md, Fallen).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHEN = HIER / "wachen.json"
KOPF = {"User-Agent": "MaxHirn-Handel/1.0"}
MAX_FEHLER = 5

# Test-Seam: die einzige Stelle, die wirklich ins Netz geht. Tests ersetzen sie.
_oeffne = None


class OandaFehler(RuntimeError):
    """Fachlicher Fehler aus einer gueltigen OANDA-Antwort. Kein Wiederholen."""


class OandaAuthFehler(OandaFehler):
    """401. Meldung unterscheidet abgelaufenen Token von Practice-gegen-Live."""


def _aus_registry(name):
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            wert, _ = winreg.QueryValueEx(k, name)
            return str(wert).strip() or None
    except OSError:
        return None


def _variable(name):
    return (os.environ.get(name) or "").strip() or _aus_registry(name)


def token():
    return _variable("OANDA_TOKEN")


def konto_id():
    return _variable("OANDA_KONTO_ID")


def zugang_vorhanden():
    return bool(token() and konto_id())


def _wachen():
    return json.loads(WACHEN.read_text(encoding="utf-8"))


def host(live):
    w = _wachen()
    return w["oanda_host_live"] if live else w["oanda_host_papier"]


def _urlopen(req, timeout):
    fn = _oeffne or urllib.request.urlopen
    return fn(req, timeout=timeout)


def _roh_json(url, *, method="GET", body=None):
    tok = token()
    if not tok:
        raise OandaFehler("OANDA_TOKEN nicht gesetzt")
    kopf = dict(KOPF)
    kopf["Authorization"] = "Bearer " + tok
    daten = None
    if body is not None:
        kopf["Content-Type"] = "application/json"
        daten = json.dumps(body).encode()
    req = urllib.request.Request(url, data=daten, headers=kopf, method=method)
    try:
        with _urlopen(req, 20) as antwort:
            return json.loads(antwort.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            if "fxtrade" in url:
                raise OandaAuthFehler(
                    "OANDA 401 gegen den Live-Host - Verdacht: ein Practice-Token "
                    "gegen fxtrade. Fuer Papier muss oanda_host_papier verwendet "
                    "werden.") from None
            raise OandaAuthFehler(
                "OANDA 401 gegen den Practice-Host - der Token ist abgelaufen "
                "oder falsch. Neuen Personal Access Token im OANDA-Konto ziehen.") from None
        raise OandaFehler("OANDA HTTP %d auf %s" % (e.code, method)) from None


def _mit_wiederholung(fn, *a, **kw):
    fehler = 0
    while True:
        try:
            return fn(*a, **kw)
        except OandaFehler:
            raise
        except Exception as e:  # noqa: BLE001 - Transportfehler, wird gezaehlt
            fehler += 1
            if fehler >= MAX_FEHLER:
                raise
            print("  OANDA-Transportfehler %d/%d: %s" % (fehler, MAX_FEHLER, e),
                  file=sys.stderr)
            time.sleep(1.5 * fehler)
```

Test-Anmerkung: der Test setzt `oanda._oeffne` (nicht `_urlopen`). `_urlopen` liest `_oeffne` bei jedem Aufruf, damit das Monkeypatching greift. In `test_oanda_http.py` `tearDown` `oanda._oeffne = None` zurücksetzen (nicht auf die echte Funktion).

- [ ] **Step 4: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_oanda_http -v`
Expected: PASS. `test_401_gegen_live_host_nennt_practice_token_verdacht` prüft die Unterscheidung aus SPEC.md.

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/orb/oanda.py Agenten/Handel/orb/tests/test_oanda_http.py
git commit -m "Spur 4 (ORB): oanda.py - HTTP-Seam, Token/Konto aus Registry, 401-Unterscheidung"
```

---

## Task 3: `oanda.py` — M15-Kerzen mit Pagination und Cache

**Files:**
- Modify: `Agenten/Handel/orb/oanda.py` (Funktionen `kerzen`, `_kerzen_seite`, Cache)
- Create: `Agenten/Handel/orb/tests/test_oanda_kerzen.py`
- Create: `Agenten/Handel/orb/tests/fixtures/candles_seite1.json`, `candles_seite2.json`

**Interfaces:**
- Consumes: `_roh_json` (Task 2)
- Produces:
  - `kerzen(oanda_inst: str, *, von: datetime, bis: datetime, granularity="M15", cache_dir: Path|None=None) -> list[dict]`
    Jede Kerze: `{"zeit": datetime (UTC, tz-aware), "o": float, "h": float, "l": float, "c": float, "complete": bool}`.
    **`complete:false`-Kerzen werden verworfen** (Global Constraint). Aufsteigend sortiert, keine Duplikate.
    Paginiert über `from`/`to` in ≤ 5000er-Blöcken. Schreibt/liest `cache_dir/<inst>_<granularity>.json` lückenfrei.

- [ ] **Step 1: Fixtures schreiben** — zwei aufeinanderfolgende OANDA-Antworten

`orb/tests/fixtures/candles_seite1.json`:
```json
{"instrument": "DE30_EUR", "granularity": "M15", "candles": [
  {"time": "2025-07-15T07:00:00.000000000Z", "complete": true,  "mid": {"o": "18000.0", "h": "18010.0", "l": "17995.0", "c": "18005.0"}},
  {"time": "2025-07-15T07:15:00.000000000Z", "complete": true,  "mid": {"o": "18005.0", "h": "18020.0", "l": "18002.0", "c": "18018.0"}},
  {"time": "2025-07-15T07:30:00.000000000Z", "complete": true,  "mid": {"o": "18018.0", "h": "18040.0", "l": "18015.0", "c": "18038.0"}}
]}
```
`orb/tests/fixtures/candles_seite2.json`:
```json
{"instrument": "DE30_EUR", "granularity": "M15", "candles": [
  {"time": "2025-07-15T07:30:00.000000000Z", "complete": true,  "mid": {"o": "18018.0", "h": "18040.0", "l": "18015.0", "c": "18038.0"}},
  {"time": "2025-07-15T07:45:00.000000000Z", "complete": true,  "mid": {"o": "18038.0", "h": "18050.0", "l": "18030.0", "c": "18033.0"}},
  {"time": "2025-07-15T08:00:00.000000000Z", "complete": false, "mid": {"o": "18033.0", "h": "18035.0", "l": "18031.0", "c": "18034.0"}}
]}
```

- [ ] **Step 2: Failing test schreiben** — `orb/tests/test_oanda_kerzen.py`

```python
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import oanda

FIX = Path(__file__).resolve().parent / "fixtures"


class TestKerzen(unittest.TestCase):
    def setUp(self):
        self.seiten = [json.loads((FIX / "candles_seite1.json").read_text()),
                       json.loads((FIX / "candles_seite2.json").read_text())]
        self.aufrufe = []

        def fake(url, *, method="GET", body=None):
            self.aufrufe.append(url)
            return self.seiten[len(self.aufrufe) - 1] if len(self.aufrufe) <= 2 else {"candles": []}

        self._alt = oanda._roh_json
        oanda._roh_json = fake
        oanda.token = lambda: "tok"

    def tearDown(self):
        oanda._roh_json = self._alt

    def test_paginiert_und_entfernt_unvollstaendige(self):
        k = oanda.kerzen("DE30_EUR",
                         von=datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc),
                         bis=datetime(2025, 7, 15, 9, 0, tzinfo=timezone.utc))
        zeiten = [c["zeit"] for c in k]
        # 07:00, 07:15, 07:30, 07:45 - die 08:00 (complete:false) ist raus
        self.assertEqual(len(k), 4)
        self.assertEqual(zeiten, sorted(zeiten))
        self.assertEqual(len(set(zeiten)), 4)  # 07:30 nicht doppelt
        self.assertTrue(all(c["complete"] for c in k))
        self.assertIsInstance(k[0]["o"], float)
        self.assertGreaterEqual(len(self.aufrufe), 2)  # hat paginiert

    def test_cache_wird_geschrieben_und_gelesen(self):
        cache = FIX.parent / "_tmp_cache"
        cache.mkdir(exist_ok=True)
        for f in cache.glob("*.json"):
            f.unlink()
        args = dict(von=datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc),
                    bis=datetime(2025, 7, 15, 9, 0, tzinfo=timezone.utc),
                    cache_dir=cache)
        oanda.kerzen("DE30_EUR", **args)
        vorher = len(self.aufrufe)
        oanda.kerzen("DE30_EUR", **args)          # zweiter Lauf: aus dem Cache
        self.assertEqual(len(self.aufrufe), vorher)  # kein weiterer Netzaufruf
```

- [ ] **Step 3: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_oanda_kerzen -v`
Expected: FAIL `AttributeError: module 'oanda' has no attribute 'kerzen'`

- [ ] **Step 4: `kerzen` in `oanda.py` implementieren**

```python
# --- Kerzen -----------------------------------------------------------------

MAX_JE_ABRUF = 5000
GRAN_SEKUNDEN = {"M15": 900, "M1": 60, "H1": 3600, "D": 86400}


def _parse_kerze(c):
    from datetime import datetime, timezone
    t = c["time"][:19]  # "2025-07-15T07:00:00" ohne Nanosekunden + Z
    m = c["mid"]
    return {"zeit": datetime.fromisoformat(t).replace(tzinfo=timezone.utc),
            "o": float(m["o"]), "h": float(m["h"]),
            "l": float(m["l"]), "c": float(m["c"]),
            "complete": bool(c["complete"])}


def _kerzen_seite(oanda_inst, granularity, von, bis, live=False):
    import urllib.parse
    p = urllib.parse.urlencode({
        "granularity": granularity, "price": "M",
        "from": von.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": bis.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": MAX_JE_ABRUF,
    })
    url = "%s/v3/instruments/%s/candles?%s" % (host(live), oanda_inst, p)
    d = _mit_wiederholung(_roh_json, url)
    return [_parse_kerze(c) for c in d.get("candles", [])]


def _cache_datei(cache_dir, oanda_inst, granularity):
    return cache_dir / ("%s_%s.json" % (oanda_inst, granularity))


def _cache_laden(pfad):
    from datetime import datetime, timezone
    if not pfad.exists():
        return []
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    for c in roh:
        c["zeit"] = datetime.fromisoformat(c["zeit"]).replace(tzinfo=timezone.utc)
    return roh


def _cache_speichern(pfad, kerzen_liste):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    roh = [dict(c, zeit=c["zeit"].strftime("%Y-%m-%dT%H:%M:%S")) for c in kerzen_liste]
    pfad.write_text(json.dumps(roh, ensure_ascii=False), encoding="utf-8")


def kerzen(oanda_inst, *, von, bis, granularity="M15", cache_dir=None, live=False):
    """M15-Kerzen [von, bis), aufsteigend, ohne Duplikate, ohne complete:false.

    Paginiert in MAX_JE_ABRUF-Bloecken ueber from/to. Mit cache_dir wird der
    Bestand lueckenlos zwischengespeichert; ein zweiter Lauf ueber denselben
    Bereich geht nicht mehr ins Netz."""
    schritt_s = GRAN_SEKUNDEN[granularity] * MAX_JE_ABRUF
    from datetime import timedelta

    vorhanden = {}
    cache_pfad = _cache_datei(cache_dir, oanda_inst, granularity) if cache_dir else None
    if cache_pfad:
        for c in _cache_laden(cache_pfad):
            vorhanden[c["zeit"]] = c

    if not vorhanden or min(vorhanden) > von or max(vorhanden) < bis - timedelta(seconds=GRAN_SEKUNDEN[granularity]):
        cursor = von
        while cursor < bis:
            block_bis = min(bis, cursor + timedelta(seconds=schritt_s))
            for c in _kerzen_seite(oanda_inst, granularity, cursor, block_bis, live):
                if c["complete"]:
                    vorhanden[c["zeit"]] = c
            cursor = block_bis

    liste = [vorhanden[t] for t in sorted(vorhanden) if von <= t < bis]
    if cache_pfad:
        _cache_speichern(cache_pfad, [vorhanden[t] for t in sorted(vorhanden)])
    return liste
```

- [ ] **Step 5: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_oanda_kerzen -v`
Expected: PASS (2 Tests). `_tmp_cache/` danach von Hand löschen (ist unter `orb/tests/`, nicht `orb/daten/` — nicht von `.gitignore` erfasst; der Test räumt am Anfang auf, aber im `git status` prüfen und nicht committen).

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/orb/oanda.py Agenten/Handel/orb/tests/test_oanda_kerzen.py Agenten/Handel/orb/tests/fixtures/candles_seite1.json Agenten/Handel/orb/tests/fixtures/candles_seite2.json
git commit -m "Spur 4 (ORB): oanda.kerzen - Pagination, Cache, complete:false verworfen"
```

---

## Task 4: `oanda.py` — Preise, Instrumentdetails, Konto-Marge; DE30-Check (Netz nötig)

**Files:**
- Modify: `Agenten/Handel/orb/oanda.py`
- Create: `Agenten/Handel/orb/tests/test_oanda_meta.py`
- Create: `Agenten/Handel/orb/tests/fixtures/pricing.json`, `instrument.json`, `account.json`

**Interfaces:**
- Produces:
  - `preis(oanda_inst, live=False) -> dict` → `{"bid": float, "ask": float, "spread_punkte": float}`
  - `instrument_details(oanda_inst, live=False) -> dict` → `{"minimumTradeSize": float, "displayPrecision": int, "pipLocation": int, "marginRate": float}`
  - `konto_marge_frei(live=False) -> float` — `account.marginAvailable` in Kontowährung (EUR)
  - `instrument_handelbar(oanda_inst, live=False) -> bool` — True, wenn `instrument_details` ohne Fehler antwortet (für den DE30-Check)

- [ ] **Step 1: Fixtures schreiben**

`fixtures/pricing.json`:
```json
{"prices": [{"instrument": "DE30_EUR", "bids": [{"price": "18004.5"}], "asks": [{"price": "18005.7"}]}]}
```
`fixtures/instrument.json`:
```json
{"instruments": [{"name": "DE30_EUR", "type": "CFD", "displayPrecision": 1, "pipLocation": 0, "minimumTradeSize": "1", "marginRate": "0.05"}]}
```
`fixtures/account.json`:
```json
{"account": {"currency": "EUR", "marginAvailable": "1234.56", "balance": "2000.00"}}
```

- [ ] **Step 2: Failing test schreiben** — `orb/tests/test_oanda_meta.py`

```python
import json
import unittest
from pathlib import Path

import oanda

FIX = Path(__file__).resolve().parent / "fixtures"


class TestMeta(unittest.TestCase):
    def setUp(self):
        self._alt = oanda._roh_json
        oanda.token = lambda: "tok"
        oanda.konto_id = lambda: "kid"

    def tearDown(self):
        oanda._roh_json = self._alt

    def _mock(self, name):
        d = json.loads((FIX / name).read_text())
        oanda._roh_json = lambda url, *, method="GET", body=None: d

    def test_preis_liefert_bid_ask_spread(self):
        self._mock("pricing.json")
        p = oanda.preis("DE30_EUR")
        self.assertAlmostEqual(p["bid"], 18004.5)
        self.assertAlmostEqual(p["ask"], 18005.7)
        self.assertAlmostEqual(p["spread_punkte"], 1.2, places=1)

    def test_instrument_details(self):
        self._mock("instrument.json")
        d = oanda.instrument_details("DE30_EUR")
        self.assertEqual(d["minimumTradeSize"], 1.0)
        self.assertEqual(d["displayPrecision"], 1)
        self.assertAlmostEqual(d["marginRate"], 0.05)

    def test_konto_marge_frei(self):
        self._mock("account.json")
        self.assertAlmostEqual(oanda.konto_marge_frei(), 1234.56)

    def test_instrument_handelbar_true_bei_antwort(self):
        self._mock("instrument.json")
        self.assertTrue(oanda.instrument_handelbar("DE30_EUR"))

    def test_instrument_handelbar_false_bei_fehler(self):
        def boom(url, *, method="GET", body=None):
            raise oanda.OandaFehler("HTTP 400")
        oanda._roh_json = boom
        self.assertFalse(oanda.instrument_handelbar("DE30_EUR"))
```

- [ ] **Step 3: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_oanda_meta -v`
Expected: FAIL `AttributeError: ... 'preis'`

- [ ] **Step 4: Funktionen in `oanda.py` implementieren**

```python
# --- Preise, Instrumentdetails, Konto -------------------------------------

def preis(oanda_inst, live=False):
    url = "%s/v3/accounts/%s/pricing?instruments=%s" % (host(live), konto_id(), oanda_inst)
    d = _mit_wiederholung(_roh_json, url)
    p = d["prices"][0]
    bid = float(p["bids"][0]["price"])
    ask = float(p["asks"][0]["price"])
    return {"bid": bid, "ask": ask, "spread_punkte": round(ask - bid, 2)}


def instrument_details(oanda_inst, live=False):
    url = "%s/v3/accounts/%s/instruments?instruments=%s" % (host(live), konto_id(), oanda_inst)
    d = _mit_wiederholung(_roh_json, url)
    i = d["instruments"][0]
    return {"minimumTradeSize": float(i.get("minimumTradeSize", 1)),
            "displayPrecision": int(i.get("displayPrecision", 1)),
            "pipLocation": int(i.get("pipLocation", 0)),
            "marginRate": float(i.get("marginRate", 0) or 0)}


def konto_marge_frei(live=False):
    url = "%s/v3/accounts/%s/summary" % (host(live), konto_id())
    d = _mit_wiederholung(_roh_json, url)
    a = d.get("account") or d
    return float(a["marginAvailable"])


def instrument_handelbar(oanda_inst, live=False):
    """Fuer den DE30-Check: antwortet OANDA Practice ueberhaupt fuer diesen
    Index? Fehlt DE30_EUR aus Deutschland, faellt die Spur auf US30/NAS100
    zurueck (SPEC.md, Fallen) - kein Blocker fuer den Rest."""
    try:
        instrument_details(oanda_inst, live)
        return True
    except OandaFehler:
        return False
```

- [ ] **Step 5: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_oanda_meta -v`
Expected: PASS (5 Tests).

- [ ] **Step 6: DE30-Check gegen echtes Practice-Konto (Netz nötig — Mensch)**

Voraussetzung: OANDA-Practice-Konto angelegt, `OANDA_TOKEN` und `OANDA_KONTO_ID` gesetzt:
```
! setx OANDA_TOKEN "<personal access token aus dem OANDA-Konto>"
! setx OANDA_KONTO_ID "<xxx-xxx-xxxxxxxx-xxx>"
```
Dann aus `Agenten/Handel/orb/`:
```
..\scanner\.venv\Scripts\python.exe -c "import oanda; print('DE30 :', oanda.instrument_handelbar('DE30_EUR')); print('US30 :', oanda.instrument_handelbar('US30_USD')); print('NAS  :', oanda.instrument_handelbar('NAS100_USD')); print('Marge:', oanda.konto_marge_frei()); print(oanda.preis('US30_USD'))"
```
Erwartung: mindestens `US30_USD` und `NAS100_USD` handelbar. Wenn `DE30_EUR` `False` ist: das in `ORB-Handel.md` (Task 15) vermerken, `instrumente` in `wachen.json` auf die zwei US-Indizes beschränken, `DE30`-Backtest in Task 6/8 überspringen. **Kein Commit in diesem Step** — nur Feststellung.

- [ ] **Step 7: Commit**

```bash
git add Agenten/Handel/orb/oanda.py Agenten/Handel/orb/tests/test_oanda_meta.py Agenten/Handel/orb/tests/fixtures/pricing.json Agenten/Handel/orb/tests/fixtures/instrument.json Agenten/Handel/orb/tests/fixtures/account.json
git commit -m "Spur 4 (ORB): oanda - Preise, Instrumentdetails, Konto-Marge, Instrument-Check"
```

---

## Task 5: `backtest.py` — Regel-Engine je Session

**Files:**
- Create: `Agenten/Handel/orb/backtest.py` (nur die Session-Mechanik)
- Create: `Agenten/Handel/orb/tests/test_backtest_session.py`

**Interfaces:**
- Consumes: `session.py` (Task 1). Kerzen als Liste `{"zeit","o","h","l","c","complete"}` wie `oanda.kerzen`.
- Produces:
  - `sessions_gruppieren(kerzen, inst_konf) -> list[tuple[date, list[kerze]]]` — M15-Kerzen nach Börsen-Handelstag, nur Kerzen ab Eröffnung bis Zwangsschluss
  - `opening_range(session_kerzen, inst_konf, tag) -> tuple[float, float] | None` — `(hoch, tief)` aus den ersten zwei M15 im Range-Fenster; `None`, wenn weniger als zwei
  - `simuliere_session(session_kerzen, inst_konf, tag, w, einstiegsmodell: str) -> dict | None`
    `einstiegsmodell` ∈ `{"schluss", "naechste_eroeffnung"}`.
    Rückgabe `None`, wenn kein Breakout / Range außerhalb `[mindest,max]_range_punkte` / Breakout nach `letzter_einstieg`.
    Sonst: `{"tag", "inst", "richtung": "long"|"short", "einstieg": float, "stop": float, "ziel": float, "ausgang": "stop"|"ziel"|"zwangsschluss", "ausstieg": float, "range_punkte": float, "mehrdeutig": bool, "gv_punkte": float}` — `gv_punkte` = `(ausstieg-einstieg)` für long, negiert für short; **ohne** Spread (der kommt in Task 6).

- [ ] **Step 1: Failing test schreiben** — `orb/tests/test_backtest_session.py`

```python
import unittest
from datetime import date, datetime, timezone, timedelta

import backtest

INST = {"eroeffnung": "09:00", "zone": "Europe/Berlin", "cash_close": "17:30"}
W = {"letzter_einstieg_min_vor_schluss": 90,
     "mindest_range_punkte": {"X": 5}, "max_range_punkte": {"X": 500},
     "ziel_modus": "r_vielfaches", "ziel_k": 2.0,
     "ziel_punkte": {"X": 40},
     "instrumente": {"X": INST}}


def _k(hh, mm, o, h, l, c, tag=date(2025, 7, 15)):
    return {"zeit": datetime(tag.year, tag.month, tag.day, hh, mm, tzinfo=timezone.utc),
            "o": o, "h": h, "l": l, "c": c, "complete": True}


def _session_long_ziel():
    # Range 07:00-07:30 UTC (= 09:00 Berlin Sommer): hoch 18010, tief 17990
    return [
        _k(7, 0, 18000, 18008, 17992, 18004),
        _k(7, 15, 18004, 18010, 17990, 18006),
        _k(7, 30, 18006, 18012, 18004, 18011),   # schliesst > hoch 18010 -> Long-Einstieg
        _k(7, 45, 18011, 18040, 18009, 18035),   # laeuft Richtung Ziel
        _k(8, 0, 18035, 18055, 18033, 18052),    # Ziel 18010 + 2*(18010-17990)=18050 getroffen
    ]


class TestOpeningRange(unittest.TestCase):
    def test_hoch_tief_aus_ersten_zwei(self):
        s = _session_long_ziel()
        hr = backtest.opening_range(s, INST, date(2025, 7, 15))
        self.assertEqual(hr, (18010.0, 17990.0))

    def test_none_bei_einer_kerze(self):
        self.assertIsNone(backtest.opening_range([_k(7, 0, 1, 2, 0, 1)], INST, date(2025, 7, 15)))


class TestSimuliere(unittest.TestCase):
    def test_long_bis_ziel(self):
        r = backtest.simuliere_session(_session_long_ziel(), INST, date(2025, 7, 15), W, "schluss")
        self.assertEqual(r["richtung"], "long")
        self.assertEqual(r["einstieg"], 18011.0)      # Schlusskurs der Breakout-Kerze
        self.assertEqual(r["stop"], 17990.0)          # Gegenseite der Range
        self.assertEqual(r["ziel"], 18051.0)          # 18011 + 2*(18011-17990)? nein: k*range ab Einstieg
        self.assertEqual(r["ausgang"], "ziel")
        self.assertGreater(r["gv_punkte"], 0)

    def test_stop_vor_ziel_gleiche_kerze_ist_stop(self):
        s = [
            _k(7, 0, 100, 105, 95, 100),
            _k(7, 15, 100, 110, 90, 101),            # Range hoch 110, tief 90
            _k(7, 30, 101, 112, 99, 111),            # Long-Einstieg bei 111, Stop 90
            _k(7, 45, 111, 140, 85, 120),            # beruehrt Ziel UND Stop -> Stop
        ]
        r = backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss")
        self.assertEqual(r["ausgang"], "stop")
        self.assertTrue(r["mehrdeutig"])
        self.assertLess(r["gv_punkte"], 0)

    def test_kein_breakout_gibt_none(self):
        s = [_k(7, 0, 100, 101, 99, 100), _k(7, 15, 100, 101, 99, 100),
             _k(7, 30, 100, 100.5, 99.5, 100), _k(7, 45, 100, 100.5, 99.5, 100)]
        self.assertIsNone(backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss"))

    def test_range_zu_klein_gibt_none(self):
        w2 = dict(W, mindest_range_punkte={"X": 50})
        r = backtest.simuliere_session(_session_long_ziel(), INST, date(2025, 7, 15), w2, "schluss")
        self.assertIsNone(r)

    def test_breakout_nach_letztem_einstieg_gibt_none(self):
        # Zwangsschluss 15:30 UTC, letzter Einstieg 14:00 UTC
        s = [_k(7, 0, 100, 110, 90, 100), _k(7, 15, 100, 110, 90, 100),
             _k(14, 15, 100, 130, 99, 121)]   # Breakout erst 14:15 -> zu spaet
        self.assertIsNone(backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss"))
```

Hinweis: Der `ziel`-Erwartungswert in `test_long_bis_ziel` ist absichtlich als
Kontrollrechnung angegeben — bei `r_vielfaches` ist `ziel = einstieg + k * range_hoehe`
für long. Bei `einstieg=18011`, `range_hoehe=20`, `k=2` → `ziel=18051`. Stop ist
**immer** die Gegenseite der Opening Range (`17990`), nicht `einstieg - k*range`.

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_backtest_session -v`
Expected: FAIL `ModuleNotFoundError: No module named 'backtest'`

- [ ] **Step 3: `backtest.py` schreiben (nur Session-Mechanik)**

```python
"""Backtest der vierten Spur: Opening Range Breakout ueber DE30/US30/NAS100.

Diese Datei prueft die "81 %"-Behauptung (SPEC.md, Anlass). Sie handelt nichts.
Regeln exakt nach SPEC.md, Abschnitt "Die Strategie, exakt".

Mehrdeutigkeit: M15 loest nicht auf, ob Hoch oder Tief zuerst kam. Beruehrt
eine Kerze Stop UND Ziel, zaehlt sie als Stop (konservativ, "am Tief pruefen,
nicht am Schluss").
"""

import session as sess


def sessions_gruppieren(kerzen, inst_konf):
    aus = {}
    for k in kerzen:
        tag = sess.handelstag(k["zeit"], inst_konf["zone"])
        _, range_ende = sess.opening_range_fenster(inst_konf, tag)
        eroeff, _ = sess.opening_range_fenster(inst_konf, tag)
        schluss = sess.zwangsschluss(inst_konf, tag)
        if eroeff <= k["zeit"] < schluss:
            aus.setdefault(tag, []).append(k)
    return [(t, sorted(aus[t], key=lambda x: x["zeit"])) for t in sorted(aus)]


def opening_range(session_kerzen, inst_konf, tag):
    start, ende = sess.opening_range_fenster(inst_konf, tag)
    im_fenster = [k for k in session_kerzen if start <= k["zeit"] < ende]
    if len(im_fenster) < 2:
        return None
    zwei = im_fenster[:2]
    return max(k["h"] for k in zwei), min(k["l"] for k in zwei)


def _inst_schluessel(inst_konf, w):
    for name, konf in w["instrumente"].items():
        if konf is inst_konf or konf == inst_konf:
            return name
    return next(iter(w["instrumente"]))


def simuliere_session(session_kerzen, inst_konf, tag, w, einstiegsmodell):
    key = _inst_schluessel(inst_konf, w)
    hr = opening_range(session_kerzen, inst_konf, tag)
    if hr is None:
        return None
    hoch, tief = hr
    range_hoehe = hoch - tief
    if range_hoehe < w["mindest_range_punkte"][key] or range_hoehe > w["max_range_punkte"][key]:
        return None

    _, range_ende = sess.opening_range_fenster(inst_konf, tag)
    letzt = sess.letzter_einstieg(inst_konf, tag, w["letzter_einstieg_min_vor_schluss"])
    nach_range = [k for k in session_kerzen if k["zeit"] >= range_ende]

    einstieg_kerze = None
    richtung = None
    for i, k in enumerate(nach_range):
        if k["zeit"] > letzt:
            break
        if k["c"] > hoch:
            einstieg_kerze, richtung, rest = k, "long", nach_range[i + 1:]
            break
        if k["c"] < tief:
            einstieg_kerze, richtung, rest = k, "short", nach_range[i + 1:]
            break
    if einstieg_kerze is None:
        return None

    if einstiegsmodell == "schluss":
        einstieg = einstieg_kerze["c"]
    else:  # naechste_eroeffnung
        if not rest:
            return None
        einstieg = rest[0]["o"]
        rest = rest[1:]

    if richtung == "long":
        stop = tief
        ziel = einstieg + (w["ziel_k"] * range_hoehe if w["ziel_modus"] == "r_vielfaches"
                           else w["ziel_punkte"][key])
    else:
        stop = hoch
        ziel = einstieg - (w["ziel_k"] * range_hoehe if w["ziel_modus"] == "r_vielfaches"
                           else w["ziel_punkte"][key])

    ausgang, ausstieg, mehrdeutig = "zwangsschluss", None, False
    pruef_kerzen = [einstieg_kerze] + list(rest) if einstiegsmodell == "schluss" else list(rest)
    for k in pruef_kerzen:
        if richtung == "long":
            stop_beruehrt = k["l"] <= stop
            ziel_beruehrt = k["h"] >= ziel
        else:
            stop_beruehrt = k["h"] >= stop
            ziel_beruehrt = k["l"] <= ziel
        if stop_beruehrt and ziel_beruehrt:
            ausgang, ausstieg, mehrdeutig = "stop", stop, True
            break
        if stop_beruehrt:
            ausgang, ausstieg = "stop", stop
            break
        if ziel_beruehrt:
            ausgang, ausstieg = "ziel", ziel
            break
    if ausstieg is None:
        ausstieg = pruef_kerzen[-1]["c"] if pruef_kerzen else einstieg

    gv = (ausstieg - einstieg) if richtung == "long" else (einstieg - ausstieg)
    return {"tag": tag, "inst": key, "richtung": richtung, "einstieg": einstieg,
            "stop": stop, "ziel": ziel, "ausgang": ausgang, "ausstieg": ausstieg,
            "range_punkte": range_hoehe, "mehrdeutig": mehrdeutig,
            "gv_punkte": gv}
```

- [ ] **Step 4: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_backtest_session -v`
Expected: PASS (8 Tests). Deckt long/short, Stop, Ziel, mehrdeutig, kein Breakout, Range-Filter, zu später Breakout.

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/orb/backtest.py Agenten/Handel/orb/tests/test_backtest_session.py
git commit -m "Spur 4 (ORB): backtest.py - Session-Regelengine (Breakout, Stop/Ziel, mehrdeutig)"
```

---

## Task 6: `backtest.py` — Aggregation, Kosten, Bericht mit Urteil

**Files:**
- Modify: `Agenten/Handel/orb/backtest.py` (Aggregation, Bericht, `--raster`, `main`)
- Create: `Agenten/Handel/orb/tests/test_backtest_bericht.py`

**Interfaces:**
- Consumes: `simuliere_session` (Task 5), `oanda.kerzen` (Task 3).
- Produces:
  - `mit_kosten(ergebnis: dict, spread_punkte: float, slippage_punkte: float=0.5) -> float` — `gv_punkte` minus `(spread + slippage)` je Runde (ein Aufschlag beim Ein-, einer beim Aus­stieg → `spread` einmal, weil Spread den halben Spread je Seite ist; **Modell: ein voller Spread + `slippage` je Runde**, SPEC.md §87)
  - `bericht(ergebnisse: list[dict], inst_konf, spread_punkte, kursreihe: list[float]) -> dict` mit Schlüsseln:
    `trefferquote`, `oe_gewinn`, `oe_verlust`, `noetige_trefferquote`, `ev_je_runde`,
    `verlierer`, `verlierer_warnung` (bool, `< 10`), `quartale` (Liste `{quartal, ev, n}`),
    `spread_sensitivitaet` (`{"1.0": ev, "1.5": ev, "2.0": ev}`),
    `max_rueckschlag`, `mehrdeutige`, `urteil` (str, eine Zeile), `haelt_81` (bool)
  - `main(argv)` — CLI: `--instrument DE30_EUR|US30_USD|NAS100_USD|alle`, `--jahre 2`, `--modell schluss|naechste_eroeffnung|beide`, `--raster`, `--cache orb/daten`

- [ ] **Step 1: Failing test schreiben** — `orb/tests/test_backtest_bericht.py`

```python
import unittest

import backtest

INST = {"eroeffnung": "09:00", "zone": "Europe/Berlin", "cash_close": "17:30"}


def _erg(gv, ausgang, mehrdeutig=False, tag="2025-01-15"):
    from datetime import date
    y, m, d = (int(x) for x in tag.split("-"))
    return {"tag": date(y, m, d), "inst": "X", "richtung": "long",
            "einstieg": 100.0, "stop": 90.0, "ziel": 120.0, "ausgang": ausgang,
            "ausstieg": 100.0 + gv, "range_punkte": 10.0,
            "mehrdeutig": mehrdeutig, "gv_punkte": gv}


class TestKosten(unittest.TestCase):
    def test_ein_spread_plus_slippage_je_runde(self):
        e = _erg(10.0, "ziel")
        self.assertAlmostEqual(backtest.mit_kosten(e, spread_punkte=1.2, slippage_punkte=0.5),
                               10.0 - 1.2 - 0.5)


class TestBericht(unittest.TestCase):
    def test_kennzahlen_und_urteil(self):
        # 7 Gewinner a +8 Netto, 3 Verlierer a -10 Netto (nach Kosten)
        erg = [_erg(9.7, "ziel") for _ in range(7)] + [_erg(-9.5, "stop") for _ in range(3)]
        b = backtest.bericht(erg, INST, spread_punkte=0.2, kursreihe=[100, 101, 99, 105])
        self.assertEqual(b["verlierer"], 3)
        self.assertFalse(b["verlierer_warnung"])          # >= 10? nein -> Warnung an
        self.assertTrue(b["verlierer_warnung"] is False or b["verlierer"] < 10)
        self.assertAlmostEqual(b["trefferquote"], 0.7, places=2)
        self.assertGreater(b["ev_je_runde"], 0)
        self.assertIn("81", b["urteil"])
        self.assertIsInstance(b["haelt_81"], bool)

    def test_warnung_bei_unter_10_verlierern(self):
        erg = [_erg(9.0, "ziel") for _ in range(30)] + [_erg(-9.0, "stop") for _ in range(4)]
        b = backtest.bericht(erg, INST, spread_punkte=0.2, kursreihe=[100, 110])
        self.assertTrue(b["verlierer_warnung"])           # 4 < 10

    def test_negatives_quartal_zieht_urteil_auf_nein(self):
        gut = [_erg(9.0, "ziel", tag="2025-01-%02d" % (d + 1)) for d in range(20)]
        schlecht = [_erg(-30.0, "stop", tag="2025-04-%02d" % (d + 1)) for d in range(12)]
        b = backtest.bericht(gut + schlecht, INST, spread_punkte=0.2, kursreihe=[100, 105])
        self.assertFalse(b["haelt_81"])
        self.assertIn("Nein", b["urteil"])
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_backtest_bericht -v`
Expected: FAIL `AttributeError: ... 'mit_kosten'`

- [ ] **Step 3: Aggregation + Bericht in `backtest.py` implementieren**

```python
# --- Kosten + Bericht -----------------------------------------------------

from collections import defaultdict


def mit_kosten(ergebnis, spread_punkte, slippage_punkte=0.5):
    """gv_punkte nach Spread. Modell SPEC.md: ein voller Spread + Slippage je
    Runde (OANDA-Index-CFD = Spread, keine Kommission auf Standard)."""
    return ergebnis["gv_punkte"] - spread_punkte - slippage_punkte


def _quartal(d):
    return "%d-Q%d" % (d.year, (d.month - 1) // 3 + 1)


def _noetige_trefferquote(oe_gewinn, oe_verlust):
    spanne = oe_gewinn + abs(oe_verlust)
    return abs(oe_verlust) / spanne if spanne > 0 else 1.0


def bericht(ergebnisse, inst_konf, spread_punkte, kursreihe, slippage_punkte=0.5):
    netto = [mit_kosten(e, spread_punkte, slippage_punkte) for e in ergebnisse]
    n = len(netto) or 1
    gewinner = [x for x in netto if x > 0]
    verlierer = [x for x in netto if x <= 0]
    oe_gewinn = sum(gewinner) / len(gewinner) if gewinner else 0.0
    oe_verlust = sum(verlierer) / len(verlierer) if verlierer else 0.0
    ev = sum(netto) / n

    q = defaultdict(list)
    for e, x in zip(ergebnisse, netto):
        q[_quartal(e["tag"])].append(x)
    quartale = [{"quartal": k, "ev": sum(v) / len(v), "n": len(v)}
                for k, v in sorted(q.items())]
    schlechtestes_q_ev = min((qq["ev"] for qq in quartale), default=0.0)

    kum = hoch = 0.0
    max_rueck = 0.0
    for x in netto:
        kum += x
        hoch = max(hoch, kum)
        max_rueck = max(max_rueck, hoch - kum)

    sens = {}
    for faktor in (1.0, 1.5, 2.0):
        sn = [e["gv_punkte"] - spread_punkte * faktor - slippage_punkte for e in ergebnisse]
        sens["%.1f" % faktor] = sum(sn) / (len(sn) or 1)

    trefferquote = len(gewinner) / n
    noetig = _noetige_trefferquote(oe_gewinn, oe_verlust)
    genug_verlierer = len(verlierer) >= 10
    haelt_81 = (ev > 0 and schlechtestes_q_ev > 0 and genug_verlierer
                and trefferquote >= 0.75)
    urteil = ("Ja - Trefferquote %.0f%%, EV %+.2f Pkt/Runde, schlechtestes Quartal "
              "%+.2f, %d Verlierer." % (trefferquote * 100, ev, schlechtestes_q_ev,
                                        len(verlierer))) if haelt_81 else \
             ("Nein - %s (Trefferquote %.0f%%, EV %+.2f, schlechtestes Quartal %+.2f, "
              "%d Verlierer)." % (
                  "EV im Fenster <= 0" if ev <= 0 else
                  "schlechtestes Quartal <= 0" if schlechtestes_q_ev <= 0 else
                  "unter 10 Verlierer" if not genug_verlierer else
                  "Trefferquote unter 75%",
                  trefferquote * 100, ev, schlechtestes_q_ev, len(verlierer)))
    return {
        "trefferquote": trefferquote, "oe_gewinn": oe_gewinn, "oe_verlust": oe_verlust,
        "noetige_trefferquote": noetig, "ev_je_runde": ev,
        "verlierer": len(verlierer), "verlierer_warnung": not genug_verlierer,
        "quartale": quartale, "spread_sensitivitaet": sens,
        "max_rueckschlag": max_rueck,
        "mehrdeutige": sum(1 for e in ergebnisse if e["mehrdeutig"]),
        "kursreihe_start_ende": (kursreihe[0], kursreihe[-1]) if kursreihe else (None, None),
        "haelt_81": haelt_81, "urteil": urteil,
    }
```

- [ ] **Step 4: `main(argv)` + `--raster` + Textausgabe implementieren**

```python
def _lauf_instrument(w, key, jahre, modell, cache_dir, live=False):
    import oanda
    from datetime import datetime, timezone, timedelta
    konf = w["instrumente"][key]
    bis = datetime.now(timezone.utc)
    von = bis - timedelta(days=365 * jahre)
    kerzen = oanda.kerzen(konf["oanda"], von=von, bis=bis, cache_dir=cache_dir, live=live)
    ergebnisse = []
    for tag, sk in sessions_gruppieren(kerzen, konf):
        r = simuliere_session(sk, konf, tag, w, modell)
        if r:
            ergebnisse.append(r)
    kursreihe = [k["c"] for k in kerzen]
    return bericht(ergebnisse, konf, konf["spread_punkte"], kursreihe), len(ergebnisse)


def _drucke_bericht(key, modell, b, n):
    print("=== %s | Einstiegsmodell: %s | %d Sessions ===" % (key, modell, n))
    print("  Trefferquote beobachtet %.1f%%   noetig (Break-even) %.1f%%"
          % (b["trefferquote"] * 100, b["noetige_trefferquote"] * 100))
    print("  Ø Gewinn %+.2f Pkt   Ø Verlust %+.2f Pkt   EV %+.3f Pkt/Runde"
          % (b["oe_gewinn"], b["oe_verlust"], b["ev_je_runde"]))
    print("  Verlierer %d%s   mehrdeutige Kerzen %d   max. Rueckschlag %.1f Pkt"
          % (b["verlierer"], "  << WARNUNG < 10" if b["verlierer_warnung"] else "",
             b["mehrdeutige"], b["max_rueckschlag"]))
    print("  Quartale:")
    for q in b["quartale"]:
        print("    %-8s EV %+.3f  (n=%d)" % (q["quartal"], q["ev"], q["n"]))
    print("  Spread-Sensitivitaet  1.0x %+.3f  1.5x %+.3f  2.0x %+.3f"
          % (b["spread_sensitivitaet"]["1.0"], b["spread_sensitivitaet"]["1.5"],
             b["spread_sensitivitaet"]["2.0"]))
    print("  URTEIL: %s" % b["urteil"])
    print()


def main(argv=None):
    import argparse
    import json as _json
    from pathlib import Path as _P
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--instrument", default="alle")
    p.add_argument("--jahre", type=int, default=2)
    p.add_argument("--modell", default="beide",
                   choices=("schluss", "naechste_eroeffnung", "beide"))
    p.add_argument("--raster", action="store_true")
    p.add_argument("--cache", default=str(_P(__file__).resolve().parent / "daten"))
    a = p.parse_args(argv)

    w = _json.loads((_P(__file__).resolve().parent / "wachen.json").read_text("utf-8"))
    cache_dir = _P(a.cache)
    keys = list(w["instrumente"]) if a.instrument == "alle" else [a.instrument]
    modelle = (["schluss", "naechste_eroeffnung"] if a.modell == "beide" else [a.modell])

    raster_ziel_k = [1.0, 1.5, 2.0, 2.5, 3.0]
    for key in keys:
        for modell in modelle:
            if a.raster:
                for k in raster_ziel_k:
                    w2 = dict(w, ziel_modus="r_vielfaches", ziel_k=k)
                    b, n = _lauf_instrument(w2, key, a.jahre, modell, cache_dir)
                    print("[Raster k=%.1f] " % k, end="")
                    _drucke_bericht(key, modell, b, n)
            else:
                b, n = _lauf_instrument(w, key, a.jahre, modell, cache_dir)
                _drucke_bericht(key, modell, b, n)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_backtest_bericht -v`
Expected: PASS (4 Tests).

- [ ] **Step 6: Gesamte Test-Suite läuft grün**

Run (aus `orb/`): `..\scanner\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: alle bisherigen Tests PASS.

- [ ] **Step 7: Commit**

```bash
git add Agenten/Handel/orb/backtest.py Agenten/Handel/orb/tests/test_backtest_bericht.py
git commit -m "Spur 4 (ORB): backtest-Aggregation, Kostenmodell, Bericht mit Urteil"
```

---

## Task 7: Backtest über 2 Jahre fahren, Spread eichen, Urteil festhalten (Netz nötig — Mensch)

**Files:**
- Modify: `Agenten/Handel/orb/wachen.json` (`instrumente[*].spread_punkte` eichen; nach Urteil `instrument_aktiv`, `ziel_modus`, `ziel_k`/`ziel_punkte`, `freigabe.backtest_bestanden`)
- Create: `Agenten/Handel/orb/daten/*.json` (Cache, nicht versioniert)

**Interfaces:** keine neuen. Dieser Task **entscheidet, ob es weitergeht**.

- [ ] **Step 1: Spread an echten `pricing`-Daten eichen**

Aus `Agenten/Handel/orb/` (Practice-Konto verbunden, aus Task 4):
```
..\scanner\.venv\Scripts\python.exe -c "import oanda; [print(i, oanda.preis(i)) for i in ('DE30_EUR','US30_USD','NAS100_USD')]"
```
Fünf Abrufe über den Tag verteilt, den **Median** des `spread_punkte` je Instrument in `wachen.json` → `instrumente[<inst>].spread_punkte` eintragen (Edit, nicht Python-Rewrite — es ist JSON, `json.dump` wäre ok, aber der Konsistenz halber Edit). Ist `DE30_EUR` aus Task 4 nicht handelbar: Eintrag `DE30_EUR` aus `instrumente`, `mindest_range_punkte`, `max_range_punkte`, `ziel_punkte` entfernen.

- [ ] **Step 2: Backtest über 2 Jahre, beide Modelle, mit Raster**

```
..\scanner\.venv\Scripts\python.exe backtest.py --jahre 2 --modell beide --raster > daten/backtest-2026-09-08.txt
```
Dauer: mehrere Minuten (paginierte Kerzen, erster Lauf). Zweiter Lauf liest aus `daten/`.

- [ ] **Step 3: Urteil festhalten**

Die `URTEIL:`-Zeile je Instrument aus `daten/backtest-2026-09-08.txt` in Task 15 (`ORB-Handel.md`) übernehmen. Dann die Verzweigung:

- **Mindestens ein Instrument: `Ja`** → in `wachen.json`: `instrument_aktiv` auf das beste Instrument, `ziel_modus`/`ziel_k` (oder `ziel_punkte`) auf die Rasterzeile mit dem höchsten EV bei positivem schlechtestem Quartal, `freigabe.backtest_bestanden` auf `true`. Weiter mit Task 8.
- **Alle Instrumente: `Nein`** → `freigabe.backtest_bestanden` bleibt `false`, `instrument_aktiv` bleibt `null`. **Task 8–14 werden übersprungen.** Der Plan endet bei Task 15: `ORB-Handel.md` hält das Nein-Urteil mit Zahlen fest, `Handelsregeln.md` bekommt Spur 4 mit dem Vermerk „Backtest nicht bestanden, kein Papierlauf", `handeln.py` wird trotzdem nicht gebraucht. **Vor dem Abbruch Rückfrage an Max** (das ist eine Weggabelung, keine Formsache).

- [ ] **Step 4: Commit**

```bash
git add Agenten/Handel/orb/wachen.json
git commit -m "Spur 4 (ORB): Backtest-Ergebnis - Spread geeicht, instrument_aktiv + TP-Startwerte gesetzt"
```

---

## Task 8: `wachen_orb.py` — Spur-Bedingungen, Range-Filter, `sperre_zu`

**Files:**
- Create: `Agenten/Handel/orb/wachen_orb.py`
- Create: `Agenten/Handel/orb/tests/test_wachen_orb.py`

**Interfaces:**
- Consumes: `../scanner/wachen_pruefung.py` (importiert, nicht kopiert) → `drawdown`, `herzschlag_frisch`, `rollierender_ev`, `spiegele_journal`, `freigabe_erfuellt`.
- Produces:
  - `runden_aus_journal(journal_pfad) -> list[dict]` — Journal-Spalte `eur`, je Runde `{"zeit","inst","modus","einsatz","erloes","gv","grund"}`. Eine Runde = `einstieg`-Zeile gefolgt von `ausstieg`-Zeile desselben Instruments (FIFO).
  - `groessenfaktor(ruecklauf_eur, w) -> float` (0.5 oder 1.0), `kill_ausgeloest(ruecklauf_eur, w) -> bool`
  - `range_ok(range_punkte, inst_key, w) -> bool`
  - `sperre_zu(grund) -> bool` — schreibt `orb/wachen.json`, `handel_erlaubt` nur `true`→`false`
  - `freigabe_voll_erfuellt(w) -> bool` — `backtest_bestanden and netto_positiv and (papierlauf-Wochen erreicht) and (sessions erreicht)` — die vier Werte aus Sperre 4
  - `lage(w, journal_pfad, zustand) -> dict` — wie `kraken.wachen_kraken.lage`, plus `freigabe_voll`

- [ ] **Step 1: Failing test schreiben** — `orb/tests/test_wachen_orb.py`

```python
import json
import unittest
from pathlib import Path

import wachen_orb as wo

HIER = Path(__file__).resolve().parent
WACHEN = HIER.parent / "wachen.json"


class TestRangeFilter(unittest.TestCase):
    def setUp(self):
        self.w = json.loads(WACHEN.read_text("utf-8"))

    def test_range_unter_mindest_nicht_ok(self):
        key = next(iter(self.w["instrumente"]))
        mn = self.w["mindest_range_punkte"][key]
        self.assertFalse(wo.range_ok(mn - 1, key, self.w))
        self.assertTrue(wo.range_ok(mn + 1, key, self.w))

    def test_range_ueber_max_nicht_ok(self):
        key = next(iter(self.w["instrumente"]))
        mx = self.w["max_range_punkte"][key]
        self.assertFalse(wo.range_ok(mx + 1, key, self.w))


class TestFreigabe(unittest.TestCase):
    def _w(self, **over):
        base = {"freigabe": {"backtest_bestanden": True, "netto_positiv": True,
                             "papierlauf_min_wochen": 6, "papierlauf_min_sessions": 50}}
        base["freigabe"].update(over)
        return base

    def test_alle_vier_erfuellt(self):
        self.assertTrue(wo.freigabe_voll_erfuellt(
            self._w(), gehandelte_wochen=7, gehandelte_sessions=60))

    def test_zu_wenig_sessions_blockt(self):
        self.assertFalse(wo.freigabe_voll_erfuellt(
            self._w(), gehandelte_wochen=7, gehandelte_sessions=40))

    def test_backtest_nicht_bestanden_blockt(self):
        self.assertFalse(wo.freigabe_voll_erfuellt(
            self._w(backtest_bestanden=False), gehandelte_wochen=99, gehandelte_sessions=99))


class TestSperreZu(unittest.TestCase):
    def test_nur_true_nach_false(self, ):
        # gegen eine Kopie testen, nicht die echte wachen.json veraendern
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp()) / "wachen.json"
        d = json.loads(WACHEN.read_text("utf-8"))
        d["handel_erlaubt"] = False
        tmp.write_text(json.dumps(d), "utf-8")
        alt = wo.WACHEN
        wo.WACHEN = tmp
        try:
            self.assertFalse(wo.sperre_zu("test"))       # war schon false
            d["handel_erlaubt"] = True
            tmp.write_text(json.dumps(d), "utf-8")
            self.assertTrue(wo.sperre_zu("test"))         # true -> false
            self.assertIs(json.loads(tmp.read_text())["handel_erlaubt"], False)
        finally:
            wo.WACHEN = alt
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_wachen_orb -v`
Expected: FAIL `ModuleNotFoundError: No module named 'wachen_orb'`

- [ ] **Step 3: `wachen_orb.py` schreiben**

```python
"""Bedingungen der vierten Spur (ORB Index-CFD, OANDA, EUR).

Die waehrungsneutrale Rechnung steht nur einmal im Haus: sie kommt aus
scanner/wachen_pruefung.py und wird hier importiert, nicht abgeschrieben.
Eigen ist hier nur, was Waehrung, Datei oder Strategie kennt: die eur-Spalte
im Journal, die Range-Filter, sperre_zu auf orb/wachen.json.

Kein Netz. Alles aus handelsjournal.csv und zustand.json. Einziger
Schreibzugriff auf wachen.json: sperre_zu, nur true -> false.
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHEN = HIER / "wachen.json"

sys.path.insert(0, str(HIER.parent / "scanner"))
import wachen_pruefung as basis  # noqa: E402

drawdown = basis.drawdown
herzschlag_frisch = basis.herzschlag_frisch
rollierender_ev = basis.rollierender_ev
spiegele_journal = basis.spiegele_journal


def runden_aus_journal(journal_pfad):
    p = Path(journal_pfad)
    if not p.exists():
        return []
    offen, runden = {}, []
    with p.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            inst = r["inst"]
            try:
                eur = float(r["eur"])
            except (TypeError, ValueError):
                continue
            if r["aktion"] == "einstieg":
                offen.setdefault(inst, []).append(eur)
            elif r["aktion"] == "ausstieg" and offen.get(inst):
                einsatz = offen[inst].pop(0)
                runden.append({"zeit": r["zeit"], "inst": inst, "modus": r["modus"],
                               "einsatz": einsatz, "erloes": eur, "gv": eur - einsatz,
                               "grund": r.get("grund", "")})
    return runden


def groessenfaktor(ruecklauf_eur, w):
    grenze = w.get("drawdown_halbierung_prozent", 15.0) / 100.0 * w["kill_switch_gesamt_eur"]
    return 0.5 if ruecklauf_eur >= grenze > 0 else 1.0


def kill_ausgeloest(ruecklauf_eur, w):
    ks = w.get("kill_switch_gesamt_eur")
    return ks is not None and ruecklauf_eur >= ks


def range_ok(range_punkte, inst_key, w):
    return (w["mindest_range_punkte"][inst_key] <= range_punkte
            <= w["max_range_punkte"][inst_key])


def freigabe_voll_erfuellt(w, gehandelte_wochen, gehandelte_sessions):
    f = w.get("freigabe") or {}
    return bool(f.get("backtest_bestanden") and f.get("netto_positiv")
                and gehandelte_wochen >= f.get("papierlauf_min_wochen", 6)
                and gehandelte_sessions >= f.get("papierlauf_min_sessions", 50))


def sperre_zu(grund):
    w = json.loads(WACHEN.read_text("utf-8"))
    if not w.get("handel_erlaubt"):
        return False
    w["handel_erlaubt"] = False
    w["_sperre_zu_ausgeloest"] = {
        "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "grund": grund}
    WACHEN.write_text(json.dumps(w, ensure_ascii=False, indent=2), "utf-8")
    return True


def _wochen_und_sessions(runden):
    papier = [r for r in runden if r["modus"] == "papier"]
    if not papier:
        return 0.0, 0
    from datetime import date
    tage = [date.fromisoformat(r["zeit"][:10]) for r in papier]
    return (max(tage) - min(tage)).days / 7.0, len(papier)


def lage(w, journal_pfad, zustand):
    runden = runden_aus_journal(journal_pfad)
    papier = [r for r in runden if r["modus"] == "papier"]
    hoch, rueck = drawdown(runden)
    frisch, alter = herzschlag_frisch(zustand, w.get("herzschlag_max_minuten", 45))
    ev = rollierender_ev(runden)
    wochen, sessions = _wochen_und_sessions(runden)
    return {
        "runden_gesamt": len(runden), "runden_papier": len(papier),
        "hoechststand_eur": hoch, "ruecklauf_eur": rueck,
        "groessenfaktor": groessenfaktor(rueck, w), "kill": kill_ausgeloest(rueck, w),
        "herzschlag_frisch": frisch, "herzschlag_alter_min": alter,
        "rollierender_ev": ev, "ev_negativ": ev is not None and ev < 0,
        "papier_wochen": wochen, "papier_sessions": sessions,
        "freigabe_voll": freigabe_voll_erfuellt(w, wochen, sessions),
    }
```

- [ ] **Step 4: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_wachen_orb -v`
Expected: PASS (6 Tests).

- [ ] **Step 5: Commit**

```bash
git add Agenten/Handel/orb/wachen_orb.py Agenten/Handel/orb/tests/test_wachen_orb.py
git commit -m "Spur 4 (ORB): wachen_orb.py - Range-Filter, Freigabe-Vollpruefung, sperre_zu"
```

---

## Task 9: `handeln.py` — Zustand, Journal, Ausstiege, Notausstieg

**Files:**
- Create: `Agenten/Handel/orb/handeln.py` (Zustand, Journal, `pruefe_ausstiege`, `flach_stellen`, `--wachen`, `--vorschau`-Gerüst)
- Create: `Agenten/Handel/orb/tests/test_handeln_ausstieg.py`

**Interfaces:**
- Consumes: `oanda` (Preis), `session`, `wachen_orb` (Task 8), `wachen.json`.
- Produces:
  - `lade_zustand() -> dict` / `schreibe_zustand(z)` — Schema `{"positionen": [...], "letzte_stops": {}, "letzter_lauf": iso, "modus": "papier"|"live"}`
    Position: `{"inst","richtung","einstieg","stop","ziel","units","risiko_eur","eroeffnet","order_id"}`
  - `journal(*felder)` — Kopf `["zeit","modus","aktion","inst","richtung","preis","eur","units","stop","ziel","grund"]`
  - `pruefe_ausstiege(z, w, live)` — je Position: Stop / Ziel / Zwangsschluss (via `session.in_session`); schließt, schreibt Journal (Spread abgezogen), setzt `letzte_stops` bei Stop
  - `flach_stellen(z, w, live, grund)` — alle Positionen sofort zu (Kill-Switch, Herzschlag alt)
  - `_erloes_eur(p, kurs, w)` — `units * (ausstieg - einstieg) * punkt_wert_eur` je Richtung, **minus halber Spread** (Ausstiegsseite)

- [ ] **Step 1: Failing test schreiben** — `orb/tests/test_handeln_ausstieg.py`

```python
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import handeln

HIER = Path(__file__).resolve().parent


class TestAusstieg(unittest.TestCase):
    def setUp(self):
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        # ein Instrument mit bekannten Werten forcieren
        self.key = "US30_USD"
        self.w["instrument_aktiv"] = self.key
        self.w["instrumente"][self.key] = {
            "oanda": "US30_USD", "eroeffnung": "15:30", "zone": "Europe/Berlin",
            "cash_close": "22:00", "spread_punkte": 2.0, "punkt_wert_eur": 1.0}
        self._preise = {}
        handeln.oanda.preis = lambda inst, live=False: {
            "bid": self._preise[inst], "ask": self._preise[inst] + 2.0,
            "spread_punkte": 2.0}
        self._journal = []
        handeln.journal = lambda *f: self._journal.append(f)

    def _pos(self, richtung, einstieg, stop, ziel, units=2.0):
        return {"inst": self.key, "richtung": richtung, "einstieg": einstieg,
                "stop": stop, "ziel": ziel, "units": units, "risiko_eur": 20.0,
                "eroeffnet": "2025-07-15", "order_id": None}

    def test_long_stop_schliesst_und_journalisiert(self):
        z = {"positionen": [self._pos("long", 40000, 39950, 40100)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 39940                     # unter Stop
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self._journal[-1][2], "ausstieg")
        self.assertEqual(self._journal[-1][10], "stop")
        self.assertIn(self.key, z["letzte_stops"])

    def test_long_ziel_schliesst(self):
        z = {"positionen": [self._pos("long", 40000, 39950, 40100)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 40120
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self._journal[-1][10], "ziel")

    def test_short_stop_ist_oben(self):
        z = {"positionen": [self._pos("short", 40000, 40050, 39900)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 40060
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self._journal[-1][10], "stop")

    def test_offen_wenn_zwischen_stop_und_ziel(self):
        z = {"positionen": [self._pos("long", 40000, 39950, 40100)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 40010
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(len(z["positionen"]), 1)
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_handeln_ausstieg -v`
Expected: FAIL `ModuleNotFoundError: No module named 'handeln'`

- [ ] **Step 3: `handeln.py` schreiben (Zustand, Journal, Ausstiege, Wachen)**

Struktur wortnah zu `kraken/handeln.py`. Kern:

```python
"""Vierte Spur: ORB Index-CFD ueber OANDA, gerichtet (long/short), gehebelt
(Hebel faellt aus der Positionsrechnung), in EUR.

Aufruf (aus diesem Ordner):
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --vorschau
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --papier
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --live
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --wachen

Neun Sperren muessen ALLE offen sein, sonst laeuft trotz --live nur Papier
(Liste in live_sperren). Ausstiege laufen NIE durch das Freigabefenster - ein
Stop muss auch greifen, wenn niemand davorsitzt.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

import oanda
import session as sess
import wachen_orb as wp

HIER = Path(__file__).resolve().parent
WACHEN = HIER / "wachen.json"
ZUSTAND = HIER / "zustand.json"
JOURNAL = HIER / "handelsjournal.csv"
FREIGABE_ZEITLIMIT_S = 120


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _wachen():
    return json.loads(WACHEN.read_text("utf-8"))


def lade_zustand():
    if ZUSTAND.exists():
        return json.loads(ZUSTAND.read_text("utf-8"))
    return {"positionen": [], "letzte_stops": {}, "letzter_lauf": None, "modus": None}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    ZUSTAND.write_text(json.dumps(z, ensure_ascii=False, indent=2), "utf-8")


def journal(*felder):
    neu = not JOURNAL.exists()
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        if neu:
            s.writerow(["zeit", "modus", "aktion", "inst", "richtung", "preis",
                        "eur", "units", "stop", "ziel", "grund"])
        s.writerow(felder)


def _inst_konf(w):
    return w["instrumente"][w["instrument_aktiv"]]


def _punkt_wert(w):
    return _inst_konf(w)["punkt_wert_eur"]


def _halber_spread_eur(w, units):
    return 0.5 * _inst_konf(w)["spread_punkte"] * _punkt_wert(w) * units


def _wert_eur(p, kurs, w):
    """Realisierter Wert der Position bei kurs, in EUR, VOR Spread."""
    diff = (kurs - p["einstieg"]) if p["richtung"] == "long" else (p["einstieg"] - kurs)
    return diff * _punkt_wert(w) * p["units"]


def _schliesse(p, kurs, w, live, grund, z):
    if live:
        try:
            oanda.markt_order(_inst_konf(w)["oanda"],
                              -_signierte_units(p), echt=True)
        except Exception as e:  # noqa: BLE001
            print("  Ausstieg %s fehlgeschlagen: %s" % (p["inst"], e), file=sys.stderr)
            return False
    gv = _wert_eur(p, kurs, w) - _halber_spread_eur(w, p["units"])
    print("  ZU  %-10s %s @ %-10.5g (%s)  G/V %+.2f EUR"
          % (p["inst"], p["richtung"], kurs, grund, gv))
    journal(_jetzt(), "live" if live else "papier", "ausstieg", p["inst"],
            p["richtung"], "%.5f" % kurs, "%.2f" % (p["risiko_eur"] + gv),
            "%.4f" % p["units"], "", "", grund)
    if grund == "stop":
        z["letzte_stops"][p["inst"]] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return True


def _signierte_units(p):
    return p["units"] if p["richtung"] == "long" else -p["units"]


def pruefe_ausstiege(z, w, live):
    behalten = []
    jetzt = datetime.now(timezone.utc)
    for p in z["positionen"]:
        preis = oanda.preis(_inst_konf(w)["oanda"], live)
        kurs = preis["bid"] if p["richtung"] == "long" else preis["ask"]
        grund = None
        if p["richtung"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif kurs >= p["ziel"]:
                grund = "ziel"
        else:
            if kurs >= p["stop"]:
                grund = "stop"
            elif kurs <= p["ziel"]:
                grund = "ziel"
        if grund is None and not sess.in_session(_inst_konf(w), jetzt):
            grund = "zwangsschluss"
        if not grund or not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def flach_stellen(z, w, live, grund):
    behalten = []
    for p in z["positionen"]:
        preis = oanda.preis(_inst_konf(w)["oanda"], live)
        kurs = preis["bid"] if p["richtung"] == "long" else preis["ask"]
        if not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def sitzung_da():
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


def zeige_wachen(w):
    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)
    print("=== Wachen-Status ORB  %s ===" % _jetzt())
    print("  Freigabe voll (Backtest+Papier)  %s   (Papier %d Sessions / %.1f Wochen, EV %s)"
          % (s["freigabe_voll"], s["papier_sessions"], s["papier_wochen"],
             "n/a" if s["rollierender_ev"] is None else "%+.3f" % s["rollierender_ev"]))
    print("  Ruecklauf  %.2f EUR von Hoechst %.2f  -> Faktor %.2f%s"
          % (s["ruecklauf_eur"], s["hoechststand_eur"], s["groessenfaktor"],
             "   >>> KILL" if s["kill"] else ""))
    print("  Herzschlag frisch  %s  (%s min, Grenze %d)"
          % (s["herzschlag_frisch"],
             "?" if s["herzschlag_alter_min"] is None else "%.0f" % s["herzschlag_alter_min"],
             w.get("herzschlag_max_minuten", 45)))
    print("  Journal-Zweitziel  %s" % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], w.get("journal_zweitziel"))
    print("  Journal ausser Haus  %s (%s)" % ("ok" if ok else "--", info))
    if s["kill"] and wp.sperre_zu("Wochenlauf: Kill-Switch, Ruecklauf %.2f EUR" % s["ruecklauf_eur"]):
        print("  -> handel_erlaubt auf false.")
    if s["ev_negativ"] and wp.sperre_zu("Wochenlauf: rollierender EV %.3f < 0" % s["rollierender_ev"]):
        print("  -> handel_erlaubt auf false.")
```

Die restlichen Teile (`--vorschau`, `--papier`-Zyklus, `pruefe_einstiege`,
`live_sperren`, `main`) kommen in Task 10 und 11. In diesem Task nur so viel
`main`, dass `--wachen` funktioniert:

```python
def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    w = _wachen()
    if not w.get("instrument_aktiv"):
        print("instrument_aktiv ist null - Backtest (Task 7) hat noch kein Urteil. Kein Lauf.")
        return
    if modus == "wachen":
        zeige_wachen(w)
        return
    print("Zyklus kommt in Task 10/11.")  # Platzhalter NUR bis Task 10; dort ersetzt.


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    for name in ("vorschau", "papier", "live", "wachen"):
        g.add_argument("--" + name, action="store_const", dest="modus", const=name)
    a = p.parse_args()
    lauf(a.modus or "papier")
```

> Der `print("Zyklus kommt ...")` ist der **einzige** erlaubte Platzhalter im
> Plan und wird in Task 10 Step 3 vollständig ersetzt. Er steht hier, damit
> Task 9 mit grünen Ausstiegs-Tests committet werden kann, ohne dass `--papier`
> etwas Falsches tut.

- [ ] **Step 4: `oanda.markt_order` ergänzen (von `pruefe_ausstiege`/`_schliesse` im Live-Pfad gebraucht)**

In `oanda.py`:
```python
def markt_order(oanda_inst, units, *, echt=False, live=False):
    """Eine Markt-Order. units ganzzahlig, Vorzeichen = Richtung (long > 0).
    echt=False -> nur validieren (OANDA rechnet sie durch, sie landet nicht
    im Buch). Gibt (order_id, fuellpreis) zurueck; fuellpreis ist der echte
    fillTransaction-Preis (Slippage), None bei echt=False."""
    ganz = int(units)  # immer abrunden Richtung 0
    body = {"order": {"type": "MARKET", "instrument": oanda_inst,
                      "units": str(ganz),
                      "timeInForce": "FOK", "positionFill": "DEFAULT"}}
    pfad = "/v3/accounts/%s/orders" % konto_id()
    if not echt:
        pfad = "/v3/accounts/%s/pricing" % konto_id()  # Trockenlauf: nur Preis ziehen
        d = _mit_wiederholung(_roh_json, host(live) + pfad + "?instruments=" + oanda_inst)
        return None, None
    d = _mit_wiederholung(_roh_json, host(live) + pfad, method="POST", body=body)
    tx = d.get("orderFillTransaction") or {}
    fp = tx.get("price")
    return tx.get("id"), (float(fp) if fp else None)
```

- [ ] **Step 5: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_handeln_ausstieg -v`
Expected: PASS (4 Tests).

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/orb/handeln.py Agenten/Handel/orb/oanda.py Agenten/Handel/orb/tests/test_handeln_ausstieg.py
git commit -m "Spur 4 (ORB): handeln.py - Zustand, Journal, Ausstiege, --wachen; oanda.markt_order"
```

---

## Task 10: `handeln.py` — Einstieg, Opening Range live, Positionsgröße

**Files:**
- Modify: `Agenten/Handel/orb/handeln.py` (`live_range`, `breakout_signal`, `positionsgroesse`, `pruefe_einstieg`, `lauf`-Zyklus, `--vorschau`)
- Create: `Agenten/Handel/orb/tests/test_handeln_einstieg.py`

**Interfaces:**
- Consumes: `oanda.kerzen` (Task 3), `session` (Task 1), `wachen_orb.range_ok` (Task 8).
- Produces:
  - `live_range(w, tag) -> tuple[float, float] | None` — Opening Range aus den ersten zwei **abgeschlossenen** M15 des heutigen Session-Fensters (`oanda.kerzen` von Eröffnung bis Range-Ende)
  - `breakout_signal(w, hoch, tief) -> tuple[str, float] | None` — `("long", einstieg)` / `("short", einstieg)` aus der letzten abgeschlossenen M15 seit Range-Ende; `None` wenn keiner / nach `letzter_einstieg`
  - `positionsgroesse(einstieg, stop, w, faktor=1.0) -> tuple[float, float]` — `(units, hebel)`; `units = (risiko_pro_trade_eur*faktor) / (|einstieg-stop| * punkt_wert_eur)`, abgerundet auf `minimumTradeSize`; `hebel = positionswert / marge`, gedeckelt auf `hebel_deckel` (nur Deckel — passt der Trade nicht in den Deckel, `units` so weit senken, dass er passt)
  - `pruefe_einstieg(z, w, live, faktor)` — höchstens **eine** offene Position; kein Einstieg wenn schon eine offen / Range außerhalb Filter / nach `letzter_einstieg` / schon eine Session heute gehandelt

- [ ] **Step 1: Failing test schreiben** — `orb/tests/test_handeln_einstieg.py`

```python
import json
import unittest
from pathlib import Path

import handeln

HIER = Path(__file__).resolve().parent


class TestPositionsgroesse(unittest.TestCase):
    def setUp(self):
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        self.w["instrument_aktiv"] = "US30_USD"
        self.w["instrumente"]["US30_USD"] = {
            "oanda": "US30_USD", "eroeffnung": "15:30", "zone": "Europe/Berlin",
            "cash_close": "22:00", "spread_punkte": 2.0, "punkt_wert_eur": 1.0}
        self.w["risiko_pro_trade_eur"] = 20
        self.w["hebel_deckel"] = 20
        handeln.oanda.instrument_details = lambda inst, live=False: {
            "minimumTradeSize": 1.0, "displayPrecision": 1, "pipLocation": 0,
            "marginRate": 0.05}
        handeln.oanda.konto_marge_frei = lambda live=False: 100000.0

    def test_units_aus_risiko_durch_stopabstand(self):
        # Stopabstand 40 Punkte, punkt_wert 1 EUR -> units = 20 / (40*1) = 0.5 -> abgerundet
        units, hebel = handeln.positionsgroesse(40000.0, 39960.0, self.w)
        self.assertLessEqual(units * 40 * 1.0, 20.0 + 1e-9)   # Risiko nie ueber Budget
        self.assertGreaterEqual(units, 0.0)

    def test_hebel_wird_gedeckelt_nicht_gesetzt(self):
        # winziger Stopabstand -> grosse Position -> Hebel muss auf Deckel begrenzt sein
        handeln.oanda.konto_marge_frei = lambda live=False: 50.0
        units, hebel = handeln.positionsgroesse(40000.0, 39999.0, self.w)
        self.assertLessEqual(hebel, self.w["hebel_deckel"] + 1e-6)


class TestBreakout(unittest.TestCase):
    def setUp(self):
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        self.w["instrument_aktiv"] = "US30_USD"
        self.w["instrumente"]["US30_USD"] = {
            "oanda": "US30_USD", "eroeffnung": "15:30", "zone": "Europe/Berlin",
            "cash_close": "22:00", "spread_punkte": 2.0, "punkt_wert_eur": 1.0}

    def test_long_wenn_schluss_ueber_hoch(self):
        from datetime import datetime, timezone
        handeln.oanda.kerzen = lambda inst, **kw: [
            {"zeit": datetime(2025, 7, 15, 14, 0, tzinfo=timezone.utc), "o": 1, "h": 1,
             "l": 1, "c": 40120, "complete": True}]
        sig = handeln.breakout_signal(self.w, hoch=40100.0, tief=40000.0)
        self.assertEqual(sig, ("long", 40120.0))

    def test_kein_signal_wenn_innerhalb_range(self):
        from datetime import datetime, timezone
        handeln.oanda.kerzen = lambda inst, **kw: [
            {"zeit": datetime(2025, 7, 15, 14, 0, tzinfo=timezone.utc), "o": 1, "h": 1,
             "l": 1, "c": 40050, "complete": True}]
        self.assertIsNone(handeln.breakout_signal(self.w, hoch=40100.0, tief=40000.0))
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_handeln_einstieg -v`
Expected: FAIL `AttributeError: module 'handeln' has no attribute 'positionsgroesse'`

- [ ] **Step 3: Einstiegslogik + vollständigen Zyklus in `handeln.py` implementieren**

```python
def positionsgroesse(einstieg, stop, w, faktor=1.0):
    konf = _inst_konf(w)
    stop_abstand = abs(einstieg - stop)
    if stop_abstand <= 0:
        return 0.0, 0.0
    pw = konf["punkt_wert_eur"]
    risiko = w["risiko_pro_trade_eur"] * faktor
    roh_units = risiko / (stop_abstand * pw)
    mts = oanda.instrument_details(konf["oanda"])["minimumTradeSize"]
    units = (int(roh_units / mts) * mts) if mts else roh_units
    positionswert = units * einstieg * pw
    marge = max(oanda.konto_marge_frei(), 1e-6)
    hebel = positionswert / marge
    if hebel > w["hebel_deckel"]:
        # Hebel ist Ergebnis, nicht Eingabe: Position so weit senken, dass der
        # Deckel haelt. units bleibt Vielfaches von mts.
        max_wert = w["hebel_deckel"] * marge
        units = (int((max_wert / (einstieg * pw)) / mts) * mts) if mts else max_wert / (einstieg * pw)
        positionswert = units * einstieg * pw
        hebel = positionswert / marge
    return units, hebel


def live_range(w, tag):
    konf = _inst_konf(w)
    start, ende = sess.opening_range_fenster(konf, tag)
    ks = oanda.kerzen(konf["oanda"], von=start, bis=ende)
    ks = [k for k in ks if k["complete"]]
    if len(ks) < 2:
        return None
    zwei = ks[:2]
    return max(k["h"] for k in zwei), min(k["l"] for k in zwei)


def breakout_signal(w, hoch, tief):
    konf = _inst_konf(w)
    heute = sess.handelstag(datetime.now(timezone.utc), konf["zone"])
    _, range_ende = sess.opening_range_fenster(konf, heute)
    letzt = sess.letzter_einstieg(konf, heute, w["letzter_einstieg_min_vor_schluss"])
    ks = [k for k in oanda.kerzen(konf["oanda"], von=range_ende,
                                  bis=datetime.now(timezone.utc))
          if k["complete"] and k["zeit"] <= letzt]
    for k in ks:
        if k["c"] > hoch:
            return "long", k["c"]
        if k["c"] < tief:
            return "short", k["c"]
    return None


def _schon_gehandelt_heute(z, w):
    konf = _inst_konf(w)
    heute = sess.handelstag(datetime.now(timezone.utc), konf["zone"]).isoformat()
    if any(p.get("eroeffnet") == heute for p in z["positionen"]):
        return True
    if not JOURNAL.exists():
        return False
    with JOURNAL.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r["aktion"] == "einstieg" and r["inst"] == w["instrument_aktiv"]
                    and r["zeit"][:10] == heute):
                return True
    return False


def pruefe_einstieg(z, w, live, faktor=1.0):
    if z["positionen"] or _schon_gehandelt_heute(z, w):
        return
    konf = _inst_konf(w)
    heute = sess.handelstag(datetime.now(timezone.utc), konf["zone"])
    hr = live_range(w, heute)
    if hr is None:
        print("  keine vollstaendige Opening Range - kein Einstieg.")
        return
    hoch, tief = hr
    key = w["instrument_aktiv"]
    if not wp.range_ok(hoch - tief, key, w):
        print("  Range %.1f Pkt ausserhalb [%s, %s] - Session ausgesetzt."
              % (hoch - tief, w["mindest_range_punkte"][key], w["max_range_punkte"][key]))
        return
    sig = breakout_signal(w, hoch, tief)
    if sig is None:
        print("  kein Breakout (oder nach letztem Einstieg) - kein Einstieg.")
        return
    richtung, einstieg = sig
    stop = tief if richtung == "long" else hoch
    if w["ziel_modus"] == "r_vielfaches":
        spanne = w["ziel_k"] * (hoch - tief)
    else:
        spanne = w["ziel_punkte"][key]
    ziel = einstieg + spanne if richtung == "long" else einstieg - spanne

    units, hebel = positionsgroesse(einstieg, stop, w, faktor)
    if units <= 0:
        print("  Positionsgroesse 0 - kein Einstieg.")
        return

    order_id = fuellpreis = None
    if live:
        signiert = units if richtung == "long" else -units
        try:
            order_id, fuellpreis = oanda.markt_order(konf["oanda"], signiert, echt=True)
        except Exception as e:  # noqa: BLE001
            print("  Einstieg %s fehlgeschlagen: %s" % (key, e), file=sys.stderr)
            return
        if fuellpreis:
            einstieg = fuellpreis           # echter Slippage-Preis ins Journal

    spread_auf = _halber_spread_eur(w, units)
    z["positionen"].append({
        "inst": key, "richtung": richtung, "einstieg": einstieg, "stop": stop,
        "ziel": ziel, "units": units, "risiko_eur": w["risiko_pro_trade_eur"] * faktor,
        "eroeffnet": heute.isoformat(), "order_id": order_id})
    print("  AUF %-10s %s @ %-10.5g  Stop %-10.5g  Ziel %-10.5g  %.4f units  Hebel %.1f"
          % (key, richtung, einstieg, stop, ziel, units, hebel))
    journal(_jetzt(), "live" if live else "papier", "einstieg", key, richtung,
            "%.5f" % einstieg, "%.2f" % (w["risiko_pro_trade_eur"] * faktor + spread_auf),
            "%.4f" % units, "%.5f" % stop, "%.5f" % ziel, "hebel %.1f" % hebel)
```

Jetzt den Platzhalter in `lauf()` aus Task 9 durch den echten Zyklus ersetzen
(Muster `kraken/handeln.py:lauf`): Kill-Switch → `flach_stellen`+`sperre_zu`;
Herzschlag alt → `flach_stellen`, kein Handel; `--vorschau` → Range + Signal +
Positionsgröße zeigen und `live_sperren`; sonst: **Ausstiege zuerst**, dann
`pruefe_einstiege` (Task 11 hängt die Freigabe davor), `schreibe_zustand`,
`spiegele_journal`.

- [ ] **Step 4: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_handeln_einstieg -v`
Expected: PASS (4 Tests).

- [ ] **Step 5: Gesamte Suite grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: alle PASS.

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/orb/handeln.py Agenten/Handel/orb/tests/test_handeln_einstieg.py
git commit -m "Spur 4 (ORB): handeln.py - Opening Range live, Breakout, Positionsgroesse (Hebel gedeckelt), Zyklus"
```

---

## Task 11: `handeln.py` — `--live` mit den neun Sperren + Freigabefenster

**Files:**
- Modify: `Agenten/Handel/orb/handeln.py` (`live_sperren`, `hole_freigabe`, `--live`-Zweig in `lauf`)
- Create: `Agenten/Handel/orb/tests/test_handeln_sperren.py`

**Interfaces:**
- Consumes: `wachen_orb.lage` (Task 8), `oanda.zugang_vorhanden`, `oanda.konto_marge_frei`, `../freigabe.py` (Task 12 — hier zunächst über try/except tolerant).
- Produces:
  - `live_sperren(w, s) -> list[str]` — alle Gründe, die den Lauf auf Papier zurückwerfen. Leere Liste = scharf. Deckt SPEC.md §107 Sperren 1–9:
    1 `handel_erlaubt=false` · 2 `OANDA_TOKEN`/`OANDA_KONTO_ID` fehlt · 3 kein `--live` (im Aufrufer, nicht hier) · 4 `freigabe_voll=false` · 5 Herzschlag alt · 6 `ev_negativ` · 7 `journal_zweitziel` fehlt · 8 `konto_marge_frei < mindest_marge_frei_eur` · 9 keine Sitzung / kein Telegram-Fenster
  - `hole_freigabe(vorschlag: dict, z, s) -> bool` — ruft `freigabe.bestaetige([vorschlag], "orb", bestand, zeitlimit=120)`; Ausnahme/leer → `False` (kein Einstieg)

- [ ] **Step 1: Failing test schreiben** — `orb/tests/test_handeln_sperren.py`

```python
import json
import unittest
from pathlib import Path

import handeln

HIER = Path(__file__).resolve().parent


def _s(**over):
    base = {"freigabe_voll": True, "herzschlag_frisch": True, "ev_negativ": False,
            "rollierender_ev": 1.0, "ruecklauf_eur": 0.0}
    base.update(over)
    return base


class TestLiveSperren(unittest.TestCase):
    def setUp(self):
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        self.w["handel_erlaubt"] = True
        self.w["journal_zweitziel"] = "X:/orb-kopie"
        self.w["mindest_marge_frei_eur"] = 200
        self.w["instrument_aktiv"] = "US30_USD"
        handeln.oanda.zugang_vorhanden = lambda: True
        handeln.oanda.konto_marge_frei = lambda live=False: 5000.0
        handeln.os.environ["MAXHIRN_ROUTINE"] = "1"   # keine Sitzung
        handeln.os.environ.pop("MAXHIRN_ROUTINE", None)  # Standard: Sitzung da (Test-TTY)

    def test_alle_offen_gibt_leere_liste(self):
        handeln.sitzung_da = lambda: True
        self.assertEqual(handeln.live_sperren(self.w, _s()), [])

    def test_handel_erlaubt_false_blockt(self):
        handeln.sitzung_da = lambda: True
        self.w["handel_erlaubt"] = False
        self.assertTrue(any("handel_erlaubt" in g for g in handeln.live_sperren(self.w, _s())))

    def test_freigabe_nicht_voll_blockt(self):
        handeln.sitzung_da = lambda: True
        self.assertTrue(any("Freigabe" in g or "freigabe" in g
                            for g in handeln.live_sperren(self.w, _s(freigabe_voll=False))))

    def test_zu_wenig_marge_blockt(self):
        handeln.sitzung_da = lambda: True
        handeln.oanda.konto_marge_frei = lambda live=False: 100.0
        self.assertTrue(any("Marge" in g or "marge" in g
                            for g in handeln.live_sperren(self.w, _s())))

    def test_keine_sitzung_blockt(self):
        handeln.sitzung_da = lambda: False
        self.assertTrue(any("Sitzung" in g for g in handeln.live_sperren(self.w, _s())))
```

- [ ] **Step 2: Test läuft und schlägt fehl**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_handeln_sperren -v`
Expected: FAIL `AttributeError: ... 'live_sperren'`

- [ ] **Step 3: `live_sperren` + `hole_freigabe` implementieren**

```python
def live_sperren(w, s):
    g = []
    if not w.get("handel_erlaubt"):
        g.append("wachen.json handel_erlaubt=false (Sperre 1)")
    if not oanda.zugang_vorhanden():
        g.append("OANDA_TOKEN/OANDA_KONTO_ID nicht gesetzt (Sperre 2)")
    if not s["freigabe_voll"]:
        g.append("Freigabe nicht voll: Backtest + 6 Wochen Papier + >=50 Sessions + netto positiv (Sperre 4)")
    if not s["herzschlag_frisch"]:
        g.append("Herzschlag alt (Sperre 5)")
    if s["ev_negativ"]:
        g.append("rollierender EV %.3f EUR < 0 (Sperre 6)" % s["rollierender_ev"])
    if not w.get("journal_zweitziel"):
        g.append("journal_zweitziel nicht gesetzt (Sperre 7)")
    noetig = w.get("mindest_marge_frei_eur", 0)
    if noetig and oanda.zugang_vorhanden():
        try:
            frei = oanda.konto_marge_frei()
            if frei < noetig:
                g.append("nur %.2f EUR Marge frei, noetig %.2f (Sperre 8)" % (frei, noetig))
        except Exception as e:  # noqa: BLE001
            g.append("Marge nicht abrufbar (%s) (Sperre 8)" % e)
    if not sitzung_da():
        g.append("keine Sitzung am Bildschirm / kein Telegram-Zeitfenster (Sperre 9)")
    return g


def hole_freigabe(vorschlag, z, s):
    sys.path.insert(0, str(HIER.parent))
    try:
        import freigabe
    except Exception as e:  # noqa: BLE001
        print("  Freigabefenster nicht verfuegbar (%s) - kein Einstieg." % e, file=sys.stderr)
        return False
    bestand = {"gebunden": sum(p["risiko_eur"] for p in z["positionen"]),
               "offene_positionen": len(z["positionen"]),
               "verlust_gesamt": s["ruecklauf_eur"]}
    try:
        bestaetigt = freigabe.bestaetige([vorschlag], "orb", bestand,
                                         zeitlimit=FREIGABE_ZEITLIMIT_S)
        return bool(bestaetigt)
    except Exception as e:  # noqa: BLE001
        print("  Freigabe abgebrochen (%s) - kein Einstieg." % e, file=sys.stderr)
        return False
```

Im `lauf()`-Zyklus: bei `modus == "live"` zuerst `gruende = live_sperren(w, s)`;
nicht leer → `print` + `live = False`. Vor `pruefe_einstieg` im Live-Fall den
`vorschlag`-Dict (inst, richtung, einstieg, stop, stop_pct, ziel, units, hebel,
risiko_eur) bauen und `hole_freigabe(...)` — `False` → kein Einstieg diesen Lauf.
Ausstiege laufen davor und **immer ohne** Freigabe.

- [ ] **Step 4: Test läuft grün**

Run: `..\scanner\.venv\Scripts\python.exe -m unittest tests.test_handeln_sperren -v`
Expected: PASS (5 Tests).

- [ ] **Step 5: `--vorschau` von Hand prüfen (kein Netz, wenn `instrument_aktiv` gesetzt und Kerzen im Cache)**

```
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau
```
Erwartung: zeigt Opening Range (oder „keine vollständige Range"), Breakout-Signal, geplante Positionsgröße/Hebel, und `Live waere gesperrt durch: ...` mit mindestens Sperre 4 und 7.

- [ ] **Step 6: Commit**

```bash
git add Agenten/Handel/orb/handeln.py Agenten/Handel/orb/tests/test_handeln_sperren.py
git commit -m "Spur 4 (ORB): --live mit den neun Sperren, Freigabefenster vor dem Einstieg"
```

---

## Task 12: `freigabe.py` — Spur `orb` ergänzen

**Files:**
- Modify: `Agenten/Handel/freigabe.py`
- Create: `Agenten/Handel/tests_orb_freigabe.py` (Testdatei **neben** `freigabe.py`, da `freigabe.py` nicht in `orb/` liegt; Name so, dass die vorhandene Whitelist `!Agenten/Handel/*.py` sie erfasst)

**Interfaces:**
- Consumes: `orb/wachen.json` (Feldnamen), Positionsrechnung „Hebel aus Stopabstand".
- Produces (in `freigabe.py`): `WACHEN["orb"]`, `TITEL["orb"]`, `BETRAGSFELD["orb"] = "risiko_eur"`, `RECHNER["orb"] = rechne_orb`, `BEISPIEL["orb"]`. `orb` ist **nicht** in `SPOTARTIG` (gerichtet + gehebelt, wie `hebel`).

- [ ] **Step 1: `freigabe.py` lesen** — die Blöcke `WACHEN` (Z. 53), `SPOTARTIG` (Z. 59), `BETRAGSFELD` (Z. 64), `TITEL` (Z. 66), `RECHNER` (Z. 169), Klasse `Freigabefenster` (`_baue_felder`/`_rechne`, Z. ~354/441), `BEISPIEL` (Z. 534). Verstehen, wie `hebel` (Spur 2, XPERP) dort behandelt wird — `orb` ist am nächsten dran.

- [ ] **Step 2: Failing test schreiben** — `Agenten/Handel/tests_orb_freigabe.py`

```python
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import freigabe


class TestOrbSpur(unittest.TestCase):
    def test_orb_in_allen_registern(self):
        self.assertIn("orb", freigabe.WACHEN)
        self.assertIn("orb", freigabe.TITEL)
        self.assertIn("orb", freigabe.BETRAGSFELD)
        self.assertIn("orb", freigabe.RECHNER)
        self.assertIn("orb", freigabe.BEISPIEL)
        self.assertNotIn("orb", freigabe.SPOTARTIG)   # gehebelt, gerichtet

    def test_orb_wachen_pfad_zeigt_auf_orb_ordner(self):
        self.assertEqual(freigabe.WACHEN["orb"].name, "wachen.json")
        self.assertEqual(freigabe.WACHEN["orb"].parent.name, "orb")

    def test_rechne_orb_liefert_stop_und_positionswert(self):
        w = {"risiko_pro_trade_eur": 20, "hebel_deckel": 20}
        auftrag = {"inst": "US30_USD", "richtung": "long", "einstieg": 40000.0,
                   "stop": 39960.0, "ziel": 40100.0, "units": 0.5, "hebel": 3.0}
        r = freigabe.RECHNER["orb"](auftrag, w)
        self.assertEqual(r["richtung"], "long")
        self.assertAlmostEqual(r["stop_abstand"], 40.0)
        self.assertLessEqual(r["hebel"], w["hebel_deckel"])

    def test_beispiel_fenster_oeffnet(self):
        # nur die Datenstruktur, kein tk-mainloop
        b = freigabe.BEISPIEL["orb"]
        self.assertEqual(b[0]["inst"][:5], "US30_")
```

- [ ] **Step 3: Test läuft und schlägt fehl**

Run (aus `Agenten/Handel/`): `..\..\Agenten\Handel\scanner\.venv\Scripts\python.exe -m unittest tests_orb_freigabe -v`
(einfacher: `cd Agenten\Handel && scanner\.venv\Scripts\python.exe -m unittest tests_orb_freigabe -v`)
Expected: FAIL `AssertionError: 'orb' not found in ...`

- [ ] **Step 4: `freigabe.py` erweitern**

```python
# WACHEN-Dict (Z. 53) um eine Zeile:
WACHEN = {"spot": HIER / "scanner" / "wachen.json",
          "hebel": HIER / "xperp" / "wachen.json",
          "kraken": HIER / "kraken" / "wachen.json",
          "orb": HIER / "orb" / "wachen.json"}

# BETRAGSFELD (Z. 64): orb rechnet EUR-Risiko je Trade
BETRAGSFELD = {"spot": "usd", "kraken": "eur", "hebel": "risiko_usd",
               "orb": "risiko_eur"}

# TITEL (Z. 66):
TITEL = {..., "orb": "4 ORB Index-CFD (OANDA, EUR)"}

# RECHNER (Z. 169): orb wie hebel behandeln - Hebel aus Stopabstand, nur Deckel
def rechne_orb(a, w):
    einstieg = float(a["einstieg"])
    stop = float(a["stop"])
    stop_abstand = abs(einstieg - stop)
    hebel = min(float(a.get("hebel", 0) or 0), w.get("hebel_deckel", 999))
    return {"inst": a["inst"], "richtung": a["richtung"],
            "einstieg": einstieg, "stop": stop, "ziel": float(a["ziel"]),
            "stop_abstand": stop_abstand, "units": float(a.get("units", 0) or 0),
            "hebel": hebel, "risiko_eur": w["risiko_pro_trade_eur"]}

RECHNER = {..., "orb": rechne_orb}

# BEISPIEL (Z. 534):
BEISPIEL = {..., "orb": [{"inst": "US30_USD", "richtung": "long",
                          "einstieg": 40000.0, "stop": 39960.0, "ziel": 40100.0,
                          "units": 0.5, "hebel": 3.0}]}
```

Im `Freigabefenster`: `orb` in die Verzweigung für gerichtete Spuren aufnehmen
(dort, wo `hebel` behandelt wird — Feld „Richtung", „Hebel (nur senkbar)",
„Stop", Obergrenze jedes Reglers = Wachen-Wert). Der Hebeldeckel-Regler kann nur
nach unten, nie über `w["hebel_deckel"]`.

- [ ] **Step 5: Test läuft grün + `--beispiel` von Hand**

Run: `cd Agenten\Handel && scanner\.venv\Scripts\python.exe -m unittest tests_orb_freigabe -v` → PASS (4).
Dann: `scanner\.venv\Scripts\python.exe freigabe.py --spur orb --beispiel` → Fenster öffnet, Titel „Scharfschalten - Spur 4 ORB Index-CFD (OANDA, EUR)", Werte anpassbar, Bestätigen/Ablehnen, Zeitlimit läuft.

- [ ] **Step 6: Regression — die anderen Spuren unverändert**

Run: `scanner\.venv\Scripts\python.exe freigabe.py --spur hebel --beispiel` und `--spur kraken --beispiel` → öffnen wie vorher.

- [ ] **Step 7: Commit**

```bash
git add Agenten/Handel/freigabe.py Agenten/Handel/tests_orb_freigabe.py
git commit -m "Spur 4 (ORB): freigabe.py - Spur orb (gerichtet, Hebel aus Stopabstand)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 13: Routine-Wrapper `orb-papier.ps1` + `handel-wachen.ps1` erweitern

**Files:**
- Create: `Agenten/Routinen/orb-papier.ps1`
- Modify: `Agenten/Routinen/handel-wachen.ps1` (einen `orb`-`--wachen`-Lauf anhängen)

**Interfaces:** keine Python-Schnittstellen. Der Wrapper setzt `MAXHIRN_ROUTINE=1`, ruft `handeln.py --papier`, schreibt nach `Routinen/logs/orb-papier-letzter-lauf.log`, läuft nur im Session-Fenster.

- [ ] **Step 1: `orb-papier.ps1` schreiben**

```powershell
# Papierlauf der vierten Spur (ORB Index-CFD, OANDA). Von der Windows-
# Aufgabenplanung alle 15 Min aufgerufen - aber nur im Session-Fenster des
# aktiven Instruments (Eroeffnung+30min bis Zwangsschluss). Ausserhalb tut der
# Lauf nichts und endet mit Code 0.
#
# NICHT ueber /schedule (Cloud-Agent) - der haette keinen Zugriff auf
# wachen.json und OANDA_TOKEN. MAXHIRN_ROUTINE=1 sagt handeln.py: hier sitzt
# niemand, kein Freigabefenster, kein scharfer Handel.

$ErrorActionPreference = 'Stop'
$env:MAXHIRN_ROUTINE = '1'
$wurzel = Split-Path $PSScriptRoot -Parent
$orb    = Join-Path $wurzel 'Handel\orb'
$py     = Join-Path $wurzel 'Handel\scanner\.venv\Scripts\python.exe'
$logs   = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'orb-papier-letzter-lauf.log'
$start = Get-Date
"=== Lauf $($start.ToString('yyyy-MM-dd HH:mm:ss')) ===" | Set-Content $log -Encoding UTF8

if (-not (Test-Path $py)) {
  "ENDE FEHLER: kein Python unter $py" | Add-Content $log -Encoding UTF8
  exit 1
}

try {
  Push-Location $orb
  # handeln.py entscheidet selbst per session.in_session, ob gehandelt wird;
  # der Wrapper ruft immer, das Skript ist ausserhalb der Session ein No-op.
  & $py 'handeln.py' '--papier' *>&1 | Add-Content $log -Encoding UTF8
  Pop-Location
  "ENDE ok nach $([int]((Get-Date) - $start).TotalSeconds) s" | Add-Content $log -Encoding UTF8
} catch {
  Pop-Location -ErrorAction SilentlyContinue
  "ENDE FEHLER: $_" | Add-Content $log -Encoding UTF8
  exit 1
}
```

- [ ] **Step 2: In `handeln.py` `lauf()` den Außer-Session-No-op sicherstellen**

Falls noch nicht: vor dem Zyklus bei `modus in ("papier","live")` prüfen
`if not sess.in_session(_inst_konf(w), datetime.now(timezone.utc)) and not z["positionen"]:`
→ `print("ausserhalb des Session-Fensters, kein Lauf.")`, `return`. (Mit offener
Position **doch** laufen — der Zwangsschluss muss greifen.) Dazu einen
Mini-Test in `tests/test_handeln_ausstieg.py` ergänzen: außerhalb Session + keine
Position → `lauf("papier")` schreibt nichts ins Journal.

- [ ] **Step 3: `handel-wachen.ps1` erweitern**

Nach dem `kraken`-Block (vor `"ENDE ok ..."`), analog:
```powershell
  $orb = Join-Path $wurzel 'Handel\orb'
  if (Test-Path (Join-Path $orb 'handeln.py')) {
    "" | Add-Content $log -Encoding UTF8
    Push-Location $orb
    & $py 'handeln.py' '--wachen' *>&1 | Add-Content $log -Encoding UTF8
    Pop-Location
  }
```
Und den Kopfkommentar um „Spur 4 Handel\orb (ORB Index-CFD, EUR)" ergänzen.

- [ ] **Step 4: Wrapper parst und läuft (No-op außerhalb der Session)**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\orb-papier.ps1`
Erwartung: Exit 0, Log enthält „ausserhalb des Session-Fensters, kein Lauf." **oder** einen echten Zyklus, je nach Uhrzeit. Kein Traceback.
Run: `powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\handel-wachen.ps1` → Exit 0, Log hat einen `=== Wachen-Status ORB ===`-Block.

- [ ] **Step 5: Aufgabe in der Windows-Aufgabenplanung anlegen (Mensch)**

`MaxHirn-ORB-Papier`: Trigger alle 15 Min, den ganzen Tag (das Skript filtert das Session-Fenster selbst); Aktion `powershell -NoProfile -ExecutionPolicy Bypass -File <...>\Agenten\Routinen\orb-papier.ps1`; „Nur ausführen, wenn Netzverbindung besteht". In `Wissen/Routinen.md` (Task 14) eintragen.

- [ ] **Step 6: Commit**

```bash
git add Agenten/Routinen/orb-papier.ps1 Agenten/Routinen/handel-wachen.ps1 Agenten/Handel/orb/handeln.py Agenten/Handel/orb/tests/test_handeln_ausstieg.py
git commit -m "Spur 4 (ORB): Papier-Routine + handel-wachen.ps1 um orb erweitert

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 14: KB-Notizen und Verweise (`Wissen/`, `Handel/README.md`)

**Files:**
- Create: `MaxHirn/Wissen/ORB-Handel.md`
- Modify: `MaxHirn/Wissen/Handelsregeln.md`, `MaxHirn/Wissen/Routinen.md`, `MaxHirn/Wissen/INDEX.md`, `Agenten/Handel/README.md`

**Interfaces:** keine. **Alle `.md`-Änderungen mit dem Edit-Werkzeug**, nie per Python-Rewrite (CRLF).

- [ ] **Step 1: `ORB-Handel.md` schreiben** (Muster `MaxHirn/Wissen/XPERP-Handel.md` — vorher lesen)

Pflichtabschnitte:
- **Frontmatter** `id: 20260908-orb-handel`, `title: 'ORB Index-CFD auf OANDA'`, `tags: [handel]`, `related: [20260902-handelsregeln, 20260830-handelsbots, 20260901-xperp-handel, 20260831-marktscanner]`, einzeilige `summary`.
- **Anlass** — die „81 %"-Behauptung, ungeprüft gehört, Auftrag Backtest+Papier parallel.
- **„10 Punkte" übersetzt** — was ein fester Punkt-TP je Index in EUR bedeutet, `punkt_wert_eur` je Instrument, warum `ziel_modus` zwischen `punkte` und `r_vielfaches` wählt.
- **Backtest-Urteil** — die `URTEIL:`-Zeilen aus Task 7 wörtlich, mit Datum, Fenster (2 Jahre), Trefferquote, EV/Runde, schlechtestem Quartal, Verliererzahl. Hält die 81 %? Ja/Nein je Instrument. **Diese Zahlen stehen nur hier, nicht im Skill/Spec** (sonst veralten sie still).
- **Die neun Sperren** — Verweis auf `SPEC.md §107`, keine Kopie.
- **Fallen** — `complete:false` nie handeln; DST je Tag lokal; 401-Unterscheidung; Wochenend-Gap; `units` abrunden; Slippage echter Füllpreis; Spread im Journal-Betrag; DE30-Zugang aus Deutschland (Ergebnis aus Task 4).
- **Stand** `2026-09-08`.

- [ ] **Step 2: `Handelsregeln.md` — Spur 4 eintragen**

Die Tabelle „die drei bewachten Spuren" um eine Zeile für Spur 4 erweitern
(OANDA, Index-CFD, EUR, `orb/wachen.json`, gerichtet, Hebel aus Stopabstand).
In der Sperrenliste einen Verweis auf `Agenten/Handel/orb/SPEC.md §107` (neun
Sperren). `related`-Frontmatter um `20260908-orb-handel` ergänzen. **Edit**, nicht
Rewrite.

- [ ] **Step 3: `Routinen.md` — die neue Aufgabe**

Eintrag `MaxHirn-ORB-Papier` (alle 15 Min, Session-Fenster-Filter im Skript,
`orb-papier.ps1`) und der Hinweis, dass `MaxHirn-Handel-Wachen` jetzt auch
`orb --wachen` fährt.

- [ ] **Step 4: `INDEX.md` — Registry-Zeile**

In der Sektion „Handel" (bei den anderen `20260901-…`-Einträgen) eine Zeile:
```
- `20260908-orb-handel` — **ORB Index-CFD auf OANDA** — `Wissen/ORB-Handel.md` — Opening-Range-Breakout als vierte bewachte Spur: Backtest-Urteil zur „81 %"-Behauptung, Fallen, Sperren, Stand.
```

- [ ] **Step 5: `Agenten/Handel/README.md` — Absatz „Spur 4"**

Kurzer Absatz mit den Aufrufen:
```
..\scanner\.venv\Scripts\python.exe orb\handeln.py --vorschau
..\scanner\.venv\Scripts\python.exe orb\handeln.py --papier
..\scanner\.venv\Scripts\python.exe orb\backtest.py --jahre 2 --raster
..\scanner\.venv\Scripts\python.exe orb\handeln.py --wachen
```

- [ ] **Step 6: `wissen-index-pruefen` gegenprüfen**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\wissen-index-pruefen.ps1`
Erwartung: keine neue Meldung über fehlende Registry-Einträge oder tote `[[Wikilinks]]`. Falls doch — beheben, bevor committet wird.

- [ ] **Step 7: Commit**

```bash
git add MaxHirn/Wissen/ORB-Handel.md MaxHirn/Wissen/Handelsregeln.md MaxHirn/Wissen/Routinen.md MaxHirn/Wissen/INDEX.md Agenten/Handel/README.md
git commit -m "Wissen: Spur 4 (ORB Index-CFD) - Notiz, Handelsregeln, Routinen, Index

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 15: `orb/README.md` — tritt an die Stelle von `SPEC.md`

**Files:**
- Create: `Agenten/Handel/orb/README.md`
- `Agenten/Handel/orb/SPEC.md` bleibt unverändert liegen (Beleg der Entwurfsentscheidungen, SPEC.md §3).

**Interfaces:** keine.

- [ ] **Step 1: `README.md` schreiben** (Muster `kraken/README.md`)

Abschnitte: Zweck (Spur 4, ORB, OANDA, EUR) · **Warum das nicht der OANDA-Zugang allein ist** (Tabelle wie kraken: Grenzen in einer Datei, Pflicht-Stop/Kill-Switch, Journal/Herzschlag, Scharfschalten von Hand, Order erlaubt) · Dateien (Tabelle) · Aufrufe · **Backtest-Urteil** (Verweis auf `[[ORB-Handel]]`, keine Zahlen hier) · die neun Sperren (Verweis auf `SPEC.md §107`) · Fallen (Verweis) · Stand.

- [ ] **Step 2: Gesamte Test-Suite ein letztes Mal**

Run (aus `orb/`): `..\scanner\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Run (aus `Agenten/Handel/`): `scanner\.venv\Scripts\python.exe -m unittest tests_orb_freigabe -v`
Erwartung: alles PASS.

- [ ] **Step 3: `git status` — kein Rauschen**

Run: `git status --porcelain`
Erwartung: nur `?? Agenten/Handel/orb/README.md`. `orb/zustand.json`, `orb/handelsjournal.csv`, `orb/daten/`, `orb/tests/_tmp_cache/` tauchen **nicht** auf (gitignore bzw. außerhalb Whitelist).

- [ ] **Step 4: Commit**

```bash
git add Agenten/Handel/orb/README.md
git commit -m "Spur 4 (ORB): README loest SPEC.md als Betriebsdoku ab"
```

---

## Self-Review

**1. Spec-Abdeckung** (SPEC.md-Abschnitte → Task):

| Spec-Abschnitt | Task |
|---|---|
| Die Strategie, exakt (§23) | Task 5 (Regelengine), Task 10 (live) |
| Mehrdeutigkeit → Stop (§37) | Task 5, `test_stop_vor_ziel_gleiche_kerze_ist_stop` |
| Ordnerinhalt (§40) | Task 0 (wachen.json), 1 (session), 2–4 (oanda), 5–6 (backtest), 8 (wachen_orb), 9–11 (handeln), 15 (README) |
| backtest.py: ≥1 Jahr, Pagination, Cache (§64) | Task 3 (Pagination/Cache), Task 6 (`--jahre 2`) |
| Zwei Einstiegsmodelle, Spanne (§70) | Task 5 (`einstiegsmodell`), Task 6 (`--modell beide`) |
| `--raster` über TP (§74) | Task 6 (`--raster`) |
| Bericht-Kennzahlen + Pflichtquellen (§76–85) | Task 6 (`bericht`) |
| Kostenmodell Spread + Slippage (§87) | Task 6 (`mit_kosten`), Task 7 (Eichung) |
| Abschlussurteil je Instrument (§93) | Task 6 (`urteil`/`haelt_81`), Task 7 (festhalten) |
| handeln.py Modi + Zyklusreihenfolge (§97–102) | Task 9 (Ausstiege/`--wachen`), Task 10 (Einstieg/Zyklus), Task 11 (`--live`) |
| Ausstiege nie durch Freigabefenster (§104) | Task 9 (`pruefe_ausstiege` ohne Freigabe), Task 11 (Freigabe nur vor Einstieg) |
| Neun Sperren (§107) | Task 11 (`live_sperren`) |
| `wachen.json`-Felder (§132) | Task 0 |
| Fehlerbehandlung & Fallen (§154) | complete:false Task 3; DST Task 1; 401 Task 2; Gap/letzter_einstieg Task 5/10; Rundung Task 10 (`positionsgroesse`/`markt_order`); Slippage Task 10; Spread im Journal Task 9/10; DE30-Zugang Task 4 |
| Routine (§173) | Task 13 |
| Änderungen außerhalb (§183) | `.gitignore` Task 0; `freigabe.py` Task 12; `Handelsregeln/Routinen/INDEX/ORB-Handel/Handel-README` Task 14 |
| YAGNI (§195) | im Plan nichts davon gebaut (kein Overnight, keine Pyramidisierung, ein Trade/Session, drei Indizes, kein Feiertagskalender, keine Range-Rasteroptimierung) |
| Reihenfolge der Umsetzung (§203) | Tasks 2–4 → 1 → 5–6 → 7 → 8 → 9–10 → 11–12 → 13–14; deckt sich (session.py ist Task 1, weil backtest.py es braucht — Vorziehen ohne Konflikt) |

Keine Lücke.

**2. Platzhalter-Scan:** Ein bewusster, markierter Platzhalter — der `print("Zyklus kommt in Task 10/11.")` in Task 9 Step 3, in Task 10 Step 3 vollständig ersetzt. Sonst keine „TBD"/„TODO"/„analog zu Task N ohne Code". Boilerplate, das `kraken/*` spiegelt, ist mit Datei + Zeilen benannt und der abweichende Teil ausgeschrieben.

**3. Typkonsistenz:**
- Kerze-Dict `{"zeit","o","h","l","c","complete"}` — einheitlich Task 3, 5, 10.
- Ergebnis-Dict aus `simuliere_session` — Schlüssel identisch in Task 5 (Definition), Task 6 (`bericht`/`mit_kosten` lesen `gv_punkte`, `mehrdeutig`, `tag`).
- Position-Dict `{"inst","richtung","einstieg","stop","ziel","units","risiko_eur","eroeffnet","order_id"}` — Task 9 (Definition), Task 10 (`pruefe_einstieg` schreibt), Task 11 (`hole_freigabe` liest `risiko_eur`).
- Journal-Kopf `["zeit","modus","aktion","inst","richtung","preis","eur","units","stop","ziel","grund"]` — Task 9 (`journal`), Task 8 (`runden_aus_journal` liest `inst`, `eur`, `aktion` ∈ {`einstieg`,`ausstieg`}), Task 10 (`_schon_gehandelt_heute` liest `aktion`/`inst`/`zeit`).
- `wachen_orb.lage`-Schlüssel (`freigabe_voll`, `ev_negativ`, `herzschlag_frisch`, `ruecklauf_eur`, `groessenfaktor`, `kill`) — Task 8 (Definition), Task 9 (`zeige_wachen`), Task 11 (`live_sperren`).
- `oanda`-Signaturen: `kerzen(oanda_inst, *, von, bis, granularity, cache_dir, live)` einheitlich Task 3/6/10; `markt_order(oanda_inst, units, *, echt, live)` Task 9 (Definition) / Task 10 (Aufruf).
- `session`-Funktionen geben durchgehend tz-aware UTC zurück; `in_session` erwartet tz-aware `moment` — Task 1 (Definition), Task 9/10/13 (Aufrufer übergeben `datetime.now(timezone.utc)`).

Keine Inkonsistenz gefunden.

**4. Scope:** Ein Subsystem (eine Handelsspur), ein Plan. Der Backtest-Ausgang (Task 7) ist die einzige Weggabelung — bei „Nein für alle Instrumente" endet der Plan früh und nachvollziehbar, mit Rückfrage an Max.

---

## Execution Handoff

**Plan complete and saved to `Werkstatt/plan-spur4-orb-oanda-2026-09-08.md`.**

Nächster Schritt getrennt: **brainstorming** für Verbesserer Ausbaustufe 2 (Spur 2/3) + F4/F7, dann ein eigener Plan dafür.

Zwei Ausführungsoptionen für diesen Plan:

1. **Subagent-Driven (empfohlen)** — pro Task ein frischer Subagent, Review zwischen den Tasks, schnelle Iteration. (`superpowers:subagent-driven-development`)
2. **Inline** — Tasks in dieser Sitzung abarbeiten, Checkpoints zum Review. (`superpowers:executing-plans`)

**Welche?**
