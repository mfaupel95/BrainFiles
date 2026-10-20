---
name: grill-me
description: Use when Plan/Design stress-getestet wird ('grill me').
---

Interview the user relentlessly about every aspect of their plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

Quelle: RobMitt/grill-me-skill (GitHub, adaptiert auf Hermes-Werkzeuge).

## How to ask questions

Use the **clarify tool** for every question you ask. Never pose questions as plain text in your response — always use the multiple-choice form so the user can quickly select an answer or type a custom one.

The call shape is `clarify(questions=[{question, choices, multi_select?}])` — an ARRAY of question objects, even for one question. A bare single object is refused with "questions[0] must be an object"; wrap every call in a list. Several INDEPENDENT questions may share one call (one form beats a chain), but a question whose answer would change the next question goes in its own call.

Ask **one question at a time**. Wait for the user's answer before moving to the next question. This keeps the conversation focused and prevents overwhelm.

For each question, provide 2–4 concrete multiple-choice options representing the most likely answers or directions. Think about what the user would realistically choose — generic options like "Yes" / "No" aren't helpful unless the question is genuinely binary. Put the recommended option FIRST (the UI marks it as recommended). The user always has the "Other" field available to write something custom. **An "Other" answer that MODIFIES an offered option ("not switching anything, just the sizes down") is the governing constraint, not a rejection of every option** — keep it verbatim as the frame and recompute the remaining branches against it.

## Flow

0. **Before the first question, MEASURE the current state** (files, tools, live numbers). Every option should carry a real value from this session, not an assumed one — a grill on assumed state produces a plan against a situation that does not exist. Part of measuring is checking whether a decision is ALREADY resolved: dated `_vermerk` fields in wachen.json, config state, git status, `gh repo view`/`gh pr list`. A question whose answer is already written in the codebase is not a question — report it as resolved and move on instead of asking it. A plan that lists 20 decisions often has 5-8 already settled on disk.
1. After receiving an answer, briefly acknowledge the decision (1–2 sentences max), then immediately ask the next question via the clarify tool.
2. If a question can be answered by exploring the codebase or files, explore them yourself instead of asking the user.
3. Continue until all branches of the design tree are resolved.
4. The form TIMES OUT when nobody answers (about 60 min). A timed-out question is not a "no": implement what WAS decided and list the unanswered branch as an open decision — never block the whole execution on it.
5. When finished, provide a concise summary of all decisions made.

## Pitfalls

- **A grill answer that contradicts a documented prior decision must be surfaced, not applied.** If the user picks an option that flips a dated `_vermerk` in wachen.json or an annotation in the source plan (e.g. "festes Ziel true" when the file says false with a backtest reason, or "v4 uebernehmen" when the extrakt says the opposite), stop and ask a follow-up clarify presenting the existing decision and its evidence. The user may have forgotten the earlier call; silently applying the answer would overwrite a deliberate, evidence-backed decision. The follow-up is cheap and the contradiction is exactly what a grill exists to catch.
- **Verify named PRs/repos exist before treating them as work.** A plan can name PRs and branches that are phantoms (a PR number that was never opened, a repo whose remote is dead, a branch already merged with 0 commits ahead). Run `gh pr list`/`gh repo view`/`git rev-list --count` on each named target; report the ones that do not exist as findings rather than executing against them. Do not merge a Draft PR before its stated verification (e.g. demo run) has passed, even when the plan says "close the PRs".

**In this house the grill does not end at the summary.** A grill that ends in decisions is followed by execution in the same session: measure, patch with a dated remark, verify with a real run, prove with a Gegenprobe, commit only own paths. The summary is the report, not the deliverable — an approval here is a work order, not a plan to restate.
