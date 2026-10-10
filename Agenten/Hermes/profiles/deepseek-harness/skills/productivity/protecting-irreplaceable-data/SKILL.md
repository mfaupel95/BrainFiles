---
name: protecting-irreplaceable-data
description: Guard vaults/archives from bad agent writes and deletes.
---

# Protecting irreplaceable data

Use for any request shaped like "here are all my important files, make sure
nothing gets lost", "which files should be protected", "clean up / reorganize
this archive" — and before *you* run any bulk write, move, rename, or delete
across a directory of user data that may have no second copy.

The core failure this prevents: an agent treats a directory of irreplaceable
originals like a code repo, where every mistake is one `git checkout` away from
being undone. In a data vault it usually isn't.

## Step 1 — Establish the recovery baseline FIRST

Do not write a single protection rule until you know what recovery actually
exists. It determines how strict every later rule has to be.

```bash
git -C <root> status              # version control at all?
ls -la <root>                     # .bak files? snapshots? .git?
```

Then read the backup script itself — do not assume it protects you:

| Question | Why it changes everything |
|---|---|
| Is it a git repo? | No git = every overwrite is final. No checkout, no reflog. |
| Does the backup keep **history**, or only mirror current state? | The one people get wrong. |
| Are all copies in the same machine / on the same physical disk? | Three copies on one PSU is one copy. |
| Are the `.bak-YYYYMMDD` files done by hand? | Then they cover a few files, not the archive. |

**A mirroring backup is not protection against a bad write.** A `robocopy`
without `/MIR` (copy-new-and-changed) or an rsync without `--backup` propagates
your corruption to the backup at the next scheduled run. It defends against
disk failure, *not* against an agent overwriting a file. Say this to the user —
it is usually the fact that reframes the whole task.

Also: separate drive letters can be one physical disk. Verify with
`Get-Partition`/`Get-Disk` or `lsblk` before calling a second copy redundant.

## Step 2 — Classify into three tiers, not two

A binary protected/unprotected split fails: it lumps "unique originals" together
with "scripts that break silently".

**Tier 0 — irreplaceable, no second source.** Documents, photos, media,
personal knowledge notes, vault config. Read yes, write no. No bulk operations
here *even with explicit permission* — present a list, then act file by file.
Change only what the user named in this same session.

**Tier 1 — operational, change only with announcement.** Backup scripts,
scheduled-task wrappers, sorting/indexing scripts, agent instruction files
(`CLAUDE.md`, `AGENTS.md`), skills, service configs. Replaceable, but they
**fail silently** — the damage surfaces weeks later as a backup that quietly
stopped running. Rule: `.bak-YYYYMMDD` before, real execution after. A change to
a backup script is not done until a real run has confirmed it.

**Tier 2 — reproducible, free hand.** `.venv`, `__pycache__`, `node_modules`,
cloned repos, downloaded models, generated indexes/DBs, logs.

### Tier 0 traps worth calling out explicitly

- **Damaged placeholder files are evidence, not garbage.** Zero-byte or
  fill-byte remnants are often the only surviving record of *which* files were
  lost. A tidying agent destroys that. Mark them keep.
- **Broken certificates/keys still document a lost access path.** Same logic.
- **An inbox/staging folder is Tier 0 until sorted** — nothing in it has been
  filed yet, so nothing in it has a second copy.
- **Secrets stores** (`.env`, `.kdbx`, `.pfx`, `id_rsa`, a passwords note): deny
  *reads*, not just writes, so they can't leak into a transcript or a log.

## Step 3 — Enforce in config, not only in prose

A rules document alone gets skimmed and overridden. Write the prose file **and**
encode it where the runtime will refuse the action — for Claude Code / Hermes a
`permissions.deny` list in `.claude/settings.local.json`. Ready block:
`templates/settings-deny-list.json`.

Two entries every deny list needs and everyone forgets:

- **`rm`, `mv`, `Remove-Item`, `Move-Item`, `git reset --hard`, `git clean`** —
  a move is as destructive as a delete when you can't find the file afterward.
- **Any mirroring flag**: `*robocopy*/MIR*`, `rsync --delete`. One of these
  pointed the wrong way empties the archive *and* the backup in one run.

Back up the settings file before editing, and validate the JSON afterwards
(`python -c "import json;json.load(open(...))"`) — a syntax error there means
*no* permissions are enforced at all.

## Step 4 — Quarantine instead of delete

Never let an agent delete in Tier 0. Establish one folder (`_to_delete/`,
`_zu_loeschen/`) where candidates are *moved*, with a README saying a human
decides. Record it in the rules file so future sessions use it.

