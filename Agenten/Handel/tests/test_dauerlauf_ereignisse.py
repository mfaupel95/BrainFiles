"""Was der Dauerlauf in den Chat schickt - und was nicht.

Zyklus 21 der Basis (25.09.2026) schickte fuenf Zeilen, davon NULL Ereignisse:

    scanner: - Ausstiege -
    swap: XAU-USDT-SWAP          short  Stop 4318.200000 (0.96%)  Ziel ...
    mosaic: 3 Live-Position(en) bleiben stehen - ...
    mosaic: 3 Live-Position(en) bleiben stehen - ...      (dreimal dasselbe)
    kraken: - Ausstiege -

Zwei Ueberschriften, die Fortsetzungszeile einer frisch eroeffneten Anlage (das
Wort "Stop" ist dort eine Spaltenueberschrift) und dreimal derselbe Hinweis -
gemeldet wurde also nichts, was Max wissen musste. Die Zeilen unten sind
woertlich aus diesem Zyklus uebernommen.

Die zweite Regel: dieselbe Zeile wird nicht zweimal geschickt. Ohne sie war
eine Sperre, die einen ganzen Tag stehen bleibt, 96-mal im Chat.
"""

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
sys.path.insert(0, str(HANDEL))

import dauerlauf                                                 # noqa: E402

# --- so sah Zyklus 21 aus ---------------------------------------------------
UEBERSCHRIFT = "- Ausstiege -"
SWAP_ANLAGE = ("        XAU-USDT-SWAP          short  Stop 4318.200000 (0.96%)  "
               "Ziel 4194.600000  Liq 5111.015000 (19.5% weg)")
SWAP_PFLICHT = ("        XAU-USDT-SWAP          short  Pflicht: Funding "
                "+0.011%, Gebuehr 0.060%, Quote noetig 0.7% / beobachtet 1.2%")
SWAP_AUF = ("  AUF XAU-USDT-SWAP      short @ 4277.000000  1 Kontrakte, 3.0x, "
            "10.00 Margin (30.00 nominal)")
MOSAIC_HINWEIS = ("  3 Live-Position(en) bleiben stehen - der Papierzweig "
                  "verkauft sie nicht (nur der Live-Lauf schliesst sie).")

# --- echte Ereignisse (aus den Spuren, woertlich) ----------------------------
AUSSTIEG_ZIEL = ("  AUSSTIEG (ziel) ZEC-USDT @ 1618.360000  +20.17%  "
                 "Erloes 1618.36 USDC")
NOTAUS = "  NOTAUS (kill): BTC-USDC @ 61234.500000  -3.10%"
KILL = "- KILL-SWITCH: Ruecklauf 101.20 USD ueber Deckel 100 - kein Neuerwerb"
KILL_SCHWELLE = "- Kill-Schwelle erreicht (Ruecklauf 41.20 USD) - Groesse halbiert"
STOP_AUSGELOEST = "  der Boersen-Stop hat ausgeloest - Position ist weg"
FEHLSCHLAG = "  Verkauf ZEC-USDT fehlgeschlagen: OKX 51119 Order failed"
GESPERRT = "--live angefordert, aber gesperrt: kein freies Guthaben"


class RauschenTest(unittest.TestCase):
    """Zeilen, die im Chat nichts zu suchen haben."""

    def test_rauschen_wird_nicht_gemeldet(self):
        for zeile in (UEBERSCHRIFT, SWAP_ANLAGE, SWAP_PFLICHT, MOSAIC_HINWEIS,
                      "", "   ", "- Einstiege -", "- Ausstiege -"):
            with self.subTest(zeile=zeile[:40]):
                self.assertEqual(dauerlauf.ereigniszeilen(zeile), [])

    def test_der_ganze_zyklus_21_ergibt_keine_meldung(self):
        """Die fuenf Zeilen des Zyklus in EINER Ausgabe: nichts bleibt uebrig."""
        ausgabe = "\n".join([
            UEBERSCHRIFT,
            SWAP_ANLAGE,
            SWAP_PFLICHT,
            MOSAIC_HINWEIS, MOSAIC_HINWEIS, MOSAIC_HINWEIS,
            UEBERSCHRIFT,
        ])
        self.assertEqual(dauerlauf.ereigniszeilen(ausgabe), [])

    def test_wort_ohne_ereignis_zaehlt_nicht(self):
        """'Stop' und 'Verkauf' sind Woerter, kein Geschehen."""
        for zeile in ("  Stop 4318.200000", "  Verkauf moeglich, kein Signal",
                      "  Ziel 4194.600000 noch offen"):
            with self.subTest(zeile=zeile):
                self.assertEqual(dauerlauf.ereigniszeilen(zeile), [])


