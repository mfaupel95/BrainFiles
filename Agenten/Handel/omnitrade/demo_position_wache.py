#!/usr/bin/env python
"""Wache: OKX-Demo-Testposition BTC-USD_UM-261030 (2,1 Kontrakte + Schutz-Stop 61000).

Watchdog-Muster: leere Ausgabe = nichts zu melden.
Gemeldet wird nur:
  - Schutz-Stop ist weg, Position aber offen        (kritisch)
  - Position geschlossen / Stop hat ausgeloest      (einmalig, mit PnL)
  - Kurs naeher als NAH_PCT an den Stop             (einmal je Annaeherung)
  - Abfrage scheitert                               (hoechstens 1x je 6 h)

Aufruf: python Agenten/Handel/omnitrade/demo_position_wache.py [--vorschau]
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
CACHE = HIER.parent.parent / "Hermes" / "cache" / "okx-demo-wache.json"

INST = "BTC-USD_UM-261030"
HOST = "https://eea.okx.com"
NAH_PCT = 1.5          # melden, wenn der Kurs so nah am Stop steht
WIEDERHOLUNG_S = 6 * 3600


# ---------------------------------------------------------------- Zugang

def _creds() -> tuple[str, str, str]:
    k = os.environ.get("OKX_DEMO_API_KEY", "")
    s = os.environ.get("OKX_DEMO_API_SECRET", "")
    p = os.environ.get("OKX_DEMO_API_PASSPHRASE", "")
    if not (k and s and p):
        raise RuntimeError("OKX_DEMO_API_* fehlen in der Umgebung")
    return k, s, p


def ruf(pfad: str, methode: str = "GET", body=None) -> dict:
    """Signierter Demo-Aufruf. Der Header x-simulated-trading ist PFLICHT."""
    key, secret, pp = _creds()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    b = json.dumps(body) if body else ""
    sig = base64.b64encode(
        hmac.new(secret.encode(), (ts + methode + pfad + b).encode(), hashlib.sha256).digest()
    ).decode()
    hdr = {
        "OK-ACCESS-KEY": key,
        "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": pp,
        "Content-Type": "application/json",
        "User-Agent": "Python/3.11",
        "x-simulated-trading": "1",
    }
    try:
        req = urllib.request.Request(HOST + pfad, data=(b.encode() if b else None),
                                     headers=hdr, method=methode)
        with urllib.request.urlopen(req, timeout=12) as res:
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return {"code": "HTTP%d" % e.code, "msg": e.read().decode()[:200]}
    except Exception as e:                                   # noqa: BLE001
        return {"code": "NETZ", "msg": str(e)[:200]}


# ---------------------------------------------------------------- Messen

def lage() -> dict:
    """Position, Stop und Kurs als reine Daten - ohne Urteil."""
    p = ruf("/api/v5/account/positions?instType=FUTURES")
    if p.get("code") != "0":
        return {"fehler": "Positionen: %s %s" % (p.get("code"), p.get("msg", ""))}
    pos = 0.0
    upl = 0.0
    avg = ""
    for x in p.get("data") or []:
        if x.get("instId") == INST:
            pos = float(x.get("pos") or 0)
            upl = float(x.get("upl") or 0)
            avg = x.get("avgPx") or ""

    a = ruf("/api/v5/trade/orders-algo-pending?ordType=conditional&instId=%s" % INST)
    if a.get("code") != "0":
        return {"fehler": "Algo-Orders: %s %s" % (a.get("code"), a.get("msg", ""))}
    stops = [x for x in (a.get("data") or [])]
    trigger = None
    geschuetzt = 0.0
    for x in stops:
        if float(x.get("sz") or 0) > 0:
            geschuetzt += float(x.get("sz") or 0)
        if x.get("slTriggerPx"):
            trigger = float(x["slTriggerPx"])

    t = ruf("/api/v5/market/ticker?instId=%s" % INST)
    kurs = None
    if t.get("code") == "0" and t.get("data"):
        try:
            kurs = float(t["data"][0]["last"])
        except (KeyError, ValueError):
            kurs = None

    return {"position": pos, "upl": upl, "avg": avg, "stops": len(stops),
            "geschuetzt": geschuetzt, "trigger": trigger, "kurs": kurs}


def beurteilen(jetzt: dict, alt: dict, zeit: float) -> list[str]:
    """Reine Funktion: welche Meldungen fallen an?"""
    meldungen: list[str] = []

    if jetzt.get("fehler"):
        if zeit - float(alt.get("letzter_fehler", 0)) > WIEDERHOLUNG_S:
            meldungen.append("OKX-Demo nicht abfragbar: %s" % jetzt["fehler"])
        return meldungen

    hat_pos = jetzt["position"] > 0
    hatte_pos = alt.get("position_war_da", False)

    if hat_pos and jetzt["stops"] == 0:
        if zeit - float(alt.get("letzte_schutzmeldung", 0)) > WIEDERHOLUNG_S:
            meldungen.append(
                "WARNUNG: %s offen mit %s Kontrakten, aber KEIN Schutz-Stop mehr"
                % (INST, jetzt["position"])
            )
    elif hat_pos and jetzt.get("geschuetzt", 0.0) + 1e-9 < jetzt["position"]:
        # Ein Stop, der nur einen TEIL deckt, schuetzt den Rest nicht.
        if zeit - float(alt.get("letzte_schutzmeldung", 0)) > WIEDERHOLUNG_S:
            meldungen.append(
                "WARNUNG: %s offen mit %s Kontrakten, Schutz-Stop deckt nur %s"
                % (INST, jetzt["position"], jetzt.get("geschuetzt", 0.0))
            )

    if hatte_pos and not hat_pos:
        meldungen.append(
            "Demo-Position geschlossen: %s ist flach (PnL laut Buch: %.2f USDC)"
            % (INST, jetzt["upl"])
        )

    if hat_pos and jetzt["trigger"] and jetzt["kurs"]:
        abstand = (jetzt["kurs"] - jetzt["trigger"]) / jetzt["trigger"] * 100
        if 0 <= abstand <= NAH_PCT and not alt.get("nahe_gemeldet"):
            meldungen.append(
                "Kurs %.1f ist nur %.2f %% ueber dem Stop %.1f (%s, %.1f Kontrakte)"
                % (jetzt["kurs"], abstand, jetzt["trigger"], INST, jetzt["position"])
            )
        elif abstand > NAH_PCT + 1:
            alt["nahe_gemeldet"] = False
            meldungen = [m for m in meldungen if "ueber dem Stop" not in m]

    return meldungen


# ---------------------------------------------------------------- Stand

def stand_lesen() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def stand_schreiben(d: dict) -> None:
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    import time
    zeit = time.time()
    jetzt = lage()
    alt = stand_lesen()
    meldungen = beurteilen(jetzt, alt, zeit)

    neu = dict(alt)
    if jetzt.get("fehler"):
        neu["letzter_fehler"] = zeit
    else:
        neu["position_war_da"] = jetzt["position"] > 0
        ungedeckt = jetzt["position"] > 0 and (
            jetzt["stops"] == 0 or jetzt.get("geschuetzt", 0.0) + 1e-9 < jetzt["position"]
        )
        if ungedeckt:
            neu["letzte_schutzmeldung"] = zeit
        if jetzt["trigger"] and jetzt["kurs"]:
            abw = (jetzt["kurs"] - jetzt["trigger"]) / jetzt["trigger"] * 100
            if 0 <= abw <= NAH_PCT:
                neu["nahe_gemeldet"] = True
            elif abw > NAH_PCT + 1:
                neu["nahe_gemeldet"] = False
        neu["zuletzt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if "--vorschau" in sys.argv:
        print(json.dumps({"lage": jetzt, "meldungen": meldungen}, indent=2, ensure_ascii=False))
        return 0

    stand_schreiben(neu)
    for m in meldungen:
        print(m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
