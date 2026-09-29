"""Tests fuer den Sammler der Backtest-Urteile.

Geprueft werden die zwei Teile, die still schiefgehen koennen:
  - die URTEILE der Motoren aus ihrer Ausgabe lesen (drei verschiedene Formen),
  - die drei Felder in eine `wachen.json` schreiben, ohne etwas anderes zu
    veraendern - und ohne je `handel_erlaubt` oder `freigabe.erfuellt` anzufassen.

Kein Netz, kein Motor: `motor_laufen` wird ersetzt, gearbeitet wird in einem
Temp-Ordner (Modulvariable HIER). Die Wachen sind FIXTURES, keine Kopien der
echten Werte - ein Test, der auf den heutigen Stand baut, bricht beim ersten
umgelegten Schalter.

Direkt ausfuehrbar:  python tests/test_backtest_urteile.py
"""

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))          # Handel/ - backtest_urteile

import backtest_urteile as bu                                  # noqa: E402

WACHEN_MIT_BACKTEST = """{
  "handel_erlaubt": false,
  "freigabe": {
    "erfuellt": false,
    "backtest_bestanden": false,
    "papierlauf_min_wochen": 6,
    "geprueft_am": null
  },
  "journal_zweitziel": "Q:\\\\Handel_Journal\\\\fixture"
}
"""

WACHEN_OHNE_FELD = """{
  "handel_erlaubt": false,
  "freigabe": {
    "erfuellt": false,
    "papierlauf_min_wochen": 6
  }
}
"""

WACHEN_OHNE_BLOCK = """{
  "handel_erlaubt": false,
  "stufen": 12,
  "journal_zweitziel": "Q:\\\\Handel_Journal\\\\fixture"
}
"""


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.alt = bu.HIER
        bu.HIER = Path(self.tmp.name)
        self.addCleanup(setattr, bu, "HIER", self.alt)

    def _wachen(self, inhalt, spur="gitter"):
        d = Path(self.tmp.name) / spur
        d.mkdir(parents=True, exist_ok=True)
        p = d / "wachen.json"
        p.write_text(inhalt, encoding="utf-8")
        return p


