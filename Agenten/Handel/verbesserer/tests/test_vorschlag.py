"""TP3 Teil 3: Artefakte bauen (vorschlag.py).

vorschlag.baue() nimmt das Ergebnis von suche.suche() und schreibt in den
Vorschlagsordner bericht.md, wachen.neu.json, bewertung.patch und commit.txt -
je nach Art des Kandidaten auch nur eine Teilmenge davon (Ruling aus Task 9:
ein reiner Sizing-Delta ist nur ein Hinweis, kein anwendbarer Vorschlag).
Geschrieben wird ausschliesslich in den Ordner, nie neben die Quelldateien.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
import vorschlag  # noqa: E402

WACHEN_TXT = (
    '{\r\n'
    '  "watchlist": ["BTC-USDT", "ETH-USDT"],\r\n'
    '  "mindest_score": 60,\r\n'
    '  "max_volatilitaet_pa": 1.20,\r\n'
    '  "abklingzeit_tage": 3\r\n'
    '}\r\n'
)


def _ergebnis_normal():
    return {
        "kandidat": {"gates": {"mindest_score": 65}, "gewichte":
                     {"chance": {}, "risiko": {}},
                     "watchlist": ["BTC-USDT"], "sizing": "flach"},
        "basis_wf": {"gesamt": {"netto_gv_je_runde": -0.1, "n": 30,
                     "beobachtete_trefferquote": 0.4,
                     "noetige_trefferquote": 0.45,
                     "gebuehr_runde_pct": 0.001, "max_drawdown": 2.0},
                     "fenster": []},
        "kandidat_wf": {"gesamt": {"netto_gv_je_runde": 0.05, "n": 30,
                        "beobachtete_trefferquote": 0.48,
                        "noetige_trefferquote": 0.45,
                        "gebuehr_runde_pct": 0.001, "max_drawdown": 2.0},
                        "fenster": []},
        "aenderungen": {"mindest_score": 65}, "grund": "ok",
    }


class TestVorschlag(unittest.TestCase):
    def test_wachen_neu_erhaelt_crlf(self):
        neu = vorschlag.wachen_neu_text(WACHEN_TXT, {"mindest_score": 65})
        self.assertIn('"mindest_score": 65', neu)
        self.assertNotIn('"mindest_score": 60', neu)
        self.assertEqual(neu.count("\r\n"), WACHEN_TXT.count("\r\n"))
        self.assertNotIn("\n\n", neu.replace("\r\n", "\n"))  # kein LF eingeschleppt

    def test_wachen_neu_ersetzt_liste(self):
        neu = vorschlag.wachen_neu_text(
            WACHEN_TXT, {"watchlist": ["BTC-USDT"]})
        self.assertIn('"watchlist": ["BTC-USDT"]', neu)

    def test_commit_text_hat_vier_pflichtzahlen(self):
        basis = {"gesamt": {"netto_gv_je_runde": -0.10,
                            "beobachtete_trefferquote": 0.40,
                            "noetige_trefferquote": 0.45,
                            "gebuehr_runde_pct": 0.001}}
        kand = {"gesamt": {"netto_gv_je_runde": 0.05,
                           "beobachtete_trefferquote": 0.48,
                           "noetige_trefferquote": 0.45,
                           "gebuehr_runde_pct": 0.001}}
        t = vorschlag.commit_text("Scanner/OKX", basis, kand,
                                  {"mindest_score": 65})
        for stueck in ("Gebuehr", "Trefferquote", "Funding", "Liquidations"):
            self.assertIn(stueck, t)
        self.assertIn("Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>", t)

    def test_baue_schreibt_vier_dateien(self):
        with TemporaryDirectory() as d:
            ordner = Path(d) / "v"
            ordner.mkdir()
            ergebnis = _ergebnis_normal()
            spur = {"wachen": str(Path(d) / "wachen.json"),
                    "bewertung_datei": str(Path(d) / "bewertung.py"),
                    "name": "Scanner/OKX"}
            (Path(d) / "wachen.json").write_text(WACHEN_TXT, "utf-8", newline="")
            (Path(d) / "bewertung.py").write_text(
                'CHANCE_GEWICHTE = {"trend": 0.30}\n', "utf-8")
            vorschlag.baue(ordner, ergebnis, spur, {})
            for name in ("bericht.md", "wachen.neu.json", "bewertung.patch",
                         "commit.txt"):
                self.assertTrue((ordner / name).exists(), name)
            # CRLF der wachen.json bleibt in wachen.neu.json erhalten.
            roh = (ordner / "wachen.neu.json").read_bytes()
            self.assertEqual(roh.count(b"\r\n"), WACHEN_TXT.count("\r\n"))
            self.assertIn(b'"mindest_score": 65', roh)

    def test_baue_sizing_only_nur_bericht(self):
        # aenderungen leer, Kandidat aendert nur die Sizing-Kurve, Gewichte
        # gleich der Basis -> nur bericht.md, Text nennt "Sizing", inkl. Delta.
        with TemporaryDirectory() as d:
            ordner = Path(d) / "v"
            ordner.mkdir()
            gew = {"chance": {"trend": 0.3, "rest": 0.7},
                   "risiko": {"vola": 0.4, "rest": 0.6}}
            ergebnis = {
                "kandidat": {"gates": {}, "gewichte": gew,
                             "watchlist": ["BTC-USDT"], "sizing": "vola-invers"},
                "basis_wf": {"gesamt": {"netto_gv_je_runde": -0.10, "n": 30,
                             "noetige_trefferquote": 0.45,
                             "beobachtete_trefferquote": 0.40,
                             "gebuehr_runde_pct": 0.001, "max_drawdown": 2.0},
                             "fenster": []},
                "kandidat_wf": {"gesamt": {"netto_gv_je_runde": 0.06, "n": 30,
                                "noetige_trefferquote": 0.45,
                                "beobachtete_trefferquote": 0.47,
                                "gebuehr_runde_pct": 0.001, "max_drawdown": 2.0},
                                "fenster": []},
                "aenderungen": {}, "grund": "Vorschlag: schlaegt Basis",
            }
            (Path(d) / "wachen.json").write_text(WACHEN_TXT, "utf-8", newline="")
            (Path(d) / "bewertung.py").write_text(
                'CHANCE_GEWICHTE = {"trend": 0.3, "rest": 0.7}\n'
                'RISIKO_GEWICHTE = {"vola": 0.4, "rest": 0.6}\n', "utf-8")
            spur = {"wachen": str(Path(d) / "wachen.json"),
                    "bewertung_datei": str(Path(d) / "bewertung.py"),
                    "name": "Scanner/OKX"}
            vorschlag.baue(ordner, ergebnis, spur, {})
            self.assertTrue((ordner / "bericht.md").exists())
            for weg in ("wachen.neu.json", "bewertung.patch", "commit.txt"):
                self.assertFalse((ordner / weg).exists(), weg)
            text = (ordner / "bericht.md").read_text("utf-8")
            self.assertIn("Sizing", text)
            self.assertIn("-0.1000 -> 0.0600", text)

    def test_baue_schreibt_nur_in_ordner(self):
        # Nichts landet neben den Quelldateien (Ersatz fuer den git-status-Check).
        with TemporaryDirectory() as d:
            ordner = Path(d) / "v"
            ordner.mkdir()
            quelle = Path(d) / "scanner"
            quelle.mkdir()
            (quelle / "wachen.json").write_text(WACHEN_TXT, "utf-8", newline="")
            (quelle / "bewertung.py").write_text(
                'CHANCE_GEWICHTE = {"trend": 0.30}\n', "utf-8")
            vorher = sorted(p.name for p in quelle.iterdir())
            ergebnis = _ergebnis_normal()
            spur = {"wachen": str(quelle / "wachen.json"),
                    "bewertung_datei": str(quelle / "bewertung.py"),
                    "name": "Scanner/OKX"}
            vorschlag.baue(ordner, ergebnis, spur, {})
            self.assertEqual(sorted(p.name for p in quelle.iterdir()), vorher)

    def test_kein_vorschlag_nur_bericht(self):
        with TemporaryDirectory() as d:
            ordner = Path(d) / "v"
            ergebnis = {
                "basis_wf": {"gesamt": {"netto_gv_je_runde": -0.1, "n": 30,
                             "max_drawdown": 2.0},
                             "fenster": [{"von_tag": 120, "bis_tag": 150,
                                          "kennzahlen": {"netto_gv_je_runde": -0.1,
                                                         "n": 6,
                                                         "max_drawdown": 1.0}}]},
                "grund": "kein besserer Kandidat gefunden",
            }
            vorschlag.kein_vorschlag(ordner, ergebnis, "Scanner/OKX")
            self.assertTrue((ordner / "bericht.md").exists())
            self.assertEqual(sorted(p.name for p in ordner.iterdir()),
                             ["bericht.md"])
            text = (ordner / "bericht.md").read_text("utf-8")
            self.assertIn("kein besserer Kandidat gefunden", text)


if __name__ == "__main__":
    unittest.main()
