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

**Aber: jede Frist kostet bis zu einer Stunde.** Die Form laeuft ins Timeout, wenn niemand am Platz ist. Ist absehbar, dass keine Antwort kommt (CLI-Sitzung ohne anwesenden Nutzer, spaete Stunde, der Auftrag war nur "grill me" ohne Plan), dann die UNABHAENGIGEN Zweige in EIN Formular legen (bis 5 Fragen) und nur die voneinander abhaengigen einzeln stellen. Eine Kette aus vier Fragen kostet sonst vier Stunden stilles Warten, ohne eine einzige Entscheidung.

For each question, provide 2–4 concrete multiple-choice options representing the most likely answers or directions. Think about what the user would realistically choose — generic options like "Yes" / "No" aren't helpful unless the question is genuinely binary. **Every option must be a real answer.** A placeholder or empty first entry (`", "`, `": "`) renders as a pickable row at the top of the list: the user ticks it, the form returns `","` and nothing at all was decided. If the answer comes back as a non-answer, say in one line that the form had a broken entry and re-ask the SAME question with clean options — do not interpret it and do not move on. Put the recommended option FIRST (the UI marks it as recommended). The user always has the "Other" field available to write something custom. **An "Other" answer that MODIFIES an offered option ("not switching anything, just the sizes down") is the governing constraint, not a rejection of every option** — keep it verbatim as the frame and recompute the remaining branches against it.

## Flow

0. **Before the first question, MEASURE the current state** (files, tools, live numbers). Every option should carry a real value from this session, not an assumed one — a grill on assumed state produces a plan against a situation that does not exist. Measure the RUNNING artifact, not only the files: the live process command line (`Get-CimInstance Win32_Process` filtered on the executable), the build/binary mtime against the commit times, and what the exchange/account actually holds. Und: eine Zahl aus Log oder Status ist erst dann ein Befund, wenn man die Zeile gelesen hat, die sie SCHREIBT — ein Feldname wie `Laufposition` kann die Position NACH dem Auftrag meinen (Projektion), nicht den Bestand. A start script edited after the process started shows flags the running process does NOT have, and a binary built before the commit that fixes its own error keeps repeating that error although the code is green — both read like live faults and are stale artifacts. Part of measuring is checking whether a decision is ALREADY resolved: dated `_vermerk` fields in wachen.json, config state, git status, `gh repo view`/`gh pr list`. A question whose answer is already written in the codebase is not a question — report it as resolved and move on instead of asking it. A plan that lists 20 decisions often has 5-8 already settled on disk.

**Ohne Plantext ist der Plan der zuletzt lebende Gegenstand.** Ein "grill me" ohne Beschreibung meint den laufenden Aufbau: Prozess-Kommandozeile, Statusdatei, letzter Commit, offene Aufgabe. Dann ist die ERSTE Frage der gemessene Widerspruch zwischen dem, was der Gegenstand von sich BEHAUPTET (`state: running`), und dem, was er TUT (seit Stunden kein Ereignis, keine Order, kein Zyklus) — der Widerspruch ist meist der Grund, warum der Plan nicht laeuft. Zwei Regeln fuer die Zahlen darin: (a) eine Kapazitaets- oder Guthabenzahl gehoert dem FELD, das die Quelle dafuer fuehrt — `max-size` der Boerse fragen, nicht aus einem Kontostand selbst rechnen, sonst baut die Option auf einem Artefakt; (b) eine Zahl, die aus einem Log/Status stammt, erst als Befund verwenden, wenn man die Zeile gelesen hat, die sie schreibt (Zeile, Feld, Rhythmus), und den Leser im Optionstext nennen.
1. After receiving an answer, briefly acknowledge the decision (1–2 sentences max), then immediately ask the next question via the clarify tool.
2. If a question can be answered by exploring the codebase or files, explore them yourself instead of asking the user.
3. Continue until all branches of the design tree are resolved.
4. The form TIMES OUT when nobody answers (about 60 min). A timed-out question is not a "no": implement what WAS decided and list the unanswered branch as an open decision — never block the whole execution on it. **Nach einem Timeout zuerst die Uhr neu lesen** (`Get-Date` bzw. `git log -1 --format=%ci`, nie die Sandbox-Uhr): die Frist hat wirklich Zeit verstreichen lassen, und jedes Alter, das du VOR der Frage gemessen hast, ist veraltet — sonst steht im Bericht "3,5 h" fuer einen Gegenstand, der inzwischen 5,5 h stillsteht. Dann die entscheidungsfreie Arbeit tun: nachmessen, den Befund als Aufgabe mit Zahlen und `datei:zeile` festhalten, eigene Pfade committen. Alles, was live oder irreversibel ist (Prozess neu starten, Order, Loeschen, Guthaben bewegen), bleibt unangetastet — eine ausgelaufene Frist ist keine Zustimmung.
5. When finished, provide a concise summary of all decisions made.

## Pitfalls

