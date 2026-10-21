# Repos-Zentrale — Design

Stand: 18.09.2026. Von Max am 18.09.2026 freigegeben (Auswahl „A" von drei
Ansaetzen). Ort des Vorhabens: `Agenten/Werkzeuge/repos-zentrale/`.

## 1. Ziel

Ein Fenster, aus dem **jedes** Projekt unter `Werkstatt/` zuverlaessig zu
erreichen ist: oeffnen, Terminal, starten, mit seinem Bot sprechen, Doku lesen.
Heute ist „starten" ein Sammelbegriff fuer fuenf verschiedene Dinge (Fenster,
Prozess, Skript, Bau, Doku) und deshalb nicht verlaesslich.

**Erfolgskriterien** (messbar, nicht beschreibbar):

1. Aus dem Fenster heraus startet `moon-dev-ai-agents` (MoonDev-GUI) und das
   Protokoll zeigt den Lauf.
2. Aus dem Fenster heraus laeuft `ProjectAtlas` (fertige Binary bzw. `cargo run`)
   bis zur ersten Ausgabe.
3. Aus dem Fenster heraus meldet `Agent-Reach doctor` seine Kanaele.
4. Jede Zeile der Liste nennt ihre Gruppe (startbar / einrichten / nur Doku) und
   ob eine venv auf der Platte liegt — nachpruefbar gegen `ls Werkstatt/`.
5. Ein Repo, das noch nie gestartet wurde, steht im Manifest **ohne**
   Startbefehl und wird nicht geraten.

## 2. Ausgangslage (gemessen am 18.09.2026, nicht erinnert)

- Die Desktop-Verknuepfung „Hermes" zeigt auf
  `…\MaxHirn\Hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`.
  **Diesen Pfad gibt es nicht mehr.** Ein Klick startet nichts. Die laufende App
  liegt unter `Agenten\Hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`.
