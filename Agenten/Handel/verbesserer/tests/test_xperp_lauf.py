import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import mkdtemp
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import xperp_lauf as lauf  # noqa: E402
import xperp_suche as xs  # noqa: E402

S = lauf.rt.SCHRITT_MS
TAG = 86_400_000
ENDE = 1000 * TAG
JETZT = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
SPUR = json.loads((WURZEL / "spuren.json").read_text("utf-8"))["spur2"]
KONF = dict(json.loads((WURZEL / "konfig.json").read_text("utf-8"))["spur2"])
ECHTE_WACHE = WURZEL.parent / "xperp" / "wachen.json"
UNI = [{"instId": "%s-X" % c, "basis": c, "kategorie": "krypto"}
       for c in "ABC"]
BASIS_W = {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
           "einstieg_atr_abschlag": 0.25, "trailing_trigger_r": 1.0,
           "trailing_stop_prozent": 0.4, "trailing_abstand_floor_pct": 0.25,
           "trailing_min_hub_r": 0.25, "trailing_max_halten_pct": 5.0,
           "trailing_aktiv": True}


def _runde(ts, gv, grund="ziel"):
    return {"geschlossen_ts": ts, "gv": gv, "grund": grund,
            "kategorie": "krypto", "funding_summe": 0.0}


def _sim_besser_bei_engem_stop(w, von, bis):
    """Je Fenster 8 Runden; ein engerer Stop (<= 1.25) ist klar besser."""
    gv = 3.0 if w["stop_atr_faktor"] <= 1.25 else 1.0
    return [_runde(von + i + 1, gv) for i in range(8)]


def _daten(_universum, _tage, _holen, _dir):
    k = {u["instId"]: [[ENDE - 10 * S, 1, 1, 1, 1, 1], [ENDE, 1, 1, 1, 1, 1]]
         for u in UNI}
    return k, dict(k), dict(k), {u["instId"]: [[0, 0.0]] for u in UNI}, []


class Basis(unittest.TestCase):
    def setUp(self):
        self.dir = Path(mkdtemp())
        self.berichte = self.dir / "berichte"
        self.wachen = self.dir / "wachen.json"
        self.wachen.write_text(ECHTE_WACHE.read_text("utf-8"), "utf-8",
                               newline="")
        for p in (
                mock.patch.object(lauf.xk, "laden_universum",
                                  return_value=UNI),
                mock.patch.object(lauf, "_daten_laden", side_effect=_daten),
                mock.patch.object(lauf, "_instrumente",
                                  return_value={"A": {"ctVal": "1"},
                                                "B": {"ctVal": "1"},
                                                "C": {"ctVal": "1"}}),
                mock.patch.object(lauf.xm, "hole_oder_baue",
                                  side_effect=lambda pfad, u, k4, k1d, ct,
                                  st: ({s: [] for s in st}, False)),
                mock.patch.object(lauf.rt, "simuliere",
                                  side_effect=lambda *a, **k:
                                  _sim_besser_bei_engem_stop(a[7], a[8], a[9])
                                  )):
            p.start()
            self.addCleanup(p.stop)

    def einmal(self, **kw):
        args = dict(kerzen_holen=False, jetzt=JETZT, konf=dict(KONF),
                    spur=SPUR, basis_w=dict(BASIS_W),
                    wachen_pfad=self.wachen, berichte=self.berichte,
                    cache_dir=self.dir / "cache",
                    merkmale_pfad=self.dir / "m.json",
                    zaehler_pfad=self.dir / "z.json")
        args.update(kw)
        return lauf.einmal(**args)


class TestVorschlag(Basis):
    def test_vorschlag_schreibt_die_drei_dateien(self):
        ordner, status = self.einmal()
        self.assertEqual(status, "vorschlag")
        self.assertEqual(ordner.name, "2026-10-12-spur2")
        for name in ("bericht.md", "wachen.neu.json", "commit.txt"):
            self.assertTrue((ordner / name).is_file(), name)

    def test_commit_txt_ist_fuer_telegram_lesbar(self):
        ordner, _ = self.einmal()
        text = (ordner / "commit.txt").read_text("utf-8")
        self.assertTrue(text.startswith("verbesserer: spur2"))
        self.assertIn("Geaenderte Schluessel:", text)
        self.assertIn("stop_atr_faktor", text)
        self.assertIn("OOS netto_gv_je_runde:", text)
        self.assertIn("Co-Authored-By: Claude Sonnet 5.5", text)

    def test_wachen_neu_aendert_nur_die_gefundenen_schluessel(self):
        # Review Focus 5 (echte Wache, Rohtext-Ersetzung)
        ordner, _ = self.einmal()
        alt = json.loads(self.wachen.read_text("utf-8"))
        neu = json.loads((ordner / "wachen.neu.json").read_text("utf-8"))
        diff = {k for k in set(alt) | set(neu) if alt.get(k) != neu.get(k)}
        self.assertTrue(diff)
        self.assertLessEqual(diff, set(xs.SCHRITT))
        self.assertIn("stop_atr_faktor", diff)

    def test_bericht_zeigt_fenster_regeln_holdout_und_nicht_geprueft(self):
        ordner, _ = self.einmal()
        b = (ordner / "bericht.md").read_text("utf-8")
        for stichwort in ("Fenster", "Siebregeln", "Holdout",
                          "Nicht geprueft", "Holdout-Nutzung: 1 von 8"):
            self.assertIn(stichwort, b)

    def test_holdout_zaehler_steigt_nur_wenn_der_holdout_lief(self):
        self.einmal()
        self.assertEqual(lauf.zaehler_lesen(self.dir / "z.json"), 1)
        self.einmal()
        self.assertEqual(lauf.zaehler_lesen(self.dir / "z.json"), 2)

    def test_verbrauchter_holdout_wird_im_bericht_gemeldet(self):
        konf = {**KONF, "holdout_max_nutzungen": 1}
        self.einmal(konf=konf)
        ordner, _ = self.einmal(konf=konf)
        self.assertIn("verbraucht",
                      (ordner / "bericht.md").read_text("utf-8"))

    def test_zweiter_lauf_am_selben_tag_raeumt_altlasten(self):
        ordner, _ = self.einmal()
        (ordner / "alt.txt").write_text("x", "utf-8")
        ordner2, _ = self.einmal()
        self.assertEqual(ordner, ordner2)
        self.assertFalse((ordner2 / "alt.txt").exists())