- **A grill answer that contradicts a documented prior decision must be surfaced, not applied.** If the user picks an option that flips a dated `_vermerk` in wachen.json or an annotation in the source plan (e.g. "festes Ziel true" when the file says false with a backtest reason, or "v4 uebernehmen" when the extrakt says the opposite), stop and ask a follow-up clarify presenting the existing decision and its evidence. The user may have forgotten the earlier call; silently applying the answer would overwrite a deliberate, evidence-backed decision. The follow-up is cheap and the contradiction is exactly what a grill exists to catch.
- **Dissent once with numbers, then record the decision instead of re-asking.** When the user picks the option your own measurement argues against (e.g. keeping a timeframe whose fee drag you just computed), the call is his: state the cost once in the option text or one line, then write the measurement as a dated remark into the task file or a `_vermerk` field so it survives. Do not press the same question twice, and do not quietly drop the number — a measurement nobody wrote down is re-derived next week.
- **A plan's own description of the running state can be stale.** Before grilling, diff the plan text against the live facts (process flags, quantities, phase). Where they disagree, the live facts win and the discrepancy is your FIRST question — it is usually the reason the plan is not working.
- **Entscheidungen haben eine Haltbarkeit — vor dem Ausfuehren neu messen.**
  Zwischen zwei Fragen kann ein Dritter den Gegenstand veraendern: im Betrieb
  gesehen, als eine parallele Sitzung den Lauf waehrend des Grills mit anderen
  Parametern neu startete (19 statt 1 Kontrakt) und damit die eben beschlossene
  Mikro-Stufe ueberholte. Dann nicht den alten Zweig ausfuehren und nicht
  fragen, als waere nichts geschehen: den gemessenen Zustand melden, die
  ueberholte Entscheidung mit Grund als offene Aufgabe notieren und pruefen, dass
  die Parameterdatei zum laufenden Prozess passt, bevor eine Automatik darauf
  reagiert.
  **Vor jedem Umsetzen einer eben erteilten Zustimmung zuerst pruefen, ob die
  ARBEIT schon existiert:** `git log --oneline <basis>..HEAD` und
  `git status` im Ziel-Repo, Zweig-Name, Commit-Zeiten und Autor. Waehrend einer
  ausgelaufenen Frist kann eine parallele Sitzung genau das gebaut, getestet und
  ausgerollt haben, was gerade freigegeben wurde — dann ist die Aufgabe
  Verifizieren statt Bauen (Tests laufen lassen, Gegenprobe, Live-Stand messen),
  und das Ergebnis nennt ausdruecklich, wer es gebaut hat. Doppelt bauen kostet
  nicht nur Zeit: zwei Fassungen derselben Funktion auf zwei Zweigen sind ein
  Merge-Konflikt mit Ansage.
- **Die eigene Praemisse kann falsch sein — dann wird die Antwort ZURUECKGEZOGEN, nicht ausgefuehrt.** Baut eine Frage auf einer Messung auf, die sich beim Nachlesen des Codes als Fehlschluss erweist (eine Log-Zeile, die den Zustand NACH der Aktion druckt; ein Feldname, der etwas anderes meint als er sagt), sage es in einem Satz, nenne den Beleg als `datei:zeile`, und stelle DIESELBE Entscheidung mit den berichtigten Zahlen neu — einmal, nicht zweimal. Wird die falsche Fassung trotzdem ausgefuehrt, entsteht Arbeit gegen einen Fehler, den es nicht gibt; wandert sie als `_vermerk` in die Datei, wird sie beim naechsten Mal als Hausentscheidung gelesen. Bei einer Zuruecknahme gehoert der Grund MIT in den Vermerk.
- **Eine TATSACHE im Optionstext ist selbst eine Behauptung — sie muss gemessen sein, bevor sie im Formular steht.** Der Nutzer waehlt eine Option samt ihrer Begruendung; steht dort ein falscher Fakt ("die Boerse rechnet in USDC ab", ein Kontostand, ein Feldwert), wird genau dieser Fakt zur Entscheidungsgrundlage, und die Zustimmung deckt ihn mit. Gemessen: eine Option nannte eine Waehrung, die dem SYMBOL nach plausibel war; das Instrument trug sie sogar im eigenen Feld — die Wahrheit stand in einem dritten Feld der Kontokonfiguration, und erst der laufende Prozess zeigte sie. Regel: jede Zahl und jede Einheit in einer Option aus der QUELLE lesen, die sie fuehrt (Kontokonfiguration, `max-size`, Kontostand je Waehrung), und im Optionstext nennen, WOher sie kommt. Zwei Optionen mit derselben Zahl aus zwei Quellen sind ein Hinweis auf einen Lesefehler, nicht auf Bestaetigung.
- **Verify named PRs/repos exist before treating them as work.** A plan can name PRs and branches that are phantoms (a PR number that was never opened, a repo whose remote is dead, a branch already merged with 0 commits ahead). Run `gh pr list`/`gh repo view`/`git rev-list --count` on each named target; report the ones that do not exist as findings rather than executing against them. Do not merge a Draft PR before its stated verification (e.g. demo run) has passed, even when the plan says "close the PRs".

**In this house the grill does not end at the summary.** A grill that ends in decisions is followed by execution in the same session: measure, patch with a dated remark, verify with a real run, prove with a Gegenprobe, commit only own paths. The summary is the report, not the deliverable — an approval here is a work order, not a plan to restate.
