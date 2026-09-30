#!/usr/bin/env python3
"""Test-Suite fuer neue Utilities-Module."""

import sys
import logging
import tempfile
import json

# Logging tests
print("=" * 60)
print("Testing logging_utils.py")
print("=" * 60)

from logging_utils import get_logger, EventLevel, TimerContext, RateLimitedLogger

logger = get_logger("test_module")
logger.info("Test info message", module="test")
logger.audit("test_action", actor="test_user", target="test_target", result="success")
logger.metric("test_metric", 42.5, unit="ms")

rate_logger = RateLimitedLogger(logger, max_per_minute=10)
for i in range(5):
    rate_logger.log(EventLevel.INFO, "rate_test", iteration=i)

with TimerContext(logger, "timer_test") as timer:
    import time
    time.sleep(0.1)

print("✓ Logging tests passed\n")

# State Manager tests
print("=" * 60)
print("Testing state_manager.py")
print("=" * 60)

from state_manager import StateManager, CachedStateManager, load_json, save_json

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = f"{tmpdir}/test.json"
    
    # Test basic write/read
    sm = StateManager(test_file)
    sm.write({"key1": "value1", "key2": {"nested": True}})
    data = sm.read()
    assert data["key1"] == "value1", "Basic write/read failed"
    assert data["key2"]["nested"] == True, "Nested write failed"
    print("✓ Basic write/read passed")
    
    # Test update
    sm.update({"key1": "updated", "key3": "new"})
    data = sm.read()
    assert data["key1"] == "updated", "Update failed"
    assert data["key3"] == "new", "Add new key failed"
    print("✓ Update operations passed")
    
    # Test get with nested keys
    assert sm.get("key1") == "updated", "Get simple key failed"
    assert sm.get("key2.nested") == True, "Get nested key failed"
    assert sm.get("missing", "default") == "default", "Default value failed"
    print("✓ Get operations passed")
    
    # Test cached manager
    cache_file = f"{tmpdir}/cache.json"
    csm = CachedStateManager(cache_file, cache_ttl_s=5.0)
    csm.write({"cached": True})
    
    # Should use cache
    data1 = csm.read()
    # Modify file directly
    with open(cache_file, 'w') as f:
        json.dump({"cached": False}, f)
    # Should still return cached data
    data2 = csm.read()
    assert data2["cached"] == True, "Caching failed"
    print("✓ CachedStateManager passed")
    
    # Invalidate and read again
    csm.invalidate_cache()
    data3 = csm.read()
    assert data3["cached"] == False, "Cache invalidation failed"
    print("✓ Cache invalidation passed")

print()

# Network utils tests
print("=" * 60)
print("Testing network_utils.py")
print("=" * 60)

from network_utils import (
    RetryConfig, retry, CircuitBreaker, 
    CircuitBreakerOpenError, RateLimiter
)

# Test retry config
config = RetryConfig(max_retries=2, base_delay_s=0.05)
delays = [config.get_delay(i) for i in range(3)]
assert all(d > 0 for d in delays), "Delays should be positive"
print("✓ RetryConfig passed")

# Test retry with flaky function
attempt_count = [0]  # Use list for mutable in nested function
def flaky_function():
    attempt_count[0] += 1
    if attempt_count[0] < 3:
        raise ValueError("Temporary error")
    return "success"

result = retry(flaky_function, config)
assert result == "success", "Retry should eventually succeed"
assert attempt_count[0] == 3, "Should have retried 2 times"
print("✓ Retry logic passed")

# Test circuit breaker
breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_s=0.5)

fail_count = [0]
def always_fails():
    fail_count[0] += 1
    raise ValueError("Test error")

# Should fail twice then open
for i in range(2):
    try:
        breaker.call(always_fails)
    except ValueError:
        pass

# Third attempt should be blocked
try:
    breaker.call(always_fails)
    assert False, "Should have raised CircuitBreakerOpenError"
except CircuitBreakerOpenError:
    print("✓ Circuit breaker OPEN state passed")

# Check state info
state_info = breaker.get_state_info()
assert state_info["state"] == "OPEN", "State should be OPEN"
assert state_info["failure_count"] == 2, "Should have 2 failures"
print("✓ Circuit breaker state info passed")

# Test rate limiter
limiter = RateLimiter(max_requests=5, window_s=1.0)

import time
start = time.time()
for _ in range(5):
    assert limiter.acquire(timeout_s=2.0), "Should acquire request"
assert time.time() - start < 0.5, "Should not throttle under limit"
print("✓ RateLimiter under limit passed")

# Test throttling
assert not limiter.acquire(timeout_s=0.1), "Should throttle over limit"
print("✓ RateLimiter throttling passed")

print()
print("=" * 60)
print("✓✓✓ ALL MODULE TESTS PASSED ✓✓✓")
print("=" * 60)
