---
name: git-recovery
description: "Recover from interrupted git rebase, merge, or stale locks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, rebase, recovery, merge, lock, detached-head, repair]
    category: software-development
    related_skills: [github, systematic-debugging]
---

# Git Recovery

## When to Use

- `git pull --rebase` interrupted by crash, power loss, or forced termination
- Repo stuck in "interactive rebase in progress" state
- `.git/index.lock` blocks all git commands
- HEAD detached after aborted rebase with unpushed commits
- Merge or rebase left half-finished, blocking push

## Diagnosis First — Never Fix Blind

Before touching anything, gather the full state:

```bash
# What operation is in progress?
ls .git/rebase-merge/ 2>/dev/null || ls .git/rebase-apply/ 2>/dev/null

# Is there a stale lock file?
ls .git/index.lock 2>/dev/null

# What branch/HEAD are we on?
git branch --show-current && git log --oneline -3

# Are there unmerged files (real conflicts)?
git diff --name-only --diff-filter=U

# What does the reflog show (original state before interruption)?
git reflog --oneline -15

# How far ahead/behind origin?
git rev-list --count origin/master..HEAD && git rev-list --count HEAD..origin/master
```

## Recovery Procedure

### 1. Remove stale lock file

```bash
rm -f .git/index.lock
```

### 2. Assess the interrupted state

**Check for real conflicts:**
```bash
git diff --name-only --diff-filter=U
```

- **No unmerged files** → the operation was proceeding normally, safe to abort/continue
- **Unmerged files exist** → read each conflict manually before proceeding

### 3. Recover — pick one path

**Path A: Abort and restart (safest when you don't know how far it got):**
```bash
git rebase --abort        # or: git merge --abort
git status                # verify clean state
```

**Path B: Continue (when rebase was nearly done and no conflicts):**
```bash
git rebase --continue
```

**Path C: Reset to origin and re-apply local commits:**
```bash
git fetch origin
git rebase origin/master  # replays your commits on top of current origin
```

### 4. Verify before pushing

```bash
git log --oneline -5          # expected commit history?
git status --short           # any unexpected changes?
git rev-list --count origin/master..HEAD  # how many commits to push?
```

### 5. Push

```bash
git push origin master
```

## Common Scenarios

### Stuck rebase after crash

**Symptom:** `git push` rejected, `git status` shows "interactive rebase in progress"

**Cause:** `git pull --rebase` was interrupted mid-operation. The repo has a `.git/rebase-merge/` directory with the rebase state, and possibly an `index.lock`.

**Fix:**
1. `rm -f .git/index.lock`
2. Check for conflicts: `git diff --name-only --diff-filter=U`
3. If no conflicts: `git rebase --abort` (returns to pre-rebase state)
4. `git fetch origin && git rebase origin/master`
5. `git push origin master`

### Detached HEAD with unpushed commits

**Symptom:** `git branch --show-current` returns empty, commits exist that aren't on any remote branch

**Cause:** Rebase started from a detached HEAD, or branch was deleted during rebase.

**Fix:**
1. Identify the commits: `git log --oneline origin/master..HEAD`
2. Create a branch at current position: `git branch recovery-<date>`
3. Or return to main branch: `git checkout master && git reset --hard origin/master`
4. Then rebase onto origin as normal

### index.lock blocks everything

**Symptom:** `fatal: Unable to create '.git/index.lock': File exists`

**Cause:** A git process was killed before releasing the lock. The lock file is stale.

**Fix:**
1. Verify no git process is actually running (`ps aux | grep git` on Unix, Task Manager on Windows)
2. `rm -f .git/index.lock`
3. Git commands work again

## Pitfalls

- **Never run `git push --force` to work around a stuck rebase** — you'll overwrite remote commits from other agents in a shared tree.
- **Never delete `.git/rebase-merge/` manually** — use `git rebase --abort` which cleans up properly.
- **Never skip the conflict check** — an interrupted rebase with unresolved conflicts will silently drop changes if you abort.
- **In a shared multi-agent tree, check `git reflog` before recovering** — another agent may have started the rebase intentionally.
- **Always `git fetch origin` before deciding the rebase is unnecessary** — origin may have moved since the interruption.

## Multi-Agent Tree Consideration

In a repo shared by multiple agents (as per this workspace's AGENTS.md), an interrupted rebase may have been started by another session. Before recovering:

1. Check if another session is actively working (reflog shows recent activity)
2. If the rebase was recent (< 1 hour), it may still be in progress elsewhere
3. Coordinate in the group chat before aborting another agent's rebase

## Verification

Recovery is complete when:
- `git status` shows a clean working tree (or expected uncommitted files)
- `git push origin master` succeeds
- `git log --oneline` shows the expected commit history
- No `.git/rebase-merge/` or `.git/rebase-apply/` directories remain
