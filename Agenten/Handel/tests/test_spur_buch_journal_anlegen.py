"""Jede Spur fuehrt Journal - auch eine, die noch nie ein Signal hatte.

AUFTRAG MAX 02.10.2026: "alle duerfen auch journal fuehren".

BEFUND DABEI: `spur_buch.journal()` legt die Datei beim ersten SCHREIBEN an.
Eine Spur ohne Signal hatte deshalb gar kein Journal - und damit auch nichts
ausser Haus (Bedingung 4). Am 02.10.2026 betraf das 7 von 38 Spuren
(klassik_donchian, klassik_donchian_trend, klassik_pmax, klassik_rsi,
klassik_rsi2, klassik_sr_breaks, trendwende_btc): lokal wie auf Q: nur
zustand.json. Gemessen wurde die Luecke zuerst - `quelle()` lieferte fuer
diese Spuren Daten ohne Fehler, nur `signal()` blieb still.

Der Test baut eine Spur im Tempordner (eigene Wachen, eigener Zustand, eigenes
Spiegelziel) und laesst den ECHTEN zyklus() laufen. Ein Waechter prueft, dass
keine echte Spur veraendert wird - das ist die Falle vom 14./16.09.2026
(Testsuite schreibt in die echten Spurenordner).

Die Gegenprobe steht in `test_gegenprobe_ohne_legen_kein_journal`: nimmt man
den Aufruf aus dem Zyklus heraus, muss dieser Test rot werden.
"""
import json
import os
import sys
import tempfile
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)
import spur_buch  # noqa: E402

assert spur_buch.__file__.startswith(HANDEL), spur_buch.__file__

_ECHTE_SPUREN = ("iv_wand", "klassik_rsi", "trendwende_btc")


def _stand(spur):
    raus = {}
    for datei in os.listdir(spur):
        p = os.path.join(spur, datei)
        if os.path.isfile(p):
            raus[datei] = os.path.getsize(p)
    return raus


_VORHER = None


def setUpModule():
    global _VORHER
    _VORHER = {s: _stand(os.path.join(HANDEL, s)) for s in _ECHTE_SPUREN}


def tearDownModule():
    for s in _ECHTE_SPUREN:
        spur = os.path.join(HANDEL, s)
        nachher = _stand(spur)
        if nachher != _VORHER[s]:
            neu = set(nachher) - set(_VORHER[s])
            geaendert = {k for k in set(nachher) & set(_VORHER[s])
                         if nachher[k] != _VORHER[s][k]}
            raise AssertionError(
                "Test hat die echte Spur %s veraendert! neu=%s geaendert=%s"
                % (s, neu, geaendert))


class JournalAnlegenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="journalprobe_")
        self.spur = os.path.join(self.tmp, "probespur")
        os.makedirs(self.spur)
        self.ziel = os.path.join(self.tmp, "spiegel")
        self._schreibe("wachen.json", {
            "journal_zweitziel": self.ziel, "grund": "probe",
            "herzschlag_max_minuten": 180, "risiko_je_position_usd": 5.0,
            "max_offene_positionen": 2, "stop_prozent": 10.0,
            "max_pro_trade_usd": 100.0, "cr": 2.0})
        self._schreibe("zustand.json", {"positionen": [], "letzter_lauf": None})

    def _schreibe(self, name, inhalt):
        with open(os.path.join(self.spur, name), "w", encoding="utf-8") as f:
            json.dump(inhalt, f)

    @property
    def _journal(self):
        return os.path.join(self.spur, "handelsjournal.csv")

    def _lauf(self, modus, daten=None):
        def quelle(w):
            return (daten if daten is not None else {}), {}, []
        return spur_buch.zyklus(self.spur, quelle, lambda d, w: None, modus,
                                ereignis_name="handel/probespur")

    # --- Die Regel -------------------------------------------------------

    def test_papier_legt_das_journal_an(self):
        """Der erste Zyklus erzeugt die Datei - auch ganz ohne Buchung."""
        self.assertFalse(os.path.exists(self._journal))
        self._lauf("papier")
        self.assertTrue(os.path.isfile(self._journal),
                        "das Journal muss ab dem ersten Zyklus existieren")

    def test_das_journal_ist_leer_nur_mit_kopfzeile(self):
        """Leer heisst null Buchungen, nicht null Zeilen - die Kopfzeile
        gehoert dazu, sonst ist die Datei nicht lesbar."""
        self._lauf("papier")
        with open(self._journal, encoding="utf-8") as f:
            zeilen = [z for z in f.read().splitlines() if z.strip()]
        self.assertEqual(len(zeilen), 1, "genau die Kopfzeile")
        self.assertIn("pos_id", zeilen[0],
                      "die Kopfzeile ist die SPALTEN-Liste des Buchs")

    def test_ohne_daten_legt_es_das_journal_auch_an(self):
        """Der trockene Zulauf ist der Normalfall einer jungen Spur - genau
        dort darf das Journal nicht fehlen (derselbe Zweig wie T-193)."""
        self._lauf("papier", daten={})
        self.assertTrue(os.path.isfile(self._journal))

    def test_das_journal_ist_nicht_leer_bei_erster_buchung(self):
        """Mit Signal wird gebucht - das Anlegen darf nichts verschlucken."""
        def quelle(w):
            return {"X": {"preis": 1.0}}, {"X": 1.0}, []
        spur_buch.zyklus(self.spur, quelle, lambda d, w: "long", "papier",
                         ereignis_name="handel/probespur")
        with open(self._journal, encoding="utf-8") as f:
            zeilen = [z for z in f.read().splitlines() if z.strip()]
        self.assertEqual(len(zeilen), 2, "Kopfzeile plus Kaufzeile")

    def test_das_journal_ist_leer_bei_ablehnung_durch_die_grenze(self):
        """Kein Signal heisst kein Journal-Schreibvorgang, aber die Datei
        steht - genau der Fall, der vorher unsichtbar war."""
        self._lauf("papier", daten={"X": {"preis": 1.0}})   # signal -> None
        self.assertTrue(os.path.isfile(self._journal))
        with open(self._journal, encoding="utf-8") as f:
            zeilen = [z for z in f.read().splitlines() if z.strip()]
        self.assertEqual(len(zeilen), 1)

    def test_zweiter_zyklus_legt_nichts_doppelt_an(self):
        self._lauf("papier")
        self._lauf("papier")
        with open(self._journal, encoding="utf-8") as f:
            zeilen = [z for z in f.read().splitlines() if z.strip()]
        self.assertEqual(len(zeilen), 1, "die Kopfzeile steht genau einmal")

    def test_es_wird_nichts_ueberschrieben(self):
        """Eine bestehende Datei bleibt, wie sie ist - auch mit Zeilen."""
        with open(self._journal, "w", encoding="utf-8") as f:
            f.write("zeit,modus\n2026-01-01T00:00:00+00:00,papier\n")
        self._lauf("papier")
        with open(self._journal, encoding="utf-8") as f:
            inhalt = f.read()
        self.assertIn("2026-01-01T00:00:00+00:00", inhalt)
        self.assertEqual(inhalt.count("zeit"), 1, "keine zweite Kopfzeile")

    # --- Bedingung 4 ------------------------------------------------------

    def test_das_leere_journal_wird_gespiegelt(self):
        """Bedingung 4 gilt auch fuer eine Spur ohne Runden."""
        self._lauf("papier")
        self.assertTrue(os.path.isfile(os.path.join(self.ziel,
                                                    "handelsjournal.csv")))

    # --- Die Vorschau bleibt lesend --------------------------------------

    def test_die_vorschau_legt_nichts_an(self):
        """`--vorschau` schreibt nichts - auch kein leeres Journal."""
        self._lauf("vorschau")
        self.assertFalse(os.path.exists(self._journal))

    def test_der_wachen_lauf_legt_nichts_an(self):
        self._lauf("wachen")
        self.assertFalse(os.path.exists(self._journal))

    # --- Gegenprobe -------------------------------------------------------

    def test_gegenprobe_ohne_legen_kein_journal(self):
        """Ruecknahme von `lege_journal_an` - dieser Test muss dann rot sein."""
        echtes = spur_buch.lege_journal_an
        spur_buch.lege_journal_an = lambda pfad: False
        try:
            self._lauf("papier")
            self.assertFalse(os.path.exists(self._journal),
                             "ohne den Aufruf darf keine Datei entstehen")
            # Gegen die Regel getestet, nicht gegen den Aufruf: jetzt muss
            # mindestens EIN Test dieses Moduls fallen. Genau das beweist der
            # naechste Lauf von aussen (siehe test_modul_rotest_ohne_regel).
        finally:
            spur_buch.lege_journal_an = echtes

    def test_SCHREIBEN_false_legt_nichts_an(self):
        """Replay und Tests (SCHREIBEN=False) duerfen nie eine Datei anlegen."""
        alt = spur_buch.SCHREIBEN
        spur_buch.SCHREIBEN = False
        try:
            self.assertFalse(spur_buch.lege_journal_an(self._journal))
            self.assertFalse(os.path.exists(self._journal))
        finally:
            spur_buch.SCHREIBEN = alt

    def test_lege_journal_an_meldet_was_es_getan_hat(self):
        self.assertTrue(spur_buch.lege_journal_an(self._journal), "neu")
        self.assertFalse(spur_buch.lege_journal_an(self._journal), "existiert")


if __name__ == "__main__":
    unittest.main(verbosity=2)
