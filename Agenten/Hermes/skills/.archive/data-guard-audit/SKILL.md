---
name: data-guard-audit
description: Verifies file safety tiers before bulk changes.
version: 0.1.0
author: Human Contributor, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [security, guard, data-protection]
    related_skills: [protecting-irreplaceable-data]
---

# Data Guard Audit

An operational safety skill that prevents destructive actions on critical data by checking the target against established safety tiers.

## When to Use
*   Before running any `rm`, `mv`, `del`, `Remove-Item`, or `robocopy /MIR`.
*   Before any bulk operation involving multiple files or directories.
*   When reorganizing or cleaning up the `MaxHirn/` archive.

**Don't use for:**
*   Single-file reads.
*   Creating new, non-existing files in Tier 2 areas.

## Prerequisites
*   The `audit_logic.py` script must be accessible.

## How to Run
Invoke the `terminal` tool to run the audit script:
`terminal(command="python optional-skills/productivity/data-guard-audit/scripts/audit_logic.py --path '<path>' --action '<action>'")`

## Quick Reference
| Action Type | Command Example |
| :--- | :--- |
| **Audit Delete** | `--action delete` |
| **Audit Move** | `--action move` |
| **Audit Overwrite** | `--action overwrite` |

## Procedure
1.  **Analyze Intent**: Determine if the planned action is a read, a single write, or a bulk destructive operation.
2.  **Run Audit**: Execute the `audit_logic.py` script with the target path and action.
3.  **Evaluate Decision**:
    *   If `DECISION: ALLOW` $\rightarrow$ Proceed with caution.
    *   If `DECISION: ENFORCE_BACKUP` $\rightarrow$ Stop. Create a `.bak-YYYYMMDD` copy of the target first.
    *   If `DECISION: QUARANTINE` $\rightarrow$ Stop. Move the file to the `_zu_loeschen/` directory instead of deleting.
    *   If `DECISION: DENY` $\rightarrow$ Stop immediately. This is a Tier 0 asset.
4.  **Verify**: After the action, confirm the target is in the intended state and no unintended files were touched.

## Pitfalls
*   **Relative Paths**: Always use absolute paths or paths relative to the repository root to ensure the audit script correctly identifies the Tier.
*   **False Sense of Security**: This script is a logic check, not a filesystem lock. It cannot prevent a process already running from doing harm.

## Verification
*   Run a test against a Tier 0 path (e.g., `MaxHirn/Wissen/Schutzregeln.md`) with `--action delete` and ensure it returns `DENY`.
