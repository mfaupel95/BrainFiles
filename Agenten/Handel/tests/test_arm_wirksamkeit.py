"""Schattenarme muessen WIRksam sein - in den vier Listen und im Waelter.

Der Befund vom 04.10.2026 (drei Fehler an einem Tag, alle in der Verdrahtung):

1. `anbindung_pruefen.py` las `Agenten/<spur>/wachen.json` statt
   `Agenten/Handel/<spur>/wachen.json` (`HANDEL = os.path.dirname(HIER)` in
   einem Werkzeug, das IN Agenten/Handel liegt). Ergebnis: jede Spur bekam {},
   `handel_erlaubt` las als False, und der Lauf meldete 12 von 12 Spuren
   "bereit, aber gesperrt" - wo 10 scharf sind.

2. `spiegelstand` fuehrte die Arm-Namen hart: ("wachen.knapp.json",
   "wachen.weit.json"). `squeeze_eth` (Ordner squeeze, Wachen
   wachen.eth.json) und `nautilus_kraken_futures` (Ordner nautilus_kraken,
   Wachen wachen.futures.json) standen damit in dauerlauf.SPUREN, spiegelten
   nach Q: und wurden von der PRUEFUNG nie gesehen - Bedingung 4 dieser zwei
   Spuren war ungeprueft.

3. Dasselbe Werkzeug riet das Arm-Suffix mit `spur.split("_", 1)[1]`. Aus
   "nautilus_kraken_futures" wird "kraken_futures"; wachen.kraken_futures.json
   gibt es nicht, also wurde still die HAUPT-Wachen des Ordners gelesen - der
   SPOT-Arm. Und `anzahl`/`alter` liefen ueberhaupt ohne Suffix, sodass die
   Zeilenzahl des fremden Arms angezeigt wurde.

Die Regel, die hier festgenagelt wird: ein Arm ist erst dann eine Spur, wenn
alle fuenf Hand-listen ihn kennen. Getestet wird die EIGENSCHAFT (jeder Arm
aus dauerlauf.SPUREN taucht auf), nicht eine Zahl - eine Liste, die morgen
eine Spur mehr hat, soll nicht rot werden.
"""

import ast
import importlib.util
import io
import contextlib
import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)          # tests/ liegt IN Agenten/Handel
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)


def lade(name, rel):
    """Ein Modul aus Agenten/Handel laden - ohne es in sys.path zu legen."""
    pfad = os.path.join(HANDEL, rel)
    spec = importlib.util.spec_from_file_location(name, pfad)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


def spuren_aus_dauerlauf():
    """Spurname -> Ordnername, per ast (kein Import, keine Nebenwirkungen)."""
    with open(os.path.join(HANDEL, "dauerlauf.py"), encoding="utf-8") as fh:
        baum = ast.parse(fh.read())
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Assign) and any(
                isinstance(z, ast.Name) and z.id == "SPUREN"
                for z in knoten.targets):
            if not isinstance(knoten.value, ast.Dict):
                return {}
            zuordnung = {}
            for schluessel, wert in zip(knoten.value.keys, knoten.value.values):
                if not isinstance(wert, ast.Dict):
                    continue
                for k2, v2 in zip(wert.keys, wert.values):
                    if (isinstance(k2, ast.Constant) and k2.value == "ordner"
                            and isinstance(v2, ast.Constant)
                            and isinstance(v2.value, str)):
                        zuordnung[schluessel.value] = v2.value
            return zuordnung
    return {}


ARME = {s: o for s, o in spuren_aus_dauerlauf().items() if s != o}


