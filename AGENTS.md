# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# BrainFiles — vier Ordner, vier Aufgaben

Wurzel von Max' KI-Betriebssystem. Seit dem **30.08.2026** ist sie in vier
Ordner geteilt, weil vorher alles in `MaxHirn/` lag: Vault, 45 GB Archiv, 51 GB
Modellgewichte, Maschinenraum und Sitzungsreste in einem.

| Ordner | Aufgabe | Größe |
|---|---|---|
| **`MaxHirn/`** | Wissen und persönliches Archiv. Obsidian-Vault. **Hier liegt nichts, was startet.** | 45 GB |
| **`Modelle/`** | Modellgewichte und Laufzeiten. Neu herunterladbar, deshalb **nicht in der Sicherung**. | 51 GB |
| **`Agenten/`** | Was läuft: MCP-Server, Hermes, Handelsagent, Routinen, Sicherungsskripte. | 4 GB |
| **`Werkstatt/`** | Gemeinsamer Arbeitsplatz aller Modelle. Übergaben, Zwischenstände, Fremd-Repos. Durchgangsware. | 1 GB |

## Wo die Regeln stehen

**Diese Datei ist nur die Karte.** Die Arbeitsanweisung steht in
[MaxHirn/CLAUDE.md](MaxHirn/CLAUDE.md) (für Claude) und
[MaxHirn/AGENTS.md](MaxHirn/AGENTS.md) (für Hermes und Codex) — beide mit
demselben Inhalt. Dort steht auch die Reihenfolge, in der eine Anfrage
bearbeitet wird: erst `Wissen/`, dann das Archiv, erst danach das Internet.

Für den gemeinsamen Arbeitsordner gelten zusätzlich die Spielregeln in
[Werkstatt/AGENTS.md](Werkstatt/AGENTS.md).

Was nicht angefasst werden darf, steht in
[MaxHirn/Wissen/Schutzregeln.md](MaxHirn/Wissen/Schutzregeln.md) — **vor jedem
schreibenden Zugriff lesen.**

## Was die Trennung leistet

Sie ist keine Kosmetik. Jeder Ordner lässt sich jetzt einzeln entscheiden:

- **Sicherung:** `MaxHirn/` und `Agenten/` gehen nach `G:`, `Modelle/` und
  `Werkstatt/` nicht. Das spart 52 GB je Lauf.
- **Git:** Die Wurzel des Repositories liegt hier. Versioniert ist nur die
  Textebene, über eine Whitelist in `.gitignore` — erst alles ignorieren, dann
  einzeln freigeben.
- **Zugriff:** Alle Modelle lesen `MaxHirn/`, schreiben aber in `Werkstatt/`.
  Ein Original liegt nie in der Werkstatt.

## Arbeit im Repo

- **Arbeitsverzeichnis (seit 30.09.2026):** Hermes' Werkzeuge und Sitzungen starten in `Agenten/Hermes` (`terminal.cwd`), nicht in dieser Wurzel. Alle Pfade in Skills, Notizen und Wiki sind relativ zur **Wurzel** - vor einem solchen Aufruf also `cd "$HERMES_HOME/../.."` (kurz `cd ..`) oder mit absolutem Pfad arbeiten. Skripte unter `Agenten/Routinen` und die Cron-Wachen lokalisieren sich selbst (`$PSScriptRoot`, `__file__`) und sind davon unberuehrt; die Wurzel-Aufrufer `omnitrade.cmd`/`omnitrade-auswertung.cmd` arbeiten mit `%~dp0` und laufen aus jedem Verzeichnis.
- **Fremd-Repos (Forks):** `Werkstatt/Repos/` haelt einen Klon je Repo - `origin` = `mfaupel95/<name>`, `upstream` = Original (shallow; `git fetch --unshallow` fuer volle Historie).
- **Bots je Repo:** Hermes-Profile unter `Agenten/Hermes/profiles/<bot>/`, Start-Verzeichnis `Werkstatt/Repos/<repo>`; chat `hermes -p <bot> chat` (oder Bots-Tab im Desktop).
- **Bus-Suite:** `cd Agenten/Bus && python tests/test_ende_zu_ende.py` - Ausgabe endet mit "Ende-zu-Ende bestanden".
- **MCP-Abgleich:** `Agenten/mcp-sync-check.ps1` (eingebunden in systempruefung.ps1).
- **Einzelner Test:** Bus-Tests sind direkt ausfuehrbare Skripte (`cd Agenten/Bus && python tests/test_journal.py`, kein unittest/pytest). Handel-Tests nutzen unittest, z. B. `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_handelszentrale*.py"`. Handel-Tests laufen ueber `Agenten/Routinen/handel-tests.ps1`; Unterordner (`gitter/`, `kopier/`, `scanner/`, `xperp/`, ...) haben eigene `tests/`.
- **Handel (Wurzel-Wrapper):** `omnitrade.cmd` (Stand; `start` = Live-Lauf im OKX-DEMO, nur einer zur Zeit; `ui` = Fenster) und `omnitrade-auswertung.cmd` (rein lesend). Detailwissen: `Agenten/Handel/README.md`, `MaxHirn/Wissen/Omnitrade.md`.
- **Regeldatei-Paare:** `CLAUDE.md`=`AGENTS.md` in der Wurzel, in `MaxHirn/` und in `Werkstatt/` muessen identisch bleiben - wer eine aendert, aendert beide. Maschinell geprueft werden nur die Paare in `MaxHirn/` (`Agenten/Routinen/wissen-index-pruefen.ps1`); das Wurzel-Paar war am 03.10.2026 auseinandergelaufen (Zweig-Abschnitt in `AGENTS.md` noch Stand 16.09.2026) und wurde angeglichen.
- **Bereichs-Besitz (seit 04.10.2026):** Drei Sitzungen teilen sich denselben
  Arbeitsbaum, und JEDE darf ueberall schreiben - deshalb gewinnt der Schnellere, und
  der geteilte Git-Index ist nur das spaeteste Symptom. Die Hausloesung ist Regelwerk,
  nicht Isolation: **eigene Git-Zweige je Sitzung wurden gemessen verworfen** (sie
  machen es schlimmer - fremde Aenderungen kommen als Branch-Differenz zurueck statt als
  erkennbar ruhende Datei, und der Zweig-Overkill kostet den Ueberblick). Der Besitz
  steht in `Agenten/BEREICHE.json`, geprueft mit `python Agenten/Werkzeuge/bereiche.py
  --register`: `handel` = `Agenten/Handel/`, `bot` = `Agenten/Bus/`,
  `Agenten/Hermes/skills/`, `Agenten/Hermes/profiles/`, `Agenten/MCP-Manifest.json`,
  `wissen` = `MaxHirn/Wissen/`, `MaxHirn/Archiv/TASKS.md`. **Alles andere ist FREI** -
  ein Bereich sperrt seinen Elternordner nicht, sonst laege der groesste Teil des Baums
  still und die Regel wuerde umgangen. Wer in einen fremden Bereich schreibt, meldet
  das als BEFUND (`--aufrufer <bereich> --pfad <pfad>`, Exitcode 1 bei Konflikt), es
  wird nicht blockiert.

