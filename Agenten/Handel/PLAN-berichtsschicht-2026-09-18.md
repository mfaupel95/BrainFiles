# Berichtsschicht — Umsetzungsplan

> **Für agentische Arbeiter:** ERFORDERLICHE UNTER-SKILL: `superpowers:subagent-driven-development`
> (empfohlen) oder `superpowers:executing-plans`, Aufgabe für Aufgabe. Schritte tragen
> Kästchen (`- [ ]`).

**Ziel:** Die Erhebung der 24 Spuren steht einmal in `lage.py`; Tages- und
Wochenbericht stellen nur noch dar, vergleichen mit gestern und ordnen nach
Vorrang.

**Aufbau:** `lage.py` sammelt je Spur eine Struktur in fester Form (Positionen,
Sperren, Wachenzahlen, Kennzahlen im Fenster, Buchlage). `schnappschuss.py`
schreibt täglich das, was die Journale nicht rekonstruieren können, nach
`stand/JJJJ-MM-TT.json` und legt den Vortag daneben. `tagesbericht.py` verliert
seine Erhebung und bekommt die Vorrangregel. `wochenbericht.py` ist eine zweite
Darstellung derselben Erhebung. `guthaben_abgleich.py` kommt zuletzt, als
einziger Teil mit Außenabhängigkeit.

**Technik:** Python 3, `unittest`, keine neuen Abhängigkeiten.

**Spec:** `ENTWURF-auswertung-berichte-2026-09-17.md`

**Vorgängerplan:** `PLAN-auswertung-datengrundlage-2026-09-17.md` (abgeschlossen,
`master` bei `846ca84`) — er hat `zeitfenster.py`, `gesamtbilanz.py`, die
Fensterparameter in `auswertung_alle.py`/`buchauswertung.py` und `kennzahlen_kurz()`
in den fünf Eigenauswertungen geliefert. Dieser Plan setzt darauf auf.

## Globale Vorgaben

- **Arbeitsverzeichnis:** `C:\Users\faupe\Documents\BrainFiles\Agenten\Handel`
- **Zahlen gehören in `wachen.json`, nicht in den Code** (`AGENTS.md`). Neue
  Schwellen werden nicht als Konstante angelegt. Ausnahme mit Begründung im
  Code: Aufbewahrungsdauer und Fensterlänge des Berichts sind Darstellungs-,
  keine Handelsgrößen — sie stehen als benannte Modulkonstante mit Kommentar.
- **Niemals lesen oder durchsuchen:** `OpenAlice/`, `.venv/`, `scanner/.venv/`,
  `nautilus/.venv/`, `__pycache__/`, `daten/`, `kerzen_*.json`, `README.md`.
- **Deutsche Docstrings und Kommentare, in `.py`-Dateien ohne Umlaute**
  (`ae`/`oe`/`ue`/`ss`). Bestehender Stil im Baum.
- **Testrahmen ist `unittest`**, Tests unter `tests/`, Dateiname `test_*.py`,
  einzeln ausführbar per `python tests/test_<name>.py`, gesamt per
  `python -m unittest discover -s tests -p "test_*.py"`.
- **Kein Test schreibt in ein echtes Ziel.** Temp-Ordner, `journal_zweitziel`
  wird nirgends berührt. Der Schnappschuss ist kein Buch — Bedingung 4 bleibt
  unangetastet, `spiegelstand.py` wird nicht verändert.
- **Kostenformeln sind tabu.** Keine Zahl in `buchauswertung.py`,
  `auswertung_alle.py` oder einer `<spur>/auswertung.py`, die Gebühr, Slippage
  oder Funding beschreibt, wird angefasst.
- **Der Bericht darf nicht am Netz hängen.** Kurs- und Guthabenabrufe scheitern
  still zu `None`; der Rahmen steht ohne Netz. Ein Ausfall wird zur Zeile, nie
  zum Abbruch.
- **Rückwärtskompatibilität:** `tagesbericht.baue()` behält Signatur und
  Aufrufort in `dauerlauf.py`. Jeder neue Parameter hat einen Vorgabewert.
- **Kein `git add -A` und kein `git add .`** — der Arbeitsbaum trägt fremde
  unverbuchte Änderungen (`Agenten/Hermes/`, `MaxHirn/`). Nur die ausdrücklich
  genannten Pfade werden verbucht.
- **Commit-Nachrichten** enden mit:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## Dateiübersicht

| Datei | Zuständigkeit | Art |
|---|---|---|
| `lage.py` | Erhebung je Spur in fester Form; Heimat der 24 `spur_*()`, `wachenlage()`, `sperren()` | **neu** |
| `schnappschuss.py` | Tagesstand schreiben/lesen/aufräumen, Vortagsdifferenz | **neu** |
| `wochenbericht.py` | Vierwochenverlauf, Gesamtbilanz, Kategorien | **neu** |
| `guthaben_abgleich.py` | Buchbilanz gegen Kontostand der drei Live-Spuren | **neu** |
| `tagesbericht.py` | nur noch Darstellung: Vorrangregel, Sammelzeile, Vortagsdifferenz | ändern |
| `dauerlauf.py` (Berichtszweig ab Z. 806) | erst Bericht, dann Schnappschuss; montags zusätzlich Wochenbericht | ändern |
| `C:\Users\faupe\Documents\BrainFiles\.gitignore` | `stand/` ausschließen | ändern |
| `tests/test_lage.py` | feste Form, Buchlage-Kategorien, Ausfall je Spur | **neu** |
| `tests/test_schnappschuss.py` | schreibt nur nach `stand/`, Aufräumen, Differenz ohne Vorgänger | **neu** |
| `tests/test_bericht_vorrang.py` | Rang 1/2/3, Sammelzeile | **neu** |
| `tests/test_wochenbericht.py` | Verlauf, getrennte Summen | **neu** |
| `tests/test_guthaben_abgleich.py` | Rest erklärbar, Ausfall wird Text | **neu** |

**Warum `lage.py` und nicht ein Umbau in `tagesbericht.py`:** Wochenbericht,
Vortagsvergleich und Konsolenauswertung brauchen dieselbe Erhebung. Bleibt sie
in der Darstellungsdatei, entstehen drei Kopien, und die Zahlen driften
zwischen Handy und Konsole auseinander.

**Warum `schnappschuss.py` getrennt von `lage.py`:** `lage.py` liest nur,
`schnappschuss.py` schreibt. Die Trennung hält die einzige schreibende Stelle
dieses Umbaus auf einer Datei, die kein Journal anfasst.

---

### Aufgabe 1: `lage.py` — die Erhebung umziehen

Reiner Umzug, keine neue Logik. Die Aufgabe ist erst fertig, wenn der
Tagesbericht Zeichen für Zeichen dieselbe Ausgabe liefert wie vorher.

**Dateien:**
- Anlegen: `lage.py`
- Ändern: `tagesbericht.py`
- Test: `tests/test_lage.py`

**Schnittstellen:**
- Verbraucht: `auswertung_alle`, `zeitfenster` (aus Plan 1)
- Liefert:
  - `HOLER` — dasselbe Tupel wie heute in `tagesbericht.py:1020`
  - `spur_*()` — die 24 Funktionen, unverändert
  - `wachenlage(spur)`, `sperren(spur, lage)` — unverändert
  - `spiegelzeile()`, `stufenzeile()` bleiben in `tagesbericht.py` (Text, keine Erhebung)

- [ ] **Schritt 1: Den Vergleichstext festhalten**

```bash
python tagesbericht.py --ohne-xperp > "$TMPDIR/bericht_vorher.txt" 2>&1 || true
```

Der Bericht kann Spurenausfälle enthalten; das ist in Ordnung, er dient nur als
Vorher-Bild. Ablage im Temp-Ordner, nicht im Projekt.

