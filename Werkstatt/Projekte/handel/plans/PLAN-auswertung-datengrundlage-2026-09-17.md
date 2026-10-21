# Auswertung: Datengrundlage — Umsetzungsplan

> **Für agentische Arbeiter:** ERFORDERLICHE SUB-SKILL: `superpowers:subagent-driven-development`
> (empfohlen) oder `superpowers:executing-plans`, um diesen Plan Aufgabe für
> Aufgabe umzusetzen. Die Schritte nutzen Checkbox-Syntax (`- [ ]`).

**Ziel:** Die Auswertung bekommt eine Zeitachse, eine ehrliche Kategorie für
Spuren ohne Buch und eine Gesamtbilanz, die Währungen und Papier/Live nicht
vermischt.

**Architektur:** Die Journale bleiben die einzige Wahrheit. Das Zeitfenster wird
in den beiden bestehenden Lesefunktionen (`auswertung_alle.zeilen()`,
`buchauswertung.lade_zeilen()`) als Filter über die Spalte `zeit` eingezogen —
keine neue Datei, kein neues Artefakt. Die fünf Spuren mit eigener
`auswertung.py` bekommen eine gemeinsame Mindestrückgabe, damit sie summierbar
werden. Die Kostenformeln werden nicht angefasst.

**Tech-Stack:** Python 3, Standardbibliothek (`csv`, `json`, `datetime`,
`argparse`), Testrahmen `unittest`. Kein `pytest` — es steht nicht in
`requirements.txt`.

**Spec:** `ENTWURF-auswertung-berichte-2026-09-17.md` (Abschnitte „Zeitachse,
Gesamtbilanz, leere Spuren" sowie „Prüfung")

**Nicht in diesem Plan:** `lage.py`, der Schnappschuss, der Vortagsvergleich,
der Umbau von `tagesbericht.py`, der Wochenbericht und der Guthabenabgleich.
Die stehen im zweiten Plan (Berichtsschicht), der erst nach diesem geschrieben
wird. Dieser Plan ist für sich lauffähig: nach Aufgabe 6 liefert
`python auswertung_alle.py --tage 30` eine vollständige, ehrliche Auswertung
auf der Konsole.

## Globale Vorgaben

- **Arbeitsverzeichnis:** `C:\Users\faupe\Documents\BrainFiles\Agenten\Handel`
- **Zahlen gehören in `wachen.json`, nicht in den Code** (Hausregel aus
  `AGENTS.md`). Neue Schwellen werden nicht als Konstante angelegt.
- **Niemals lesen oder durchsuchen:** `OpenAlice/`, `.venv/`, `scanner/.venv/`,
  `nautilus/.venv/`, `__pycache__/`, `daten/`, `kerzen_*.json`, `README.md`.
- **Testrahmen ist `unittest`**, Tests liegen unter `tests/`, Dateiname
  `test_*.py`, ausführbar per `python tests/test_<name>.py`.
- **Kein Test schreibt in ein echtes Ziel.** Gearbeitet wird in einem
  Temp-Ordner über die Modulvariable `HIER` (Muster: `tests/test_backtest_urteile.py`).
  `journal_zweitziel` wird in diesem Plan nirgends berührt.
- **Kostenformeln sind tabu.** Keine Zahl in `buchauswertung.py` oder
  `auswertung_alle.py`, die eine Gebühr, Slippage oder Funding beschreibt, wird
  geändert.
- **Zeitformat der Journale:** Spalte `zeit`, ISO-8601 mit Offset `+00:00`
  (UTC-aware). Einzige Ausnahme: `orbk` führt nur ein Datum (`2026-09-13`) ohne
  Uhrzeit und ohne Zone.
- **Live-Merker:** `handel_erlaubt` in der `wachen.json` der Spur. Heute steht
  er nur bei `scanner` auf `true`.
- **Rückwärtskompatibilität:** Jeder neue Parameter hat einen Vorgabewert, der
  das heutige Verhalten unverändert lässt. Ein Aufruf ohne Zeitfenster muss
  dieselbe Ausgabe liefern wie vor dem Umbau.
- **Commit-Nachrichten** enden mit:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## Dateiübersicht

| Datei | Zuständigkeit | Art |
|---|---|---|
| `zeitfenster.py` | Zeitstempel parsen, Fenster berechnen, Zeilen filtern — die eine Stelle, an der das Format der Journale interpretiert wird | **neu** |
| `auswertung_alle.py` | Zuordnung Spur → Rechenweg, Übersicht, Kommandozeile | ändern |
| `buchauswertung.py` | gemeinsame Mechanik der Papierbücher | ändern |
| `gesamtbilanz.py` | Summe über alle Bücher, getrennt nach Währung und Papier/Live | **neu** |
| `spiegel/auswertung.py`, `omniquant/auswertung.py`, `kopier/auswertung.py`, `kopier1zu1/auswertung.py`, `gitter/auswertung.py` | je eine Funktion `kennzahlen_kurz()` ergänzen | ändern |
| `tests/test_zeitfenster.py` | Parsen, Filtern, `orbk`-Sonderfall | **neu** |
| `tests/test_auswertung_fenster.py` | `MIN_RUNDEN` je Fenster, Kategorien | **neu** |
| `tests/test_gesamtbilanz.py` | Währungstrennung, Papier/Live-Trennung | **neu** |

Begründung für `zeitfenster.py` als eigene Datei: das Journalformat wird sonst
an zwei Stellen interpretiert (`auswertung_alle.zeilen()` und
`buchauswertung.lade_zeilen()`), und der `orbk`-Sonderfall wäre damit zweimal
da. Der Entwurf nennt „zwei Formeln für dieselbe Frage laufen auseinander" als
Leitmotiv — das gilt hier genauso.

---

### Aufgabe 1: Zeitfenster-Modul

**Dateien:**
- Anlegen: `zeitfenster.py`
- Test: `tests/test_zeitfenster.py`

**Schnittstellen:**
- Verbraucht: nichts
- Liefert:
  - `parse(wert)` → `datetime` (UTC-aware) oder `None`
  - `fenster(tage=None, seit=None, bis=None)` → `(von, bis)` als
    UTC-aware `datetime` oder `(None, None)`
  - `im_fenster(zeile, von, bis, spalte="zeit")` → `bool`

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

`tests/test_zeitfenster.py`:

