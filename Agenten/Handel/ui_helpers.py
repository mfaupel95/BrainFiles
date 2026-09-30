"""UI-Hilfsfunktionen: Formatierung, Styling, Thread-Management.

Extrahiert aus handelszentrale.py zur Verbesserung der Wartbarkeit.
"""

import logging
import threading
from typing import Optional, Callable, Any, Tuple
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def format_currency(value: Optional[float]) -> str:
    """Formatiere Kurs mit intelligenter Dezimalplatzierung.
    
    Args:
        value: Kurs als float oder None
        
    Returns:
        Formatierter String; '-' wenn None
    """
    if value is None:
        return "-"
    
    try:
        if abs(value) < 0.01:
            return f"{value:.8f}".rstrip('0').rstrip('.')
        elif abs(value) < 100:
            return f"{value:.4f}".rstrip('0').rstrip('.')
        else:
            return f"{value:.2f}".rstrip('0').rstrip('.')
    except (TypeError, ValueError) as e:
        log.warning(f"Fehler beim Formatieren von {value}: {e}")
        return str(value)


def format_time_short(timestamp: Optional[str]) -> str:
    """Kurze Zeitanzeige: 'HH:MM' oder 'TT.MM.'.
    
    Args:
        timestamp: ISO-Zeitstempel oder Datum
        
    Returns:
        Formatierter Kurzzeitstring
    """
    if not timestamp:
        return "--:--"
    
    try:
        w = str(timestamp).strip()
        if len(w) >= 16 and w[10] in ("T", " "):
            return w[11:16]
        elif len(w) >= 10 and w[4] == "-":
            return f"{w[8:10]}.{w[5:7]}."
    except (IndexError, TypeError) as e:
        log.debug(f"Fehler beim Parsen von Zeitstempel '{timestamp}': {e}")
    
    return "--:--"


def safe_thread_operation(
    func: Callable[..., Any],
    args: Tuple[Any, ...] = (),
    daemon: bool = True,
    name: Optional[str] = None
) -> threading.Thread:
    """Starte Thread mit Fehlerbehandlung.
    
    Args:
        func: Zielfunktion
        args: Argumente fuer Zielfunktion
        daemon: Daemon-Modus (Vorgabe True)
        name: Optionaler Thread-Name
        
    Returns:
        Gestarteter Thread
    """
    def wrapper() -> None:
        try:
            func(*args)
        except Exception as e:
            log.exception(f"Thread-Fehler in {func.__name__}: {e}")
    
    thread = threading.Thread(
        target=wrapper,
        daemon=daemon,
        name=name or f"ui-worker-{func.__name__}"
    )
    thread.start()
    return thread


def safe_queue_get(q: Any, timeout: float = 0.1) -> Optional[Any]:
    """Sichere Queue-Operation mit Fehlerbehandlung.
    
    Args:
        q: queue.Queue-Instanz
        timeout: Timeout in Sekunden
        
    Returns:
        Daten oder None bei Timeout/Fehler
    """
    try:
        import queue as queue_module
        return q.get_nowait() if timeout == 0 else q.get(timeout=timeout)
    except queue_module.Empty:
        return None
    except Exception as e:
        log.error(f"Fehler beim Queue-Abruf: {e}")
        return None


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Begrenzen Wert auf Bereich.
    
    Args:
        value: Wert
        min_val: Minimum (Vorgabe 0)
        max_val: Maximum (Vorgabe 1)
        
    Returns:
        Begrenzter Wert
    """
    return max(min_val, min(max_val, value))


def elapsed_minutes(dt_past: datetime) -> float:
    """Minuten seit gegebener Zeit.
    
    Args:
        dt_past: Vergangenheitspunkt
        
    Returns:
        Minuten als Float
    """
    if dt_past is None:
        return float('inf')
    
    now = datetime.now(timezone.utc) if dt_past.tzinfo else datetime.now()
    try:
        return (now - dt_past).total_seconds() / 60.0
    except (TypeError, AttributeError) as e:
        log.error(f"Fehler bei Zeitberechnung: {e}")
        return float('inf')
