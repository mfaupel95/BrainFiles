# Implementing the tier gatekeeper

Depth for Step 3 of the parent skill: turning "here are the tiers" into a
program an unattended job can call.

## Verdicts

One verdict per tier, plus the secret-store case. The exit code is the
interface — a caller must branch without parsing prose.

| Verdict | Code | Caller does |
|---|---|---|
| allowed | 0 | proceed |
| blocked | 1 | stop, report to the user |
| backup-required | 2 | make `.bak-<YYYYMMDD>` first, then proceed |
| quarantine | 3 | move into the quarantine folder; never delete |
| expectation violated | 4 | assertion mode only — see below; nothing was done |

## Decision table

| Tier | read | delete / overwrite | move / rename |
|---|---|---|---|
| 0 | allowed (except secrets) | blocked | quarantine |
| 0, secret store | blocked | blocked | blocked |
| 1 | allowed | backup-required | backup-required |
| 2 | allowed | allowed | allowed |

Secret stores are withheld on *read* as well, so their contents cannot reach a
transcript or a log line.

## Matcher ordering

Check in this order; first hit wins:

1. secret-store patterns — highest, because a `.kdbx` inside a free-tier folder
   is still a secret
2. tier-0 patterns
3. explicit tier-2 exceptions (log dirs, `.venv`, `__pycache__`, `node_modules`,
   `.git`)
4. general tier-1 patterns
5. default → tier 2

Step 3 exists because the general tier-1 patterns swallow subpaths the rules
exempt. Normalise before matching — absolute form, lower case, forward slashes —
so a Windows path is testable from any platform.

Two pattern-shape rules, both of which leave a hole that no test case written
from the *rules file* will catch:

- **End a directory rule with a boundary, not a bare slash.** `.../routinen/logs/`
  matches paths *inside* the log directory but not the directory itself, so a
  query on the directory falls through to the general rule below it and reports
  the higher tier. Write `.../routinen/logs(/|$)`. Apply the same shape to every
  exempt folder (`.venv`, `__pycache__`, `node_modules`, `.git`) and to the
  tier-1 directory rules.
- **Match a protected root wholesale; never enumerate today's subfolders.** A
  tier-0 pattern listing `archiv/dokumente|bilder|videos|musik|posteingang`
  leaves the archive root itself at the free tier — so does a folder added next
  month, until someone remembers the list. One boundary-anchored pattern on the
  root (`^<drive>:/archiv(/|$)`) covers all of it, including names nobody has
  thought of yet. Enumerate only what is genuinely narrower than its parent.

## Assertion mode — wiring a gatekeeper into a job that already runs

A gatekeeper that only returns verdicts cannot be attached to an existing job
as a per-file veto. The jobs that need it most are the ones whose legitimate
work *is* moving tier-0 material: the inbox sorter moves files out of the
unsorted inbox, and "tier 0 + move → quarantine" stops it dead. Demand a backup
for every file being consolidated and the consolidation job is nonsense within a
day. A veto wired in that way gets switched off, which is worse than no guard.

Add a mode where the caller names the verdict it *requires* and the gatekeeper
only checks:

```
gatekeeper.ps1 -Path <root> -Aktion <action> -Erwartet <verdict> [-Stille]
```

- **No side effect.** It does not move, copy or delete whatever the verdict —
  the caller asked for a check, not an action.
- `0` when the verdict matches, `4` when it does not; log the mismatch.
- `-Stille` suppresses the normal output so an owning routine's log stays
  readable.

This turns the rule set into a checked invariant instead of a per-file veto:
each job asserts, before it starts, that the protection it depends on is still
armed. If a rule is later loosened, the job fails loudly instead of quietly
walking through a folder it was never meant to touch.

The two assertions that carry most of the value, because neither is a tier fact:

- **the destination roots the job writes into** are still blocked against bulk
  delete
- **an exclusion list inside the job itself** still contains the entry holding a
  taboo branch back — where that branch sits in a free tier, the job's own list
  is the only thing in the way, and a tier check cannot see it at all

## One rule, two runtimes

The host-side check (PowerShell, for scheduled jobs) and the agent-side check
(python, for sessions without a shell) will drift apart. Either keep a single
implementation, or cross-check them: run the same case matrix through both and
require identical verdicts. Two implementations that have never been compared
are one working implementation and one trap.

When comparing them, expect the *count* to match even where a case was written
wrongly: a case whose expectation turns out to be mistaken shows up as both
implementations disagreeing with the expectation and agreeing with each other.
That is a test bug, not a matcher bug — fix the expectation, and keep the
agreement figure as the real signal.

## Minimum test matrix

Write the expected code down before running anything, then assert the actual
one. One case per tier, plus each exception:

| Case | Action | Expected |
|---|---|---|
| tier-0 media | delete | 1 |
| tier-0 media | move | 3 |
| tier-0 root itself | overwrite | 1 |
| tier-0 root, subfolder that does not exist yet | bulk delete | 1 |
| tier-0 inbox (unsorted) | delete | 1 |
| secret store | read | 1 |
| git-tracked notes directory | delete | 0 |
| operational script | delete | 2 |
| operational *directory* | delete | 2 |
| exempt directory itself, not just files in it | delete | 0 |
| log dir under an operational parent | delete | 0 |
| service config | overwrite | 2 |
| agent instruction file | overwrite | 2 |
| `node_modules` | bulk delete | 0 |

The two cases naming a directory rather than a file are the ones that catch the
boundary bug above; a matrix built only from file paths passes with the hole
wide open.

Then exercise the two branches that change something, on a throwaway file: the
backup branch by creating a disposable file in a tier-1 directory, running with
execute on, and confirming the `.bak` exists. The quarantine branch needs a real
tier-0 path — create one disposable file there, run with execute on, confirm it
landed in the quarantine folder, then remove it. Leave the branch untested only
when even that is unacceptable, and say so plainly rather than implying it was
verified.

## Writing the artefact

Text in these vaults is UTF-8 without BOM and LF-only. Write the file, then
normalise and verify it before trusting it:

```powershell
$t = [IO.File]::ReadAllText($f)
$t = $t -replace "`r`n","`n" -replace "`r","`n"
[IO.File]::WriteAllText($f, $t, (New-Object System.Text.UTF8Encoding($false)))
$b = [IO.File]::ReadAllBytes($f)   # $b[0] -eq 0xEF means a BOM crept in
```

Before splicing non-ASCII text into an existing file, probe the transport once:
write a throwaway string containing an umlaut and an em dash, read it back, and
confirm the bytes are `C3 BC` and `E2 80 94` rather than double-encoded. A
mangled umlaut is silent and survives every later hash comparison.

Check syntax without running the file where the shell can do it
(`[Management.Automation.Language.Parser]::ParseFile` for PowerShell,
`ast.parse` for python) — a gatekeeper with a syntax error fails open at the
caller's `if`.

For editing an existing script by string replacement, and for the PowerShell
traps that present as something else (empty `Split-Path -LiteralPath -Leaf`,
`exit` escaping a `try` block, the tool-layer shell not being the interpreter
the scheduled job runs under), the owning skill is `windows-host-zugriff`.
