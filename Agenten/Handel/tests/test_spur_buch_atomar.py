"""EIN Ausstieg = EINE Buchung: Journal UND Zustand zusammen (T-356).

BEFUND 05.10.2026: die Position NIGHT (moondev_signalwelle) stand doppelt im
Buch - das Journal hatte sie am 05.10. um 02:26:36 verkauft (grund=stop), der
Zustand fuehrte sie weiter offen. Ursache im Quelltext: `pruefe_ausstiege()`
schrieb die Verkaufszeile direkt ins Journal, der `--vorschau`-Zweig von
`zyklus()` kehrte davor ohne `schreibe_zustand()` zurueck. Jeder spätere
Zyklus sah die Position offen und verkaufte sie erneut.

DIE EIGENSCHAFT, die hier geprueft wird: Eine Buchung ist Journalzeile UND
Zustand in einem Aufruf (spur_buch.buche). Eine Vorschau schreibt GAR nichts.
Dadurch kann eine Journalzeile nie ohne den dazugehoerigen Zustand entstehen
- und umgekehrt.

Der Test baut eine Spur im Tempordner und laesst den ECHTEN zyklus() laufen
(ohne Netz, ohne echte Spurdatei, Bus-stumm). Keine echte Spur wird
angefasst.
"""
import contextlib
import json
import os
import sys
import tempfile
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)
BUS = os.path.join(os.path.dirname(HANDEL), "Bus")
if BUS not in sys.path:
    sys.path.insert(0, BUS)
import spur_buch  # noqa: E402
import ereignis  # noqa: E402

assert spur_buch.__file__.startswith(HANDEL), spur_buch.__file__

WACHEN = {"journal_zweitziel": None, "grund": "probe",
          "herzschlag_max_minuten": 180, "risiko_je_position_usd": 5.0,
          "max_offene_positionen": 2, "stop_prozent": 10.0,
          "max_pro_trade_usd": 100.0, "cr": 2.0}

POSITION = {"inst": "X", "seite": "long", "einstieg": 100.0, "stop": 90.0,
            "ziel": 130.0, "stop_pct": 10.0, "nominal": 50.0,
            "modus": "papier", "pos_id": "pos-1",
            "eroeffnet_zeit": "2026-10-04T00:00:00+00:00"}


class AtomarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="atomar_")
        self.spur = os.path.join(self.tmp, "probespur")
        os.makedirs(self.spur)
        self.ziel = os.path.join(self.tmp, "spiegel")
        self._schreibe("wachen.json", dict(WACHEN, journal_zweitziel=self.ziel))
        self._schreibe("zustand.json", {"positionen": [dict(POSITION)],
                                        "letzter_lauf": None})
        # Der Bus ist nicht Teil dieser Pruefung: ereignis.lauf wird
        # stummgeschaltet, damit kein Testlauf im echten Bus-Journal landet.
        self._alt_lauf = ereignis.lauf
        ereignis.lauf = lambda *a, **k: contextlib.nullcontext()

    def tearDown(self):
        ereignis.lauf = self._alt_lauf
        for p in (os.path.join(self.spur, name) for name in os.listdir(self.spur)):
            try:
                os.remove(p)
            except OSError:
                pass
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _schreibe(self, name, inhalt):
        with open(os.path.join(self.spur, name), "w", encoding="utf-8") as f:
            json.dump(inhalt, f)

    @property
    def _journal(self):
        return os.path.join(self.spur, "handelsjournal.csv")

    def _zustand(self):
        with open(os.path.join(self.spur, "zustand.json"), encoding="utf-8") as f:
            return json.load(f)

    def _lauf(self, modus, daten, kurse, signal=None):
        def quelle(w):
            return daten, kurse, []
        return spur_buch.zyklus(
            self.spur, quelle, (signal or (lambda d, w: None)), modus,
            ereignis_name="handel/probespur")

    def _verkaufszeilen(self):
        if not os.path.exists(self._journal):
            return 0
        with open(self._journal, encoding="utf-8") as f:
            import csv
            return sum(1 for z in csv.DictReader(f) if z["aktion"] == "verkauf")

    # --- Der Geist vom 05.10.2026 -----------------------------------------

    def test_vorschau_bucht_keinen_ausstieg(self):
        """Die Vorschau schreibt NICHTS - auch keine Verkaufszeile.

        Vor dem Fix buchte `pruefe_ausstiege()` hier die Verkaufszeile, der
        Vorschau-Zweig kehrte danach ohne `schreibe_zustand()` zurueck:
        Journal verkauft, Zustand offen (NIGHT, T-356).
        """
        self._lauf("vorschau", {"X": {"preis": 1.0}}, {"X": 85.0})
        self.assertFalse(os.path.exists(self._journal),
                         "die Vorschau hat keine Journalzeile geschrieben")
        z = self._zustand()
        self.assertEqual([p["inst"] for p in z["positionen"]], ["X"],
                         "der Zustand fuehrt die Position weiter offen")
        self.assertIsNone(z.get("letzter_lauf"),
                          "auch der Zustand blieb unberuehrt")

    def test_ausstieg_bucht_genau_einmal(self):
        """Ein Ausstieg erzeugt GENAU EINE Buchung: Verkaufszeile UND Zustand.

        Der zweite Zyklus sieht die Position nicht mehr - ein Doppelverkauf
        wie bei NIGHT ist damit strukturell weg.
        """
        self._lauf("papier", {"X": {"preis": 1.0}}, {"X": 85.0})
        self.assertEqual(self._verkaufszeilen(), 1,
                         "genau eine Verkaufszeile im Journal")
        self.assertEqual(self._zustand()["positionen"], [],
                         "die Position ist aus dem Zustand verschwunden")
        # Zweiter Zyklus: dieselbe Quelle, keine Position mehr.
        self._lauf("papier", {"X": {"preis": 1.0}}, {"X": 85.0})
        self.assertEqual(self._verkaufszeilen(), 1,
                         "kein zweiter Verkauf - das war der Geist")

    def test_einstieg_bucht_journal_und_zustand_zusammen(self):
        self._schreibe("zustand.json", {"positionen": [], "letzter_lauf": None})
        self._lauf("papier", {"X": {"preis": 1.0}}, {"X": 100.0},
                   signal=lambda d, w: "long")
        with open(self._journal, encoding="utf-8") as f:
            import csv
            zeilen = list(csv.DictReader(f))
        self.assertEqual([z["aktion"] for z in zeilen], ["kauf"])
        z = self._zustand()
        self.assertEqual([p["inst"] for p in z["positionen"]], ["X"],
                         "der Zustand fuehrt die neue Position sofort")

    # --- buche ist fail-closed -------------------------------------------

    def test_buche_ohne_zustandspfad_wirft(self):
        """Eine Buchung ohne Zustand ist ein Geist - laut abbrechen, nicht
        still nur ins Journal schreiben."""
        j = os.path.join(self.tmp, "waise.csv")
        with self.assertRaises(ValueError):
            spur_buch.buche({"positionen": []}, None, j,
                            zeit="2026-10-05T00:00:00+00:00", aktion="kauf")
        self.assertFalse(os.path.exists(j), "es wurde nichts geschrieben")

    def test_buche_schreibt_nichts_bei_SCHREIBEN_false(self):
        """Replay und Tests (SCHREIBEN=False) duerfen nie schreiben."""
        j = os.path.join(self.tmp, "replay.csv")
        z = os.path.join(self.tmp, "replay.json")
        alt = spur_buch.SCHREIBEN
        spur_buch.SCHREIBEN = False
        try:
            spur_buch.buche({"positionen": []}, z, j,
                            zeit="2026-10-05T00:00:00+00:00", aktion="kauf")
            self.assertFalse(os.path.exists(j))
            self.assertFalse(os.path.exists(z))
        finally:
            spur_buch.SCHREIBEN = alt


if __name__ == "__main__":
    unittest.main(verbosity=2)
