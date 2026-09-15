# XPERP-Rollover, Journal-Schutz, Zeitbomben-Tests (14.09.2026)

Vier Fallen aus dem 14.09.2026, als XAU/BZ-Positionen im Bericht "kein Kurs"
zeigten, der SWAP-Bericht eine Short als "Stop gerissen" markierte und die
orbk-Wachen sich mit KeyError 'eur' verabschiedeten.

## 1. XPERP-Kontrakte rollen (OKX 51001)

OKX legt den XPERP-Kontrakt eines Basiswerts neu auf; der alte instId
antwortet dann mit `OKX 51001: Instrument ID doesn't exist`.
14.09.2026: XAU -310516 -> -310502, BZ -310530 -> -310509 (auch FIL und CL
hatten gewechselt). ctVal bleibt beim Rollover gleich (XAU 0.001, BZ 0.01) -
die Positionsgroesse bleibt gueltig.

Folge ohne Gegenmassnahme: eine offene Position auf dem alten Kontrakt hat
keinen Kurs, Stop und Ziel werden nie geprueft, der Bestand friert, der
Tagesbericht zeigt "(kein Kurs)".

Fix (commit a72020c):
- `okxf.letzter_kurs_mit_fallback(inst, basis)` - bei 51001 den lebenden
  Kontrakt des Basiswerts aufloesen (`okxf.instrument(basis)`, filtert
  state=live) und DESSEN Kurs nehmen. Andere Fehler (429, Timeout) werden
  durchgereicht, kein stiller Kontraktwechsel.
- `xperp/handeln.py::_kurs_aktuell(p)` benutzt das ueberall
  (pruefe_ausstiege, flach_stellen), migriert p["inst"] und bucht eine
  `aktion=rollover`-Journalzeile (zaehlt in keiner Runden-Rechnung).
- `tagesbericht.spur_xperp_positionen` liest den Kurs ueber den Fallback.
Neue Einstiege sind dank `okxf.instrument()` immer aktuell - betroffen sind
nur offene Positionen. Tests: `xperp/test_ausstieg.py` (Fallback-Klasse +
Migrationstests mit mock.patch).

## 2. Tests schreiben nie ins echte Journal (Muster TEST-Q-Falle)

`orbk/tests/test_handeln_papier.py::TestAusstiege` rief `pruefe_ausstiege`
ohne Umleitung von `handeln.JOURNAL` auf: JEDE Suite fuellte die echte
`orbk/handelsjournal.csv` mit synthetischen Zeilen (Einstieg 100.4). Am
14.09.2026 standen 24 davon im echten Journal; der Wachen-Leser zaehlte sie
als Runden. Umleitung in setUp/tearDown auf Temp-Pfad (als `Path`, denn
`journal()` ruft `.exists()`), Nachweis per sha256 vorher/nachher.

Klebefalle dazu: endet die letzte Journalzeile ohne Newline, haengt der
naechste Appender seine Zeile direkt an (Header+Zeile waren verknotet).

## 3. Tests mit hartem Handelstag sind Zeitbomben

`pruefe_ausstiege(z, w)` ohne `jetzt` nimmt die echte Uhr. Ist die
Testposition aelter als ihr Zwangsschluss, faellt jeder Ausstiegs-Test als
`zwangsschluss` statt des geprueften Grundes (14.09.2026, Tests mit
tag=13.09). Feste `JETZT`-Uhrzeit je Testklasse setzen.

## 4. zeile_position braucht die Richtung im Positions-Dict

Der Stop-Abstand in `zeile_position` ist richtungsbewusst (vz aus seite/
richtung). Fehlte `seite` in den Zeilen von `spur_swap` und
`spur_xperp_positionen`, rechnete der Bericht jede Short wie einen Long:
"Stop gerissen (X.X%)" trotz intaktem Stop (14.09.2026 an der Swap-XAU-Short).
Jede Position in den Berichts-Dicts traegt seite/richtung, nicht nur im Namen.
