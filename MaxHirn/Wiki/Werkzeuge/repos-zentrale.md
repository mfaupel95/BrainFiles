---
titel: Repos-Zentrale (Startfenster fuer Werkstatt/Repos)
aktualisiert: 2026-09-25
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

## Gemessener Stand (25.09.2026)

- 36 Repos auf der Platte, 36 Manifest-Eintraege, 5 startbar.
- Nachtraeglich dokumentiert: intelligent-trading-bot, moon-dev-ai-agents,
  openmontage, kraken-cli, fomo-robinhood-radar (Befehle), Kronos/laya/
  robinhood-fomo-kronos-arena (nur Anleitung, kein startbarer Weg).
- Die 5 Klone ohne Manifest-Eintrag (fomo-robinhood-radar, kraken-cli, Kronos,
  laya, robinhood-fomo-kronos-arena) sind aufgenommen — vorher standen sie als
  „NEU" und ohne jede Erklaerung im Fenster.
- Was noch keine eigenen Befehle hat, steht als Task in `Archiv/TASKS.md`
  (T-073): dort fehlt Wissen ueber das Repo, nicht Code.

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