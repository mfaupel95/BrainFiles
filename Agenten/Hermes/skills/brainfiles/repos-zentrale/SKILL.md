---
name: repos-zentrale
description: "Use when ein Repo, Werkstatt-Projekt oder Handelsspur gestartet oder aufgenommen wird."
license: MIT
metadata:
  hermes:
    tags: [werkstatt, repos, starten, manifest, werkzeuge]
    related_skills: [repo-flotte, fremd-agenten-betrieb, fremdrepo-agent-start]
---

# Zentrale: Repos, Werkstatt und Handel erreichen

`Agenten/Werkzeuge/repos-zentrale` ist das Startfenster fuer **drei Bereiche**:
`Werkstatt/Repos` (46 Klone mit eigenem Bot), `Werkstatt` samt
`Werkstatt/Projekte` (eigene Projekte, Datenfelder, Ablagen) und
`Agenten/Handel` (45 Ordner und die Werkzeugdateien der Wurzel). Es ersetzt das
Suchen nach dem "richtigen" Startweg je Projekt: die Befehle stehen im Manifest,
die Gruppen sagen, ob etwas fehlt.

## Wann
"X starten", "Zugriff auf Projekt Y", "wo liegt nochmal ...", ein neues Repo oder
Projekt aufnehmen, ein Startbefehl soll hinterlegt werden, oder die Frage "warum
geht Projekt Z nicht". Auch der schnellste Weg zu einer Handelsspur oder einem
Handelswerkzeug (`--pruefen --bereich HANDEL`).

## Aufrufen

```
cd Agenten/Werkzeuge/repos-zentrale
.venv/Scripts/pythonw.exe repos_zentrale.py                   # Fenster
.venv/Scripts/python.exe   repos_zentrale.py --pruefen        # nur auflisten, kein Fenster
.venv/Scripts/python.exe   repos_zentrale.py --pruefen --bereich HANDEL
.venv/Scripts/python.exe   messprobe.py                       # Layout messen (Spaltenbreiten)
```

`--pruefen` ist der schnelle Beleg ohne Fenster: nennt je Bereich jede Gruppe
und jeden Startbefehl und markiert Auffaelligkeiten (NEU/FEHLT).

## Die drei Bereiche (seit 30.09.2026)

Die Wurzeln stehen in `quellen.py` - Pfade **relativ**, keine absoluten:

| Bereich | Wurzel | Was eine Zeile bekommt |
|---|---|---|
| REPOS | `Werkstatt/Repos` | nur Ordner mit `.git` |
| WERKSTATT | `Werkstatt` + `Werkstatt/Projekte` | jeder Ordner |
| HANDEL | `Agenten/Handel` | jeder Ordner **und** jede Werkzeugdatei mit `__main__` UND `argparse` |

In jeder Wurzel gesperrt (Namensliste, kein Muster): `.venv`, `venv`,
`node_modules`, `__pycache__`, `.git`, `.vscode`, `cache` und Konsorten.
Die Wurzel wird nur an der Oberflaeche durchsucht. Werkzeuge in **Unterordnern**
stehen darum namentlich in `quellen.WERKZEUG_ZUSATZ` (Pfad mit `/`, ohne `..`) -
eine Liste, keine Suche: unter `Agenten/Handel/OpenAlice` liegen 130 Dateien
eines fremden Projekts, die sonst als Zeilen auftauchen. Eine `--help`-Angabe
bekommt nur, wer einmal gelaufen ist (`fuellen.HILFE_VERIFIZIERT`).

**Nicht als Zeile aufgenommen: die 30 `handeln.py` der Spuren.** Welches Skript
eine Spur fahrt, steht in `dauerlauf.py` (`SPUREN`) - meist gar kein
`skript`-Feld (Vorgabe `handeln.py`), aber `nautilus_kraken_futures` teilt sich
den Ordner `nautilus_kraken` und faehrt `handeln_futures.py`. Diese Liste im
Manifest nachzubauen waere eine dritte Wahrheit; wer den Stand einer Spur will,
nimmt `spuren_stand.py` oder `sperrgruende.py` (sie fragen jede Spur selbst).

**Strategien** sind drei Sorten und alle drei sind Zeilen: Spuren (`Spur`),
Freqtrade-Klassen (`Strategie`, kein Start - freqtrade laedt sie) und Backtests
(`Backtest`). Die **drei Risikostufen** Basis/mittel/hoch sind kein eigener
Eintrag: dieselben Spuren mit groesseren Betraegen in eigenen Dateien, sichtbar
ueber `spuren_stand.py` (Spalte Buch: `haupt/.mittel/.hoch`),
`auswertung_alle.py --risiko mittel|hoch` und `spiegelstand.py --risiko ...`.

## Das Manifest fuellen

`fuellen.py` traegt ein, was auf der Platte liegt und fehlt. Notiz und Art kommen
aus dem Projekt SELBST (README-Ueberschrift, sonst Modul-Docstring), Rolle und
Startbefehle aus der kuratierten Tabelle im Skript.