class TestKeinVorschlag(Basis):
    def test_ohne_verbesserung_kein_commit_txt(self):
        with mock.patch.object(
                lauf.rt, "simuliere",
                side_effect=lambda *a, **k: [_runde(a[8] + 1, 1.0)] * 8):
            ordner, status = self.einmal()
        self.assertEqual(status, "kein_vorschlag")
        self.assertFalse((ordner / "commit.txt").exists())
        self.assertIn("kein besserer Kandidat",
                      (ordner / "bericht.md").read_text("utf-8"))

    def test_zu_wenig_historie_fuer_die_fenster(self):
        # Review Focus 4
        konf = {**KONF, "such_tage": 30}
        ordner, status = self.einmal(konf=konf)
        self.assertEqual(status, "kein_vorschlag")
        self.assertIn("zu wenig Historie",
                      (ordner / "bericht.md").read_text("utf-8"))
        self.assertFalse((ordner / "commit.txt").exists())


class TestAbbruch(Basis):
    def test_kein_universum_cache(self):
        # Review Focus 2
        with mock.patch.object(lauf.xk, "laden_universum", return_value=[]):
            ordner, status = self.einmal()
        self.assertEqual(status, "abbruch")
        self.assertIn("Universum", (ordner / "bericht.md").read_text("utf-8"))
        self.assertFalse((ordner / "commit.txt").exists())

    def test_zu_wenige_instrumente_mit_vollstaendigem_cache(self):
        def daten(u, t, h, d):
            k = {"A-X": [[ENDE, 1, 1, 1, 1, 1]]}
            return k, dict(k), dict(k), {"A-X": [[0, 0.0]]}, ["B-X", "C-X"]
        with mock.patch.object(lauf, "_daten_laden", side_effect=daten):
            ordner, status = self.einmal()
        self.assertEqual(status, "abbruch")
        b = (ordner / "bericht.md").read_text("utf-8")
        self.assertIn("B-X", b)
        self.assertFalse((ordner / "commit.txt").exists())

    def test_ausgelassene_instrumente_stehen_im_bericht(self):
        def daten(u, t, h, d):
            k, k1h, k1d, s, _ = _daten(u, t, h, d)
            return k, k1h, k1d, s, ["Z-X"]
        with mock.patch.object(lauf, "_daten_laden", side_effect=daten):
            ordner, status = self.einmal()
        self.assertEqual(status, "vorschlag")
        self.assertIn("Z-X", (ordner / "bericht.md").read_text("utf-8"))

    def test_funding_luecke_bricht_ab_ohne_vorschlag(self):
        # Review Focus 3
        def sim(*a, **k):
            raise lauf.rt.FundingLuecke("kein Funding-Satz vor 123")
        with mock.patch.object(lauf.rt, "simuliere", side_effect=sim):
            ordner, status = self.einmal()
        self.assertEqual(status, "abbruch")
        b = (ordner / "bericht.md").read_text("utf-8")
        self.assertIn("kein Funding-Satz vor 123", b)
        self.assertFalse((ordner / "commit.txt").exists())
        self.assertFalse((ordner / "wachen.neu.json").exists())

    def test_okx_instrumente_nicht_abrufbar(self):
        with mock.patch.object(lauf, "_instrumente",
                               side_effect=OSError("offline")):
            ordner, status = self.einmal()
        self.assertEqual(status, "abbruch")
        self.assertIn("offline", (ordner / "bericht.md").read_text("utf-8"))


