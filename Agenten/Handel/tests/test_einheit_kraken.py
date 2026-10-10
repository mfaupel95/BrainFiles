"""Die Einheit der kraken-Zahlen kommt aus dem BUCH, nicht aus einer Tabelle.

Anlass (T-212): Seit dem 30.09.2026 kann die kraken-Spur in EUR, USDC und EURC
handeln - die Quotewaehrung kommt je Paar aus der API (`kraken/quote.py`), das
Guthaben-Tor prueft in der Waehrung des Paares. `auswertung_alle.EINHEIT` trug
aber weiter fest `{"kraken": "EUR"}`: Steht das Buch einmal in USDC, sind die
Betraege richtig und ihre Einheit falsch - genau die Klasse Anzeigefehler, die
am 23.09.2026 bei mosaic einen BTC-Kurs aus der falschen Boerse zeigte.

Geprueft wird die REGEL (Buch -> Einheit, Altbestand -> EUR, Tabelle -> nur
Vorgabe), nicht der Tagesstand des Kontos.
"""
import importlib.util
import os
import sys
import unittest
from pathlib import Path

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import auswertung_alle as aw  # noqa: E402

assert aw.__file__.startswith(HANDEL), aw.__file__


def _lade(name, datei):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HANDEL, datei))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class EinheitAusBuchTest(unittest.TestCase):
    def test_usdc_buch_gibt_usdc(self):
        z = {"positionen": [{"paar": "SOLUSDC", "waehrung": "usdc"}]}
        self.assertEqual(aw.einheit_fuer("kraken", z), "USDC")

    def test_eurc_buch_gibt_eurc(self):
        z = {"positionen": [{"paar": "SOLEURC", "waehrung": "eurc"}]}
        self.assertEqual(aw.einheit_fuer("kraken", z), "EURC")

    def test_altbestand_ohne_feld_ist_eur(self):
        """Positionen aus der Zeit vor dem 30.09.2026 tragen kein `waehrung`."""
        z = {"positionen": [{"paar": "DOTEUR", "menge": 45.98}]}
        self.assertEqual(aw.einheit_fuer("kraken", z), "EUR")

    def test_leeres_buch_ist_eur(self):
        self.assertEqual(aw.einheit_fuer("kraken", {"positionen": []}), "EUR")
        self.assertEqual(aw.einheit_fuer("kraken", {}), "EUR")
        self.assertEqual(aw.einheit_fuer("kraken", None), "EUR")

    def test_erste_position_entscheidet(self):
        z = {"positionen": [{"waehrung": "USDC"}, {"waehrung": "EUR"}]}
        self.assertEqual(aw.einheit_fuer("kraken", z), "USDC")

    def test_andere_spuren_bleiben_in_der_tabelle(self):
        self.assertEqual(aw.einheit_fuer("nautilus_kraken", {}), "EUR")
        self.assertEqual(aw.einheit_fuer("scanner", {}), "USDC")
        self.assertEqual(aw.einheit_fuer("gitter", {}), "USD")


class ZustandspfadTest(unittest.TestCase):
    def test_stufe_haengt_am_zustandsnamen(self):
        alt = aw.STUFE
        try:
            aw.STUFE = None
            basis = aw._zustand_pfad("kraken")
            aw.STUFE = "mittel"
            mittel = aw._zustand_pfad("kraken")
        finally:
            aw.STUFE = alt
        self.assertEqual(basis.name, "zustand.json")
        self.assertEqual(mittel.name, "zustand.mittel.json")
        self.assertEqual(basis.parent, mittel.parent)

    def test_echter_zustand_liefert_eine_waehrung(self):
        """Ohne z wird der Zustand gelesen - und die Antwort ist eine Waehrung."""
        self.assertIn(aw.kraken_buch_waehrung(), ("EUR", "USDC", "EURC"))


class QuelleTest(unittest.TestCase):
    """Die Tabelle darf die Einheit der kraken-Spur nicht mehr bestimmen."""

    def test_kennzahlen_fuer_benutzt_einheit_fuer(self):
        with open(aw.__file__, encoding="utf-8") as f:
            quelle = f.read()
        # Die Tabelle darf NUR noch an EINER Stelle gelesen werden - in
        # einheit_fuer() selbst. Zweimal gelesen heisst: eine zweite Stelle
        # umgeht die Ableitung aus dem Buch.
        self.assertEqual(quelle.count("EINHEIT.get(spur"), 1,
                         "die Tabelle wird an mehr als einer Stelle gelesen")
        # Geprueft wird die EIGENSCHAFT, nicht der Wortlaut des Aufrufs: T-192
        # hat `kennzahlen(...)` um Gebuehr und Brutto-Haekchen erweitert, die
        # alte Zeichenkette stimmte danach nicht mehr, obwohl die Regel galt.
        rumpf = quelle.split("def kennzahlen_fuer(")[1].split("\ndef ")[0]
        self.assertIn("einheit_fuer(spur)", rumpf)

    def test_kein_zweiter_leser_der_tabelle(self):
        """Wer die Einheit braucht, ruft einheit_fuer().

        `strategie_kennzahlen.py` las die Tabelle bis zum 30.09.2026 direkt
        und haette fuer kraken weiter EUR gemeldet, waehrend der Bericht
        schon USDC sagte - zwei Anzeigen derselben Spur mit zwei Einheiten.
        """
        fremd = []
        for wurzel, ordner, dateien in os.walk(HANDEL):
            teile = Path(wurzel).parts
            if any(t in teile for t in ("tests", ".venv", "daten", "__pycache__")):
                ordner[:] = []
                continue
            for name in dateien:
                if not name.endswith(".py"):
                    continue
                p = Path(wurzel) / name
                if p.resolve() == Path(aw.__file__).resolve():
                    continue
                try:
                    text = p.read_text(encoding="utf-8")
                except OSError:
                    continue
                if "EINHEIT.get(" in text:
                    fremd.append(str(p.relative_to(HANDEL)))
        self.assertEqual(fremd, [],
                         "liest die Tabelle direkt statt einheit_fuer()")


class LageDelegiertTest(unittest.TestCase):
    """Der Bericht fuehrt die Regel nicht ein zweites Mal."""

    def test_lage_nutzt_dieselbe_regel(self):
        lage = _lade("lage", "lage.py")
        for z in ({"positionen": [{"waehrung": "usdc"}]},
                  {"positionen": [{"paar": "DOTEUR"}]},
                  {}):
            self.assertEqual(lage._kraken_buch_waehrung(z),
                             aw.kraken_buch_waehrung(z), z)


if __name__ == "__main__":
    unittest.main(verbosity=2)
