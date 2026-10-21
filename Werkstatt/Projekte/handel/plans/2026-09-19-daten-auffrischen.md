# daten/*.csv auffrischen — Implementierungsplan

**Ziel:** Alle 19 `Agenten/Handel/daten/*.csv` bis heute auffrischen (fehlende
Tage anhaengen), Format `Datum,Open,High,Low,Close` unveraendert, damit
`sweep_strategien.py` (Zyklus B) ohne Aenderung auf aktuellen Daten laeuft.
**Architektur:** Neues Skript `nautilus/daten_auffrischen.py`; Tagesdaten von
yfinance (Yahoo hat alle 19 Ticker). Fehlende Tage werden angehaengt, die
Historie bleibt unangetastet. Unmoegliche Schlusszeilen (Close < Low) werden
vor dem Anhaengen ersetzt statt dupliziert. Ein Ticker ohne neue Daten
(MATIC-USD nach Umbenennung) wird in der Ausgabe dokumentiert, nicht zum
Abbruch.
**Tech-Stack:** yfinance (neu, ins nautilus-venv), pandas (vorhanden),
reine Standardbibliothek fuer die CSV-Verarbeitung.

## Projektweite Anforderungen

- **Format bleibt:** `Datum,Open,High,Low,Close`, Datum `YYYY-MM-DD`,
  Zeilenende **CRLF** (Bestand ist CRLF — neue Zeilen muessen CRLF sein,
  sonst gemischte Enden und Ganzdatei-Diff).
- **Nur anhaengen:** Bestehende Zeilen werden nicht veraendert. Ausnahme:
  die letzte Zeile, wenn sie unmoeglich ist (Close < Low) — sie wird aus der
  Datei entfernt und durch die frische Zeile fuer dasselbe Datum ersetzt.
- **Kein Abbruch bei leerem Ticker:** MATIC-USD liefert seit der
  POL-Umbenennung (2025-03) keine neuen Daten — dokumentieren, weiter.
- **Netz nur im echten Lauf:** Alle Tests laufen ohne Netz (yfinance gemockt).
- **Keine Zahlenliterale pruefen:** Die Hoehe der Kurse ist Sache der Quelle;
  der Test prueft Datum, Format und Vollstaendigkeit der angehaengten Zeilen.
- **Pfad relativ:** Keine absoluten Pfade; `daten/` wird gegen
  `Path(__file__).resolve().parent.parent` aufgeloest (Skript liegt in
  `Agenten/Handel/nautilus/`).

## Dateistruktur

| Datei | Verantwortung |
|---|---|
| `nautilus/daten_auffrischen.py` (neu) | CSV-Format-Helfer + yfinance-Abruf + Anhaengen + `main()` mit Bericht |
| `nautilus/test_daten_auffrischen.py` (neu) | Tests ohne Netz, yfinance gemockt |
| `daten/*.csv` (19, aendern) | angehaengte Tageszeilen |

---

### Aufgabe 1: `daten_auffrischen.py` + Tests (ohne Netz)

**Dateien:**
- Neu: `Agenten/Handel/nautilus/daten_auffrischen.py`
- Test: `Agenten/Handel/nautilus/test_daten_auffrischen.py`

**Interfaces:**
- Konsumiert: nichts von anderen Aufgaben.
- Produziert (Aufgabe 2 stuetzt sich darauf):
  - `da.main(heute=None)` — frischt alle 19 CSVs auf, gibt Liste von
    Diktaten zurueck: `{"datei": str, "ticker": str, "letzte_zeile_vorher": str|None, "letzte_zeile_nachher": str|None, "angehaengt": int, "unmoeglich_entfernt": int, "hinweis": str|None}`
  - `da.DATEN` — `Path` auf `Agenten/Handel/daten/`
  - `da.TICKER_EINDEUTIG` — dict `"BTC-USD.csv" -> "BTC-USD"` (Dateiname
    ohne `.csv` ist der yfinance-Ticker; explizite Zuordnung fuer den
    unmoeglichen Sonderfall nichts noetig, Aussnahme dokumentieren).

