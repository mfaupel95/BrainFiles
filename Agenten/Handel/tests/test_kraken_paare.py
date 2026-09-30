"""EINE Kraken-Paar-Tabelle je Quote (EUR Vorgabe, USDC waehlbar).

Anlass (Auftrag Max 28.09.2026: "Welche Spuren koennen live auf Kraken USDC
geschaltet werden?"): Vier Spuren fragten dieselbe Sache und jede hatte ihre
eigene Antwort - mosaic/kraken_spot.PAARE, moondev_marktlage/live_kraken.PAAR,
die Watchlist der kraken-Spur und nautilus_kraken/wachen.json. Kraken fuehrt
BTC/ETH/SOL/XRP auch gegen USDC (am 28.09.2026 gemessen, 45 Paare online).

Der Kern dieser Tests ist NICHT die Tabelle, sondern die Regel dahinter: mit
Quote USDC darf nie still ein EUR-Markt herauskommen. Ein unbekanntes oder
falsch quotiertes Paar ist ein Fehler, keine Ersatzwahl - sonst landet eine
Order im falschen Markt.
"""
import importlib.util
import os
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


kp = _lade("kraken_paare", os.path.join(HANDEL, "kraken_paare.py"))
assert kp.__file__.endswith("kraken_paare.py")


class AbbildungTest(unittest.TestCase):
    def test_eur_ist_die_vorgabe(self):
        self.assertEqual("XXBTZEUR", kp.paar_fuer("BTC-USDC"))
        self.assertEqual("XXBTZEUR", kp.paar_fuer("BTC-USDC", "EUR"))
        self.assertEqual("SOLEUR", kp.paar_fuer("SOL-USDC"))

    def test_usdc_liefert_usdc_paare(self):
        # mosaic rechnet in OKX-Namen; die Kraken-Quote ist eine eigene Wahl.
        self.assertEqual("XBTUSDC", kp.paar_fuer("BTC-USDC", "USDC"))
        self.assertEqual("ETHUSDC", kp.paar_fuer("ETH-USDC", "USDC"))
        self.assertEqual("SOLUSDC", kp.paar_fuer("SOL-USDC", "USDC"))
        self.assertEqual("LINKUSDC", kp.paar_fuer("LINK-USDC", "USDC"))

    def test_fertiger_kraken_name_geht_durch(self):
        # Watchlist-Fall: der Name enthaelt seine Quote schon.
        self.assertEqual("SOLEUR", kp.paar_fuer("SOLEUR", "USDC"))
        self.assertEqual("XBTUSDC", kp.paar_fuer("XBTUSDC", "EUR"))

    def test_fremde_quote_ist_ein_fehler_nicht_der_rueckfall(self):
        # Das ist die eigentliche Falle: 'BTC-EUR' mit USDC darf NICHT still
        # als XXBTZEUR durchgehen.
        with self.assertRaises(ValueError):
            kp.paar_fuer("BTC-EUR", "USDC")

    def test_unbekanntes_instrument_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            kp.paar_fuer("GIBTSNICHT-USDC")
        with self.assertRaises(ValueError):
            kp.paar_fuer("BTC-USDC", "GBP")

    def test_quote_von_paar(self):
        self.assertEqual("USDC", kp.quote_von_paar("XBTUSDC"))
        self.assertEqual("EUR", kp.quote_von_paar("SOLEUR"))
        self.assertEqual("EUR", kp.quote_von_paar("XXBTZEUR"))
        self.assertIsNone(kp.quote_von_paar("PF_XBTUSD"))


class WachenTest(unittest.TestCase):
    def test_vorgabe_ohne_schluessel(self):
        self.assertEqual("EUR", kp.quote_aus_wachen({}))
        self.assertEqual("EUR", kp.quote_aus_wachen(None))

    def test_kleinschreibung_ist_erlaubt(self):
        self.assertEqual("USDC", kp.quote_aus_wachen({"kraken_quote": "usdc"}))

    def test_tippfehler_ist_ein_fehler(self):
        # Ein 'EURO' darf nicht still auf EUR zurueckfallen.
        with self.assertRaises(ValueError):
            kp.quote_aus_wachen({"kraken_quote": "EURO"})


class MosaicTest(unittest.TestCase):
    """mosaic muss die Quote aus der wachen uebernehmen - und ohne sie nichts
    aendern (Bestandsschutz fuer den laufenden Live-Betrieb)."""

    def setUp(self):
        self.ks = _lade("mosaic_kraken_spot_test",
                        os.path.join(HANDEL, "mosaic", "kraken_spot.py"))
        self.ks.setze_quote("EUR")

    def tearDown(self):
        self.ks.setze_quote("EUR")

    def test_ohne_umstellung_bleibt_es_bei_eur(self):
        self.assertEqual("XETHZEUR", self.ks.paar_fuer("ETH-USDC"))

    def test_umstellung_auf_usdc(self):
        self.ks.setze_quote("USDC")
        self.assertEqual("ETHUSDC", self.ks.paar_fuer("ETH-USDC"))
        self.assertEqual("SOLUSDC", self.ks.paar_fuer("SOL-USDC"))

    def test_usdc_lauf_laesst_kein_eur_paar_durch(self):
        self.ks.setze_quote("USDC")
        with self.assertRaises(ValueError):
            self.ks.paar_fuer("HYPE-EUR")     # nur in der EUR-Tabelle

    def test_unbekannte_quote_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            self.ks.setze_quote("EURO")

    def test_handeln_gibt_die_quote_aus_der_wachen_weiter(self):
        quelle = open(os.path.join(HANDEL, "mosaic", "handeln.py"),
                      encoding="utf-8").read()
        self.assertIn("kraken_paare.quote_aus_wachen", quelle)
        self.assertIn("setze_quote", quelle)


