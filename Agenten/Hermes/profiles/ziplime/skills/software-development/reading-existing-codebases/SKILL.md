---
name: reading-existing-codebases
description: "Review unfamiliar code: verify claims in the tree."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, code-reading, codebases, review, evidence, multi-agent, trading-systems]
    related_skills: [codebase-inspection, grounded-citations, requesting-code-review, systematic-debugging]
---

# Reading an Unfamiliar Codebase

How to answer "is this already implemented?", "where does that rule live?", "review this design",
or "check the plan against the code" on code you have never seen — fast enough to be useful,
never wrong.

## When to Use

- The user asks what a system already does, or whether something is already implemented.
- A plan, spec, ticket, or design must be checked against the code that exists.
- A codebase is handed over for a change, a critique, or a review.
- Several agents (group chat, subagents) are asked to assess the same code and must agree on
  what the code actually says.
- Agents hand over findings as quoted `path:line` citations from a repo you can open yourself.
- You are asked to settle which of several proposed "first fixes" is the real bottleneck in an
  unfamiliar repo.

## Rule Zero — Trace symbols, never names

A function name is a claim, not a fact. A class, module, or flag name asserts intent; the
body decides behaviour. The names in a codebase are written by whoever *wrote* it and read by
whoever wants to be believed.

Before asserting anything, do all three, in this order:

1. **Read the body.** The whole function or class, not the docstring. Docstrings and comments
   are the least reliable lines in a file — they describe what the author meant, and they age.
2. **Find every caller.** `search_files` the symbol across the tree. A function with no caller
   is dead, and a flag no caller reads is inert configuration.
3. **Count real usage.** Count the lines, rows, and records the claim is about. A claim that
   "this category never fires" or "this limit never binds" is a measurement, not an opinion —
   and the number is the whole answer.

A proposal built on a name alone reads as confident and lands as wrong.

## Procedure

1. **Orient cheaply before reading.** List the tree; read the repo/area `AGENTS.md`, `README`, and
   the file header docstring. Then stop reading docs and start reading code — headers tell you
   the author's intent, which is exactly what you must not trust.
2. **Build the claim from the code.** For each thing the spec says, locate the function that
   implements it and quote the line numbers you will cite.
3. **Check the data, not the prose.** When a claim is about categories, thresholds, or limits,
   run the numbers against the real config/data files. See
   `references/audit-existing-implementation.md`.
4. **Check the tests.** Tests encode intended precedence (what wins when two rules collide) and
   are cheaper to read than the implementation. Search for the test *name*, not the bug — names
   like `test_stop_takes_priority_over_forced_close` state the rule.
5. **Write findings with `path:line` and the measured number.** Never "the code seems to". Either
   cite the line or say you could not find it.
6. **Reconcile a cost against the cash, and check the output can carry it.** A cost claim is
   settled by summing the fills' cash effects and comparing against the ledger's own cash delta —
   when they match exactly, the cost never entered the cash. Then list the result object's columns
   and the summary function's keys: a cost that is computed but has no column and no summary key is
   a different finding from one that is computed wrong, and the two have different owners. See
   `references/reproduction-recipes.md` and `references/verifying-agent-findings.md`.

## Run the Code Before Settling a Multi-Agent Dispute

When several participants propose different fixes, they are usually describing different gaps.
A one-line reading of each file tells you whether a mechanism *exists*; it cannot tell you which
proposal is the bottleneck. Run one minimal reproduction per competing hypothesis, in the repo you
were given, before the next round.

- **Read the output object, not the log.** A hand-written runner frequently swallows its own
  stdout (`print_algo=False`), so the log looks empty while the result carries the answer. Inspect
  the engine's result object directly — list its columns, count non-empty rows, and print the
  record when one exists.
- **Run the counter-case with real inputs.** If the hypothesis is "the fill path is unreachable on
  this dataset", the counter-case is the same strategy against a dataset that *does* carry the
  required column. Fill price present there and absent here is a measured finding, not an opinion.
- **Report a third possibility instead of picking a side.** When the evidence contradicts the
  premise both proposals share, name the other cause and show it with numbers.
- **An unresolved instrument gap is a finding, stated as one.** If you cannot resolve why a log
  is missing the diagnostic you traced in code, say "the one number I could not resolve is …" and
  give the line the behaviour lives at. An open question with a citation is a contribution; a
  guessed mechanism is not.

See `references/reproduction-recipes.md` for the counter-case scripts and how to drive the engine
end-to-end.

## Reconciling the Plan with the Code

A plan or design document is written before the code; when the two disagree, the disagreement
is itself the finding.

- **Align the plan to the code when the plan describes something that cannot occur.** If the
  spec names a category, state, or failure mode that no code path produces, the plan is describing
  a ghost — say so plainly, with the reason it cannot occur.
- **But first find where the thing lives instead.** The same situation often exists one layer over:
  an early return that writes a diagnostic record instead of a row, a position kept open instead
  of closed, a counter that lives in state instead of a log. The case is real; only its *home* differs
  from the spec. Locating it beats declaring it absent.
- **If the code already implements several categories of the same thing, align the plan to all of
  them.** A spec that names one category while the code distinguishes three is a worse spec after
  the "fix" than before.
- **Never "fix" a definition to match the code without naming the collision.** The collision is the
  useful part; a silently corrected definition teaches nothing.

## Ordering Rules: New Checks Must Respect Existing Ones