class TestUniversumAuffrischen(Basis):
    def test_mit_abruf_wird_das_universum_geholt(self):
        with mock.patch.object(lauf.xk, "hole_universum",
                               return_value=UNI) as h:
            self.einmal(kerzen_holen=True)
        h.assert_called_once()

    def test_ohne_abruf_wird_nichts_geholt(self):
        with mock.patch.object(lauf.xk, "hole_universum") as h:
            self.einmal(kerzen_holen=False)
        h.assert_not_called()

    def test_fehlgeschlagener_abruf_faellt_auf_den_cache_zurueck(self):
        with mock.patch.object(lauf.xk, "hole_universum",
                               side_effect=OSError("offline")):
            _, status = self.einmal(kerzen_holen=True)
        self.assertEqual(status, "vorschlag")

    def test_abbruchmeldung_nennt_keine_wirkungslose_abhilfe(self):
        with mock.patch.object(lauf.xk, "laden_universum", return_value=[]):
            ordner, _ = self.einmal()
        b = (ordner / "bericht.md").read_text("utf-8")
        self.assertIn("Universum", b)
        self.assertNotIn("ohne --ohne-kerzen-abruf", b)


class TestBasisPruefsumme(Basis):
    def test_lauf_schreibt_die_pruefsumme_der_wache(self):
        import hashlib
        ordner, _ = self.einmal()
        self.assertEqual(
            (ordner / "basis.sha256").read_text("utf-8").strip(),
            hashlib.sha256(self.wachen.read_bytes()).hexdigest())

    def test_kein_vorschlag_schreibt_keine_pruefsumme(self):
        with mock.patch.object(
                lauf.rt, "simuliere",
                side_effect=lambda *a, **k: [_runde(a[8] + 1, 1.0)] * 8):
            ordner, _ = self.einmal()
        self.assertFalse((ordner / "basis.sha256").exists())


class TestFundingAbdeckung(Basis):
    """OKX liefert Funding-Historie nur ca. 3 Monate zurueck: ein Instrument,
    dessen erster Satz nach dem Simulationsstart liegt, wuerde mitten im Lauf
    eine FundingLuecke werfen (echter Befund aus Task 7)."""

    def test_filter_laesst_nur_ausreichende_historie_durch(self):
        uni = [{"instId": "A-X"}, {"instId": "B-X"}, {"instId": "C-X"}]
        saetze = {"A-X": [[100, 0.0], [900, 0.0]], "B-X": [[500, 0.0]],
                  "C-X": []}
        bleibt, fehlt = lauf.mit_funding_ab(uni, saetze, 200)
        self.assertEqual([x["instId"] for x in bleibt], ["A-X"])
        self.assertEqual(fehlt, ["B-X", "C-X"])

    def test_genau_am_start_reicht(self):
        bleibt, fehlt = lauf.mit_funding_ab(
            [{"instId": "A-X"}], {"A-X": [[200, 0.0]]}, 200)
        self.assertEqual(len(bleibt), 1)
        self.assertEqual(fehlt, [])

    def test_lauf_laesst_spaetes_funding_aus_und_nennt_es(self):
        uni4 = UNI + [{"instId": "D-X", "basis": "D", "kategorie": "krypto"}]

        def daten(u, t, h, d):
            k, k1h, k1d, s, fehlt = _daten(u, t, h, d)
            for z in (k, k1h, k1d):
                z["D-X"] = z["A-X"]
            s["D-X"] = [[ENDE, 0.0]]            # beginnt erst am Ende
            return k, k1h, k1d, s, fehlt

        with mock.patch.object(lauf.xk, "laden_universum",
                               return_value=uni4),                 mock.patch.object(lauf, "_daten_laden", side_effect=daten):
            ordner, status = self.einmal()
        self.assertEqual(status, "vorschlag")
        b = (ordner / "bericht.md").read_text("utf-8")
        self.assertIn("D-X", b)
        self.assertIn("Funding", b)

    def test_zu_wenige_instrumente_mit_funding_bricht_ab(self):
        def daten(u, t, h, d):
            k, k1h, k1d, s, fehlt = _daten(u, t, h, d)
            s["B-X"] = [[ENDE, 0.0]]
            s["C-X"] = [[ENDE, 0.0]]
            return k, k1h, k1d, s, fehlt

        with mock.patch.object(lauf, "_daten_laden", side_effect=daten):
            ordner, status = self.einmal()
        self.assertEqual(status, "abbruch")
        self.assertIn("Funding", (ordner / "bericht.md").read_text("utf-8"))
        self.assertFalse((ordner / "commit.txt").exists())


class TestZaehler(unittest.TestCase):
    def test_lesen_ohne_datei_und_mit_kaputter_datei(self):
        d = Path(mkdtemp())
        self.assertEqual(lauf.zaehler_lesen(d / "z.json"), 0)
        (d / "z.json").write_text("{kaputt", "utf-8")
        self.assertEqual(lauf.zaehler_lesen(d / "z.json"), 0)

    def test_erhoehen(self):
        d = Path(mkdtemp()) / "z.json"
        self.assertEqual(lauf.zaehler_erhoehen(d, "2026-10-12"), 1)
        self.assertEqual(lauf.zaehler_erhoehen(d, "2026-10-19"), 2)
        self.assertEqual(lauf.zaehler_lesen(d), 2)


if __name__ == "__main__":
    unittest.main()
