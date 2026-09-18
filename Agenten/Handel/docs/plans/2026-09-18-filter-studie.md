# Eingangsfilter-Studie (spiegel/kopier/kopier1zu1) — Implementierungsplan

**Ziel:** Ein lesendes Studienwerkzeug, das auf den vorhandenen Journalen
prüft, ob eine Änderung des Marktkapitalisierungs-Bands oder der Kette in
BEIDEN Zeithälften trägt — und daraus Vorschlagswerte für `wachen.json`
ableitet, ohne irgendetwas zu ändern.

**Architektur:** `filter_studie.py` ist ein reines Auswerte-Skript. Die
Buchhaltung wird NICHT nachgebaut: je Spur wird `<spur>/auswertung.py` über
den Pfad geladen (`importlib`), und dessen `lade_ausstiege()` sowie
`kennzahlen()` liefern Paare und Kennzahlen. Die Studie ergänzt nur drei
Dinge: das Aufteilen nach Zeit, das Anwenden von Filterregeln und das
Verdikt.

**Tech-Stack:** Python 3.11 (Spur-venv `scanner/.venv`), nur Standardbibliothek
plus die vorhandenen Hausmodule (`buchauswertung.py` über die geladene
Auswertung). Kein Netz. Tests mit `unittest` auf synthetischen Journalen.

**Projektweite Anforderungen (gelten für jede Aufgabe):**
- Die Studie liest nur; sie schreibt ausschließlich
  `Agenten/Handel/filter_studie_ergebnis.json`.
- Keine zweite Buchhaltung: Paarung und Kennzahlen kommen aus der Spur.
- Mindestbesetzung 30 Ausstiege je Gruppe JE HÄLFTE (Wert aus der
  Spezifikation, Abschnitt 4.4).
- Tests dürfen nie in echte Spurenordner schreiben (Tempdateien + Wächter).
- Deutsche Bezeichner und Meldungen wie im Haus.

## Dateistruktur

| Datei | Verantwortung |
|---|---|
| `Agenten/Handel/filter_studie.py` (neu) | Regeln, Zeithalbierung, Verdikt, CLI, Bericht |
| `Agenten/Handel/tests/test_filter_studie.py` (neu) | Test auf synthetischem Journal mit bekanntem Ausgang |
| `Agenten/Handel/filter_studie_ergebnis.json` (erzeugt) | Ergebnis aller Spuren |
| `.gitignore` (geändert) | Freigabe für `docs/plans/*.md` und die Ergebnisdatei |

---

### Aufgabe 1: Zeit-Halbierung und Kennzahlen einer Teilmenge

**Dateien:**
- Neu: `Agenten/Handel/filter_studie.py`
- Test: `Agenten/Handel/tests/test_filter_studie.py`

**Interfaces:**
- Konsumiert: `buchauswertung.kennzahlen(aus, k)` (Feldnamen: `n`, `quote`,
  `netto_pct`, `brutto_pct`, `median_pct`, `gv_usd`).
- Produziert: `zeit_halbieren(aus) -> (alt, jung)`; `masse(aus, k) -> dict`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
class HalbierungTest(unittest.TestCase):
    def test_halbierung_60_40_nach_zeit(self):
        aus = [_zeile("2026-09-1%dT00:00:00+00:00" % i) for i in range(1, 6)]
        alt, jung = fs.zeit_halbieren(aus)
        self.assertEqual(len(alt), 3)     # 60 % von 5 -> 3
        self.assertEqual(len(jung), 2)
        self.assertEqual(alt[0]["zeit"], "2026-09-11T00:00:00+00:00")
        self.assertEqual(jung[-1]["zeit"], "2026-09-15T00:00:00+00:00")

    def test_masse_liefert_beide_kostenblicke(self):
        aus = [_zeile_gv(50.0, 100.0), _zeile_gv(50.0, 25.0)]
        m = fs.masse(aus, 1.0)
        self.assertEqual(m["n"], 2)
        self.assertAlmostEqual(m["netto"], 25.0, places=6)   # (100+50)/2/50-1
        self.assertAlmostEqual(m["quote"], 50.0, places=6)
