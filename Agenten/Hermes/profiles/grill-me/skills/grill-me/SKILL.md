---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

Interview the user relentlessly about every aspect of their plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

## How to ask questions

Use the **clarify tool** for every question you ask (Hermes-Äquivalent zu Claude Codes AskUserQuestion). Never pose questions as plain text in your response — always use the multiple-choice popup so the user can quickly select an answer or type a custom one.

Ask **one question at a time**. Wait for the user's answer before moving to the next question. This keeps the conversation focused and prevents overwhelm.

For each question, provide 2–4 concrete multiple-choice options representing the most likely answers or directions. Think about what the user would realistically choose — generic options like "Yes" / "No" aren't helpful unless the question is genuinely binary. The user always has the "Other" field available to write something custom.

## Flow

1. After receiving an answer, briefly acknowledge the decision (1–2 sentences max), then immediately ask the next question via the clarify tool — but only the *gating* questions that actually change which tool/path you take (see "Don't over-grill" below).
2. If a question can be answered by exploring the codebase or files, explore them yourself instead of asking the user — and when the answer requires measuring reality (config values, git state, descriptions), measure it with a real command and cite the number, never a guess. A claimed baseline (e.g. "10 of 37 profiles on model X") must come from an actual grep/wc, and an estimate you're unsure of should be verified before writing it down.
3. Continue until the decision tree of *dependencies* is resolved.
4. When finished, provide a concise summary of all decisions made.

## Don't over-grill

Grilling is for resolving a genuine decision tree. The moment the user has given an execution directive ("macht das", "teilt die aufgaben", "stell die Frage hier"), stop popping clarify on every remaining branch — repeated popups get skipped/timed-out and the user will say "frag einfach nicht so viel". Ask only the gating decision(s), then **act and delegate**. 

## Task-shaped grilling: grill → decide → delegate → record

When the "plan" is a coordination task on a multi-agent system (distribute work, reclassify profiles, evaluate a stack):
1. Resolve the gating decisions one at a time via clarify (e.g. the taxonomy / criterion that gates every later action).
2. When the user picks, immediately hand each resolved branch to the best-suited teammate (@-mention the agent whose specialty it is: measurement, research, implementation, consolidation), rather than doing everything yourself. State who owns what.
3. Record every decision + the division of labor in a committed PLAN doc (e.g. `PLAN.md`, changed via patch, committed via git) so the state is demonstrable, not just promised. Re-open the doc across turns to append the next decision.
4. Verify real numbers before asserting them in the doc — a wrong baseline that later steps build on is worse than a short delay.
