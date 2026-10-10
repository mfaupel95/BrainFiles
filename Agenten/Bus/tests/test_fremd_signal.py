"""Test fuer fremd_signal.py - Bus-Nachrichtentyp "signal".
Der Bus ist hier absichtlich tot (Port 1); es zaehlt das Journal.
Direkt ausfuehrbar: python tests/test_fremd_signal.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ereignis      # noqa: E402
import fremd_signal  # noqa: E402
import journal       # noqa: E402
import auffaellig    # noqa: E402

TOT = 1
OFFEN = {"fremd_signale_erlaubt": True, "modi_erlaubt": ["paper", "demo"],
         "quellen_erlaubt": ["kraken-cli"], "instrumente_erlaubt": ["BTC/USD"],
         "size_pct_max": 0.5}
JETZT = 1_728_432_100


def sig(**ueber):
    s = {"instrument": "BTC/USD", "venue": "kraken", "direction": "long",
         "size_pct": 0.25, "source": "kraken-cli", "ts_utc": JETZT - 5,
         "expiry_s": 180, "mode": "paper"}
    s.update(ueber)
    return s


def test_gueltiges_signal_wird_als_signal_journalisiert():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        ok, grund = fremd_signal.melden_signal("fremd/kraken-cli", sig(),
                                               jetzt=JETZT, port=TOT, wurzel=w,
                                               wache=OFFEN)
        assert ok and grund == "ok", grund
        zeilen = journal.lesen(wurzel=w)
        assert len(zeilen) == 1 and zeilen[0]["was"] == "signal", zeilen
        assert json.loads(zeilen[0]["text"])["instrument"] == "BTC/USD"


def test_live_signal_wird_verworfen_und_so_vermerkt():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        ok, grund = fremd_signal.melden_signal(
            "fremd/kraken-cli", sig(mode="live"), jetzt=JETZT, port=TOT, wurzel=w,
            wache=OFFEN)
        assert not ok and "mode" in grund, grund
        z = journal.lesen(wurzel=w)
        assert len(z) == 1 and z[0]["was"] == "signal_verworfen", z
        assert "mode" in z[0]["text"]


def test_stales_signal_wird_verworfen():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        ok, grund = fremd_signal.melden_signal(
            "fremd/kraken-cli", sig(ts_utc=JETZT - 999), jetzt=JETZT,
            port=TOT, wurzel=w, wache=OFFEN)
        assert not ok and "stale" in grund, grund


def test_ohne_wache_ist_das_tor_zu():
    # Auslieferungszustand: fremd_signale/wachen.json hat das Tor zu
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        ok, grund = fremd_signal.melden_signal("fremd/kraken-cli", sig(),
                                               jetzt=JETZT, port=TOT, wurzel=w)
        assert not ok and "Tor" in grund, grund
        z = journal.lesen(wurzel=w)
        assert z[0]["was"] == "signal_verworfen" and "Tor" in z[0]["text"], z


def test_kaputte_wache_schliesst_das_tor():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        ok, grund = fremd_signal.melden_signal("fremd/kraken-cli", sig(),
                                               jetzt=JETZT, port=TOT, wurzel=w,
                                               wache="kaputt")
        assert not ok and "Tor" in grund, grund


def test_tor_regeln_greifen_ueber_den_bus(
):
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        ok, grund = fremd_signal.melden_signal(
            "fremd/kraken-cli", sig(source="moon-dev"), jetzt=JETZT, port=TOT,
            wurzel=w, wache=OFFEN)
        assert not ok and "source" in grund, grund
        ok, grund = fremd_signal.melden_signal(
            "fremd/kraken-cli", sig(size_pct=0.9), jetzt=JETZT, port=TOT,
            wurzel=w, wache=OFFEN)
        assert not ok and "Deckel" in grund, grund


def test_muell_wirft_nie():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        for muell in (None, "long", 42, [], {"x": object()}):
            ok, _ = fremd_signal.melden_signal("fremd/x", muell, jetzt=JETZT,
                                               port=TOT, wurzel=w)
            assert ok is False


def test_signale_machen_den_handy_sprecher_nicht_laut():
    # unbekannte "was" -> still sammeln (bewerte gibt None)
    for was in ("signal", "signal_verworfen"):
        e = journal.neu("fremd/x", was, text="{}")
        assert auffaellig.bewerte(e, [], {"dauer_mindestlaeufe": 3,
                                          "dauer_faktor": 3}) is None


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            f()
            print("ok", n)
    print("fremd_signal bestanden")
