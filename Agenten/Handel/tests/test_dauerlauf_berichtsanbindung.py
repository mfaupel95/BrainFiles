"""Test fuer Aufgabe 6: Anbindung der Berichtsschicht an dauerlauf.py.

Belegt wird nur der Zweig "3. Tagesbericht faellig?" in Lauf.runde():
  1. Nach dem Tagesbericht wird der Schnappschuss geschrieben (mit
     mit_xperp=False), NICHT davor.
  2. Ein gescheiterter Schnappschuss geht nur ins Protokoll, nicht per
     Telegram (sende bleibt auf den Tagesbericht/Wochenbericht beschraenkt).
  3. Am Montag folgt zusaetzlich der Wochenbericht.
  4. Ein gescheiterter Wochenbericht haengt den Dauerlauf nicht auf.

Kein echter Spiegelzugriff, kein echtes Netz: alle Aufrufe werden ersetzt.

Nachsehen statt glauben:
    python tests/test_dauerlauf_berichtsanbindung.py
"""

import datetime as dt
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import dauerlauf                                          # noqa: E402


class BerichtszweigTest(unittest.TestCase):
    def _lauf(self):
        lauf = dauerlauf.Lauf(takt=0, trocken=True)
        lauf.pausiert = True  # Zyklus (Schritt 2) ausblenden
        lauf.stumm = False
        lauf.letzter_bericht = None
        return lauf

    def test_schnappschuss_kommt_nach_dem_bericht(self):
        lauf = self._lauf()
        reihenfolge = []
        # Dienstag: kein Wochenbericht, der die Reihenfolge stoert.
        with patch("dauerlauf.jetzt",
                    return_value=dt.datetime(2026, 9, 22, 9, 0)), \
             patch("dauerlauf.tagesbericht.baue",
                   side_effect=lambda **kw: reihenfolge.append("bericht")
                   or "BERICHT") as m_bericht, \
             patch("dauerlauf.lage.erhebe",
                   side_effect=lambda **kw: reihenfolge.append("lage")
                   or "LAGE") as m_lage, \
             patch("dauerlauf.schnappschuss.baue",
                   side_effect=lambda stand: reihenfolge.append("baue")
                   or "STAND") as m_sbaue, \
             patch("dauerlauf.schnappschuss.schreibe",
                   side_effect=lambda stand: reihenfolge.append(
                       "schreibe")) as m_schreibe:
            lauf.runde()
        self.assertEqual(reihenfolge, ["bericht", "lage", "baue", "schreibe"])
        m_bericht.assert_called_once_with(mit_xperp=True)
        m_lage.assert_called_once_with(mit_xperp=False)
        m_sbaue.assert_called_once_with("LAGE")
        m_schreibe.assert_called_once_with("STAND")

    def test_gescheiterter_schnappschuss_geht_nur_ins_protokoll(self):
        lauf = self._lauf()
        with patch("dauerlauf.jetzt",
                    return_value=dt.datetime(2026, 9, 22, 9, 0)), \
             patch("dauerlauf.tagesbericht.baue", return_value="BERICHT"), \
             patch("dauerlauf.lage.erhebe", return_value="LAGE"), \
             patch("dauerlauf.schnappschuss.baue", return_value="STAND"), \
             patch("dauerlauf.schnappschuss.schreibe",
                   side_effect=RuntimeError("Platte weg")), \
             patch("dauerlauf.protokoll") as m_protokoll, \
             patch.object(lauf, "sende") as m_sende:
            lauf.runde()
        gesendet = [c.args[0] for c in m_sende.call_args_list]
        self.assertIn("BERICHT", gesendet)
        self.assertFalse(any("Schnappschuss" in g for g in gesendet))
        protokolliert = [c.args[0] for c in m_protokoll.call_args_list]
        self.assertTrue(any("Schnappschuss gescheitert" in p
                             for p in protokolliert))

    def test_montags_kommt_der_wochenbericht_danach(self):
        lauf = self._lauf()
        reihenfolge = []
        with patch("dauerlauf.jetzt",
                    return_value=dt.datetime(2026, 9, 21, 9, 0)), \
             patch("dauerlauf.tagesbericht.baue",
                   side_effect=lambda **kw: reihenfolge.append("tag")
                   or "T"), \
             patch("dauerlauf.lage.erhebe", return_value="LAGE"), \
             patch("dauerlauf.schnappschuss.baue", return_value="STAND"), \
             patch("dauerlauf.schnappschuss.schreibe",
                   side_effect=lambda stand: reihenfolge.append("schreibe")), \
             patch("dauerlauf.wochenbericht.baue",
                   side_effect=lambda: reihenfolge.append("woche")
                   or "W") as m_woche:
            lauf.runde()
        self.assertEqual(dt.date(2026, 9, 21).weekday(), 0)
        self.assertEqual(reihenfolge, ["tag", "schreibe", "woche"])
        m_woche.assert_called_once_with()

    def test_dienstags_kein_wochenbericht(self):
        lauf = self._lauf()
        with patch("dauerlauf.jetzt",
                    return_value=dt.datetime(2026, 9, 22, 9, 0)), \
             patch("dauerlauf.tagesbericht.baue", return_value="T"), \
             patch("dauerlauf.lage.erhebe", return_value="LAGE"), \
             patch("dauerlauf.schnappschuss.baue", return_value="STAND"), \
             patch("dauerlauf.schnappschuss.schreibe"), \
             patch("dauerlauf.wochenbericht.baue") as m_woche:
            lauf.runde()
        m_woche.assert_not_called()

    def test_gescheiterter_wochenbericht_haengt_nichts_auf(self):
        lauf = self._lauf()
        with patch("dauerlauf.jetzt",
                    return_value=dt.datetime(2026, 9, 21, 9, 0)), \
             patch("dauerlauf.tagesbericht.baue", return_value="T"), \
             patch("dauerlauf.lage.erhebe", return_value="LAGE"), \
             patch("dauerlauf.schnappschuss.baue", return_value="STAND"), \
             patch("dauerlauf.schnappschuss.schreibe"), \
             patch("dauerlauf.wochenbericht.baue",
                   side_effect=RuntimeError("kaputt")), \
             patch.object(lauf, "sende") as m_sende:
            lauf.runde()  # darf nicht werfen
        gesendet = [c.args[0] for c in m_sende.call_args_list]
        self.assertTrue(any("Wochenbericht gescheitert" in g
                             for g in gesendet))


if __name__ == "__main__":
    unittest.main()