- [ ] **Schritt 2: Die Erhebung verschieben**

Nach `lage.py` wandern aus `tagesbericht.py` **unverändert**, in dieser
Reihenfolge: `HIER`, `XPERP`, `_lies`, `_prozent`, alle `spur_*()` (inklusive
`_bilanz`, `_spur_indikator`, `_stop_preis_1zu1`, `spur_xperp_positionen`,
`spur_xperp`), `wachenlage`, `sperren`, `HOLER`.

Kopf von `lage.py`:

```python
"""Die Erhebung je Spur - an EINER Stelle.

Liest, rechnet nicht und formatiert nicht. Wer Text will, nimmt
tagesbericht.py oder wochenbericht.py; beide bekommen ihre Zahlen von hier.
Vor dem 18.09.2026 stand diese Erhebung in tagesbericht.py und waere fuer
den Wochenbericht ein zweites Mal entstanden.
"""
```

In `tagesbericht.py` bleiben: `zeile_position`, `spiegelzeile`, `STUFEN`,
`_stufenbuecher`, `stufenzeile`, `_stufenzahlen`, `baue`, `main`. Ganz oben:

```python
import lage
from lage import HOLER, sperren, wachenlage
```

Jeder Aufruf im Rumpf von `baue()` bleibt wortgleich — `wachenlage(s)`,
`sperren(s, lage_)`. **Achtung:** die lokale Variable `lage` in `baue()`
verdeckt sonst das Modul; sie wird zu `lage_` umbenannt (drei Stellen).

- [ ] **Schritt 3: Der Test auf die feste Form**

`tests/test_lage.py`:

```python
"""Tests fuer die Erhebungsschicht."""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import lage                                              # noqa: E402


class FormTest(unittest.TestCase):
    def test_jeder_holer_liefert_die_pflichtfelder(self):
        for hole in lage.HOLER:
            with self.subTest(spur=hole.__name__):
                try:
                    s = hole()
                except Exception as e:                   # noqa: BLE001
                    self.fail("%s ist ausgefallen: %s" % (hole.__name__, e))
                for feld in ("name", "waehrung", "w", "positionen"):
                    self.assertIn(feld, s, hole.__name__)
                self.assertIsInstance(s["positionen"], list)

    def test_holer_sind_vollzaehlig(self):
        self.assertEqual(len(lage.HOLER), 24)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 4: Test laufen lassen**

Aufruf: `python tests/test_lage.py`
Erwartet: PASS. Schlägt `test_holer_sind_vollzaehlig` fehl, ist die Zahl an die
tatsächliche Länge von `HOLER` anzupassen — sie steht dort, damit ein
verlorengegangener Umzug auffällt, nicht als Vorgabe.

- [ ] **Schritt 5: Gleichheit beweisen**

```bash
python tagesbericht.py --ohne-xperp > "$TMPDIR/bericht_nachher.txt" 2>&1 || true
diff "$TMPDIR/bericht_vorher.txt" "$TMPDIR/bericht_nachher.txt"
```

Erwartet: nur die Kopfzeile mit der Uhrzeit unterscheidet sich. Jede weitere
Abweichung ist ein Umzugsfehler und wird behoben, bevor es weitergeht.

- [ ] **Schritt 6: Volle Suite**

Aufruf: `python -m unittest discover -s tests -p "test_*.py"`
Erwartet: keine neuen Fehler. Bekannt und **nicht** von diesem Plan verursacht:
`test_risikovorfilter.EinbauTest.test_bei_gerissener_grenze_entsteht_keine_position`
(vorbestehend auf `master`, notiert in `BEFUND-hygiene-2026-09-17.md`).

- [ ] **Schritt 7: Verbuchen**

```bash
git add lage.py tagesbericht.py tests/test_lage.py
git commit -m "refactor(lage): die Erhebung zieht aus dem Bericht aus"
```

---

### Aufgabe 2: Kennzahlen im Fenster und die dritte Kategorie

**Dateien:**
- Ändern: `lage.py`
- Test: `tests/test_lage.py`

**Schnittstellen:**
- Verbraucht: `auswertung_alle.kennzahlen_fuer(spur, von, bis)`,
  `auswertung_alle.belastbar(k)`, `auswertung_alle.hat_buch(spur)`,
  `auswertung_alle.buch_seit(spur)`, `zeitfenster.fenster(tage=...)`
- Liefert:
  - `FENSTER_TAGE = 7`
  - `zu_lage(roh, schluessel, tage, kennzahlen)` → Lage-Struktur
  - `erhebe(mit_xperp=True, tage=FENSTER_TAGE, holer=None)` → Liste davon

Die Lage-Struktur je Spur, feste Form:

```python
{
  "schluessel": "scanner",        # Ordnername, oder None bei Sammelspuren
  "name": "Spur 1  OKX Spot",
  "waehrung": "USD",
  "positionen": [...],            # wie heute
  "wachen": {...} | None,         # Rueckgabe von wachenlage(), oder None
  "sperren": ["handel_erlaubt=false", ...],
  "stillgelegt": True | False,
  "kennzahlen": {...} | None,     # auswertung_alle.kennzahlen_fuer im Fenster
  "buchlage": "belastbar" | "zu_wenige_runden" | "kein_buch",
  "buch_seit": "2026-08-04" | None,
  "bilanz": "..." | None,         # der heutige Bilanztext, unveraendert
  "fehler": None | "TypeError: ...",
  "roh": {...},                   # die unveraenderte spur_*()-Rueckgabe
}
```

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

An `tests/test_lage.py` anhängen:

```python
class BuchlageTest(unittest.TestCase):
    def test_kategorie_kein_buch_wenn_journal_fehlt(self):
        roh = {"name": "Testspur", "waehrung": "USD", "w": {}, "z": {},
               "positionen": []}
        e = lage.zu_lage(roh, schluessel="gibtesnicht", tage=7)
        self.assertEqual(e["buchlage"], "kein_buch")
        self.assertIsNone(e["kennzahlen"])

    def test_zu_wenige_runden_zeigt_keine_zahl(self):
        roh = {"name": "Testspur", "waehrung": "USD", "w": {}, "z": {},
               "positionen": []}
        e = lage.zu_lage(roh, schluessel=None, tage=7,
                         kennzahlen={"n": 2, "ergebnis": 5.0, "treffer": 1})
        self.assertEqual(e["buchlage"], "zu_wenige_runden")

    def test_belastbar_ab_min_runden(self):
        roh = {"name": "Testspur", "waehrung": "USD", "w": {}, "z": {},
               "positionen": []}
        e = lage.zu_lage(roh, schluessel=None, tage=7,
                         kennzahlen={"n": 12, "ergebnis": 5.0, "treffer": 7})
        self.assertEqual(e["buchlage"], "belastbar")

    def test_ausfall_einer_spur_bleibt_eine_zeile(self):
        def kaputt():
            raise RuntimeError("Journal unlesbar")
        kaputt.__name__ = "spur_kaputt"
        ergebnis = lage.erhebe(holer=(kaputt,), mit_xperp=False)
        self.assertEqual(len(ergebnis), 1)
        self.assertIn("Journal unlesbar", ergebnis[0]["fehler"])
```

- [ ] **Schritt 2: Lauf zur Bestätigung des Fehlschlags**

Aufruf: `python tests/test_lage.py`
Erwartet: FAIL mit `AttributeError: module 'lage' has no attribute 'zu_lage'`.

- [ ] **Schritt 3: `zu_lage()` und `erhebe()` schreiben**

In `lage.py`, direkt unter den Importen:

```python
_UNGESETZT = object()