- `Agenten\Routinen\repos-launcher.ps1` (genau fuer „Repos starten" gebaut) wirft
  im Modus `Tui` ab (`lazygit.exe` fehlt) und im Modus `Gui` (`code.exe` fehlt,
  VSCode ist auf dem Rechner nicht installiert). Modus `Terminal` laeuft, oeffnet
  aber nur leere PowerShell-Tabs je Repo — es startet nichts.
  **Korrektur vom selben Tag:** VSCode IST installiert
  (`AppData\Local\Programs\Microsoft VS Code\bin\code.cmd`) — der erste Befund
  kam aus einer Pruefung ueber die bash-PATH, die den Windows-PATH nicht sieht.
  Falsch war also nur der `lazygit`-Teil; `code.cmd` findet PowerShell sehr wohl.
  Das Skript wurde zusaetzlich nie versioniert (es lag nur auf der Platte) und
  liegt jetzt als Werkzeug unter `Agenten\Werkzeuge\`.
- Bestand: **28 Git-Repos** in `Werkstatt/`, dazu `copilot-worktrees` (kein
  `.git`) und `.vscode`. **28 Hermes-Bots**, einer je Repo.
- Nur **4 Repos haben eine venv**: `Agent-Reach`, `moon-dev-ai-agents`,
  `openmontage`, `Trading-View-MCP-for-AI-by-Moon-Dev`.
- **Kein einziges Repo hat `node_modules`** — jedes JS-Repo braucht erst
  `npm install`. `node v24.19.0`, `npm 11.17.0`, `cargo 1.98.1`, `uv 0.12.5` sind
  vorhanden, `lazygit` und `code` nicht.
- Die geplante Aufgabe `MaxHirn-MoonDev-GUI` ist **nicht registriert**; `moongui.py`
  wird ueber ein VBS im Startup-Ordner gestartet. Die Desktop-Verknuepfung
  „moongui.py" zielt direkt auf die `.py`-Datei statt auf den Wrapper.
- Neue Ordner unter `Agenten/Werkzeuge/` sind ohne `.gitignore`-Freigabezeilen
  unsichtbar (`git status --ignored` → `!!`).

## 3. Warum GUI — und wofuer CLI und TUI bleiben

| Form | Rolle hier | Begruendung |
|---|---|---|
| **GUI** | **Hauptflaeche** | Jeder gemeldete Fehler ist ein Fenster, das nicht kommt. Ein Fenster mit Startknoepfen und belegtem Status loest genau das, ohne Tippen. |
| **CLI** | Automatisierung, **durch den Agenten** | Nicht Max tippt — Hermes ruft dieselben Startbefehle auf (aus Telegram oder dem Desktop). Deshalb liegen die Befehle im Manifest, nicht im Skript. |
| **TUI** | optional (Git im Terminal) | Braucht `lazygit`, bringt fuer „Projekte erreichen" nichts. Nicht Teil dieses Auftrags. |
| **Bot-Chat** | der Arbeitsweg | 28 Profile existieren schon; der Chat ist der Weg, in einem Projekt zu *arbeiten*, das Fenster der Weg, es zu *oeffnen*. |

Leitsatz: **GUI zum Starten und Ueberblicken, CLI zum Automatisieren (durch den
Agenten), Bot fuer die Arbeit, TUI nur wenn ausdruecklich gewuenscht.**

## 4. Dateien und Verantwortlichkeiten

| Datei | Verantwortung |
|---|---|
| `repos-zentrale.py` | Das Fenster: Liste, Gruppen, Filter, 5 Aktionen je Zeile, Log. Nur Standardbibliothek (tkinter), keine Fremdpakete. |
| `repos-zentrale.json` | Das **Manifest**: je Repo die Startbefehle, das Bot-Profil, optional Port und Notiz. Die einzige Stelle, an der ein Startbefehl steht. |
| `.venv/` | Eigene kleine venv der Zentrale (Python 3.13, nur Standardbibliothek). Haengt an **keiner** Repo-venv. |
| `logs/` | Laufzeit: eine Logdatei je Start (`<repo>-JJJJMMTT-HHMM.log`). Nicht versioniert. |
| `repos-zentrale.ps1` | Optionaler fensterloser Wrapper (Anmeldung +2 Min). Erst nach Freigabe, nicht Teil von Stufe 1. |
| `docs/design/`, `docs/plans/` | Diese Spezifikation und der Implementierungsplan. |
| `.gitignore` | Vier Freigabezeilen fuer den neuen Ordner (Muster wie `Agenten/Handel/docs/`). |

Die Zentrale **besitzt** das Repo nicht: sie liest die Platte und ruft Befehle auf.
Fremde Repos werden nie verändert.

## 5. Fenster

    [ Suchfeld ................ ]   [ Aktualisieren ]
    ┌─ STARTBAR (4) ───────────────────────────────────────────────┐
    │ moon-dev-ai-agents  Python  venv✓  bot:moon-dev-agents        │
    │ Agent-Reach         Python  venv✓  bot:agent-reach            │
    └──────────────────────────────────────────────────────────────┘
    ┌─ EINRICHTEN (12) ────────────────────────────────────────────┐
    └──────────────────────────────────────────────────────────────┘
    ┌─ NUR DOKU (12) ──────────────────────────────────────────────┐
    └──────────────────────────────────────────────────────────────┘
    [ Statuszeile: letzter Start, Exit-Code, Logpfad ]

Spalten je Zeile (max. 5 sichtbare Angaben): **Name**, **Art** (Python / Node /
Rust / Doku), **venv da?**, **Bot-Profil**, **letzter Lauf** (Exit-Code + Uhrzeit
aus `logs/`, sonst leer).

Fuenf Aktionen je Zeile — mehr nicht:

1. **Ordner** — Explorer im Repo.
2. **Terminal** — `wt.exe` mit `-d <repo>` (vorhanden, gemessen).
3. **Starten** — der Befehl aus dem Manifest, eigenes Fenster, Ausgabe zusaetzlich
   in `logs/`. Ohne Manifest-Befehl ist der Knopf deaktiviert und nennt den Grund.
4. **Bot** — `hermes -p <bot> chat` mit Arbeitsverzeichnis = Repo (Profile sind da).
5. **Doku** — erste README des Repos im Standardprogramm.

## 6. Manifest `repos-zentrale.json`

    {
      "stand": "2026-09-18",
      "repos": [
        {
          "ordner": "moon-dev-ai-agents",
          "art": "python",
          "gruppe": "startbar",
          "start": [".venv\\Scripts\\pythonw.exe", "moongui.py"],
          "start_titel": "MoonDev-GUI",
          "bot": "moon-dev-agents",
          "notiz": "47 Agenten, RBI-Swarm, Boersen-Adapter"
        },
        {
          "ordner": "OpenTerminal",
          "art": "node",
          "gruppe": "einrichten",
          "start": ["npm", "start"],
          "einrichten": ["npm", "install"],
          "bot": "openterminal",
          "notiz": "braucht erst npm install"
        }
      ]
    }

Feldregeln:

- `start` ist eine **argv-Liste** (kein Shell-String) — kein `shell=True`, keine
  Zeichenketten-Injektion, Pfade mit Backslashes.
- `start`, `einrichten` und `bauen` werden **weggelassen**, solange sie nicht
  einmal echt gelaufen sind. Fehlen sie, zeigt die GUI das als Zustand an.
- `bot` ist der **klein geschriebene** Profilname. Fehlt das Profil, ist der
  Bot-Knopf deaktiviert und nennt das fehlende Profil.
- Die Platte **schlaegt** das Manifest im Zustand: venv, `.git`, README und
  Ordnerbestand werden live gescannt. Ein Klon ohne Manifest-Eintrag erscheint in
  der Gruppe **NEU** statt zu verschwinden; ein Manifest-Eintrag ohne Ordner
  erscheint als **FEHLT**.

## 7. Regeln (gelten fuer jede Zeile)

1. **Kein geratener Startbefehl.** Ein Befehl kommt erst ins Manifest, wenn er
   einmal echt gelaufen ist und die erste Ausgabe belegt wurde.
2. **Start nur auf Klick.** Nie automatisch im Hintergrund. Kein Autostart von
   Repo-Programmen.
3. **Kein „laeuft"-Versprechen aus Prozessnamen.** Angezeigt wird nur Belegbares:
   Exit-Code, Logzeit, und — falls im Manifest hinterlegt — ein offener Port.
   Beendet wird nie per Prozessname, nur per gemerkter PID.
4. **Keine Schreibzugriffe in fremde Repos.** Ausnahme: der vom Manifest
   ausdruecklich genannte Einrichtungsbefehl (`npm install`), und der nur auf Klick.
5. **Keine Schluessel, keine Anzeige von Schluesselwerten.** Die Zentrale liest
   `.env`-Dateien nicht.
6. **Deaktivierter Knopf statt Fehlermeldung.** Was nicht geht, ist sichtbar
   deaktiviert mit Grund — wie `repos-launcher.ps1` es heute falsch macht (wirft
   hart ab).
7. **`copilot-worktrees` ist kein Repo** (kein `.git`, Sammlung von Arbeitsbaeumen)
   und `.vscode` ist ein Konfigurationsordner fuer einen nicht installierten
   Editor: beide bekommen eine erkennbare Zeile bzw. werden uebersprungen — kein
   Start, kein Bot, keine Gruppe.

## 8. Bestandsaufnahme (28 Repos, drei Gruppen)

| Gruppe | Anzahl | Repos |
|---|---|---|
| **STARTBAR** (venv + Einstieg vorhanden) | 4 | moon-dev-ai-agents, Agent-Reach, openmontage, Trading-View-MCP-for-AI-by-Moon-Dev |
| **EINRICHTEN** (Einstieg da, Abhaengigkeiten fehlen) | 12 | OpenTerminal, claudian, EasyCLIProxyAPI, gbrain, deepseek-harness, codex, caveman, ProjectAtlas, basic-memory, Scrapling, graphify, odysseus |
| **NUR DOKU** (kein Programm, nur Text/PDF/Skills) | 12 | awesome-systematic-trading, claude-code, claude-plugins-official, everything-claude-code, Harvard-Algorithmic-Trading-with-AI, Moon-Dev-Code, obsidian-skills, one-skill-to-rule-them-all, santiment, skills, superpowers, winget-cli |

Summe 4 + 12 + 12 = 28 Repos. `copilot-worktrees` und `.vscode` sind keine Repos
und zaehlen nicht mit (§7 Regel 7).

Die Zuordnung ist eine Aussage ueber den **Einstieg** (gemessen), keine Zusage
ueber den Lauf. Pro Repo wird der Startbefehl im Bau einmal ausgefuehrt; erst
danach steht er im Manifest und das Repo wandert in die Gruppe STARTBAR.

## 9. Die zwei Reparaturen (ausserhalb der Zentrale)

1. **Desktop-Verknuepfung „Hermes"** auf
   `Agenten\Hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`
   umbiegen, Arbeitsverzeichnis auf dessen Ordner. Heute zeigt sie ins Leere.
2. **`repos-launcher.ps1` verliert die harten Abhaengigkeiten und zieht um.**
   Fehlt ein Werkzeug (`lazygit`), wird es **nicht benutzt und im Klartext
   genannt** statt zu werfen; nur `wt.exe` ist Pflicht. Das Skript bleibt als
   Massenweg erhalten und wird nicht geloescht. Es liegt jetzt unter
   `Agenten\Werkzeuge\` (in `Routinen` gilt jede `.ps1` als Bus-Routine) und ist
   erstmals in der `.gitignore` freigegeben — vorher existierte es nur auf dieser
   Platte. `-Mode Gui` funktioniert: VSCode ist installiert.

## 10. Nachweis

**Gemessen am 18.09.2026** (alles unten mit echtem Lauf, nicht beschrieben):

- `repos_zentrale.py --pruefen`: **28 Repos auf der Platte, 28 Manifest-Eintraege,
  29 Bot-Profile** — 4 in STARTBAR, 12 in EINRICHTEN, 12 in NUR DOKU.
- Vier Starts aus der Zentrale heraus, jeder mit Logdatei in `logs/`:
  | Repo | Befehl | Ergebnis |
  |---|---|---|
  | Agent-Reach | `.venv\Scripts\agent-reach.exe doctor` | Code 0, Kanalbericht (5 von 16 Kanaelen nutzbar) |
  | moon-dev-ai-agents | `.venv\Scripts\pythonw.exe moongui.py` | MoonDev-GUI laeuft (Fenster „MoonDev-GUI") |
  | openmontage | `.venv\Scripts\python.exe -c … registry.provider_menu()` | Code 0, Werkzeugregister |
  | ProjectAtlas | `target\release\projectatlas.exe --help` | Code 0, „ProjectAtlas 3 repository intelligence engine" (Bau: `cargo build --release`, 2:46 Min) |
- Gegenprobe „kein geratener Befehl": `tests/test_manifest_gegenprobe.py` prueft
  jeden Startbefehl gegen `logs/` — gruen.
- **56 Tests** gruen in `Agenten/Werkzeuge/repos-zentrale/tests/`, darunter ein
  echter Fensteraufbau (unsichtbar) und der Nachweis, dass ein relatives
  Programm gegen den Repo-Ordner aufgeloest wird.
- `git check-ignore -v` je freigegebener Datei: kein `!!` im Arbeitsbaum;
  `git add --dry-run` nimmt genau die gewollten Dateien.
- Zwei Reparaturen mit Beleg:
  - Verknuepfung „Hermes" zeigt jetzt auf
    `Agenten\Hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`,
    `Test-Path` auf das Ziel: **True** (vorher: toter Pfad `MaxHirn\Hermes\…`).
    Auch die Verknuepfung „moongui.py" startet jetzt ueber
    `.venv\Scripts\pythonw.exe` statt die `.py`-Datei zu oeffnen.
  - `repos-launcher.ps1` unter PowerShell 5.1: `-Mode Tui` meldet
    „lazygit.exe fehlt - 'Tui' wird uebersprungen" und endet mit **0** statt
    mit einem Abbruch; `-Mode Gui` funktioniert (VSCode ist installiert).
- Nebenbefund und mitbehoben: die **Bus-Suite** war rot
  (`test_anbindung_routinen` meldete `auslagerung-c-festlegen` und
  `moondev-gui` ohne Anbindung; danach kam ein maskierter dritter Fehler in
  `optimierungen-finden` zum Vorschein). Alle drei behoben,
  `Agenten/Bus/tests/test_ende_zu_ende.py` endet wieder mit
  „Ende-zu-Ende bestanden".
- Ein Fehlbefund wurde richtiggestellt: VSCode **ist** installiert. Der erste
  Befund „code.exe fehlt" kam aus einer Pruefung ueber die bash-PATH, die den
  Windows-PATH nicht sieht (§2, Korrektur).

- Der Test der Zentrale startet **nichts** echt: die Prozessaufrufe werden
  ersetzt, geprueft wird die Kommandozeile (argv), nicht das Fenster.
- **Bot-Weg gemessen** (18.09.2026): aus `Werkstatt/moon-dev-ai-agents`
  heraus gibt `hermes -p moon-dev-agents chat -q "Antworte mit genau einem
  Wort: PONG" -Q` die Antwort **PONG**. Genau diese Kommandozeile (mit `wt.exe
  -d <repo>` davor) baut der Bot-Knopf.

## 11. Absichtlich nicht

- Kein Autostart der Zentrale in Stufe 1 (kommt als Aufgabe/VBS erst nach
  Freigabe, gleiches Muster wie `moondev-gui.ps1`).
- Kein Eingriff in fremde Repos, keine `.env`-Werte, keine Schluessel.
- Keine Aenderung an `moongui.py` (die moondev-GUI bleibt, wie sie ist).
- Kein Ersatz fuer `handelszentrale.py` (Handelsspuren) — eigener Zweck.
- Kein Modell-/Router-Thema.

## 12. Offene Entscheidungen von Max

1. **Bots in der Telegram-Bruecke:** die Zentrale startet Bot-Chats lokal. Fuer
   unterwegs (`/bot NAME …` per Telegram) ist nichts zu bauen, weil es steht —
   nur wissen: die Zentrale ist der Heimatweg, Telegram der Fernweg.
2. **VSCode ist installiert** (nur nicht ueber die bash-PATH sichtbar), der
   „Gui"-Weg des Launchers funktioniert also. Der Explorer-Weg bleibt trotzdem
   drin, weil er ohne Zusatzprogramm geht.
3. **Node-Repos einrichten** (17 × `npm install`, je 1–5 Minuten und 200–800 MB
   `node_modules`) — erst auf Zuruf, Repo fuer Repo aus dem Fenster.
