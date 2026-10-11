---
name: leitstand-nautilus
description: "Use when working on Leitstand Nautilus/Prozesse tabs."
author: Hermes Agent
license: MIT
version: 1.1.0
metadata:
  hermes:
    tags: [leitstand, nautilus, tkinter, prozesse, robinhood, brainfiles]
    related_skills: [arbeitsbaum-git-hygiene, systematic-debugging]
---

# Leitstand Nautilus & Prozesse

The Leitstand (`leitstand.py`) is a Tkinter notebook with 8 tabs. It never trades live — it only observes and starts/stops child processes. This skill covers the Nautilus tab, the Prozesse tab, and how to bind the trading repos in `Agenten/Handel/`.

## When to Use

Load when modifying `leitstand_nautilus.py`, `leitstand_prozesse.py`, or adding new trading repos as tabs. The repos all live under `C:\Users\faupe\Documents\BrainFiles\Agenten\Handel\`.

## Repo Map (Agenten/Handel/)

| Repo | Type | Entry point | Leitstand |
|------|------|-------------|----------|
| `nautilus/` | OKX DEMO Node (Tkinter GUI) | `nautilus_gui.py` → `NautilusFrame` | ✅ Nautilus tab |
| `nautilus_kraken/` | Kraken Paper Node (Spot/Futures) | `run_kraken_paper_node.py` | ✅ Prozesse tab |
| `nautilus_emacross/` | EMA-Cross Strategy (Kraken) | `handeln.py` | ❌ |
| `nautilus_rc5/` | Kraken Order Test | `kraken_order_test_rc5.py` | ❌ |
| `omnitrade/` | Rust Handelsagent (OKX DEMO) | `omnitrade_lauf.py` / `omnitrade.cmd` | ✅ Prozesse tab |
| `omnitrade_futures/` | Omnitrade + Kraken Futures x7 | `handeln.py` | ❌ |
| `omniquant/` | GUI for Papierspur | `gui.py` | ✅ Omniquant tab |
| `freqtrade/` | Freqtrade Bots | `freqtrade_bridge.py` | ✅ FreqTrade tab |
| `xperp/` | XPerp Trading | `handeln.py` | ❌ |
| `orb/` | ORB Trading | `handeln.py` | ❌ |
| `orbk/` | ORB Trading (Kraken) | `handeln.py` | ❌ |
| `kraken/` | Kraken Trading | `handeln.py` | ❌ |
| `robinhood_radar/` | Robinhood Radar (Paper) | `handeln.py` | ❌ |

## Nautilus Tab Architecture

`NautilusReiter` (in `leitstand_nautilus.py`) is a thin wrapper:
1. Calls `nautilus_gui_laden()` — imports `nautilus_gui` module from `Agenten/Handel/nautilus/`
2. If import fails: shows explanation text instead of crashing (the Leitstand must survive a missing wheel)
3. If success: embeds `modul.NautilusFrame(self)` as the tab content

`NautilusFrame` is a `ttk.Frame` — no window management (title/geometry/minsize/protocol belong to the host).

## Prozesse Tab Architecture

`ProzessReiter` (in `leitstand_prozesse.py`) manages OS-level child processes:
- Each process: `laeuft()`, `starten()`, `stoppen()` + `read_only` flag
- Processes survive Leitstand close (`CREATE_NEW_CONSOLE`)
- PID files: `*.pid` (first field = PID, second = timestamp)
- Quote-only nodes strip API keys from child env
- A persisted PID is only accepted when exe, script AND product env var all match
  (`psutil` cmdline + `environ`) — a bare `prozess_lebt(pid)` would adopt a recycled PID

## Verification

Run the tab suites from their `tests/` directory (each tab module has its own `handeln.py`
and the search path decides which one an import hits):

```bash
cd Agenten/Handel/tests
../scanner/.venv/Scripts/python.exe -m unittest test_leitstand_nautilus test_leitstand_prozesse
```

`lesepruefung.schreibstellen(<modul>)` can be called directly to see a module's write sites
without running the suite — the fastest way to check a read-only claim before editing.

**Those two suites are the fast check, not the whole gate.** A change in shared Handel code can
be green here and red in the tree. The tree runner is `Agenten/Handel/testlauf.py` (40 suites; **~1400 s** measured end to end with
every suite reporting its real count — deliberately NOT the sum of the per-suite limits, which
overshoots by ~2x) and it reports only REGRESSIONS against
`Agenten/Handel/testlauf_basis.json` — so **without that baseline it checks nothing**: a runner
with no recorded stand reports "no change" forever, which is exactly how a red suite can sit in
master unnoticed. Run the tree gate before calling a Leitstand change done.

```bash
cd Agenten/Handel
./scanner/.venv/Scripts/python.exe testlauf.py                    # whole tree
./scanner/.venv/Scripts/python.exe testlauf.py --nur tests        # one suite, fast check
./scanner/.venv/Scripts/python.exe testlauf.py --basis-schreiben  # record the current stand
```

`--nur <suite>` is the fast counter-check after a limit or baseline change: it exercises the one
suite you touched instead of waiting out all 40. Reach for it while iterating, and the full run
once before calling the work done.

**A red test is a claim about the CONTRACT, not proof of a bug in the code.** When a suite fails
because a symbol is missing, grep the source for that symbol before calling it a defect: a
deliberately disabled feature is usually disabled WITH its reason in a comment right at the
line (`# <NAME> AUS seit <datum> (Auftrag ...): <Grund>`), and the module stays importable while
the entry is commented out. The test then encodes an expectation that is simply older than the
decision. Naming which side is wrong decides the fix: calling it a code bug sends the next
session to re-enable a feature that was measured and rejected; calling it a stale test sends
them to update the expectation. Same shape as the write-contract tie-breaker above, and the same
question: is the failing thing the program, or the belief about the program?

