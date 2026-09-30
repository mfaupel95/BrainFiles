"""Tests fuer das Scharfschalten-Fenster: die Regeln und die Bedienung.

Zwei Ebenen:

* `plan_bauen` ist eine reine Funktion - hier stehen die REGELN (Herzschlag
  zuerst, Haken nur auf Ankreuzen, Tippen nur wenn wirklich geordert werden
  kann).
* Die Fenster selbst werden gebaut und bedient, aber unsichtbar (`withdraw`),
  und mit einem `ausfuehren`, das NUR mitschreibt. Kein Test schreibt in eine
  echte Wachen-Datei.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import handelstand  # noqa: E402
import schalter  # noqa: E402

try:
    import tkinter as tk

    _r = tk.Tk()
    _r.destroy()
    TK_DA = True
except Exception:  # pragma: no cover
    TK_DA = False

STAND_PAPIER = {"spur": "klassik_sma", "erlaubt": False, "frei": False, "order": [],
                "art": None, "auto": False, "fenster": "-", "buch": {}, "scharf": False}
STAND_HAUS = {"spur": "mosaic", "erlaubt": False, "frei": False,
              "order": ["kraken_spot.py"], "art": "haus", "auto": True, "fenster": "-",
              "buch": {}, "scharf": False}
WACHEN_180 = {"herzschlag_max_minuten": 180, "max_pro_trade_usd": 100}

# Dieselben Farbtokens wie fenster_design.FARBEN - die Fenster lesen sie ueber
# den Aufrufer, hier steht nur, was sie wirklich anfassen.
FARBEN = {"bg": "#1e1e2e", "blatt": "#181825", "gitter": "#313244",
          "text": "#cdd6f4", "matt": "#a6adc8", "akzent": "#89b4fa",
          "gruen": "#a6e3a1", "rot": "#f38ba8", "gelb": "#f9e2af",
          "zellgruen": "#1b4d3e", "zellrot": "#5c1f2b", "auswahl": "#45475a"}
WACHEN_45 = {"herzschlag_max_minuten": 45, "max_pro_trade_usd": 100}


class PlanTest(unittest.TestCase):
    def test_papierspur_ohne_orderweg_braucht_nur_den_haken(self):
        plan = schalter.plan_bauen("klassik_sma", WACHEN_180, STAND_PAPIER,
                                   herzschlag=False, freigabe=False)
        self.assertEqual(plan.aenderungen, {"handel_erlaubt": True})
        self.assertEqual(plan.bestaetigung, schalter.HAKEN)

    def test_herzschlag_unter_180_wird_mitgesetzt(self):
        plan = schalter.plan_bauen("klassik_sma", WACHEN_45, STAND_PAPIER,
                                   herzschlag=True, freigabe=False)
        self.assertEqual(plan.aenderungen["herzschlag_max_minuten"],
                         handelstand.HERZSCHLAG_LIVE)

    def test_fehlender_herzschlag_wird_gesetzt(self):
        plan = schalter.plan_bauen("klassik_sma", {}, STAND_PAPIER,
                                   herzschlag=False, freigabe=False)
        self.assertIn("herzschlag_max_minuten", plan.aenderungen)

    def test_wer_ordern_kann_muss_tippen(self):
        plan = schalter.plan_bauen("mosaic", WACHEN_180, STAND_HAUS,
                                   herzschlag=False, freigabe=True)
        self.assertEqual(plan.bestaetigung, schalter.TIPPEN)
        self.assertIn("freigabe.erfuellt ist true", plan.wirkung)
        self.assertIn("AUTO_FREIGABE", plan.wirkung)

    def test_ohne_haken_bleibt_es_beim_haken(self):
        """Orderweg ja, aber freigabe.erfuellt false - es kann nichts geordert werden."""
        plan = schalter.plan_bauen("mosaic", WACHEN_180, STAND_HAUS,
                                   herzschlag=False, freigabe=False)
        self.assertEqual(plan.bestaetigung, schalter.HAKEN)
        self.assertIn("nichts geordert", plan.wirkung)

    def test_freigabe_none_fasst_den_haken_nicht_an(self):
        plan = schalter.plan_bauen("mosaic", WACHEN_180, STAND_HAUS,
                                   herzschlag=False, freigabe=None)
        self.assertNotIn("freigabe.erfuellt", plan.aenderungen)

    def test_haken_wird_nur_bei_abweichung_geschrieben(self):
        stand = dict(STAND_HAUS, frei=True)
        plan = schalter.plan_bauen("mosaic", WACHEN_180, stand,
                                   herzschlag=False, freigabe=True)
        self.assertNotIn("freigabe.erfuellt", plan.aenderungen)

    def test_nichts_zu_tun(self):
        stand = dict(STAND_HAUS, erlaubt=True, frei=True)
        plan = schalter.plan_bauen("mosaic", WACHEN_180, stand,
                                   herzschlag=False, freigabe=True)
        self.assertFalse(plan.etwas_zu_tun)
        self.assertEqual(plan.bestaetigung, schalter.NICHTS)

    def test_entschaerfen_setzt_nur_den_schalter(self):
        plan = schalter.plan_bauen("mosaic", WACHEN_180,
                                   dict(STAND_HAUS, erlaubt=True, frei=True),
                                   herzschlag=False, freigabe=None, entschaerfen=True)
        self.assertEqual(plan.aenderungen, {"handel_erlaubt": False})
        self.assertIn("handelt nicht mehr", plan.wirkung)
        self.assertIn("Entschaerfen", plan.titel)


@unittest.skipUnless(TK_DA, "kein Fenstersystem verfuegbar")
class FensterTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.gerufen = []

    def tearDown(self):
        self.root.destroy()

    def _ausfuehren(self, spur, aenderungen, vermerk):
        self.gerufen.append((spur, dict(aenderungen), vermerk))

        class E:
            ok = True
            geaendert = [f"{k} gesetzt" for k in aenderungen]
            sicherung = None
            fehler = ""

        return E()

    def _fenster(self, spur="mosaic", stand=None, wachen=None):
        f = schalter.ScharfFenster(
            self.root, spur=spur, wachen=wachen or WACHEN_180,
            stand=stand or STAND_HAUS, farben=FARBEN,
            schrift_tupel=("Consolas", 11), radius=9, s=1.0,
            ausfuehren=self._ausfuehren, jetzt=None,
        )
        f.withdraw()
        f.update()
        return f

    def test_knopf_ist_aus_bis_bestaetigt(self):
        f = self._fenster()
        self.assertFalse(f.knopf_an.aktiv)
        f.gelesen.set(True)
        f._neu_rechnen()
        self.assertTrue(f.knopf_an.aktiv)
        f.destroy()

    def test_tippen_muss_genau_stimmen(self):
        f = self._fenster()
        f.freigabe.set(True)
        f._neu_rechnen()
        f.update()
        self.assertEqual(f.best_tipp.winfo_manager(), "pack")
        f.tipptext.set("mosa")
        f._neu_rechnen()
        self.assertFalse(f.knopf_an.aktiv)
        f.tipptext.set("  MOSAIC  ")
        f._neu_rechnen()
        self.assertTrue(f.knopf_an.aktiv, "Gross-/Kleinschreibung und Leerzeichen egal")
        f.destroy()

    def test_anwenden_ruft_ausfuehren_mit_dem_plan(self):
        f = self._fenster()
        f.gelesen.set(True)
        f._neu_rechnen()
        f._anwenden()
        f.update()
        self.assertEqual(len(self.gerufen), 1)
        spur, aenderungen, _ = self.gerufen[0]
        self.assertEqual(spur, "mosaic")
        self.assertEqual(aenderungen, {"handel_erlaubt": True})
        self.assertIn("Geschrieben", f.text.get("1.0", "end"))
        f.destroy()

    def test_ohne_bestaetigung_wird_nicht_ausgefuehrt(self):
        f = self._fenster()
        f._anwenden()
        self.assertEqual(self.gerufen, [])
        f.destroy()

    def test_die_checkliste_steht_im_fenster(self):
        f = self._fenster(wachen=WACHEN_45)
        text = f.text.get("1.0", "end")
        for erwartet in ("Herzschlag", "Orderweg", "freigabe.erfuellt", "Deckel"):
            self.assertIn(erwartet, text)
        f.destroy()

    def test_entschaerfen_fenster_verlangt_den_haken(self):
        f = schalter.EntschaerfenFenster(
            self.root, spur="mosaic", farben=FARBEN,
            schrift_tupel=("Consolas", 11), radius=9, s=1.0,
            ausfuehren=self._ausfuehren, jetzt=None,
        )
        f.withdraw()
        f.update()
        self.assertFalse(f.knopf_an.aktiv)
        f._anwenden()
        self.assertEqual(self.gerufen, [])
        f.gelesen.set(True)
        f.knopf_an.setze_aktiv(True)
        f._anwenden()
        self.assertEqual(self.gerufen[0][1], {"handel_erlaubt": False})
        f.destroy()


if __name__ == "__main__":
    unittest.main()