```python
"""Tests fuer das Zeitfenster der Auswertung.

Geprueft wird das, was still schiefgehen kann: ein Journal mit Offset gegen
eines ohne Uhrzeit (orbk), und die Regel, dass ein leeres Fenster ALLES
durchlaesst statt NICHTS - sonst liest ein Aufruf ohne --tage ein leeres Buch.
"""

import datetime as dt
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import zeitfenster as zf                                       # noqa: E402


class TestParse(unittest.TestCase):

    def test_iso_mit_offset(self):
        d = zf.parse("2026-09-14T15:01:34+00:00")
        self.assertEqual(d, dt.datetime(2026, 9, 14, 15, 1, 34,
                                        tzinfo=dt.timezone.utc))

    def test_nur_datum_wird_tagesbeginn_utc(self):
        # orbk fuehrt nur ein Datum. Tagesbeginn ist die einzige Lesart, die
        # ein Tagesfenster nicht um einen Tag verschiebt.
        d = zf.parse("2026-09-13")
        self.assertEqual(d, dt.datetime(2026, 9, 13, 0, 0, 0,
                                        tzinfo=dt.timezone.utc))

    def test_muell_ist_none(self):
        self.assertIsNone(zf.parse(""))
        self.assertIsNone(zf.parse("gestern"))
        self.assertIsNone(zf.parse(None))

    def test_naiver_zeitstempel_gilt_als_utc(self):
        # Kein Journal schreibt heute naiv. Faellt eines doch so aus, ist
        # "als UTC lesen" die Lesart, die zum Rest des Baums passt - ein
        # TypeError beim Vergleich waere der schlechtere Ausgang.
        d = zf.parse("2026-09-14T15:01:34")
        self.assertEqual(d.tzinfo, dt.timezone.utc)


class TestFenster(unittest.TestCase):

    def test_ohne_angabe_offen(self):
        self.assertEqual(zf.fenster(), (None, None))

    def test_tage_zaehlt_rueckwaerts(self):
        von, bis = zf.fenster(tage=30)
        self.assertIsNotNone(von)
        self.assertIsNone(bis)
        self.assertAlmostEqual((zf.jetzt() - von).days, 30, delta=1)

    def test_seit_und_bis_als_datum(self):
        von, bis = zf.fenster(seit="2026-09-01", bis="2026-09-30")
        self.assertEqual(von.date(), dt.date(2026, 9, 1))
        self.assertEqual(bis.date(), dt.date(2026, 9, 30))

    def test_tage_und_seit_zusammen_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            zf.fenster(tage=30, seit="2026-09-01")


class TestImFenster(unittest.TestCase):

    def setUp(self):
        self.von = dt.datetime(2026, 9, 10, tzinfo=dt.timezone.utc)
        self.bis = dt.datetime(2026, 9, 20, tzinfo=dt.timezone.utc)

    def test_offenes_fenster_laesst_alles_durch(self):
        self.assertTrue(zf.im_fenster({"zeit": "2020-01-01T00:00:00+00:00"},
                                      None, None))

    def test_drin_und_draussen(self):
        self.assertTrue(zf.im_fenster({"zeit": "2026-09-15T12:00:00+00:00"},
                                      self.von, self.bis))
        self.assertFalse(zf.im_fenster({"zeit": "2026-09-01T12:00:00+00:00"},
                                       self.von, self.bis))
        self.assertFalse(zf.im_fenster({"zeit": "2026-09-25T12:00:00+00:00"},
                                       self.von, self.bis))

    def test_unlesbare_zeit_faellt_raus(self):
        # Eine Zeile ohne lesbare Zeit ist im Fenster nicht belegbar. Sie
        # durchzulassen hiesse, sie jedem Fenster zuzuschlagen.
        self.assertFalse(zf.im_fenster({"zeit": ""}, self.von, self.bis))

    def test_unlesbare_zeit_bleibt_bei_offenem_fenster(self):
        self.assertTrue(zf.im_fenster({"zeit": ""}, None, None))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag bestätigen**

```bash
python tests/test_zeitfenster.py -v
```

Erwartet: `ModuleNotFoundError: No module named 'zeitfenster'`

- [ ] **Schritt 3: Die minimale Umsetzung schreiben**

`zeitfenster.py`:

```python
"""Das Zeitfenster der Auswertung - an EINER Stelle.

Warum es diese Datei gibt: das Journalformat wird sonst zweimal gelesen
(auswertung_alle.zeilen und buchauswertung.lade_zeilen), und der orbk-
Sonderfall (nur Datum, keine Uhrzeit, keine Zone) waere zweimal da. Zwei
Lesarten desselben Zeitstempels laufen auseinander.

Alle Journale ausser orbk schreiben ISO-8601 mit Offset +00:00. Hier wird
alles auf UTC-aware normalisiert - naive Zeitstempel gelten als UTC, weil
das zum Rest des Spurenbaums passt.
"""

import datetime as dt

UTC = dt.timezone.utc


def jetzt():
    """Der aktuelle Zeitpunkt, UTC-aware. Eigene Funktion, damit Tests ihn
    ersetzen koennen, ohne datetime zu patchen."""
    return dt.datetime.now(UTC)


def parse(wert):
    """Ein Journalfeld als UTC-aware datetime, oder None.

    Zwei Formen kommen vor: ISO mit Offset (der Normalfall) und ein blosses
    Datum (orbk). Das Datum wird als Tagesbeginn UTC gelesen - jede andere
    Lesart verschiebt ein Tagesfenster um einen Tag.
    """
    if not wert:
        return None
    s = str(wert).strip()
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)


def _rand(wert, ende=False):
    """Eine Kommandozeilenangabe als Fenstergrenze."""
    d = parse(wert)
    if d is None:
        raise ValueError("Zeitangabe nicht lesbar: %r" % (wert,))
    if ende and len(str(wert).strip()) == 10:
        # Ein blosses Enddatum meint den ganzen Tag, nicht seinen Beginn.
        d = d + dt.timedelta(days=1) - dt.timedelta(microseconds=1)
    return d


def fenster(tage=None, seit=None, bis=None):
    """Die Grenzen eines Fensters. (None, None) heisst: alles.

    tage und seit schliessen sich aus - zwei Angaben fuer denselben Anfang
    waeren eine stille Vorrangregel.
    """
    if tage is not None and seit is not None:
        raise ValueError("tage und seit zusammen sind nicht eindeutig")
    if tage is not None:
        return (jetzt() - dt.timedelta(days=int(tage)),
                _rand(bis, ende=True) if bis else None)
    return (_rand(seit) if seit else None,
            _rand(bis, ende=True) if bis else None)


