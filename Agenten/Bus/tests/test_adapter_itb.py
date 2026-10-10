"""Test fuer adapter_itb.py - signals.csv von intelligent-trading-bot -> Fremd-Signal.
Der Bus ist hier absichtlich tot (Port 1). Direkt ausfuehrbar: python tests/test_adapter_itb.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import adapter_itb   # noqa: E402
import ereignis      # noqa: E402
import journal       # noqa: E402

KOPF = "timestamp,open,high,low,close,trade_score,buy_signal_column,sell_signal_column\n"
T0 = "2026-10-10 16:00:00+00:00"          # Kerze 16:00-17:00 UTC
SCHLUSS = 1_791_651_600                    # 17:00 UTC in Unix-Sekunden
WACHE = {"fremd_signale_erlaubt": True, "modi_erlaubt": ["paper"],
         "quellen_erlaubt": ["intelligent-trading-bot"],
         "instrumente_erlaubt": ["BTC-USDT-SWAP"], "size_pct_max": 0.25}


def csv(ordner, zeilen):
    p = os.path.join(ordner, "signals.csv")
    with open(p, "w", encoding="utf-8") as f:
        f.write(KOPF + "".join(zeilen))
    return p


def zeile(ts, buy, sell):
    return "%s,1,1,1,83000,0.1,%s,%s\n" % (ts, buy, sell)


def test_buy_wird_long_sell_wird_flat():
    s = adapter_itb.signal_aus_zeile(
        {"timestamp": T0, "buy_signal_column": True, "sell_signal_column": False},
        instrument="BTC-USDT-SWAP", bar_s=3600, size_pct=0.2, expiry_s=180)
    assert s["direction"] == "long" and s["size_pct"] == 0.2
    assert s["source"] == "intelligent-trading-bot" and s["venue"] == "okx"
    assert s["mode"] == "paper" and s["ts_utc"] == SCHLUSS and s["expiry_s"] == 180
    f = adapter_itb.signal_aus_zeile(
        {"timestamp": T0, "buy_signal_column": False, "sell_signal_column": True},
        instrument="BTC-USDT-SWAP", bar_s=3600, size_pct=0.2, expiry_s=180)
    assert f["direction"] == "flat" and "size_pct" not in f


def test_kein_signal_oder_widerspruch_liefert_nichts():
    for b, s in ((False, False), (True, True)):
        assert adapter_itb.signal_aus_zeile(
            {"timestamp": T0, "buy_signal_column": b, "sell_signal_column": s},
            instrument="BTC-USDT-SWAP", bar_s=3600, size_pct=0.2, expiry_s=180) is None


def test_lauf_meldet_einmal_und_nicht_doppelt():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as d:
        p = csv(d, [zeile("2026-10-10 15:00:00+00:00", False, False),
                    zeile(T0, True, False)])
        stand = os.path.join(d, "stand.json")
        kw = dict(csv_pfad=p, stand_pfad=stand, instrument="BTC-USDT-SWAP",
                  jetzt=SCHLUSS + 20, port=1, wurzel=d, wache=WACHE)
        r1 = adapter_itb.lauf(**kw)
        r2 = adapter_itb.lauf(**kw)
        assert r1[0] == "gemeldet" and r1[1] is True, r1
        assert r2[0] == "schon_gemeldet", r2
        assert [z["was"] for z in journal.lesen(wurzel=d)] == ["signal"]


def test_zu_spaet_wird_vom_tor_verworfen():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as d:
        p = csv(d, [zeile(T0, True, False)])
        r = adapter_itb.lauf(csv_pfad=p, stand_pfad=os.path.join(d, "s.json"),
                             instrument="BTC-USDT-SWAP", jetzt=SCHLUSS + 3000,
                             port=1, wurzel=d, wache=WACHE)
        assert r[0] == "gemeldet" and r[1] is False and "stale" in r[2], r
        assert journal.lesen(wurzel=d)[0]["was"] == "signal_verworfen"


def test_ohne_signal_in_der_letzten_zeile_wird_nichts_gemeldet():
    with tempfile.TemporaryDirectory() as d:
        p = csv(d, [zeile(T0, False, False)])
        r = adapter_itb.lauf(csv_pfad=p, stand_pfad=os.path.join(d, "s.json"),
                             instrument="BTC-USDT-SWAP", jetzt=SCHLUSS + 20,
                             port=1, wurzel=d, wache=WACHE)
        assert r[0] == "kein_signal", r
        assert journal.lesen(wurzel=d) == []


def test_kaputte_oder_fehlende_csv_wirft_nicht():
    with tempfile.TemporaryDirectory() as d:
        r = adapter_itb.lauf(csv_pfad=os.path.join(d, "gibts_nicht.csv"),
                             stand_pfad=os.path.join(d, "s.json"),
                             instrument="BTC-USDT-SWAP", jetzt=SCHLUSS, port=1,
                             wurzel=d, wache=WACHE)
        assert r[0] == "fehler", r
        with open(os.path.join(d, "x.csv"), "w") as f:
            f.write("muell\nohne,spalten\n")
        r = adapter_itb.lauf(csv_pfad=os.path.join(d, "x.csv"),
                             stand_pfad=os.path.join(d, "s.json"),
                             instrument="BTC-USDT-SWAP", jetzt=SCHLUSS, port=1,
                             wurzel=d, wache=WACHE)
        assert r[0] == "fehler", r


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            f()
            print("ok", n)
    print("adapter_itb bestanden")
