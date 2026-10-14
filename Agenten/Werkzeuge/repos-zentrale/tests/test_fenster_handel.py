"""Tests fuer den Handelsteil und die neue Ansicht der Zentrale.

Das Fenster wird wirklich gebaut (unsichtbar, `withdraw`) - ein Tippfehler in
einem Widgetnamen faellt so auf. Der Handelsstand kommt aus einem ERFUNDENEN
Lader: der Test liest nicht die echten Spuren, und er schreibt nur in seine
eigene Temp-Wachen-Datei.
"""

import datetime as dt
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auswahl  # noqa: E402
import fenster  # noqa: E402

try:
    import tkinter as tk

    _r = tk.Tk()
    _r.destroy()
    TK_DA = True
except Exception:  # pragma: no cover
    TK_DA = False

DAUERLAUF = '''"""Probe-Treiber fuer den Test."""
SPUREN = {
    "probe":  {"ordner": "probe",  "waehrung": "USD"},
    "zweite": {"ordner": "zweite", "waehrung": "USD", "skript": "handeln_zwei.py"},
    # AUSKOMMENTIERT: "alte": {"ordner": "alte", "waehrung": "USD"},
}
AUTO_FREIGABE = ("probe",)
'''

WACHEN = '{\n  "handel_erlaubt": false,\n  "herzschlag_max_minuten": 45,\n' \
         '  "freigabe": {\n    "erfuellt": false\n  },\n  "max_pro_trade_usd": 100\n}\n'


def standard(erlaubt=False, frei=False, order=None, fenster="zu"):
    return {"spur": "probe", "erlaubt": erlaubt, "frei": frei,
            "order": order if order is not None else ["handeln.py"],
            "art": "haus" if order is None or order else None, "auto": True,
            "fenster": fenster, "buch": {"haupt": 2}, "alter": 7,
            "scharf": bool(order if order is not None else True) and erlaubt}


