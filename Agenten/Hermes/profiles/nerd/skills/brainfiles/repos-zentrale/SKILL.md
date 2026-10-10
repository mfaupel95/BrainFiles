---
name: repos-zentrale
description: "Use when ein Repo, Projekt oder Spur zu starten ist."
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Werkstatt, Repos, Starten, Manifest, Bestandsaufnahme]
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

**Jede Spur ist eine startbare Zeile (30.09.2026).** Eine Spur ist ein Ordner
ohne eigenes venv, ihre Datei heisst nicht immer `handeln.py`. `SPUREN_START` in
`fuellen.py` haelt je Spur das Paar (Skript, Interpreter) - dieselben Paare wie
`dauerlauf.SPUREN`; die zweite Liste dort bleibt die einzige Wahrheit. Der Start
ist **immer `<interpreter> <skript> --vorschau`** (37 Spuren): der lesende Blick
einer Spur, sie schreibt nichts. Ohne `--vorschau` liefe ein voller
Handelszyklus los - das ist Sache des Dauerlaufs, nicht eines Klicks. Der
Interpreter steht relativ zur Spur (`..\scanner\.venv\Scripts\python.exe`,
Nautilus-Arme `..\nautilus\.venv\...`), weil das Arbeitsverzeichnis einer Zeile
ihr eigener Ordner ist.

**Nicht als Zeile aufgenommen: die `handeln.py` der Spuren als DATEI.** Welches Skript
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

## Fremd-Material: benannt, nicht mitgezaehlt

Fremdes liegt mitten in eigenen Ordnern (`Agenten/Handel/OpenAlice` = 81 % der
Zeilen in `Agenten/Handel`). Die Grenze steht EINMAL in
`Agenten/FREMD-Liste.json`, gelesen von `Agenten/Werkzeuge/fremd.py`
(Python) bzw. `ConvertFrom-Json` (PowerShell); lesbare Fassung `Agenten/FREMD.md`,
Bestand `Agenten/Werkzeuge/bestand.py`. Ohne sie zaehlt jede Bestandsfrage 4,2
Mio. Zeilen statt 173.481.

- Die Zentrale zeigt fremde Zeilen mit Herkunft (`fremd: <regel> (<herkunft>)`)
  und nennt die Zahl in der Kopfzeile - sie **gruppiert sie aber nicht anders**:
  fremd heisst nicht kaputt.
- **Nie raten, was fremd ist.** Die acht `klassik_*`-Spuren sahen fremd aus
  (keine Tests, ungetrackt) und waren unser Code vom selben Tag. Ein Eintrag ist
  eine Aussage ueber Herkunft.
- Fremdes wird nicht aufgeraeumt, nur benannt.

## Terminal-Fenster: ein Tab statt vieler Fenster

`wt.exe` oeffnet je Aufruf ein NEUES Fenster - jeder Klick liess eins stehen
(gemessen: acht sichtbare Fenster). Jeder Aufruf in `aktionen.py` traegt deshalb
`-w 0` (Tab im vorhandenen Fenster; gemessen Fensterzahl 1 -> 1). **Ein
Bauplatz**: `fenster.py` enthaelt kein `wt.exe` mehr, ein Test prueft das.
`cmd /c` statt `/k` schliesst den Tab wieder - die Ausgabe geht dann ins Log
(`logs/<ordner>-befehl-<zeit>.log`), sonst waere sie weg.

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

## Bestands-Audit: Duplikate, Missstaende, Startbereitschaft

Auftrag der Art *„die Ordner sind voll, alles auf einer Platte? schau nach
Duplikaten, binde an die Zentrale an, mach die UIs startbereit"*. Reihenfolge
ist nicht beliebig — jeder Schritt liefert die Eingabe fuer den naechsten.

1. **Zuerst die Frage „ein Ort oder zwei?" beantworten, nicht die Dateien
   zaehlen.** `Get-ChildItem <wurzel> -Force | Where-Object { $_.Attributes -band
   [IO.FileAttributes]::ReparsePoint }` — ist einer der genannten Pfade ein
   Verweis, ist es EIN Speicherort, und jede Mengenrechnung ist eine Rechnung
   zu viel. Gemessen: `BrainFiles\Werkstatt` -> `O:\Werkstatt`.
