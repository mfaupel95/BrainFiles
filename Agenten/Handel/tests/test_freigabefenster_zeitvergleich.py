"""freigabefenster.py: naive/aware-Zeitvergleich darf nie crashen.

Befund 17.09.2026: _jetzt() wurde von UTC-aware auf naive lokale Zeit
umgestellt (Commit d2957a7-Nachfolge), aber ein alter Eintrag in
freigabe_fenster.json trug noch "+00:00" (mit der ALTEN _jetzt() geschrieben).
anfrage_offen() und die bis-Property riefen dt.datetime.fromisoformat()
direkt statt ueber den sicheren _zeit()-Helfer - jeder Dauerlauf-Start
crashte beim Rendern der Startmeldung (TypeError: can't compare
offset-naive and offset-aware datetimes). Der Dauerlauf startete von
04:57 bis 07:47 zwoelfmal neu, ohne einen einzigen Spurenzyklus zu
schaffen (Bus/Waechter hielt den Prozess am Leben, aber wirkungslos).

Diese Tests schreiben NIE in die echte freigabe_fenster.json - DATEI wird
je Test auf eine Temp-Datei umgebogen.
"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)  # Agenten/Handel
if SPUR not in sys.path:
    sys.path.insert(0, SPUR)

import freigabefenster as ff  # noqa: E402


class ZeitfensterMischformTest(unittest.TestCase):
    def setUp(self):
        self._alte_datei = ff.DATEI
        fd, pfad = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        ff.DATEI = pfad
        self.addCleanup(self._aufraeumen, pfad)

    def _aufraeumen(self, pfad):
        ff.DATEI = self._alte_datei
        try:
            os.remove(pfad)
        except OSError:
            pass

    def _schreib_roh(self, inhalt):
        with open(ff.DATEI, "w", encoding="utf-8") as f:
            json.dump(inhalt, f)

    def test_alter_utc_aware_anfrage_bis_crasht_nicht(self):
        """Der genaue Altfall aus freigabe_fenster.json vom 17.09.2026."""
        aware = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
        self._schreib_roh({"scanner": {"anfrage_bis": aware.isoformat()}})
        f = ff.lade("scanner")
        # darf nicht werfen - das war der Crash
        self.assertIsInstance(f.anfrage_offen(), bool)
        self.assertIsInstance(f.text(), str)

    def test_alter_utc_aware_offen_bis_crasht_nicht(self):
        aware = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
        self._schreib_roh({"scanner": {"offen_bis": aware.isoformat()}})
        f = ff.lade("scanner")
        self.assertIsInstance(f.offen(), bool)
        self.assertIsInstance(f.rest_minuten(), int)

    def test_naive_anfrage_bis_bleibt_korrekt(self):
        """Regressionsschutz: der Normalfall (naiv, von _jetzt() selbst
        geschrieben) muss weiter richtig auswerten."""
        naiv = dt.datetime.now() + dt.timedelta(minutes=10)
        self._schreib_roh({"scanner": {"anfrage_bis": naiv.isoformat()}})
        self.assertTrue(ff.lade("scanner").anfrage_offen())

    def test_abgelaufene_aware_anfrage_ist_nicht_offen(self):
        aware = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        self._schreib_roh({"scanner": {"anfrage_bis": aware.isoformat()}})
        self.assertFalse(ff.lade("scanner").anfrage_offen())

    def test_echte_schliessgruende_zaehlen_als_ablehnung(self):
        """Zweiter Fehler in derselben Fremd-Aenderung: der Exact-Match-Fix
        aus FIXES_APPLIED.md (grund in ABLEHNUNGSGRUENDE) hat die eigenen
        Aufrufer in dauerlauf.py zerschossen - 'Telegram stop' und
        'Befehl /stop' sind NIE exakt 'stop' oder 'abgelehnt'. Wortgrenzen-
        Match ist der richtige Mittelweg: trifft echte Gruende, nicht
        'stoppage'/'stopped early'."""
        for grund in ("Telegram stop", "Befehl /stop", "abgelehnt"):
            self._schreib_roh({})
            ff._schreib({"scanner": {"zuletzt_geschlossen":
                                      dt.datetime.now().isoformat(),
                                      "schliess_grund": grund}})
            self.assertFalse(ff.neue_anfrage_erlaubt("scanner"),
                              "Grund %r muss als Ablehnung zaehlen" % grund)

    def test_kein_fehlalarm_bei_aehnlichem_wort(self):
        self._schreib_roh({})
        ff._schreib({"scanner": {"zuletzt_geschlossen":
                                  dt.datetime.now().isoformat(),
                                  "schliess_grund": "stoppage im Feed"}})
        self.assertTrue(ff.neue_anfrage_erlaubt("scanner"),
                         "'stoppage' darf nicht wie 'stop' zaehlen")

    def test_hilfe_rendern_ueber_alle_spuren_crasht_nicht(self):
        """Das war der tatsaechliche Absturzpfad: dauerlauf.hilfe() ruft
        text() fuer jede Spur beim Start auf."""
        aware = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
        self._schreib_roh({
            "scanner": {"anfrage_bis": aware.isoformat()},
            "xperp": {"offen_bis": aware.isoformat()},
        })
        for spur, f in ff.alle().items():
            self.assertIsInstance(f.text(), str)


if __name__ == "__main__":
    unittest.main()
