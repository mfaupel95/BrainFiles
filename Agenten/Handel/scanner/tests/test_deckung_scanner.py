"""Stop-DECKUNG beim scanner: die vierte Abgleichsstufe (T-362).

Warum dieser Test existiert
---------------------------
`boersenstops.pruefe()` prueft seit 28.09.2026 drei Dinge: ob die Position an
der Boerse ist, ob die gemerkte Stop-Kennung wirksam ist, und ob Waisenstops
liegen. Es fragt nicht, **wie viele Kontrakte** dieser Schutz abdeckt.

Am echten Konto gemessen (05.10.2026) sind das zwei verschiedene Befunde, und
der zweite hat mich eine ganze Messrunde gekostet:

**1. Gemessen wird gegen die BOERSE, nicht gegen das Buch.** Dieselben acht
Positionen ergaben

    gegen das Buch (usd / einstieg)   7 ungeschuetzt, 39,23 EUR
    gegen die Boerse (Bestand)        1 ungeschuetzt,  2,08 EUR (nur WLD)

`usd / einstieg` ist der **geplante** Einsatz; die Boerse haelt den Bestand
nach Gebuehr und Ausfuehrung. Ein Handgriff verschiebt das Buch, ohne die
Boerse zu beruehren - und was die Boerse haelt, ist ungeschuetzt, egal was
das Buch behauptet (T-323).

**2. `reduceOnly` ist KEIN Filter fuer diese Spur.** `scanner/okx.py`
setzt das Feld beim Stop nicht, also meldet OKX `reduceOnly: "false"` fuer
jeden Stop (gemessen an WLD: sz 111,15, slTriggerPx 0,5131, state live,
reduceOnly **false**). Ein Filter wie bei xperp verwirft jeden echten Stop
und meldet 7 von 8 Positionen als ungeschuetzt. Die xperp-Regel gehoert zum
**Ordnweg**, nicht zum Markt.

Ebenfalls festgenagelt:

  * **Es wird nichts gestellt.** Die Stufe liest und meldet.
  * **"Nicht lesbar" ist ein dritter Zustand** und wird nicht zu "kein Stop".
  * **Alle OrdTypen fragen** - `oco` und `move_order_stop` fehlen in vielen
    Abfragen, und eine OCO-Position liest sich dann wie "kein Stop" (T-278).

Kein Netz, keine Order, keine echte Datei: ``FakeOKX`` aus
``test_boersenstops`` ist die Naht.

Gegenproben (im Aufruf geprueft):
 * Messgrundlage auf das Buch umstellen -> ``test_gegen_die_boerse_nicht_gegen_das_buch``
 * ``reduceOnly`` wieder erzwingen -> ``test_reduce_only_false_zaehlt_als_schutz``
 * Mengenvergleich entfernen -> ``test_teilmenge_ist_ein_befund``

Lauf (aus dem scanner-Ordner):
    ../scanner/.venv/Scripts/python.exe -m unittest tests.test_deckung_scanner
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
for p in (HIER, HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

import boersenstops as bs                        # noqa: E402
from tests.test_boersenstops import (            # noqa: E402
    AKTIV, FakeOKX, position, zustand)

assert bs.__file__.startswith(HIER), bs.__file__


def algo(sz, stop=0.5131, side="sell", reduce="false", inst="WLD-USDC",
         algo_id="3976770450114895872", typ="conditional"):
    """Eine offene Algo-Order, wie OKX sie fuer scanner liefert."""
    return {"instId": inst, "side": side, "reduceOnly": reduce,
            "sz": str(sz), "slTriggerPx": str(stop), "tpTriggerPx": "",
            "moveTriggerPx": "", "state": "live", "accFillSz": "0",
            "algoId": algo_id, "ordType": typ}


class GrundlageDerMessungTest(unittest.TestCase):
    """Gegen die Boerse messen - das ist der Unterschied."""

    def test_gegen_die_boerse_nicht_gegen_das_buch(self):
        """DER Fall vom 05.10.2026: dieselben Zahlen, zwei Befunde.

        Das Buch behauptet 115,41 Stueck (usd 65,22 / einstieg 0,5651), die
        Boerse haelt 115,21. Der Stop deckt 111,15. Gegen das Buch fehlen
        4,26 Stueck, gegen die Boerse 4,06 - und nur die zweite Zahl
        beschreibt, was wirklich ungeschuetzt ist.
        """
        p = position(inst="WLD-USDC", usd=65.22, einstieg=0.5651, stop=0.5131)
        b = FakeOKX(algo={"conditional": [algo(111.15)]})
        gedeckt, soll, luecke = bs.deckung(b, "WLD-USDC", p, 115.21)
        self.assertAlmostEqual(soll, 115.21, places=8)
        self.assertAlmostEqual(gedeckt, 111.15, places=8)
        self.assertAlmostEqual(luecke, 4.06, places=8)

    def test_die_buchmenge_ist_kein_mass(self):
        """`usd / einstieg` ist der geplante Einsatz, nicht der Bestand."""
        p = position(inst="WLD-USDC", usd=65.22, einstieg=0.5651, stop=0.5131)
        b = FakeOKX(algo={"conditional": [algo(111.15)]})
        _, soll, _ = bs.deckung(b, "WLD-USDC", p, 115.21)
        buchmenge = 65.22 / 0.5651
        self.assertNotAlmostEqual(soll, buchmenge, places=2,
                                  msg="der Test waere sinnlos, wenn beide "
                                      "gleich waeren")

    def test_ohne_bestand_gibt_es_keine_aussage(self):
        p = position(inst="WLD-USDC")
        b = FakeOKX(algo={"conditional": [algo(111.15)]})
        gedeckt, soll, luecke = bs.deckung(b, "WLD-USDC", p, 0.0)
        self.assertIsNone(gedeckt, "Null-Bestand heisst 'unbekannt', nicht "
                                   "'kein Stop'")
        self.assertEqual(soll, 0.0)
        self.assertIsNone(luecke)


class ToleranzTest(unittest.TestCase):
    """Die Toleranz kommt aus dem Markt, nicht aus einer festen Zahl.

    Gemessen 05.10.2026: ETH-USDC haelt 0,03730101, der Stop deckt
    0,03730100. Die Differenz von 1e-8 ist Lot-Rundung (lotSz 0,000001), und
    mit einer festen Toleranz von 1e-9 meldete der Abgleich sie als Luecke.
    WLD-USDC hat lotSz 0,001 - eine feste Grenze von 1e-3 wuerde dort eine
    echte Luecke von 4 Stueck verdecken.
    """

    def test_lotrundung_ist_keine_luecke(self):
        p = position(inst="ETH-USDC", usd=100.0, einstieg=2500.0, stop=2400.0)
        b = FakeOKX(algo={"conditional": [algo(0.03730100, stop=2400.0,
                                                inst="ETH-USDC")]},
                    lot={"ETH-USDC": {"lotSz": 0.000001}})
        gedeckt, soll, luecke = bs.deckung(b, "ETH-USDC", p, 0.03730101)
        self.assertEqual(luecke, 0.0,
                         "ein halber Lot-Schritt ist dieselbe Position")

    def test_die_toleranz_ist_marktabhaengig(self):
        """Die Toleranz folgt dem Lot-Schritt - und ist nie zu LAX.

        Zwei Richtungen, beide gemessen:

        * Zu streng (1e-9 fest): eine Lot-Rundung von 1e-8 gilt als Luecke.
        * Zu lax (1e-3 fest): eine echte Luecke von 4 WLD wird verdeckt,
          weil 4,06 groesser als 1e-3 ist - aber eine halbe Lot-Rundung von
          0,0006 waere es auch.

        Der Test prueft beide Enden: eine Rundung faellt durch, eine echte
        halbe Menge faellt durch.
        """
        p = position(inst="WLD-USDC", usd=65.22, einstieg=0.5651, stop=0.5131)
        a = algo(111.15)
        b = FakeOKX(algo={"conditional": [a]},
                    lot={"WLD-USDC": {"lotSz": 0.001}})
        # 0,0004 liegt unter einem halben Lot-Schritt (0,0005) -> noch
        # dieselbe Position.
        _, _, rundung = bs.deckung(b, "WLD-USDC", p, 111.1504)
        self.assertEqual(rundung, 0.0,
                         "ein halber Lot-Schritt ist dieselbe Position")
        # 4,06 Stueck sind vier volle Schritte -> eine echte Luecke.
        _, _, luecke = bs.deckung(b, "WLD-USDC", p, 115.21)
        self.assertAlmostEqual(luecke, 4.0595, places=8)

    def test_ohne_lotsz_gilt_die_notfallgrenze(self):
        """Faellt die Instrumenttabelle aus, sollte es nicht still werden."""
        class Kaputt(FakeOKX):
            def instrument_regeln(self, inst):
                raise RuntimeError("Instrumenttabelle nicht lesbar")
        p = position(inst="WLD-USDC", usd=65.22, einstieg=0.5651, stop=0.5131)
        b = Kaputt(algo={"conditional": [algo(111.15)]})
        gedeckt, soll, _ = bs.deckung(b, "WLD-USDC", p, 115.21)
        self.assertAlmostEqual(gedeckt, 111.15, places=8)
        self.assertAlmostEqual(soll, 115.21, places=8)


class ReduceOnlyTest(unittest.TestCase):
    """Die Regel, die mich eine Messrunde gekostet hat."""

    def test_reduce_only_false_zaehlt_als_schutz(self):
        """Gemessen an WLD: `reduceOnly: false`, `sz: 111.15`, state live.

        `scanner/okx.py` setzt das Feld nicht - ein Filter darauf verwarf
        jeden echten Stop dieser Spur.
        """
        a = algo(111.15, reduce="false")
        self.assertEqual(a["reduceOnly"], "false", "Vorbedingung des Fehlers")
        b = FakeOKX(algo={"conditional": [a]})
        auftraege = bs.schutz_auftraege(b, "WLD-USDC")
        self.assertEqual(len(auftraege), 1,
                         "ein Stop dieser Spur traegt reduceOnly=false")
        self.assertAlmostEqual(auftraege[0]["sz"], 111.15)

    def test_die_seite_muss_gegen_die_position_laufen(self):
        """Ein `buy` auf einer Long-Position schuetzt nicht - das ist eine
        Wette, kein Notausstieg."""
        b = FakeOKX(algo={"conditional": [algo(111.15, side="buy")]})
        self.assertEqual(bs.schutz_auftraege(b, "WLD-USDC"), [])

    def test_ohne_ausloesung_zaehlt_nicht(self):
        """Ein reiner Limit ohne Stoppreis schuetzt nicht."""
        a = algo(111.15)
        a["slTriggerPx"] = ""
        a["tpTriggerPx"] = ""
        b = FakeOKX(algo={"conditional": [a]})
        self.assertEqual(bs.schutz_auftraege(b, "WLD-USDC"), [])

    def test_ein_trailing_zaehlt_ueber_move_trigger(self):
        """`move_order_stop` traegt `moveTriggerPx`, kein `slTriggerPx`
        (T-278) - wer nur sl liest, stellt einen zweiten Stop daneben."""
        a = algo(111.15, stop="", typ="move_order_stop")
        a["slTriggerPx"] = ""
        a["moveTriggerPx"] = "0.5131"
        b = FakeOKX(algo={"move_order_stop": [a]})
        auftraege = bs.schutz_auftraege(b, "WLD-USDC")
        self.assertEqual(len(auftraege), 1)
        self.assertAlmostEqual(auftraege[0]["sz"], 111.15)

    def test_alle_ordtypen_werden_gefragt(self):
        """Pro Frage darf OKX genau EINEN ordType; fehlende Abfragen lesen
        sich als 'kein Stop'."""
        pfade = []
        class Aufzeichner(FakeOKX):
            def _roh(self, pfad, methode="GET", body=None, signiert=False):
                pfade.append(pfad)
                return super()._roh(pfad, methode, body, signiert)
        b = Aufzeichner(algo={"oco": [algo(50.0, typ="oco")]})
        auftraege = bs.schutz_auftraege(b, "WLD-USDC")
        self.assertEqual(len(auftraege), 1)
        for typ in bs.ALGO_ORDTYPES:
            self.assertTrue(any("ordType=" + typ in p for p in pfade),
                            "%s wurde nicht gefragt" % typ)

    def test_nichts_gefunden_und_fehler_ist_kein_befund(self):
        """Leer heisst 'kein Schutz'. Ein Fehler heisst 'unbekannt' - und
        wird geworfen, damit der Aufrufer 'nicht lesbar' meldet."""
        b = FakeOKX(algo_fehler="no route to host")
        with self.assertRaises(RuntimeError):
            bs.schutz_auftraege(b, "WLD-USDC")
        p = position(inst="WLD-USDC", stop=0.5131)
        gedeckt, soll, luecke = bs.deckung(b, "WLD-USDC", p, 115.21)
        self.assertIsNone(gedeckt, "'nicht lesbar' ist ein dritter Zustand")
        self.assertEqual(soll, 115.21)
        self.assertIsNone(luecke)


class AbgleichMeldetDieLueckeTest(unittest.TestCase):
    """Die Stufe haengt am Abgleich und schreibt nur eine Zahl in die Position."""

    def _lauf(self, algo_liste, bestand, **kw):
        z = zustand(position(inst="WLD-USDC", usd=65.22, einstieg=0.5651,
                             stop=0.5131))
        b = FakeOKX(bestaende={"WLD-USDC": (bestand, bestand)},
                    stops={"alt-1": AKTIV}, algo=algo_liste,
                    lot={"WLD-USDC": {"lotSz": 0.001}}, **kw)
        bilanz = bs.pruefe(z, b, anwenden=True)
        return z, bilanz, b

    def test_teilmenge_ist_ein_befund(self):
        z, bilanz, _ = self._lauf({"conditional": [algo(111.15)]}, 115.21)
        lagen = [f["lage"] for f in bilanz.get("befunde", [])]
        self.assertIn("ungeschuetzt", lagen)
        self.assertEqual(bilanz.get("ungeschuetzt"), 1)
        # Die Toleranz (halber Lot-Schritt 0,0005) steckt im Ergebnis:
        # 115,21 - 111,15 - 0,0005 = 4,0595.
        self.assertAlmostEqual(z["positionen"][0]["deckung_luecke"],
                               4.0595, places=8)

    def test_vollstaendig_gedeckt_hinterlaesst_keine_luecke(self):
        z, bilanz, _ = self._lauf({"conditional": [algo(115.21)]}, 115.21)
        self.assertNotIn("deckung_luecke", z["positionen"][0])
        self.assertNotIn("ungeschuetzt", bilanz)

    def test_es_wird_nie_gestellt(self):
        """Die vierte Stufe liest und meldet. Ein geratener Notausstieg waere
        eine Order, die jemand nicht bestellt hat."""
        _, _, b = self._lauf({"conditional": [algo(111.15)]}, 115.21)
        self.assertEqual(b.gesetzt, [],
                         "die Deckungsstufe hat eine Order ausgeloest")

    def test_keine_buchung_durch_die_vierte_stufe(self):
        z, bilanz, _ = self._lauf({"conditional": [algo(111.15)]}, 115.21)
        self.assertEqual(bilanz["ausgebucht"], 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_nicht_lesbar_wird_gezaehlt_und_nicht_vermutet(self):
        z, bilanz, _ = self._lauf({}, 115.21, algo_fehler="timeout")
        lagen = [f["lage"] for f in bilanz.get("befunde", [])]
        self.assertIn("unklar_deckung", lagen)
        self.assertNotIn("ungeschuetzt", lagen,
                         "'unbekannt' darf nicht als 'ungeschuetzt' enden")
        self.assertNotIn("deckung_luecke", z["positionen"][0])


if __name__ == "__main__":
    unittest.main()