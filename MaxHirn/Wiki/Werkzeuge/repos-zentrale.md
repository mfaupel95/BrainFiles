---
titel: Repos-Zentrale (Startfenster fuer Repos, Werkstatt und Handel)
aktualisiert: 2026-09-30
tags: [werkzeug, repos, handel, oberflaeche]
---

# Repos-Zentrale — ein Fenster fuer alle Repos

> **Kernsatz:** Der Bereich „Was dieses Projekt kann" ist die Antwort auf „ich
> kenne mich in der Kommandozeile nicht aus". Man waehlt links ein Projekt und
> bekommt rechts seine Befehle als anklickbare Zeilen — mit einem Knopf, der sie
> ausfuehrt, einem, der sie in die Zwischenablage legt, und einem, der den
> Repo-Bot damit beauftragt.
>
> **Seit 30.09.2026** ist das Fenster nicht mehr auf `Werkstatt/Repos` begrenzt:
> es zeigt drei **Bereiche** — REPOS (46 Klone), WERKSTATT (eigene Projekte,
> Datenfelder, Ablagen) und HANDEL (45 Ordner und 40 Werkzeugdateien unter
> `Agenten/Handel`). Aufbau, Rollen und Layoutfehler: eigener Abschnitt unten.

Ort: `Agenten/Werkzeuge/repos-zentrale/`. Start:

```
cd Agenten\Werkzeuge\repos-zentrale
.venv\Scripts\pythonw.exe repos_zentrale.py            # Fenster
.venv\Scripts\python.exe   repos_zentrale.py --pruefen  # nur auflisten
```

Die venv gehoert nur diesem Werkzeug (Python 3.13, Standardbibliothek).

## Aufbau des Fensters

Oben ein Suchfeld und „Aktualisieren", darunter der Baum mit den Gruppen
STARTBAR / EINRICHTEN / NEU / NUR DOKU / FEHLT. Zeile auswaehlen, dann:

| Knopf unten | Wirkung |
|---|---|
| Ordner | Explorer im Repo |
| Terminal | `wt.exe` mit Arbeitsverzeichnis = Repo |
| Starten | der `start`-Befehl aus dem Manifest, Ausgabe in `logs/` (Beleg + Exit-Code) |
| Bot | `hermes -p <bot> chat` im Repo-Ordner |
| Doku | die README des Repos |

## Der Bereich „Was dieses Projekt kann"

- **Links** ein Textblock: Zweck (`notiz`), Pfad, venv-Status, „Zu tun: …" und
  der Ablauf in Worten (`anleitung` im Manifest). Ist keine Anleitung
  hinterlegt, steht das ausdruecklich da — es wird nichts erfunden.
- **Rechts** die Befehlsliste `Was | Befehl | Hinweis`. Die ersten Zeilen sind
  bei jedem Repo dieselben (Starten, Terminal, Ordner, Doku, Bot), danach kommen
  die `befehle` aus dem Manifest.
- Drei Knoepfe auf die gewaehlte Zeile: **Befehl ausfuehren** (sichtbares
  Terminal im Repo, `cmd /k`, damit die Ausgabe stehen bleibt), **Befehl
  kopieren** (Zwischenablage — der Weg von Hand) und **Bot damit beauftragen**
  (`hermes -p <bot> chat -q "… ausfuehren und in drei Saetzen sagen, was
  herauskam"`, nur aktiv, wenn das Profil existiert).

## Manifest: die beiden Felder

`Agenten/Werkzeuge/repos-zentrale/repos-zentrale.json` ist die einzige Stelle,
an der ein Befehl steht. Je Repo:

```json
"anleitung": "Was das Repo tut und in welcher Reihenfolge man es anfasst.",
"befehle": [
  {"was": "Walk-Forward rechnen (4 Schritte, ~2 min)",
   "cmd": [".venv\\Scripts\\python.exe", "-m", "scripts.predict_rolling", "-c", "configs/...json"],
   "hinweis": "schreibt predictions.csv mit ungesehenen Zeilen"}
]
```

Regeln (der Code setzt sie durch):

- `cmd` ist eine **argv-Liste** wie `start` — keine Shell-Zeichenkette, keine
  Pipes. Wer ketten will, tippt im geoeffneten Terminal weiter.
- **Kein Befehl ins Manifest, der nie echt gelaufen ist** (Hausregel, gilt auch
  hier — der Start hinterlaesst einen Logbeleg in `logs/`).
