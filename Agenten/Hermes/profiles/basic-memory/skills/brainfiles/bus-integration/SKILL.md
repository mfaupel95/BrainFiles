---
name: bus-integration
description: Use when adding a BrainFiles routine to the Telegram Bus.
category: brainfiles
---

## Procedure

1. **Create the Bus Wrapper PowerShell Script**
   - File: `Agenten/Routinen/bus.ps1`
   - Content:
     ```powershell
     # Registriert den Bus als Aufgabe 'bei Systemstart'.
     # ... (see skill for full script)
     ```
   - This script registers a scheduled task `BrainFiles-Bus` that runs `Agenten/Bus/bus.py` at startup with highest priority and restart on failure.

2. **Update the Central README**
   - File: `Agenten/Bus/README.md`
   - Provide a short description of the bus, its files, usage, and the guarantee "ein toter Bus darf niemals einen Lauf abbrechen".

3. **Extend the Routinen Overview in the Vault**
   - File: `MaxHirn/Wissen/Routinen.md`
   - Insert a new row in the "Geplant" table:
     ```markdown
     | bei Systemstart | BrainFiles-Bus starten | Agenten/Bus/bus.py | **eingeplant** 2026-09-10 — `MaxHirn-BrainFiles-Bus` |
     ```
   - Keep the existing table format; do not use Python to rewrite the file—use `edit` or `sed` to preserve line endings.

4. **Add End-to-End Test**
   - File: `Agenten/Bus/tests/test_ende_zu_ende.py`
   - This test verifies:
     - Errors reach the user's device within one minute.
     - A stopped bus still lets a routine run (journal entries appear).
     - All module tests pass.
   - Ensure it is runnable with `python tests/test_ende_zu_ende.py` from the `Agenten/Bus` directory.

5. **Run the Test Suite**
   - Execute:
     ```bash
     cd Agenten/Bus && python tests/test_ende_zu_ende.py
     ```
   - Expect output ending with "Ende-zu-Ende bestanden".

6. **Commit Changes**
   - Stage the new/changed files:
     ```bash
     git add Agenten/Routinen/bus.ps1 Agenten/Bus/README.md MaxHirn/Wissen/Routinen.md Agenten/Bus/tests/test_ende_zu_ende.py
     ```
   - Commit with a descriptive German message and the required trailer:
     ```bash
     git commit -m "Bus: Betrieb ueber die Aufgabenplanung, Ende-zu-Ende-Abnahme" -m "Co-Authored-By: Claude Opus 5 noreply@anthropic.com"
     ```

## Pitfalls
- **Preserve line endings**: When editing `MaxHirn/Wissen/Routinen.md`, never use a Python rewrite that converts CRLF to LF. Use `edit` or `sed` with appropriate flags to keep the original line endings.
- **Run as Administrator**: The `bus.ps1` script must be executed with elevated privileges because it creates a scheduled task with `-RunLevel Highest`. Failing to do so results in a "Zugriff verweigert" error.
- **Do not alter routine logic**: Only add the four required lines (`. (Join-Path $wurzel 'Bus\Ereignis.ps1')`, `$marke = Melde-Start ...`, and `Melde-Ende` before each `exit` and in each `catch`). Keep the existing behavior, exit codes, and output unchanged.
- **Avoid absolute paths**: All paths must be relative to `$PSScriptRoot` or derived from it; the only absolute path appears in `bus.ps1` where it is constructed at runtime from `$PSScriptRoot`.
- **Test before committing**: Always run the end‑to‑end test after modifications; a failure indicates a missing `Melde-Ende` or an incorrect `-Wer` value.

## References
- See `Agenten/Bus/Ereignis.ps1` for the `Melde-Start` / `Melde-Ende` contract.
- Refer to `Wissen/Routinen.md` for the complete list of planned tasks and their wrappers.

- **Jedes neue Skript in `Agenten/Routinen/` gilt als Routine.** Die Prüfung
  `tests/test_anbindung_routinen.py::geplante()` nimmt **jede** `*.ps1` in diesem
  Ordner, ausgenommen nur `einmalig-*`, `*-hook.ps1` und `bus.ps1`. Ein
  Registrierungsskript (eigene Aufgabe per `Register-ScheduledTask`, wie das
  Gegenstück zu `bus.ps1`) fällt damit unter den Routine-Begriff und färbt die
  ganze Kette rot: `test_ende_zu_ende.py` bricht in `test_alle_modultests_laufen`
  ab, die Meldung lautet `ohne Bus-Anbindung: ['<name>']`. Nicht das Skript
  anbinden, sondern die Ausnahme generisch fassen — Dateien mit
  `Register-ScheduledTask` überspringen, statt Namen aufzuzählen; sonst reißt das
  nächste Registrierungsskript die Suite erneut ein.
