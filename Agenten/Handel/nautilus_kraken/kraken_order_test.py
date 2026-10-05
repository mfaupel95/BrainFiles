"""Bounded Kraken SPOT order smoke test. NICHT MEHR VERDRAHTEN.

WARUM DIESE DATEI TOT IST (T-064, Entscheidung Max 24.09.2026)
------------------------------------------------------------
Der Weg hier ist der Nautilus-Exec-Client. Er verlangt einen WebSocket-Token
und bekommt ihn nicht: `Failed to get WebSocket token: API error:
EGeneral:Permission denied` (gemessen 24.09.2026 18:49 UTC, siehe
logs/kraken-orders-20260924T184919894096Z.jsonl -> success: false,
entered: false). Ueber REST arbeitet derselbe Schluessel einwandfrei.

ENTSCHEIDUNG Max 24.09.2026: REST bleibt, dieser Exec-Client wird
aufgegeben, und der Kraken-Schluessel wird NICHT um WebSockets-Rechte
erweitert. Der lebende Weg ist `kraken_rest.py` (REST, am Adapter vorbei),
mit dem Live-Zweig in `handeln.py`.

Die Datei bleibt als BELEG stehen (der gemessene Fehler ist der Nachweis der
Entscheidung) und damit niemand den toten Weg neu verdrahtet. Jeder Aufruf
bricht sofort ab und sagt, welcher Weg gilt.

Bisheriger Zweck (historisisch): read-only Preflight (Kontostand + offene
Positionen, keine Order); `--execute` erlaubte EINEN winzigen Round-Trip.

Keys: las KRAKEN_API_KEY/KRAKEN_API_SECRET aus HKCU\\Environment.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
import winreg

from nautilus_trader.adapters.kraken import KRAKEN
from nautilus_trader.adapters.kraken.config import KrakenDataClientConfig
from nautilus_trader.adapters.kraken.config import KrakenExecClientConfig
from nautilus_trader.adapters.kraken.factories import KrakenLiveDataClientFactory
from nautilus_trader.adapters.kraken.factories import KrakenLiveExecClientFactory
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.core.nautilus_pyo3 import KrakenEnvironment
from nautilus_trader.core.nautilus_pyo3 import KrakenProductType
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.config import StrategyConfig
from nautilus_trader.trading.strategy import Strategy

IID = InstrumentId.from_str("BTC/EUR.KRAKEN")
ROOT = Path(__file__).resolve().parent
CAP_EUR = Decimal("5")


def _hkcue(name):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        return winreg.QueryValueEx(key, name)[0]


def load_keys():
    api_key = _hkcue("KRAKEN_SPOT_API_KEY")
    api_secret = _hkcue("KRAKEN_SPOT_API_SECRET")
    if not (api_key and api_secret):
        raise SystemExit("KRAKEN_SPOT_API_KEY/SECRET fehlen in HKCU\\Environment")
    return api_key, api_secret


class KrakenOrderNode(TradingNode):
    def build(self):
        self.ConfigureDataFactory()
        self.ConfigureExecFactory()
        super().build()

    def ConfigureDataFactory(self):
        if KRAKEN not in self._builder._data_factories:
            self._builder.add_data_client_factory(KRAKEN, KrakenLiveDataClientFactory)

    def ConfigureExecFactory(self):
        if KRAKEN not in self._builder._exec_factories:
            self._builder.add_exec_client_factory(KRAKEN, KrakenLiveExecClientFactory)


class RoundTrip(Strategy):
    def __init__(self, record, cap, execute):
        super().__init__(StrategyConfig(strategy_id="kraken-spot-smoke"))
        self.record = record
        self.cap = cap
        self.execute = execute
        self.entry = self.exit_order = None
        self.entered = self.closed = self.failed = False
        self.quantity = None
        self.instrument = None

    def on_start(self):
        self.instrument = self.cache.instrument(IID)
        if self.instrument is None:
            self.failed = True
            self.record("failure", reason="instrument missing")
            return
        self.subscribe_quote_ticks(IID)
        if not self.execute:
            self.record("preflight", note="verbunden, keine Order (--execute fehlt)")

    def on_quote_tick(self, tick):
        if not self.execute or self.entry is not None or self.failed:
            return
        # Winzige Menge: ~1 EUR, gedeckelt auf CAP_EUR, nie unter min_quantity.
        ask = tick.ask_price.as_decimal()
        menge = (Decimal("1") / ask).quantize(Decimal("0.00000001"))
        if menge * ask > self.cap:
            menge = (self.cap / ask).quantize(Decimal("0.00000001"))
        if self.instrument.min_quantity is not None and menge < self.instrument.min_quantity.as_decimal():
            menge = self.instrument.min_quantity.as_decimal()
        self.quantity = menge
        self.entry = self.order_factory.market(
            IID, OrderSide.BUY, self.quantity,
            client_order_id=self._new_id())
        self.record("entry_submitted", quantity=str(self.quantity),
                    notional=str(menge * ask))
        self.submit_order(self.entry)

    def _new_id(self):
        from uuid import uuid4
        from nautilus_trader.model.identifiers import ClientOrderId
        return ClientOrderId(uuid4().hex)

    def close_test(self):
        if not self.entered or self.closed or self.exit_order is not None:
            return
        self.exit_order = self.order_factory.market(
            IID, OrderSide.SELL, self.quantity, reduce_only=True,
            client_order_id=self._new_id())
        self.record("close_submitted", client_id=str(self.exit_order.client_order_id))
        self.submit_order(self.exit_order)

    def on_order_filled(self, event):
        self.record("fill", client_id=str(event.client_order_id),
                    venue_id=str(event.venue_order_id),
                    quantity=str(event.last_qty), price=str(event.last_px))
        if self.entry and event.client_order_id == self.entry.client_order_id:
            self.entered = True
            self.close_test()
        elif self.exit_order and event.client_order_id == self.exit_order.client_order_id:
            self.closed = True

    def on_order_rejected(self, event):
        self.record("rejected", client_id=str(event.client_order_id),
                    reason=str(event.reason))
        self.failed = True
        self.close_test()

    def on_order_denied(self, event):
        self.record("denied", client_id=str(event.client_order_id),
                    reason=str(event.reason))
        self.failed = True
        self.close_test()

    def on_stop(self):
        self.unsubscribe_quote_ticks(IID)


def main():
    parser = argparse.ArgumentParser(
        description="TOT seit 24.09.2026 (T-064): der Nautilus-Exec-Client "
                    "bekommt keinen WebSocket-Token. Es gilt der REST-Weg "
                    "ueber kraken_rest.py.")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    # T-064: der Weg ist aufgegeben. Wer ihn startet, soll die Meldung lesen
    # und den lebenden Weg nehmen - nicht 90 Sekunden auf einen Token warten,
    # den es nicht gibt.
    sys.stderr.write(
        "ABGEBROCHEN (T-064): dieser Weg nutzt den Nautilus-Exec-Client, der "
        "seit 24.09.2026 'Failed to get WebSocket token: EGeneral:Permission "
        "denied' liefert. Entscheidung Max: REST bleibt, der Schluessel wird "
        "NICHT um WebSockets-Rechte erweitert.\n"
        "Gilt: kraken_rest.py (REST, am Adapter vorbei) + der Live-Zweig in "
        "handeln.py. Fuer den Orderweg-Nachweis: futures_probe.py bzw. "
        "handeln.py --vorschau.\n")
    return 3

    api_key, api_secret = load_keys()
    market_data = {
        "instrument_provider": InstrumentProviderConfig(
            load_ids=frozenset({IID})),
        "environment": KrakenEnvironment.LIVE,
        "product_types": (KrakenProductType.SPOT,),
    }
    data_clients = {KRAKEN: KrakenDataClientConfig(
        **market_data, update_instruments_interval_mins=60)}
    exec_clients = {KRAKEN: KrakenExecClientConfig(
        **market_data, api_key=api_key, api_secret=api_secret)}

    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    evidence = logs / ("kraken-orders-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".jsonl")

    def record(event, **fields):
        row = {"time": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
        with evidence.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(json.dumps(row), flush=True)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    node = KrakenOrderNode(TradingNodeConfig(
        environment="sandbox",
        logging=LoggingConfig(log_level="ERROR"),
        data_clients=data_clients, exec_clients=exec_clients,
        timeout_post_stop=1.0), loop=loop)
    strategy = RoundTrip(record, CAP_EUR, args.execute)
    node.trader.add_strategy(strategy)
    node.build()

    async def monitor():
        if not args.execute:
            # Preflight: warten bis verbunden (Exec-Client authentifiziert,
            # Konto geladen), dann stoppen - keine Order.
            for _ in range(60):
                await asyncio.sleep(1)
                if strategy.instrument is not None:
                    break
            node.stop()
            return
        for _ in range(90):
            await asyncio.sleep(1)
            if strategy.closed or (strategy.failed and not strategy.entered):
                break
        if strategy.entered and not strategy.closed:
            record("timeout_cleanup")
            strategy.close_test()
            for _ in range(20):
                await asyncio.sleep(1)
                if strategy.closed:
                    break
        node.stop()

    loop.create_task(monitor())
    try:
        node.run()
    finally:
        node.dispose()

    ok = (strategy.entered and strategy.closed and not strategy.failed)
    record("result", success=ok, entered=strategy.entered,
           closed=strategy.closed, failed=strategy.failed)
    print("EVIDENCE", evidence, flush=True)
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
