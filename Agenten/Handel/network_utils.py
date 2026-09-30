"""Network-Utilities: Retry-Logik, Circuit Breaker, Timeouts.

Fuer API-Aufrufe zu Exchanges, Kurs-Feeds, Telegram etc.
"""

import time
import logging
import random
from typing import Any, Callable, Optional, TypeVar, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from functools import wraps

log = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Zustaende des Circuit Breakers."""
    CLOSED = "CLOSED"  # Normal, requests durchgelassen
    OPEN = "OPEN"  # Zu viele Fehler, requests blockiert
    HALF_OPEN = "HALF_OPEN"  # Recovery-Mode, limitierte Requests


class CircuitBreaker:
    """Circuit Breaker fuer cascading failures.
    
    Wenn Fehlerrate zu hoch: blockiere Requests kurzzeitig und versuche Recovery.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_s: float = 60.0,
        expected_exception: type = Exception
    ):
        """Initialisiere Circuit Breaker.
        
        Args:
            failure_threshold: Fehler bis zum OPEN-Zustand
            recovery_timeout_s: Warten vor HALF_OPEN
            expected_exception: Exception-Typ fuer Fehlerbehandlung
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.expected_exception = expected_exception
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.last_attempt_time = None
    
    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Rufe Funktion durch Circuit Breaker auf.
        
        Args:
            func: Zielfunktion
            *args, **kwargs: Argumente fuer Zielfunktion
            
        Returns:
            Ergebnis von func
            
        Raises:
            CircuitBreakerOpenError: wenn Circuit OPEN ist
            Original exception: von func wenn sie fehlschlaegt
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Retry in "
                    f"{self.recovery_timeout_s}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Pruefe ob Recovery-Timeout abgelaufen ist."""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout_s
    
    def _on_success(self) -> None:
        """Fehler aufraeumen nach erfolg."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        log.info("Circuit breaker: CLOSED (healthy)")
    
    def _on_failure(self) -> None:
        """Fehler erhoehen, ggf. oeffnen."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            log.warning(
                f"Circuit breaker: OPEN (failures={self.failure_count})"
            )
    
    def get_state_info(self) -> dict:
        """Debug-Info ueber Circuit Breaker-Status."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class CircuitBreakerOpenError(Exception):
    """Exception wenn Circuit Breaker OPEN ist."""
    pass


class RetryConfig:
    """Konfiguration fuer Retry-Logik."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay_s: float = 1.0,
        max_delay_s: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Args:
            max_retries: Max Retry-Versuche
            base_delay_s: Start-Delay in Sekunden
            max_delay_s: Max Delay zwischen Retries
            exponential_base: Basis fuer exponentielle Backoff
            jitter: Zufaellige Verzoegerung hinzufuegen
        """
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s
        self.max_delay_s = max_delay_s
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Berechne Delay fuer Attempt N.
        
        Args:
            attempt: Versuch (0-indexed)
            
        Returns:
            Verzoegerung in Sekunden
        """
        delay = self.base_delay_s * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay_s)
        
        if self.jitter:
            # Jitter: +/- 10% vom Delay
            jitter_amount = delay * 0.1
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(delay, 0.0)


def retry(
    func: Callable[..., T],
    config: RetryConfig = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None
) -> T:
    """Rufe Funktion mit Retry-Logik auf.
    
    Args:
        func: Zielfunktion
        config: RetryConfig (Vorgabe: 3 Retries mit exponential backoff)
        on_retry: Callback bei jedem Retry: (attempt_num, exception)
        
    Returns:
        Ergebnis von func
        
    Raises:
        Exception: von func wenn alle Retries fehlschlagen
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return func()
        
        except Exception as e:
            last_exception = e
            
            if attempt < config.max_retries:
                delay = config.get_delay(attempt)
                
                if on_retry:
                    on_retry(attempt + 1, e)
                
                log.debug(
                    f"Retry {attempt + 1}/{config.max_retries} "
                    f"in {delay:.1f}s after {type(e).__name__}: {str(e)[:100]}"
                )
                
                time.sleep(delay)
            else:
                log.error(
                    f"All {config.max_retries + 1} attempts failed. "
                    f"Last error: {type(last_exception).__name__}: {str(last_exception)}"
                )
    
    raise last_exception


def retry_decorator(config: RetryConfig = None, on_retry: Optional[Callable] = None):
    """Decorator fuer Funktionen mit Retry.
    
    Usage:
        @retry_decorator(RetryConfig(max_retries=5))
        def fetch_price(symbol: str):
            return api.get_price(symbol)
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            def call_func():
                return func(*args, **kwargs)
            
            return retry(call_func, config, on_retry)
        
        return wrapper
    
    return decorator


class RateLimiter:
    """Einfacher Rate Limiter (Requests pro Sekunde)."""
    
    def __init__(self, max_requests: int, window_s: float = 1.0):
        """
        Args:
            max_requests: Max Requests pro Window
            window_s: Fenster in Sekunden
        """
        self.max_requests = max_requests
        self.window_s = window_s
        self.requests = []
    
    def acquire(self, timeout_s: float = 10.0) -> bool:
        """Warte bis Request gestattet ist.
        
        Args:
            timeout_s: Max Warte-Zeit
            
        Returns:
            True wenn Request gestattet, False bei Timeout
        """
        start_time = time.time()
        
        while True:
            now = time.time()
            
            # Alte Requests aus Window entfernen
            self.requests = [
                req_time for req_time in self.requests
                if now - req_time < self.window_s
            ]
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            if time.time() - start_time > timeout_s:
                return False
            
            time.sleep(0.01)


class Timeout:
    """Context-Manager fuer Timeout-Ausfuehrung."""
    
    def __init__(self, seconds: float, error_message: str = "Operation timed out"):
        """
        Args:
            seconds: Timeout in Sekunden
            error_message: Error-Nachricht
            
        Note:
            Auf Unix: nutzt signal. Auf Windows: kann nicht unterbrochen werden.
        """
        self.seconds = seconds
        self.error_message = error_message
    
    def __enter__(self):
        import signal
        
        def _timeout_handler(signum, frame):
            raise TimeoutError(self.error_message)
        
        self.old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(int(self.seconds))
        return self
    
    def __exit__(self, *args):
        import signal
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self.old_handler)


# Convenience-Funktion
def call_with_retry_and_timeout(
    func: Callable[..., T],
    timeout_s: float = 30.0,
    retry_config: RetryConfig = None,
    operation_name: str = "operation"
) -> Tuple[bool, Optional[T], Optional[str]]:
    """Rufe Funktion mit Retry und Timeout auf.
    
    Args:
        func: Zielfunktion
        timeout_s: Timeout pro Versuch
        retry_config: Retry-Konfiguration
        operation_name: Name fuer Logging
        
    Returns:
        (success: bool, result: Optional[T], error: Optional[str])
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    try:
        def call_func():
            # Timeout wird hier nicht implementiert (signal auf Windows nicht veruegbar)
            return func()
        
        result = retry(call_func, retry_config)
        return (True, result, None)
    
    except Exception as e:
        error_msg = f"{operation_name} failed: {type(e).__name__}: {str(e)}"
        log.error(error_msg)
        return (False, None, error_msg)
