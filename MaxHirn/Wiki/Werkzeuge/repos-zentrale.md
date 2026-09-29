---
titel: Repos-Zentrale (Startfenster fuer Werkstatt/Repos)
aktualisiert: 2026-09-29
tags: [werkzeug, repos, oberflaeche]
---

# Repos-Zentrale — ein Fenster fuer alle Repos

> **Kernsatz:** Der Bereich „Was dieses Projekt kann" ist die Antwort auf „ich
> kenne mich in der Kommandozeile nicht aus". Man waehlt links ein Projekt und
> bekommt rechts seine Befehle als anklickbare Zeilen — mit einem Knopf, der sie
> ausfuehrt, einem, der sie in die Zwischenablage legt, und einem, der den
> Repo-Bot damit beauftragt.

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
cd Agenten\Werkzeuge\repos-zentrale\tests
..\.venv\Scripts\python.exe -m unittest discover -s . -t .
```

Bekannt rot (bewusst, nicht durch dieses Werkzeug verursacht): `test_manifest.
test_jedes_bot_profil_des_manifests_existiert` — das Manifest nennt Bot-Namen,
deren Profil seit dem 19.09.2026 unter `profiles/.deleted/` liegt (T-072).