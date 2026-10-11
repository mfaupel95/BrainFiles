---
name: brainfiles-git-hygiene
category: software-development
description: Audit and clean BrainFiles git repo; build watchdog crons.
version: 1.0.0
author: Hermes Agent
license: proprietary
metadata:
  hermes:
    tags: [git, hygiene, worktree, watchdog, cron, brainfiles]
    related_skills: [handel-spuren, hermes-agent]
---

# BrainFiles Git-Hygiene und Wachen bauen

## When to Use

Max bittet um „git anbindung prüfen und arbeit auf lücken und fehler prüfen", „wie verhindern wir zukünftige fehler durch falsche worktrees und dateischwund", oder darum, eine Wache auf einen wiederkehrenden Fehler zu bauen. Zwei Klassen: (1) den Git-Zustand des BrainFiles-Repos auditieren und aufräumen, (2) eine no_agent-Cron-Wache bauen, die einen Fehler automatisch meldet.

## Git-Audit: Reihenfolge

1. **`git status --short -b`** — uncommittete Arbeit + ahead/behind gegen origin. Alles committen, bevor du aufräumst.
2. **Fremde Arbeit in getrennten Commits sichern.** Was nicht von dir stammt (MCP-Manifest, config, SKILL-Lehren, neue Profile), committest du mit `git commit --author="Andere Sitzung <fremd@local>"` — nie vermischt mit eigener Arbeit, nie `git add -A`. Eigene Arbeit (z. B. `skills.disabled`) mit `--author="Hermes <hermes@local>"`.
3. **Untracked prüfen:** `git check-ignore -v <pfad>` sagt, ob etwas bewusst ignoriert ist (z. B. `Agenten/.claude/settings.local.json`, `Agenten/Hermes/cron/jobs.json`). Ein neues Hermes-Profil (`profiles/<name>/config.yaml` + `profile.yaml` + `SOUL.md`) gehört versioniert; `.env`/`cron`/`cache` sind ignoriert.
4. **Zweige/Worktrees messen:** `python Agenten/Werkzeuge/zweige.py` (nur messen) bzw. `--entfernen --push` (belegte weg). Das Werkzeug klassifiziert mit drei Zeugen (merge-base, rev-list, cherry) — `behalten` = echter Vorlauf, `entfernen` = in master ohne Vorlauf.
5. **Push:** `git push origin master` nach dem Aufräumen; `git status -sb` muss `## master...origin/master` (ohne ahead) zeigen.
6. **Regelpaare prüfen:** `CLAUDE.md`/`AGENTS.md` in Wurzel, `MaxHirn/`, `Werkstatt/` müssen byte-identisch sein (`cmp -s`).

## Worktree-Regeln

