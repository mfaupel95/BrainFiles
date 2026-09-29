"""Freigaben-Reiter: Ja/Ablehnen nur bei wartender Anfrage, verfallene Anfrage
und Zeitablauf schreiben nichts, Notaus schliesst alles - auch bei belegter
Sperre ohne Absturz.

freigabefenster.DATEI zeigt auf einen Temp-Ordner. Die Dialoge werden durch
Attrappen ersetzt, die ein festes Ergebnis liefern; der echte Dialog wird
einzeln auf den Zeitablauf geprueft.

Direkt ausfuehrbar:  python tests/test_leitstand_freigaben.py
"""

import datetime as dt
import json
import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import freigabefenster as ff                                   # noqa: E402
import leitstand_bedienung as lb                               # noqa: E402
import leitstand_freigaben as lf                               # noqa: E402


class StubLeitstand:
    def __init__(self, root, zustand):
        self.root, self.zustand, self.meldungen = root, zustand, []

    def melde(self, text):
        self.meldungen.append(text)


def attrappe(ergebnis):
    class Dialog:
        aufrufe = []

        def __init__(self, eltern, spur, grenzen, stunden, **kw):
            Dialog.aufrufe.append((spur, grenzen, stunden))

        def zeige_modal(self):
            return ergebnis
    return Dialog


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(ff, "DATEI",
                         os.path.join(self.tmp.name, "freigabe_fenster.json"))
        p.start()
        self.addCleanup(p.stop)

    def _roh(self):
        try:
            with open(ff.DATEI, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _verfallene_anfrage(self, spur="xperp"):
        ff.anfrage_stellen(spur, 60)
        d = json.loads(self._roh())
        d[spur]["anfrage_bis"] = (ff._jetzt() - dt.timedelta(minutes=1)).isoformat()
        with open(ff.DATEI, "w", encoding="utf-8") as f:
            json.dump(d, f)


class Aktionen(Basis):
    def test_freigeben_bei_wartender_anfrage(self):
        ff.anfrage_stellen("xperp", 90)
        self.assertEqual(lf.freigeben("xperp", 6), "xperp scharf für 6:00 h")
        f = ff.lade("xperp")
        self.assertTrue(f.offen())
        self.assertEqual(f.d["freigegeben_von"], "leitstand")

    def test_freigeben_ohne_anfrage_schreibt_nichts(self):
        self.assertEqual(lf.freigeben("xperp", 6),
                         "Anfrage war verfallen — nichts geändert")
        self.assertIsNone(self._roh())

    def test_verfallene_anfrage_schreibt_nichts(self):
        self._verfallene_anfrage()
        vorher = self._roh()
        self.assertIn("verfallen", lf.freigeben("xperp", 2))
        self.assertIn("keine wartende Anfrage", lf.ablehnen("xperp"))
        self.assertEqual(self._roh(), vorher)

    def test_ablehnen_setzt_wiedervorlage_grund(self):
        ff.anfrage_stellen("xperp", 60)
        self.assertIn("abgelehnt", lf.ablehnen("xperp"))
        d = ff.lade("xperp").d
        self.assertEqual(d["schliess_grund"], "abgelehnt (Leitstand)")
        self.assertNotIn("anfrage_bis", d)

    def test_schliessen(self):
        ff.anfrage_stellen("xperp", 60)
        ff.oeffnen("xperp", 2, wer="test")
        self.assertEqual(lf.schliessen("xperp"), "xperp zurück auf Papier")
        self.assertFalse(ff.lade("xperp").offen())
        self.assertEqual(ff.lade("xperp").d["schliess_grund"], "von Hand (Leitstand)")

    def test_notaus_schliesst_alle(self):
        for s in ("xperp", "scanner"):
            ff.anfrage_stellen(s, 60)
            ff.oeffnen(s, 2, wer="test")
        ff.anfrage_stellen("orb", 60)
        meldung = lf.notaus()
        self.assertIn("scanner", meldung)
        self.assertIn("xperp", meldung)
        for s, f in ff.alle().items():
            self.assertFalse(f.offen(), s)
            self.assertFalse(f.anfrage_offen(), s)
            self.assertEqual(f.d["schliess_grund"], "Notaus (Leitstand)")

    def test_notaus_haelt_kaputten_eintrag_aus(self):
        ff.anfrage_stellen("xperp", 60)
        ff.oeffnen("xperp", 2, wer="test")
        d = json.loads(self._roh())
        d["scanner"] = "kaputt"
        with open(ff.DATEI, "w", encoding="utf-8") as f:
            json.dump(d, f)
        self.assertIn("xperp", lf.notaus())
        self.assertFalse(ff.lade("xperp").offen())

    def test_beliebige_ausnahme_wird_zur_meldung(self):
        with patch.object(ff, "alles_schliessen", side_effect=OSError("platte")):
            self.assertTrue(lf.notaus().startswith("Notaus NICHT ausgeführt"))
        with patch.object(ff, "lade", side_effect=OSError("platte")):
            self.assertIn("NICHT ausgeführt", lf.ablehnen("xperp"))
        with patch.object(ff, "schliessen", side_effect=ValueError("x")):
            self.assertIn("NICHT ausgeführt", lf.schliessen("xperp"))
        with patch.object(ff, "oeffnen", side_effect=ValueError("x")):
            self.assertIn("NICHT ausgeführt", lf.freigeben("xperp", 1))

    def test_notaus_bei_belegter_sperre_meldet_und_schreibt_nichts(self):
        ff.anfrage_stellen("xperp", 60)
        ff.oeffnen("xperp", 2, wer="test")
        vorher = self._roh()
        open(ff.DATEI + ".lock", "w").close()
        with patch.object(ff, "SPERRE_WARTEN_S", 0.2):
            self.assertEqual(lf.notaus(), lf.SPERRE_BELEGT)
            self.assertEqual(lf.freigeben("xperp", 1), lf.SPERRE_BELEGT)
        self.assertEqual(self._roh(), vorher)


class Anzeige(Basis):
    def test_spuren_ohne_eintrag_stehen_als_papier_da(self):
        ff.anfrage_stellen("xperp", 60)
        z = {r[0]: r for r in lf.zeilen(ff.alle())}
        self.assertEqual(z["xperp"][1], "Anfrage laeuft, unbeantwortet")
        self.assertRegex(z["xperp"][2], r"^\d+ min$")
        self.assertEqual(z["scanner"][1], "Papier")
        self.assertEqual(z["scanner"][7], "ja")         # AUTO_FREIGABE

    def test_kaputter_eintrag_wird_uebersprungen(self):
        with open(ff.DATEI, "w", encoding="utf-8") as f:
            json.dump({"xperp": "kaputt"}, f)
        z = {r[0]: r for r in lf.zeilen(ff.alle())}
        self.assertEqual(z["xperp"][1], "Papier")

    def test_knoepfe(self):
        self.assertFalse(lf.knopf_zustand(None)["freigeben"][0])
        ff.anfrage_stellen("xperp", 60)
        k = lf.knopf_zustand(ff.lade("xperp"))
        self.assertEqual(k["freigeben"], (True, ""))
        self.assertEqual(k["schliessen"], (False, "Spur ist nicht scharf"))
        self.assertEqual(lf.knopf_zustand(ff.lade("orb"))["ablehnen"],
                         (False, "keine wartende Anfrage"))

    def test_vorbelegte_stunden(self):
        self.assertEqual(lf.vorbelegte_stunden(ff.Fenster("x", {"anfrage_dauer_minuten": 90})), 2)
        self.assertEqual(lf.vorbelegte_stunden(ff.Fenster("x", {})), 1)
        self.assertEqual(lf.vorbelegte_stunden(ff.Fenster("x", {"anfrage_dauer_minuten": 9000})), 24)

    def test_neue_anfrage_blinkt_nur_einmal(self):
        ff.anfrage_stellen("xperp", 60)
        neu, gesehen = lf.neue_anfragen(set(), ff.alle())
        self.assertEqual(len(neu), 1)
        neu, gesehen = lf.neue_anfragen(gesehen, ff.alle())
        self.assertEqual(neu, set())

    def test_grenzen_einer_spur(self):
        ordner = Path(self.tmp.name) / "xperp"
        ordner.mkdir()
        (ordner / "wachen.json").write_text(json.dumps({"max_pro_trade_usd": 50}),
                                            encoding="utf-8")
        with patch.object(lf, "HIER", Path(self.tmp.name)):
            self.assertEqual(lf.grenz_zeilen("xperp"), [("je Anlauf", "50 USD")])
            self.assertEqual(lf.grenz_zeilen("scanner"),
                             [("wachen.json", "nicht lesbar")])


class Reiter(Basis):
    def setUp(self):
        super().setUp()
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.ls = StubLeitstand(self.root, lb.Zustand(
            Path(self.tmp.name) / "z.json", lambda: 0.0))
        p = patch.object(lf, "blinken", return_value=True)
        self.blinken = p.start()
        self.addCleanup(p.stop)

    def _reiter(self, ergebnis, frage=True):
        r = lf.FreigabenReiter(self.root, self.ls, dialog=attrappe(ergebnis),
                               frage=lambda *a, **k: frage)
        r._waehle = lambda spur: r.tabelle.baum.selection_set(
            [i for i in r.tabelle.baum.get_children()
             if r.tabelle.baum.item(i, "values")[0] == spur])
        return r

    def test_zeitablauf_schreibt_nichts(self):
        ff.anfrage_stellen("xperp", 60)
        vorher = self._roh()
        r = self._reiter("zeitablauf")
        r._waehle("xperp")
        r.freigeben_klick()
        self.assertEqual(self._roh(), vorher)
        self.assertIn("nichts geändert", self.ls.meldungen[-1])

    def test_ja_im_dialog_gibt_frei(self):
        ff.anfrage_stellen("xperp", 60)
        r = self._reiter(("ja", 3))
        r._waehle("xperp")
        r.freigeben_klick()
        self.assertEqual(self.ls.meldungen[-1], "xperp scharf für 3:00 h")

    def test_freigeben_ohne_anfrage_oeffnet_keinen_dialog(self):
        r = self._reiter(("ja", 3))
        r._waehle("xperp")
        r.freigeben_klick()
        self.assertIsNone(self._roh())

    def test_titel_zaehlt_wartende_und_blinkt(self):
        ff.anfrage_stellen("xperp", 60)
        r = self._reiter("abgebrochen")
        self.assertEqual(r.titel_zusatz(), " (1)")
        self.blinken.assert_called_once()
        r.refresh()
        self.blinken.assert_called_once()

    def test_notaus_nur_nach_rueckfrage(self):
        ff.anfrage_stellen("xperp", 60)
        vorher = self._roh()
        self._reiter("abgebrochen", frage=False).notaus_klick()
        self.assertEqual(self._roh(), vorher)

    def test_notaus_rueckfrage_hat_nein_als_vorgabe(self):
        aufrufe = []
        r = lf.FreigabenReiter(self.root, self.ls, dialog=attrappe("abgebrochen"),
                               frage=lambda *a, **k: aufrufe.append(k) or False)
        r.notaus_klick()
        self.assertEqual(aufrufe[0].get("default"), "no")

    def test_echter_dialog_laeuft_ab(self):
        uhr = [0.0]
        d = lf.FreigabeDialog(self.root, "xperp", [("je Anlauf", "50 USD")], 2,
                              uhr=lambda: uhr[0])
        self.assertEqual(d.w_stunden.get(), 2)
        uhr[0] = 121.0
        d._takt()
        self.assertEqual(d.ergebnis, "zeitablauf")


if __name__ == "__main__":
    unittest.main()
