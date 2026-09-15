"""Drawdown-Ratsche: der Ausloeser muss ein Betrag sein, keine Quote.

Die Ratsche halbiert neue Positionen, wenn die realisierte Gewinnkurve vom
Hoechststand zurueckfaellt. Ihr Ausloeser war ein Prozentsatz von
max_gesamt_usd - zwei unabhaengige Groessen. Am 15.09.2026 hob die Erhoehung
des Deckels von 400 auf 1000 die Schwelle von 60 auf 150 USD, waehrend der
hoechste je erreichte Gewinnstand 140.24 USD war: die Ratsche konnte nie mehr
ausloesen. Kein Test fiel, weil groessenfaktor() gar nicht geprueft war.

Diese Suite haelt drei Dinge fest:
  1. der absolute Wert hat Vorrang vor dem Prozentsatz,
  2. ohne absoluten Wert gilt der Prozentsatz weiter (andere Spuren),
  3. die Schwelle darf den Hoechststand nicht uebersteigen - sonst ist die
     Ratsche bei diesem Gewinnstand nicht ausloesbar.
"""

import json
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import wachen_pruefung as wp                                    # noqa: E402

WACHEN = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))


class SchwelleTest(unittest.TestCase):
    def test_absoluter_wert_hat_vorrang(self):
        w = {"drawdown_halbierung_usd": 60.0,
             "drawdown_halbierung_prozent": 15.0,
             "max_gesamt_usd": 1000}
        self.assertEqual(wp.halbierungsschwelle(w), 60.0)

    def test_ohne_absoluten_wert_gilt_der_prozentsatz(self):
        """Andere Spuren kennen den neuen Schluessel nicht und duerfen sich
        nicht aendern."""
        w = {"drawdown_halbierung_prozent": 15.0, "max_gesamt_usd": 400}
        self.assertEqual(wp.halbierungsschwelle(w), 60.0)

    def test_prozentsatz_auf_eur_als_rueckfall(self):
        w = {"drawdown_halbierung_prozent": 15.0, "max_gesamt_eur": 200}
        self.assertEqual(wp.halbierungsschwelle(w), 30.0)

    def test_ohne_jede_angabe_greift_die_altlast(self):
        self.assertEqual(wp.halbierungsschwelle({}), 0.0)


class GroessenfaktorTest(unittest.TestCase):
    def test_unter_der_schwelle_bleibt_es_bei_voller_groesse(self):
        w = {"drawdown_halbierung_usd": 60.0}
        self.assertEqual(wp.groessenfaktor(59.99, w), 1.0)

    def test_ab_der_schwelle_wird_halbiert(self):
        w = {"drawdown_halbierung_usd": 60.0}
        self.assertEqual(wp.groessenfaktor(60.0, w), 0.5)
        self.assertEqual(wp.groessenfaktor(90.0, w), 0.5)

    def test_schwelle_null_halbiert_nicht_dauerhaft(self):
        """Ohne Rahmen (0) darf der Faktor nicht auf 0.5 einrasten."""
        self.assertEqual(wp.groessenfaktor(10.0, {"drawdown_halbierung_usd": 0}), 1.0)


class EchteWachenTest(unittest.TestCase):
    """Die Werte, mit denen die Spur wirklich laeuft."""

    def test_beide_wege_ergeben_denselben_betrag(self):
        """Sonst verschiebt sich die Schwelle lautlos, sobald jemand den
        absoluten Wert entfernt."""
        w = dict(WACHEN)
        absolut = wp.halbierungsschwelle({"drawdown_halbierung_usd": w["drawdown_halbierung_usd"]})
        prozent = wp.halbierungsschwelle(
            {k: v for k, v in w.items() if k != "drawdown_halbierung_usd"})
        self.assertEqual(absolut, prozent)

    def test_echte_wachen_haben_den_absoluten_wert(self):
        """Ohne diesen Schluessel greift wieder die Quote vom Kapitaldeckel -
        und die verschiebt sich bei jeder Aenderung von max_gesamt_usd."""
        self.assertIn("drawdown_halbierung_usd", WACHEN)
        self.assertEqual(wp.halbierungsschwelle(WACHEN),
                         float(WACHEN["drawdown_halbierung_usd"]))

    def test_schwelle_ist_erreichbar(self):
        """Der Test, der die tote Ratsche gefunden haette: eine Schwelle ueber
        dem Hoechststand ist bei diesem Gewinnstand nicht ausloesbar."""
        journal = HIER.parent / "handelsjournal.csv"
        runden = wp.runden_aus_journal(str(journal))
        hoch, _ = wp.drawdown(runden)
        if hoch == 0:
            self.skipTest("noch keine realisierten Runden")
        grenze = wp.halbierungsschwelle(WACHEN)
        self.assertLessEqual(
            grenze, hoch,
            "Schwelle %.2f USD liegt ueber dem Hoechststand %.2f USD - "
            "die Ratsche kann nie ausloesen" % (grenze, hoch))


class ErreichbarkeitTest(unittest.TestCase):
    """Die Erreichbarkeit haengt NUR am Hoechststand, nicht am aktuellen
    Ruecklauf. Sonst meldet die Anzeige 'NICHT AUSLOESBAR', waehrend der
    Faktor daneben schon 0.50 zeigt."""

    def _journal(self, tmp, zeilen):
        p = Path(tmp) / "j.csv"
        p.write_text("zeit,modus,aktion,inst,usd\n" + "\n".join(zeilen) + "\n",
                     encoding="utf-8", newline="")
        return str(p)

    def _lage(self, tmp, schwelle, zeilen):
        w = {"drawdown_halbierung_usd": schwelle, "max_gesamt_usd": 1000}
        return wp.lage(w, self._journal(tmp, zeilen), {})

    def test_schwelle_ueber_dem_hoechststand_ist_nicht_erreichbar(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            s = self._lage(tmp, 150.0, [
                "2026-09-01T00:00:00+00:00,papier,kauf,A,100",
                "2026-09-02T00:00:00+00:00,papier,verkauf,A,140",
                "2026-09-03T00:00:00+00:00,papier,kauf,B,100",
                "2026-09-04T00:00:00+00:00,papier,verkauf,B,60",
            ])
            self.assertEqual(s["hoechststand_usd"], 40.0)
            self.assertEqual(s["ruecklauf_usd"], 40.0)
            self.assertFalse(s["halbierung_erreichbar"])

    def test_schwelle_unter_dem_hoechststand_ist_erreichbar(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            s = self._lage(tmp, 30.0, [
                "2026-09-01T00:00:00+00:00,papier,kauf,A,100",
                "2026-09-02T00:00:00+00:00,papier,verkauf,A,140",
                "2026-09-03T00:00:00+00:00,papier,kauf,B,100",
                "2026-09-04T00:00:00+00:00,papier,verkauf,B,60",
            ])
            # schon ausgeloest: Faktor halbiert UND trotzdem erreichbar -
            # die beiden Aussagen duerfen sich nicht widersprechen.
            self.assertEqual(s["groessenfaktor"], 0.5)
            self.assertTrue(s["halbierung_erreichbar"])

    def test_ohne_runden_kein_falscher_alarm(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            s = self._lage(tmp, 60.0, [])
            self.assertEqual(s["hoechststand_usd"], 0.0)
            self.assertTrue(s["halbierung_erreichbar"],
                            "eine frische Spur darf nicht als tote Ratsche gelten")


if __name__ == "__main__":
    unittest.main()
