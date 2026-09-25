<!-- Referenz zu hermes-maintenance, Abschnitt "SQLite WAL-reset bug". Stand 25.09.2026. -->

## SQLite WAL-reset bug — the real blocker

Signs in `hermes doctor`:

- `SQLite X (WAL-reset bug)` with a fixed-version hint: 3.51.3+ / 3.50.7 /
  3.44.6.
- `state.db is in WAL mode` + the same for cron/projects/verification_evidence
  /kanban — exposed until SQLite is upgraded.

The version is the LINKED sqlite inside the Python interpreter, not the
Python version — ugrading Python alone can keep a vulnerable SQLite. On an
unstable host this is a real data-corruption risk, not theoretical.

### The fix: `repair_vulnerable_runtime`

Hermes ships a managed repair (`hermes_cli/managed_uv.py`:
`repair_vulnerable_runtime`) that:

1. provisions a uv-Managed Python generation with fixed SQLite
   (`uv python install`, probed + smoke-tested),
2. stages it under `<checkout>/.hermes-runtime/python`,
3. parks the live venv aside and cuts over, then reinstalls deps.

Every failure before cutover leaves the live venv untouched; post-cutover
smoke failures restore it synchronously.

**Key gate:** this repair fires automatically inside `hermes update` via
`ensure_uv()` — but ONLY if uv is already installed when the update runs.
If uv was missing at update time, the update rebuilds the venv with the
system Python and keeps the vulnerable SQLite.

So the fix sequence is:

1. Install uv if missing: `pip install uv` (it lands in `~/.local/bin`,
   already on PATH on this host).
2. Re-run `hermes update` so the repair path is armed.
3. Verify with `hermes doctor` — the SQLite `WAL-reset bug` line and the
   `is in WAL mode` DB warnings must both clear.

### When the repair itself fails: smoke-test false negative (Windows)

Even with uv present and run from an external interpreter, the repair can
return `STATUS: failed` / `detail: replacement environment did not pass
dependency and import smoke tests` while the candidate venv is actually
healthy. Root cause: the staging smoke check (`_smoke_candidate_venv` in
`hermes_cli/managed_uv.py`) launches the candidate with `-I` (isolated
mode), which DISABLES the editable-install sys.path finder. Hermes ships
top-level single-file modules (in `pyproject.toml [tool.setuptools]
py-modules`) that only resolve through that finder — e.g.
`hermes_state_holders` (imported by `hermes_state.py`). Under `-I` the
import fails: `ModuleNotFoundError: No module named 'hermes_state_holders'`.
The live venv fails this same `-I` import too, so it is a false negative,
not real breakage.

Confirm it's a false negative before concluding the candidate is broken:
run the exact same smoke import WITHOUT `-I` on the staged candidate. If it
returns rc 0 and links fixed SQLite, the candidate is good and only the
`-I` flag is to blame.

**Since the auto-repair won't cut over a candidate it misjudges, the manual
cutover is the fix.** The venv is fully regenerable (all real data lives in
HERMES_HOME) so this is low-risk and reversible:

1. Stop the gateway (`hermes gateway stop`) — a running `gateway run`
   process maps the venv and blocks the rename (Windows can't rename a dir
   a process executes from).
2. Locate the newest staged candidate:
   `<checkout>/.hermes-runtime/python/venv-candidate-*` (the fixed managed
   Python + built deps are already there). Verify its `Scripts/python.exe`
   reports fixed SQLite and passes the no-`-I` smoke.
3. Swap: `mv venv venv.bak.sqlite-repair && mv <candidate> venv`.
4. Verify: `venv/Scripts/python.exe -c "import sqlite3;print(sqlite3.sqlite_version)"`
   then `hermes doctor` (the `WAL-reset bug` line must be gone) and
   `venv/Scripts/python.exe -m hermes_cli.main gateway start`.
5. Optionally re-run `hermes update` from the new venv to refresh lazy
   backends / tool deps.

If the repair defers with `cannot verify Windows venv holders from this
update context`, it means the repair ran outside the real `hermes_cli.main`
context (the holder-detector lives on that module). Run it via
`<system-python> -m hermes_cli.main` (or a script that imports
`hermes_cli.main` so `_detect_venv_python_processes` is registered) — then
the remaining holder is just the gateway, which you stop as in step 1.
Full reproduction: `references/sqlite-repair-false-negative.md`.

### Windows self-lock pitfall (hard requirement)

On Windows the repair refuses to cut over when the updater process maps the
venv it is replacing, printing:

> SQLite runtime repair deferred: <...> this process maps the live venv's
> own executable. Retrying `hermes update` from inside this venv cannot help.

Run the update from an interpreter OUTSIDE the venv being replaced:

    cd <checkout>   # e.g. C:/Hermes
    <system-python> -m hermes_cli.main update

Then verify `hermes doctor`.
