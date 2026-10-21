---
name: gbrain-memory
description: Use when durable memory recall or saving facts is needed. Operates Max's local GBrain installation at /workspace/gbrain (WSL archlinux) via its absolute launcher; also for remember/recall/forget requests.
---

# GBrain memory

This Bot runs on Windows; the GBrain installation lives inside the WSL2
distribution `archlinux` at `C:\...`-unreachable POSIX path `/workspace/gbrain`.
The executable for every memory command is the installation's generated
absolute launcher, called THROUGH WSL so the same installation with the same
root is always selected:

```
wsl.exe -d archlinux /workspace/gbrain/bin/gbrain <command> [args...]
```

Do NOT invent a different `gbrain` from PATH or a different root; this
installation owns the host brain and the source `default`. Use this same
absolute launcher path from every conversation and native routine.

## When to use

Recall relevant memory BEFORE answering personal or continuing-work questions.
Use `gbrain recall --help` through the launcher for the installed command
schema. Explicitly remember user-requested durable facts, with their source
and date.

## Rules

- Preserve uncertainty and distinguish what the user said from an inference.
- Correct or forget outdated facts when asked; verify the change through a
  fresh recall. Forgetting withdraws active memory; history, source material,
  and private backups may remain. Never promise physical erasure.
- Never import connected-service history or enable automatic capture without
  the user's instruction.
- Do not replace the agent's identity. This is one shared local installation,
  not a boundary between Bots.
- Memory calls are finite CLI processes. A busy database means another command
  is running: retry after it finishes; never remove its lock.

## Setup evidence (2026-09-20)

- Init mode: keyless fact memory (`--pglite --no-embedding`), search mode
  `conservative` (auto-selected: no expansion-capable API key).
- Round trip verified: fact #1 "My setup test phrase is amber-orbit-f0c2c7",
  provenance "explicit setup test, 2026-09-20", entity `projects/gbrain-setup`,
  recalled by a separate process with the exact phrase.
- Fresh-conversation test VERIFIED (2026-09-20): a new conversation recalled
  the phrase via this skill and the WSL launcher without it being supplied.
- Bulk capture and paid maintenance stayed opt-in (off).
- Generated instructions: `/workspace/gbrain/instructions/gbrain-skill.md` and
  `/workspace/gbrain/instructions/maintenance.md` (Linux paths inside WSL).
- Receipt: `/workspace/gbrain/.gbrain/agent-install/receipt.json` (state
  `ready`).