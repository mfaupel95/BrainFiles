"""Tests fuer den Handelsstand der Zentrale (lesen, pruefen, schreiben).

Zwei Sorten:

* **Lesen** - der Laufplan kommt aus `dauerlauf.SPUREN`. Er wird gegen die
  Namensliste von `spuren_stand.py` gehalten: beide lesen dieselbe Datei, also
  muessen sie dieselben Spuren nennen. Zusaetzlich wird geprueft, dass ein
  AUSKOMMENTIERTER Block keine Spur erzeugt (genau dieser Fehler stand schon
  einmal in einem README).
* **Schreiben** - `wachen_setzen` arbeitet auf Kopien in einem Temp-Ordner.
  Die echten Wachen-Dateien der Spuren werden NIE angefasst; ein Test, der in
  eine echte Spur schreibt, waere ein Betriebseingriff.
"""

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import handelstand  # noqa: E402

BRAINFILES = Path(__file__).resolve().parents[4]
HANDEL = BRAINFILES / "Agenten" / "Handel"


def wachen_text(*, erlaubt=False, hs=180, frei=False, crlf=False, extra=""):
    """Eine kleine Wachen-Datei wie die echten - mit Notizen und Kommentaren."""
    text = (
        '{\n'
        '  "_zweck": "Probe. handel_erlaubt wird hier nur gelesen, nie geschrieben.",\n'
        f'  "handel_erlaubt": {str(erlaubt).lower()},\n'
        f'  "herzschlag_max_minuten": {hs},\n'
        '  "freigabe": {\n'
        '    "erfuellt": %s,\n' % str(frei).lower()
        + '    "_notiz": "erfuellt ist der von Hand gesetzte Haken"\n'
        '  },\n'
        '  "max_pro_trade_usd": 120,\n'
        '  "max_offene_positionen": 5\n'
        + extra + '}\n'
    )
    return text.replace("\n", "\r\n") if crlf else text


