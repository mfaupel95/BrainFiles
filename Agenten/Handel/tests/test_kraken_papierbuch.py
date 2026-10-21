"""Papierbuch des Kraken-Paper-Nodes: Signal, Fills, Gebuehr, PnL, Persistenz."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "nautilus_kraken"))
import papierbuch as pb


def buch(tmp, **kw):
    kw.setdefault("schnell", 2)
    kw.setdefault("langsam", 4)
    kw.setdefault("takt_s", 60)
    kw.setdefault("band", 0.0)
    return pb.Papierbuch("spot", Path(tmp), startkapital=1000.0, gebuehr=0.0026, **kw)


def fuettere(b, mids, start=0):
    for i, m in enumerate(mids):
        b.tick(m - 0.5, m + 0.5, start + i * 60)


class Papierbuch(unittest.TestCase):
    def test_ohne_signal_kein_handel(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = buch(tmp)
            fuettere(b, [100] * 10)
            self.assertIsNone(b.position)
            self.assertEqual(b.stand()["trades"], 0)

    def test_aufwaertskreuzung_kauft_am_ask_mit_gebuehr(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = buch(tmp)
            fuettere(b, [100, 100, 100, 100, 110, 120])
            self.assertIsNotNone(b.position)
            self.assertAlmostEqual(b.position["einstieg"], 110.5)
            self.assertAlmostEqual(b.kasse, 0.0)

    def test_abwaertskreuzung_schliesst_am_bid_und_bucht_pnl(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = buch(tmp)
            fuettere(b, [100, 100, 100, 100, 110, 120, 130, 90, 80])
            self.assertIsNone(b.position)
            s = b.stand()
            self.assertEqual(s["trades"], 1)
            menge = 1000 * (1 - 0.0026) / 110.5
            erwartet = menge * 89.5 * (1 - 0.0026) - 1000
            self.assertAlmostEqual(s["realisiert"], erwartet, places=6)
            journal = (Path(tmp) / "papierjournal.spot.csv").read_text(encoding="utf-8")
            self.assertEqual(len(journal.strip().splitlines()), 3)  # Kopf + kauf + verkauf

    def test_ticks_innerhalb_takt_zaehlen_nur_einmal(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = buch(tmp)
            for s in range(0, 59):
                b.tick(99.5, 100.5, s)
            self.assertEqual(len(b._mids), 1)

    def test_stand_wird_als_json_geschrieben_und_beim_neustart_geladen(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = buch(tmp)
            fuettere(b, [100, 100, 100, 100, 110, 120])
            daten = json.loads((Path(tmp) / "papierbuch.spot.json").read_text(encoding="utf-8"))
            self.assertIn("unrealisiert", daten)
            self.assertGreater(daten["unrealisiert"], 0)
            neu = buch(tmp)
            self.assertIsNotNone(neu.position)
            self.assertAlmostEqual(neu.position["einstieg"], 110.5)

    def test_band_unterdrueckt_kleine_kreuzung(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = buch(tmp, band=0.05)
            fuettere(b, [100, 100, 100, 100, 101, 102])
            self.assertIsNone(b.position)
            fuettere(b, [130, 140], start=600)
            self.assertIsNotNone(b.position)

    def test_mids_ueberleben_neustart(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = buch(tmp)
            fuettere(b, [100, 100, 100])
            neu = buch(tmp)
            self.assertEqual(list(neu._mids), [100, 100, 100])
            neu.tick(99.5, 100.5, 120)  # gleicher Takt wie zuletzt: zaehlt nicht
            self.assertEqual(len(neu._mids), 3)

    def test_sperre_ist_exklusiv(self):
        with tempfile.TemporaryDirectory() as tmp:
            erste = pb.sperren("spot", tmp)
            self.assertIsNotNone(erste)
            self.assertIsNone(pb.sperren("spot", tmp))
            erste.close()
            zweite = pb.sperren("spot", tmp)
            self.assertIsNotNone(zweite)
            zweite.close()

    def test_lese_stand_ohne_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(pb.lese_stand("spot", Path(tmp)))


if __name__ == "__main__":
    unittest.main()