- [ ] **Schritt 1: yfinance installieren**
  Run: `nautilus/.venv/Scripts/python.exe -m pip install yfinance`
  Erwartet: Exit 0, `import yfinance` laeuft im nautilus-venv.

- [ ] **Schritt 2: Fehlschlagenden Test schreiben** — `test_daten_auffrischen.py`:

  ```python
  """Tests fuer daten_auffrischen.py — laufen OHNE Netz (yfinance gemockt)."""
  import csv
  import tempfile
  import unittest
  from datetime import date
  from pathlib import Path
  from unittest.mock import patch

  import daten_auffrischen as da


  def schreibe_csv(pfad, zeilen, crlf=True):
      ende = "\r\n" if crlf else "\n"
      with open(pfad, "w", newline="", encoding="utf-8") as f:
          f.write(ende.join(zeilen) + ende)


  class ZeilenParsenTest(unittest.TestCase):
      def test_liest_header_und_zeilen(self):
          with tempfile.TemporaryDirectory() as tmp:
              p = Path(tmp) / "a.csv"
              schreibe_csv(p, ["Datum,Open,High,Low,Close",
                               "2026-08-07,100,101,99,100",
                               "2026-08-08,101,102,100,101"])
              header, zeilen = da.parse_csv(p)
              self.assertEqual(header, ["Datum", "Open", "High", "Low", "Close"])
              self.assertEqual(zeilen[0]["datum"], date(2026, 8, 7))
              self.assertEqual(zeilen[-1]["datum"], date(2026, 8, 8))

      def test_leere_datei_ok(self):
          with tempfile.TemporaryDirectory() as tmp:
              p = Path(tmp) / "a.csv"
              schreibe_csv(p, ["Datum,Open,High,Low,Close"])
              header, zeilen = da.parse_csv(p)
              self.assertEqual(zeilen, [])


  class UnmoeglicheZeileTest(unittest.TestCase):
      def test_erkennt_close_unter_low(self):
          with tempfile.TemporaryDirectory() as tmp:
              p = Path(tmp) / "a.csv"
              schreibe_csv(p, ["Datum,Open,High,Low,Close",
                               "2026-08-08,101,102,100,101",
                               "2026-08-10,100,102,101,99.5"])  # Close < Low
              header, zeilen = da.parse_csv(p)
              self.assertTrue(da.ist_unmoeglich(zeilen[-1]))

      def test_letzte_unmoegliche_zeile_entfernen(self):
          with tempfile.TemporaryDirectory() as tmp:
              p = Path(tmp) / "a.csv"
              schreibe_csv(p, ["Datum,Open,High,Low,Close",
                               "2026-08-08,101,102,100,101",
                               "2026-08-10,100,102,101,99.5"])
              zeilen, entfernt = da.entferne_letzte_unmoegliche(p)
              self.assertEqual(entfernt, 1)
              self.assertEqual(zeilen[-1]["datum"], date(2026, 8, 8))

      def test_gesunde_datei_unveraendert(self):
          with tempfile.TemporaryDirectory() as tmp:
              p = Path(tmp) / "a.csv"
              schreibe_csv(p, ["Datum,Open,High,Low,Close",
                               "2026-08-10,100,102,101,101.5"])
              zeilen, entfernt = da.entferne_letzte_unmoegliche(p)
              self.assertEqual(entfernt, 0)
              self.assertEqual(zeilen[-1]["datum"], date(2026, 8, 10))


  class AufbereitenTest(unittest.TestCase):
      def test_bereitet_yfinance_zeilen_auf(self):
          import pandas as pd
          from datetime import datetime, timezone
          idx = [datetime(2026, 8, 11, tzinfo=timezone.utc)]
          df = pd.DataFrame({"Open": [102.0], "High": [103.0],
                             "Low": [101.5], "Close": [102.5]}, index=idx)
          zeilen = da.aufbereiten(df)
          self.assertEqual(zeilen, [("2026-08-11", 102.0, 103.0, 101.5, 102.5)])


  class AnhaengenTest(unittest.TestCase):
      def test_haengt_mit_crlf_an(self):
          with tempfile.TemporaryDirectory() as tmp:
              p = Path(tmp) / "a.csv"
              schreibe_csv(p, ["Datum,Open,High,Low,Close",
                               "2026-08-10,100,102,101,101.5"])
              neu = [("2026-08-11", 102.0, 103.0, 101.5, 102.5),
                     ("2026-08-12", 102.5, 104.0, 102.0, 103.0)]
              n = da.haenge_an(p, neu)
              self.assertEqual(n, 2)
              raw = p.read_bytes()
              self.assertIn(b"2026-08-11,102.0,103.0,101.5,102.5\r\n", raw)
              with open(p, newline="", encoding="utf-8") as f:
                  reader = csv.reader(f)
                  zeilen = list(reader)
              self.assertEqual(len(zeilen), 3)  # Header + 2


  class MainTest(unittest.TestCase):
      def test_frischt_alle_csv_auf(self):
          with tempfile.TemporaryDirectory() as tmp:
              daten_dir = Path(tmp)
              (daten_dir / "BTC-USD.csv").write_bytes(
                  b"Datum,Open,High,Low,Close\r\n"
                  b"2026-08-10,100,102,101,99.5\r\n")  # unmoeglich
              (daten_dir / "AAPL.csv").write_bytes(
                  b"Datum,Open,High,Low,Close\r\n"
                  b"2026-08-10,100,102,101,101.5\r\n")
              fake = [
                  (daten_dir / "BTC-USD.csv", "2026-08-11", 102.0, 103.0, 101.5, 102.5),
                  (daten_dir / "AAPL.csv", "2026-08-11", 200.0, 201.0, 199.0, 200.5),
              ]
              befunde = da.main(daten_dir=daten_dir, heute=date(2026, 8, 11),
                                _fake=fake)
              self.assertEqual(len(befunde), 2)
              for b in befunde:
                  self.assertEqual(b["angehaengt"], 1)
              # BTC: unmoegliche Zeile entfernt und ersetzt
              btc = [b for b in befunde if b["datei"].endswith("BTC-USD.csv")][0]
              self.assertEqual(btc["unmoeglich_entfernt"], 1)
              self.assertIn(b"2026-08-11,102.0,103.0,101.5,102.5\r\n",
                            (daten_dir / "BTC-USD.csv").read_bytes())


  if __name__ == "__main__":
      unittest.main()
  ```

