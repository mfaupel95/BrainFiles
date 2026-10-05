#!/usr/bin/env python3
"""Tests der Konfig-Doktor-Wache - Regeln, keine Tageswerte.

Geprueft wird die REGEL: wann meldet die Wache und wann bleibt sie still.
Alle Pfade werden auf TEMP-Verzeichnisse umgebogen (`verweis_lage` bekommt
Wurzel und Ziel als Argument, `doktor_kurz` bekommt Pfad und Wurzel) - die
ECHTE Wurzel, die echte Junction und der echte Doktor werden nie beruehrt.

Anlass: am 05.10.2026 um 22:12:52 war `BrainFiles/Werkstatt` kein Verweis mehr
auf `O:/Werkstatt`, sondern ein echter, fast leerer Ordner - alle 49 Repos waren
ueber den BrainFiles-Pfad unsichtbar. Die Wache existiert, damit das auffaellt,
OHNE dass jemand zufaellig hinsieht. Der wichtigste Test ist deshalb die
Gegenprobe: ein ECHTES Verzeichnis an der Stelle des Verweises MUSS gemeldet
werden, ein lebender Verweis darf NICHT.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
import time
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SKRIPT = os.path.join(HIER, "konfig-doktor-wache.py")


def laden():
    spec = importlib.util.spec_from_file_location("kd_wache", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class Basis(unittest.TestCase):
    """TEMP-Wurzel, gefaelschter Doktor, Merkdatei im Temp."""

    def setUp(self):
        self.w = laden()
        self.tmp = tempfile.mkdtemp(prefix="kd-wache-")
        self.wurzel = os.path.join(self.tmp, "Wurzel")
        os.makedirs(self.wurzel, exist_ok=True)
        self.ziel = os.path.join(self.tmp, "Ziel")
        os.makedirs(self.ziel, exist_ok=True)
        # Merkdatei und Doktorpfad nach innen biegen.
        self.w.ZUSTAND = os.path.join(self.tmp, "cache", "wache.json")
        self.doktor = os.path.join(self.tmp, "konfig-doktor.ps1")
        with open(self.doktor, "w", encoding="utf-8") as fh:
            fh.write("# Platzhalter\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _verweis(self, name, ziel):
        """Einen echten Verweis anlegen - Junction, wie im Haus."""
        pfad = os.path.join(self.wurzel, name)
        os.symlink(ziel, pfad, target_is_directory=True)
        return pfad

    def _doktor(self, kritisch):
        """doktor_kurz faelschen: liefert (kritisch, zeile, '')."""
        self.w.doktor_kurz = lambda d, w: (
            kritisch, "konfig-doktor: KRITISCH %d | WARNUNG 6" % kritisch, "")


class VerweisRegelTest(Basis):
    """Zeuge 1: der direkte Verweis-Test."""

    def test_lebender_verweis_ist_kein_befund(self):
        self._verweis("Werkstatt", self.ziel)
        self.assertEqual(
            self.w.verweis_lage(self.wurzel, "Werkstatt", self.ziel), "")

    def test_echtes_verzeichnis_ist_ein_befund(self):
        """DER Vorfall vom 05.10.2026 - ein Ordner statt des Verweises."""
        os.makedirs(os.path.join(self.wurzel, "Werkstatt"))
        text = self.w.verweis_lage(self.wurzel, "Werkstatt", self.ziel)
        self.assertIn("KEIN Verweis", text)
        self.assertIn("echter Ordner", text)

    def test_fehlender_verweis_ist_ein_befund(self):
        text = self.w.verweis_lage(self.wurzel, "Werkstatt", self.ziel)
        self.assertIn("fehlt ganz", text)

    def test_toter_verweis_ist_ein_befund(self):
        """Ziel geloescht: der Verweis zeigt ins Leere."""
        self._verweis("Werkstatt", self.ziel)
        shutil.rmtree(self.ziel)
        text = self.w.verweis_lage(self.wurzel, "Werkstatt", self.ziel)
        self.assertNotEqual(text, "", "eine tote Junction muss auffallen")

    def test_der_befund_nennt_den_ordnerinhalt(self):
        """Damit man den Schaden SOFORT einschaetzen kann."""
        d = os.path.join(self.wurzel, "Werkstatt")
        os.makedirs(d)
        for n in ("a.txt", "b.txt"):
            with open(os.path.join(d, n), "w", encoding="utf-8") as fh:
                fh.write("x")
        text = self.w.verweis_lage(self.wurzel, "Werkstatt", self.ziel)
        self.assertIn("2 Eintraege", text)


class MerkfristTest(Basis):
    """Derselbe Befund darf nicht bei jedem Lauf erneut melden."""

    def _lauf(self, kritisch, verweise=None):
        self.w.VERWEISE = verweise or {}
        self._doktor(kritisch)
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            self.w.main([])
        return puffer.getvalue()

    def test_kritisch_wird_gemeldet(self):
        aus = self._lauf(2)
        self.assertIn("2 KRITISCH", aus)

    def test_null_kritisch_bleibt_still(self):
        self.assertEqual(self._lauf(0), "")

    def test_derselbe_befund_wiederholt_sich_nicht(self):
        self.assertIn("KRITISCH", self._lauf(2))
        self.assertEqual(self._lauf(2), "",
                         "zweiter Lauf mit demselben Befund muss leise sein")

    def test_nach_der_merkfrist_wird_wieder_gemeldet(self):
        self.assertIn("KRITISCH", self._lauf(2))
        # Merkzeit zurueckdatieren.
        with open(self.w.ZUSTAND, encoding="utf-8") as fh:
            d = json.load(fh)
        for k in d.get("gesendet", {}):
            d["gesendet"][k] = time.time() - (self.w.WIEDERHOLUNG_H + 1) * 3600
        with open(self.w.ZUSTAND, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
        self.assertIn("KRITISCH", self._lauf(2))


class DoktorAusfallTest(Basis):
    """Ein Fehler der Pruefung ist NIE ein leeres Ergebnis."""

    def test_doktor_fehlt_wird_gemeldet(self):
        self.w.VERWEISE = {}
        self.w.DOKTOR = os.path.join(self.tmp, "gibtsnicht.ps1")
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            self.w.main([])
        self.assertIn("fehlt", puffer.getvalue())

    def test_defekter_doktor_exit2_wird_gemeldet(self):
        """Exit 2 heisst 'Doktor selbst defekt' - das muss raus, nicht schweigen."""
        self.w.VERWEISE = {}
        self.w.doktor_kurz = lambda d, w: (None, "kaputt", "Doktor defekt")
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            self.w.main([])
        self.assertIn("defekt", puffer.getvalue())

    def test_unlesbare_ausgabe_wird_gemeldet(self):
        self.w.VERWEISE = {}
        self.w.doktor_kurz = lambda d, w: (None, "", "keine lesbare Zeile")
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            self.w.main([])
        self.assertIn("lesbare Zeile", puffer.getvalue())


class KennungTest(Basis):
    """Die Kennung ignoriert Zahlen - ein wachsender Wert bleibt derselbe Befund."""

    def test_zahlen_aendern_die_kennung_nicht(self):
        a = self.w._kennung("Werkstatt ist ein echter Ordner (3 Eintraege)")
        b = self.w._kennung("Werkstatt ist ein echter Ordner (99 Eintraege)")
        self.assertEqual(a, b)

    def test_verschiedene_befunde_haben_verschiedene_kennungen(self):
        a = self.w._kennung("Werkstatt fehlt ganz")
        b = self.w._kennung("Modelle fehlt ganz")
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
