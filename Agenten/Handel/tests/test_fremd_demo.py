import json, os, sys, time, unittest
HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))
sys.path.insert(0, os.path.join(os.path.dirname(HIER), "..", "Bus"))
import fremd_demo, fremd_papier

W = json.load(open(os.path.join(os.path.dirname(HIER), "fremd_signale", "wachen.json")))
W["fremd_signale_erlaubt"] = True
JETZT = int(time.time())


def sig(**k):
    s = {"instrument": "BTC-USDC", "venue": "okx", "direction": "long", "size_pct": 0.2,
         "source": "agent-trade-kit", "ts_utc": JETZT, "expiry_s": 300, "mode": "demo"}
    s.update(k)
    return s


class T(unittest.TestCase):
    def test_long_plan_mit_stop(self):
        z = fremd_papier.leer()
        ok, p = fremd_demo.plane(z, sig(), 80000.0, W, "a", JETZT)
        self.assertTrue(ok, p)
        self.assertEqual(p["args"]["side"], "buy")
        self.assertEqual(p["args"]["slTriggerPx"], "76800.00")
        self.assertEqual(p["args"]["sz"], "50.00")

    def test_short_abgelehnt(self):
        ok, g = fremd_demo.plane(fremd_papier.leer(), sig(direction="short"), 80000.0, W, "a", JETZT)
        self.assertFalse(ok)

    def test_papier_modus_abgelehnt(self):
        ok, g = fremd_demo.plane(fremd_papier.leer(), sig(mode="paper"), 80000.0, W, "a", JETZT)
        self.assertFalse(ok)

    def test_tor_zu(self):
        w = dict(W, fremd_signale_erlaubt=False)
        self.assertFalse(fremd_demo.plane(fremd_papier.leer(), sig(), 80000.0, w, "a", JETZT)[0])

    def test_doppelt_und_flat(self):
        z = fremd_papier.leer()
        self.assertTrue(fremd_demo.plane(z, sig(), 80000.0, W, "a", JETZT)[0])
        self.assertFalse(fremd_demo.plane(z, sig(), 80000.0, W, "b", JETZT)[0])
        ok, p = fremd_demo.plane(z, sig(direction="flat"), 81000.0, W, "c", JETZT)
        self.assertTrue(ok)
        self.assertEqual(p["args"]["side"], "sell")

    def test_flat_ohne_position(self):
        self.assertFalse(fremd_demo.plane(fremd_papier.leer(), sig(direction="flat"), 1.0, W, "a", JETZT)[0])

    def test_kein_spot(self):
        w = dict(W, instrumente_erlaubt=["BTC/USD"])
        self.assertFalse(fremd_demo.plane(fremd_papier.leer(), sig(instrument="BTC/USD"), 1.0, w, "a", JETZT)[0])


if __name__ == "__main__":
    unittest.main()