- **Ein abgebrochener Lauf sieht wie ein Ausbleiben aus, ist aber keins.** Wird
  die Aufgabe von außen beendet (Herunterfahren, `Stop-ScheduledTask`, Absturz),
  steht ein `start` ohne `ende` im Journal — kein PowerShell kann die Schlusszeile
  nach einem Kill noch schreiben. Vor dem Melden einer fehlenden Meldung deshalb
  immer `Get-ScheduledTaskInfo` fragen: `0` = sauber, `267009` (0x41301) = läuft
  gerade, `3221225786` (0xC000013A) = von außen beendet. Nur `0` ohne `ende` ist
  ein Befund am Bus.
- **Angebunden ist nicht gestartet.** Eine Routine ohne eigene geplante Aufgabe
  meldet nie; die Anbindung ist vorhanden, aber unsichtbar. Bei der Abnahme die
  gemeldeten Namen gegen die Liste der geplanten Aufgaben halten — sonst hält man
  den Bus für kaputt, während nur der Auslöser fehlt.
- **Logik unangetastet lassen.** Beim Anbinden einer bestehenden Routine keine
  Bedingungen, Reihenfolgen, Exit-Codes oder Ausgaben ändern; ein Fremdskript
  (`.ps1`) nie per Python-Rewrite bearbeiten, das stellt CRLF auf LF um.

## Abnahme am laufenden System

Die vier Punkte der Spec werden am echten Rechner geprüft, nicht am Testcode
allein. Kurzfassung, vollständiges Rezept mit allen Befehlen in
`references/abnahme-am-laufenden-bus.md`:

1. **Bus lebt?** Port aus `Agenten/Bus/bus.json` gegen `Test-NetConnection`
   prüfen, dazu `bus.pid` und `Get-ScheduledTask -TaskName 'BrainFiles-Bus'`.
2. **Fehler kommt an:** eine Probe über `ereignis.melden(...)` absetzen, dann
   belegen, dass der Bus sie verarbeitet hat (Probe-ID in `Agenten/Bus/stand.json`)
   und `auffaellig.bewerte` sie für meldewürdig hält.
3. **Toter Bus:** `Stop-ScheduledTask`, Port als geschlossen belegen, eine **nur
   lesende** Routine starten — sie muss mit Exit 0 durchlaufen und trotzdem
   `start` und `ende` ins Journal schreiben —, Bus starten und das Nachholen
   beweisen (keine Journal-ID bleibt ungelesen).
4. **Tagesmeldung:** `sprecher.Sprecher(None, auffaellig.regeln()).tagesmeldung()`
   gegen die `ende`-Zeilen des Tages halten.

Für die Prüfung eine harmlose Routine wählen (`wissen-index-pruefen.ps1` liest
nur) — keine Sicherung, kein Versand, keine Order, solange die Abnahme nicht
ausdrücklich einen echten Lauf verlangt. Vor dem Anbinden und nach jeder Änderung
an `.ps1`-Routinen die Suite zeigen: `python tests/test_ende_zu_ende.py` aus
`Agenten/Bus`.

## Telegram-Meldungen: zwei Fallen, die eine Meldung wertlos machen

`melder.sende()` sendet mit `parse_mode=HTML`. Zwei Regeln folgen daraus:

1. **Freitext escapen.** `sprecher._sende` escaped jeden Text mit `html.escape`,
   bevor er an den Melder geht. Ein Fehlertext wie
   `URLError: <urlopen error timed out>` enthaelt spitze Klammern; Telegram
   antwortet dann mit `400 Bad Request`, `_sende` verschluckt das (ein totes
   Telegram darf den Bus nicht reissen) - die Meldung kommt nie an, und zwar
   lautlos. Neue Meldetexte immer durch `html.escape`, niemals roh.
2. **Ursache mitschicken.** `auffaellig.bewerte` haengt bei Fehlern `text` und
   `log` an den Grund (`_mit_ursache`). Ohne das sagt die Meldung nur
   "Ergebniscode 1" und ist nicht zu deuten; die Ursache steht im Journal.

Nach jeder Aenderung an `sprecher.py` oder `auffaellig.py` den Bus neu starten
(`Stop-ScheduledTask`/`Start-ScheduledTask -TaskName 'BrainFiles-Bus'`): er
laedt die Module beim Start, nicht je Ereignis. Eine alte `bus.pid` ist danach
harmlos, `pid_sperren` ersetzt sie.

Beim ersten Start nach Stillstand holt `sprecher.nachholen()` das Journal des
Tages nach - bis zum Deckel (`deckel_je_stunde`, 20). Ein Schwall alter
Meldungen direkt nach dem Start ist also kein neuer Fehler.

## When to Use
Use this skill whenever you need to add a new automated routine to the BrainFiles Telegram Bus, or when you are setting up the bus for the first time on a new machine.