- Ein Eintrag **ohne** `cmd` faellt einzeln weg; falsche `befehle` erscheinen als
  Hinweis in der Zeile und machen das Repo **nicht** un-startbar (dafuer ist
  allein `start` + Abhaengigkeiten zustaendig).

## Gemessener Stand (29.09.2026)

- **45 Repos auf der Platte, 45 Manifest-Eintraege, 10 startbar** — keine Zeile
  steht mehr auf „NEU".
- Nachtraeglich dokumentiert: intelligent-trading-bot, moon-dev-ai-agents,
  openmontage, kraken-cli, fomo-robinhood-radar (Befehle), Kronos/laya/
  robinhood-fomo-kronos-arena (nur Anleitung, kein startbarer Weg).
- Was noch keine eigenen Befehle hat, steht als Task in `Archiv/TASKS.md`
  (T-073): dort fehlt Wissen ueber das Repo, nicht Code.

### Nachtrag 29.09.2026 — neun Repos aus `O:\Werkstatt 2\` aufgenommen

Bestand war schon unter `Werkstatt/Repos/` vorhanden, nur im Manifest gefehlt.
Jeder Startbefehl wurde **einmal echt gestartet** (Beleg in `logs/`).

| Repo | Art | Start | Beleg im Log |
|---|---|---|---|
| `osiris` | node | `npm run dev` | Next.js 16.3.4, `Ready in 7.8s`, Port 3000 |
| `jev-trader` | node | `bun run start` | Bun-Server, DRY RUN, echte Monad-Bloecke, **Port 3010** |
| `deepseek-harness` | node | `npx -y @deepseek-ai/dsh web` | `dsh web: http://127.0.0.1:3080/?token=…` |
| `tradememory-protocol` | python | `.venv\Scripts\tradememory-api.exe` | `Uvicorn running on http://127.0.0.1:8000` |
| `ziplime` | python | `.venv\Scripts\python.exe -m ai_assistant` | fragt nach `OPENROUTER_API_KEY` |
| `foreman` | python | — (venv fehlt) | EINRICHTEN |
| `awesome-dsh-plugin`, `awesome-deepseek-harness-plugins`, `fast-jev-compaction`, `jev-chat-jarvis` | doku | — | kein Startprogramm, nur Anleitung |

**Zwei Korrekturen, die nur der echte Lauf zeigte:**

- `deepseek-harness` stand als „nur Bau, kein Start" im Manifest. Falsch: es hat
  eine **Web-UI** auf Port 3080. Und `npx` braucht `-y`, weil `aktionen.
  start_ausfuehren` mit `stdin=DEVNULL` startet — ohne `-y` bleibt npx an der
  Rueckfrage stehen.
- `jev-trader` laeuft auf **3010** (`PORT` in der `.env`), nicht auf 3000 wie die
  README nahelegt.

**Voraussetzung, die fehlte:** `bun` war nicht installiert (`npm install -g bun`).
`foreman` braucht noch ein venv, `ziplime` einen `OPENROUTER_API_KEY`.

### Nachtrag 30.09.2026 — OpenTerminalUI (46. Repo)

Erschien mitten in der Sitzung, war aber schon eingerichtet: `.venv`
(Python 3.13.15, 295 Pakete), `frontend/dist` gebaut (279 Dateien, 33,8 MB).
Aufgenommen als **11. STARTBARER** Eintrag — ein Server bedient beides:

```
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Belegt im Log: `Application startup complete`, `GET / → 200 OK` nach **57 s**,
`GET /api/health → 401` (die API ist authentifiziert). Zwei fehlende Dienste
werden still abgefangen: Redis fehlt (L2-Cache und Quote-Bus fallen auf
Speicher zurueck), Kite meldet fehlende Zugangsdaten.

**Die Junction-Falle — und warum sie den Start NICHT trifft:**

`scan.repos_scannen()` liefert `O:\Werkstatt\Repos\...`, nicht den C:-Pfad der
Junction. Die Zentrale startet also aus dem **echten** O:-Pfad. Wer dagegen von
Hand aus `C:\...\Werkstatt\Repos\OpenTerminalUI\frontend` heraus baut, bekommt
von vite `fileName darf nicht absolut sein, received O:/Werkstatt/...` — der
Junction wird aufgeloest und der absolute Eingabepfad abgelehnt. Schlimmer als
der Fehler: **ein gescheiterter Lauf leert `frontend/dist`** (279 Dateien waren
danach weg). Deshalb steht im Manifest die Bau-Form ueber den echten Pfad:

```
cmd /c cd /d O:\Werkstatt\Repos\OpenTerminalUI\frontend && npm run build   (exit 0, 58,9 s)
```

Merksatz: bei einem Repo unter einer Junction entscheidet das
**Arbeitsverzeichnis**, ob ein relativer Pfad noch stimmt — und ein fehlgeschlagener
Build ist kein harmloser Fehlschlag, wenn er das Ausgabeverzeichnis vorher leert.

### Das Zentrale-Fenster starten

```
.venv\Scripts\pythonw.exe repos_zentrale.py
```

**Stolperstein beim Start aus einer Agenten-Sitzung:** `cmd /c start "" … pythonw.exe`
und PowerShells `Start-Process` liefern beide scheinbar Erfolg (die Prozesse sind
kurz da, PID und Startzeit stimmen), aber **beim Ende des Terminal-Aufrufs ist das
Fenster wieder weg** — gemessen zweimal: nach 15 s noch zwei Prozesse, nach 40 s
null. Über ein `Popen` aus einem Python-Skript gestartet überlebt dasselbe Fenster
(pythonw und python, je 40 s geprüft, unabhaengig nachgezaehlt). Der Vordergrundlauf
haelt 90 s durch — die GUI selbst ist gesund, es ist die Startart.
Merksatz: **ein Prozess, der die Sitzung ueberleben soll, wird per `Popen` gestartet,
nicht per `start`/`Start-Process`** — und danach in einem ZWEITEN Aufruf nachgezaehlt,
weil „Erfolg" beim Starten nichts ueber das Ueberleben sagt.

### Nachtrag 30.09.2026 — Flotte gegen upstream gezogen (gemessen)

`Werkstatt/Repos` traegt **46 Klone** (`copilot-worktrees` ist keine: Worktree-
Sammlung ohne `.git`, wird vom Werkzeug richtig uebergangen). Drei Laeufe von
`Agenten/Werkzeuge/repos-updaten.py`:

| Lauf | Ergebnis |
|---|---|
| 1 · `--trocken` | 28 Klone hinterher, zusammen **4512 Commits** |
| 2 · anwenden | **26 vorgespult**, 15 waren schon aktuell |
| 3 · Gegenprobe | **41 aktuell**; die 4 anderen sind Regel, nicht Rueckstand |

Groesste Rueckstaende (Commits): `deepseek-harness` 2411, `laya` 887, `codex` 523,
`graphify` 143, `awesome-dsh-plugin` 110, `claudian` 86, `EasyCLIProxyAPI` 63,
`claude-plugins-official` 58, `one-skill-to-rule-them-all` 53.

**Was der Lauf NICHT anfasst — vier Faelle, jeder mit Grund im Bericht:**

- `moon-dev-ai-agents` — **ausgenommen** (`AUSGENOMMEN` im Skript): dort laeuft der
  kraken_agent. Wird gemessen (die 6 Aenderungen an verfolgten Dateien bleiben),
  nie gespult.
- `OpenTerminal` (`package.json`/`-lock`, 4 hinter) und `osiris`
  (`package-lock.json`, 5 hinter) — **schmutzig**: eine Aenderung an einer
  verfolgten Datei sperrt den Klon. Verwerfen ist verboten, also entscheidet Max.
- `jev-chat-jarvis` (Zweig `JEV`, 84 hinter) und `tradememory-protocol` (Zweig
  `Werkstatt`, 91 hinter) — **anderer Zweig**: das Skript raet den Quellzweig
  nicht und schaltet nicht um. Nachgemessen, nicht angefasst.
- `claude-red` ist aktuell, hat aber 4 von Defender entfernte `SKILL.md` als
  Loeschung im Baum (`Skills/…/offensive-{sqli,rce,file-upload,shellcode}`).

**Beobachtung zur Historie:** zwei der neun shallow-Klone wurden beim Vorspulen
**unshallowed** (`OpenTerminalUI`, `awesome-systematic-trading`) — ein
Shallow-Klon kann nicht `--ff-only`, weil der gemeinsame Vorfahr fehlt; das
Skript holt die Historie dann einmal nach. Sieben bleiben shallow.

Umgestellt im Werkzeug: `AUSGENOMMEN` (Liste der Nur-Messen-Klone) und `--ausser`
fuer weitere, ausserdem meldet der Bericht jetzt den Rueckstand in Commits je
Zeile. Wirkung sofort, ohne Neustart — es ist ein Handwerkzeug, keine Routine.

## Nachtrag 30.09.2026 — drei Bereiche, gefuelltes Manifest, Layout gerechnet

Auftrag Max: „professionell designen und mit allem aus O:/Werkstatt/ und
Brainfiles/Werkstatt und Brainfiles/Agenten/Handel auffuellen und kombinieren."
`O:/Werkstatt` und `BrainFiles/Werkstatt` sind **derselbe** Ordner (Junction) —
es waren also zwei Orte: Werkstatt und `Agenten/Handel`.

### Bereiche statt einer Wurzel

Neu: `quellen.py` haelt die Wurzeln (Pfade **relativ**, keine absoluten) und was
eine Zeile bekommt:

| Bereich | Wurzel | Regel |
|---|---|---|
| REPOS | `Werkstatt/Repos` | nur Ordner mit `.git` (wie vorher) |
| WERKSTATT | `Werkstatt` + `Werkstatt/Projekte` | jeder Ordner |
| HANDEL | `Agenten/Handel` | jeder Ordner **und** jede Werkzeugdatei mit Einstieg |

Ein Manifest-Eintrag traegt jetzt `wurzel` und `pfad` — der **Schluessel ist das
Paar (wurzel, pfad)**. Nur so kann `OmniRoute` einmal unter `Werkstatt/` und
einmal unter `Werkstatt/Projekte/` stehen, ohne dass eins das andere verdeckt.
Neu ausserdem die Spalte **Rolle** (Spur, Werkzeug, Modell, MCP-Server, Ablage)
und `warnungen` fuer Vermerke, die den Start nicht sperren.

Der Baum hat drei Ebenen: **BEREICH → GRUPPE → Projekt**. Die funf Gruppen
bleiben unveraendert; „EINRICHTEN" heisst weiterhin „es fehlt noch etwas",
jetzt auch „kein Startbefehl belegt".

### Gefuellt: 46 → 162 Zeilen

`fuellen.py` (neu) traegt ein, was auf der Platte liegt und fehlt. Notiz und Art
kommen aus dem Projekt **selbst** (README-Ueberschrift, sonst Modul-Docstring),
Rolle und Startbefehle aus einer kuratierten Tabelle im Skript. Drei Werkzeuge:

| Aufruf | Wirkung |
|---|---|
| `fuellen.py` | Trockenlauf: zeigt, was neu entstuende |
| `fuellen.py --anwenden` | schreibt (Sicherung `.bak-JJJJMMTT`), Feldreihenfolge fest |
| `fuellen.py --belege` | fuehrt jeden Startbefehl ohne Log EINMAL aus (Frist 90 s) |
| `fuellen.py --auffrischen --anwenden` | traegt nur FEHLENDE Felder bestehender Eintraege nach |

**Vorhandene Eintraege bleiben unangetastet** — Handarbeit wird nie
ueberschrieben. Ergebnis: 46 (REPOS) + 30 (WERKSTATT) + 86 (HANDEL) = **162
Zeilen, 50 mit Startbefehl, 39 davon neu belegt**.

**Die 13 „Bot-Profil fehlt"-Eintraege sind weg.** Gemessen: `profiles/.deleted/`
enthaelt keine Profile, sondern **9-Byte-Vermerke** mit dem Wort `deleted` — die
Profile selbst sind am 19.09.2026 geloescht worden (`ls -la` unterscheidet die
beiden Faelle). Die 13 Eintraege tragen jetzt eine `warnung` statt eines
Bot-Namens; der Knopf ins Leere ist damit weg und
`test_jedes_bot_profil_des_manifests_existiert` ist wieder gruen.

### Layout: gerechnet, nicht gesetzt

Zwei echte Layoutfehler, beide durch **Messen** gefunden, nicht durch Hinsehen
(`messprobe.py` baut das Fenster und vergleicht jede Spaltenbreite mit der
Schrift):

1. **Skalierte Anzeige, feste Pixelbreiten.** Mit `dpi_bewusst()` setzt Tk
   Schrift in Geraetepixeln; auf diesem Rechner meldet `winfo_fpixels('1i')`
   **120** (Faktor 1,25). Ein 41-Zeichen-Hinweis braucht damit 410 px in einer
   366-px-Spalte — abgeschnitten. Jetzt rechnet `fenster.spaltenbreiten()` aus
   der WIRKLICHEN Baumbreite und dem Faktor; gekuerzt wird in dieser Reihenfolge:
   Nebenspalten → Projektspalte → Hinweisspalte (sie traegt den Grund), Rest geht
   an den Hinweis.
2. **`stretch=True` ist der stille Verfaelscher.** Tk verteilte die Restbreite
   selbst, gemessene Werte stimmten nicht mehr (191 statt 125 px). Jede Spalte
   steht jetzt auf `stretch=False`.

Dazu: die Bereichs-Erklaerung stand versehentlich in der **Rolle**-Spalte und
wurde dort abgeschnitten — sie gehoert in die Hinweisspalte. Die Summenzeile ist
von „162 Eintraege · REPOS 46 · WERKSTATT 30 · HANDEL 86" auf das kurze
„162 von 162 Zeilen" oben geschrumpft; die Bereichszahlen stehen in der
Statuszeile, wo die ganze Fensterbreite zur Verfuegung steht.

Merksatz: **eine Spaltenbreite ohne die Schrift zu messen ist geraten.** Ein
Blick auf ein Bild hilft nicht — die Zahlen helfen.

### Ein neuer Ordner erscheint von selbst

Was in einer Wurzel liegt und keinen Eintrag hat, wird **NEU** — auch eine Datei,
die eine parallele Sitzung gerade angefangen hat (`kerzenschluss_bias.py`,
mitten in dieser Arbeit aufgetaucht). Sie bekam **keinen** Startbefehl: der
Hilfe-Start (`<datei> --help`) gibt es nur fuer Dateien in `HILFE_VERIFIZIERT`,
also fuer die, deren Aufruf einmal wirklich gelaufen ist. Das ist die Hausregel
„kein geratener Befehl", diesmal als Code.

## Einen Befehl belegen: der Beleglauf

Die Hausregel „kein Befehl ins Manifest, der nie echt gelaufen ist" laesst sich
maschinell nachziehen — `test_manifest_gegenprobe.py` verlangt zu jedem `start`
eine Logdatei `<ordner>-*.log`. Statt den Start von Hand zu machen:

```python
import aktionen, manifest, scan          # aus Agenten/Werkzeuge/repos-zentrale
repos   = scan.repos_scannen(REPOS)
zeilen  = manifest.zeilen_bauen(repos, manifest.manifest_laden(MANIFEST), PROFILE, REPOS)
erg     = aktionen.start_ausfuehren(zeile, LOGS)   # schreibt den Logbeleg
# warten bis Prozess lebt ODER Log Inhalt hat, dann taskkill /T /F /PID <pid>
aktionen.ereignis_anhaengen(erg.log, f"beendet (Code {code})")
```

`aktionen` liest nur die Attribute `ordner`, `start`, `repo` — ein kleiner Shim
genuegt, es muss keine Zeile veraendert werden. Mit `taskkill /T /F` den **ganzen
Baum** beenden (`npm run dev` laesst sonst `next dev` als Waise zurueck).

## Fallen

- **Befehl und Anzeige sind zwei Dinge.** Der Knopf „Starten" fuehrt versteckt
  aus und schreibt in `logs/`; „Befehl ausfuehren" im Detailbereich oeffnet ein
  sichtbares Terminal. Fuer einen Beleg zaehlt nur der Log.
- **Relative Programmpfade** werden gegen den Repo-Ordner aufgeloest (Windows
  wuerde sie sonst gegen das Arbeitsverzeichnis des Aufrufers suchen) — deshalb
  darf im Manifest `.venv\Scripts\python.exe` stehen.
- Der Fenstertest baut die Oberflaeche wirklich auf, aber unsichtbar
  (`withdraw`) — ein Tippfehler in einem Widgetnamen faellt so auf.

## Pruefen

```
cd Agenten\Werkzeuge\repos-zentrale
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Stand 30.09.2026: **118 Tests, alle gruen** (vorher 78 mit einer bekannten roten
Stelle). Die rote Stelle `test_jedes_bot_profil_des_manifests_existiert` ist
behoben — sie war zu Recht rot: das Manifest nannte 13 Bot-Namen, deren Profil
seit dem 19.09.2026 nicht mehr existiert (T-072 erledigt, siehe Nachtrag oben).

Dazu die Messprobe, die kein Test ersetzt:

```
.\.venv\Scripts\python.exe messprobe.py
```