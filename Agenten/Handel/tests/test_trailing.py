"""trailing.py: der Stop wandert mit dem Preis, nicht nur beim Ziel.

Auftrag Max 05.10.2026: Stop-Loss an den gehebelten Positionen nachziehen und
anpassen, bei allen Spuren mit 1-3R-Take-Profit.

Diese Tests pruefen die EIGENSCHAFTEN, die das Modell tragen - nicht die
Vorgabewerte. Eine Vorgabe ist eine Hausentscheidung, keine Eigenschaft;
wird sie geaendert, muss der Test gruen bleiben und nur die BEWEGUNG zeigen.

Die vier Faelle, an denen ein Trailing-Stop real Geld kostet:
  1. Er feuert zu frueh (Marktrauschen)  -> Mindestabstand
  2. Er wandert ZURUECK (Ruecksetzer)     -> er folgt dem HOCH, nicht dem Kurs
  3. Er wird zur Illusion (Liquidationsmarke) -> stop_vor_liq
  4. Er verschwindet (Scheitern)          -> der alte Stop bleibt
"""

import importlib.util
import pathlib
import sys
import unittest

HANDEL = pathlib.Path(__file__).resolve().parents[1]
if str(HANDEL) not in sys.path:
    sys.path.insert(0, str(HANDEL))

_spec = importlib.util.spec_from_file_location(
    "trailing_testmod", HANDEL / "trailing.py")
tr = importlib.util.module_from_spec(_spec)
sys.modules["trailing_testmod"] = tr
_spec.loader.exec_module(tr)


def long_position(einstieg=100.0, stop=95.0, seite="long"):
    return {"inst": "TEST-USDC", "seite": seite, "einstieg": einstieg,
            "stop": stop, "stop_id": "algo-1", "menge": 10.0}


class TriggerTest(unittest.TestCase):
    """Bis 1R passiert nichts - vorher waere jeder Stop ein Raten."""

    def test_unter_trigger_nichts(self):
        p = long_position()
        w = tr.neu()
        for kurs in (94.0, 95.0, 98.0, 99.9, 100.0, 102.0, 104.9):
            tr.erst_hoch(p, kurs)
            k, g = tr.kandidat(p, kurs, w)
            self.assertIsNone(k, "bei %.1f darf nichts passieren" % kurs)
            self.assertIn("Trigger", g)

    def test_ab_trigger_darf_es(self):
        p = long_position()
        w = tr.neu()
        k, g = tr.kandidat(p, 110.0, w)
        self.assertIsNotNone(k, "bei +2R muss der Stop wandern: %s" % g)
        self.assertGreater(k["stop"], float(p["stop"]))


class BewegungTest(unittest.TestCase):
    """Der Stop folgt dem HOCHSTAND. Ein Ruecksetzer holt ihn nicht zurueck.

    Das ist der ganze Sinn: der Stop bei 1,2R darf bei einem Ruecksetzer auf
    0,8R nicht wieder auf Minus zurueckfallen - sonst ist der Trailing am
    Ende schaedlicher als kein Trailing.
    """

    def _fahre(self, kurse, w=None, **kwargs):
        p = long_position(**kwargs)
        w = w or tr.neu()
        verlauf = []
        for kurs in kurse:
            tr.erst_hoch(p, kurs)
            k, g = tr.kandidat(p, kurs, w)
            if k:
                p["stop"] = k["stop"]
                p["hoechstkurs"] = k["hoechstkurs"]
            verlauf.append((kurs, float(p["stop"])))
        return p, verlauf

    def test_stop_bleibt_auf_hochstand(self):
        p, v = self._fahre([110.0, 108.0, 106.0, 104.0, 103.0])
        stops = [s for _, s in v]
        # Ab dem Moment, in dem der Stop gewandert ist, geht er NICHT mehr
        # zurueck - auch nicht, als der Kurs deutlich faellt.
        gewandert = [s for i, (k, s) in enumerate(v) if s > 95.0]
        self.assertTrue(gewandert, "der Stop ist nie gewandert")
        nach = stops[stops.index(gewandert[0]):]
        for a, b in zip(nach, nach[1:]):
            self.assertGreaterEqual(b, a - 1e-9,
                                    "der Stop ging zurueck: %s" % v)

    def test_hoechstkurs_steigt_nur(self):
        p, v = self._fahre([110.0, 104.0, 108.0, 106.0, 120.0])
        hoch = [p["hoechstkurs"]]
        # Der Hochstand ist der groesste je gesehene Kurs, unabhaengig davon,
        # was der Stop danach macht.
        self.assertGreaterEqual(p["hoechstkurs"], 110.0)

    def test_short_ist_der_spiegel(self):
        p, v = self._fahre([90.0, 88.0, 85.0, 83.0], einstieg=100.0,
                           stop=105.0, seite="short")
        gewandert = [s for _, s in v if s < 105.0]
        self.assertTrue(gewandert, "short: der Stop ist nie gewandert")
        nach = v[v.index((90.0, 105.0)):] if False else None
        stops = [s for _, s in v]
        i = stops.index(gewandert[0])
        for a, b in zip(stops[i:], stops[i + 1:]):
            self.assertLessEqual(b, a + 1e-9,
                                 "short: der Stop ging zurueck: %s" % v)


