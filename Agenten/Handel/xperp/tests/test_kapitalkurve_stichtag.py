"""Stichtag der Kapitalkurve (wachen.json "kapitalkurve_ab").

Regel: Runden VOR dem Stichtag zaehlen weiter fuer Statistik und
Erwartungswert, aber NICHT fuer Hoechststand/Ruecklauf/Kill. Ein alter,
aufgeblaehter Peak (Phantomzeilen, Handpositions-Buchungen) darf den
Kill-Switch nicht ueber Wochen binden.

Gegenproben: ohne Feld zaehlen alle Runden (Altverhalten); ein Stichtag in
der Zukunft leert die Kurve (hoch=0, rueck=0); die Rundenzahl der Statistik
bleibt in ALLEN Faellen gleich.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../scanner")
import wachen_xperp as wx  # noqa: E402

KOPF = ("zeit,inst,aktion,modus,margin_usd,preis,kontrakte,nominal_usd,"
        "pnl_usd,grund,seite,pos_id\n")


def journal(runden):
    """runden = [(zeit, inst, gv)] - eroeffnen mit margin 100, schliessen
    mit margin 100+gv, damit die Paarung exakt gv ergibt."""
    zeilen = [KOPF]
    for i, (zeit, inst, gv) in enumerate(runden):
        pid = "p%d" % i
        zeilen.append("%s,%s,eroeffnen,live,100,100,1,100,0,einstieg,long,%s\n"
                      % (zeit, inst, pid))
        zeilen.append("%s,%s,schliessen,live,%s,100,1,100,%s,stop,long,%s\n"
                      % (zeit, inst, 100 + gv, gv, pid))
    return "".join(zeilen)


RUNDEN = [
    ("2026-10-05T10:00:00+00:00", "AAA", 300.0),   # Alt-Peak, Phantom-Aera
    ("2026-10-08T10:00:00+00:00", "BBB", 200.0),   # Peak 500, Alt-Aera
    ("2026-10-12T10:00:00+00:00", "CCC", -100.0),  # ab Stichtag: -100
    ("2026-10-14T10:00:00+00:00", "DDD", -50.0),   # neu: -150
]


class StichtagTest(unittest.TestCase):
    def _lage(self, wachen_extra):
        with tempfile.TemporaryDirectory() as tmp:
            jp = os.path.join(tmp, "j.csv")
            open(jp, "w", newline="", encoding="utf-8").write(journal(RUNDEN))
            w = dict(json.load(open(
                os.path.join(os.path.dirname(os.path.abspath(wx.__file__)),
                             "wachen.json"), encoding="utf-8")))
            # Das echte Feld der Wachen darf den Test nicht faelschen: jeder
            # Fall setzt seinen Stichtag AUSDRUECKLICH (None = alle Runden).
            w["kapitalkurve_ab"] = wachen_extra.pop("kapitalkurve_ab", None)
            w.update(wachen_extra)
            return wx.lage(w, jp, {})

    def test_ohne_feld_zaehlen_alle_runden(self):
        # kum: 300 -> 500 -> 400 -> 350; Peak 500, Ruecklauf 500-350 = 150.
        s = self._lage({})
        self.assertAlmostEqual(s["hoechststand_usd"], 500.0, places=2)
        self.assertAlmostEqual(s["ruecklauf_usd"], 150.0, places=2)

    def test_stichtag_16_10_leert_die_kurve(self):
        s = self._lage({"kapitalkurve_ab": "2026-10-16"})
        self.assertAlmostEqual(s["hoechststand_usd"], 0.0, places=2)
        self.assertAlmostEqual(s["ruecklauf_usd"], 0.0, places=2)

    def test_stichtag_12_10_nimmt_nur_die_neuen_runden(self):
        s = self._lage({"kapitalkurve_ab": "2026-10-12"})
        self.assertAlmostEqual(s["hoechststand_usd"], 0.0, places=2)
        self.assertAlmostEqual(s["ruecklauf_usd"], 150.0, places=2)

    def test_stichtag_aendert_nicht_die_statistik(self):
        ohne = self._lage({})
        mit = self._lage({"kapitalkurve_ab": "2026-10-12"})
        self.assertEqual(ohne["runden_gesamt"], mit["runden_gesamt"])
        self.assertEqual(ohne["runden_gesamt"], 4)

    def test_stichtag_in_der_vergangenheit_ist_wie_alle_runden(self):
        s = self._lage({"kapitalkurve_ab": "2026-01-01"})
        self.assertAlmostEqual(s["hoechststand_usd"], 500.0, places=2)


if __name__ == "__main__":
    unittest.main()
