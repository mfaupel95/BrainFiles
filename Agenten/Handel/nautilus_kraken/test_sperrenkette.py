"""Tests fuer die Sperrenkette (sperren_zeile) des Live-Orderwegs.

Kein Netz, keine echten Orders. Geprueft wird: Nur wenn handel_erlaubt,
freigabe.erfuellt UND ein offenes Freigabefenster zusammenkommen, gibt
sperren_zeile() None zurueck (live erlaubt). Jede einzelne Sperre muss
genannt werden. Das ist der Kern des REST-API-Umbaus: Der Live-Orderweg
(live = modus == "live" and not sperren_zeile(w)) wird NIE ausgefuehrt,
solange die Spur nicht ueber die Freigabekette scharf ist.

Aufruf:  .venv\\Scripts\\python.exe test_sperrenkette.py
"""

import os
import sys
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import handeln  # noqa: E402


class SperrenketteTest(unittest.TestCase):
    def test_handel_erlaubt_false_sperrt(self):
        w = {"handel_erlaubt": False, "freigabe": {"erfuellt": True}}
        with patch("handeln.freigabefenster.lade") as lade:
            lade.return_value.offen.return_value = True
            sperren = handeln.sperren_zeile(w)
        self.assertIn("handel_erlaubt=false", sperren)

    def test_freigabe_nicht_erfuellt_sperrt(self):
        w = {"handel_erlaubt": True, "freigabe": {"erfuellt": False}}
        with patch("handeln.freigabefenster.lade") as lade:
            lade.return_value.offen.return_value = True
            sperren = handeln.sperren_zeile(w)
        self.assertIn("freigabe.erfuellt=false", sperren)

    def test_fenster_zu_sperrt(self):
        w = {"handel_erlaubt": True, "freigabe": {"erfuellt": True}}
        with patch("handeln.freigabefenster.lade") as lade:
            lade.return_value.offen.return_value = False
            sperren = handeln.sperren_zeile(w)
        self.assertIn("Freigabefenster", sperren)

    def test_spot_guthaben_unter_dem_einsatz_sperrt(self):
        # Spot: ohne freies Guthaben scheitert die Order an
        # 'EOrder:Insufficient funds' - und die Spur saehe trotzdem ok aus.
        w = {"handel_erlaubt": True, "freigabe": {"erfuellt": True},
             "live_einsatz_eur": 1.0}
        with patch("handeln.freigabefenster.lade") as lade, \
             patch("handeln.kraken_rest.produkt", return_value="spot"), \
             patch("handeln.kraken_rest.guthaben", return_value=0.5):
            lade.return_value.offen.return_value = True
            sperren = handeln.sperren_zeile(w)
        self.assertIn("Guthaben zu klein", sperren)
        self.assertIn("0.50 EUR frei", sperren)
        self.assertIn("noetig 1.00", sperren)

    def test_spot_guthaben_ueber_dem_einsatz_erlaubt(self):
        w = {"handel_erlaubt": True, "freigabe": {"erfuellt": True},
             "live_einsatz_eur": 1.0}
        with patch("handeln.freigabefenster.lade") as lade, \
             patch("handeln.kraken_rest.produkt", return_value="spot"), \
             patch("handeln.kraken_rest.guthaben", return_value=4.1):
            lade.return_value.offen.return_value = True
            self.assertIsNone(handeln.sperren_zeile(w))

    def test_ohne_einsatz_kein_guthabenabruf(self):
        # Ohne Einsatz-Zahl gibt es kein Tor und keinen Netzaufruf: die
        # Sperrenkette darf nicht bei jedem Aufruf Kraken fragen.
        w = {"handel_erlaubt": True, "freigabe": {"erfuellt": True}}
        with patch("handeln.freigabefenster.lade") as lade, \
             patch("handeln.kraken_rest.produkt", return_value="spot"), \
             patch("handeln.kraken_rest.guthaben") as guthaben:
            lade.return_value.offen.return_value = True
            self.assertIsNone(handeln.sperren_zeile(w))
        guthaben.assert_not_called()

    def test_alle_offen_erlaubt(self):
        w = {"handel_erlaubt": True, "freigabe": {"erfuellt": True}}
        with patch("handeln.freigabefenster.lade") as lade:
            lade.return_value.offen.return_value = True
            sperren = handeln.sperren_zeile(w)
        self.assertIsNone(sperren)


if __name__ == "__main__":
    unittest.main()