def im_fenster(zeile, von, bis, spalte="zeit"):
    """Liegt die Zeile im Fenster?

    Bei offenem Fenster (von und bis None) ist die Antwort immer ja - auch
    fuer eine Zeile ohne lesbare Zeit. Sonst faellt sie raus: ihre
    Zugehoerigkeit ist nicht belegbar, und sie jedem Fenster zuzuschlagen
    waere die unehrlichere Wahl.
    """
    if von is None and bis is None:
        return True
    d = parse(zeile.get(spalte))
    if d is None:
        return False
    if von is not None and d < von:
        return False
    if bis is not None and d > bis:
        return False
    return True
```

- [ ] **Schritt 4: Test laufen lassen, Erfolg bestätigen**

```bash
python tests/test_zeitfenster.py -v
```

Erwartet: alle Tests PASS.

- [ ] **Schritt 5: Committen**

```bash
git add zeitfenster.py tests/test_zeitfenster.py
git commit -m "feat(auswertung): Zeitfenster-Modul mit orbk-Sonderfall"
```

---

### Aufgabe 2: Zeitfenster in `auswertung_alle.py`

**Dateien:**
- Ändern: `auswertung_alle.py` (`zeilen()` Z. 129-141, `kennzahlen_fuer()` Z. 68-107, `main()` Z. 385-434)
- Test: `tests/test_auswertung_fenster.py`

**Schnittstellen:**
- Verbraucht: `zeitfenster.fenster()`, `zeitfenster.im_fenster()` aus Aufgabe 1
- Liefert:
  - `zeilen(spur, datei="handelsjournal.csv", von=None, bis=None)` → `list[dict]`
  - `kennzahlen_fuer(spur, von=None, bis=None)` → `dict` oder `None`
  - Kommandozeile: `--tage N`, `--seit JJJJ-MM-TT`, `--bis JJJJ-MM-TT`

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

`tests/test_auswertung_fenster.py`:

```python
"""Tests fuer das Zeitfenster in der Spurenauswertung.

Zwei Dinge, die still schiefgehen: ein Aufruf OHNE Fenster muss dieselbe
Zahl liefern wie vor dem Umbau (sonst aendert der Umbau die Buecher), und
MIN_RUNDEN muss JE FENSTER greifen (sonst behauptet ein Monat mit drei
Runden eine Trefferquote).

Gearbeitet wird auf erfundenen Journalen in einem Temp-Ordner.
"""

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import auswertung_alle as aa                                   # noqa: E402

# Das Format, das runden_indikator ueber _paare wirklich liest: die Spalte
# `inst` gruppiert die Runden, und `einsatz_usd` traegt beim Kauf den Einsatz
# und beim Verkauf den Erloes - derselbe Feldname, zwei Bedeutungen
# (auswertung_alle.py:285 und :223). Ohne `inst` baut _paare keine Runde.
KOPF = "zeit,aktion,inst,einsatz_usd,grund\n"

# Eine Runde im August (+10), eine im September (-10).
JOURNAL = KOPF + (
    "2026-08-01T10:00:00+00:00,kauf,BTC,100,einstieg\n"
    "2026-08-02T10:00:00+00:00,verkauf,BTC,110,ziel\n"
    "2026-09-10T10:00:00+00:00,kauf,BTC,100,einstieg\n"
    "2026-09-11T10:00:00+00:00,verkauf,BTC,90,stop\n"
)


class TestFensterInZeilen(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wurzel = Path(self.tmp.name)
        (wurzel / "squeeze").mkdir()
        (wurzel / "squeeze" / "handelsjournal.csv").write_text(
            JOURNAL, encoding="utf-8")
        self._alt = aa.HIER
        aa.HIER = wurzel

    def tearDown(self):
        aa.HIER = self._alt
        self.tmp.cleanup()

    def test_ohne_fenster_alle_zeilen(self):
        self.assertEqual(len(aa.zeilen("squeeze")), 4)

    def test_fenster_schneidet(self):
        von = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
        self.assertEqual(len(aa.zeilen("squeeze", von=von, bis=None)), 2)

    def test_fenster_ohne_treffer_ist_leer_nicht_fehler(self):
        von = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)
        self.assertEqual(aa.zeilen("squeeze", von=von, bis=None), [])

    def test_kennzahlen_ohne_zeilen_sind_none(self):
        von = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)
        self.assertIsNone(aa.kennzahlen_fuer("squeeze", von=von, bis=None))


class TestMinRundenJeFenster(unittest.TestCase):

    def test_wenige_runden_gelten_als_nicht_belastbar(self):
        # Zwei Runden liegen unter MIN_RUNDEN. Die Kennzahlen duerfen
        # entstehen, aber die Belastbarkeit muss falsch sein.
        k = aa.kennzahlen([{"ergebnis": 10.0, "einsatz": 100.0, "grund": "ziel"},
                           {"ergebnis": -10.0, "einsatz": 100.0, "grund": "stop"}], "USD")
        self.assertFalse(aa.belastbar(k))

    def test_genug_runden_sind_belastbar(self):
        runden = [{"ergebnis": 1.0, "einsatz": 100.0, "grund": "ziel"}] * aa.MIN_RUNDEN
        self.assertTrue(aa.belastbar(aa.kennzahlen(runden, "USD")))

    def test_keine_kennzahlen_sind_nicht_belastbar(self):
        self.assertFalse(aa.belastbar(None))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag bestätigen**

```bash
python tests/test_auswertung_fenster.py -v
```

Erwartet: FAIL — `zeilen()` kennt `von`/`bis` nicht, `belastbar` existiert nicht.

- [ ] **Schritt 3: Die minimale Umsetzung schreiben**

In `auswertung_alle.py` den Import ergänzen (zu den übrigen Modulimporten):

```python
import zeitfenster
```

`zeilen()` (Z. 129-141) ersetzen durch:

```python
def zeilen(spur, datei="handelsjournal.csv", von=None, bis=None):
    """Die Journalzeilen einer Spur, wahlweise auf ein Fenster beschraenkt.

    von/bis mit Vorgabe None: ohne Angabe bleibt alles wie vorher.
    """
    if STUFE:
        # Risikostufe: dieselbe Auswertung auf den Dateien der Stufe
        # (handelsjournal.mittel.csv). Der Rechenweg bleibt derselbe - die
        # Betraege sind groesser, die Regeln nicht anders.
        datei = risikostufe.datei_fuer(datei, STUFE)
    p = HIER / spur / datei
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f)
                if zeitfenster.im_fenster(r, von, bis)]
```