## Step 5 — Check what your new folder breaks (second-order effects)

**This is the step that gets skipped.** A quarantine folder inside a directory
some automated job already walks will be silently re-ingested on its next run —
the files you set aside get filed back into the archive at 22:00 and nobody
notices.

After creating any new folder, grep the automation touching its parent
(`rglob`, `os.walk`, `Get-ChildItem -Recurse`, robocopy source roots) and add an
exclusion. Comment *why*, or someone removes it later.

```python
files = [
    p for p in sorted(INBOX.rglob("*"))
    if p.is_file() and "_zu_loeschen" not in p.relative_to(INBOX).parts
]
```

Same question for the backup scripts: does the new path belong in, or out?

## Step 6 — Verify with a dry run, then report honestly

Use the real dry-run switch (`--dry-run`, `robocopy /L`) and show the output.
Confirm the excluded folder is genuinely absent from the run.

Finish by naming what the rules **do not** solve. All copies in one machine? No
version history? Secrets riding along in cleartext to every backup drive? Say it
plainly and offer the concrete fix — a git repo over just the text files,
excluding the multi-GB media, is usually the cheap win. Rules that overstate
their own coverage are worse than none.

## Pitfalls

- **Don't open with "let me clean this up".** In an archive the default action
  is read, catalogue, report.
- **Don't trust an exit code as proof.** `robocopy` signals via exit code and
  returns <8 for partial success; wrappers ignoring `$LASTEXITCODE` print "OK"
  on a failed backup. Check the code *and* the destination.
- **A live process inside the source breaks the backup.** When the thing you
  back up runs a daemon whose data dir sits inside the source tree (the agent
  itself, MCP servers, a live DB), robocopy can't read the held-open files,
  exhausts its retries and exits ≥8 (code 11) — the run reports failure even
  though everything else copied. Identify what holds the dirs (`Get-Process`),
  then exclude only the daemon's *volatile runtime* dirs (pending messages,
  terminal output, telemetry) via `/XD`, same class as `logs`. Do not exclude
  the durable data (config, skills, memories) — that is the point of the backup.
- **Edit backup scripts so the diff stays honest.** PowerShell
  `[IO.File]::WriteAllLines`/`WriteAllText` rewrites line endings to the system
  default (CRLF); when the repo stores a script LF-only, a one-line change
  becomes a full-file churn (and a self-inflicted multi-hundred-line diff).
  Preserve LF when writing, or fix after with a CRLF→LF pass and confirm
  `git diff --stat` shows only the intended line.
- **A robocopy line ending in a backtick continues on the next line.** The
  backtick joins the *following* line; a line appended *after* the backtick line
  with no backtick runs as a separate command (`pending_messages` is not a
  Cmdlet). Put added `/XD` names on the same continuation line, not a new one.
- **A stale `.git/index.lock` blocks every commit.** A hung or crashed git leaves
  one behind after the process is gone. Check the lock's mtime and confirm no
  git is mid-operation (`Get-Process git`), then `rm` it and retry — not every
  "unable to create index.lock" means your change is at fault.
- **Don't dedupe by name or timestamp.** Only a content hash may authorize a
  delete. Name-and-date matching has wiped thousands of same-named,
  different-content files in a single run.
- **Don't put the rules only in `CLAUDE.md`.** Other agents read `AGENTS.md`.
  Update both, plus subdirectory copies, and cross-link them.
- **Don't check a signature by "starts with FF".** An intact JPEG starts
  `FF D8 FF`. Test whether the first ~4 KB are all one repeated byte instead.
- **Cloned repos with their own `.git` inside a whitelisted vault become gitlink submodules and break `git add -A`.** A clone under `MaxHirn/skills/`, `MaxHirn/CLIProxyAPI/` or `Agenten/Handel/OpenAlice/` is taken as an embedded git repository — the Zwischenstand (`git add -A` → `git commit-tree`) then fails with `warning: adding embedded git repository` and a silent Exit 1 / empty log. The whitelist's `!*/` traversability re-exposes ignored dirs, so `**` alone does not hide them. Keep Fremd-Repos outside the versioned tree when possible; if they must live inside it, add an explicit ignore for the root (`MaxHirn/skills/`, `MaxHirn/CLIProxyAPI/`, `Agenten/Handel/OpenAlice/`) in the `.gitignore` Rückausnahmen so `git status` stays silent.

## Reference

- `references/maxhirn-vault-case.md` — worked example: a 46 GB Obsidian vault +
  file archive, no git, non-mirroring backup; the exact tiering, deny list and
  automation patch applied.
- `templates/settings-deny-list.json` — drop-in `permissions.deny` block.
