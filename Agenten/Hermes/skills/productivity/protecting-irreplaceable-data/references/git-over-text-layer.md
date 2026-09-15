# Git over the text layer of a data vault

The cheap win named in Step 6: version history for the hand-maintained text of
an archive, **without** dragging in the multi-GB media. Closes the one gap a
mirroring backup cannot — it defends against a bad *write*, not just disk loss.

Scope check before starting: this does not replace the backup and does not give
an off-site copy. `.git` sits on the same disk as the original. Say so.

## Why a whitelist .gitignore, never a blacklist

A blacklist ingests every new file unasked. That is exactly how a key file ends
up in history — and **git never forgets**: deleting the file later leaves it in
every past commit and every clone. Invert the default.

```gitignore
# 1) ignore everything
*

# 2) but keep directories walkable — WITHOUT this, git stops at the first
#    ignored level and finds none of the allows below
!*/

# 3) the ignore rules must whitelist THEMSELVES, or rule 1 swallows them
!/.gitignore
!/.gitattributes

# 4) then allow, path by path
!/*.md
!Notes/**/*.md
!scripts/*.py

# 5) re-exceptions: things that must stay out despite the allows above.
#    Unqualified patterns like *.env.template match at ANY depth and will
#    pull in vendor files from directories you never meant to include.
Secrets.md
**/.env
**/*.pem
**/*.pfx
**/*.p12
**/*.kdbx
vendor-servers/*/**
```

Consequence to tell the user plainly: **new files are not picked up
automatically.** Anything that should be versioned needs an allow line. That is
the price of the safety, and they will otherwise discover it by losing a note.

## Trap: `git check-ignore` stays silent about tracked files

The single most time-wasting trap here. Once a path is in the index,
`check-ignore` reports nothing for it — so a rule that *is* correct looks
broken, and you go hunting a pattern bug that does not exist.

```bash
git check-ignore -v <path>              # ignores the question for tracked files
git check-ignore --no-index -v <path>   # what the RULE actually says
```

Use `--no-index` when auditing rules. Use plain `check-ignore` only for files
you know are untracked. A tracked file is not un-tracked by adding a rule —
remove it from the index explicitly (below).

## Trap: nested repos become broken gitlinks

Any subdirectory with its own `.git` (vendored clones, an installed agent, a
downloaded tool) is staged as mode `160000` — a submodule reference — even with
no `.gitmodules`. It stores only a foreign commit hash; on checkout the user
finds an **empty folder**. It also makes `git status` permanently dirty.

```bash
# detect: any 160000 is wrong unless you deliberately run submodules
git ls-files -s | awk '{print $1}' | sort | uniq -c
git ls-files -s | grep ' 160000 '
```

Remove from the index only — never from disk:

```bash
git rm --cached -f -q <dir1> <dir2>
```

`git rm --cached` refuses with "staged content different from HEAD" before the
first commit; `-f` is required and is safe here because it touches the index
only. **Prove it:** count files before and after and show both numbers.

```bash
for d in <dirs>; do printf '%-40s %s\n' "$d" "$(find "$d" -type f | wc -l)"; done
```

## Line endings: pin them, or a 3-line edit looks like a rewrite

If the tree uses LF, Git for Windows converts to CRLF on checkout and back on
commit. Every diff then shows the whole file. Ship a `.gitattributes`:

```gitattributes
* -text
*.png binary
*.pdf binary
*.db  binary
```

Plus `git config core.autocrlf false` locally. `.gitattributes` wins on its own,
but the pair survives a clone onto a differently-configured machine.

Audit what git sees. `attr/-text` means no conversion; a `w/crlf` working-tree
entry alongside it is fine — the file is simply CRLF on disk and stays that way.

```bash
git ls-files --eol
```

## Before the first commit: prove no secrets are in it

Two independent checks. Path-based, then content-based.

```bash
# 1) is anything secret-shaped staged?
git ls-files | grep -Ei 'secret|passwo|/\.env$|\.pfx|\.pem|\.kdbx|\.p12'

# 2) key-shaped strings inside tracked files
git ls-files -z | xargs -0 grep -InE \
  '(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)' \
  | grep -viE 'lock|\.template|placeholder|your_api_key|example'
```

Filter the noise (lockfiles, `.env.template` placeholders) or the real signal
drowns. Long base64-ish matches are usually hashes or file paths — read each hit
rather than assuming.

After committing, confirm the secret paths were **never** in history:

```bash
git log --all --full-history -- Secrets.md '**/.env'   # must print nothing
```

## Keep `git status` empty, not merely short

A directory with nothing whitelisted still shows as `?? Dir/` because `!*/` made
it walkable. Persistent noise is a safety problem: someone used to two junk
lines misses the third that matters. Add `Dir/**` and get to a clean tree.

## Verify by restoring, not by asserting

Do not report "version control is set up" off a successful commit. Run the drill:

```bash
cp Notes/Deadlines.md "$TMPDIR/probe"            # safety copy outside the repo
# ...corrupt the file in place...
git diff --stat Notes/Deadlines.md               # shows the loss
git restore Notes/Deadlines.md
sha256sum Notes/Deadlines.md; diff -q "$TMPDIR/probe" Notes/Deadlines.md
```

Report the before/after hashes. That is the evidence the mechanism works; a
commit hash alone is not.

## Hand the user the four commands they will actually use

```bash
git status                  # what changed since the last commit
git diff <path>             # what exactly
git restore <path>          # undo an accidental overwrite
git add -A && git commit -m "..."
```

## If your own deny list blocks you

Setting up protection and then bypassing it is the failure this whole skill
exists to prevent. A blocked `git rm -r --cached .` or `rm -rf` is the guard
working. Do not rephrase it, do not route around it — switch to explicitly
named paths and continue. Sweeping index rebuilds are avoidable; targeted
`git rm --cached <path>` plus `git add <path>` reaches the same state.
