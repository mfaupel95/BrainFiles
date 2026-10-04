"""Tests fuer gebuehr_boerse_abgleich.py - die LUECKE, die T-329 aufmachte.

WAS HIER GEPRUEFT WIRD
----------------------
Nicht "steht der richtige Wert drin", sondern: WELCHE Boerse wird beurteilt,
wenn die Wache selbst schweigt. Genau daran ist die erste Fassung des
Werkzeugs gescheitert - sie nahm OKX als Vorgabe und beanstandete daraufhin
16 Spuren zu Unrecht (`kraken` handelt ueber `import kraken`, `xperp` ueber
`okxf`).

DIE DREI STUFEN, in der Reihenfolge der Guelle
---------------------------------------------
1. `boersen[0]` - eine Spur mit zwei Boersen handelt auf der ersten,
2. `boerse`/`venue`,
3. der IMPORT in der eigenen `handeln.py`,
4. OKX als Vorgabe (`spur_buch.orderweg`).

Zusaetzlich die wichtigere Regel: eine MODELLANNAHME (Onchain, 1,0 % DEX)
ist kein Befund. Sie zu melden hiesse eine getroffene Entscheidung mit einem
Fehler zu verwechseln - und wuerde beim `--anwenden` das Onchain-Buch um eine
Groessenordnung schoenrechnen.

SCHREIBZUGRIFF: keiner. Der Test rechnet auf Attrappen-Wachen und einem
Tempordner; ein Modulwaechter vergleicht jede echte wachen.json des Hauses
vorher und nachher.
"""

import importlib.util
import json
import os
import pathlib
import shutil
import tempfile
import unittest

HIER = pathlib.Path(__file__).resolve().parent
HANDEL = HIER.parent


