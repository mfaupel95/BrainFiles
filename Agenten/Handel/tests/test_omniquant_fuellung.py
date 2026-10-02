"""HBAR-Liveposition: Fuellung und Ausstieg (T-306, 01.10.2026).

Zwo Fehler, die am 01.10.2026 zusammen eine echte Sicherheitsluecke erzeugten:

1. `kraken_futures.gefuellte_menge` las `/fills` sofort nach dem Kauf. Die
   Boerse hatte noch nicht gefuellt -> Teilwert oder 0. Der Aufrufer rechnete
   `int(0.4)` = 0 und bestellte Stop UND Rueckdrehung mit `size: 0`. Kraken
   antwortete `invalidArgument: 0`. Die Rueckdrehung blieb wirkungslos, wurde
   aber als Erfolg protokolliert -> 5706 Kontrakte ohne Schutz an der Boerse.

2. Das Einstiegs-Gate `live_pf_ableitung` wurde auch beim AUSSTIEG geprueft.
   Eine bereits offene Live-Position konnte sich nicht schliessen und stand
   ueber zwei Stunden da, waehrend jede Rueckrechnung am selben Gate scheiterte.

Beide Tests pruefen die REGEL, nicht den Wert. Kein Netz, keine Order:
`_roh` ist eine Attrappe, die antwortet, was der Test braucht.

Ausfuehrbar:  python tests/test_omniquant_fuellung.py   (aus Agenten/Handel)
"""
import sys
import time
import types
import unittest
from pathlib import Path

HANDEL = Path(__file__).resolve().parent.parent
OMNI = HANDEL / "omniquant"
NAUT = HANDEL / "nautilus_kraken"
for p in (str(OMNI), str(NAUT), str(HANDEL)):
    if p not in sys.path:
        sys.path.insert(0, p)

import kraken_futures as kf                                        # noqa: E402
import kraken_perp as kp                                          # noqa: E402
import live_perp as lp                                            # noqa: E402


class RohAttrappe:
    """`_roh` mit programmierbarem Antwortverlauf - kein Netz."""

    def __init__(self, verlauf):
        self.verlauf = list(verlauf)
        self.rufe = []

    nach_pfad = {}          # {pfad-prefix: antwort} - je Aufruf dieselbe

    def __call__(self, pfad, daten=None, post=None, **kwargs):
        """**kwargs absichtlich: `_roh` fuehrt je nach Aufruf `signiert=`
        und `post=` mit - die Attrappe nimmt beides an, damit ein Test nicht
        an der Signatur statt an der Regel scheitert."""
        self.rufe.append(pfad)
        for muster, antwort in self.nach_pfad.items():
            if pfad.startswith(muster):
                return antwort
        if not self.verlauf:
            return {}
        wert = self.verlauf.pop(0)
        if isinstance(wert, Exception):
            raise wert
        return wert


class FuellungTest(unittest.TestCase):
    """`gefuellte_menge` unterscheidet 0 von 'nicht bestaetigt' und rundet
    nie auf 0 - ein Kontrakt ist die kleinste handelbare Einheit."""

    def setUp(self):
        self.echt_roh = kf._roh
        self.echt_sleep = kf.time.sleep

    def tearDown(self):
        kf._roh = self.echt_roh
        kf.time.sleep = self.echt_sleep

    @staticmethod
    def _fills(*groessen):
        return {"fills": [{"order_id": "O1", "size": g} for g in groessen]}

    def test_teilfuellung_rundet_auf_keine_null(self):
        """Der Ausloeser: `int(0.4)` == 0 wurde als Kontraktzahl bestellt."""
        kf._roh = RohAttrappe([self._fills(0.4)])
        kf.time.sleep = lambda s: None
        menge, bestaetigt = kf.gefuellte_menge("O1", sekunden=0)
        self.assertTrue(bestaetigt, "eine Fuellung ist vorhanden")
        self.assertGreaterEqual(menge, 1,
                                "ein Kontrakt ist die kleinste handelbare "
                                "Einheit - 0 ergibt `size: 0` an der Boerse")
        self.assertIsInstance(menge, int)

    def test_kleine_teilfuellung_wird_zusammengefasst(self):
        """Drei Fuellungen desselben Kaufs sind EINE Position."""
        kf._roh = RohAttrappe([self._fills(0.3, 0.3, 0.4)])
        kf.time.sleep = lambda s: None
        menge, bestaetigt = kf.gefuellte_menge("O1", sekunden=0)
        self.assertTrue(bestaetigt)
        self.assertEqual(menge, 1)

    def test_nicht_gefuellt_liefert_null_und_bestaetigt_falsch(self):
        """Ohne Fill: (0, False) - NICHT (0, True). Sonst bucht der Aufrufer
        eine Position mit Groesse 0 und meldet Erfolg."""
        kf._roh = RohAttrappe([{"fills": []}])
        kf.time.sleep = lambda s: None
        menge, bestaetigt = kf.gefuellte_menge("O1", sekunden=0)
        self.assertEqual(menge, 0)
        self.assertFalse(bestaetigt,
                         "0 ist hier 'nicht bestaetigt', nicht '0 Kontrakte "
                         "ausgefuehrt'")

    def test_es_wartet_bis_die_boerse_antwortet(self):
        """Der Fill erscheint erst beim zweiten Abruf - dann MUSS gewartet
        werden, statt mit 0 weiterzumachen."""
        kf._roh = RohAttrappe([{"fills": []}, self._fills(2935)])
        kf.time.sleep = lambda s: None
        menge, bestaetigt = kf.gefuellte_menge("O1", sekunden=5)
        self.assertTrue(bestaetigt)
        self.assertEqual(menge, 2935)

    def test_abfragefehler_ist_kein_nullbefund(self):
        """Eine nicht lesbare Boerse ist KEIN '0 ausgefuehrt'."""
        kf._roh = RohAttrappe([kf.KrakenFuturesFehler("nope")])
        kf.time.sleep = lambda s: None
        menge, bestaetigt = kf.gefuellte_menge("O1", sekunden=0)
        self.assertEqual(menge, 0)
        self.assertFalse(bestaetigt)

    def test_gegenprobe_ohne_fix_wuerde_null_liefern(self):
        """Der Fehler von gestern in seiner alten Form: `int()` statt
        `max(1, int(round()))`. Beide rechnen 0.4 - aber nur die alte Form
        liefert 0, und genau diese 0 ging als `size` an die Boerse.
        Der Test ist damit kein Schutz, sondern die Fehlerbeschreibung."""
        alt_menge = sum(float(f.get("size") or 0.0)
                        for f in self._fills(0.4)["fills"]
                        if f.get("order_id") == "O1")
        self.assertEqual(int(alt_menge), 0,
                         "genau daraus entstand `size: 0` an der Boerse")
        self.assertEqual(max(1, int(round(alt_menge))), 1,
                         "die neue Form liefert mindestens einen Kontrakt")


