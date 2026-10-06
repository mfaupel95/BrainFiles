# Plan: Verbesserer Stufe 1.5 — Umsetzung

**Stand:** 2026-10-07  
**Spec:** `Werkstatt/spec-verbesserer-stufe-1-5-2026-10-04.md` (commit `02d8251e`)  
**Bereich:** `handel` → `Agenten/Handel/verbesserer/`  
**Status:** Entwurf — wartet auf Abnahme durch Max. Kein Code ohne Abnahme.

---

## Ziel

Zwei bekannte Schwächen vor Spur 2/3 beheben:

- **F7:** `walk_forward()` richtet Kerzen über Listenindex aus — fehlt ein Tag,
  verschiebt sich die Reihe still.
- **F4:** Auswahl und Overfitting-Prüfung nutzen dieselben Fenster — kein
  unberührter Holdout-Block.

---

## Schritt 1 — F7: `ausrichten()` in `ruecktest.py`

### Was entsteht
Neue Funktion `ausrichten(kerzen_je_inst, min_anteil=0.9)` → `(ausgerichtet, hinweise)`:

- Tag = `ts // 86400000`. Schnittmenge aller Tage nach Ausschluss von
  Instrumenten mit < `min_anteil` der Tage des längsten.
- Jede Reihe wird auf die Schnittmenge gefiltert (aufsteigend). Danach gilt:
  Index `t` = identischer Kalendertag für alle Instrumente.
- `hinweise`: Liste von Strings (verworfene Instrumente, Lückenzahl).
- Idempotent: bereits ausgerichtete Reihen kommen unverändert zurück.
- Bei < 3 verbleibenden Instrumenten: Abbruch (bestehende Regel in `lauf.py`).

### Eingehängt in
- `walk_forward()` (Anfang der Funktion, vor der Matrix): einmaliger Aufruf.
- `lauf.py` (nach `kerzen`, vor `suche`): einmaliger Aufruf, nur um Hinweise zu melden.

### Tests
Neue Datei `tests/test_ausrichten.py`:
- Gleiche Reihen → unveränderter Output.
- Ein fehlender Tag fällt aus der Schnittmenge.
- Zu kurzes Instrument wird verworfen + gemeldet.
- Idempotenz: zweimaliger Aufruf = gleiches Ergebnis.
- Hinweise sind gefüllt wenn etwas verworfen wurde.

### Commit
`git add verbesserer/ruecktest.py verbesserer/tests/test_ausrichten.py`  
Nachricht: `verbesserer: F7 ausrichten() - Kerzenreihen ueber Zeitstempel statt Listenindex`

---

## Schritt 2 — F4: `holdout()` in `suche.py`

### Was entsteht
Neue Funktion `holdout(kerzen_je_inst, kandidat, holdout_tage)`:
- Rechnet einen Block `simuliere(matrix, ..., L - H, L)` (`L` = Länge nach
  `ausrichten`, `H` = `holdout_tage`).
- Gibt `kennzahlen()` zurück.

Änderungen an `suche()`:
- Richtet einmal aus, schneidet die letzten `H` Tage für Suche + `walk_forward()` ab.
- Misst Sieger + Basis auf demselben Holdout-Block **genau einmal**.
- **Bestanden:** `netto_gv_je_runde(Kandidat) > netto_gv_je_runde(Basis)` und
  `n >= holdout_min_runden`.
- **Fehlschlag:** `kandidat=None`, `grund="Holdout nicht bestanden"`,
  `fast_kandidat` = der abgelehnte Sieger.
- **Zu wenig Historie:** `grund="zu wenig Historie fuer Holdout"` — nie still.
- Neue Rückgabefelder (abwärtskompatibel): `holdout_basis`, `holdout_kandidat`.

Konfig-Ergänzungen in `konfig.json`:
```json
"holdout_tage": 60,
"holdout_min_runden": 8
```

Änderung in `lauf.py`:
- Kerzenmenge: `tage = oos_training_tage + oos_fenster_ziel * oos_test_tage + holdout_tage`
  → 540 statt 480 (damit nach Abzug ~12 Suchfenster bleiben).

Hinweis in `digest.py`:
- `fast_kandidat` wird erwähnt als „fast, aber Holdout nein" — nur Annotation, kein Vorschlag.

### Tests
Neue Datei `tests/test_holdout.py`:
- Kandidat mit Fenstergewinn, aber Holdout-Verlust → abgelehnt, `fast_kandidat` gesetzt.
- Echter Gewinn → Kandidat durchläuft.
- Zu wenig Runden im Holdout → Ablehnung mit korrektem Grund.
- Zu wenig Historie gesamt → Ablehnung mit korrektem Grund.

`test_suche_lauf.py`: nur anpassen wenn Rückgabeform zwingt; Fixture `_kerzen(n)` bleibt.

### Commit
`git add verbesserer/suche.py verbesserer/lauf.py verbesserer/konfig.json verbesserer/digest.py verbesserer/tests/test_holdout.py`  
Nachricht: `verbesserer: F4 Holdout - vierte Overfitting-Sperre (540 Tage Kerzenfenster)`

---

## Schritt 3 — Dokumentation

- `MaxHirn/Wissen/Verbesserer.md`: Stufe-1.5-Abschnitt mit F7/F4 ergänzen,
  Stand auf 2026-10-07 anpassen.
- `MaxHirn/Wissen/INDEX.md`: Zusammenfassungszeile aktualisieren falls nötig.
- Commit: `docs(verbesserer): Wissen/Verbesserer.md auf Stufe 1.5 Stand bringen`

---

## Reihenfolge

1. F7 vollständig (ruecktest.py + Tests + Commit) — alle 100 Bestandstests grün.
2. F4 vollständig (suche.py, lauf.py, konfig.json, digest.py + Tests + Commit) — alle Tests grün.
3. Docs (Commit).

---

## Abnahmekriterien

- [ ] `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests` → **0 Fehler, ≥ 110 Tests** (100 Bestand + ~10 neue).
- [ ] Ein Lauf mit Lücke im Zeitstempel: Lücke erkannt, nicht verschluckt.
- [ ] Ein Sieger der Suche: wird am Holdout gemessen — Beleg im Bericht.
- [ ] `konfig.json`: `holdout_tage` und `holdout_min_runden` vorhanden.
- [ ] Kein bestehender Test rot.

---

## Risiken

- Holdout verkürzt Suchbereich um 60 Tage → mehr Ablehnungen möglich (gewollt).
- `holdout_min_runden: 8` bei 60 Tagen ist knapp; `holdout_tage` ist Konfig-Wert
  (kein Codeeingriff zum Anpassen).
- Wirkt nur auf Spur 1; Spur 2/3 erben beides erst in ihrer eigenen Stufe.
