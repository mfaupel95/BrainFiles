"""Kraken-Tageshistorie holen und lokal cachen - dieselbe hole()/laden()-Form
wie kerzen.py (OKX), damit lauf.py beide Quellen per Namen austauschen kann.

kraken.kerzen() liefert bereits bis zu 720 Tageskerzen in einem Abruf (kein
Blaettern wie bei OKX history-candles noetig). Faellt der Abruf leer aus,
arbeitet laden() mit dem Cache weiter - wie kerzen.py.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
if str(HIER.parent / "kraken") not in sys.path:
    sys.path.insert(0, str(HIER.parent / "kraken"))

import kraken  # Agenten/Handel/kraken/kraken.py

CACHE = HIER / "kraken_kerzen"


def hole(paar, tage, cache_dir=CACHE):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    reihen = kraken.kerzen(paar, intervall=1440, anzahl=tage)
    if not reihen:
        # Leerer, aber erfolgreicher Abruf - Cache nicht ueberschreiben.
        return laden(paar, cache_dir)[0]
    (cache_dir / (paar + ".json")).write_text(json.dumps(
        {"geholt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "kerzen": reihen}, ensure_ascii=False), "utf-8")
    return reihen


def laden(paar, cache_dir=CACHE):
    p = Path(cache_dir) / (paar + ".json")
    if not p.exists():
        return [], None
    d = json.loads(p.read_text("utf-8"))
    t = datetime.fromisoformat(d["geholt"])
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    alter = (datetime.now(timezone.utc) - t).total_seconds() / 86400.0
    return d["kerzen"], alter
