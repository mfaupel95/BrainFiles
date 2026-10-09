"""Der Kill von spur_buch.zyklus nach Ablauf der Frist (Befund 09.10.2026).

BEFUND, mit dem echten Code nachgestellt: Ist der gebuchte Ruecklauf >= kill_switch_gesamt_usd,
stellt zyklus() alle Positionen flach, OHNE sie zu buchen (z["positionen"] = [], keine
Verkaufszeile), und sperrt fuer kill_frist_stunden (168 h). Nach der Frist laeuft EIN Zyklus
frei und eroeffnet eine Position. Im naechsten Zyklus gilt der Kill sofort wieder - der
Ruecklauf wurde ja nie kleiner, weil nichts gebucht wurde - und die frisch eroeffnete
Position wird wieder OHNE Buchung geloescht. Die Spur kann die Schwelle so nie mehr
verlassen: der Kill ist faktisch dauerhaft (T-176 wollte genau das verhindern).

Der erste Test haelt das GEWUENSCHTE Verhalten fest und ist deshalb als erwarteter Fehlschlag
markiert (expectedFailure). Behebt jemand den Kill, meldet unittest "unexpected success" -
dann den Marker entfernen. Der zweite Test haelt den heutigen Ist-Zustand fest.
"""

import csv
import datetime
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

spec = importlib.util.spec_from_file_location("spur_buch_kill", os.path.join(HANDEL, "spur_buch.py"))
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)

KERZEN = [[0, 100, 101, 99, 100, 1.0]] * 100


def quelle(w):
    return {"BTC-USDT-SWAP": {"kerzen": KERZEN}}, {"BTC-USDT-SWAP": 100.0}, []


def signal(d, w):
    return "long"


class KillNachFristTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="kill-frist-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        with open(os.path.join(HANDEL, "klassik_ema", "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        w.update(journal_zweitziel=None, risikovorfilter=False, handel_erlaubt=False)
        with open(os.path.join(self.tmp, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(w, f)
        self.jp = os.path.join(self.tmp, "handelsjournal.csv")
        self.zp = os.path.join(self.tmp, "zustand.json")
        sb.lege_journal_an(self.jp)
        t0 = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
        for n in range(5):                                   # 5 Verlustrunden je -10 USD -> Ruecklauf 50 >= 45
            z = (t0 + datetime.timedelta(hours=n)).isoformat(timespec="seconds")
            sb.journal(self.jp, zeit=z, modus="papier", aktion="kauf", inst="BTC-USDT-SWAP",
                       seite="long", preis="100", einsatz_usd="200.00", grund="test")
            sb.journal(self.jp, zeit=z, modus="papier", aktion="verkauf", inst="BTC-USDT-SWAP",
                       seite="long", preis="95", einsatz_usd="190.00", grund="stop")
        seit = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=200)).isoformat(timespec="seconds")
        with open(self.zp, "w", encoding="utf-8") as f:
            json.dump({"positionen": [], "modus": "papier", "letzter_lauf": None,
                       "verlust_usd": 0.0, "kill_seit": seit}, f)     # Frist (168 h) ist um

    def _zyklus(self):
        with redirect_stdout(io.StringIO()):
            sb.zyklus(self.tmp, quelle, signal, "papier", "kill-test")
        with open(self.zp, encoding="utf-8") as f:
            return json.load(f)

    def _verkaeufe(self):
        with open(self.jp, encoding="utf-8", newline="") as f:
            return sum(1 for r in csv.DictReader(f) if r.get("aktion") == "verkauf")

    def test_ist_zustand_freier_zyklus_dann_wieder_kill(self):
        z1 = self._zyklus()
        self.assertEqual(len(z1["positionen"]), 1)            # freier Zyklus: Position eroeffnet
        self.assertNotIn("kill_seit", z1)
        z2 = self._zyklus()
        self.assertEqual(z2["positionen"], [])                # naechster Zyklus: Kill, Position weg
        self.assertIn("kill_seit", z2)
        self.assertEqual(self._verkaeufe(), 5)                # ... und OHNE Buchung (keine neue Verkaufszeile)

    @unittest.expectedFailure
    def test_gewuenscht_position_des_freien_zyklus_wird_gebucht_oder_bleibt(self):
        self._zyklus()                                        # freier Zyklus
        z2 = self._zyklus()
        gebucht = self._verkaeufe() > 5
        self.assertTrue(len(z2["positionen"]) == 1 or gebucht,
                        "die Position des freien Zyklus verschwindet ohne Buchung")


if __name__ == "__main__":
    unittest.main()
