# Leitstand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Stand: 3d70c36 vom 29.09.2026

**Goal:** Ein Tk-Fenster `leitstand.py` mit vier Reitern (Überwachen, Freigaben, Backtests, Markt), aus dem Max überwacht, Freigaben beantwortet, Backtests, Optimierung und Urteile fährt — ohne je live zu handeln.

**Architecture:** `leitstand.py` ist die Tk-Wurzel mit einem `ttk.Notebook`. Die Handelszentrale wird unverändert als Reiter eingehängt. Die übrigen Reiter sind je eine Klasse in einem eigenen Modul mit derselben kleinen Schnittstelle (`refresh`, `titel_zusatz`, `status`). Geschrieben wird nur an drei eng umrissenen Stellen:
- über `freigabefenster.*`, künftig mit Dateisperre;
- in die Ablage `backtest_laeufe/` des Leitstands;
- über `backtest_urteile.py --aus-vorschau`, und nur nach Bestätigung.

**Tech Stack:** Python 3 (Interpreter `scanner/.venv`), tkinter/ttk, unittest, subprocess, ctypes (Windows: `FlashWindowEx`, `GetSystemMetrics`).

**Spec:** `Agenten/Handel/docs/design/2026-09-29-leitstand-design.md` (Spezifikation) — die Umsetzung liest beide Dateien.

## Global Constraints

- **Nie live handeln.** Kein Modul des Leitstands importiert einen Börsen-Client oder ruft eine Order-Funktion auf.
- **Nie in eine `wachen.json` schreiben.** Einzige Ausnahme ist `backtest_urteile.py --aus-vorschau`, und nur nach dem Bestätigungsdialog.
- Tkinter-Fenster, kein Server, kein offener Port.
- `test_handelszentrale_rein_lesend.py` bleibt unverändert grün; `python handelszentrale.py` funktioniert allein wie bisher.
- Bestehende Aufrufe von `freigabefenster.*` und `backtest_urteile.py` behalten ihr Verhalten.
- Freigabe-Dialog und Urteils-Dialog: **120 s ohne Bedienung → schließen, nichts schreiben.** Esc = Abbrechen, schreibt nichts.
- Notaus, Freigeben und Urteile eintragen haben **kein** Tastenkürzel.
- Höchstens **ein** Lauf gleichzeitig; Läufe mit `BELOW_NORMAL_PRIORITY_CLASS`, Arbeitsordner `Agenten/Handel`.
- Replay-Läufe bekommen `--lauf leitstand-<JJJJMMTT-hhmmss>`.
- Ablage: `backtest_laeufe/<JJJJMMTT-hhmmss>-<name>.json`, Ausgabe auf 1 MB gekürzt.
- Zustandsdatei `leitstand_zustand.json`: höchstens alle 5 s geschrieben, atomar über `.tmp` + `os.replace`.
- Jede Dateilesung fängt `OSError` und `ValueError` ab und zeigt „nicht lesbar“.
- Sperre `freigabe_fenster.json.lock`: höchstens 5 s warten, danach `TimeoutError`; verwaist ab 30 s.
- Vorschau der Urteile gilt 60 Minuten.
- Alterswarnung des Marktberichts ab 26 h.
- Keine absoluten Pfade. Zahlen gehören in JSON-Dateien. Versionierte Dateien nie per Rewrite neu schreiben (LF/CRLF): gezielt ersetzen und den Diff ansehen.
- Tests arbeiten nur mit temporären Dateien: keine echte `freigabe_fenster.json`, kein echtes `daten/backtest/`, kein Netz.
- Commit-Nachrichten enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Notaus bei belegter Sperre:** Der Notaus fängt `TimeoutError` ab und meldet „Sperre belegt — bitte erneut“. Er darf nicht abstürzen und nicht still „erledigt“ melden. Test in Aufgabe 5 (`test_notaus_bei_belegter_sperre_meldet_und_schreibt_nichts`).
2. **Abbruch mit Kindprozessen:** `backtest_urteile.py` startet seine Motoren als Kindprozesse. Ein Abbruch muss den ganzen Prozessbaum beenden, sonst rechnet ein Motor 15 min weiter. Test in Aufgabe 6 (`test_abbruch_beendet_auch_kindprozesse`).
3. **Vorschau veraltet zwischen Rechnen und Eintragen:** Hat sich die `wachen.json` inzwischen geändert (Hash) oder ist die Vorschau älter als 60 min, wird nichts geschrieben. Das gilt auch, wenn die Vorschau-Datei in der Zukunft datiert ist. Test in Aufgabe 10 (`test_zukunftsstand_wird_abgelehnt`).
4. **Unlesbare Eingabedateien:** Zustandsdatei, Marktbericht, `optimierung.json` und Lauf-Ablage können kaputt sein. Der Leitstand startet trotzdem und zeigt „nicht lesbar“. Tests in Aufgabe 4, 7, 9 und 12.
5. **Windows-`PermissionError` bei `os.replace`:** Ein Leser hält die Zieldatei offen. `_schreib` wiederholt den Versuch, statt die Freigabe zu verlieren. Test in Aufgabe 2 (`test_replace_wiederholt_bei_permissionerror`).

---

## Befund zu den offenen Punkten der Spezifikation

Stand: 3d70c36 vom 29.09.2026

1. **`SPUREN_TEIL_B` über die Kommandozeile: nein.** `replay.main()` (replay.py:570–603) ruft immer `lauf_a(...)` auf und liest die Wachen über `spur_modul(spur).lade_wachen()`. Familie B läuft über `spur_buch`, einen Kommandozeilenweg dafür gibt es nicht.
   - Angeboten werden deshalb nur die Spuren aus `SPUREN_TEIL_A` (replay.py:37).
   - Ausgegraut und mit Grund erscheinen die Schlüssel von `NICHT_NACHRECHENBAR` (replay.py:48).
   - `SPUREN_TEIL_B` bleibt draußen.
2. **Einzelskripte, Nachweis der Aufnahmebedingung.** Die Suche nach `create_order|place_order|order_aufgeben|.order(|api_key|secret|private_key|ccxt.<x>({` ergab in allen fünf Kandidaten keinen Treffer.

   | Skript | schreibt | liest ein Betriebsteil das? | Entscheidung |
   |---|---|---|---|
   | `gitter/backtest_gitter.py` | nichts | — | aufgenommen |
   | `orb/backtest.py` | Kerzen-Zwischenspeicher `orb/daten/<inst>_M15.json` (Z. 238) | nein: `_M15` kommt nur in `orb/backtest.py` und `orbk/backtest.py` vor | aufgenommen |
   | `orbk/backtest.py` | `orbk/daten/<inst>_M15.json` (Z. 255) | nein, wie oben | aufgenommen |
   | `backtest_prognose.py` | `daten/backtest_kerzen/*.json` (Z. 77–110); `--json` schreibt frei | nein: `backtest_kerzen` kommt nur in `backtest_prognose.py` und `bt_opt/4h_gegenprobe.py` vor | aufgenommen, **ohne** `--json` |
   | `bt_varianten_fast.py` | nur mit `--json` (Z. 323) | — | aufgenommen, ohne Felder |
   | `nautilus/backtest.py` | `backtest_ergebnis.json` | wird von `backtest_urteile.urteil_nautilus` gelesen; braucht `nautilus/.venv` | **nicht** aufgenommen |
   | `iv_waelle/backtest_iv_waelle.py` | `backtest_ergebnis.json` | steht in `NICHT_NACHRECHENBAR` (keine Strike-OI-Historie) | **nicht** aufgenommen |

   Ob die Liste diese Bedingung weiter erfüllt, prüft `test_leitstand_backtests_liste.py` bei jedem Lauf (Aufgabe 8).
3. **Spiegelung:** `freigabe_fenster.json` steht weder in `spiegelstand.py` noch in einem `journal_zweitziel`. Die Suche nach `freigabe_fenster` in `spiegelstand.py` und `dauerlauf.py` fand keine Spiegelstelle. `.lock` und `.tmp` laufen also nirgends mit. `spiegelstand.py` läuft in Aufgabe 14 trotzdem als Nachweis.
4. **Interpreter der Urteile:** `backtest_urteile.py` startet seine Motoren mit `PY_SCANNER` und `PY_NAUTILUS`. Der Leitstand ruft es deshalb mit `str(backtest_urteile.PY_SCANNER)` auf, nicht mit `sys.executable`.

## Abweichungen von der Spezifikation (begründet)

- **Mehr Module als in der Spezifikation.** Die Spezifikation nennt `leitstand_backtests.py` als einen Reiter. Der Plan teilt ihn in vier Module:
  - `leitstand_laeufe.py`: Prozess, Ablage, Liste, Vergleich;
  - `leitstand_optimieren.py`;
  - `leitstand_urteile.py`;
  - `leitstand_backtests.py`: der Reiter selbst mit Replay und Einzelskripten.

  Grund: Jede Datei bleibt so im Kopf zu halten und einzeln testbar. Die Urteile, der einzige Weg in eine `wachen.json`, liegen dann in einer eigenen Datei mit eigenem Review.
- **Abbrechen per `taskkill /T /F`** statt nur `terminate()` und nach 5 s `kill()`. `terminate()` beendet unter Windows nur den direkten Prozess. Die Motoren von `backtest_urteile.py` liefen weiter (Review Focus 2). Außerhalb von Windows bleibt es bei `terminate()` und nach 5 s `kill()`.
- **Kürzel-Prüfung in `test_leitstand.py`** statt in `test_leitstand_bedienung.py`. Ob Notaus, Freigeben oder Eintragen eine Taste haben, lässt sich erst am fertigen Fenster mit allen vier Reitern prüfen (Aufgabe 13).
- **Der Trockenlauf der Optimierung startet erst, wenn der Unterreiter „Optimieren“ sichtbar ist**, nicht schon beim Aufbau. Sonst rechnete jeder Start des Leitstands einen Plan (Aufgabe 9).

## Arbeitsort und Befehle

Alle Aufgaben laufen im Worktree `../Handel-leitstand` neben `BrainFiles/`. Die Befehle gelten, wenn nicht anders gesagt, aus `../Handel-leitstand/Agenten/Handel`.

```bash
PY=../../../BrainFiles/Agenten/Handel/scanner/.venv/Scripts/python.exe
```

Einzeltest: `$PY -m unittest tests.test_xyz -v`
Ganze Suite: `$PY -m unittest discover -s tests -p "test_*.py"`

Die ganze Suite läuft am Ende jeder Aufgabe. Sie muss so grün sein wie vorher: Tests, die schon im Hauptbaum rot waren, notiert Aufgabe 1 als Ausgangslage.

## Dateien

| Datei | Aufgabe | Verantwortung |
|---|---|---|
| `freigabefenster.py` (ändern) | 1, 2 | `grenzwerte()`, Sperre, atomares Schreiben |
| `handelszentrale.py` (ändern) | 3 | Fensterpflege nur, wenn das Elternteil ein `tk.Tk` ist |
| `leitstand_bedienung.py` (neu) | 4 | Sortieren, Filtern, TSV/CSV, Zustandsdatei, Tooltip, Tabelle, ZeitDialog, Fensterlage, Blinken |
| `leitstand_freigaben.py` (neu) | 5 | Freigaben-Reiter und Freigabe-Dialog |
| `leitstand_laeufe.py` (neu) | 6 | Laufsteuerung (ein Lauf, Abbruch, Ablage), Laufliste, Vergleich |
| `leitstand_backtests.py` (neu) | 7, 8, 9, 11 | Backtest-Reiter: Replay, Einzelskripte, Läufe; bindet Optimieren und Urteile ein |
| `leitstand_backtests.json` (neu) | 8 | geprüfte Liste der Einzelskripte |
| `.gitignore` der Repo-Wurzel (ändern) | 8 | eine Zeile `!Agenten/Handel/leitstand_backtests.json` |
| `leitstand_optimieren.py` (neu) | 9 | Bereich Optimieren |
| `backtest_urteile.py` (ändern) | 10 | `--vorschau-datei`, `--aus-vorschau` |
| `leitstand_urteile.py` (neu) | 11 | Bereich Urteile |
| `leitstand_markt.py` (neu) | 12 | Markt-Reiter, rein lesend |
| `tests/lesepruefung.py` (neu) | 9 | AST-Prüfung „schreibt nichts“ für neue Module |
| `leitstand.py` (neu) | 13 | Wurzel, Reiter, Takt, Kürzel, Statusleiste, Zustand |

Dazu je Aufgabe eine Testdatei unter `tests/`; welche, steht unter **Files** der Aufgabe. Aufgabe 12 hat zwei (`test_leitstand_markt.py`, `test_leitstand_markt_rein_lesend.py`), Aufgabe 13 eine (`test_leitstand.py`).

Nicht versioniert, also ohne Zeile in `.gitignore`: `backtest_laeufe/` und `leitstand_zustand.json`. Beide sind durch `*` in `.gitignore:20` ausgeschlossen; `git check-ignore` hat das bestätigt.

### Schnittstelle der Reiter (gilt für Aufgaben 5, 7, 12, 13)

```python
class XReiter(ttk.Frame):
    def __init__(self, eltern, leitstand): ...
    def refresh(self): ...            # liest neu; nur für den sichtbaren Reiter
    def titel_zusatz(self) -> str: ...  # "" oder z. B. " (2)"
    def status(self) -> str: ...        # "" oder Text für die Statusleiste
```

`leitstand` stellt bereit: `.root` (tk.Tk), `.zustand` (`leitstand_bedienung.Zustand`), `.melde(text: str)` (letzte Meldung in der Statusleiste). In Tests steht dafür ein Stub:

```python
class StubLeitstand:
    def __init__(self, root, zustand):
        self.root, self.zustand, self.meldungen = root, zustand, []
    def melde(self, text):
        self.meldungen.append(text)
```

---

### Task 1: Worktree und `freigabefenster.grenzwerte()`

**Files:**
- Modify: `Agenten/Handel/freigabefenster.py:272-291` (Wertetabelle in `anfrage_text`)
- Test: `Agenten/Handel/tests/test_freigabefenster_grenzwerte.py`

**Interfaces:**
- Consumes: —
- Produces: `freigabefenster.grenzwerte(w: dict, waehrung: str = "USD") -> list[tuple[str, str]]`, z. B. `[("je Anlauf", "50 USD"), ("Positionen", "3 ")]`. Der Wert ist `"%s %s" % (wert, einheit)`, bei leerer Einheit also mit nachgestelltem Leerzeichen; Anzeigen entfernen es mit `.strip()`.

- [ ] **Step 1: Worktree anlegen und Ausgangslage messen**

Aus `BrainFiles/`:

```bash
git status --short
git worktree add ../Handel-leitstand -b arbeit/leitstand master
```

Dann aus `../Handel-leitstand/Agenten/Handel`:

```bash
PY=../../../BrainFiles/Agenten/Handel/scanner/.venv/Scripts/python.exe
$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -5
```

Notiere die Zahl der Tests und der roten Tests als Ausgangslage. Am Ende jeder Aufgabe darf kein Test dazukommen, der rot ist.

- [ ] **Step 2: Den goldenen Test schreiben**

`tests/test_freigabefenster_grenzwerte.py`:

```python
"""anfrage_text() liefert nach dem Herausziehen von grenzwerte() denselben Text.

Die goldenen Texte stammen aus dem Code vor der Aenderung (Stand 3d70c36,
29.09.2026). anfrage_text liest keine Datei - kein Temp-Ordner noetig.

Direkt ausfuehrbar:  python tests/test_freigabefenster_grenzwerte.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import freigabefenster as ff                                   # noqa: E402

W_XPERP = {"max_pro_trade_usd": 50, "max_gesamt_usd": 200,
           "max_offene_positionen": 3, "max_hebel": 5,
           "kill_switch_gesamt_usd": 100}

GOLD_XPERP = (
    "<b>Freigabe xperp?</b>\n"
    "Dauer: 1:30 h\n"
    "\n"
    "Es gelten die Grenzen aus wachen.json:\n"
    "  je Anlauf          50 USD\n"
    "  gesamt             200 USD\n"
    "  Positionen         3 \n"
    "  Hebel bis          5 x\n"
    "  Kill-Switch        100 USD\n"
    "\n"
    "/ja        freigeben fuer 1:30 h\n"
    "/ja 6      stattdessen 6 Stunden\n"
    "/nein      ablehnen\n"
    "\n"
    "Ohne Antwort verfaellt die Anfrage in 30 Minuten.")

GOLD_KRAKEN = (
    "<b>Freigabe kraken?</b>\n"
    "Dauer: 1:00 h\n"
    "\n"
    "Es gelten die Grenzen aus wachen.json:\n"
    "  je Anlauf          25 EUR\n"
    "\n"
    "/ja        freigeben fuer 1:00 h\n"
    "/ja 6      stattdessen 6 Stunden\n"
    "/nein      ablehnen\n"
    "\n"
    "Ohne Antwort verfaellt die Anfrage in 30 Minuten.")


class AnfrageText(unittest.TestCase):
    def test_xperp_text_unveraendert(self):
        self.assertEqual(ff.anfrage_text("xperp", W_XPERP, 90, "USD"), GOLD_XPERP)

    def test_kraken_text_unveraendert(self):
        self.assertEqual(ff.anfrage_text("kraken", {"max_pro_trade_eur": 25},
                                         60, "EUR"), GOLD_KRAKEN)


class Grenzwerte(unittest.TestCase):
    def test_paare_in_fester_reihenfolge(self):
        self.assertEqual(ff.grenzwerte(W_XPERP, "USD"), [
            ("je Anlauf", "50 USD"), ("gesamt", "200 USD"),
            ("Positionen", "3 "), ("Hebel bis", "5 x"),
            ("Kill-Switch", "100 USD")])

    def test_fehlende_werte_fallen_weg(self):
        self.assertEqual(ff.grenzwerte({}, "USD"), [])

    def test_erster_vorhandener_name_gewinnt(self):
        w = {"max_margin_je_anlauf_usd": 7, "max_pro_trade_usd": 9}
        self.assertEqual(ff.grenzwerte(w, "USD")[0], ("je Anlauf", "9 USD"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Test laufen lassen — er muss scheitern**

Run: `$PY -m unittest tests.test_freigabefenster_grenzwerte -v`
Erwartet: die beiden `AnfrageText`-Tests grün, die drei `Grenzwerte`-Tests mit `AttributeError: module 'freigabefenster' has no attribute 'grenzwerte'`.

- [ ] **Step 4: `grenzwerte()` herausziehen**

In `freigabefenster.py` direkt **vor** `def anfrage_text` einfügen:

```python
def grenzwerte(w, waehrung="USD"):
    """Die Grenzen aus wachen.json als (Bezeichnung, Wert mit Einheit).

    anfrage_text() (Telegram) und der Freigabe-Dialog des Leitstands zeigen
    dieselbe Liste - eine zweite Fassung waere eine zweite Wahrheit.
    """
    def w_(*namen):
        for n in namen:
            if n in w:
                return w[n]
        return None

    paare = [
        ("je Anlauf", w_("max_pro_trade_eur", "max_pro_trade_usd",
                         "max_margin_je_anlauf_usd"), waehrung),
        ("gesamt", w_("max_gesamt_eur", "max_gesamt_usd",
                      "max_margin_gesamt_usd"), waehrung),
        ("Positionen", w_("max_offene_positionen", "max_offene_anlaeufe"), ""),
        ("Hebel bis", w_("max_hebel"), "x"),
        ("Risiko je Anlauf", w_("risiko_je_anlauf_usd"), waehrung),
        ("Kill-Switch", w_("kill_switch_gesamt_usd"), waehrung),
    ]
    return [(name, "%s %s" % (wert, einheit))
            for name, wert, einheit in paare if wert is not None]
```

In `anfrage_text` den Block von `def w_(*namen):` bis einschließlich der Schleife `for name, wert, einheit in paare: ...` (heute Z. 273–291) **gezielt ersetzen** (Edit, kein Rewrite) durch:

```python
    for name, wert in grenzwerte(w, waehrung):
        z.append("  %-18s %s" % (name, wert))
```

- [ ] **Step 5: Tests laufen lassen**

Run: `$PY -m unittest tests.test_freigabefenster_grenzwerte tests.test_telegram_freigabe -v`
Erwartet: alle grün.

Run: `git diff --stat` — nur `freigabefenster.py` geändert; `git diff freigabefenster.py` zeigt keine Zeilenende-Änderung außerhalb des Blocks.

- [ ] **Step 6: Commit**

```bash
git status --short
git add Agenten/Handel/freigabefenster.py Agenten/Handel/tests/test_freigabefenster_grenzwerte.py
git commit -m "freigabefenster: grenzwerte() aus anfrage_text herausgezogen (Leitstand, Aufgabe 1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Sperre und atomares Schreiben in `freigabefenster.py`

**Files:**
- Modify: `Agenten/Handel/freigabefenster.py` (Imports; `_schreib` Z. 101–104; `anfrage_stellen`, `oeffnen`, `schliessen`, `alles_schliessen` Z. 204–260)
- Test: `Agenten/Handel/tests/test_freigabefenster_sperre.py`

**Interfaces:**
- Consumes: —
- Produces: `schliessen`, `alles_schliessen`, `anfrage_stellen` und `oeffnen` behalten Signatur und Rückgabe. Neu: Alle vier können `TimeoutError` werfen, wenn die Sperre länger als `SPERRE_WARTEN_S` belegt ist. Konstanten `SPERRE_WARTEN_S = 5.0`, `SPERRE_VERWAIST_S = 30.0`. `alles_schliessen(grund) -> list[str]` gibt wie bisher die Spuren zurück, die offen waren.

- [ ] **Step 1: Tests schreiben**

`tests/test_freigabefenster_sperre.py`:

```python
"""Zwei Schreiber auf freigabe_fenster.json: Dauerlauf und Leitstand.

Geprueft: kein verlorener Eintrag bei parallelem Schreiben, belegte Sperre ->
TimeoutError ohne Schreiben, verwaiste Sperre wird entfernt, keine .tmp/.lock
bleibt liegen, os.replace wird bei PermissionError (Windows) wiederholt.
Gearbeitet wird in einem Temp-Ordner (DATEI wird umgebogen).

Direkt ausfuehrbar:  python tests/test_freigabefenster_sperre.py
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import freigabefenster as ff                                   # noqa: E402


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(ff, "DATEI",
                         os.path.join(self.tmp.name, "freigabe_fenster.json"))
        p.start()
        self.addCleanup(p.stop)

    def _inhalt(self):
        with open(ff.DATEI, encoding="utf-8") as f:
            return json.load(f)


class Sperre(Basis):
    def test_belegte_sperre_wirft_timeout_und_schreibt_nichts(self):
        ff.anfrage_stellen("xperp", 60)
        vorher = self._inhalt()
        open(ff.DATEI + ".lock", "w").close()
        with patch.object(ff, "SPERRE_WARTEN_S", 0.2):
            with self.assertRaises(TimeoutError):
                ff.schliessen("xperp", "Test")
        self.assertEqual(self._inhalt(), vorher)

    def test_verwaiste_sperre_wird_entfernt(self):
        sperre = ff.DATEI + ".lock"
        open(sperre, "w").close()
        alt = time.time() - 60
        os.utime(sperre, (alt, alt))
        ff.schliessen("xperp", "Test")
        self.assertFalse(os.path.exists(sperre))
        self.assertEqual(self._inhalt()["xperp"]["schliess_grund"], "Test")

    def test_parallele_schreiber_verlieren_nichts(self):
        def schreiber(praefix):
            for i in range(25):
                ff.anfrage_stellen("%s%d" % (praefix, i), 60)
        faeden = [threading.Thread(target=schreiber, args=(p,))
                  for p in ("a", "b")]
        for t in faeden:
            t.start()
        for t in faeden:
            t.join(30)
        self.assertEqual(len(self._inhalt()), 50)

    def test_keine_tmp_und_keine_sperre_bleibt_liegen(self):
        ff.anfrage_stellen("xperp", 60)
        ff.oeffnen("xperp", 2, wer="test")
        ff.alles_schliessen("Test")
        self.assertEqual(sorted(os.listdir(self.tmp.name)),
                         ["freigabe_fenster.json"])

    def test_replace_wiederholt_bei_permissionerror(self):
        echt = os.replace
        fehler = [PermissionError("belegt"), PermissionError("belegt")]

        def ersatz(a, b):
            if fehler:
                raise fehler.pop(0)
            return echt(a, b)

        with patch.object(ff.os, "replace", side_effect=ersatz):
            ff.anfrage_stellen("xperp", 60)
        self.assertIn("xperp", self._inhalt())
        self.assertEqual(fehler, [])


class Verhalten(Basis):
    def test_alles_schliessen_meldet_nur_offene(self):
        ff.anfrage_stellen("a", 60)
        ff.oeffnen("a", 1, wer="test")
        ff.anfrage_stellen("b", 60)
        self.assertEqual(ff.alles_schliessen("Test"), ["a"])
        d = self._inhalt()
        self.assertEqual(d["b"]["schliess_grund"], "Test")
        self.assertNotIn("anfrage_bis", d["b"])
        self.assertNotIn("offen_bis", d["a"])

    def test_alles_schliessen_ohne_datei_schreibt_nichts(self):
        self.assertEqual(ff.alles_schliessen("Test"), [])
        self.assertFalse(os.path.exists(ff.DATEI))

    def test_oeffnen_ohne_anfrage_bleibt_none(self):
        self.assertIsNone(ff.oeffnen("xperp", 2, wer="test"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Tests laufen lassen — sie müssen scheitern**

Run: `$PY -m unittest tests.test_freigabefenster_sperre -v`
Erwartet:
- FAIL bei `test_belegte_sperre_…` (kein `TimeoutError`) und `test_verwaiste_sperre_…` (die Sperrdatei bleibt).
- `test_parallele_…` und `test_replace_…` können schon jetzt zufällig grün sein. `test_replace_…` wird erst mit dem neuen `_schreib` aussagekräftig.

- [ ] **Step 3: Sperre und atomares Schreiben einbauen**

Imports ergänzen: `import contextlib` und `import time`, alphabetisch in die bestehende Importzeile bzw. -liste einsortiert. Nach `WIEDERVORLAGE_NACH_ABLEHNUNG_STUNDEN`/`ABLEHNUNGSGRUENDE` einfügen:

```python
# Zwei Schreiber (Dauerlauf, Leitstand): jede Lesen-Aendern-Schreiben-Folge
# laeuft unter einer Dateisperre neben DATEI.
SPERRE_WARTEN_S = 5.0
SPERRE_VERWAIST_S = 30.0


