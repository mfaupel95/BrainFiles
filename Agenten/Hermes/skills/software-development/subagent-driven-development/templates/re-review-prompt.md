# Scoped Re-Review Prompt Template

Use after a fix round. The re-reviewer verifies each finding was addressed and that the fix itself broke nothing. This is NOT a fresh review - the full review already happened.

```
Task: Re-review Task N fix round R
Model: [MODEL - choose per SKILL.md Modell-Auswahl; small fix diffs take cheap-to-mid tier]

Read the task brief: [BRIEF_FILE]
Findings under verification: [FINDINGS - the Critical/Important findings and spec gaps from the previous review, verbatim, one per bullet]
Read the implementer's report (fix reports are appended at the end): [REPORT_FILE]
Fix base: [FIX_BASE_SHA] (the head the previous review saw)
Head: [HEAD_SHA]
Diff file: [DIFF_FILE]

Scope
Your scope is the findings list plus the fix diff. Verdict every
finding; inspect the fix diff for new problems the fix itself
introduced. Do NOT re-review code the fix did not touch. If you notice
an issue entirely outside the fix diff, report it as an out-of-scope
observation (non-blocking; the controller will ledger it for the final
review). You may run a focused subset of tests covering the amended
code to verify the fix; do not re-run the full suite.

Read-only: never mutate the working tree, index, HEAD, or branch state.

Output Format
The final message IS the report: begin directly with the first
finding's verdict.

Finding verdicts (for each finding, in order):
[one-liner] ADDRESSED or NOT ADDRESSED, with file:line evidence.
"Attempted" is not addressed - the specific defect must no longer exist.

New breakage in fix diff:
Anything the fix itself broke or introduced, with severity
(Critical/Important/Minor) and file:line. "None" if clean.

Out-of-scope observations:
Issues noticed entirely outside the fix diff. "None" if none.

Verdict:
Fix round [all findings addressed, no new Critical/Important breakage]
or [findings remain open: list them].
