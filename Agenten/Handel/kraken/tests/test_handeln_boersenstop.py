"""Der Boersen-Stop im Live-Pfad der Kraken-Spur: gesetzt, abgeraeumt, nachgesehen.

Drei Loecher, die dieser Test festhaelt (Befund 14.09.2026):

1. Scheiterte `stop_setzen` NACH einem erfolgreichen Kauf, brach die
   Ausnahmebehandlung den ganzen Einstieg ab (`continue`) - die gekauften
   Coins lagen am Markt, standen aber in keinem Buch und hatten keinen Stop.
2. Ein nicht stornierbarer Stop (schon ausgeloest oder schon storniert) brach
   den Verkauf ab, weil beide Aufrufe in einem try-Block standen. Die Position
   blieb als Karteileiche im Buch stehen, obwohl sie am Markt weg war.
3. Loeste der Boersen-Stop zwischen zwei Zyklen aus, scheiterte der eigene
   Verkauf - niemand sah nach, ob der Stop nicht laengst verkauft hatte.

Kein Netz: handeln.kraken wird durch eine Attrappe ersetzt, JOURNAL zeigt in
eine Temp-Datei. Direkt ausfuehrbar:  python tests/test_handeln_boersenstop.py
"""

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))          # kraken/ - handeln, kraken

import handeln as h                                            # noqa: E402

# Nur die Form: welche Felder liest der Lauf.
W = {"max_offene_positionen": 4, "max_gesamt_eur": 200, "abklingzeit_tage": 3,
     "gebuehr_taker": 0.0}

V = {"inst": "XLINKZEUR", "einstieg": 11.8, "stop": 11.0, "ziel": 13.3,
     "stop_pct": 6.4, "eur": 50.0, "score": 70.0}

P = {"paar": "XLINKZEUR", "einstieg": 11.8, "eur": 50.0, "menge": 4.2373,
     "stop": 11.0, "ziel": 13.3, "eroeffnet": "2026-09-14",
     "kauf_txid": "kauf-1", "stop_txid": "stop-1", "boersen_stop_fehlt": False}


class AttrappeKraken:
    """Das kraken-Modul ohne Netz. Jeder Aufruf wird mitgeschrieben."""

    def __init__(self, kurs=11.9, fuellung=4.2, stop_fehler=False,
                 verkauf_fehler=False, storno_fehler=False,
                 stop_gefuellt=False):
        self.kurs = kurs
        self.fuellung = fuellung
        self.stop_fehler = stop_fehler
        self.verkauf_fehler = verkauf_fehler
        self.storno_fehler = storno_fehler
        # nicht self.stop_gefuellt: so heisst die Methode darunter.
        self.gefuellt_flag = stop_gefuellt
        self.rufe = []

    def letzter_kurs(self, paar):
        self.rufe.append(("kurs", paar))
        return self.kurs

    def paar_info(self, paar):
        return {"mengen_stellen": 8, "mindestmenge": 0.0001, "mindestwert": 0.5}

    def markt_kauf(self, paar, menge, echt=False):
        self.rufe.append(("kauf", paar, menge))
        return "kauf-1"

    def gefuellte_menge(self, txid):
        return self.fuellung

    def fuellung_abwarten(self, txid, sekunden=30.0, abstand=3.0):
        """Ohne Warten: was in der Attrappe gefuellt ist, ist sofort da.

        Die echte Funktion fragt bis zu `sekunden` lang nach - hier waere das
        nur Verzoegerung ohne Erkenntnis. 0 heisst: die Boerse kennt die
        Kennung (noch) nicht, die Order ist unbestaetigt.
        """
        self.rufe.append(("fuellung_abwarten", txid))
        menge = self.gefuellte_menge(txid)
        return (float(menge), True) if menge else (0.0, False)

    def markt_verkauf(self, paar, menge, echt=False):
        self.rufe.append(("verkauf", paar, menge))
        if self.verkauf_fehler:
            raise RuntimeError("EOrder:Insufficient funds")
        return "verkauf-1"

    def stop_setzen(self, paar, menge, preis, echt=False):
        self.rufe.append(("stop", paar, menge, preis))
        if self.stop_fehler:
            raise RuntimeError("EOrder:Invalid price")
        return "stop-1"

    def order_stornieren(self, txid):
        self.rufe.append(("storno", txid))
        if self.storno_fehler:
            raise RuntimeError("EOrder:Order not found")
        return {"count": 1}

    def stop_gefuellt(self, txid):
        self.rufe.append(("stopgefuellt", txid))
        return self.gefuellt_flag

    def namen(self):
        return [r[0] for r in self.rufe]


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.alt = h.JOURNAL
        h.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"
        self.addCleanup(setattr, h, "JOURNAL", self.alt)
        # Auch die BELEGABLAGE zeigt in den Temp-Ordner. Am 29.09.2026
        # fiel auf, dass test_ohne_beleg_kein_kauf einen ECHTEN Beleg
        # fuer die Kraken-Spur nach cache/freigabebelege/ geschrieben
        # hat, weil das Freigabefenster zur Laufzeit zufaellig offen
        # stand - ein Test hat in einem echten Schreibziel nichts zu
        # suchen (Bedingung 4 in AGENTS.md).
        self.alt_cache = h.freigabebeleg.CACHE
        h.freigabebeleg.CACHE = str(Path(self.tmp.name) / "belege")
        self.addCleanup(setattr, h.freigabebeleg, "CACHE",
                        self.alt_cache)

    def _lauf(self, fake, fn):
        """fn() mit Attrappe statt kraken, gestelltem Beleg, abgefangener Ausgabe.

        WARUM der Beleg hier gestubbt wird: `_beleg_zur_order` verlangt ein
        OFFENES Freigabefenster und handel_erlaubt=true. Diese Klasse prueft den
        BOERSENWEG (Fuellung, Stop, Rueckverkauf) - das Tor selbst hat eigene
        Tests (Handel/tests/test_freigabebeleg_tor.py) und hier einen eigenen
        Fall: `test_ohne_beleg_kein_kauf`. Vor dem 24.09.2026 waren diese vier
        Tests rot, weil das Tor gar keinen Beleg ausstellen konnte (Aufruf auf
        dem Modul statt auf dem Fenster).
        """
        puffer = io.StringIO()
        with patch.object(h, "kraken", fake),              patch.object(h, "_beleg_zur_order",
                          return_value={"kennung": "testbeleg"}),              patch.object(h.freigabebeleg, "pruefe",
                          return_value=(True, "ok")),              patch.object(h.freigabebeleg, "verbrauche", return_value=True):
            with patch("sys.stdout", puffer), patch("sys.stderr", puffer):
                fn()
        return puffer.getvalue()