@contextlib.contextmanager
def _gesperrt():
    """Exklusiv lesen-aendern-schreiben. Sperre = DATEI.lock (O_CREAT|O_EXCL).

    Wer sie nicht bekommt, wartet hoechstens SPERRE_WARTEN_S und bekommt dann
    TimeoutError - geschrieben wird dann nichts. Eine Sperre, die aelter als
    SPERRE_VERWAIST_S ist, stammt von einem abgestuerzten Prozess und wird
    entfernt.
    """
    sperre = DATEI + ".lock"
    frist = time.monotonic() + SPERRE_WARTEN_S
    while True:
        try:
            fd = os.open(sperre, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except (FileExistsError, PermissionError):
            # PermissionError: Windows, die Sperre wird gerade geloescht.
            try:
                if time.time() - os.path.getmtime(sperre) > SPERRE_VERWAIST_S:
                    os.remove(sperre)
                    continue
            except OSError:
                pass
            if time.monotonic() >= frist:
                raise TimeoutError("Sperre %s belegt" % sperre)
            time.sleep(0.02)
    try:
        try:
            os.write(fd, str(os.getpid()).encode("ascii"))
        finally:
            os.close(fd)
        yield
    finally:
        try:
            os.remove(sperre)
        except OSError:
            pass
```

`_schreib` gezielt ersetzen durch:

```python
def _schreib(d):
    """Atomar: erst DATEI.tmp, dann os.replace - kein Leser sieht eine halbe Datei."""
    tmp = DATEI + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")
    for versuch in range(20):
        try:
            os.replace(tmp, DATEI)
            return
        except PermissionError:
            # Windows: ein Leser haelt DATEI gerade offen.
            if versuch == 19:
                raise
            time.sleep(0.05)
```

`anfrage_stellen` und `oeffnen`: Den Rumpf ab `d = _lies()` jeweils in `with _gesperrt():` einrücken. Die `return`-Anweisungen dürfen im Block bleiben. `anfrage_stellen` sieht danach so aus:

```python
def anfrage_stellen(spur, dauer_minuten):
    """Merkt eine wartende Anfrage vor. Oeffnet noch nichts."""
    with _gesperrt():
        d = _lies()
        e = d.setdefault(spur, {})
        e["anfrage_bis"] = (_jetzt() + dt.timedelta(
            minutes=ANTWORT_FRIST_MINUTEN)).isoformat()
        e["anfrage_dauer_minuten"] = min(dauer_minuten, MAX_STUNDEN * 60)
        e["anfrage_gestellt"] = _jetzt().isoformat()
        _schreib(d)
        return e["anfrage_dauer_minuten"]
```

`schliessen` und `alles_schliessen` ersetzen durch (eine Sperre, ein Schreiben; `alles_schliessen` ruft **nicht** `schliessen` auf, sonst sperrt es sich selbst):

```python
def _schliesse_in(d, spur, grund):
    """Eine Spur in d auf Papier setzen. Ohne Sperre, ohne Schreiben."""
    e = d.setdefault(spur, {})
    war = Fenster(spur, dict(e)).offen()
    e.pop("offen_bis", None)
    e.pop("anfrage_bis", None)
    e["zuletzt_geschlossen"] = _jetzt().isoformat()
    e["schliess_grund"] = grund
    return war


def schliessen(spur, grund="von Hand"):
    """Sofort zurueck auf Papier. Geht immer, ohne Anfrage, ohne Frist."""
    with _gesperrt():
        d = _lies()
        war = _schliesse_in(d, spur, grund)
        _schreib(d)
    return war


def alles_schliessen(grund="Notaus"):
    """Jede Spur zurueck auf Papier - eine Sperre, ein Schreiben."""
    with _gesperrt():
        d = _lies()
        if not d:
            return []
        offen = [s for s in list(d) if _schliesse_in(d, s, grund)]
        _schreib(d)
    return offen
```

- [ ] **Step 4: Tests laufen lassen**

Run: `$PY -m unittest tests.test_freigabefenster_sperre tests.test_freigabefenster_grenzwerte tests.test_freigabefenster_zeitvergleich tests.test_telegram_freigabe -v`
Erwartet: alle grün.

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3` — Ausgangslage aus Aufgabe 1 unverändert.

- [ ] **Step 5: Commit**

```bash
git status --short
git add Agenten/Handel/freigabefenster.py Agenten/Handel/tests/test_freigabefenster_sperre.py
git commit -m "freigabefenster: Dateisperre und atomares Schreiben fuer zwei Schreiber (Leitstand, Aufgabe 2)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Handelszentrale als Rahmen

**Files:**
- Modify: `Agenten/Handel/handelszentrale.py:590-597` (Ende von `Handelszentrale.__init__`)
- Test: `Agenten/Handel/tests/test_handelszentrale_als_rahmen.py`

**Interfaces:**
- Consumes: —
- Produces: `handelszentrale.Handelszentrale(eltern)` nimmt jedes Tk-Widget. Titel, `configure(bg)`, `geometry`, `minsize` und `_buero_im_bild()` nur, wenn `isinstance(eltern, tk.Tk)`. Von außen genutzt (Aufgabe 13):
  - Modul: `SCHRIFT_GROESSE`, `RISIKO`, `FARBEN`, `dauerlauf_dateien() -> (pid_pfad, log_pfad)`, `dauerlauf_stand(pfad, jetzt) -> (text|None, minuten|None)`, `prozess_lebt(pid) -> bool|None`.
  - Instanz: `.w_schrift` (Combobox), `._schrift_gewaehlt()`.

- [ ] **Step 1: Test schreiben**

`tests/test_handelszentrale_als_rahmen.py`:

```python
"""Die Handelszentrale baut sich in einem Frame auf (Leitstand-Reiter) und
setzt allein gestartet weiter Titel und Mindestgroesse.

refresh() und _buero_im_bild() werden ersetzt: refresh startet Kurs-Threads
(Netz), _buero_im_bild verschiebt das Fenster. Ohne Bildschirm wird der Test
uebersprungen.

Direkt ausfuehrbar:  python tests/test_handelszentrale_als_rahmen.py
"""

import sys
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import handelszentrale as hz                                   # noqa: E402


class Rahmen(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.ersetzt = {}
        for name in ("refresh", "_buero_im_bild"):
            p = patch.object(hz.Handelszentrale, name, autospec=True)
            self.ersetzt[name] = p.start()
            self.addCleanup(p.stop)

    def test_im_rahmen_bleibt_das_fenster_unberuehrt(self):
        self.root.title("Leitstand")
        rahmen = ttk.Frame(self.root)
        hz.Handelszentrale(rahmen)
        self.assertEqual(self.root.title(), "Leitstand")
        self.assertTrue(rahmen.winfo_children())
        self.ersetzt["_buero_im_bild"].assert_not_called()
        self.ersetzt["refresh"].assert_called_once()

    def test_allein_setzt_sie_titel_und_mindestgroesse(self):
        hz.Handelszentrale(self.root)
        self.assertTrue(self.root.title().startswith("Handelszentrale"))
        self.assertEqual(self.root.minsize(), (1000, 640))
        self.ersetzt["_buero_im_bild"].assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen lassen — er muss scheitern**

Run: `$PY -m unittest tests.test_handelszentrale_als_rahmen -v`
Erwartet: `test_im_rahmen_…` ERROR mit `AttributeError: 'Frame' object has no attribute 'title'`; der zweite Test grün.

- [ ] **Step 3: Fensterpflege nur für `tk.Tk`**

Im `__init__` von `root.title(` bis `self._buero_im_bild()` gezielt ersetzen durch:

```python
        if isinstance(root, tk.Tk):
            # Allein gestartet gehoert das Fenster der Zentrale; als Reiter
            # im Leitstand gehoeren Titel, Groesse und Lage dem Leitstand.
            root.title("Handelszentrale — %d Spuren (Papier, nur lesend)"
                       % len(SPUREN))
            root.configure(bg=FARBEN["bg"])
            root.geometry("1280x860")
            root.minsize(1000, 640)
        self._baue()
        if isinstance(root, tk.Tk):
            self._buero_im_bild()
```

`self.refresh()` und `root.after(REFRESH_MS, self._planer)` bleiben unverändert dahinter.

- [ ] **Step 4: Tests laufen lassen**

Run: `$PY -m unittest tests.test_handelszentrale_als_rahmen tests.test_handelszentrale_rein_lesend tests.test_handelszentrale_bindung -v`
Erwartet: alle grün. `rein_lesend` ist unverändert, weil keine neue Schreibstelle und kein neuer Import dazukommt.

Run: `$PY handelszentrale.py --pruefen` — gibt wie bisher die Zeilen aus. Im Worktree fehlen Daten, deshalb stehen dort Hinweise wie „nicht lesbar“; ein Absturz darf nicht vorkommen.

- [ ] **Step 5: Commit**

```bash
git status --short
git add Agenten/Handel/handelszentrale.py Agenten/Handel/tests/test_handelszentrale_als_rahmen.py
git commit -m "handelszentrale: laesst sich als Reiter in einen Frame einbauen (Leitstand, Aufgabe 3)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Gemeinsame Bausteine `leitstand_bedienung.py`

**Files:**
- Create: `Agenten/Handel/leitstand_bedienung.py`
- Test: `Agenten/Handel/tests/test_leitstand_bedienung.py`

**Interfaces:**
- Consumes: —
- Produces (von allen späteren Aufgaben benutzt):
  - `HIER: Path`, `ZUSTAND_DATEI: Path`, `SPEICHER_ABSTAND_S = 5.0`, `ZEITLIMIT_S = 120`
  - `sortier_schluessel(wert) -> tuple`: Zahlen und Texte wie „12,5 %“ oder „50 USD“ numerisch, alles andere als Text. Zahlen stehen vor Texten.
  - `passt(zeile, text) -> bool`: Jedes Wort des Filters muss irgendwo in der Zeile stehen, ohne Groß- und Kleinschreibung.
  - `sortiere(zeilen, spalte: int, umgekehrt: bool) -> list`
  - `als_tsv(spalten, zeilen) -> str`, `csv_schreiben(pfad, spalten, zeilen) -> None` (`;`, utf-8-sig)
  - `lage_gueltig(geometrie: str, schirm: tuple[int,int,int,int]) -> bool`, `virtueller_schirm(root) -> (x, y, b, h)`
  - `blinken(root) -> bool`
  - `class Zustand(pfad=ZUSTAND_DATEI, uhr=time.monotonic)`: `.daten`, `.get(k)`, `.merke(k, v)`, `.merke_in(k, schluessel, v)`, `.speichern(sofort=False) -> bool`, `.nachholen() -> bool`. Die Schlüssel stehen in `VORGABEN`: `reiter` (int), `geometrie` (str), `schrift` (int, 0 = nicht gesetzt), `werte` (dict je Backtest-Art), `sortierung` (dict Tabellenname → `[spalte, umgekehrt]`).
  - `class Tooltip(widget, text="")`: `.setze(text)`
  - `setze_knopf(knopf: ttk.Button, tip: Tooltip, erlaubt: bool, grund: str) -> None`
  - `class Tabelle(ttk.Frame)(eltern, spalten, zustand, name, hoehe=10, auswahl="browse")`: `.baum`, `.w_filter`, `.setze(zeilen, tags=None)`, `.sichtbare() -> list[tuple]`, `.auswahl() -> list[tuple]`, `.sortiere_nach(spalte: str)`, `.sortierung -> (spalte, umgekehrt) | None`, `.kopieren() -> str`, `.csv_speichern()`
  - `class ZeitDialog(tk.Toplevel)(eltern, titel, zeitlimit_s=ZEITLIMIT_S, uhr=time.monotonic)`: `.inhalt` (Frame für Unterklassen), `.ergebnis`, `.rest_s()`, `._takt()`, `._bedient()`, `.fertig(wert)`, `.zeige_modal() -> ergebnis`. Das Ergebnis ist `"zeitablauf"` oder `"abgebrochen"`, oder was die Unterklasse an `fertig` übergibt.

- [ ] **Step 1: Tests schreiben**

`tests/test_leitstand_bedienung.py`:

```python
"""Bausteine des Leitstands: Sortieren, Filtern, Kopieren, Zustandsdatei,
Fensterlage, Zeit-Dialog, Tabelle.

Gearbeitet wird in einem Temp-Ordner. Die Tk-Teile werden ohne Bildschirm
uebersprungen. Die Uhr ist eine Liste, die der Test weiterstellt.

Direkt ausfuehrbar:  python tests/test_leitstand_bedienung.py
"""

import csv
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand_bedienung as lb                               # noqa: E402


class Uhr:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class Sortieren(unittest.TestCase):
    def test_zahlen_numerisch_nicht_als_text(self):
        zeilen = [("a", "10"), ("b", "9"), ("c", "-2,5 %"), ("d", "100 USD")]
        self.assertEqual([z[0] for z in lb.sortiere(zeilen, 1, False)],
                         ["c", "b", "a", "d"])

    def test_umgekehrt(self):
        zeilen = [("a", 1), ("b", 3), ("c", 2)]
        self.assertEqual([z[0] for z in lb.sortiere(zeilen, 1, True)],
                         ["b", "c", "a"])

    def test_datum_und_dauer_sind_text(self):
        self.assertEqual(lb.sortier_schluessel("2026-09-29")[0], 1)
        self.assertEqual(lb.sortier_schluessel("1:30 h")[0], 1)
        self.assertEqual(lb.sortier_schluessel(True)[0], 1)
        self.assertEqual(lb.sortier_schluessel(None), (1, 0.0, ""))

    def test_zahlen_vor_text(self):
        zeilen = [("a", "Papier"), ("b", "3")]
        self.assertEqual([z[0] for z in lb.sortiere(zeilen, 1, False)], ["b", "a"])


class Filtern(unittest.TestCase):
    def test_alle_woerter_muessen_vorkommen(self):
        z = ("xperp", "scharf, noch 1:00 h", "leitstand")
        self.assertTrue(lb.passt(z, ""))
        self.assertTrue(lb.passt(z, "XPERP scharf"))
        self.assertFalse(lb.passt(z, "xperp papier"))


class Kopieren(unittest.TestCase):
    def test_tsv_ohne_tab_und_umbruch_in_zellen(self):
        t = lb.als_tsv(("A", "B"), [("x\ty", "z\nw"), (1, 2.5)])
        self.assertEqual(t, "A\tB\nx y\tz w\n1\t2.5")

    def test_csv_rundreise(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.csv")
            lb.csv_schreiben(p, ("Spur", "Wert"), [("xperp", "1,5"), ("orb", 3)])
            with open(p, encoding="utf-8-sig", newline="") as f:
                self.assertEqual(list(csv.reader(f, delimiter=";")),
                                 [["Spur", "Wert"], ["xperp", "1,5"], ["orb", "3"]])


class Fensterlage(unittest.TestCase):
    SCHIRM = (0, 0, 1920, 1080)

    def test_sichtbar(self):
        self.assertTrue(lb.lage_gueltig("1280x860+80+60", self.SCHIRM))

    def test_rechts_ausserhalb(self):
        self.assertFalse(lb.lage_gueltig("1280x860+1900+60", self.SCHIRM))

    def test_titelleiste_unter_dem_schirm(self):
        self.assertFalse(lb.lage_gueltig("1280x860+80+1070", self.SCHIRM))

    def test_linker_zweitmonitor(self):
        self.assertTrue(lb.lage_gueltig("1280x860+-1800+40", (-1920, 0, 3840, 1080)))

    def test_unsinn(self):
        self.assertFalse(lb.lage_gueltig("", self.SCHIRM))
        self.assertFalse(lb.lage_gueltig("gross", self.SCHIRM))


class ZustandDatei(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = Path(self.tmp.name) / "leitstand_zustand.json"

    def test_rundreise(self):
        z = lb.Zustand(self.pfad, Uhr())
        z.merke("reiter", 2)
        z.merke_in("sortierung", "freigaben", ["Spur", True])
        self.assertTrue(z.speichern(sofort=True))
        neu = lb.Zustand(self.pfad, Uhr())
        self.assertEqual(neu.get("reiter"), 2)
        self.assertEqual(neu.get("sortierung"), {"freigaben": ["Spur", True]})

    def test_fehlend_gibt_vorgaben(self):
        self.assertEqual(lb.Zustand(self.pfad, Uhr()).daten, lb.Zustand.VORGABEN)

    def test_unlesbar_gibt_vorgaben(self):
        self.pfad.write_text("{kaputt", encoding="utf-8")
        self.assertEqual(lb.Zustand(self.pfad, Uhr()).daten, lb.Zustand.VORGABEN)

    def test_falscher_typ_wird_verworfen(self):
        self.pfad.write_text(json.dumps({"reiter": "zwei", "werte": [],
                                         "geometrie": "800x600+0+0"}),
                             encoding="utf-8")
        z = lb.Zustand(self.pfad, Uhr())
        self.assertEqual(z.get("reiter"), 0)
        self.assertEqual(z.get("werte"), {})
        self.assertEqual(z.get("geometrie"), "800x600+0+0")

    def test_liste_statt_objekt(self):
        self.pfad.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(lb.Zustand(self.pfad, Uhr()).daten, lb.Zustand.VORGABEN)

    def test_vorgaben_werden_nicht_geteilt(self):
        a = lb.Zustand(self.pfad, Uhr())
        a.daten["werte"]["x"] = 1
        self.assertEqual(lb.Zustand.VORGABEN["werte"], {})

    def test_hoechstens_alle_5_s(self):
        uhr = Uhr()
        z = lb.Zustand(self.pfad, uhr)
        z.merke("reiter", 1)                        # erster Wunsch: sofort
        self.assertEqual(json.loads(self.pfad.read_text("utf-8"))["reiter"], 1)
        uhr.t += 1
        z.merke("reiter", 2)                        # gebuendelt
        self.assertEqual(json.loads(self.pfad.read_text("utf-8"))["reiter"], 1)
        uhr.t += 2
        self.assertFalse(z.nachholen())
        uhr.t += 3
        self.assertTrue(z.nachholen())
        self.assertEqual(json.loads(self.pfad.read_text("utf-8"))["reiter"], 2)
        self.assertFalse(z.nachholen())             # nichts mehr offen

    def test_keine_tmp_bleibt_liegen(self):
        z = lb.Zustand(self.pfad, Uhr())
        z.merke("reiter", 3)
        self.assertEqual(os.listdir(self.tmp.name), ["leitstand_zustand.json"])


class MitTk(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.zustand = lb.Zustand(Path(self.tmp.name) / "z.json", Uhr())


class ZeitDialogTest(MitTk):
    def test_zeitablauf(self):
        uhr = Uhr()
        d = lb.ZeitDialog(self.root, "Test", 120, uhr=uhr)
        uhr.t += 121
        d._takt()
        self.assertEqual(d.ergebnis, "zeitablauf")

    def test_bedienung_setzt_die_uhr_zurueck(self):
        uhr = Uhr()
        d = lb.ZeitDialog(self.root, "Test", 120, uhr=uhr)
        uhr.t += 100
        d._bedient()
        uhr.t += 50
        d._takt()
        self.assertIsNone(d.ergebnis)
        self.assertAlmostEqual(d.rest_s(), 70)
        d.fertig("abgebrochen")

    def test_escape_und_schliessen_brechen_ab(self):
        d = lb.ZeitDialog(self.root, "Test", 120, uhr=Uhr())
        self.assertTrue(d.bind("<Escape>"))
        d.fertig("abgebrochen")
        d.fertig("ja")                              # zweiter Aufruf wirkungslos
        self.assertEqual(d.ergebnis, "abgebrochen")


class TabelleTest(MitTk):
    def _tabelle(self):
        t = lb.Tabelle(self.root, ("Spur", "Wert"), self.zustand, "probe")
        t.setze([("xperp", "10"), ("orb", "9"), ("gitter", "100")])
        return t

    def test_filter(self):
        t = self._tabelle()
        t.w_filter.set("or")
        self.assertEqual(t.sichtbare(), [("orb", "9")])

    def test_sortieren_und_umkehren(self):
        t = self._tabelle()
        t.sortiere_nach("Wert")
        self.assertEqual([z[0] for z in t.sichtbare()], ["orb", "xperp", "gitter"])
        t.sortiere_nach("Wert")
        self.assertEqual([z[0] for z in t.sichtbare()], ["gitter", "xperp", "orb"])
        self.assertEqual(self.zustand.get("sortierung")["probe"], ["Wert", True])
        self.assertTrue(t.baum.heading("Wert", "text").endswith("▼"))

    def test_sortierung_kommt_aus_dem_zustand(self):
        self.zustand.merke_in("sortierung", "probe", ["Spur", False])
        t = self._tabelle()
        self.assertEqual([z[0] for z in t.sichtbare()], ["gitter", "orb", "xperp"])

    def test_auswahl_bleibt_nach_neuem_setzen(self):
        t = self._tabelle()
        t.baum.selection_set(t.baum.get_children()[1])
        t.setze([("xperp", "11"), ("orb", "8"), ("gitter", "100")])
        self.assertEqual(t.auswahl(), [("orb", "8")])

    def test_kopieren_legt_sichtbares_ab(self):
        t = self._tabelle()
        t.w_filter.set("gitter")
        self.assertEqual(t.kopieren(), "Spur\tWert\ngitter\t100")
        self.assertEqual(self.root.clipboard_get(), "Spur\tWert\ngitter\t100")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Tests laufen lassen — sie müssen scheitern**

Run: `$PY -m unittest tests.test_leitstand_bedienung -v`
Erwartet: `ModuleNotFoundError: No module named 'leitstand_bedienung'`.

- [ ] **Step 3: `leitstand_bedienung.py` schreiben**

```python
"""Gemeinsame Bausteine des Leitstands.

Sortieren, Filtern, Kopieren, die Zustandsdatei, Tooltip, sortierbare
Tabelle und der Dialog mit Zeitablauf - damit die Reiter sie nicht je
einzeln bauen und sich nicht je anders verhalten.

Die Zustandsdatei `leitstand_zustand.json` ist nicht versioniert und wird
von keinem Betriebsteil gelesen.
"""

import csv
import ctypes
import json
import os
import re
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

HIER = Path(__file__).resolve().parent
ZUSTAND_DATEI = HIER / "leitstand_zustand.json"
SPEICHER_ABSTAND_S = 5.0          # Zustand hoechstens alle 5 s schreiben
ZEITLIMIT_S = 120                 # Dialoge: ohne Bedienung zu, nichts geschrieben

_ZAHL = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*([^\d.,:\-]*)$")
_LAGE = re.compile(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$")


# --- Sortieren, Filtern, Kopieren ------------------------------------------

def sortier_schluessel(wert):
    """Zahlen (auch "12,5 %", "50 USD") numerisch, alles andere als Text.

    Datum ("2026-09-29") und Dauer ("1:30 h") sind Text: lexikalisch
    sortieren sie richtig, numerisch waere nur die erste Zahl gelesen.
    """
    if wert is None:
        return (1, 0.0, "")
    if isinstance(wert, bool):
        return (1, 0.0, str(wert).lower())
    if isinstance(wert, (int, float)):
        return (0, float(wert), "")
    text = str(wert)
    m = _ZAHL.match(text)
    if m:
        return (0, float(m.group(1).replace(",", ".")), "")
    return (1, 0.0, text.lower())


def passt(zeile, text):
    worte = (text or "").lower().split()
    gesamt = " ".join(str(z) for z in zeile).lower()
    return all(w in gesamt for w in worte)


def sortiere(zeilen, spalte, umgekehrt):
    return sorted(zeilen, key=lambda z: sortier_schluessel(z[spalte]),
                  reverse=umgekehrt)


def _zelle(wert):
    return (str(wert).replace("\t", " ").replace("\r", " ")
            .replace("\n", " "))


def als_tsv(spalten, zeilen):
    return "\n".join("\t".join(_zelle(c) for c in z)
                     for z in [tuple(spalten)] + list(zeilen))


def csv_schreiben(pfad, spalten, zeilen):
    """Semikolon und BOM: so oeffnet Excel mit deutschem Gebietsschema richtig."""
    with open(pfad, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(spalten)
        w.writerows(zeilen)


# --- Fenster ----------------------------------------------------------------

def lage_gueltig(geometrie, schirm):
    """Liegt die Titelleiste auf dem (virtuellen) Schirm, mind. 100 px breit?"""
    m = _LAGE.match(geometrie or "")
    if not m:
        return False
    b, _h, x, y = (int(g) for g in m.groups())
    sx, sy, sb, sh = schirm
    ueberlappung = min(x + b, sx + sb) - max(x, sx)
    return ueberlappung >= 100 and sy <= y <= sy + sh - 30


def virtueller_schirm(root):
    """(x, y, Breite, Hoehe) ueber alle Monitore; ohne Windows der Hauptschirm."""
    try:
        m = ctypes.windll.user32.GetSystemMetrics      # type: ignore[attr-defined]
        x, y, b, h = m(76), m(77), m(78), m(79)
        if b > 0 and h > 0:
            return (x, y, b, h)
    except Exception:                                        # noqa: BLE001
        pass
    return (0, 0, root.winfo_screenwidth(), root.winfo_screenheight())


class _FLASHWINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("hwnd", ctypes.c_void_p),
                ("dwFlags", ctypes.c_uint), ("uCount", ctypes.c_uint),
                ("dwTimeout", ctypes.c_uint)]


FLASHW_TRAY = 0x2


def blinken(root):
    """Einmal (3 Takte) in der Taskleiste blinken. False ohne Windows."""
    try:
        u = ctypes.windll.user32                          # type: ignore[attr-defined]
        u.GetParent.restype = ctypes.c_void_p
        u.GetParent.argtypes = [ctypes.c_void_p]
        hwnd = u.GetParent(root.winfo_id()) or root.winfo_id()
        info = _FLASHWINFO(ctypes.sizeof(_FLASHWINFO), hwnd, FLASHW_TRAY, 3, 0)
        u.FlashWindowEx(ctypes.byref(info))
        return True
    except Exception:                                        # noqa: BLE001
        return False


# --- Zustand ----------------------------------------------------------------

class Zustand:
    """leitstand_zustand.json: gebuendelt, atomar, unlesbar -> Vorgaben."""

    VORGABEN = {"reiter": 0, "geometrie": "", "schrift": 0,
                "werte": {}, "sortierung": {}}

    def __init__(self, pfad=ZUSTAND_DATEI, uhr=time.monotonic):
        self.pfad = Path(pfad)
        self.uhr = uhr
        self._zuletzt = None
        self._faellig = False
        self.daten = self.lade()

    def lade(self):
        aus = json.loads(json.dumps(self.VORGABEN))            # tiefe Kopie
        try:
            roh = json.loads(self.pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return aus
        if not isinstance(roh, dict):
            return aus
        for k, v in roh.items():
            if k in aus and type(v) is type(aus[k]):
                aus[k] = v
        return aus

    def get(self, k):
        return self.daten.get(k)

    def merke(self, k, v):
        self.daten[k] = v
        self.speichern()

    def merke_in(self, k, schluessel, v):
        self.daten.setdefault(k, {})[schluessel] = v
        self.speichern()

    def speichern(self, sofort=False):
        jetzt = self.uhr()
        if (not sofort and self._zuletzt is not None
                and jetzt - self._zuletzt < SPEICHER_ABSTAND_S):
            self._faellig = True
            return False
        tmp = self.pfad.with_name(self.pfad.name + ".tmp")
        try:
            tmp.write_text(json.dumps(self.daten, ensure_ascii=False, indent=2)
                           + "\n", encoding="utf-8")
            os.replace(tmp, self.pfad)
        except OSError:
            return False
        self._zuletzt = jetzt
        self._faellig = False
        return True

    def nachholen(self):
        """Vom Takt des Leitstands gerufen: einen gebuendelten Wunsch nachholen."""
        return self.speichern() if self._faellig else False


# --- Tk-Bausteine -----------------------------------------------------------

class Tooltip:
    def __init__(self, widget, text=""):
        self.widget, self.text, self.fenster = widget, text, None
        widget.bind("<Enter>", self._zeigen, add="+")
        widget.bind("<Leave>", self._weg, add="+")

    def setze(self, text):
        self.text = text

    def _zeigen(self, _e=None):
        if not self.text or self.fenster:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.fenster = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        tk.Label(tw, text=self.text, background="#ffffe0", foreground="#000000",
                 relief="solid", borderwidth=1, padx=4, pady=2).pack()

    def _weg(self, _e=None):
        if self.fenster:
            self.fenster.destroy()
            self.fenster = None


def setze_knopf(knopf, tip, erlaubt, grund):
    """Knopf frei/gesperrt; gesperrt nennt der Tooltip den Grund."""
    knopf.state(["!disabled"] if erlaubt else ["disabled"])
    tip.setze("" if erlaubt else grund)


class Tabelle(ttk.Frame):
    """Treeview mit Filterfeld, Sortieren per Spaltenkopf, Kopieren und CSV."""

    def __init__(self, eltern, spalten, zustand, name, hoehe=10,
                 auswahl="browse"):
        super().__init__(eltern)
        self.spalten, self.zustand, self.name = tuple(spalten), zustand, name
        self._alle, self._tags, self._sichtbar = [], [], []
        s = (zustand.get("sortierung") or {}).get(name)
        self.sortierung = (tuple(s) if isinstance(s, list) and len(s) == 2
                           and s[0] in self.spalten else None)

        kopf = ttk.Frame(self)
        kopf.pack(fill="x", pady=(0, 4))
        ttk.Label(kopf, text="Filter:").pack(side="left")
        self.w_filter = tk.StringVar()
        self.w_filter.trace_add("write", lambda *_: self._zeigen())
        ttk.Entry(kopf, textvariable=self.w_filter, width=24).pack(side="left",
                                                                   padx=4)
        ttk.Button(kopf, text="CSV …", command=self.csv_speichern).pack(side="right")
        ttk.Button(kopf, text="Kopieren", command=self.kopieren).pack(side="right",
                                                                     padx=4)
        self.baum = ttk.Treeview(self, columns=self.spalten, show="headings",
                                 height=hoehe, selectmode=auswahl)
        for sp in self.spalten:
            self.baum.heading(sp, text=sp,
                              command=lambda sp=sp: self.sortiere_nach(sp))
            self.baum.column(sp, width=110, anchor="w")
        leiste = ttk.Scrollbar(self, orient="vertical", command=self.baum.yview)
        self.baum.configure(yscrollcommand=leiste.set)
        self.baum.pack(side="left", fill="both", expand=True)
        leiste.pack(side="right", fill="y")
        self._pfeile()

    def setze(self, zeilen, tags=None):
        self._alle = [tuple(z) for z in zeilen]
        self._tags = [tuple(t) for t in tags] if tags else [()] * len(self._alle)
        self._zeigen()

    def _zeigen(self):
        gewaehlt = {str(z[0]) for z in self.auswahl()}
        paare = [(z, t) for z, t in zip(self._alle, self._tags)
                 if passt(z, self.w_filter.get())]
        if self.sortierung:
            i = self.spalten.index(self.sortierung[0])
            paare.sort(key=lambda p: sortier_schluessel(p[0][i]),
                       reverse=self.sortierung[1])
        self.baum.delete(*self.baum.get_children())
        self._sichtbar = [z for z, _t in paare]
        for z, t in paare:
            iid = self.baum.insert("", "end", values=z, tags=t)
            if str(z[0]) in gewaehlt:
                self.baum.selection_add(iid)

    def sichtbare(self):
        return list(self._sichtbar)

    def auswahl(self):
        kinder = self.baum.get_children()
        return [self._sichtbar[kinder.index(i)] for i in self.baum.selection()
                if i in kinder and kinder.index(i) < len(self._sichtbar)]

    def sortiere_nach(self, spalte):
        umgekehrt = bool(self.sortierung and self.sortierung[0] == spalte
                         and not self.sortierung[1])
        self.sortierung = (spalte, umgekehrt)
        self.zustand.merke_in("sortierung", self.name, [spalte, umgekehrt])
        self._pfeile()
        self._zeigen()

    def _pfeile(self):
        for sp in self.spalten:
            zeichen = ""
            if self.sortierung and self.sortierung[0] == sp:
                zeichen = " ▼" if self.sortierung[1] else " ▲"
            self.baum.heading(sp, text=sp + zeichen)

    def kopieren(self):
        text = als_tsv(self.spalten, self.sichtbare())
        self.clipboard_clear()
        self.clipboard_append(text)
        return text

    def csv_speichern(self):
        pfad = filedialog.asksaveasfilename(parent=self, defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not pfad:
            return
        try:
            csv_schreiben(pfad, self.spalten, self.sichtbare())
        except OSError as e:
            messagebox.showerror("CSV", "nicht geschrieben: %s" % e, parent=self)


class ZeitDialog(tk.Toplevel):
    """Modaler Dialog, der sich nach `zeitlimit_s` ohne Bedienung schliesst.

    Jede Taste und jeder Klick setzt die Uhr zurueck. Esc und das
    Fensterkreuz ergeben "abgebrochen", der Ablauf "zeitablauf" - in beiden
    Faellen schreibt der Aufrufer nichts. Kein Return-Kuerzel: Bestaetigen
    geht nur per Mausklick auf den Knopf.
    """

    def __init__(self, eltern, titel, zeitlimit_s=ZEITLIMIT_S, uhr=time.monotonic):
        super().__init__(eltern)
        self.title(titel)
        self.transient(eltern)
        self.zeitlimit_s, self.uhr = zeitlimit_s, uhr
        self.ergebnis = None
        self._letzte = uhr()
        self.inhalt = ttk.Frame(self, padding=10)
        self.inhalt.pack(fill="both", expand=True)
        self.w_rest = ttk.Label(self, text="")
        self.w_rest.pack(anchor="e", padx=10, pady=(0, 6))
        self.bind("<KeyPress>", self._bedient, add="+")
        self.bind("<ButtonPress>", self._bedient, add="+")
        self.bind("<Escape>", lambda _e: self.fertig("abgebrochen"))
        self.protocol("WM_DELETE_WINDOW", lambda: self.fertig("abgebrochen"))
        self._takt_id = self.after(250, self._takt)

    def _bedient(self, _e=None):
        self._letzte = self.uhr()

    def rest_s(self):
        return max(0.0, self.zeitlimit_s - (self.uhr() - self._letzte))

    def _takt(self):
        if self.ergebnis is not None:
            return
        rest = self.rest_s()
        if rest <= 0:
            self.fertig("zeitablauf")
            return
        self.w_rest.config(text="schließt ohne Bedienung in %d s" % rest)
        self._takt_id = self.after(250, self._takt)

    def fertig(self, wert):
        if self.ergebnis is not None:
            return
        self.ergebnis = wert
        try:
            self.after_cancel(self._takt_id)
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def zeige_modal(self):
        self.grab_set()
        self.focus_set()
        self.wait_window()
        return self.ergebnis
```

- [ ] **Step 4: Tests laufen lassen**

Run: `$PY -m unittest tests.test_leitstand_bedienung -v`
Erwartet: alle grün.

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage aus Aufgabe 1 bleibt unverändert.

- [ ] **Step 5: Commit**

```bash
git status --short
git add Agenten/Handel/leitstand_bedienung.py Agenten/Handel/tests/test_leitstand_bedienung.py
git commit -m "Leitstand: gemeinsame Bausteine (Tabelle, Zustand, Zeit-Dialog) (Aufgabe 4)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Freigaben-Reiter `leitstand_freigaben.py`

**Files:**
- Create: `Agenten/Handel/leitstand_freigaben.py`
- Test: `Agenten/Handel/tests/test_leitstand_freigaben.py`

**Interfaces:**
- Consumes:
  - aus Aufgabe 1: `ff.grenzwerte(w, waehrung)`;
  - aus Aufgabe 2: `ff.oeffnen`, `ff.schliessen`, `ff.alles_schliessen` (können `TimeoutError` werfen), dazu `ff.alle()`, `ff.lade(spur)`, `ff.Fenster`, `ff._zeit`, `ff._jetzt`, `ff.WIEDERVORLAGE_NACH_ABLEHNUNG_STUNDEN`;
  - aus Aufgabe 4: `Tabelle`, `Tooltip`, `setze_knopf`, `ZeitDialog`, `blinken`;
  - `dauerlauf.SPUREN`, `dauerlauf.AUTO_FREIGABE`.
- Produces:
  - `SPALTEN`, `SPERRE_BELEGT = "Sperre belegt — bitte erneut"`;
  - `zeilen(fenster: dict[str, ff.Fenster], jetzt=None) -> list[tuple]`, `knopf_zustand(f: ff.Fenster | None) -> dict[str, (bool, str)]`;
  - `freigeben(spur, stunden) -> str`, `ablehnen(spur) -> str`, `schliessen(spur) -> str`, `notaus() -> str` (jede gibt die Meldung für die Statusleiste zurück und wirft nie `TimeoutError`);
  - `vorbelegte_stunden(f) -> int`, `grenz_zeilen(spur) -> list[(str, str)]`, `neue_anfragen(gesehen: set, fenster: dict) -> (neu: set, aktuell: set)`;
  - `class FreigabeDialog(ZeitDialog)(eltern, spur, grenzen, stunden, **kw)`, Ergebnis `("ja", stunden)`, `"nein"`, `"abgebrochen"` oder `"zeitablauf"`;
  - `class FreigabenReiter(ttk.Frame)(eltern, leitstand, dialog=FreigabeDialog, frage=messagebox.askyesno)` mit der Reiter-Schnittstelle.

- [ ] **Step 1: Tests schreiben**

`tests/test_leitstand_freigaben.py`:

```python
"""Freigaben-Reiter: Ja/Ablehnen nur bei wartender Anfrage, verfallene Anfrage
und Zeitablauf schreiben nichts, Notaus schliesst alles - auch bei belegter
Sperre ohne Absturz.

freigabefenster.DATEI zeigt auf einen Temp-Ordner. Die Dialoge werden durch
Attrappen ersetzt, die ein festes Ergebnis liefern; der echte Dialog wird
einzeln auf den Zeitablauf geprueft.

Direkt ausfuehrbar:  python tests/test_leitstand_freigaben.py
"""

import datetime as dt
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import freigabefenster as ff                                   # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_freigaben as lf                               # noqa: E402


class StubLeitstand:
    def __init__(self, root, zustand):
        self.root, self.zustand, self.meldungen = root, zustand, []

    def melde(self, text):
        self.meldungen.append(text)


def attrappe(ergebnis):
    class Dialog:
        aufrufe = []

        def __init__(self, eltern, spur, grenzen, stunden, **kw):
            Dialog.aufrufe.append((spur, grenzen, stunden))

        def zeige_modal(self):
            return ergebnis
    return Dialog


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(ff, "DATEI",
                         os.path.join(self.tmp.name, "freigabe_fenster.json"))
        p.start()
        self.addCleanup(p.stop)

    def _roh(self):
        try:
            with open(ff.DATEI, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _verfallene_anfrage(self, spur="xperp"):
        ff.anfrage_stellen(spur, 60)
        d = json.loads(self._roh())
        d[spur]["anfrage_bis"] = (ff._jetzt() - dt.timedelta(minutes=1)).isoformat()
        with open(ff.DATEI, "w", encoding="utf-8") as f:
            json.dump(d, f)


class Aktionen(Basis):
    def test_freigeben_bei_wartender_anfrage(self):
        ff.anfrage_stellen("xperp", 90)
        self.assertEqual(lf.freigeben("xperp", 6), "xperp scharf für 6:00 h")
        f = ff.lade("xperp")
        self.assertTrue(f.offen())
        self.assertEqual(f.d["freigegeben_von"], "leitstand")

    def test_freigeben_ohne_anfrage_schreibt_nichts(self):
        self.assertEqual(lf.freigeben("xperp", 6),
                         "Anfrage war verfallen — nichts geändert")
        self.assertIsNone(self._roh())

    def test_verfallene_anfrage_schreibt_nichts(self):
        self._verfallene_anfrage()
        vorher = self._roh()
        self.assertIn("verfallen", lf.freigeben("xperp", 2))
        self.assertIn("keine wartende Anfrage", lf.ablehnen("xperp"))
        self.assertEqual(self._roh(), vorher)

    def test_ablehnen_setzt_wiedervorlage_grund(self):
        ff.anfrage_stellen("xperp", 60)
        self.assertIn("abgelehnt", lf.ablehnen("xperp"))
        d = ff.lade("xperp").d
        self.assertEqual(d["schliess_grund"], "abgelehnt (Leitstand)")
        self.assertNotIn("anfrage_bis", d)

    def test_schliessen(self):
        ff.anfrage_stellen("xperp", 60)
        ff.oeffnen("xperp", 2, wer="test")
        self.assertEqual(lf.schliessen("xperp"), "xperp zurück auf Papier")
        self.assertFalse(ff.lade("xperp").offen())
        self.assertEqual(ff.lade("xperp").d["schliess_grund"], "von Hand (Leitstand)")

    def test_notaus_schliesst_alle(self):
        for s in ("xperp", "scanner"):
            ff.anfrage_stellen(s, 60)
            ff.oeffnen(s, 2, wer="test")
        ff.anfrage_stellen("orb", 60)
        meldung = lf.notaus()
        self.assertIn("scanner", meldung)
        self.assertIn("xperp", meldung)
        for s, f in ff.alle().items():
            self.assertFalse(f.offen(), s)
            self.assertFalse(f.anfrage_offen(), s)
            self.assertEqual(f.d["schliess_grund"], "Notaus (Leitstand)")

    def test_notaus_bei_belegter_sperre_meldet_und_schreibt_nichts(self):
        ff.anfrage_stellen("xperp", 60)
        ff.oeffnen("xperp", 2, wer="test")
        vorher = self._roh()
        open(ff.DATEI + ".lock", "w").close()
        with patch.object(ff, "SPERRE_WARTEN_S", 0.2):
            self.assertEqual(lf.notaus(), lf.SPERRE_BELEGT)
            self.assertEqual(lf.freigeben("xperp", 1), lf.SPERRE_BELEGT)
        self.assertEqual(self._roh(), vorher)


class Anzeige(Basis):
    def test_spuren_ohne_eintrag_stehen_als_papier_da(self):
        ff.anfrage_stellen("xperp", 60)
        z = {r[0]: r for r in lf.zeilen(ff.alle())}
        self.assertEqual(z["xperp"][1], "Anfrage laeuft, unbeantwortet")
        self.assertRegex(z["xperp"][2], r"^\d+ min$")
        self.assertEqual(z["scanner"][1], "Papier")
        self.assertEqual(z["scanner"][7], "ja")         # AUTO_FREIGABE

    def test_kaputter_eintrag_wird_uebersprungen(self):
        with open(ff.DATEI, "w", encoding="utf-8") as f:
            json.dump({"xperp": "kaputt"}, f)
        z = {r[0]: r for r in lf.zeilen(ff.alle())}
        self.assertEqual(z["xperp"][1], "Papier")

    def test_knoepfe(self):
        self.assertFalse(lf.knopf_zustand(None)["freigeben"][0])
        ff.anfrage_stellen("xperp", 60)
        k = lf.knopf_zustand(ff.lade("xperp"))
        self.assertEqual(k["freigeben"], (True, ""))
        self.assertEqual(k["schliessen"], (False, "Spur ist nicht scharf"))
        self.assertEqual(lf.knopf_zustand(ff.lade("orb"))["ablehnen"],
                         (False, "keine wartende Anfrage"))

    def test_vorbelegte_stunden(self):
        self.assertEqual(lf.vorbelegte_stunden(ff.Fenster("x", {"anfrage_dauer_minuten": 90})), 2)
        self.assertEqual(lf.vorbelegte_stunden(ff.Fenster("x", {})), 1)
        self.assertEqual(lf.vorbelegte_stunden(ff.Fenster("x", {"anfrage_dauer_minuten": 9000})), 24)

    def test_neue_anfrage_blinkt_nur_einmal(self):
        ff.anfrage_stellen("xperp", 60)
        neu, gesehen = lf.neue_anfragen(set(), ff.alle())
        self.assertEqual(len(neu), 1)
        neu, gesehen = lf.neue_anfragen(gesehen, ff.alle())
        self.assertEqual(neu, set())

    def test_grenzen_einer_spur(self):
        ordner = Path(self.tmp.name) / "xperp"
        ordner.mkdir()
        (ordner / "wachen.json").write_text(json.dumps({"max_pro_trade_usd": 50}),
                                            encoding="utf-8")
        with patch.object(lf, "HIER", Path(self.tmp.name)):
            self.assertEqual(lf.grenz_zeilen("xperp"), [("je Anlauf", "50 USD")])
            self.assertEqual(lf.grenz_zeilen("scanner"),
                             [("wachen.json", "nicht lesbar")])


class Reiter(Basis):
    def setUp(self):
        super().setUp()
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.ls = StubLeitstand(self.root, lb.Zustand(
            Path(self.tmp.name) / "z.json", lambda: 0.0))
        p = patch.object(lf, "blinken", return_value=True)
        self.blinken = p.start()
        self.addCleanup(p.stop)

    def _reiter(self, ergebnis, frage=True):
        r = lf.FreigabenReiter(self.root, self.ls, dialog=attrappe(ergebnis),
                               frage=lambda *a, **k: frage)
        r._waehle = lambda spur: r.tabelle.baum.selection_set(
            [i for i in r.tabelle.baum.get_children()
             if r.tabelle.baum.item(i, "values")[0] == spur])
        return r

    def test_zeitablauf_schreibt_nichts(self):
        ff.anfrage_stellen("xperp", 60)
        vorher = self._roh()
        r = self._reiter("zeitablauf")
        r._waehle("xperp")
        r.freigeben_klick()
        self.assertEqual(self._roh(), vorher)
        self.assertIn("nichts geändert", self.ls.meldungen[-1])

    def test_ja_im_dialog_gibt_frei(self):
        ff.anfrage_stellen("xperp", 60)
        r = self._reiter(("ja", 3))
        r._waehle("xperp")
        r.freigeben_klick()
        self.assertEqual(self.ls.meldungen[-1], "xperp scharf für 3:00 h")

    def test_freigeben_ohne_anfrage_oeffnet_keinen_dialog(self):
        r = self._reiter(("ja", 3))
        r._waehle("xperp")
        r.freigeben_klick()
        self.assertIsNone(self._roh())

    def test_titel_zaehlt_wartende_und_blinkt(self):
        ff.anfrage_stellen("xperp", 60)
        r = self._reiter("abgebrochen")
        self.assertEqual(r.titel_zusatz(), " (1)")
        self.blinken.assert_called_once()
        r.refresh()
        self.blinken.assert_called_once()

    def test_notaus_nur_nach_rueckfrage(self):
        ff.anfrage_stellen("xperp", 60)
        vorher = self._roh()
        self._reiter("abgebrochen", frage=False).notaus_klick()
        self.assertEqual(self._roh(), vorher)

    def test_echter_dialog_laeuft_ab(self):
        uhr = [0.0]
        d = lf.FreigabeDialog(self.root, "xperp", [("je Anlauf", "50 USD")], 2,
                              uhr=lambda: uhr[0])
        self.assertEqual(d.w_stunden.get(), 2)
        uhr[0] = 121.0
        d._takt()
        self.assertEqual(d.ergebnis, "zeitablauf")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Tests laufen lassen — sie müssen scheitern**

Run: `$PY -m unittest tests.test_leitstand_freigaben -v`
Erwartet: `ModuleNotFoundError: No module named 'leitstand_freigaben'`.

- [ ] **Step 3: `leitstand_freigaben.py` schreiben**

```python
"""Freigaben-Reiter des Leitstands.

Schreibt NUR ueber freigabefenster.* - dieselben Funktionen, die Telegram
benutzt; die Wirkung ist dieselbe wie /ja und /nein. Freigeben geht nur,
wenn der Dauerlauf eine Anfrage gestellt hat. Freigeben und Notaus haben kein
Tastenkuerzel; der Dialog schliesst sich nach 120 s ohne Bedienung und
schreibt dann nichts.
"""

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import dauerlauf
import freigabefenster as ff
from leitstand_bedienung import Tabelle, Tooltip, ZeitDialog, blinken, setze_knopf

HIER = Path(__file__).resolve().parent
SPALTEN = ("Spur", "Stand", "Anfrage verfällt in", "Freigegeben von",
           "Freigegeben am", "Geschlossen am", "Grund", "Auto")
SPERRE_BELEGT = "Sperre belegt — bitte erneut"


def _kurz(iso):
    t = ff._zeit(iso)
    return t.strftime("%d.%m. %H:%M") if t else ""


def _gueltig(fenster):
    return {s: f for s, f in fenster.items() if isinstance(f.d, dict)}


def zeilen(fenster, jetzt=None):
    """Eine Zeile je Spur; Spuren aus dauerlauf.SPUREN ohne Eintrag als Papier."""
    jetzt = jetzt or ff._jetzt()
    fenster = _gueltig(fenster)
    for spur in dauerlauf.SPUREN:
        fenster.setdefault(spur, ff.Fenster(spur, {}))
    aus = []
    for spur in sorted(fenster):
        f = fenster[spur]
        d = f.d
        verfaellt = ""
        if f.anfrage_offen():
            rest = ff._zeit(d.get("anfrage_bis")) - jetzt
            verfaellt = "%d min" % max(0, int(rest.total_seconds() // 60))
        aus.append((spur, f.text(), verfaellt, d.get("freigegeben_von") or "",
                    _kurz(d.get("freigegeben_am")),
                    _kurz(d.get("zuletzt_geschlossen")),
                    d.get("schliess_grund") or "",
                    "ja" if spur in dauerlauf.AUTO_FREIGABE else ""))
    return aus


def knopf_zustand(f):
    if f is None:
        kein = (False, "keine Spur gewählt")
        return {"freigeben": kein, "ablehnen": kein, "schliessen": kein}
    anfrage = f.anfrage_offen()
    grund_a = "" if anfrage else "keine wartende Anfrage"
    scharf = f.offen()
    return {"freigeben": (anfrage, grund_a), "ablehnen": (anfrage, grund_a),
            "schliessen": (scharf, "" if scharf else "Spur ist nicht scharf")}


def freigeben(spur, stunden):
    try:
        minuten = ff.oeffnen(spur, stunden, wer="leitstand")
    except TimeoutError:
        return SPERRE_BELEGT
    if minuten is None:
        return "Anfrage war verfallen — nichts geändert"
    return "%s scharf für %d:%02d h" % (spur, minuten // 60, minuten % 60)


def ablehnen(spur):
    if not ff.lade(spur).anfrage_offen():
        return "%s: keine wartende Anfrage — nichts geändert" % spur
    try:
        ff.schliessen(spur, "abgelehnt (Leitstand)")
    except TimeoutError:
        return SPERRE_BELEGT
    return "%s abgelehnt — Wiedervorlage in %d h" % (
        spur, ff.WIEDERVORLAGE_NACH_ABLEHNUNG_STUNDEN)


def schliessen(spur):
    try:
        war = ff.schliessen(spur, "von Hand (Leitstand)")
    except TimeoutError:
        return SPERRE_BELEGT
    return ("%s zurück auf Papier" % spur if war
            else "%s war nicht scharf — Grund vermerkt" % spur)


def notaus():
    try:
        spuren = ff.alles_schliessen("Notaus (Leitstand)")
    except TimeoutError:
        return SPERRE_BELEGT
    if spuren:
        return "Notaus: %s zurück auf Papier" % ", ".join(sorted(spuren))
    return "Notaus: keine Spur war scharf — Anfragen verworfen"


def vorbelegte_stunden(f):
    minuten = f.d.get("anfrage_dauer_minuten") or 60
    return max(1, min(24, round(minuten / 60)))


def grenz_zeilen(spur):
    info = dauerlauf.SPUREN.get(spur, {})
    pfad = HIER / info.get("ordner", spur) / "wachen.json"
    try:
        w = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [("wachen.json", "nicht lesbar")]
    if not isinstance(w, dict):
        return [("wachen.json", "nicht lesbar")]
    paare = [(n, v.strip()) for n, v in ff.grenzwerte(w, info.get("waehrung", "USD"))]
    return paare or [("Grenzen", "keine in wachen.json")]


def neue_anfragen(gesehen, fenster):
    """(neu, aktuell): eine Anfrage ist neu, bis sie einmal gesehen wurde."""
    aktuell = {(s, f.d.get("anfrage_gestellt"))
               for s, f in _gueltig(fenster).items() if f.anfrage_offen()}
    return aktuell - set(gesehen), aktuell


class FreigabeDialog(ZeitDialog):
    """Ergebnis: ("ja", stunden) | "nein" | "abgebrochen" | "zeitablauf"."""

    def __init__(self, eltern, spur, grenzen, stunden, **kw):
        super().__init__(eltern, "Freigabe %s" % spur, **kw)
        i = self.inhalt
        ttk.Label(i, text="Freigabe %s?" % spur,
                  font=("Segoe UI", 12, "bold")).grid(row=0, column=0,
                                                      columnspan=2, sticky="w")
        ttk.Label(i, text="Es gelten die Grenzen aus wachen.json:").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 2))
        for n, (name, wert) in enumerate(grenzen, start=2):
            ttk.Label(i, text=name).grid(row=n, column=0, sticky="w", padx=(10, 20))
            ttk.Label(i, text=wert).grid(row=n, column=1, sticky="w")
        r = len(grenzen) + 2
        ttk.Label(i, text="Dauer (Stunden):").grid(row=r, column=0, sticky="w",
                                                   pady=(8, 0))
        self.w_stunden = tk.IntVar(value=stunden)
        ttk.Spinbox(i, from_=1, to=24, textvariable=self.w_stunden, width=5,
                    state="readonly").grid(row=r, column=1, sticky="w", pady=(8, 0))
        knoepfe = ttk.Frame(i)
        knoepfe.grid(row=r + 1, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(knoepfe, text="Ja, freigeben", command=self.ja).pack(side="left",
                                                                       padx=4)
        ttk.Button(knoepfe, text="Nein, ablehnen",
                   command=lambda: self.fertig("nein")).pack(side="left", padx=4)
        ttk.Button(knoepfe, text="Abbrechen",
                   command=lambda: self.fertig("abgebrochen")).pack(side="left",
                                                                    padx=4)

    def ja(self):
        self.fertig(("ja", max(1, min(24, int(self.w_stunden.get())))))


class FreigabenReiter(ttk.Frame):
    def __init__(self, eltern, leitstand, dialog=FreigabeDialog,
                 frage=messagebox.askyesno):
        super().__init__(eltern, padding=6)
        self.ls, self.dialog, self.frage = leitstand, dialog, frage
        self._fenster, self._gesehen = {}, set()
        self.tabelle = Tabelle(self, SPALTEN, leitstand.zustand, "freigaben",
                               hoehe=14)
        self.tabelle.pack(fill="both", expand=True)
        self.tabelle.baum.tag_configure("wartet", background="#f9e2af",
                                        foreground="#000000")
        self.tabelle.baum.bind("<<TreeviewSelect>>", lambda _e: self._knoepfe())
        leiste = ttk.Frame(self)
        leiste.pack(fill="x", pady=(6, 0))
        self.k = {
            "freigeben": ttk.Button(leiste, text="Freigeben …",
                                    command=self.freigeben_klick),
            "ablehnen": ttk.Button(leiste, text="Ablehnen",
                                   command=self.ablehnen_klick),
            "schliessen": ttk.Button(leiste, text="Schließen",
                                     command=self.schliessen_klick),
        }
        self.tips = {}
        for name, knopf in self.k.items():
            knopf.pack(side="left", padx=4)
            self.tips[name] = Tooltip(knopf)
        self.k_notaus = tk.Button(leiste, text="NOTAUS", command=self.notaus_klick,
                                  bg="#c0392b", fg="white",
                                  activebackground="#e74c3c",
                                  font=("Segoe UI", 10, "bold"), padx=12)
        self.k_notaus.pack(side="right", padx=4)
        self.refresh()

    # Reiter-Schnittstelle
    def refresh(self):
        try:
            self._fenster = _gueltig(ff.alle())
        except (AttributeError, TypeError):          # Datei ist kein Objekt
            self._fenster = {}
        z = zeilen(self._fenster)
        self.tabelle.setze(z, [("wartet",) if r[2] else () for r in z])
        neu, self._gesehen = neue_anfragen(self._gesehen, self._fenster)
        if neu:
            blinken(self.ls.root)
        self._knoepfe()

    def titel_zusatz(self):
        return " (%d)" % len(self._gesehen) if self._gesehen else ""

    def status(self):
        return ""

    # Bedienung
    def gewaehlt(self):
        a = self.tabelle.auswahl()
        return a[0][0] if a else None

    def _knoepfe(self):
        spur = self.gewaehlt()
        f = (self._fenster.get(spur) or ff.Fenster(spur, {})) if spur else None
        for name, (erlaubt, grund) in knopf_zustand(f).items():
            setze_knopf(self.k[name], self.tips[name], erlaubt, grund)

    def freigeben_klick(self):
        spur = self.gewaehlt()
        f = ff.lade(spur) if spur else None
        if f is None or not f.anfrage_offen():
            self.ls.melde("%s: keine wartende Anfrage — nichts geändert" % spur)
            self.refresh()
            return
        erg = self.dialog(self.ls.root, spur, grenz_zeilen(spur),
                          vorbelegte_stunden(f)).zeige_modal()
        if isinstance(erg, tuple) and erg[0] == "ja":
            self.ls.melde(freigeben(spur, erg[1]))
        elif erg == "nein":
            self.ls.melde(ablehnen(spur))
        elif erg == "zeitablauf":
            self.ls.melde("Freigabe-Dialog ohne Bedienung geschlossen — nichts geändert")
        else:
            self.ls.melde("Freigabe abgebrochen — nichts geändert")
        self.refresh()

    def ablehnen_klick(self):
        spur = self.gewaehlt()
        if spur and self.frage("Ablehnen", "Anfrage von %s ablehnen?" % spur,
                               parent=self):
            self.ls.melde(ablehnen(spur))
            self.refresh()

    def schliessen_klick(self):
        spur = self.gewaehlt()
        if spur and self.frage("Schließen", "%s sofort zurück auf Papier?" % spur,
                               parent=self):
            self.ls.melde(schliessen(spur))
            self.refresh()

    def notaus_klick(self):
        if self.frage("NOTAUS", "Alle Spuren sofort zurück auf Papier?\n"
                      "Wartende Anfragen werden verworfen.", icon="warning",
                      parent=self):
            self.ls.melde(notaus())
            self.refresh()
```

- [ ] **Step 4: Tests laufen lassen**

Run: `$PY -m unittest tests.test_leitstand_freigaben tests.test_freigabefenster_sperre -v`
Erwartet: alle grün.

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage bleibt unverändert.

- [ ] **Step 5: Commit**

```bash
git status --short
git add Agenten/Handel/leitstand_freigaben.py Agenten/Handel/tests/test_leitstand_freigaben.py
git commit -m "Leitstand: Freigaben-Reiter mit Dialog, Schliessen und Notaus (Aufgabe 5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Laufsteuerung `leitstand_laeufe.py`

**Files:**
- Create: `Agenten/Handel/leitstand_laeufe.py`
- Test: `Agenten/Handel/tests/test_leitstand_backtests_lauf.py`

**Interfaces:**
- Consumes: —
- Produces (Aufgaben 7–11 und 13):
  - `HIER: Path`, `ABLAGE: Path` (= `HIER / "backtest_laeufe"`), `MAX_AUSGABE = 1_000_000`, `ABBRUCH_WARTEN_S = 5`, `VORSCHAU_ENDUNG = "-vorschau.json"`
  - `zeitstempel(jetzt: datetime | None = None) -> str` im Format `JJJJMMTT-hhmmss` (Ortszeit)
  - `sicherer_name(name: str) -> str`: nur `[A-Za-z0-9_-]`, sonst `_`
  - `kuerze(text: str, grenze=MAX_AUSGABE) -> str`: behält das **Ende**
  - `json_aus_ausgabe(text: str) -> dict | None`: das letzte JSON-Objekt, das am Zeilenanfang beginnt
  - `class Lauf(name, befehl, ablage=None, stempel=None, auswerten=None)`: `.name`, `.befehl`, `.pfad`, `.zeilen`, `.abgebrochen`, `.exit_code`, `.neue_zeilen() -> list[str]`, `.fertig() -> bool`, `.abbrechen()`, `.abschliessen() -> (Path, dict)`, `.verstrichen_s() -> float`
  - `class Steuerung(ablage=None)`: `.ablage`, `.lauf`, `.laeuft() -> bool`, `.starte(name, befehl, auswerten=None, stempel=None) -> Lauf` (wirft `RuntimeError("es läuft schon: <name>")`, bei Startfehler `OSError`), `.abbrechen()`, `.takt() -> (list[str], (Path, dict) | None)`, `.status() -> str`
  - Ablage-Dict: `name`, `befehl`, `start`, `ende`, `dauer_s`, `exit_code`, `abgebrochen`, `ausgabe`, bei `auswerten` zusätzlich `ergebnis`
  - `laufliste(ablage=None) -> list[dict]` (neueste zuerst, `*-vorschau.json` ausgelassen, unlesbar → `{"datei": n, "name": "nicht lesbar"}`), `lade_lauf(pfad) -> dict | None`
  - `LISTE_SPALTEN = ("Datei", "Lauf", "Start", "Dauer", "Ergebnis")`, `listen_zeilen(liste) -> list[tuple]`
  - `KENNZAHL_SPALTEN = ("Kennzahl", "A", "B", "Differenz B−A")`, `kennzahlen_flach(daten) -> list[(str, wert)] | None`, `ergebnis_zeilen(daten) -> list[tuple]`, `vergleich(a, b) -> list[tuple]` (wirft `ValueError` ohne Replay-Ergebnis)

Alle Pfad-Vorgaben werden **zur Laufzeit** aufgelöst (`ablage or ABLAGE`), damit Tests `ll.ABLAGE` auf einen Temp-Ordner umbiegen können.

- [ ] **Step 1: Tests schreiben**

`tests/test_leitstand_backtests_lauf.py`:

```python
"""Laufsteuerung: Ausgabe kommt an, nur ein Lauf gleichzeitig, Abbruch wirkt
(auch auf Kindprozesse), Ablagedatei ist vollstaendig.

Gestartet werden Mini-Skripte aus einem Temp-Ordner mit sys.executable; die
Ablage liegt ebenfalls im Temp-Ordner. Kein Netz, kein echtes daten/backtest/.

Direkt ausfuehrbar:  python tests/test_leitstand_backtests_lauf.py
"""

import json
import os
import re
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand_laeufe as ll                                  # noqa: E402

ECHO = """
import json
print("zeile 1")
print("zeile 2")
print(json.dumps({"runden": 3}, indent=2))
"""

FEHLER = """
import sys
sys.stderr.write("kaputt\\n")
sys.exit(3)
"""

SCHLAEFER = """
import time
print("start", flush=True)
time.sleep(60)
"""

# Startet ein Kind, das alle 0,1 s die Uhr in eine Datei schreibt, und
# schlaeft dann selbst. Lebt das Kind nach dem Abbruch weiter, aendert sich
# die Datei weiter.
MIT_KIND = """
import subprocess, sys, time
herz = sys.argv[1]
kind = ("import time\\n"
        "while True:\\n"
        "    open(%r, 'w').write(str(time.monotonic()))\\n"
        "    time.sleep(0.1)\\n" % herz)
subprocess.Popen([sys.executable, "-c", kind], stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL)
print("kind gestartet", flush=True)
time.sleep(60)
"""


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ablage = self.tmp / "ablage"
        self.st = ll.Steuerung(self.ablage)
        self.addCleanup(self._aufraeumen)

    def _aufraeumen(self):
        if self.st.lauf:
            self.st.abbrechen()
            self.bis_fertig(frist=20)
        # Temp-Ordner bleibt bei Windows-Sperren notfalls liegen
        for p in sorted(self.tmp.rglob("*"), reverse=True):
            try:
                p.unlink() if p.is_file() else p.rmdir()
            except OSError:
                pass

    def skript(self, name, text):
        p = self.tmp / name
        p.write_text(textwrap.dedent(text), encoding="utf-8")
        return [sys.executable, str(p)]

    def bis_fertig(self, frist=30):
        zeilen, ende = [], None
        schluss = time.monotonic() + frist
        while ende is None:
            if time.monotonic() > schluss:
                self.fail("Lauf nicht fertig nach %d s" % frist)
            neu, ende = self.st.takt()
            zeilen += neu
            time.sleep(0.05)
        return zeilen, ende

    def bis_zeile(self, text, frist=20):
        schluss = time.monotonic() + frist
        gesehen = []
        while time.monotonic() < schluss:
            neu, ende = self.st.takt()
            gesehen += neu
            if any(text in z for z in gesehen):
                return
            self.assertIsNone(ende, "Lauf endete vor %r" % text)
            time.sleep(0.05)
        self.fail("Zeile %r kam nicht" % text)


class Ablauf(Basis):
    def test_ausgabe_kommt_an_und_ablage_vollstaendig(self):
        self.st.starte("mini", self.skript("echo.py", ECHO),
                       auswerten=ll.json_aus_ausgabe)
        zeilen, (pfad, daten) = self.bis_fertig()
        self.assertEqual(zeilen[:2], ["zeile 1\n", "zeile 2\n"])
        self.assertRegex(pfad.name, r"^\d{8}-\d{6}-mini\.json$")
        gelesen = json.loads(pfad.read_text(encoding="utf-8"))
        self.assertEqual(set(gelesen), {"name", "befehl", "start", "ende", "dauer_s",
                                        "exit_code", "abgebrochen", "ausgabe",
                                        "ergebnis"})
        self.assertEqual(gelesen["exit_code"], 0)
        self.assertFalse(gelesen["abgebrochen"])
        self.assertEqual(gelesen["ergebnis"], {"runden": 3})
        self.assertIn("zeile 2", gelesen["ausgabe"])
        self.assertEqual(daten, gelesen)
        self.assertFalse(list(self.ablage.glob("*.tmp")))

    def test_stderr_und_exit_code_landen_in_der_ablage(self):
        self.st.starte("fehler", self.skript("fehler.py", FEHLER))
        _z, (_p, daten) = self.bis_fertig()
        self.assertEqual(daten["exit_code"], 3)
        self.assertIn("kaputt", daten["ausgabe"])
        self.assertNotIn("ergebnis", daten)

    def test_nur_ein_lauf_gleichzeitig(self):
        self.st.starte("lang", self.skript("s.py", SCHLAEFER))
        self.bis_zeile("start")
        with self.assertRaisesRegex(RuntimeError, "es läuft schon: lang"):
            self.st.starte("zweiter", self.skript("e.py", ECHO))
        self.assertTrue(self.st.laeuft())
        self.assertIn("Backtest: lang läuft seit 0:", self.st.status())

    def test_abbruch_wirkt(self):
        self.st.starte("lang", self.skript("s.py", SCHLAEFER))
        self.bis_zeile("start")
        t0 = time.monotonic()
        self.st.abbrechen()
        _z, (_p, daten) = self.bis_fertig(frist=15)
        self.assertLess(time.monotonic() - t0, 15)
        self.assertTrue(daten["abgebrochen"])
        self.assertNotEqual(daten["exit_code"], 0)
        self.assertFalse(self.st.laeuft())
        self.assertEqual(self.st.status(), "")

    def test_abbruch_beendet_auch_kindprozesse(self):
        herz = self.tmp / "herz.txt"
        befehl = self.skript("k.py", MIT_KIND) + [str(herz)]
        self.st.starte("kind", befehl)
        self.bis_zeile("kind gestartet")
        schluss = time.monotonic() + 10
        while not herz.exists() and time.monotonic() < schluss:
            time.sleep(0.05)
        self.assertTrue(herz.exists(), "Kind hat nie geschrieben")
        self.st.abbrechen()
        self.bis_fertig(frist=15)
        time.sleep(1.0)
        vorher = herz.read_text()
        time.sleep(1.0)
        self.assertEqual(herz.read_text(), vorher,
                         "Kindprozess rechnet nach dem Abbruch weiter")


class Hilfen(unittest.TestCase):
    def test_kuerzen_behaelt_das_ende(self):
        t = ll.kuerze("a" * 10 + "b" * 10, 10)
        self.assertTrue(t.startswith("[… 10 Zeichen am Anfang gekürzt]"))
        self.assertTrue(t.endswith("b" * 10))
        self.assertEqual(ll.kuerze("kurz", 10), "kurz")

    def test_json_aus_ausgabe_mit_hinweiszeilen(self):
        text = ("Zeitraum angehoben: 6 Monate im 4H-Takt ...\n"
                "{\n  \"a\": {\n    \"b\": 1\n  }\n}\n"
                "Trockenlauf: nichts gerechnet, nichts geschrieben.\n")
        self.assertEqual(ll.json_aus_ausgabe(text), {"a": {"b": 1}})
        self.assertIsNone(ll.json_aus_ausgabe("nur Text\n"))
        self.assertIsNone(ll.json_aus_ausgabe("{kaputt\n"))

    def test_json_aus_ausgabe_nimmt_das_letzte(self):
        self.assertEqual(ll.json_aus_ausgabe('{"x": 1}\n{"x": 2}\n'), {"x": 2})

    def test_sicherer_name(self):
        self.assertEqual(ll.sicherer_name("einzel-ORB (xperp)"), "einzel-ORB_xperp")
        self.assertEqual(ll.sicherer_name("///"), "lauf")

    def test_zeitstempel_format(self):
        self.assertRegex(ll.zeitstempel(), r"^\d{8}-\d{6}$")


class Liste(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.o = Path(self.tmp.name)

    def _lauf(self, datei, **felder):
        d = {"name": "a", "befehl": ["py", "x.py"], "start": "s", "ende": "e",
             "dauer_s": 75.0, "exit_code": 0, "abgebrochen": False, "ausgabe": ""}
        d.update(felder)
        (self.o / datei).write_text(json.dumps(d), encoding="utf-8")

    def test_neueste_zuerst_unlesbar_benannt_vorschau_ausgelassen(self):
        self._lauf("20260101-000000-a.json")
        (self.o / "20260102-000000-b.json").write_text("{kaputt", encoding="utf-8")
        (self.o / "20260103-000000-urteile-vorschau.json").write_text("{}",
                                                                    encoding="utf-8")
        liste = ll.laufliste(self.o)
        self.assertEqual([d["datei"] for d in liste],
                         ["20260102-000000-b.json", "20260101-000000-a.json"])
        self.assertEqual(liste[0]["name"], "nicht lesbar")
        zeilen = ll.listen_zeilen(liste)
        self.assertEqual(zeilen[0][1], "nicht lesbar")
        self.assertEqual(zeilen[1], ("20260101-000000-a.json", "a", "s", "1:15", "ok"))

    def test_ergebnisspalte(self):
        self._lauf("1.json", abgebrochen=True, exit_code=1)
        self._lauf("2.json", exit_code=2)
        erg = {z[0]: z[4] for z in ll.listen_zeilen(ll.laufliste(self.o))}
        self.assertEqual(erg, {"1.json": "abgebrochen", "2.json": "Exit 2"})

    def test_fehlender_ordner_ist_leere_liste(self):
        self.assertEqual(ll.laufliste(self.o / "gibtsnicht"), [])


class Vergleich(unittest.TestCase):
    A = {"ergebnis": {"spur": "squeeze", "runden": 10, "kennzahlen": {"ev": 0.5}}}
    B = {"ergebnis": {"spur": "squeeze", "runden": 12,
                      "kennzahlen": {"ev": 0.25, "neu": 1}}}

    def test_nebeneinander_mit_differenz(self):
        z = {r[0]: r[1:] for r in ll.vergleich(self.A, self.B)}
        self.assertEqual(z["runden"], ("10", "12", "2"))
        self.assertEqual(z["ev"], ("0.5", "0.25", "-0.25"))
        self.assertEqual(z["neu"], ("", "1", ""))
        self.assertEqual(z["spur"], ("squeeze", "squeeze", ""))

    def test_ohne_ergebnis_wirft(self):
        with self.assertRaises(ValueError):
            ll.vergleich(self.A, {"ausgabe": "x"})

    def test_einzelergebnis_und_gegenprobe(self):
        z = ll.ergebnis_zeilen({"ergebnis": {"gleich": True, "abweichungen": [],
                                             "runden": 4, "runden_alt": 4}})
        self.assertIn(("gleich", "True", "", ""), z)
        self.assertEqual(ll.ergebnis_zeilen({}),
                         [("Ergebnis", "kein Replay-Ergebnis", "", "")])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen lassen — er muss scheitern**

Run: `$PY -m unittest tests.test_leitstand_backtests_lauf -v`
Erwartet: `ModuleNotFoundError: No module named 'leitstand_laeufe'`.

- [ ] **Step 3: `leitstand_laeufe.py` schreiben**

```python
"""Laeufe des Leitstands: ein Prozess zur Zeit, abbrechbar, abgelegt.

Jeder Backtest, jede Optimierung und jede Urteils-Vorschau laeuft hierueber:
  * hoechstens EIN Lauf gleichzeitig (Steuerung.starte wirft sonst),
  * niedrige Prioritaet (Windows: BELOW_NORMAL_PRIORITY_CLASS), Arbeitsordner
    ist Handel/, stdout und stderr zusammen, zeilenweise ueber eine Queue,
  * Abbrechen beendet den ganzen Prozessbaum (Windows: taskkill /T /F).
    backtest_urteile.py startet seine Motoren als Kindprozesse; terminate()
    allein liesse sie bis zu 15 min weiterrechnen.
  * Ablage backtest_laeufe/<JJJJMMTT-hhmmss>-<name>.json, Ausgabe auf 1 MB
    gekuerzt. Der Ordner ist nicht versioniert und wird von keinem
    Betriebsteil gelesen.
"""

import json
import os
import queue
import re
import signal
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
ABLAGE = HIER / "backtest_laeufe"
MAX_AUSGABE = 1_000_000           # Zeichen der Ausgabe in der Ablage
ABBRUCH_WARTEN_S = 5              # ausserhalb Windows: terminate, dann kill
BELOW_NORMAL = 0x00004000         # BELOW_NORMAL_PRIORITY_CLASS
OHNE_FENSTER = 0x08000000         # CREATE_NO_WINDOW fuer taskkill
VORSCHAU_ENDUNG = "-vorschau.json"

LISTE_SPALTEN = ("Datei", "Lauf", "Start", "Dauer", "Ergebnis")
KENNZAHL_SPALTEN = ("Kennzahl", "A", "B", "Differenz B−A")
_KOPF = ("spur", "runden", "offen", "gebuehr_pct", "fenster", "kerzenquelle",
         "gleich", "abweichungen", "runden_alt")


# --- Hilfen -----------------------------------------------------------------

def zeitstempel(jetzt=None):
    return (jetzt or datetime.now()).strftime("%Y%m%d-%H%M%S")


def sicherer_name(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(name)).strip("_") or "lauf"


def kuerze(text, grenze=MAX_AUSGABE):
    """Das ENDE behalten: dort stehen Kennzahlen und Urteil."""
    if len(text) <= grenze:
        return text
    return ("[… %d Zeichen am Anfang gekürzt]\n" % (len(text) - grenze)
            + text[-grenze:])


def json_aus_ausgabe(text):
    """Das letzte JSON-Objekt, das am Anfang einer Zeile beginnt, oder None.

    Davor koennen Hinweise stehen ("Zeitraum angehoben: ..."), danach
    Schlusszeilen ("Trockenlauf: nichts gerechnet ..."). Eingerueckte
    Klammern (verschachtelte Objekte) beginnen nie am Zeilenanfang.
    """
    dec = json.JSONDecoder()
    letztes = None
    for m in re.finditer(r"(?m)^\{", text):
        try:
            obj, _ende = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(obj, dict):
            letztes = obj
    return letztes


def _schreib_json(pfad, daten):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, pfad)


def _jetzt_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _posix_start():
    os.setsid()                   # eigene Prozessgruppe: killpg trifft den Baum
    os.nice(10)


# --- ein Lauf ---------------------------------------------------------------

class Lauf:
    def __init__(self, name, befehl, ablage=None, stempel=None, auswerten=None):
        self.name, self.befehl = name, [str(b) for b in befehl]
        self.ablage = Path(ablage or ABLAGE)
        self.stempel = stempel or zeitstempel()
        self.auswerten = auswerten
        self.pfad = self.ablage / ("%s-%s.json" % (self.stempel, sicherer_name(name)))
        self.zeilen, self.abgebrochen, self.exit_code = [], False, None
        self.start = _jetzt_iso()
        self._t0 = time.monotonic()
        self._q = queue.Queue()
        self._eof = False
        umgebung = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        kw = ({"creationflags": BELOW_NORMAL} if os.name == "nt"
              else {"preexec_fn": _posix_start})
        self.proc = subprocess.Popen(
            self.befehl, cwd=str(HIER), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1, env=umgebung, **kw)
        threading.Thread(target=self._lesen, daemon=True).start()

    def _lesen(self):
        try:
            for zeile in self.proc.stdout:
                self._q.put(zeile)
        finally:
            self._q.put(None)

    def neue_zeilen(self):
        neu = []
        while not self._eof:
            try:
                z = self._q.get_nowait()
            except queue.Empty:
                break
            if z is None:
                self._eof = True
            else:
                neu.append(z)
        self.zeilen.extend(neu)
        return neu

    def fertig(self):
        return self._eof and self.proc.poll() is not None

    def verstrichen_s(self):
        return time.monotonic() - self._t0

    def abbrechen(self):
        if self.proc.poll() is not None:
            return
        self.abgebrochen = True
        if os.name == "nt":
            r = subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=OHNE_FENSTER)
            if r.returncode != 0 and self.proc.poll() is None:
                self.proc.kill()
            return
        try:
            os.killpg(self.proc.pid, signal.SIGTERM)
        except OSError:
            return
        threading.Thread(target=self._nachfassen, daemon=True).start()

    def _nachfassen(self):
        try:
            self.proc.wait(ABBRUCH_WARTEN_S)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except OSError:
                pass

    def abschliessen(self):
        """Nach fertig(): Ablage schreiben. Gibt (Pfad, Daten) zurueck."""
        self.exit_code = self.proc.wait()
        self.neue_zeilen()
        ausgabe = "".join(self.zeilen)
        daten = {"name": self.name, "befehl": self.befehl, "start": self.start,
                 "ende": _jetzt_iso(), "dauer_s": round(self.verstrichen_s(), 1),
                 "exit_code": self.exit_code, "abgebrochen": self.abgebrochen,
                 "ausgabe": kuerze(ausgabe)}
        if self.auswerten:
            daten["ergebnis"] = self.auswerten(ausgabe)
        try:
            _schreib_json(self.pfad, daten)
        except OSError as e:
            daten["ablage_fehler"] = str(e)
        return self.pfad, daten


class Steuerung:
    """Hoechstens ein Lauf. Der Reiter ruft takt() alle 200 ms."""

    def __init__(self, ablage=None):
        self.ablage = ablage
        self.lauf = None

    def laeuft(self):
        return self.lauf is not None

    def starte(self, name, befehl, auswerten=None, stempel=None):
        if self.lauf is not None:
            raise RuntimeError("es läuft schon: %s" % self.lauf.name)
        self.lauf = Lauf(name, befehl, self.ablage, stempel, auswerten)
        return self.lauf

    def abbrechen(self):
        if self.lauf is not None:
            self.lauf.abbrechen()

    def takt(self):
        """(neue Zeilen, (Pfad, Daten) oder None)."""
        if self.lauf is None:
            return [], None
        neu = self.lauf.neue_zeilen()
        if not self.lauf.fertig():
            return neu, None
        ende = self.lauf.abschliessen()
        self.lauf = None
        return neu, ende

    def status(self):
        if self.lauf is None:
            return ""
        s = int(self.lauf.verstrichen_s())
        return "Backtest: %s läuft seit %d:%02d" % (self.lauf.name, s // 60, s % 60)


# --- Laufliste und Vergleich ------------------------------------------------

def lade_lauf(pfad):
    try:
        d = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) and "befehl" in d else None


def laufliste(ablage=None):
    ordner = Path(ablage or ABLAGE)
    try:
        namen = sorted((p.name for p in ordner.glob("*.json")
                        if not p.name.endswith(VORSCHAU_ENDUNG)), reverse=True)
    except OSError:
        return []
    aus = []
    for n in namen:
        d = lade_lauf(ordner / n)
        aus.append(dict(d, datei=n) if d else {"datei": n, "name": "nicht lesbar"})
    return aus


def listen_zeilen(liste):
    zeilen = []
    for d in liste:
        if "befehl" not in d:
            zeilen.append((d["datei"], "nicht lesbar", "", "", ""))
            continue
        if d.get("abgebrochen"):
            erg = "abgebrochen"
        elif d.get("exit_code") == 0:
            erg = "ok"
        else:
            erg = "Exit %s" % d.get("exit_code")
        dauer = d.get("dauer_s")
        dauer_t = ("%d:%02d" % divmod(int(dauer), 60)
                   if isinstance(dauer, (int, float)) else "")
        zeilen.append((d["datei"], d.get("name", ""), d.get("start", ""), dauer_t, erg))
    return zeilen


def _zahl(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return ("%.4f" % v).rstrip("0").rstrip(".")
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)[:80]
    return str(v)


def kennzahlen_flach(daten):
    """Replay-Ergebnis als geordnete Liste (Name, Wert); None ohne Ergebnis."""
    e = (daten or {}).get("ergebnis")
    if not isinstance(e, dict):
        return None
    aus = [(k, e[k]) for k in _KOPF if k in e]
    k = e.get("kennzahlen")
    if isinstance(k, dict):
        aus += list(k.items())
    return aus


def ergebnis_zeilen(daten):
    k = kennzahlen_flach(daten)
    if k is None:
        return [("Ergebnis", "kein Replay-Ergebnis", "", "")]
    return [(n, _fmt(v), "", "") for n, v in k]


def vergleich(a, b):
    ka, kb = kennzahlen_flach(a), kennzahlen_flach(b)
    if ka is None or kb is None:
        raise ValueError("Vergleich nur zwischen zwei Replay-Läufen mit Ergebnis")
    da, db = dict(ka), dict(kb)
    namen = [n for n, _ in ka] + [n for n, _ in kb if n not in da]
    zeilen = []
    for n in namen:
        va, vb = da.get(n), db.get(n)
        diff = _fmt(vb - va) if _zahl(va) and _zahl(vb) else ""
        zeilen.append((n, _fmt(va), _fmt(vb), diff))
    return zeilen
```

- [ ] **Step 4: Tests laufen lassen**

Run: `$PY -m unittest tests.test_leitstand_backtests_lauf -v`
Erwartet: alle grün. `test_abbruch_beendet_auch_kindprozesse` dauert etwa 3 s.

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage aus Aufgabe 1 bleibt unverändert.

- [ ] **Step 5: Commit**

```bash
git status --short
git add Agenten/Handel/leitstand_laeufe.py Agenten/Handel/tests/test_leitstand_backtests_lauf.py
git commit -m "Leitstand: Laufsteuerung mit Ablage, Abbruch des ganzen Prozessbaums, Vergleich (Aufgabe 6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Backtest-Reiter mit Replay `leitstand_backtests.py`

**Files:**
- Create: `Agenten/Handel/leitstand_backtests.py`
- Test: `Agenten/Handel/tests/test_leitstand_backtests.py`

**Interfaces:**
- Consumes:
  - aus Aufgabe 4: `Tabelle`, `Tooltip`, `setze_knopf`, `Zustand`;
  - aus Aufgabe 6: `ll.Steuerung`, `ll.zeitstempel`, `ll.json_aus_ausgabe`, `ll.laufliste`, `ll.listen_zeilen`, `ll.lade_lauf`, `ll.ergebnis_zeilen`, `ll.vergleich`, `ll.LISTE_SPALTEN`, `ll.KENNZAHL_SPALTEN`, `ll.ABLAGE`;
  - `replay.SPUREN_TEIL_A`, `replay.NICHT_NACHRECHENBAR`.
- Produces:
  - `HIER`, `HINWEIS_FREIGABE`, `TAKT_MS = 200`, `REPLAY_VORGABEN`;
  - `replay_spuren() -> list[str]`, `nicht_nachrechenbar() -> list[(spur, grund)]`;
  - `pruefe_replay(werte: dict) -> (list[str] | None, str)`, `replay_befehl(teile, stempel) -> list[str]`;
  - **Bereich-Schnittstelle** (Aufgaben 8, 9, 11): `class XBereich(ttk.Frame)` mit `TITEL: str`, `__init__(self, eltern, reiter)`, `lauf_wechsel(self, laeuft: bool)`, `refresh(self)`;
  - `class BacktestReiter(ttk.Frame)(eltern, leitstand, steuerung=None, bereiche=None)` mit der Reiter-Schnittstelle. Für die Bereiche stellt es bereit: `.ls`, `.zustand`, `.steuerung`, `.ablage() -> Path`, `.starte(name, befehl, auswerten=None, fertig=None, stempel=None) -> bool` (`fertig(pfad, daten)` wird nach dem Ende gerufen), `.schreibe(text)`;
  - `BEREICHE: list` — hier `[ReplayBereich]`, erweitert in den Aufgaben 8, 9 und 11.

`bereiche=None` bedeutet: die Modulliste `BEREICHE`, zur Laufzeit gelesen.

- [ ] **Step 1: Tests schreiben**

`tests/test_leitstand_backtests.py`:

```python
"""Backtest-Reiter: Replay-Befehl, feste Hinweiszeile, ein Lauf gleichzeitig,
Kennzahlen nach dem Ende, unlesbare Ablage.

Die Laufsteuerung ist eine Attrappe (kein Prozess); die echte ist in
test_leitstand_backtests_lauf.py geprueft. Ablage und Zustand liegen in einem
Temp-Ordner. Tk-Teile werden ohne Bildschirm uebersprungen.

Direkt ausfuehrbar:  python tests/test_leitstand_backtests.py
"""

import json
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand_backtests as lbt                              # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_laeufe as ll                                  # noqa: E402
import replay                                                  # noqa: E402


class StubLeitstand:
    def __init__(self, root, zustand):
        self.root, self.zustand, self.meldungen = root, zustand, []

    def melde(self, text):
        self.meldungen.append(text)


class FakeSteuerung:
    def __init__(self, ablage):
        self.ablage, self.gestartet, self.lauf = ablage, [], None
        self.naechstes = ([], None)

    def starte(self, name, befehl, auswerten=None, stempel=None):
        if self.lauf:
            raise RuntimeError("es läuft schon: %s" % self.lauf)
        self.lauf = name
        self.gestartet.append((name, list(befehl), auswerten, stempel))
        return SimpleNamespace(name=name, befehl=list(befehl))

    def laeuft(self):
        return self.lauf is not None

    def abbrechen(self):
        pass

    def takt(self):
        erg, self.naechstes = self.naechstes, ([], None)
        if erg[1]:
            self.lauf = None
        return erg

    def status(self):
        return "Backtest: %s läuft seit 0:01" % self.lauf if self.lauf else ""


class Replay(unittest.TestCase):
    def test_angeboten_wird_nur_teil_a(self):
        self.assertEqual(lbt.replay_spuren(), list(replay.SPUREN_TEIL_A))
        for spur, _grund in lbt.nicht_nachrechenbar():
            self.assertNotIn(spur, lbt.replay_spuren())

    def test_befehl_mit_allen_feldern(self):
        teile, fehler = lbt.pruefe_replay({"spur": "squeeze", "max_kerzen": "2000",
                                           "gebuehr": "0,2", "gegenprobe": True})
        self.assertEqual(fehler, "")
        self.assertEqual(teile, ["--spur", "squeeze", "--gebuehr", "0.2",
                                 "--max-kerzen", "2000", "--gegenprobe"])
        b = lbt.replay_befehl(teile, "20260929-120000")
        self.assertEqual(b[0], sys.executable)
        self.assertEqual(b[1], "replay.py")
        self.assertEqual(b[-2:], ["--lauf", "leitstand-20260929-120000"])

    def test_null_kerzen_heisst_alle(self):
        teile, _f = lbt.pruefe_replay({"spur": "gitter", "max_kerzen": "0",
                                       "gebuehr": "0.1", "gegenprobe": False})
        self.assertEqual(teile, ["--spur", "gitter", "--gebuehr", "0.1"])

    def test_ungueltige_eingaben(self):
        for werte in ({"spur": "nautilus", "max_kerzen": "0", "gebuehr": "0.1"},
                      {"spur": "squeeze", "max_kerzen": "x", "gebuehr": "0.1"},
                      {"spur": "squeeze", "max_kerzen": "0", "gebuehr": "abc"},
                      {"spur": "squeeze", "max_kerzen": "0", "gebuehr": "9"},
                      {"spur": "squeeze", "max_kerzen": "-5", "gebuehr": "0.1"}):
            teile, fehler = lbt.pruefe_replay(werte)
            self.assertIsNone(teile, werte)
            self.assertTrue(fehler)


class TkBasis(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ablage = Path(self.tmp.name) / "ablage"
        self.ablage.mkdir()
        self.ls = StubLeitstand(self.root,
                                lb.Zustand(Path(self.tmp.name) / "z.json"))
        self.st = FakeSteuerung(self.ablage)

    def reiter(self, bereiche=None):
        r = lbt.BacktestReiter(self.root, self.ls, steuerung=self.st,
                               bereiche=bereiche)
        self.root.update_idletasks()
        return r


def _alle_texte(widget):
    aus = []
    for k in widget.winfo_children():
        try:
            aus.append(str(k.cget("text")))
        except tk.TclError:
            pass
        aus += _alle_texte(k)
    return aus


class Reiter(TkBasis):
    def test_feste_hinweiszeile(self):
        r = self.reiter()
        self.assertIn(lbt.HINWEIS_FREIGABE, _alle_texte(r))

    def test_start_uebergibt_befehl_und_merkt_werte(self):
        r = self.reiter([lbt.ReplayBereich])
        b = r.bereiche[0]
        b.w_spur.set("squeeze")
        b.w_kerzen.set("1500")
        b.w_gebuehr.set("0.1")
        b.w_gegen.set(True)
        b.starten()
        name, befehl, auswerten, stempel = self.st.gestartet[0]
        self.assertEqual(name, "replay-squeeze")
        self.assertIn("--gegenprobe", befehl)
        self.assertEqual(befehl[-1], "leitstand-" + stempel)
        self.assertIs(auswerten, ll.json_aus_ausgabe)
        self.assertEqual(self.ls.zustand.get("werte")["replay"]["max_kerzen"], "1500")
        self.assertIn("disabled", b.k_start.state())

    def test_ungueltige_gebuehr_startet_nicht(self):
        r = self.reiter([lbt.ReplayBereich])
        r.bereiche[0].w_gebuehr.set("viel")
        r.bereiche[0].starten()
        self.assertEqual(self.st.gestartet, [])
        self.assertIn("Gebühr", self.ls.meldungen[-1])

    def test_zweiter_start_meldet_statt_zu_starten(self):
        r = self.reiter([lbt.ReplayBereich])
        self.assertTrue(r.starte("a", ["x"]))
        self.assertFalse(r.starte("b", ["y"]))
        self.assertEqual(self.ls.meldungen[-1], "es läuft schon: a")
        self.assertEqual(len(self.st.gestartet), 1)

    def test_lauf_ende_zeigt_kennzahlen_und_gibt_start_frei(self):
        r = self.reiter([lbt.ReplayBereich])
        rueck = []
        r.starte("replay-squeeze", ["x"], fertig=lambda p, d: rueck.append(d))
        daten = {"name": "replay-squeeze", "exit_code": 0, "abgebrochen": False,
                 "ergebnis": {"spur": "squeeze", "runden": 10}}
        self.st.naechstes = (["fertig\n"], (self.ablage / "x.json", daten))
        r._takt()
        self.assertIn(("runden", "10", "", ""), r.ergebnis.sichtbare())
        self.assertEqual(self.ls.meldungen[-1], "replay-squeeze fertig")
        self.assertEqual(rueck, [daten])
        self.assertNotIn("disabled", r.bereiche[0].k_start.state())
        self.assertIn("fertig", r.w_ausgabe.get("1.0", "end"))

    def test_abgebrochen_und_exit_code_werden_gemeldet(self):
        r = self.reiter([])
        r.starte("a", ["x"])
        self.st.naechstes = ([], (self.ablage / "a.json",
                                  {"name": "a", "exit_code": 1, "abgebrochen": True}))
        r._takt()
        self.assertEqual(self.ls.meldungen[-1], "a abgebrochen")
        r.starte("b", ["x"])
        self.st.naechstes = ([], (self.ablage / "b.json",
                                  {"name": "b", "exit_code": 4, "abgebrochen": False}))
        r._takt()
        self.assertEqual(self.ls.meldungen[-1], "b endete mit Exit 4")

    def test_unlesbare_ablage_steht_als_nicht_lesbar_in_der_liste(self):
        (self.ablage / "20260929-120000-x.json").write_text("{kaputt",
                                                            encoding="utf-8")
        r = self.reiter([])
        r.refresh()
        self.assertEqual(r.liste.sichtbare()[0][1], "nicht lesbar")

    def test_vergleichen_zweier_laeufe(self):
        for datei, runden in (("20260929-120000-a.json", 10),
                              ("20260929-130000-b.json", 12)):
            (self.ablage / datei).write_text(json.dumps(
                {"name": datei, "befehl": ["x"], "exit_code": 0,
                 "ergebnis": {"runden": runden}}), encoding="utf-8")
        r = self.reiter([])
        r.refresh()
        for iid in r.liste.baum.get_children():
            r.liste.baum.selection_add(iid)
        r.vergleichen()
        self.assertIn(("runden", "10", "12", "2"), r.ergebnis.sichtbare())

    def test_titel_und_status_waehrend_eines_laufs(self):
        r = self.reiter([])
        self.assertEqual(r.titel_zusatz(), "")
        r.starte("a", ["x"])
        self.assertEqual(r.titel_zusatz(), " ●")
        self.assertEqual(r.status(), "Backtest: a läuft seit 0:01")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen lassen — er muss scheitern**

Run: `$PY -m unittest tests.test_leitstand_backtests -v`
Erwartet: `ModuleNotFoundError: No module named 'leitstand_backtests'`.

- [ ] **Step 3: `leitstand_backtests.py` schreiben**

```python
"""Backtest-Reiter des Leitstands.

Vier Bereiche teilen sich eine Laufsteuerung (ein Lauf gleichzeitig), ein
Ausgabefeld und die Laufliste: Replay (Hauptweg), Einzelskripte, Optimieren,
Urteile. Jeder Bereich ist ein Frame mit TITEL, lauf_wechsel(laeuft) und
refresh(); er startet ueber reiter.starte(...).

Backtest-Runden zaehlen NICHT fuer die Freigabe (Design Backtest-Fundament);
der Reiter sagt das in einer festen Zeile.
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import leitstand_laeufe as ll
import replay
from leitstand_bedienung import Tabelle, Tooltip, setze_knopf

HIER = Path(__file__).resolve().parent
HINWEIS_FREIGABE = ("Backtest-Runden zählen nicht für die Freigabe — dafür zählen "
                    "nur Papier-Runden und der Freigaben-Reiter.")
TAKT_MS = 200
MAX_TEXT_ZEILEN = 5000
REPLAY_VORGABEN = {"spur": replay.SPUREN_TEIL_A[0], "max_kerzen": "0",
                   "gebuehr": "0.1", "gegenprobe": False}


# --- Replay: reine Funktionen -----------------------------------------------

def replay_spuren():
    return list(replay.SPUREN_TEIL_A)


def nicht_nachrechenbar():
    return sorted(replay.NICHT_NACHRECHENBAR.items())


def pruefe_replay(werte):
    """(Argumente ohne Interpreter und --lauf, "") oder (None, Fehlertext)."""
    spur = werte.get("spur")
    if spur not in replay.SPUREN_TEIL_A:
        return None, "Spur %r ist nicht nachrechenbar" % spur
    try:
        mk = int(str(werte.get("max_kerzen") or "0").strip())
    except ValueError:
        return None, "Max. Kerzen: ganze Zahl erwartet (0 = alle)"
    try:
        g = float(str(werte.get("gebuehr", "")).strip().replace(",", "."))
    except ValueError:
        return None, "Gebühr: Zahl erwartet (Prozent je Seite)"
    if not 0 <= mk <= 1_000_000:
        return None, "Max. Kerzen: 0 bis 1 000 000"
    if not 0 <= g <= 5:
        return None, "Gebühr: 0 bis 5 %"
    teile = ["--spur", spur, "--gebuehr", repr(g)]
    if mk:
        teile += ["--max-kerzen", str(mk)]
    if werte.get("gegenprobe"):
        teile.append("--gegenprobe")
    return teile, ""


def replay_befehl(teile, stempel):
    """Eigener Laufname: ein Leitstand-Lauf ueberschreibt keinen anderen."""
    return [sys.executable, "replay.py"] + list(teile) + ["--lauf",
                                                         "leitstand-" + stempel]


# --- Bereich Replay ---------------------------------------------------------

class ReplayBereich(ttk.Frame):
    TITEL = "Replay"

    def __init__(self, eltern, reiter):
        super().__init__(eltern, padding=8)
        self.reiter = reiter
        g = dict(REPLAY_VORGABEN,
                 **((reiter.zustand.get("werte") or {}).get("replay") or {}))
        if g["spur"] not in replay.SPUREN_TEIL_A:
            g["spur"] = REPLAY_VORGABEN["spur"]
        self.w_spur = tk.StringVar(value=g["spur"])
        self.w_kerzen = tk.StringVar(value=str(g["max_kerzen"]))
        self.w_gebuehr = tk.StringVar(value=str(g["gebuehr"]))
        self.w_gegen = tk.BooleanVar(value=bool(g["gegenprobe"]))

        ttk.Label(self, text="Spur").grid(row=0, column=0, sticky="w")
        ttk.Combobox(self, textvariable=self.w_spur, values=replay_spuren(),
                     state="readonly", width=18).grid(row=0, column=1, sticky="w")
        ttk.Label(self, text="Max. Kerzen (0 = alle)").grid(row=1, column=0,
                                                           sticky="w")
        ttk.Spinbox(self, textvariable=self.w_kerzen, from_=0, to=1_000_000,
                    increment=500, width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(self, text="Gebühr % je Seite").grid(row=2, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.w_gebuehr, width=10).grid(row=2, column=1,
                                                                    sticky="w")
        ttk.Checkbutton(self, text="Gegenprobe (alter gegen neuen Kern)",
                        variable=self.w_gegen).grid(row=3, column=0, columnspan=2,
                                                    sticky="w")
        self.k_start = ttk.Button(self, text="Replay starten", command=self.starten)
        self.k_start.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.tip = Tooltip(self.k_start)

        ttk.Label(self, text="Nicht nachrechenbar:").grid(row=0, column=2,
                                                          sticky="nw", padx=(24, 4))
        grau = tk.Text(self, height=6, width=60, foreground="#888888",
                       relief="flat", wrap="none")
        grau.insert("1.0", "\n".join("%s — %s" % p for p in nicht_nachrechenbar()))
        grau.configure(state="disabled")
        grau.grid(row=0, column=3, rowspan=5, sticky="nsew")
        self.columnconfigure(3, weight=1)

    def werte(self):
        return {"spur": self.w_spur.get(),
                "max_kerzen": self.w_kerzen.get().strip() or "0",
                "gebuehr": self.w_gebuehr.get().strip(),
                "gegenprobe": bool(self.w_gegen.get())}

    def starten(self):
        teile, fehler = pruefe_replay(self.werte())
        if teile is None:
            self.reiter.ls.melde(fehler)
            return
        self.reiter.zustand.merke_in("werte", "replay", self.werte())
        stempel = ll.zeitstempel()
        self.reiter.starte("replay-%s" % self.w_spur.get(),
                           replay_befehl(teile, stempel),
                           auswerten=ll.json_aus_ausgabe, stempel=stempel)

    def lauf_wechsel(self, laeuft):
        setze_knopf(self.k_start, self.tip, not laeuft, "es läuft schon ein Lauf")

    def refresh(self):
        pass


# --- der Reiter -------------------------------------------------------------

class BacktestReiter(ttk.Frame):
    def __init__(self, eltern, leitstand, steuerung=None, bereiche=None):
        super().__init__(eltern, padding=6)
        self.ls, self.zustand = leitstand, leitstand.zustand
        self.steuerung = steuerung or ll.Steuerung()
        self._fertig = None
        self._liste = []

        ttk.Label(self, text=HINWEIS_FREIGABE, foreground="#b35c00").pack(
            anchor="w", pady=(0, 4))
        teiler = ttk.PanedWindow(self, orient="vertical")
        teiler.pack(fill="both", expand=True)

        self.arten = ttk.Notebook(teiler)
        teiler.add(self.arten, weight=2)
        self.bereiche = []
        for klasse in (BEREICHE if bereiche is None else bereiche):
            b = klasse(self.arten, self)
            self.arten.add(b, text=b.TITEL)      # Instanz: Fabriken erlaubt
            self.bereiche.append(b)

        mitte = ttk.Frame(teiler)
        teiler.add(mitte, weight=2)
        kopf = ttk.Frame(mitte)
        kopf.pack(fill="x")
        self.w_lauf = ttk.Label(kopf, text="kein Lauf")
        self.w_lauf.pack(side="left")
        self.k_abbrechen = ttk.Button(kopf, text="Abbrechen", command=self.abbrechen)
        self.k_abbrechen.pack(side="right")
        self.tip_abbrechen = Tooltip(self.k_abbrechen)
        self.w_ausgabe = tk.Text(mitte, height=10, wrap="none", state="disabled",
                                 font=("Consolas", 9))
        leiste = ttk.Scrollbar(mitte, orient="vertical", command=self.w_ausgabe.yview)
        self.w_ausgabe.configure(yscrollcommand=leiste.set)
        self.w_ausgabe.pack(side="left", fill="both", expand=True)
        leiste.pack(side="right", fill="y")

        unten = ttk.PanedWindow(teiler, orient="horizontal")
        teiler.add(unten, weight=1)
        links = ttk.Frame(unten)
        unten.add(links, weight=1)
        self.liste = Tabelle(links, ll.LISTE_SPALTEN, self.zustand, "laeufe",
                             hoehe=6, auswahl="extended")
        self.liste.pack(fill="both", expand=True)
        knoepfe = ttk.Frame(links)
        knoepfe.pack(fill="x", pady=(4, 0))
        ttk.Button(knoepfe, text="Anzeigen", command=self.anzeigen).pack(side="left")
        ttk.Button(knoepfe, text="Vergleichen",
                   command=self.vergleichen).pack(side="left", padx=4)
        self.ergebnis = Tabelle(unten, ll.KENNZAHL_SPALTEN, self.zustand,
                                "kennzahlen", hoehe=6)
        unten.add(self.ergebnis, weight=1)

        self._lauf_wechsel(self.steuerung.laeuft())
        self.refresh()
        self.after(TAKT_MS, self._takt)

    # Reiter-Schnittstelle
    def refresh(self):
        self.refresh_liste()
        for b in self.bereiche:
            b.refresh()

    def titel_zusatz(self):
        return " ●" if self.steuerung.laeuft() else ""

    def status(self):
        return self.steuerung.status()

    # fuer die Bereiche
    def ablage(self):
        return Path(self.steuerung.ablage or ll.ABLAGE)

    def starte(self, name, befehl, auswerten=None, fertig=None, stempel=None):
        try:
            lauf = self.steuerung.starte(name, befehl, auswerten, stempel)
        except RuntimeError as e:
            self.ls.melde(str(e))
            return False
        except OSError as e:
            self.ls.melde("Start fehlgeschlagen: %s" % e)
            return False
        self._fertig = fertig
        self._leeren()
        self.schreibe("$ %s\n" % " ".join(lauf.befehl[1:]))
        self._lauf_wechsel(True)
        return True

    def schreibe(self, text):
        w = self.w_ausgabe
        w.configure(state="normal")
        w.insert("end", text)
        zeilen = int(w.index("end-1c").split(".")[0])
        if zeilen > MAX_TEXT_ZEILEN:
            w.delete("1.0", "%d.0" % (zeilen - MAX_TEXT_ZEILEN))
        w.see("end")
        w.configure(state="disabled")

    def _leeren(self):
        self.w_ausgabe.configure(state="normal")
        self.w_ausgabe.delete("1.0", "end")
        self.w_ausgabe.configure(state="disabled")

    # Ablauf
    def _takt(self):
        try:
            neu, ende = self.steuerung.takt()
            if neu:
                self.schreibe("".join(neu))
            if ende:
                self._lauf_ende(*ende)
            self.w_lauf.config(text=self.steuerung.status() or "kein Lauf")
        finally:
            try:
                self.after(TAKT_MS, self._takt)
            except tk.TclError:
                pass                       # Fenster ist zu

    def _lauf_ende(self, pfad, daten):
        rueck, self._fertig = self._fertig, None
        name = daten.get("name", "Lauf")
        if daten.get("abgebrochen"):
            self.ls.melde("%s abgebrochen" % name)
        elif daten.get("exit_code") == 0:
            self.ls.melde("%s fertig" % name)
        else:
            self.ls.melde("%s endete mit Exit %s" % (name, daten.get("exit_code")))
        if "ergebnis" in daten:
            self.ergebnis.setze(ll.ergebnis_zeilen(daten))
        self._lauf_wechsel(False)
        self.refresh_liste()
        if rueck:
            rueck(pfad, daten)

    def _lauf_wechsel(self, laeuft):
        setze_knopf(self.k_abbrechen, self.tip_abbrechen, laeuft, "kein Lauf")
        for b in self.bereiche:
            b.lauf_wechsel(laeuft)

    def abbrechen(self):
        if self.steuerung.laeuft():
            self.steuerung.abbrechen()
            self.ls.melde("Abbruch angefordert")

    # Laufliste
    def refresh_liste(self):
        self._liste = ll.laufliste(self.ablage())
        self.liste.setze(ll.listen_zeilen(self._liste))

    def _gewaehlte_laeufe(self):
        aus = []
        for zeile in self.liste.auswahl():
            d = ll.lade_lauf(self.ablage() / zeile[0])
            if d is None:
                self.ls.melde("%s nicht lesbar" % zeile[0])
                return None
            aus.append(dict(d, datei=zeile[0]))
        return aus

    def anzeigen(self):
        laeufe = self._gewaehlte_laeufe()
        if not laeufe:
            return
        d = laeufe[0]
        self._leeren()
        self.schreibe(d.get("ausgabe", ""))
        self.ergebnis.setze(ll.ergebnis_zeilen(d))

    def vergleichen(self):
        laeufe = self._gewaehlte_laeufe()
        if laeufe is None:
            return
        if len(laeufe) != 2:
            self.ls.melde("Vergleichen: genau zwei Läufe markieren")
            return
        # aelterer Lauf = A; Dateiname (beginnt mit dem Zeitstempel) als Ersatz
        a, b = sorted(laeufe, key=lambda d: (d.get("start", ""), d["datei"]))
        try:
            self.ergebnis.setze(ll.vergleich(a, b))
        except ValueError as e:
            self.ls.melde(str(e))


BEREICHE = [ReplayBereich]
```

- [ ] **Step 4: Tests laufen lassen**

Run: `$PY -m unittest tests.test_leitstand_backtests tests.test_leitstand_backtests_lauf -v`
Erwartet: alle grün.

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage bleibt unverändert.

- [ ] **Step 5: Commit**

```bash
git status --short
git add Agenten/Handel/leitstand_backtests.py Agenten/Handel/tests/test_leitstand_backtests.py
git commit -m "Leitstand: Backtest-Reiter mit Replay, Laufliste und Vergleich (Aufgabe 7)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Einzelskripte `leitstand_backtests.json`

**Files:**
- Create: `Agenten/Handel/leitstand_backtests.json`
- Modify: `Agenten/Handel/leitstand_backtests.py` (Einzelskripte, `BEREICHE`)
- Modify: `.gitignore` der Repo-Wurzel, nach Zeile 76 (`!Agenten/Handel/spur_opt.json`)
- Test: `Agenten/Handel/tests/test_leitstand_backtests_liste.py`, `Agenten/Handel/tests/test_leitstand_backtests.py` (Klasse `Einzel` dazu)

**Interfaces:**
- Consumes: Bereich-Schnittstelle und `BacktestReiter.starte` aus Aufgabe 7; `ll.sicherer_name` aus Aufgabe 6.
- Produces:
  - `LISTE: Path`, `VERBOTENE_FLAGS = ("--json", "--cache", "--lokal")`, `EIGENE_BEREICHE = ("optimieren.py", "backtest_urteile.py")`, `TYPEN = ("float", "int", "text", "wahl", "schalter")`;
  - `lade_liste(pfad=None) -> (list[dict], str)`, `eintrag_fehler(e) -> str`, `pruefe_feld(feld, wert) -> (list[str] | None, str)`, `einzel_befehl(eintrag, werte) -> (list[str] | None, str)`;
  - `class EinzelBereich(ttk.Frame)(eltern, reiter, pfad=None)`;
  - `BEREICHE = [ReplayBereich, EinzelBereich]`.

Format eines Eintrags: `name`, `skript` (relativ zu `Agenten/Handel`), `felder` (je `flag`, `typ`, `vorgabe`, bei Zahlen `min`/`max`, bei `wahl` die `werte`), `schreibt` (je `muster` und `kennung`: die Zeichenfolge, an der ein Leser zu erkennen wäre). Ein leerer Wert oder `null` lässt das Flag weg.

- [ ] **Step 1: Die Liste anlegen**

`leitstand_backtests.json` (LF, UTF-8):

```json
{
  "_zweck": "Welche Einzelskripte der Leitstand starten darf. Aufnahme nur nach Pruefung: keine Order-Funktion, kein Boersen-Client mit Schluessel, keine Datei aus 'schreibt' wird im Betrieb gelesen (docs/plans/2026-09-29-leitstand-plan.md, Befund 2). Nie --json, --cache oder --lokal. optimieren.py und backtest_urteile.py haben eigene Bereiche.",
  "eintraege": [
    {
      "name": "Gitter",
      "skript": "gitter/backtest_gitter.py",
      "felder": [
        {"flag": "--wochen", "typ": "float", "vorgabe": 8.0, "min": 1, "max": 104},
        {"flag": "--stufen", "typ": "int", "vorgabe": null, "min": 2, "max": 200},
        {"flag": "--spanne-prozent", "typ": "float", "vorgabe": null, "min": 0.5, "max": 50}
      ],
      "schreibt": []
    },
    {
      "name": "ORB (xperp)",
      "skript": "orb/backtest.py",
      "felder": [
        {"flag": "--instrument", "typ": "text", "vorgabe": "alle"},
        {"flag": "--jahre", "typ": "int", "vorgabe": 2, "min": 1, "max": 5},
        {"flag": "--modell", "typ": "wahl", "vorgabe": "beide", "werte": ["schluss", "naechste_eroeffnung", "beide"]},
        {"flag": "--raster", "typ": "schalter", "vorgabe": false}
      ],
      "schreibt": [{"muster": "orb/daten/<instrument>_M15.json", "kennung": "_M15"}]
    },
    {
      "name": "ORB (Kraken)",
      "skript": "orbk/backtest.py",
      "felder": [
        {"flag": "--instrument", "typ": "text", "vorgabe": "alle"},
        {"flag": "--jahre", "typ": "int", "vorgabe": 2, "min": 1, "max": 5},
        {"flag": "--modell", "typ": "wahl", "vorgabe": "beide", "werte": ["schluss", "naechste_eroeffnung", "beide"]},
        {"flag": "--raster", "typ": "schalter", "vorgabe": false}
      ],
      "schreibt": [{"muster": "orbk/daten/<instrument>_M15.json", "kennung": "_M15"}]
    },
    {
      "name": "Prognose-Spuren",
      "skript": "backtest_prognose.py",
      "felder": [
        {"flag": "--spur", "typ": "wahl", "vorgabe": "", "werte": ["", "squeeze", "wavetrend", "macd_mtf", "supertrend"]},
        {"flag": "--kerzen", "typ": "int", "vorgabe": 3000, "min": 100, "max": 20000},
        {"flag": "--gebuehr", "typ": "float", "vorgabe": 0.1, "min": 0, "max": 5},
        {"flag": "--takt", "typ": "wahl", "vorgabe": "", "werte": ["", "1H", "4H", "1D"]}
      ],
      "schreibt": [{"muster": "daten/backtest_kerzen/*.json", "kennung": "backtest_kerzen"}]
    },
    {
      "name": "Varianten (schnell)",
      "skript": "bt_varianten_fast.py",
      "felder": [],
      "schreibt": []
    }
  ]
}
```

Vor dem Anlegen prüfen, ob die Werte der `--modell`-Wahl noch stimmen: `grep -n "choices" orb/backtest.py orbk/backtest.py backtest_prognose.py`.

- [ ] **Step 2: Den Listentest schreiben**

`tests/test_leitstand_backtests_liste.py`:

```python
"""Die Liste der Einzelskripte haelt ihre Aufnahmebedingung - bei jedem Lauf.

  * jedes Skript existiert, jedes Flag steht in dessen add_argument (AST),
  * kein gesperrtes Flag (--json, --cache, --lokal),
  * optimieren.py und backtest_urteile.py stehen nicht drin,
  * keine Datei aus 'schreibt' wird im Betrieb gelesen: ihre Kennung kommt
    in dauerlauf.py, in keinem handeln.py/bot.py und in keiner Spur vor
    (ausser im gelisteten Skript selbst),
  * kein Skript enthaelt einen Order-Aufruf oder einen Schluessel.

Liest nur Quelltext. Direkt ausfuehrbar:  python tests/test_leitstand_backtests_liste.py
"""

import ast
import json
import re
import sys
import unittest
from pathlib import Path

HANDEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HANDEL))

import dauerlauf                                               # noqa: E402
import leitstand_backtests as lbt                              # noqa: E402

ORDER = re.compile(r"create_order|place_order|order_aufgeben|\.order\(|api_key|"
                   r"secret|private_key|ccxt\.\w+\(\{")


def _eintraege():
    return json.loads(lbt.LISTE.read_text(encoding="utf-8"))["eintraege"]


def _flags(skript):
    baum = ast.parse((HANDEL / skript).read_text(encoding="utf-8"))
    aus = set()
    for k in ast.walk(baum):
        if (isinstance(k, ast.Call) and isinstance(k.func, ast.Attribute)
                and k.func.attr == "add_argument"):
            aus |= {a.value for a in k.args
                    if isinstance(a, ast.Constant) and isinstance(a.value, str)}
    return aus


def _betriebsdateien(ausnahmen):
    dateien = {HANDEL / "dauerlauf.py", HANDEL / "bot.py"}
    dateien |= set(HANDEL.glob("*/handeln.py")) | set(HANDEL.glob("*/bot.py"))
    for info in dauerlauf.SPUREN.values():
        ordner = HANDEL / info.get("ordner", "")
        if ordner != HANDEL and ordner.is_dir():
            dateien |= set(ordner.glob("*.py"))
    return sorted(p for p in dateien
                  if p.is_file() and p.resolve() not in ausnahmen)


class Liste(unittest.TestCase):
    def test_jedes_skript_existiert(self):
        for e in _eintraege():
            self.assertTrue((HANDEL / e["skript"]).is_file(), e["skript"])

    def test_jedes_flag_steht_in_add_argument(self):
        for e in _eintraege():
            vorhanden = _flags(e["skript"])
            for f in e["felder"]:
                self.assertIn(f["flag"], vorhanden, "%s: %s" % (e["skript"], f["flag"]))

    def test_keine_gesperrten_flags(self):
        for e in _eintraege():
            for f in e["felder"]:
                self.assertNotIn(f["flag"], lbt.VERBOTENE_FLAGS, e["name"])

    def test_eigene_bereiche_stehen_nicht_drin(self):
        namen = {Path(e["skript"]).name for e in _eintraege()}
        self.assertFalse(namen & {"optimieren.py", "backtest_urteile.py"})

    def test_schreibt_wird_im_betrieb_nicht_gelesen(self):
        eintraege = _eintraege()
        ausnahmen = {(HANDEL / e["skript"]).resolve() for e in eintraege}
        dateien = _betriebsdateien(ausnahmen)
        self.assertIn(HANDEL / "dauerlauf.py", dateien)
        for e in eintraege:
            for s in e["schreibt"]:
                for p in dateien:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    self.assertNotIn(s["kennung"], text,
                                     "%s liest %s" % (p.relative_to(HANDEL), s["muster"]))

    def test_kein_order_aufruf_und_kein_schluessel(self):
        for e in _eintraege():
            text = (HANDEL / e["skript"]).read_text(encoding="utf-8")
            self.assertIsNone(ORDER.search(text), e["skript"])

    def test_die_liste_laedt_ohne_verworfene_eintraege(self):
        gut, fehler = lbt.lade_liste()
        self.assertEqual(fehler, "")
        self.assertEqual(len(gut), len(_eintraege()))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Die Klasse `Einzel` an `tests/test_leitstand_backtests.py` anhängen**

Vor `if __name__ == "__main__":` einfügen:

```python
EINTRAG = {"name": "Mini", "skript": "gitter/backtest_gitter.py", "schreibt": [],
           "felder": [
               {"flag": "--wochen", "typ": "float", "vorgabe": 8.0, "min": 1, "max": 104},
               {"flag": "--stufen", "typ": "int", "vorgabe": None, "min": 2, "max": 200},
               {"flag": "--modell", "typ": "wahl", "vorgabe": "beide",
                "werte": ["schluss", "beide"]},
               {"flag": "--instrument", "typ": "text", "vorgabe": "alle"},
               {"flag": "--raster", "typ": "schalter", "vorgabe": False}]}


class Einzel(unittest.TestCase):
    def test_befehl_aus_vorgaben(self):
        werte = {f["flag"]: f["vorgabe"] for f in EINTRAG["felder"]}
        befehl, fehler = lbt.einzel_befehl(EINTRAG, werte)
        self.assertEqual(fehler, "")
        self.assertEqual(befehl, [sys.executable, "gitter/backtest_gitter.py",
                                  "--wochen", "8.0", "--modell", "beide",
                                  "--instrument", "alle"])

    def test_schalter_und_leere_felder(self):
        befehl, _f = lbt.einzel_befehl(EINTRAG, {"--wochen": "", "--stufen": "12",
                                                 "--modell": "", "--instrument": "",
                                                 "--raster": True})
        self.assertEqual(befehl[2:], ["--stufen", "12", "--raster"])

    def test_ungueltige_werte(self):
        for flag, wert in (("--wochen", "200"), ("--wochen", "acht"),
                           ("--stufen", "1.5"), ("--modell", "alles"),
                           ("--instrument", "BTC; del *")):
            befehl, fehler = lbt.einzel_befehl(EINTRAG, {flag: wert})
            self.assertIsNone(befehl, (flag, wert))
            self.assertIn(flag, fehler)

    def test_liste_verwirft_gefaehrliche_eintraege(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "liste.json"
            p.write_text(json.dumps({"eintraege": [
                EINTRAG,
                dict(EINTRAG, name="Json", felder=[{"flag": "--json", "typ": "text"}]),
                dict(EINTRAG, name="Opt", skript="optimieren.py"),
                dict(EINTRAG, name="Weg", skript="../x.py"),
                dict(EINTRAG, name="Fehlt", skript="gibtsnicht.py")]}),
                encoding="utf-8")
            gut, fehler = lbt.lade_liste(p)
        self.assertEqual([e["name"] for e in gut], ["Mini"])
        for name in ("Json", "Opt", "Weg", "Fehlt"):
            self.assertIn(name, fehler)

    def test_unlesbare_liste(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "liste.json"
            p.write_text("{kaputt", encoding="utf-8")
            self.assertEqual(lbt.lade_liste(p),
                             ([], "leitstand_backtests.json nicht lesbar"))


class EinzelReiter(TkBasis):
    def _liste(self, eintraege):
        p = Path(self.tmp.name) / "liste.json"
        p.write_text(json.dumps({"eintraege": eintraege}), encoding="utf-8")
        return p

    def test_start_mit_feldern_aus_der_liste(self):
        p = self._liste([EINTRAG])
        r = lbt.BacktestReiter(self.root, self.ls, steuerung=self.st,
                               bereiche=[lambda e, rt: lbt.EinzelBereich(e, rt, p)])
        b = r.bereiche[0]
        b.vars["--wochen"].set("4")
        b.starten()
        name, befehl, _a, _s = self.st.gestartet[0]
        self.assertEqual(name, "einzel-Mini")
        self.assertEqual(befehl[1:4], ["gitter/backtest_gitter.py", "--wochen", "4.0"])
        self.assertEqual(self.ls.zustand.get("werte")["einzel"]["Mini"]["--wochen"], "4")

    def test_leere_liste_sperrt_start(self):
        p = self._liste([])
        r = lbt.BacktestReiter(self.root, self.ls, steuerung=self.st,
                               bereiche=[lambda e, rt: lbt.EinzelBereich(e, rt, p)])
        self.assertIn("disabled", r.bereiche[0].k_start.state())
```

Die Lambdas als Bereich-Fabrik funktionieren, weil `BacktestReiter` den Titel von der Instanz liest (`b.TITEL`, Aufgabe 7).

- [ ] **Step 4: Tests laufen lassen — sie müssen scheitern**

Run: `$PY -m unittest tests.test_leitstand_backtests_liste tests.test_leitstand_backtests -v`
Erwartet: `AttributeError: module 'leitstand_backtests' has no attribute 'LISTE'` bzw. `… 'einzel_befehl'`.

- [ ] **Step 5: Einzelskripte in `leitstand_backtests.py` einbauen**

Zu den Imports oben `import json` und `import re` ergänzen (alphabetisch vor `import sys`). Unter `REPLAY_VORGABEN` einfügen:

```python
LISTE = HIER / "leitstand_backtests.json"
VERBOTENE_FLAGS = ("--json", "--cache", "--lokal")
EIGENE_BEREICHE = ("optimieren.py", "backtest_urteile.py")
TYPEN = ("float", "int", "text", "wahl", "schalter")
_TEXT = re.compile(r"^[A-Za-z0-9_./-]{1,40}$")
```

Vor `# --- der Reiter ---` einfügen:

```python
# --- Einzelskripte ----------------------------------------------------------

def eintrag_fehler(e):
    """"" oder der Grund, warum der Eintrag nicht startbar ist."""
    if not isinstance(e, dict) or not isinstance(e.get("name"), str):
        return "Eintrag ohne Namen"
    name, skript = e["name"], e.get("skript")
    if (not isinstance(skript, str) or Path(skript).is_absolute()
            or ".." in Path(skript).parts):
        return "%s: Skriptpfad ungültig" % name
    if Path(skript).name in EIGENE_BEREICHE:
        return "%s: hat einen eigenen Bereich" % name
    if not (HIER / skript).is_file():
        return "%s: %s fehlt" % (name, skript)
    felder = e.get("felder")
    if not isinstance(felder, list):
        return "%s: felder fehlt" % name
    for f in felder:
        if (not isinstance(f, dict) or f.get("typ") not in TYPEN
                or not str(f.get("flag", "")).startswith("--")):
            return "%s: Feld ungültig" % name
        if f["flag"] in VERBOTENE_FLAGS:
            return "%s: %s ist gesperrt" % (name, f["flag"])
        if f["typ"] == "wahl" and not isinstance(f.get("werte"), list):
            return "%s: %s ohne werte" % (name, f["flag"])
    return ""


def lade_liste(pfad=None):
    """(gueltige Eintraege, Fehlertext). Ungueltige fallen weg und werden genannt."""
    try:
        roh = json.loads(Path(pfad or LISTE).read_text(encoding="utf-8"))
        eintraege = roh["eintraege"]
        if not isinstance(eintraege, list):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        return [], "leitstand_backtests.json nicht lesbar"
    gut, fehler = [], []
    for e in eintraege:
        grund = eintrag_fehler(e)
        if grund:
            fehler.append(grund)
        else:
            gut.append(e)
    return gut, "; ".join(fehler)


def pruefe_feld(feld, wert):
    """(Argumente, "") oder (None, Fehler). Leer oder None: Flag weglassen."""
    typ, flag = feld["typ"], feld["flag"]
    if wert is None:
        return [], ""
    if typ == "schalter":
        return ([flag] if wert in (True, 1, "1", "true") else []), ""
    text = str(wert).strip()
    if text == "":
        return [], ""
    if typ == "wahl":
        if text not in [str(w) for w in feld["werte"]]:
            return None, "%s: %r nicht erlaubt" % (flag, text)
        return [flag, text], ""
    if typ == "text":
        if not _TEXT.match(text):
            return None, "%s: nur Buchstaben, Ziffern und _ . / -" % flag
        return [flag, text], ""
    try:
        zahl = int(text) if typ == "int" else float(text.replace(",", "."))
    except ValueError:
        return None, "%s: %s erwartet" % (flag, "ganze Zahl" if typ == "int"
                                          else "Zahl")
    lo, hi = feld.get("min"), feld.get("max")
    if (lo is not None and zahl < lo) or (hi is not None and zahl > hi):
        return None, "%s: erlaubt %s bis %s" % (flag, lo, hi)
    return [flag, str(zahl)], ""


def einzel_befehl(eintrag, werte):
    """werte: Flag -> Text/bool. (Befehl, "") oder (None, Fehler)."""
    args = []
    for f in eintrag["felder"]:
        teil, fehler = pruefe_feld(f, werte.get(f["flag"], f.get("vorgabe")))
        if teil is None:
            return None, fehler
        args += teil
    return [sys.executable, eintrag["skript"]] + args, ""


class EinzelBereich(ttk.Frame):
    TITEL = "Einzelskripte"

    def __init__(self, eltern, reiter, pfad=None):
        super().__init__(eltern, padding=8)
        self.reiter = reiter
        self.eintraege, fehler = lade_liste(pfad)
        self.vars = {}
        oben = ttk.Frame(self)
        oben.pack(fill="x")
        ttk.Label(oben, text="Skript").pack(side="left")
        namen = [e["name"] for e in self.eintraege]
        gemerkt = (reiter.zustand.get("werte") or {}).get("einzel_name")
        self.w_name = tk.StringVar(value=gemerkt if gemerkt in namen
                                   else (namen[0] if namen else ""))
        wahl = ttk.Combobox(oben, textvariable=self.w_name, values=namen,
                            state="readonly", width=24)
        wahl.pack(side="left", padx=6)
        wahl.bind("<<ComboboxSelected>>", lambda _e: self._felder_bauen())
        self.k_start = ttk.Button(oben, text="Starten", command=self.starten)
        self.k_start.pack(side="left", padx=6)
        self.tip = Tooltip(self.k_start)
        ttk.Label(self, text=fehler, foreground="#c0392b").pack(anchor="w")
        self.rahmen = ttk.Frame(self)
        self.rahmen.pack(fill="x", pady=(6, 0))
        self._felder_bauen()
        self.lauf_wechsel(False)

    def eintrag(self):
        return next((e for e in self.eintraege if e["name"] == self.w_name.get()),
                    None)

    def _felder_bauen(self):
        for k in self.rahmen.winfo_children():
            k.destroy()
        self.vars = {}
        e = self.eintrag()
        if e is None:
            return
        gemerkt = (((self.reiter.zustand.get("werte") or {}).get("einzel") or {})
                   .get(e["name"]) or {})
        for r, f in enumerate(e["felder"]):
            vorgabe = gemerkt.get(f["flag"], f.get("vorgabe"))
            if f["typ"] == "schalter":
                v = tk.BooleanVar(value=bool(vorgabe))
                ttk.Checkbutton(self.rahmen, text=f["flag"], variable=v).grid(
                    row=r, column=0, columnspan=2, sticky="w")
            else:
                v = tk.StringVar(value="" if vorgabe is None else str(vorgabe))
                ttk.Label(self.rahmen, text=f["flag"]).grid(row=r, column=0,
                                                            sticky="w", padx=(0, 8))
                if f["typ"] == "wahl":
                    ttk.Combobox(self.rahmen, textvariable=v, state="readonly",
                                 values=[str(w) for w in f["werte"]],
                                 width=22).grid(row=r, column=1, sticky="w")
                else:
                    ttk.Entry(self.rahmen, textvariable=v, width=24).grid(
                        row=r, column=1, sticky="w")
            self.vars[f["flag"]] = v
        if not e["felder"]:
            ttk.Label(self.rahmen, text="ohne Einstellungen").grid(row=0, column=0,
                                                                  sticky="w")

    def werte(self):
        return {flag: v.get() for flag, v in self.vars.items()}

    def starten(self):
        e = self.eintrag()
        if e is None:
            return
        befehl, fehler = einzel_befehl(e, self.werte())
        if befehl is None:
            self.reiter.ls.melde(fehler)
            return
        alle = dict((self.reiter.zustand.get("werte") or {}).get("einzel") or {})
        alle[e["name"]] = self.werte()
        self.reiter.zustand.merke_in("werte", "einzel", alle)
        self.reiter.zustand.merke_in("werte", "einzel_name", e["name"])
        self.reiter.starte("einzel-%s" % e["name"], befehl)

    def lauf_wechsel(self, laeuft):
        if not self.eintraege:
            setze_knopf(self.k_start, self.tip, False, "keine Einträge in der Liste")
        else:
            setze_knopf(self.k_start, self.tip, not laeuft, "es läuft schon ein Lauf")

    def refresh(self):
        pass
```

Die letzte Zeile der Datei gezielt ersetzen: aus `BEREICHE = [ReplayBereich]` wird `BEREICHE = [ReplayBereich, EinzelBereich]`.

Im Test erwartet `test_start_mit_feldern_aus_der_liste` den Laufnamen `einzel-Mini`. Die Ablage macht daraus mit `ll.sicherer_name` den Dateinamen. Die ORB-Namen mit Klammern und Leerzeichen landen so als `einzel-ORB_xperp` im Dateinamen.

- [ ] **Step 6: `.gitignore` freigeben**

In der `.gitignore` der Repo-Wurzel direkt nach der Zeile `!Agenten/Handel/spur_opt.json` (Z. 76) gezielt einfügen:

```
!Agenten/Handel/leitstand_backtests.json
```

Prüfen, aus der Worktree-Wurzel:

```bash
git check-ignore -v Agenten/Handel/leitstand_backtests.json; echo "exit $?"
git check-ignore -v Agenten/Handel/backtest_laeufe/x.json Agenten/Handel/leitstand_zustand.json
git diff .gitignore
```

Erwartet: Die erste Prüfung meldet `exit 1`, die Datei wird also nicht ignoriert. Die zweite nennt für beide Pfade die `*`-Regel. Der Diff zeigt genau eine neue Zeile.

- [ ] **Step 7: Tests laufen lassen**

Run: `$PY -m unittest tests.test_leitstand_backtests_liste tests.test_leitstand_backtests tests.test_leitstand_backtests_lauf -v`
Erwartet: alle grün.

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage bleibt unverändert.

- [ ] **Step 8: Commit**

```bash
git status --short
git add .gitignore Agenten/Handel/leitstand_backtests.json Agenten/Handel/leitstand_backtests.py Agenten/Handel/tests/test_leitstand_backtests.py Agenten/Handel/tests/test_leitstand_backtests_liste.py
git commit -m "Leitstand: geprüfte Liste der Einzelskripte und ihr Bereich (Aufgabe 8)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Bereich Optimieren `leitstand_optimieren.py`

**Files:**
- Create: `Agenten/Handel/tests/lesepruefung.py` (Hilfsmodul, kein Test)
- Create: `Agenten/Handel/leitstand_optimieren.py`
- Modify: `Agenten/Handel/leitstand_backtests.py` (ein Import, die Zeile `BEREICHE = …`)
- Test: `Agenten/Handel/tests/test_leitstand_optimieren.py`

**Interfaces:**
- Consumes:
  - aus Aufgabe 4: `Tabelle(eltern, spalten, zustand, name, hoehe=10, auswahl="browse")` mit `.baum`, `setze(zeilen, tags)`, `sichtbare()`, `auswahl()`; `Tooltip(widget)` mit `.text`; `setze_knopf(knopf, tip, erlaubt, grund)`.
  - aus Aufgabe 6: `ll.json_aus_ausgabe(text) -> dict|None`, `ll._fmt(v) -> str`.
  - aus Aufgabe 7: der Reiter `reiter` mit `.arten` (ttk.Notebook), `.zustand`, `.ls.melde(text)`, `.starte(name, befehl, auswerten=None, fertig=None, stempel=None) -> bool`. `fertig(pfad, daten)` wird nach Laufende gerufen; `daten` hat `exit_code`, `abgebrochen`, `ausgabe`.
  - `optimieren.py` (unverändert): `--spur --monate --fenster --max-kandidaten [--gebuehr] [--trocken]`. Der Trockenlauf druckt den Plan als JSON (`spur`, `kerzen`, `von_index`, `n_fenster`, `kandidaten`, `schlussel`, `takt`, `geschaetzte_sekunden`), davor eventuell „Zeitraum angehoben: …“. Die Suche schreibt `daten/backtest/<spur>/optimierung.json` mit `grundlinie_netto_je_runde`, `ohne_wirkung` (Liste von Feldnamen) und `kandidaten` (je `werte`, `netto_je_runde`, `ueberlebt`, `fenster_gewonnen`, `fenster_verloren`, `fenster_zu_wenig`, `grund` — oder `werte` + `fehler`).
- Produces:
  - `tests/lesepruefung.py`: `schreibstellen(pfad) -> list[str]` (leer = schreibt nichts), `importiert(pfad, modul) -> bool`. Genutzt in den Aufgaben 9, 11 und 12.
  - `leitstand_optimieren`: `spuren(pfad=None)`, `pruefe_werte(werte, spur_datei=None) -> str`, `optimieren_befehl(werte, trocken) -> list`, `plan_text(plan, hinweis="")`, `angehoben(text)`, `lade_optimierung(spur, wurzel=None) -> (dict|None, str)`, `kandidaten_zeilen(opt) -> (zeilen, tags)`, `ohne_wirkung_text(opt)`, `alte_werte(spur, schluessel, hier=None) -> dict|None`, `diff_text(spur, alt, neu)`, `class TrockenPruefung`, `class OptimierenBereich(ttk.Frame)(eltern, reiter, spur_datei=None, wurzel=None, hier=None)` mit `TITEL = "Optimieren"`.
  - `leitstand_backtests.BEREICHE = [ReplayBereich, EinzelBereich, OptimierenBereich]`.

Der Trockenlauf startet automatisch, aber erst, wenn der Unterreiter „Optimieren“ sichtbar ist — nicht schon beim Aufbau des Backtest-Reiters. Sonst rechnete jeder Start des Leitstands einen Plan, und die Tests aus Aufgabe 7 mit der Standardliste `BEREICHE` stießen einen echten Lauf an.

- [ ] **Step 1: Hilfsmodul `tests/lesepruefung.py` schreiben**

```python
"""AST-Pruefung "schreibt nichts" fuer die Module des Leitstands.

Hilfsmodul fuer Tests, selbst kein Test (der Name beginnt nicht mit test_).
Dieselben Regeln wie tests/test_handelszentrale_rein_lesend.py, dazu die
Schreibmethoden von pathlib (write_text, write_bytes, unlink, touch, open im
Schreibmodus). Geprueft wird der Quelltext, nicht ein Stichwort: ein
Kommentar mit "schreiben" ist kein Schreibzugriff.
"""

import ast
from pathlib import Path

SCHREIBMODI = ("w", "a", "x", "w+", "a+", "r+", "wb", "ab", "xb")
VERBOTEN = {("json", "dump"), ("json", "dumps"), ("csv", "writer"),
            ("os", "remove"), ("os", "rename"), ("os", "replace"),
            ("os", "mkdir"), ("os", "makedirs"), ("os", "rmdir"),
            ("shutil", "rmtree"), ("shutil", "copy")}
PFAD_METHODEN = ("write_text", "write_bytes", "unlink", "touch")


def _baum(pfad):
    return ast.parse(Path(pfad).read_text(encoding="utf-8"))


def _modus(knoten, stelle):
    """Modus eines open-Aufrufs: Argument an `stelle` oder mode=, sonst None."""
    if len(knoten.args) > stelle and isinstance(knoten.args[stelle], ast.Constant):
        return knoten.args[stelle].value
    for kw in knoten.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def schreibstellen(pfad):
    """Alle Schreibstellen als "Z. <zeile>: <was>"; leer = schreibt nichts."""
    aus = []
    for k in ast.walk(_baum(pfad)):
        if not isinstance(k, ast.Call):
            continue
        f = k.func
        if isinstance(f, ast.Name) and f.id == "open":
            m = _modus(k, 1)
            if m is not None and str(m) in SCHREIBMODI:
                aus.append("Z. %d: open(..., %r)" % (k.lineno, m))
        elif isinstance(f, ast.Attribute):
            if isinstance(f.value, ast.Name) and (f.value.id, f.attr) in VERBOTEN:
                aus.append("Z. %d: %s.%s" % (k.lineno, f.value.id, f.attr))
            elif f.attr in PFAD_METHODEN:
                aus.append("Z. %d: .%s" % (k.lineno, f.attr))
            elif f.attr == "open":
                m = _modus(k, 0)
                if m is not None and str(m) in SCHREIBMODI:
                    aus.append("Z. %d: .open(%r)" % (k.lineno, m))
    return aus


def importiert(pfad, modul):
    """Importiert die Datei `modul` (auch als `from modul import ...`)?"""
    for k in ast.walk(_baum(pfad)):
        if isinstance(k, ast.Import):
            if any(a.name.split(".")[0] == modul for a in k.names):
                return True
        elif isinstance(k, ast.ImportFrom):
            if (k.module or "").split(".")[0] == modul:
                return True
    return False
```

- [ ] **Step 2: Tests schreiben**

`tests/test_leitstand_optimieren.py`:

```python
"""Bereich Optimieren: Trockenlauf zuerst, Rechnen erst danach, Anzeige und
Unterschied aus einer Fixture-optimierung.json, keine Schreibstelle.

Kein echtes daten/backtest und keine echte wachen.json: spur_opt.json,
optimierung.json und wachen.json liegen im temporaeren Ordner. Laeufe starten
nie wirklich; FakeSteuerung nimmt den Befehl nur entgegen.

Direkt ausfuehrbar:  python tests/test_leitstand_optimieren.py
"""

import json
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import leitstand_backtests as lbt                              # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_optimieren as lo                              # noqa: E402
import lesepruefung                                            # noqa: E402

SPUR_OPT = {"_hinweis": "x", "squeeze": {"schluessel": ["a", "b"], "raster": {}}}
WACHEN = {"a": 1, "b": 2.0, "c": "x"}
OPT = {
    "spur": "squeeze", "grundlinie_netto_je_runde": 0.12, "ohne_wirkung": ["c"],
    "kandidaten": [
        {"werte": {"a": 3, "b": 2.0}, "netto_je_runde": 0.4, "ueberlebt": True,
         "fenster_gewonnen": 2, "fenster_verloren": 0, "fenster_zu_wenig": 0,
         "grund": "gewinnt alle 2"},
        {"werte": {"a": 1, "b": 3.0}, "netto_je_runde": 0.05, "ueberlebt": False,
         "fenster_gewonnen": 1, "fenster_verloren": 1, "fenster_zu_wenig": 0,
         "grund": "kein Hebel"},
        {"werte": {"a": 5, "b": 1.0}, "fehler": "zu wenige Fenster"},
    ],
}
PLAN_AUSGABE = (
    "Zeitraum angehoben: 6 Monate im 4H-Takt sind 1092 Kerzen\n"
    "{\n  \"spur\": \"squeeze\",\n  \"kerzen\": 4380,\n  \"n_fenster\": 2,\n"
    "  \"kandidaten\": 9,\n  \"takt\": \"1H\",\n  \"geschaetzte_sekunden\": 432\n}\n"
    "Trockenlauf: nichts gerechnet, nichts geschrieben.\n")
GUELTIG = {"spur": "squeeze", "monate": "6", "fenster": "2", "kandidaten": "40",
           "gebuehr": ""}


class StubLeitstand:
    def __init__(self, root, zustand):
        self.root, self.zustand, self.meldungen = root, zustand, []
    def melde(self, text):
        self.meldungen.append(text)


class FakeSteuerung:
    def __init__(self, ablage):
        self.ablage, self.gestartet, self.lauf = ablage, [], None
        self.naechstes = ([], None)
    def starte(self, name, befehl, auswerten=None, stempel=None):
        if self.lauf:
            raise RuntimeError("es läuft schon: %s" % self.lauf)
        self.lauf = name
        self.gestartet.append((name, list(befehl), auswerten, stempel))
        return SimpleNamespace(name=name, befehl=list(befehl))
    def laeuft(self): return self.lauf is not None
    def abbrechen(self): pass
    def takt(self):
        erg, self.naechstes = self.naechstes, ([], None)
        if erg[1]:
            self.lauf = None
        return erg
    def status(self):
        return "Backtest: %s läuft seit 0:01" % self.lauf if self.lauf else ""


class TkBasis(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ablage = Path(self.tmp.name) / "ablage"
        self.ablage.mkdir()
        self.ls = StubLeitstand(self.root, lb.Zustand(Path(self.tmp.name) / "z.json"))
        self.st = FakeSteuerung(self.ablage)
    def reiter(self, bereiche=None):
        r = lbt.BacktestReiter(self.root, self.ls, steuerung=self.st, bereiche=bereiche)
        self.root.update_idletasks()
        return r


def _schreib(pfad, daten):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(daten if isinstance(daten, str) else json.dumps(daten),
                    encoding="utf-8")
    return pfad


class Rein(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.t = Path(self.tmp.name)
        self.spur_opt = _schreib(self.t / "spur_opt.json", SPUR_OPT)

    def test_spuren_nur_mit_eintrag(self):
        self.assertEqual(lo.spuren(self.spur_opt), ["squeeze"])
        self.assertEqual(lo.spuren(_schreib(self.t / "kaputt.json", "{x")), [])
        self.assertEqual(lo.spuren(self.t / "fehlt.json"), [])

    def test_pruefe_werte(self):
        p = lambda **aend: lo.pruefe_werte(dict(GUELTIG, **aend), self.spur_opt)
        self.assertEqual(p(), "")
        self.assertEqual(p(gebuehr="0,2"), "")
        self.assertEqual(p(spur="gitter"),
                         "Spur 'gitter' hat keinen Eintrag in spur_opt.json")
        self.assertEqual(p(monate="sechs"), "monate: ganze Zahl erwartet")
        self.assertEqual(p(fenster="1"), "fenster: erlaubt 2 bis 12")
        self.assertEqual(p(kandidaten="501"), "kandidaten: erlaubt 1 bis 500")
        self.assertEqual(p(gebuehr="viel"), "gebuehr: Zahl erwartet")
        self.assertEqual(p(gebuehr="9"), "gebuehr: erlaubt 0 bis 5")

    def test_befehl(self):
        b = lo.optimieren_befehl(dict(GUELTIG, gebuehr="0,2"), trocken=True)
        self.assertEqual(b[1:], ["optimieren.py", "--spur", "squeeze", "--monate", "6",
                                 "--fenster", "2", "--max-kandidaten", "40",
                                 "--gebuehr", "0.2", "--trocken"])
        b = lo.optimieren_befehl(GUELTIG, trocken=False)
        self.assertNotIn("--trocken", b)
        self.assertNotIn("--gebuehr", b)

    def test_plan_text_mit_hinweis(self):
        import leitstand_laeufe as ll
        plan = ll.json_aus_ausgabe(PLAN_AUSGABE)
        text = lo.plan_text(plan, lo.angehoben(PLAN_AUSGABE))
        self.assertTrue(text.startswith(
            "9 Kandidaten · 2 Fenster · Takt 1H · 4380 Kerzen"
            " · etwa 7:12 min"))
        self.assertIn("\nZeitraum angehoben: 6 Monate", text)
        self.assertEqual(lo.angehoben("nur Text\n"), "")

    def test_kandidaten_zeilen(self):
        zeilen, tags = lo.kandidaten_zeilen(OPT)
        self.assertEqual(zeilen[0], ("heute", "heutige Einstellung", "0.12", "", "",
                                     "Grundlinie"))
        self.assertEqual(zeilen[1], (1, "a=3, b=2", "0.4", "2/0/0", "ja",
                                     "gewinnt alle 2"))
        self.assertEqual(zeilen[3][0], 3)
        self.assertEqual(zeilen[3][5], "Fehler: zu wenige Fenster")
        self.assertEqual(tags, [("grundlinie",), ("ueberlebt",), (), ()])
        self.assertEqual(lo.ohne_wirkung_text(OPT), "Feld c ändert nichts")

    def test_lade_optimierung(self):
        opt, fehler = lo.lade_optimierung("squeeze", self.t / "bt")
        self.assertIsNone(opt)
        self.assertEqual(fehler, "noch keine Optimierung für squeeze")
        _schreib(self.t / "bt" / "squeeze" / "optimierung.json", "{kaputt")
        self.assertEqual(lo.lade_optimierung("squeeze", self.t / "bt"),
                         (None, "optimierung.json nicht lesbar"))
        _schreib(self.t / "bt" / "squeeze" / "optimierung.json", OPT)
        self.assertEqual(lo.lade_optimierung("squeeze", self.t / "bt"), (OPT, ""))

    def test_alte_werte_und_diff(self):
        _schreib(self.t / "squeeze" / "wachen.json", WACHEN)
        alt = lo.alte_werte("squeeze", ["a", "b", "neu"], self.t)
        self.assertEqual(alt, {"a": 1, "b": 2.0})
        self.assertEqual(lo.diff_text("squeeze", alt, {"a": 3, "b": 2.0, "neu": 1}),
                         "squeeze/wachen.json\n  a: 1 → 3\n  neu: fehlt → 1")
        self.assertEqual(lo.diff_text("squeeze", alt, {"a": 1, "b": 2}),
                         "squeeze/wachen.json: keine Änderung gegenüber heute")
        self.assertIsNone(lo.alte_werte("gitter", ["a"], self.t))
        self.assertEqual(lo.diff_text("gitter", None, {"a": 1}),
                         "gitter/wachen.json nicht lesbar")

    def test_trocken_pruefung(self):
        p = lo.TrockenPruefung()
        self.assertEqual(p.darf_rechnen(GUELTIG), (False, "erst Trockenlauf"))
        p.merke(GUELTIG)
        self.assertEqual(p.darf_rechnen(GUELTIG), (True, ""))
        self.assertEqual(p.darf_rechnen(dict(GUELTIG, monate="12")),
                         (False, "Werte geändert — Trockenlauf läuft neu"))
        p.vergiss()
        self.assertEqual(p.darf_rechnen(GUELTIG), (False, "erst Trockenlauf"))


class Lesepruefung(unittest.TestCase):
    def test_optimieren_schreibt_nichts(self):
        self.assertEqual(lesepruefung.schreibstellen(lo.__file__), [])
        self.assertFalse(lesepruefung.importiert(lo.__file__, "subprocess"))

    def test_die_pruefung_findet_schreibstellen(self):
        with tempfile.TemporaryDirectory() as tmp:
            quelle = Path(tmp) / "probe.py"
            quelle.write_text(
                "import json, os\nfrom pathlib import Path\nopen('x', 'w')\n"
                "open('x')\njson.dumps({})\nos.replace('a', 'b')\n"
                "Path('x').write_text('')\nPath('x').open('a')\n"
                "import subprocess\n", encoding="utf-8")
            self.assertEqual(lesepruefung.schreibstellen(quelle),
                             ["Z. 3: open(..., 'w')", "Z. 5: json.dumps",
                              "Z. 6: os.replace", "Z. 7: .write_text",
                              "Z. 8: .open('a')"])
            self.assertTrue(lesepruefung.importiert(quelle, "subprocess"))
            self.assertFalse(lesepruefung.importiert(quelle, "shutil"))


class Bereich(TkBasis):
    def setUp(self):
        super().setUp()
        t = Path(self.tmp.name)
        self.spur_opt = _schreib(t / "spur_opt.json", SPUR_OPT)
        self.wurzel = t / "bt"
        self.opt_datei = _schreib(self.wurzel / "squeeze" / "optimierung.json", OPT)
        self.hier = t / "hier"
        _schreib(self.hier / "squeeze" / "wachen.json", WACHEN)
        self.fabrik = lambda e, r: lo.OptimierenBereich(
            e, r, spur_datei=self.spur_opt, wurzel=self.wurzel, hier=self.hier)

    def _trocken_fertig(self, r, exit_code=0, ausgabe=PLAN_AUSGABE):
        self.st.naechstes = ([], (self.ablage / "x.json", {
            "name": self.st.lauf, "exit_code": exit_code, "abgebrochen": False,
            "ausgabe": ausgabe}))
        r._takt()
        self.root.update_idletasks()

    def _waehle(self, b, nr):
        for iid in b.tabelle.baum.get_children():
            if b.tabelle.baum.item(iid, "values")[0] == str(nr):
                b.tabelle.baum.selection_set(iid)
        b._auswahl()

    def test_trockenlauf_startet_sobald_sichtbar(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self.assertEqual(len(self.st.gestartet), 1)
        name, befehl, _a, _s = self.st.gestartet[0]
        self.assertEqual(name, "optimieren-trocken-squeeze")
        self.assertEqual(befehl[-1], "--trocken")
        self.assertIn("disabled", b.k_rechnen.state())
        self.assertEqual(b.tip.text, "erst Trockenlauf")

    def test_rechnen_erst_nach_trockenlauf(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self._trocken_fertig(r)
        self.assertNotIn("disabled", b.k_rechnen.state())
        self.assertIn("9 Kandidaten", b.w_plan.cget("text"))
        self.assertIn("Zeitraum angehoben", b.w_plan.cget("text"))
        self.assertEqual(len(self.st.gestartet), 1)        # kein zweiter Trockenlauf
        b.rechnen()
        name, befehl, _a, _s = self.st.gestartet[-1]
        self.assertEqual(name, "optimieren-squeeze")
        self.assertNotIn("--trocken", befehl)
        self.assertEqual(self.ls.zustand.get("werte")["optimieren"]["spur"], "squeeze")

    def test_wertaenderung_sperrt_und_rechnet_den_plan_neu(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self._trocken_fertig(r)
        b.vars["monate"].set("12")
        self.assertIn("disabled", b.k_rechnen.state())
        self.assertEqual(b.tip.text,
                         "Werte geändert — Trockenlauf läuft neu")
        b._wenn_sichtbar()                                  # statt der Entprellung
        self.assertEqual(len(self.st.gestartet), 2)
        self.assertIn("12", self.st.gestartet[-1][1])

    def test_ungueltiger_wert_sperrt_ohne_lauf(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self._trocken_fertig(r)
        b.vars["fenster"].set("99")
        b._wenn_sichtbar()
        self.assertEqual(len(self.st.gestartet), 1)
        self.assertEqual(b.tip.text, "fenster: erlaubt 2 bis 12")

    def test_trockenlauf_ohne_plan(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self._trocken_fertig(r, exit_code=1, ausgabe="Traceback ...\nKeyError\n")
        self.assertEqual(b.w_plan.cget("text"), "Trockenlauf ohne Plan (Exit 1)")
        self.assertEqual(b.tip.text, "erst Trockenlauf")
        b._wenn_sichtbar()                   # derselbe Versuch nicht in Schleife
        self.assertEqual(len(self.st.gestartet), 1)

    def test_tabelle_und_unterschied(self):
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self.assertEqual(len(b.tabelle.sichtbare()), 4)
        self.assertEqual(b.tabelle.sichtbare()[0][0], "heute")
        self.assertEqual(b.w_hinweis.cget("text"), "Feld c ändert nichts")
        self._waehle(b, 1)
        self.assertEqual(b.w_diff.get("1.0", "end-1c"),
                         "squeeze/wachen.json\n  a: 1 → 3")
        self.assertEqual(b.kopieren(), "squeeze/wachen.json\n  a: 1 → 3")
        self.assertEqual(self.root.clipboard_get(), "squeeze/wachen.json\n  a: 1 → 3")
        self.assertEqual(self.ls.meldungen[-1], "Unterschied kopiert")
        self._waehle(b, 2)
        self.assertEqual(b.w_diff.get("1.0", "end-1c"),
                         "nur überlebende Kandidaten werden verglichen")
        self.assertEqual(json.loads((self.hier / "squeeze" / "wachen.json")
                                    .read_text(encoding="utf-8")), WACHEN)

    def test_unlesbare_optimierung(self):
        self.opt_datei.write_text("{kaputt", encoding="utf-8")
        r = self.reiter([self.fabrik])
        b = r.bereiche[0]
        self.assertEqual(b.w_hinweis.cget("text"), "optimierung.json nicht lesbar")
        self.assertEqual(b.tabelle.sichtbare(), [])

    def test_unsichtbar_startet_nichts(self):
        r = self.reiter([lbt.ReplayBereich, self.fabrik])
        self.root.update()
        self.assertEqual(self.st.gestartet, [])
        r.arten.select(1)
        self.root.update()
        self.assertEqual([g[0] for g in self.st.gestartet],
                         ["optimieren-trocken-squeeze"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Test laufen lassen — er muss scheitern**

Run: `$PY -m unittest tests.test_leitstand_optimieren -v`
Erwartet: `ModuleNotFoundError: No module named 'leitstand_optimieren'`.

- [ ] **Step 4: `leitstand_optimieren.py` schreiben**

```python
"""Bereich Optimieren im Backtest-Reiter des Leitstands.

Faehrt optimieren.py: erst automatisch den Trockenlauf (Plan und geschaetzte
Dauer), sobald der Bereich sichtbar ist; "Rechnen" wird erst danach frei und
sperrt wieder, wenn sich ein Wert aendert. Das Ergebnis aus
daten/backtest/<spur>/optimierung.json erscheint als Tabelle; fuer einen
ueberlebenden Kandidaten zeigt der Bereich den Unterschied zur heutigen
<spur>/wachen.json als Text zum Kopieren.

Dieses Modul schreibt NICHTS - keine wachen.json, keine andere Datei
(geprueft per AST in tests/test_leitstand_optimieren.py). optimieren.py selbst
schreibt nur die Vorschlagsdatei optimierung.json. Einen Kandidaten
uebernimmt Max von Hand: ein anderer Stop ist eine Entscheidung ueber Geld.
"""

import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import leitstand_laeufe as ll
import replay
from leitstand_bedienung import Tabelle, Tooltip, setze_knopf

HIER = Path(__file__).resolve().parent
SPUR_OPT = HIER / "spur_opt.json"

FELDER = (("spur", "Spur"), ("monate", "Monate"), ("fenster", "Fenster"),
          ("kandidaten", "höchstens Kandidaten"),
          ("gebuehr", "Gebühr % (leer = Vorgabe)"))
VORGABEN = {"spur": "", "monate": "6", "fenster": "2", "kandidaten": "40",
            "gebuehr": ""}
GRENZEN = {"monate": (1, 60), "fenster": (2, 12), "kandidaten": (1, 500)}
ENTPRELL_MS = 800
KANDIDAT_SPALTEN = ("Nr", "Werte", "netto je Runde", "Fenster +/−/zu wenig",
                    "überlebt", "Grund")


# --- rein ------------------------------------------------------------------

def spuren(pfad=None):
    """Spuren mit Suchbereich in spur_opt.json; [] wenn fehlend oder unlesbar."""
    try:
        d = json.loads(Path(pfad or SPUR_OPT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(d, dict):
        return []
    return sorted(k for k, v in d.items()
                  if not k.startswith("_") and isinstance(v, dict))


def _ganz(text, name):
    try:
        zahl = int(str(text).strip())
    except ValueError:
        return None, "%s: ganze Zahl erwartet" % name
    lo, hi = GRENZEN[name]
    if not lo <= zahl <= hi:
        return None, "%s: erlaubt %d bis %d" % (name, lo, hi)
    return zahl, ""


def pruefe_werte(werte, spur_datei=None):
    """"" wenn die Werte gueltig sind, sonst die erste Fehlermeldung."""
    if werte.get("spur") not in spuren(spur_datei):
        return "Spur %r hat keinen Eintrag in spur_opt.json" % werte.get("spur")
    for name in ("monate", "fenster", "kandidaten"):
        _zahl, fehler = _ganz(werte.get(name, ""), name)
        if fehler:
            return fehler
    g = str(werte.get("gebuehr", "")).strip()
    if g:
        try:
            zahl = float(g.replace(",", "."))
        except ValueError:
            return "gebuehr: Zahl erwartet"
        if not 0 <= zahl <= 5:                    # auch NaN faellt hier heraus
            return "gebuehr: erlaubt 0 bis 5"
    return ""


def optimieren_befehl(werte, trocken):
    """Befehl fuer gueltige Werte (vorher pruefe_werte)."""
    b = [sys.executable, "optimieren.py", "--spur", werte["spur"],
         "--monate", str(int(str(werte["monate"]).strip())),
         "--fenster", str(int(str(werte["fenster"]).strip())),
         "--max-kandidaten", str(int(str(werte["kandidaten"]).strip()))]
    g = str(werte.get("gebuehr", "")).strip()
    if g:
        b += ["--gebuehr", str(float(g.replace(",", ".")))]
    if trocken:
        b.append("--trocken")
    return b


def angehoben(text):
    """Die Zeile "Zeitraum angehoben: ..." aus der Ausgabe, sonst ""."""
    for z in (text or "").splitlines():
        if z.startswith("Zeitraum angehoben:"):
            return z.strip()
    return ""


def _dauer(sek):
    try:
        m, s = divmod(int(sek), 60)
    except (TypeError, ValueError):
        return "?"
    return "%d:%02d min" % (m, s)


def plan_text(plan, hinweis=""):
    text = ("%s Kandidaten · %s Fenster · Takt %s · %s Kerzen · etwa %s"
            % (plan.get("kandidaten", "?"), plan.get("n_fenster", "?"),
               plan.get("takt", "?"), plan.get("kerzen", "?"),
               _dauer(plan.get("geschaetzte_sekunden"))))
    return text + ("\n" + hinweis if hinweis else "")


def lade_optimierung(spur, wurzel=None):
    """(Daten, "") oder (None, Grund). Liest nur."""
    pfad = Path(wurzel or replay.wurzel()) / spur / "optimierung.json"
    if not pfad.exists():
        return None, "noch keine Optimierung für %s" % spur
    try:
        d = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "optimierung.json nicht lesbar"
    if not isinstance(d, dict) or not isinstance(d.get("kandidaten"), list):
        return None, "optimierung.json nicht lesbar"
    return d, ""


def _werte_text(werte):
    if not isinstance(werte, dict):
        return ""
    return ", ".join("%s=%s" % (k, ll._fmt(v)) for k, v in sorted(werte.items()))


def kandidaten_zeilen(opt):
    """Grundlinie zuerst, dann je Kandidat eine Zeile; Nr bleibt int."""
    zeilen = [("heute", "heutige Einstellung",
               ll._fmt(opt.get("grundlinie_netto_je_runde")), "", "", "Grundlinie")]
    tags = [("grundlinie",)]
    for nr, k in enumerate(opt.get("kandidaten") or [], 1):
        if not isinstance(k, dict):
            continue
        if "fehler" in k:
            zeilen.append((nr, _werte_text(k.get("werte")), "", "", "nein",
                           "Fehler: %s" % k["fehler"]))
            tags.append(())
            continue
        fenster = ("%s/%s/%s" % (k.get("fenster_gewonnen"), k.get("fenster_verloren"),
                                 k.get("fenster_zu_wenig"))
                   if "fenster_gewonnen" in k else "")
        ueberlebt = bool(k.get("ueberlebt"))
        zeilen.append((nr, _werte_text(k.get("werte")),
                       ll._fmt(k.get("netto_je_runde")), fenster,
                       "ja" if ueberlebt else "nein", str(k.get("grund", ""))))
        tags.append(("ueberlebt",) if ueberlebt else ())
    return zeilen, tags


def ohne_wirkung_text(opt):
    return "; ".join("Feld %s ändert nichts" % f
                     for f in (opt.get("ohne_wirkung") or []))


def alte_werte(spur, schluessel, hier=None):
    """Heutige Werte dieser Schluessel aus <spur>/wachen.json; None wenn unlesbar.
    Fehlt ein Schluessel, fehlt er auch im Ergebnis."""
    try:
        d = json.loads((Path(hier or HIER) / spur / "wachen.json")
                       .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    return {k: d[k] for k in schluessel if k in d}


def diff_text(spur, alt, neu):
    if alt is None:
        return "%s/wachen.json nicht lesbar" % spur
    zeilen = ["%s/wachen.json" % spur]
    for k in sorted(neu):
        if k not in alt or alt[k] != neu[k]:
            zeilen.append("  %s: %s → %s" % (k, ll._fmt(alt[k]) if k in alt else "fehlt",
                                             ll._fmt(neu[k])))
    if len(zeilen) == 1:
        return "%s/wachen.json: keine Änderung gegenüber heute" % spur
    return "\n".join(zeilen)


class TrockenPruefung:
    """Merkt die Werte des letzten gelungenen Trockenlaufs."""

    def __init__(self):
        self.werte = None

    def merke(self, werte):
        self.werte = dict(werte)

    def vergiss(self):
        self.werte = None

    def darf_rechnen(self, werte):
        if self.werte is None:
            return False, "erst Trockenlauf"
        if dict(werte) != self.werte:
            return False, "Werte geändert — Trockenlauf läuft neu"
        return True, ""


# --- der Bereich -----------------------------------------------------------

class OptimierenBereich(ttk.Frame):
    TITEL = "Optimieren"

    def __init__(self, eltern, reiter, spur_datei=None, wurzel=None, hier=None):
        super().__init__(eltern, padding=8)
        self.reiter = reiter
        self.spur_datei, self.wurzel, self.hier = spur_datei, wurzel, hier
        self.pruefung = TrockenPruefung()
        self._laeuft = False
        self._versucht = None           # Werte des letzten Trockenlauf-Starts
        self._entprell = None
        self._spur_angezeigt = None
        self._opt = None

        liste = spuren(spur_datei)
        g = dict(VORGABEN, **((reiter.zustand.get("werte") or {})
                              .get("optimieren") or {}))
        if g["spur"] not in liste:
            g["spur"] = liste[0] if liste else ""

        oben = ttk.Frame(self)
        oben.pack(fill="x")
        self.vars = {}
        for spalte, (name, text) in enumerate(FELDER):
            ttk.Label(oben, text=text).grid(row=0, column=spalte, sticky="w",
                                            padx=(0, 8))
            v = tk.StringVar(value=str(g[name]))
            if name == "spur":
                ttk.Combobox(oben, textvariable=v, values=liste, state="readonly",
                             width=16).grid(row=1, column=spalte, sticky="w",
                                            padx=(0, 8))
            else:
                ttk.Entry(oben, textvariable=v, width=10).grid(
                    row=1, column=spalte, sticky="w", padx=(0, 8))
            self.vars[name] = v
        self.w_spur = self.vars["spur"]

        zeile = ttk.Frame(self)
        zeile.pack(fill="x", pady=(6, 0))
        self.k_rechnen = ttk.Button(zeile, text="Rechnen", command=self.rechnen)
        self.k_rechnen.pack(side="left")
        self.tip = Tooltip(self.k_rechnen)
        ttk.Button(zeile, text="Ergebnis zeigen",
                   command=lambda: self.zeige(self.w_spur.get())).pack(
                       side="left", padx=6)
        self.w_plan = ttk.Label(zeile, text="", justify="left")
        self.w_plan.pack(side="left", padx=12)
        self.w_hinweis = ttk.Label(self, text="", foreground="#b35c00")
        self.w_hinweis.pack(anchor="w", pady=(4, 0))

        teiler = ttk.PanedWindow(self, orient="horizontal")
        teiler.pack(fill="both", expand=True, pady=(4, 0))
        self.tabelle = Tabelle(teiler, KANDIDAT_SPALTEN, reiter.zustand,
                               "optimieren", hoehe=8)
        self.tabelle.baum.tag_configure("grundlinie", foreground="#888888")
        self.tabelle.baum.tag_configure("ueberlebt", background="#d5f5e3")
        self.tabelle.baum.bind("<<TreeviewSelect>>", self._auswahl, add="+")
        teiler.add(self.tabelle, weight=3)
        rechts = ttk.Frame(teiler)
        teiler.add(rechts, weight=2)
        ttk.Label(rechts, text="Übernahme von Hand — der Leitstand schreibt "
                               "nie in eine wachen.json").pack(anchor="w")
        self.w_diff = tk.Text(rechts, height=8, width=40, wrap="none",
                              state="disabled", font=("Consolas", 9))
        self.w_diff.pack(fill="both", expand=True)
        ttk.Button(rechts, text="Kopieren", command=self.kopieren).pack(
            anchor="e", pady=(4, 0))

        reiter.arten.bind("<<NotebookTabChanged>>", self._wenn_sichtbar, add="+")
        for v in self.vars.values():
            v.trace_add("write", lambda *_: self._geaendert())
        self._knopf()

    # Werte und Knopf
    def werte(self):
        return {name: v.get().strip() for name, v in self.vars.items()}

    def _knopf(self):
        w = self.werte()
        fehler = pruefe_werte(w, self.spur_datei)
        if fehler:
            erlaubt, grund = False, fehler
        else:
            erlaubt, grund = self.pruefung.darf_rechnen(w)
            if erlaubt and self._laeuft:
                erlaubt, grund = False, "es läuft schon ein Lauf"
        setze_knopf(self.k_rechnen, self.tip, erlaubt, grund)

    def _geaendert(self):
        self._knopf()
        if self._entprell is not None:
            self.after_cancel(self._entprell)
        self._entprell = self.after(ENTPRELL_MS, self._wenn_sichtbar)

    # Trockenlauf automatisch, aber nur sichtbar
    def sichtbar(self):
        return str(self.reiter.arten.select()) == str(self)

    def _wenn_sichtbar(self, _e=None):
        self._entprell = None
        try:
            if not self.sichtbar():
                return
        except tk.TclError:
            return                                  # Fenster ist zu
        spur = self.w_spur.get()
        if spur and spur != self._spur_angezeigt:
            self.zeige(spur)
        self._trocken_jetzt()

    def _trocken_jetzt(self):
        w = self.werte()
        fehler = pruefe_werte(w, self.spur_datei)
        if fehler:
            self.w_plan.config(text=fehler)
            self._knopf()
            return
        if self._laeuft or self.pruefung.werte == w or self._versucht == w:
            return
        self._versucht = w
        self.pruefung.vergiss()
        self.w_plan.config(text="Trockenlauf läuft …")
        self.reiter.starte("optimieren-trocken-%s" % w["spur"],
                           optimieren_befehl(w, trocken=True),
                           fertig=lambda _p, d: self._trocken_fertig(w, d))
        self._knopf()

    def _trocken_fertig(self, w, daten):
        ausgabe = daten.get("ausgabe", "")
        plan = ll.json_aus_ausgabe(ausgabe) if daten.get("exit_code") == 0 else None
        if not isinstance(plan, dict) or "kandidaten" not in plan:
            self.pruefung.vergiss()
            self.w_plan.config(text="Trockenlauf ohne Plan (Exit %s)"
                               % daten.get("exit_code"))
        else:
            self.pruefung.merke(w)
            self.w_plan.config(text=plan_text(plan, angehoben(ausgabe)))
        self._knopf()

    # Bereich-Schnittstelle
    def lauf_wechsel(self, laeuft):
        self._laeuft = laeuft
        self._knopf()
        if not laeuft:
            self.after_idle(self._wenn_sichtbar)

    def refresh(self):
        self._knopf()
        self._wenn_sichtbar()

    # Rechnen
    def rechnen(self):
        w = self.werte()
        erlaubt, _grund = self.pruefung.darf_rechnen(w)
        if pruefe_werte(w, self.spur_datei) or not erlaubt or self._laeuft:
            return
        self.reiter.zustand.merke_in("werte", "optimieren", w)
        self.reiter.starte("optimieren-%s" % w["spur"],
                           optimieren_befehl(w, trocken=False),
                           fertig=lambda _p, d: self._rechnen_fertig(w["spur"], d))

    def _rechnen_fertig(self, spur, daten):
        if daten.get("exit_code") == 0:
            self.zeige(spur)
        else:
            self.w_hinweis.config(text="Optimierung ohne Ergebnis (Exit %s) — "
                                       "Ausgabe oben" % daten.get("exit_code"))

    # Anzeige
    def zeige(self, spur):
        self._spur_angezeigt = spur
        self._diff_setzen("")
        self._opt, fehler = lade_optimierung(spur, self.wurzel)
        if self._opt is None:
            self.tabelle.setze([])
            self.w_hinweis.config(text=fehler)
            return
        zeilen, tags = kandidaten_zeilen(self._opt)
        self.tabelle.setze(zeilen, tags)
        self.w_hinweis.config(text=ohne_wirkung_text(self._opt))

    def _diff_setzen(self, text):
        self.w_diff.configure(state="normal")
        self.w_diff.delete("1.0", "end")
        self.w_diff.insert("1.0", text)
        self.w_diff.configure(state="disabled")

    def _auswahl(self, _e=None):
        zeilen = self.tabelle.auswahl()
        if not zeilen or self._opt is None:
            return
        nr = zeilen[0][0]
        kand = self._opt.get("kandidaten") or []
        k = kand[nr - 1] if isinstance(nr, int) and 1 <= nr <= len(kand) else None
        if not isinstance(k, dict) or not k.get("ueberlebt"):
            self._diff_setzen("nur überlebende Kandidaten werden verglichen")
            return
        neu = k.get("werte") or {}
        spur = self._spur_angezeigt
        self._diff_setzen(diff_text(spur, alte_werte(spur, list(neu), self.hier), neu))

    def kopieren(self):
        text = self.w_diff.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.reiter.ls.melde("Unterschied kopiert")
        return text
```

Zur Reihenfolge im Knopf: Ein ungültiger Wert nennt zuerst den Wert, danach kommt „erst Trockenlauf“ oder „Werte geändert …“, erst zuletzt „es läuft schon ein Lauf“. Während der Trockenlauf rechnet, zeigt der Tooltip also „erst Trockenlauf“ — der Grund, auf den Max wartet.

- [ ] **Step 5: In den Backtest-Reiter einhängen**

In `leitstand_backtests.py` direkt nach der Zeile `from leitstand_bedienung import Tabelle, Tooltip, setze_knopf` gezielt einfügen:

```python
from leitstand_optimieren import OptimierenBereich
```

Die letzte Zeile der Datei gezielt ersetzen: aus `BEREICHE = [ReplayBereich, EinzelBereich]` wird `BEREICHE = [ReplayBereich, EinzelBereich, OptimierenBereich]`.

Mit der Standardliste ist „Replay“ der erste und damit gewählte Unterreiter. Der Optimieren-Bereich baut sich auf, liest nur `spur_opt.json` und startet nichts — `test_feste_hinweiszeile` aus Aufgabe 7 bleibt so ohne Lauf.

- [ ] **Step 6: Tests laufen lassen**

Run: `$PY -m unittest tests.test_leitstand_optimieren tests.test_leitstand_backtests tests.test_leitstand_backtests_liste -v`
Erwartet: alle grün.

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage bleibt unverändert. `lesepruefung.py` beginnt nicht mit `test_` und wird von `discover` nicht als Test gesammelt.

- [ ] **Step 7: Commit**

```bash
git status --short
git add Agenten/Handel/leitstand_optimieren.py Agenten/Handel/leitstand_backtests.py Agenten/Handel/tests/lesepruefung.py Agenten/Handel/tests/test_leitstand_optimieren.py
git commit -m "Leitstand: Bereich Optimieren mit Trockenlauf zuerst und Unterschied zum Kopieren (Aufgabe 9)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: `backtest_urteile.py` — Vorschau ablegen und genau diese Vorschau übernehmen

**Files:**
- Modify: `Agenten/Handel/backtest_urteile.py` (Docstring, Importe, zwei Hilfsfunktionen, drei neue Funktionen, `main`)
- Test: `Agenten/Handel/tests/test_backtest_urteile.py` (neue Klasse `Vorschau`, Importe)

**Interfaces:**
- Consumes: im Modul vorhanden: `HIER`, `URTEILE`, `MOTOREN`, `wachen_laden(spur)`, `freigabe_schreiben(spur, bestanden, urteil, vorschau=False, tag=None) -> None | str`.
- Produces:
  - Aufruf `backtest_urteile.py [--spur S ...] --vorschau --vorschau-datei DATEI` — rechnet wie `--vorschau`, schreibt keine `wachen.json` und nicht `backtest_urteile.json`, legt aber `DATEI` ab: `{"stand": ISO mit Zeitzone, "art": "urteile-vorschau", "spuren": {spur: {"stand", "bestanden" (bool|None), "urteil", "kennzahlen", "alt" (bisheriger backtest_bestanden), "sha256" (der wachen.json beim Lesen)}}}`.
  - Aufruf `backtest_urteile.py --aus-vorschau DATEI` — fährt **keinen** Motor. Schreibt genau die Urteile der Datei, wenn sie höchstens 60 min alt ist und jede betroffene `wachen.json` noch denselben SHA-256 hat. Sonst `nichts geschrieben - <Grund>` und Exit 2.
  - Konstanten `VORSCHAU_GUELTIG_MIN = 60`, `VORSCHAU_ZUKUNFT_MIN = 5`; Funktionen `vorschau_pruefen(daten, jetzt) -> str` ("" = gültig), `vorschau_ablegen(pfad, eintraege, stand)`, `aus_vorschau(pfad) -> int`, `_sha256(pfad) -> str|None`, `_jetzt_dt() -> datetime`.
  - Aufgabe 11 baut ihre Befehle genau auf diese zwei Aufrufe und zeigt die Gründe wörtlich an.

Das ist der **einzige** Weg, auf dem der Leitstand eine `wachen.json` berührt: Er startet `--aus-vorschau` erst nach Max' Bestätigung. Er schreibt nicht selbst, und er übernimmt nur, was Max in der Vorschau gesehen hat. Ein neuer Motorlauf zwischen Vorschau und Eintrag könnte ein anderes Urteil liefern (neue Kerzen). Darum rechnet `--aus-vorschau` nicht, es übernimmt. Der Hash schützt vor dem zweiten Fall: Jemand hat die `wachen.json` zwischendurch von Hand geändert. Dann passt die Vorschau (Spalte „alt“) nicht mehr, und es wird nichts geschrieben.

Die Datei bleibt ASCII wie bisher (Umlaute als ae/oe/ue). Alle Änderungen gezielt; die Datei nicht neu schreiben (CRLF/LF).

- [ ] **Step 1: Tests schreiben**

In `tests/test_backtest_urteile.py` den Importblock gezielt ersetzen. Aus

```python
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
```

wird

```python
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
```

Direkt vor `if __name__ == "__main__":` die neue Klasse einfügen:

```python
JETZT = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


class Vorschau(Basis):
    """--vorschau-datei legt ab, --aus-vorschau uebernimmt genau das - ohne Motor."""

    def setUp(self):
        super().setUp()
        self.jetzt = JETZT
        self.urteile = Path(self.tmp.name) / "backtest_urteile.json"
        self.datei = Path(self.tmp.name) / "ablage" / "v.json"
        self.motor = Mock(return_value=(True, "Gitter schlaegt Halten", {"zyklen": 7}))
        for p in (patch.object(bu, "URTEILE", self.urteile),
                  patch.dict(bu.MOTOREN, {"gitter": self.motor}, clear=True),
                  patch.object(bu, "_jetzt_dt", side_effect=lambda: self.jetzt)):
            p.start()
            self.addCleanup(p.stop)
        self.wachen = self._wachen(WACHEN_MIT_BACKTEST)

    def _main(self, *args):
        aus, fehler = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["backtest_urteile.py"] + list(args)), \
                redirect_stdout(aus), redirect_stderr(fehler):
            rc = bu.main()
        return rc, aus.getvalue()

    def _vorschau(self):
        rc, text = self._main("--spur", "gitter", "--vorschau",
                              "--vorschau-datei", str(self.datei))
        self.assertEqual(rc, 0)
        self.motor.reset_mock()
        return text

    def _tag(self):
        return JETZT.astimezone().strftime("%Y-%m-%d")

    def test_vorschau_datei_schreibt_keine_wachen(self):
        text = self._vorschau()
        self.assertIn("Vorschau-Datei: %s" % self.datei, text)
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_MIT_BACKTEST)
        self.assertFalse(self.urteile.exists())
        d = json.loads(self.datei.read_text("utf-8"))
        self.assertEqual(d["art"], "urteile-vorschau")
        self.assertEqual(d["stand"], "2026-09-29T12:00:00+00:00")
        e = d["spuren"]["gitter"]
        self.assertIs(e["bestanden"], True)
        self.assertIs(e["alt"], False)
        self.assertEqual(e["urteil"], "Gitter schlaegt Halten")
        self.assertEqual(e["sha256"],
                         hashlib.sha256(self.wachen.read_bytes()).hexdigest())
        self.assertEqual(list(self.datei.parent.glob("*.tmp")), [])

    def test_aus_vorschau_schreibt_genau_die_werte_ohne_motor(self):
        self._vorschau()
        self.jetzt = JETZT + timedelta(minutes=10)
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 0)
        self.motor.assert_not_called()
        self.assertIn("geschrieben: gitter/wachen.json", text)
        d = json.loads(self.wachen.read_text("utf-8"))
        self.assertTrue(d["freigabe"]["backtest_bestanden"])
        self.assertEqual(d["freigabe"]["backtest_urteil"], "Gitter schlaegt Halten")
        self.assertEqual(d["freigabe"]["backtest_geprueft_am"], self._tag())
        self.assertFalse(d["handel_erlaubt"])
        self.assertFalse(d["freigabe"]["erfuellt"])

    def test_zu_alte_vorschau_schreibt_nichts(self):
        self._vorschau()
        self.jetzt = JETZT + timedelta(minutes=61)
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("nichts geschrieben - Vorschau aelter als 60 min", text)
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_MIT_BACKTEST)

    def test_geaenderte_wachen_schreibt_nichts(self):
        self._vorschau()
        von_hand = WACHEN_MIT_BACKTEST.replace('"papierlauf_min_wochen": 6',
                                               '"papierlauf_min_wochen": 7')
        self.wachen.write_text(von_hand, encoding="utf-8")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("nichts geschrieben - gitter/wachen.json hat sich seit der "
                      "Vorschau geaendert", text)
        self.assertEqual(self.wachen.read_text("utf-8"), von_hand)

    def test_zukunftsstand_wird_abgelehnt(self):
        self._vorschau()
        self.jetzt = JETZT - timedelta(minutes=10)
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("Stand liegt in der Zukunft", text)

    def test_unlesbare_vorschau(self):
        self.datei.parent.mkdir(parents=True)
        self.datei.write_text("{kaputt", encoding="utf-8")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("nichts geschrieben - Vorschau unlesbar", text)
        rc, text = self._main("--aus-vorschau", str(self.datei.with_name("fehlt.json")))
        self.assertIn("Vorschau unlesbar", text)
        self.assertEqual(bu.vorschau_pruefen({"art": "urteile-vorschau", "spuren": {},
                                              "stand": "2026-09-29T12:00:00"}, JETZT),
                         "Vorschau ohne Stand")

    def test_unbekannte_spur_schreibt_nichts(self):
        self.datei.parent.mkdir(parents=True)
        self.datei.write_text(json.dumps({
            "stand": JETZT.isoformat(), "art": "urteile-vorschau",
            "spuren": {"squeeze": {"bestanden": True, "urteil": "x", "sha256": "0"}}}),
            encoding="utf-8")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("unbekannte Spur in der Vorschau: squeeze", text)

    def test_optionskonflikte(self):
        for args in (("--vorschau-datei", "x.json"),
                     ("--aus-vorschau", "x.json", "--vorschau"),
                     ("--aus-vorschau", "x.json", "--spur", "gitter")):
            with self.assertRaises(SystemExit):
                self._main(*args)
        self.motor.assert_not_called()

    def test_unveraendert_wird_gemeldet(self):
        schon = WACHEN_MIT_BACKTEST.replace(
            '"backtest_bestanden": false,',
            '"backtest_bestanden": true,\n    "backtest_urteil": "Gitter schlaegt '
            'Halten",\n    "backtest_geprueft_am": "%s",' % self._tag())
        self.wachen.write_text(schon, encoding="utf-8")
        self._vorschau()
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 0)
        self.assertIn("unveraendert: gitter/wachen.json", text)
        self.assertEqual(self.wachen.read_text("utf-8"), schon)

    def test_urteile_datei_wird_fortgeschrieben(self):
        self.urteile.write_text(json.dumps({
            "stand": "alt", "ohne_motor": ["squeeze"],
            "spuren": {"orbk": {"bestanden": False}}}), encoding="utf-8")
        self._vorschau()
        self._main("--aus-vorschau", str(self.datei))
        d = json.loads(self.urteile.read_text("utf-8"))
        self.assertEqual(d["ohne_motor"], ["squeeze"])
        self.assertEqual(d["spuren"]["orbk"], {"bestanden": False})
        g = d["spuren"]["gitter"]
        self.assertTrue(g["aus_vorschau"])
        self.assertTrue(g["bestanden"])
        self.assertTrue(g["geschrieben"])
```

- [ ] **Step 2: Test laufen lassen — er muss scheitern**

Run: `$PY -m unittest tests.test_backtest_urteile -v`
Erwartet: Die alten Tests bleiben grün. Die neuen scheitern mit `AttributeError: <module 'backtest_urteile' …> does not have the attribute '_jetzt_dt'`.

- [ ] **Step 3: `backtest_urteile.py` gezielt ändern**

(a) Im Docstring gezielt ersetzen. Aus

```
    scanner/.venv/Scripts/python.exe backtest_urteile.py --vorschau    # schreibt nichts
"""
```

wird

```
    scanner/.venv/Scripts/python.exe backtest_urteile.py --vorschau    # schreibt nichts
    scanner/.venv/Scripts/python.exe backtest_urteile.py --vorschau --vorschau-datei V.json
    scanner/.venv/Scripts/python.exe backtest_urteile.py --aus-vorschau V.json

VORSCHAU UEBERNEHMEN (der Weg des Leitstands)
  --vorschau-datei legt die Vorschau als Datei ab, mit dem SHA-256 jeder
  gelesenen wachen.json. --aus-vorschau faehrt KEINEN Motor, sondern schreibt
  genau diese Urteile - nur wenn die Vorschau hoechstens 60 min alt ist und
  keine wachen.json sich seitdem geaendert hat. Sonst: nichts geschrieben,
  Exit 2. So landet in der Datei, was Max gesehen und bestaetigt hat, nicht
  das Ergebnis eines neuen Laufs mit neueren Kerzen.
"""
```

(b) Importe gezielt ersetzen. Aus `import argparse` wird

```python
import argparse
import hashlib
```

(c) Direkt unter `ZEITLIMIT_S = 900` einfügen:

```python
VORSCHAU_GUELTIG_MIN = 60
VORSCHAU_ZUKUNFT_MIN = 5      # Uhren zweier Laeufe duerfen so weit auseinander liegen
```

(d) `_jetzt` gezielt ersetzen. Aus

```python
def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
```

wird

```python
def _jetzt_dt():
    return datetime.now(timezone.utc)


def _jetzt():
    return _jetzt_dt().isoformat(timespec="seconds")


def _sha256(pfad):
    """SHA-256 der Datei als Hex, oder None wenn sie nicht lesbar ist."""
    try:
        return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()
    except OSError:
        return None
```

(e) Direkt vor `def main():` einfügen:

```python
# --- Vorschau ablegen und uebernehmen --------------------------------------

def vorschau_ablegen(pfad, eintraege, stand):
    """Die Vorschau als Datei ablegen (erst .tmp, dann umbenennen)."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps({"stand": stand, "art": "urteile-vorschau",
                               "spuren": eintraege}, ensure_ascii=False, indent=2)
                   + "\n", encoding="utf-8")
    os.replace(tmp, pfad)


def vorschau_pruefen(daten, jetzt):
    """"" wenn die Vorschau uebernommen werden darf, sonst der Grund."""
    if (not isinstance(daten, dict) or daten.get("art") != "urteile-vorschau"
            or not isinstance(daten.get("spuren"), dict)):
        return "Vorschau unlesbar"
    try:
        stand = datetime.fromisoformat(str(daten.get("stand")))
    except ValueError:
        return "Vorschau ohne Stand"
    if stand.tzinfo is None:
        return "Vorschau ohne Stand"
    alter_min = (jetzt - stand).total_seconds() / 60
    if alter_min < -VORSCHAU_ZUKUNFT_MIN:
        return "Stand liegt in der Zukunft"
    if alter_min > VORSCHAU_GUELTIG_MIN:
        return "Vorschau aelter als %d min" % VORSCHAU_GUELTIG_MIN
    return ""


def _urteile_laden():
    if URTEILE.exists():
        try:
            d = json.loads(URTEILE.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
        except ValueError:
            pass
    return {}


def aus_vorschau(pfad):
    """Genau die Urteile der Vorschau schreiben - ohne Motor. Exit-Code."""
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        daten = None
    grund = vorschau_pruefen(daten, _jetzt_dt())
    if not grund:
        # Erst ALLES pruefen, dann schreiben: keine halbe Uebernahme.
        for spur, e in sorted(daten["spuren"].items()):
            if spur not in MOTOREN or not isinstance(e, dict):
                grund = "unbekannte Spur in der Vorschau: %s" % spur
                break
            b = e.get("bestanden")
            if not (b is None or isinstance(b, bool)):
                grund = "Vorschau unlesbar"
                break
            sha = _sha256(HIER / spur / "wachen.json")
            if sha is None or sha != e.get("sha256"):
                grund = "%s/wachen.json hat sich seit der Vorschau geaendert" % spur
                break
    if grund:
        print("nichts geschrieben - %s" % grund)
        return 2

    tag = datetime.fromisoformat(daten["stand"]).astimezone().strftime("%Y-%m-%d")
    alt = _urteile_laden()
    aus = {"stand": _jetzt(), "spuren": dict(alt.get("spuren") or {}),
           "ohne_motor": alt.get("ohne_motor") or []}
    rc = 0
    for spur, e in sorted(daten["spuren"].items()):
        if e.get("bestanden") is None:
            print("nicht ermittelbar: %s - nichts zu schreiben" % spur)
            continue
        vorher = _sha256(HIER / spur / "wachen.json")
        try:
            hinweis = freigabe_schreiben(spur, e["bestanden"], e.get("urteil"),
                                         tag=tag)
        except OSError as fehler:
            hinweis = str(fehler)
        if hinweis:
            print("nicht geschrieben: %s - %s" % (spur, hinweis))
            rc = 1
        elif _sha256(HIER / spur / "wachen.json") == vorher:
            print("unveraendert: %s/wachen.json" % spur)
        else:
            print("geschrieben: %s/wachen.json" % spur)
        aus["spuren"][spur] = {
            "stand": e.get("stand"), "bestanden": e["bestanden"],
            "urteil": e.get("urteil"), "kennzahlen": e.get("kennzahlen") or {},
            "geschrieben": not hinweis, "hinweis": hinweis, "aus_vorschau": True,
        }
    URTEILE.write_text(json.dumps(aus, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    return rc
```

(f) In `main` gezielt ersetzen. Aus

```python
    ap.add_argument("--vorschau", action="store_true", help="nichts schreiben")
    a = ap.parse_args()

    spuren = a.spur or sorted(MOTOREN)
```

wird

```python
    ap.add_argument("--vorschau", action="store_true", help="nichts schreiben")
    ap.add_argument("--vorschau-datei", help="Vorschau zusaetzlich als Datei ablegen")
    ap.add_argument("--aus-vorschau", help="genau diese Vorschau uebernehmen")
    a = ap.parse_args()
    if a.vorschau_datei and not a.vorschau:
        ap.error("--vorschau-datei nur zusammen mit --vorschau")
    if a.aus_vorschau and (a.vorschau or a.spur):
        ap.error("--aus-vorschau steht allein (die Spuren kommen aus der Datei)")
    if a.aus_vorschau:
        return aus_vorschau(a.aus_vorschau)

    beginn = _jetzt()
    vorschau = {}
    spuren = a.spur or sorted(MOTOREN)
```

(g) In `main` gezielt ersetzen. Aus

```python
    for spur in spuren:
        w = wachen_laden(spur)
        try:
```

wird

```python
    for spur in spuren:
        sha = _sha256(HIER / spur / "wachen.json")   # VOR dem Motor: was Max sieht
        w = wachen_laden(spur)
        try:
```

(h) In `main` gezielt ersetzen. Aus

```python
            "kennzahlen": kennzahlen, "geschrieben": not a.vorschau
            and bestanden is not None, "hinweis": hinweis,
        }
```

wird

```python
            "kennzahlen": kennzahlen, "geschrieben": not a.vorschau
            and bestanden is not None, "hinweis": hinweis,
        }
        vorschau[spur] = {"stand": aus["spuren"][spur]["stand"],
                          "bestanden": bestanden, "urteil": urteil,
                          "kennzahlen": kennzahlen, "alt": alt_wert,
                          "sha256": sha}
```

(i) In `main` gezielt ersetzen. Aus

```python
    else:
        print("\n(Vorschau - nichts geschrieben)")
    return 0
```

wird

```python
    else:
        print("\n(Vorschau - nichts geschrieben)")
        if a.vorschau_datei:
            vorschau_ablegen(a.vorschau_datei, vorschau, beginn)
            print("Vorschau-Datei: %s" % a.vorschau_datei)
    return 0
```

Der Stand der Vorschau ist `beginn`, also der Zeitpunkt, an dem die `wachen.json` gelesen und gehasht wurden. Die 60 Minuten zählen darum ab dem Lesen, nicht ab dem Ende der Motorläufe. Das ist die vorsichtigere Uhr.

- [ ] **Step 4: Diff ansehen**

Run: `git diff --stat Agenten/Handel/backtest_urteile.py` und `git diff Agenten/Handel/backtest_urteile.py | head -80`
Erwartet: nur Einfügungen und die neun Stellen oben, keine Zeilenende-Umstellung (kein Diff über die ganze Datei).

- [ ] **Step 5: Tests laufen lassen**

Run: `$PY -m unittest tests.test_backtest_urteile -v`
Erwartet: alle grün, 26 Tests (16 alte, 10 neue).

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage bleibt unverändert.

- [ ] **Step 6: Commit**

```bash
git status --short
git add Agenten/Handel/backtest_urteile.py Agenten/Handel/tests/test_backtest_urteile.py
git commit -m "backtest_urteile: Vorschau als Datei ablegen und genau diese uebernehmen (Aufgabe 10)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Bereich Urteile `leitstand_urteile.py`

**Files:**
- Create: `Agenten/Handel/leitstand_urteile.py`
- Modify: `Agenten/Handel/leitstand_backtests.py` (ein Import, die Zeile `BEREICHE = …`)
- Test: `Agenten/Handel/tests/test_leitstand_urteile.py`

**Interfaces:**
- Consumes:
  - aus Aufgabe 4: `ZeitDialog(eltern, titel, zeitlimit_s=ZEITLIMIT_S, uhr=time.monotonic)` mit `.inhalt`, `.fertig(wert)`, `.zeige_modal()`; `Tabelle`, `Tooltip`, `setze_knopf`.
  - aus Aufgabe 6: `ll.zeitstempel()`, `ll.VORSCHAU_ENDUNG = "-vorschau.json"` (die Laufliste überspringt solche Dateien).
  - aus Aufgabe 7: `reiter.ablage() -> Path`, `reiter.starte(name, befehl, auswerten=None, fertig=None, stempel=None) -> bool`, `reiter.zustand`, `reiter.ls.melde`.
  - aus Aufgabe 9: `tests/lesepruefung.py` (`schreibstellen`, `importiert`).
  - aus Aufgabe 10: `bu.PY_SCANNER`, `bu.MOTOREN`, `bu.VORSCHAU_GUELTIG_MIN`, `bu.VORSCHAU_ZUKUNFT_MIN`; Aufrufe `--vorschau --vorschau-datei DATEI` und `--aus-vorschau DATEI` mit den Ausgabezeilen `geschrieben: …`, `unveraendert: …`, `nicht geschrieben: …`, `nichts geschrieben - …` (Exit 0/1/2); Format der Vorschau-Datei (`stand`, `art`, `spuren` mit `bestanden`, `urteil`, `alt`, `sha256`).
- Produces: `urteile_befehl(spuren, datei)`, `eintragen_befehl(datei)`, `lade_vorschau(pfad) -> dict|None`, `vorschau_zeilen(daten)`, `aenderungen(daten) -> list[str]`, `alter_min(daten, jetzt) -> float|None`, `darf_eintragen(datei, daten, jetzt) -> (bool, str)`, `ergebnis_zeile(exit_code, ausgabe) -> str`, `class EintragenDialog(ZeitDialog)(eltern, aenderungen, **kw)`, `class UrteileBereich(ttk.Frame)(eltern, reiter, dialog=EintragenDialog, uhr=None)` mit `TITEL = "Urteile"`. `leitstand_backtests.BEREICHE = [ReplayBereich, EinzelBereich, OptimierenBereich, UrteileBereich]`.

Ablauf: „Vorschau rechnen“ startet `backtest_urteile.py --vorschau --vorschau-datei <ablage>/<stempel>-urteile-vorschau.json` als gewöhnlichen Lauf. Das Ergebnis erscheint in der Tabelle. „Urteile eintragen …“ öffnet den Bestätigungsdialog: 120 s ohne Bedienung schließen ihn, Esc bricht ab, es gibt kein Tastenkürzel. Erst nach „Ja, eintragen“ startet `--aus-vorschau` mit genau dieser Datei. Der Bereich prüft Alter und Änderungen zur Bequemlichkeit selbst. Maßgeblich ist aber die Prüfung in `backtest_urteile.py`: Hash, Alter und Zukunft — sie meldet `nichts geschrieben - …`, und der Bereich zeigt das wörtlich. Einen Autostart gibt es nicht; die Motoren laufen bis zu 15 min.

Der Lauf der Vorschau heißt `urteile`, seine Ablage also `<stempel>-urteile.json`. Die Vorschau-Datei heißt `<stempel>-urteile-vorschau.json` — zwei Namen, keine Überschneidung. Die Laufliste zeigt nur den Lauf.

- [ ] **Step 1: Tests schreiben**

`tests/test_leitstand_urteile.py`:

```python
"""Bereich Urteile: Vorschau rechnen, bestaetigen, genau diese Vorschau
eintragen lassen - und selbst nichts schreiben.

Kein Motor, keine echte wachen.json: FakeSteuerung nimmt die Befehle nur
entgegen, die Vorschau-Datei legt der Test selbst in den Temp-Ordner, der
Dialog ist eine Attrappe (ausser im Zeitablauf-Test).

Direkt ausfuehrbar:  python tests/test_leitstand_urteile.py
"""

import json
import sys
import tempfile
import tkinter as tk
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import backtest_urteile as bu                                  # noqa: E402
import leitstand_backtests as lbt                              # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_urteile as lu                                 # noqa: E402
import lesepruefung                                            # noqa: E402

JETZT = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
VORSCHAU = {
    "stand": "2026-09-29T12:00:00+00:00", "art": "urteile-vorschau",
    "spuren": {
        "gitter": {"stand": "2026-09-29T12:00:00+00:00", "bestanden": True,
                   "urteil": "Gitter schlaegt Halten", "kennzahlen": {}, "alt": False,
                   "sha256": "aa"},
        "nautilus": {"stand": "2026-09-29T12:00:00+00:00", "bestanden": False,
                     "urteil": "Gitter -3 USDT", "kennzahlen": {}, "alt": False,
                     "sha256": "bb"},
        "orbk": {"stand": "2026-09-29T12:00:00+00:00", "bestanden": None,
                 "urteil": "kein URTEIL", "kennzahlen": {}, "alt": False,
                 "sha256": "cc"},
    },
}


class StubLeitstand:
    def __init__(self, root, zustand):
        self.root, self.zustand, self.meldungen = root, zustand, []
    def melde(self, text):
        self.meldungen.append(text)


class FakeSteuerung:
    def __init__(self, ablage):
        self.ablage, self.gestartet, self.lauf = ablage, [], None
        self.naechstes = ([], None)
    def starte(self, name, befehl, auswerten=None, stempel=None):
        if self.lauf:
            raise RuntimeError("es läuft schon: %s" % self.lauf)
        self.lauf = name
        self.gestartet.append((name, list(befehl), auswerten, stempel))
        return SimpleNamespace(name=name, befehl=list(befehl))
    def laeuft(self): return self.lauf is not None
    def abbrechen(self): pass
    def takt(self):
        erg, self.naechstes = self.naechstes, ([], None)
        if erg[1]:
            self.lauf = None
        return erg
    def status(self):
        return "Backtest: %s läuft seit 0:01" % self.lauf if self.lauf else ""


class TkBasis(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ablage = Path(self.tmp.name) / "ablage"
        self.ablage.mkdir()
        self.ls = StubLeitstand(self.root, lb.Zustand(Path(self.tmp.name) / "z.json"))
        self.st = FakeSteuerung(self.ablage)
    def reiter(self, bereiche=None):
        r = lbt.BacktestReiter(self.root, self.ls, steuerung=self.st, bereiche=bereiche)
        self.root.update_idletasks()
        return r


class Rein(unittest.TestCase):
    def test_befehle(self):
        p = Path("ablage") / "x-urteile-vorschau.json"
        self.assertEqual(lu.urteile_befehl(["gitter", "orbk"], p),
                         [str(bu.PY_SCANNER), "backtest_urteile.py", "--spur", "gitter",
                          "--spur", "orbk", "--vorschau", "--vorschau-datei", str(p)])
        self.assertEqual(lu.eintragen_befehl(p),
                         [str(bu.PY_SCANNER), "backtest_urteile.py", "--aus-vorschau",
                          str(p)])

    def test_lade_vorschau(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "v.json"
            p.write_text(json.dumps(VORSCHAU), encoding="utf-8")
            self.assertEqual(lu.lade_vorschau(p), VORSCHAU)
            p.write_text("{kaputt", encoding="utf-8")
            self.assertIsNone(lu.lade_vorschau(p))
            p.write_text(json.dumps(dict(VORSCHAU, art="anderes")), encoding="utf-8")
            self.assertIsNone(lu.lade_vorschau(p))
            self.assertIsNone(lu.lade_vorschau(Path(tmp) / "fehlt.json"))

    def test_zeilen_und_aenderungen(self):
        self.assertEqual(lu.vorschau_zeilen(VORSCHAU), [
            ("gitter", "bestanden", "false → true", "Gitter schlaegt Halten"),
            ("nautilus", "nicht bestanden", "false → false", "Gitter -3 USDT"),
            ("orbk", "nicht ermittelbar", "false → bleibt", "kein URTEIL")])
        self.assertEqual(lu.aenderungen(VORSCHAU), [
            "gitter/wachen.json: backtest_bestanden false → true",
            "nautilus/wachen.json: backtest_bestanden false → false "
            "(Urteilstext und Datum neu)"])

    def test_darf_eintragen(self):
        p = Path("v.json")
        self.assertEqual(lu.darf_eintragen(None, None, JETZT),
                         (False, "erst Vorschau rechnen"))
        self.assertEqual(lu.darf_eintragen(p, None, JETZT),
                         (False, "Vorschau nicht lesbar"))
        self.assertEqual(lu.darf_eintragen(p, VORSCHAU, JETZT), (True, ""))
        self.assertEqual(lu.darf_eintragen(p, VORSCHAU, JETZT + timedelta(minutes=61)),
                         (False, "Vorschau älter als 60 min"))
        self.assertEqual(lu.darf_eintragen(p, VORSCHAU, JETZT - timedelta(minutes=10)),
                         (False, "Vorschau liegt in der Zukunft"))
        nur_orbk = dict(VORSCHAU, spuren={"orbk": VORSCHAU["spuren"]["orbk"]})
        self.assertEqual(lu.darf_eintragen(p, nur_orbk, JETZT),
                         (False, "keine Änderung"))
        self.assertEqual(lu.darf_eintragen(p, dict(VORSCHAU, stand="gestern"), JETZT),
                         (False, "Vorschau nicht lesbar"))

    def test_ergebnis_zeile(self):
        self.assertEqual(lu.ergebnis_zeile(0, "geschrieben: gitter/wachen.json\n"
                                              "unveraendert: nautilus/wachen.json\n"),
                         "geschrieben: gitter/wachen.json; "
                         "unveraendert: nautilus/wachen.json")
        self.assertEqual(lu.ergebnis_zeile(2, "nichts geschrieben - gitter/wachen.json "
                                              "hat sich seit der Vorschau geaendert\n"),
                         "nichts geschrieben - gitter/wachen.json hat sich seit der "
                         "Vorschau geaendert")
        self.assertEqual(lu.ergebnis_zeile(1, "nicht geschrieben: orbk - JSON\n"),
                         "Exit 1 — nicht geschrieben: orbk - JSON")
        self.assertEqual(lu.ergebnis_zeile(0, ""), "nichts zu schreiben")


class Lesepruefung(unittest.TestCase):
    def test_urteile_bereich_schreibt_nichts(self):
        self.assertEqual(lesepruefung.schreibstellen(lu.__file__), [])
        self.assertFalse(lesepruefung.importiert(lu.__file__, "subprocess"))

    def test_eingebunden(self):
        self.assertIn(lu.UrteileBereich, lbt.BEREICHE)


def attrappe(antwort, nebenbei=None):
    class Dialog:
        aufrufe = []

        def __init__(self, eltern, aenderungen, **kw):
            Dialog.aufrufe.append(list(aenderungen))

        def zeige_modal(self):
            if nebenbei:
                nebenbei()
            return antwort
    return Dialog


class Bereich(TkBasis):
    def setUp(self):
        super().setUp()
        self.jetzt = JETZT
        self.antwort, self.nebenbei = "ja", None

    def _bereich(self):
        fabrik = lambda e, r: lu.UrteileBereich(          # noqa: E731
            e, r, dialog=attrappe(self.antwort, self.nebenbei), uhr=lambda: self.jetzt)
        self.r = self.reiter([fabrik])
        return self.r.bereiche[0]

    def _ende(self, name, exit_code=0, ausgabe=""):
        self.st.naechstes = ([], (self.ablage / "x.json", {
            "name": name, "exit_code": exit_code, "abgebrochen": False,
            "ausgabe": ausgabe}))
        self.r._takt()
        self.root.update_idletasks()

    def _mit_vorschau(self):
        b = self._bereich()
        b.vorschau()
        name, befehl, _a, stempel = self.st.gestartet[-1]
        datei = Path(befehl[-1])
        datei.write_text(json.dumps(VORSCHAU), encoding="utf-8")
        self._ende(name)
        return b, datei

    def test_kein_autostart_und_eintragen_gesperrt(self):
        b = self._bereich()
        self.assertEqual(self.st.gestartet, [])
        self.assertIn("disabled", b.k_eintragen.state())
        self.assertEqual(b.tip_eintragen.text, "erst Vorschau rechnen")

    def test_vorschau_rechnen(self):
        b = self._bereich()
        b.vorschau()
        name, befehl, _a, stempel = self.st.gestartet[0]
        self.assertEqual(name, "urteile")
        self.assertEqual(befehl[-2:], ["--vorschau-datei",
                                       str(self.ablage / ("%s-urteile-vorschau.json"
                                                          % stempel))])
        self.assertEqual(befehl.count("--spur"), len(bu.MOTOREN))
        Path(befehl[-1]).write_text(json.dumps(VORSCHAU), encoding="utf-8")
        self._ende(name)
        self.assertEqual(len(b.tabelle.sichtbare()), 3)
        self.assertNotIn("disabled", b.k_eintragen.state())

    def test_keine_spur_gewaehlt(self):
        b = self._bereich()
        for v in b.vars.values():
            v.set(False)
        b._knoepfe()
        self.assertIn("disabled", b.k_vorschau.state())
        self.assertEqual(b.tip_vorschau.text, "keine Spur gewählt")

    def test_eintragen_nach_ja(self):
        b, datei = self._mit_vorschau()
        b.eintragen()
        name, befehl, _a, _s = self.st.gestartet[-1]
        self.assertEqual(name, "urteile-eintragen")
        self.assertEqual(befehl[-2:], ["--aus-vorschau", str(datei)])
        self.assertEqual(b.dialog.aufrufe, [lu.aenderungen(VORSCHAU)])
        self._ende(name, 0, "geschrieben: gitter/wachen.json\n")
        self.assertEqual(b.w_ergebnis.cget("text"), "geschrieben: gitter/wachen.json")
        self.assertIn("disabled", b.k_eintragen.state())    # Vorschau verbraucht
        self.assertEqual(b.tip_eintragen.text, "erst Vorschau rechnen")

    def test_abbrechen_schreibt_nichts(self):
        self.antwort = "abgebrochen"
        b, _datei = self._mit_vorschau()
        n = len(self.st.gestartet)
        b.eintragen()
        self.assertEqual(len(self.st.gestartet), n)
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "Urteile nicht eingetragen — nichts geschrieben")
        self.assertNotIn("disabled", b.k_eintragen.state())

    def test_vorschau_veraltet_waehrend_des_dialogs(self):
        self.nebenbei = lambda: setattr(self, "jetzt", JETZT + timedelta(minutes=61))
        b, _datei = self._mit_vorschau()
        n = len(self.st.gestartet)
        b.eintragen()
        self.assertEqual(len(self.st.gestartet), n)
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "Urteile nicht eingetragen — nichts geschrieben "
                         "(Vorschau älter als 60 min)")

    def test_alte_vorschau_sperrt_beim_refresh(self):
        b, _datei = self._mit_vorschau()
        self.jetzt = JETZT + timedelta(minutes=61)
        b.refresh()
        self.assertIn("disabled", b.k_eintragen.state())
        self.assertEqual(b.tip_eintragen.text, "Vorschau älter als 60 min")

    def test_vorschau_ohne_ergebnis(self):
        b = self._bereich()
        b.vorschau()
        self._ende("urteile", exit_code=1)
        self.assertEqual(b.w_ergebnis.cget("text"),
                         "Vorschau ohne Ergebnis (Exit 1) — Ausgabe oben")
        self.assertIn("disabled", b.k_eintragen.state())

    def test_gescheiterter_start_behaelt_die_vorschau(self):
        b, datei = self._mit_vorschau()
        self.st.lauf = "fremder-lauf"          # Steuerung lehnt den Start ab
        b.eintragen()
        self.assertEqual(b.datei, datei)
        self.st.lauf = None
        b._knoepfe()
        self.assertNotIn("disabled", b.k_eintragen.state())

    def test_echter_dialog_laeuft_ab_ohne_return_kuerzel(self):
        uhr = [0.0]
        d = lu.EintragenDialog(self.root, ["gitter/wachen.json: x"],
                               uhr=lambda: uhr[0])
        self.assertEqual(d.bind("<Return>"), "")
        uhr[0] = 121.0
        d._takt()
        self.assertEqual(d.ergebnis, "zeitablauf")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen lassen — er muss scheitern**

Run: `$PY -m unittest tests.test_leitstand_urteile -v`
Erwartet: `ModuleNotFoundError: No module named 'leitstand_urteile'`.

- [ ] **Step 3: `leitstand_urteile.py` schreiben**

```python
"""Bereich Urteile im Backtest-Reiter des Leitstands.

"Vorschau rechnen" faehrt backtest_urteile.py --vorschau --vorschau-datei:
Die Motoren laufen, geschrieben wird nur die Vorschau-Datei in der Ablage.
"Urteile eintragen ..." fragt nach (120 s, Esc = Abbruch, kein Kuerzel) und
startet erst dann backtest_urteile.py --aus-vorschau mit GENAU dieser Datei:
kein neuer Motorlauf. Nur so kommt der Leitstand an eine wachen.json, und
dort nur an die drei backtest-Felder der freigabe.

Dieses Modul schreibt selbst NICHTS (AST-Pruefung in
tests/test_leitstand_urteile.py). Die Pruefungen hier (Alter, Aenderungen)
sind Bequemlichkeit; massgeblich prueft backtest_urteile.py (Hash, Alter,
Zukunft) und meldet "nichts geschrieben - <Grund>".
"""

import json
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk

import backtest_urteile as bu
import leitstand_laeufe as ll
from leitstand_bedienung import Tabelle, Tooltip, ZeitDialog, setze_knopf

SPALTEN = ("Spur", "Urteil", "backtest_bestanden", "Text")
URTEIL_TEXT = {True: "bestanden", False: "nicht bestanden", None: "nicht ermittelbar"}


# --- rein ------------------------------------------------------------------

def urteile_befehl(spuren, datei):
    befehl = [str(bu.PY_SCANNER), "backtest_urteile.py"]
    for s in spuren:
        befehl += ["--spur", s]
    return befehl + ["--vorschau", "--vorschau-datei", str(datei)]


def eintragen_befehl(datei):
    return [str(bu.PY_SCANNER), "backtest_urteile.py", "--aus-vorschau", str(datei)]


def lade_vorschau(pfad):
    """Die Vorschau-Datei, oder None wenn sie fehlt, kaputt oder fremd ist."""
    try:
        d = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (not isinstance(d, dict) or d.get("art") != "urteile-vorschau"
            or not isinstance(d.get("spuren"), dict)):
        return None
    return d


def _wert(v):
    if v is None:
        return "—"
    return "true" if v is True else "false" if v is False else str(v)


def _eintraege(daten):
    return [(s, e) for s, e in sorted(daten["spuren"].items()) if isinstance(e, dict)]


def vorschau_zeilen(daten):
    zeilen = []
    for spur, e in _eintraege(daten):
        neu = e.get("bestanden")
        wechsel = "%s → %s" % (_wert(e.get("alt")),
                               "bleibt" if neu is None else _wert(neu))
        zeilen.append((spur, URTEIL_TEXT.get(neu, "?"), wechsel,
                       str(e.get("urteil") or "")))
    return zeilen


def aenderungen(daten):
    """Was --aus-vorschau schreiben wuerde, je Spur eine Zeile."""
    aus = []
    for spur, e in _eintraege(daten):
        neu = e.get("bestanden")
        if neu is None:
            continue                    # nicht ermittelbar: alter Wert bleibt
        zeile = "%s/wachen.json: backtest_bestanden %s → %s" % (
            spur, _wert(e.get("alt")), _wert(neu))
        if e.get("alt") == neu:
            zeile += " (Urteilstext und Datum neu)"
        aus.append(zeile)
    return aus


def alter_min(daten, jetzt):
    try:
        stand = datetime.fromisoformat(str(daten.get("stand")))
    except ValueError:
        return None
    if stand.tzinfo is None:
        return None
    return (jetzt - stand).total_seconds() / 60


def darf_eintragen(datei, daten, jetzt):
    if datei is None:
        return False, "erst Vorschau rechnen"
    if daten is None:
        return False, "Vorschau nicht lesbar"
    alter = alter_min(daten, jetzt)
    if alter is None:
        return False, "Vorschau nicht lesbar"
    if alter < -bu.VORSCHAU_ZUKUNFT_MIN:
        return False, "Vorschau liegt in der Zukunft"
    if alter > bu.VORSCHAU_GUELTIG_MIN:
        return False, "Vorschau älter als %d min" % bu.VORSCHAU_GUELTIG_MIN
    if not aenderungen(daten):
        return False, "keine Änderung"
    return True, ""


def ergebnis_zeile(exit_code, ausgabe):
    zeilen = [z.strip() for z in (ausgabe or "").splitlines() if z.strip()]
    if exit_code == 2:
        return next((z for z in reversed(zeilen) if z.startswith("nichts geschrieben")),
                    "nichts geschrieben (Exit 2)")
    treffer = "; ".join(z for z in zeilen if z.startswith(
        ("geschrieben:", "unveraendert:", "nicht geschrieben:")))
    if exit_code == 0:
        return treffer or "nichts zu schreiben"
    return "Exit %s — %s" % (exit_code, treffer or "Ausgabe oben")


# --- Dialog ----------------------------------------------------------------

class EintragenDialog(ZeitDialog):
    """Ergebnis: "ja" | "abgebrochen" | "zeitablauf". Kein Return-Kuerzel."""

    def __init__(self, eltern, aenderungen, **kw):
        super().__init__(eltern, "Urteile eintragen", **kw)
        i = self.inhalt
        ttk.Label(i, text="Diese Urteile in die wachen.json schreiben?",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        for zeile in aenderungen:
            ttk.Label(i, text=zeile).pack(anchor="w", padx=(10, 0))
        ttk.Label(i, text="handel_erlaubt und freigabe.erfuellt bleiben unberührt.",
                  foreground="#555555").pack(anchor="w", pady=(6, 0))
        knoepfe = ttk.Frame(i)
        knoepfe.pack(anchor="e", pady=(10, 0))
        ttk.Button(knoepfe, text="Ja, eintragen",
                   command=lambda: self.fertig("ja")).pack(side="left", padx=4)
        ttk.Button(knoepfe, text="Abbrechen",
                   command=lambda: self.fertig("abgebrochen")).pack(side="left", padx=4)


# --- der Bereich -----------------------------------------------------------

class UrteileBereich(ttk.Frame):
    TITEL = "Urteile"

    def __init__(self, eltern, reiter, dialog=EintragenDialog, uhr=None):
        super().__init__(eltern, padding=8)
        self.reiter, self.dialog = reiter, dialog
        self.uhr = uhr or (lambda: datetime.now(timezone.utc))
        self._laeuft = False
        self.datei, self.daten = None, None      # die angezeigte Vorschau

        oben = ttk.Frame(self)
        oben.pack(fill="x")
        ttk.Label(oben, text="Spuren").pack(side="left")
        gemerkt = (reiter.zustand.get("werte") or {}).get("urteile_spuren")
        self.vars = {}
        for s in sorted(bu.MOTOREN):
            v = tk.BooleanVar(value=(s in gemerkt) if isinstance(gemerkt, list)
                              else True)
            ttk.Checkbutton(oben, text=s, variable=v,
                            command=self._knoepfe).pack(side="left", padx=4)
            self.vars[s] = v
        self.k_vorschau = ttk.Button(oben, text="Vorschau rechnen",
                                     command=self.vorschau)
        self.k_vorschau.pack(side="left", padx=(12, 0))
        self.tip_vorschau = Tooltip(self.k_vorschau)
        ttk.Label(self, text="Die Vorschau schreibt nichts. Eintragen übernimmt genau "
                             "diese Vorschau — kein neuer Lauf.",
                  foreground="#555555").pack(anchor="w", pady=(4, 0))

        self.tabelle = Tabelle(self, SPALTEN, reiter.zustand, "urteile", hoehe=4)
        self.tabelle.pack(fill="both", expand=True, pady=(4, 0))
        unten = ttk.Frame(self)
        unten.pack(fill="x", pady=(4, 0))
        self.k_eintragen = ttk.Button(unten, text="Urteile eintragen …",
                                      command=self.eintragen)
        self.k_eintragen.pack(side="left")
        self.tip_eintragen = Tooltip(self.k_eintragen)
        self.w_ergebnis = ttk.Label(unten, text="")
        self.w_ergebnis.pack(side="left", padx=12)
        self._knoepfe()

    def gewaehlte(self):
        return [s for s, v in self.vars.items() if v.get()]

    def _knoepfe(self):
        if not self.gewaehlte():
            setze_knopf(self.k_vorschau, self.tip_vorschau, False, "keine Spur gewählt")
        else:
            setze_knopf(self.k_vorschau, self.tip_vorschau, not self._laeuft,
                        "es läuft schon ein Lauf")
        erlaubt, grund = darf_eintragen(self.datei, self.daten, self.uhr())
        if erlaubt and self._laeuft:
            erlaubt, grund = False, "es läuft schon ein Lauf"
        setze_knopf(self.k_eintragen, self.tip_eintragen, erlaubt, grund)

    # Bereich-Schnittstelle
    def lauf_wechsel(self, laeuft):
        self._laeuft = laeuft
        self._knoepfe()

    def refresh(self):
        self._knoepfe()                          # die Vorschau altert

    # Vorschau
    def vorschau(self):
        spuren = self.gewaehlte()
        if not spuren or self._laeuft:
            return
        self.reiter.zustand.merke_in("werte", "urteile_spuren", spuren)
        stempel = ll.zeitstempel()
        datei = self.reiter.ablage() / ("%s-urteile%s" % (stempel, ll.VORSCHAU_ENDUNG))
        self.datei, self.daten = None, None
        self.tabelle.setze([])
        if self.reiter.starte("urteile", urteile_befehl(spuren, datei),
                              fertig=lambda _p, d: self._vorschau_fertig(datei, d),
                              stempel=stempel):
            self.w_ergebnis.config(text="Vorschau läuft …")
        self._knoepfe()

    def _vorschau_fertig(self, datei, daten):
        if daten.get("exit_code") != 0:
            self.w_ergebnis.config(text="Vorschau ohne Ergebnis (Exit %s) — Ausgabe oben"
                                   % daten.get("exit_code"))
        else:
            d = lade_vorschau(datei)
            if d is None:
                self.w_ergebnis.config(text="Vorschau nicht lesbar")
            else:
                self.datei, self.daten = datei, d
                self.tabelle.setze(vorschau_zeilen(d))
                self.w_ergebnis.config(text="Vorschau gilt %d min"
                                       % bu.VORSCHAU_GUELTIG_MIN)
        self._knoepfe()

    # Eintragen
    def eintragen(self):
        erlaubt, grund = darf_eintragen(self.datei, self.daten, self.uhr())
        if not erlaubt or self._laeuft:
            self.reiter.ls.melde(grund or "es läuft schon ein Lauf")
            return
        datei, daten = self.datei, self.daten
        antwort = self.dialog(self, aenderungen(daten)).zeige_modal()
        # Der Dialog kann bis zu 120 s offen gewesen sein: noch einmal pruefen.
        erlaubt, grund = darf_eintragen(self.datei, self.daten, self.uhr())
        if antwort != "ja" or not erlaubt or self.datei != datei:
            text = "Urteile nicht eingetragen — nichts geschrieben"
            if antwort == "ja" and grund:
                text += " (%s)" % grund
            self.w_ergebnis.config(text=text)
            self._knoepfe()
            return
        self.datei, self.daten = None, None      # verbraucht: kein zweites Mal
        if self.reiter.starte("urteile-eintragen", eintragen_befehl(datei),
                              fertig=lambda _p, d: self._eintragen_fertig(d)):
            self.w_ergebnis.config(text="trage ein …")
        else:
            self.datei, self.daten = datei, daten
        self._knoepfe()

    def _eintragen_fertig(self, daten):
        self.w_ergebnis.config(text=ergebnis_zeile(daten.get("exit_code"),
                                                   daten.get("ausgabe", "")))
        self._knoepfe()
```

- [ ] **Step 4: In den Backtest-Reiter einhängen**

In `leitstand_backtests.py` direkt nach der Zeile `from leitstand_optimieren import OptimierenBereich` gezielt einfügen:

```python
from leitstand_urteile import UrteileBereich
```

Die letzte Zeile der Datei gezielt ersetzen: aus `BEREICHE = [ReplayBereich, EinzelBereich, OptimierenBereich]` wird `BEREICHE = [ReplayBereich, EinzelBereich, OptimierenBereich, UrteileBereich]`.

- [ ] **Step 5: Tests laufen lassen**

Run: `$PY -m unittest tests.test_leitstand_urteile tests.test_leitstand_backtests -v`
Erwartet: alle grün.

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage bleibt unverändert.

- [ ] **Step 6: Commit**

```bash
git status --short
git add Agenten/Handel/leitstand_urteile.py Agenten/Handel/leitstand_backtests.py Agenten/Handel/tests/test_leitstand_urteile.py
git commit -m "Leitstand: Bereich Urteile - Vorschau rechnen, bestaetigen, genau diese eintragen (Aufgabe 11)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Markt-Reiter `leitstand_markt.py`

**Files:**
- Create: `Agenten/Handel/leitstand_markt.py`
- Test: `Agenten/Handel/tests/test_leitstand_markt.py`, `Agenten/Handel/tests/test_leitstand_markt_rein_lesend.py`

**Interfaces:**
- Consumes:
  - aus Aufgabe 4: `Tabelle(eltern, spalten, zustand, name, hoehe=10)` mit `.setze(zeilen)`, `.sichtbare()`; `Tooltip(widget)`; `setze_knopf(knopf, tip, erlaubt, grund)`; `Zustand.get`, `Zustand.merke_in`.
  - aus Aufgabe 9: `tests/lesepruefung.py` (`schreibstellen`, `importiert`).
  - die Schnittstelle der Reiter (Abschnitt „Dateien“): `leitstand.zustand`, `leitstand.melde`.
  - das Format von `prognose.py` (prognose.py:339–346): `datum` (`JJJJ-MM-TT`), `erzeugt` (ISO mit `+00:00`), `tore` (dict, Erklärungen unter `_<name>`), `maerkte_geprueft` (int), `treffer` (Liste von dicts: `inst`, `richtung`, `preis`, `score`, `cr`, `stop`, `ziel`, `risiko_prozent`, `umsatz_24h_usd`, `kennzahlen`, `offene_tore`, …). Die Dateien heißen `prognose_berichte/neuester.json` und `prognose_berichte/neuester.weit.json`.
- Produces: `BERICHTE`, `DATEIEN = {"streng": "neuester.json", "weit": "neuester.weit.json"}`, `ALTER_WARNUNG_H = 26`, `TREFFER_FELDER`, `lade_bericht(pfad) -> (dict|None, str)`, `alter_h(bericht, jetzt) -> float|None`, `kopfzeile(bericht, jetzt) -> str`, `warnung(bericht, jetzt) -> str`, `treffer_zeilen(bericht) -> list[tuple]`, `tore_zeilen(bericht) -> list[tuple]`, `class MarktReiter(ttk.Frame)(eltern, leitstand, ordner=None, uhr=None)` mit `refresh()`, `titel_zusatz()`, `status()`, `umschalten()`, `.fassung` (tk.StringVar), `.w_kopf`, `.w_warnung`, `.treffer`, `.tore`, `.r_weit`, `.tip_weit`. Aufgabe 13 baut ihn mit `MarktReiter(nb, leitstand)`.

`leitstand_markt.py` importiert `prognose` **nicht**: `prognose` zieht `okx` nach, einen Börsen-Client (Global Constraints). Den Ordner `BERICHTE` legt das Modul selbst fest, genauso wie `prognose.py` ihn nennt. Einen Knopf „Scan jetzt“ gibt es nicht, und der Reiter holt keine Kurse.

- [ ] **Step 1: Tests schreiben**

`tests/test_leitstand_markt_rein_lesend.py`:

```python
"""Markt-Reiter bleibt rein lesend: keine Schreibstelle, kein Prozess, kein
Boersen-Client (auch nicht ueber prognose.py, das okx importiert).

Direkt ausfuehrbar:  python tests/test_leitstand_markt_rein_lesend.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import leitstand_markt as lm                                   # noqa: E402
import lesepruefung                                            # noqa: E402


class ReinLesend(unittest.TestCase):
    def test_keine_schreibstelle(self):
        self.assertEqual(lesepruefung.schreibstellen(lm.__file__), [])

    def test_kein_prozess_und_kein_boersen_client(self):
        for modul in ("subprocess", "prognose", "okx", "ccxt", "requests", "urllib",
                      "kraken", "freigabefenster", "backtest_urteile"):
            self.assertFalse(lesepruefung.importiert(lm.__file__, modul), modul)


if __name__ == "__main__":
    unittest.main()
```

`tests/test_leitstand_markt.py`:

```python
"""Markt-Reiter: Bericht-Fixture wird angezeigt, fehlender oder kaputter
Bericht gibt einen Hinweis statt eines Absturzes, Alterswarnung ab 26 h,
Umschalter streng/weit.

Nur Temp-Dateien: kein echtes prognose_berichte/, kein Netz.

Direkt ausfuehrbar:  python tests/test_leitstand_markt.py
"""

import json
import sys
import tempfile
import tkinter as tk
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitstand_bedienung as lb                               # noqa: E402
import leitstand_markt as lm                                   # noqa: E402

ERZEUGT = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)
TREFFER = {"inst": "ZEC-USDC", "richtung": "long", "preis": 1419.51, "score": 65.2,
           "chance": 81.5, "risiko": 28.6, "verhaeltnis": 2.85, "stop": 1249.1688,
           "ziel": 1696.69, "risiko_prozent": 12.0, "cr": 1.63,
           "kennzahlen": {"rsi14": 67.3}, "offene_tore": [], "guenstig": True,
           "umsatz_24h_usd": 12200137}
BERICHT = {
    "datum": "2026-09-29", "erzeugt": "2026-09-29T09:00:00+00:00",
    "tore": {"_mindest_score": "LONG: wie wachen.json", "mindest_score": 60,
             "hoechst_rsi": 55, "_hoechst_rsi": "nicht ueberhitzt"},
    "maerkte_geprueft": 65,
    "treffer": [TREFFER, dict(TREFFER, inst="FIL-USDT", score=61.0,
                              umsatz_24h_usd=11586398)],
    "werte": [],
}


class StubLeitstand:
    def __init__(self, root, zustand):
        self.root, self.zustand, self.meldungen = root, zustand, []
    def melde(self, text):
        self.meldungen.append(text)


class Rein(unittest.TestCase):
    def test_lade_bericht(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "neuester.json"
            self.assertEqual(lm.lade_bericht(p), (None, "fehlt"))
            p.write_text(json.dumps(BERICHT), encoding="utf-8")
            self.assertEqual(lm.lade_bericht(p), (BERICHT, ""))
            p.write_text("{kaputt", encoding="utf-8")
            self.assertEqual(lm.lade_bericht(p), (None, "nicht lesbar"))
            p.write_bytes(b"\xff\xfe\x00")
            self.assertEqual(lm.lade_bericht(p), (None, "nicht lesbar"))
            p.write_text(json.dumps(dict(BERICHT, treffer="viele")), encoding="utf-8")
            self.assertEqual(lm.lade_bericht(p), (None, "nicht lesbar"))
            p.write_text("[]", encoding="utf-8")
            self.assertEqual(lm.lade_bericht(p), (None, "nicht lesbar"))

    def test_alter_und_warnung(self):
        self.assertEqual(lm.alter_h(BERICHT, ERZEUGT + timedelta(hours=3)), 3.0)
        self.assertEqual(lm.warnung(BERICHT, ERZEUGT + timedelta(hours=25, minutes=59)),
                         "")
        self.assertEqual(lm.warnung(BERICHT, ERZEUGT + timedelta(hours=26)),
                         "Bericht ist 26 h alt — der Dauerlauf hat keinen "
                         "neueren geschrieben")
        kaputt = dict(BERICHT, erzeugt="gestern")
        self.assertIsNone(lm.alter_h(kaputt, ERZEUGT))
        self.assertEqual(lm.warnung(kaputt, ERZEUGT),
                         "Erzeugungszeit nicht lesbar")
        ohne_zone = dict(BERICHT, erzeugt="2026-09-29T09:00:00")
        self.assertIsNone(lm.alter_h(ohne_zone, ERZEUGT))

    def test_kopfzeile(self):
        self.assertEqual(lm.kopfzeile(BERICHT, ERZEUGT + timedelta(hours=3)),
                         "Bericht vom 2026-09-29 · erzeugt vor 3.0 h · "
                         "65 Märkte geprüft · 2 Treffer")

    def test_treffer_zeilen(self):
        zeilen = lm.treffer_zeilen(BERICHT)
        self.assertEqual(len(zeilen), 2)
        self.assertEqual(len(zeilen[0]), len(lm.TREFFER_FELDER))
        self.assertEqual(zeilen[0][:3], ("ZEC-USDC", "long", 1419.51))
        ohne = lm.treffer_zeilen(dict(BERICHT, treffer=[{"inst": "X"}, "kaputt"]))
        self.assertEqual(ohne, [("X",) + ("—",) * (len(lm.TREFFER_FELDER) - 1)])

    def test_tore_zeilen(self):
        self.assertEqual(lm.tore_zeilen(BERICHT), [
            ("hoechst_rsi", 55, "nicht ueberhitzt"),
            ("mindest_score", 60, "LONG: wie wachen.json")])
        self.assertEqual(lm.tore_zeilen(dict(BERICHT, tore="kaputt")), [])


class Reiter(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ordner = Path(self.tmp.name) / "prognose_berichte"
        self.ordner.mkdir()
        self.ls = StubLeitstand(self.root, lb.Zustand(Path(self.tmp.name) / "z.json"))
        self.jetzt = ERZEUGT + timedelta(hours=3)

    def _bericht(self, name, daten):
        text = daten if isinstance(daten, str) else json.dumps(daten)
        (self.ordner / name).write_text(text, encoding="utf-8")

    def _reiter(self):
        r = lm.MarktReiter(self.root, self.ls, ordner=self.ordner,
                           uhr=lambda: self.jetzt)
        self.root.update_idletasks()
        return r

    def test_bericht_wird_angezeigt(self):
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.assertIn("65 Märkte geprüft", r.w_kopf.cget("text"))
        self.assertEqual(r.w_warnung.cget("text"), "")
        self.assertEqual(len(r.treffer.sichtbare()), 2)
        self.assertEqual(len(r.tore.sichtbare()), 2)
        self.assertEqual(r.titel_zusatz(), "")
        self.assertEqual(r.status(), "")

    def test_fehlender_bericht_gibt_hinweis(self):
        r = self._reiter()
        self.assertEqual(r.w_kopf.cget("text"),
                         "Kein Marktbericht: neuester.json fehlt — ihn schreibt "
                         "der Dauerlauf (prognose.py)")
        self.assertEqual(r.treffer.sichtbare(), [])

    def test_unlesbarer_bericht_gibt_hinweis(self):
        self._bericht("neuester.json", "{kaputt")
        r = self._reiter()
        self.assertEqual(r.w_kopf.cget("text"), "Marktbericht nicht lesbar: neuester.json")
        self.assertEqual(r.treffer.sichtbare(), [])
        self.assertEqual(r.tore.sichtbare(), [])

    def test_alterswarnung_ab_26_h(self):
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.jetzt = ERZEUGT + timedelta(hours=26)
        r.refresh()
        self.assertEqual(r.w_warnung.cget("text"),
                         "Bericht ist 26 h alt — der Dauerlauf hat keinen "
                         "neueren geschrieben")
        self.assertEqual(r.status(), "Marktbericht 26 h alt")

    def test_umschalter_streng_weit(self):
        self._bericht("neuester.json", dict(BERICHT, treffer=[]))
        self._bericht("neuester.weit.json", BERICHT)
        r = self._reiter()
        self.assertNotIn("disabled", r.r_weit.state())
        self.assertEqual(r.treffer.sichtbare(), [])
        r.fassung.set("weit")
        r.umschalten()
        self.assertEqual(len(r.treffer.sichtbare()), 2)
        self.assertEqual(self.ls.zustand.get("werte")["markt_fassung"], "weit")

    def test_ohne_weiten_bericht_ist_weit_gesperrt(self):
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.assertIn("disabled", r.r_weit.state())
        self.assertEqual(r.tip_weit.text, "kein neuester.weit.json")

    def test_gemerkte_fassung_ohne_datei_faellt_auf_streng(self):
        self.ls.zustand.merke_in("werte", "markt_fassung", "weit")
        self._bericht("neuester.json", BERICHT)
        r = self._reiter()
        self.assertEqual(r.fassung.get(), "streng")
        self.assertEqual(len(r.treffer.sichtbare()), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Tests laufen lassen — sie müssen scheitern**

Run: `$PY -m unittest tests.test_leitstand_markt tests.test_leitstand_markt_rein_lesend -v`
Erwartet: `ModuleNotFoundError: No module named 'leitstand_markt'`.

- [ ] **Step 3: `leitstand_markt.py` schreiben**

```python
"""Markt-Reiter des Leitstands: zeigt den letzten Prognose-Bericht.

Liest prognose_berichte/neuester.json (streng) und, wenn vorhanden,
neuester.weit.json (weit). Schreibt nichts, startet nichts, holt keine
Kurse - den Bericht schreibt der Dauerlauf (prognose.py), die Kurse zeigt
der Ueberwachen-Reiter. prognose.py wird bewusst NICHT importiert: es zieht
okx nach, einen Boersen-Client (tests/test_leitstand_markt_rein_lesend.py).
"""

import json
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk

from leitstand_bedienung import Tabelle, Tooltip, setze_knopf

HIER = Path(__file__).resolve().parent
BERICHTE = HIER / "prognose_berichte"          # wie in prognose.py
DATEIEN = {"streng": "neuester.json", "weit": "neuester.weit.json"}
ALTER_WARNUNG_H = 26
TREFFER_FELDER = ("inst", "richtung", "preis", "score", "cr", "stop", "ziel",
                  "risiko_prozent", "umsatz_24h_usd")
TORE_SPALTEN = ("Tor", "Wert", "Erklärung")
LEER = "—"


# --- rein ------------------------------------------------------------------

def lade_bericht(pfad):
    """(bericht, "") oder (None, "fehlt" | "nicht lesbar")."""
    pfad = Path(pfad)
    if not pfad.exists():
        return None, "fehlt"
    try:
        d = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "nicht lesbar"
    if not isinstance(d, dict) or not isinstance(d.get("treffer", []), list):
        return None, "nicht lesbar"
    return d, ""


def alter_h(bericht, jetzt):
    try:
        erzeugt = datetime.fromisoformat(str(bericht.get("erzeugt")))
    except ValueError:
        return None
    if erzeugt.tzinfo is None:
        return None
    return (jetzt - erzeugt).total_seconds() / 3600   # ungerundet: 25:59 h warnt nicht


def warnung(bericht, jetzt):
    alter = alter_h(bericht, jetzt)
    if alter is None:
        return "Erzeugungszeit nicht lesbar"
    if alter >= ALTER_WARNUNG_H:
        return ("Bericht ist %d h alt — der Dauerlauf hat keinen neueren geschrieben"
                % alter)
    return ""


def kopfzeile(bericht, jetzt):
    alter = alter_h(bericht, jetzt)
    return "Bericht vom %s · erzeugt vor %s · %s Märkte geprüft · %d Treffer" % (
        bericht.get("datum", LEER),
        LEER if alter is None else "%.1f h" % alter,
        bericht.get("maerkte_geprueft", LEER),
        len([t for t in bericht.get("treffer", []) if isinstance(t, dict)]))


def treffer_zeilen(bericht):
    return [tuple(t.get(f, LEER) for f in TREFFER_FELDER)
            for t in bericht.get("treffer", []) if isinstance(t, dict)]


def tore_zeilen(bericht):
    tore = bericht.get("tore")
    if not isinstance(tore, dict):
        return []
    return [(k, v, str(tore.get("_" + k, ""))) for k, v in sorted(tore.items())
            if not k.startswith("_")]


# --- der Reiter ------------------------------------------------------------

class MarktReiter(ttk.Frame):
    def __init__(self, eltern, leitstand, ordner=None, uhr=None):
        super().__init__(eltern, padding=8)
        self.ls, self.zustand = leitstand, leitstand.zustand
        self.ordner = Path(ordner) if ordner else BERICHTE
        self.uhr = uhr or (lambda: datetime.now(timezone.utc))
        self._status = ""

        gemerkt = (self.zustand.get("werte") or {}).get("markt_fassung")
        self.fassung = tk.StringVar(value=gemerkt if gemerkt in DATEIEN else "streng")
        oben = ttk.Frame(self)
        oben.pack(fill="x")
        ttk.Label(oben, text="Fassung").pack(side="left")
        ttk.Radiobutton(oben, text="streng", value="streng", variable=self.fassung,
                        command=self.umschalten).pack(side="left", padx=4)
        self.r_weit = ttk.Radiobutton(oben, text="weit", value="weit",
                                      variable=self.fassung, command=self.umschalten)
        self.r_weit.pack(side="left", padx=4)
        self.tip_weit = Tooltip(self.r_weit)

        self.w_kopf = ttk.Label(self, text="")
        self.w_kopf.pack(anchor="w", pady=(6, 0))
        self.w_warnung = tk.Label(self, text="", anchor="w")
        self.w_warnung.pack(fill="x")
        self._bg = self.w_warnung.cget("background")

        teiler = ttk.PanedWindow(self, orient="vertical")
        teiler.pack(fill="both", expand=True, pady=(4, 0))
        self.treffer = Tabelle(teiler, TREFFER_FELDER, self.zustand, "markt_treffer")
        teiler.add(self.treffer, weight=3)
        self.tore = Tabelle(teiler, TORE_SPALTEN, self.zustand, "markt_tore", hoehe=6)
        teiler.add(self.tore, weight=1)
        self.refresh()

    def umschalten(self):
        self.zustand.merke_in("werte", "markt_fassung", self.fassung.get())
        self.refresh()

    def refresh(self):
        weit_da = (self.ordner / DATEIEN["weit"]).exists()
        setze_knopf(self.r_weit, self.tip_weit, weit_da,
                    "kein %s" % DATEIEN["weit"])
        if not weit_da and self.fassung.get() == "weit":
            self.fassung.set("streng")
        name = DATEIEN[self.fassung.get()]
        bericht, fehler = lade_bericht(self.ordner / name)
        jetzt = self.uhr()
        if bericht is None:
            self.w_kopf.config(text=(
                "Kein Marktbericht: %s fehlt — ihn schreibt der Dauerlauf (prognose.py)"
                % name) if fehler == "fehlt" else "Marktbericht nicht lesbar: %s" % name)
            self._warne("")
            self.treffer.setze([])
            self.tore.setze([])
            return
        self.w_kopf.config(text=kopfzeile(bericht, jetzt))
        self._warne(warnung(bericht, jetzt))
        alter = alter_h(bericht, jetzt)
        self._status = ("Marktbericht %d h alt" % alter
                        if alter is not None and alter >= ALTER_WARNUNG_H else "")
        self.treffer.setze(treffer_zeilen(bericht))
        self.tore.setze(tore_zeilen(bericht))

    def _warne(self, text):
        self.w_warnung.config(text=text, background="#fff3b0" if text else self._bg)
        if not text:
            self._status = ""

    def titel_zusatz(self):
        return ""

    def status(self):
        return self._status
```

- [ ] **Step 4: Tests laufen lassen**

Run: `$PY -m unittest tests.test_leitstand_markt tests.test_leitstand_markt_rein_lesend -v`
Erwartet: alle grün (5 + 7 + 2).

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage bleibt unverändert.

- [ ] **Step 5: Commit**

```bash
git status --short
git add Agenten/Handel/leitstand_markt.py Agenten/Handel/tests/test_leitstand_markt.py Agenten/Handel/tests/test_leitstand_markt_rein_lesend.py
git commit -m "Leitstand: Markt-Reiter liest den Prognose-Bericht, streng und weit, mit Alterswarnung (Aufgabe 12)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: `leitstand.py` — Wurzel, Reiter, Takt, Kürzel, Statusleiste, Zustand

**Files:**
- Create: `Agenten/Handel/leitstand.py`
- Test: `Agenten/Handel/tests/test_leitstand.py`

**Interfaces:**
- Consumes:
  - aus Aufgabe 3: `hz.Handelszentrale(eltern)` (nimmt einen Frame), `.w_schrift`, `._schrift_gewaehlt()`, `hz.SCHRIFT_GROESSE`, `hz.dauerlauf_dateien()`, `hz.dauerlauf_stand(pfad, jetzt)`, `hz.prozess_lebt(pid)`, `hz.nach_vorn(root)`;
  - aus Aufgabe 4: `lb.Zustand` (`get`, `merke`, `speichern(sofort)`, `nachholen()`, `.daten`), `lb.lage_gueltig(geometrie, schirm)`, `lb.virtueller_schirm(root)`;
  - aus Aufgabe 5: `FreigabenReiter(eltern, leitstand)`;
  - aus Aufgabe 7: `BacktestReiter(eltern, leitstand)` mit `.steuerung` (`laeuft()`, `abbrechen()`);
  - aus Aufgabe 9: `tests/lesepruefung.py` (`schreibstellen`, `importiert`);
  - aus Aufgabe 12: `MarktReiter(eltern, leitstand)`, `lm.BERICHTE`.
- Produces:
  - `leitstand.KUERZEL: dict[str, tuple[str, int|None]]`, `REITER`, `TAKT_MS = 5000`, `TAKT_IMMER = {"Freigaben"}`, `TAKT_SICHTBAR = {"Markt"}`;
  - `herzschlag(jetzt=None) -> str`;
  - `class UeberwachenReiter(ttk.Frame)(eltern, leitstand)` mit `.hz`;
  - `class Leitstand(root, zustand=None, reiter=None, uhr=None, herz=herzschlag)` mit `.root`, `.zustand`, `.buch`, `.reiter`, `.titel`, `.schrift`, `.w_status`, `melde(text)`, `kuerzel(seq)`, `sichtbarer_index()`, `setze_schrift(n, merken=True)`, `schliessen(frage=messagebox.askyesno) -> bool`;
  - `main()`.

Die Reiter bekommen den Leitstand als `leitstand`, genau wie der `StubLeitstand` der früheren Aufgaben: `.root`, `.zustand`, `.melde(text)`.

Welcher Reiter im Takt aufgefrischt wird, hängt am **Titel**, nicht an der Klasse. So prüfen die Tests die Regel mit Stub-Reitern:
- „Freigaben“ immer (Reitertitel „Freigaben (n)“ und Blinken auch im Hintergrund);
- „Markt“ nur, wenn er sichtbar ist;
- „Überwachen“ taktet sich selbst (Handelszentrale, 15 s), „Backtests“ ebenfalls (`TAKT_MS = 200` in Aufgabe 7).

Die Kürzel sind in `KUERZEL` abschließend aufgezählt. Die Bindung ruft `kuerzel(seq)`; die Tests rufen diese Methode direkt, weil ein zurückgezogenes Fenster keine Tastenereignisse bekommt. Ob die Bindungen bestehen, prüft ein eigener Test.

- [ ] **Step 1: Tests schreiben**

`tests/test_leitstand.py`:

```python
"""Leitstand-Rahmen: Reiter, Takt, Kuerzel, Statusleiste, Zustand, Herzschlag.

Die meisten Tests haengen Stub-Reiter ein. Ein Rauchtest baut die echten vier
Reiter mit Temp-Dateien (Freigaben, Ablage, Marktbericht) und ohne Netz:
Handelszentrale.refresh startet Kurs-Threads und wird ersetzt. Ohne
Bildschirm werden die Tk-Tests uebersprungen.

Direkt ausfuehrbar:  python tests/test_leitstand.py
"""

import datetime as dt
import json
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import freigabefenster as ff                                   # noqa: E402
import handelszentrale as hz                                   # noqa: E402
import leitstand as lst                                        # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_freigaben as lf                               # noqa: E402
import leitstand_laeufe as ll                                  # noqa: E402
import leitstand_markt as lm                                   # noqa: E402
import lesepruefung                                            # noqa: E402

TITEL = ("Überwachen", "Freigaben", "Backtests", "Markt")
VERBOTENE_TASTEN = ("Return", "KP_Enter", "Control-", "Alt-")


class StubReiter(ttk.Frame):
    def __init__(self, eltern, leitstand):
        super().__init__(eltern)
        self.ls, self.aufrufe, self.zusatz, self.text = leitstand, 0, "", ""
    def refresh(self):
        self.aufrufe += 1
    def titel_zusatz(self):
        return self.zusatz
    def status(self):
        return self.text


class FakeLauf:
    def __init__(self):
        self.abgebrochen = 0
    def laeuft(self):
        return True
    def abbrechen(self):
        self.abgebrochen += 1


STUBS = [(t, StubReiter) for t in TITEL]


class Basis(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self._zu)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = Path(self.tmp.name) / "z.json"
        p = patch.object(hz, "SCHRIFT_GROESSE", 11)
        p.start()
        self.addCleanup(p.stop)

    def _zu(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass                      # schliessen() hat es schon getan

    def leitstand(self, daten=None, reiter=STUBS):
        if daten is not None:
            self.pfad.write_text(json.dumps(daten), encoding="utf-8")
        self.z = lb.Zustand(self.pfad)
        ls = lst.Leitstand(self.root, zustand=self.z, reiter=reiter,
                           uhr=lambda: dt.datetime(2026, 9, 29, 12, 0, 5),
                           herz=lambda: "Dauerlauf läuft nicht")
        self.root.update()
        return ls


class Rahmen(Basis):
    def test_titel_bekommen_den_zusatz(self):
        ls = self.leitstand()
        ls.reiter[1].zusatz = " (2)"
        ls._takt()
        self.assertEqual(ls.buch.tab(1, "text"), "Freigaben (2)")
        self.assertEqual(ls.buch.tab(0, "text"), TITEL[0])

    def test_gemerkter_reiter_gilt_beim_start(self):
        ls = self.leitstand({"reiter": 2})
        self.assertEqual(ls.sichtbarer_index(), 2)

    def test_unsinniger_reiter_faellt_auf_den_ersten(self):
        ls = self.leitstand({"reiter": 9})
        self.assertEqual(ls.sichtbarer_index(), 0)

    def test_kuerzel_wechselt_reiter_merkt_ihn_und_frischt_auf(self):
        ls = self.leitstand()
        vorher = ls.reiter[2].aufrufe
        ls.kuerzel("<Control-Key-3>")
        self.root.update()
        self.assertEqual(ls.sichtbarer_index(), 2)
        self.assertEqual(self.z.get("reiter"), 2)
        self.assertEqual(ls.reiter[2].aufrufe, vorher + 1)

    def test_f5_frischt_nur_den_sichtbaren_auf(self):
        ls = self.leitstand()
        vorher = [r.aufrufe for r in ls.reiter]
        ls.kuerzel("<F5>")
        nachher = [r.aufrufe for r in ls.reiter]
        self.assertEqual(nachher, [vorher[0] + 1] + vorher[1:])

    def test_schrift_bleibt_in_den_grenzen_und_wird_gemerkt(self):
        ls = self.leitstand()
        ls.setze_schrift(16)
        ls.kuerzel("<Control-plus>")
        self.assertEqual(ls.schrift, 16)
        ls.setze_schrift(8)
        ls.kuerzel("<Control-KP_Subtract>")
        self.assertEqual(ls.schrift, 8)
        self.assertEqual(self.z.get("schrift"), 8)
        ls.kuerzel("<Control-KP_Add>")
        self.assertEqual(ls.schrift, 9)

    def test_gemerkte_schrift_gilt_nur_in_den_grenzen(self):
        self.assertEqual(self.leitstand({"schrift": 14}).schrift, 14)

    def test_unsinnige_schrift_bleibt_bei_der_vorgabe(self):
        self.assertEqual(self.leitstand({"schrift": 40}).schrift, 11)

    def test_takt_freigaben_immer_markt_nur_sichtbar(self):
        ls = self.leitstand()
        vorher = [r.aufrufe for r in ls.reiter]
        ls._takt()
        nachher = [r.aufrufe for r in ls.reiter]
        self.assertEqual(nachher, [vorher[0], vorher[1] + 1, vorher[2], vorher[3]])
        ls.kuerzel("<Control-Key-4>")
        self.root.update()
        vorher = [r.aufrufe for r in ls.reiter]
        ls._takt()
        nachher = [r.aufrufe for r in ls.reiter]
        self.assertEqual(nachher, [vorher[0], vorher[1] + 1, vorher[2], vorher[3] + 1])

    def test_statusleiste_zeigt_herz_zeit_status_und_meldung(self):
        ls = self.leitstand()
        ls.reiter[2].text = "Backtest: replay läuft seit 0:07"
        ls.melde("xperp scharf für 6:00 h")
        ls._takt()
        text = ls.w_status.cget("text")
        for teil in ("Dauerlauf läuft nicht", "aktualisiert 12:00:05",
                     "Backtest: replay läuft seit 0:07",
                     "xperp scharf für 6:00 h"):
            self.assertIn(teil, text)

    def test_fehler_eines_reiters_haelt_den_takt_nicht_an(self):
        ls = self.leitstand()
        def kaputt():
            raise ValueError("nicht lesbar")
        ls.reiter[1].refresh = kaputt
        ls._takt()
        self.assertIn("Freigaben: Fehler beim Auffrischen", ls.w_status.cget("text"))
        self.assertIn("aktualisiert 12:00:05", ls.w_status.cget("text"))

    def test_kuerzel_sind_gebunden_und_nur_diese(self):
        self.leitstand()
        for seq in lst.KUERZEL:
            self.assertTrue(self.root.bind(seq), seq)
        self.assertEqual(len(self.root.bind()), len(lst.KUERZEL))
        self.assertEqual({was for was, _arg in lst.KUERZEL.values()},
                         {"reiter", "auffrischen", "schrift"})

    def test_gueltige_lage_wird_uebernommen(self):
        x, y, _b, _h = lb.virtueller_schirm(self.root)
        geo = "900x700+%d+%d" % (x + 10, y + 10)
        with patch.object(self.root, "geometry") as g:
            self.leitstand({"geometrie": geo})
        g.assert_any_call(geo)

    def test_lage_ausserhalb_aller_schirme_wird_verworfen(self):
        geo = "900x700+-30000+-30000"
        with patch.object(self.root, "geometry") as g:
            self.leitstand({"geometrie": geo})
        self.assertNotIn(geo, [c.args[0] for c in g.call_args_list if c.args])
        g.assert_any_call(lst.GEOMETRIE_VORGABE)

    def test_schliessen_speichert_sofort_und_zerstoert(self):
        ls = self.leitstand()
        ls.kuerzel("<Control-Key-2>")
        self.root.update()
        self.assertTrue(ls.schliessen(frage=lambda *a, **k: self.fail("gefragt")))
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertEqual(daten["reiter"], 1)
        self.assertTrue(daten["geometrie"])
        with self.assertRaises(tk.TclError):
            self.root.winfo_exists()

    def test_schliessen_bei_laufendem_backtest_fragt_erst(self):
        ls = self.leitstand()
        ls.reiter[2].steuerung = lauf = FakeLauf()
        self.assertFalse(ls.schliessen(frage=lambda *a, **k: False))
        self.assertEqual(lauf.abgebrochen, 0)
        self.assertTrue(self.root.winfo_exists())
        self.assertTrue(ls.schliessen(frage=lambda *a, **k: True))
        self.assertEqual(lauf.abgebrochen, 1)


class Echt(Basis):
    """Die vier echten Reiter, alles auf Temp-Dateien, kein Netz."""

    def setUp(self):
        super().setUp()
        t = Path(self.tmp.name)
        self.hz_refresh = self._ersetze(hz.Handelszentrale, "refresh")
        self._ersetze(hz.Handelszentrale, "_buero_im_bild")
        for ziel, name, wert in ((ff, "DATEI", t / "freigabe_fenster.json"),
                                 (ll, "ABLAGE", t / "ablage"),
                                 (lm, "BERICHTE", t / "berichte"),
                                 (lf, "blinken", lambda _root: False)):
            p = patch.object(ziel, name, wert)
            p.start()
            self.addCleanup(p.stop)

    def _ersetze(self, klasse, name):
        p = patch.object(klasse, name, autospec=True)
        m = p.start()
        self.addCleanup(p.stop)
        return m

    def test_vier_reiter_mit_ihren_titeln(self):
        ls = self.leitstand(reiter=None)
        self.assertEqual([ls.buch.tab(i, "text") for i in range(4)], list(TITEL))
        ls._takt()
        self.assertNotIn("Fehler", ls.w_status.cget("text"))

    def test_f5_im_ueberwachen_reiter_ruft_die_zentrale(self):
        ls = self.leitstand(reiter=None)
        vorher = self.hz_refresh.call_count
        ls.kuerzel("<F5>")
        self.assertEqual(self.hz_refresh.call_count, vorher + 1)

    def test_schrift_wirkt_auf_die_zentrale(self):
        ls = self.leitstand(reiter=None)
        ls.setze_schrift(14)
        self.assertEqual(hz.SCHRIFT_GROESSE, 14)
        self.assertEqual(ls.reiter[0].hz.w_schrift.get(), "14")

    def test_kein_widget_bindet_eine_ausloesende_taste(self):
        ls = self.leitstand(reiter=None)
        offen = list(self.root.winfo_children())
        while offen:
            w = offen.pop()
            offen.extend(w.winfo_children())
            for seq in w.bind():
                for taste in VERBOTENE_TASTEN:
                    self.assertNotIn(taste, seq, "%s bindet %s" % (w, seq))
        self.assertEqual(len(self.root.bind()), len(lst.KUERZEL))
        self.assertEqual(ls.sichtbarer_index(), 0)


class Herzschlag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.pid, self.log = t / "dauerlauf.pid", t / "dauerlauf.log"
        p = patch.object(hz, "dauerlauf_dateien",
                         lambda: (str(self.pid), str(self.log)))
        p.start()
        self.addCleanup(p.stop)

    def herz(self, lebt, minuten):
        with patch.object(hz, "prozess_lebt", return_value=lebt) as pl, \
                patch.object(hz, "dauerlauf_stand", return_value=("x", minuten)):
            text = lst.herzschlag(dt.datetime(2026, 9, 29, 12, 0, tzinfo=dt.timezone.utc))
        return text, pl

    def test_lebt_und_frisch(self):
        self.pid.write_text("1234", encoding="ascii")
        text, pl = self.herz(True, 5.0)
        self.assertEqual(text, "Dauerlauf läuft (letzter Zyklus vor 5 min)")
        pl.assert_called_once_with(1234)

    def test_lebt_aber_zu_lange_still(self):
        self.pid.write_text("1234", encoding="ascii")
        self.assertEqual(self.herz(True, 45.0)[0], "Dauerlauf läuft nicht")

    def test_prozess_nicht_abfragbar(self):
        self.pid.write_text("1234", encoding="ascii")
        self.assertEqual(self.herz(None, 5.0)[0], "Dauerlauf läuft nicht")

    def test_ohne_pid_datei(self):
        text, pl = self.herz(None, None)
        self.assertEqual(text, "Dauerlauf läuft nicht")
        pl.assert_called_once_with(None)

    def test_unlesbare_pid_datei(self):
        self.pid.write_text("kaputt", encoding="ascii")
        text, pl = self.herz(None, 5.0)
        self.assertEqual(text, "Dauerlauf läuft nicht")
        pl.assert_called_once_with(None)


class Lesepruefung(unittest.TestCase):
    def test_der_rahmen_schreibt_selbst_nichts(self):
        self.assertEqual(lesepruefung.schreibstellen(lst.__file__), [])

    def test_der_rahmen_startet_nichts_und_handelt_nicht(self):
        for modul in ("subprocess", "okx", "ccxt", "requests", "kraken",
                      "backtest_urteile"):
            self.assertFalse(lesepruefung.importiert(lst.__file__, modul), modul)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Test laufen lassen — er muss scheitern**

Run: `$PY -m unittest tests.test_leitstand -v`
Erwartet: ERROR beim Import mit `ModuleNotFoundError: No module named 'leitstand'`.

- [ ] **Step 3: `leitstand.py` schreiben**

```python
"""Leitstand - ein Fenster fuer Ueberwachen, Freigaben, Backtests und Markt.

Handelt nie live und schreibt in keine wachen.json. Geschrieben wird nur an
drei Stellen, und keine davon liegt in diesem Rahmen:
  * freigabefenster.* aus dem Freigaben-Reiter (mit Sperre);
  * backtest_laeufe/ aus dem Backtest-Reiter;
  * backtest_urteile.py --aus-vorschau nach Bestaetigung (Bereich Urteile).
Der Rahmen selbst schreibt nur leitstand_zustand.json, ueber
leitstand_bedienung.Zustand.

Tastatur: Strg+1..4 Reiter, F5 sichtbaren Reiter auffrischen, Strg+Plus/Minus
Schrift. Notaus, Freigeben und Urteile eintragen haben bewusst KEIN Kuerzel.

Aufruf:  python leitstand.py
"""

import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk

import handelszentrale as hz
from leitstand_backtests import BacktestReiter
from leitstand_bedienung import Zustand, lage_gueltig, virtueller_schirm
from leitstand_freigaben import FreigabenReiter
from leitstand_markt import MarktReiter

TAKT_MS = 5000
SCHRIFT_MIN, SCHRIFT_MAX = 8, 16
HERZ_MAX_MIN = 30                  # wie die Handelszentrale: aelter = rot
GEOMETRIE_VORGABE = "1280x900"

# Abschliessend: was hier nicht steht, hat kein Kuerzel.
KUERZEL = {
    "<Control-Key-1>": ("reiter", 0),
    "<Control-Key-2>": ("reiter", 1),
    "<Control-Key-3>": ("reiter", 2),
    "<Control-Key-4>": ("reiter", 3),
    "<F5>": ("auffrischen", None),
    "<Control-plus>": ("schrift", 1),
    "<Control-KP_Add>": ("schrift", 1),
    "<Control-minus>": ("schrift", -1),
    "<Control-KP_Subtract>": ("schrift", -1),
}

# Welcher Reiter im Takt aufgefrischt wird, haengt am Titel. Ueberwachen und
# Backtests takten sich selbst (15 s bzw. 200 ms).
TAKT_IMMER = {"Freigaben"}         # Titel "Freigaben (n)" und Blinken auch im Hintergrund
TAKT_SICHTBAR = {"Markt"}


class UeberwachenReiter(ttk.Frame):
    """Die Handelszentrale als Reiter; sie holt ihre Kurse selbst alle 15 s."""

    def __init__(self, eltern, leitstand):
        super().__init__(eltern)
        self.ls = leitstand
        self.hz = hz.Handelszentrale(self)

    def refresh(self):
        self.hz.refresh()

    def titel_zusatz(self):
        return ""

    def status(self):
        return ""


REITER = [("Überwachen", UeberwachenReiter),
          ("Freigaben", FreigabenReiter),
          ("Backtests", BacktestReiter),
          ("Markt", MarktReiter)]


def herzschlag(jetzt=None):
    """Laeuft der Dauerlauf? Gelesen wie in der Handelszentrale (PID + Log)."""
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    pid_pfad, log_pfad = hz.dauerlauf_dateien()
    try:
        with open(pid_pfad, encoding="ascii") as f:
            pid = int((f.read() or "0").strip() or 0) or None
    except (OSError, ValueError):
        pid = None
    lebt = hz.prozess_lebt(pid)
    _text, alt = hz.dauerlauf_stand(log_pfad, jetzt)
    if lebt and alt is not None and alt <= HERZ_MAX_MIN:
        return "Dauerlauf läuft (letzter Zyklus vor %.0f min)" % alt
    return "Dauerlauf läuft nicht"


class Leitstand:
    def __init__(self, root, zustand=None, reiter=None, uhr=None, herz=herzschlag):
        self.root = root
        self.zustand = zustand or Zustand()
        self.uhr = uhr or dt.datetime.now
        self.herz = herz
        self._meldung = ""
        self._zuletzt = ""
        self._fehler = []

        root.title("Leitstand — Papier, handelt nie live")
        root.minsize(1000, 640)
        geo = self.zustand.get("geometrie")
        if geo and lage_gueltig(geo, virtueller_schirm(root)):
            root.geometry(geo)
        else:
            root.geometry(GEOMETRIE_VORGABE)

        # Statusleiste zuerst packen, sonst draengt das Notebook sie hinaus.
        self.w_status = ttk.Label(root, anchor="w", padding=(6, 2))
        self.w_status.pack(side="bottom", fill="x")
        self.buch = ttk.Notebook(root)
        self.buch.pack(fill="both", expand=True)

        self.reiter, self.titel = [], []
        for titel, klasse in (reiter or REITER):
            r = klasse(self.buch, self)
            self.buch.add(r, text=titel)
            self.reiter.append(r)
            self.titel.append(titel)
        i = self.zustand.get("reiter")
        if isinstance(i, int) and 0 <= i < len(self.reiter):
            self.buch.select(i)
        self.buch.bind("<<NotebookTabChanged>>", self._gewechselt, add="+")

        self.schrift = hz.SCHRIFT_GROESSE
        n = self.zustand.get("schrift")
        if isinstance(n, int) and SCHRIFT_MIN <= n <= SCHRIFT_MAX:
            self.setze_schrift(n, merken=False)

        for seq in KUERZEL:
            root.bind(seq, lambda _e, s=seq: self.kuerzel(s))
        root.protocol("WM_DELETE_WINDOW", self.schliessen)
        self._rahmen()
        root.after(TAKT_MS, self._takt)

    # --- Reiter -------------------------------------------------------------

    def sichtbarer_index(self):
        return self.buch.index(self.buch.select())

    def _gewechselt(self, _event=None):
        i = self.sichtbarer_index()
        self.zustand.merke("reiter", i)
        self._auffrischen(i)
        self._rahmen()

    def _auffrischen(self, i):
        try:
            self.reiter[i].refresh()
        except Exception as e:                               # noqa: BLE001
            self._fehler.append("%s: Fehler beim Auffrischen (%s)"
                                % (self.titel[i], e))

    def kuerzel(self, seq):
        was, arg = KUERZEL[seq]
        if was == "reiter":
            if arg < len(self.reiter):
                self.buch.select(arg)
        elif was == "auffrischen":
            self._auffrischen(self.sichtbarer_index())
            self._rahmen()
        elif was == "schrift":
            self.setze_schrift(self.schrift + arg)
        return "break"

    # --- Schrift ------------------------------------------------------------

    def _zentrale(self):
        for r in self.reiter:
            if isinstance(getattr(r, "hz", None), hz.Handelszentrale):
                return r.hz
        return None

    def setze_schrift(self, n, merken=True):
        n = max(SCHRIFT_MIN, min(SCHRIFT_MAX, int(n)))
        self.schrift = n
        z = self._zentrale()
        if z is not None:
            z.w_schrift.set(str(n))
            z._schrift_gewaehlt()
        if merken:
            self.zustand.merke("schrift", n)

    # --- Takt und Statusleiste ----------------------------------------------

    def melde(self, text):
        self._meldung = text
        self._rahmen()

    def _takt(self):
        try:
            sichtbar = self.sichtbarer_index()
            for i, titel in enumerate(self.titel):
                if titel in TAKT_IMMER or (titel in TAKT_SICHTBAR and i == sichtbar):
                    self._auffrischen(i)
            self._zuletzt = self.uhr().strftime("%H:%M:%S")
            self._rahmen()
            self.zustand.nachholen()
        finally:
            self.root.after(TAKT_MS, self._takt)

    def _rahmen(self):
        """Reitertitel und Statusleiste aus dem Stand der Reiter."""
        for i, (titel, r) in enumerate(zip(self.titel, self.reiter)):
            self.buch.tab(i, text=titel + r.titel_zusatz())
        teile = [self.herz()]
        if self._zuletzt:
            teile.append("aktualisiert %s" % self._zuletzt)
        teile += [s for s in (r.status() for r in self.reiter) if s]
        teile += self._fehler
        self._fehler = []
        if self._meldung:
            teile.append(self._meldung)
        self.w_status.config(text="   |   ".join(teile))

    # --- Schliessen ---------------------------------------------------------

    def schliessen(self, frage=messagebox.askyesno):
        laeufe = [r.steuerung for r in self.reiter
                  if getattr(r, "steuerung", None) is not None
                  and r.steuerung.laeuft()]
        if laeufe:
            if not frage("Leitstand schließen",
                         "Ein Backtest läuft noch. Abbrechen und schließen?",
                         parent=self.root):
                return False
            for s in laeufe:
                s.abbrechen()
        self.zustand.daten["geometrie"] = self.root.geometry()
        self.zustand.speichern(sofort=True)
        self.root.destroy()
        return True


def main():
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.1)
    except tk.TclError:
        pass
    Leitstand(root)
    hz.nach_vorn(root)
    root.mainloop()


if __name__ == "__main__":
    main()
```

Hinweise zur Umsetzung:
- `_fehler` sammelt Fehler der Reiter bis zur nächsten Statuszeile. So bleibt die Meldung genau einen Takt stehen und der Takt läuft weiter.
- `schrift` im Zustand ist in den Vorgaben `0` und damit außerhalb von 8..16: Ohne gemerkte Wahl gilt `hz.SCHRIFT_GROESSE`.
- Die beiden Lage-Tests ersetzen `root.geometry` durch einen Mock. Ein zurückgezogenes Fenster meldet seine Geometrie erst nach dem Anzeigen verlässlich; gezählt wird deshalb, womit der Leitstand `geometry` aufruft.
- `<<NotebookTabChanged>>` kommt über die Ereigniswarteschlange. Die Tests rufen deshalb nach jedem Reiterwechsel `root.update()`.

- [ ] **Step 4: Tests laufen lassen**

Run: `$PY -m unittest tests.test_leitstand -v`
Erwartet: alle grün (Rahmen 16, Echt 4, Herzschlag 5, Lesepruefung 2).

Run: `$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3`. Die Ausgangslage bleibt unverändert.

Dann einmal von Hand aus dem Worktree: `$PY leitstand.py`.
- Das Fenster öffnet sich mit vier Reitern.
- Strg+1…4 wechseln, F5 frischt auf, Strg+Plus/Minus ändern die Schrift.
- Beim Schließen entsteht `leitstand_zustand.json`. Beim nächsten Start steht der zuletzt benutzte Reiter vorn.
- Im Worktree fehlen Betriebsdaten. Hinweise wie „Kein Marktbericht“ sind richtig, ein Absturz nicht.
- Die Datei `leitstand_zustand.json` im Worktree danach löschen: sie ist nicht versioniert und gehört nicht in den Merge.

- [ ] **Step 5: Commit**

```bash
git status --short
git add Agenten/Handel/leitstand.py Agenten/Handel/tests/test_leitstand.py
git commit -m "Leitstand: Fenster mit vier Reitern, Takt, Kuerzel, Statusleiste und gemerktem Zustand (Aufgabe 13)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Abschluss — Nachweise, Zusammenführen, Aufräumen

**Files:**
- keine neuen; nur Prüfungen, Merge und Aufräumen

**Interfaces:**
- Consumes: alle Aufgaben 1–13 auf dem Zweig `arbeit/leitstand`
- Produces: `master` enthält den Leitstand; Zweig und Worktree sind entfernt

- [ ] **Step 1: Ganze Suite im Worktree**

Aus `../Handel-leitstand/Agenten/Handel`:

```bash
$PY -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -5
```

Erwartet: dieselben roten Tests wie in der Ausgangslage aus Aufgabe 1, kein neuer. Die neuen Testdateien laufen mit:
- `test_freigabefenster_grenzwerte`, `test_freigabefenster_sperre`;
- `test_handelszentrale_als_rahmen`;
- `test_leitstand_bedienung`, `test_leitstand_freigaben`;
- `test_leitstand_backtests_lauf`, `test_leitstand_backtests`, `test_leitstand_backtests_liste`;
- `test_leitstand_optimieren`, `test_backtest_urteile` (erweitert), `test_leitstand_urteile`;
- `test_leitstand_markt`, `test_leitstand_markt_rein_lesend`, `test_leitstand`.

Außerdem unverändert grün: `test_handelszentrale_rein_lesend`.

- [ ] **Step 2: Keine Reste im Worktree**

```bash
git status --short --ignored
```

Erwartet: kein `.bak`, kein `.tmp`, kein `.lock`. Übrig bleiben dürfen nur ignorierte Laufreste wie `__pycache__/`, `backtest_laeufe/` und `leitstand_zustand.json`. Diese sind nicht versioniert und gehen beim Entfernen des Worktrees mit.

Findet sich eine versionierte Datei, die in keiner Aufgabe steht: nicht committen, sondern Max fragen.

- [ ] **Step 3: Prüfen, ob `master` sich inzwischen bewegt hat**

Aus `BrainFiles/`:

```bash
git status --short
git log --oneline -1 master
git merge-base --is-ancestor master arbeit/leitstand && echo "master ist Vorfahre"
```

- Steht „master ist Vorfahre“ da: weiter mit Step 4.
- Sonst: im Worktree `git merge master`. Konflikte gezielt lösen, die Suite erneut laufen lassen (Step 1), dann weiter.

Vor dem Merge die 10-Minuten-Regel beachten: Hat eine andere Sitzung eine der Dateien aus der Dateitabelle vor weniger als 10 Minuten im Hauptbaum geändert (`git status` zeigt sie als geändert), dann warten und Max fragen.

Die fremden Änderungen im Hauptbaum werden nicht angefasst. Dazu gehören `ai4trade/tests/test_heartbeat.py`, die Hermes-Skills, `dauerlauf.py`, `requirements.txt`, `Routinen/handel-dauerlauf.ps1`, `sperre.py` und `tests/test_sperre.py`.

- [ ] **Step 4: Auf `master` zusammenführen**

Aus `BrainFiles/`, auf `master`:

```bash
git merge --ff-only arbeit/leitstand
git log --oneline -15
```

Erwartet: die Commits der Aufgaben 1–13 liegen auf `master`.

Scheitert `--ff-only`, weil `master` sich in der Zwischenzeit bewegt hat: zurück zu Step 3.

- [ ] **Step 5: Nachweise im Hauptbaum**

Aus `Agenten/Handel`:

```bash
PY=scanner/.venv/Scripts/python.exe
$PY -m unittest tests.test_handelszentrale_rein_lesend tests.test_leitstand_markt_rein_lesend tests.test_leitstand -v 2>&1 | tail -3
$PY spiegelstand.py
$PY freigabefenster.py --stand
$PY handelszentrale.py --pruefen
```

Erwartet:
- Die drei Testdateien sind grün.
- `spiegelstand.py` zeigt denselben Rückgabecode wie vor dem Merge. `freigabe_fenster.json` taucht darin nicht auf, `.lock` und `.tmp` auch nicht (Befund, Punkt 3).
- `freigabefenster.py --stand` zeigt denselben Stand wie vorher; es schreibt nichts.
- `handelszentrale.py --pruefen` gibt die gewohnten Zeilen aus.

Dann einmal `$PY leitstand.py` starten und ansehen:
- vier Reiter;
- der Markt-Reiter zeigt den echten Bericht;
- der Freigaben-Reiter zeigt den echten Stand.

**Nichts freigeben und nichts eintragen:** Dies ist ein Sichttest, keine Bedienung.

- [ ] **Step 6: Zweig und Worktree entfernen**

Aus `BrainFiles/`:

```bash
git worktree remove ../Handel-leitstand
git branch -d arbeit/leitstand
git worktree list
git branch --list
```

Erwartet:
- Nur der Hauptbaum ist noch da.
- Es gibt nur die Zweige `master` und gegebenenfalls `zwischenstand`, den nie anfassen.

`git worktree remove` verweigert bei ungesicherten Änderungen. Dann nicht `--force` setzen, sondern nachsehen, was dort liegt (Step 2).

- [ ] **Step 6b: Push**

```bash
git push origin master
```

Nur nach Rückfrage bei Max, wenn er es in dieser Sitzung nicht schon freigegeben hat.

---
