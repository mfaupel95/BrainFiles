"""
Kraken-Paper-Trading-Node fuer die lokale NautilusTrader-Installation (v1.231).

Zwei Produkttypen, ein Kern:
  - SPOT   (BTC/EUR, kein Hebel, EUR-Waehrung)  -> KrakenEnvironment.LIVE
  - FUTURES(PF_XBTUSD Perpetual, Hebel, USD)    -> KrakenEnvironment.DEMO
            (Kraken-Demo gibt es NUR fuer Futures, nicht fuer Spot)

Der Node registriert die Kraken-Factories am TradingNode und subskribiert
Quotes. REINER PAPIER-/QUOTEN-BETRIEB, keine Broker-Order: die Strategie
fuehrt ein Papierbuch (papierbuch.py: SMA-Kreuzung, simulierte Fills,
PnL in papierbuch.<produkt>.json, liest der Leitstand). Der Data-Client bekommt
bewusst KEINE Zugangsdaten - oeffentliche Quotes brauchen keinen Key.

Produkttyp ueber die Umgebungsvariable KRAKEN_PRODUKT (spot|futures),
Vorgabe spot. Symbol und Waehrung kommen aus wachen.json der Spur.

Start:
    set KRAKEN_PRODUKT=spot|futures
    python run_kraken_paper_node.py
    (Abbruch mit Ctrl+C)
"""

import asyncio
import json
import os
from pathlib import Path

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
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.config import StrategyConfig
from nautilus_trader.trading.strategy import Strategy

from papierbuch import Papierbuch, sperren


# --- Produkttyp-Auswahl ------------------------------------------------------

def produkt_typ() -> KrakenProductType:
    wahl = os.environ.get("KRAKEN_PRODUKT", "spot").strip().lower()
    if wahl in ("futures", "future", "perpetual", "pf"):
        return KrakenProductType.FUTURES
    return KrakenProductType.SPOT


def produkt_name() -> str:
    return "futures" if produkt_typ() == KrakenProductType.FUTURES else "spot"


# --- Demo-Datastrategie (liest nur Quoten, gibt nichts aus / kein Handel) ----

class DemoQuoteStrategy(Strategy):
    """Liest Quoten und fuehrt damit ein Papierbuch. Keine Broker-Order."""

    def __init__(self, config, symbol: str):
        super().__init__(config)
        self.symbol = symbol
        self.buch = Papierbuch(produkt_name(), Path(__file__).resolve().parent)

    def on_start(self):
        for inst in self.cache.instruments():
            if self.symbol in str(inst.id):
                self.subscribe_quote_ticks(inst.id)
                self.log.info(f"Subscribed quotes (cache): {inst.id}")
                return
        ziel = InstrumentId.from_str(f"{self.symbol}.{KRAKEN}")
        self.subscribe_quote_ticks(ziel)
        self.log.info(f"Subscribed quotes (fallback): {ziel}")

    def on_quote_tick(self, tick: QuoteTick):
        vorher = self.buch.trades, self.buch.position is None
        self.buch.tick(float(tick.bid_price), float(tick.ask_price), tick.ts_event / 1e9)
        if (self.buch.trades, self.buch.position is None) != vorher:
            s = self.buch.stand()
            self.log.info(f"Papierbuch: trades={s['trades']} realisiert={s['realisiert']:.2f}")


# --- Node-Umbau mit Kraken-Factories ----------------------------------------

class KrakenPaperNode(TradingNode):
    def build(self):
        # Factory vor dem Node-Build registrieren (sonst "No LiveDataClientFactory")
        self.ConfigureDataFactory()
        self.ConfigureExecFactory()
        super().build()

    def ConfigureDataFactory(self):
        if KRAKEN not in self._builder._data_factories:
            self._builder.add_data_client_factory(KRAKEN, KrakenLiveDataClientFactory)

    def ConfigureExecFactory(self):
        if KRAKEN not in self._builder._exec_factories:
            self._builder.add_exec_client_factory(KRAKEN, KrakenLiveExecClientFactory)


