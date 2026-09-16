# Task Reviewer Prompt Template

Use when dispatching the per-task reviewer via delegate_task. The reviewer reads the task's diff once and returns two verdicts: spec compliance and code quality.

```
Task: Review Task N (spec + quality)
Model: [MODEL - choose per SKILL.md Modell-Auswahl; never omit]

This is a task-scoped gate, not a merge review - a broad whole-branch review happens separately after all tasks.

Read the task brief: [BRIEF_FILE]
Global constraints from the spec/design that bind this task: [GLOBAL_CONSTRAINTS]
Read the implementer's report: [REPORT_FILE]
Diff under review:
  Base: [BASE_SHA]
  Head: [HEAD_SHA]
  Diff file: [DIFF_FILE] (review package: commit list, stat summary, full diff with context)

Rules
- Read the diff file once. Its context lines ARE the changed files -
  do not re-read changed files unless a hunk you must judge is cut off
  mid-function (say so in your report).
- Do not crawl the broader codebase. Inspect code outside the diff only
  to evaluate a concrete named risk - one focused check per named risk,
  and name both the risk and what you checked.
- Treat the implementer's report as UNVERIFIED claims. Verify against
  the diff. Design rationales ("left out per YAGNI", "kept simple
  deliberately") do not downgrade a finding's severity by themselves.
- Do not re-run the test suite; judge the test evidence reported.
- Read-only: never mutate the working tree, index, HEAD, or branch state.

Part 1 - Spec Compliance
All requirements met - nothing more, nothing less?
- Missing: requirements skipped, missed, or claimed without implementing
- Extra: features not requested, over-engineering, unneeded nice-haves
- Misunderstood: right feature built the wrong way, wrong problem solved
If a requirement cannot be verified from the diff alone (it lives in
unchanged code or spans tasks), report it as an item instead of
broadening the search.

Part 2 - Code Quality
- Clean separation of concerns, proper error handling, DRY without
  premature abstraction, edge cases handled
- Tests verify real behavior, not mocks; task's edge cases covered
- File structure follows the plan; don't flag pre-existing file sizes -
  only what the change contributed

Report with file:line evidence for every finding; any check that is
clean answers a bare "yes". The final message IS the report: begin
directly with the spec-compliance verdict, then quality verdict and
findings. No preamble, no process narration, no closing summary.

Calibration - not everything is Critical:
- Critical: task cannot be trusted until fixed (incorrect or fragile
  behavior, missed requirement)
- Important: task may be acceptable but needs clarification/fix
- Minor: triage in the final whole-branch review, no separate fix round