**A `fehler: -1` in the baseline is a blind spot, not a zero.** `-1` means the runner's OWN
per-suite limit cut the suite off before its summary, and the runner counts it as a regression
forever — so that suite can never go green and its real failures are never reported. Before
trusting a green tree run, read the baseline for `-1` entries and raise `zeitlimit_sekunden`
until the suite reports its real count. A suite that needs ~1500 s under a 900 s limit reads as
`-1` indefinitely, and its genuine failures stay invisible behind a value that looks like
"unknown".

**When the count fluctuates between runs, record the LOWER number.** Some suites carry tests
whose result depends on what else is running (wall-clock or filesystem-fingerprint assertions
against a tree that live tracks are writing to), so the same suite honestly reports different
counts minutes apart. The baseline is a floor for regression detection, not a record of the
worst case: recording the higher number means a genuinely NEW failure can appear and still land
at or below the stored value, so the runner reports "no change" and the failure goes unnoticed.
Take the smaller of your measurements, and note the spread in the comment so the next reader
knows the number is a floor rather than a constant. Re-measure after raising a limit rather than
reusing a count taken while the suite was truncated — a count from a cut-off run is not a
measurement of anything.

**Set a timeout from a measurement, never from a sum of the parts.** `testlauf.py` gives each
suite its own limit and runs them in sequence, so adding the limits overshoots badly. A too-small
outer limit turns a healthy run into a self-reported failure; a far-too-large one hides a hang.
Measure once, then leave headroom — `Agenten/Hermes/scripts/syntax-tor-wache.py` carries the
measured number.

**And check that the measurement is not itself an artifact of truncation.** A wall time is only
the whole run if no inner suite was cut off. A run measured while one suite hit its own limit
reports a number that is too SMALL: raising the inner limit afterwards makes the real run longer
than anything measured, and the outer limit derived from it then fails on a healthy run. Raise
the inner limit first (`zeitlimit_sekunden` in the baseline), re-measure the whole run, then set
the outer one — never the other way round.

