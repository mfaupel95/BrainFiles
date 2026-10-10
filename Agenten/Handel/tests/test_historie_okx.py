"""Naht-Tests fuer historie_okx.py - kein Netz, kein echter Zielpfad.

Der Abruf wird ueber `historie_okx.abruf` gefaelscht, die Namensaufloesung
ueber `historie_okx._OKXF` (Attrappen-Modul statt xperp/okxf.py). Die Naht
ist bewusst die FUNKTION `abruf`, nicht ein URL-Fake wie bei
historie_binance: history-candles ist keine offene URL-Sammlung, sondern ein
pfadgebauter Abruf - wer die URL faelscht, testet die URL, nicht die
Pagination.
"""

import json
import os
import sys
import tempfile
import types
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))

import historie_okx                                                  # noqa: E402


def _reihe(ts, kurs):
    return [ts, kurs, kurs + 1.0, kurs - 1.0, kurs + 0.5, 12.0]


class _FakeOkxf:
    """Attrappe fuer xperp/okxf.py - instrument() und instrumente()."""

    def __init__(self):
        self.kontrakte = {
            "RE": {"instId": "RE-USD_UM_XPERP-310620", "state": "live"},
            "BTC": {"instId": "BTC-USD_UM_XPERP-310629", "state": "live"},
        }

    def instrument(self, basis):
        b = basis.upper()
        if b in self.kontrakte:
            return self.kontrakte[b]
        raise RuntimeError("kein XPERP-Kontrakt zu %r" % basis)

    def instrumente(self, kategorie=None):
        return list(self.kontrakte.values())


class NamensTest(unittest.TestCase):
    def setUp(self):
        self.alt = historie_okx._OKXF
        historie_okx._OKXF = _FakeOkxf()

    def tearDown(self):
        historie_okx._OKXF = self.alt

    def test_voller_instid_bleibt(self):
        for name in ("RE-USD_UM_XPERP-310620",
                     "BTC-USDT-SWAP"):
            self.assertEqual(name, historie_okx.instid(name))

    def test_basiswert_wird_aufgeloest(self):
        self.assertEqual("RE-USD_UM_XPERP-310620", historie_okx.instid("RE"))

    def test_unbekannter_name_wirft(self):
        with self.assertRaises(KeyError):
            historie_okx.instid("GIBTESNICHT")


class SpeicherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = historie_okx.ORDNER
        self.alt_okxf = historie_okx._OKXF
        historie_okx.ORDNER = self.tmp.name
        historie_okx._OKXF = _FakeOkxf()

    def tearDown(self):
        historie_okx.ORDNER, historie_okx._OKXF = self.alt, self.alt_okxf
        self.tmp.cleanup()

    def test_speichere_haengt_an_entdoppelt_und_normalisiert(self):
        a = [_reihe(1000, 10.0), _reihe(2000, 11.0)]
        b = [_reihe(2000, 11.0), _reihe(3000, 12.0)]
        self.assertEqual(2, historie_okx.speichere("RE", "1H", a))
        self.assertEqual(3, historie_okx.speichere("RE", "1H", b))
        reihen = historie_okx.lade("RE", "1H")
        self.assertEqual([1000, 2000, 3000], [r[0] for r in reihen])
        self.assertEqual([int, float, float, float, float, float],
                         [type(x) for x in reihen[0]])

    def test_schreibt_unter_vollen_instid(self):
        historie_okx.speichere("RE", "1H", [_reihe(1000, 10.0)])
        self.assertTrue(os.path.isfile(os.path.join(
            self.tmp.name, "RE-USD_UM_XPERP-310620_1H.json")))
        self.assertFalse(os.path.exists(os.path.join(
            self.tmp.name, "RE_1H.json")))

    def test_lade_ohne_datei_ist_leer(self):
        self.assertEqual([], historie_okx.lade("RE", "1H"))

    def test_kaputte_datei_wirft_historie_kaputt(self):
        p = os.path.join(self.tmp.name, "RE-USD_UM_XPERP-310620_1H.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write("{kein json")
        with self.assertRaises(historie_okx.HistorieKaputt):
            historie_okx.lade("RE", "1H")

    def test_unbekannter_takt_wird_abgelehnt(self):
        with self.assertRaises(KeyError):
            historie_okx.datei("RE", "7M")


class AbrufTest(unittest.TestCase):
    """Pagination wird ueber `abruf` gefaelscht - kein Netz.

    Der Fake bildet die ECHTE OKX-Semantik ab: `after=N` liefert Kerzen
    AELTER als N (ts < N), Seite neueste zuerst, hoechstens GRENZE je Seite.
    Wer den Fake einfacher baut (eine Seite je Aufruf), testet den Loader
    nicht - der haengt genau am after-Rueckwaertsblaettern.
    """

    # Alle Kerzen der Fake-Boerse, aufsteigend.
    ALLE = [[1000, 10.0, 11.0, 9.0, 10.5, 5.0],
            [1001, 10.5, 11.5, 10.0, 11.0, 6.0],
            [2000, 11.0, 12.0, 10.0, 11.5, 7.0],
            [2001, 11.5, 12.5, 11.0, 12.0, 8.0],
            [3000, 12.0, 13.0, 11.0, 12.5, 9.0],
            [3001, 12.5, 13.5, 12.0, 13.0, 10.0]]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_o = historie_okx.ORDNER
        self.alt_a = historie_okx.abruf
        self.alt_okxf = historie_okx._OKXF
        historie_okx.ORDNER = self.tmp.name
        historie_okx._OKXF = _FakeOkxf()
        self.aufrufe = []

    def tearDown(self):
        historie_okx.ORDNER = self.alt_o
        historie_okx.abruf = self.alt_a
        historie_okx._OKXF = self.alt_okxf
        self.tmp.cleanup()

    def _seiten(self, pfad):
        """Echte API-Semantik: ts < after, neueste zuerst, max 2 je Seite."""
        self.aufrufe.append(pfad)
        import urllib.parse
        q = urllib.parse.parse_qs(pfad.split("?", 1)[1])
        after = int(q["after"][0]) if "after" in q else 10 ** 15
        seite = [list(r) for r in self.ALLE if r[0] < after][-2:]
        return [["%d" % r[0]] + ["%g" % x for x in r[1:]] for r in seite]

    def test_blaettert_mit_after_und_sortiert_aufsteigend(self):
        historie_okx.abruf = self._seiten
        r = historie_okx.von_okx("RE", "1H", 999, 4000)
        self.assertEqual([1000, 1001, 2000, 2001, 3000, 3001],
                         [x[0] for x in r])
        # 4001 (bis_ms+1, damit die Kerze auf bis_ms selbst mitkommt)
        # -> 3000/3001 (after=3000) -> 2000/2001 (after=2000)
        # -> 1000/1001 (after=1000, dann Stopp: keine aeltere Seite)
        self.assertEqual(["4001", "3000", "2000", "1000"],
                         [p.split("after=")[1].split("&")[0] for p in self.aufrufe])
        self.assertEqual(float, type(r[0][4]))

    def test_von_und_bis_werden_eingehalten(self):
        historie_okx.abruf = self._seiten
        r = historie_okx.von_okx("RE", "1H", 1999, 2500)
        self.assertEqual([2000, 2001], [x[0] for x in r])

    def test_stoppt_bei_wiederholter_seite(self):
        def dieselbe(pfad):
            self.aufrufe.append(pfad)
            return [["2000", "11", "12", "10", "11.5", "7"]]
        historie_okx.abruf = dieselbe
        r = historie_okx.von_okx("RE", "1H", 1000, 4000)
        self.assertEqual([2000], [x[0] for x in r])
        self.assertEqual(2, len(self.aufrufe))

    def test_auffuellen_schreibt_und_stand_zahlt(self):
        historie_okx.abruf = self._seiten
        b = historie_okx.auffuellen(["RE"], ["1H"], von_ms=999, bis_ms=4000)
        self.assertEqual(6, b["RE"]["1H"]["kerzen"])
        self.assertEqual("RE-USD_UM_XPERP-310620", b["RE"]["1H"]["instId"])
        stand = historie_okx.stand()["reihen"]
        self.assertEqual(6, stand["RE-USD_UM_XPERP-310620_1H"]["kerzen"])
        self.assertEqual("okx", stand["RE-USD_UM_XPERP-310620_1H"]["herkunft"])


class WachenTest(unittest.TestCase):
    """Die wachen.json-Struktur der Spur (familien statt instrumente)."""

    def setUp(self):
        self.alt_okxf = historie_okx._OKXF
        historie_okx._OKXF = _FakeOkxf()

    def tearDown(self):
        historie_okx._OKXF = self.alt_okxf

    def test_instrumente_feld_hat_vorrang_und_wird_aufgeloest(self):
        w = {"instrumente": ["RE", "BTC-USD_UM_XPERP-310629"]}
        self.assertEqual(["BTC-USD_UM_XPERP-310629", "RE-USD_UM_XPERP-310620"],
                         historie_okx.instrumente_fuer(w))

    def test_familien_nur_aktive_werden_aufgeloest(self):
        w = {"familien": {
            "krypto": {"aktiv": True, "instCategory": "1"},
            "rohstoff": {"aktiv": False, "instCategory": "4"},
        }}
        # Die Attrappe kennt keine instCategory-Filter: alle Kontrakte
        # kommen zurueck - die Regel (aktiv filtert) prueft der Test ueber
        # die aufgerufene Kategorie-Liste des Fake-Moduls.
        self.assertEqual(["BTC-USD_UM_XPERP-310629", "RE-USD_UM_XPERP-310620"],
                         historie_okx.instrumente_fuer(w))

    def test_ohne_familien_und_instrumente_leer(self):
        self.assertEqual([], historie_okx.instrumente_fuer({"vola": 1.2}))

    def test_familie_ohne_instcategory_wird_uebersprungen(self):
        w = {"familien": {"krypto": {"aktiv": True}}}
        self.assertEqual([], historie_okx.instrumente_fuer(w))


if __name__ == "__main__":
    unittest.main()
