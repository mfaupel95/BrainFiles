"""Tests fuer den Sammler der Backtest-Urteile.

Geprueft werden die zwei Teile, die still schiefgehen koennen:
  - die URTEILE der Motoren aus ihrer Ausgabe lesen (drei verschiedene Formen),
  - die drei Felder in eine `wachen.json` schreiben, ohne etwas anderes zu
    veraendern - und ohne je `handel_erlaubt` oder `freigabe.erfuellt` anzufassen.

Kein Netz, kein Motor: `motor_laufen` wird ersetzt, gearbeitet wird in einem
Temp-Ordner (Modulvariable HIER). Die Wachen sind FIXTURES, keine Kopien der
echten Werte - ein Test, der auf den heutigen Stand baut, bricht beim ersten
umgelegten Schalter.

Direkt ausfuehrbar:  python tests/test_backtest_urteile.py
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))          # Handel/ - backtest_urteile

import backtest_urteile as bu                                  # noqa: E402

WACHEN_MIT_BACKTEST = """{
  "handel_erlaubt": false,
  "freigabe": {
    "erfuellt": false,
    "backtest_bestanden": false,
    "papierlauf_min_wochen": 6,
    "geprueft_am": null
  },
  "journal_zweitziel": "Q:\\\\Handel_Journal\\\\fixture"
}
"""

WACHEN_OHNE_FELD = """{
  "handel_erlaubt": false,
  "freigabe": {
    "erfuellt": false,
    "papierlauf_min_wochen": 6
  }
}
"""

WACHEN_OHNE_BLOCK = """{
  "handel_erlaubt": false,
  "stufen": 12,
  "journal_zweitziel": "Q:\\\\Handel_Journal\\\\fixture"
}
"""


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.alt = bu.HIER
        bu.HIER = Path(self.tmp.name)
        self.addCleanup(setattr, bu, "HIER", self.alt)

    def _wachen(self, inhalt, spur="gitter"):
        d = Path(self.tmp.name) / spur
        d.mkdir(parents=True, exist_ok=True)
        p = d / "wachen.json"
        p.write_text(inhalt, encoding="utf-8")
        return p


class Schreiben(Basis):
    def test_bestanden_wird_gesetzt_und_nichts_anderes_veraendert(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        vorher = json.loads(p.read_text("utf-8"))
        self.assertIsNone(bu.freigabe_schreiben("gitter", True, "Gitter schlaegt Halten"))
        nachher = json.loads(p.read_text("utf-8"))
        self.assertTrue(nachher["freigabe"]["backtest_bestanden"])
        # Alles andere bleibt gleich - auch der Handels-Schalter.
        self.assertEqual(nachher["handel_erlaubt"], vorher["handel_erlaubt"])
        self.assertFalse(nachher["handel_erlaubt"])
        self.assertFalse(nachher["freigabe"]["erfuellt"])
        for k, v in vorher.items():
            if k != "freigabe":
                self.assertEqual(nachher[k], v, "%s wurde angefasst" % k)
        self.assertEqual(nachher["freigabe"]["papierlauf_min_wochen"], 6)
        self.assertIsNone(nachher["freigabe"]["geprueft_am"])

    def test_fehlendes_feld_wird_eingefuegt(self):
        p = self._wachen(WACHEN_OHNE_FELD)
        bu.freigabe_schreiben("gitter", False, "unter 10 Verlierer")
        f = json.loads(p.read_text("utf-8"))["freigabe"]
        self.assertFalse(f["backtest_bestanden"])
        self.assertIn("unter 10 Verlierer", f["backtest_urteil"])
        self.assertRegex(str(f["backtest_geprueft_am"]), r"^\d{4}-\d{2}-\d{2}$")

    def test_ohne_freigabe_block_wird_einer_angelegt(self):
        p = self._wachen(WACHEN_OHNE_BLOCK)
        bu.freigabe_schreiben("gitter", True, "Gitter schlaegt Halten")
        d = json.loads(p.read_text("utf-8"))
        self.assertTrue(d["freigabe"]["backtest_bestanden"])
        self.assertFalse(d["freigabe"]["erfuellt"], "erfuellt bleibt unberuehrt")
        self.assertEqual(d["stufen"], 12)
        self.assertFalse(d["handel_erlaubt"])

    def test_zweiter_lauf_aendert_nichts_mehr(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        bu.freigabe_schreiben("gitter", True, "gleich")
        erster = p.read_bytes()
        hinweis = bu.freigabe_schreiben("gitter", True, "gleich")
        self.assertEqual(p.read_bytes(), erster)
        self.assertIsNone(hinweis)

    def test_sicherung_wird_einmal_angelegt(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        bu.freigabe_schreiben("gitter", True, "erster")
        baks = list(p.parent.glob("wachen.json.bak-*"))
        self.assertEqual(len(baks), 1)
        self.assertEqual(baks[0].read_text("utf-8"), WACHEN_MIT_BACKTEST)

    def test_vorschau_schreibt_nicht(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        hinweis = bu.freigabe_schreiben("gitter", True, "x", vorschau=True)
        self.assertIn("VORSCHAU", hinweis)
        self.assertEqual(p.read_text("utf-8"), WACHEN_MIT_BACKTEST)

    def test_urteil_mit_anfuehrungszeichen_bleibt_lesbar(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        bu.freigabe_schreiben("gitter", False, 'Urteil mit "Zitat" drin')
        d = json.loads(p.read_text("utf-8"))
        self.assertIn("Zitat", d["freigabe"]["backtest_urteil"])


class UrteileLesen(Basis):
    """Die drei Ausgabeformen der Motoren."""

    def test_gitter_json_zeile(self):
        text = ('irgendein Geschwaetz\n'
                '{"start": 100.0, "ende": 120.0, "rendite_pct": 2.14,'
                ' "halten_pct": 15.15, "zyklen": 7, "kerzen": 1344}\n')
        with patch.object(bu, "motor_laufen", return_value=(text, None)):
            bestanden, urteil, kennzahlen = bu.urteil_gitter({"stufen": 12})
        self.assertFalse(bestanden)
        self.assertIn("2.14", urteil)
        self.assertIn("15.15", urteil)
        self.assertEqual(kennzahlen["zyklen"], 7)

    def test_gitter_besser_als_halten_ist_bestanden(self):
        text = '{"rendite_pct": -17.7, "halten_pct": -31.95, "zyklen": 12}'
        with patch.object(bu, "motor_laufen", return_value=(text, None)):
            bestanden, urteil, _ = bu.urteil_gitter({})
        self.assertTrue(bestanden)

    def test_orbk_urteilszeilen(self):
        text = ("=== ETH_USD | Einstiegsmodell: schluss | 7 Sessions ===\n"
                "  URTEIL: Nein - die 81-%-Behauptung faellt (unter 10 Verlierer): "
                "Trefferquote 43%, EV +6.05\n")
        with patch.object(bu, "motor_laufen", return_value=(text, None)):
            bestanden, urteil, kz = bu.urteil_orbk({})
        self.assertFalse(bestanden)
        self.assertIn("zu wenig Daten", urteil)
        self.assertEqual(len(kz["urteile"]), 1)

    def test_orbk_ein_ja_reicht(self):
        text = ("URTEIL: Nein - die 81-%-Behauptung faellt (EV im Fenster <= 0)\n"
                "URTEIL: Ja - Trefferquote ueber Break-even, EV +6.05\n")
        with patch.object(bu, "motor_laufen", return_value=(text, None)):
            bestanden, urteil, _ = bu.urteil_orbk({})
        self.assertTrue(bestanden)

    def test_motor_ohne_urteil_ist_nicht_ermittelbar(self):
        with patch.object(bu, "motor_laufen", return_value=("nur Gelaber", None)):
            bestanden, urteil, _ = bu.urteil_orbk({})
        self.assertIsNone(bestanden)
        self.assertIn("kein URTEIL", urteil)

    def test_motorfehler_ist_nicht_ermittelbar(self):
        with patch.object(bu, "motor_laufen", return_value=("", "kein Motor: x")):
            bestanden, urteil, _ = bu.urteil_gitter({})
        self.assertIsNone(bestanden)
        self.assertIn("kein Motor", urteil)

    def test_nautilus_liest_die_ergebnisdatei(self):
        d = Path(self.tmp.name) / "nautilus"
        d.mkdir(parents=True, exist_ok=True)
        ziel = d / "backtest_grid_ergebnis.json"

        def motor(*a, **kw):
            ziel.write_text(json.dumps({"differenz_zu_hold": 1425.3,
                                        "buy_and_hold_prozent": -31.95}),
                            encoding="utf-8")
            return "Ergebnis gespeichert", None

        ziel.write_text(json.dumps({"differenz_zu_hold": 0.0}), encoding="utf-8")
        with patch.object(bu, "motor_laufen", side_effect=motor):
            bestanden, urteil, kz = bu.urteil_nautilus({})
        self.assertTrue(bestanden)
        self.assertIn("1425", urteil)


class Sicherheitsnetz(Basis):
    """Was der Sammler nie tut."""

    def test_handel_erlaubt_bleibt_falsch_auch_bei_bestandenem_urteil(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        bu.freigabe_schreiben("gitter", True, "bestanden")
        roh = p.read_text("utf-8")
        self.assertIn('"handel_erlaubt": false', roh)
        self.assertIn('"erfuellt": false', roh)

    def test_kein_freigabe_block_ergibt_einen_hinweis_statt_eines_schreibens(self):
        # Wenn eine Datei gar keinen Anker hat, wird nichts geraten.
        p = self._wachen("{ \"handel_erlaubt\": false }\n")
        vorher = p.read_bytes()
        with patch.object(bu, "_freigabe_spanne", return_value=None):
            hinweis = bu.freigabe_schreiben("gitter", True, "x")
        self.assertIn("kein freigabe-Block", hinweis)
        self.assertEqual(p.read_bytes(), vorher)


if __name__ == "__main__":
    unittest.main()