@unittest.skipUnless(TK_DA, "kein Fenstersystem verfuegbar")
class HandelsansichtTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.bf = Path(self.t.name)
        handel = self.bf / "Agenten" / "Handel"
        (handel / "probe").mkdir(parents=True)
        (handel / "zweite").mkdir(parents=True)
        (handel / "dauerlauf.py").write_text(DAUERLAUF, encoding="utf-8", newline="\n")
        (handel / "probe" / "wachen.json").write_text(WACHEN, encoding="utf-8", newline="\n")
        (handel / "probe" / "handeln.py").write_text("# x\n", encoding="utf-8")
        (handel / "zweite" / "wachen.json").write_text(WACHEN, encoding="utf-8", newline="\n")
        (handel / "kein-werkzeug").mkdir()
        (handel / "werkzeug.py").write_text(
            "import argparse\nif __name__ == '__main__':\n    pass\n", encoding="utf-8")

        (self.bf / "Werkstatt" / "ein-repo" / ".git").mkdir(parents=True)
        (self.bf / "Werkstatt" / "ein-repo" / "README.md").write_text("# x\n")
        (self.bf / "profiles").mkdir()

        self.manifest = self.bf / "repos-zentrale.json"
        self.manifest.write_text(json.dumps({"stand": "x", "repos": []}), encoding="utf-8")
        self.logs = self.bf / "logs"
        self.stand = {"probe": standard(), "zweite": standard(order=[])}
        self.gerufen = []

    def tearDown(self):
        self.t.cleanup()

    def _bauen(self, stand=None, **kwargs):
        f = fenster.Fenster(
            self.bf, self.manifest, self.bf / "profiles", self.logs,
            lauf=lambda argv: self.gerufen.append(argv),
            handel_zustand_lader=lambda: (stand if stand is not None else self.stand),
            vorschau_lauf=lambda spur: (True, f"VORSCHAU {spur}: keine Dateien geschrieben."),
            **kwargs,
        )
        f.root.withdraw()
        f.root.update()
        return f

    def _item(self, f, ordner):
        for item, z in f.kinder.items():
            if z.ordner == ordner:
                return item, z
        raise AssertionError(f"{ordner} steht nicht im Baum")

    def _waehlen(self, f, ordner):
        item, z = self._item(f, ordner)
        f.baum.selection_set(item)
        f._auswahl_geaendert()
        f.root.update()
        return z

    # ---------------------------------------------------------- Kennzeichen
    def test_nur_handelszeilen_bekommen_ein_spurkennzeichen(self):
        f = self._bauen()
        try:
            _, probe = self._item(f, "probe")
            _, repo = self._item(f, "ein-repo")
            self.assertEqual(probe.spur, "probe")
            self.assertEqual(probe.spuren, ["probe"])
            self.assertEqual(repo.spur, "")
        finally:
            f.root.destroy()

    def test_der_auskommentierte_block_erzeugt_keine_spur(self):
        f = self._bauen()
        try:
            self.assertNotIn("alte", f._plan)
        finally:
            f.root.destroy()

    # ---------------------------------------------------------- Handelskarte
    def test_handelskarte_zeigt_den_stand_der_spur(self):
        f = self._bauen()
        try:
            self._waehlen(f, "probe")
            kopf = f.handel_kopf["text"]
            self.assertIn("Spur probe", kopf)
            self.assertIn("Orderweg haus", kopf)
            self.assertIn("handel_erlaubt=false", kopf)
            self.assertIn("Buch haupt 2", kopf)
            text = f.handel_text.get("1.0", "end")
            self.assertIn("Herzschlag", text)
            self.assertIn("FEHLT", text, "45 min ist fuer live zu wenig")
        finally:
            f.root.destroy()

    def test_knoepfe_haengen_am_zustand(self):
        f = self._bauen()
        try:
            self._waehlen(f, "probe")
            self.assertEqual(str(f.handel_knoepfe["test"]["state"]), "normal")
            self.assertEqual(str(f.handel_knoepfe["scharf"]["state"]), "normal")
            self.assertEqual(str(f.handel_knoepfe["entschaerfen"]["state"]), "disabled")
            self._waehlen(f, "ein-repo")
            self.assertEqual(str(f.handel_knoepfe["test"]["state"]), "disabled")
            self.assertIn("Keine Handels-Spur", f.handel_kopf["text"])
        finally:
            f.root.destroy()

    def test_scharfe_spur_zeigt_gruen_und_laesst_sich_entschaerfen(self):
        stand = {"probe": standard(erlaubt=True, frei=True, fenster="offen bis 06:24")}
        f = self._bauen(stand=stand)
        try:
            z = self._waehlen(f, "probe")
            self.assertTrue(z.scharf)
            self.assertEqual(str(f.handel_knoepfe["scharf"]["state"]), "disabled")
            self.assertEqual(str(f.handel_knoepfe["entschaerfen"]["state"]), "normal")
            self.assertIn("KANN live ordern", f.handel_text.get("1.0", "end"))
        finally:
            f.root.destroy()

    # ---------------------------------------------------------- Testlauf
    def test_vorschau_schreibt_ihre_ausgabe_in_die_karte(self):
        f = self._bauen()
        try:
            self._waehlen(f, "probe")
            f.handel_testen()
            for _ in range(40):
                f.root.update()
                time.sleep(0.02)
            text = f.handel_text.get("1.0", "end")
            self.assertIn("VORSCHAU probe", text)
            self.assertIn("beendet", f.status["text"])
        finally:
            f.root.destroy()

    def test_vorschau_ohne_spur_testet_nichts(self):
        f = self._bauen()
        try:
            self._waehlen(f, "ein-repo")
            f.handel_testen()
            self.assertIn("Keine Handels-Spur", f.status["text"])
        finally:
            f.root.destroy()

    # ---------------------------------------------------------- Filter
    def test_chip_spuren_zeigt_nur_spuren(self):
        f = self._bauen()
        try:
            f.kennzeichen_umschalten("spuren")
            f.root.update()
            gezeigt = {z.ordner for z in f.zeilen if auswahl.trifft(z, f._filter())}
            self.assertIn("probe", gezeigt)
            self.assertIn("zweite", gezeigt)
            self.assertNotIn("ein-repo", gezeigt)
            f.kennzeichen_umschalten("spuren")
            self.assertNotIn("spuren", f.kennzeichen)
        finally:
            f.root.destroy()

    def test_chip_scharf_zeigt_nur_scharfe_spuren(self):
        stand = {"probe": standard(erlaubt=True), "zweite": standard(order=[])}
        f = self._bauen(stand=stand)
        try:
            f.kennzeichen_umschalten("scharf")
            f.root.update()
            gezeigt = {z.ordner for z in f.zeilen if auswahl.trifft(z, f._filter())}
            self.assertEqual(gezeigt, {"probe"})
            self.assertIn("scharf", f.zusammenfassung["text"])
        finally:
            f.root.destroy()

    def test_filter_zuruecksetzen_raeumt_alles(self):
        f = self._bauen()
        try:
            f.suchtext.set("probe")
            f.kennzeichen_umschalten("handel")
            f.gruppe.set("STARTBAR")
            f.filter_zuruecksetzen()
            f.root.update()
            self.assertEqual(f.suchtext.get(), "")
            self.assertEqual(f.kennzeichen, set())
            self.assertEqual(f.gruppe.get(), auswahl.ALLE_GRUPPEN)
            self.assertEqual(str(f.chip_knoepfe["handel"].variante), "flach")
        finally:
            f.root.destroy()

    # ---------------------------------------------------------- Skalierung
    def test_schrift_skaliert_zeilen_und_knoepfe(self):
        f = self._bauen()
        try:
            vorher = f._zeilenhoehe()
            f.schrift_setzen(15)
            f.root.update()
            self.assertEqual(f.schrift_label["text"], "15 pt")
            self.assertGreater(f._zeilenhoehe(), vorher)
            self.assertEqual(f.knoepfe["start"].schrift_tupel[1], 15)
        finally:
            f.root.destroy()

    def test_schrift_bleibt_im_bereich(self):
        f = self._bauen()
        try:
            f.schrift_setzen(99)
            self.assertEqual(f.schriftgroesse, 16)
            f.schrift_setzen(-5)
            self.assertEqual(f.schriftgroesse, 8)
        finally:
            f.root.destroy()

    def test_dichte_aendert_nur_den_abstand(self):
        f = self._bauen()
        try:
            f.dichte_setzen("kompakt")
            kompakt = f._zeilenhoehe()
            f.dichte_setzen("gross")
            gross = f._zeilenhoehe()
            self.assertLess(kompakt, gross)
            self.assertEqual(f.schriftgroesse, 11, "die Schrift bleibt")
        finally:
            f.root.destroy()

    def test_ansicht_wird_gemerkt_und_beim_start_gelesen(self):
        pfad = self.bf / "einstellungen.json"
        f = self._bauen(einstellungen_pfad=pfad)
        try:
            f.schrift_setzen(13)
            f.dichte_setzen("kompakt")
            f.groesse_setzen("gross")
            f.kennzeichen_umschalten("fremd")
            f.root.update()
        finally:
            f.root.destroy()
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        self.assertEqual(daten["schrift"], 13)
        self.assertEqual(daten["dichte"], "kompakt")
        self.assertEqual(daten["fenster"], "gross")
        self.assertEqual(daten["filter"], ["fremd"])

        g = self._bauen(einstellungen_pfad=pfad)
        try:
            self.assertEqual(g.schriftgroesse, 13)
            self.assertIn("fremd", g.kennzeichen)
            self.assertEqual(str(g.chip_knoepfe["fremd"].variante), "haupt")
        finally:
            g.root.destroy()

    def test_groesse_masse_bleibt_im_bild(self):
        self.assertEqual(fenster.groesse_masse((1920, 1080), "klein", 1.0), (1100, 700))
        b, h = fenster.groesse_masse((1920, 1080), "bildschirm", 1.0)
        self.assertLess(b, 1920)
        self.assertLess(h, 1080)
        b2, _ = fenster.groesse_masse((1366, 768), "gross", 1.25)
        self.assertLessEqual(b2, 1366 - 80)

    # ---------------------------------------------------------- Schreiben
    def test_schalter_schreibt_in_die_wachen_datei_und_belegt_es(self):
        f = self._bauen()
        try:
            f.handel_zustand()          # erst laden - der Dialog ist auch nur nach einer Auswahl erreichbar
            ergebnis = f._schalter_ausfuehren(
                "probe", {"handel_erlaubt": True, "herzschlag_max_minuten": 180},
                "Probe aus dem Test",
            )
            self.assertTrue(ergebnis.ok, ergebnis.fehler)
            daten = json.loads(
                (self.bf / "Agenten" / "Handel" / "probe" / "wachen.json")
                .read_text(encoding="utf-8"))
            self.assertIs(daten["handel_erlaubt"], True)
            self.assertEqual(daten["herzschlag_max_minuten"], 180)
            self.assertIn("_scharfgeschaltet", daten)
            belege = list(self.logs.glob("handel-schalter-*.log"))
            self.assertEqual(len(belege), 1)
            self.assertIn("OK probe", belege[0].read_text(encoding="utf-8"))
            # Der gelesene Stand wird mitgezogen, ohne alles neu zu lesen.
            self.assertTrue(f.handel_zustand()["probe"]["erlaubt"])
        finally:
            f.root.destroy()

    def test_schalter_meldet_einen_fehlschlag_und_aendert_nichts(self):
        pfad = self.bf / "Agenten" / "Handel" / "zweite" / "wachen.json"
        vorher = pfad.read_bytes()
        f = self._bauen()
        try:
            ergebnis = f._schalter_ausfuehren("zweite", {"gibtsnicht": True}, "Probe")
            self.assertFalse(ergebnis.ok)
            self.assertEqual(pfad.read_bytes(), vorher)
            self.assertIn("FEHLER", (list(self.logs.glob("handel-schalter-*.log"))[0])
                          .read_text(encoding="utf-8"))
        finally:
            f.root.destroy()

    def test_scharf_dialog_oeffnet_sich_ohne_auswahl_nicht(self):
        f = self._bauen()
        try:
            self._waehlen(f, "ein-repo")
            f.scharf_dialog()
            self.assertIn("Keine Handels-Spur", f.status["text"])
            f.entschaerfen()
            self.assertIn("Keine Handels-Spur", f.status["text"])
        finally:
            f.root.destroy()


if __name__ == "__main__":
    unittest.main()