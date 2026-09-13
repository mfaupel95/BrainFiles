import json
import unittest
from pathlib import Path

import wachen_orb as wo

HIER = Path(__file__).resolve().parent
WACHEN = HIER.parent / "wachen.json"


class TestRangeFilter(unittest.TestCase):
    def setUp(self):
        self.w = json.loads(WACHEN.read_text("utf-8"))

    def test_range_unter_mindest_nicht_ok(self):
        key = next(iter(self.w["instrumente"]))
        mn = self.w["mindest_range_punkte"][key]
        self.assertFalse(wo.range_ok(mn - 1, key, self.w))
        self.assertTrue(wo.range_ok(mn + 1, key, self.w))

    def test_range_ueber_max_nicht_ok(self):
        key = next(iter(self.w["instrumente"]))
        mx = self.w["max_range_punkte"][key]
        self.assertFalse(wo.range_ok(mx + 1, key, self.w))


class TestFreigabe(unittest.TestCase):
    def _w(self, **over):
        base = {"freigabe": {"backtest_bestanden": True, "netto_positiv": True,
                             "papierlauf_min_wochen": 6, "papierlauf_min_sessions": 50}}
        base["freigabe"].update(over)
        return base

    def test_alle_vier_erfuellt(self):
        self.assertTrue(wo.freigabe_voll_erfuellt(
            self._w(), gehandelte_wochen=7, gehandelte_sessions=60))

    def test_zu_wenig_sessions_blockt(self):
        self.assertFalse(wo.freigabe_voll_erfuellt(
            self._w(), gehandelte_wochen=7, gehandelte_sessions=40))

    def test_backtest_nicht_bestanden_blockt(self):
        self.assertFalse(wo.freigabe_voll_erfuellt(
            self._w(backtest_bestanden=False), gehandelte_wochen=99, gehandelte_sessions=99))


class TestSperreZu(unittest.TestCase):
    def test_nur_true_nach_false(self, ):
        # gegen eine Kopie testen, nicht die echte wachen.json veraendern
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp()) / "wachen.json"
        d = json.loads(WACHEN.read_text("utf-8"))
        d["handel_erlaubt"] = False
        tmp.write_text(json.dumps(d), "utf-8")
        alt = wo.WACHEN
        wo.WACHEN = tmp
        try:
            self.assertFalse(wo.sperre_zu("test"))       # war schon false
            d["handel_erlaubt"] = True
            tmp.write_text(json.dumps(d), "utf-8")
            self.assertTrue(wo.sperre_zu("test"))         # true -> false
            self.assertIs(json.loads(tmp.read_text())["handel_erlaubt"], False)
        finally:
            wo.WACHEN = alt