class EreignisTest(unittest.TestCase):
    """Zeilen, die gemeldet werden muessen."""

    def test_ausstieg_und_notaus(self):
        for zeile in (AUSSTIEG_ZIEL, NOTAUS):
            with self.subTest(zeile=zeile[:30]):
                self.assertEqual(dauerlauf.ereigniszeilen(zeile), [zeile.strip()])

    def test_eroeffnung_nennt_ihr_instrument(self):
        """Die AUF-Zeile traegt das Subjekt, die Fortsetzungszeile nicht."""
        self.assertEqual(dauerlauf.ereigniszeilen(SWAP_AUF),
                         [SWAP_AUF.strip()])

    def test_kill_und_fehlschlag(self):
        for zeile in (KILL, KILL_SCHWELLE, STOP_AUSGELOEST, FEHLSCHLAG,
                      GESPERRT):
            with self.subTest(zeile=zeile[:30]):
                self.assertEqual(dauerlauf.ereigniszeilen(zeile), [zeile.strip()])

    def test_halbe_ausgabe_haelt_richtige_zeilen_auseinander(self):
        ausgabe = "\n".join(["Einstiege:", SWAP_AUF, "", "Ausstiege:",
                             AUSSTIEG_ZIEL, FEHLSCHLAG])
        self.assertEqual(dauerlauf.ereigniszeilen(ausgabe),
                         [SWAP_AUF.strip(), AUSSTIEG_ZIEL.strip(),
                          FEHLSCHLAG.strip()])


class WiederholungTest(unittest.TestCase):
    """Dieselbe Zeile nur einmal - aber nach einer Pause wieder."""

    def test_gleiche_zeile_zweimal_ergibt_eine_meldung(self):
        neu, alle = dauerlauf.neue_ereignisse(KILL, ())
        self.assertEqual(neu, [KILL])
        neu2, alle2 = dauerlauf.neue_ereignisse(KILL, alle)
        self.assertEqual(neu2, [])
        self.assertEqual(alle2, alle)

    def test_neue_zeile_kommt_dazu(self):
        _, alle = dauerlauf.neue_ereignisse(KILL, ())
        neu, alle2 = dauerlauf.neue_ereignisse("\n".join([KILL, FEHLSCHLAG]),
                                               alle)
        self.assertEqual(neu, [FEHLSCHLAG.strip()])
        self.assertEqual(alle2, [KILL, FEHLSCHLAG.strip()])

    def test_ereignis_verschwindet_und_kehrt_wieder(self):
        """Stille heisst nicht 'abgehakt': ein wiederkehrendes Ereignis meldet sich."""
        _, alle = dauerlauf.neue_ereignisse(FEHLSCHLAG, ())
        neu, alle_leer = dauerlauf.neue_ereignisse("Einstiege: keine", alle)
        self.assertEqual((neu, alle_leer), ([], []))
        neu2, _ = dauerlauf.neue_ereignisse(FEHLSCHLAG, alle_leer)
        self.assertEqual(neu2, [FEHLSCHLAG.strip()])

    def test_unbekannte_spur_startet_ohne_vorwissen(self):
        neu, _ = dauerlauf.neue_ereignisse(AUSSTIEG_ZIEL, None)
        self.assertEqual(neu, [AUSSTIEG_ZIEL.strip()])


if __name__ == "__main__":
    unittest.main()