In `kennzahlen_fuer()` (Z. 68) die Signatur und den ersten Aufruf ändern:

```python
def kennzahlen_fuer(spur, von=None, bis=None):
    ...
    z = zeilen(spur, von=von, bis=bis)
```

Neu, direkt hinter `kennzahlen_fuer()`:

```python
def belastbar(k, min_runden=None):
    """Sagt die Spur im gewaehlten Fenster ueberhaupt etwas?

    Die Schwelle gilt JE FENSTER. Ein Monat mit drei Runden ist keine
    Aussage, auch wenn die Spur insgesamt fuenfzig hat - sonst erzeugt die
    Zeitachse genau die Scheingenauigkeit, die MIN_RUNDEN verhindern soll.
    """
    if not k:
        return False
    return k.get("n", 0) >= (MIN_RUNDEN if min_runden is None else min_runden)
```

In `main()` die Argumente ergänzen (hinter `--min`):

```python
    p.add_argument("--tage", type=int,
                   help="nur die letzten N Tage auswerten")
    p.add_argument("--seit", help="Fensteranfang, JJJJ-MM-TT")
    p.add_argument("--bis", help="Fensterende, JJJJ-MM-TT (einschliesslich)")
```

und direkt hinter `a = p.parse_args()`:

```python
    try:
        von, bis = zeitfenster.fenster(tage=a.tage, seit=a.seit, bis=a.bis)
    except ValueError as e:
        p.error(str(e))
    if von or bis:
        print("Fenster: %s bis %s\n"
              % (von.date() if von else "Anfang",
                 bis.date() if bis else "heute"))
```

und den Aufruf in der Schleife:

```python
        k = kennzahlen_fuer(spur, von=von, bis=bis)
```

- [ ] **Schritt 4: Tests laufen lassen, Erfolg bestätigen**

```bash
python tests/test_auswertung_fenster.py -v
```

Erwartet: alle PASS.

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Erwartet: kein neuer Fehlschlag gegenüber dem Stand vor der Änderung.

- [ ] **Schritt 5: Unverändertheit ohne Fenster nachweisen**

```bash
python auswertung_alle.py > /tmp/nachher.txt 2>&1; git stash; python auswertung_alle.py > /tmp/vorher.txt 2>&1; git stash pop; diff /tmp/vorher.txt /tmp/nachher.txt
```

Erwartet: kein Unterschied. Findet sich einer, ist der Umbau nicht
rückwärtskompatibel und muss korrigiert werden, bevor es weitergeht.

- [ ] **Schritt 6: Committen**

```bash
git add auswertung_alle.py tests/test_auswertung_fenster.py
git commit -m "feat(auswertung): --tage/--seit/--bis, MIN_RUNDEN je Fenster"
```

---

### Aufgabe 3: Zeitfenster in `buchauswertung.py`

**Dateien:**
- Ändern: `buchauswertung.py` (`lade_zeilen()` Z. 88-145)
- Test: `tests/test_buchauswertung.py` (vorhanden, wird ergänzt)

**Schnittstellen:**
- Verbraucht: `zeitfenster.im_fenster()` aus Aufgabe 1
- Liefert: `lade_zeilen(pfad, aktionen, extra=(), mit_kosten=False, name=None, von=None, bis=None)`

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

An `tests/test_buchauswertung.py` anhängen:

```python
class TestLadeZeilenFenster(unittest.TestCase):
    """Das Fenster in der gemeinsamen Mechanik der Papierbuecher."""

    KOPF = "zeit,aktion,einsatz_usd,wert_usd\n"
    ZEILEN = (
        "2026-08-01T10:00:00+00:00,verkauf,100,110\n"
        "2026-09-10T10:00:00+00:00,verkauf,100,90\n"
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = Path(self.tmp.name) / "handelsjournal.csv"
        self.pfad.write_text(self.KOPF + self.ZEILEN, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ohne_fenster_alle(self):
        aus = ba.lade_zeilen(str(self.pfad), ("verkauf",))
        self.assertEqual(len(aus), 2)

    def test_mit_fenster_geschnitten(self):
        von = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
        aus = ba.lade_zeilen(str(self.pfad), ("verkauf",), von=von)
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["wert"], 90.0)
```

Falls `datetime`, `tempfile` oder `Path` in der Datei noch nicht importiert
sind, die Importe oben ergänzen: `import datetime as dt`, `import tempfile`,
`from pathlib import Path`.

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag bestätigen**

```bash
python tests/test_buchauswertung.py -v
```

Erwartet: FAIL — `lade_zeilen() got an unexpected keyword argument 'von'`

- [ ] **Schritt 3: Die minimale Umsetzung schreiben**

In `buchauswertung.py` oben `import zeitfenster` ergänzen. Signatur (Z. 88):

```python
def lade_zeilen(pfad, aktionen, extra=(), mit_kosten=False, name=None,
                von=None, bis=None):
```

Im Docstring hinter dem Absatz zu `name` ergänzen:

```
    von/bis: Zeitfenster ueber die Spalte `zeit`. Vorgabe None/None heisst
    alles - ein Aufruf ohne Fenster liest dasselbe wie vorher.
```

In der Leseschleife, direkt nach `for zeile in csv.DictReader(f):` als
erste Prüfung:

```python
            if not zeitfenster.im_fenster(zeile, von, bis):
                continue
```

- [ ] **Schritt 4: Test laufen lassen, Erfolg bestätigen**

```bash
python tests/test_buchauswertung.py -v
```

Erwartet: alle PASS, auch die vorher schon vorhandenen.

- [ ] **Schritt 5: Committen**

```bash
git add buchauswertung.py tests/test_buchauswertung.py
git commit -m "feat(buchauswertung): Zeitfenster in lade_zeilen"
```

---

### Aufgabe 4: Die Kategorie „kein Buch"

**Dateien:**
- Ändern: `auswertung_alle.py` (Übersicht ab Z. 417)
- Test: `tests/test_auswertung_fenster.py` (aus Aufgabe 2, wird ergänzt)

