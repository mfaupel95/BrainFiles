# Uebergabe: Verbesserer Stufe 1.5 - Plan schreiben

Stand 06.10.2026. Naechste Sitzung startet hier. Bereich `handel` (`Agenten/Handel/verbesserer/`).

## Wo wir stehen

- Spec `Werkstatt/spec-verbesserer-stufe-1-5-2026-10-04.md` ist committet (`02d8251e`) und von Max abgenommen ("passt plan schreiben").
- Skill `superpowers:writing-plans` ist der naechste Schritt. Der Plan ist NICHT geschrieben, am Code wurde nichts geaendert.
- HARD-GATE: erst Plan schreiben, Max verlinken, Max waehlt Ausfuehrungsart (Empfehlung: Native, drei kleine abhaengige Tasks in einem Modul), dann Code.

## Auftrag fuer die neue Sitzung

Plan nach `Werkstatt/plan-verbesserer-stufe-1-5-2026-10-04.md` (nicht `docs/superpowers/`). Pflichtkopf des Skills, drei Tasks:

1. F7: `ausrichten(kerzen_je_inst, min_anteil=0.9) -> (ausgerichtet, hinweise)` in `ruecktest.py`; Aufruf am Anfang von `walk_forward()`; `lauf.py` ruft sie einmal vor der Suche (Hinweise melden, unter 3 Instrumenten Abbruch mit Grund). Test `tests/test_ausrichten.py`.
2. F4: `holdout(...)` + Einbau in `suche()`, Konfig `holdout_tage: 60` / `holdout_min_runden: 8`, `lauf.py` `tage` + `holdout_tage` (540), `digest.py` `fast_kandidat`. Test `tests/test_holdout.py`.
3. Notiz `MaxHirn/Wissen/Verbesserer.md` + `Wissen/INDEX.md` nachziehen.

Je Task: failing Test, Lauf, Code, Lauf, Commit (`git add` namentlich). Testlauf: `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s verbesserer/tests` (Stand 100 Tests gruen).

## Entscheidungen fuer den Plan (aus dem Code-Lesen)

- `kennzahlen([])` ist sicher (n=0, netto_gv_je_runde=0): leerer Holdout scheitert sauber an `n >= holdout_min_runden`.
- Holdout in `suche()` nur aktiv, wenn `konfig.get("holdout_tage", 0) > 0`. Bestandstests (`test_suche_lauf.py`: `KONF` ohne `holdout_tage`, `kerzen_je_inst={}`, Attrappen-`bewerte`) muessen gruen bleiben; Ausrichten/Abschneiden darf dort nicht brechen.
- Holdout-Funktion injizierbar (`holdout_fn=None`, analog `bewerte`), Default `ruecktest`-basiert mit traegem Import.
- Rueckgabe von `suche()` abwaertskompatibel; neu `holdout_basis`, `holdout_kandidat`, bei Fehlschlag `fast_kandidat`, `kandidat=None`, `grund="Holdout nicht bestanden"`; zu wenig Historie: `grund="zu wenig Historie fuer Holdout"`.
- `digest._prompt`/`erzeuge`: optionaler Parameter `fast_kandidat=None`, abwaertskompatibel.
- Docstring in `suche.py` ("ein echter Train/Test-Split fehlt") anpassen; Erklaerfeld `_oos_fenster_ziel` ("~480") in `konfig.json` auf 540 nachziehen.
- Bestandstests `tests/test_lauf.py` duerfen nicht brechen.
- `ruecktest.py`, `suche.py`, `lauf.py`, `digest.py` sind laut `file` ASCII, `konfig.json` JSON: nur gezielter Ersatz (Edit), nie Rewrite. Vor jedem Edit frisch lesen.

## Danach

Ausbaustufe 2 (Spur 2 XPERP: Margin/Funding/Liquidation; Spur 3 Kraken-EUR, 0,80 % je Runde) als eigenes Brainstorming mit eigener Spec.

## Einstieg in der neuen Sitzung

"Lies `Werkstatt/uebergabe-verbesserer-stufe-1-5-2026-10-06.md` und mach mit `superpowers:writing-plans` weiter." Die ORB-Tasks 0-15 gehoeren zu einem anderen Auftrag.