Before proposing where to add a check, enforcement, or validation, establish the existing order
of operations and its documented rationale — the order is almost always deliberate (e.g. "stop
and target outrank forced exit because they are the more expensive truth").

Place a new check so it cannot preempt an existing, more honest one. If the code already routes
the same condition through an existing exit path, route the new check through that path instead
of inserting a parallel one: the existing path already carries the ordering and the reporting
for free. Then confirm the order against the tests that pin it, not against your reading of the
comment above the code.

## Delegation and Conflicting Claims

**Run in the tree you were given — the current directory is a trap.** In a workspace with several
checkouts of the same project, `search_files` over `.` finds nothing while the sibling tree holds
thousands of matches. `find <root> -name <file> -not -path "*/.venv/*"` from the workspace root
first, then work in the directory you actually found. Never report "not present" from a tree that
may be the wrong one.

**Bound every recursive search with a depth or an exclusion.** A bare `find`/`grep -r` over a
workspace containing virtualenvs and dependency trees hits the tool timeout. `-maxdepth 3`,
`-not -path "*/.venv/*"`, or a specific subdirectory each keep it inside the limit.

**Cross-check a teammate's summary of code you cannot read.** Their quoted line numbers are
unverified until you open the file. Their *conclusion* may be right while their citation is off —
or the reverse. When several agents comment on the same code, verify the disputed line yourself
before repeating the number in the room.

**Count events, not log lines — a log line is not a stage.** An audit that "found the fill
price in the log" has proven nothing until it has counted the *event kinds* the run emits. Grep
for the marker the strategy prints, for the fill event, for the transaction event; a runner that
logs `ORDER_SUBMIT` a thousand times and never a fill is a run with no measurable output, and the
claim it appears to support is unverified. See `references/verifying-agent-findings.md`.

**Check the column under the aggregate before quoting the aggregate.** A count, threshold, or
cost figure read off one file can come from a different unit than the one the aggregate implies
— a size field that is not direction-aware, a volume column that is all zero, a total built from
a per-side value. Read the field definition and the arithmetic it feeds, then quote the number.

**Deliver an evidence-backed conclusion even when it is the uncomfortable one.** "This is already
implemented", "this is not the case you think it is", or "the threshold you chose is derived from
the number you are trying to replace" is the valuable contribution. Adding a soft agreement to
make the room comfortable is how a bad design gets written into code.

**One finding per numbered point, each ending in an answer and a line.** In a multi-participant
thread, structure the message so each numbered item states: the claim it answers, the measured
result, and the `path:line` that carries it. A run log, a column list, or a traceback quoted
without the count it was drawn from is not evidence; the count is.

**Report a teammate's number only if you opened the line it came from.** Quote your own citations
with the tree you opened them in; for theirs, either reproduce it in your tree or hand it back as
"not verified in my tree — I cannot reproduce your line". Reproducing a number you did not
measure, even with a citation attached, propagates someone else's error into your name.

**Keep the proposed fix inside the boundaries the existing architecture sets.** Do not build the
second verifier, the second gate, or the second writer when the tree already has exactly one. When
the mechanism exists and the wiring does not, the work is the wiring; when the data does not carry
the field, the work is the data. Say which of those it is and stop there.

## Pitfalls

- **Quoting a teammate's line numbers without opening the file** — their claim is a lead, not
  evidence. Open the file in the tree *you* were given; a teammate's citations are frequently
  from a different checkout, branch, or project of the same name, and reporting their finding as
  if it were yours misattributes it.
- **Reporting "not present" from a partial tree** — search from a known root, exclude dependency
  directories, and depth-bound recursive searches.
- **Trusting a docstring over the body** — the body decides; the docstring ages.
- **Adding a check without asking what the code already does at that point** — a second copy of a
  rule is a third failure mode when the first two drift apart.
- **Proposing a place to insert code without reading the ordering rationale above it** — the order
  is the design; the new check usually belongs at the existing seam, not before it.
- **Saying "this never fires" without counting** — measure it; the count is the finding.
- **Letting a plan describe a category the code cannot produce** — align the plan, and say where
  the real case lives instead.
- **Generalizing from one repo layout** — this class of system is a fleet (one directory per
  strategy, shared ledger, per-strategy config) and most conclusions are aggregate measurements
  across the fleet, not facts about one file. State the denominator.
- **Treating a debug runner or scratch script as a deliverable** — untracked, hand-written runner
  scripts under a repo root are probes someone left behind, not the project's mechanism. Check
  `git log`/`git status` before calling one "the" way the system does something; the committed
  code path is the claim, the scratch file is the author's own attempt.
- **Reading a field the way the aggregate reads it** — a count, cost, or limit is only as good as
  the field it is computed from; check that field's definition and units before quoting the
  total.
- **Reporting a cost as applied because a projection was logged** — a pre-check that adjusts the
  order size and logs a projected commission is not a charge. Reconcile the fills' cash effects
  against the ledger's cash delta; when the configured cost is non-zero and the two match exactly,
  the cost never entered the cash.
- **Merging a wiring gap with an output gap** — "the cost is wrong" and "the cost is invisible in
  the report" are different findings with different owners. Report which one you measured.
- **Leaving probe scripts and their generated files inside the project tree** — a runner that
  writes its strategy under the project's own example/strategy directory becomes part of the suite
  and cannot be told apart from a real file. Probe in the agent's scratch directory and hand the
  engine the absolute path.
- **Reading a crash as an artefact of one input** — a zero-size crash and a partial-sell crash can
  be the same defect. Reproduce with a quantity that is not the artefact (sell a fraction of the
  position) and report the general rule, not the special case.

## Reference

- `references/audit-existing-implementation.md` — the recipe for measuring whether a category,
  threshold, or limit actually fires, including the model that was wrong and how it was caught.
- `references/verifying-agent-findings.md` — the checklist for trusting a teammate's cited
  finding, including the per-project citation trap and the cost-wiring read.
- `references/reproduction-recipes.md` — minimal, re-runnable counter-case scripts: inspect a
  run's result object directly, and drive the engine end-to-end for the hypotheses a read cannot
  settle.
