"""Task 13: der Orchestrator lauf.einmal().

Zwei Faelle:

* ohne Kerzen-Cache bricht einmal() hart ab und gibt None
* liefert die Suche keinen Kandidaten, entsteht trotzdem ein Ordner mit
  bericht.md, aber ohne commit.txt (kein-Vorschlag-Pfad)

Der zweite Fall haengt an echten wachen.json/konfig.json/spuren.json, ersetzt
aber die teuren Schritte (kerzen.laden, auswerter.befund, suche.suche,
digest.erzeuge) durch Fakes.
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import lauf  # noqa: E402


class TestLaufAbbruch(unittest.TestCase):
    def test_kein_kerzencache_bricht_ab(self):
        alt = lauf.KERZEN_DIR
        try:
            with TemporaryDirectory() as d:
                lauf.KERZEN_DIR = Path(d) / "leer"
                r = lauf.einmal("spur1", kerzen_holen=False)
                self.assertIsNone(r)
        finally:
            lauf.KERZEN_DIR = alt


def _basis_wf():
    return {
        "gesamt": {"netto_gv_je_runde": -0.1, "n": 5, "max_drawdown": 1.0},
        "fenster": [],
    }


class TestLaufKeinVorschlag(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        self._berichte_alt = lauf.BERICHTE
        lauf.BERICHTE = Path(self._tmp.name)
        self.addCleanup(setattr, lauf, "BERICHTE", self._berichte_alt)

        p = mock.patch.object(
            lauf.kerzen, "laden",
            side_effect=lambda inst, cache_dir=None: ([[0, 1, 2, 3, 4, 5]], 1.0))
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.auswerter, "befund",
            side_effect=lambda spur, konfig, ordner: {"befunde": [],
                                                      "runden_gesamt": 5})
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.suche, "suche",
            side_effect=lambda *a, **k: {
                "kandidat": None,
                "basis_wf": _basis_wf(),
                "kandidat_wf": None,
                "auswertungen": 1,
                "grund": "nur 5 OOS-Runden (>= 20 noetig)",
                "aenderungen": {},
            })
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.digest, "erzeuge",
            side_effect=lambda *a, **k: {"empfehlungen": "", "lehren": "",
                                        "uebersprungen": "LLM-Modus aus"})
        p.start(); self.addCleanup(p.stop)

    def test_zu_wenig_runden_gibt_kein_vorschlag(self):
        p = lauf.einmal("spur1", kerzen_holen=False)
        self.assertIsNotNone(p)
        self.assertTrue((p / "bericht.md").exists())
        self.assertFalse((p / "commit.txt").exists())

    def test_zweiter_lauf_raeumt_alte_artefakte(self):
        # Ein zweiter Lauf am selben Tag nutzt denselben Ordner. Reste des
        # ersten Laufs (wachen.neu.json, commit.txt, ANGEFRAGT ...) muessen
        # verschwinden - sonst wendet ein spaeteres /ja einen Mischstand an.
        jetzt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ordner = Path(self._tmp.name) / "2026-01-01-spur1"
        ordner.mkdir(parents=True)
        (ordner / "wachen.neu.json").write_text("{}", encoding="utf-8")
        (ordner / "commit.txt").write_text("alt", encoding="utf-8")
        (ordner / "bewertung.patch").write_text("alt", encoding="utf-8")
        (ordner / "ANGEFRAGT").write_text("x", encoding="utf-8")

        # Nachbar-Ablagen duerfen nicht angefasst werden.
        erledigt = Path(self._tmp.name) / "erledigt" / "alt-spur1"
        erledigt.mkdir(parents=True)
        (erledigt / "bericht.md").write_text("archiv", encoding="utf-8")

        p = lauf.einmal("spur1", kerzen_holen=False, jetzt=jetzt)
        self.assertEqual(p, ordner)
        self.assertFalse((ordner / "wachen.neu.json").exists())
        self.assertFalse((ordner / "commit.txt").exists())
        self.assertFalse((ordner / "bewertung.patch").exists())
        self.assertFalse((ordner / "ANGEFRAGT").exists())
        self.assertTrue((ordner / "bericht.md").exists())
        self.assertTrue((erledigt / "bericht.md").exists())


class TestLaufHoldoutUndAusrichtung(unittest.TestCase):
    """Review-Funde C1/I2: basis_wf=None darf nicht abstuerzen, und
    Ausrichtungs-Hinweise muessen im Bericht landen - end-to-end durch
    lauf.einmal(), nicht nur auf vorschlag.py-Ebene."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        self._berichte_alt = lauf.BERICHTE
        lauf.BERICHTE = Path(self._tmp.name)
        self.addCleanup(setattr, lauf, "BERICHTE", self._berichte_alt)

        p = mock.patch.object(
            lauf.kerzen, "laden",
            side_effect=lambda inst, cache_dir=None: ([[0, 1, 2, 3, 4, 5]], 1.0))
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.auswerter, "befund",
            side_effect=lambda spur, konfig, ordner: {"befunde": [],
                                                      "runden_gesamt": 0})
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.digest, "erzeuge",
            side_effect=lambda *a, **k: {"empfehlungen": "", "lehren": "",
                                        "uebersprungen": "LLM-Modus aus"})
        p.start(); self.addCleanup(p.stop)

    def test_zu_wenig_historie_fuer_holdout_stuerzt_nicht_ab(self):
        p = mock.patch.object(
            lauf.suche, "suche",
            side_effect=lambda *a, **k: {
                "kandidat": None, "basis_wf": None, "kandidat_wf": None,
                "auswertungen": 0, "grund": "zu wenig Historie fuer Holdout",
                "aenderungen": {}, "holdout_basis": None,
                "holdout_kandidat": None, "fast_kandidat": None,
            })
        p.start(); self.addCleanup(p.stop)

        ordner = lauf.einmal("spur1", kerzen_holen=False)
        self.assertIsNotNone(ordner)
        text = (ordner / "bericht.md").read_text("utf-8")
        self.assertIn("zu wenig Historie fuer Holdout", text)

    def test_ausrichtungs_hinweise_landen_im_bericht(self):
        p = mock.patch.object(
            lauf.suche, "suche",
            side_effect=lambda *a, **k: {
                "kandidat": None, "basis_wf": _basis_wf(), "kandidat_wf": None,
                "auswertungen": 1, "grund": "nur 5 OOS-Runden (>= 20 noetig)",
                "aenderungen": {},
            })
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.ruecktest, "ausrichten",
            side_effect=lambda kerzen: (
                kerzen, ["XYZ-USDT verworfen: 5 von 20 Tagen (< 90%)"]))
        p.start(); self.addCleanup(p.stop)

        ordner = lauf.einmal("spur1", kerzen_holen=False)
        text = (ordner / "bericht.md").read_text("utf-8")
        self.assertIn("XYZ-USDT verworfen", text)