```

- [ ] **Schritt 2: Test laufen lassen und Fehlschlag verifizieren**
  Run: `cd Agenten/Handel/tests && ../scanner/.venv/Scripts/python.exe -m unittest test_filter_studie` — Erwartet: FAIL (`AttributeError: module ... has no attribute 'zeit_halbieren'`)

- [ ] **Schritt 3: Minimale Implementierung**

```python
def zeit_halbieren(aus, anteil_alt=0.6):
    """Ausstiege nach Zeit in Suchhaelfte (aeltere 60 %) und Gegenprobe."""
    sortiert = sorted(aus, key=lambda a: a.get("zeit") or "")
    grenze = int(round(len(sortiert) * anteil_alt))
    return sortiert[:grenze], sortiert[grenze:]


def masse(aus, kosten):
    """Die Kennzahlen einer Teilmenge ueber die Buchhaltung der Spur."""
    k = mod_kennzahlen(aus, kosten)
    if not k.get("n"):
        return {"n": 0}
    return {"n": k["n"], "quote": k["quote"], "netto": k["netto_pct"],
            "brutto": k["brutto_pct"], "median": k["median_pct"],
            "gv_usd": k["gv_usd"]}
```

**Hinweis zur Buchhaltung:** `mod_kennzahlen` ist der Import
`from buchauswertung import kennzahlen as mod_kennzahlen` — dieselbe Funktion,
die die Spurauswertung benutzt. Kein Nachbau.

- [ ] **Schritt 4: Test laufen lassen, PASS verifizieren**
  Run: `python -m unittest test_filter_studie` — Erwartet: OK
- [ ] **Schritt 5: Committen** (`Studie: Zeithalbierung und Kennzahlen einer Teilmenge`)

---

### Aufgabe 2: Spuren laden (Paare und Kostensätze)

**Dateien:**
- Ändern: `Agenten/Handel/filter_studie.py`
- Test: `Agenten/Handel/tests/test_filter_studie.py`

**Interfaces:**
- Konsumiert: `<spur>/auswertung.py` mit `lade_ausstiege(pfad=...)` und
  `_kosten()`.
- Produziert: `lade_spur(spur) -> (aus, kosten)`; `paare(spur)` liefert je
  Ausstieg die Felder `zeit`, `netto_pct`, `einsatz`, `wert`, `grund`,
  `kette`, `wallet`, `token`, `marktkap_usd`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
class LadenTest(unittest.TestCase):
    def test_lade_spur_liest_das_journal_der_spur(self):
        aus, kosten = fs.lade_spur("spiegel", journal=SYNTH_JOURNAL)
        self.assertEqual(len(aus), 4)
        self.assertEqual(aus[0]["kette"], "solana")
        self.assertIsNotNone(kosten)

    def test_unbekannte_spur_wirft(self):
        with self.assertRaises(ValueError):
            fs.lade_spur("gibtsnicht")
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag verifizieren** — FAIL (Attribut fehlt)
- [ ] **Schritt 3: Minimale Implementierung**

```python
SPUREN = ("spiegel", "kopier", "kopier1zu1")