2. **Verweise auflisten, DANN Duplikate suchen.** `scripts/klon-doppel.py`
   (write_file, dann durch `terminal` aufrufen) macht beides in dieser
   Reihenfolge: erst die Reparse-Punkte, dann die Klone nach `origin`
   gruppiert. Ohne Schritt 1 haelt es zwei Pfade derselben Ablage fuer eine
   Dublette.
3. **Groessen messen, nicht schaetzen.** Je Ordner eine Zeile (Dateien + GB) —
   `Get-ChildItem -Recurse -File -Force | Measure-Object Length -Sum` ueber
   `terminal`, NIE `du`: unter der Werkstatt-Junction (→ `O:\`) laeuft `du`
   in Zeitueberschreitungen (gemessen 180 s und 240 s fuer ~15 Ordner),
   PowerShell misst dieselbe Menge in einem Lauf. Die zweite Zahl, die zaehlt:
   wieviel davon venv/node_modules/
   `target`/`.git` ist (wieder herstellbar).
4. **Warum steht eine Zeile in EINRICHTEN?** `scripts/warum-einrichten.py`
   (write_file, durch `terminal` aufrufen) druckt je Zeile Bereich, Gruppe und
   jeden Grund und zaehlt die Gruppen. Ohne diese Sonde behandelt man 86
   Zeilen, von denen 84 in Ordnung sind.
5. **Gruppen ehrlich machen, bevor Startbefehle erfunden werden.** Eine Zeile
   ohne Startbefehl ist nicht automatisch unfertig (fremd + nur lesen,
   geladene Strategieklasse, Werkzeug mit Startverbot) — siehe die Gruppe
   `kein_start` oben. Erst danach fehlende Starts kuratieren.
6. **Jeden neuen Start einmal echt fahren** (`fuellen.py --belege`), sonst
   bleibt `test_manifest_gegenprobe.py` rot.
7. **Verschieben statt loeschen**, wenn etwas weggeraeumt wird: Zielordner
   `Werkstatt/Ausgemustert/<anlass>-JJJJMMTT/`. Nach dem Verschieben die
   Gegenprobe (`Test-Path` auf Quelle UND Ziel) und `--pruefen` — ein
   verschobener Ordner mit Manifest-Eintrag wird sonst FEHLT.
8. **Was du nicht angefasst hast, in `MaxHirn/Archiv/TASKS.md` eintragen**
   (Entscheidungen, die Max braucht) — nicht in die Antwort allein.

### Welche Repos sind ungenutzt? (Nutzungs-Audit)

„Prüfe, welche der Projekte ungenutzt sind“ hat eine feste Kriterienkette —
ein Repo gilt erst als ungenutzt, wenn ALLE sechs Zeugen schweigen:

1. **Bot-Profil über die `cwd`, nicht über den Profilnamen.** Profilnamen sind
   klein und weichen vom Reponamen ab (`nerd` → `claude-red`, `fomo-radar` →
   `fomo-robinhood-radar`). Maßgeblich ist `config.yaml` → `terminal.cwd`;
   ein Repo hat einen Bot, wenn ein Profil-cwd auf `Werkstatt/Repos/<name>`
   zeigt. Die Namensgleichheit allein verliert die Hälfte der Bots.
2. **Startbefehl im Manifest** (`repos-zentrale.json` → `start` nicht leer).
3. **Laufender Prozess:** `Get-CimInstance Win32_Process` mit exaktem
   Pfadmuster `Werkstatt\\Repos\\<name>` in CommandLine ODER ExecutablePath —
   und die EIGENE PID ausschließen (`$_.ProcessId -ne $PID`): der Prüfaufruf
   selbst trägt die Pfade in seiner Kommandozeile und matcht sich sonst
   selbst. Ein bloßer Namens-Regex trifft außerdem fremde Prozesse („skills“
   steht in jeder claude/Kommandzeile) — nie bloße Namen matchen.
4. **Exakte Pfad-Referenzen statt bloßem Namen.** `rg 'Repos/<name>'` in
   Skills/scripts/cron/Routinen/Wissen/Wiki; der bloße Name ist wertlos
   („skills“ 3375, „codex“ 1522, „laya“ 202 Treffer). Wrapper außerhalb der
   Repos zählen als Nutzung (`codex-remote-control.ps1` macht `codex`
   genutzt, obwohl 0 Pfad-Referenzen).
5. **MCP-Manifest:** ein Eintrag unter `disabled` ist KEINE Nutzung
   (`santiment` war seit 13.09. disabled = ungenutzt).
6. **Frisches `.venv` ist das Gegenzeichen:** ein venv, das Tage alt ist,
   heißt „jemand richtet das gerade ein“ — trotz 0 Referenzen NICHT
   anfassen (`foreman`). Alter von `Get-Item <dir>\.venv` → CreationTime.

Danach verschieben (Schritt 7) und das Manifest nachziehen: `gruppe` auf
`ausgemustert` setzen, `notiz` mit „(ausgemustert am JJJJMMTT nach
Werkstatt/Ausgemustert/<name>-JJJJMMTT)“ praefixieren. Dabei `git diff`
LESEN, nicht nur `--numstat`: Einträge ohne vorherige gruppe-Zeile bekommen
sie neu dazu — 36/31 statt 30/30 ist dann korrekt, kein Schaden. Eine
Worktree-Sammlung ohne `.git`-Wahrheit kann ganz außerhalb des Manifests
stehen (`copilot-worktrees`) — fehlt sie dort, ist das kein Widerspruch.

**Ein Repo mit `plugins/`-Unterordner ist KEIN Hermes-Desktop-Plugin.**
Die Plugin-Ordner der Flotte (basic-memory, caveman, claude-code,
everything-claude-code, …) sind Claude-Code-Plugin-Formate (agent-sdk-dev,
code-review, …) und laufen unter claude, nicht in der Hermes-Desktop-App.
Hermes-Desktop-Plugins erkennst du an `desktop/plugin.js` (Standalone) bzw.
`plugins/<id>/desktop/plugin.js` + `plugin.yaml` (unified package);
Katalog-Einträge installiert `hermes plugins install <name>`. Die Antwort
auf „gehört das in Desktop-Plugins?“ ist für die Repo-Flotte also fast
immer NEIN — die echten Kandidaten sind die eigenen GUI-Werkzeuge
(handelszentrale, leitstand, repos-zentrale), ein Bau-Projekt, kein
Klon-Thema.

### Was der Audit typischerweise findet

- **Doppelte Klone:** mehrere Pfade mit derselben `origin`. Zu pruefen ist
  immer, welcher gebaut/belegt ist (Binary, venv, Logbeleg) — der andere geht
  nach `Ausgemustert/`.
- **Ballast in den Klonen:** venv/node_modules/`target`/`.git` sind oft der
  groesste Teil der Sammlung (gemessen 19,42 von 26,26 GB). Nicht anfassen,
  solange die STARTBAR-Zeilen darauf stehen.
- **Fremdes am falschen Ort:** ein Klon im Vault, ein Gitlink ohne Unterbau,
  Docker-Volumen im gesicherten Ordner. Messen, benennen, als Task eintragen.
- **Lose Dateien in einer Arbeitswurzel:** Installer, Plaene, Altskripte.
  Installer gehoeren nach `Ausgemustert/installer-JJJJMMTT/`.

## Die sechs Gruppen

STARTBAR (Befehl belegt UND Abhaengigkeiten da) · EINRICHTEN (es fehlt etwas:
venv, node_modules, Binary) · NEU (Ordner ohne Manifest-Eintrag) · **KEIN
EIGENER START** (richtig so: wird geladen oder ist nur lesbar) · NUR DOKU (kein
Programm, nur Text) · FEHLT (Manifest-Eintrag ohne Ordner).

**KEIN EIGENER START** entstand am 30.09.2026, weil 86 Zeilen in EINRICHTEN
standen und als „86 Sachen sind kaputt" gelesen wurden. Die Bedingung in
`manifest._zeile` ist eng: es darf **kein** anderer Grund vorliegen
(`startgruende == ["kein Startbefehl belegt"]`, ein fehlendes venv bleibt
also EINRICHTEN), und der Grund muss dabeistehen - als kuratierte Gruppe
(`gruppe: kein_start`), als Vermerk (`warnungen`, z. B. aus `fuellen.OHNE_START`)
oder in der FREMD-Liste als `nur lesen`. Wer eine Zeile hierher schiebt, sagt
damit „das ist fertig", nicht „das ist mir zu viel".

**Das Feld `warnungen` wird jetzt gelesen.** `manifest_laden` hat es bis zum
30.09.2026 nie aus der Datei geholt - die Liste startete leer und fuellte sich
nur aus Befehls-Fehlern. Ein Vermerk, den niemand sieht, ist keiner.

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

- **Ein Duplikat-Scan laeuft ueber Junctions in die Irre.** `Werkstatt/Repos/
  intelligent-trading-bot` ist eine **Junction** auf `Werkstatt/
  intelligent-trading-bot`: derselbe Inhalt unter zwei Pfaden, gleicher
  Fingerabdruck, gleiche Groesse - das sieht wie eine Dublette aus und ist EINE
  Ablage. Beim Verschieben des „Duplikats" wanderte der echte Ordner weg, die
  Junction zeigte ins Leere und die Zeile stand als FEHLT im Fenster. Vor jedem
  Duplikat-Urteil die Reparse-Punkte auflisten:
  `Get-ChildItem <wurzel> -Force -Recurse -Depth 1 | Where-Object { $_.Attributes
  -band [IO.FileAttributes]::ReparsePoint }`. Unter `O:\Werkstatt` gibt es genau
  einen (diesen); unter `Agenten\Hermes\skills` die sieben `okx-*`.
- **Ein per Pfad geladenes Modul mit `@dataclass` braucht einen
  `sys.modules`-Eintrag.** `importlib.util.module_from_spec` + `exec_module`
  allein laesst `sys.modules[cls.__module__]` leer; dataclasses bricht dann mit
  `AttributeError: 'NoneType' object has no attribute '__dict__'` ab - erst beim
  Laden. Vor `exec_module` ein `sys.modules[<name>] = modul` setzen (so laedt
  `quellen.fremd_modul()` das Fremd-Modul).
- **Die Wurzel nicht verzaehlen.** `Path(__file__).resolve().parents[1]` ist von
  `Agenten/Werkzeuge/repos-zentrale` aus `Agenten`, nicht BrainFiles - ein Test
  mit dieser Wurzel findet null Dateien und bleibt gruen, solange er nur
  "keine Fremden" behauptet. Richtig: `parents[2]` oder der Anker aus
  `fremd.wurzel()`.
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
- **`repos-zentrale.json` mit `indent=2` schreiben, sonst ist der Diff die ganze
  Datei.** Die Datei ist 2-Space-formatiert (LF); ein `json.dump(..., indent=1)`
  oder `indent=4` formatiert JEDE Zeile um und `git diff --numstat` zeigt
  3106/3065 statt der einen Zeile. Nach dem Schreiben `git diff --numstat`
  pruefen: zeigt es die ganze Datei, mit `indent=2` neu schreiben (und
  `ensure_ascii=False`, LF, abschliessendes Newline). Derselbe Test
  `test_manifest_gegenprobe` verlangt ausserdem einen Logbeleg in `logs/` fuer
  jeden Startbefehl — `fuellen.py --belege` erzeugt ihn automatisch, ein
  manuell eingetragener `start` ohne Log bleibt rot.

## Verwandtes

- Massenweg: `Agenten/Werkzeuge/repos-launcher.ps1 -Mode Terminal|Tui|Gui`
  (`Tui` braucht lazygit, das auf diesem Rechner fehlt).
- Ein Bot je Repo, Telegram-Zugriff (`/bots`, `/bot NAME ...`): `repo-flotte`.
- Fremd-Agenten schluessellos betreiben: `fremd-agenten-betrieb`,
  `fremdrepo-agent-start`.
