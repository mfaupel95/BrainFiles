"""T-119: MAE/MFE landen wirklich im Journal (kraken und mosaic).

Geprueft wird die EIGENSCHAFT, nicht der Zufallswert: eine Position, die im
Laufs des Lebens unter den Einstieg fiel, traegt danach einen echten
mae_pct-Wert; eine Position, die nie unter den Einstieg kam, traegt 0. Ohne
diese Trennung wuerde auch ein Modul, das MAE/MFE pauschal als 0.0000
schreibt, den Test bestehen - das war genau der Befund, aus dem die
Aufgabe entstanden ist.

Kein Netz, keine Boerse: die Kursabrufe sind Seams (kraken.letzter_kurs
bzw. die Kerzenliste in pruefe_ausstiege).

Lauf (aus Agenten/Handel/tests):
    python -m unittest test_mae_im_journal -v
"""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
from pathlib import Path                     # noqa: E402
# Rueckwaerts: HIER muss vorn landen, sonst gewinnt ein gleichnamiges
# handeln.py aus einem anderen Spurenordner (Hausregel). Der kraken-Ordner
# gehoert dazu, sonst findet die Spur ihr eigenes `abgleich` nicht.
for p in (os.path.join(HANDEL, "kraken"), os.path.join(HANDEL, "mosaic"),
          os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)


# Nur die Felder, die der Ausstiegsweg wirklich liest. Kein Wachen-Abschnitt:
# der Test soll die Buchfuehrung pruefen, nicht die Freigabekette.
W_KRAKEN = {"gebuehr_taker": 0.0}
W_MOSAIC = {"gebuehr_taker": 0.0}


