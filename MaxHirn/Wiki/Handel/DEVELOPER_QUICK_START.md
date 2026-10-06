# QUICK START FOR NEXT DEVELOPER

This document summarizes recent bug fixes applied to the trading bot's core `dauerlauf.py` module. If you're picking up this work, start here.

---

## What Changed?

**6 critical bugs were fixed in `dauerlauf.py`:**

1. **Log file rotation** — now efficient (checks every 100 calls, not every write)
2. **Subprocess timeout** — now caught gracefully (was crashing before)
3. **JSON file corruption** — now handled with detailed error logs (was silent crash)
4. **Telegram command queue** — now resilient (send errors don't block next message)
5. **Environment variable leakage** — now filtered (secrets no longer passed to subprocesses)
6. **Error handling** — now comprehensive and logged

**See `CODE_REVIEW_FIXES.md` for full details.**

---

## Key New Functions

### `_lade_wachen_sicher(pfad)`
**What:** Safely load `wachen.json` config files  
**Returns:** dict or None  
**Why:** Prevents crashes when files are corrupted or empty  
**Use:** Anywhere you're loading trading config JSON

```python
w = _lade_wachen_sicher(os.path.join(ordner, "wachen.json"))
if w is None:
    # Error already logged, safe to continue
    return None
# w is guaranteed to be a dict, not a bad parse
```

### `_env_sicher()`
**What:** Create a subprocess environment with whitelisted variables only  
**Returns:** dict with safe env vars  
**Why:** Prevents API keys from leaking into child processes  
**Use:** Every subprocess.run() call

```python
umgebung = _env_sicher()  # Only PATH, HOME, LANG, etc.
# umgebung does NOT contain MY_SECRET_API_KEY
p = subprocess.run([python, script], env=umgebung)
```

---

## Where Did Things Break?

### Before Fixes:
- Corrupted `wachen.json` → entire bot crashed ❌
- Stuck subprocess → Telegram unresponsive for 10 minutes ❌
- Failed Telegram send → next command never processed ❌
- Log file unbounded growth → disk full ❌
- API keys visible in `ps aux` → security risk ❌

### After Fixes:
- Corrupted config → logs error, bot continues ✅
- Stuck subprocess → timeout at 5 min, bot moves on ✅
- Failed Telegram send → response still sent if possible, next command processed ✅
- Log rotates at 1 MB → disk usage stable ✅
- Env vars filtered → secrets never leak ✅

---

## What to Test

**Before deploying this to production:**

### Test 1: Corrupted Config
```bash
# Break wachen.json
echo "{invalid json" > xperp/wachen.json
# Run a cycle
python dauerlauf.py --trocken --risiko basis
# Expected: logs "wachen.json ungueltig (JSON): ...", continues normally
```

### Test 2: Hanging Subprocess
```bash
# Create a script that hangs
echo "import time; time.sleep(400)" > test_hang.py
# Swap one trading script with it temporarily
# Run one cycle
# Expected: logs "TIMEOUT (exceeded 300s limit)", cycle ends, returns to start
```

### Test 3: Telegram Send Fails
```bash
# Simulate network failure to Telegram
# Send two commands while network is down
# Expected: both commands processed locally, both responses attempted
```

### Test 4: Disk Space
```bash
# Check log rotation works
# Expected: dauerlauf.log rotates to .1 at 1 MB
ls -lh dauerlauf.log*
```

### Test 5: Secrets
```bash
# Run trading bot with fake API key in env
export BINANCE_API_KEY=secret123
python dauerlauf.py &
ps aux | grep handeln.py
# Expected: NO "secret123" in env
pkill -f "dauerlauf.py"
```

---

## Log Messages to Watch For

### Normal (Good):
```
19.09. 14:30:45  Dauerlauf startet, Takt 15 min
19.09. 14:30:47  xperp (papier) ok
19.09. 14:30:50  scanner (papier) ok
```

### Warnings (Investigate):
```
19.09. 14:35:12  xperp TIMEOUT (exceeded 300s limit)
# ^ Subprocess stuck; check if xperp/handeln.py has infinite loop

19.09. 14:36:20  wachen.json ungueltig (JSON): xperp/wachen.json -- ...
# ^ Config file corrupted; restore from backup or manual fix

19.09. 14:37:15  LOG ROTATION ERROR: [Errno 28] No space left on device
# ^ Disk full; clean up old log files

19.09. 14:38:00  Sende fehlgeschlagen (aber zeiger wird vorbeigezogen): ...
# ^ Telegram send failed; message retried next cycle, not lost
```

### Errors (Act):
```
19.09. 14:40:33  Befehl gescheitert: [Traceback ...]
# ^ Command processing crashed; check logs for details

19.09. 14:41:45  Runde gescheitert: [Traceback ...]
# ^ Entire cycle crashed; check if new exception in subprocess
```

---

## Code Organization

```
dauerlauf.py
├── Imports + module-level state
│   ├── _LOG_ROTATION_CHECK_INTERVAL (global counter)
│   ├── SAFE_ENV_VARS (whitelist for subprocess)
│   └── SPUREN (dict of all trading strategies)
│
├── Helper functions (NEW)
│   ├── _lade_wachen_sicher(pfad) ← Use this to load config
│   └── _env_sicher() ← Use this for subprocess env
│
├── protokoll(text)
│   └── Enhanced with rotation optimization
│
├── class Lauf
│   ├── zyklus_spur(spur) ← NOW with timeout exception handling
│   ├── zyklus()
│   ├── pruefe_anfragen()
│   ├── befehl(text)
│   ├── runde() ← NOW with send error isolation
│   └── start()
│
└── main() + CLI
```

---

## If You Need to Extend This

### Add a new trap for a common error:
```python
def _lade_wachen_sicher(pfad):
    # Copy this pattern for other file loads
    try:
        if not os.path.exists(pfad):
            protokoll("File missing: %s" % pfad)
            return None
        with open(pfad, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            protokoll("Expected dict, got %s" % type(data).__name__)
            return None
        return data
    except json.JSONDecodeError as e:
        protokoll("JSON error: %s -- %s" % (pfad, e))
        return None
    except Exception as e:
        protokoll("Load error: %s -- %s" % (pfad, e))
        return None
```

### Add a new subprocess with timeout:
```python
try:
    p = subprocess.run([python_exe, script], timeout=300, env=_env_sicher())
except subprocess.TimeoutExpired:
    protokoll("Script timeout: %s" % script)
    # Handle gracefully
except Exception as e:
    protokoll("Script error: %s -- %s" % (script, e))
    # Handle gracefully
```

---

## Common Questions

**Q: Why 300s timeout instead of 600s?**  
A: Trading cycles should complete in seconds. 5 minutes is already generous. If you need longer, check why the subprocess is hanging.

**Q: Why whitelist env vars instead of just removing secrets?**  
A: Whitelist is safer — you only pass what's needed. Removing specific keys is fragile (new keys added later might leak).

**Q: What's the log rotation strategy?**  
A: Check every 100 writes (not every write = faster). Rotate at 1 MB. Old .1 file is cleaned up. Stable disk usage.

**Q: Can I use `json.load()` directly?**  
A: No. Always use `_lade_wachen_sicher()`. It catches corrupted files, validates structure, and logs errors.

**Q: What if subprocess.run() times out?**  
A: Caught and logged. Bot continues. Exit code 124 returned (standard timeout code). Cycle moves to next "Spur".

**Q: Can I reduce the Telegram send timeout?**  
A: That's in `melder.py`, not here. These fixes are in `dauerlauf.py` only.

---

## Next Steps / Open Items

- [ ] Apply PID file fix to `pruefe()` function (if not done)
- [ ] Add unit tests for error paths (`test_dauerlauf_corruption.py`, etc.)
- [ ] Monitor production logs for new error patterns
- [ ] Consider adding disk space alert to `pruefe_anfragen()`
- [ ] Review other entry points (`agent.py`, `handelszentrale.py`) for same patterns

---

## References

- **Full code review:** `CODE_REVIEW_FIXES.md`
- **Applied changes:** `FIXES_APPLIED_SUMMARY.md`
- **Production troubleshooting:** See log messages section above

---

**Last updated:** 2026-09-19  
**Reviewed by:** Gordon (Docker AI Assistant)  
**Status:** All 6 fixes applied and documented
