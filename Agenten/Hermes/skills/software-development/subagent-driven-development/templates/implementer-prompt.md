# Implementer Subagent Prompt Template

Use when dispatching the implementer via delegate_task.

```
Task: Implement Task [name]
Model: [MODEL - choose per SKILL.md Modell-Auswahl; never omit]
Work from: [directory]
Read the task brief first: [BRIEF_FILE]
Write your full report to: [REPORT_FILE]

Context
[Scene-setting: where this fits, dependencies, architectural context]

Before Begin
Raise any questions now about: requirements and acceptance criteria,
approach and implementation strategy, dependencies and assumptions,
anything unclear in the task description. Ask before starting.

Job
Once clear:
1. Implement exactly what the task specifies
2. Write tests (TDD if the task says so)
3. Verify the implementation works - focused tests while iterating,
   the full suite once before committing, not after every edit
4. Commit work
5. Self-review (checklist below), fix what you find
6. Report back with one status

While working: if you hit something unexpected or unclear, ASK.
Don't guess and don't make assumptions.

Code Organization
Follow the file structure the plan defines. Each file has one clear
responsibility and a well-defined interface. If a file you create is
growing beyond the plan's intent, say so in your report instead of
silently inflating it.

Escalation
If you are genuinely stuck (no progress after real attempts), report
BLOCKED or NEEDS_CONTEXT. Describe specifically what you are stuck on,
what you tried, and what kind of help you need. The controller will
provide context, dispatch a more capable model, or break the task down.

Self-Review Before Reporting Back
Ask yourself, with fresh eyes:
- Completeness: is everything in the spec implemented? Missed
  requirements? Unhandled edge cases?
- Quality: names clear and accurate (match what things do, not how)?
  Code clean and maintainable?
- Discipline: no overbuilding (YAGNI)? Only what was requested?
  Following existing codebase patterns?
- Testing: do tests verify real behavior (not just mocks)? Output
  pristine - no stray warnings or noise?

If you find issues in self-review, fix them NOW before reporting.

Fix Rounds
When resumed with review findings: fix them, re-run tests covering the
amended code, and APPEND a fix report to [REPORT_FILE] - what changed,
which tests you ran, the command, the output. Reviewers will not re-run
tests for you; the report is your test evidence. Then reply with the
same short status contract as the first report.

Report Format
Write the full report to [REPORT_FILE]:
- What you implemented (or attempted, if blocked)
- What you tested and the results
- TDD evidence (if TDD was required)
- Any concerns or deviations from the brief

Status contract (reply with exactly one):
DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
