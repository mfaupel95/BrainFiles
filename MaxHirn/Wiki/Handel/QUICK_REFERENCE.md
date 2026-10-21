# Quick Reference: New BrainFiles Utilities

**Location**: `/Agenten/Handel/`  
**All modules**: Type-annotated, documented, tested ✅

---

## 🚀 Quick Start

### Configuration (Zero Runtime Cost)
```python
from config import SPUREN, RISIKO_STUFEN, ThresholdConfig

# All spuren with their currency
print(SPUREN.keys())  # dict_keys(['xperp', 'scanner', 'swap', 'kraken', 'omniquant'])

# Risk levels
for name, stufe in RISIKO_STUFEN.items():
    print(f"{name}: x{stufe.faktor}")  # niedrig: x1.0, mittel: x2.0, etc.
```

### Logging (JSON Events)
```python
from logging_utils import get_logger

logger = get_logger(__name__)
logger.info("Bot started", version="1.0")
logger.audit("position_opened", "bot", "BTC-USD", "success", size=1.5)
logger.metric("cycle_time", 2.3, unit="s")
```

### State Management (Atomic)
```python
from state_manager import StateManager

state = StateManager("zustand.json")
state.write({"position": 1.5})
state.update({"stop": 100.0})
price = state.get("stop")
```

### Network Resilience
```python
from network_utils import retry, CircuitBreaker

# Simple retry
result = retry(lambda: api.get_price("BTC"))

# With circuit breaker
breaker = CircuitBreaker(failure_threshold=3)
try:
    price = breaker.call(fetch_price, "BTC")
except:
    price = get_cached_price("BTC")
```

---

## 📚 Full API Reference

### config.py
```python
from config import (
    SPUREN,              # Dict[str, SpurConfig] — all trading tracks
    RISIKO_STUFEN,       # Dict[str, RisikoStufe] — risk levels
    ThresholdConfig,     # Class with monitoring thresholds
    DEFAULT_TAKT_MINUTEN,# Cycle interval
    TIMEOUT_S,           # Max cycle duration
)

# SpurConfig fields
spur = SPUREN["xperp"]
spur.ordner          # "xperp"
spur.waehrung        # "USD"
spur.beschreibung    # "OKX Perpetuals - Hauptweg"

# RisikoStufe fields
stufe = RISIKO_STUFEN["mittel"]
stufe.name           # "Mittel"
stufe.faktor         # 2.0
stufe.live_mode      # False
stufe.telegram_aktiv # False
```

### logging_utils.py
```python
from logging_utils import (
    get_logger,           # Get StructuredLogger
    EventLevel,          # Enum: DEBUG, INFO, WARNING, ERROR, AUDIT, METRIC
    TimerContext,        # Measure function duration
    RateLimitedLogger,   # Prevent log spam
    log_call,           # Decorator for function tracing
)

logger = get_logger("my_module")

# Methods
logger.info(msg, **kwargs)        # Info event
logger.warning(msg, **kwargs)     # Warning event
logger.error(msg, exc_info=True)  # Error with exception
logger.audit(action, actor, target, result, **kwargs)  # Compliance log
logger.metric(name, value, unit="", **kwargs)  # Performance metric

# Context manager
with TimerContext(logger, "operation_name"):
    do_something()  # Auto-logs duration

# Rate limiting
rate_logger = RateLimitedLogger(logger, max_per_minute=100)
rate_logger.log(EventLevel.WARNING, "action")  # Returns bool
```

### state_manager.py
```python
from state_manager import (
    StateManager,        # Basic JSON operations
    CachedStateManager,  # With TTL cache
    load_json,          # Quick load
    save_json,          # Quick save
)

# Basic
state = StateManager("file.json")
state.write({"key": "value"})
state.read()
state.get("key", default=None)
state.update({"key": "new_value"})
state.delete()

# Cached (30s TTL default)
cached = CachedStateManager("file.json", cache_ttl_s=30)
cached.read()  # Uses cache if fresh
cached.invalidate_cache()

# Validation
schema = {"required_key": str, "count": int}
if state.validate(schema):
    print("Valid!")
```