def load_client_configs(symbol: str, mit_order_client: bool = False) -> tuple[dict, dict]:
    """Baut die Client-Konfigurationen fuer den Kraken-Paper-Node.

    ``mit_order_client=False`` (Vorgabe) liefert einen reinen Quoten-Node: nur
    Data-Client, kein Ausfuehrungs-Client. Das ist der Betriebsmodus fuer den
    Papier-/Beobachtungslauf. Der Data-Client bekommt KEINE Zugangsdaten -
    oeffentliche Quotes brauchen keinen Key (Muster: OKX-Quoten-Node).

    Fuer echte Orders (spaeter, Live) ``mit_order_client=True`` - dann werden
    die Kraken-Keys aus HKCU\\Environment gelesen (KRAKEN_SPOT_API_KEY/SECRET
    bzw. KRAKEN_FUTURES_DEMO_API_KEY/SECRET).
    """
    ptype = produkt_typ()
    # Quote-Feed: LIVE fuer beide Produkttypen (oeffentliche Quotes, nur lesen,
    # kein Key noetig). DEMO gibt es bei Kraken NUR fuer Futures - fuer echte
    # DEMO-Orders (spaeter) wird der Exec-Client separat auf DEMO gestellt.
    env = KrakenEnvironment.LIVE

    market_data = {
        "instrument_provider": InstrumentProviderConfig(
            load_ids=frozenset({InstrumentId.from_str(f"{symbol}.{KRAKEN}")}),
        ),
        "environment": env,
        "product_types": (ptype,),
    }

    data_clients = {
        KRAKEN: KrakenDataClientConfig(**market_data, update_instruments_interval_mins=60)
    }

    if not mit_order_client:
        return data_clients, {}

    # Keys nur fuer den Exec-Client noetig. Quelle: HKCU\\Environment.
    if ptype == KrakenProductType.SPOT:
        names = ("KRAKEN_SPOT_API_KEY", "KRAKEN_SPOT_API_SECRET")
    else:
        names = ("KRAKEN_FUTURES_DEMO_API_KEY", "KRAKEN_FUTURES_DEMO_API_SECRET")
    credentials = ("", "")
    try:
        import winreg
    except ImportError:
        credentials = tuple(os.environ.get(name) for name in names)
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                credentials = tuple(winreg.QueryValueEx(key, name)[0] for name in names)
        except OSError as exc:
            raise SystemExit("Kraken-Zugangsdaten in HKCU\\Environment fehlen oder sind nicht lesbar.") from exc
    api_key, api_secret = credentials
    if not (api_key and api_secret):
        raise SystemExit("Kraken-API-Keys muessen gesetzt sein.")

    exec_clients = {
        KRAKEN: KrakenExecClientConfig(
            **market_data,
            api_key=api_key,
            api_secret=api_secret,
        )
    }
    return data_clients, exec_clients


def main() -> None:
    # Ein Buch, ein Node: die Sperre lebt bis Prozessende.
    sperre = sperren(produkt_name(), Path(__file__).resolve().parent)
    if sperre is None:
        raise SystemExit("Papierbuch %s ist belegt - ein Node laeuft schon." % produkt_name())
    symbol = os.environ.get("KRAKEN_SYMBOL", "BTC/EUR")
    mit_order = os.environ.get("NAUTILUS_MIT_ORDER", "").strip() in {"1", "true", "ja", "yes"}
    data_clients, exec_clients = load_client_configs(symbol, mit_order_client=mit_order)

    config = TradingNodeConfig(
        environment="sandbox",
        logging=LoggingConfig(log_level="INFO"),
        data_clients=data_clients,
        exec_clients=exec_clients,
    )

    node = KrakenPaperNode(config=config)
    node.trader.add_strategy(DemoQuoteStrategy(
        StrategyConfig(strategy_id="kraken-demo-quote"), symbol))
    node.build()

    try:
        node.run()
    except KeyboardInterrupt:
        node.stop()
    finally:
        pass


if __name__ == "__main__":
    main()
