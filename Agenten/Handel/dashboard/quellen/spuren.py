# dashboard/quellen/spuren.py
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import spuren_stand as _ss

_HIER = _ss.HIER  # Agenten/Handel/


def _sammle_roh() -> list[dict]:
    try:
        return _ss.sammle()
    except Exception:
        return []


def _status(e: dict) -> str:
    if e.get("erlaubt") is None and e.get("hs") is None:
        return "nicht_konfiguriert"
    alter = e.get("alter")
    hs = e.get("hs") or 0
    if hs > 0 and alter is None:
        return "unbekannt"  # kein Herzschlag-Beleg im Log: nicht gruen anzeigen
    if hs > 0 and alter > hs:
        return "veraltet"
    return "ok"


def get_spuren() -> list[dict]:
    spuren = _sammle_roh()
    for e in spuren:
        e["status"] = _status(e)

    # Fremdrepo-Signale anhaengen
    for sig_pfad in sorted(_HIER.glob("fremdrepos-signal-*.json")):
        try:
            eintraege = json.loads(sig_pfad.read_text(encoding="utf-8"))
            if isinstance(eintraege, list):
                for eintrag in eintraege:
                    if not isinstance(eintrag, dict):
                        continue
                    eintrag.setdefault("status", _status(eintrag))
                    spuren.append(eintrag)
        except Exception:
            pass

    return spuren
