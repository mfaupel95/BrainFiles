#!/usr/bin/env python
"""OKX Demo Trade Test Script für Omnitrade2."""

import os
import sys
from pathlib import Path
import urllib.request
import urllib.error
import json
import hashlib
import base64
import hmac
from datetime import datetime, timezone

def sign(pfad: str, methode: str, daten: dict) -> dict:
    """House-Signatur (wie scanner/okx.py)"""
    key = os.environ.get("OKX_DEMO_API_KEY", os.environ.get("OKX_API_KEY", ""))
    secret = os.environ.get("OKX_DEMO_API_SECRET", os.environ.get("OKX_API_SECRET", ""))
    passphrase = os.environ.get("OKX_DEMO_API_PASSPHRASE", os.environ.get("OKX_PASSPHRASE", ""))

    if not all([key, secret, passphrase]):
        raise ValueError("OKX credentials fehlen")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    body_str = json.dumps(daten) if daten else ""
    pre = ts + methode + pfad + body_str

    sig = base64.b64encode(
        hmac.new(secret.encode(), pre.encode(), hashlib.sha256).digest()
    ).decode()

    hdr = {
        "OK-ACCESS-KEY": key,
        "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
        "x-simulated-trading": "1",  # 1 = demo
    }
    return hdr

def trade(inst_id: str, size: int, side: str = "buy", pos_side: str = "long"):
    print(f"=== OKX Demo Trade Test ===")
    print(f"Order: {side.upper()} {size} Kontrakte von {inst_id}")
    print(f"OKX_BASE: {os.environ.get('OKX_BASE', 'https://www.okx.com')}")
    print(f"Mode: DEMO (x-simulated-trading: 1)")

    pfad = "/api/v5/trade/order"
    # posMode ist net_mode -> KEIN posSide mitschicken (sonst Fehler)
    daten = {
        "instId": inst_id,
        "tdMode": "isolated",
        "side": side,
        "ordType": "market",
        "sz": str(size),
    }
    hdr = sign(pfad, "POST", daten)

    try:
        req = urllib.request.Request(
            os.environ.get("OKX_BASE", "https://www.okx.com") + pfad,
            data=json.dumps(daten).encode(),
            headers={**{"User-Agent": "Python/3.11"}, **hdr},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode())
            if data.get("code") == "0":
                print(f"\nORDER ERFAHRT")
                print(f"ordId: {data['data'][0]['ordId']}")
                print(f"sz: {data['data'][0]['sz']}")
                print(f"px: {data['data'][0].get('px', 'market')}")
            else:
                print(f"\nORDER ABGELEHNT")
                print(f"code: {data.get('code')}")
                print(f"msg: {data.get('msg')}")
    except urllib.error.HTTPError as e:
        print(f"\nHTTP ERROR {e.code}")
        print(e.read().decode())

if __name__ == "__main__":
    inst_id = sys.argv[1] if len(sys.argv) > 1 else "BTC-USD_UM-261030"
    size = sys.argv[2] if len(sys.argv) > 2 else "0.1"
    trade(inst_id, size)
