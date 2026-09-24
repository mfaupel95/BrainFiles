"""Buchbereinigung beim ersten Live-Lauf in swap.

Anlass (22.09.2026): swap fuehrt ein gemeinsames Buch fuer Papier und Live.
Wird das Freigabefenster geoeffnet waehrend Papier-Positionen im Buch liegen,
bucht der Live-Lauf diese durch. pruefe_ausstiege() pruefte kein modus-Feld
und haette im naechsten Stop-Ausstieg ein echtes okxf.markt_schliessen() auf
eine Position geschickt, die an der Boerse nie existiert hat.

Muster: scanner/tests/test_handeln_altlasten.py, xperp gleiches Muster.
"""

import csv
import io
import os
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
SPUR = HIER.parent
HANDEL = SPUR.parent
for p in (str(HANDEL / "scanner"), str(HANDEL), str(SPUR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln as h  # noqa: E402

assert h.__file__.startswith(str(SPUR)), "falsches handeln: %s" % h.__file__


def _pos(modus="papier", inst="TRX-USDT-SWAP"):
    return {
        "inst": inst, "basis": "TRX", "seite": "long", "familie": "krypto",
        "einstieg": 0.342, "stop": 0.338, "ziel": 0.350, "liq": 0.275,
        "kontrakte": 0.73, "nominal": 249.8, "margin": 49.96, "hebel": 5,
        "gebuehr_taker": 0.0005, "eroeffnet": "2026-09-22",
        "eroeffnet_zeit": "2026-09-22T08:00:00+00:00",
        "funding_zuletzt": "2026-09-22T08:00:00+00:00",
        "funding_summe": 0.0, "modus": modus,
    }


def _pos_kein_modus(inst="TRX-USDT-SWAP"):
    p = _pos()
    del p["modus"]
    return p


class BuchbereinigungTest(unittest.TestCase):
    """bueche_papier_altlasten_aus entfernt nur ALTBESTAND ohne modus-Feld.

    Seit 25.09.2026 traegt jede Position ein modus-Feld, und pruefe_ausstiege()
    sowie flach_stellen() fassen nur noch den eigenen Zweig an. Eine
    Papier-Position im Live-Buch ist damit harmlos und wird NICHT mehr
    ausgebucht - sie haette sonst nie Stop oder Ziel erreicht (Journal
    22.-24.09.2026: dreimal eroeffnen, 13 bis 28 Minuten spaeter
    buchbereinigung).
    """

    def setUp(self):
        self.alt_journal = h.JOURNAL
        self.buf = io.StringIO()
        h.JOURNAL = self.buf
        self._orig_journal = h.journal

        def _journal_buf(**felder):
            neu = self.buf.tell() == 0
            w = csv.DictWriter(self.buf, fieldnames=h.SPALTEN, extrasaction="ignore")
            if neu:
                w.writeheader()
            w.writerow({k: felder.get(k, "") for k in h.SPALTEN})

        h.journal = _journal_buf

    def tearDown(self):
        h.JOURNAL = self.alt_journal
        h.journal = self._orig_journal

    def test_papier_position_bleibt_im_buch(self):
        """Papier ist kein Altbestand: die Position darf ihren Ausstieg erleben."""
        z = {"positionen": [_pos(modus="papier")], "letzte_stops": {}}
        n = h.bueche_papier_altlasten_aus(z)
        self.assertEqual(n, 0)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.buf.getvalue(), "")

    def test_kein_modus_feld_wird_ausgebucht(self):
        z = {"positionen": [_pos_kein_modus()], "letzte_stops": {}}
        n = h.bueche_papier_altlasten_aus(z)
        self.assertEqual(n, 1)
        self.assertEqual(z["positionen"], [])

    def test_live_position_bleibt(self):
        live = _pos(modus="live")
        z = {"positionen": [live], "letzte_stops": {}}
        n = h.bueche_papier_altlasten_aus(z)
        self.assertEqual(n, 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_gemischt_nur_altbestand_raus(self):
        """Nur die Position OHNE modus-Feld faellt - Papier und Live bleiben."""
        z = {"positionen": [_pos(modus="papier"),
                            _pos(modus="live", inst="XAU-USDT-SWAP"),
                            _pos_kein_modus(inst="BZ-USDT-SWAP")],
             "letzte_stops": {}}
        n = h.bueche_papier_altlasten_aus(z)
        self.assertEqual(n, 1)
        self.assertEqual(sorted(p["inst"] for p in z["positionen"]),
                         ["TRX-USDT-SWAP", "XAU-USDT-SWAP"])

    def test_lauf_ruft_bereinigung_im_live_modus(self):
        """Im Live-Lauf wird bueche_papier_altlasten_aus am Anfang aufgerufen."""
        quelle = h.bueche_papier_altlasten_aus.__code__.co_filename
        lauf_src = open(os.path.join(str(SPUR), "handeln.py"),
                        encoding="utf-8").read()
        self.assertIn("bueche_papier_altlasten_aus",
                      lauf_src,
                      "bueche_papier_altlasten_aus muss in handeln.py stehen")
        # Pruefen dass der Aufruf im Live-Zweig steht (nach 'if live:')
        idx_live = lauf_src.find("live = True")
        idx_buch = lauf_src.find("bueche_papier_altlasten_aus", idx_live)
        self.assertGreater(
            idx_buch, idx_live,
            "bueche_papier_altlasten_aus muss NACH 'live = True' stehen")


if __name__ == "__main__":
    unittest.main(verbosity=2)
