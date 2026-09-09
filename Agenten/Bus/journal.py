"""Der einzige Ort der Wahrheit: Agenten/Bus/journal/JJJJ-MM-TT.jsonl.

Alles im Bus schreibt und liest ueber dieses Modul. Es kennt kein Netz und
keinen Melder - damit ein Erzeuger es auch dann benutzen kann, wenn der Bus
tot ist. Angehaengt wird mit fsync, weil die Spec verlangt, dass die Zeile auf
Platte steht, bevor irgendjemand sie weitergibt.
"""

import json
import os
import uuid
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HIER, "journal")


def neu(wer, was, code=None, dauer_s=None, text="", log=None):
    """Baut eine Ereigniszeile. Felder wie in der Spec, immer dieselben acht."""
    return {
        "id": uuid.uuid4().hex,
        "zeit": datetime.now().astimezone().isoformat(timespec="seconds"),
        "wer": wer,
        "was": was,
        "code": code,
        "dauer_s": dauer_s,
        "text": text,
        "log": log,
    }


def pfad(zeit=None, wurzel=None):
    z = zeit or datetime.now()
    return os.path.join(wurzel or JOURNAL, z.strftime("%Y-%m-%d") + ".jsonl")


def anhaengen(ereignis, wurzel=None):
    """Haengt eine Zeile an und erzwingt sie auf Platte. Gibt den Pfad zurueck."""
    p = pfad(wurzel=wurzel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(ereignis, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return p


def lesen(tag=None, wurzel=None):
    """Liest einen Tag. Kaputte Zeilen werden uebersprungen, nicht gemeldet -
    eine halbe Zeile nach einem Absturz darf die guten nicht mitreissen."""
    p = pfad(zeit=tag, wurzel=wurzel)
    if not os.path.exists(p):
        return []
    zeilen = []
    with open(p, encoding="utf-8-sig") as f:
        for z in f:
            z = z.strip()
            if not z:
                continue
            try:
                zeilen.append(json.loads(z))
            except json.JSONDecodeError:
                continue
    return zeilen
