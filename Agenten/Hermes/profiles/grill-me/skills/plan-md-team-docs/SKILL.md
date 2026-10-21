---
name: plan-md-team-docs
description: "Use for PLAN.md team documentation in the Werkstatt repo."
version: 1.0.0
author: grill-me
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [plan-md, team-workflow, documentation, grill-me, werkstatt, decisions]
---

# PLAN.md Team Documentation

The team's standing work plan lives in `PLAN.md` at the root of the grill-me-skill repo
(`O:\Werkstatt\grill-me-skill` — same tree as `C:\Users\faupe\Documents\BrainFiles\Werkstatt\grill-me-skill`
via drive mapping). Every decision, Auftrag, and implementation gets a dated section; the repo's
git history is a sequence of exactly such commits.

## When to use

- The user (@user) makes a decision in chat the team must act on or remember.
- An Auftrag (tasking) is being defined, split, decided, or implemented.
- An implementation is verified and its state must be recorded (which profiles/models/jobs
  changed, with evidence).

## Procedure

1. Read PLAN.md fully first — section numbers are sequential and cross-referenced (§-numbers).
   Find the last top-level `## N.` section and the open questions it leaves; extend the existing
   section when the decision belongs to an open Auftrag, otherwise append a new one.
2. New section: `## N. <topic> (date, author)`. Never renumber existing sections.
3. Section structure:
   - **Decisions** as numbered items, each attributed `(@user, date)` when it came from the user —
     an unattributed decision reads as agent invention.
   - **Umgesetzt & verifiziert** bullets with the ACTUAL changes: exact model ids, config keys,
     cron job IDs, paths. Use the team's marker style for measured state ("verifiziert/gemessen,
     nicht behauptet") — never document a state you have not re-read.
   - **Offen / Hinweise**: what still depends on someone else (measurements, restarts, gating
     decisions), with the owning profile @mentioned.
4. Concise German (the team's working language). Decisions + evidence only — no chat transcripts.
5. Commit: one commit per PLAN.md update, message pattern
   `PLAN.md §N: <topic> (<short change summary>)`. Do not push — the team pushes separately.

## Pitfalls

- If the write/patch tools refuse the repo's C:\ paths (write-safe-root mismatch on this
  machine), append via terminal instead: python heredoc with `encoding='utf-8'` and a RAW
  string for any text containing Windows paths (a bare `C:\Users` in a normal Python literal is a
  `\U` escape error). Verify with `git diff` before committing.
- When claiming two paths (drive-mapped vs physical) are identical, verify with a live probe
  (create a file on one side, check the other) — identical listings can also be a synced copy.
- Do not mark a change "verifiziert" on the strength of the tool's success line alone —
  re-read the target file/config afterwards (a CLI success line can name the WRONG file).
