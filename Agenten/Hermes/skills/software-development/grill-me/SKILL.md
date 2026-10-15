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

0. **Before the first question, MEASURE the current state** (files, tools, live numbers). Every option should carry a real value from this session, not an assumed one — a grill on assumed state produces a plan against a situation that does not exist.
1. After receiving an answer, briefly acknowledge the decision (1–2 sentences max), then immediately ask the next question via the clarify tool.
2. If a question can be answered by exploring the codebase or files, explore them yourself instead of asking the user.
3. Continue until all branches of the design tree are resolved.
4. The form TIMES OUT when nobody answers (about 60 min). A timed-out question is not a "no": implement what WAS decided and list the unanswered branch as an open decision — never block the whole execution on it.
5. When finished, provide a concise summary of all decisions made.

**In this house the grill does not end at the summary.** A grill that ends in decisions is followed by execution in the same session: measure, patch with a dated remark, verify with a real run, prove with a Gegenprobe, commit only own paths. The summary is the report, not the deliverable — an approval here is a work order, not a plan to restate.