**Schnittstellen:**
- Verbraucht: `belastbar()` aus Aufgabe 2
- Liefert: `lage_der_spur(spur, k)` → `"belastbar"` | `"zu wenige Runden"` |
  `"kein Buch"`, `hat_buch(spur)` → `bool`, und `buch_seit(spur)` → `date`
  oder `None`
- Die Übersicht kennt eine vierte Anzeige, die nicht aus `lage_der_spur()`
  kommt: ein vorhandenes Buch ohne jede geschlossene Runde (`k is None`).
  Es wird als „keine geschlossene Runde" ausgewiesen, damit es nicht wie
  „kein Buch" aussieht.

**Warum:** `supertrend`, `moondev_funding` und `iv_wand` stehen in `SPUREN`,
führen aber kein Journal. Sie liefern heute einen Strich, der wie „keine
Trades" aussieht und „kein Buch" heißt. Eine Spur, die seit Wochen läuft und
kein Journal hat, ist ein Betriebsfehler.

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

An `tests/test_auswertung_fenster.py` anhängen:

```python
class TestLage(unittest.TestCase):
    """Drei Kategorien statt zwei - und ein Strich heisst nicht mehr
    zweierlei."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.tmp.name)
        # Eine Spur mit Buch, eine ohne - beide mit Zustand, wie im Baum.
        for spur in ("squeeze", "supertrend"):
            (self.wurzel / spur).mkdir()
            (self.wurzel / spur / "zustand.json").write_text(
                "{}", encoding="utf-8")
        (self.wurzel / "squeeze" / "handelsjournal.csv").write_text(
            JOURNAL, encoding="utf-8")
        self._alt = aa.HIER
        aa.HIER = self.wurzel

    def tearDown(self):
        aa.HIER = self._alt
        self.tmp.cleanup()

    def test_ohne_journal_heisst_kein_buch(self):
        self.assertEqual(aa.lage_der_spur("supertrend", None), "kein Buch")

    def test_mit_journal_aber_wenig_runden(self):
        k = aa.kennzahlen_fuer("squeeze")
        self.assertEqual(aa.lage_der_spur("squeeze", k), "zu wenige Runden")

    def test_mit_genug_runden_belastbar(self):
        k = aa.kennzahlen([{"ergebnis": 1.0, "einsatz": 100.0, "grund": "ziel"}] * aa.MIN_RUNDEN,
                          "USD")
        self.assertEqual(aa.lage_der_spur("squeeze", k), "belastbar")

    def test_buch_seit_nennt_den_zustand(self):
        # Ohne Journal ist der Zustand die einzige Spur davon, dass die
        # Spur ueberhaupt laeuft.
        self.assertIsNotNone(aa.buch_seit("supertrend"))
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag bestätigen**

```bash
python tests/test_auswertung_fenster.py -v
```

Erwartet: FAIL — `module 'auswertung_alle' has no attribute 'lage_der_spur'`

- [ ] **Schritt 3: Die minimale Umsetzung schreiben**

In `auswertung_alle.py`, hinter `belastbar()`:

```python
def hat_buch(spur, datei="handelsjournal.csv"):
    """Fuehrt die Spur ueberhaupt ein Journal?

    Getrennt von "hat Runden": eine Spur ohne Datei und eine Spur mit leerer
    Datei sind verschiedene Befunde, und nur der erste ist ein
    Betriebsfehler.
    """
    if STUFE:
        datei = risikostufe.datei_fuer(datei, STUFE)
    return (HIER / spur / datei).exists()


def buch_seit(spur):
    """Seit wann die Spur laeuft, soweit der Baum es hergibt.

    Quelle ist die Aenderungszeit von `zustand.json` - ohne Journal gibt es
    keine andere. Das ist ein Anhaltspunkt, keine Anmeldung: die Datei wird
    bei jedem Lauf angefasst. Sie beantwortet trotzdem die Frage, auf die es
    ankommt - laeuft die Spur, obwohl sie nichts schreibt?
    """
    p = HIER / spur / "zustand.json"
    if not p.exists():
        return None
    return datetime.fromtimestamp(p.stat().st_mtime).date()


def lage_der_spur(spur, k):
    """Eine von drei Kategorien - nie ein blosser Strich."""
    if not hat_buch(spur):
        return "kein Buch"
    if not belastbar(k):
        return "zu wenige Runden"
    return "belastbar"
```

`datetime` ist in `auswertung_alle.py:32` bereits importiert
(`from datetime import datetime`) — kein neuer Import nötig.

Die Übersicht ab Z. 417 ersetzen durch:

```python
    print("\n=== Uebersicht ===")
    print("  %-10s %6s %8s %10s %8s  %s"
          % ("Spur", "Runden", "Treffer", "Ergebnis", "Treffer %", "Lage"))
    ohne_buch = []
    for spur, k in zahlen.items():
        lage = lage_der_spur(spur, k)
        if lage == "kein Buch":
            ohne_buch.append(spur)
            print("  %-10s %6s %8s %10s %8s  kein Buch"
                  % (spur, "-", "-", "-", "-"))
            continue
        if k is None:
            # Buch vorhanden, aber keine geschlossene Runde darin. Das ist
            # ein dritter Zustand und darf nicht wie "kein Buch" aussehen.
            print("  %-10s %6d %8s %10s %8s  keine geschlossene Runde"
                  % (spur, 0, "-", "-", "-"))
            continue
        print("  %-10s %6d %8d %10.2f %7.0f %%  %s"
              % (spur, k["n"], k["treffer"], k["ergebnis"],
                 k["treffer_pct"], lage))
    if ohne_buch:
        print("\n  KEIN BUCH - diese Spuren schreiben kein Journal:")
        for spur in ohne_buch:
            seit = buch_seit(spur)
            print("    %-10s Zustand zuletzt %s"
                  % (spur, seit.isoformat() if seit else "nie"))
        print("  Eine laufende Spur ohne Journal ist ein Betriebsfehler, "
              "keine Formatfrage.")
    print("\n  spiegel, omniquant und gitter haben eigene Auswertungen "
          "(auswertung.py im jeweiligen Ordner).")
