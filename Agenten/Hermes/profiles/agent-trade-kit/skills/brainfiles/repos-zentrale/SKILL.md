---
name: repos-zentrale
description: "Use when ein Repo aus Werkstatt gestartet wird."
license: MIT
metadata:
  hermes:
    tags: [werkstatt, repos, starten, manifest, werkzeuge]
    related_skills: [repo-flotte, fremd-agenten-betrieb, fremdrepo-agent-start]
---

# Repos-Zentrale: Projekte unter Werkstatt erreichen

`Agenten/Werkzeuge/repos-zentrale` ist das Startfenster fuer alle Projekte unter
`Werkstatt` (28 Repos, ein Hermes-Bot je Repo). Es ersetzt das Suchen nach
dem "richtigen" Startweg je Repo: die Befehle stehen im Manifest, die Gruppen
sagen, ob etwas fehlt.

## Wann
"X starten", "Zugriff auf Projekt Y", ein neues Repo aufnehmen, ein Startbefehl
soll hinterlegt werden, oder die Frage "warum geht Projekt Z nicht".

## Aufrufen

```
cd Agenten/Werkzeuge/repos-zentrale
.venv/Scripts/pythonw.exe repos_zentrale.py          # Fenster
.venv/Scripts/python.exe   repos_zentrale.py --pruefen   # nur auflisten, kein Fenster
.venv/Scripts/python.exe   -m unittest discover -s tests
```

`--pruefen` ist der schnelle Beleg ohne Fenster: nennt je Gruppe jedes Repo und
seinen Startbefehl und markiert Auffaelligkeiten (NEU/FEHLT).

## Die fuenf Gruppen

STARTBAR (Befehl belegt UND Abhaengigkeiten da) · EINRICHTEN (es fehlt etwas:
venv, node_modules, Binary) · NEU (Ordner ohne Manifest-Eintrag) · NUR DOKU
(kein Programm) · FEHLT (Manifest-Eintrag ohne Ordner).

## Ein Repo aufnehmen oder einen Start hinterlegen

1. Manifest-Eintrag in `repos-zentrale.json`: `ordner`, `art`, `bot` (Profilname,
   klein), `notiz`.
2. Den Startbefehl **einmal echt laufen lassen** — erst danach als `start`
   eintragen. Die Logdatei in `logs/` ist der Beleg;
   `tests/test_manifest_gegenprobe.py` prueft, dass kein Befehl ohne Log dasteht.
3. Pflichtangaben mitdenken: `venv_pflicht` (Python), `node_modules_pflicht`
   (Node), `pfad_pflicht` (z. B. `target\release\x.exe`). Fehlt das Genannte,
   landet das Repo ehrlich in EINRICHTEN statt in STARTBAR.
4. Danach `--pruefen` und die Tests laufen lassen.

## Manifest-Regeln (der Code setzt sie durch)

- `start`/`einrichten`/`bauen` sind **argv-Listen**, nie Shell-Zeichenketten.
- **Kein geratener Befehl.** Fehlt er, ist das der Zustand "kein Startbefehl
  belegt" — kein Fehler, kein Platzhalter.
- Die **Platte schlaegt das Manifest** beim Zustand (venv, node_modules, README,
  Pflichtpfad werden live geprueft). Ein Klon ohne Eintrag verschwindet nicht,
  er wird NEU.
- Bot-Namen klein; fehlt das Profil, ist der Knopf deaktiviert und nennt den
  Grund.

## Fallen

- **Relativer Programmpfad scheitert unter Windows.**
  `Popen([".venv\\Scripts\\pythonw.exe"], cwd=<repo>)` wirft FileNotFoundError,
  weil Windows argv[0] gegen das Arbeitsverzeichnis des AUFRUFERS aufloest. Vor
  dem Start gegen `cwd` aufloesen (`aktionen.start_ausfuehren` tut das) — in
  einem eigenen Werkzeug dieselbe Zeile einbauen.
- **"Ist X installiert?" nie mit `which` entscheiden.** Die bash/MSYS-PATH sieht
den Windows-PATH nicht (VS Code liegt in
  `AppData\Local\Programs\Microsoft VS Code\bin\code.cmd`, `which code.cmd`
  findet nichts). Mit PowerShell `Get-Command` pruefen — sonst entsteht ein
  Falschbefund, der in einer Spezifikation landet.
- **Ein neuer Ordner unter `Agenten/Werkzeuge/` ist ohne .gitignore-Zeilen
  unsichtbar** (`!!`). Je Endung eine Freigabe **plus eigene Zeile fuer jeden
  Unterordner** (`tests/`, `docs/design/`): ein `!dir/*.py` greift nicht, solange
  der Ordner selbst ignoriert ist. Gegenprobe: `git add --dry-run <ordner>`.
- **Hilfsskripte nicht nach `Agenten/Routinen/`.** Dort gilt jede `.ps1` als
  Routine: `Bus/tests/test_anbindung_routinen.py` verlangt in JEDER Datei
  Melde-Start, Melde-Ende unmittelbar vor jedem `exit` und den Namen
  `routine/<name>`; Ausnahmen sind `einmalig-*`, `*-hook.ps1` und der Vermerk
  `BUS: Bibliothek` im Kopf. Ein Einmal-Skript gehoert umbenannt auf
  `einmalig-JJJJMMTT-<name>.ps1`.
- **Beim Testen eines Launchers keine Fensterflut ausloesen.**
  `repos-launcher.ps1 -Mode Gui` oeffnet je Repo ein VSCode-Fenster (28 Stueck,
  je mehrere Prozesse). Vorher `-Repos <eins>` setzen. Nach einem versehentlichen
  Lauf nur Prozesse beenden, deren Startzeit im eigenen Testfenster liegt.

## Verwandtes

- Massenweg: `Agenten/Werkzeuge/repos-launcher.ps1 -Mode Terminal|Tui|Gui`
  (`Tui` braucht lazygit, das auf diesem Rechner fehlt).
- Ein Bot je Repo, Telegram-Zugriff (`/bots`, `/bot NAME ...`): `repo-flotte`.
- Fremd-Agenten schluessellos betreiben: `fremd-agenten-betrieb`,
  `fremdrepo-agent-start`.
