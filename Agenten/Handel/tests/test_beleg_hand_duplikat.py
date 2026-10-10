"""Test: Duplikats-Gatter in beleg_hand.py (T-102).

Die Regel: ein Beleg fuer ein Instrument, das schon eine offene Position,
einen ANDEREN offenen Beleg oder eine offene Kauf-Order an der Boerse hat,
wird abgelehnt. Das verhindert, dass derselbe Wert mehrfach gekauft wird
(FILEUR-Fehler 28.09.2026: vier Kaeufe ~200 EUR fuer EIN Signal).

Der EIGENE Beleg ist kein Duplikat: `lauf()` iteriert `offene()` und fuehrt
jeden Beleg aus, waehrend er noch in der Liste steht (verbrauche() kommt erst
nach allen Gates). Wer den eigenen Beleg mitzaehlt, lehnt JEDE Ausfuehrung ab.

Lauf: cd Agenten/Handel && python -m unittest tests.test_beleg_hand_duplikat
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import beleg_hand as bh                                                    # noqa: E402


class _FakeBeleg:
    """Attrappe: verbraucht und offene Belege."""

    def __init__(self, offen=None):
        self._offen = offen or []
        self.verbraucht = []

    def verbrauche(self, spur, kennung, ergebnis=""):
        self.verbraucht.append((spur, kennung, ergebnis))

    def offene(self):
        return list(self._offen)

    def pruefe(self, kennung, spur, seite, paar, menge, kurs):
        return True, ""


class _FakeHandeln:
    """Attrappe: liefert Wachen, Zustand und Kraken-Modul."""

    def __init__(self, positionen=None, wachen=None, offene_orders=None,
                 offene_orders_fehler=None):
        self._positionen = positionen or []
        self._wachen = wachen or {"max_offene_positionen": 4}
        self._offene_orders = offene_orders or {}
        self._offene_orders_fehler = offene_orders_fehler
        self.kraken = self
        self.scan = self

    def wachen(self):
        return self._wachen

    def lade_zustand(self):
        return {"positionen": list(self._positionen)}

    def offene_orders(self):
        if self._offene_orders_fehler is not None:
            raise self._offene_orders_fehler
        return dict(self._offene_orders)

    def journal(self, *args, **kwargs):
        pass

    def schreibe_zustand(self, z):
        pass

    def _spiegeln(self, w, z):
        pass

    def letzter_kurs(self, inst):
        return 1.0

    def fuellung_abwarten(self, txid, sekunden=30.0, abstand=3.0):
        return 10.0, True

    def markt_kauf(self, inst, menge, echt=False):
        return "txid-123"

    def stop_setzen(self, inst, menge, stop, echt=False):
        return "stop-txid"

    def markt_verkauf(self, inst, menge, echt=False):
        return "verkauf-txid"


class DuplikatsGatterTest(unittest.TestCase):
    """Das Gatter muss einen zweiten Kauf fuer dasselbe Instrument abweisen."""

    def _eintrag(self, paar="FILEUR", inst=None, kennung="B1"):
        e = {"spur": "kraken", "kennung": kennung, "seite": "kauf",
             "paar": paar, "menge": "10.0", "preis_max": "1.0"}
        if inst:
            e["zusatz"] = {"inst": inst, "stop": "0.9", "ziel": "1.2"}
        return e

    def _fuehre(self, eintrag, fake_beleg, handeln):
        """fuehre_aus mit Attrappen - der Rest des Gatters ist ehrlich."""
        orig_beleg, orig_kraken = bh.beleg, bh._kraken_weg
        bh.beleg, bh._kraken_weg = fake_beleg, (lambda: handeln)
        try:
            return bh.fuehre_aus(eintrag, anwenden=True)
        finally:
            bh.beleg, bh._kraken_weg = orig_beleg, orig_kraken

    def test_offener_beleg_fuer_dasselbe_instrument_wird_abgelehnt(self):
        """Ein ANDERER offener Beleg fuer FILEUR blockiert einen neuen."""
        anderer = self._eintrag(paar="FILEUR", inst="FILEUR", kennung="B0")
        fake = _FakeBeleg(offen=[anderer])
        r = self._fuehre(self._eintrag(paar="FILEUR", inst="FILEUR"),
                         fake, _FakeHandeln())
        self.assertIn("abgelehnt", r["ergebnis"])
        self.assertIn("Beleg offen", r["ergebnis"])
        self.assertEqual(len(fake.verbraucht), 0,
                         "Beleg darf nicht verbraucht werden")

    def test_eigener_beleg_blockiert_sich_nicht(self):
        """Der KRITISCHE Fall: der gerade ausgefuehrte Beleg steht bis
        verbrauche() selbst in `offene()` - er darf sich nicht selbst
        ablehnen. Fehlt die kennung-Ausnahme, faellt jede Ausfuehrung."""
        eigener = self._eintrag(paar="FILEUR", inst="FILEUR")
        fake = _FakeBeleg(offen=[eigener])
        r = self._fuehre(eigener, fake, _FakeHandeln())
        self.assertNotIn("abgelehnt", r["ergebnis"], r["ergebnis"])
        self.assertEqual(len(fake.verbraucht), 1,
                         "der eigene Beleg wird normal eingeloest")

    def test_offene_position_fuer_dasselbe_instrument_wird_abgelehnt(self):
        """Eine offene Position blockiert einen neuen Kauf."""
        fake = _FakeBeleg()
        r = self._fuehre(self._eintrag(paar="FILEUR", inst="FILEUR"), fake,
                         _FakeHandeln(
                             positionen=[{"paar": "FILEUR", "menge": 5.0}]))
        self.assertIn("abgelehnt", r["ergebnis"])
        self.assertIn("Position offen", r["ergebnis"])

    def test_offene_kauf_order_an_der_boerse_blockiert(self):
        """Eine offene KAUF-Order fuer dasselbe Paar blockiert (Boersen-Zeuge)."""
        fake = _FakeBeleg()
        r = self._fuehre(self._eintrag(paar="FILEUR", inst="FILEUR"), fake,
                         _FakeHandeln(offene_orders={
                             "O1": {"paar": "FILEUR", "seite": "buy",
                                    "art": "market", "menge": "5"}}))
        self.assertIn("abgelehnt", r["ergebnis"])
        self.assertIn("Kauf-Order", r["ergebnis"])
        self.assertEqual(len(fake.verbraucht), 0)

    def test_offene_verkauf_order_blockiert_nicht(self):
        """Eine offene VERKAUF-Order (Schutz-Stop einer Position) blockiert
        keinen Neukauf - sie ist kein Doppelkauf."""
        fake = _FakeBeleg()
        r = self._fuehre(self._eintrag(paar="FILEUR", inst="FILEUR"), fake,
                         _FakeHandeln(offene_orders={
                             "O1": {"paar": "FILEUR", "seite": "sell",
                                    "art": "stop-loss", "menge": "5"}}))
        self.assertNotIn("abgelehnt", r["ergebnis"], r["ergebnis"])

    def test_boerse_nicht_abrufbar_ist_kein_kauf(self):
        """Fail-closed: kann die Hand die Boerse nicht fragen, kauft sie
        nicht - eine ungesehene offene Order waere der Doppelkauf."""
        fake = _FakeBeleg()
        r = self._fuehre(self._eintrag(paar="FILEUR", inst="FILEUR"), fake,
                         _FakeHandeln(
                             offene_orders_fehler=OSError("Netz weg")))
        self.assertIn("abgelehnt", r["ergebnis"])
        self.assertIn("nicht abrufbar", r["ergebnis"])
        self.assertEqual(len(fake.verbraucht), 0)

    def test_verschiedene_instrumente_werden_nicht_blockiert(self):
        """Ein Beleg fuer FILEUR blockiert nicht einen Beleg fuer DOTEUR -
        weder im Beleg- noch im Boersen-Zeugen."""
        fake = _FakeBeleg(offen=[self._eintrag(paar="FILEUR", inst="FILEUR")])
        r = self._fuehre(self._eintrag(paar="DOTEUR", inst="DOTEUR"), fake,
                         _FakeHandeln(offene_orders={
                             "O1": {"paar": "FILEUR", "seite": "buy",
                                    "art": "market", "menge": "5"}}))
        self.assertNotIn("abgelehnt", r["ergebnis"], r["ergebnis"])
        self.assertEqual(len(fake.verbraucht), 1)

    def test_buch_voll_wird_vor_dem_duplikat_gemerkt(self):
        """Bei vollem Buch gewinnt die Buch-Voll-Meldung (frueherer Test)."""
        fake = _FakeBeleg()
        r = self._fuehre(self._eintrag(paar="FILEUR", inst="FILEUR"), fake,
                         _FakeHandeln(
                             positionen=[{"paar": "A"}, {"paar": "B"},
                                         {"paar": "C"}, {"paar": "D"}],
                             wachen={"max_offene_positionen": 4}))
        self.assertIn("Buch voll", r["ergebnis"])


if __name__ == "__main__":
    unittest.main()
