"""Regel: der Einstieg ist der MARKTkurs, nicht der Preis des Berichts.

Anlass (03.10.2026, Befund T-316): der Scanner wurde als mit Abstand
beste Spur gefuehrt (+17,49 % ueber 124 Runden, 85 % Trefferquote,
t = 15,3). Die Ursache war kein Signal, sondern ein Rechenfehler:

  * vorschlaege() nahm den Einstieg aus dem Tagesbericht
    (bewertung.bewerten -> preis = schluss[-1] der 1D-Kerze).
  * Der Bericht vom 17.09. 05:30 trug AVAX-USDT mit 7,531.
  * Der Markt am 19.09. 02:50 (Kaufzeitpunkt) lag bei 8,535-8,747.
  * Einstieg 12 % UNTER Markt -> Ziel = Einstieg + 2x Stop war beim
    Kauf bereits erfuellt -> der naechste Zyklus (15 min spaeter)
    verkaufte im Ziel mit ~15 % Gewinn. 82 Runden an einem Tag,
    Summe +1866 % an einem einzigen Tag.
  * 97 von 105 Ziel-Ausstiegen kamen nach 0,25 h. Ein echter Markt-
    ausstieg braucht Tage.

Die Regel gilt fuer Papier UND Live: beide buchen denselben Einstieg.

Geprueft wird die EIGENSCHAFT, nicht ein Tageswert:
  1. Der Einstieg entspricht dem zur Kaufzeit abgerufenen Kurs.
  2. Ein zurueckgesetzter Berichtspreis aendert daran nichts (Gegen-
     probe: der Fehler von damals).
  3. Ein nicht abrufbarer Kurs fuehrt zur Ablehnung, NICHT zum
     Berichtspreis als Notfall (sonst waere der Fehler wieder da).
  4. Das Ziel wird aus dem Einstieg gerechnet (2:1 bleibt erhalten).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SPUR)
sys.path.insert(0, os.path.join(os.path.dirname(SPUR), "scanner"))

import handeln  # noqa: E402


class EinstiegIstMarktkursTest(unittest.TestCase):
    def setUp(self):
        self.okx = sys.modules["okx"]
        self._alt = self.okx.letzter_kurs
        # 03.10.2026: dieser Test rief vorschlaege() mit SCHREIBEN=True und
        # ungebogenem Pfad. vorschlaege() protokolliert je Markt
        # ('bewertete Maerkte', 'Kurs nicht abrufbar'), also landete jede
        # Ausfuehrung in der ECHTEN scanner/ablehnungen.csv - belegt durch
        # die Zeile '2026-10-02T22:15:57+00:00,zyklus,bewertete Maerkte,1'
        # mitten im echten Protokoll und durch den Modulwaechter
        # test_papier_laesst_live_stehen, der 'geaendert=[ablehnungen.csv]'
        # meldete. Das ist Stufe 2 in der Hauslogik, aber die Datei IST das
        # Betriebsprotokoll: ein Test darf sie nicht anfassen.
        # Zwei Schranken, weil beide noetig sind: SCHREIBEN=False nimmt dem
        # Aufrufer das Schreiben, der umgebogene Pfad schuetzt die Datei,
        # falls ein spaeterer Test SCHREIBEN wieder anstellt.
        self._alt_schreiben = handeln.SCHREIBEN
        self._alt_abl = handeln.ABLEHNUNGEN
        handeln.SCHREIBEN = False
        handeln.ABLEHNUNGEN = Path(tempfile.gettempdir()) / (
            "scan_marktkurs_%d.csv" % os.getpid())

    def tearDown(self):
        self.okx.letzter_kurs = self._alt
        # REIHENFOLGE: die Temp-Datei wird GELOESCHT, BEVOR der Pfad
        # zurueckgesetzt wird. Sonst loescht der tearDown die ECHTE Datei -
        # genau das ist beim ersten Versuch passiert (03.10.2026, die
        # scanner/ablehnungen.csv war danach weg). Ein Reihenfolgefehler in
        # einem Test-Waechter ist teurer als der Waechter selbst.
        try:
            handeln.ABLEHNUNGEN.unlink(missing_ok=True)
        except OSError:
            pass
        handeln.SCHREIBEN = self._alt_schreiben
        handeln.ABLEHNUNGEN = self._alt_abl

    def _bericht(self, berichtspreis, score=70.0, verhaeltnis=2.0, vola=1.0):
        return {"werte": [{"inst": "AVAX-USDT", "preis": berichtspreis,
                           "score": score, "chance": 70.0, "risiko": 35.0,
                           "verhaeltnis": verhaeltnis,
                           "kennzahlen": {"volatilitaet_pa": vola}}]}

    def _wachen(self):
        return {"mindest_score": 60, "max_volatilitaet_pa": 2.0,
                "mindest_chance_risiko": 1.5,
                "pflicht_stop_prozent_min": 5.0,
                "pflicht_stop_prozent_max": 12.0,
                "max_pro_trade_usd": 120.0, "risiko_je_position_usd": 6.0}

    # 1) Grundregel
    def test_einstieg_ist_der_jetzt_kurs(self):
        self.okx.letzter_kurs = lambda inst: 8.60
        vs = handeln.vorschlaege(self._bericht(7.531), self._wachen())
        self.assertEqual(len(vs), 1)
        self.assertAlmostEqual(vs[0]["einstieg"], 8.60, places=6,
                               msg="Einstieg muss der Jetzt-Kurs sein")

    # 2) Gegenprobe: genau der Fehler vom 19.09.
    def test_gegenprobe_veralteter_berichtspreis(self):
        """Mit zurueckgesetztem Code (Berichtspreis als Einstieg) faellt
        der Test - er prueft die Regel, nicht den Tageswert."""
        self.okx.letzter_kurs = lambda inst: 8.60
        bericht = self._bericht(7.531)
        alt = handeln.vorschlaege(bericht, self._wachen())
        # Nachbildung des alten Verhaltens: Einstieg = Berichtspreis.
        self.assertAlmostEqual(alt[0]["einstieg"], 8.60, places=6)
        alt_einstieg = bericht["werte"][0]["preis"]
        # Das Ziel lag beim alten Code 1,07 USD unter dem Markt.
        altes_ziel = alt_einstieg + 2 * (alt_einstieg - alt_einstieg * 0.937)
        self.assertLess(altes_ziel, 8.60,
                        "alter Zielpreis waere sofort erfuellt - das ist der Fehler")
        self.assertGreater(vs_ziel := alt[0]["ziel"], 8.60,
                           "neues Ziel muss ueber dem Markt liegen")

    # 3) Kein Kurs -> Ablehnung, kein Notfallpreis
    def test_ohne_kurs_keine_position(self):
        self.okx.letzter_kurs = lambda inst: 0.0
        vs = handeln.vorschlaege(self._bericht(7.531), self._wachen())
        self.assertEqual(vs, [], "ohne Kurs darf keine Position entstehen")

        self.okx.letzter_kurs = lambda inst: None
        self.assertEqual(handeln.vorschlaege(self._bericht(7.531),
                                             self._wachen()), [])

    # 4) Geometrie 2:1 bleibt
    def test_ziel_bleibt_zweifacher_stop_abstand(self):
        self.okx.letzter_kurs = lambda inst: 100.0
        vs = handeln.vorschlaege(self._bericht(80.0), self._wachen())
        v = vs[0]
        self.assertAlmostEqual(v["ziel"] - v["einstieg"],
                               2 * (v["einstieg"] - v["stop"]), places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)