# Das Fenster der Berichtszahlen. Sieben Tage, weil "seit Anfang" jede
# Aenderung der letzten Woche unter dem Gewicht der Historie verschwinden
# laesst. Darstellungsgroesse, keine Handelsgroesse - deshalb hier und
# nicht in einer wachen.json.
FENSTER_TAGE = 7
```

Und als Funktionen:

```python
def zu_lage(roh, schluessel, tage=FENSTER_TAGE, kennzahlen=_UNGESETZT):
    """Eine spur_*()-Rueckgabe in die feste Form bringen.

    kennzahlen wird nur von Tests gesetzt; im Betrieb holt die Funktion sie
    selbst. Der Wachtposten _UNGESETZT unterscheidet "nicht uebergeben" von
    "ausdruecklich keine" - None ist eine gueltige Antwort.
    """
    if kennzahlen is _UNGESETZT:
        kennzahlen = None
        if schluessel and auswertung_alle.hat_buch(schluessel):
            von, bis = zeitfenster.fenster(tage=tage)
            kennzahlen = auswertung_alle.kennzahlen_fuer(schluessel,
                                                         von=von, bis=bis)

    if schluessel and not auswertung_alle.hat_buch(schluessel):
        buchlage = "kein_buch"
        kennzahlen = None
    elif not kennzahlen or not kennzahlen.get("n"):
        buchlage = "zu_wenige_runden"
    elif auswertung_alle.belastbar(kennzahlen):
        buchlage = "belastbar"
    else:
        buchlage = "zu_wenige_runden"

    return {
        "schluessel": schluessel,
        "name": roh["name"],
        "waehrung": roh["waehrung"],
        "positionen": roh.get("positionen", []),
        "wachen": None,
        "sperren": [],
        "stillgelegt": bool(roh.get("w", {}).get("stillgelegt")),
        "kennzahlen": kennzahlen,
        "buchlage": buchlage,
        "buch_seit": auswertung_alle.buch_seit(schluessel) if schluessel else None,
        "bilanz": roh.get("bilanz"),
        "fehler": None,
        "roh": roh,
    }


def _schluessel_von(roh):
    """Der Ordnername der Spur, oder None. auswertung_alle kennt Spuren
    unter diesem Namen; ohne ihn gibt es keine Kennzahlen."""
    ordner = roh.get("ordner")
    if not ordner:
        return None
    name = os.path.basename(ordner.rstrip(os.sep))
    return name if name in auswertung_alle.SPUREN else None


def erhebe(mit_xperp=True, tage=FENSTER_TAGE, holer=None):
    """Alle Spuren in fester Form. Ein Ausfall kostet eine Spur, nicht den Lauf."""
    aus = []
    for hole in (holer if holer is not None else HOLER):
        try:
            roh = hole()
        except Exception as e:                           # noqa: BLE001
            aus.append({"schluessel": None, "name": hole.__name__,
                        "waehrung": "", "positionen": [], "wachen": None,
                        "sperren": [], "stillgelegt": False,
                        "kennzahlen": None, "buchlage": "kein_buch",
                        "buch_seit": None, "bilanz": None,
                        "fehler": "%s: %s" % (type(e).__name__, e),
                        "roh": {}})
            continue
        e = zu_lage(roh, _schluessel_von(roh), tage=tage)
        e["wachen"] = (wachenlage(roh)
                       if roh.get("pruefmodul", "wachen_pruefung") else None)
        e["sperren"] = sperren(roh, e["wachen"])
        if roh.get("papierfest"):
            e["sperren"].insert(0, "kein Live-Zweig (Papierpfad)")
        aus.append(e)
    return aus
```

`mit_xperp` ist in `erhebe()` bewusst wirkungslos für `HOLER` — die
XPERP-Rangliste (`spur_xperp()`) ist kein Erhebungsposten, sondern ein
Textblock, und bleibt in `tagesbericht.baue()`. Der Parameter existiert, damit
Aufrufer dieselbe Sprache sprechen wie `tagesbericht.baue()`.

- [ ] **Schritt 4: Test laufen lassen**

Aufruf: `python tests/test_lage.py`
Erwartet: PASS.

- [ ] **Schritt 5: Verbuchen**

```bash
git add lage.py tests/test_lage.py
git commit -m "feat(lage): Kennzahlen im Fenster, dritte Kategorie kein Buch"
```

---

### Aufgabe 3: Der Schnappschuss

**Dateien:**
- Anlegen: `schnappschuss.py`
- Ändern: `C:\Users\faupe\Documents\BrainFiles\.gitignore`
- Test: `tests/test_schnappschuss.py`

**Schnittstellen:**
- Verbraucht: `lage.erhebe()`
- Liefert:
  - `ORDNER`, `AUFBEWAHRUNG_TAGE = 90`
  - `baue(erhebung, heute=None)` → `dict` mit `{"datum", "gebaut", "spuren"}`
  - `schreibe(stand, ordner=ORDNER)` → Pfad
  - `lade(datum, ordner=ORDNER)` → `dict` oder `None`
  - `aufraeumen(ordner=ORDNER, tage=AUFBEWAHRUNG_TAGE)` → Zahl gelöschter Dateien
  - `unterschiede(heute, gestern)` → `dict` je Spur

Je Spur trägt der Schnappschuss **vier** Felder und keines mehr: `positionen`
(Name, Einsatz, Einstieg), `sperren`, `runden`, `stillgelegt`. Bilanz,
Trefferquote und Rendite bleiben draußen — sie kommen aus den Journalen und
werden bei jedem Lesen neu gerechnet.

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

`tests/test_schnappschuss.py`:

```python
"""Tests fuer den Tagesschnappschuss.

Schreibt ausschliesslich in einen Temp-Ordner. Der Schnappschuss ist kein
Buch - journal_zweitziel wird nirgends beruehrt, Bedingung 4 bleibt aussen vor.
"""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import schnappschuss                                     # noqa: E402


def _lage(name, positionen=(), sperren=(), runden=0, still=False):
    return {"schluessel": name, "name": name, "waehrung": "USD",
            "positionen": list(positionen), "sperren": list(sperren),
            "stillgelegt": still, "wachen": {"runden_gesamt": runden},
            "kennzahlen": None, "buchlage": "kein_buch", "buch_seit": None,
            "bilanz": None, "fehler": None, "roh": {}}


class SchreibenTest(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="stand_test_")
        self.addCleanup(shutil.rmtree, self.ordner, True)

    def test_schreibt_genau_eine_datei_mit_datumsnamen(self):
        stand = schnappschuss.baue([_lage("scanner", runden=5)])
        pfad = schnappschuss.schreibe(stand, ordner=self.ordner)
        self.assertEqual(os.listdir(self.ordner), [os.path.basename(pfad)])
        self.assertRegex(os.path.basename(pfad), r"^\d{4}-\d{2}-\d{2}\.json$")

    def test_traegt_nur_die_vier_felder(self):
        stand = schnappschuss.baue([_lage("scanner", runden=5)])
        felder = set(stand["spuren"]["scanner"])
        self.assertEqual(felder, {"positionen", "sperren", "runden",
                                  "stillgelegt"})

    def test_aufraeumen_loescht_nur_zu_alte(self):
        alt = (dt.date.today() - dt.timedelta(days=200)).isoformat()
        neu = dt.date.today().isoformat()
        for tag in (alt, neu):
            with open(os.path.join(self.ordner, tag + ".json"), "w",
                      encoding="utf-8") as f:
                json.dump({"datum": tag, "spuren": {}}, f)
        weg = schnappschuss.aufraeumen(ordner=self.ordner, tage=90)
        self.assertEqual(weg, 1)
        self.assertEqual(os.listdir(self.ordner), [neu + ".json"])

    def test_fremde_dateien_bleiben_liegen(self):
        with open(os.path.join(self.ordner, "notizen.txt"), "w",
                  encoding="utf-8") as f:
            f.write("nicht meins")
        schnappschuss.aufraeumen(ordner=self.ordner, tage=0)
        self.assertIn("notizen.txt", os.listdir(self.ordner))


