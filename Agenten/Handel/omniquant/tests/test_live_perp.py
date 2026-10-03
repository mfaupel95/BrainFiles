"""Tests des Live-Zweigs: Kraken Futures, Hebel 6, und die Sperrenkette.

Kein Netz, keine Order, keine echte Datei. Alle Boersen-Funktionen werden
durch Attrappen ersetzt - `markt_kauf` darf in keinem Test erreicht werden.

Der zweite Zweck dieser Datei ist der Modulwaechter: `setUpModule` merkt
Dateiliste und Groessen des echten Spurenordners, `tearDownModule` vergleicht.
So faellt jeder Test auf, der versehentlich nach draussen schreibt (die Falle
vom 16.09.2026, die 16 Buchungen ins echte Journal geschrieben hat).

Lauf (aus dem omniquant-Ordner):
    ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
"""

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
while HIER in sys.path:
    sys.path.remove(HIER)
sys.path.insert(0, HIER)          # eigene Spur ZULETZT vorne - nicht scanner/

import handeln as h                                 # noqa: E402
import kraken_perp as kp                            # noqa: E402
import live_perp as lp                              # noqa: E402

assert h.__file__.startswith(HIER), "falsches handeln: %s" % h.__file__
assert kp.__file__.startswith(HIER), "falsches kraken_perp: %s" % kp.__file__

_SPURORDNER = HIER


def _stand():
    aus = {}
    for name in sorted(os.listdir(_SPURORDNER)):
        p = os.path.join(_SPURORDNER, name)
        if os.path.isfile(p):
            aus[name] = os.path.getsize(p)
    return aus


_STAND_VOR = None


def setUpModule():
    global _STAND_VOR
    _STAND_VOR = _stand()


def tearDownModule():
    nach = _stand()
    neu = {k: v for k, v in nach.items() if _STAND_VOR.get(k) != v}
    assert not neu, "Tests haben in den echten Spurenordner geschrieben: %s" % neu


def _w(**felder):
    """Eine Wachen-Kopie - nie die echte Datei."""
    basis = {
        "hebel": 6, "max_einsatz_je_position_usd": 50,
        "live_einsatz_usd": 50, "live_max_offene_positionen": 1,
        "live_max_gesamt_usd": 50, "mindest_guthaben_usd": 35,
        "herzschlag_max_minuten": 180, "max_halte_dauer_tage": 14,
        "handel_erlaubt": False, "freigabe": {"erfuellt": False},
    }
    basis.update(felder)
    return basis


class PaarAbbildungTest(unittest.TestCase):
    """Ein unbekanntes Instrument ist ein Fehler, keine stille Ersatzwahl."""

    def test_bekannte_namen_werden_uebersetzt(self):
        f = kp.paar_fuer
        self.assertEqual("PF_STRKUSD", f("STRK-USDT"))
        self.assertEqual("PF_DOGEUSD", f("DOGE-USDT"))
        self.assertEqual("PF_XRPUSD", f("XRP-USDC"))
        self.assertEqual("PF_ORDIUSD", f("ORDI-USDT"))
        self.assertEqual("PF_ZECUSD", f("ZEC-USDC"))

    def test_magic_ist_kein_unbekannter_name_sondern_ein_fehlender_markt(self):
        with self.assertRaises(ValueError) as c:
            kp.paar_fuer("MAGIC-USDT")
        self.assertIn("keinen Markt", str(c.exception))

    def test_voellig_unbekannt_nennt_die_bekannten(self):
        with self.assertRaises(ValueError) as c:
            kp.paar_fuer("NOPE-USDT")
        self.assertIn("unbekanntes Instrument", str(c.exception))
        self.assertIn("STRK-USDT", str(c.exception))

    def test_gross_klein_egal(self):
        self.assertEqual("PF_STRKUSD", kp.paar_fuer(" strk-usdt "))


class SizingTest(unittest.TestCase):
    """Nennwert = Einsatz x Hebel; 1 Kontrakt = 1 Einheit der Basiswaehrung."""

    def test_hebel_6_ergibt_das_sechsfache(self):
        kontrakte = kp.kontrakte_fuer("XRP-USDC", 50, 1.5072, _w())
        self.assertEqual(199, kontrakte)                  # 300 / 1.5072
        nennwert = kp.nennwert_usd("XRP-USDC", kontrakte, 1.5072)
        self.assertAlmostEqual(299.93, nennwert, places=1)

    def test_hebel_aus_der_wachen_nicht_aus_dem_modul(self):
        self.assertAlmostEqual(12.0, kp.hebel(_w(hebel=12)))
        self.assertAlmostEqual(6.0, kp.hebel({}))

    def test_einsatz_live_liest_das_live_feld(self):
        self.assertEqual(80, kp.einsatz_usd(_w(live_einsatz_usd=80), live=True))
        self.assertEqual(50, kp.einsatz_usd(_w(), live=True))

    def test_kurs_null_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            kp.kontrakte_fuer("XRP-USDC", 50, 0, _w())