```
.venv/Scripts/python.exe fuellen.py                            # Trockenlauf
.venv/Scripts/python.exe fuellen.py --anwenden                 # schreiben (+ .bak)
.venv/Scripts/python.exe fuellen.py --belege                    # jeden Start ohne Log einmal ausfuehren
.venv/Scripts/python.exe fuellen.py --auffrischen --anwenden    # nur FEHLENDE Felder nachtragen
```

Vorhandene Eintraege bleiben unangetastet - Handarbeit wird nie ueberschrieben.
Ein neuer Ordner erscheint auch ohne Lauf als NEU; eine neue Datei bekommt
KEINEN Startbefehl, bis ihr Aufruf einmal belegt ist.

## Die Klone aktuell halten

```
python Agenten/Werkzeuge/repos-updaten.py --trocken            # nur zeigen
python Agenten/Werkzeuge/repos-updaten.py                      # vorspulen
python Agenten/Werkzeuge/repos-updaten.py --nur ProjectAtlas   # einzelne
python Agenten/Werkzeuge/repos-updaten.py --ausser <repo>      # nur messen
```

Je Klon: Quelle bestimmen (**upstream hat Vorrang vor origin**), deren
Standardzweig erfragen (`main`/`master`/`dev`/`v8`/`github-main` — nicht raten),
fetchen und **nur vorspulen** (`--ff-only`). Nie Merge, nie Rebase, nie Push.
Schmutzig heisst nur: eine Aenderung an einer **verfolgten** Datei. Ein untracked
`.env.template` — das tragen fast alle Klone — sperrt nicht.
Zustand: `Agenten/Hermes/cache/repos-update.json`.

Vier Faelle, in denen der Lauf **nichts** tut (alle stehen im Bericht):

| Stand | Grund |
|---|---|
| `ausgenommen (laeuft)` | Repo steht in `AUSGENOMMEN` im Skript (`moon-dev-ai-agents`) — dort laeuft ein Prozess; wird gemessen, nie gespult |
| `uebersprungen (lokale Aenderungen)` | Aenderung an einer verfolgten Datei — erst Max fragen, nichts verwerfen |
| `anderer Zweig` | lokaler Zweigname weicht vom Quell-Standardzweig ab (`JEV`, `Werkstatt`) — das Skript raet nicht |
| `fetch fehlgeschlagen` / `Vorspulen fehlgeschlagen` | Netz oder shallow; shallow-Klone holt das Skript einmal mit `--unshallow` |

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
- Ein Eintrag traegt `wurzel` (Vorgabe `repos`) und `pfad` (Vorgabe = `ordner`);
  der **Schluessel ist das Paar (wurzel, pfad)**. Zwei Wurzeln duerfen denselben
  Namen tragen (`OmniRoute` in `Werkstatt` und in `Werkstatt/Projekte`).
- `rolle` ist Klartext fuer die Spalte (Spur, Werkzeug, Modell, MCP-Server,
  Ablage); `warnungen` sind Vermerke, die den Start NICHT sperren.
- **Kein geratener Befehl.** Fehlt er, ist das der Zustand "kein Startbefehl
  belegt" - kein Fehler, kein Platzhalter.
- Die **Platte schlaegt das Manifest** beim Zustand (venv, node_modules, README,
  Pflichtpfad werden live geprueft). Ein Ordner ohne Eintrag verschwindet nicht,
  er wird NEU.
- Bot-Namen klein; **fehlt das Profil, gehoert der Name nicht ins Manifest** -
  der Bot-Knopf waere ein Knopf ins Leere (Test
  `test_jedes_bot_profil_des_manifests_existiert`). Weggelegte Profile liegen als
  9-Byte-Vermerk in `profiles/.deleted/`.

## Fallen

- **Eine Konfiguration nie per Regex nachbauen.** `dauerlauf.SPUREN` mit einem
  Suchmuster zu lesen lieferte plausible, aber falsche Werte (der Ausdruck griff
  ueber auskommentierte Bloecke und zog deren Werte in den vorigen Eintrag:
  angeblich `swap -> spiegel.py`, tatsaechlich Vorgabe `handeln.py`). Wer eine
  Liste aus einer anderen Quelle uebernimmt, liest sie Zeile fuer Zeile nach.
- **Feste Spaltenbreiten bei skalierter Anzeige.** Mit `dpi_bewusst()` setzt Tk
  die Schrift in Geraetepixeln; auf 125 % (`winfo_fpixels('1i')` = 120) braucht
  ein 41-Zeichen-Hinweis 410 px. Breiten also aus der wirklichen Baumbreite und
  dem DPI-Faktor rechnen (`fenster.spaltenbreiten`), NIE fest eintragen - und
  jede Spalte auf `stretch=False` setzen, sonst verteilt Tk die Restbreite
  selbst und die Rechnung gilt nicht. Nachpruefen mit `messprobe.py`.
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
- **Shallow-Klon bricht beim Vorspulen ab.** Mit `--depth=1` fehlt der
  gemeinsame Vorfahr, `merge --ff-only` sagt `refusing to merge unrelated
  histories` — gemessen am 21.09.2026 an OpenTerminal (1 Commit) und santiment
  (4). Das Werkzeug holt dann die Historie nach (`fetch --unshallow`) und spult
  erneut; von Hand ist das der Weg.
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
