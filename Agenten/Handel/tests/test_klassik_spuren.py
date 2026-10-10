"""Vertrag der klassischen Papierspuren (klassik_*) - eine Pruefung fuer alle.

Warum diese Datei: die Spuren bestehen aus je einem 17-Zeilen-`handeln.py`,
einer `wachen.json` und einem README; die Rechnung liegt gemeinsam in
`Handel/klassik_regeln.py` (dort liegt auch `tests/test_klassik_regeln.py` fuer
die Regeln selbst). Was fehlte, war der **Vertrag der Ordner**: dass Name, Wachen
und Anmeldung im Dauerlauf zusammenpassen und dass keine Spur still einen
Orderweg bekommt.

Geprueft wird die REGEL, nicht der Stand: keine festen Zahlen aus dem September,
sondern Beziehungen (Stop im erlaubten Band, Ratsche = Buchrisiko, Deckel
passt zu den Plaetzen, genug Kerzen fuer den laengsten Indikator). Die Zahl der
Spuren ist keine Eigenschaft - die Mengengleichheit mit `REGELN` ist sie.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HANDEL = Path(__file__).resolve().parent.parent
TESTS = Path(__file__).resolve().parent
SPUREN = sorted(p for p in HANDEL.glob("klassik_*") if p.is_dir())

sys.path.insert(0, str(HANDEL))
import klassik_regeln  # noqa: E402

# Der laengste Indikator je Regel braucht so viele Kerzen. Abgeleitet aus den
# Feldern der Wachen - hier steht nur, WELCHE Felder zaehlen, nicht ihr Wert.
NOETIGE_FELDER = ("langsam_n", "signal_n", "bb_n", "kanal_ein_n", "kanal_aus_n",
                  "rsi_n", "aus_sma_n", "volumen_langsam_n", "ma_laenge",
                  "atr_perioden")
VENV = HANDEL / ".venv" / "Scripts" / "python.exe"


def wachen(spur: Path) -> dict:
    return json.loads((spur / "wachen.json").read_text(encoding="utf-8"))


def mindestens(w: dict) -> int:
    """Wie viele Kerzen die Regel mindestens braucht, aus den Feldern selbst."""
    zahlen = [int(w[f]) for f in NOETIGE_FELDER if isinstance(w.get(f), int)]
    if isinstance(w.get("trend_n"), int):
        zahlen.append(int(w["trend_n"]) + int(w.get("steigung_n", 0)))
    if isinstance(w.get("pivot_left"), int) and isinstance(w.get("pivot_right"), int):
        zahlen.append(w["pivot_left"] + w["pivot_right"] + 1)
    if w.get("ma_typ") == "TMA" and isinstance(w.get("ma_laenge"), int):
        n = w["ma_laenge"]
        zahlen.append((n + 1) // 2 + n // 2 + 1 - 1)   # sma(sma(...)) braucht h+k-1
    return max(zahlen or [0])


class Bestand(unittest.TestCase):
    """Es gibt genau die Spuren, die die Rechnung kennt - in beide Richtungen."""

    def test_ordner_und_regeln_stimmen_ueberein(self):
        auf_der_platte = {p.name for p in SPUREN}
        self.assertEqual(auf_der_platte, set(klassik_regeln.REGELN),
                         "Ordner und REGELN weichen ab (Waisen in beide Richtungen)")

    def test_jede_spur_hat_die_drei_dateien(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                self.assertTrue((s / "handeln.py").is_file())
                self.assertTrue((s / "wachen.json").is_file())
                self.assertTrue((s / "README.md").is_file())


class WachenVertrag(unittest.TestCase):
    """Die Wachen einer Papierspur sagen: kein Geld, kein Orderweg, 180 Minuten."""

    def test_grund_ist_der_ordnername(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                self.assertEqual(wachen(s).get("_grund"), s.name)

    def test_papier_und_nicht_freigegeben(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                w = wachen(s)
                self.assertIs(w.get("handel_erlaubt"), False,
                              "eine Papierspur ohne Orderweg darf nicht handeln")
                self.assertIs(w.get("freigabe", {}).get("erfuellt"), False)

    def test_herzschlag_und_gebuehr(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                w = wachen(s)
                self.assertEqual(w.get("herzschlag_max_minuten"), 180)
                self.assertGreater(w.get("gebuehr_taker", 0), 0,
                                   "0 waere eine Gratisannahme - OKX nimmt 0,05 %/Seite")

    def test_zweitziel_ist_der_eigene_journalordner(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                self.assertEqual(wachen(s).get("journal_zweitziel"),
                                 "Q:\\Handel_Journal\\" + s.name)

    def test_instrumente_und_zeitrahmen_gesetzt(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                w = wachen(s)
                self.assertTrue(w.get("instrumente"), "ohne Instrument kein Signal")
                self.assertTrue(w.get("kerzen_zeitrahmen"))


class RisikoVertrag(unittest.TestCase):
    """Die Groessen passen zueinander - nicht zu Zahlen vom September."""

    def test_stop_liegt_im_erlaubten_band(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                w = wachen(s)
                self.assertGreaterEqual(w["stop_prozent"], w["pflicht_stop_prozent_min"])
                self.assertLessEqual(w["stop_prozent"], w["pflicht_stop_prozent_max"])

    def test_position_ist_beim_eigenen_stop_baubar(self):
        """risiko = nominal * stop%  ->  nominal muss unter max_pro_trade passen."""
        for s in SPUREN:
            with self.subTest(spur=s.name):
                w = wachen(s)
                nominal = w["risiko_je_position_usd"] / (w["stop_prozent"] / 100.0)
                self.assertLessEqual(round(nominal, 2), w["max_pro_trade_usd"],
                                     "sonst wird die Position gedeckelt und das "
                                     "Risiko ist kleiner als eingestellt")

    def test_ratsche_ist_mindestens_das_buchrisiko(self):
        # Bis 09.10.2026 genau das Buchrisiko (15 USD); der Backtest (PR #21) zeigte,
        # dass das 42 % des Gewinns kostet - jetzt 20 x Risiko, aber nie unter dem
        # Buchrisiko, sonst halbiert schon ein einziger voller Stop-Lauf.
        for s in SPUREN:
            with self.subTest(spur=s.name):
                w = wachen(s)
                buchrisiko = w["risiko_je_position_usd"] * w["max_offene_positionen"]
                self.assertGreaterEqual(w["drawdown_halbierung_usd"], buchrisiko)

    def test_kill_switch_ueber_der_ratsche(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                w = wachen(s)
                self.assertGreater(w["kill_switch_gesamt_usd"], w["drawdown_halbierung_usd"])

    def test_gesamtdeckel_passt_zu_den_plaetzen(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                w = wachen(s)
                self.assertGreaterEqual(w["max_gesamt_usd"],
                                        w["risiko_je_position_usd"] * w["max_offene_positionen"])
                self.assertLessEqual(w["max_gesamt_usd"],
                                     w["max_pro_trade_usd"] * w["max_offene_positionen"],
                                     "der Deckel verspricht mehr, als die Plaetze hergeben")

    def test_genug_kerzen_fuer_den_laengsten_indikator(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                w = wachen(s)
                self.assertGreaterEqual(
                    int(w["mindest_kerzen"]), mindestens(w),
                    "der laengste Indikator dieser Regel hat zu wenig Kerzen")
                self.assertGreaterEqual(int(w["kerzen_anzahl"]), int(w["mindest_kerzen"]))


class Anmeldung(unittest.TestCase):
    """Die Spur steht im Dauerlauf - und nur ueber ihre eigene handeln.py."""

    @classmethod
    def setUpClass(cls):
        cls.quelle = (HANDEL / "dauerlauf.py").read_text(encoding="utf-8")

    def test_jede_spur_ist_im_dauerlauf_angemeldet(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                self.assertIn('"%s": {"ordner": "%s"' % (s.name, s.name), self.quelle)

    def test_handeln_ruft_die_eigene_regel(self):
        for s in SPUREN:
            with self.subTest(spur=s.name):
                text = (s / "handeln.py").read_text(encoding="utf-8")
                self.assertIn('spur_main("%s"' % s.name, text)
                self.assertIn('__main__', text)

    def test_handeln_meldet_ihren_bus_namen_woertlich(self):
        """T-255: der Bus-Name steht als Literal in der gestarteten Datei.

        Der Dauerlauf startet genau diese `handeln.py`; die Bus-Suite
        (`Bus/tests/test_anbindung_handel.py`) sucht den Journalnamen
        WORTWOERTLICH dort. Leitet der Kern ihn nur aus dem Ordnernamen ab,
        findet die Pruefung nichts - und eine Umbenennung des Ordners zoege den
        Journalnamen still mit. Der Wert muss deshalb der Spurname sein, nicht
        eine zweite Schreibweise desselben Ordners.
        """
        for s in SPUREN:
            with self.subTest(spur=s.name):
                text = (s / "handeln.py").read_text(encoding="utf-8")
                self.assertIn('bus_name="handel/%s"' % s.name, text)

    def test_kein_orderweg_in_den_spuren(self):
        """Eine Kursregel ordert nicht - kein Boersenzugriff im Quelltext."""
        verboten = ("okxf", "okx_spot", "kraken.", "markt_kauf", "markt_verkauf",
                    "stop_setzen", "place_order", "submit_order")
        dateien = [s / "handeln.py" for s in SPUREN] + [HANDEL / "klassik_regeln.py"]
        for f in dateien:
            text = f.read_text(encoding="utf-8")
            for wort in verboten:
                with self.subTest(datei=f.name, wort=wort):
                    self.assertNotIn(wort, text)

    def test_live_wird_verweigert(self):
        """--live darf nicht handeln: kein Live-Zweig, Exit 0, klarer Text."""
        if not VENV.exists():
            self.skipTest("Handel-venv fehlt")
        for s in SPUREN:
            with self.subTest(spur=s.name):
                r = subprocess.run(
                    [str(VENV), str(s / "handeln.py"), "--live"],
                    cwd=str(HANDEL), capture_output=True, text=True, timeout=120,
                )
                self.assertEqual(r.returncode, 0, r.stderr[-400:])
                self.assertIn("kein Live-Zweig", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()