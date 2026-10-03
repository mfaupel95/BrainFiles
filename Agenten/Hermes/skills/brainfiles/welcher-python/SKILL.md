---
name: welcher-python
description: "Use when ein Python-Aufruf den falschen Interpreter trifft."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
category: brainfiles
metadata:
  hermes:
    tags: [python, venv, interpreter, ModuleNotFoundError, subprocess, brainfiles]
    related_skills: [fremdrepo-agent-start, dauerprozess-bewachen, windows-host-zugriff, trugschluesse]
---

# Den richtigen Interpreter waehlen und belegen

Dieser Rechner hat **sechs bis acht Pythons** (Handels-venvs, Hermes-Checkout,
Hermes-`tools`, je ein MCP-Server-venv, je Fremd-Repo ein venv, dazu die
Docker-Sandbox). `python` allein heisst "der Interpreter der aufrufenden
Umgebung" — welcher das ist, entscheidet der STARTWEG.

Die Pfade, Versionen und die Herkunft der Zahlen stehen in
`MaxHirn/Wiki/Betrieb/Interpreter-Landkarte.md`. Dieser Skill ist das Verfahren.

## Wann

- `ModuleNotFoundError` / `No module named 'x'`, obwohl das Paket installiert ist
- ein Skript rechnet **stumm** falsch (falsche Version, leere Liste, keine Daten)
- ein Kindprozess verhaelt sich anders als derselbe Aufruf von Hand
- ein Hermes-Cron-Skript stirbt, waehrend es interaktiv laeuft
- `Fatal Python error: init_import_site ... start_joinable_thread`

## Ablauf

1. **Komponente benennen, dann Interpreter.** Welcher Teil ist es — Handels-Spur,
   Werkzeug, Wache, Fremd-Repo? Die venv gehoert zur KOMPONENTE, nicht zum Skript.
   Tabelle in der Wiki-Seite.
2. **Relativ aus dem Ordner der Komponente aufrufen**
   (`cd <komponente> && .venv/Scripts/python.exe <skript>`). Ein absoluter Pfad
   aus einem fremden Baum ist der haeufigste Fehler — dasselbe Skript wurde
   gemessen ueber drei verschiedene venv-Wurzeln gestartet.
3. **Importprobe statt Vertrauen** — sie ist der Beleg, dass der richtige laeuft:
   `<venv>/Scripts/python.exe -c "import sys; print(sys.executable); import <paket>"`.
   `sys.executable` ausgeben, nicht annehmen.
4. **Erst dann den echten Lauf** und die Ausgabe pruefen (nicht den Exit-Code:
   ein falscher Interpreter endet oft mit 0).

## Pitfalls

- **`subprocess` erbt `sys.executable` des AUFRUFERS.** Ein Treiber im
  `scanner`-venv startet sein Kind damit im `scanner`-venv, auch wenn das Kind
  die venv des Fremd-Repos braucht. Den Interpreter des Kindes **explizit**
  setzen (Pfad aus der Repo-Konfiguration), nie erben lassen.
- **Ein relativer Programmname in `argv[0]` gilt gegen das Arbeitsverzeichnis
  des Aufrufers**, nicht gegen das `cwd` des Kindes —
  `Popen([".venv\\Scripts\\python.exe", …], cwd=<repo>)` faellt mit
  `FileNotFoundError` um. Programmpfad vorher absolut machen.
- **Hermes-Cron-Wachen laufen unter dem Interpreter von Hermes**, nicht in der
  venv der Komponente. Nur Standardbibliothek importieren und Fachmodule per
  PFAD laden (`importlib.util.spec_from_file_location`) — nicht ueber `sys.path`
  (ein Eintrag verdeckt gleichnamige Module).
- **`PYTHONHOME`/`PYTHONPATH` vergiften die Kette.** Ein uv-venv setzt
  `PYTHONHOME` in die eigene Prozessumgebung, jedes Kind erbt es und stirbt mit
  `init_import_site`. Vor Aufrufen aus einer MCP-Session entfernen:
  `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH`.
- **Das `tools`-Python von Hermes traegt absichtlich nur `pip`.** Handproben
  laufen mit dem Checkout-venv (`hermes-agent/venv`) oder mit dem venv der
  Komponente; wer im `tools`-Python ein Paket sucht, sucht im leeren Ordner.
- **Die Sandbox ist ein anderer Rechner.** `terminal`/`execute_code` laufen im
  Docker-Container mit eigenem Python; Host-Pfade und Host-Pakete sind dort nicht
  dieselbe Welt. Host-Arbeit ueber windows-mcp fahren.
- **Ein fehlendes Paket ist kein Beweis fuer einen fehlenden Interpreter.**
  Erst `sys.executable` und `pip list` im LAUFENDEN Interpreter zeigen, dann
  installieren — sonst installiert man in den falschen Baum.

## Verification

Fertig ist es, wenn `sys.executable` der Komponente entspricht UND die
Importprobe aller gebrauchten Pakete ohne Fehler durchlaeuft UND der echte Lauf
seine erwartete Ausgabe liefert (nicht nur Exit 0).

## Abgrenzung

- Start eines Fremd-Repo-Agenten (venv anlegen, .env, Fenster): `fremdrepo-agent-start`
- Wachen/Cron bauen und belegen: `dauerprozess-bewachen`
- Zahlen und Pfade: `MaxHirn/Wiki/Betrieb/Interpreter-Landkarte.md`
