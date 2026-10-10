import json, os, sys, time, unittest
HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
sys.path.insert(0, os.path.join(WURZEL, "fremd_signale"))
sys.path.insert(0, WURZEL)
sys.path.insert(0, os.path.join(WURZEL, "scanner"))
sys.path.insert(0, os.path.join(WURZEL, "..", "Bus"))
import demo_plan, fremd_papier

W = json.load(open(os.path.join(WURZEL, "fremd_signale", "wachen.json")))
W["fremd_signale_erlaubt"] = True
J = int(time.time())


def zeile(sid, **k):
    s = {"instrument": "BTC-USDC", "venue": "okx", "direction": "long", "size_pct": 0.2,
         "source": "agent-trade-kit", "ts_utc": J, "expiry_s": 300, "mode": "demo"}
    s.update(k)
    return {"was": "signal", "id": sid, "text": json.dumps(s)}


class T(unittest.TestCase):
    def test_demo_plan_und_einmalig(self):
        z = fremd_papier.leer()
        r = demo_plan.plaene(z, [zeile("a")], lambda i: 80000.0, W, J)
        self.assertTrue(r[0][1])
        self.assertEqual(demo_plan.plaene(z, [zeile("a")], lambda i: 80000.0, W, J), [])

    def test_papier_signal_ignoriert(self):
        z = fremd_papier.leer()
        self.assertEqual(demo_plan.plaene(z, [zeile("a", mode="paper")], lambda i: 1.0, W, J), [])
        self.assertEqual(z["verarbeitet"], [])

    def test_kurs_fehler(self):
        def boese(i):
            raise OSError("x")
        r = demo_plan.plaene(fremd_papier.leer(), [zeile("a")], boese, W, J)
        self.assertFalse(r[0][1])

    def test_verwerfen_ohne_argument(self):
        self.assertEqual(demo_plan.main(["--verwerfen"]), 2)

    def test_live_verweigert(self):
        self.assertEqual(demo_plan.main(["--live"]), 2)


if __name__ == "__main__":
    unittest.main()
