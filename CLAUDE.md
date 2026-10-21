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

- **Arbeitsverzeichnis (seit 30.09.2026):** Hermes' Werkzeuge und Sitzungen starten in `Agenten/Hermes`, nicht in dieser Wurzel. Zwei Mechanismen tragen das: `terminal.cwd` in `Agenten/Hermes/config.yaml` fuer Gateway, Cron und entfernte Backends, und ein `hermes`-Wrapper in Max' PowerShell-Profil (`Documents/PowerShell/Microsoft.PowerShell_profile.ps1`) fuer die interaktive CLI/TUI - eine solche Sitzung uebernimmt naemlich das Startverzeichnis der Shell, `terminal.cwd` gilt dort nicht. Alle Pfade in Skills, Notizen und Wiki sind relativ zur **Wurzel** - vor einem solchen Aufruf also `cd "$HERMES_HOME/../.."` (kurz `cd ..`) oder mit absolutem Pfad arbeiten. Skripte unter `Agenten/Routinen` und die Cron-Wachen lokalisieren sich selbst (`$PSScriptRoot`, `__file__`) und sind davon unberuehrt; die Wurzel-Aufrufer `omnitrade.cmd`/`omnitrade-auswertung.cmd` arbeiten mit `%~dp0` und laufen aus jedem Verzeichnis.
- **Wurzel bleibt leer (seit 11.10.2026):** In dieser Wurzel liegen nur die vier Hauptordner, Regeldateien, README, die `.cmd`-Aufrufer und Konfigurationsordner (`.claude`, `.git`, `.githooks`, ...). Keine Plaene, Specs, Handover, Dumps, venvs, `node_modules`, `.env`- oder Compose-Dateien hier ablegen. Plaene und Specs (auch die Vorgabe `docs/superpowers/plans|specs/` des superpowers-Plugins) gehoeren nach `Werkstatt/Projekte/`, Uebergaben nach `Werkstatt/Austausch/`; kein `npm install` in der Wurzel. Altbestand liegt in `Werkstatt/Altlasten-Wurzel-2026-10-11/`. Geprueft taeglich vom Konfig-Doktor (Modul `wurzel`, Erlaubt-Liste dort).
- **Fremd-Repos (Klone):** `Werkstatt/` haelt einen Klon je Repo direkt im Ordner (seit 14.10.2026, nicht mehr unter `Werkstatt/Repos/`) - `origin` = `upstream` (das Original), kein Fork-Mirror mehr; shallow, `git fetch --unshallow` fuer volle Historie. Eigene Werks-Repos (omnitrade, handel-stack, ...) liegen ebenfalls direkt in `Werkstatt/`.
- **Bots je Repo:** Hermes-Profile unter `Agenten/Hermes/profiles/<bot>/`, Start-Verzeichnis `Werkstatt/<repo>`; chat `hermes -p <bot> chat` (oder Bots-Tab im Desktop).
- **Bus-Suite:** `cd Agenten/Bus && python tests/test_ende_zu_ende.py` - Ausgabe endet mit "Ende-zu-Ende bestanden".
- **MCP-Abgleich:** `Agenten/mcp-sync-check.ps1` (eingebunden in systempruefung.ps1).
- **Einzelner Test:** Bus-Tests sind direkt ausfuehrbare Skripte (`cd Agenten/Bus && python tests/test_journal.py`, kein unittest/pytest). Handel-Tests nutzen unittest, z. B. `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_handelszentrale*.py"`. Handel-Tests laufen ueber `Agenten/Routinen/handel-tests.ps1`; Unterordner (`gitter/`, `kopier/`, `scanner/`, `xperp/`, ...) haben eigene `tests/`.
- **Werkzeug-Tests:** `Agenten/Werkzeuge/tests/` (zweige, bereiche, fremd, ...) sind unittest, aus der Wurzel: `python -m unittest discover -s Agenten/Werkzeuge/tests -p "test_zweige.py" -v` oder direkt `python Agenten/Werkzeuge/tests/test_zweige.py`. Die Tests bauen echte temporaere Git-Repos (kein Mock).
- **xperp (Spur 2, OKX-Perpetuals):** Live-Pfad `Agenten/Handel/xperp/handeln.py` (`--vorschau` | `--papier` | `--live` | `--wachen`); gerechnet wird nur in `bot.py`, `handeln.py` holt die Zahlen von dort. Tests liegen zweifach: `test_*.py` neben dem Code und in `tests/`, beide unittest: `cd Agenten/Handel/xperp && ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests` bzw. `-m unittest test_deckel`. Der Trailing-Stop lebt in `Agenten/Handel/trailing.py`, die Verdrahtung in `xperp/handeln.py` (nur aktiv mit `trailing_aktiv` in der Wache).
- **Handel (Wurzel-Wrapper):** `omnitrade.cmd` (Stand; `start` = Live-Lauf im OKX-DEMO, nur einer zur Zeit; `ui` = Fenster) und `omnitrade-auswertung.cmd` (rein lesend). Detailwissen: `Agenten/Handel/README.md`, `MaxHirn/Wissen/Omnitrade.md`.
- **Regeldatei-Paare:** `CLAUDE.md`=`AGENTS.md` in der Wurzel, in `MaxHirn/` und in `Werkstatt/` muessen identisch bleiben - wer eine aendert, aendert beide. Maschinell geprueft werden die Paare in `MaxHirn/` (`Agenten/Routinen/wissen-index-pruefen.ps1`) und seit 09.10.2026 alle drei Paare taeglich durch den Konfig-Doktor (Block 16 der Systempruefung, Modul regelpaare); das Wurzel-Paar war am 03.10.2026 auseinandergelaufen (Zweig-Abschnitt in `AGENTS.md` noch Stand 16.09.2026) und wurde angeglichen.
- **Bereichs-Besitz (seit 04.10.2026):** Drei Sitzungen teilen sich denselben
  Arbeitsbaum, und JEDE darf ueberall schreiben - deshalb gewinnt der Schnellere, und
  der geteilte Git-Index ist nur das spaeteste Symptom. Die Hausloesung ist
  Regelwerk plus eigene Zweige (seit 08.10.2026, siehe Abschnitt
  Zweige; die frueher verworfene Zweig-Variante gilt nicht mehr). Der Besitz
  steht in `Agenten/BEREICHE.json`, geprueft mit `python Agenten/Werkzeuge/bereiche.py
  --register`: `handel` = `Agenten/Handel/`, `bot` = `Agenten/Bus/`,
  `Agenten/Hermes/skills/`, `Agenten/Hermes/profiles/`, `Agenten/MCP-Manifest.json`,
  `wissen` = `MaxHirn/Wissen/`, `MaxHirn/Archiv/TASKS.md`. **Alles andere ist FREI** -
  ein Bereich sperrt seinen Elternordner nicht, sonst laege der groesste Teil des Baums
  still und die Regel wuerde umgangen. Wer in einen fremden Bereich schreibt, meldet
  das als BEFUND (`--aufrufer <bereich> --pfad <pfad>`, Exitcode 1 bei Konflikt), es
  wird nicht blockiert.
  Seit 09.10.2026 gibt es zusaetzlich den Commit-Hook `.githooks/pre-commit`
  (einmalig je Klon `git config core.hooksPath .githooks`): wer sich per
  `BRAINFILES_BEREICH=handel|bot|wissen` ausweist, kann nicht in fremde Bereiche
  committen; ohne die Variable wird nichts blockiert.
