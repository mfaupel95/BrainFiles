"""Test: die Wochenend-Sperre heisst, was sie tut, und tut, was sie heisst.

ANLASS - Frage Max, 21.09.2026: "Muesste die nicht wennnichtwochenende
heissen?" Die Logik war richtig, der Name 'we' aber irrefuehrend: er liest
sich wie eine Tatsache ("es ist Wochenende"), gemeint ist eine SPERRE - und
am Freitag ab 19:00 UTC ist noch kein Wochenende, die Sperre greift trotzdem.

Dieser Test haelt beides fest: die Sperrzeiten selbst und die Bedingung im
Einstiegspfad (gesperrt + Aktie/Rohstoff = kein Anlauf; Krypto laeuft weiter,
weil Kryptomaerkte durchgehend handeln).
"""

from __future__ import annotations

import ast
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parents[0]
for p in (HANDEL / "scanner", HANDEL, SPUR):
    if str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))

import wachen_xperp as wx                                           # noqa: E402

W = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))


def _zeit(weekday, stunde, minute=0):
    # Ein Montag als Bezugspunkt, dann auf den gesuchten Wochentag schieben.
    montag = dt.datetime(2026, 9, 21, tzinfo=dt.timezone.utc)
    return (montag + dt.timedelta(days=weekday)).replace(hour=stunde,
                                                         minute=minute)


class Sperrzeiten(unittest.TestCase):
    def test_freitag_vor_dem_stopp_ist_offen(self):
        self.assertFalse(wx.wochenende_sperrt(W, _zeit(4, 18, 59)))

    def test_freitag_ab_dem_stopp_ist_gesperrt(self):
        # freitag_stopp_utc steht auf 19:00 - ab da keine neuen Aktien- und
        # Rohstoff-Anlaeufe, obwohl noch kein Wochenende ist. Genau dieser
        # Fall macht den alten Namen 'we' falsch.
        self.assertTrue(wx.wochenende_sperrt(W, _zeit(4, 19, 0)))
        self.assertTrue(wx.wochenende_sperrt(W, _zeit(4, 23, 30)))

    def test_samstag_und_sonntag_sind_gesperrt(self):
        self.assertTrue(wx.wochenende_sperrt(W, _zeit(5, 12)))
        self.assertTrue(wx.wochenende_sperrt(W, _zeit(6, 12)))

    def test_montag_ist_wieder_offen(self):
        self.assertFalse(wx.wochenende_sperrt(W, _zeit(0, 0, 1)))
        self.assertFalse(wx.wochenende_sperrt(W, _zeit(0, 9)))

    def test_ohne_stoppzeit_keine_sperre(self):
        ohne = dict(W)
        ohne.pop("freitag_stopp_utc", None)
        self.assertFalse(wx.wochenende_sperrt(ohne, _zeit(5, 12)))

    def test_kaputte_stoppzeit_sperrt_nicht(self):
        # Lieber handeln als wegen eines Tippfehlers dauerhaft stillstehen.
        self.assertFalse(wx.wochenende_sperrt(dict(W, freitag_stopp_utc="x"),
                                              _zeit(4, 20)))


class NameUndBedingung(unittest.TestCase):
    """Der Name im Einstiegspfad muss die Sperre benennen, nicht den Tag."""

    @staticmethod
    def _quelle():
        q = (SPUR / "handeln.py").read_text(encoding="utf-8")
        fn = next(n for n in ast.walk(ast.parse(q))
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "pruefe_einstiege")
        return ast.get_source_segment(q, fn)

    def test_sprechender_name(self):
        q = self._quelle()
        self.assertIn('wochenende_gesperrt = s["wochenende"]', q)

    def test_kein_nacktes_we_mehr(self):
        for zeile in self._quelle().split("\n"):
            if "wochenende_gesperrt" in zeile:
                continue
            self.assertNotIn(" we ", zeile)
            self.assertFalse(zeile.strip().startswith("we "))

    def test_nur_aktien_und_rohstoffe_betroffen(self):
        q = self._quelle()
        self.assertIn('if wochenende_gesperrt and kandidat["kategorie"] in '
                      '("aktie", "rohstoff"):', q)
        # Krypto laeuft durch - stuende hier kein Filter, waere die ganze
        # Spur am Wochenende blind.
        self.assertNotIn('if wochenende_gesperrt:\n            continue', q)


if __name__ == "__main__":
    unittest.main()
