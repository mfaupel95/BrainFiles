---
name: hermes-doctor
description: "Use when Hermes repariert/diagnostiziert werden soll."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Hermes, Wartung, Diagnose, Claude-Code, Worktree]
    related_skills: [hermes-maintenance, claude-code, hermes-agent]
---

# Hermes-Doctor — separate Claude-Code-Session zur Diagnose/Reparatur

Laeuft auf Zuruf (dieser Skill) oder als woechentlicher Diagnose-Cron. Grundidee
aus dem "Claude Code als Hermes Doctor"-Thread: ein separates Claude-Code-CLI-
Prozess untersucht den Hermes-Checkout und findet Fehler, waehrend Hermes selbst
der ausfuehrende und kommunizierende Agent bleibt (Telegram-Bus, Skills, API-Keys
unangetastet).

## Skript

`Agenten/Hermes/scripts/hermes-doctor.py`

## Zwei Modi

### Diagnose (STANDARD, sicher, rein lesend)

    python Agenten/Hermes/scripts/hermes-doctor.py --diagnose

Sammelt mechanische Befunde (hermes doctor, git-Status, Gateway-Log-Fehler) und
schreibt `logs/hermes-doctor-diagnose-<stamp>.json`. Fasst den Live-Checkout
NICHT an, startet/stoppt nichts, liest keine Secrets.

Mit Claude-Code-Analyse (Ursachen + empfohlene Fixes):

    python Agenten/Hermes/scripts/hermes-doctor.py --diagnose --claude --max-turns 10

### Repair (explizit, opt-in, worktree-isoliert)

    python Agenten/Hermes/scripts/hermes-doctor.py --repair --max-turns 15

Legt ein git-worktree vom Checkout an, kopiert `doctor-context.md` als CLAUDE.md
hinein und laesst Claude Code dort mit Edit/Write/Bash(git*)/Bash(pytest*)
arbeiten. Der Fix-Branch bleibt zur Pruefung stehen; das Worktree wird entfernt.
Der Live-Checkout bleibt unberuehrt. `--aufgabe "..."` ueberschreibt die
Standard-Reparatur mit einer eigenen Aufgabe (z.B. harmloser Test: nur zaehlen,
kein Code aendern) - noetig fuer unbeaufsichtigte Tests. WICHTIG:
claude_ausfuehren muss im repair-Modus cwd=str(doc_dir) bekommen, sonst waere
die Isolation aufgehoben.

## Repair-Endtest nach Rate-Limit-Reset

Einmal-Cron `hermes-doctor-repair-test` (job faf1cdae33d8, 20.09.2026 03:45,
deliver telegram, no_agent) nutzt `scripts/hermes-doctor-repair-test.py`, das
`--repair --aufgabe "<TODO zaehlen, kein Code aendern>" --max-turns 3`
ausfuehrt. Er prueft die volle Repair-Pipeline ohne den Live-Checkout zu
beruehren. Nach dem Lauf: Worktree-Liste pruefen (muss nur Haupt-Checkout
zeigen) und befund.json in logs/ lesen.

## WICHTIGE FALLEN

1. **Claude Code kann rate-limitiert sein** (weekly limit / out_of_credits).
   Das Skript erkennt das und meldet `claude_gesperrt` im Befund statt eines
   kryptischen Fehlers. Die mechanische Diagnose ist dann trotzdem vollstaendig.
   Das Limit resetet um 2 Uhr (Europe/Berlin).
2. **`claude` braucht den ABSOLUTEN Pfad** — subprocess scheitert mit blosem
   Namen auf Windows (WinError 2), obwohl `claude` auf PATH ist. Das Skript
   loest ihn per `shutil.which` auf.
3. **Prompt per stdin pipen**, nicht als Argument — der volle `hermes doctor`-
   Output sprengt das Windows-Befehlszeilenlimit (~32k Zeichen).
4. **PYTHONHOME/PYTHONPATH entfernen** vor jedem subprocess (uv-venv-Falle).
5. **Worktree-Isolation pruefen** nach jedem Repair-Lauf:
   `git -C Agenten/Hermes/hermes-agent worktree list` muss nur den Haupt-Checkout
   zeigen, und `git status --porcelain` darf durch den Doctor nicht veraendert
   sein.

## Verifikation nach einem Lauf

- Befund-Datei existiert unter `Agenten/Hermes/logs/hermes-doctor-*.json`.
- `git -C Agenten/Hermes/hermes-agent worktree list` zeigt nur den Haupt-Checkout.
- `git -C Agenten/Hermes/hermes-agent status --porcelain` unveraendert (die 3
  package.json-Aenderungen aus `npm audit fix` bleiben liegen).

## Woechentlicher Diagnose-Cron (aktiv seit 19.09.2026)

Cron `hermes-doctor-check` (job 011d13bd9684, Montag 9:45, deliver telegram,
no_agent) nutzt den Wrapper `scripts/hermes-doctor-report.py`, der `--report`
an hermes-doctor.py durchreicht (der Scheduler ruft Skripte OHNE Argumente
auf - das script-Feld ist nur ein Pfad). NUR Diagnose, kein --claude, kein
--repair - ein Cron repariert nie automatisch. Der Bericht IST die Lieferung
(wie repo-updates-check/skill-usage-report).