## Zweige (Stand 29.09.2026)

- `master` ist der Arbeitszweig: hier wird committet, gepusht und gemergt. Ein
  Zweig, der getrennt laeuft und liegen bleibt, kostet Ueberblick, ohne etwas
  zu sichern - darum wurde `telegram-bus` am 16.09.2026 hinein gefuehrt und
  geloescht (lokal und auf GitHub, Standardzweig ist wieder `master`).
- **Ausnahme, seit 29.09.2026: kurzlebige PR-Zweige.** Verlangt ein Ablauf
  (z. B. `<create-pr-command>`) ausdruecklich eine PR, darf dafuer ein Zweig
  angelegt werden - erzeugen, pushen, PR eroeffnen, nach dem Mergen SOFORT
  loeschen (lokal `git branch -d <zweig>` und `git push origin --delete
  <zweig>`). Kein PR-Zweig bleibt laenger als bis zum Merge liegen; ohne
  konkreten PR-Anlass gilt weiter nur `master`. Grund der Lockerung: gefuehlt
  ging Arbeit verloren - Ursache war aber kein Zweig, sondern uncommittete
  Arbeit, die zu lange im Baum stand (siehe Zwischenstand-Takt unten).
- `zwischenstand` ist keine Arbeit, sondern die automatische Sicherung der
  Routine `zwischenstand.ps1` (Commit direkt auf diesen Zweig, seit 29.09.2026
  stuendlich statt taeglich). Nie dort committen, nie anfassen; Aufraeumen,
  wenn er stoert: `git update-ref -d refs/heads/zwischenstand` (Regeln in
  MaxHirn/Wissen/Routinen.md).
- Sonst keine weiteren Zweige anlegen. Ist doch einer entstanden: auf `master`
  zusammenfuehren (`git branch -f master <zweig>`, wenn master ein Vorfahre
  ist, sonst `git merge`) und loeschen.

## Umgebung

Das System laeuft auf Windows (PowerShell, `.ps1`/`.cmd`, Pfade `G:`/`O:`). `Modelle/` und `Werkstatt/` sind Junctions auf `O:\Modelle` bzw. `O:\Werkstatt` und sind in einem frischen Linux-/Cloud-Checkout leer bzw. fehlen (`Modelle/` gibt es dort gar nicht, von `Werkstatt/` nur die versionierten Dateien). Dort lassen sich nur Textebene und plattformneutrale Python-Tests pruefen; `.ps1`-Laeufe, venvs (`.venv/Scripts/`) und Handels-/Hermes-Betrieb nicht.

## Portabilität

Keine absoluten Pfade in Skills, Notizen oder Skripten. Was der Umzug auf eine
externe SSD trotzdem kostet, steht in
[MaxHirn/Wissen/Portabilitaet.md](MaxHirn/Wissen/Portabilitaet.md); die
Ordnerstruktur selbst mit ihren Fallen in
[MaxHirn/Wissen/Ordnerstruktur.md](MaxHirn/Wissen/Ordnerstruktur.md).

## Fallen

- **`hermes.exe` und windows-mcp:** Aus einer Session, die durch den MCP-Supervisor laeuft, startet `hermes.exe` nur mit entferntem `PYTHONHOME`/`PYTHONPATH` (Symptom: `Fatal Python error: init_import_site ... _thread ... start_joinable_thread`; das venv ist gesund). Vor jedem Aufruf: `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH`.
- **PowerShell-Skripte:** `ErrorActionPreference='Stop'` + `git ... 2>&1` bricht ab, weil stderr als Fehler zaehlt (NativeCommandError). `Continue` setzen, `git clone --quiet` verwenden, Erfolg am Exit-Code messen.
- **Versionierte Textdateien** nie per Rewrite neu schreiben (LF/CRLF); wo moeglich gezielter Ersatz und Diff ansehen. AGENTS.md ist LF.