**A suite that shows no output for many minutes is NOT hung.** `testlauf.py` reads each suite
with `stdout=subprocess.PIPE` and prints its text only after the suite ends. A long inner suite
is therefore completely silent while it runs: the log stands still on the previous suite's line,
the child process sits at ~0% CPU (it is waiting on I/O or a single test's own sleep, not
spinning), and RAM does not move. All three signals look exactly like a deadlock. Measure the
real one instead of diagnosing from silence: watch the outer process's own elapsed time, and
check whether the child is still alive. Reading the run as "stuck" and killing it throws away a
healthy 20-minute run — and the same pipe is why a truncated log tail is never proof that a run
ended: `grep -E "^(Ran|OK|FAILED)"` on the finished log is, not the last line you happen to see.

**Enumerating files for the static gate: `git ls-files A B` is an OR, not a filter.**
`git ls-files Agenten/ '*.py'` returns EVERY tracked file under `Agenten/` plus every `.py` in
the tree — thousands instead of the ~1100 wanted — and a checker that then parses `.gitignore`
and `.md` as Python reports a flood of fake syntax findings. Pass one glob and filter in code
(`for p in out.splitlines(): if p.endswith('.py') and p.startswith('Agenten/')`), and assert the
count is in the expected order of magnitude before trusting a clean result.

**The static half of the same gate** is `Agenten/Hermes/scripts/syntax-tor-wache.py`: it parses
every versioned `.py` (`ast.parse`) and rejects builtins called with the wrong arity. That is the
`getattr` four-argument case below — a `TypeError` at runtime that parses fine, so no `py_compile`
and no test suite will find it. The unattended fremdarbeit sweep runs this half before it commits;
the full run is the cron `syntax-tor-wache`.

## Adding a New Repo to Prozesse

1. Add a class with `laeuft()`, `starten()`, `stoppen()` to `leitstand_prozesse.py`
2. Add it to the `PROZESSE` list
3. The UI auto-builds `_ProzessZeile` for each entry

## Adding a New Repo as Tab

1. Create `leitstand_<name>.py` with a `ttk.Frame` subclass
2. Add to `REITER` list in `leitstand.py`
3. Add to `TAKT_SICHTBAR` if it needs periodic refresh
4. Add keyboard shortcut if needed (Ctrl+1..8)

## Always-on Rules

- **Fail soft**: a missing venv, missing nautilus_trader, or missing keys must NEVER crash the Leitstand
- **No live trading**: the Leitstand is observation-only. Child processes decide their own trading mode
- **No secrets in code**: API keys come from env vars, never hardcoded
- **Read-only by default**: new repos start observation-only until explicitly wired to a trading path
- **One PID file, one owner.** A child process is started, polled and stopped by exactly ONE
  tab class. Two surfaces reading the same `nautilus_kraken_node_<produkt>.pid` each see the
  other's process: `laeuft()` lies, and a second Start leaves an orphan nobody stops. Before
  giving a tab its own Start/Stop, grep the PID filename across the tree — if a `PROZESSE`
  entry already owns it, the new tab is a duplicate, not a feature.
- **The repo map above is the authority.** `nautilus_kraken` (Spot/Futures) belongs to the
  Prozesse tab. A change that re-implements an existing node inside a second tab contradicts
  the map; the map wins until it is deliberately changed here.
- **The read-only claim is machine-enforced.** `tests/lesepruefung.py` parses a module's AST and
  returns every write site (`.write_text`, `.unlink`, `.mkdir`, `json.dump`, `open(...,'w')`, …);
  `test_der_reiter_schreibt_nichts` asserts that list is empty. Adding any write to a read-only
  tab module turns that test red — and that test is the OLDER witness, so decide which side is
  wrong before editing either one. Details: `references/read-only-contract.md`.
- **The tab interface runs on EVERY refresh.** `leitstand.py` calls `r.titel_zusatz()` and
  `r.status()` for every tab each cycle. An exception there takes down the whole window, not one
  tab — so those methods must be total: never index, never assume an attribute exists, and never
  call a builtin with the wrong arity (`getattr(obj, name, default, False)` is four arguments and
  raises `TypeError` on every call while parsing fine).
- **A tab that builds without its dependency is a feature, not a fallback.** `nautilus_gui_laden()`
  returning `(None, grund)` must leave a readable explanation in the tab, never a traceback.