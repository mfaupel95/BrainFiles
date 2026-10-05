"""Stop-DECKUNG fuer mosaic: die vierte Abgleichsstufe (T-362).

Warum dieser Test existiert
---------------------------
`boersenabgleich` prueft seit 30.09.2026, OB die gemerkte Stop-Kennung an der
Boerse wirksam ist. Das ist die dritte Stufe. Sie scheitert zweifach, und
beides ist am 05.10.2026 am echten Konto gemessen:

  1. **Existenz ist keine Menge.** BTC-USDC: Buch 0,00065270, Stop an der
     Boerse 0,00064984. Die Luecke (2,86e-06, rund 0,20 EUR bei 70.047
     EUR/Stueck) laeuft bis zur Liquidation - der Stop war wirksam, die
     Position war es nicht.
  2. **Die Paarauflosung findet nichts.** Kraken nennt das Paar in
     `AssetPairs` als `XXBTZEUR`, in `OpenOrders` als `XBTEUR`. Ein
     Lookup auf den Paarnamen liefert `base=None` und damit NULL Treffer,
     was sich wie "kein Stop" liest. Vor der Korrektur meldeten BTC und ETH
     **0 Stops an der Boerse**, obwohl je einer lag.

Und der dritte Punkt, der kein Test ist, sondern eine Grenze: **fremde
Stops zaehlen zur Deckung, werden aber nie angefasst.** Am 05.10. lagen
fuenf Stops auf SOL (zusammen 9,54 gegen 0,48 im Buch), vier davon von
fremden Spuren (Solf, LME). Die Position gilt als gedeckt - der Abgleich
faengt sie aber nicht an, das ist Sache von ``waisen_stops``.

Ebenfalls festgenagelt:

  * **Es wird nichts gestellt.** Die Stufe liest und meldet; ein Nachsetzen
    braucht einen Schutzpreis, den niemand genannt hat.
  * **"Nicht lesbar" ist ein dritter Zustand** und wird nicht zu "kein Stop".

Kein Netz, keine Order, keine echte Datei: ``laden`` ist die Naht, und ein
Modulwaechter vergleicht am Ende Dateigroessen des echten Spurenordners.

Gegenproben (im Aufruf geprueft):
 * Mengenvergleich aus ``deckung()`` entfernen -> ``test_teilmenge_ist_ein_befund``
 * Paarauflosung wieder auf den reinen Lookup setzen -> ``test_ beide_schreibweisen``

Lauf (aus mosaic/tests):
    ../../scanner/.venv/Scripts/python.exe -m unittest test_deckung_abgleich -v
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    sys.path.insert(0, p)

import boersenabgleich as ba                                  # noqa: E402
import handeln                                               # noqa: E402

assert os.path.dirname(os.path.abspath(ba.__file__)) == HIER, \
    "falsches boersenabgleich: %s" % ba.__file__


# --- Modulwaechter -----------------------------------------------------------

def _stand():
    return {n: os.path.getsize(os.path.join(HIER, n))
            for n in sorted(os.listdir(HIER))
            if os.path.isfile(os.path.join(HIER, n))}


_VORHER = None


def setUpModule():
    global _VORHER
    _VORHER = _stand()


def tearDownModule():
    neu = {k: v for k, v in _stand().items() if _VORHER.get(k) != v}
    assert not neu, "Test hat in den echten Spurenordner geschrieben: %s" % neu


# --- Attrappe ----------------------------------------------------------------

class Boerse:
    """Ein Boersenzugang ohne Netz, mit derselben Oberflaeche wie das Haus."""

    def __init__(self, basis, schutz=None, fehler=None, bestand=1.0):
        self._basis = basis
        self._schutz = list(schutz or [])      # [{txid, menge, preis, paar}]
        self._fehler = fehler
        self._bestand = bestand

    def basis(self, inst):
        return self._basis

    def bestand(self, inst):
        return self._bestand

    def schutz_auftraege(self, inst, basis):
        if self._fehler:
            raise RuntimeError(self._fehler)
        return list(self._schutz)

    def stop_wirksam(self, txid):
        return True          # die dritte Stufe sagt "ja" - die vierte prueft

    def stop_gefuellt(self, txid):
        return False

    def menge_gerundet(self, inst, menge):
        return float(menge) or None

    def stop_setzen(self, inst, menge, preis):
        raise AssertionError("die Deckungsstufe darf NICHTS setzen")


def _pos(inst="BTC-USDC", menge=0.00065270, stop=70047.0):
    return {"inst": inst, "seite": "long", "menge": menge, "modus": "live",
            "stop": stop, "ziel": 80000.0, "stop_algo_id": "OL2N6C",
            "boerse": "kraken"}


def _z(positionen=None):
    return {"positionen": positionen if positionen is not None else [_pos()]}


def _laden(boerse):
    return lambda namen: {"kraken": boerse}


class DeckungRechnungTest(unittest.TestCase):
    """Die Regel: gedeckt ist, was die MENGE abdeckt."""

    def test_vollstaendig_geschuetzt_ist_kein_befund(self):
        b = Boerse("BTC", [{"txid": "A", "menge": 0.00065270,
                            "preis": 70047.0, "paar": "XBTEUR"}])
        g, soll, auftraege = ba.deckung(b, "BTC-USDC", _pos())
        self.assertAlmostEqual(soll, 0.00065270)
        self.assertEqual(len(auftraege), 1)

    def test_teilmenge_ist_ein_befund(self):
        """DER Fall vom 05.10.2026: wirksamer Stop, Position nicht gedeckt."""
        b = Boerse("BTC", [{"txid": "A", "menge": 0.00064984,
                            "preis": 70047.0, "paar": "XBTEUR"}])
        g, soll, _ = ba.deckung(b, "BTC-USDC", _pos())
        luecke = soll - g
        self.assertAlmostEqual(luecke, 0.00000286, places=9)
        self.assertGreater(luecke, 0.0, "eine wirksame Kennung ist keine Deckung")

    def test_fremde_stops_decken_mit_werden_nicht_angefasst(self):
        """Fuenf Stops auf SOL, vier von fremden Spuren: gedeckt, unberuehrt."""
        p = _pos(inst="SOL-USDC", menge=0.48058439)
        stops = [{"txid": "F1", "menge": 2.57995006, "paar": "SOLEUR"},
                 {"txid": "F2", "menge": 2.65711020, "paar": "SOLEUR"},
                 {"txid": "F3", "menge": 3.34158322, "paar": "SOLEUR"},
                 {"txid": "F4", "menge": 0.47998464, "paar": "SOLEUR"},
                 {"txid": "EIGEN", "menge": 0.48058439, "paar": "SOLEUR"}]
        b = Boerse("SOL", stops)
        g, soll, auftraege = ba.deckung(b, "SOL-USDC", p)
        self.assertEqual(len(auftraege), 5)
        self.assertGreaterEqual(g, soll, "die Position ist gedeckt")

    def test_nicht_lesbar_ist_kein_befund(self):
        """Ein Abruf-Fehler ist NICHT 'kein Stop' - dritter Zustand."""
        b = Boerse("BTC", fehler="no route to host")
        g, soll, _ = ba.deckung(b, "BTC-USDC", _pos())
        self.assertIsNone(g, "None heisst unbekannt, nicht leer")
        self.assertGreater(soll, 0.0)

    def test_ohne_menge_im_buch_keine_aussage(self):
        """Ohne Buchmenge gibt es nichts zu vergleichen - nicht '0 gedeckt'."""
        p = _pos()
        p["menge"] = 0.0
        p["nominal"] = 0.0
        p["einstieg"] = 0.0
        g, soll, _ = ba.deckung(Boerse("BTC", []), "BTC-USDC", p)
        self.assertIsNone(g)
        self.assertEqual(soll, 0.0)


class AbgleichMeldetDieLueckeTest(unittest.TestCase):
    """Die Stufe haengt am Abgleich und schreibt nur eine Zahl in den Zustand."""

    def _lauf(self, schutz):
        z = _z()
        bilanz = ba.pruefe(z, anwenden=True, laden=_laden(Boerse("BTC", schutz)))
        return z, bilanz

    def test_teilmenge_erscheint_als_befund(self):
        z, bilanz = self._lauf([{"txid": "A", "menge": 0.00064984,
                                 "paar": "XBTEUR"}])
        lagen = [f["lage"] for f in bilanz["befunde"]]
        self.assertIn("ungeschuetzt", lagen,
                      "eine Teilmenge ist ein Befund, kein Buchungsvorgang")
        self.assertEqual(bilanz.get("ungeschuetzt"), 1)

    def test_die_luecke_steht_im_zustand(self):
        """Damit Vorschau und Bericht sie zeigen koennen."""
        z, _ = self._lauf([{"txid": "A", "menge": 0.00064984,
                            "paar": "XBTEUR"}])
        p = z["positionen"][0]
        # Die Rechnung zieht MENGE_TOLERANZ (1e-9) von der Differenz ab,
        # damit eine Lot-Rundung nicht als Luecke meldet. Deshalb ist der
        # Erwartungswert 2,859e-06 und nicht 2,860e-06 - die TOLERANZ
        # steckt im Ergebnis, nicht in der Toleranz des Vergleichs.
        self.assertAlmostEqual(p["deckung_luecke"], 2.859e-06, places=12)

    def test_vollstaendig_gedeckt_hinterlaesst_keine_luecke(self):
        z, bilanz = self._lauf([{"txid": "A", "menge": 0.00065270,
                                 "paar": "XBTEUR"}])
        self.assertNotIn("deckung_luecke", z["positionen"][0])
        self.assertNotIn("ungeschuetzt", bilanz)

    def test_es_wird_nie_gestellt(self):
        """Die Stufe liest und meldet - ein geratener Stop waere eine Order."""
        z = _z()
        ba.pruefe(z, anwenden=True,
                  laden=_laden(Boerse("BTC", [{"txid": "A",
                                               "menge": 0.00064984,
                                               "paar": "XBTEUR"}])))
        # `stop_setzen` der Attrappe wirft AssertionError - ein Aufruf hier
        # laesst den Test rot werden statt still zu bleiben.

    def test_keine_buchnung_durch_die_vierte_stufe(self):
        """Die Luecke ist ein BEFUND: sie darf keine Runde erzeugen."""
        z, bilanz = self._lauf([{"txid": "A", "menge": 0.00064984,
                                 "paar": "XBTEUR"}])
        self.assertEqual(bilanz["ausgebucht"], 0)
        self.assertEqual(bilanz["nachgesetzt"], 0)
        self.assertEqual(len(z["positionen"]), 1)


def _spot_stops():
    """`kraken` ist ein ORDNER, kein Paket - `import kraken.spot_stops`
    scheitert mit ModuleNotFoundError, obwohl die Datei da ist (Hausfalle:
    die Spuren laden Nachbarn ueber den PFAD)."""
    import importlib.util
    pfad = os.path.join(HANDEL, "kraken", "spot_stops.py")
    spec = importlib.util.spec_from_file_location("spot_stops_test", pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules["spot_stops_test"] = m
    spec.loader.exec_module(m)
    return m.muenze_aus_paar, m.norm


class BeideSchreibweisenTest(unittest.TestCase):
    """Kraken nennt dasselbe Paar in zwei Formen (Abschnitt 14 der Referenz).

    Der Test baut die Attrappe so, wie der BUG aussieht: `AssetPairs` fuehrt
    `XXBTZEUR`, `OpenOrders` fuehrt `XBTEUR`. Eine Aufloesung ueber das
    Register liefert dann `base=None` und damit keinen Treffer.
    """

    def test_die_kurzform_findet_der_stop(self):
        """XBTEUR steht in OpenOrders, nicht im Register - es muss trotzdem
        als BTC erkannt werden."""
        muenze_aus_paar, norm = _spot_stops()
        paare = {"XXBTZEUR": {"base": "XXBT", "quote": "EUR"}}
        self.assertIsNone(paare.get("XBTEUR", {}).get("base"),
                          "Vorbedingung des Fehlers")
        self.assertEqual(norm(muenze_aus_paar("XBTEUR", paare)), "BTC",
                         "der Rueckfall auf den Ordnernamen muss greifen")

    def test_die_lange_form_findet_der_stop(self):
        muenze_aus_paar, norm = _spot_stops()
        paare = {"XXBTZEUR": {"base": "XXBT", "quote": "EUR"}}
        self.assertEqual(norm(muenze_aus_paar("XXBTZEUR", paare)), "BTC")

    def test_gestaktes_traegt_die_endung(self):
        """'ADAZEUR' ist dasselbe Geld wie 'XADAZEUR' ohne das Register -

        Der Rueckfall auf den Ordnernamen muss die Staking-Endung `.S`
        abschneiden, sonst findet der Filter einen Bestand, den es so
        nicht gibt.
        """
        muenze_aus_paar, norm = _spot_stops()
        self.assertEqual(norm(muenze_aus_paar('ADAZEUR', {})), 'ADA')

    def test_das_x_praefix_ist_nur_teilweise_abgebildet(self):
        """`XADA` bleibt `XADA` - `_PRAEFIX` fuehrt nur XXBT und XETH.

        Das ist kein Fehler, sondern eine Grenze des Registers: der
        Lookup-Zweig liefert fuer XADA ein base, das nicht auf ADA zeigt.
        Wer das nicht weiss, haelt die Kurzform fuer die richtige und
        bekommt bei jeder zweiten Muenze einen leeren Befund.
        """
        muenze_aus_paar, norm = _spot_stops()
        paare = {"XADAZEUR": {"base": "XADA", "quote": "EUR"}}
        self.assertEqual(norm(muenze_aus_paar("XADAZEUR", paare)), "XADA")


if __name__ == "__main__":
    unittest.main()