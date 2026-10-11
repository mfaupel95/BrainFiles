"""Test fuer adapter_moondev.py. Bus absichtlich tot (Port 1). Direkt ausfuehrbar:
python tests/test_adapter_moondev.py
"""
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import adapter_moondev as am   # noqa: E402
import ereignis                # noqa: E402
import journal                 # noqa: E402

KOPF = "timestamp,symbol,agent_one_recommendation,agent_two_recommendation\n"
TS = "2026-10-11T10:00:00"
T = int(datetime.fromisoformat(TS).astimezone().timestamp())
ERLAUBT = {"BTC-USDC", "SOL-USDC"}
WACHE = {"fremd_signale_erlaubt": True, "modi_erlaubt": ["paper"],
         "quellen_erlaubt": ["moon-dev-ai-agents"],
         "instrumente_erlaubt": sorted(ERLAUBT), "size_pct_max": 0.25}


def csv(d, zeilen):
    p = os.path.join(d, "buys.csv")
    with open(p, "w", encoding="utf-8") as f:
        f.write(KOPF + "".join("%s,%s,%s,%s\n" % z for z in zeilen))
    return p


def z(sym, a, b):
    return {"timestamp": TS, "symbol": sym, "agent_one_recommendation": a, "agent_two_recommendation": b}


def test_konsens_buy_long_sell_flat():
    s = am.signal_aus_zeile(z("btc", "BUY", "BUY"), ERLAUBT)
    assert s["instrument"] == "BTC-USDC" and s["direction"] == "long" and s["size_pct"] == 0.2
    assert s["source"] == "moon-dev-ai-agents" and s["ts_utc"] == T and s["mode"] == "paper"
    f = am.signal_aus_zeile(z("SOL", "SELL", "SELL"), ERLAUBT)
    assert f["direction"] == "flat" and "size_pct" not in f


def test_uneinig_oder_nichts_tun_ist_kein_signal():
    for a, b in (("BUY", "DO NOTHING"), ("BUY", "SELL"), ("DO NOTHING", "DO NOTHING")):
        assert am.signal_aus_zeile(z("BTC", a, b), ERLAUBT) is None


def test_unbekanntes_token_wird_vorab_verworfen():
    assert am.signal_aus_zeile(z("BIGJIM", "BUY", "BUY"), ERLAUBT) is None
    assert am.signal_aus_zeile(z("BT C", "BUY", "BUY"), None) is None


def test_lauf_nur_neue_zeilen_einmal():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as d:
        p = csv(d, [(TS, "BTC", "BUY", "BUY"), (TS, "BIGJIM", "BUY", "BUY")])
        kw = dict(csv_pfad=p, stand_pfad=os.path.join(d, "s.json"), jetzt=T + 10,
                  port=1, wurzel=d, wache=WACHE)
        assert am.lauf(**kw) == ("ok", 1, 1)
        assert am.lauf(**kw) == ("ok", 0, 0)
        assert [x["was"] for x in journal.lesen(wurzel=d)] == ["signal"]


def test_zu_spaet_wird_verworfen():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as d:
        p = csv(d, [(TS, "BTC", "BUY", "BUY")])
        r = am.lauf(p, os.path.join(d, "s.json"), jetzt=T + 3000, port=1, wurzel=d, wache=WACHE)
        assert r == ("ok", 1, 1), r
        assert journal.lesen(wurzel=d)[0]["was"] == "signal_verworfen"


def test_fehlende_datei_wirft_nicht():
    assert am.lauf("/gibt/es/nicht", "/tmp/x.json", wache=WACHE)[0] == "fehler"


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            f()
    print("adapter_moondev bestanden")
