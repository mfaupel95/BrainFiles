"""XPERP-Historie holen und lokal cachen: Universum, Kerzen (1H/4H/1D),
Funding-Historie. Dieselbe hole()/laden()-Form wie kraken_kerzen.py, aber mit
drei Granularitaeten statt einer und einem eigenen Universum-Cache.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
_XPERP = HIER.parent / "xperp"
if str(_XPERP) not in sys.path:
    sys.path.insert(0, str(_XPERP))

import okxf  # Agenten/Handel/xperp/okxf.py  # noqa: E402
import auswahl  # Agenten/Handel/xperp/auswahl.py  # noqa: E402

CACHE = HIER / "xperp_kerzen"
UNIVERSUM_DATEI = "universum.json"


def hole_universum(cache_dir=CACHE):
    """Alle heute gelisteten Kontrakte der drei Familien, gecacht."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    aus = []
    for name, kat in auswahl.KATEGORIEN.items():
        for x in okxf.instrumente(kategorie=kat["code"]):
            aus.append({"instId": x["instId"],
                        "basis": x["instId"].split("-")[0],
                        "kategorie": name})
    (cache_dir / UNIVERSUM_DATEI).write_text(json.dumps(
        {"geholt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "universum": aus}, ensure_ascii=False), "utf-8")
    return aus


def laden_universum(cache_dir=CACHE):
    p = Path(cache_dir) / UNIVERSUM_DATEI
    if not p.exists():
        return []
    return json.loads(p.read_text("utf-8"))["universum"]
