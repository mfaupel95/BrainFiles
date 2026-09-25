"""Tests fuer swap/kandidaten.py - ohne Netz, ohne Order, ohne Zustandsdatei.

Der Order-Pfad wird nicht benutzt, sondern geprueft: Der Modulquelltext darf
keine Order-Funktion nennen. Ein Test, der eine Order erreichen koennte, waere
der Fehler, nicht der Nachweis.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SWAP = os.path.dirname(HIER)
if SWAP not in sys.path:
    sys.path.insert(0, SWAP)

import kandidaten as k                                        # noqa: E402
import okxf                                                   # noqa: E402


def kerzen(basis):
    """Kerzen in der Form, die okxf.kerzen() liefert: [ts, o, h, l, c, vol].

    Aufsteigend, mit echter Bewegung - sonst ist die Vola 0 und der Hebel-Deckel
    faellt auf seinen Hoechstwert, und der Test prueft nichts.
    """
    reihe = []
    kurs = basis
    for i in range(300):
        schwung = 1 + (i % 7) * 0.004 - 0.012
        offen = kurs
        kurs = kurs * schwung
        reihe.append([i, offen, max(offen, kurs) * 1.003,
                      min(offen, kurs) * 0.997, kurs, 10.0])
    return reihe


ROH = [
    {"instId": "CHIP-USDT-SWAP", "state": "live", "ctType": "linear",
     "settleCcy": "USDT", "instCategory": "1", "lever": "20"},
    {"instId": "BTC-USD-SWAP", "state": "live", "ctType": "inverse",
     "settleCcy": "BTC", "instCategory": "1"},
    {"instId": "POL-USDT-SWAP", "state": "suspendiert", "ctType": "linear",
     "settleCcy": "USDT", "instCategory": "1"},
    {"instId": "DASH-USDC-SWAP", "state": "live", "ctType": "linear",
     "settleCcy": "USDC", "instCategory": "1"},
    {"instId": "RE-USD_UM_XPERP-310620", "state": "live",
     "ctType": "linear", "settleCcy": "USDT", "instCategory": "1"},
]


class Zugang(unittest.TestCase):

    def test_basiswert_trennt_am_bindestrich(self):
        self.assertEqual(k.basiswert("CHIP-USDT-SWAP"), "CHIP")
        self.assertEqual(k.basiswert("RE-USD_UM_XPERP-310620"), "RE")

    def test_universum_nimmt_nur_live_lineare_usdt_swaps(self):
        alt = okxf._mit_wiederholung
        okxf._mit_wiederholung = lambda *a, **kw: ROH
        try:
            namen = [x["instId"] for x in k.instrumente()]
        finally:
            okxf._mit_wiederholung = alt
        self.assertEqual(namen, ["CHIP-USDT-SWAP"])

    def test_umsatz_ist_basiswaehrung_nicht_kontrakte(self):
        tick = {"CHIP-USDT-SWAP": {"volCcy24h": "1000", "last": "0.05"}}
        self.assertAlmostEqual(k.umsatz_je_reihe(tick)["CHIP-USDT-SWAP"], 50.0)


class Sammlung(unittest.TestCase):

    def setUp(self):
        self.k4h = kerzen(1.0)
        self.k1d = kerzen(1.0)
        self.alt = (okxf.kerzen, okxf.tickers, k.instrumente)
        self.alt_hk = k.handels_kontrakte

        okxf.kerzen = lambda inst, bar="1H", anzahl=300: (
            self.k1d if bar == "1D" else self.k4h)
        okxf.tickers = lambda inst_type="FUTURES": {
            "CHIP-USDT-SWAP": {"volCcy24h": "50000000", "last": "1.0"},
            "KLEIN-USDT-SWAP": {"volCcy24h": "1000", "last": "1.0"},
        }
        k.instrumente = lambda: [
            {"instId": "CHIP-USDT-SWAP", "lever": "20", "instCategory": "1"},
            {"instId": "KLEIN-USDT-SWAP", "lever": "5", "instCategory": "1"},
        ]
        # Der handelbare Zwilling je Reihe. Ohne ihn faellt die Reihe aus der
        # Liste - nur der XPERP-Zweig ist auf diesem Konto handelbar.
        k.handels_kontrakte = lambda: {
            "CHIP": {"instId": "CHIP-USD_UM_XPERP-310822", "lever": "20"},
            "KLEIN": {"instId": "KLEIN-USD_UM_XPERP-310999", "lever": "5"},
        }

    def tearDown(self):
        okxf.kerzen, okxf.tickers, k.instrumente = self.alt
        k.handels_kontrakte = self.alt_hk

    def test_kandidatenform_ist_dieselbe_wie_in_der_xperp_auswahl(self):
        d = k.sammle(still=True, vorsortiert=None)
        self.assertEqual(len(d), 2)
        z = d[0]
        for feld in ("basis", "instId", "kurs", "vola", "atr", "weg", "er",
                     "mae_long", "mae_short", "kerzen", "umsatz",
                     "kategorie", "vola_tor", "max_lever", "punkte"):
            self.assertIn(feld, z)
        for zweck in ("long", "short", "grid"):
            self.assertIn(zweck, z["punkte"])
        self.assertEqual(z["instId"], "CHIP-USDT-SWAP")
        self.assertEqual(z["basis"], "CHIP")
        self.assertEqual(z["kategorie"], "krypto")

    def test_vorsortiert_behaelt_nur_die_umsatzstaerksten(self):
        d = k.sammle(still=True, vorsortiert=1)
        self.assertEqual([z["instId"] for z in d], ["CHIP-USDT-SWAP"])

    def test_umsatz_kommt_aus_dem_swap_ticker(self):
        d = k.sammle(still=True, vorsortiert=None)
        nach = {z["instId"]: z["umsatz"] for z in d}
        self.assertAlmostEqual(nach["CHIP-USDT-SWAP"], 50000000.0)
        self.assertAlmostEqual(nach["KLEIN-USDT-SWAP"], 1000.0)


class KeinOrderpfad(unittest.TestCase):

    def test_modul_nennt_keine_order_funktion(self):
        with open(os.path.join(SWAP, "kandidaten.py"), encoding="utf-8") as f:
            quelle = f.read()
        for verboten in ("order_limit", "markt_schliessen", "hebel_setzen",
                         "order_stornieren", "marktkauf", "markt_kauf"):
            self.assertNotIn(verboten, quelle,
                             "%s darf im Universum nicht vorkommen" % verboten)


if __name__ == "__main__":
    unittest.main()