- [ ] **Schritt 3: Test laufen lassen und Fehlschlag verifizieren**
  Run (aus `Agenten/Handel/nautilus/`):
  `.venv/Scripts/python.exe -m unittest test_daten_auffrischen`
  Erwartet: FAIL/ERROR (Modul `daten_auffrischen` fehlt).

- [ ] **Schritt 4: Minimale Implementierung** — `daten_auffrischen.py`:

  ```python
  """Frischt Agenten/Handel/daten/*.csv bis heute auf (Tagesdaten, yfinance).

  Haengt fehlende Tage an, Format Datum,Open,High,Low,Close (CRLF).
  Eine unmoegliche Schlusszeile (Close < Low oder Close > High oder
  High < Low) wird entfernt und durch die frische Zeile fuer dasselbe Datum
  ersetzt. Ticker ohne neue Daten werden dokumentiert, nicht abgebrochen.
  """
  import csv
  from datetime import date, timedelta
  from pathlib import Path

  DATEN = Path(__file__).resolve().parent.parent / "daten"


  def parse_csv(pfad):
      """Liefert (header, zeilen) — zeilen sind dicts mit datum: date und floats."""
      zeilen = []
      with open(pfad, newline="", encoding="utf-8") as f:
          reader = csv.DictReader(f)
          header = reader.fieldnames
          for row in reader:
              zeilen.append({
                  "datum": date.fromisoformat(row["Datum"].strip()),
                  "open": float(row["Open"]),
                  "high": float(row["High"]),
                  "low": float(row["Low"]),
                  "close": float(row["Close"]),
              })
      return header, zeilen


  def ist_unmoeglich(z):
      return not (z["low"] <= z["close"] <= z["high"] and z["low"] <= z["open"] <= z["high"] and z["low"] <= z["high"])


  def entferne_letzte_unmoegliche(pfad):
      """Entfernt die letzte Zeile, wenn unmoeglich. Liefert (zeilen, entfernt)."""
      _, zeilen = parse_csv(pfad)
      entfernt = 0
      if zeilen and ist_unmoeglich(zeilen[-1]):
          zeilen.pop()
          entfernt = 1
      return zeilen, entfernt


  def aufbereiten(frame):
      """yfinance history()-Ergebnis -> Liste (datum_str, open, high, low, close)."""
      zeilen = []
      for ts, row in frame.iterrows():
          zeilen.append((ts.date().isoformat(), float(row["Open"]),
                         float(row["High"]), float(row["Low"]), float(row["Close"])))
      return zeilen


  def hole_kerzen(ticker, start, end):
      """Tagesdaten fuer [start, end) von yfinance. start/end: date."""
      import yfinance as yf
      t = yf.Ticker(ticker)
      hist = t.history(start=start.isoformat(), end=end.isoformat(),
                       interval="1d", auto_adjust=False)
      if hist is None or hist.empty:
          return []
      return aufbereiten(hist)


  def haenge_an(pfad, zeilen):
      """Haengt Zeilen (datum_str, open, high, low, close) mit CRLF an."""
      n = 0
      with open(pfad, "a", newline="", encoding="utf-8") as f:
          for z in zeilen:
              f.write(",".join([z[0], repr(z[1]), repr(z[2]), repr(z[3]), repr(z[4])]) + "\r\n")
              n += 1
      return n


  def main(daten_dir=None, heute=None, _fake=None):
      daten_dir = daten_dir or DATEN
      heute = heute or date.today()
      befunde = []
      for pfad in sorted(daten_dir.glob("*.csv")):
          ticker = pfad.stem
          hinweis = None
          zeilen, entfernt = entferne_letzte_unmoegliche(pfad)
          if not zeilen:
              befunde.append({"datei": pfad.name, "ticker": ticker, "angehaengt": 0,
                              "unmoeglich_entfernt": entfernt, "hinweis": "leer"})
              continue
          letzte_vorher = zeilen[-1]["datum"].isoformat()
          start = zeilen[-1]["datum"] + timedelta(days=1)
          if _fake is not None:
              neue = [z[1:] for z in _fake if z[0] == pfad]
          else:
              neue = hole_kerzen(ticker, start, heute + timedelta(days=1))
          # nur Zeilen mit Datum >= start aufnehmen, sortiert
          neue_gefiltert = [z for z in neue if z[0] >= start.isoformat()]
          n = haenge_an(pfad, neue_gefiltert) if neue_gefiltert else 0
          if not neue:
              hinweis = "keine neuen Daten (Ticker umbenannt?)"
          _, nachher = parse_csv(pfad)
          befunde.append({
              "datei": pfad.name, "ticker": ticker,
              "letzte_zeile_vorher": letzte_vorher,
              "letzte_zeile_nachher": nachher[-1]["datum"].isoformat() if nachher else None,
              "angehaengt": n, "unmoeglich_entfernt": entfernt, "hinweis": hinweis,
          })
      return befunde


  if __name__ == "__main__":
      for b in main():
          print(f"{b['datei']}: +{b['angehaengt']} Tage "
                f"(unmoeglich entfernt: {b['unmoeglich_entfernt']}) "
                f"bis {b['letzte_zeile_nachher']} {b['hinweis'] or ''}")
  ```

