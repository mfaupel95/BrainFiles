---
name: multi-agent-discussion-contributions
description: "Reply to multi-agent threads with verified, cited evidence."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Discussion, Multi-Agent, Codebase, Evidence, Review]
    category: software-development
    related_skills: [grounded-citations, codebase-inspection, requesting-code-review]
---

# Contributing to a Multi-Agent Discussion Thread

One message, several participants, each citing paths, line numbers and file sizes.
A reply that is merely plausible adds noise; a reply that is *verifiable*
reorders the room. The deliverable is not agreement — it is a claim the next
reader can check.

## When to Use

- You are one participant in a thread with several handles, where each message
  cites repository paths, functions or measurements.
- The thread asks for proposals on what to build, extend or optimise next.
- You hold local access to the repository the thread is arguing about.

Skip when the thread is purely conversational or you have no repository access —
then contribute reasoning, not citations.

## Procedure

1. **Inventory the repo before reading any peer claim.** One batched pass:
   top-level dirs, `git log --oneline -8`, `git branch --show-current`,
   `git status --short`. You need to know which branch/worktree you are actually
   looking at, because peers are usually describing a different one.

2. **Existence-check every path any participant cites.** `search_files` with
   `target=files` and the literal path stem, plus a content search for the
   symbol. A cited file that returns nothing is the single highest-value fact
   you can contribute — state it as such instead of accepting the claim.

3. **Grep the symbol before describing the component.** `grep -rn` for the
   symbol across `src/`, and `wc -l` the file, so "exists / does not exist" and
   "how big" come from the tree rather than from memory.

4. **Read the invariant text, not just the code.** Repo-root `AGENTS.md`,
   `LIMITATIONS.md`, and the plan or design docs under `docs/` are where the
   project's own constraints live. A proposal that violates one of these is the
   correction the thread actually needs.

5. **Classify each peer claim as *already built*, *built but ungated*, or
   *missing*. Most "we should build X" threads are 2 of 3. Say which, and name
   the gap precisely (no gate, no owner, wrong writer) rather than voting.

6. **Write the message**: one new verified fact first, then the classification,
   then a concrete ask that assigns the next step to a named handle. End with
   a question — a message that ends in a statement ends the thread.

## Pitfalls

- **Accepting a path without checking it.** A peer's `repo/Module/file.py` may
  belong to a sibling repository you do not have. Verify the path exists before
  building an argument on it, and say plainly when it does not — that corrects
  the whole thread, not one participant.
- **Restating a peer's claim in your own words.** Restatement is not a new
  contribution. Only write when you checked something they did not.
- **Quoting the codebase loosely.** Never paraphrase a file as "the code says
  costs are not modelled" unless you read that line. Load-bearing claims get a
  `path:line` reference copied from the file you actually read; the reader must
  be able to jump to it.
- **Building a gate without finding the single writer.** If an architecture names
  one component as the sole owner of a write (a controller, a resolver), a
  proposed second verifier is an architectural violation, not an improvement.
  Locate the owner first, then propose feeding *it*.
- **Proposing a gate that cannot fire.** Before suggesting a statistical gate,
  check whether the existing evidence shows it failing by construction — e.g. a
  trial-count bottleneck that makes every run fail. Propose the test that
  discriminates (power, required sample size) instead of a verdict.
- **Arguing about a parameter the system already computes.** When a peer asks
  for a feature, grep the tree for it first: it often exists as an untyped
  helper. The real gap is typing, versioning or promoting it, not writing it.
- **Reciting the codebase map.** Paths, file sizes and module inventories are
  evidence for a point, not the message. One line per claim, in service of the
  correction.

## Verification

- [ ] Every path, line number and file size you cite was returned by a search or
      read in this session, not recalled.
- [ ] Any path a peer cited that does not exist in your tree is reported as
      missing rather than absorbed into your argument.
- [ ] No point made by another participant is repeated without new evidence.
- [ ] The message ends with a question or an assignment to a named handle.
- [ ] At least one claim is something you verified and no peer had checked.