class ArmWirdGeprueftTest(unittest.TestCase):
    """Jeder Schattenarm muss in spiegelstand.stand() vorkommen."""

    def test_es_gibt_ueberhaupt_arme_zu_pruefen(self):
        self.assertTrue(ARME, "kein Schattenarm gefunden - der Test waere gruen "
                              "ohne etwas zu pruefen")

    def test_jeder_arm_erscheint_in_stand(self):
        ss = lade("spiegelstand_pruefung", "spiegelstand.py")
        ergebnis = ss.stand()
        geprueft = {x["spur"] for x in ergebnis["spuren"]}
        fehlend = sorted(set(ARME) - geprueft)
        self.assertEqual([], fehlend,
                         "diese Schattenarme werden nie auf Q: geprueft "
                         "(Bedingung 4 ungeprueft): %s" % fehlend)

    def test_kein_arm_wird_doppelt_gezaehlt(self):
        ss = lade("spiegelstand_pruefung2", "spiegelstand.py")
        namen = [x["spur"] for x in ss.stand()["spuren"]]
        doppelt = sorted({n for n in namen if namen.count(n) > 1})
        self.assertEqual([], doppelt, "%s steht mehrfach in der Liste" % doppelt)

    def test_hauptarm_verschwindet_durch_die_armreparatur_nicht(self):
        """Die Reparatur haengt die Arme AN die Ordnerliste - ein Ordner,
        der selbst eine Spur ist (squeeze, nautilus_kraken), muss erhalten
        bleiben."""
        ss = lade("spiegelstand_pruefung3", "spiegelstand.py")
        geprueft = {x["spur"] for x in ss.stand()["spuren"]}
        for spur, ordner in ARME.items():
            self.assertIn(ordner, geprueft,
                          "Ordner %s ist aus der Pruefung verschwunden" % ordner)


class ArmSuffixWirdGelesenTest(unittest.TestCase):
    """Das Suffix kommt aus der Wachen-Datei, nicht aus einem Raten."""

    def test_zweitstuelliger_armname_findet_seine_wachen(self):
        """nautilus_kraken_futures -> wachen.futures.json, nicht wachen.json.

        Der alte Code riet `spur.split("_", 1)[1]` = "kraken_futures" und
        las danach still die Haupt-Wachen des Ordners (der SPOT-Arm).
        """
        ss = lade("spiegelstand_pruefung4", "spiegelstand.py")
        spuren = spuren_aus_dauerlauf()
        if "nautilus_kraken_futures" not in spuren:
            self.skipTest("der Arm ist nicht mehr im Lauf")
        spur, ordner = "nautilus_kraken_futures", spuren["nautilus_kraken_futures"]
        z = ss.spur_zeile(HANDEL, spur, ordner=ordner)
        erwartet = "Q:\\Handel_Journal\\nautilus_kraken_futures"
        self.assertEqual(erwartet.replace("\\", os.sep), z["ziel"],
                         "gelesen wurde die Wachen-Datei des SPOT-Arms")

    def test_zustand_und_journal_zaehlen_je_arm_fuer_sich(self):
        ss = lade("spiegelstand_pruefung5", "spiegelstand.py")
        spuren = spuren_aus_dauerlauf()
        zeilen = {}
        for spur, ordner in spuren.items():
            z = ss.spur_zeile(HANDEL, spur, ordner=ordner)
            zeilen[spur] = z["zeilen"]
        # Ein Arm, dessen Journal nicht existiert, zaehlt 0 - nicht die Zahl
        # des Hauptbuchs. (squeeze_eth legt sein Journal erst mit dem ersten
        # Buchungsvorgang an, es ist also juenger als das Hauptjournal.)
        if "squeeze" in zeilen and "squeeze_eth" in zeilen:
            self.assertNotEqual(
                zeilen["squeeze"], zeilen["squeeze_eth"],
                "beide Arme melden dieselbe Journalzahl - das Suffix fehlt "
                "beim Zaehlen")


