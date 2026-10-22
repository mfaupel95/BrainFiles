---
name: skill-github-cli-health-check
description: Trockenlauf des Skills github-cli-health-check — GitHub-CLI-Gesundheitscheck (auth, repos, rate-limit); drei Ausführungspfade (Routine, Cowork+DC, lokal); Trockenlauf.
metadata:
  type: reference
---

**Zweck:** GitHub-CLI-Status prüfen: Installation, Auth, Repo-Zugriff, API-Rate-Limit → Markdown-Report.

**Lauf:** 2026-10-22, trockenlauf.

**Drei Ausführungspfade:**
| Kontext | Pfad | Erkennung |
|---|---|---|
| Cloud-Routine | `gh` direkt + `GITHUB_TOKEN` | Routine-Session |
| Cowork (Mac) | Desktop Commander → `/opt/homebrew/bin/gh` | `mcp__Desktop_Commander__*` verfügbar |
| Lokale Session | VM-Bash, Fallback DC | User ist anwesend |

**Bekannte Einschränkung (Cowork-VM):** Proxy blockiert `api.github.com` → 403. `git push`/`git fetch` funktioniert (nur `github.com`, nicht `api.github.com`). Issue: #37970 (anthropics/claude-code). Nie neu diagnostizieren — nur verlinken und DC nutzen.

**Vier Checks:**
```bash
gh --version
gh auth status
gh repo list --limit 5 --json name,visibility,description,updatedAt,primaryLanguage
gh api rate_limit
```

**Report:** `github-health-check-YYYY-MM-DD.md` unter `$HOME/Claude/Scheduled/github-cli-health-check/` (Mac, nie im Git-Repo, nie im Cowork-Workspace).

**Read-only:** Nie GitHub-State ändern (kein Push, PR, Issue, Token-Rotation), Token nie plaintext ausgeben.
