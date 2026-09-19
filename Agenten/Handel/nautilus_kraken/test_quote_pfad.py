"""Kurzer Quote-Pfad-Test fuer den Kraken-Node (Spot BTC/EUR).

Startet den Node, sammelt 15 s Quotes, zeigt die Anzahl. Analog zu
test_gui_quote_pfad.py der OKX-Spur.
"""
import os
import sys
import threading
import time

os.environ.setdefault("KRAKEN_PRODUKT", "spot")
os.environ.setdefault("KRAKEN_SYMBOL", "BTC/EUR")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_kraken_paper_node as node_mod  # noqa: E402

from nautilus_trader.config import LoggingConfig, TradingNodeConfig  # noqa: E402
from nautilus_trader.trading.config import StrategyConfig  # noqa: E402


class Sammler(node_mod.DemoQuoteStrategy):
    def __init__(self, config, symbol):
        super().__init__(config, symbol)
        self.quotes = []

    def on_quote_tick(self, tick):
        self.quotes.append(tick)


def main():
    data_clients, exec_clients = node_mod.load_client_configs("BTC/EUR")
    config = TradingNodeConfig(
        environment="sandbox",
        logging=LoggingConfig(log_level="ERROR"),
        data_clients=data_clients,
        exec_clients=exec_clients,
    )
    node = node_mod.KrakenPaperNode(config=config)
    strat = Sammler(StrategyConfig(strategy_id="kraken-quote-test"), "BTC/EUR")
    node.trader.add_strategy(strat)
    node.build()

    fehler = []

    def lauf():
        try:
            node.run()
        except Exception as exc:  # noqa: BLE001
            fehler.append(exc)

    t = threading.Thread(target=lauf, daemon=True, name="kraken-quote-test")
    t.start()
    time.sleep(15)
    try:
        node.stop()
    except Exception:  # noqa: BLE001
        pass
    time.sleep(1)
    if fehler:
        print("FEHLER:", repr(fehler[0]))
        return 1
    print("Quotes in 15 s:", len(strat.quotes))
    if strat.quotes:
        q = strat.quotes[-1]
        print("Letzte Quote bid=%s ask=%s" % (q.bid_price, q.ask_price))
        return 0
    print("KEINE Quote angekommen")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
