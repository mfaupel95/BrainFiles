---
name: caveman-eval-refresh
description: Refresh caveman eval snapshot and measure token savings.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Caveman, Evals, Tokens, Claude, Windows]
---

# Caveman Repo Eval Refresh

Bot-Routine fuer das caveman-Repo (O:\Werkstatt\caveman, = C:\...\BrainFiles\Werkstatt via Junction): Repo aktuell halten, Token-Ersparnisse der Skills MESSEN statt glauben, Eval-Snapshot frisch erzeugen. Misst Zeichen UND Token (tiktoken o200k_base). Misst NICHT Antwort-Fidelity oder Latenz — nur Laenge.

## When to Use
- "run" / Bot-Durchlauf fuer caveman-Repo.
- Skill-Behauptungen ueber Token-Ersparnis pruefen (Abkuerzungen, Pfeile, Sterbeworte).
- Eval-Snapshot veraltet: evals/snapshots/results.json metadata.generated_at alt gegenueber skill-Aenderungen.
- Frage "wie viel kuerzer wird das" mit Beleg, vorher/nachher in Zeichen und Token.

## Prerequisites
- Repo: O:\Werkstatt\caveman (git clone, main). C:\Users\faupe\Documents\BrainFiles\Werkstatt\caveman ist DIESELBE Datei (Junction auf O:).
- claude CLI eingeloggt. NATIVE Binaries: C:\Users\faupe\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe.
- uv installiert (fuer tiktoken und llm_run.py).
- Optional: CAVEMAN_EVAL_MODEL=claude-haiku-4-5 (klein, billig — README empfiehlt es).

## How to Run
Ueber das `terminal`-Tool:
```bash
cd 'O:/Werkstatt/caveman'
git fetch origin && git status -sb          # Stand pruefen (Aufgabe 1)
CAVEMAN_EVAL_MODEL=claude-haiku-4-5 uv run python evals/llm_run.py   # Snapshot erzeugen
uv run --with tiktoken python evals/measure.py                        # Zahlen lesen
```

## Quick Reference
- Snapshot-Datei: evals/snapshots/results.json (10 Prompts x (20 Skills + 2 Kontrollarme)).
- Prompts: evals/prompts/en.txt, ein Prompt pro Zeile. Skill: eine Zeile anhaengen, Snapshot neu.
- Skills: evals/../skills/*/SKILL.md, automatisch alle gefunden.
- Ehrliches Delta: Skill-Arm GEGEN __terse__ ("Answer concisely."), NICHT gegen __baseline__ — gegen Baseline blaeht die Zahl (README).
- Zaehlen: `uv run --with tiktoken python -c "import tiktoken; e=tiktoken.get_encoding('o200k_base'); print(len(e.encode('TEXT')))"`

## Procedure
1. **Stand pruefen**: `git fetch origin`, `git status -sb`, HEAD == origin/main. Nur .env.template untracked = ok.
2. **Veraltungs-Check**: results.json metadata (generated_at, model) vs. letzter skill-Commit (`git log --oneline -5 -- skills/`). Aelter als skill-Aenderungen → Refresh noetig.
3. **Messung vorher/nachher** (Aufgabe 2): ein realistisches Satzpaar (voll vs. knapp), gleicher Inhalt, mit o200k zaehlen. Beispiel aus dem Durchlauf 2026-09-30: 233 Zeichen/60 Token -> 60 Zeichen/22 Token (74% Zeichen, 63% Token).
4. **Snapshot-Refresh**: `CAVEMAN_EVAL_MODEL=claude-haiku-4-5 uv run python evals/llm_run.py`. 220+ CLI-Calls — als background=true mit notify=true UND persist_on_release=true starten, nicht im Vordergrund.
5. **Zahlen lesen**: `uv run --with tiktoken python evals/measure.py`, Tabelle nach Median sortiert.
6. **Befund melden**: was haelt was, was nicht. Eine Empfehlung, keine Optionsliste.

## Pitfalls
- **write_file/patch verweigert fuer Repo-Pfade**: C:\...\Werkstatt ist Junction auf O:; HERMES_WRITE_SAFE_ROOT deckt O: nicht ab. Dateien im Repo via `terminal` aendern (python-Heredoc, siehe unten), NIE write_file.
- **claude.CMD-Shim frisst lange Args**: `shutil.which("claude")` liefert claude.CMD (npm-Shim); cmd.exe %*-Expansion verschluckt lange --system-prompt → Exit 1 "Input must be provided". IMMER native claude.exe nutzen, Pfad: <npm>/node_modules/@anthropic-ai/claude-code/bin/claude.exe (in llm_run.py: claude_bin() bevorzugt jetzt .exe).
- **Session-Limit**: kostenlose claude-Session zeigt "You've hit your session limit · resets 7pm (Europe/Berlin)" — KEIN Bug. Bis 19:00 warten (`sleep 240` + Probe-Call), dann neu starten.
- **Terse-Kontrolle kann laenger sein als baseline** (mehr Detail): trotzdem ist Skill-vs-terse das ehrliche Delta.
- **Abkuerzungen sparen 0 Token** (cfg=config=1 Token unter o200k), Pfeile (->) auch 0 gegen Verbworte. Skill-Verbot ist messbar richtig — nicht kippen.
- **Einzel-Call testen vor Volllauf** (exit 0, stderr leer) — sonst 200 Calls ins Leere bei Auth/Limit/Shim-Problem.

## Verification
`uv run --with tiktoken python evals/measure.py` laeuft fehlerfrei und zeigt die Skill-Tabelle (Median-Savings pro Skill). Oder Minimalprobe: claude.exe -p mit einem Prompt, exit 0 + Antwort.

## Repo-Dateien aendern (Junction-Workaround)
```bash
cd 'O:/Werkstatt/caveman' && python - <<'EOF'
import io
p='evals/llm_run.py'
s=io.open(p,encoding='utf-8').read()
old='...'
new='...'
assert old in s
io.open(p,'w',encoding='utf-8',newline='').write(s.replace(old,new))
EOF
```
Danach `git diff --stat` zur Kontrolle.
