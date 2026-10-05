# Spec: Verbesserer Stufe 1.5 (F7 Kerzen-Ausrichtung, F4 Holdout) - nur Spur 1

Stand 04.10.2026. Status: Entwurf, wartet auf Abnahme durch Max.
Bereich `handel` (`Agenten/Handel/verbesserer/`). Vorgaenger: Ausbaustufe 1
(Merge `6795a31`, 100 Modul-Tests), Notiz `MaxHirn/Wissen/Verbesserer.md`.

## Ziel

Zwei bekannte Schwaechen der woechentlichen Suche beheben, bevor Spur 2/3 darauf
aufbauen:

- **F7:** `walk_forward()` und `merkmals_matrix()` richten Kerzen ueber den
  Listenindex aus (`laenge = min(len(k))`). Fehlt einem Instrument ein Tag,
  verschiebt sich seine Reihe still gegen die anderen - falsche Zahlen ohne Fehler.
- **F4:** Die Suche waehlt ueber `netto_gv_je_runde` aus denselben OOS-Fenstern,
  an denen die Overfitting-Sperre prueft. Ein unberuehrter Test fehlt.

**Erfolg:** Eine Luecke im Zeitstempel wird erkannt statt verschluckt; ein Sieger
der Suche muss einen Block bestehen, den die Suche nie gesehen hat.

## Nicht Teil dieser Stufe

- Spur 2 (XPERP: Margin, Funding, Liquidation) und Spur 3 (Kraken-EUR, 0,80 %
  je Runde) - eigene Spec danach.
- `anwenden.py`, die Denylist (`handel_erlaubt`, `max_pro_trade_usd`,
  `max_gesamt_usd`, `max_offene_positionen`, `freigabe`, `drawdown`, `herzschlag`,
  `kill_switch`) und `auto_anwenden` (bleibt `false`).
- Aenderung der Fensterlogik (`oos_training_tage`/`oos_test_tage`/`oos_schritt_tage`).

## F7: `ausrichten()` in `ruecktest.py`

`ausrichten(kerzen_je_inst, min_anteil=0.9) -> (ausgerichtet, hinweise)`

- Tag = `ts // 86400000`. Schnittmenge der Tage aller verbleibenden Instrumente;
  jede Reihe wird auf diese Tage gefiltert, aufsteigend.
- Ein Instrument mit weniger als `min_anteil` (90 %) der Tage des laengsten faellt
  mit Hinweis heraus (junges Listing soll nicht die ganze Watchlist kuerzen).
  Die Schnittmenge wird erst danach gebildet.
- `hinweise`: Liste von Strings - verworfene Instrumente, Zahl der Luecken, die
  die Schnittmenge gekostet haben. Sie gehen in den Lauf-Bericht.
- **Idempotent:** schon ausgerichtete Reihen kommen unveraendert zurueck, mehrfacher
  Aufruf ist harmlos.
- `walk_forward()` ruft `ausrichten()` am Anfang selbst auf. `lauf.py` ruft sie
  einmal vor der Suche, nur um die Hinweise zu melden. Danach bedeutet Index `t`
  fuer alle Instrumente denselben Kalendertag.
- Bleiben weniger als 3 Instrumente uebrig, bricht der Lauf mit Grund ab
  (bestehende Regel aus `lauf.py`).

## F4: Holdout in `suche.py`

- `holdout(kerzen_je_inst, kandidat, holdout_tage)` rechnet **einen** Block
  `simuliere(matrix, ..., L - H, L)` (`L` = Laenge nach `ausrichten`, `H` =
  `holdout_tage`) und gibt `kennzahlen()` zurueck.
- `suche()` richtet einmal aus, schneidet die letzten `H` Tage fuer Suche und
  `walk_forward()` ab und misst den Sieger danach genau einmal, **Kandidat und
  Basis auf demselben Holdout**.
- **Bestanden**, wenn `netto_gv_je_runde(Kandidat) > netto_gv_je_runde(Basis)` und
  `n >= holdout_min_runden`. Das ist eine **zusaetzliche** Sperre neben den
  bestehenden (kein besserer Kandidat; Aggregat nicht besser; Mehrheit der
  Fenster; `overfit_min_runden`).
- Rueckgabe von `suche()` (abwaertskompatibel, alte Felder bleiben): neu
  `holdout_basis`, `holdout_kandidat`. Bei Fehlschlag: `kandidat=None`,
  `grund="Holdout nicht bestanden"`, dazu `fast_kandidat` (der abgelehnte Sieger)
  fuer den Digest. Daraus entsteht kein Vorschlag.
- **Zu wenig Historie** (`L - H` reicht nicht fuer `oos_training_tage` plus
  `overfit_min_fenster` Testfenster): Ablehnung mit
  `grund="zu wenig Historie fuer Holdout"`. Nie still ueberspringen.
- Konfig (`konfig.json`): `holdout_tage: 60`, `holdout_min_runden: 8`.
- `lauf.py`: Kerzenmenge `tage = oos_training_tage + oos_fenster_ziel *
  oos_test_tage + holdout_tage` (540 statt 480), damit nach dem Abzug weiter ~12
  Suchfenster bleiben.
- `digest.py`: erwaehnt einen `fast_kandidat` als „fast, aber Holdout nein" - ohne
  Vorschlag, ohne Anwenden. Das LLM annotiert nur (Hausregel: deterministisch).

## Tests (unittest, Muster der Bestandstests)

- `tests/test_ausrichten.py` (neu): gleiche Reihen bleiben gleich; ein fehlender
  Tag faellt aus der Schnittmenge; ein zu kurzes Instrument wird verworfen und
  gemeldet; Idempotenz; Hinweise gefuellt.
- `tests/test_holdout.py` (neu): Kandidat mit Fenster-Gewinn, aber Holdout-Verlust
  wird abgelehnt (`fast_kandidat` gesetzt); echter Gewinn laeuft durch; zu wenig
  Runden im Holdout; zu wenig Historie.
- Bestand: `test_suche_lauf.py` nur anpassen, wenn die Rueckgabeform es zwingt;
  Fixture `_kerzen(n)` (`ts = i * 86400000`) bleibt. **Alle bisherigen 100
  Modul-Tests muessen gruen bleiben.**
- Lauf: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest
  discover -s verbesserer/tests`.

## Umsetzungsreihenfolge

1. F7 (`ausrichten`, Einhaengen in `walk_forward` und `lauf.py`, Tests).
2. F4 (`holdout`, `suche()`, Konfig, `lauf.py`, Digest-Hinweis, Tests).
3. Notiz `MaxHirn/Wissen/Verbesserer.md` und `Wissen/INDEX.md` nachziehen.

Je Schritt eigener Commit, `git add` namentlich. Versionierte Dateien nur per
gezieltem Ersatz aendern (CRLF/LF).

## Risiken

- Das Holdout verkuerzt den Suchbereich um 60 Tage. Bei duenner Historie lehnt
  die Suche haeufiger ab - gewollt, der Grund steht im Bericht.
- 60 Tage mit `holdout_min_runden: 8` ist knapp. Zeigt die Praxis zu viele
  Ablehnungen, ist `holdout_tage` ein Konfig-Wert und kein Codeeingriff.
- Wirkt nur auf Spur 1; Spur 2/3 erben beides erst mit ihrer eigenen Stufe.