class HebelSperreTest(unittest.TestCase):
    """1 Kontrakt ist die kleinste Order - ZEC sprengt damit jeden 6x-Rahmen."""

    def test_zec_ist_bei_hebel_6_nicht_abbildbar(self):
        grund = kp.hebel_grund("ZEC-USDC", 50, 1436.99, _w())
        self.assertIsNotNone(grund)
        self.assertIn("nicht abbildbar", grund)

    def test_xrp_passt(self):
        self.assertIsNone(kp.hebel_grund("XRP-USDC", 50, 1.5072, _w()))

    def test_mit_grossem_einsatz_geht_zec_wieder(self):
        grund = kp.hebel_grund("ZEC-USDC", 250, 1436.99, _w(hebel=6))
        self.assertIsNone(grund)


class SperrenketteTest(unittest.TestCase):
    """Der Sperrtext ist eine Schnittstelle - der Dauerlauf parst ihn."""

    def setUp(self):
        self._alt = (lp.zeitfenster_offen, lp.sitzung_da,
                     kp.schluessel_vorhanden, kp.guthaben_usd, kp.demo_modus)

    def tearDown(self):
        (lp.zeitfenster_offen, lp.sitzung_da, kp.schluessel_vorhanden,
         kp.guthaben_usd, kp.demo_modus) = self._alt

    def _boerse_ok(self, frei=100.0, fenster=False):
        lp.zeitfenster_offen = lambda: fenster
        lp.sitzung_da = lambda: False
        kp.schluessel_vorhanden = lambda: True
        kp.guthaben_usd = lambda: frei
        kp.demo_modus = lambda: False

    def test_ohne_schalter_und_haken_werden_beide_genannt(self):
        self._boerse_ok()
        g = lp.live_sperren(_w(), {})
        self.assertTrue(any("handel_erlaubt" in x for x in g))
        self.assertTrue(any("freigabe.erfuellt" in x for x in g))

    def test_nur_das_fenster_fehlt_ergibt_genau_einen_grund_mit_dem_wort(self):
        """Nur so greift dauerlauf.nur_fenster_fehlt und die Auto-Freigabe fragt."""
        self._boerse_ok(fenster=False)
        zeile = io.StringIO()
        with redirect_stdout(zeile):
            h.sperren_zeile(_w(handel_erlaubt=True,
                               freigabe={"erfuellt": True}), {})
        text = zeile.getvalue().strip()
        self.assertTrue(text.startswith("Live waere gesperrt durch: "))
        gruende = text.split(": ", 1)[1].split("; ")
        self.assertEqual(1, len(gruende), "erwartet genau ein Grund: %r" % gruende)
        self.assertIn("Freigabefenster", gruende[0])

    def test_offenes_fenster_und_guthaben_ergeben_nichts(self):
        self._boerse_ok(frei=100.0, fenster=True)
        g = lp.live_sperren(_w(handel_erlaubt=True,
                               freigabe={"erfuellt": True}), {})
        self.assertEqual([], g, "erwartet keine Sperre, war %r" % g)

    def test_zu_wenig_margin_nennt_beide_zahlen(self):
        self._boerse_ok(frei=1.32, fenster=True)
        g = lp.live_sperren(_w(handel_erlaubt=True,
                               freigabe={"erfuellt": True}), {})
        self.assertTrue(any("1.32" in x and "35.00" in x for x in g), g)

    def test_schluessel_fehlen_ist_ein_eigener_grund(self):
        self._boerse_ok(fenster=True)
        kp.schluessel_vorhanden = lambda: False
        g = lp.live_sperren(_w(), {})
        self.assertTrue(any("Schluessel" in x for x in g), g)

    def test_sperrzeile_druckt_auch_bei_leerer_liste(self):
        """Eine Zeile nur im Fehlerfall ist von 'nicht geprueft' nicht zu trennen."""
        self._boerse_ok(frei=100.0, fenster=True)
        zeile = io.StringIO()
        with redirect_stdout(zeile):
            h.sperren_zeile(_w(handel_erlaubt=True,
                               freigabe={"erfuellt": True}), {})
        self.assertIn("nichts", zeile.getvalue())