class MarktlageTest(unittest.TestCase):
    """moondev_marktlage: Paar und Kontowaehrung muessen zusammenpassen -
    die Waehrung des Paares MUSS die Waehrung des Guthabens sein."""

    def test_vorgabe_bleibt_xbtzeur(self):
        lk = _lade("marktlage_live_test",
                   os.path.join(HANDEL, "moondev_marktlage", "live_kraken.py"))
        paar, waehrung = lk._paar_und_waehrung({})
        self.assertEqual("XXBTZEUR", paar)
        self.assertEqual("EUR", waehrung)

    def test_usdc_stellt_paar_und_waehrung_um(self):
        lk = _lade("marktlage_live_test2",
                   os.path.join(HANDEL, "moondev_marktlage", "live_kraken.py"))
        paar, waehrung = lk._paar_und_waehrung({"kraken_quote": "USDC"})
        self.assertEqual("XBTUSDC", paar)
        self.assertEqual("USDC", waehrung)

    def test_festes_paar_gewinnt_und_setzt_die_waehrung(self):
        lk = _lade("marktlage_live_test3",
                   os.path.join(HANDEL, "moondev_marktlage", "live_kraken.py"))
        paar, waehrung = lk._paar_und_waehrung({"paar": "XETHUSDC"})
        self.assertEqual("XETHUSDC", paar)
        self.assertEqual("USDC", waehrung)


class EurcTest(unittest.TestCase):
    """EURC ist eine dritte Quote - und sie ist KURZ: Kraken fuehrt gegen EURC
    nur XBT, ETH und SOL (30.09.2026 gemessen). Genau darum ist der Fehlerfall
    hier der wichtigere Test: ein Instrument ohne EURC-Markt darf NICHT still in
    einem EUR-Markt landen."""

    def test_eurc_ist_eine_erlaubte_quote(self):
        self.assertEqual("EURC", kp.quote_aus_wachen({"kraken_quote": "eurc"}))
        self.assertIn("EURC", kp.QUOTEN)

    def test_die_drei_maerkte_werden_abgebildet(self):
        self.assertEqual("XBTEURC", kp.paar_fuer("BTC-USDC", "EURC"))
        self.assertEqual("ETHEURC", kp.paar_fuer("ETH-USDC", "EURC"))
        self.assertEqual("SOLEURC", kp.paar_fuer("SOL-USDC", "EURC"))
        # Dasselbe Instrument, in EURC notiert - mosaic rechnet in OKX-Namen,
        # die Quote ist eine eigene Wahl.
        self.assertEqual("XBTEURC", kp.paar_fuer("BTC-EUR", "EURC"))

    def test_ohne_markt_ist_es_ein_fehler(self):
        with self.assertRaises(ValueError):
            kp.paar_fuer("DOGE-USDC", "EURC")   # DOGE hat kein EURC-Paar
        with self.assertRaises(ValueError):
            kp.paar_fuer("ADA-EUR", "EURC")

    def test_tabelle_erfindet_keine_maerkte(self):
        """Drei Paare, drei Maerkte - mehr gibt es bei Kraken nicht."""
        werte = set(kp.PAARE["EURC"].values())
        self.assertEqual({"XBTEURC", "ETHEURC", "SOLEURC"}, werte)

    def test_quote_von_paar_kennt_eurc(self):
        """'XBTEURC' endet auf EURC - die EUR-Regel darf hier nicht greifen."""
        self.assertEqual("EURC", kp.quote_von_paar("XBTEURC"))
        self.assertEqual("EUR", kp.quote_von_paar("XXBTZEUR"))
        self.assertEqual("USDC", kp.quote_von_paar("XBTUSDC"))

    def test_marktlage_stellt_paar_und_waehrung_um(self):
        lk = _lade("marktlage_eurc_test",
                   os.path.join(HANDEL, "moondev_marktlage", "live_kraken.py"))
        paar, waehrung = lk._paar_und_waehrung({"kraken_quote": "EURC"})
        self.assertEqual("XBTEURC", paar)
        self.assertEqual("EURC", waehrung)

    def test_mosaic_nimmt_eurc_an(self):
        ks = _lade("mosaic_eurc_test",
                   os.path.join(HANDEL, "mosaic", "kraken_spot.py"))
        try:
            ks.setze_quote("EURC")
            self.assertEqual("SOLEURC", ks.paar_fuer("SOL-USDC"))
            with self.assertRaises(ValueError):
                ks.paar_fuer("HYPE-EUR")     # nur in der EUR-Tabelle
        finally:
            ks.setze_quote("EUR")


if __name__ == "__main__":
    unittest.main()