class EinstiegLive(Basis):
    def _einstieg(self, fake):
        z = {"positionen": [], "letzte_stops": {}}
        text = self._lauf(fake, lambda: h.pruefe_einstiege(z, [dict(V)], W, True))
        return text, z

    def test_stop_wird_gesetzt_und_die_nummer_gemerkt(self):
        fake = AttrappeKraken()
        _, z = self._einstieg(fake)
        self.assertIn(("stop", "XLINKZEUR", 4.2, 11.0), fake.rufe)
        self.assertEqual(z["positionen"][0]["stop_txid"], "stop-1")
        self.assertFalse(z["positionen"][0]["boersen_stop_fehlt"])
        self.assertEqual(z["positionen"][0]["menge"], 4.2,
                         "gebucht wird die gefuellte Menge")

    def test_stop_nicht_setzbar_wird_zurueckverkauft(self):
        fake = AttrappeKraken(stop_fehler=True)
        text, z = self._einstieg(fake)
        self.assertEqual(z["positionen"], [], "ohne Stop nicht halten")
        self.assertIn(("verkauf", "XLINKZEUR", 4.2), fake.rufe)
        self.assertIn("zurueckverkauft", text)

    def test_rueckverkauf_fehlt_position_wird_markiert(self):
        fake = AttrappeKraken(stop_fehler=True, verkauf_fehler=True)
        _, z = self._einstieg(fake)
        self.assertEqual(len(z["positionen"]), 1,
                         "eine Position am Markt muss im Buch stehen")
        self.assertTrue(z["positionen"][0]["boersen_stop_fehlt"])
        self.assertIsNone(z["positionen"][0]["stop_txid"])

    def test_kauf_ohne_fuellung_wird_trotzdem_gebucht(self):
        """Aus "noch keine Fuellung" folgt NIE "kein Eintrag".

        Die Order HAT eine Kennung, das Geld ist gebunden. Wird sie nicht
        gebucht, signalisiert die Spur im naechsten Zyklus erneut und kauft
        denselben Wert wieder (T-102, FILEUR viermal). Gebucht wird deshalb die
        BESTELLTE Menge, gekennzeichnet mit fuellung_offen=True.

        Bis zum 01.10.2026 hiess dieser Test `..._wird_nicht_gebucht` und
        verlangte eine leere Positionsliste - er fror den Stand VOR der
        T-102-Regel ein. Die Attrappe kannte `fuellung_abwarten` gar nicht,
        weil sie nie lief.
        """
        fake = AttrappeKraken(fuellung=0)
        text, z = self._einstieg(fake)
        self.assertEqual(len(z["positionen"]), 1,
                         "eine Order mit Kennung muss im Buch stehen")
        self.assertTrue(z["positionen"][0]["fuellung_offen"])
        self.assertAlmostEqual(z["positionen"][0]["menge"], 50.0 / 11.8, places=7,
                               msg="unbestaetigt wird die BESTELLTE Menge gebucht")
        self.assertIn("unbestaetigt", text)

    def test_ohne_beleg_kein_kauf(self):
        """Ohne Beleg gibt es an der Boerse nichts zu tun - kein Kauf, kein Stop."""
        fake = AttrappeKraken()
        z = {"positionen": [], "letzte_stops": {}}
        puffer = io.StringIO()
        # Die Verweigerung wird GESTELLT, nicht dem Systemzustand
        # ueberlassen: ob gerade ein Freigabefenster offen ist, haengt
        # am laufenden Dauerlauf. Bis zum 29.09.2026 stand hier nichts,
        # und der Test war immer dann rot, wenn das Fenster zufaellig
        # offen stand - also genau dann, wenn er gebraucht wird.
        ohne_beleg = patch.object(
            h.freigabebeleg, "schreibe",
            return_value={"ok": False, "grund": "kein Fenster (Test)"})
        with patch.object(h, "kraken", fake), ohne_beleg:
            with patch("sys.stdout", puffer), patch("sys.stderr", puffer):
                h.pruefe_einstiege(z, [dict(V)], W, True)
        self.assertEqual(z["positionen"], [])
        self.assertNotIn("kauf", fake.namen())
        self.assertIn("kein Beleg", puffer.getvalue())


