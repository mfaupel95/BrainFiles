"""State-Management: JSON-basiert, mit atomaren Schreibvorgaengen und Locking.

Verwaltet zustand.json, wachen.json, freigabefenster.json etc.
"""

import json
import os
import tempfile
import shutil
import logging
from typing import Any, Dict, Optional, Callable, TypeVar
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    # Windows
    HAS_FCNTL = False

log = logging.getLogger(__name__)

T = TypeVar('T')


class StateManager:
    """Verwaltet JSON-Zustandsdateien mit Locking und Validation."""
    
    def __init__(self, file_path: str, auto_create: bool = True, default_data: Optional[Dict] = None):
        """Initialisiere State-Manager.
        
        Args:
            file_path: Pfad zur JSON-Datei
            auto_create: Erstelle Datei mit default_data wenn nicht existent
            default_data: Default-Dict bei Erstellung
        """
        self.file_path = Path(file_path)
        self.auto_create = auto_create
        self.default_data = default_data or {}
        self._lock_file = None
        
        if auto_create and not self.file_path.exists():
            self._ensure_file()
    
    def _ensure_file(self) -> None:
        """Erstelle Datei mit default_data wenn nicht existent."""
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.write(self.default_data)
    
    @contextmanager
    def _lock(self):
        """Context-Manager fuer Datei-Locking (Unix/Windows kompatibel)."""
        lock_path = str(self.file_path) + ".lock"
        lock_file = None
        try:
            lock_file = open(lock_path, 'w')
            if HAS_FCNTL:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                if lock_file and HAS_FCNTL:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except (AttributeError, IOError, ValueError):
                pass
            try:
                if lock_file:
                    lock_file.close()
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception:
                pass
    
    def read(self) -> Dict[str, Any]:
        """Lese JSON-Datei mit Fehlerbehandlung.
        
        Returns:
            Dict aus JSON oder {} wenn unbrauchbar
        """
        if not self.file_path.exists():
            if self.auto_create:
                self._ensure_file()
                return self.default_data.copy()
            return {}
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                log.warning(f"Unerwarteter Datentyp in {self.file_path}: {type(data).__name__}, erwarte dict")
                return self.default_data.copy()
            
            return data
        
        except json.JSONDecodeError as e:
            log.error(f"JSON-Parse-Fehler in {self.file_path}: {e}")
            return self.default_data.copy()
        except Exception as e:
            log.error(f"Fehler beim Lesen von {self.file_path}: {e}")
            return self.default_data.copy()
    
    def write(self, data: Dict[str, Any], atomic: bool = True) -> bool:
        """Schreibe JSON-Datei (atomar).
        
        Args:
            data: Dict zum Schreiben
            atomic: Nutze temp-file + rename (sicherer)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not isinstance(data, dict):
            log.error(f"write() erwartet dict, erhielt {type(data).__name__}")
            return False
        
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if atomic:
                # Atomare Schreibweise: temp-datei + rename
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    dir=self.file_path.parent,
                    delete=False,
                    encoding='utf-8',
                    suffix='.tmp'
                ) as tmp:
                    json.dump(data, tmp, indent=2, ensure_ascii=False, default=str)
                    tmp_path = tmp.name
                
                shutil.move(tmp_path, self.file_path)
            else:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            return True
        
        except Exception as e:
            log.error(f"Fehler beim Schreiben von {self.file_path}: {e}")
            return False
    
    def update(self, updates: Dict[str, Any]) -> bool:
        """Updaten einzelne Felder (read-modify-write).
        
        Args:
            updates: Dict mit Aenderungen (nested paths unterstutzen z.B. "a.b.c")
            
        Returns:
            True wenn erfolgreich
        """
        with self._lock():
            data = self.read()
            
            for key, value in updates.items():
                if '.' in key:
                    # Nested update (vereinfacht: nur eine Ebene)
                    parts = key.split('.', 1)
                    if parts[0] not in data:
                        data[parts[0]] = {}
                    data[parts[0]][parts[1]] = value
                else:
                    data[key] = value
            
            return self.write(data)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Hole Wert mit default.
        
        Args:
            key: Key (nested mit "a.b.c" unterstutzen)
            default: Default-Wert
            
        Returns:
            Wert oder default
        """
        data = self.read()
        
        if '.' in key:
            parts = key.split('.')
            current = data
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return default
            return current if current is not None else default
        
        return data.get(key, default)
    
    def delete(self) -> bool:
        """Loesche die Datei.
        
        Returns:
            True wenn erfolgreich
        """
        try:
            if self.file_path.exists():
                self.file_path.unlink()
            return True
        except Exception as e:
            log.error(f"Fehler beim Loeschen von {self.file_path}: {e}")
            return False
    
    def add_timestamp(self) -> None:
        """Fuege _updated_at Timestamp hinzu."""
        self.update({
            "_updated_at": datetime.now(timezone.utc).isoformat()
        })
    
    def validate(self, schema: Dict[str, type]) -> bool:
        """Validiere Struktur gegen einfaches Schema.
        
        Args:
            schema: Dict mit {key: expected_type}
            
        Returns:
            True wenn alle Keys vorhanden und vom richtigen Typ
        """
        data = self.read()
        
        for key, expected_type in schema.items():
            if key not in data:
                log.warning(f"Missing key in {self.file_path}: {key}")
                return False
            
            if not isinstance(data[key], expected_type):
                log.warning(
                    f"Type mismatch for {key} in {self.file_path}: "
                    f"expected {expected_type.__name__}, got {type(data[key]).__name__}"
                )
                return False
        
        return True


class CachedStateManager(StateManager):
    """StateManager mit In-Memory-Cache und TTL."""
    
    def __init__(self, file_path: str, cache_ttl_s: float = 30.0, **kwargs):
        """
        Args:
            file_path: Pfad zur JSON-Datei
            cache_ttl_s: Cache-Gueltigkeit in Sekunden
            **kwargs: Weitere Args fuer StateManager
        """
        super().__init__(file_path, **kwargs)
        self.cache_ttl_s = cache_ttl_s
        self._cache = None
        self._cache_time = 0.0
    
    def read(self) -> Dict[str, Any]:
        """Lese mit Cache."""
        now = datetime.now(timezone.utc).timestamp()
        
        if self._cache is not None and (now - self._cache_time) < self.cache_ttl_s:
            return self._cache.copy()
        
        data = super().read()
        self._cache = data.copy()
        self._cache_time = now
        
        return data
    
    def write(self, data: Dict[str, Any], atomic: bool = True) -> bool:
        """Schreibe und invalidiere Cache."""
        result = super().write(data, atomic)
        if result:
            self._cache = data.copy()
            self._cache_time = datetime.now(timezone.utc).timestamp()
        return result
    
    def invalidate_cache(self) -> None:
        """Loeschen Cache."""
        self._cache = None
        self._cache_time = 0.0


# Convenience-Funktionen fuer haeufige Operationen
def load_json(file_path: str) -> Dict[str, Any]:
    """Schnelles Laden einer JSON-Datei."""
    manager = StateManager(file_path, auto_create=False)
    return manager.read()


def save_json(file_path: str, data: Dict[str, Any]) -> bool:
    """Schnelles Speichern einer JSON-Datei."""
    manager = StateManager(file_path)
    return manager.write(data)


def merge_states(*managers: StateManager) -> Dict[str, Any]:
    """Merge mehrerer State-Manager zu einem Dict."""
    result = {}
    for manager in managers:
        result.update(manager.read())
    return result
