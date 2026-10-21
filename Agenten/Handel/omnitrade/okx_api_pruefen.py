#!/usr/bin/env python
"""OKX API-Konfiguration prüfen (nur lesend)."""

import os
import json
import urllib.request
import urllib.error
import hashlib
import base64
import hmac
from datetime import datetime, timezone

def test_signatures():
    """Prüft ob Signatur-Format stimmt."""
    api_key = os.environ.get("OKX_DEMO_API_KEY", "")
    api_secret = os.environ.get("OKX_DEMO_API_SECRET", "")
    passphrase = os.environ.get("OKX_DEMO_API_PASSPHRASE", "")

    print("=== OKX Demo API Prüfung ===")
    print(f"API_KEY (vor): {'OK' if api_key else 'FEHLT'}")
    print(f"SECRET (vor): {'OK' if api_secret else 'FEHLT'}")
    print(f"PASSPHRASE (vor): {'OK' if passphrase else 'FEHLT'}")

    if not all([api_key, api_secret, passphrase]):
        print("\n❌ API Credentials unvollständig")
        print("OKX_API_DEMO_* im ENV prüfen")
        return

    # Test 1: Öffentlicher Endpunkt (ohne Signatur)
    print(f"\n--- Test 1: Public Time (ohne Signatur) ---")
    try:
        req = urllib.request.Request(
            "https://eea.okx.com/api/v5/public/time",
            headers={"User-Agent": "Python/3.11"},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
            if data.get("code") == "0":
                print("✅ Public Endpoint OK")
            else:
                print(f"❌ Public Endpoint: {data.get('msg')}")
    except Exception as e:
        print(f"❌ Public Endpoint: {e}")

    # Test 2: Signierter Endpunkt (Balance)
    print(f"\n--- Test 2: Signierter Endpunkt (Balance) ---")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    pfad = "/api/v5/account/balance"
    pre = ts + "GET" + pfad + ""
    sig = base64.b64encode(
        hmac.new(api_secret.encode(), pre.encode(), hashlib.sha256).digest()
    ).decode()

    hdr = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
        "User-Agent": "Python/3.11",
        "x-simulated-trading": "1",  # PFLICHT: Demo-Keys werden sonst mit 50101 abgewiesen
    }
    try:
        req = urllib.request.Request(
            "https://eea.okx.com" + pfad,
            headers=hdr,
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
            if data.get("code") == "0":
                print("✅ Signierter Endpunkt OK")
                print(f"Guthaben: {data['data'][0]['details'][0].get('availEq')} {data['data'][0]['details'][0].get('ccy')}")
            else:
                print(f"❌ Signierter Endpunkt: code={data.get('code')} msg={data.get('msg')}")
    except urllib.error.HTTPError as e:
        print(f"❌ Signierter Endpunkt: HTTP {e.code} {e.read().decode()[:100]}")

if __name__ == "__main__":
    test_signatures()
