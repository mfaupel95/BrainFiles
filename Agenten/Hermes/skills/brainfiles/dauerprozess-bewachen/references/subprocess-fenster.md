# subprocess-Aufrufe in Wachen: kein aufploppendes Fenster

Gilt fuer JEDE no_agent-Cron-Wache und jeden Bus-/Handels-Prozess, der per
`subprocess` ein Konsolenprogramm startet.

## Die Regel

Jeder `subprocess.run`/`Popen` in einer Wache braucht

```python
creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
```

**Warum:** Die no_agent-Cron-Wachen laufen im fensterlosen Gateway (pythonw).
Ein Konsolen-Subprozess (tasklist, powershell, python, cmd) ohne das Flag
bekommt dann ein EIGENES sichtbares Fenster — bei jedem Wachen-Lauf poppt eins
auf. Das Flag gehoert an JEDEN subprocess-Aufruf, nicht nur an tasklist: auch
`powershell`- und `sys.executable`-Aufrufe. `os` muss importiert sein.

## Pruefen

Ueber alle aktiven Cron-Skripte (aus `cron/jobs.json`, `enabled`):

```bash
grep -L CREATE_NO_WINDOW <wache>.py
```

Ein Treffer heisst: die Wache ruft subprocess auf, ohne das Fenster zu
unterdruecken. Auch `subprocess.Popen` mit `creationflags=flags` (Variable)
ist ok, solange `flags` CREATE_NO_WINDOW enthaelt.

## Fallen beim Einfuegen

- **Das Flag gehoert in die Argumentliste VOR die schliessende Klammer.**
  Ein zeilenbasiertes Einfuegen, das `capture_output=True`-Zeilen anfasst,
  kann das Flag NACH der schliessenden Klammer platzieren (syntaktisch ein
  Tupel, kein Argument) oder die schliessende Klammer verschlucken. Nach dem
  Einfuegen IMMER `python -m py_compile` UND die Stelle visuell pruefen.
- **`os` importieren**, wenn es fehlt — sonst NameError zur Laufzeit, den der
  Compile nicht zeigt.
- **Ein Test, der das Modul statisch prueft, kann CREATE_NO_WINDOW verbieten**
  („rein lesend, keine Fenstersteuerung“). Das ist eine veraltete Regel: das
  Modul laeuft auch aus dem fensterlosen Gateway. Die Regel praezisieren
  (CREATE_NO_WINDOW ist Pflicht), nicht den Test umgehen.
