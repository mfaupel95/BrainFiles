"""Tests fuer den Fristwaechter der Ausser-Haus-Kopie
(Agenten/Hermes/scripts/ausserhaus-frist-wache.py).

Geprueft wird die REGEL, nicht ein Tageswert:
- frische Kopie            -> LEERE Ausgabe (Watchdog: nichts senden),
- Kopie aelter als die Frist -> ein Befund mit Alter, Frist und Anleitung,
- Ziel fehlt / ist leer / Laufwerk fehlt -> je ein Befund, kein Absturz,
- dieselbe Feststellung    -> innerhalb der Wiederholungsfrist still,
  danach wieder gemeldet,
- --frist-tage 0            -> meldet auch eine frische Kopie (Alarmrichtung).

Gemessen wird in TEMP-Verzeichnissen; Q: wird NICHT angefasst und die
Merkdatei des echten Waechters bleibt unberuehrt.

Start:  python -m unittest test_ausserhaus_frist_wache  (aus diesem Ordner)
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHE_PFAD = HIER / "ausserhaus-frist-wache.py"

_spec = importlib.util.spec_from_file_location("ausserhaus_frist_wache", WACHE_PFAD)
wache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wache)


def baum(anlegen=True, alter_tage=0.0):
    """Temp-Ordner, der eine Kopie darstellt: <ziel>/MaxHirn/Wissen/notiz.md."""
    ziel = Path(tempfile.mkdtemp(prefix="ausserhaus-"))
    if anlegen:
        tief = ziel / "MaxHirn" / "Wissen"
        tief.mkdir(parents=True)
        datei = tief / "notiz.md"
        datei.write_text("inhalt", encoding="utf-8")
        if alter_tage:
            t = time.time() - alter_tage * 86400
            for p in (datei, tief, tief.parent, ziel):
                os.utime(p, (t, t))
    return ziel


class Basis(unittest.TestCase):
    def setUp(self):
        self.merk = Path(tempfile.mkdtemp(prefix="ausserhaus-merk-")) / "merker.json"
        self._ziel, self._merk = wache.ZIEL, wache.MERKDATEI
        wache.MERKDATEI = self.merk

    def tearDown(self):
        wache.ZIEL, wache.MERKDATEI = self._ziel, self._merk
        shutil.rmtree(getattr(self, "ziel", ""), ignore_errors=True)

    def lauf(self, *argumente):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = wache.main(list(argumente))
        return code, puffer.getvalue()


class RegelTest(Basis):

    def test_frische_kopie_ist_still(self):
        self.ziel = baum(anlegen=True, alter_tage=0.5)
        wache.ZIEL = self.ziel
        code, ausgabe = self.lauf()
        self.assertEqual(code, 0)
        self.assertEqual(ausgabe.strip(), "", "frische Kopie darf nichts melden")

    def test_alte_kopie_wird_gemeldet(self):
        self.ziel = baum(anlegen=True, alter_tage=30.0)
        wache.ZIEL = self.ziel
        code, ausgabe = self.lauf()
        self.assertEqual(code, 0)
        self.assertIn("30", ausgabe)
        self.assertIn("Frist", ausgabe)
        self.assertIn(wache.QUELLE_ANLEITUNG, ausgabe)

    def test_frist_grenze_genau_einmal_ueberschritten(self):
        """13 Tage = still, 15 Tage = Befund - die Frist ist 14."""
        self.ziel = baum(anlegen=True, alter_tage=13.0)
        wache.ZIEL = self.ziel
        self.assertEqual(self.lauf()[1].strip(), "")
        shutil.rmtree(self.ziel, ignore_errors=True)
        self.merk.unlink(missing_ok=True)
        self.ziel = baum(anlegen=True, alter_tage=15.0)
        wache.ZIEL = self.ziel
        self.assertNotEqual(self.lauf()[1].strip(), "")

    def test_alarmrichtung_frist_null_meldet_auch_frisch(self):
        """Gegenprobe: mit --frist-tage 0 muss derselbe Aufruf rot werden."""
        self.ziel = baum(anlegen=True, alter_tage=0.5)
        wache.ZIEL = self.ziel
        code, ausgabe = self.lauf("--frist-tage", "0")
        self.assertEqual(code, 0)
        self.assertIn("Tage alt", ausgabe)

    def test_leeres_ziel_wird_gemeldet(self):
        self.ziel = baum(anlegen=False)
        wache.ZIEL = self.ziel
        _, ausgabe = self.lauf()
        self.assertIn("LEER", ausgabe)

    def test_fehlendes_ziel_wird_gemeldet(self):
        self.ziel = baum(anlegen=False)
        wache.ZIEL = self.ziel / "gibt-es-nicht"
        _, ausgabe = self.lauf()
        self.assertIn("fehlt", ausgabe)
        self.assertIn("keine Ausser-Haus-Kopie", ausgabe)

    def test_fehlendes_laufwerk_ist_ein_befund(self):
        """Ein Laufwerk, das es nicht gibt (Y:), darf nicht als 'still' gelten."""
        if os.path.isdir("Y:\\"):
            self.skipTest("Y: ist belegt - Testlaufwerk existiert wirklich")
        wache.ZIEL = Path("Y:/MaxHirn-AusserHaus")
        _, ausgabe = self.lauf()
        self.assertIn("nicht angeschlossen", ausgabe)

    def test_alle_zeigt_den_umfang_bei_gesunder_kopie(self):
        self.ziel = baum(anlegen=True, alter_tage=1.0)
        wache.ZIEL = self.ziel
        _, ausgabe = self.lauf("--alle")
        self.assertIn("in Ordnung", ausgabe)


class WiederholungTest(Basis):

    def test_dieselbe_feststellung_bleibt_still(self):
        self.ziel = baum(anlegen=True, alter_tage=30.0)
        wache.ZIEL = self.ziel
        _, erster = self.lauf()
        self.assertNotEqual(erster.strip(), "")
        _, zweiter = self.lauf()
        self.assertEqual(zweiter.strip(), "",
                         "dieselbe Feststellung darf nicht wiederholt werden")
        # Die Wiederholungsfrist haengt an der Merkdatei: sie muss entstanden sein.
        self.assertTrue(self.merk.exists(), "Merkdatei wurde nicht geschrieben")

    def test_nach_ablauf_der_wiederholung_wieder_gemeldet(self):
        """Merkzeit zurueckdatieren = Frist abgelaufen -> Meldung kommt wieder."""
        import json
        from datetime import datetime, timezone
        self.ziel = baum(anlegen=True, alter_tage=30.0)
        wache.ZIEL = self.ziel
        self.lauf()
        stand = json.loads(self.merk.read_text(encoding="utf-8"))
        alt = (time.time() - (wache.WIEDERHOLUNG_STUNDEN + 1) * 3600)
        for k in stand:
            stand[k] = datetime.fromtimestamp(alt, timezone.utc).isoformat(timespec="seconds")
        self.merk.write_text(json.dumps(stand), encoding="utf-8")
        _, wieder = self.lauf()
        self.assertNotEqual(wieder.strip(), "")

    def test_anderer_befund_wird_nicht_verschluckt(self):
        """Aus 'Kopie alt' wird 'Ziel fehlt' - das ist eine neue Feststellung."""
        self.ziel = baum(anlegen=True, alter_tage=30.0)
        wache.ZIEL = self.ziel
        self.assertNotEqual(self.lauf()[1].strip(), "")
        wache.ZIEL = self.ziel / "weg"
        self.assertIn("fehlt", self.lauf()[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