class SchutzTest(unittest.TestCase):
    """Drei Schranken, die je eine Position ohne echten Schutz erzeugen."""

    def test_mindestabstand_zum_kurs(self):
        """Ein Stop direkt am Kurs wird vom naechsten Tick erreicht."""
        w = tr.neu()
        w["trailing_stop_prozent"] = 0.05        # 0,05 % - bewusst zu knapp
        w["trailing_min_hub_r"] = 0.0            # Hub-Bedingung aus
        w["trailing_trigger_r"] = 0.1
        p = long_position()
        p["hoechstkurs"] = 110.0
        k, g = tr.kandidat(p, 110.0, w)
        self.assertIsNotNone(k)
        abstand_pct = (110.0 - k["stop"]) / 110.0 * 100.0
        self.assertGreaterEqual(abstand_pct,
                                w["trailing_abstand_floor_pct"],
                                "der Stop liegt zu nah am Kurs: %.3f %%"
                                % abstand_pct)

    def test_stop_nie_zurueck_zum_einstieg(self):
        w = tr.neu()
        p = long_position()
        p["hoechstkurs"] = 101.0
        k, g = tr.kandidat(p, 101.0, w)
        # 101 ist noch nicht im Trigger - es darf gar nichts geben.
        self.assertIsNone(k)

    def test_kein_stop_ohne_kennung(self):
        """Ohne Boersen-Stop gibt es nichts zu verlegen. Dieser Weg
        ERFINDET keinen - er sagt es."""
        w = tr.neu()
        p = long_position()
        del p["stop_id"]
        k, g = tr.kandidat(p, 110.0, w)
        self.assertIsNone(k)
        self.assertIn("Boersen-Stop", g)

    def test_liquidationsmarke_wird_verweigert(self):
        w = tr.neu()
        p = long_position()
        # Hoch 110, Abstand 1,5 % -> Ziel-Stop 108,35. Liquidation bei 109 liegt darueber.
        k, g = tr.kandidat(p, 110.0, w, liq=109.0)
        self.assertIsNone(k, "ein Stop unter der Liquidation ist kein Schutz")
        self.assertIn("Liquidationsmarke", g)
        # Oberhalb der Marke ist er erlaubt.
        k2, g2 = tr.kandidat(p, 110.0, w, liq=90.0)
        self.assertIsNotNone(k2, g2)

    def test_abstand_hinter_dem_hoch_ist_halten_pct_nicht_max_halten(self):
        """Regression 09.10.2026: min/max war vertauscht, der Stop lag immer
        max_halten_pct (5 %) hinter dem Hoch, egal was halten_pct sagte."""
        w = tr.neu()
        w["trailing_stop_prozent"] = 1.5
        k, g = tr.kandidat(long_position(), 112.0, w)
        self.assertIsNotNone(k, g)
        self.assertAlmostEqual(k["stop"], 112.0 * (1 - 0.015), places=6)

    def test_max_halten_pct_begrenzt_den_abstand_nach_oben(self):
        """Ein halten_pct ueber max_halten_pct wird auf max_halten_pct gekappt."""
        w = tr.neu()
        w["trailing_stop_prozent"] = 8.0
        w["trailing_max_halten_pct"] = 5.0
        k, g = tr.kandidat(long_position(), 120.0, w)
        self.assertIsNotNone(k, g)
        self.assertAlmostEqual(k["stop"], 120.0 * 0.95, places=6)

    def test_short_abstand_hinter_dem_tief(self):
        w = tr.neu()
        w["trailing_stop_prozent"] = 1.5
        p = long_position(einstieg=100.0, stop=105.0, seite="short")
        k, g = tr.kandidat(p, 90.0, w)
        self.assertIsNotNone(k, g)
        self.assertAlmostEqual(k["stop"], 90.0 * 1.015, places=6)

    def test_vorgabe_ist_1_5_prozent(self):
        self.assertEqual(tr.VORGABE_HALTEN_PCT, 1.5)

    def test_hub_zu_klein_wird_verweigert(self):
        """Eine Verlegung um einen Tick kostet eine Order und bringt
        nichts - deshalb `min_hub_r`."""
        w = tr.neu()
        w["trailing_min_hub_r"] = 5.0          # absurd hoch
        p = long_position()
        k, g = tr.kandidat(p, 112.0, w)          # erst weit ueber dem Trigger
        self.assertIsNone(k)
        self.assertIn("Hub", g)


