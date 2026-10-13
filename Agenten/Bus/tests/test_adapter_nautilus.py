"""Test fuer adapter_nautilus.py. Bus absichtlich tot (Port 1). Direkt ausfuehrbar:
python tests/test_adapter_nautilus.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import adapter_nautilus as an   # noqa: E402
import ereignis                 # noqa: E402
import journal                  # noqa: E402

T = 1_791_651_600
WACHE = {"fremd_signale_erlaubt": True, "modi_erlaubt": ["paper"],
         "quellen_erlaubt": ["nautilus_trader"],
         "instrumente_erlaubt": ["BTC-USDC", "BTC/USD"], "size_pct_max": 0.25}


def schreibe(d, zeilen):
    p = os.path.join(d, "intents.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        for z in zeilen:
            f.write((z if isinstance(z, str) else json.dumps(z)) + "\n")
    return p


def test_instrument_zuordnung():
    assert an.instrument_aus_id("BTC-USDC.OKX") == ("BTC-USDC", "okx")
    assert an.instrument_aus_id("XBT/USD.KRAKEN") == ("BTC/USD", "kraken")
    assert an.instrument_aus_id("BTCUSDT.BINANCE") is None
    assert an.instrument_aus_id("XBTUSD.KRAKEN") is None
    assert an.instrument_aus_id("kaputt") is None


def test_buy_sell_und_nanosekunden():
    s = an.signal_aus_zeile({"ts_event": T * 10**9, "instrument_id": "BTC-USDC.OKX", "side": "buy"})
    assert s["direction"] == "long" and s["size_pct"] == 0.2 and s["ts_utc"] == T
    assert s["source"] == "nautilus_trader" and s["mode"] == "paper"
    f = an.signal_aus_zeile({"ts_event": T, "instrument_id": "BTC-USDC.OKX", "side": "SELL"})
    assert f["direction"] == "flat" and "size_pct" not in f


def test_ungueltige_zeilen_liefern_none():
    for z in ({"ts_event": T, "instrument_id": "BTC-USDC.OKX", "side": "HOLD"},
              {"instrument_id": "BTC-USDC.OKX", "side": "BUY"},
              {"ts_event": T, "instrument_id": "X.BINANCE", "side": "BUY"}):
        assert an.signal_aus_zeile(z) is None


def test_lauf_nur_neue_zeilen_einmal():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as d:
        p = schreibe(d, [{"ts_event": T, "instrument_id": "BTC-USDC.OKX", "side": "BUY"}, "kein json"])
        stand = os.path.join(d, "s.json")
        kw = dict(jsonl_pfad=p, stand_pfad=stand, jetzt=T + 10, port=1, wurzel=d, wache=WACHE)
        assert an.lauf(**kw) == ("ok", 1, 1)
        assert an.lauf(**kw) == ("ok", 0, 0)
        assert [z["was"] for z in journal.lesen(wurzel=d)] == ["signal"]


def test_zu_spaet_wird_verworfen():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as d:
        p = schreibe(d, [{"ts_event": T, "instrument_id": "BTC-USDC.OKX", "side": "BUY"}])
        r = an.lauf(p, os.path.join(d, "s.json"), jetzt=T + 3000, port=1, wurzel=d, wache=WACHE)
        assert r == ("ok", 0, 1), r


def test_fehlende_datei_wirft_nicht():
    assert an.lauf("/gibt/es/nicht", "/tmp/x.json")[0] == "fehler"


def test_size_pct_aus_der_zeile_wird_uebernommen():
    s = an.signal_aus_zeile({"ts_event": T, "instrument_id": "BTC-USDC.OKX", "side": "BUY", "size_pct": 0.05})
    assert s["size_pct"] == 0.05
    s = an.signal_aus_zeile({"ts_event": T, "instrument_id": "BTC-USDC.OKX", "side": "BUY", "size_pct": "x"})
    assert s["size_pct"] == 0.2
    s = an.signal_aus_zeile({"ts_event": T, "instrument_id": "BTC-USDC.OKX", "side": "BUY", "size_pct": -1})
    assert s["size_pct"] == 0.2


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            f()
    print("adapter_nautilus bestanden")
