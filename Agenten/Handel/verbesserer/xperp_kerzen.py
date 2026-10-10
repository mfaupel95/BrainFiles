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


def _dateiname(inst, teil):
    return "%s__%s.json" % (inst, teil)


def _alter_tage(geholt):
    t = datetime.fromisoformat(geholt)
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() / 86400.0


def hole(inst, granularitaet, seiten=10, cache_dir=CACHE):
    """Kerzen einer Granularitaet ('1H'/'4H'/'1D') holen und cachen.

    1H/4H blaettern ueber kerzen_lang() (mehr als 300 Kerzen). 1D bleibt bei
    kerzen() mit 300 - das deckt den Bedarf von auswahl.mae_tage().
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    if granularitaet == "1D":
        reihen = okxf.kerzen(inst, "1D", 300)
    else:
        reihen = okxf.kerzen_lang(inst, granularitaet, seiten)
    if not reihen:
        # Leerer, aber erfolgreicher Abruf - Cache nicht ueberschreiben.
        return laden(inst, granularitaet, cache_dir)[0]
    (cache_dir / _dateiname(inst, granularitaet)).write_text(json.dumps(
        {"geholt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "kerzen": reihen}, ensure_ascii=False), "utf-8")
    return reihen


def laden(inst, granularitaet, cache_dir=CACHE):
    p = Path(cache_dir) / _dateiname(inst, granularitaet)
    if not p.exists():
        return [], None
    d = json.loads(p.read_text("utf-8"))
    return d["kerzen"], _alter_tage(d["geholt"])


def hole_funding(inst, seiten=10, cache_dir=CACHE):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    saetze = okxf.funding_historie(inst, seiten=seiten)
    if not saetze:
        return laden_funding(inst, cache_dir)[0]
    (cache_dir / _dateiname(inst, "funding")).write_text(json.dumps(
        {"geholt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "saetze": saetze}, ensure_ascii=False), "utf-8")
    return saetze


def laden_funding(inst, cache_dir=CACHE):
    p = Path(cache_dir) / _dateiname(inst, "funding")
    if not p.exists():
        return [], None
    d = json.loads(p.read_text("utf-8"))
    return d["saetze"], _alter_tage(d["geholt"])
