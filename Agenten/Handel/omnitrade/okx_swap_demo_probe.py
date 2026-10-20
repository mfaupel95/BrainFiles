#!/usr/bin/env python
"""Probe script für omnitrade2 Demo-Verifikation (XPERP InstType).

Testet OKX EEA Demo-Konto auf XPERP-Berechtigung (FUTURES InstType).
Erwartet: 51001 / 50124 wenn keine Erlaubnis für Perpetuals.
"""

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
        "x-simulated-trading": "1",  # 1 = demo, 0 = live
    }
    return hdr

def probe(inst_id: str, ct_val: float):
    print(f"=== OKX XPERP Demo-Probe ===")
    print(f"Instrument: {inst_id}")
    print(f"ctVal: {ct_val}")
    print(f"OKX_BASE: {os.environ.get('OKX_BASE', 'https://www.okx.com')}")

    # 1. Account Config prüfen
    print(f"\n--- Test: /account/config ---")
    try:
        pfad = "/api/v5/account/config"
        hdr = sign(pfad, "GET", {})
        req = urllib.request.Request(
            os.environ.get("OKX_BASE", "https://www.okx.com") + pfad,
            headers={**{"User-Agent": "Python/3.11"}, **hdr},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
            if data.get("code") != "0":
                print(f"Account Config: {data.get('msg', 'Fehler')}")
            else:
                pos_mode = data["data"][0].get("posMode")
                print(f"posMode: {pos_mode}")
    except Exception as e:
        print(f"Account Config Fehler: {e}")

    # 2. Set Leverage (Test auf Perpetual-Berechtigung)
    print(f"\n--- Test: set-leverage (XPERP) ---")
    try:
        pfad = "/api/v5/account/set-leverage"
        daten = {"instId": inst_id, "lever": "3", "mgnMode": "isolated"}
        hdr = sign(pfad, "POST", daten)
        req = urllib.request.Request(
            os.environ.get("OKX_BASE", "https://www.okx.com") + pfad,
            data=json.dumps(daten).encode(),
            headers={**{"User-Agent": "Python/3.11"}, **hdr},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
            if data.get("code") == "0":
                print("SET LEVERAGE OK")
            else:
                print(f"SET LEVERAGE: {data.get('msg', 'Fehler')}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}")

    # 3. Instrument Info (Öffentlich, nicht signiert)
    print(f"\n--- Test: /public/instruments ---")
    try:
        pfad = f"/api/v5/public/instruments?instType=FUTURES&instId={inst_id}"
        req = urllib.request.Request(
            os.environ.get("OKX_BASE", "https://www.okx.com") + pfad,
            headers={"User-Agent": "Python/3.11"},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
            if data.get("code") == "0":
                inst = data["data"][0]
                print(f"InstType: {inst.get('instType')}")
                print(f"ctVal: {inst.get('ctVal')}")
            else:
                print(f"INSTRUMENT: {data.get('msg', 'Fehler')}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}")

    print(f"\n=== Ende ===")

if __name__ == "__main__":
    inst_id = sys.argv[1] if len(sys.argv) > 1 else "BTC-USD_UM_XPERP-310404"
    ct_val = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0001
    probe(inst_id, ct_val)
