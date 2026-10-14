---
name: grill-me
description: Use when Plan/Design stress-getestet wird ('grill me').
---

Interview the user relentlessly about every aspect of their plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

Quelle: RobMitt/grill-me-skill (GitHub, adaptiert auf Hermes-Werkzeuge).

## How to ask questions

Use the **clarify tool** for every question you ask. Never pose questions as plain text in your response — always use the multiple-choice form so the user can quickly select an answer or type a custom one.

Ask **one question at a time**. Wait for the user's answer before moving to the next question. This keeps the conversation focused and prevents overwhelm.

For each question, provide 2–4 concrete multiple-choice options representing the most likely answers or directions. Think about what the user would realistically choose — generic options like "Yes" / "No" aren't helpful unless the question is genuinely binary. Put the recommended option FIRST (the UI marks it as recommended). The user always has the "Other" field available to write something custom.

## Flow

1. After receiving an answer, briefly acknowledge the decision (1–2 sentences max), then immediately ask the next question via the clarify tool.
2. If a question can be answered by exploring the codebase or files, explore them yourself instead of asking the user.
3. Continue until all branches of the design tree are resolved.
4. When finished, provide a concise summary of all decisions made.
