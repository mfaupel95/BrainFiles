---
name: struktur-in-eine-quelle
description: Baum-Aussagen messen, in eine Quelle giessen, belegen.
version: 0.1.0
author: Hermes
platforms: [windows]
license: MIT
metadata:
  hermes:
    tags: [Struktur, Quelle, Beleg, Vertragstest, Commit]
    related_skills: [codebasis-bestand, trugschluesse, repos-zentrale, arbeitsbaum-git-hygiene, brainstorming]
---

# Verstreute Baum-Aussagen in eine Quelle giessen

Wenn dieselbe Aussage ueber den Codebaum an mehreren Stellen liegt (Rollen,
Listen, Konfigurationen) oder eine Zahl nicht belastbar ist, wird hier EINE
Quelle daraus: eine JSON-Datei, ein Leser, eine Anzeige, angeschlossene
Verbraucher, Vertragstests, ein eigener Commit.

Der Skill **misst nicht** den Bestand — das ist `codebasis-bestand`. Er
**startet nichts** und **raeumt nichts um**: Fremdes und Unklares wird benannt,
nicht beseitigt. Alle Hilfsmittel sind Standardbibliothek.

## When to Use

- "code und struktur ueberall optimieren", "aufraeumen", "vereinheitlichen"
- dieselbe Aussage steht mehrfach: eine Rolle, eine Liste, ein Fakt in N Dateien
- eine Zahl soll weitergegeben werden und muss dafuer ehrlich sein
- ein neuer Ordner/eine neue Spur hat keine Tests
- ein Launcher hinterlaesst Fenster, die niemand schliesst
- ein Befund soll dauerhaft gelten, nicht nur in dieser Sitzung

**Don't use for:** Bestandszahlen allein (`codebasis-bestand`), Zustand belegen
(`trugschluesse`), ein Projekt starten (`repos-zentrale`), fremde Skills
(`fundus-zugriff`).

## Prerequisites

- Arbeiten aus der BrainFiles-Wurzel; Pfade relativ, nie absolut.
- Python mit Standardbibliothek: `Agenten/Werkzeuge/repos-zentrale/.venv/Scripts/python.exe`
  (traegt kein Fremdpaket — reicht fuer Messung, Leser, Tests).
- Git-Zugriff; Schreiben mit **eigenem Index** (siehe Schritt 10).
- Vor jedem schreibenden Zugriff: `MaxHirn/Wissen/Schutzregeln.md`.

## How to Run

Alle Schritte ueber die Hermes-Werkzeuge: `terminal` fuer Messung und Tests,
`read_file`/`search_files` zum Nachsehen an der Quelle, `patch`/`write_file`
zum Schreiben, `skill_view` fuer die References dieses Skills.

## Quick Reference

```
bestand.cmd                       # eigene Codebasis (Wurzel-Aufrufer)
bestand.cmd --mit-fremd           # beide Zahlen, zum Vergleich
python Agenten/Werkzeuge/fremd.py --pruefen    # Quelle gesund?
python Agenten/Werkzeuge/fremd.py --tabelle    # Anzeige erzeugen
python -m unittest discover -s tests           # je Ordner mit tests/
powershell -File <skill>/scripts/fenster_zaehlen.ps1   # Fensterzahl vor/nach
```

## Procedure

1. **Messen, nicht schaetzen.** Zahl mit und ohne Fremd-Material, je Bereich;
   `os.walk` mit geschnittenen Ordnern (`.venv`, `node_modules`, `__pycache__`,
   `.git`, `cache`, `tools`, `dist`, `build`, `target`). Ein `rglob` oder
   `find -exec cat` laeuft in die venvs und in den Timeout. Details:
   `codebasis-bestand`.
2. **Den Fakt finden, der mehrfach liegt.** `search_files` nach dem Wort, das
   die Aussage traegt (Rolle, Listenname, Pfad). Zaehlen, in wie vielen Dateien
   er steht — erst dann lohnt eine Quelle.
3. **Quelle bauen**: JSON, weil Python UND PowerShell sie lesen (Muster
   `Agenten/MCP-Manifest.json` + `mcp-sync-check.ps1`). Pfade relativ zur Wurzel
   mit `/`, ohne `..`, ohne Laufwerksbuchstaben. Feldliste und Regeln:
   `references/eine-quelle-muster.md`.
4. **Leser bauen** (Standardbibliothek, per Pfad geladen): `laden`, `ist_*`,
   `ohne_*`, `pruefen`, `als_text`. `pruefen` liefert **Befunde** (leer = gesund),
   nicht Wahr/Falsch. Achtung: `sys.modules`-Eintrag VOR `exec_module`.
5. **Anzeige erzeugen und gegen die Quelle pruefen.** Die Markdown-Fassung wird
   aus der JSON erzeugt; ein Test vergleicht die Pfadmengen. Zwei Fassungen ohne
   diesen Test sind zwei Wahrheiten.
6. **Verbraucher anschliessen — ergaenzend, nicht umbauend.** Eine fremde Zeile
   bekommt Rolle und Hinweis, ihre **Gruppe bleibt unveraendert**: fremd heisst
   nicht kaputt. Wurzeln, die der Verbraucher schon kennt, werden HEREINGEREICHT
   statt in der Quelle wiederholt.
7. **Vertragstests ueber alle Objekte.** Nicht ein Objekt pruefen, sondern die
   REGEL fuer jedes: Name passt zum Ordner, Anmeldung vorhanden, Zweitziel
   gesetzt, Stop im Band, Ratsche = Buchrisiko, kein Orderweg, `--live`
   verweigert. Keine festen Zahlen aus dem Monat der Entstehung.
