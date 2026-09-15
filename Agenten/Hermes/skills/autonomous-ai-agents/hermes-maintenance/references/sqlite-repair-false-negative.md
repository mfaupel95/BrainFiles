# SQLite runtime repair — smoke-test false negative (worked example)

Real debug path from a Windows Hermes install (checkout `C:/Hermes`).
Symptom: `hermes doctor` reports `SQLite 3.45.1 (WAL-reset bug)`, the DBs
state `is in WAL mode`, and the auto-repair (armed by installing uv and
re-running `hermes update` from an external interpreter) keeps returning:

```
STATUS: failed
detail: replacement environment did not pass dependency and import smoke tests
sqlite_before: 3.45.1
sqlite_after: 3.53.1
```

`s/n after` shows the repair DID provision a fixed-SQLite runtime (3.53.1)
— the failure is the smoke gate rejecting the staged candidate, after which
it rolls back and removes the candidate. Live venv untouched.

## Reproducing the smoke failure

The staged candidate venv is built and dumped under
`<checkout>/.hermes-runtime/python/venv-candidate-<token>/`. To see the
real error, replicate `_stage_candidate_venv` / `_smoke_candidate_venv`
steps by hand against the existing managed Python generation:

```python
# managed Python lives under .hermes-runtime/python/generation-*/
py = <newest generation>/cpython-3.11.16-windows-x86_64-none/python.exe
# build candidate: uv venv <cand> --python <py> --managed-python \
#   --no-python-downloads --relocatable --no-config
# sync:          uv sync --extra all --locked --python <cand>/Scripts/python.exe
```

Then run the smoke import with the `-I` flag the repair uses:

```python
check = ("import dotenv, fastapi, openai, prompt_toolkit, pydantic, rich, "
         "uvicorn, yaml\nimport hermes_state\n")
# candidate:  <cand>/Scripts/python.exe -I -c "<check>"
```

Reproduced error:

```
ModuleNotFoundError: No module named 'hermes_state_holders'
```

Same command WITHOUT `-I` returns rc 0. So the candidate is healthy and
only the `-I` isolated-mode flag breaks the editable-install finder.

## Why `-I` breaks it

`-I` (isolated mode) ignores `PYTHONPATH` and cwd, but more importantly it
disables the `.pth`-based editable install finder
(`__editable___hermes_agent_0_21_0_finder.py`, installed via
`__editable__.hermes_agent-0.21.0.pth`). Hermes' top-level single-file
modules (listed under `pyproject.toml [tool.setuptools] py-modules`) are
NOT packages — they exist only as loose `.py` files in the checkout and are
mapped by that editable finder. `hermes_state_holders.py` is imported by
`hermes_state.py`, so under `-I` the import chain collapses. The live venv
fails the identical `-I` check, confirming it is the checker, not the
candidate.

## Manual cutover (the fix)

Since the auto-repair refuses to cut over a candidate it misjudges, swap
by hand. Constraint: no process may be executing from the venv (Windows
locks the directory). See the SKILL.md body for the ordered steps; the
invariant to respect:

- Verify candidate BEFORE swap: fixed SQLite + no-`-I` smoke = rc 0.
- Keep the old venv as a backup during the swap (rename, never delete).
- Swap both ways with `os.rename`-style move (or `mv`), not copy, to keep
  the relocatable venv's internal paths intact.
- After swap, retest: `venv/Scripts/python.exe -c "import sqlite3"` and a
  smoke import; then `hermes doctor` and restart the gateway.

## Other repair deferral on Windows (context gate)

Calling `repair_vulnerable_runtime()` from an ad-hoc script (not through
`hermes_cli.main`) yields:

```
SQLite runtime repair deferred: cannot verify Windows venv holders from this update context
```

The holder detector `_detect_venv_python_processes` is attached to the
`hermes_cli.main` module at import time (`main.py` registers it). A script
that only imports `managed_uv` has no detector, so the repair bails
defensively. Run the repair through `hermes_cli.main` context (e.g.
`<system-python> -m hermes_cli.main <update>`), or import `hermes_cli.main`
in the script first. Once armed, the only remaining holder is a live
`gateway run` process — stop it first (`hermes gateway stop`).
