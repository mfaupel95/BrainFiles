"""OKX-Tageshistorie holen und lokal cachen.

scanner/okx.kerzen() gibt nur die letzten 300 Kerzen. Der Backtest braucht
mehr - /api/v5/market/history-candles laesst sich ueber den Parameter `after`
(Millisekunden-Zeitstempel) rueckwaerts durchblaettern. OKX liefert je Seite
bis 100 Kerzen, neueste zuerst. Wir blaettern, bis genug zusammen sind oder
eine leere Seite kommt.

Faellt der Abruf aus, arbeitet laden() mit dem Cache weiter und meldet sein
Alter. Kein Cache -> ([], None), der Aufrufer bricht dann ab.
"""

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import okx  # scanner/okx.py ueber sys.path

CACHE = Path(__file__).resolve().parent / "kerzen"
_BASIS = "https://www.okx.com"
_SEITE = 100


def _seite(inst, bar, after_ms):
    q = {"instId": inst, "bar": bar, "limit": _SEITE}
    if after_ms is not None:
        q["after"] = str(after_ms)
    url = _BASIS + "/api/v5/market/history-candles?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers=okx.HEADERS, method="GET")
    fehler = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=20) as a:
                d = json.loads(a.read().decode())
            break
        except Exception as e:  # noqa: BLE001
            fehler += 1
            if fehler >= okx.MAX_FEHLER:
                raise
            time.sleep(1.5 * fehler)
    if d.get("code") not in ("0", 0):
        raise okx.OKXFehler("OKX %s: %s" % (d.get("code"), d.get("msg")))
    return d.get("data", [])


def hole(inst, tage, cache_dir=CACHE):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    roh = []
    after = None
    while len(roh) < tage:
        seite = _seite(inst, "1D", after)
        if not seite:
            break
        roh.extend(seite)
        after = int(seite[-1][0])  # aeltester Zeitstempel dieser Seite
        time.sleep(0.2)
    reihen = [[int(r[0])] + [float(x) for x in r[1:6]] for r in roh]
    reihen.sort(key=lambda r: r[0])
    reihen = reihen[-tage:]
    if not reihen:
        # Abruf lieferte nichts (leere, aber erfolgreiche Antwort) - einen
        # vorhandenen Cache nie mit einem leeren Ergebnis ueberschreiben.
        # Spec: Abruf faellt aus -> Cache behalten. Rueckgabe: was der Cache
        # schon hat (moeglicherweise []).
        return laden(inst, cache_dir)[0]
    (cache_dir / (inst + ".json")).write_text(json.dumps(
        {"geholt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "kerzen": reihen}, ensure_ascii=False), "utf-8")
    return reihen


def laden(inst, cache_dir=CACHE):
    p = Path(cache_dir) / (inst + ".json")
    if not p.exists():
        return [], None
    d = json.loads(p.read_text("utf-8"))
    t = datetime.fromisoformat(d["geholt"])
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    alter = (datetime.now(timezone.utc) - t).total_seconds() / 86400.0
    return d["kerzen"], alter
