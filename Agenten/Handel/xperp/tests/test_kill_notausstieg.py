"""Kill-Notausstieg ohne Freigabekette (Auftrag Max 14.10.2026, Entscheidung 2).

Die Freigabekette begrenzt NEUES Risiko; ein reduceOnly-Marktverkauf schafft keines.
Sie schliesst sich aber oft genau dann, wenn Verluste auflaufen. Der Kill darf
deshalb echte Live-Positionen verkaufen, wenn `kill_verkauf_ohne_freigabekette`
gesetzt ist - nur Basisstufe, OKX-Schluessel vorhanden, nur modus=live, keine
Handpositionen ohne den Schalter `handpositionen_automatisch_schliessen`.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPUR))
sys.path.insert(0, str(SPUR.parent))

import handeln as h                                                  # noqa: E402


def pos(inst, modus="live", herkunft=None):
    p = {"inst": inst, "basis": inst.split("-")[0], "seite": "long", "familie": "krypto",
         "einstieg": 1.0, "nominal": 100.0, "margin": 20.0, "hebel": 5.0,
         "kontrakte": 10.0, "stop": 0.9, "ziel": 1.2, "liq": 0.0, "modus": modus,
         "pos_id": "p-" + inst}
    if herkunft:
        p["herkunft"] = herkunft
    return p


class NotausstiegTest(unittest.TestCase):
    def setUp(self):
        self.journal = []
        for pt in (patch.object(h, "journal", side_effect=lambda **k: self.journal.append(k)),
                   patch.object(h, "_kurs_aktuell", return_value=0.95),
                   patch.object(h.okxf, "markt_schliessen", return_value="1")):
            pt.start()
            self.addCleanup(pt.stop)

    def test_ohne_notaus_bleibt_die_live_position_stehen(self):
        z = {"positionen": [pos("AAA-USD_UM_XPERP-1")]}
        h.flach_stellen(z, live=False, grund="kill_switch")
        self.assertEqual(len(z["positionen"]), 1)
        h.okxf.markt_schliessen.assert_not_called()

    def test_mit_notaus_wird_die_live_position_an_der_boerse_verkauft(self):
        z = {"positionen": [pos("AAA-USD_UM_XPERP-1")]}
        h.flach_stellen(z, live=False, grund="kill_switch", notaus_live=True)
        self.assertEqual(z["positionen"], [])
        h.okxf.markt_schliessen.assert_called_once()
        self.assertEqual(self.journal[-1]["modus"], "live")
        self.assertEqual(self.journal[-1]["grund"], "kill_switch")

    def test_papierposition_wird_nie_an_der_boerse_verkauft(self):
        z = {"positionen": [pos("AAA-USD_UM_XPERP-1", modus="papier"),
                            pos("BBB-USD_UM_XPERP-1")]}
        h.flach_stellen(z, live=False, grund="kill_switch", notaus_live=True)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(h.okxf.markt_schliessen.call_count, 1)        # nur BBB
        self.assertEqual(h.okxf.markt_schliessen.call_args[0][0], "BBB-USD_UM_XPERP-1")
        modi = {j["inst"]: j["modus"] for j in self.journal}
        self.assertEqual(modi["AAA-USD_UM_XPERP-1"], "papier")
        self.assertEqual(modi["BBB-USD_UM_XPERP-1"], "live")

    def test_handposition_bleibt_auch_mit_notaus_stehen(self):
        z = {"positionen": [pos("HAND-USD_UM_XPERP-1", herkunft="boerse_handgriff")]}
        h.flach_stellen(z, live=False, grund="kill_switch", w={}, notaus_live=True)
        self.assertEqual(len(z["positionen"]), 1)
        h.okxf.markt_schliessen.assert_not_called()

    def test_scheitert_der_verkauf_bleibt_die_position(self):
        z = {"positionen": [pos("AAA-USD_UM_XPERP-1")]}
        h.okxf.markt_schliessen.side_effect = RuntimeError("Boerse")
        h.flach_stellen(z, live=False, grund="kill_switch", notaus_live=True)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.journal, [])

    def test_alter_live_weg_unveraendert(self):
        z = {"positionen": [pos("AAA-USD_UM_XPERP-1")]}
        h.flach_stellen(z, live=True, grund="kill_switch")
        self.assertEqual(z["positionen"], [])
        h.okxf.markt_schliessen.assert_called_once()


class VoraussetzungenTest(unittest.TestCase):
    def test_schalter_fehlt_kein_notaus(self):
        with patch.object(h.risikostufe, "live_erlaubt", return_value=True), \
                patch.object(h.okxf, "schluessel_vorhanden", return_value=True):
            self.assertFalse(h.kill_verkauf_ohne_freigabe({}))

    def test_alles_erfuellt(self):
        w = {"kill_verkauf_ohne_freigabekette": True}
        with patch.object(h.risikostufe, "live_erlaubt", return_value=True), \
                patch.object(h.okxf, "schluessel_vorhanden", return_value=True):
            self.assertTrue(h.kill_verkauf_ohne_freigabe(w))

    def test_stufe_nie(self):
        w = {"kill_verkauf_ohne_freigabekette": True}
        with patch.object(h.risikostufe, "live_erlaubt", return_value=False), \
                patch.object(h.okxf, "schluessel_vorhanden", return_value=True):
            self.assertFalse(h.kill_verkauf_ohne_freigabe(w))

    def test_ohne_schluessel_nie(self):
        w = {"kill_verkauf_ohne_freigabekette": True}
        with patch.object(h.risikostufe, "live_erlaubt", return_value=True), \
                patch.object(h.okxf, "schluessel_vorhanden", return_value=False):
            self.assertFalse(h.kill_verkauf_ohne_freigabe(w))

    def test_echte_wache_schaltet_ein(self):
        import json
        w = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))
        self.assertIs(w.get("kill_verkauf_ohne_freigabekette"), True)


if __name__ == "__main__":
    unittest.main()