```

Die Zeile mit `if STUFE:` am Ende von `main()` bleibt unverändert stehen.

- [ ] **Schritt 4: Tests laufen lassen, Erfolg bestätigen**

```bash
python tests/test_auswertung_fenster.py -v
```

Erwartet: alle PASS.

- [ ] **Schritt 5: Am echten Baum ansehen**

```bash
python auswertung_alle.py
```

Erwartet: `supertrend`, `moondev_funding` und `iv_wand` stehen unter „KEIN
BUCH" mit einem Datum. Das ist der Befund, den der Entwurf vorhergesagt hat.

- [ ] **Schritt 6: Committen**

```bash
git add auswertung_alle.py tests/test_auswertung_fenster.py
git commit -m "feat(auswertung): Kategorie 'kein Buch' statt stummem Strich"
```

---

### Aufgabe 5: Gemeinsame Mindestform der fünf Einzelauswertungen

**Dateien:**
- Ändern: `spiegel/auswertung.py`, `omniquant/auswertung.py`,
  `kopier/auswertung.py`, `kopier1zu1/auswertung.py`, `gitter/auswertung.py`
- Test: `tests/test_kennzahlen_kurz.py` (neu)

**Schnittstellen:**
- Verbraucht: `buchauswertung.lade_zeilen(..., von=, bis=)` aus Aufgabe 3
- Liefert: in jedem der fünf Module
  `kennzahlen_kurz(von=None, bis=None)` →
  `{"n": int, "ergebnis": float, "treffer": int, "waehrung": str, "live": bool}`
  oder `None`
- Und, in jedem der fünf Module, `lade_ausstiege(pfad=JOURNAL, von=None,
  bis=None)` — die Durchreichung des Fensters bis in `lade_zeilen`. Ohne sie
  lieferten diese fünf Spuren bei `--tage 30` stumm ihre Zahlen seit Anfang,
  während alle anderen das Fenster beachten: genau die stille Falschzahl, die
  der Entwurf verhindern soll.

**Warum:** Diese fünf Spuren tauchen in keiner Übersicht auf, weil jede eine
eigene Rückgabeform hat. Die Kostenformeln bleiben unberührt — nur die
Rückgabe kommt hinzu.

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

`tests/test_kennzahlen_kurz.py`:

```python
"""Die fuenf Spuren mit eigener Auswertung muessen summierbar werden.

Geprueft wird nicht die RECHNUNG - die bleibt, wie sie ist - sondern die
FORM: fuenf Module, eine Rueckgabe, damit die Gesamtbilanz sie addieren
kann, ohne fuenf Sonderfaelle zu kennen.
"""

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

MODULE = ("spiegel.auswertung", "omniquant.auswertung", "kopier.auswertung",
          "kopier1zu1.auswertung", "gitter.auswertung")

PFLICHTFELDER = ("n", "ergebnis", "treffer", "waehrung", "live")


class TestMindestform(unittest.TestCase):

    def test_jedes_modul_hat_kennzahlen_kurz(self):
        import importlib
        for name in MODULE:
            with self.subTest(modul=name):
                m = importlib.import_module(name)
                self.assertTrue(hasattr(m, "kennzahlen_kurz"),
                                "%s fehlt kennzahlen_kurz()" % name)

    def test_rueckgabe_ist_none_oder_vollstaendig(self):
        import importlib
        for name in MODULE:
            with self.subTest(modul=name):
                k = importlib.import_module(name).kennzahlen_kurz()
                if k is None:
                    continue
                for feld in PFLICHTFELDER:
                    self.assertIn(feld, k, "%s: %s fehlt" % (name, feld))
                self.assertIsInstance(k["waehrung"], str)
                self.assertIsInstance(k["live"], bool)

    def test_fenster_wird_angenommen_und_schneidet(self):
        # Ein Fenster in der Zukunft darf nichts mehr enthalten. Wuerde das
        # Fenster nur entgegengenommen und nicht durchgereicht, kaeme hier
        # weiter die Zahl seit Anfang - die stille Falschzahl.
        import datetime as dt
        import importlib
        kuenftig = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)
        for name in MODULE:
            with self.subTest(modul=name):
                m = importlib.import_module(name)
                self.assertIsNone(m.kennzahlen_kurz(von=kuenftig))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag bestätigen**

```bash
python tests/test_kennzahlen_kurz.py -v
```

Erwartet: FAIL — `kennzahlen_kurz()` fehlt in allen fünf Modulen.

- [ ] **Schritt 3: Die minimale Umsetzung schreiben**

Alle fünf Module haben denselben inneren Aufbau — `lade_ausstiege(pfad=JOURNAL)`,
`_kosten(pfad=WACHEN)` und `kennzahlen(aus, k)`, das an
`buchauswertung.kennzahlen()` durchreicht. Deshalb ist der Zusatz in allen
fünf Dateien **wörtlich derselbe**. Ans Ende jeder der fünf Dateien, vor
`def main():`, einfügen:

```python
def kennzahlen_kurz(von=None, bis=None):
    """Die Mindestform fuer die Gesamtbilanz - vier Zahlen und ein Merker.

    Angelegt, damit gesamtbilanz.py die fuenf Spuren mit eigener Auswertung
    addieren kann, ohne fuenf Sonderfaelle zu kennen. Die RECHNUNG ist
    unveraendert die dieses Moduls - hier steht nur die Uebergabe.
    `gv_usd` heisst hier `ergebnis`, weil auswertung_alle.kennzahlen() das
    Feld so nennt und die Bilanz nur EINEN Namen kennen soll.

    None heisst: diese Spur hat nichts auszusagen (kein Buch, keine
    geschlossenen Ausstiege).
    """
    import json

    k = kennzahlen(lade_ausstiege(von=von, bis=bis), _kosten())
    if not k.get("n"):
        return None
    live = False
    try:
        live = bool(json.loads(
            Path(WACHEN).read_text("utf-8")).get("handel_erlaubt"))
    except (OSError, ValueError, TypeError):
        # Keine wachen.json, kaputtes JSON: dann gilt Papier. Eine Spur
        # faelschlich als Live zu zaehlen waere der teurere Irrtum.
        live = False
    return {"n": k["n"],
            "ergebnis": k["gv_usd"],
            "treffer": k["treffer"],
            "waehrung": "USD",
            "live": live}
```

Und in jedem der fünf Module `lade_ausstiege` um das Fenster erweitern —
die Signatur und der eine `b.lade_zeilen`-Aufruf darin, sonst nichts:

```python
def lade_ausstiege(pfad=JOURNAL, von=None, bis=None):
    ...
    aus = b.lade_zeilen(pfad, ACTIONEN, extra=EXTRA, mit_kosten=True,
                        von=von, bis=bis)
```