### network_utils.py
```python
from network_utils import (
    retry,                    # Function retry
    retry_decorator,         # @retry_decorator()
    CircuitBreaker,          # Cascading failure prevention
    CircuitBreakerOpenError,
    RetryConfig,            # Exponential backoff config
    RateLimiter,            # Max requests/window
)

# Simple retry
result = retry(lambda: risky_function())

# Retry with config
config = RetryConfig(max_retries=5, base_delay_s=1.0, exponential_base=2.0)
result = retry(lambda: api_call(), config)

# Decorator
@retry_decorator(RetryConfig(max_retries=3))
def fetch_data():
    return api.get_data()

# Circuit breaker
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout_s=60)
try:
    result = breaker.call(risky_func, arg1, arg2)
except CircuitBreakerOpenError:
    result = fallback_value

# Rate limiting
limiter = RateLimiter(max_requests=10, window_s=1.0)
for item in items:
    limiter.acquire(timeout_s=5.0)  # Block until allowed
    process(item)
```

### ui_helpers.py
```python
from ui_helpers import (
    format_currency,    # 1234.567 → "1234.57"
    format_time_short,  # ISO → "HH:MM"
    safe_thread_operation,  # Thread with error handling
    safe_queue_get,     # Queue with timeout
    clamp,              # Constrain value to range
    elapsed_minutes,    # Time since datetime
)

# Formatting
kurs = format_currency(1234.567)  # "1234.57"
zeit = format_time_short("2026-09-30T16:45:00")  # "16:45"

# Threading
thread = safe_thread_operation(my_func, args=(arg1,), daemon=True)

# Queue
from queue import Queue
q = Queue()
data = safe_queue_get(q, timeout=0.5)  # None if timeout

# Math
clamped = clamp(1.5, min_val=0.0, max_val=1.0)  # 1.0
```

---

## 🔧 Common Patterns

### Pattern 1: Cycle with Logging & Timing
```python
from config import DEFAULT_TAKT_MINUTEN
from logging_utils import get_logger, TimerContext

logger = get_logger("dauerlauf")

def cycle():
    with TimerContext(logger, "cycle_xperp"):
        # Your cycle logic
        pass

logger.info("Cycle started", takt_s=DEFAULT_TAKT_MINUTEN * 60)
cycle()
```

### Pattern 2: Resilient API Call
```python
from network_utils import CircuitBreaker
from logging_utils import get_logger

logger = get_logger("okx_api")
okx_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_s=120)

def get_price(symbol):
    try:
        return okx_breaker.call(okx_api.letzter_kurs, symbol)
    except Exception as e:
        logger.error(f"Price fetch failed: {e}")
        return None
```

### Pattern 3: State Update with Audit
```python
from state_manager import StateManager
from logging_utils import get_logger

state = StateManager("zustand.json")
logger = get_logger("trader")

def open_position(symbol, size):
    state.update({"position": size, "symbol": symbol})
    logger.audit("position_opened", "trader", symbol, "success", size=size)
```

### Pattern 4: Rate-Limited Event Logging
```python
from logging_utils import RateLimitedLogger, get_logger

logger = get_logger("market")
rate_logger = RateLimitedLogger(logger, max_per_minute=100)

for tick in price_stream:
    # Only log max 100 ticks/min
    rate_logger.log(EventLevel.DEBUG, "price_tick", price=tick)
```

---

## ⚡ Performance Tips

1. **Config** — Access constants directly, no overhead
2. **Logging** — JSON serialization is fast; use rate limiting for high-frequency events
3. **State** — CachedStateManager is ideal for frequent reads
4. **Network** — Circuit breaker costs 0 unless in OPEN state
5. **UI** — format_currency/format_time_short are O(1)

---

## 🧪 Testing

```bash
cd Agenten/Handel
python test_modules.py
```

Expected output: `✓✓✓ ALL MODULE TESTS PASSED ✓✓✓`

---

## 📝 Migration Checklist

- [ ] Replace `print()` → `logger.info()`
- [ ] Replace manual JSON → `StateManager`
- [ ] Add CircuitBreaker to API calls
- [ ] Use `format_currency()` in UI
- [ ] Add `TimerContext` to slow functions
- [ ] Add metrics with `logger.metric()`

---

**Questions?** Check `MaxHirn/Archiv/IMPROVEMENTS_2026-09-30.md` for detailed docs.
