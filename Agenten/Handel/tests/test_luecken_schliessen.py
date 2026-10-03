"""Die zwei offenen Lücken vom 03.10.2026 schliessen.

1. `prophet_signal` hatte NULL Testdateien - eine Spur, die laeuft, spiegelt
   und am Bus haengt, deren Rechnung aber niemand prueft.
2. Die Skalierungsregel war nur in der Mitte getestet (`skalieren.py`), nicht
   in der VERDRAHTUNG. Und genau dort ist es am 03.10. gescheitert: drei
   Spuren brachen mit `NameError: seite` ab, weil die Seite dort `sig` hiess.
   Eine Regel, deren Einfuegestelle ungetestet ist, ist beim naechsten Umbau
   wieder eine stille Baustelle.

Die Vertraege sind GEMESSEN, nicht angenommen (03.10.2026):
  * `prophet_regeln.trend_richtung` liefert 1 / -1, NICHT "long"/"short".
  * macd_mtf, squeeze, wavetrend erwarten von `signal(k, idx)` einen
    truthy STRING; supertrend ein Tupel `(seite, linie)` - es entpackt es.
  * `mindest_kerzen` unterscheidet sich stark (macd_mtf 600, die anderen 300),
    also kommt die Zahl aus der Wachen und nicht aus dem Test.

Gegenprobe zu (2): nimmt man die Verdrahtung aus einer Spur heraus, muss
`SkalierverdrahtungTest` rot werden.
"""
import json
import os
import sys
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

SPUREN = ("supertrend", "macd_mtf", "squeeze", "wavetrend")


def kerzen(n=700, start=100.0, schritt=0.35):
    """OKX-Format [ts, o, h, l, c, v] mit gleichmaessiger Bewegung."""
    return [[1_700_000_000_000 + i * 900_000,
             start + i * schritt,
             (start + i * schritt) * 1.002,
             (start + i * schritt) * 0.998,
             start + i * schritt,
             10.0 + i]
            for i in range(n)]