class LaufplanTest(unittest.TestCase):
    def setUp(self):
        self.plan = handelstand.laufplan(BRAINFILES)

    def test_plan_ist_nicht_leer(self):
        self.assertGreater(len(self.plan), 20)

    def test_nennt_dieselben_spuren_wie_spuren_stand(self):
        """Zwei Leser derselben Datei muessen dasselbe sagen."""
        modul = handelstand.stand_modul(HANDEL)
        self.assertIsNotNone(modul, "spuren_stand.py nicht gefunden")
        namen = set(modul.spurenliste()[0])
        self.assertEqual(namen, set(self.plan), "Laufplan und spuren_stand gehen auseinander")

    def test_auskommentierte_bloecke_erzeugen_keine_spur(self):
        """spiegel/spiegel_knapp/omniquant_weit stehen als Kommentar in dauerlauf.SPUREN."""
        for tot in ("spiegel", "spiegel_knapp", "omniquant_weit"):
            self.assertNotIn(tot, self.plan, f"{tot} ist auskommentiert, darf nicht im Plan sein")
        for lebt in ("xperp", "scanner", "mosaic", "klassik_sma", "kopier"):
            self.assertIn(lebt, self.plan)

    def test_jede_spur_hat_ordner_und_skript_und_der_ordner_existiert(self):
        for name, e in self.plan.items():
            with self.subTest(spur=name):
                self.assertTrue(e["ordner"])
                self.assertTrue(e["skript"].endswith(".py"), e["skript"])
                self.assertTrue((HANDEL / e["ordner"]).is_dir(), f"{e['ordner']} fehlt")

    def test_fehlende_datei_gibt_leeren_plan(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(handelstand.laufplan(Path(t)), {})

    def test_interpreter_kommt_aus_der_spur(self):
        nautilus = handelstand.interpreter(BRAINFILES, "nautilus")
        self.assertIn("nautilus", str(nautilus))
        self.assertIn(".venv", str(nautilus))
        # Eine Spur ohne eigenen Interpreter bekommt das scanner-venv (so
        # startet der Dauerlauf seine Spuren).
        self.assertEqual(handelstand.interpreter(BRAINFILES, "klassik_sma"),
                         HANDEL / "scanner" / ".venv" / "Scripts" / "python.exe")

    def test_vorschau_argv(self):
        argv = handelstand.vorschau_argv(BRAINFILES, "klassik_sma")
        self.assertEqual(argv[-1], "--vorschau")
        self.assertTrue(argv[0].endswith("python.exe"))
        self.assertEqual(Path(argv[1]), HANDEL / "klassik_sma" / "handeln.py")

    def test_vorschau_argv_folgt_dem_skript_der_spur(self):
        """nautilus_kraken_futures faehrt handeln_futures.py im Ordner nautilus_kraken."""
        argv = handelstand.vorschau_argv(BRAINFILES, "nautilus_kraken_futures")
        self.assertEqual(Path(argv[1]), HANDEL / "nautilus_kraken" / "handeln_futures.py")

    def test_vorschau_umgebung_setzt_die_hausregeln(self):
        umgebung = handelstand.vorschau_umgebung({"PYTHONHOME": "C:/x", "PYTHONPATH": "y",
                                                  "PATH": "z"})
        self.assertEqual(umgebung["MAXHIRN_ROUTINE"], "1")
        self.assertNotIn("PYTHONHOME", umgebung)
        self.assertNotIn("PYTHONPATH", umgebung)
        self.assertEqual(umgebung["PATH"], "z")


class PruefpunkteTest(unittest.TestCase):
    def _punkte(self, w, eintrag, alter=None):
        return {p.name: p for p in handelstand.pruefpunkte(w, eintrag, alter=alter)}

    def test_herzschlag_unter_180_ist_ein_fehlender_punkt(self):
        p = self._punkte({"herzschlag_max_minuten": 45}, {})
        self.assertEqual(p["Herzschlag"].stand, "fehlt")
        self.assertIn("180", p["Herzschlag"].text)

    def test_herzschlag_180_ist_ok(self):
        p = self._punkte({"herzschlag_max_minuten": 180}, {})
        self.assertEqual(p["Herzschlag"].stand, "ok")

    def test_ohne_orderweg_ist_es_eine_warnung(self):
        p = self._punkte({"herzschlag_max_minuten": 180}, {"order": []})
        self.assertEqual(p["Orderweg"].stand, "warnung")

    def test_freigabe_haken_false_erklaert_die_folge(self):
        p = self._punkte({}, {"frei": False})
        self.assertEqual(p["freigabe.erfuellt"].stand, "unbekannt")
        self.assertIn("nicht live", p["freigabe.erfuellt"].text)

    def test_guthaben_bleibt_unbekannt(self):
        """Eine geratene Aussage waere schlimmer als eine fehlende."""
        p = self._punkte({}, {})
        self.assertEqual(p["Guthaben/Schluessel"].stand, "unbekannt")

    def test_deckel_nennt_die_zahlen_der_wachen(self):
        p = self._punkte({"max_pro_trade_usd": 120, "max_offene_positionen": 5}, {})
        self.assertIn("je Trade USD 120", p["Deckel"].text)
        self.assertIn("Plaetze 5", p["Deckel"].text)

    def test_alter_zyklus_ist_eine_warnung(self):
        p = self._punkte({}, {}, alter=400)
        self.assertEqual(p["Zyklus"].stand, "warnung")


class WirkungTest(unittest.TestCase):
    def test_ohne_orderweg_aendert_der_schalter_nichts(self):
        text = handelstand.wirkung({"order": []}, erlaubt=True)
        self.assertIn("nichts", text)

    def test_mit_orderweg_haken_und_fenster_kann_er_ordern(self):
        text = handelstand.wirkung(
            {"order": ["handeln.py"], "frei": True, "fenster": "offen bis 06:24"},
            erlaubt=True,
        )
        self.assertIn("KANN live ordern", text)

    def test_ohne_haken_kann_er_nicht_ordern(self):
        text = handelstand.wirkung(
            {"order": ["handeln.py"], "frei": False, "fenster": "offen bis 06:24"},
            erlaubt=True,
        )
        self.assertIn("nichts geordert", text)

    def test_ausschalten_sagt_was_mit_offenen_positionen_passiert(self):
        text = handelstand.wirkung({"order": ["handeln.py"]}, erlaubt=False)
        self.assertIn("handelt nicht mehr", text)
        self.assertIn("Stop", text)


class WachenSetzenTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.pfad = Path(self.t.name) / "wachen.json"
        self.jetzt = dt.datetime(2026, 9, 30, 18, 0)

    def tearDown(self):
        self.t.cleanup()

    def _schreiben(self, text: str) -> None:
        self.pfad.write_bytes(text.encode("utf-8"))

    def test_schreibt_und_legt_eine_sicherung_an(self):
        self._schreiben(wachen_text())
        e = handelstand.wachen_setzen(self.pfad, {"handel_erlaubt": True},
                                      vermerk="Probe", notiz_schluessel="_scharfgeschaltet",
                                      jetzt=self.jetzt)
        self.assertTrue(e.ok, e.fehler)
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertIs(daten["handel_erlaubt"], True)
        self.assertTrue(e.sicherung.is_file())
        self.assertEqual(e.sicherung.name, "wachen.json.bak-20260930")

    def test_die_sicherung_haelt_den_ersten_stand_des_tages(self):
        self._schreiben(wachen_text())
        handelstand.wachen_setzen(self.pfad, {"handel_erlaubt": True}, jetzt=self.jetzt)
        handelstand.wachen_setzen(self.pfad, {"handel_erlaubt": False}, jetzt=self.jetzt)
        sicherung = self.pfad.with_name("wachen.json.bak-20260930")
        self.assertIn('"handel_erlaubt": false', sicherung.read_text(encoding="utf-8"))

    def test_notiz_wird_gesetzt_und_nicht_doppelt(self):
        self._schreiben(wachen_text())
        for _ in range(2):
            handelstand.wachen_setzen(
                self.pfad, {"handel_erlaubt": True}, vermerk="Probe",
                notiz_schluessel="_scharfgeschaltet", jetzt=self.jetzt,
            )
        text = self.pfad.read_text(encoding="utf-8")
        self.assertEqual(text.count('"_scharfgeschaltet"'), 1)
        daten = json.loads(text)
        self.assertIn("2026-09-30", daten["_scharfgeschaltet"])
        self.assertIn("Probe", daten["_scharfgeschaltet"])

    def test_crlf_bleibt_erhalten(self):
        self._schreiben(wachen_text(crlf=True))
        handelstand.wachen_setzen(self.pfad, {"handel_erlaubt": True}, jetzt=self.jetzt)
        roh = self.pfad.read_bytes()
        self.assertIn(b"\r\n", roh)
        self.assertNotIn(b"\n\n", roh.replace(b"\r\n", b"\n"))
        json.loads(roh.decode("utf-8"))

    def test_lf_bleibt_lf(self):
        self._schreiben(wachen_text())
        handelstand.wachen_setzen(self.pfad, {"handel_erlaubt": True}, jetzt=self.jetzt)
        self.assertNotIn(b"\r\n", self.pfad.read_bytes())

    def test_verschachtelter_schluessel_freigabe_erfuellt(self):
        self._schreiben(wachen_text())
        e = handelstand.wachen_setzen(self.pfad, {"freigabe.erfuellt": True}, jetzt=self.jetzt)
        self.assertTrue(e.ok, e.fehler)
        self.assertIs(json.loads(self.pfad.read_text(encoding="utf-8"))["freigabe"]["erfuellt"],
                      True)

    def test_eine_notiz_mit_schluesselnamen_wird_nicht_getroffen(self):
        """Der Textersatz ist am ZEILENANFANG verankert - sonst zerschneidet er Notizen."""
        self._schreiben(wachen_text(
            extra=',\n  "_warnung": "handel_erlaubt steht hier im Text"\n'))
        e = handelstand.wachen_setzen(self.pfad, {"handel_erlaubt": True}, jetzt=self.jetzt)
        self.assertTrue(e.ok, e.fehler)
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertIn("handel_erlaubt steht hier im Text", daten["_warnung"])

    def test_fehlender_schluessel_schreibt_nichts(self):
        self._schreiben(wachen_text())
        vorher = self.pfad.read_bytes()
        e = handelstand.wachen_setzen(self.pfad, {"gibtsnicht": True}, jetzt=self.jetzt)
        self.assertFalse(e.ok)
        self.assertIn("nicht gefunden", e.fehler)
        self.assertEqual(self.pfad.read_bytes(), vorher)

    def test_fehlende_datei_meldet_sich(self):
        e = handelstand.wachen_setzen(Path(self.t.name) / "weg.json", {"handel_erlaubt": True})
        self.assertFalse(e.ok)
        self.assertIn("fehlt", e.fehler)

    def test_scharf_schalten_setzt_den_herzschlag_zuerst(self):
        self._schreiben(wachen_text(hs=45))
        w = json.loads(self.pfad.read_text(encoding="utf-8"))
        e = handelstand.scharf_schalten(self.pfad, w=w, jetzt=self.jetzt)
        self.assertTrue(e.ok, e.fehler)
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertEqual(daten["herzschlag_max_minuten"], handelstand.HERZSCHLAG_LIVE)
        self.assertIs(daten["handel_erlaubt"], True)
        self.assertIs(daten["freigabe"]["erfuellt"], False, "der Haken bleibt unberuehrt")

    def test_scharf_schalten_ohne_herzschlag_verweigert(self):
        self._schreiben('{\n  "handel_erlaubt": false\n}\n')
        e = handelstand.scharf_schalten(self.pfad, w={"handel_erlaubt": False},
                                        jetzt=self.jetzt)
        self.assertFalse(e.ok)
        self.assertIn("herzschlag", e.fehler)

    def test_entschaerfen_laesst_den_haken_stehen(self):
        self._schreiben(wachen_text(erlaubt=True, frei=True))
        e = handelstand.entschaerfen(self.pfad, jetzt=self.jetzt)
        self.assertTrue(e.ok, e.fehler)
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertIs(daten["handel_erlaubt"], False)
        self.assertIs(daten["freigabe"]["erfuellt"], True)

    def test_ersetzte_werte_werden_gegengeprueft(self):
        """Ein Tippfehler im Muster darf nicht als Erfolg durchgehen."""
        text, meldung = handelstand.ersetze_wert('{\n  "handel_erlaubt": false\n}\n',
                                                 "handel_erlaubt", True)
        self.assertIn("false -> true", meldung)
        self.assertIn("true", text)

    def test_zweite_fundstelle_wird_verweigert(self):
        text, meldung = handelstand.ersetze_wert(
            '{\n  "handel_erlaubt": false,\n  "handel_erlaubt": true\n}\n',
            "handel_erlaubt", False)
        self.assertIn("2 Fundstellen", meldung)
        self.assertIn('"handel_erlaubt": false', text)


class BelegTest(unittest.TestCase):
    def test_beleg_haengt_zeilen_an(self):
        with tempfile.TemporaryDirectory() as t:
            p = handelstand.beleg(Path(t), "OK scanner: handel_erlaubt false -> true",
                                  jetzt=dt.datetime(2026, 9, 30, 18, 5))
            self.assertTrue(p.is_file())
            handelstand.beleg(Path(t), "zweite Zeile",
                              jetzt=dt.datetime(2026, 9, 30, 18, 6))
            zeilen = p.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(zeilen), 2)
            self.assertIn("18:05:00", zeilen[0])


class ZustandTest(unittest.TestCase):
    def test_zustand_liest_die_echten_spuren(self):
        """Nur LESEN: spuren_stand.sammle() oeffnet keine Order und schreibt nichts."""
        daten = handelstand.zustand(BRAINFILES)
        self.assertGreater(len(daten), 20)
        for e in daten.values():
            self.assertIn("erlaubt", e)
            self.assertIn("order", e)
            self.assertIn("scharf", e)

    def test_fehlender_handelsordner_gibt_leeren_stand(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(handelstand.zustand(Path(t)), {})


if __name__ == "__main__":
    unittest.main()