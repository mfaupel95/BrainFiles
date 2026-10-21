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

### Make the tiers queryable, so unattended jobs can ask before they act

A deny list stops the agent's shell. It does not stop the user's own scheduled
sorting, dedup, or cleanup scripts — which is where bulk damage actually lands,
unattended, with nobody reading the output. Give those something to ask:

```
gatekeeper.ps1 -Path <target> -Aktion <delete|move|overwrite|read> [-Execute]
```

One verdict per tier, one exit code each, so a caller branches without parsing
prose: `0` allowed, `1` blocked, `2` backup-required, `3` quarantine. Table and
test matrix: `references/gatekeeper-implementation.md`.

- **Report-only is the default.** The destructive act stays with the caller;
  the gatekeeper judges and, on request, makes the `.bak` copy or performs the
  quarantine move. A helper that deletes is one more thing that can be wrong.
- **Exempt directories are explicit exceptions, checked before the general
  rule.** "Everything under `Routines/` requires a backup" also captures
  `Routines/logs/`; the gatekeeper would then demand a backup for every log
  write and be switched off within a week.

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
- **Detect line endings by reading BYTES, not text.** A text-mode read
  (`open(p, encoding="utf-8")`) silently folds CRLF to LF, so the natural guard
  `"\r\n" in text` is FALSE on a CRLF file — you then write the whole file back
  as LF and turn a five-line insertion into a 113-line diff. Read
  `open(p, "rb").read()`, decide the ending from the bytes, and write with `wb`.
  In a MIXED file (real example: 86 CRLF + 52 LF in one README) there is no
  single right answer — insert line by line (`splitlines(keepends=True)`) and give
  each new line the ending of its NEIGHBOUR. Same routine when the `patch` tool
  reports "Could not find a match" on text you can see: don't guess anchor
  variants, switch to the byte-level write. Check with `git diff --stat` (the
  intended `+n/-0`, not whole-file) and `git diff --ignore-cr-at-eol --stat`
  (must find nothing extra).
- **Your own test run can make the backup look broken.** A suite that writes into
  real state files (a trail's journal, a status JSON inside the watched tree)
  leaves the live copy differing from the mirrored one until the next scheduled
  run or daemon cycle. Wait for that cycle before declaring "the base file is
  untouched" — otherwise you report your own side effect as a defect and start
  hunting a bug that does not exist.
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
- **Take the tier boundaries from the user's own rules file; never infer them.**
  An inverted boundary is worse than no gatekeeper: a git-tracked notes
  directory classed as irreplaceable blocks ordinary work, and the user learns
  to bypass the check instead of trusting it. Name the authoritative file
  inside the gatekeeper, and state that it wins on any disagreement.
- **Run the gatekeeper once per tier and once per exception, with the expected
  exit code written down first.** A verdict that is merely plausible still ships
  a guard nobody can rely on; when a case disagrees, fix the rule rather than
  the expectation.
- **Exercise the backup and quarantine branches on a throwaway file.** A
  gatekeeper whose backup branch was never executed is assumed-correct exactly
  where it must not be. Create one disposable file in a tier-1 location, run
  with execute on, confirm the `.bak` exists, then remove both.
- **Cloned repos with their own `.git` inside a whitelisted vault become gitlink submodules and break `git add -A`.** A clone under `MaxHirn/skills/`, `MaxHirn/CLIProxyAPI/` or `Agenten/Handel/OpenAlice/` is taken as an embedded git repository — the Zwischenstand (`git add -A` → `git commit-tree`) then fails with `warning: adding embedded git repository` and a silent Exit 1 / empty log. The whitelist's `!*/` traversability re-exposes ignored dirs, so `**` alone does not hide them. Keep Fremd-Repos outside the versioned tree when possible; if they must live inside it, add an explicit ignore for the root (`MaxHirn/skills/`, `MaxHirn/CLIProxyAPI/`, `Agenten/Handel/OpenAlice/`) in the `.gitignore` Rückausnahmen so `git status` stays silent.

- **A directory rule must match the directory, not only what is inside it.**
  `.../logs/` matches paths under the log dir but not the dir itself, so a query
  on it falls through to the general rule below and reports the higher tier.
  End directory rules with `(/|$)`. Likewise, match a protected root wholesale:
  a tier-0 pattern that enumerates today's subfolders leaves the root itself —
  and every folder created next month — at the free tier.
- **Wire the gatekeeper into a job that already runs as an assertion, not as a
  per-file veto.** The jobs that need it most are the ones whose legitimate work
  is moving tier-0 material; a veto on "move" stops the inbox sorter dead and
  gets switched off within a day. Give the gatekeeper a mode where the caller
  names the verdict it requires and it only checks (own exit code, no side
  effect), so each job asserts up front that its protection is still armed.
  Details and the two assertions worth having: `references/gatekeeper-implementation.md`.
- **Anchor scan exclusions by path, never by bare directory name — and keep the
  residual short enough to read.** An exclusion written as `skills` also drops
  `.claude/skills`, i.e. exactly the hand-written material the scan exists to
  inspect; match the cloned-repo root instead, so same-named hand-written dirs
  stay in scope. Then route the reproducible noise out and read every remaining
  line: the real hits sit in the short tail, and a check whose output has to be
  paged through is a check nobody runs. Measure before and after — the count of
  findings that no human has assessed is the number that matters.

## Reference

- `references/gatekeeper-implementation.md` — tier→verdict decision table,
  matcher ordering, the dual-runtime cross-check and its test matrix.
- `references/git-over-text-layer.md` — versioning only the text layer of a
  media-heavy vault.
- `references/verifying-protection-worked.md` — proving a protection change
  actually took effect.
- `templates/settings-deny-list.json` — drop-in `permissions.deny` block.