class AusstiegGateTest(unittest.TestCase):
    """`live_pf_ableitung` ist ein EINSTIEGS-Gate. Eine offene Position muss
    sich auch dann schliessen koennen, wenn es false ist."""

    HBAR = "HBAR-USDT"

    def setUp(self):
        kp.setze_ableitung(False)
        kp.merke_maerkte({"PF_HBARUSD"})
        # kp._kf() laedt kraken_futures bei JEDEM Aufruf neu - die Naht fuer
        # Tests ist deshalb _kf selbst, nicht _roh der importierten Instanz.
        self.echt_kf = kp._kf
        kp._kf = lambda: kf
        self.addCleanup(setattr, kp, "_kf", self.echt_kf)
        # Jeder Aufruf bekommt seine Antwort: /tickers fuer den Kurs,
        # /openPositions fuer den Bestand. Die Attrappe antwortet je PFAD.
        self.roh = RohAttrappe([])
        self.roh.nach_pfad = {
            "/openPositions": {
                "openPositions": [{"symbol": "PF_HBARUSD", "side": "long",
                                   "size": 8641, "price": 0.10336}]},
            "/tickers": {"tickers": [{"symbol": "PF_HBARUSD",
                                      "last": 0.10336}]},
        }
        kf._roh = self.roh

    def tearDown(self):
        kp.setze_ableitung(False)

    def test_einstieg_bleibt_gesperrt(self):
        """Das Gate hat genau eine Aufgabe: einen NEUEN Markt nicht zu
        eroeffnen. Das bleibt erhalten."""
        with self.assertRaises(ValueError) as c:
            kp.pf_markt(self.HBAR)
        self.assertIn("live_pf_ableitung=false", str(c.exception))

    def test_ausstieg_findet_den_markt_trotzdem(self):
        for aufruf, was in (
            (lambda: kp.pf_markt(self.HBAR, fuer_ausstieg=True), "pf_markt"),
            (lambda: kp.letzter_kurs(self.HBAR, fuer_ausstieg=True), "Kurs"),
            (lambda: kp.offene_positionen(self.HBAR, fuer_ausstieg=True),
             "Positionen"),
        ):
            with self.subTest(was=was):
                aufruf()   # darf NICHT werfen

    def test_ausstieg_wirft_ausserhalb_des_markts(self):
        """fuer_ausstieg hebt die Freigabe auf, NICHT den Marktbeweis: ein
        Name ohne PF_-Markt bleibt ein lauter Fehler."""
        kp.merke_maerkte({"PF_SOLUSD"})
        with self.assertRaises(ValueError):
            kp.pf_markt(self.HBAR, fuer_ausstieg=True)

    def test_ausstieg_braucht_die_marktliste_trotzdem(self):
        """Kein Markt = kein Beweis, auch beim Ausstieg nicht."""
        kp.merke_maerkte(set())
        with self.assertRaises(ValueError) as c:
            kp.pf_markt(self.HBAR, fuer_ausstieg=True)
        self.assertIn("Marktliste", str(c.exception))

    def test_markt_verkauf_umgeht_das_gate(self):
        """Der Verkauf ist VORGABESEITIG frei - er trifft keine neue
        Marktwahl. Ohne das blieb jede offene Position liegen."""
        gesendet = []
        self.echt_order_aufgeben = kf._order_aufgeben  # noqa: F841
        kf._order_aufgeben = lambda werte: gesendet.append(werte) or {
            "sendStatus": {"status": "placed", "order_id": "R1"}}
        self.addCleanup(setattr, kf, "_order_aufgeben",
                        self.echt_order_aufgeben)
        kp.markt_verkauf(self.HBAR, 2935)
        self.assertEqual(len(gesendet), 1, "der Verkauf ging raus")
        self.assertEqual(gesendet[0]["symbol"], "PF_HBARUSD")
        self.assertEqual(gesendet[0]["size"], 2935)