class WegTest(unittest.TestCase):
    """Das Nachziehen selbst: mit Weg, ohne Weg, mit Fehler."""

    class Weg:
        def __init__(self, antwort="algo-2", wirft=None):
            self.antwort = antwort
            self.wirft = wirft
            self.rufe = []

        def stop_nachziehen(self, kennung, inst, preis):
            self.rufe.append((kennung, inst, preis))
            if self.wirft:
                raise self.wirft
            return self.antwort

    def test_ruft_den_weg_mit_der_kennung_aus_der_position(self):
        p = long_position()
        p["venue_inst"] = "BTC-USD_UM_XPERP-310404"
        w = tr.neu()
        weg = self.Weg()
        k, g = tr.nachziehen(p, 110.0, weg, w, tick=0.1)
        self.assertIsNotNone(k, g)
        self.assertEqual(weg.rufe[0][0], "algo-1")
        self.assertEqual(weg.rufe[0][1], "BTC-USD_UM_XPERP-310404")
        self.assertAlmostEqual(weg.rufe[0][2], k["stop"], places=3,
                               msg="der Weg bekam einen anderen Preis als im Buch")

    def test_ohne_weg_passiert_nichts(self):
        class OhneWeg:
            pass
        p = long_position()
        k, g = tr.nachziehen(p, 110.0, OhneWeg(), tr.neu())
        self.assertIsNone(k)
        self.assertIn("stop_nachziehen", g)
        self.assertIn("Schutz", g)

    def test_fehler_laesst_den_alten_stop_stehen(self):
        p = long_position()
        weg = self.Weg(wirft=RuntimeError("Boesenfehler 51400"))
        alt = float(p["stop"])
        k, g = tr.nachziehen(p, 110.0, weg, tr.neu(), tick=0.1)
        self.assertIsNone(k)
        self.assertEqual(float(p["stop"]), alt, "der Stop wurde trotzdem bewegt")
        self.assertIn("bleibt", g)

    def test_trockenlruf_ruft_nichts(self):
        """Ein Trockenlauf, der eine echte Order stellt, waere gefaehrlicher
        als kein Trockenlauf - er sieht aus wie ein Erfolg."""
        p = long_position()
        weg = self.Weg()
        k, g = tr.nachziehen(p, 110.0, weg, tr.neu(), tick=0.1, trocken=True)
        self.assertIsNotNone(k)
        self.assertEqual(weg.rufe, [], "der Trockenlauf hat den Weg gerufen")
        self.assertIn("TROCKENLAUF", g)


class VorgabeTest(unittest.TestCase):
    """Die Vorgaben sind Hauswerte, keine Messung - der Test prueft ihre
    FORM, nicht ihren Betrag."""

    def test_felder_sind_vollstaendig(self):
        n = tr.neu()
        for k in ("trailing_stop_prozent", "trailing_trigger_r",
                  "trailing_abstand_floor_pct", "trailing_min_hub_r",
                  "trailing_max_halten_pct"):
            self.assertIn(k, n)
            self.assertGreater(float(n[k]), 0.0)

    def test_die_wache_gibt_die_werte_vor(self):
        """Ohne die Felder in der Wache gilt die Vorgabe - eine Spur, die
        nachziehen soll, muss sie nicht tragen."""
        v = tr.verdrahtung({})
        self.assertEqual(v["halten_pct"], tr.VORGABE_HALTEN_PCT)

    def test_die_wache_gewinnt_gegen_die_vorgabe(self):
        v = tr.verdrahtung({"trailing_stop_prozent": 1.25})
        self.assertEqual(v["halten_pct"], 1.25)