class WerkzeugLiegtImHandelOrdnerTest(unittest.TestCase):
    """Ein Werkzeug IN Agenten/Handel schreibt HANDEL = HIER.

    Dieselbe Regel wie in jeder Spur (sonst zeigt ein Pfad auf Agenten/ und
    das Werkzeug meldet 'keine Positionen im Haus', statt zu scheitern).
    """

    WURZEL_WERKZEUGE = ("anbindung_pruefen.py",)

    def test_kein_werkzeug_zeigt_auf_die_elternebene(self):
        schlecht = []
        for name in self.WURZEL_WERKZEUGE:
            pfad = os.path.join(HANDEL, name)
            if not os.path.isfile(pfad):
                continue
            with open(pfad, encoding="utf-8") as fh:
                text = fh.read()
            for i, zeile in enumerate(text.splitlines(), 1):
                if zeile.strip().startswith("HANDEL = os.path.dirname(HIER)"):
                    schlecht.append("%s:%d" % (name, i))
        self.assertEqual([], schlecht,
                         "HANDEL = os.path.dirname(HIER) in einem Werkzeug, das "
                         "IN Agenten/Handel liegt - es laest einen Ordner zu "
                         "hoch: %s" % schlecht)

    def test_anbindung_pruefen_liest_die_wirklichen_wachen(self):
        """Gegenprobe auf den Befund selbst: die Wachen, die das Werkzeug
        meldet, muessen die handel_erlaubt-Werte der echten Dateien sein."""
        ap = lade("anbindung_pruefen_wirklich", "anbindung_pruefen.py")
        spur, boerse, quote = ap.SPUREN[0]
        gelesen = ap.lade_wachen(spur)
        with open(os.path.join(HANDEL, spur, "wachen.json"),
                  encoding="utf-8") as fh:
            echt = json.load(fh)
        self.assertEqual(bool(echt.get("handel_erlaubt")),
                         bool(gelesen.get("handel_erlaubt")),
                         "%s: das Werkzeug las nicht die echte wachen.json" % spur)


class GebuehrFolgtDerBoerseTest(unittest.TestCase):
    """Die Gebuehr gehoert zur ORDER-BOERSE, nicht zur Historie der Spur.

    Befund 04.10.2026: mosaic verlor am 30.09.2026 Kraken aus `boersen`
    (Auftrag Max 'nur noch omnitrade auf kraken', Commit e6f2715c), die
    Kraken-Spurole 0.006 blieb aber in der Wachen stehen. Jede Runde wurde
    mit 1,2 % statt der gemessenen 0,2 % gerechnet.
    """

    SATZ = {"okx": 0.001, "okx_futures": 0.0005, "kraken": 0.006,
            "kraken_futures": 0.0005, "deribit": 0.0007, "signalwelle": 0.0005}

    def ordner(self):
        return os.path.join(HANDEL, "tests", "_temp_gebuhr_boerse")

    def setUp(self):
        import shutil
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="gebuhr_boerse_")
        self.ziel = os.path.join(self.tmp, "handel", "beispiel")
        os.makedirs(self.ziel)
        shutil.copy(os.path.join(HANDEL, "mosaic", "wachen.json"),
                    os.path.join(self.ziel, "wachen.json"))
        gs = lade("gebuehren_setzen_gebuhr", "gebuehren_setzen.py")
        self.gs = gs

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def schreibe(self, **felder):
        pfad = os.path.join(self.ziel, "wachen.json")
        with open(pfad, encoding="utf-8") as fh:
            w = json.load(fh)
        w.update(felder)
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(w, fh, ensure_ascii=False, indent=2)

    def aktive_boerse(self, w):
        b = w.get("boersen")
        if isinstance(b, list) and b:
            return b[0]
        return w.get("boerse")

    def test_gemessener_satz_der_boerse(self):
        w = json.load(open(os.path.join(self.ziel, "wachen.json"),
                           encoding="utf-8"))
        aktiv = self.aktive_boerse(w)
        soll = self.SATZ.get(aktiv)
        self.assertIsNotNone(soll, "unbekannte Boerse %r" % aktiv)
        self.assertAlmostEqual(soll, w["gebuehr_taker"], places=6,
                               msg="%s: gebuehr_taker passt nicht zu Boerse %s"
                                   % (aktiv, aktiv))

    def test_gegenprobe_auf_dem_echten_mosaik_wachen(self):
        """Ohne den Fix muss dieser Test fallen: die gebuehren_setzen-Tabelle
        traegt den OKX-Spot-Satz fuer mosaic."""
        zeilen = [z for z in self.gs.AENDERUNGEN
                  if z[0] == "mosaic/wachen.json" and z[1] == "gebuehr_taker"]
        self.assertTrue(zeilen, "mosaic fehlt in der Gebuehren-Tabelle - der "
                                "Befund vom 30.09.2026 kaeme zurueck")
        self.assertAlmostEqual(0.001, zeilen[0][2], places=6)
        self.assertEqual("okx", self.aktive_boerse(
            json.load(open(os.path.join(HANDEL, "mosaic", "wachen.json"),
                           encoding="utf-8"))))


if __name__ == "__main__":
    unittest.main()