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

## Nachtrag 30.09.2026 (abends) — Strategien, Stufen, Werkzeuge in Unterordnern

Drei Fragen von Max, drei Antworten mit Messung.

### `Werkstatt/handel-stack` — ein Duplikat, aber ein gewolltes

Gemessen: `mfaupel95/handel-stack` ist ein **privates** GitHub-Repo (6,4 MB,
`pushedAt` 18.09.2026 20:27) mit der Beschreibung *„Spiegel von Agenten/Handel"*
und dem ersten Commit *„feat: Handelsstack importiert (Spuren, Dauerlauf,
Auswertung, Journal und Zustand)"*. Inhalt nachgezaehlt: **22 Spuren mit
`handeln.py`** (heute 30), dieselben Dateinamen, aber aelterer Stand
(`dauerlauf.py` 43 KB gegen 64 KB, `handelszentrale.py` 47 gegen 70, `lage.py`
37 gegen 53) — und **43 Journal-Dateien** mit den Laufzeitstaenden der Spuren
(`handelsjournal.csv`, `zustand.json`, auch die `.mittel`-Fassungen).

- **Stoert es den Betrieb?** Nein. Eine Suche ueber `Agenten/` findet den Pfad
  nur in der Zentrale selbst (`fuellen.py`, `repos-zentrale.json`); keine Spur,
  kein Skript, keine Routine liest ihn. `repos-updaten.py` fasst ihn nicht an
  (das Werkzeug liest nur `Werkstatt/Repos`).
