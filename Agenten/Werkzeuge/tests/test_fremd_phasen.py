"""Tests fuer fremdrepos.py.

Ausfuehrung: python Agenten/Werkzeuge/tests/test_fremdrepos.py
Kein Mock - echte temporaere JSON-Datei (analog zu test_fremd.py, test_bereiche.py).
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

_WERKZEUGE = Path(__file__).resolve().parents[1]
if str(_WERKZEUGE) not in sys.path:
    sys.path.insert(0, str(_WERKZEUGE))
from fremd_phasen import (
    FremdPhase,
    datei_pfad,
    laden,
    pruefen,
    setzen,
)


def _schreibe(tmp: Path, eintraege: list[dict]) -> Path:
    dp = tmp / "Agenten" / "FREMD-Phasen.json"
    dp.parent.mkdir(parents=True, exist_ok=True)
    for e in eintraege:
        pfad = e.get("pfad", "")
        if pfad:
            (tmp / pfad).mkdir(parents=True, exist_ok=True)
    dp.write_text(json.dumps({"stand": "2026-01-01", "eintraege": eintraege}), encoding="utf-8")
    return tmp


def _basis() -> dict:
    return {
        "name": "test-repo",
        "pfad": "Werkstatt/test-repo",
        "rolle": "Testrepo",
        "phase_aktuell": 2,
        "status": "fertig",
        "blockiert_weil": None,
        "notiz": None,
        "geaendert": "2026-01-01",
    }


class TestLaden(unittest.TestCase):
    def test_laden_leer_bei_fehlender_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp)
            (w / "Agenten").mkdir()
            self.assertEqual(laden(w), [])

    def test_laden_leer_bei_kaputtem_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp)
            dp = w / "Agenten" / "FREMD-Phasen.json"
            dp.parent.mkdir()
            dp.write_text("KEIN JSON", encoding="utf-8")
            self.assertEqual(laden(w), [])

    def test_laden_gueltiger_eintrag(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), [_basis()])
            eintraege = laden(w)
            self.assertEqual(len(eintraege), 1)
            e = eintraege[0]
            self.assertIsInstance(e, FremdPhase)
            self.assertEqual(e.name, "test-repo")
            self.assertEqual(e.phase_aktuell, 2)
            self.assertEqual(e.status, "fertig")

    def test_laden_ueberspringt_ungueltige(self):
        schlechter = {**_basis(), "status": "unbekannt"}
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), [_basis(), schlechter])
            self.assertEqual(len(laden(w)), 1)


class TestSetzen(unittest.TestCase):
    def test_setzen_neu(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp)
            (w / "Agenten").mkdir()
            setzen("neu-repo", 1, "offen", pfad="Werkstatt/neu", rolle="Test", wurzel_dir=w)
            eintraege = laden(w)
            self.assertEqual(len(eintraege), 1)
            self.assertEqual(eintraege[0].name, "neu-repo")
            self.assertEqual(eintraege[0].phase_aktuell, 1)

    def test_setzen_aktualisiert_vorhandenen(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), [_basis()])
            setzen("test-repo", 3, "blockiert", blockiert_weil="Walk-forward negativ", wurzel_dir=w)
            eintraege = laden(w)
            self.assertEqual(len(eintraege), 1)
            self.assertEqual(eintraege[0].phase_aktuell, 3)
            self.assertEqual(eintraege[0].status, "blockiert")
            self.assertEqual(eintraege[0].blockiert_weil, "Walk-forward negativ")

    def test_setzen_aktualisiert_geaendert(self):
        from datetime import date
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), [_basis()])
            setzen("test-repo", 2, "fertig", wurzel_dir=w)
            dp = datei_pfad(w)
            roh = json.loads(dp.read_text(encoding="utf-8"))
            self.assertEqual(roh["eintraege"][0]["geaendert"], str(date.today()))

    def test_setzen_neu_ohne_pfad_wirft_fehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp)
            (w / "Agenten").mkdir()
            with self.assertRaises(ValueError):
                setzen("x", 0, "offen", wurzel_dir=w)


class TestBefund(unittest.TestCase):
    def _befund_exitcode(self, eintraege: list[dict], name: str) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), eintraege)
            for e in laden(w):
                if e.name == name:
                    return 1 if e.status == "blockiert" else 0
        return 2

    def test_befund_blockiert_gibt_exitcode_1(self):
        e = {**_basis(), "status": "blockiert", "blockiert_weil": "Grund"}
        self.assertEqual(self._befund_exitcode([e], "test-repo"), 1)

    def test_befund_ok_gibt_exitcode_0(self):
        self.assertEqual(self._befund_exitcode([_basis()], "test-repo"), 0)

    def test_befund_nicht_gefunden_gibt_exitcode_2(self):
        self.assertEqual(self._befund_exitcode([_basis()], "unbekannt"), 2)


class TestPruefen(unittest.TestCase):
    def test_pruefen_gesunde_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), [_basis()])
            self.assertEqual(pruefen(w), [])

    def test_pruefen_fehlende_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp)
            (w / "Agenten").mkdir()
            befunde = pruefen(w)
            self.assertTrue(any("fehlt" in b for b in befunde))

    def test_pruefen_ungueltige_phase(self):
        e = {**_basis(), "phase_aktuell": 9}
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), [e])
            befunde = pruefen(w)
            self.assertTrue(any("phase_aktuell" in b for b in befunde))

    def test_pruefen_ungueltige_status(self):
        e = {**_basis(), "status": "unklar"}
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), [e])
            befunde = pruefen(w)
            self.assertTrue(any("status" in b for b in befunde))

    def test_pruefen_blockiert_ohne_grund(self):
        e = {**_basis(), "status": "blockiert", "blockiert_weil": None}
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), [e])
            befunde = pruefen(w)
            self.assertTrue(any("blockiert_weil" in b for b in befunde))

    def test_pruefen_doppelter_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = _schreibe(Path(tmp), [_basis(), _basis()])
            befunde = pruefen(w)
            self.assertTrue(any("doppelt" in b for b in befunde))


if __name__ == "__main__":
    unittest.main(verbosity=2)
