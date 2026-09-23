"""stops_bereinigen.py: Bestandsaufnahme der offenen Stops, ohne Netz.

Der echte Zustand wird ueber eine Attrappe geprueft: erledigte Stops fallen,
doppelte werden zusammengefasst, Waisen (Stop ohne Position) werden gemeldet,
unlesbare bleiben stehen. Geschrieben wird nur bei --anwenden.
"""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SPUR)
import stops_bereinigen as sb  # noqa: E402

assert sb.__file__.startswith(SPUR), sb.__file__

ZUSTAENDE = {"erledigt": "canceled", "aktiv": "live", "gefuellt": "filled",
             "kaputt": "order_failed"}


class AttrappeOKX:
    def __init__(self, staende, unlesbar=()):
        self.staende = staende
        self.unlesbar = set(unlesbar)
        self.storniert = []

    def stop_details(self, algo_id):
        if algo_id in self.unlesbar:
            raise RuntimeError("kein Netz")
        return {"state": self.staende.get(algo_id, "live"),
                "instId": "ZEC-USDC"}

    def stop_stornieren(self, algo_id, inst=None):
        self.storniert.append((algo_id, inst))
        self.staende[algo_id] = "canceled"
        return algo_id


def zustand(**abweichend):
    z = {"positionen": [{"inst": "ZEC-USDC", "stop_ord_id": "lebt-1"}],
         "offene_stops": []}
    z.update(abweichend)
    return z


class BereinigenTest(unittest.TestCase):
    def test_erledigte_stops_fallen_raus(self):
        z = zustand(offene_stops=[
            {"inst": "ZEC-USDC", "stop_ord_id": "alt-1", "seit": "2026-09-22"}])
        a = AttrappeOKX({"alt-1": "canceled"})
        with patch.object(sb, "okx", a):
            erg = sb.bereinige(z, anwenden=True)
        self.assertEqual(z["offene_stops"], [])
        self.assertEqual(erg["erledigt"], 1)

    def test_dieselbe_kennung_wird_einmal_gezaehlt(self):
        e = {"inst": "ZEC-USDC", "stop_ord_id": "alt-1", "seit": "2026-09-22"}
        z = zustand(offene_stops=[e] * 23)
        a = AttrappeOKX({"alt-1": "canceled"})
        with patch.object(sb, "okx", a):
            erg = sb.bereinige(z, anwenden=True)
        self.assertEqual(erg["doppelt"], 22, "22 Kopien fallen weg")
        self.assertEqual(erg["erledigt"], 1)
        self.assertEqual(z["offene_stops"], [])

    def test_aktiver_stop_einer_position_bleibt(self):
        z = zustand(offene_stops=[
            {"inst": "ZEC-USDC", "stop_ord_id": "lebt-1", "seit": "2026-09-23"}])
        a = AttrappeOKX({"lebt-1": "live"})
        with patch.object(sb, "okx", a):
            sb.bereinige(z, anwenden=True)
        self.assertEqual([e["stop_ord_id"] for e in z["offene_stops"]],
                         ["lebt-1"], "gehoert zur offenen Position")

    def test_aktiver_stop_ohne_position_ist_eine_waise(self):
        z = zustand(offene_stops=[
            {"inst": "SOL-USDC", "stop_ord_id": "waise-1", "seit": "2026-09-22"}])
        a = AttrappeOKX({"waise-1": "live"})
        with patch.object(sb, "okx", a):
            erg = sb.bereinige(z, anwenden=False)
        self.assertEqual([w[0] for w in erg["waisen"]], ["waise-1"])
        self.assertEqual(a.storniert, [], "Vorschau storniert nichts")
        self.assertEqual(len(z["offene_stops"]), 1)

    def test_waise_wird_nur_mit_stornieren_abgestellt(self):
        z = zustand(offene_stops=[
            {"inst": "SOL-USDC", "stop_ord_id": "waise-1", "seit": "2026-09-22"}])
        a = AttrappeOKX({"waise-1": "live"})
        with patch.object(sb, "okx", a):
            sb.bereinige(z, stornieren=True, anwenden=True)
        self.assertEqual(a.storniert, [("waise-1", "SOL-USDC")])
        self.assertEqual(z["offene_stops"], [])

    def test_unlesbarer_stop_bleibt_stehen(self):
        z = zustand(offene_stops=[
            {"inst": "SOL-USDC", "stop_ord_id": "blind-1", "seit": "2026-09-22"}])
        a = AttrappeOKX({}, unlesbar=("blind-1",))
        with patch.object(sb, "okx", a):
            sb.bereinige(z, anwenden=True)
        self.assertEqual(len(z["offene_stops"]), 1,
                         "lieber behalten als eine echte Order vergessen")

    def test_fehlendes_inst_wird_aus_der_boerse_ergaenzt(self):
        z = zustand(offene_stops=[{"stop_ord_id": "alt-1", "seit": "2026-09-22"}])
        a = AttrappeOKX({"alt-1": "canceled"})
        with patch.object(sb, "okx", a):
            sb.bereinige(z, anwenden=True)
        self.assertEqual(z["offene_stops"], [], "erledigt - nichts mehr zu merken")


class DateiTest(unittest.TestCase):
    """Der Schreibweg: nur bei --anwenden, und nicht in einen laufenden Zyklus."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = os.path.join(self.tmp.name, "zustand.json")

    def _schreibe(self, z):
        with open(self.pfad, "w", encoding="utf-8") as f:
            json.dump(z, f)

    def test_vorschau_schreibt_nichts(self):
        z = zustand(offene_stops=[
            {"inst": "ZEC-USDC", "stop_ord_id": "alt-1", "seit": "2026-09-22"}])
        self._schreibe(z)
        a = AttrappeOKX({"alt-1": "canceled"})
        with patch.object(sb, "okx", a):
            rc = sb.main(["--pfad", self.pfad])
        self.assertEqual(rc, 0)
        with open(self.pfad, encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)["offene_stops"]), 1,
                             "Vorschau laesst die Datei unveraendert")

    def test_anwenden_schreibt_die_bereinigte_liste(self):
        z = zustand(offene_stops=[
            {"inst": "ZEC-USDC", "stop_ord_id": "alt-1", "seit": "2026-09-22"}])
        self._schreibe(z)
        os.utime(self.pfad, (0, 0))          # alt genug
        a = AttrappeOKX({"alt-1": "canceled"})
        with patch.object(sb, "okx", a):
            rc = sb.main(["--pfad", self.pfad, "--anwenden"])
        self.assertEqual(rc, 0)
        with open(self.pfad, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["offene_stops"], [])

    def test_frische_datei_wird_nicht_angefasst(self):
        # Ein laufender Zyklus wuerde die Aenderung ohnehin ueberschreiben.
        self._schreibe(zustand(offene_stops=[
            {"inst": "ZEC-USDC", "stop_ord_id": "alt-1", "seit": "2026-09-22"}]))
        a = AttrappeOKX({"alt-1": "canceled"})
        with patch.object(sb, "okx", a):
            rc = sb.main(["--pfad", self.pfad, "--anwenden"])
        self.assertEqual(rc, 2, "zu frisch - spaeter erneut versuchen")


if __name__ == "__main__":
    unittest.main()