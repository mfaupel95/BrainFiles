"""Tests fuer stille_spuren.py - die Urteile, nicht die Formatierung.

Eigener Dateiname: tests/test_stille_spuren.py gehoert bereits zur
Berichtszeile des Tagesberichts (andere Sitzung, anderer Zweck) und bleibt
unberuehrt.

Gebaut mit kuenstlichen Spurenordnern im Tempverzeichnis. Ein Waechter
vergleicht vor- und nachher die Dateien der ECHTEN Spurenordner: kein Test
darf in eine echte Spur schreiben (die Falle, die hier schon zweimal
zugeschlagen hat).
"""
import datetime
import importlib.util
import json
import os
import sys
import tempfile
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_vorher = None


def _abbild():
    """Dateiname -> Groesse, oberste Ebene aller Spurenordner."""
    raus = {}
    for name in sorted(os.listdir(HANDEL)):
        ordner = os.path.join(HANDEL, name)
        if not os.path.isdir(ordner):
            continue
        for datei in ("zustand.json", "handelsjournal.csv", "wachen.json"):
            p = os.path.join(ordner, datei)
            if os.path.isfile(p):
                raus["%s/%s" % (name, datei)] = os.path.getsize(p)
    return raus


def setUpModule():
    global _vorher
    _vorher = _abbild()


def tearDownModule():
    nachher = _abbild()
    if nachher != _vorher:
        neu = set(nachher) - set(_vorher)
        weg = set(_vorher) - set(nachher)
        geaendert = {k for k in set(nachher) & set(_vorher)
                     if nachher[k] != _vorher[k]}
        raise AssertionError(
            "Die Tests haben echte Spurendateien veraendert! "
            "neu=%s entfernt=%s geaendert=%s" % (neu, weg, geaendert))


def lade_modul():
    pfad = os.path.join(HANDEL, "stille_spuren.py")
    spec = importlib.util.spec_from_file_location("stille_spuren_pruef", pfad)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["stille_spuren_pruef"] = mod
    spec.loader.exec_module(mod)
    return mod


