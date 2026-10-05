"""Historie atomar schreiben, und eine kaputte Datei BENENNEN (05.10.2026).

Der Befund: `spur_audit.py --spur <x>` stuerzte mitten im Lauf ab
(json.load scheiterte). Ursache war nicht die Spur, sondern das Schreiben:
`historie_binance.speichere()` oeffnete die Zieldatei mit "w" und schrieb
hinein. Ein Leser, der im Betrieb genau dann laed (der Dauerlauf laeuft,
es sind 82 Python-Prozesse), sieht eine halbe Datei.

Diese Tests halten beide Seiten fest:

1. SCHREIBEN: waehrend `speichere()` laeuft, ist die alte Datei noch lesbar
   und vollstaendig - nie eine halbe.
2. LESEN: eine kaputte Datei fuehrt zu `HistorieKaputt` mit Pfad und
   Zeichenlaenge, NICHT zu einem stillen [].

Direkt ausfuehrbar:  python tests/test_historie_atomar.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import historie_binance as hb                                   # noqa: E402


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ordner = Path(self.tmp.name) / "historie"
        p = patch.object(hb, "ORDNER", str(self.ordner))
        p.start()
        self.addCleanup(p.stop)
        self.ordner.mkdir(parents=True, exist_ok=True)   # die Lesetests
        # schreiben direkt hinein, speichere() waere der einzige Erzeuger

    def kerzen(self, n=5, start=1700000000000):
        return [[start + i * 3600000, i + 1.0, i + 2.0, i, i + 3.0, 100.0]
                for i in range(n)]


class Schreiben(Basis):
    def test_keine_tmp_bleibt_liegen(self):
        hb.speichere("BTC", "1H", self.kerzen())
        self.assertEqual(sorted(os.listdir(self.ordner)), ["BTCUSDT_1H.json"])

    def test_ergebnis_ist_vollstaendig(self):
        hb.speichere("BTC", "1H", self.kerzen(7))
        self.assertEqual(len(hb.lade("BTC", "1H")), 7)

    def test_anhaengen_behaelt_den_bestand(self):
        hb.speichere("BTC", "1H", self.kerzen(5))
        # ECHT neue Zeitstempel - dieselben wuerden entdoppelt
        hb.speichere("BTC", "1H", self.kerzen(2, start=1700000000000 + 10 * 3600000))
        self.assertEqual(len(hb.lade("BTC", "1H")), 7)

    def test_waehrend_des_schreibens_bleibt_die_alte_datei_lesbar(self):
        """Das ist der eigentliche Test: der Leser darf keine halbe Datei sehen.

        Der Schreibvorgang wird im json.dump angehalten und in diesem Moment
        gelesen. Ohne .tmp + os.replace waere die Datei hier abgeschnitten.
        """
        hb.speichere("BTC", "1H", self.kerzen(5))
        alt = hb.lade("BTC", "1H")
        ziel = hb.datei("BTC", "1H")
        gesehen = {}

        echtes_dump = json.dump

        def haelt_durch(obj, f, **kw):
            # in die offene Datei schreiben, dann den Leser dazwischenrufen
            teil = json.dumps(obj[: len(obj) // 2])
            f.write(teil)
            f.flush()
            try:
                with open(ziel, encoding="utf-8") as leser:
                    gesehen["inhalt"] = leser.read()
            except OSError as e:
                gesehen["fehler"] = str(e)
            return echtes_dump(obj, f, **kw)

        with patch.object(hb.json, "dump", haelt_durch):
            hb.speichere("BTC", "1H", self.kerzen(9))

        self.assertIn("inhalt", gesehen,
                      "die Zieldatei war waehrend des Schreibens gar nicht lesbar")
        # Was der Leser sah, ist VOLLSTAENDIG - entweder alt (5 Kerzen) oder
        # neu (9), aber kein abgeschnittenes JSON.
        try:
            gelesen = json.loads(gesehen["inhalt"])
        except json.JSONDecodeError as e:
            self.fail("der Leser sah eine halbe Datei: %s" % e)
        self.assertIn(len(gelesen), (5, 9), gelesen.__len__())
        self.assertEqual(len(alt), 5)

    def test_die_neue_datei_ist_komplett(self):
        hb.speichere("BTC", "1H", self.kerzen(11))
        with open(hb.datei("BTC", "1H"), encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)), 11)


class Lesen(Basis):
    def test_fehlende_datei_ist_leer_kein_fehler(self):
        # ZAR "gibt es nicht" heisst: gueltiger Name, aber keine Datei.
        # Ein UNBEKANNTER Name ist etwas anderes - da ist KeyError richtig.
        self.assertEqual(hb.lade("XLM", "1H"), [])
        with self.assertRaises(KeyError):
            hb.lade("GIBTSNICHT", "1H")

    def test_leere_datei_ist_leer(self):
        (self.ordner / "BTCUSDT_1H.json").write_text("", encoding="utf-8")
        self.assertEqual(hb.lade("BTC", "1H"), [])

    def test_kaputte_datei_wird_benannt(self):
        ziel = self.ordner / "BTCUSDT_1H.json"
        ziel.write_text('[{"kaputt', encoding="utf-8")
        with self.assertRaises(hb.HistorieKaputt) as ctx:
            hb.lade("BTC", "1H")
        text = str(ctx.exception)
        self.assertIn("BTCUSDT_1H.json", text)
        self.assertIn("9", text)               # Zeichen gelesen
        self.assertIn("geschrieben", text)     # die naheliegende Ursache

    def test_leerer_inhalt_ist_kein_kaputt(self):
        (self.ordner / "BTCUSDT_1H.json").write_text("   \n", encoding="utf-8")
        self.assertEqual(hb.lade("BTC", "1H"), [])

    def test_echte_kerzen_bleiben_lesbar(self):
        hb.speichere("BTC", "1H", self.kerzen(4))
        self.assertEqual(len(hb.lade("BTC", "1H")), 4)

    def test_historiekaputt_ist_kein_oserror(self):
        # Wer `except OSError` schreibt, faengt es NICHT - so bleibt die
        # Unterscheidung "fehlt" (leer) gegen "da, aber kaputt" (benannt).
        self.assertFalse(issubclass(hb.HistorieKaputt, OSError))
        self.assertFalse(issubclass(hb.HistorieKaputt, ValueError))


if __name__ == "__main__":
    unittest.main()