class VergleichTest(unittest.TestCase):
    def test_fehlender_vorgaenger_ist_kein_fehler(self):
        heute = schnappschuss.baue([_lage("scanner", runden=5)])
        self.assertEqual(schnappschuss.unterschiede(heute, None), {})

    def test_neue_sperre_wird_gemeldet(self):
        gestern = schnappschuss.baue([_lage("scanner", runden=5)])
        heute = schnappschuss.baue([_lage("scanner", runden=6,
                                          sperren=["KILL-SWITCH erreicht"])])
        d = schnappschuss.unterschiede(heute, gestern)
        self.assertIn("KILL-SWITCH erreicht", d["scanner"]["sperre_neu"])
        self.assertEqual(d["scanner"]["runden_mehr"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Lauf zur Bestätigung des Fehlschlags**

Aufruf: `python tests/test_schnappschuss.py`
Erwartet: FAIL mit `ModuleNotFoundError: No module named 'schnappschuss'`.

- [ ] **Schritt 3: `schnappschuss.py` schreiben**

```python
"""Der Tagesschnappschuss - nur was die Journale nicht hergeben.

Vier Felder je Spur: offene Positionen, Sperrenlage, Rundenzaehler der
Wachen, Stillgelegt-Merker. Alles andere waere eine zweite Wahrheit; Bilanz
und Trefferquote werden aus den Journalen gerechnet, jedes Mal neu.

Ein verlorener Schnappschuss ist unwiederbringlich. Das ist bewusst in Kauf
genommen: ein fehlender Vortagsvergleich ist eine Unbequemlichkeit, ein
falsch gespiegeltes Buch ein Schaden. Deshalb liegt der Stand zentral unter
stand/ und nicht je Spurordner - spiegelstand.py prueft genau zwei
Dateinamen je Spur, und ein dritter dort waere ein Eingriff in einen
Schreibpfad, den dieser Umbau nicht braucht.
"""
import datetime as dt
import json
import os
import re

HIER = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(HIER, "stand")

# Aufbewahrung. Darstellungsgroesse, keine Handelsgroesse - der Vergleich
# reicht nie weiter zurueck als der Wochenbericht schaut.
AUFBEWAHRUNG_TAGE = 90

_DATEINAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


def baue(erhebung, heute=None):
    """Aus der Erhebung den duennen Stand bauen."""
    heute = heute or dt.date.today()
    spuren = {}
    for e in erhebung:
        schluessel = e.get("schluessel") or e.get("name")
        wachen = e.get("wachen") or {}
        spuren[schluessel] = {
            "positionen": [{"name": p.get("name"),
                            "wert": p.get("wert"),
                            "einstieg": p.get("einstieg")}
                           for p in e.get("positionen", [])],
            "sperren": list(e.get("sperren", [])),
            "runden": wachen.get("runden_gesamt") if "fehler" not in wachen else None,
            "stillgelegt": bool(e.get("stillgelegt")),
        }
    return {"datum": heute.isoformat(),
            "gebaut": dt.datetime.now().isoformat(timespec="seconds"),
            "spuren": spuren}


def schreibe(stand, ordner=ORDNER):
    """Den Stand ablegen und danach aufraeumen. Gibt den Pfad zurueck."""
    os.makedirs(ordner, exist_ok=True)
    pfad = os.path.join(ordner, "%s.json" % stand["datum"])
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)
    aufraeumen(ordner=ordner)
    return pfad


def lade(datum, ordner=ORDNER):
    """Der Stand eines Tages, oder None. Ein fehlender Stand ist kein Fehler."""
    if hasattr(datum, "isoformat"):
        datum = datum.isoformat()
    try:
        with open(os.path.join(ordner, "%s.json" % datum), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def aufraeumen(ordner=ORDNER, tage=AUFBEWAHRUNG_TAGE):
    """Staende aelter als 'tage' entfernen. Nur Dateien im Datumsformat -
    was sonst in dem Ordner liegt, gehoert jemand anderem."""
    grenze = dt.date.today() - dt.timedelta(days=tage)
    weg = 0
    try:
        namen = os.listdir(ordner)
    except OSError:
        return 0
    for name in namen:
        treffer = _DATEINAME.match(name)
        if not treffer:
            continue
        try:
            wann = dt.date.fromisoformat(treffer.group(1))
        except ValueError:
            continue
        if wann < grenze:
            try:
                os.remove(os.path.join(ordner, name))
                weg += 1
            except OSError:
                pass
    return weg


def unterschiede(heute, gestern):
    """Was sich seit gestern geaendert hat, je Spur.

    Fehlt der Vorgaenger, ist das Ergebnis leer - der Bericht schreibt dann
    einen Satz und baut trotzdem.
    """
    if not gestern:
        return {}
    aus = {}
    for name, h in heute.get("spuren", {}).items():
        g = gestern.get("spuren", {}).get(name)
        if g is None:
            continue
        alt_pos = {p["name"] for p in g["positionen"]}
        neu_pos = {p["name"] for p in h["positionen"]}
        alt_sperre, neu_sperre = set(g["sperren"]), set(h["sperren"])
        d = {
            "position_neu": sorted(neu_pos - alt_pos),
            "position_weg": sorted(alt_pos - neu_pos),
            "sperre_neu": sorted(neu_sperre - alt_sperre),
            "sperre_weg": sorted(alt_sperre - neu_sperre),
            "runden_mehr": (h["runden"] or 0) - (g["runden"] or 0),
            "stillgelegt_neu": h["stillgelegt"] and not g["stillgelegt"],
        }
        if any(d[k] for k in d):
            aus[name] = d
    return aus
```

- [ ] **Schritt 4: Test laufen lassen**

Aufruf: `python tests/test_schnappschuss.py`
Erwartet: PASS.

- [ ] **Schritt 5: `stand/` aus der Versionierung halten**

`C:\Users\faupe\Documents\BrainFiles\.gitignore` folgt Deny-all mit Allowlist;
Zeile 66 (`!Agenten/Handel/*.md`) gibt Markdown im Wurzelverzeichnis frei. JSON
unter `Agenten/Handel/stand/` ist davon nicht erfasst und damit ohnehin
ignoriert. Trotzdem wird die Absicht benannt — sonst gibt eine spätere
Erweiterung der Allowlist Laufzeitdaten frei. Direkt hinter Zeile 66 einfügen:

```
# Laufzeitdaten: der Tagesschnappschuss. Abgeleitet, kein Buch.
Agenten/Handel/stand/
```

Prüfung: `git check-ignore -v Agenten/Handel/stand/2026-09-18.json` nennt diese
Zeile.

- [ ] **Schritt 6: Verbuchen**

```bash
git add schnappschuss.py tests/test_schnappschuss.py
git -C "C:/Users/faupe/Documents/BrainFiles" add .gitignore
git commit -m "feat(schnappschuss): der Tagesstand, vier Felder je Spur"
```

---

### Aufgabe 4: Vorrangregel und Sammelzeile im Tagesbericht

**Dateien:**
- Ändern: `tagesbericht.py`
- Test: `tests/test_bericht_vorrang.py`

**Schnittstellen:**
- Verbraucht: `lage.erhebe()`, `schnappschuss.baue/lade/unterschiede`
- Liefert:
  - `rang(e, diff)` → `1`, `2` oder `3`
  - `sammelzeile(stille)` → Text
  - `_block(e, d)` → Text eines vollen Blocks
  - `baue(mit_xperp=True)` unverändert in Signatur und Wirkung nach außen

Die drei Ränge:

| Rang | Auslöser | Darstellung |
|---|---|---|
| 1 | Ausfall beim Einsammeln, neu geschlossene Sperre, stillgelegt, Herzschlag zu alt, KILL-SWITCH | voller Block |
| 2 | offene Positionen, seit gestern geschlossene oder eröffnete Runden | voller Block |
| 3 | alles Übrige | eine Sammelzeile |

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

`tests/test_bericht_vorrang.py`:

```python
"""Tests fuer die Vorrangregel des Tagesberichts."""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import tagesbericht                                      # noqa: E402


def _e(name, positionen=(), sperren=(), still=False, fehler=None, wachen=None):
    return {"schluessel": name, "name": name, "waehrung": "USD",
            "positionen": list(positionen), "sperren": list(sperren),
            "stillgelegt": still, "wachen": wachen, "kennzahlen": None,
            "buchlage": "kein_buch", "buch_seit": None, "bilanz": None,
            "fehler": fehler, "roh": {}}


class VorrangTest(unittest.TestCase):
    def test_ausfall_ist_rang_eins(self):
        self.assertEqual(tagesbericht.rang(_e("a", fehler="kaputt"), {}), 1)

    def test_neue_sperre_ist_rang_eins(self):
        diff = {"sperre_neu": ["KILL-SWITCH erreicht"]}
        self.assertEqual(tagesbericht.rang(_e("a"), diff), 1)

    def test_stillgelegt_ist_rang_eins(self):
        self.assertEqual(tagesbericht.rang(_e("a", still=True), {}), 1)

    def test_herzschlag_alt_ist_rang_eins(self):
        e = _e("a", wachen={"herzschlag_frisch": False, "freigabe_erfuellt": True,
                            "kill": False, "ev_negativ": False})
        self.assertEqual(tagesbericht.rang(e, {}), 1)

    def test_offene_position_ist_rang_zwei(self):
        e = _e("a", positionen=[{"name": "BTC", "wert": 100, "einstieg": 1.0,
                                 "kurs": None, "vh": None, "stop": None,
                                 "seit": None}])
        self.assertEqual(tagesbericht.rang(e, {}), 2)

    def test_geschlossene_runde_ist_rang_zwei(self):
        self.assertEqual(tagesbericht.rang(_e("a"), {"runden_mehr": 2}), 2)

    def test_stille_spur_ist_rang_drei(self):
        self.assertEqual(tagesbericht.rang(_e("a"), {}), 3)


class SammelzeileTest(unittest.TestCase):
    def test_zaehlt_und_benennt(self):
        zeile = tagesbericht.sammelzeile([_e("macd_mtf"), _e("squeeze")])
        self.assertIn("2 Spuren still", zeile)
        self.assertIn("macd_mtf", zeile)
        self.assertIn("squeeze", zeile)

    def test_leere_liste_gibt_leeren_text(self):
        self.assertEqual(tagesbericht.sammelzeile([]), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Lauf zur Bestätigung des Fehlschlags**

Aufruf: `python tests/test_bericht_vorrang.py`
Erwartet: FAIL mit `AttributeError: module 'tagesbericht' has no attribute 'rang'`.

- [ ] **Schritt 3: Vorrangregel und Sammelzeile schreiben**

In `tagesbericht.py`, vor `baue()`:

```python
def rang(e, diff):
    """Welchen Platz eine Spur im Bericht bekommt: 1, 2 oder 3.

    Die Rangfolge ordnet nach Dringlichkeit, nicht nach Interesse. Ein
    Bericht mit 24 gleichlangen Bloecken hat keinen Vorrang - man liest ihn
    einmal ganz und danach nie wieder.
    """
    w = e.get("wachen") or {}
    if (e.get("fehler") or e.get("stillgelegt")
            or diff.get("sperre_neu")
            or ("fehler" not in w
                and (w.get("herzschlag_frisch") is False or w.get("kill")))):
        return 1
    if (e.get("positionen") or diff.get("runden_mehr")
            or diff.get("position_neu") or diff.get("position_weg")):
        return 2
    return 3


def sammelzeile(stille):
    """Der stille Rest als eine Zeile: gezaehlt und benannt."""
    if not stille:
        return ""
    namen = [e["schluessel"] or e["name"] for e in stille]
    return "%d Spuren still: %s" % (len(namen), ", ".join(sorted(namen)))
```

- [ ] **Schritt 4: Den Blocktext in `_block()` fassen**

Der heutige Rumpf der `for hole in HOLER`-Schleife wird zu `_block(e, d)` und
liest aus der Lage-Struktur statt aus `s`: `e["name"]`, `e["positionen"]`,
`e["waehrung"]`, `e["bilanz"]`, `e["wachen"]`, `e["sperren"]`,
`e["stillgelegt"]`. Der Ausfallzweig wird zur ersten Zeile:

```python
def _block(e, d):
    """Ein voller Block. Text, sonst nichts."""
    if e["fehler"]:
        return "\n<b>%s</b>\n  AUSFALL: %s" % (e["name"], e["fehler"])
    zeilen = ["\n<b>%s</b>%s" % (e["name"],
                                "  — STILLGELEGT" if e["stillgelegt"] else "")]
    ...
```

Der bestehende Text — Positionszeilen, Summenzeile, Bilanzzeile, Wachenzeile
mit `ruecklauf_<waehrung>`, Stillgelegt-Satz und `Live: ...` — wandert
wortgleich hierher. Danach zwei neue Zeilen. Zuerst die Kennzahlzeile:

```python
    if e["buchlage"] == "belastbar":
        k = e["kennzahlen"]
        zeilen.append("  7 Tage: %d Runden, %+.2f %s, Treffer %d%%"
                      % (k["n"], k["ergebnis"], e["waehrung"],
                         round(100.0 * k["treffer"] / k["n"])))
    elif e["buchlage"] == "zu_wenige_runden":
        zeilen.append("  7 Tage: zu wenige Runden (%d)"
                      % (e["kennzahlen"] or {}).get("n", 0))
    elif e["schluessel"]:
        seit = e["buch_seit"]
        zeilen.append("  kein Buch%s" % (" (seit %s)" % seit if seit else ""))
```

Dann die Differenzzeile, wenn es eine gibt:

```python
    teile = []
    if d.get("position_neu"):
        teile.append("neu: " + ", ".join(d["position_neu"]))
    if d.get("position_weg"):
        teile.append("geschlossen: " + ", ".join(d["position_weg"]))
    if d.get("sperre_neu"):
        teile.append("Sperre zu: " + "; ".join(d["sperre_neu"]))
    if d.get("sperre_weg"):
        teile.append("Sperre auf: " + "; ".join(d["sperre_weg"]))
    if d.get("runden_mehr"):
        teile.append("%+d Runden" % d["runden_mehr"])
    if teile:
        zeilen.append("  seit gestern: " + " | ".join(teile))
    return "\n".join(zeilen)
```

- [ ] **Schritt 5: `baue()` auf die Erhebung umstellen**

```python
def baue(mit_xperp=True):
    """Der ganze Bericht als Text. Kein Netz noetig fuer den Rahmen."""
    heute = dt.datetime.now()
    t = ["<b>Handel  %s</b>" % heute.strftime("%d.%m.%Y %H:%M")]

    erhebung = lage.erhebe(mit_xperp=mit_xperp)
    stand = schnappschuss.baue(erhebung, heute=heute.date())
    gestern = schnappschuss.lade(heute.date() - dt.timedelta(days=1))
    diffs = schnappschuss.unterschiede(stand, gestern)
    if gestern is None:
        t.append("Kein Stand von gestern - der Vergleich faellt heute aus.")

    stille = []
    gesamt_offen = 0
    for e in erhebung:
        gesamt_offen += len(e["positionen"])
        d = diffs.get(e["schluessel"] or e["name"], {})
        if rang(e, d) == 3:
            stille.append(e)
            continue
        t.append(_block(e, d))

    zeile = sammelzeile(stille)
    if zeile:
        t.append("\n" + zeile)
```

Der Rest von `baue()` — XPERP-Rangliste unter `if mit_xperp:`, `spiegelzeile()`,
`stufenzeile()`, die Gesamtzahl der offenen Positionen und der Melderhinweis —
bleibt unverändert am Ende stehen. `gesamt_offen` zählt **vor** dem `continue`,
also über alle Spuren: heute kann eine stille Spur keine Position haben (Rang 2
greift), aber die Zählung bleibt so gegen spätere Änderungen der Rangregel
robust.

Oben in `tagesbericht.py` dazu: `import schnappschuss`.

**Wichtig:** `baue()` **schreibt keinen** Schnappschuss. Es baut ihn nur im
Speicher, um mit gestern zu vergleichen. Geschrieben wird an genau einer Stelle,
in `dauerlauf.py` (Aufgabe 6) — ein zweiter Schreibort wäre ein zweiter Ort zum
Scheitern.

- [ ] **Schritt 6: Tests laufen lassen**

Aufruf: `python tests/test_bericht_vorrang.py`
Erwartet: PASS.

Aufruf: `python tagesbericht.py --ohne-xperp`
Erwartet: ein Bericht, der deutlich kürzer ist als der aus Aufgabe 1 — fünf bis
acht Blöcke plus eine Sammelzeile — und in dem jede verbliebene Spur einen
sichtbaren Grund für ihren Platz hat.

- [ ] **Schritt 7: Verbuchen**

```bash
git add tagesbericht.py tests/test_bericht_vorrang.py
git commit -m "feat(bericht): Vorrangregel, Sammelzeile, Vortagsdifferenz"
```

---

### Aufgabe 5: Der Wochenbericht

**Dateien:**
- Anlegen: `wochenbericht.py`
- Test: `tests/test_wochenbericht.py`

**Schnittstellen:**
- Verbraucht: `lage`, `auswertung_alle.kennzahlen_fuer`, `auswertung_alle.belastbar`,
  `zeitfenster.jetzt/fenster`, `gesamtbilanz.posten/summe`, `melder`
- Liefert:
  - `FENSTER_ANZAHL = 4`, `FENSTER_TAGE = 7`
  - `verlauf(spur, anzahl, tage, kennzahlen_fn=None)` → Liste von `dict` oder `None`
  - `verlaufszeile(spur, werte)` → Text
  - `bilanzteil(posten)` → Text
  - `baue()` → Text

Der Verlauf ist *n*-mal derselbe Aufruf von `kennzahlen_fuer()` mit
verschobenem Fenster — keine neue Rechnung, keine neue Formel.

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

`tests/test_wochenbericht.py`:

```python
"""Tests fuer den Wochenbericht."""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import wochenbericht                                     # noqa: E402


class VerlaufTest(unittest.TestCase):
    def test_vier_fenster_vier_eintraege(self):
        gerufen = []

        def fake(spur, von=None, bis=None):
            gerufen.append((von, bis))
            return {"n": 10, "ergebnis": 1.0, "treffer": 6}

        v = wochenbericht.verlauf("scanner", kennzahlen_fn=fake)
        self.assertEqual(len(v), 4)
        self.assertEqual(len(gerufen), 4)

    def test_fenster_liegen_hintereinander_und_ueberlappen_nicht(self):
        gerufen = []

        def fake(spur, von=None, bis=None):
            gerufen.append((von, bis))
            return None

        wochenbericht.verlauf("scanner", kennzahlen_fn=fake)
        for juenger, aelter in zip(gerufen, gerufen[1:]):
            self.assertLessEqual(aelter[1], juenger[0])


class SummenTest(unittest.TestCase):
    def test_waehrungen_werden_nicht_stumm_addiert(self):
        posten = [
            {"spur": "scanner", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "USD", "live": True, "belastbar": True},
            {"spur": "kraken", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "EUR", "live": False, "belastbar": True},
        ]
        text = wochenbericht.bilanzteil(posten)
        self.assertIn("USD", text)
        self.assertIn("EUR", text)
        self.assertNotIn("+10.00", text)     # keine Summe ueber beide

    def test_papier_und_live_bleiben_getrennt(self):
        posten = [
            {"spur": "scanner", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "USD", "live": True, "belastbar": True},
            {"spur": "swap", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "USD", "live": False, "belastbar": True},
        ]
        text = wochenbericht.bilanzteil(posten)
        self.assertIn("Live", text)
        self.assertIn("Papier", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Lauf zur Bestätigung des Fehlschlags**

Aufruf: `python tests/test_wochenbericht.py`
Erwartet: FAIL mit `ModuleNotFoundError: No module named 'wochenbericht'`.

- [ ] **Schritt 3: `wochenbericht.py` schreiben**

```python
"""Der Wochenbericht - montags, aus derselben Erhebung wie der Tagesbericht.

Der Verlauf ist n-mal derselbe Aufruf mit verschobenem Fenster. Keine neue
Rechnung: waere es eine, gaebe es zwei Formeln fuer dieselbe Frage, und die
beiden liefen auseinander.
"""
import argparse
import datetime as dt
import sys

import auswertung_alle
import gesamtbilanz
import lage
import melder
import zeitfenster

# Vier Wochen nebeneinander. Darstellungsgroesse, keine Handelsgroesse.
FENSTER_ANZAHL = 4
FENSTER_TAGE = 7


def verlauf(spur, anzahl=FENSTER_ANZAHL, tage=FENSTER_TAGE, kennzahlen_fn=None):
    """Die letzten 'anzahl' Fenster, juengstes zuerst."""
    hole = kennzahlen_fn or auswertung_alle.kennzahlen_fuer
    jetzt = zeitfenster.jetzt()
    aus = []
    for i in range(anzahl):
        bis = jetzt - dt.timedelta(days=tage * i)
        von = bis - dt.timedelta(days=tage)
        aus.append(hole(spur, von=von, bis=bis))
    return aus


def verlaufszeile(spur, werte):
    """Eine Zeile je Spur: vier Fenster nebeneinander."""
    teile = []
    for k in werte:
        if not k or not k.get("n"):
            teile.append("    -   ")
        elif auswertung_alle.belastbar(k):
            teile.append("%+7.2f" % k["ergebnis"])
        else:
            teile.append("  n=%-2d " % k["n"])
    return "  %-20s %s" % (spur, " ".join(teile))


def bilanzteil(posten):
    """Die Gesamtbilanz, getrennt nach Waehrung und Papier/Live."""
    s = gesamtbilanz.summe(posten)
    zeilen = []
    for (waehrung, live), t in sorted(s.items()):
        zeilen.append("  %-4s %-7s %4d Runden  %+10.2f  Treffer %d%%"
                      % (waehrung, "Live" if live else "Papier", t["n"],
                         t["ergebnis"],
                         round(100.0 * t["treffer"] / t["n"]) if t["n"] else 0))
    if not zeilen:
        zeilen.append("  Keine belastbare Spur in diesem Fenster.")
    return "\n".join(zeilen)


def baue():
    """Der Wochenbericht als Text."""
    heute = dt.datetime.now()
    t = ["<b>Handel - Woche  %s</b>" % heute.strftime("%d.%m.%Y")]

    t.append("\n<b>Verlauf</b>  (vier Fenster a %d Tage, juengstes links)"
             % FENSTER_TAGE)
    erhebung = lage.erhebe(mit_xperp=False)
    for e in erhebung:
        if not e["schluessel"]:
            continue
        t.append(verlaufszeile(e["schluessel"], verlauf(e["schluessel"])))
    t.append("  n=<Zahl> heisst: zu wenige Runden fuer eine Aussage.")

    von, bis = zeitfenster.fenster(tage=FENSTER_TAGE * FENSTER_ANZAHL)
    posten = gesamtbilanz.posten(von=von, bis=bis)
    t.append("\n<b>Gesamtbilanz</b>  (%d Tage)" % (FENSTER_TAGE * FENSTER_ANZAHL))
    t.append(bilanzteil(posten))

    ohne_buch = sorted(e["schluessel"] for e in erhebung
                       if e["buchlage"] == "kein_buch" and e["schluessel"])
    if ohne_buch:
        t.append("\n<b>Kein Buch</b>")
        for name in ohne_buch:
            t.append("  %s" % name)
        t.append("  Eine laufende Spur ohne Journal ist ein Betriebsfehler.")

    try:
        import guthaben_abgleich                          # noqa: PLC0415
        t.append("\n" + guthaben_abgleich.text())
    except Exception as e:                                # noqa: BLE001
        t.append("\nGuthabenabgleich nicht verfuegbar: %s" % e)

    return "\n".join(t)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--senden", action="store_true",
                   help="zusaetzlich per Telegram schicken")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = baue()
    print(text.replace("<b>", "").replace("</b>", ""))
    if a.senden and not melder.sende(text):
        print("\n-> nicht gesendet: %s fehlt" % melder.fehlt())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Der Aufruf von `guthaben_abgleich` steht bereits hier, obwohl das Modul erst in
Aufgabe 7 entsteht — deshalb der `try`. Bis dahin schreibt der Wochenbericht
eine Zeile statt einer Zahl, und genau so soll er sich auch später bei einem
Ausfall verhalten.

- [ ] **Schritt 4: Tests laufen lassen**

Aufruf: `python tests/test_wochenbericht.py`
Erwartet: PASS.

Aufruf: `python wochenbericht.py`
Erwartet: Verlaufstabelle, getrennte Summen, Liste der Spuren ohne Buch und die
Zeile „Guthabenabgleich nicht verfuegbar".

- [ ] **Schritt 5: Verbuchen**

```bash
git add wochenbericht.py tests/test_wochenbericht.py
git commit -m "feat(wochenbericht): Vierwochenverlauf und getrennte Summen"
```

---

### Aufgabe 6: Anbindung an `dauerlauf.py`

**Dateien:**
- Ändern: `dauerlauf.py` (Berichtszweig ab Z. 806)

**Schnittstellen:**
- Verbraucht: `lage`, `schnappschuss`, `wochenbericht`
- Ändert kein Verhalten der Zyklusschleife.

- [ ] **Schritt 1: Den Zweig erweitern**

Der heutige Zweig (ab `# 3. Tagesbericht faellig?`) bekommt zwei Ergänzungen.
Der Schnappschuss wird **nach** dem Bericht geschrieben: der Bericht legt den
Stand von gestern daneben, und ein zu früh geschriebener Stand wäre sein
eigener Vortag.

```python
        heute = jetzt().date()
        if (not self.stumm and self.letzter_bericht != heute
                and jetzt().hour >= 8):
            self.letzter_bericht = heute
            protokoll("Tagesbericht")
            try:
                self.sende(tagesbericht.baue(mit_xperp=True))
            except Exception as e:                       # noqa: BLE001
                self.sende("<b>Tagesbericht gescheitert</b>\n%s" % e)
            # Erst danach den Stand von heute ablegen - siehe oben.
            try:
                schnappschuss.schreibe(
                    schnappschuss.baue(lage.erhebe(mit_xperp=False)))
            except Exception as e:                       # noqa: BLE001
                protokoll("Schnappschuss gescheitert: %s" % e)
            if heute.weekday() == 0:
                protokoll("Wochenbericht")
                try:
                    self.sende(wochenbericht.baue())
                except Exception as e:                   # noqa: BLE001
                    self.sende("<b>Wochenbericht gescheitert</b>\n%s" % e)
```

Der Schnappschuss meldet seinen Ausfall ins Protokoll, nicht per Telegram — ein
fehlender Vortagsvergleich ist eine Unbequemlichkeit, keine Nachricht wert.

Oben in `dauerlauf.py` dazu: `import lage`, `import schnappschuss`,
`import wochenbericht`, alphabetisch in die bestehende Importgruppe.

- [ ] **Schritt 2: Trockenlauf**

Aufruf: `python -c "import dauerlauf"`
Erwartet: kein Fehler, kein Import-Zyklus.

Aufruf: `python -m unittest discover -s tests -p "test_*.py"`
Erwartet: keine neuen Fehler gegenüber Aufgabe 1, Schritt 6.

- [ ] **Schritt 3: Verbuchen**

```bash
git add dauerlauf.py
git commit -m "feat(dauerlauf): Schnappschuss nach dem Bericht, montags die Woche"
```

---

### Aufgabe 7: Guthabenabgleich der drei Live-Spuren

Zuletzt, weil es der einzige Teil mit Außenabhängigkeit ist. Alles davor
funktioniert ohne ihn.

**Dateien:**
- Anlegen: `guthaben_abgleich.py`
- Test: `tests/test_guthaben_abgleich.py`

**Schnittstellen:**
- Verbraucht: `kraken/kraken.py:190 guthaben(waehrung="ZEUR")`,
  `scanner/okx.py:217 guthaben_usdt()`, `xperp/okxf.py:399 guthaben_usdt()`,
  `auswertung_alle.kennzahlen_fuer`, `lage.erhebe`
- Liefert:
  - `LIVE = ("scanner", "kraken", "xperp")`
  - `abgleich(spur, konto=None, bilanz=None, gebunden=None)` → `dict`
  - `text(abgleiche=None)` → Text für den Wochenbericht

Ziel ist **nicht** Übereinstimmung — bei offenen Positionen kann es sie nicht
geben —, sondern die Erklärbarkeit der Differenz:
`Bilanz + gebundener Einsatz ≈ Kontostand`. Was übrig bleibt, ist der Fund. Eine
systematisch danebenliegende Kostenformel zeigt sich als wachsender Rest und
sonst nirgends.

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

`tests/test_guthaben_abgleich.py`:

```python
"""Tests fuer den Guthabenabgleich.

Kein Test geht ans Netz: der Kontostand wird uebergeben.
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import guthaben_abgleich                                 # noqa: E402


class AbgleichTest(unittest.TestCase):
    def test_rest_ist_konto_minus_bilanz_minus_gebunden(self):
        a = guthaben_abgleich.abgleich("scanner", konto=1050.0, bilanz=30.0,
                                       gebunden=1000.0)
        self.assertAlmostEqual(a["rest"], 20.0)
        self.assertIsNone(a["fehler"])

    def test_ausgefallener_abruf_traegt_den_grund_statt_einer_zahl(self):
        def kaputt():
            raise OSError("Netz weg")
        a = guthaben_abgleich.abgleich("scanner", konto=kaputt, bilanz=0.0,
                                       gebunden=0.0)
        self.assertIsNone(a["rest"])
        self.assertIn("Netz weg", a["fehler"])

    def test_papierspur_ist_nicht_dabei(self):
        self.assertNotIn("swap", guthaben_abgleich.LIVE)

    def test_text_nennt_papierbuch_fuer_die_uebrigen(self):
        t = guthaben_abgleich.text(abgleiche=[
            {"spur": "scanner", "konto": 1050.0, "bilanz": 30.0,
             "gebunden": 1000.0, "rest": 20.0, "waehrung": "USD",
             "fehler": None}])
        self.assertIn("scanner", t)
        self.assertIn("Papierbuch", t)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Lauf zur Bestätigung des Fehlschlags**

Aufruf: `python tests/test_guthaben_abgleich.py`
Erwartet: FAIL mit `ModuleNotFoundError: No module named 'guthaben_abgleich'`.

- [ ] **Schritt 3: `guthaben_abgleich.py` schreiben**

```python
"""Buchbilanz gegen Kontostand - nur fuer die drei Spuren mit Boersenzugang.

Ziel ist nicht Uebereinstimmung. Bei offenen Positionen kann es sie nicht
geben. Ziel ist die Erklaerbarkeit der Differenz: Bilanz plus gebundener
Einsatz sollte den Kontostand ergeben. Was uebrig bleibt, ist der Fund - eine
systematisch danebenliegende Kostenformel zeigt sich hier als wachsender Rest
und sonst nirgends.

Fuer die 21 Papierspuren gibt es nichts abzugleichen. Ein "Abgleich" gegen ein
leeres Konto waere eine Zahl, die Vertrauen erzeugt, ohne etwas zu pruefen.

Abruf nur beim Wochenbericht, nie beim Tagesbericht: der darf nicht am Netz
haengen.
"""
import os
import sys

import auswertung_alle
import lage
import zeitfenster

HIER = os.path.dirname(os.path.abspath(__file__))

LIVE = ("scanner", "kraken", "xperp")
WAEHRUNG = {"scanner": "USD", "kraken": "EUR", "xperp": "USD"}


def _konto_fn(spur):
    """Der Kontostandabruf der Spur. Import erst beim Aufruf - ein fehlendes
    Boersenmodul darf den Bericht nicht am Laden hindern."""
    def hole():
        sys.path.insert(0, os.path.join(HIER, spur))
        if spur == "kraken":
            import kraken                                # noqa: PLC0415
            return float(kraken.guthaben("ZEUR"))
        if spur == "scanner":
            import okx                                   # noqa: PLC0415
            return float(okx.guthaben_usdt())
        import okxf                                      # noqa: PLC0415
        return float(okxf.guthaben_usdt())
    return hole


def _gebunden(spur):
    """Was gerade in offenen Positionen steckt."""
    for e in lage.erhebe(mit_xperp=False):
        if e["schluessel"] == spur:
            return sum(p.get("wert") or 0 for p in e["positionen"])
    return 0.0


def abgleich(spur, konto=None, bilanz=None, gebunden=None):
    """Ein Abgleich. Alle drei Groessen sind uebergebbar - fuer Tests, und
    damit der Abruf an genau einer Stelle scheitern kann."""
    fehler = None
    if callable(konto):
        try:
            konto = konto()
        except Exception as e:                           # noqa: BLE001
            fehler = "%s: %s" % (type(e).__name__, e)
            konto = None
    elif konto is None:
        try:
            konto = _konto_fn(spur)()
        except Exception as e:                           # noqa: BLE001
            fehler = "%s: %s" % (type(e).__name__, e)
    if bilanz is None:
        von, bis = zeitfenster.fenster()
        k = auswertung_alle.kennzahlen_fuer(spur, von=von, bis=bis)
        bilanz = (k or {}).get("ergebnis", 0.0)
    if gebunden is None:
        gebunden = _gebunden(spur)
    rest = None if fehler else konto - bilanz - gebunden
    return {"spur": spur, "konto": konto, "bilanz": bilanz,
            "gebunden": gebunden, "rest": rest,
            "waehrung": WAEHRUNG[spur], "fehler": fehler}


def text(abgleiche=None):
    """Der Abschnitt fuer den Wochenbericht."""
    if abgleiche is None:
        abgleiche = [abgleich(s) for s in LIVE]
    t = ["<b>Guthabenabgleich</b>"]
    for a in abgleiche:
        if a["fehler"]:
            t.append("  %-8s Abruf ausgefallen: %s"
                     % (a["spur"], a["fehler"][:80]))
            continue
        t.append("  %-8s Konto %.2f %s = Bilanz %+.2f + gebunden %.2f "
                 "+ Rest %+.2f"
                 % (a["spur"], a["konto"], a["waehrung"], a["bilanz"],
                    a["gebunden"], a["rest"]))
    t.append("  Die uebrigen Spuren fuehren ein Papierbuch - nichts abzugleichen.")
    t.append("  Ein wachsender Rest ist der Fund, nicht die Uebereinstimmung.")
    return "\n".join(t)
```

- [ ] **Schritt 4: Tests laufen lassen**

Aufruf: `python tests/test_guthaben_abgleich.py`
Erwartet: PASS.

- [ ] **Schritt 5: Verbuchen**

```bash
git add guthaben_abgleich.py tests/test_guthaben_abgleich.py
git commit -m "feat(guthaben): Buchbilanz gegen Konto, der Rest ist der Fund"
```

---

## Abschlussprüfung

- [x] **Volle Suite:** `python -m unittest discover -s tests -p "test_*.py"`
  Erwartet: keine neuen Fehler gegenüber dem Stand vor diesem Plan. Der bekannte
  vorbestehende Fehler `test_risikovorfilter` bleibt und gehört zu Thema 4.
  **Beleg 19.09.2026:** 398 Tests, 1 Fehler — ausschließlich
  `test_risikovorfilter.EinbauTest.test_bei_gerissener_grenze_entsteht_keine_position`
  (seit `f9734a2` vom 16.09. vorhanden, Plan berührt `risikovorfilter.py` nicht).
- [x] **Bedingung 4:** `python spiegelstand.py`
  Der Umbau fasst keinen Journal- oder Zustandsschreibpfad an — der Lauf ist der
  Nachweis, nicht die Behauptung. Erwartet: derselbe Befund wie vor dem Plan.
  **Beleg 19.09.2026:** 24/24 byte-gleich (scanner zeigte einmal kurz ABWEICHUNG
  direkt nach der Volle-Suite — bekannter Testeffekt, heilte im nächsten Zyklus).
- [x] **Bericht von Hand:** `python tagesbericht.py --ohne-xperp`, dann
  `python -c "import lage, schnappschuss; schnappschuss.schreibe(schnappschuss.baue(lage.erhebe(mit_xperp=False)))"`,
  dann die Datei in `stand/` auf das gestrige Datum umbenennen und den Bericht
  erneut bauen. Der zweite Lauf muss die Zeile „Kein Stand von gestern"
  verlieren und mindestens eine Differenzzeile zeigen.
  **Beleg 19.09.2026:** zweiter Lauf ohne „Kein Stand von gestern", Differenzzeile
  „seit gestern: neu: HYPE-USDC" vorhanden; echter Vortag danach wiederhergestellt.
- [x] **Keine Laufzeitdaten im Index:** `git status --short` nennt keine Datei
  unter `stand/`.
  **Beleg 19.09.2026:** `git status --short | grep stand/` leer; `stand/` ist
  über `.gitignore:77` gesperrt.

## Was dieser Plan ausdrücklich nicht anfasst

- **Die Kostenformeln.** Zeigt der Guthabenabgleich einen Rest, ist das ein
  Befund für eine eigene Runde, keine Korrektur in diesem Plan.
- Die Punkte aus `BEFUND-hygiene-2026-09-17.md` (CI, `xperp`-Doppelwahrheiten,
  die drei englischen Review-Dokumente, der `test_risikovorfilter`-Fehler).
- Die leeren Spuren **reparieren**. Der Plan macht sichtbar, dass `supertrend`,
  `moondev_funding` und `iv_wand` kein Buch führen; warum, gehört zu Thema 2.
- Themen 2 und 1 — Betrieb/Überwachung und die neue Spur.