8. **Jede Behauptung einmal echt messen.** "wt -w 0 oeffnet kein neues Fenster"
   ist erst wahr, wenn die Fensterzahl vorher/nachher dasteht. Siehe
   `references/windows-launcher-popouts.md`.
9. **Design-Gate.** Bei einem Umbau ("brainstorm"): erst Spezifikation nach
   `Agenten/Werkzeuge/<werkzeug>/docs/design/JJJJ-MM-TT-<thema>-design.md`,
   committen, dann bauen. Kein Code vor der Zustimmung; danach ist das Doc der
   Beleg, worauf der Plan aufbaut.
10. **Sichern, sofort.** Die Fremdarbeit-Routine committet alles, was >30 min
    uncommittet liegt, unter fremdem Namen — eigene Arbeit also zuegig selbst
    committen. Nur eigene Pfade stagen, mit eigenem Index:
    `export GIT_INDEX_FILE=<scratch>/idx_<thema>` + `git read-tree HEAD` +
    `git add <eigene Pfade>` + `git commit -F <msg>`; danach `unset` und dieselben
    Pfade im echten Index nachziehen.
11. **Doku an vier Stellen**: README des Werkzeugs, Wiki-Seite + `INDEX.md`,
    der Skill, den die Arbeit betrifft, und `MaxHirn/Archiv/TASKS.md` fuer alles,
    was bewusst offen bleibt.

## Pitfalls

- **Die Wurzel nicht verzaehlen.** `parents[1]` von
  `Agenten/Werkzeuge/repos-zentrale` ist `Agenten`, nicht BrainFiles. Ein Test
  mit falscher Wurzel findet null Objekte und bleibt gruen, solange er nur
  "keine Fremden" behauptet — immer zusaetzlich "mindestens einer" pruefen.
- **`@dataclass` in einem per Pfad geladenen Modul braucht `sys.modules`.**
  `module_from_spec` + `exec_module` allein laesst `sys.modules[cls.__module__]`
  leer: `AttributeError: 'NoneType' object has no attribute '__dict__'` — erst
  beim Laden, nie beim Schreiben.
- **Eine Liste traegt Blocker UND Hinweise.** `gruende == []` einzufrieren bricht
  bei jedem neuen Hinweis. Richtig: auf die abgeleitete Gruppe pruefen
  (`gruppe == "startbar"`) plus "kein Grund nennt ein Fehlen".
- **Erst nachrechnen, dann den Code beschuldigen.** Zwei rote Tests waren falsche
  Fixtures (ein Kreuz braucht EINE Sprungkerze; ein EMA-Warmlauf verschiebt den
  Start um `n-1`). Bei jedem Fehlschlag zuerst die Erwartung nachrechnen.
- **Fremde Konfiguration nie per Regex nachbauen.** Ein Suchmuster ueber eine
  Config griff ueber auskommentierte Bloecke und lieferte plausible, falsche
  Werte — die Quelle Zeile fuer Zeile lesen.
- **`write_file` verweigert das Ueberschreiben** einer bestehenden Datei, die in
  dieser Aufgabe nicht vollstaendig gelesen wurde: es kommt `None` statt
  `bytes_written` zurueck, und ein folgendes `git add` nimmt still die ALTE
  Fassung. Rueckgabewert pruefen.
- **Zeilenenden.** Nach jedem Schreiben `git diff --numstat` je Datei: eine
  gewollte Zeile muss wenige Ein-/Ausfuegungen zeigen. Ganze Datei = falsches
  Ende. Wurzel-`.cmd` brauchen CRLF.
- **Neue Dateien sind ohne `.gitignore`-Freigabe unsichtbar** (`!!`): je Endung
  eine Zeile, bei ignoriertem Elternordner zusaetzlich der Ordner selbst.
- **PowerShell liest einen relativen Programmpfad nicht.**
  `Agenten\...\python.exe x.py` endet in "Das Modul 'Agenten' konnte nicht
  geladen werden"; richtig ist `& ".\..."` oder absolut. Fuer oft benutzte
  Werkzeuge gehoert ein Wurzel-Aufrufer hin (`.cmd` mit `%~dp0`).

## Verification

1. `python Agenten/Werkzeuge/fremd.py --pruefen` → "gesund: n Eintraege".
2. Beide Zahlen in einer Zeile: `bestand.cmd` und `bestand.cmd --mit-fremd`.
3. Tests aller beruehrten Ordner gruen (Zentrale, Werkzeuge, Handel).
4. `git diff --numstat` zeigt nur die gewollten Zeilen (keine Ganzdatei).
5. Jede im Bericht genannte Zahl ist in dieser Sitzung gemessen worden — keine
   aus dem Gedaechtnis.

## References

- `references/eine-quelle-muster.md` — laden, wenn eine Quelle gebaut wird:
  Feldliste, Leser-API, die acht Befunde von `pruefen`, Verbraucher-Muster,
  Testformen.
- `references/windows-launcher-popouts.md` — laden, wenn ein Launcher Fenster
  hinterlaesst oder ein Windows-Programm gestartet wird: `wt -w 0`, `cmd /c` mit
  Log, ein Bauplatz, Fensterzahl messen.
- `scripts/fenster_zaehlen.ps1` — die Fensterzahl vor/nach einem Klick.