- **Geheimnisse?** Keine. Keine `.env`, keine Bearer-Token; die zwei
  Schluessel-artigen Zeilen in `nautilus/set-okx-env.ps1` sind Platzhalter
  („HIER…", byte-gleich auch im lebenden Baum). Das Repo ist privat.
- **Wo es stoeren KANN:** als zweite, aeltere Wahrheit im Suchweg. Ein `grep`
  nach `handelsjournal.csv` oder `zustand.json` findet ab jetzt zwei Baeume.
  Deshalb steht es im Manifest als **Rolle „Spiegel (18.09.)"** mit einer
  Warnung, die sagt: Altstand, nichts liest ihn, der lebende Baum liegt in
  `Agenten/Handel`.

Merksatz: **ein eingefrorener Spiegel ist kein Fehler — ein unbenannter ist
einer.** Eine Zeile im Fenster, die sagt was es ist, kostet nichts; ein Fund im
falschen Baum kostet eine Sitzung.

### Strategien: drei Dinge heissen so

| Art | Wo | Rolle im Fenster |
|---|---|---|
| Spuren | `Agenten/Handel/<spur>/` | `Spur` (32) |
| Freqtrade-Strategien | `freqtrade/user_data/strategies/*.py` | `Strategie` (6) |
| Backtests | `orb/backtest.py`, `gitter/backtest_gitter.py`, `nautilus/backtest_grid.py`, ... | `Backtest` |

Die sechs Freqtrade-Strategien sind **Klassen, keine Programme**: freqtrade
laedt sie, der Bot-Aufsatz steht in `freqtrade/user_data/bots/`. Sie bekommen
darum keinen Startbefehl, sondern einen Hinweis — und stehen trotzdem als Zeile
im Fenster, damit man sie findet.

### Stufen: kein eigener Eintrag, sondern drei Befehle

Basis / mittel / hoch sind **dieselben Spuren mit groesseren Betraegen** in
eigenen Dateien (`zustand.mittel.json`, `handelsjournal.hoch.csv`,
`dauerlauf.mittel.log`). Drei Zeilen daraus zu machen waere irrefuehrend: es
gibt nicht drei Laeufe mit verschiedenen Strategien, sondern einen Betrieb mit
drei Groessen. Sichtbar werden sie ueber die Befehlsliste der drei Leser (alle
gemessen):

| Zeile | Befehl | Ergebnis 30.09. |
|---|---|---|
| `spuren_stand.py` | `--nur scharf` | scanner, mosaic, moondev_listingarb — je mit `haupt/.mittel/.hoch` im Buch |
| `auswertung_alle.py` | `--risiko mittel` | eigener Kopf „Risikostufe mittel: eigene Journale je Spur (handelsjournal.mittel.csv)" |
| `spiegelstand.py` | `--risiko mittel` | „29 von 29 Spuren byte-gleich (Q:)" |

### Werkzeuge in Unterordnern: eine Liste, keine Suche

`quellen.WERKZEUG_ZUSATZ` nimmt jetzt auch **Pfade** auf
(`okx_bot_waechter/analyse.py`, `kraken/abgleich.py`, die fuenf
`auswertung.py`). Damit stieg das Manifest von 162 auf **192 Zeilen**, 23 neue
Startbefehle wurden einmal echt gefahren (`fuellen.py --belege`).

Warum keine rekursive Suche: in `Agenten/Handel` liegen unter `OpenAlice/`
**130 Dateien** eines fremden Projekts (eigener Baum, eigene `AGENTS.md`).
211 Kandidaten mit `__main__`+`argparse` waeren sonst als Zeilen aufgetaucht.
Eine Namensliste ist eine Entscheidung, ein Muster ist eine Hoffnung.

**Nicht aufgenommen: die 30 `handeln.py` der Spuren.** Welches Skript eine Spur
fahrt, steht in `dauerlauf.py` (`SPUREN`) — und dort steht NICHT bei allen
`handeln.py`: die meisten tragen kein `skript`-Feld (Vorgabe `handeln.py`), aber
`nautilus_kraken_futures` teilt sich den Ordner `nautilus_kraken` mit dem
Spot-Arm und faehrt `handeln_futures.py` mit dem `nautilus/.venv`. Diese Liste
im Manifest nachzubauen waere eine dritte Wahrheit.

### Falle beim Nachbauen: eine Extraktion ist keine Messung

Beim ersten Versuch habe ich `dauerlauf.SPUREN` per Regex gelesen und kam auf
`swap -> spiegel.py`, `kraken -> spiegel_knapp.py`, `omniquant ->
omniquant_weit.py`. **Alles drei falsch**: der Ausdruck griff ueber
auskommentierte Bloecke hinweg und zog deren Werte in den vorigen Eintrag. Die
Quelle sagt: `swap` und `kraken` tragen gar kein `skript`-Feld, `omniquant`
faehrt `handeln.py`. Nur der vierte Wert (`nautilus_kraken_futures`) stimmte.

Merksatz: **wer eine Konfiguration nachbaut, liest sie — und prueft jede Zeile
an der Quelle.** Ein Parser, der plausible Werte liefert, ist gefaehrlicher als
einer, der abbricht; die falsche Liste stand schon im README, bevor ich sie
nachgesehen habe.

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

## Nachtrag 30.09.2026 (Nacht) — runde Ecken, Skalierung, Filter, Handelsteil

Zweiter Auftrag Max am selben Tag: *„professionell designen … mehr
skalierungsoptionen. filter, knoepfe zum testen und scharfschalten. runde
ecken?"* — der erste Teil (drei Bereiche, gefuelltes Manifest) steht im
Abschnitt darueber; hier steht, was danach kam.

### Fuenf neue Dateien statt einer groesseren `fenster.py`

| Datei | Aufgabe |
|---|---|
| `rund.py` | runde Ecken: Umriss-Rechnung, `RunderKnopf`, `Karte`, Fensterrand |
| `einstellungen.py` | gemerkte Ansicht (Schrift, Dichte, Fenster, Filter) |
| `auswahl.py` | die Filter als reine Rechnung (Text, Bereich, Gruppe, Chips) |
| `handelstand.py` | Stand je Spur, Checkliste, Vorschau-Befehl, Schreiben in die Wachen |
| `schalter.py` | die zwei Fenster: Scharfschalten und Entschaerfen |

`fenster.py` baut nur noch zusammen. Die Anzeigelogik liegt weiter als reine
Funktionen oben — **alle** 137 alten Tests liefen unveraendert weiter.

### Runde Ecken

Tk/ttk zeichnet Rechtecke. `rund.ecken_punkte()` rechnet den Umriss eines
Rechtecks mit runden Ecken (Radius auf die halbe kurze Seite begrenzt, sonst
waere es eine Raute), `RunderKnopf` und `Karte` zeichnen damit. Der Knopf
beantwortet `knopf["state"]` wie ein ttk-Widget (`cget`/`__getitem__`) — ohne
das waeren die alten Knopf-Tests gebrochen.

Das **Fenster** bekommt seine Ecken vom System:
`rund.fenster_ecken()` setzt `DWMWA_WINDOW_CORNER_PREFERENCE` (33, Wert 2) auf
das Top-Level-Fenster hinter `winfo_id()`. Gemessen auf diesem Rechner:
`DwmSetWindowAttribute` gibt 0, das Ruecklesen liefert 2. Fehlertolerant — auf
Windows 10 bleibt es eckig, und das ist kein Fehler.

### Skalierung (drei Regler, alle gemerkt)

| Regler | Wirkung |
|---|---|
| Schrift 8–16 pt | skaliert Tabelle, Knoepfe, Karten und Zeilenhoehe gemeinsam |
| Dichte kompakt/normal/gross | aendert NUR den Zeilenabstand (Faktor 0,85/1,0/1,3) |
| Fenster klein/mittel/gross/bildschirm | Vorgaben, auf Bildschirm minus 80 px begrenzt |

Tasten: `Strg +`, `Strg -`, `Strg 0`, `Strg-Mausrad`. Die Werte liegen in
`einstellungen.json` — **Laufzeitstand, nicht versioniert** (die Datei aendert
sich bei jedem Chip-Klick; ein versionierter Stand waere in jedem Commit eine
Phantom-Aenderung). Die Ausnahme steht in der `.gitignore` NACH der Freigabe
`!…/repos-zentrale/*.json` — spaetere Regel gewinnt.

### Filter

Acht Chips (`auffaellig`, `startbar`, `mit Start`, `mit Bot`, `fremd`,
`nur Handel`, `nur Spuren`, `scharf`) plus Suchfeld, Bereich und Gruppe.
**Die Chips sind UND-verknuepft** — wer zwei anmacht, will die Schnittmenge,
nicht die Vereinigung.

### Handelsteil: Testen und Scharfschalten

Die rechte Karte erscheint, sobald eine Handels-Spur gewaehlt ist (Ordner aus
`dauerlauf.SPUREN`). Sie zeigt die Checkliste aus
[[Handel/Gates-und-Freigabe]] und bietet:

* **Vorschau testen (F9)** — `<spur>/handeln.py --vorschau` **mit**
  `MAXHIRN_ROUTINE=1`, Ausgabe in die Karte und nach `logs/`. Rein lesend.
* **Stand neu lesen** — `spuren_stand.py` im Hintergrund (rein lesend).
* **Scharf schalten … (F10)** — eigenes Fenster mit Checkliste, Pflichtfeld
  Herzschlag 180, Haken `freigabe.erfuellt` und **Tipp-Bestaetigung**, wenn die
  Spur danach wirklich ordern kann.
* **Entschaerfen** — nur `handel_erlaubt=false`; der Haken bleibt stehen.

Geschrieben wird **gezielt im Text**, nie per `json.dump`: die Wachen-Dateien
sind handformatiert (lange Notizen, CRLF). Der Textersatz ist am
**Zeilenanfang** verankert (`^\s*"schluessel"\s*:`) — eine Notiz, die den
Schluesselnamen im Text traegt, wird so nicht zerschnitten. Danach Gegenprobe
per `json.loads` UND Vergleich jedes Wertes; stimmt etwas nicht, wird nichts
geschrieben.

### Vier echte Fallen, jede gefunden statt vermutet

1. **Gruppentitel ist nicht der Gruppenschluessel.** Die Auswahl zeigt
   `NUR DOKU`, gefiltert wurde ueber den Schluessel `doku` — der Gruppenfilter
   war damit **immer leer**, und am Bildschirm sieht das aus wie „es gibt
   nichts". Jetzt macht `auswahl.gruppe_schluessel()` daraus den Schluessel;
   ein Test prueft beide Schreibweisen.
2. **`root.after` aus einem Faden ist verboten.** Der Vorschau-Lauf meldete
   `RuntimeError: main thread is not in main loop` (Tk ist nicht threadsicher).
   Faeden legen ihren Aufruf jetzt in eine `queue`, die Hauptschleife holt ihn
   alle 80 ms ab. Zweiter Teil derselben Falle: der `after`-Auftrag muss beim
   Zerstoeren **abbestellt** werden, sonst schreibt Tk danach `invalid command
   name …_post_pollen` auf die Fehlerausgabe (in der Testsuite sichtbar).
3. **Karten im PanedWindow brauchen eine Wunschbreite.** Ohne sie startet die
   Teilung bei zwei Tk-Vorgaben (2 × 378 px) — `messprobe.py` zeigte die
   Befehlsliste mit 490 px in einem 385-px-Widget. Jetzt 1000/700 px
   Wunschbreite und schmalere Spalten; die Probe sagt wieder PASST.
4. **Ein Test darf nie in eine echte Spur schreiben.** Die Wachen-Proben
   laufen ausschliesslich auf Temp-Dateien; die Lese-Tests
   (`handelstand.zustand`, `laufplan`) oeffnen nichts und schreiben nichts.

### Zahlen

* **259 Tests, alle gruen** (vorher 137): +122 in `test_rund`,
  `test_einstellungen`, `test_auswahl`, `test_handelstand`, `test_schalter`,
  `test_fenster_handel`.
* `messprobe.py`: Spalten 1679 px in 1697 px Platz → PASST; Hinweisspalte
  705 px, 63 von 216 Hinweisen bleiben zu lang (das war vorher so und ist der
  Preis dafuer, dass die Spalte den Grund traegt).
* Die Handels-Karte liest `spuren_stand.py` **einmal** (gemerkt), nicht bei
  jedem Tastendruck im Suchfeld.

### Pflege: einrichten, bauen, pruefen, reparieren

Zweiter Teil desselben Auftrags: *„mehr fertige automatisierung zur einrichtung /
implementierung / bearbeitung der projekte. reparatur ueberpruefen etc"*.

Die rechte Karte ist jetzt ein **Notebook** mit zwei Reitern: „Handel · Testen"
und „Einrichten · Reparatur" (`pflege.py`).

| Knopf | Was er tut |
|---|---|
| **Pruefen (F7)** | misst venv (laeuft ihr `python.exe`?), node_modules, Pflichtpfad, Git-Zweig/Aenderungen/Rueckstand, README, Bot-Profil, Port |
| **Einrichten** | fuehrt `einrichten`/`einrichten_kette` aus dem Manifest aus, sonst die Schritte aus den Dateien des Projekts |
| **Bauen** | dasselbe fuer `bauen`/`bauen_kette` bzw. Cargo/go/npm/Make |
| **Alles pruefen** | Bericht ueber alle Zeilen des Filters nach `logs/pruefbericht-*.log` |

Drei Entscheidungen, die den Charakter bestimmen:

1. **Der Vorschlag kommt aus einer Datei, die da ist** — `requirements.txt` ->
   venv + `pip install -r`, `pyproject.toml` -> `pip install -e .`,
   `package.json` -> `npm install`, `Cargo.toml` -> `cargo build --release`,
   `go.mod` -> `go build ./...`. Ohne Anhaltspunkt sagt die Karte das und der
   Knopf ist aus. Kein Befehl wird erfunden.
2. **Ein Befehl wird erst nach einem erfolgreichen Lauf belegt.** Exit-Code 0
   und noch nichts im Manifest -> `pflege.eintragen()` schreibt ihn (Sicherung
   `.bak-JJJJMMTT`, Notiz `_einrichten_belegt`). Mehrere Schritte landen als
   **Kette** — `einrichten_kette` ist eine Liste von argv-Listen, ausdruecklich
   KEINE Shell-Zeile (die Hausregel gilt auch fuer eine Kette). `fuellen.py`
   kennt die neuen Felder in seiner festen Reihenfolge.
3. **Ein kaputter Zustand wird benannt, nicht blind repariert.** Eine `.venv`,
   deren `python.exe` nicht startet, ist kein `pip`-Fall: sie wird gemeldet und
   der Vorschlag lautet `python -m venv --clear`. Ein schmutziger Git-Baum wird
   gemeldet, nicht angefasst; der Vorschlag fuer Rueckstand ist der vorhandene
   Weg (`repos-updaten.py --nur <ordner>`).

Ohne Fenster geht derselbe Lauf als `repos_zentrale.py --pruefbericht`
(erster echter Lauf: 31 auffaellige Projekte in REPOS, Bericht in `logs/`).

**Was der erste echte Lauf sofort zeigte:** `manifest._zeile` warf bei JEDEM
Eintrag der FREMD-Liste `UnboundLocalError: gruende` — die Notiz wurde
angehaengt, bevor die Liste angelegt war. Die 137 Tests sahen das nicht (die
wenigsten bauen Zeilen aus der echten FREMD-Liste); ein Lauf ueber ALLE Zeilen
fand es in der ersten Sekunde. Merksatz: **ein Pfad, den nur echte Daten
ausloesen, braucht einen Lauf ueber echte Daten.**

### Absichtlich nicht angefasst

* Keine echte `wachen.json` einer Spur: die Schreibprobe lief auf Temp-Dateien,
  und es wurde **kein** Schalter scharf gestellt.
* Kein Kommandozeilen-Weg zum Scharfschalten — Handelsregeln Punkt 3 verlangt
  ein Fenster; `--handel` und `--test` lesen nur.
* `handelszentrale.py` und `leitstand.py` (die anderen Fenster) bleiben, wie sie
  sind; `fenster_design.py` wurde nicht geaendert (die Karten-Stile stehen
  lokal in `fenster.py`, damit die anderen Fenster unberuehrt bleiben).

## Nachtrag 30.09.2026 (spaet) — Spuren startbar, Gruppe „KEIN EIGENER START", Junction-Falle

Auftrag Max: *„brainfiles/werkstatt und O:/werkstatt sind beide mit meinen Repos
voll. alles auf einer platte lagern? nach duplikaten und missstaenden
ausschauhalten. an zentrale anbinden was fehlt, uis startbereit machen in der
zentrale"*.

### Erst die Frage: es sind nicht zwei Orte

`BrainFiles\Werkstatt` **ist** `O:\Werkstatt` — eine Junction, kein zweiter
Ordner. Beide Listen sind Zeile fuer Zeile identisch, beide zeigen dieselben
Zeitstempel und dieselbe Groesse. „Beide voll" hiess also: **ein** Ort, 66 GB.
Zweiter Befund derselben Art: `Werkstatt\Repos\intelligent-trading-bot` ist eine
Junction auf `Werkstatt\intelligent-trading-bot` (siehe unten).

### Jede Spur ist jetzt aus dem Fenster startbar

Eine Spur ist ein **Ordner**, kein Programm: kein eigenes venv (ausser den
Nautilus-Armen), und die Datei heisst nicht immer `handeln.py`. Der Start kommt
deshalb aus derselben Quelle wie im Dauerlauf:

```
..\scanner\.venv\Scripts\python.exe  handeln.py  --vorschau     # Vorgabe
..\nautilus\.venv\Scripts\python.exe handeln.py  --vorschau     # die drei Nautilus-Arme
.venv\Scripts\python.exe             handeln.py  --vorschau     # scanner (eigenes venv)
```

`SPUREN_START` in `fuellen.py` haelt die Paare (Skript, Interpreter) fuer **37
Spuren** — dieselben Paare wie `dauerlauf.SPUREN`, aber es bleibt EINE Liste
dort. Gestartet wird **immer `--vorschau`**: das ist der lesende Blick einer
Spur, sie schreibt dabei nichts. Ohne den Zusatz liefe ein voller Handelszyklus
los, und das ist Sache des Dauerlaufs, nicht eines Klicks.

Dazu die beiden Fenster (`handelszentrale.py`, `leitstand.py`) mit
`pythonw.exe` und der Freqtrade-Betrieb (`bots.py liste` plus fuenf Befehle,
darunter die drei Web-UIs auf 8081/8082/8083). `leitstand.py` stand vorher
ausdruecklich OHNE Klick-Start („es hat keine Argumente") — eine UI ohne
Startknopf ist in einer Startzentrale aber fehl am Platz.

`fuellen.py --belege` hat **43 Startbefehle** einmal echt gefahren; jeder hat
seinen Logbeleg in `logs/`. Einzige Auffaelligkeit: `leitstand.py` lief in die
90-s-Frist — es ist ein Fenster, es endet nicht von selbst.

### Die Gruppe „KEIN EIGENER START"

Vorher standen **86 Zeilen** in EINRICHTEN — gelesen als „86 Sachen sind
kaputt". Die meisten waren es nicht: fremde Klone, die nur gelesen werden, sechs
Freqtrade-Strategieklassen, die freqtrade laedt, und vier Werkzeuge, die man
nicht von Hand starten darf (`dauerlauf.py`, `melder.py`,
`kraken_abweisungs_sonde.py`, `nautilus_rc5`-Rauchproben).

Neu ist deshalb die Gruppe **KEIN EIGENER START** („richtig so: wird geladen
oder ist nur lesbar"). Die Bedingung ist eng und steht in `manifest._zeile`:

- **kein** anderer Grund darf vorliegen (`startgruende == ["kein Startbefehl
  belegt"]`) — ein fehlendes venv bleibt EINRICHTEN, sonst waere die Gruppe ein
  Versteck fuer echte Luecken;
- der Grund muss **dabeistehen**: als kuratierte Gruppe (`gruppe: kein_start`),
  als Vermerk (`warnungen`, z. B. aus `fuellen.OHNE_START`) oder in der
  FREMD-Liste als `nur lesen`.

Ergebnis: EINRICHTEN faellt von 86 auf **2** (REPOS `foreman` — venv fehlt,
HANDEL `kerzenschluss_bias.py` — kein Startbefehl). Beide sind echte Luecken und
bleiben stehen.

### Gefunden: das Manifest-Feld `warnungen` wurde nie gelesen

`fuellen.py` schreibt `warnungen` seit jeher in die Datei, `manifest_laden` hat
es **nie gelesen** — die Liste startete als `[]` und wurde nur von
Befehls-Fehlern gefuellt. Ein Vermerk, den niemand sieht, ist keiner: die
„NIE von Hand starten"-Warnung von `dauerlauf.py` war im Fenster unsichtbar.
Behoben (Typ wird geprueft, ein falscher Typ ist ein Eintragsfehler).

### Die Junction-Falle im Doppel-Scan

Ein Scan ueber alle `.git`-Ordner fand **87 Klone** und sieben „gleiche Herkunft
an mehreren Orten". Fast alle sind gewollt oder schon weggeraeumt
(`Ausgemustert\klon-doppel-20260930`). **Eine** war echt: der zweite
`kraken-cli`-Klon an der BrainFiles-Wurzel (5,5 MB, **ohne** Bau) neben dem
gebauten in `Werkstatt/Repos` (2,7 GB, `target/release/kraken.exe` — den
`Agenten/Werkzeuge/kraken.ps1` benutzt).

Und **eine** war keine: `Werkstatt\Repos\intelligent-trading-bot` ist eine
**Junction** auf `Werkstatt\intelligent-trading-bot`. Ein Inhalts-Fingerabdruck
ueber beide Pfade liefert denselben Hash — das sieht wie eine Dublette aus und
ist dieselbe Ablage. Die alte Manifest-Notiz („Zweite Ablage des
ML-Backtest-Pruefstands") hat den Irrtum noch bestaetigt. Beim Verschieben des
„Duplikats" wanderte der echte Ordner weg und die Junction zeigte ins Leere; das
Fenster meldete die Zeile als FEHLT. Beide Zeilen tragen jetzt den Vermerk, der
Start steht in der Repos-Zeile.

**Merksatz: vor jedem Duplikat-Urteil die Reparse-Punkte pruefen.** Ein
Inhaltsvergleich ueber zwei Pfade beweist nichts, wenn einer ein Verweis ist.
`Get-ChildItem -Force | Where-Object { $_.Attributes -band
[IO.FileAttributes]::ReparsePoint }` kostet eine Sekunde. Unter `O:\Werkstatt`
gibt es genau **einen** solchen Verweis (diesen); unter `Agenten\Hermes\skills`
die bekannten sieben `okx-*`.

### Was noch auffiel (nicht angefasst)

- **`MaxHirn\codex`** (0,66 GB) ist als **Gitlink** (Modus 160000) im
  BrainFiles-Repo eingetragen — ein Klon im Vault, und der Vault sagt selbst
  „hier liegt nichts, was startet". Ein Gitlink auf einen nicht existierenden
  Unterbau ist beim Klon kaputt.
- **`MaxHirn\DockerDesktopWSL`** (4,88 GB) — Docker-Daten im Vault. Der Vault
  geht nach `G:`, das Volumen wird also mitgesichert.
- `Werkstatt\handel-stack` (0,03 GB) ist der eingefrorene Spiegel vom 18.09. —
  gewollt, im Manifest als Rolle „Spiegel (18.09.)" benannt.
- `Werkstatt\Ausgemustert` 4,86 GB (`c-entlasten` 3,62 = alte Hermes-Anlage,
  `installer` 0,73, `klon-doppel` 0,51).
- In `Werkstatt\Repos` sind **19,42 GB** der 26,26 GB venv/node_modules/target/
  `.git` — wieder herstellbar, aber genau das, was die STARTBAR-Zeilen tragen.

### Zahlen

* Zentrale: **201 Zeilen** (REPOS 46 · WERKSTATT 30 · HANDEL 125), 0 NEU,
  0 FEHLT, 0 auffaellig; HANDEL **106 startbar** (vorher 62).
* **296 Tests gruen** (vorher 259 in dieser Zaehlung: +37 in dieser Runde).
* Verschoben (reversibel, nichts geloescht): `kraken-cli`-Wurzelklon →
  `Ausgemustert\klon-doppel-20260930\kraken-cli-wurzel`; Bionic-1.1.6 (634 MB),
  OKX Security Assistant (115 MB) und das VSIX-Paket →
  `Ausgemustert\installer-20260930`. Die Werkstatt-Wurzel hat jetzt 29 statt 32
  lose Dateien.
