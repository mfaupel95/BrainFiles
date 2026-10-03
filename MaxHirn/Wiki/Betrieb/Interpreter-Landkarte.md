---
id: 20260930-interpreter-landkarte
title: 'Betrieb — Interpreter-Landkarte'
tags: [betrieb, python, venv]
created: 2026-09-30
updated: 2026-09-30
related: ['[[Betrieb/Docker-und-Sandbox]]', '[[Lektionen/Windows-Umgebung]]', '[[Betrieb/Hermes]]']
summary: 'Welcher Python gehoert zu welcher Komponente, und wie man den falschen erkennt, bevor er stumm scheitert.'
---

# Interpreter-Landkarte

## Regel

**Jedes Skript laeuft mit dem Interpreter SEINER Komponente, und der Beweis ist
eine Importprobe — nicht der Pfad, den man getippt hat.**

```bash
<venv>/Scripts/python.exe -c "import sys; print(sys.executable); import <paket>"
```

Wer nur `python` schreibt, bekommt den Interpreter der aufrufenden Umgebung.
Unter Windows ist das je nach Startweg ein anderer: Hermes-Cron, Docker-Sandbox,
geplante Aufgabe und Handstart haben vier verschiedene Pythons.

## Die Landkarte (gemessen 30.09.2026)

| Ort | Interpreter | Wofuer |
|---|---|---|
| `Agenten/Handel/scanner/.venv` | 3.13.15 | **die Handels-Spuren** (`handeln.py`, `okx.py`, `kraken.py`, `lage.py`) — kein numpy |
| `Agenten/Handel/.venv` | 3.13.15 | **numpy/pandas** (`strategie_metrics.py`, `strategie_kennzahlen.py`) |
| `Agenten/Handel/verbesserer/.venv` | 3.13.15 | Bewertung/Verbesserer |
| `Agenten/Handel/nautilus/.venv`, `nautilus_rc5/.venv` | 3.13.15 | Nautilus-Arme (eigenes Repo) |
| `Agenten/Hermes/hermes-agent/venv` | 3.11.16 | Hermes-Checkout — **Handproben** (303 Pakete) |
| `Agenten/Hermes/tools/python-3.14.7…` | 3.14.7 | Gateway/Launcher; `site-packages` traegt **nur pip**, Fremdpakete liegen in `installs/<hash>/environments/<id>/venv` |
| `Agenten/MCP-Server/<server>/.venv` | 3.13.15 | je MCP-Server (`.venv.bak-20260918` = alte uv-Bauer) |
| `Agenten/Werkzeuge/repos-zentrale/.venv` | 3.13.15 | Startfenster der Repos |
| `Werkstatt/Repos/<repo>/.venv` | je Repo | Fremd-Repo-Agenten (10 Klone) |
| Docker-Sandbox (`hermes-*`) | eigener Python | `terminal`/`execute_code`; Host-Pfade (`C:/…`) sind dort nicht dieselbe Welt |

**Hermes-Cron-Wachen laufen unter dem Interpreter von Hermes, nicht in der venv
der Komponente.** Eine Wache darf deshalb nur die Standardbibliothek importieren
und Fachmodule ueber den PFAD laden (`importlib.util.spec_from_file_location`),
nie ueber `sys.path`.

## Wie der falsche Interpreter aussieht

- **Laut:** `ModuleNotFoundError: No module named 'pandas'` — das Paket fehlt im
  gerade laufenden Interpreter, nicht auf dem Rechner.
- **Leise:** ein per `subprocess` gestartetes Kind erbt `sys.executable` des
  **Aufrufers** (z. B. `scanner/.venv`) statt der venv der Komponente; das Kind
  laeuft mit falschen Paketen weiter und liefert still falsche Ergebnisse.
- **Leise und hartnäckig:** `PYTHONHOME`/`PYTHONPATH` aus einem uv-venv
  vergiften jedes Kind (`Fatal Python error: init_import_site`). Vor Aufrufen aus
  einer MCP-Session `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH`.

## Nachweis, dass es ein Muster ist (nicht ein Vorfall)

Rueckschau der Sitzungen vom 01.-30.09.2026 (390 Transkripte):

```
python Agenten/Hermes/skills/claude-code-imports/rueckschau/sitzungen_auswerten.py --umwege --seit 2026-09-01
  Modul nicht gefunden     41 Sitzungen / 14 Tage / 251 Treffer
  Falscher Interpreter     18 Sitzungen /  6 Tage /  66 Treffer
```

Dazu die Befehlsseite: **2026 der 11.735 Befehle** nennen einen venv-Pfad, und
dasselbe Skript wurde ueber drei verschiedene venv-Wurzeln aufgerufen
(`scanner/.venv` 318x, `Handel/scanner/.venv` 145x, `Handel/verbesserer/.venv`
134x). Der Umweg ist also nicht „einmal falsch getippt", sondern wiederkehrend.

## Der kuerzeste Weg zur richtigen venv

1. Welche Komponente ist es? (Spur, Werkzeug, Wache, Fremd-Repo) -> Tabelle oben.
2. `cd` in ihren Ordner und den Interpreter **relativ** aufrufen
   (`.venv/Scripts/python.exe`), nicht mit absolutem Pfad aus einem anderen Baum.
3. Importprobe vor dem echten Lauf, wenn das Skript Pakete braucht.
4. Beim Starten von Kindern den Pfad gegen das `cwd` des Kindes aufloesen — ein
   relativer Programmname in `argv[0]` gilt gegen das Arbeitsverzeichnis des
   AUFRUFERS.