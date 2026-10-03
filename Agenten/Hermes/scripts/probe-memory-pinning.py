"""Sonde: greift die Verweigerung fuer ungepinnte Memory-Vorschlaege wirklich?
Rein lesend - der Abbruch liegt VOR dem Schreiben (memory_tool.py:306)."""
import json, sys, os
sys.path.insert(0, r"C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\hermes-agent")
os.environ.setdefault("HERMES_HOME", r"C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes")
from tools.memory_tool import apply_memory_pending, destructive_ops, load_on_disk_store

store = load_on_disk_store()  # derselbe Store, den /memory approve baut (Limits aus config.yaml)

# 1) so sah ein Queue-Eintrag aus: replace OHNE matched_entry
alt = {"action": "replace", "target": "memory",
       "content": "NEUER TEXT", "old_text": "BEWAEHRT: auto/best-coding"}
print("destructive_ops erkennt:", json.dumps(destructive_ops(alt), ensure_ascii=False))
print("Ergebnis:", json.dumps(apply_memory_pending(alt, store), ensure_ascii=False))

# 2) Batch-Form (so waren 12 der 25 Dateien gebaut)
alt2 = {"action": "batch", "target": "memory", "operations": [
    {"action": "add", "content": "harmloser Zusatz"},
    {"action": "replace", "content": "NEU", "old_text": "STOERUNGEN GETRENNT"}]}
print("Batch-Ergebnis:", json.dumps(apply_memory_pending(alt2, store), ensure_ascii=False))
print("MEMORY.md-Groesse nach den zwei Aufrufen:", os.path.getsize(
    r"C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\memories\MEMORY.md"))