- **Kein `git stash` im geteilten Arbeitsbaum (seit 08.10.2026).** Der Stash
  friert Arbeit ein, während andere Sitzungen weiter committen; ein späteres
  `stash pop` konfligiert gegen Zwischencommits (Fall „Vault-Schutzschicht":
  7 Konflikte gegen 14 Zwischencommits). Eigenes sofort committen statt
  stashen. Pop doch nötig: bei Konflikt ist OURS der aktuelle Repo-Stand,
  THEIRS der ältere Stash - Seiten per Datum vergleichen (Stash-Datum gegen
  die Commits, die die Datei seither berührt haben), nur übernehmen, was im
  Repo noch fehlt; Stash erst nach Verifikation droppen.

## Zweige (Stand 08.10.2026)

- **Jeder Agent arbeitet auf einem eigenen Zweig, der von `master` abzweigt**
  (`git switch -c <agent>/<thema> master`, z. B. `claude/gold-hebel`). Ein
  Arbeitsbaum haelt nur einen Zweig - parallele Agenten brauchen deshalb je einen
  eigenen Arbeitsbaum unter `.worktrees/` (`git worktree add .worktrees/<name> -b
  <zweig> master`), nie `git switch` im geteilten Hauptbaum.
- **Gemergt wird erst, wenn die PR abgeschlossen ist:** Tests gruen, PR eroeffnet
  und freigegeben. Vorher nichts nach `master` schieben. Gemergt wird per PR; nach
  dem Merge Zweig und Arbeitsbaum loeschen (lokal `git branch -d <zweig>`,
  `git worktree remove`, `git push origin --delete <zweig>`). Ein Zweig mit
  offener Arbeit bleibt bis dahin stehen und ist kein Altlast-Verdacht.
- `master` ist der Integrationszweig: nur abgeschlossene, getestete Arbeit, dazu
  die Routinen (kb-sync, Fremdarbeit-Einziehen) und reine Pflege-Commits ohne
  eigenen Zweig (Notizen, Index, TASKS-Vermerke).
- `zwischenstand` ist keine Arbeit, sondern die automatische Sicherung der
  Routine `zwischenstand.ps1` (Commit direkt auf diesen Zweig, stuendlich). Nie
  dort committen, nie anfassen; Aufraeumen, wenn er stoert: `git update-ref -d
  refs/heads/zwischenstand` (Regeln in MaxHirn/Wissen/Routinen.md).
- Uncommittete Arbeit bleibt das eigentliche Verlustrisiko, nicht der Zweig:
  oft committen, auf dem eigenen Zweig auch halbfertig.

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