class RollbackTest(unittest.TestCase):
    """Eine Rueckdrehung gilt erst als gelungen, wenn die BOERSE die Position
    danach nicht mehr fuehrt. Am 01.10.2026 wurde sie mit Groesse 0
    abgeschickt, blieb wirkungslos und wurde als Erfolg protokolliert."""

    def _handeln_stub(self, journal_zeilen):
        h = types.SimpleNamespace()
        h._jetzt = lambda: "2026-10-01T22:00:00+00:00"
        h._heute = lambda: "2026-10-01"
        h.journal = lambda **kw: journal_zeilen.append(kw)
        return h

    def _wachen(self):
        return {"live_einsatz_usd": 50, "hebel": 6, "handel_erlaubt": True,
                "freigabe": {"erfuellt": True},
                "live_max_offene_positionen": 1, "live_max_gesamt_usd": 50,
                "mindest_guthaben_usd": 31, "live_pf_ableitung": True}

    def test_rollback_meldet_bleibende_position_laut(self):
        zeilen = []
        h = self._handeln_stub(zeilen)
        # Der Verkauf "klappt", die Boerse fuehrt aber weiter -> das ist
        # genau der Fall vom 01.10. und MUSS als Luecke gelten.
        kp.markt_verkauf = lambda *a, **k: {"sendStatus": {"order_id": "R9"}}
        kp.offene_positionen = lambda *a, **k: [
            {"symbol": "PF_HBARUSD", "side": "long", "size": 8641}]
        kp.stop_setzen = lambda *a, **k: (_ for _ in ()).throw(
            kf.KrakenFuturesFehler("invalidArgument: 0"))
        kp.guthaben_usd = lambda: 100.0
        kp.einschuss_usd = lambda *a: 5.0
        kp.letzter_kurs = lambda *a, **k: 0.10223
        kp.hebel_grund = lambda *a, **k: None
        kp.kontrakte_fuer = lambda *a, **k: 2935
        kp.nennwert_usd = lambda *a: 300.0
        kp.effektiver_hebel = lambda *a: 6.0
        kp.markt_kauf = lambda *a: {"sendStatus": {"order_id": "O9"}}
        kp.gefuellte_menge = lambda *a, **k: (2935, True)
        lp.zeitfenster_offen = lambda: True

        p = lp.kaufe(h, self._wachen(), {"positionen": []},
                     {"inst": "HBAR-USDT", "stop": 0.09, "ziel": 0.13,
                      "score": 68.0})
        self.assertIsNone(p, "ohne Stop ist es kein Einstieg")
        gruende = " | ".join(str(z.get("grund")) for z in zeilen)
        self.assertIn("SICHERHEITSLÜCKE", gruende,
                      "eine wirkungslose Rueckdrehung muss LAUT sein")

    def test_rollback_mit_wirkung_gilt_als_erfolg(self):
        zeilen = []
        h = self._handeln_stub(zeilen)
        kp.markt_verkauf = lambda *a, **k: {"sendStatus": {"order_id": "R9"}}
        kp.offene_positionen = lambda *a, **k: []      # Boerse ist leer
        kp.stop_setzen = lambda *a, **k: (_ for _ in ()).throw(
            kf.KrakenFuturesFehler("invalidArgument: 0"))
        kp.guthaben_usd = lambda: 100.0
        kp.einschuss_usd = lambda *a: 5.0
        kp.letzter_kurs = lambda *a, **k: 0.10223
        kp.hebel_grund = lambda *a, **k: None
        kp.kontrakte_fuer = lambda *a, **k: 2935
        kp.markt_kauf = lambda *a: {"sendStatus": {"order_id": "O9"}}
        kp.gefuellte_menge = lambda *a, **k: (2935, True)
        lp.zeitfenster_offen = lambda: True

        p = lp.kaufe(h, self._wachen(), {"positionen": []},
                     {"inst": "HBAR-USDT", "stop": 0.09, "ziel": 0.13,
                      "score": 68.0})
        self.assertIsNone(p)
        gruende = " | ".join(str(z.get("grund")) for z in zeilen)
        self.assertNotIn("SICHERHEITSLÜCKE", gruende)
        self.assertIn("zurueckgedreht", gruende)


if __name__ == "__main__":
    unittest.main(verbosity=2)