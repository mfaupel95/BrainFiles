#!/usr/bin/env python
"""OKX-Gegenprobe: Host x Demo-Kopf x Instrumentklasse in EINEM Lauf.

Beantwortet die drei Fragen, die jede Demo-Verifikation kostet:
  1. Nimmt dieser Schluessel diesen Host? (50101 = meist fehlender Demo-Kopf)
  2. Welche Instrumentklasse darf das Konto handeln? (set-leverage ist KEIN Beweis)
  3. Fuellt eine Order dort ueberhaupt, und ist das Orderbuch brauchbar?

Standard ist REIN LESEND. Eine Order wird nur mit --order gesetzt und nur auf
Instrumente, deren Book gesund aussieht. Nichts wird storniert oder verkauft.

Aufruf:
  python okx-demo-matrix.py
  python okx-demo-matrix.py --order BTC-USD_UM-261030 0.1

Schluessel aus der Umgebung: OKX_DEMO_API_KEY / _SECRET / _PASSPHRASE
(Rueckfall: OKX_API_KEY / OKX_API_SECRET / OKX_PASSPHRASE).
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

K = os.environ.get("OKX_DEMO_API_KEY") or os.environ.get("OKX_API_KEY", "")
S = os.environ.get("OKX_DEMO_API_SECRET") or os.environ.get("OKX_API_SECRET", "")
P = os.environ.get("OKX_DEMO_API_PASSPHRASE") or os.environ.get("OKX_PASSPHRASE", "")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36"


def ruf(host, pfad, methode="GET", body=None, demo=True):
    """Signierter Aufruf. demo=True setzt den Kopf, ohne den OKX 50101 gibt."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    b = json.dumps(body) if body else ""
    sig = base64.b64encode(
        hmac.new(S.encode(), (ts + methode + pfad + b).encode(), hashlib.sha256).digest()
    ).decode()
    hdr = {
        "OK-ACCESS-KEY": K,
        "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": P,
        "Content-Type": "application/json",
        "User-Agent": UA,
    }
    if demo:
        hdr["x-simulated-trading"] = "1"
    req = urllib.request.Request(
        host + pfad, data=(b.encode() if b else None), headers=hdr, method=methode
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"code": "HTTP%d" % e.code, "msg": ""}


def kurz(d):
    """OKX-Antwort auf eine Zeile: code + sCode + Text."""
    if not isinstance(d, dict):
        return str(d)[:80]
    daten = d.get("data") or [{}]
    e = daten[0] if isinstance(daten[0], dict) else {}
    return "code=%s sCode=%s %s" % (
        d.get("code"), e.get("sCode"), (e.get("sMsg") or d.get("msg") or "")[:70]
    )


def main():
    if not all([K, S, P]):
        print("Keine Demo-Zugangsdaten in der Umgebung (OKX_DEMO_API_*).")
        return 2

    print("=== 1) Host x Demo-Kopf (signiertes /account/balance) ===")
    for host in ("https://eea.okx.com", "https://www.okx.com"):
        for demo in (True, False):
            r = ruf(host, "/api/v5/account/balance", demo=demo)
            ok = r.get("code") == "0"
            print("   %-22s kopf=%-5s %s" % (host, demo, "OK" if ok else kurz(r)))

    print("\n=== 2) Konto ===")
    c = ruf("https://eea.okx.com", "/api/v5/account/config")
    if c.get("code") == "0":
        d = c["data"][0]
        print("   acctLv=%s perm=%s posMode=%s" % (d.get("acctLv"), d.get("perm"), d.get("posMode")))
    b = ruf("https://eea.okx.com", "/api/v5/account/balance")
    if b.get("code") == "0":
        print("   totalEq=%s" % b["data"][0].get("totalEq"))
        for x in b["data"][0]["details"][:6]:
            print("     %-6s eq=%-18s availEq=%s" % (x.get("ccy"), x.get("eq"), x.get("availEq")))

    print("\n=== 3) set-leverage je Instrument (NICHT ausreichend als Handelsbeweis) ===")
    kandidaten = ["BTC-USD_UM-261030", "BTC-USDT-SWAP", "BTC-USD-SWAP", "BTC-USD_UM_XPERP-310404"]
    for inst in kandidaten:
        r = ruf("https://eea.okx.com", "/api/v5/account/set-leverage", "POST",
                {"instId": inst, "lever": "3", "mgnMode": "isolated"})
        print("   %-24s %s" % (inst, "OK" if r.get("code") == "0" else kurz(r)))

    print("\n=== 4) Orderbuch — entscheidet, ob ein VERKAUF je fuellen kann ===")
    for inst in kandidaten:
        bk = ruf("https://eea.okx.com", "/api/v5/market/books?instId=%s&sz=5" % inst, demo=False)
        if bk.get("code") != "0" or not bk.get("data"):
            print("   %-24s kein Book (%s)" % (inst, kurz(bk)))
            continue
        d = bk["data"][0]
        bid = float(d["bids"][0][0]) if d.get("bids") else 0.0
        ask = float(d["asks"][0][0]) if d.get("asks") else 0.0
        spanne = (ask / bid) if bid else 0.0
        urteil = "GESUND" if 0.9 < spanne < 1.1 else "KAPUTT (Kaeufe fuellen, Verkaeufe haengen)"
        print("   %-24s bid=%-12s ask=%-12s %s" % (inst, bid, ask, urteil))

    if "--order" in sys.argv:
        i = sys.argv.index("--order")
        inst = sys.argv[i + 1]
        sz = sys.argv[i + 2] if len(sys.argv) > i + 2 else "0.1"
        print("\n=== 5) Order (Kauf, market, isolated) %s sz=%s ===" % (inst, sz))
        # posMode=net_mode -> KEIN posSide im Koerper
        r = ruf("https://eea.okx.com", "/api/v5/trade/order", "POST",
                {"instId": inst, "tdMode": "isolated", "side": "buy",
                 "ordType": "market", "sz": sz})
        print("   %s" % kurz(r))
        p = ruf("https://eea.okx.com", "/api/v5/account/positions?instType=FUTURES")
        for x in p.get("data") or []:
            if x.get("instId") == inst:
                print("   Position pos=%s avgPx=%s margin=%s lever=%s upl=%s"
                      % (x.get("pos"), x.get("avgPx"), x.get("margin"), x.get("lever"), x.get("upl")))
        print("   HINWEIS: Verkauf kann auf einem kaputten Demo-Book haengen —")
        print("   dann Schutz-Stop setzen (order-algo/conditional, reduceOnly=true).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