Der Rest des Rumpfs bleibt unberührt — in `spiegel`, `kopier` und `kopier1zu1`
folgt danach die Marktkapitalisierung, die mit dem Fenster nichts zu tun hat.
Die übrigen Argumente von `b.lade_zeilen` unterscheiden sich je Modul
(`ACTIONEN`, `EXTRA`, `mit_kosten`); nur `von=von, bis=bis` kommt hinzu.

**Vor dem Einsetzen in jeder Datei zweierlei prüfen:** ob `Path` dort schon
importiert ist (sonst `from pathlib import Path` ergänzen), und ob `WACHEN`
und `JOURNAL` als Modulkonstanten vorhanden sind — bei allen fünf sind sie es,
weil `_kosten(pfad=WACHEN)` und `lade_ausstiege(pfad=JOURNAL)` sie als Vorgabe
führen. Die Währung ist überall `"USD"`; `kraken` (EUR) hat keine eigene
`auswertung.py` und ist hier nicht betroffen.

- [ ] **Schritt 4: Test laufen lassen, Erfolg bestätigen**

```bash
python tests/test_kennzahlen_kurz.py -v
```

Erwartet: alle PASS.

- [ ] **Schritt 5: Committen**

```bash
git add spiegel/auswertung.py omniquant/auswertung.py kopier/auswertung.py kopier1zu1/auswertung.py gitter/auswertung.py tests/test_kennzahlen_kurz.py
git commit -m "feat(auswertung): gemeinsame Mindestform kennzahlen_kurz()"
```

---

### Aufgabe 6: Die Gesamtbilanz

**Dateien:**
- Anlegen: `gesamtbilanz.py`
- Test: `tests/test_gesamtbilanz.py`

**Schnittstellen:**
- Verbraucht: `auswertung_alle.kennzahlen_fuer()`, `auswertung_alle.lage_der_spur()`
  (Aufgaben 2 und 4), `kennzahlen_kurz()` der fünf Module (Aufgabe 5)
- Liefert:
  - `summe(posten)` → `{(waehrung, live): {"n", "ergebnis", "treffer"}}`
  - `bericht(von=None, bis=None)` → `str`

**Die zwei Ehrlichkeitsregeln**, die dieser Aufgabe ihren Sinn geben:
Währungen werden nicht stumm gemischt, und Papier wird nicht mit Live
verrechnet. Beide stehen als Test, nicht als Kommentar.

- [ ] **Schritt 1: Den fehlschlagenden Test schreiben**

`tests/test_gesamtbilanz.py`:

```python
"""Tests fuer die Gesamtbilanz.

Der gefaehrlichste Fehler dieses Umbaus ist eine Zahl, die stimmt aussieht
und nicht stimmt: EUR zu USD addiert, oder Papiergewinn mit echtem Geld
verrechnet. Beides steht hier als Test.
"""

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import gesamtbilanz as gb                                      # noqa: E402

POSTEN = [
    {"spur": "scanner", "n": 10, "ergebnis": 100.0, "treffer": 6,
     "waehrung": "USD", "live": True},
    {"spur": "swap", "n": 8, "ergebnis": -20.0, "treffer": 3,
     "waehrung": "USD", "live": False},
    {"spur": "kraken", "n": 12, "ergebnis": 50.0, "treffer": 7,
     "waehrung": "EUR", "live": False},
]


class TestSumme(unittest.TestCase):

    def test_waehrungen_bleiben_getrennt(self):
        s = gb.summe(POSTEN)
        self.assertIn(("EUR", False), s)
        self.assertIn(("USD", False), s)
        self.assertEqual(s[("EUR", False)]["ergebnis"], 50.0)
        self.assertEqual(s[("USD", False)]["ergebnis"], -20.0)

    def test_papier_und_live_bleiben_getrennt(self):
        s = gb.summe(POSTEN)
        self.assertEqual(s[("USD", True)]["ergebnis"], 100.0)
        self.assertEqual(s[("USD", False)]["ergebnis"], -20.0)

    def test_keine_gemeinsame_summe_ueber_alles(self):
        # Es darf keinen Schluessel geben, der alles zusammenwirft.
        s = gb.summe(POSTEN)
        self.assertEqual(len(s), 3)
        for schluessel in s:
            self.assertIsInstance(schluessel, tuple)
            self.assertEqual(len(schluessel), 2)

    def test_runden_und_treffer_werden_mitgezaehlt(self):
        s = gb.summe(POSTEN)
        self.assertEqual(s[("USD", True)]["n"], 10)
        self.assertEqual(s[("USD", True)]["treffer"], 6)

    def test_leere_eingabe_ist_leere_summe(self):
        self.assertEqual(gb.summe([]), {})


class TestBerichtstext(unittest.TestCase):

    def test_text_nennt_papier_und_live_getrennt(self):
        t = gb.zeilen_text(gb.summe(POSTEN))
        self.assertIn("Live", t)
        self.assertIn("Papier", t)
        self.assertIn("EUR", t)
        self.assertIn("USD", t)

    def test_text_wirft_keine_gesamtzahl_aus(self):
        # 100 - 20 + 50 = 130 waere die verbotene Zahl.
        t = gb.zeilen_text(gb.summe(POSTEN))
        self.assertNotIn("130", t)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag bestätigen**

```bash
python tests/test_gesamtbilanz.py -v
```

Erwartet: `ModuleNotFoundError: No module named 'gesamtbilanz'`

- [ ] **Schritt 3: Die minimale Umsetzung schreiben**

`gesamtbilanz.py`:

```python
"""Die Summe ueber alle Buecher - getrennt nach Waehrung und nach Papier/Live.

Warum es diese Datei gibt: die Uebersicht in auswertung_alle.py kennt die
fuenf Spuren mit eigener auswertung.py nicht, und niemand rechnet den
Gesamtstand. Hier wird nichts NEU gerechnet - die Posten kommen fertig aus
den vorhandenen Auswertungen.

Zwei Regeln, die hier nicht verhandelbar sind:

  - Waehrungen werden nicht stumm gemischt. kraken rechnet EUR, der Rest USD.
    Eine Summe ueber beide waere eine Zahl ohne Einheit.
  - Papier und Live werden nicht verrechnet. Eine Zahl, die Papiergewinne mit
    echtem Geld zusammenwirft, ist schlimmer als keine Zahl.

Aufruf:
    python gesamtbilanz.py              # alles seit Anfang
    python gesamtbilanz.py --tage 30    # nur der letzte Monat
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import auswertung_alle                                         # noqa: E402
import zeitfenster                                             # noqa: E402

# Die fuenf Spuren mit eigener Auswertung. Sie liefern kennzahlen_kurz();
# die Rechnung bleibt ihre eigene.
EIGENE = ("spiegel", "omniquant", "kopier", "kopier1zu1", "gitter")


def _live(spur):
    """Handelt die Spur echt? Quelle ist handel_erlaubt in wachen.json."""
    p = HIER / spur / "wachen.json"
    if not p.exists():
        return False
    try:
        return bool(json.loads(p.read_text("utf-8")).get("handel_erlaubt"))
    except (OSError, ValueError):
        return False


def posten(von=None, bis=None):
    """Alle Buecher als flache Liste gleichgeformter Posten."""
    aus = []
    for spur in auswertung_alle.SPUREN:
        if spur in EIGENE:
            continue          # die bringen ihre eigene Rechnung mit
        k = auswertung_alle.kennzahlen_fuer(spur, von=von, bis=bis)
        if not k or not k.get("n"):
            continue
        aus.append({"spur": spur, "n": k["n"], "ergebnis": k["ergebnis"],
                    "treffer": k["treffer"],
                    "waehrung": "EUR" if spur == "kraken" else "USD",
                    "live": _live(spur)})
    for spur in EIGENE:
        try:
            m = importlib.import_module("%s.auswertung" % spur)
            k = m.kennzahlen_kurz(von=von, bis=bis)
        except Exception as e:                           # noqa: BLE001
            # Eine Spur, die beim Auswerten ausfaellt, darf die Bilanz der
            # anderen nicht mitnehmen - dieselbe Regel wie im Tagesbericht.
            print("  %s: Auswertung ausgefallen (%s)" % (spur, e))
            continue
        if k:
            k = dict(k, spur=spur)
            aus.append(k)
    return aus


def summe(posten_):
    """Die Posten zu Summen je (Waehrung, Live) verdichten.

    Der Schluessel ist bewusst ein Paar. Es gibt keinen Schluessel, der
    alles zusammenwirft - eine solche Zahl waere ohne Einheit und ohne
    Bedeutung.
    """
    s = {}
    for p in posten_:
        schluessel = (p["waehrung"], bool(p["live"]))
        t = s.setdefault(schluessel, {"n": 0, "ergebnis": 0.0, "treffer": 0})
        t["n"] += p["n"]
        t["ergebnis"] += p["ergebnis"]
        t["treffer"] += p["treffer"]
    return s


def zeilen_text(s):
    """Die Summen als Text - je Paar eine Zeile, nie eine Gesamtzahl."""
    if not s:
        return "  Keine Buecher mit geschlossenen Runden."
    zeilen = []
    for (waehrung, live) in sorted(s, key=lambda k: (not k[1], k[0])):
        t = s[(waehrung, live)]
        quote = (100.0 * t["treffer"] / t["n"]) if t["n"] else 0.0
        zeilen.append("  %-6s %-6s  %4d Runden  %+10.2f %s  Treffer %.0f %%"
                      % ("Live" if live else "Papier", waehrung,
                         t["n"], t["ergebnis"], waehrung, quote))
    return "\n".join(zeilen)


def bericht(von=None, bis=None):
    p = posten(von, bis)
    t = ["=== Gesamtbilanz ==="]
    if von or bis:
        t.append("Fenster: %s bis %s"
                 % (von.date() if von else "Anfang",
                    bis.date() if bis else "heute"))
    t.append(zeilen_text(summe(p)))
    t.append("")
    t.append("  Papier und Live werden nicht verrechnet, Waehrungen nicht "
             "gemischt.")
    t.append("  %d Buecher gezaehlt." % len(p))
    return "\n".join(t)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Summe ueber alle Buecher")
    p.add_argument("--tage", type=int, help="nur die letzten N Tage")
    p.add_argument("--seit", help="Fensteranfang, JJJJ-MM-TT")
    p.add_argument("--bis", help="Fensterende, JJJJ-MM-TT")
    a = p.parse_args()
    try:
        von, bis = zeitfenster.fenster(tage=a.tage, seit=a.seit, bis=a.bis)
    except ValueError as e:
        p.error(str(e))
    print(bericht(von, bis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Schritt 4: Test laufen lassen, Erfolg bestätigen**

```bash
python tests/test_gesamtbilanz.py -v
```

Erwartet: alle PASS.

- [ ] **Schritt 5: Am echten Baum ansehen**

```bash
python gesamtbilanz.py
```

```bash
python gesamtbilanz.py --tage 30
```

Erwartet: getrennte Zeilen für Papier/USD, Papier/EUR und Live/USD; keine
Gesamtzahl über alles.

- [ ] **Schritt 6: Den ganzen Testlauf und den Spiegelnachweis**

```bash
python -m unittest discover -s tests -p "test_*.py"
```

```bash
python spiegelstand.py
```

Der Spiegelnachweis ist reine Formsache — dieser Plan fasst keinen
Schreibpfad an —, aber er schließt die Frage, statt sie zu behaupten.

- [ ] **Schritt 7: Committen**

```bash
git add gesamtbilanz.py tests/test_gesamtbilanz.py
git commit -m "feat(auswertung): Gesamtbilanz, getrennt nach Waehrung und Papier/Live"
```

---

## Was nach diesem Plan noch offen ist

Für den zweiten Plan (Berichtsschicht), der nach Abschluss dieses Plans
geschrieben wird:

- `lage.py` — die Erhebungsschicht, in die die 24 `spur_*()`-Funktionen aus
  `tagesbericht.py` wandern
- Der Schnappschuss `stand/JJJJ-MM-TT.json` und sein Aufräumen
- Der Vortagsvergleich
- Die Vorrangregel und die Sammelzeile im Tagesbericht
- Der Wochenbericht und seine Anbindung an `dauerlauf.py`
- Der Guthabenabgleich der drei Live-Spuren

Der **Verlauf über mehrere Fenster** (vier Wochen nebeneinander) steht
ebenfalls im zweiten Plan: er ist *n*-mal derselbe Aufruf von
`kennzahlen_fuer()`, und seine einzige Verwendung ist der Wochenbericht. Ihn
hier zu bauen hieße, eine Funktion ohne Aufrufer anzulegen.