class TestLaufPfadAufloesung(unittest.TestCase):
    """auswerter.befund muss die Spur-Pfade absolut sehen - sonst loest es
    spur["journal"]/spur["berichte"] gegen das CWD auf und liest aus der
    Repo-Wurzel gestartet ein leeres Journal."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        self._berichte_alt = lauf.BERICHTE
        lauf.BERICHTE = Path(self._tmp.name)
        self.addCleanup(setattr, lauf, "BERICHTE", self._berichte_alt)

        p = mock.patch.object(
            lauf.kerzen, "laden",
            side_effect=lambda inst, cache_dir=None: ([[0, 1, 2, 3, 4, 5]], 1.0))
        p.start(); self.addCleanup(p.stop)

        self.gesehene_spur = {}

        def _fake_befund(spur, konfig, ordner):
            self.gesehene_spur.update(spur)
            return {"befunde": [], "runden_gesamt": 5}

        p = mock.patch.object(lauf.auswerter, "befund", side_effect=_fake_befund)
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.suche, "suche",
            side_effect=lambda *a, **k: {
                "kandidat": None,
                "basis_wf": _basis_wf(),
                "kandidat_wf": None,
                "auswertungen": 1,
                "grund": "nur 5 OOS-Runden (>= 20 noetig)",
                "aenderungen": {},
            })
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.digest, "erzeuge",
            side_effect=lambda *a, **k: {"empfehlungen": "", "lehren": "",
                                        "uebersprungen": "LLM-Modus aus"})
        p.start(); self.addCleanup(p.stop)

    def test_journalpfad_wird_absolut_aufgeloest(self):
        lauf.einmal("spur1", kerzen_holen=False)
        journal = self.gesehene_spur["journal"]
        self.assertTrue(Path(journal).is_absolute(),
                        "journal-Pfad nicht absolut: %r" % journal)
        self.assertTrue(
            Path(journal).as_posix().endswith("scanner/handelsjournal.csv"),
            "unerwarteter journal-Pfad: %r" % journal)
        self.assertTrue(Path(self.gesehene_spur["berichte"]).is_absolute())


class TestLaufSpur3(unittest.TestCase):
    """End-to-End: lauf.einmal('spur3') nutzt kraken_kerzen statt kerzen und
    ein KrakenModell statt SPOT_MODELL, ohne spur1 zu beruehren."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._berichte_alt = lauf.BERICHTE
        lauf.BERICHTE = Path(self._tmp.name)
        self.addCleanup(setattr, lauf, "BERICHTE", self._berichte_alt)

        # spuren.json liefert fuer spur3 echte Pfade (Task 6 legt sie an) -
        # hier nur kraken_kerzen.laden faken, damit der Test ohne Netz und
        # ohne echtes kraken/wachen.json laeuft.
        import kraken_kerzen
        p = mock.patch.object(
            kraken_kerzen, "laden",
            side_effect=lambda inst, cache_dir=None: (
                [[i * 86400000, 1.0, 1.0, 1.0, 1.0, 1.0] for i in range(5)],
                1.0))
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.auswerter, "befund",
            side_effect=lambda spur, konfig, ordner: {"befunde": [],
                                                      "runden_gesamt": 0})
        p.start(); self.addCleanup(p.stop)
        p = mock.patch.object(
            lauf.digest, "erzeuge",
            side_effect=lambda *a, **k: {"empfehlungen": "", "lehren": "",
                                        "uebersprungen": "LLM-Modus aus"})
        p.start(); self.addCleanup(p.stop)

    def test_spur3_laeuft_ohne_absturz_und_nutzt_kraken_kerzen(self):
        ordner = lauf.einmal("spur3", kerzen_holen=False)
        self.assertIsNotNone(ordner)
        self.assertTrue((ordner / "bericht.md").exists())

    def test_spur1_unveraendert_nutzt_weiter_kerzen_modul(self):
        # Regression: spur1 ohne kerzen_modul-Schluessel laeuft weiter ueber
        # das oben schon gemockte lauf.kerzen (Bestandsmock in setUp der
        # Nachbarklassen) - hier nur die Modulauswahl selbst pruefen.
        self.assertIs(lauf._kerzen_modul({"name": "spur1"}), lauf.kerzen)

    def test_spur3_waehlt_kraken_kerzen_modul(self):
        import kraken_kerzen
        self.assertIs(lauf._kerzen_modul({"kerzen_modul": "kraken_kerzen"}),
                     kraken_kerzen)


if __name__ == "__main__":
    unittest.main()