def lade_auswertung(spur):
    """Das Auswertungsmodul der Spur ueber den PFAD laden.

    Alle drei Spuren haben ein Modul `auswertung` - ueber sys.path geladen
    gewaenne die zuletzt eingefuegte Spur. Darum je Spur ein eindeutiger
    Modulname.
    """
    pfad = HIER / spur / "auswertung.py"
    if not pfad.exists():
        raise ValueError("unbekannte Spur: %s" % spur)
    spec = importlib.util.spec_from_file_location("auswertung_%s" % spur, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


def lade_spur(spur, journal=None):
    """Ausstiege und Kostensaetze einer Spur - aus ihrer eigenen Auswertung."""
    modul = lade_auswertung(spur)
    if journal is not None:
        aus = modul.lade_ausstiege(str(journal))
    else:
        aus = modul.lade_ausstiege()
    return aus, modul._kosten()
```

- [ ] **Schritt 4: PASS verifizieren** — Run: `python -m unittest test_filter_studie`
- [ ] **Schritt 5: Committen**

---

### Aufgabe 3: Regeln und Verdikt

**Dateien:**
- Ändern: `Agenten/Handel/filter_studie.py`
- Test: `Agenten/Handel/tests/test_filter_studie.py`

**Interfaces:**
- Produziert: `regeln() -> list[dict]` mit `name`, `pruef` (Callable auf einem
  Ausstieg); `pruefe_regel(regel, aus, kosten) -> dict` mit `regel`, `ganz`,
  `alt`, `jung`, `rest`, `verdikt`, `grund`.
- Verdikt-Werte: `"traegt"`, `"nicht entschieden"`, `"verworfen"`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
class VerdiktTest(unittest.TestCase):
    def test_traegt_wenn_beide_haelften_positiv_und_besetzt(self):
        aus = _journal_klein_unten_verliert_oben_gewinnt()
        r = fs.studie_aus(aus, 1.0)
        untergrenze = [x for x in r if x["regel"] == "untergrenze 250k"][0]
        self.assertEqual(untergrenze["verdikt"], "traegt")
        self.assertGreater(untergrenze["alt"]["n"], 0)
        self.assertGreater(untergrenze["jung"]["n"], 0)

    def test_nicht_entschieden_bei_zu_kleiner_gruppe(self):
        aus = _drei_ausstiege()
        r = fs.studie_aus(aus, 1.0)
        self.assertTrue(all(x["verdikt"] == "nicht entschieden" for x in r))

    def test_gegenprobe_zeigt_die_gegenrichtung(self):
        aus = _journal_klein_unten_verliert_oben_gewinnt()
        r = {x["regel"]: x for x in fs.studie_aus(aus, 1.0)}
        self.assertEqual(r["obergrenze 250k"]["verdikt"], "verworfen")
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag verifizieren**
- [ ] **Schritt 3: Minimale Implementierung**

```python
UNTERGRENZEN = (100_000, 150_000, 250_000, 500_000)
OBERGRENZEN = (1_000_000, 2_000_000, 5_000_000)
KETTEN_TEST = ("solana",)


def regeln():
    """Die geprueften Eingangsfilter (Spezifikation, Abschnitt 4.3).

    Nur die Untergrenze oeffnen und die Obergrenze weiten sind Regeln des
    Auftrags; die Gegenprobe (Band verschieben statt oeffnen) laeuft als
    eigene Regel mit, damit ein Artefakt auffaellt.
    """
    r = []
    for u in UNTERGRENZEN:
        r.append({"name": "untergrenze %s" % kurz(u),
                  "pruef": lambda a, u=u: (a.get("marktkap_usd") or 0) >= u})
    for o in OBERGRENZEN[1:]:
        r.append({"name": "obergrenze %s" % kurz(o),
                  "pruef": lambda a, o=o: (a.get("marktkap_usd") or 1e18) <= o})
    r.append({"name": "nur solana",
              "pruef": lambda a: (a.get("kette") or "").lower() == "solana"})
    r.append({"name": "untergrenze 250k ohne solana",
              "pruef": lambda a: (a.get("marktkap_usd") or 0) >= 250_000
              and (a.get("kette") or "").lower() != "solana"})
    return r


def verdikt(alt, jung, rest_alt, rest_jung, mindest=MINDEST_JE_HALBE):
    """Darf diese Regel als Vorschlag gelten?

    Drei Bedingungen, alle in der Spezifikation belegt: Besetzung in beiden
    Haelften, positives Vorzeichen in beiden Haelften, Vorsprung gegen die
    Restgruppe in beiden Haelften.
    """
    if alt["n"] < mindest or jung["n"] < mindest:
        return "nicht entschieden", "Gruppe zu klein (mind. %d je Haelfte)" % mindest
    if alt["netto"] <= 0 or jung["netto"] <= 0:
        return "verworfen", "in einer Haelfte nicht positiv"
    if alt["netto"] <= rest_alt["netto"] or jung["netto"] <= rest_jung["netto"]:
        return "verworfen", "kein Vorsprung gegen die Restgruppe"
    return "traegt", "in beiden Haelften positiv und besser als der Rest"
```

- [ ] **Schritt 4: PASS verifizieren**
- [ ] **Schritt 5: Committen**

---

### Aufgabe 4: CLI, Bericht und Ergebnisdatei

**Dateien:**
- Ändern: `Agenten/Handel/filter_studie.py`
- Test: `Agenten/Handel/tests/test_filter_studie.py`

**Interfaces:**
- Produziert: `studie(spur) -> dict`, `bericht(ergebnis) -> list[str]`,
  `main(argv=None) -> int`.
- CLI: `--spur NAME` (mehrfach möglich, Vorgabe alle), `--json` (schreibt
  `filter_studie_ergebnis.json`), `--mindest N` (Vorgabe 30).

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
class BerichtTest(unittest.TestCase):
    def test_bericht_nennt_jede_regel_und_ihr_verdikt(self):
        e = {"spiegel": {"n": 4, "regeln": [
            {"regel": "untergrenze 250k", "verdikt": "traegt", "grund": "x",
             "ganz": {"n": 4}, "alt": {"n": 2}, "jung": {"n": 2}}]}
        zeilen = "\n".join(fs.bericht(e))
        self.assertIn("untergrenze 250k", zeilen)
        self.assertIn("traegt", zeilen)

    def test_main_ohne_json_schreibt_nichts(self):
        ziel = Path("filter_studie_ergebnis.json")
        vorher = ziel.exists()
        rc = fs.main(["--spur", "spiegel", "--journal", str(SYNTH_JOURNAL)])
        self.assertEqual(rc, 0)
        self.assertEqual(ziel.exists(), vorher)
```

- [ ] **Schritt 2: Test laufen lassen, Fehlschlag verifizieren**
- [ ] **Schritt 3: Minimale Implementierung** (Bericht als Liste von Zeilen,
  `--json` schreibt erst nach vollständiger Rechnung — kein halbes Ergebnis
  auf der Platte)
- [ ] **Schritt 4: PASS verifizieren**
- [ ] **Schritt 5: Committen**

---

### Aufgabe 5: Wächter-Test und Lauf auf den echten Journalen

**Dateien:**
- Ändern: `Agenten/Handel/tests/test_filter_studie.py`
- Erzeugt: `Agenten/Handel/filter_studie_ergebnis.json`

**Interfaces:**
- Konsumiert: alles Vorherige.

- [ ] **Schritt 1: Wächter-Test schreiben** (`setUpModule` merkt Dateiliste und
  Größen der drei Spurenordner, `tearDownModule` vergleicht) — belegt, dass
  kein Test in echte Spuren schreibt (Hausmuster).
- [ ] **Schritt 2: Test laufen lassen, PASS verifizieren**
- [ ] **Schritt 3: Lauf auf den echten Journalen** mit `--json`
- [ ] **Schritt 4: Ergebnis gegen die Handzahlen der Spezifikation prüfen**
  (spiegel: 807 Ausstiege, Ø −9,32 % nach / −1,77 % vor Kosten). Abweichung
  bedeutet: die Studie rechnet anders als die Spur — dann ist die Studie
  falsch, nicht die Spur.
- [ ] **Schritt 5: Committen und pushen**

---

## Self-Review

1. **Spezifikations-Abdeckung:** 4.1 (eine Buchhaltung) → Aufgabe 2;
   4.2 (Zeithalbierung) → Aufgabe 1; 4.3 (Regeln) → Aufgabe 3;
   4.4 (Kennzahlen + Mindestbesetzung) → Aufgaben 1 und 3;
   4.5 (Ergebnis und Verdikt) → Aufgabe 4; 5 (Erfolgskriterien) → Aufgabe 5;
   7 (Grenzen: keine Verdikte bei kleinen Büchern) → `nicht entschieden` in
   Aufgabe 3. Keine Lücke.
2. **Platzhalter-Scan:** keine TBD/TODO; jeder Schritt trägt Code oder einen
   konkreten Befehl.
3. **Typ-Konsistenz:** `masse()` (Aufgabe 1) liefert `netto`/`brutto`/`n`,
   `verdikt()` (Aufgabe 3) liest genau diese Schlüssel, `bericht()`
   (Aufgabe 4) liest `verdikt`/`regel`/`grund` aus `pruefe_regel`.
   `lade_spur()` (Aufgabe 2) liefert das Paar `(aus, kosten)`, das
   `studie_aus()` in Aufgabe 3 erwartet.
4. **Umfang:** ein Plan, ein Werkzeug, ein Testmodul — ein
   Implementierungsdurchgang.
