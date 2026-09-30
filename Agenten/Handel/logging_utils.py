"""Logging-Utilities: strukturierte Logs, Events, Metriken.

Ersetzt ad-hoc print()/logging in allen Modulen.
"""

import logging
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Callable
from enum import Enum
from functools import wraps

# Global log level (kann zur Laufzeit aendert werden)
_GLOBAL_LOG_LEVEL = logging.INFO


class EventLevel(Enum):
    """Event-Kategorien fuer strukturierte Logs."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    AUDIT = "AUDIT"  # Sicherheits-/Handel-Ereignisse
    METRIC = "METRIC"  # Performance-Metriken


class StructuredLogger:
    """Logger mit strukturierten Events (JSON) statt rohem Text."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.name = name
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Handler einmalig setup (Vorgabe: Datei + Console)."""
        if self.logger.handlers:
            return
        
        # Console-Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def event(
        self,
        level: EventLevel,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        """Strukturiertes Event loggen.
        
        Args:
            level: EventLevel (DEBUG, INFO, WARNING, ERROR, CRITICAL, AUDIT, METRIC)
            action: Kurze Aktion (z.B. "trade_opened", "network_timeout")
            details: Optional Dict mit Details
            **kwargs: Zusaetzliche Felder
        """
        event_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "level": level.value,
            **(details or {}),
            **kwargs
        }
        
        log_level = getattr(logging, level.value, logging.INFO)
        msg = json.dumps(event_data, default=str, ensure_ascii=False)
        self.logger.log(log_level, msg)
    
    def debug(self, msg: str, **kwargs: Any) -> None:
        """Debug-Log mit strukturiertem Event."""
        self.event(EventLevel.DEBUG, msg.replace(" ", "_").lower(), **kwargs)
    
    def info(self, msg: str, **kwargs: Any) -> None:
        """Info-Log."""
        self.event(EventLevel.INFO, msg.replace(" ", "_").lower(), **kwargs)
    
    def warning(self, msg: str, **kwargs: Any) -> None:
        """Warning-Log."""
        self.event(EventLevel.WARNING, msg.replace(" ", "_").lower(), **kwargs)
    
    def error(self, msg: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Error-Log mit optionalem Exception-Trace."""
        if exc_info:
            kwargs["exc_info"] = True
        self.event(EventLevel.ERROR, msg.replace(" ", "_").lower(), **kwargs)
    
    def audit(self, action: str, actor: str, target: str, result: str, **kwargs: Any) -> None:
        """Audit-Log fuer Handel und Sicherheit.
        
        Args:
            action: Aktion (z.B. "position_opened", "freigabe_granted")
            actor: Wer (z.B. "dauerlauf", "user_max")
            target: Was (z.B. "xperp/BTC-USD", "spur_scanner")
            result: Ergebnis (z.B. "success", "rejected")
        """
        self.event(
            EventLevel.AUDIT,
            action,
            actor=actor,
            target=target,
            result=result,
            **kwargs
        )
    
    def metric(self, name: str, value: float, unit: str = "", **kwargs: Any) -> None:
        """Performance-Metrik loggen.
        
        Args:
            name: Metriken-Name (z.B. "cycle_duration_s", "queue_depth")
            value: Wert
            unit: Einheit (optional, fuer Lesbarkeit)
        """
        self.event(
            EventLevel.METRIC,
            name,
            value=value,
            unit=unit,
            **kwargs
        )


def log_call(logger: StructuredLogger, level: EventLevel = EventLevel.DEBUG):
    """Decorator: logge Funktionsaufrufe mit Duration.
    
    Args:
        logger: StructuredLogger-Instanz
        level: Log-Level fuer Aufrufe
        
    Usage:
        @log_call(logger)
        def my_function(x):
            return x * 2
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.event(
                    level,
                    f"{func.__name__}_called",
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys()),
                    duration_s=duration,
                    result_type=type(result).__name__
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{func.__name__}_failed",
                    exc_type=type(e).__name__,
                    exc_message=str(e),
                    duration_s=duration,
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


class RateLimitedLogger:
    """Logger mit Rate-Limiting (verhindert Log-Spam)."""
    
    def __init__(self, logger: StructuredLogger, max_per_minute: int = 100):
        self.logger = logger
        self.max_per_minute = max_per_minute
        self._log_times: Dict[str, list] = {}  # action -> [timestamps]
        self._minute = 60.0
    
    def log(self, level: EventLevel, action: str, **kwargs: Any) -> bool:
        """Log mit Rate-Limiting.
        
        Returns:
            True wenn geloggt wurde, False wenn rate-limited
        """
        now = time.time()
        
        if action not in self._log_times:
            self._log_times[action] = []
        
        # Alte Timestamps entfernen (> 1 Minute)
        self._log_times[action] = [
            ts for ts in self._log_times[action]
            if now - ts < self._minute
        ]
        
        # Rate-Limit pruefen
        if len(self._log_times[action]) >= self.max_per_minute:
            return False
        
        self._log_times[action].append(now)
        self.logger.event(level, action, **kwargs)
        return True


# Globale Standard-Logger-Instanzen
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """Hole oder erstelle Logger fuer Module.
    
    Args:
        name: Logger-Name (typisch __name__)
        
    Returns:
        StructuredLogger-Instanz
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, _GLOBAL_LOG_LEVEL)
    return _loggers[name]


def set_global_level(level: int) -> None:
    """Setze globales Log-Level fuer alle Logger."""
    global _GLOBAL_LOG_LEVEL
    _GLOBAL_LOG_LEVEL = level
    for logger in _loggers.values():
        logger.logger.setLevel(level)


# Performance-Kontext-Manager fuer zeitmessungen
class TimerContext:
    """Context-Manager fuer Zeitmessungen.
    
    Usage:
        with TimerContext(logger, "database_query") as timer:
            do_something()
        # Loggt automatisch die Duration
    """
    
    def __init__(self, logger: StructuredLogger, name: str):
        self.logger = logger
        self.name = name
        self.start_time = 0.0
    
    def __enter__(self) -> "TimerContext":
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(
                f"{self.name}_failed",
                duration_s=duration,
                error=str(exc_val),
                exc_info=True
            )
        else:
            self.logger.metric(self.name, duration, unit="s")