class Schreiben(Basis):
    def test_bestanden_wird_gesetzt_und_nichts_anderes_veraendert(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        vorher = json.loads(p.read_text("utf-8"))
        self.assertIsNone(bu.freigabe_schreiben("gitter", True, "Gitter schlaegt Halten"))
        nachher = json.loads(p.read_text("utf-8"))
        self.assertTrue(nachher["freigabe"]["backtest_bestanden"])
        # Alles andere bleibt gleich - auch der Handels-Schalter.
        self.assertEqual(nachher["handel_erlaubt"], vorher["handel_erlaubt"])
        self.assertFalse(nachher["handel_erlaubt"])
        self.assertFalse(nachher["freigabe"]["erfuellt"])
        for k, v in vorher.items():
            if k != "freigabe":
                self.assertEqual(nachher[k], v, "%s wurde angefasst" % k)
        self.assertEqual(nachher["freigabe"]["papierlauf_min_wochen"], 6)
        self.assertIsNone(nachher["freigabe"]["geprueft_am"])

    def test_fehlendes_feld_wird_eingefuegt(self):
        p = self._wachen(WACHEN_OHNE_FELD)
        bu.freigabe_schreiben("gitter", False, "unter 10 Verlierer")
        f = json.loads(p.read_text("utf-8"))["freigabe"]
        self.assertFalse(f["backtest_bestanden"])
        self.assertIn("unter 10 Verlierer", f["backtest_urteil"])
        self.assertRegex(str(f["backtest_geprueft_am"]), r"^\d{4}-\d{2}-\d{2}$")

    def test_ohne_freigabe_block_wird_einer_angelegt(self):
        p = self._wachen(WACHEN_OHNE_BLOCK)
        bu.freigabe_schreiben("gitter", True, "Gitter schlaegt Halten")
        d = json.loads(p.read_text("utf-8"))
        self.assertTrue(d["freigabe"]["backtest_bestanden"])
        self.assertFalse(d["freigabe"]["erfuellt"], "erfuellt bleibt unberuehrt")
        self.assertEqual(d["stufen"], 12)
        self.assertFalse(d["handel_erlaubt"])

    def test_zweiter_lauf_aendert_nichts_mehr(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        bu.freigabe_schreiben("gitter", True, "gleich")
        erster = p.read_bytes()
        hinweis = bu.freigabe_schreiben("gitter", True, "gleich")
        self.assertEqual(p.read_bytes(), erster)
        self.assertIsNone(hinweis)

    def test_sicherung_wird_einmal_angelegt(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        bu.freigabe_schreiben("gitter", True, "erster")
        baks = list(p.parent.glob("wachen.json.bak-*"))
        self.assertEqual(len(baks), 1)
        self.assertEqual(baks[0].read_text("utf-8"), WACHEN_MIT_BACKTEST)

    def test_vorschau_schreibt_nicht(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        hinweis = bu.freigabe_schreiben("gitter", True, "x", vorschau=True)
        self.assertIn("VORSCHAU", hinweis)
        self.assertEqual(p.read_text("utf-8"), WACHEN_MIT_BACKTEST)

    def test_urteil_mit_anfuehrungszeichen_bleibt_lesbar(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        bu.freigabe_schreiben("gitter", False, 'Urteil mit "Zitat" drin')
        d = json.loads(p.read_text("utf-8"))
        self.assertIn("Zitat", d["freigabe"]["backtest_urteil"])

    def test_abbruch_vor_dem_tausch_laesst_die_alte_datei_ganz(self):
        # Ein Abbruch (taskkill, voller Datentraeger) mitten im Schreiben darf
        # keine halbe wachen.json hinterlassen: erst .tmp, dann os.replace.
        p = self._wachen(WACHEN_MIT_BACKTEST)
        with patch.object(bu.os, "replace", side_effect=OSError("abgebrochen")):
            with self.assertRaises(OSError):
                bu.freigabe_schreiben("gitter", True, "bestanden")
        self.assertEqual(p.read_text("utf-8"), WACHEN_MIT_BACKTEST)
        self.assertEqual(list(p.parent.glob("*.tmp")), [], "kein .tmp-Rest")

    def test_nach_dem_schreiben_bleibt_kein_tmp_liegen(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        bu.freigabe_schreiben("gitter", True, "bestanden")
        self.assertTrue(json.loads(p.read_text("utf-8"))["freigabe"]["backtest_bestanden"])
        self.assertEqual(list(p.parent.glob("*.tmp")), [])


class UrteileLesen(Basis):
    """Die drei Ausgabeformen der Motoren."""

    def test_gitter_json_zeile(self):
        text = ('irgendein Geschwaetz\n'
                '{"start": 100.0, "ende": 120.0, "rendite_pct": 2.14,'
                ' "halten_pct": 15.15, "zyklen": 7, "kerzen": 1344}\n')
        with patch.object(bu, "motor_laufen", return_value=(text, None)):
            bestanden, urteil, kennzahlen = bu.urteil_gitter({"stufen": 12})
        self.assertFalse(bestanden)
        self.assertIn("2.14", urteil)
        self.assertIn("15.15", urteil)
        self.assertEqual(kennzahlen["zyklen"], 7)

    def test_gitter_besser_als_halten_ist_bestanden(self):
        text = '{"rendite_pct": -17.7, "halten_pct": -31.95, "zyklen": 12}'
        with patch.object(bu, "motor_laufen", return_value=(text, None)):
            bestanden, urteil, _ = bu.urteil_gitter({})
        self.assertTrue(bestanden)

    def test_orbk_urteilszeilen(self):
        text = ("=== ETH_USD | Einstiegsmodell: schluss | 7 Sessions ===\n"
                "  URTEIL: Nein - die 81-%-Behauptung faellt (unter 10 Verlierer): "
                "Trefferquote 43%, EV +6.05\n")
        with patch.object(bu, "motor_laufen", return_value=(text, None)):
            bestanden, urteil, kz = bu.urteil_orbk({})
        self.assertFalse(bestanden)
        self.assertIn("zu wenig Daten", urteil)
        self.assertEqual(len(kz["urteile"]), 1)

    def test_orbk_ein_ja_reicht(self):
        text = ("URTEIL: Nein - die 81-%-Behauptung faellt (EV im Fenster <= 0)\n"
                "URTEIL: Ja - Trefferquote ueber Break-even, EV +6.05\n")
        with patch.object(bu, "motor_laufen", return_value=(text, None)):
            bestanden, urteil, _ = bu.urteil_orbk({})
        self.assertTrue(bestanden)

    def test_motor_ohne_urteil_ist_nicht_ermittelbar(self):
        with patch.object(bu, "motor_laufen", return_value=("nur Gelaber", None)):
            bestanden, urteil, _ = bu.urteil_orbk({})
        self.assertIsNone(bestanden)
        self.assertIn("kein URTEIL", urteil)

    def test_motorfehler_ist_nicht_ermittelbar(self):
        with patch.object(bu, "motor_laufen", return_value=("", "kein Motor: x")):
            bestanden, urteil, _ = bu.urteil_gitter({})
        self.assertIsNone(bestanden)
        self.assertIn("kein Motor", urteil)

    def test_nautilus_liest_die_ergebnisdatei(self):
        d = Path(self.tmp.name) / "nautilus"
        d.mkdir(parents=True, exist_ok=True)
        ziel = d / "backtest_grid_ergebnis.json"

        def motor(*a, **kw):
            ziel.write_text(json.dumps({"differenz_zu_hold": 1425.3,
                                        "buy_and_hold_prozent": -31.95}),
                            encoding="utf-8")
            return "Ergebnis gespeichert", None

        ziel.write_text(json.dumps({"differenz_zu_hold": 0.0}), encoding="utf-8")
        with patch.object(bu, "motor_laufen", side_effect=motor):
            bestanden, urteil, kz = bu.urteil_nautilus({})
        self.assertTrue(bestanden)
        self.assertIn("1425", urteil)


class Sicherheitsnetz(Basis):
    """Was der Sammler nie tut."""

    def test_handel_erlaubt_bleibt_falsch_auch_bei_bestandenem_urteil(self):
        p = self._wachen(WACHEN_MIT_BACKTEST)
        bu.freigabe_schreiben("gitter", True, "bestanden")
        roh = p.read_text("utf-8")
        self.assertIn('"handel_erlaubt": false', roh)
        self.assertIn('"erfuellt": false', roh)

    def test_kein_freigabe_block_ergibt_einen_hinweis_statt_eines_schreibens(self):
        # Wenn eine Datei gar keinen Anker hat, wird nichts geraten.
        p = self._wachen("{ \"handel_erlaubt\": false }\n")
        vorher = p.read_bytes()
        with patch.object(bu, "_freigabe_spanne", return_value=None):
            hinweis = bu.freigabe_schreiben("gitter", True, "x")
        self.assertIn("kein freigabe-Block", hinweis)
        self.assertEqual(p.read_bytes(), vorher)


JETZT = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
KEIN = object()


class Vorschau(Basis):
    """--vorschau-datei legt ab, --aus-vorschau uebernimmt genau das - ohne Motor."""

    def setUp(self):
        super().setUp()
        self.jetzt = JETZT
        self.urteile = Path(self.tmp.name) / "backtest_urteile.json"
        self.datei = Path(self.tmp.name) / "ablage" / "v.json"
        self.motor = Mock(return_value=(True, "Gitter schlaegt Halten", {"zyklen": 7}))
        for p in (patch.object(bu, "URTEILE", self.urteile),
                  patch.dict(bu.MOTOREN, {"gitter": self.motor}, clear=True),
                  patch.object(bu, "_jetzt_dt", side_effect=lambda: self.jetzt)):
            p.start()
            self.addCleanup(p.stop)
        self.wachen = self._wachen(WACHEN_MIT_BACKTEST)

    def _main(self, *args):
        aus, fehler = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["backtest_urteile.py"] + list(args)), \
                redirect_stdout(aus), redirect_stderr(fehler):
            rc = bu.main()
        return rc, aus.getvalue()

    def _vorschau(self):
        rc, text = self._main("--spur", "gitter", "--vorschau",
                              "--vorschau-datei", str(self.datei))
        self.assertEqual(rc, 0)
        self.motor.reset_mock()
        return text

    def _tag(self):
        return JETZT.astimezone().strftime("%Y-%m-%d")

    def test_vorschau_datei_schreibt_keine_wachen(self):
        text = self._vorschau()
        self.assertIn("Vorschau-Datei: %s" % self.datei, text)
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_MIT_BACKTEST)
        self.assertFalse(self.urteile.exists())
        d = json.loads(self.datei.read_text("utf-8"))
        self.assertEqual(d["art"], "urteile-vorschau")
        self.assertEqual(d["stand"], "2026-09-29T12:00:00+00:00")
        e = d["spuren"]["gitter"]
        self.assertIs(e["bestanden"], True)
        self.assertIs(e["alt"], False)
        self.assertEqual(e["urteil"], "Gitter schlaegt Halten")
        self.assertEqual(e["sha256"],
                         hashlib.sha256(self.wachen.read_bytes()).hexdigest())
        self.assertEqual(list(self.datei.parent.glob("*.tmp")), [])

    def test_aus_vorschau_schreibt_genau_die_werte_ohne_motor(self):
        self._vorschau()
        self.jetzt = JETZT + timedelta(minutes=10)
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 0)
        self.motor.assert_not_called()
        self.assertIn("geschrieben: gitter/wachen.json", text)
        d = json.loads(self.wachen.read_text("utf-8"))
        self.assertTrue(d["freigabe"]["backtest_bestanden"])
        self.assertEqual(d["freigabe"]["backtest_urteil"], "Gitter schlaegt Halten")
        self.assertEqual(d["freigabe"]["backtest_geprueft_am"], self._tag())
        self.assertFalse(d["handel_erlaubt"])
        self.assertFalse(d["freigabe"]["erfuellt"])

    def test_zu_alte_vorschau_schreibt_nichts(self):
        self._vorschau()
        self.jetzt = JETZT + timedelta(minutes=61)
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("nichts geschrieben - Vorschau aelter als 60 min", text)
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_MIT_BACKTEST)

    def test_geaenderte_wachen_schreibt_nichts(self):
        self._vorschau()
        von_hand = WACHEN_MIT_BACKTEST.replace('"papierlauf_min_wochen": 6',
                                               '"papierlauf_min_wochen": 7')
        self.wachen.write_text(von_hand, encoding="utf-8")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("nichts geschrieben - gitter/wachen.json hat sich seit der "
                      "Vorschau geaendert", text)
        self.assertEqual(self.wachen.read_text("utf-8"), von_hand)

    def test_zukunftsstand_wird_abgelehnt(self):
        self._vorschau()
        self.jetzt = JETZT - timedelta(minutes=10)
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("Stand liegt in der Zukunft", text)

    def test_unlesbare_vorschau(self):
        self.datei.parent.mkdir(parents=True)
        self.datei.write_text("{kaputt", encoding="utf-8")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("nichts geschrieben - Vorschau unlesbar", text)
        rc, text = self._main("--aus-vorschau", str(self.datei.with_name("fehlt.json")))
        self.assertIn("Vorschau unlesbar", text)
        self.assertEqual(bu.vorschau_pruefen({"art": "urteile-vorschau", "spuren": {},
                                              "stand": "2026-09-29T12:00:00"}, JETZT),
                         "Vorschau ohne Stand")

    def test_unbekannte_spur_schreibt_nichts(self):
        self.datei.parent.mkdir(parents=True)
        self.datei.write_text(json.dumps({
            "stand": JETZT.isoformat(), "art": "urteile-vorschau",
            "spuren": {"squeeze": {"bestanden": True, "urteil": "x", "sha256": "0"}}}),
            encoding="utf-8")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("unbekannte Spur in der Vorschau: squeeze", text)

    def test_optionskonflikte(self):
        for args in (("--vorschau-datei", "x.json"),
                     ("--aus-vorschau", "x.json", "--vorschau"),
                     ("--aus-vorschau", "x.json", "--spur", "gitter")):
            with self.assertRaises(SystemExit):
                self._main(*args)
        self.motor.assert_not_called()

    def test_unveraendert_wird_gemeldet(self):
        schon = WACHEN_MIT_BACKTEST.replace(
            '"backtest_bestanden": false,',
            '"backtest_bestanden": true,\n    "backtest_urteil": "Gitter schlaegt '
            'Halten",\n    "backtest_geprueft_am": "%s",' % self._tag())
        self.wachen.write_text(schon, encoding="utf-8")
        self._vorschau()
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 0)
        self.assertIn("unveraendert: gitter/wachen.json", text)
        self.assertEqual(self.wachen.read_text("utf-8"), schon)

    def test_urteile_datei_wird_fortgeschrieben(self):
        self.urteile.write_text(json.dumps({
            "stand": "alt", "ohne_motor": ["squeeze"],
            "spuren": {"orbk": {"bestanden": False}}}), encoding="utf-8")
        self._vorschau()
        self._main("--aus-vorschau", str(self.datei))
        d = json.loads(self.urteile.read_text("utf-8"))
        self.assertEqual(d["ohne_motor"], ["squeeze"])
        self.assertEqual(d["spuren"]["orbk"], {"bestanden": False})
        g = d["spuren"]["gitter"]
        self.assertTrue(g["aus_vorschau"])
        self.assertTrue(g["bestanden"])
        self.assertTrue(g["geschrieben"])


    # --- Nachbesserung (Review): alles vorab pruefen, atomar, Typen ---------

    def _zwei_spuren(self, zweite, urteil2="ok"):
        """gitter (gueltig) + orbk (Inhalt `zweite`), Vorschau von Hand geschrieben."""
        p2 = self._wachen(zweite, "orbk")
        bu.MOTOREN["orbk"] = Mock()
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        e = lambda p, u: {"stand": "x", "bestanden": True, "urteil": u,
                          "kennzahlen": {}, "alt": False,
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        self.datei.write_text(json.dumps({
            "stand": JETZT.isoformat(), "art": "urteile-vorschau",
            "spuren": {"gitter": e(self.wachen, "Gitter schlaegt Halten"),
                       "orbk": e(p2, urteil2)}}), encoding="utf-8")
        return p2

    def test_zweite_spur_ohne_anker_schreibt_gar_nichts(self):
        p2 = self._zwei_spuren("{ \"handel_erlaubt\": false }\n")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("nichts geschrieben - orbk: ", text)
        self.assertIn("kein freigabe-Block", text)
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_MIT_BACKTEST)
        self.assertFalse(self.urteile.exists())

    def test_zweite_spur_urteil_mit_backslash_schreibt_gar_nichts(self):
        self._zwei_spuren(WACHEN_MIT_BACKTEST, "endet auf \\")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("nichts geschrieben - orbk: ", text)
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_MIT_BACKTEST)

    def test_zweite_spur_geaendert_laesst_erste_unberuehrt(self):
        p2 = self._zwei_spuren(WACHEN_MIT_BACKTEST)
        p2.write_text(WACHEN_MIT_BACKTEST.replace("6", "7"), encoding="utf-8")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("orbk/wachen.json hat sich seit der Vorschau geaendert", text)
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_MIT_BACKTEST)

    def _mit_eintrag(self, **aenderung):
        self._vorschau()
        d = json.loads(self.datei.read_text("utf-8"))
        e = d["spuren"]["gitter"]
        for k, v in aenderung.items():
            if v is KEIN:
                e.pop(k, None)
            else:
                e[k] = v
        self.datei.write_text(json.dumps(d), encoding="utf-8")
        return self._main("--aus-vorschau", str(self.datei))

    def test_typen_werden_geprueft(self):
        for aend in ({"bestanden": "true"}, {"bestanden": 1}, {"urteil": {"a": 1}},
                     {"sha256": KEIN}, {"sha256": 5}, {"kennzahlen": [1]}):
            with self.subTest(aend=aend):
                rc, text = self._mit_eintrag(**aend)
                self.assertEqual(rc, 2)
                self.assertIn("nichts geschrieben - Vorschau unlesbar", text)
                self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_MIT_BACKTEST)

    def test_spurname_mit_pfad_wird_abgelehnt(self):
        self.datei.parent.mkdir(parents=True)
        self.datei.write_text(json.dumps({
            "stand": JETZT.isoformat(), "art": "urteile-vorschau",
            "spuren": {"../x": {"bestanden": True, "urteil": "x", "sha256": "0"}}}),
            encoding="utf-8")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("unbekannte Spur in der Vorschau: ../x", text)

    def test_ausnahme_beim_schreiben_wird_gemeldet(self):
        self._vorschau()
        echt = bu.freigabe_schreiben

        def f(*a, **k):
            if k.get("vorschau"):
                return echt(*a, **k)
            raise ValueError("kaputt")
        with patch.object(bu, "freigabe_schreiben", side_effect=f):
            rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 1)
        self.assertIn("nicht geschrieben: gitter - kaputt", text)
        self.assertFalse(json.loads(self.urteile.read_text("utf-8"))
                         ["spuren"]["gitter"]["geschrieben"])

    def test_urteile_datei_wird_atomar_geschrieben(self):
        self._vorschau()
        with patch.object(bu.os, "replace", side_effect=OSError("gesperrt")):
            rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 1)
        self.assertIn("Urteile-Datei nicht geschrieben - gesperrt", text)
        self.assertEqual(list(self.urteile.parent.glob("*.tmp")), [])
        self.assertFalse(self.urteile.exists())

    def test_urteile_laden_faengt_oserror(self):
        self.urteile.mkdir()                      # Verzeichnis: read_text -> OSError
        self.assertEqual(bu._urteile_laden(), {})

    def test_leere_vorschau_schreibt_nichts(self):
        self.datei.parent.mkdir(parents=True)
        self.datei.write_text(json.dumps({
            "stand": JETZT.isoformat(), "art": "urteile-vorschau", "spuren": {}}),
            encoding="utf-8")
        rc, text = self._main("--aus-vorschau", str(self.datei))
        self.assertEqual(rc, 2)
        self.assertIn("nichts geschrieben - Vorschau ohne Spuren", text)
        self.assertFalse(self.urteile.exists())


if __name__ == "__main__":
    unittest.main()
