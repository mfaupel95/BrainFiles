"""orb: Stop/Ziel/Zwangsschluss duerfen eine ECHTE Position nicht ohne Order ausbuchen.

Bis 20.10.2026 buchte pruefe_ausstiege jede Position, auch eine mit modus=live, am
Sessionende aus dem Buch - an der Boerse blieb sie offen (Muster mosaic 23.09.2026).
Jetzt: Papierlauf laesst sie stehen, Live-Lauf schliesst ueber _exit_live (Boerse zuerst
fragen, reduceOnly, nie eine zweite Order). Ohne Netz.
"""
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import handeln

W = {"instrumente": {"ETH_USDT": {"okx": "ETH-USDT-SWAP", "zone": "UTC",
                                  "eroeffnung": "00:00", "session_ende": "24:00",
                                  "punkt_wert_usd": 1.0}}}
NACH_SCHLUSS = datetime(2026, 9, 14, 0, 5, tzinfo=timezone.utc)   # Zwangsschluss des 13.09.
MITTEN = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def pos(kurs, modus="live", **kw):
    p = {"inst": "ETH_USDT", "richtung": "long", "einstieg": 100.4, "stop": 98.0,
         "ziel": 103.4, "tag": date(2026, 9, 13), "letzter_kurs": kurs, "kontrakte": 3}
    if modus:
        p["modus"] = modus
    p.update(kw)
    return p


class FakeOkxf:
    def __init__(self, offen=True, fehler=False):
        self.offen, self.fehler, self.geschlossen = offen, fehler, []

    def positionen(self):
        if self.fehler:
            raise RuntimeError("boerse weg")
        return [{"instId": "ETH-USDT-SWAP"}] if self.offen else []

    def markt_schliessen(self, paar, kontrakte, richtung):
        self.geschlossen.append((paar, kontrakte, richtung))


class ZwangsschlussLive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name in ("JOURNAL", "okxf"):
            self.addCleanup(setattr, handeln, name, getattr(handeln, name))
        handeln.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"
        self.okx = FakeOkxf()
        handeln.okxf = self.okx

    def lauf(self, p, jetzt, live):
        z = {"positionen": [p]}
        return z, handeln.pruefe_ausstiege(z, W, jetzt, live=live)

    def test_papierlauf_laesst_echte_position_am_sessionende_stehen(self):
        z, g = self.lauf(pos(101.0), NACH_SCHLUSS, live=False)
        self.assertEqual(g, [])
        self.assertEqual(len(z["positionen"]), 1)
        self.assertFalse(handeln.JOURNAL.exists())          # nichts gebucht
        self.assertEqual(self.okx.geschlossen, [])

    def test_papierlauf_laesst_echte_position_bei_stop_stehen(self):
        z, g = self.lauf(pos(97.0), MITTEN, live=False)
        self.assertEqual((g, len(z["positionen"])), ([], 1))

    def test_livelauf_schliesst_am_sessionende_per_marktorder(self):
        z, g = self.lauf(pos(101.0), NACH_SCHLUSS, live=True)
        self.assertEqual([x[1] for x in g], ["zwangsschluss"])
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self.okx.geschlossen, [("ETH-USDT-SWAP", 3, "long")])

    def test_boerse_hat_schon_geschlossen_keine_zweite_order(self):
        self.okx.offen = False
        z, g = self.lauf(pos(97.0), MITTEN, live=True)
        self.assertEqual(self.okx.geschlossen, [])
        self.assertEqual(g[0][1], "stop (boerse)")
        self.assertEqual(z["positionen"], [])

    def test_boerse_nicht_lesbar_position_bleibt_ungeklaert(self):
        self.okx.fehler = True
        z, g = self.lauf(pos(101.0), NACH_SCHLUSS, live=True)
        self.assertEqual(g, [])
        self.assertTrue(z["positionen"][0]["exit_ungeklaert"])
        self.assertEqual(self.okx.geschlossen, [])

    def test_papierposition_wird_weiter_gebucht(self):
        z, g = self.lauf(pos(101.0, modus=None), NACH_SCHLUSS, live=False)
        self.assertEqual([x[1] for x in g], ["zwangsschluss"])
        self.assertEqual(self.okx.geschlossen, [])


if __name__ == "__main__":
    unittest.main()
