#!/usr/bin/env python3
"""
Test FreqTrade REST API
Nutze: python test-freqtrade-api.py
"""

import httpx
import json
import asyncio
from typing import Optional

class FreqTradeAPI:
    def __init__(self, base_url: str = "http://localhost:8080", jwt_token: Optional[str] = None):
        self.base_url = base_url
        self.jwt_token = jwt_token or ""
        self.headers = {
            "Authorization": f"Bearer {jwt_token}" if jwt_token else "",
            "Content-Type": "application/json"
        }

    async def get_status(self) -> dict:
        """Bot-Status abrufen"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/status",
                headers=self.headers,
                timeout=5.0
            )
            return response.json()

    async def get_trades(self) -> dict:
        """Alle offenen Trades"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/trades",
                headers=self.headers,
                timeout=5.0
            )
            return response.json()

    async def get_profit(self) -> dict:
        """Profit/Loss Übersicht"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/profit",
                headers=self.headers,
                timeout=5.0
            )
            return response.json()

    async def get_performance(self) -> list:
        """Performance pro Pair"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/performance",
                headers=self.headers,
                timeout=5.0
            )
            return response.json()

    async def get_balance(self) -> dict:
        """Wallet-Balance"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/balance",
                headers=self.headers,
                timeout=5.0
            )
            return response.json()

async def main():
    api = FreqTradeAPI()

    print("🤖 FreqTrade API Test\n")
    print("=" * 50)

    try:
        # Status
        print("\n📊 BOT STATUS:")
        status = await api.get_status()
        print(json.dumps(status, indent=2))

        # Trades
        print("\n💹 OPEN TRADES:")
        trades = await api.get_trades()
        print(f"Total: {len(trades)} trades")
        if trades:
            print(json.dumps(trades[:1], indent=2))  # First trade

        # Profit
        print("\n💰 PROFIT/LOSS:")
        profit = await api.get_profit()
        print(json.dumps(profit, indent=2))

        # Performance
        print("\n📈 PERFORMANCE:")
        perf = await api.get_performance()
        print(json.dumps(perf[:3], indent=2))  # Top 3

        # Balance
        print("\n💵 BALANCE:")
        balance = await api.get_balance()
        print(json.dumps(balance, indent=2))

        print("\n" + "=" * 50)
        print("✅ API Test erfolgreich!")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nFreqTrade läuft nicht oder API nicht erreichbar.")
        print("Starten mit: docker run ... oder freqtrade trade ...")

if __name__ == "__main__":
    asyncio.run(main())