- [ ] **Schritt 5: Test laufen lassen, PASS verifizieren**
  Run (aus `Agenten/Handel/nautilus/`):
  `.venv/Scripts/python.exe -m unittest test_daten_auffrischen -v`
  Erwartet: 8 Tests, alle ok.

- [ ] **Schritt 6: Dateityp pruefen (CRLF-Handler der neuen Datei)**
  Run: `git status --porcelain Agenten/Handel/` — nur die zwei neuen Dateien
  als `??`. `file Agenten/Handel/nautilus/daten_auffrischen.py` — Text.

- [ ] **Schritt 7: Committen**
  `git add Agenten/Handel/nautilus/daten_auffrischen.py Agenten/Handel/nautilus/test_daten_auffrischen.py`
  `git commit -m "feat(nautilus): daten_auffrischen.py — fehlende Tagesdaten via yfinance anhaengen (Tests ohne Netz)"`

---

### Aufgabe 2: Echter Lauf auf allen 19 CSVs + Verifikation

**Dateien:**
- Aendern: `daten/*.csv` (19, nur angehaengte Zeilen)
- (Code aus Aufgabe 1 bleibt unveraendert)

**Interfaces:**
- Konsumiert: `da.main()` aus Aufgabe 1.

- [ ] **Schritt 1: Lauf ausfuehren (Netz)**
  Run (aus `Agenten/Handel/nautilus/`):
  `.venv/Scripts/python.exe daten_auffrischen.py`
  Erwartet: je CSV eine Zeile `+N Tage ... bis <heute>`; MATIC-USD darf den
  Hinweis `keine neuen Daten (Ticker umbenannt?)` tragen. Exit 0.