def _lade():
    spec = importlib.util.spec_from_file_location(
        "gebuehr_boerse_abgleich", HANDEL / "gebuehr_boerse_abgleich.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


gba = _lade()


def _stand():
    aus = {}
    for p in sorted(HANDEL.glob("*/wachen*.json")):
        if ".bak-" in p.name:
            continue
        st = p.stat()
        aus[str(p.relative_to(HANDEL))] = (st.st_size, int(st.st_mtime))
    return aus


_VORHER = None


def setUpModule():
    global _VORHER
    _VORHER = _stand()


def tearDownModule():
    nachher = _stand()
    if nachher != _VORHER:
        neu = {k: v for k, v in nachher.items() if _VORHER.get(k) != v}
        raise AssertionError("Test hat in echte Wachen geschrieben: %s" % neu)


class BoerseErmittelnTest(unittest.TestCase):
    """WELCHE Boerse - die Reihenfolge ist die Regel."""

    def test_boersen_liste_nimmt_den_ersten(self):
        self.assertEqual(gba.aktive_boerse({"boersen": ["okx", "kraken"]}),
                         "okx")

    def test_boerse_schlaegt_boersen_als_string(self):
        # `boersen` als einzelner String kommt im Baum vor.
        self.assertEqual(gba.aktive_boerse({"boersen": "kraken"}), "kraken")

    def test_boersen_leer_ist_keine_angabe(self):
        self.assertEqual(gba.aktive_boerse({"boersen": [], "boerse": "kraken"}),
                         "kraken")

    def test_ohne_alles_ist_okx_vorgabe(self):
        self.assertEqual(gba.aktive_boerse({}), gba.VORGABE_BOERSE)

    def test_der_code_weiss_mehr_als_die_wache(self):
        """DER BEFUND VOM 04.10.: `kraken` traegt kein `boerse`-Feld."""
        tmp = tempfile.mkdtemp(prefix="gba-code-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ordner = os.path.join(tmp, "kraken")
        os.makedirs(ordner)
        with open(os.path.join(ordner, "handeln.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("import kraken\nimport sys\n")
        self.assertEqual(gba.aktive_boerse({}, ordner), "kraken")

    def test_kein_import_heisst_okx(self):
        tmp = tempfile.mkdtemp(prefix="gba-code-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ordner = os.path.join(tmp, "etwas")
        os.makedirs(ordner)
        with open(os.path.join(ordner, "handeln.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("import spur_buch\n")
        self.assertEqual(gba.aktive_boerse({}, ordner), gba.VORGABE_BOERSE)

    def test_okxf_ist_perp_nicht_spot(self):
        """`okxf` ist das XPERP-Hausmodul - 0,05 % statt 0,10 %."""
        tmp = tempfile.mkdtemp(prefix="gba-code-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ordner = os.path.join(tmp, "xperp")
        os.makedirs(ordner)
        with open(os.path.join(ordner, "handeln.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("import okxf\n")
        soll, _hat, key, _modell = gba.befund(
            {"gebuehr_taker": 0.0005}, ordner)
        self.assertEqual(key, "okx_perp")
        self.assertAlmostEqual(soll, 0.05)

    def test_produktname_schlaegt_boersenname(self):
        """`kraken_futures` (0,05 %) vor `kraken` (0,60 %)."""
        tmp = tempfile.mkdtemp(prefix="gba-code-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ordner = os.path.join(tmp, "nautilus_kraken_futures")
        os.makedirs(ordner)
        with open(os.path.join(ordner, "handeln.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("import kraken_futures\nimport kraken\n")
        _soll, _hat, key, _modell = gba.befund({"gebuehr_taker": 0.0005},
                                                ordner)
        self.assertEqual(key, "kraken_futures")


class ModellannahmeTest(unittest.TestCase):
    """Eine bewusst gesetzte Zahl ist kein Befund."""

    def test_onchain_notiz_ist_modellannahme(self):
        w = {"gebuehr_taker": 0.01,
             "_gebuehr_quelle": "MODELLANNAHME, NICHT gemessen: 1,0 % je "
                                "Seite fuer Onchain-Handel"}
        self.assertTrue(gba._ist_modellannahme(w))

    def test_gemessener_satz_ist_keine_modellannahme(self):
        w = {"gebuehr_taker": 0.001,
             "_gebuehr_quelle": "GEMESSEN 01.10.2026: Tarif Lv1 taker 0,10 %"}
        self.assertFalse(gba._ist_modellannahme(w))

    def test_der_befund_nennt_die_modellannahme(self):
        soll, hat, key, modell = gba.befund(
            {"gebuehr_taker": 0.01, "boerse": "okx",
             "_gebuehr_quelle": "MODELLANNAHME fuer Onchain"})
        self.assertTrue(modell)
        self.assertEqual(key, "okx_spot")
        self.assertAlmostEqual(hat, 1.0)


class AbgleichTest(unittest.TestCase):
    """Der Lauf ueber einen Tempordner - echte Wachen werden nie beruehrt."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gba-lauf-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _spur(self, name, wachen, handeln_text=None):
        ordner = os.path.join(self.tmp, name)
        os.makedirs(ordner, exist_ok=True)
        # Die Attrappe traegt das Format einer echten Wachen: ein Feld je
        # Zeile und die schliessende Klammer allein. `gs._feld_setzen`
        # sucht genau danach - eine einzeilige Datei laesst es mit
        # "keine schliessende Klammer gefunden" abbrechen, und das waere ein
        # Fehler der Attrappe, nicht des Werkzeugs.
        with open(os.path.join(ordner, "wachen.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(wachen, fh, indent=2)
            fh.write("\n")
        if handeln_text is not None:
            with open(os.path.join(ordner, "handeln.py"), "w",
                      encoding="utf-8") as fh:
                fh.write(handeln_text)
        return ordner

    def test_passende_waechte_meldet_nichts(self):
        self._spur("gut", {"boerse": "okx", "gebuehr_taker": 0.001})
        alt = gba.HIER
        gba.HIER = self.tmp
        self.addCleanup(setattr, gba, "HIER", alt)
        zeilen, offen, _nicht = gba.pruefe()
        self.assertEqual(offen, 0, "OKX-Spot mit 0,10 % stimmt")
        self.assertEqual(zeilen, [])

    def test_falscher_satz_wird_gemeldet(self):
        self._spur("falsch", {"boerse": "kraken", "gebuehr_taker": 0.001})
        alt = gba.HIER
        gba.HIER = self.tmp
        self.addCleanup(setattr, gba, "HIER", alt)
        _zeilen, offen, _nicht = gba.pruefe()
        self.assertEqual(offen, 1,
                         "Kraken-Spot traegt den OKX-Satz - genau T-329")

    def test_onchain_wird_nicht_gemeldet(self):
        """GEGENPROBE zur falschen Fassung: sie meldete die Modellannahme."""
        self._spur("spiegel", {"boerse": "okx", "gebuehr_taker": 0.01,
                               "_gebuehr_quelle": "MODELLANNAHME, "
                                                  "NICHT gemessen: 1,0 %"})
        alt = gba.HIER
        gba.HIER = self.tmp
        self.addCleanup(setattr, gba, "HIER", alt)
        _zeilen, offen, nicht = gba.pruefe()
        self.assertEqual(offen, 0)
        self.assertEqual(nicht, 1, "gezaehlt, nicht gemeldet")

    def test_ohne_schreiben_aendert_sich_nichts(self):
        ordner = self._spur("falsch", {"boerse": "kraken",
                                       "gebuehr_taker": 0.001})
        alt = gba.HIER
        gba.HIER = self.tmp
        self.addCleanup(setattr, gba, "HIER", alt)
        gba.pruefe(schreiben=False)
        with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as fh:
            w = json.load(fh)
        self.assertEqual(w["gebuehr_taker"], 0.001,
                         "die Vorschau schreibt nicht")
        self.assertFalse([f for f in os.listdir(ordner) if ".bak-" in f],
                         "die Vorschau legt keine Sicherung an")

    def test_mit_anwenden_stellt_um_und_sichert(self):
        ordner = self._spur("falsch", {"boerse": "kraken",
                                       "gebuehr_taker": 0.001})
        alt = gba.HIER
        gba.HIER = self.tmp
        self.addCleanup(setattr, gba, "HIER", alt)
        _zeilen, offen, _nicht = gba.pruefe(schreiben=True)
        self.assertEqual(offen, 1)
        with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as fh:
            w = json.load(fh)
        self.assertAlmostEqual(w["gebuehr_taker"], 0.006)
        sich = [f for f in os.listdir(ordner) if ".bak-" in f]
        self.assertEqual(len(sich), 1, "genau eine Sicherung")


if __name__ == "__main__":
    unittest.main()