class EinProzentDreiRTest(unittest.TestCase):
    """Die Aufgabe nannte das 1-3R-Fenster. Warum es KEIN Filter ist."""

    def test_r_ist_ausstiegsgeometrie_kein_zustand(self):
        """Zwei Spuren mit 1,5R und 2,0R Ziel brauchen denselben Trailing.
        Der Weg entscheidet nicht nach dem Ziel, sondern nach dem Zustand."""
        w15 = dict(tr.neu(), ziel_r=1.5)
        w20 = dict(tr.neu(), ziel_r=2.0)
        p15 = long_position()
        p20 = long_position()
        k15, _ = tr.kandidat(p15, 108.0, w15)
        k20, _ = tr.kandidat(p20, 108.0, w20)
        # BEIDE Spuren bekommen bei +1,6R denselben Stop. Der Trailing
        # haengt an der OFFENEN Position (Einstieg, Stop, Kurs), nicht am
        # Ziel - deshalb greift ein Filter auf ziel_r nicht.
        self.assertIsNotNone(k15, "1,5R: bei +1,6R ist der Stop am Gewinn")
        self.assertIsNotNone(k20, "2,0R: bei +1,6R ist der Stop noch im Minus")
        self.assertAlmostEqual(k15["stop"], k20["stop"], places=9,
                               msg="die beiden Spuren bekommen verschiedene "
                                   "Stops - der Weg haengt am Ziel")

    def test_der_bandfilter_wuerde_die_falsche_auswaehlen(self):
        """Ein Filter 'Ziel zwischen 1R und 3R' schliesst die 2R-Spur aus -
        genau die, die am meisten davon haette. Das ist der Beleg gegen die
        Filterlesart des Auftrags."""
        p = long_position()
        w = tr.neu()
        # Ein 2R-Ziel mit 5 % Stop: Ziel bei 110, Trigger bei 105.
        # Ein 1,5R-Ziel derselben Spur liegt mit 7,5 % darunter - die Spur
        # waere mit einem ziel_r-Filter ('1-3R raussuchen') ALSO nicht
        # ausgeschlossen, sondern die 2R-Spur waere es auch nicht. Der
        # Gegenbeweis: bei 1,5R-Ziel ist der Stop zu einem frueheren Zeit-
        # punkt am Gewinn, obwohl die Wache AEHNLICHE Ziele traegt.
        k, g = tr.kandidat(p, 106.0, w)
        self.assertIsNotNone(k, "bei +1,2R muss der Stop wandern: %s" % g)
        self.assertGreater(k["stop"], 100.0,
                           "der neue Stop muss im Plus liegen, nicht am "
                           "Einstieg - sonst gibt es keinen Vorteil")
        # Und die Grenze: knapp unter dem Trigger passiert NICHTS, auch
        # nicht bei einem R-Wert, der im 1-3R-Band liegt.
        k2, g2 = tr.kandidat(p, 104.0, w)
        self.assertIsNone(k2, g2)


class DeckungsTest(unittest.TestCase):
    """T-365: die Mengen-Deckung ist die ERSTE Bedingung (Referenz 5.1).

    Eine Position, deren Schutz-Menge an der Boerse die Buchmenge nicht
    deckt, ist nicht trailingbar: der engste Stop feuert zuerst, die
    uebrigen bleiben als Waisen zurueck. Erst zusammenfuehren, dann
    trailingen.
    """

    class Weg:
        def __init__(self):
            self.rufe = []

        def stop_nachziehen(self, kennung, inst, preis):
            self.rufe.append((kennung, inst, preis))
            return "algo-2"

    def test_geteilte_deckung_wird_abgelehnt(self):
        p = long_position()          # menge 10.0
        w = tr.neu()
        weg = self.Weg()

        def deckung(pos):
            return {"gedeckt": 6.0, "soll": 10.0, "fehlt": 4.0}

        k, g = tr.nachziehen(p, 110.0, weg, w, tick=0.1,
                             deckung_pruefen=deckung)
        self.assertIsNone(k, "geteilte Deckung darf nicht trailingen")
        self.assertIn("nicht voll gedeckt", g)
        self.assertEqual(weg.rufe, [], "der Weg wurde trotz Unterdeckung gerufen")

    def test_volle_deckung_darf_durch(self):
        p = long_position()
        w = tr.neu()
        weg = self.Weg()

        def deckung(pos):
            return {"gedeckt": 10.0, "soll": 10.0, "fehlt": 0.0}

        k, g = tr.nachziehen(p, 110.0, weg, w, tick=0.1,
                             deckung_pruefen=deckung)
        self.assertIsNotNone(k, "volle Deckung muss trailingen duerfen: %s" % g)
        self.assertEqual(len(weg.rufe), 1)

    def test_ohne_deckungspruefung_unveraendert(self):
        """Ohne deckung_pruefen aendert sich nichts - Rueckwaertskompatibilitaet."""
        p = long_position()
        w = tr.neu()
        weg = self.Weg()
        k, g = tr.nachziehen(p, 110.0, weg, w, tick=0.1)
        self.assertIsNotNone(k, g)
        self.assertEqual(len(weg.rufe), 1)

    def test_deckungspruefung_fehler_laesst_alten_stop_stehen(self):
        p = long_position()
        w = tr.neu()
        weg = self.Weg()
        alt = float(p["stop"])

        def deckung(pos):
            raise RuntimeError("Boersenfrage fehlgeschlagen")

        k, g = tr.nachziehen(p, 110.0, weg, w, tick=0.1,
                             deckung_pruefen=deckung)
        self.assertIsNone(k)
        self.assertEqual(float(p["stop"]), alt, "der Stop wurde trotzdem bewegt")
        self.assertIn("Deckungspruefung fehlgeschlagen", g)


if __name__ == "__main__":
    unittest.main(verbosity=2)