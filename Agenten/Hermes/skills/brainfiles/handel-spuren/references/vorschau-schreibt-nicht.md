# Vorschau, die schreibt, ist keine Vorschau

Regel: `--vorschau` darf NIE schreiben - kein Journal, kein Zustand, keine
Spiegelung, kein Kill. Ein Exit ist eine Buchung, keine Ansage.

## Warum

`spur_buch.pruefe_ausstiege(z, kurse, w, journal_pfad)` schreibt beim Exit
ins Journal (aktion="verkauf") und entfernt die Position aus `z`. Wird sie
VOR der Vorschau-Verzweigung aufgerufen, bucht die Vorschau echte Ausstiege
ins echte Journal - und der naechste Papierlauf schliesst dieselbe Position
noch einmal (Doppelbuchung).

## Wo es passiert ist

iv_waelle/handeln.py (19.09.2026): `lauf()` rief `buch.pruefe_ausstiege`
vor dem `if modus == "vorschau"`-Block. Behoben: die Vorschau kehrt VOR dem
Ausstiegspruefen zurueck (nach `_hole_markt`), der Kill-Zweig und
`pruefe_ausstiege` laufen nur noch im echten Modus.

## Muster-Falle

moondev_funding/handeln.py hat dieselbe latente Stelle (pruefe_ausstiege vor
der Vorschau-Rueckkehr). Sie faellt im Betrieb nicht auf, weil die
Vorschau dort nur als Freigabe-Probe (nur_fenster_fehlt) laeuft und Papier-
Spuren nie eine Freigabe-Frage stellen - aber ein manuelles `--vorschau`
mit offener Position am Stop wuerde buchen. Bei neuen Spuren die Vorschau
strukturell VOR dem Ausstiegspruefen zurueckkehren lassen.

## Test

Regressionstest: Position am Stop in zustand.json + `lauf("vorschau")` ->
Journal darf nicht entstehen, zustand.json unveraendert. (test_handeln.py:
test_vorschau_bucht_auch_keinen_ausstieg.)
