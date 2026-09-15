# Verifying the protection actually works

Companion to `git-over-text-layer.md`. That file covers building the repo; this
one covers proving it, and the false alarms that waste a session.

The rule behind all of it: **a backup that was never restored is not a backup.**
Never report "version control is set up" off a successful commit. A commit hash
proves bytes were written, not that the right bytes come back.

## Two independent proofs, not one

| Proof | What it catches | What it misses |
|---|---|---|
| `git restore` after corrupting a file | the undo path works | wrong scope — media could still be in there |
| `git clone` into a temp dir | scope, size, exclusions | nothing about restoring a damaged file |

Run both. They fail in different directions.

```bash
git clone -q <root> "$TMPDIR/probe-clone"
git -C "$TMPDIR/probe-clone" ls-files | wc -l    # must match the source count
du -sh "$TMPDIR/probe-clone"                     # MB, not GB
ls "$TMPDIR/probe-clone/<archive-dir>"           # media dirs must be ABSENT
```

Then delete the clone. If the delete is blocked by your own deny list, say so
and leave it — do not route around the guard (see the note at the end).

## Trap: mixed-path hash comparison invents failures

Comparing source against clone with `git hash-object` is the right instinct, but
each path must be resolved against the repo it lives in. Hand a source-absolute
path to the clone's `git -C` (or the reverse) and it hashes a **missing or
wrong file** — every entry then reports as differing.

This produced four confident `ABWEICHUNG` lines in one session. The files were
byte-identical. The comparison was broken, not the repo.

**Never conclude "the clone is corrupt" from a hash mismatch alone.** Confirm
with a real content diff; only a non-zero line count is a genuine difference.

```bash
Q=<source-root>
cd "$TMPDIR/probe-clone"
for f in Notes/Deadlines.md scripts/sort.py; do
  n=$(diff <(tr -d '\r' < "$Q/$f") <(tr -d '\r' < "$f") | wc -l)
  printf '%-40s diffs: %s\n' "$f" "$n"
done
```

`tr -d '\r'` keeps a CRLF difference from masquerading as a content difference.
Check line endings separately with `git ls-files --eol`.

## Trap: an empty staging area reads like a broken .gitignore

After `git reset`, `git diff --cached --name-only | wc -l` returns 0 — which
looks exactly like a whitelist that excludes everything. It usually is not.

Before rewriting rules, ask whether the work is simply already committed:

```bash
git log --oneline        # commits exist?
git ls-files | wc -l     # index populated?
git status --short       # clean tree = nothing staged BECAUSE nothing changed
```

A clean tree with commits present means the repo is fine and the diff was the
wrong question. `git check-ignore -v <path>` printing "NICHT ignoriert" for
files you expected to be excluded is the same signal read from the other side —
and remember it stays silent about tracked files entirely, so use
`--no-index` when auditing rules.

## Report the residue honestly

Two things routinely get glossed at the end of these sessions. Name both:

- **The repo is on the same disk as the original.** It defends against a bad
  write, not against losing the drive. A remote (private GitHub) is the step
  that also delivers the off-site copy — offer it, do not imply it exists.
- **Temp artefacts you could not remove.** If a probe clone survived because a
  delete was refused, say where it is and how big. Do not quietly leave it.

## When your own guard blocks the verification

A refused `rm -rf`, `git rm -r --cached .`, or `Remove-Item` is the protection
working as designed. Setting up a deny list and then bypassing it is the exact
failure this skill exists to prevent.

Do not rephrase the command, do not reach for a different tool to achieve the
same delete. Either switch to explicitly named narrow paths, or explain the
block to the user and let them decide. When a sweeping index rebuild is blocked,
`git reset` (index only, files untouched) reaches the same state and is worth
offering as the safer alternative — spell out that it touches no files on disk.
