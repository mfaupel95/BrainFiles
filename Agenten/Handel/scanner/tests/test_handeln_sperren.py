"""Die Freigabe von Hand in der Fassung fuer den Dauerbetrieb.

Prueft die siebte Sperre von scanner/handeln.py: Ohne Sitzung am Bildschirm
muss ein offenes Zeitfenster (freigabefenster.py, /ja am Handy) die Freigabe
tragen - und die Begruendung muss so bleiben, wie dauerlauf.nur_fenster_fehlt
sie liest. Sonst wird nie gefragt, und ein /ja bleibt folgenlos (Befund
10.09.2026).

Kein Netz: okx.schluessel_vorhanden, sitzung_da und zeitfenster_offen werden
je Test gesetzt und in addCleanup zurueckgestellt.
"""

import json
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))          # scanner/ - handeln, okx, scan
sys.path.insert(0, str(HIER.parent.parent))   # Handel/ - freigabe, freigabefenster

import handeln  # noqa: E402


def _s(**over):
    base = {"freigabe_erfuellt": True, "herzschlag_frisch": True,
            "ev_negativ": False, "rollierender_ev": 1.0, "ruecklauf_usd": 0.0}
    base.update(over)
    return base


class TestSperrenLive(unittest.TestCase):
    def setUp(self):
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        self.w["handel_erlaubt"] = True
        self.addCleanup(setattr, handeln.okx, "schluessel_vorhanden",
                        handeln.okx.schluessel_vorhanden)
        self.addCleanup(setattr, handeln, "sitzung_da", handeln.sitzung_da)
        self.addCleanup(setattr, handeln, "zeitfenster_offen",
                        handeln.zeitfenster_offen)
        handeln.okx.schluessel_vorhanden = lambda: True
        handeln.sitzung_da = lambda: True
        handeln.zeitfenster_offen = lambda: False

    def test_sitzung_am_bildschirm_gibt_frei(self):
        self.assertEqual(handeln.sperren_live(self.w, _s()), [])

    def test_zeitfenster_gibt_frei_wenn_niemand_davorsitzt(self):
        handeln.sitzung_da = lambda: False
        handeln.zeitfenster_offen = lambda: True
        self.assertEqual(handeln.sperren_live(self.w, _s()), [])

    def test_ohne_beides_gesperrt(self):
        handeln.sitzung_da = lambda: False
        g = handeln.sperren_live(self.w, _s())
        self.assertEqual(len(g), 1)
        self.assertIn("Freigabefenster", g[0])

    def test_begruendung_bleibt_fuer_den_dauerlauf_lesbar(self):
        handeln.sitzung_da = lambda: False
        g = handeln.sperren_live(self.w, _s())
        for grund in g:
            self.assertNotIn(";", grund)
            self.assertNotIn(":", grund)
        self.assertEqual(len(g), 1)
        self.assertIn("Freigabefenster", g[0])

    def test_die_uebrigen_sperren_bleiben(self):
        handeln.sitzung_da = lambda: True
        self.w["handel_erlaubt"] = False
        self.assertTrue(any("handel_erlaubt" in x
                            for x in handeln.sperren_live(self.w, _s())))
        self.w["handel_erlaubt"] = True
        handeln.okx.schluessel_vorhanden = lambda: False
        self.assertTrue(any("OKX" in x
                            for x in handeln.sperren_live(self.w, _s())))
        handeln.okx.schluessel_vorhanden = lambda: True
        self.assertTrue(any("freigabe" in x for x in
                            handeln.sperren_live(self.w, _s(freigabe_erfuellt=False))))
        self.assertTrue(any("Herzschlag" in x for x in
                            handeln.sperren_live(self.w, _s(herzschlag_frisch=False))))
        self.assertTrue(any("EV" in x for x in
                            handeln.sperren_live(self.w, _s(ev_negativ=True))))


class TestZeitfensterOffen(unittest.TestCase):
    """Faellt freigabefenster aus, gilt NICHT freigegeben - im Zweifel Papier."""

    def test_ohne_modul_false(self):
        # handeln laedt freigabefenster ueber den PFAD und haelt die Referenz
        # als Modulattribut - ein Eintrag in sys.modules erreicht sie nicht
        # mehr. Geprueft wird die REGEL: ein Ladefehler gilt als "zu".
        echt = handeln.freigabefenster
        handeln.freigabefenster = None
        try:
            self.assertFalse(handeln.zeitfenster_offen())
        finally:
            handeln.freigabefenster = echt


class TestFreigabeProtokoll(unittest.TestCase):
    """Die Freigabe ueber das Zeitfenster muss im Journal stehen."""

    def setUp(self):
        import freigabe
        self.zeilen = []
        self.addCleanup(setattr, freigabe, "audit", freigabe.audit)
        freigabe.audit = self.zeilen.append

    def test_jeder_einstieg_wird_protokolliert(self):
        vs = [{"inst": "LINK-USDC", "einstieg": 11.8, "stop": 11.0,
               "ziel": 13.3, "stop_pct": 6.4, "usd": 50.0}]
        z = {"positionen": [{"usd": 100.0}]}
        handeln.freigabe_protokoll(vs, z, _s())
        self.assertEqual(len(self.zeilen), 1)
        e = self.zeilen[0]
        self.assertEqual(e["quelle"], "zeitfenster")
        self.assertEqual(e["spur"], "scanner")
        self.assertEqual(e["gebunden"], 50.0)
        self.assertEqual(e["offene_positionen"], 1)


class TestAuditOeffentlich(unittest.TestCase):
    def test_freigabe_hat_audit(self):
        import freigabe
        self.assertTrue(callable(freigabe.audit))


if __name__ == "__main__":
    unittest.main()