class StilleSpurenTest(unittest.TestCase):

    def setUp(self):
        self.mod = lade_modul()
        self.tmp = tempfile.mkdtemp(prefix="stille_")
        # pruefe() arbeitet relativ zu HIER - auf den Tempordner biegen,
        # damit kein echter Spurenordner gelesen oder beruehrt wird.
        self.mod.HIER = self.tmp
        self.jetzt = datetime.datetime.now(datetime.timezone.utc)

    def _spur(self, name, zustand):
        ordner = os.path.join(self.tmp, name)
        os.makedirs(ordner, exist_ok=True)
        with open(os.path.join(ordner, "zustand.json"), "w",
                  encoding="utf-8") as f:
            json.dump(zustand, f)
        return ordner

    def _frisch(self):
        return (self.jetzt - datetime.timedelta(minutes=5)).isoformat()

    def _zustands_paar(self, name, papier_h, live_h):
        """Papierbuch und Live-Buch mit verschiedenem Alter."""
        ordner = os.path.join(self.tmp, name)
        os.makedirs(ordner, exist_ok=True)
        for datei, stunden in (("zustand.json", papier_h),
                               ("zustand.live.json", live_h)):
            with open(os.path.join(ordner, datei), "w", encoding="utf-8") as f:
                json.dump({"letzter_lauf":
                           (self.jetzt - datetime.timedelta(hours=stunden))
                           .isoformat(), "positionen": []}, f)
        return ordner

    def test_frischer_live_zustand_gilt_als_laufend(self):
        """Eine live laufende Spur schreibt den Papierzweig nicht mehr.

        Befund 23.09.2026: moondev_marktlage lief alle 15 Minuten live, ihr
        zustand.json stand seit dem Morgen still - die Wache meldete "TOT".
        """
        self._zustands_paar("live_spur", papier_h=7.0, live_h=0.2)
        r = self.mod.pruefe("live_spur", "live_spur")
        self.assertNotEqual(r["lage"], "TOT", r["text"])

    def test_beide_staende_alt_bleibt_tot(self):
        self._zustands_paar("tote_spur", papier_h=9.0, live_h=8.0)
        r = self.mod.pruefe("tote_spur", "tote_spur")
        self.assertEqual(r["lage"], "TOT")

    def test_kaputte_live_datei_kippt_nicht_auf_tot(self):
        ordner = self._spur("halb",
                            {"letzter_lauf": self._frisch(), "positionen": []})
        with open(os.path.join(ordner, "zustand.live.json"), "w") as f:
            f.write("{ kein json")
        r = self.mod.pruefe("halb", "halb")
        self.assertNotEqual(r["lage"], "TOT", r["text"])

    def test_frischer_zustand_ohne_buch_ist_wartet(self):
        """Eine neue Spur ohne Signal ist gesund, nicht kaputt."""
        self._spur("neu", {"letzter_lauf": self._frisch(), "positionen": []})
        e = self.mod.pruefe("neu", "neu")
        self.assertEqual(e["lage"], "WARTET")
        self.assertFalse(e["auffaellig"])

    def test_alter_zustand_ist_tot(self):
        alt = (self.jetzt - datetime.timedelta(hours=48)).isoformat()
        self._spur("alt", {"letzter_lauf": alt, "positionen": []})
        e = self.mod.pruefe("alt", "alt")
        self.assertEqual(e["lage"], "TOT")
        self.assertTrue(e["auffaellig"])

    def test_fehlender_ordner_ist_tot(self):
        e = self.mod.pruefe("gibtsnicht", "gibtsnicht")
        self.assertEqual(e["lage"], "TOT")
        self.assertTrue(e["auffaellig"])

    def test_offene_position_ohne_faellige_frist_ist_haelt(self):
        """Der Normalfall der nautilus-Arme: im Plus, Frist laeuft noch."""
        spaeter = (self.jetzt + datetime.timedelta(hours=12)).isoformat()
        self._spur("haelt", {
            "letzter_lauf": self._frisch(),
            "positionen": [{"symbol": "BTC", "frist": spaeter}]})
        e = self.mod.pruefe("haelt", "haelt")
        self.assertEqual(e["lage"], "HAELT")
        self.assertFalse(e["auffaellig"])

    def test_abgelaufene_frist_ist_ueberfaellig(self):
        """Der eigentliche Befund: Frist vorbei, kein Ausstieg gebucht."""
        vorbei = (self.jetzt - datetime.timedelta(hours=3)).isoformat()
        self._spur("spaet", {
            "letzter_lauf": self._frisch(),
            "positionen": [{"symbol": "BTC", "frist": vorbei}]})
        e = self.mod.pruefe("spaet", "spaet")
        self.assertEqual(e["lage"], "UEBERFAELLIG")
        self.assertTrue(e["auffaellig"])
        self.assertIn("BTC", e["text"])

    def test_position_als_dict_zaehlt_als_eine(self):
        """orbk fuehrt genau einen Platz und speichert ihn als Dict."""
        spaeter = (self.jetzt + datetime.timedelta(hours=5)).isoformat()
        self._spur("einsplatz", {
            "letzter_lauf": self._frisch(),
            "positionen": {"symbol": "ETH", "frist": spaeter}})
        e = self.mod.pruefe("einsplatz", "einsplatz")
        self.assertEqual(e["lage"], "HAELT")
        self.assertIn("1 Position", e["text"])

    def test_spurliste_kommt_aus_dauerlauf(self):
        """Neue Spuren muessen von selbst erscheinen, ohne dieses Werkzeug
        zu aendern - deshalb wird dauerlauf.SPUREN gelesen."""
        mod = lade_modul()          # echtes HIER, nur lesend
        namen = [n for n, _ in mod.spuren()]
        self.assertGreater(len(namen), 20)
        self.assertIn("xperp", namen)
        self.assertIn("scanner", namen)

    def test_wache_schweigt_wenn_alles_gesund(self):
        self._spur("ruhig", {"letzter_lauf": self._frisch(), "positionen": []})
        e = self.mod.pruefe("ruhig", "ruhig")
        self.assertFalse(e["auffaellig"])


if __name__ == "__main__":
    unittest.main()