class PapierLaesstLiveStehenTest(unittest.TestCase):
    """Ein Papierlauf schliesst keine echte Position.

    SCHREIBEN=False ist PFLICHT: `pruefe_ausstiege` ruft `schliesse`, und das
    journalisiert die Papierposition. Ohne den Schalter landeten die Zeilen im
    ECHTEN handelsjournal.csv - beim ersten Lauf dieser Datei passiert, vier
    Zeilen mussten wieder heraus (Falle vom 16.09.2026).
    """

    def setUp(self):
        self._alt_schreiben = h.SCHREIBEN
        h.SCHREIBEN = False

    def tearDown(self):
        h.SCHREIBEN = self._alt_schreiben

    def test_live_position_ueberlebt_den_papier_ausstieg(self):
        alt = h.letzter_kurs_quelle
        h.letzter_kurs_quelle = lambda inst: 1.0     # unter jedem Stop
        try:
            z = {"positionen": [
                {"inst": "XRP-USDC", "seite": "long", "modus": "live",
                 "einstieg": 1.5, "stop": 1.45, "ziel": 1.7, "kontrakte": 199,
                 "einsatz_usd": 50},
                {"inst": "STRK-USDT", "seite": "long", "einstieg": 0.04,
                 "stop": 0.05, "ziel": 0.06, "nominal": 50,
                 "eroeffnet": "2026-10-01"},
            ]}
            h.pruefe_ausstiege(z, _w())
            uebrig = [p["inst"] for p in z["positionen"]]
            self.assertIn("XRP-USDC", uebrig, "Live-Position wurde angefasst")
        finally:
            h.letzter_kurs_quelle = alt


class VorschauSchreibtNichtTest(unittest.TestCase):
    """Bedingung: eine Vorschau ist kein Schreibzugriff."""

    def setUp(self):
        self.alt = h.SCHREIBEN
        h.SCHREIBEN = False

    def tearDown(self):
        h.SCHREIBEN = self.alt

    def test_vorschau_aendert_keine_datei(self):
        vor = _stand()
        with redirect_stdout(io.StringIO()):
            h.lauf("vorschau")
        self.assertEqual(vor, _stand())

    def test_vorschau_nennt_die_sperrzeile(self):
        zeile = io.StringIO()
        with redirect_stdout(zeile):
            h.lauf("vorschau")
        self.assertIn("Live waere gesperrt durch:", zeile.getvalue())


class WachenZeigtLiveGrenzenTest(unittest.TestCase):
    def test_wachen_nennt_hebel_und_live_einsatz(self):
        zeile = io.StringIO()
        with redirect_stdout(zeile):
            h.zeige_wachen(h.lade_wachen())
        text = zeile.getvalue()
        self.assertIn("live_einsatz_usd", text)
        self.assertIn("hebel", text)
        self.assertIn("live_max_offene_positionen", text)


class EchteWachenTest(unittest.TestCase):
    """Die ausgelieferte wachen.json muss zum Live-Zweig passen.

    Was hier NICHT geprueft wird: OB die beiden Haken gesetzt sind. Das ist
    Max' Entscheidung (am 01.10.2026: 'auto freigabe erlaubt' -> beide an) und
    kein Fehler. Ein Test, der den Zustand einfriert, wird bei jeder Entscheidung
    rot statt bei einem Fehler. Die REGEL - scharf nur mit BEIDEN Haken - prueft
    `test_scharf_nur_mit_beiden_haken` mit einer Wachen-Kopie.
    """

    def test_hebel_und_live_grenzen_stehen_in_der_datei(self):
        with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        self.assertEqual(6, w.get("hebel"))
        self.assertEqual("kraken_futures", w.get("boerse"))
        self.assertEqual(50, w.get("live_einsatz_usd"))
        self.assertEqual(1, w.get("live_max_offene_positionen"))
        self.assertIn("freigabe", w)
        # Haken sind Haken: boolesch, und der Code verlangt BEIDE.
        self.assertIsInstance(w.get("handel_erlaubt"), bool)
        self.assertIsInstance(w["freigabe"].get("erfuellt"), bool)

    def test_scharf_nur_mit_beiden_haken(self):
        """Regel statt Zustand: fehlt EINER der Haken, nennt die Kette ihn."""
        with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
            echt = json.load(f)
        for schalter, haken in ((False, False), (True, False), (False, True),
                                (True, True)):
            kopie = dict(echt, handel_erlaubt=schalter,
                         freigabe=dict(echt["freigabe"], erfuellt=haken))
            alt = (lp.sitzung_da, lp.zeitfenster_offen, kp.schluessel_vorhanden,
                   kp.guthaben_usd, kp.demo_modus)
            lp.sitzung_da = lambda: False
            lp.zeitfenster_offen = lambda: True
            kp.schluessel_vorhanden = lambda: True
            kp.guthaben_usd = lambda: 1000.0
            kp.demo_modus = lambda: False
            try:
                g = lp.live_sperren(kopie, {})
            finally:
                (lp.sitzung_da, lp.zeitfenster_offen, kp.schluessel_vorhanden,
                 kp.guthaben_usd, kp.demo_modus) = alt
            if not schalter:
                self.assertTrue(any("handel_erlaubt=false" in x for x in g), g)
            if not haken:
                self.assertTrue(any("freigabe.erfuellt=false" in x for x in g), g)
            if schalter and haken:
                self.assertEqual([], g, g)


if __name__ == "__main__":
    unittest.main()