def lade(spur):
    import importlib.util
    ordner = os.path.join(HANDEL, spur)
    sys.path.insert(0, ordner)
    try:
        spec = importlib.util.spec_from_file_location(
            "_t_%s_handeln" % spur, os.path.join(ordner, "handeln.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(ordner)


def wachen_von(spur, **extra):
    with open(os.path.join(HANDEL, spur, "wachen.json"), encoding="utf-8") as fh:
        w = json.load(fh)
    w["max_offene_positionen"] = 4
    w.update(extra)
    return w


# --------------------------------------------------------------- Prophet
class ProphetSignalTest(unittest.TestCase):
    """prophet_regeln.py - reine Funktionen, kein Netz, kein Buch."""

    def setUp(self):
        import prophet_regeln
        self.pr = prophet_regeln
        with open(os.path.join(HANDEL, "prophet_signal", "wachen.json"),
                  encoding="utf-8") as fh:
            self.w = json.load(fh)

    def test_sma_rechnet_den_mittelwert(self):
        # GEMESSEN: sma/ema liefern eine REIHE (mit None am Anfang), keine
        # Zahl. Wer die Funktion auf eine Zahl prueft, prueft eine Annahme.
        reihe = self.pr.sma([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        self.assertEqual(len(reihe), 5)
        self.assertIsNone(reihe[0])
        self.assertAlmostEqual(reihe[2], 2.0, places=6)
        self.assertAlmostEqual(reihe[4], 4.0, places=6)

    def test_ema_und_sma_stimmen_bei_konstanter_reihe_ueberein(self):
        # Auf einer linearen Reihe laeuft die EMA in die SMA (beides 6.0) -
        # das war eine falsche Praemisse. Eine EIGENTLICHE Eigenschaft:
        # bei konstanter Reihe muessen beide genau den Wert liefern, und die
        # EMA muss ihr langsamer folgen als die SMA.
        konstant = [5.0] * 12
        self.assertAlmostEqual(self.pr.ema(konstant, 4)[-1], 5.0, places=6)
        self.assertAlmostEqual(self.pr.sma(konstant, 4)[-1], 5.0, places=6)

        sprung = [1.0] * 10 + [20.0] * 5
        letzte_ema = self.pr.ema(sprung, 4)[-1]
        letzte_sma = self.pr.sma(sprung, 4)[-1]
        # die SMA ist der reine Mittelwert des Fensters, die EMA gewichtet
        # das Neue hoeher - bei einem Sprung liegt sie darunter
        self.assertLess(letzte_ema, letzte_sma)

    def test_trend_richtung_liefert_eine_richtung_nicht_einen_text(self):
        """Gemessen: die Funktion liefert 1 / -1. Wer im Test 'long'
        erwartet, prueft eine Annahme."""
        hoch = self.pr.trend_richtung(kerzen(200), trend_n=10, min_kerzen=30)
        runter = self.pr.trend_richtung(kerzen(200, schritt=-0.35),
                                        trend_n=10, min_kerzen=30)
        self.assertEqual(hoch, 1)
        self.assertEqual(runter, -1)

    def test_zu_wenige_kerzen_ergeben_keine_richtung(self):
        self.assertIsNone(self.pr.trend_richtung(kerzen(20), trend_n=30,
                                                 min_kerzen=60))

    def test_saisonalitaet_ist_eine_zahl_in_einem_sinnvollen_rahmen(self):
        wert = self.pr.saisonalitaet_staerke(kerzen(300), trend_n=20,
                                             min_kerzen=60)
        self.assertIsInstance(float(wert), float)
        self.assertGreaterEqual(float(wert), 0.0)

    def test_saison_schwelle_aus_der_wachen_wird_beachtet(self):
        """Unter der Schwelle darf die Regel keinen Einstieg vorschlagen.

        Der Test misst die Saisonalitaet selbst und vergleicht mit der Schwelle
        aus der Wachen - er behauptet nicht, dass eine bestimmte Kerzenzahl
        ueber oder unter der Schwelle liegt.
        """
        k = kerzen(300)
        w = dict(self.w)
        stark = self.pr.saisonalitaet_staerke(k, int(w.get("trend_n") or 30),
                                             int(w.get("mindest_kerzen") or 60))
        schwelle = float(w.get("saison_min") or 0.2)
        if stark is not None and float(stark) < schwelle:
            self.assertIsNone(self.pr.einstieg(k, w),
                              "unter der Schwellle darf kein Einstieg kommen")
        elif stark is not None:
            self.assertIn(self.pr.einstieg(k, w), ("long", "short"))


# ------------------------------------------------------ Skalierverdrahtung
class SkalierverdrahtungTest(unittest.TestCase):

    def lauf(self, spur, anzahl_signale=2):
        mod = lade(spur)
        w = wachen_von(spur)
        k = kerzen(max(400, int(w.get("mindest_kerzen") or 300) + 100))
        z = {"positionen": []}

        # DER TEST SCHREIBT NICHT. `pruefe_einstieg` journalisiert in das ECHTE
        # Journal der Spur - so hat dieser Test am 03.10.2026 192 Zeilen in vier
        # echte Buecher geschrieben (supertrend 57, macd_mtf 45, wavetrend 45,
        # squeeze 45), alle am synthetischen Kurs erkennbar. Der Sammel-Modus
        # ist hier Pflicht, nicht Kosmetik; `test_der_test_schreibt_nicht`
        # belegt es.
        geschrieben = []
        mod.journal = lambda **kw: geschrieben.append(kw)

        # supertrend entpackt das Ergebnis (`seite, _linie = sig`), die
        # anderen drei vergleichen es als Text. Gemessen, nicht geraten.
        stub = (lambda *a, **kw: ("long", 0.0)) if spur == "supertrend" \
            else (lambda *a, **kw: "long")
        mod.signal = stub
        for _ in range(anzahl_signale):
            mod.pruefe_einstieg("BTC-USDT", k, z, w, 1.0)
        self.geschrieben = geschrieben
        return z

    def test_der_test_schreibt_nicht(self):
        """Gegenprobe auf mich selbst: kein Test darf eine echte Datei
        anfasst. Die vier Buecher bekamen am 03.10. 192 Zeilen, weil dieser
        Test `pruefe_einstieg` mit dem echten Journal aufrief."""
        for spur in SPUREN:
            with self.subTest(spur=spur):
                pfad = os.path.join(HANDEL, spur, "handelsjournal.csv")
                vorher = os.path.getsize(pfad) if os.path.isfile(pfad) else -1
                self.lauf(spur, 2)
                nachher = os.path.getsize(pfad) if os.path.isfile(pfad) else -1
                self.assertEqual(
                    vorher, nachher,
                    "%s: die Groesse des echten Journals hat sich geaendert" % spur)
                # und es wurde tatsaechlich protokolliert - sonst prueft
                # der Test oben gar nichts und waere gruen aus Faulheit
                self.assertTrue(self.geschrieben,
                                "%s: es wurde nichts protokolliert - der "
                                "Test prueft dann nichts" % spur)

    def test_zwei_signale_ergeben_eine_position(self):
        for spur in SPUREN:
            with self.subTest(spur=spur):
                pos = self.lauf(spur, 2)["positionen"]
                self.assertEqual(len(pos), 1,
                                 "%s: zwei Signale muessen EINE Position "
                                 "ergeben, es wurden %d angelegt"
                                 % (spur, len(pos)))

    def test_kein_nameerror_in_der_verdrahtung(self):
        """Genau der Fehler vom 03.10.: die Seite hiess in drei Spuren `sig`."""
        for spur in SPUREN:
            with self.subTest(spur=spur):
                try:
                    self.lauf(spur, 1)
                except NameError as e:                       # noqa: PERF203
                    self.fail("%s: NameError in der Verdrahtung: %s" % (spur, e))

    def test_das_nominal_waechst_statt_zu_stapeln(self):
        for spur in SPUREN:
            with self.subTest(spur=spur):
                eins = self.lauf(spur, 1)["positionen"][0]
                zwei = self.lauf(spur, 2)["positionen"][0]
                self.assertGreater(float(zwei["nominal"]), float(eins["nominal"]),
                                   "%s: das Nominal waechst nicht" % spur)

    def test_das_nominal_waechst_um_genau_den_zweiten_einsatz(self):
        for spur in SPUREN:
            with self.subTest(spur=spur):
                eins = float(self.lauf(spur, 1)["positionen"][0]["nominal"])
                zwei = float(self.lauf(spur, 2)["positionen"][0]["nominal"])
                self.assertAlmostEqual(zwei, eins * 2.0, delta=eins * 0.01,
                                       msg="%s: nicht verdoppelt" % spur)


if __name__ == "__main__":
    unittest.main(verbosity=2)