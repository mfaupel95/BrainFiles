"""Saisonalitaet auf der tiefen Reihe (T-018) - reine Rechnung, kein Netz.

Der gehandelte XPERP-Kontrakt ist oft erst ~300 4h-Kerzen alt (50 Tage, damit
~7 Beobachtungen je Wochentag). Die Saisonalitaet ist aber STATISTIK wie
Hebel-Deckel und Trefferquote und darf auf der tiefen Reihe desselben
Basiswerts rechnen (historie.py, `<Basis>-USDT-SWAP`). Geprueft wird:

  1. die Datenbasis wechselt nur, wenn die tiefe Reihe LAENGER ist,
  2. eine tiefe Reihe, die nicht gleichzeitig endet, wird NICHT uebernommen
     (saisonalitaet() liest Wochentag und Phase der naechsten Kerze aus dem Ende),
  3. der Signal-Merge laeuft danach wirklich neu (signal_bauen),
  4. ohne k_stat aendert sich nichts.

Aufruf: python -m unittest test_saisonalitaet_tief   (aus dem xperp-Ordner)
"""

import unittest
from datetime import datetime, timezone

import indikatoren

BAR_MS = 14_400_000          # 4h, wie BAR in bot.py
TS0 = 1_700_000_000_000


def _wt(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc).weekday()


def reihe_mit_wochentag(ende_ts, anzahl, drift_ziel, drift_rest):
    """Kerzenreihe, die auf `ende_ts` endet. Die Kerzen des Wochentags der
    NAECHSTEN Kerze laufen mit `drift_ziel`, alle anderen mit `drift_rest` -
    genau das liest saisonalitaet()."""
    ziel_wt = _wt(ende_ts + BAR_MS)
    start = ende_ts - (anzahl - 1) * BAR_MS
    k = []
    preis = 100.0
    for i in range(anzahl):
        ts = start + i * BAR_MS
        o = preis
        preis += drift_ziel if _wt(ts) == ziel_wt else drift_rest
        h, l = max(o, preis) + 0.05, min(o, preis) - 0.05
        k.append([ts, o, h, l, preis, 1000.0])
    return k


class SaisonalitaetTiefTest(unittest.TestCase):

    def setUp(self):
        # Beide Reihen enden auf derselben Kerze; die kurze ist der junge
        # Kontrakt, die lange die tiefe Reihe. Der Ziel-Wochentag laeuft in der
        # kurzen Reihe AUF und in der langen AB - so ist die Richtung eindeutig
        # zuzuordnen.
        self.ende = TS0 + 400 * BAR_MS
        self.kurz = reihe_mit_wochentag(self.ende, 60, +0.5, -0.2)
        self.tief = reihe_mit_wochentag(self.ende, 300, -0.5, +0.2)

    def test_ohne_k_stat_bleibt_alles_wie_vorher(self):
        a = indikatoren.lage(self.kurz)
        b = indikatoren.lage(self.kurz, k_stat=None)
        self.assertEqual(a["signal"], b["signal"])
        self.assertEqual(a["grund"], b["grund"])
        self.assertEqual(a["sais"], b["sais"])
        self.assertFalse(a["sais_tief"])
        self.assertEqual(a["sais_kerzen"], len(self.kurz))

    def test_gleich_lange_reihe_wechselt_die_basis_nicht(self):
        """k_stat=k ist der Fall ohne --historie: keine Aenderung."""
        a = indikatoren.lage(self.kurz)
        b = indikatoren.lage(self.kurz, k_stat=self.kurz)
        self.assertEqual(a["signal"], b["signal"])
        self.assertEqual(a["sais"], b["sais"])
        self.assertFalse(b["sais_tief"])

    def test_tiefe_reihe_traegt_die_saisonalitaet(self):
        z = indikatoren.lage(self.kurz, k_stat=self.tief)
        self.assertTrue(z["sais_tief"], z["sais"])
        self.assertEqual(z["sais_kerzen"], len(self.tief))
        self.assertGreater(z["sais"]["n"], 6, "zu wenige Beobachtungen aus der tiefen Reihe")
        # Wochentag laeuft in der tiefen Reihe ab -> kurze Reihe
        self.assertEqual(z["sais"]["richtung"], -1, z["sais"])

    def test_merge_laeuft_mit_der_neuen_basis_neu(self):
        kurz = indikatoren.lage(self.kurz)
        tief = indikatoren.lage(self.kurz, k_stat=self.tief)
        self.assertEqual(kurz["sais"]["richtung"], 1, kurz["sais"])
        self.assertNotEqual(kurz["signal"], tief["signal"],
                            "die Saisonalitaet aus der tiefen Reihe hat das Signal nicht bewegt")
        self.assertIn("Saisonalitaet", tief["grund"])

    def test_ungleichzeitige_reihe_wird_nicht_uebernommen(self):
        alt = reihe_mit_wochentag(self.ende - 10 * BAR_MS, 300, -0.5, +0.2)
        z = indikatoren.lage(self.kurz, k_stat=alt)
        self.assertFalse(z["sais_tief"], "alte Reihe darf das Raster nicht verschieben")
        self.assertEqual(z["sais_kerzen"], len(self.kurz))
        self.assertEqual(z["sais"]["richtung"], 1, z["sais"])

    def test_kurze_tiefe_reihe_wird_nicht_uebernommen(self):
        z = indikatoren.lage(self.tief, k_stat=self.kurz)
        self.assertFalse(z["sais_tief"])
        self.assertEqual(z["sais_kerzen"], len(self.tief))


if __name__ == "__main__":
    unittest.main(verbosity=2)