- **Ein Worktree gehört unter `.worktrees/` in der Wurzel, NIE in den Hauptbaum.** `Agenten/.claude/worktrees/<name>` (Claude-Code-Ablage) und `Agenten/.claude/worktrees/` sind Fehler — sie verunreinigen den geteilten Arbeitsbaum und können von `fremdarbeit-einziehen.ps1` als Fremdarbeit committet werden.
- **`git worktree prune` bereinigt verwaiste Einträge NICHT immer.** Ein Worktree, dessen Ordner weg ist, aber den git noch registriert, bleibt nach `prune` stehen. `zweige.py` erkennt ihn über `git -C <pfad> rev-parse --git-dir` (returncode != 0 = verwaist).
- **MSYS/git-bash löst Pfade anders auf als nativ.** `os.path.isdir(pfad)` kann True melden, obwohl der Ordner nativ weg ist (Junction/Reparse-Artefakt). Der robuste Zeuge ist `git -C <pfad>` selbst, nicht `os.path.isdir`.
- Ein Worktree, dessen Ordner von einem **aktiven Prozess** (laufende Claude-Code-Sitzung) gehalten wird, lässt sich nicht löschen („Device or resource busy"). Fremde Prozesse nicht beenden — den leeren Restordner stehen lassen, er verschwindet, wenn die Sitzung fertig ist.
- Vor dem Entfernen einer Junction unter einem Worktree-Pfad das Ziel und den genauen Linkpfad nativ prüfen; Junction-Operationen können unerwartet das Ziel betreffen, daher nie rekursiv auf dem Zielpfad löschen.

## Wache bauen (no_agent-Cron)

Das Hausmuster für jede Wache auf einen wiederkehrenden Fehler:

1. **Werkzeug erweitern, das den Fehler misst** (z. B. `zweige.py` um Worktree-Lage/detached/verwaist), mit `--json`-Ausgabe für Anhänger.
2. **Wache-Skript** unter `Agenten/Hermes/scripts/`: ruft das Werkzeug mit `--json`, extrahiert nur die Fehlerklassen, **meldet nur bei Auffälligkeit** (leere Ausgabe = nichts senden), dedupliziert über eine Merkdatei mit `RUHE_STUNDEN` (dieselbe Feststellung höchstens alle 6 h).
3. **Cron im Hauptprofil** (`hermes --profile default cron create`), nicht im bots-Profil — dort liegen alle Wachen-Crons. `--script` ist **relativ zum scripts-Ordner** (nur den Dateinamen angeben, nicht den vollen Pfad). `--no-agent --deliver telegram`.
4. **Verifizieren:** `hermes --profile default cron run <name>` (manueller Lauf), Gegenprobe (den Fehler simulieren → Befund erscheint), Ruhe-Logik (zweiter Lauf leer).
5. **`Agenten/Hermes/cron/jobs.json` ist git-ignoriert** — der Cron-Eintrag wird nicht versioniert. Das ist Design (konsistent mit allen Wachen), kein Fehler; nur das Skript selbst committen.

## Dateischwund über den ganzen Baum

Der T-100-Fall (versionierte Datei verschwindet, `fremdarbeit-einziehen.ps1` committet die Löschung nach 30 Min) kann überall passieren, nicht nur in `scripts/`/`Handel/`. Eine Baum-Wache, die den ganzen Dateibaum `rglob`-t, wäre zu teuer (Minuten). **Stattdessen die versionierte Textebene prüfen:** `git ls-files` (~2800 Dateien, Laufzeit ~1 s) — das ist genau das, was T-100 schützt. Git-Soll (in HEAD, aber weg) + Merkliste + Leer-Erkennung.

Bei der Merkliste für unversionierte Dateien nicht stillschweigend behaupten, der ganze Baum sei abgedeckt: ein schneller `git ls-files`-Wächter deckt nur versionierte Pfade; behalte gezielte Snapshot-Wächter für kleine, risikoreiche Ordner, wenn frische uncommittete Dateien ebenfalls geschützt werden müssen.

## Fallen

- **PowerShell über git-bash:** `$_.X` wird von bash zerlegt. Ein `.ps1`-File schreiben und mit `powershell -ExecutionPolicy Bypass -File` ausführen, statt Inline-`-Command`.
- **`hermes cron create` mit vollem `--script`-Pfad** verdoppelt den Pfad (`scripts/scripts/...`). Nur den Dateinamen angeben.
- **`git status` nach dem Aufräumen:** ein leerer `Agenten/.claude/`-Ordner (nur ignoriertes `settings.local.json`) bleibt als `??` stehen — harmlos, nicht committen.
- **Git-Worktree Hygiene:** No_agent-Cron-Wachen (`dateischwund-wache-baum`, `zweige-wache`) decken den Git-Zustand ab. Bei einem Worktree-Konflikt oder Dateischwund `git status` prüfen, nicht blind `git checkout` oder `prune`. Die `dateischwund-wache-baum.py` deckt nur die versionierte Textebene ab (`git ls-files`); keine Snapshots über `rglob` in `.venv/`.
- **Worktree-Aufräumen:** Verwaiste Junctions im Worktree-Pfad (z.B. `...\nautilus`) lassen sich nicht via `git` lösen, sondern müssen explizit per PowerShell/File-Tool entfernt werden (`Remove-Item -Force -Recurse`).