class AusstiegLive(Basis):
    def _ausstieg(self, fake, pos=None, offene_stops=None):
        z = {"positionen": [dict(P if pos is None else pos)],
             "letzte_stops": {}}
        if offene_stops is not None:
            z["offene_stops"] = offene_stops
        text = self._lauf(fake, lambda: h.pruefe_ausstiege(z, W, True))
        return text, z

    def test_ausstieg_storniert_den_stop_vor_dem_verkauf(self):
        fake = AttrappeKraken(kurs=P["ziel"] + 1)
        _, z = self._ausstieg(fake)
        self.assertIn("storno", fake.namen())
        self.assertLess(fake.namen().index("storno"),
                        fake.namen().index("verkauf"),
                        "erst den Stop abbestellen, dann verkaufen")
        self.assertEqual(z["positionen"], [])

    def test_nicht_stornierbarer_stop_haelt_den_verkauf_nicht_auf(self):
        fake = AttrappeKraken(kurs=P["ziel"] + 1, storno_fehler=True)
        _, z = self._ausstieg(fake)
        self.assertIn("verkauf", fake.namen())
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(z["offene_stops"]), 1,
                         "der offene Stop wird gemerkt")
        self.assertEqual(z["offene_stops"][0]["stop_txid"], "stop-1")

    def test_ausgeloester_boersenstop_raeumt_die_position_weg(self):
        fake = AttrappeKraken(kurs=P["ziel"] + 1, storno_fehler=True,
                              stop_gefuellt=True)
        text, z = self._ausstieg(fake)
        self.assertNotIn("verkauf", fake.namen(),
                         "der Stop hat schon verkauft - kein zweiter Verkauf")
        self.assertEqual(z["positionen"], [], "keine Karteileiche im Buch")
        self.assertIn("stop (boerse)", text)
        self.assertEqual(z["letzte_stops"][P["paar"]], h._heute())

    def test_verkauf_fehlt_ohne_boersenstop_position_bleibt(self):
        fake = AttrappeKraken(kurs=P["ziel"] + 1, verkauf_fehler=True)
        _, z = self._ausstieg(fake)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertIsNone(z.get("offene_stops"))

    def test_notausstieg_storniert_den_stop(self):
        fake = AttrappeKraken()
        z = {"positionen": [dict(P)], "letzte_stops": {}}
        self._lauf(fake, lambda: h.flach_stellen(z, W, True, "herzschlag_alt"))
        self.assertEqual(z["positionen"], [])
        self.assertIn("storno", fake.namen())

    def test_offene_stops_werden_beim_naechsten_lauf_storniert(self):
        fake = AttrappeKraken()
        z = {"positionen": [], "letzte_stops": {},
             "offene_stops": [{"paar": "XLINKZEUR", "stop_txid": "stop-9",
                               "seit": "2026-09-14"}]}
        text = self._lauf(fake, lambda: h.pruefe_ausstiege(z, W, True))
        self.assertIn(("storno", "stop-9"), fake.rufe)
        self.assertEqual(z["offene_stops"], [])
        self.assertIn("storniert", text)

    def test_offener_stop_bleibt_wenn_er_nicht_weggeht(self):
        fake = AttrappeKraken(storno_fehler=True)
        z = {"positionen": [], "letzte_stops": {},
             "offene_stops": [{"paar": "XLINKZEUR", "stop_txid": "stop-9",
                               "seit": "2026-09-14"}]}
        self._lauf(fake, lambda: h.pruefe_ausstiege(z, W, True))
        self.assertEqual(len(z["offene_stops"]), 1,
                         "was nicht weggeht, bleibt gemerkt")


if __name__ == "__main__":
    unittest.main()