def spur_laden(name):
    pfad = os.path.join(HANDEL, name, "handeln.py")
    spec = importlib.util.spec_from_file_location("handelen_" + name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.__file__.startswith(os.path.join(HANDEL, name)), \
        "falsches handeln geladen: %s" % m.__file__
    return m


class MaeMfeTest(unittest.TestCase):
    """Basis: Spur, Temp-Buch, Journal lesen."""

    SPUR = "kraken"

    def setUp(self):
        self.h = spur_laden(self.SPUR)
        self.tmp = tempfile.mkdtemp(prefix="mae-%s-" % self.SPUR)
        self.alt = (self.h.JOURNAL, self.h.ZUSTAND,
                    getattr(self.h, "SCHREIBEN", None))
        # Path, nicht str: kraken ruft JOURNAL.exists() auf, mosaic mit
        # os.path.exists() - die Art des Pfades ist Teil des Vertrags
        # (Hausfall 03.10.2026).
        self.h.JOURNAL = Path(self.tmp) / "handelsjournal.csv"
        self.h.ZUSTAND = Path(self.tmp) / "zustand.json"
        # kraken schreibt immer (kein SCHREIBEN-Flag), mosaic kennt eines.
        if hasattr(self.h, "SCHREIBEN"):
            self.h.SCHREIBEN = True

    def tearDown(self):
        self.h.JOURNAL, self.h.ZUSTAND, schreiben = self.alt
        if schreiben is not None:
            self.h.SCHREIBEN = schreiben
        shutil.rmtree(self.tmp, ignore_errors=True)

    def kopf(self):
        with open(self.h.JOURNAL, encoding="utf-8", newline="") as f:
            return f.readline().strip().split(",")

    def verkaeufe(self):
        if not os.path.exists(self.h.JOURNAL):
            return []          # noch nichts geschrieben - kein Fehler
        with open(self.h.JOURNAL, encoding="utf-8", newline="") as f:
            return [z for z in csv.DictReader(f) if z.get("aktion") == "verkauf"]

    def position(self):
        return {"inst": "BTC-USDC", "paar": "XBTUSDC", "seite": "long",
                "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
                "stop_pct": 5.0, "nominal": 100.0, "menge": 1.0,
                "eur": 100.0, "usd": 100.0, "pos_id": "p1",
                "eroeffnet_zeit": "2026-10-01T10:00:00+00:00"}


class KrakenMaeMfe(MaeMfeTest):
    SPUR = "kraken"

    def _zyklus(self, z, kurs):
        self.h.kraken.letzter_kurs = lambda paar: kurs
        # _schliesse NICHT ersetzen: es schreibt die Verkaufzeile ins Journal.
        # Ein Attrapp, das nur True zurueckgibt, laesst genau die Zeile weg,
        # um die es hier geht - der Test waere gruen und beweise nichts.
        self.h.pruefe_ausstiege(z, W_KRAKEN, False)

    def test_spaltentabelle(self):
        self.h.journal("2026-10-04T10:00:00+00:00", "papier", "kauf",
                       "XBTUSDC", "100", "100", "1", "95", "110", "test", "p1")
        kopf = self.kopf()
        for feld in ("mfe_pct", "mae_pct", "haltetage"):
            self.assertIn(feld, kopf)

    def test_gegenlauf_ist_ein_wert(self):
        z = {"positionen": [self.position()], "letzte_stops": {}}
        self._zyklus(z, 94.0)            # Stop bei 95 gerissen
        v = self.verkaeufe()
        self.assertTrue(v)
        self.assertEqual(round(float(v[-1]["mae_pct"]), 4), -6.0)

    def test_ohne_gegenlauf_null(self):
        z = {"positionen": [self.position()]}
        self._zyklus(z, 112.0)
        v = self.verkaeufe()
        self.assertTrue(v)
        self.assertEqual(float(v[-1]["mae_pct"]), 0.0)
        self.assertGreater(float(v[-1]["mfe_pct"]), 0.0)

    def test_ueber_die_lebensdauer(self):
        z = {"positionen": [self.position()]}
        self._zyklus(z, 98.0)          # Zyklus 1: unter dem Einstieg, kein Ausstieg
        self.assertEqual(self.verkaeufe(), [])
        self._zyklus(z, 112.0)         # Zyklus 2: Ziel
        v = self.verkaeufe()
        self.assertTrue(v)
        self.assertEqual(round(float(v[-1]["mae_pct"]), 4), -2.0)
        self.assertEqual(round(float(v[-1]["mfe_pct"]), 4), 12.0)


class MosaicMaeMfe(MaeMfeTest):
    SPUR = "mosaic"

    def _zyklus(self, z, kurs):
        k5 = [[0, kurs, kurs, kurs, kurs, 1]]
        self.h.pruefe_ausstiege(z, k5, W_MOSAIC, nur=None)

    def test_spaltentabelle(self):
        self.h.journal(zeit="2026-10-04T10:00:00+00:00", modus="papier",
                       aktion="kauf", inst="BTC-USDC", pos_id="p1",
                       seite="long", preis="100", einsatz_usd="100",
                       stop="95", ziel="110", stop_pct="5", grund="test")
        kopf = self.kopf()
        for feld in ("mfe_pct", "mae_pct", "haltetage"):
            self.assertIn(feld, kopf)

    def test_gegenlauf_ist_ein_wert(self):
        z = {"positionen": [self.position()], "letzte_stops": {}}
        self._zyklus(z, 94.0)            # Stop bei 95 gerissen
        v = self.verkaeufe()
        self.assertTrue(v)
        self.assertEqual(round(float(v[-1]["mae_pct"]), 4), -6.0)

    def test_ohne_gegenlauf_null(self):
        z = {"positionen": [self.position()]}
        self._zyklus(z, 112.0)
        v = self.verkaeufe()
        self.assertTrue(v)
        self.assertEqual(float(v[-1]["mae_pct"]), 0.0)
        self.assertGreater(float(v[-1]["mfe_pct"]), 0.0)

    def test_ueber_die_lebensdauer(self):
        z = {"positionen": [self.position()]}
        self._zyklus(z, 98.0)
        self.assertEqual(self.verkaeufe(), [])
        self._zyklus(z, 112.0)
        v = self.verkaeufe()
        self.assertTrue(v)
        self.assertEqual(round(float(v[-1]["mae_pct"]), 4), -2.0)
        self.assertEqual(round(float(v[-1]["mfe_pct"]), 4), 12.0)

    def test_short_bekommt_das_richtige_vorzeichen(self):
        """Der Richtungsfaktor gehoert dazu (mae.py, Hausfall 03.10.2026):
        bei short ist der STIEGENDE Kurs ein Gegenlauf. Ohne den Faktor
        bekaeme diese Position mae = +7 und damit das falsche Vorzeichen -
        eine Positionsgroesse, die den Verlust als Vorlauf liest.

        Der Ausstieg passiert am Stop ueber dem Einstieg, damit ueberhaupt eine
        Zeile entsteht.
        """
        p = self.position()
        p["seite"] = "short"
        p["stop"], p["ziel"] = 106.0, 90.0
        z = {"positionen": [p], "letzte_stops": {}}
        self._zyklus(z, 107.0)          # steigt gegen short: Stop reisst
        v = self.verkaeufe()
        self.assertTrue(v)
        self.assertEqual(round(float(v[-1]["mae_pct"]), 4), -7.0)
        self.assertEqual(float(v[-1]["mfe_pct"]), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)