- [ ] **Schritt 2: Verifikation — letzte Daten, Luecken, Format**
  Run:
  ```
  cd Agenten/Handel/daten && for f in *.csv; do echo "$f: letzte $(tail -1 $f | cut -d, -f1)"; done
  ```
  Erwartet: letzte Zeile = heute (19.09.2026 bzw. naechster Handelstag davor)
  fuer alle ausser ggf. MATIC-USD. Danach Lueckenpruefung:
  `.venv/Scripts/python.exe -c "
  import csv, sys
  from datetime import date, timedelta
  from pathlib import Path
  for pfad in sorted(Path('daten').glob('*.csv')):
      daten = [r['Datum'].strip() for r in csv.DictReader(open(pfad, newline=''))]
      loecher = 0
      for a, b in zip(daten, daten[1:]):
          d1, d2 = date.fromisoformat(a), date.fromisoformat(b)
          if (d2 - d1).days > 4:  # Wochenende + Feiertag Toleranz
              loecher += (d2 - d1).days - 1
      print(f'{pfad.name}: {len(daten)} Zeilen, {loecher} Lueckentage')
  "` (aus `Agenten/Handel/`)
  Erwartet: Lueckentage nur dort, wo die Historie beginnt (keine Luecken im
  aktuellen Monat).

- [ ] **Schritt 3: Diff pruefen — nur angehaengte Zeilen**
  Run: `git diff --stat Agenten/Handel/daten/`
  Erwartet: je CSV `+N` Zeilen, 0 Loeschungen (ausser BTC-USD: 1 Loeschung
  fuer die unmoegliche Zeile, dafuer 1 Einfuegung derselben Zeile mit der
  frischen Version). `git diff Agenten/Handel/daten/BTC-USD.csv` zeigt
  exakt die unmoegliche Zeile ersetzt + neue Zeilen.

- [ ] **Schritt 4: Gegenprobe Sweep laeuft (nur Vorschau, kein Komplett-Sweep)**
  Run (aus `Agenten/Handel/nautilus/`):
  `.venv/Scripts/python.exe -c "import sweep_strategien; print('import ok')"`
  Erwartet: `import ok` — die Datenstruktur ist kompatibel.

- [ ] **Schritt 5: Committen**
  `git add Agenten/Handel/daten/`
  `git commit -m "daten(nautilus): Tagesdaten bis 2026-09-19 aufgefuellt (yfinance), BTC-Fallzeile ersetzt"`