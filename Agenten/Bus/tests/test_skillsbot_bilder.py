"""Bilder und Bildunterschriften (SkillsBot).

Anlass (03.10.2026): Max schickte `/bot openmontage mit dem Muster im 2. Bild
den Boden im 1. Bild bedecken` als BILDUNTERSCHRIFT. Die Pollschleife las nur
`message.text`, `message.caption` blieb `None`, und `continue` verwarf die
Nachricht OHNE Log-Eintrag - der Auftrag war weg und der Bot sah harmlos aus.

Geprueft wird die REGEL, nicht der eine Fall: eine Bildunterschrift ist ein
Auftrag, die groesste Bildfassung kommt an, und der Bot bekommt den Dateipfad
zu sehen - nicht nur die Zahl der Bytes. Die Netzpfade (getFile/Download)
laufen gegen Attrappen, nie gegen Telegram.
"""

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import skillsbot as s                                             # noqa: E402


class BildunterchriftTest(unittest.TestCase):

    def test_bildunterschrift_ist_ein_auftrag(self):
        self.assertEqual(
            s._bild_text({"caption": "/bot openmontage bau was"}),
            "/bot openmontage bau was")

    def test_text_hat_vorrang_vor_caption(self):
        self.assertEqual(s._bild_text({"text": "/lage",
                                       "caption": " egal "}), "/lage")

    def test_leere_nachricht_bleibt_leer(self):
        self.assertEqual(s._bild_text({}), "")
        self.assertEqual(s._bild_text({"photo": [{"file_id": "a"}]}), "")

    def test_groesste_fassung_je_bild(self):
        """Telegram liefert je Bild bis zu vier Staufen - die groesste gilt."""
        n = {"photo": [{"file_id": "klein", "file_size": 100},
                       {"file_id": "gross", "file_size": 9000},
                       {"file_id": "mitte", "file_size": 800}]}
        self.assertEqual(s._bilder(n)[0], "gross")
        self.assertEqual(len(s._bilder(n)), 3)

    def test_capital_der_gruppe_ist_beschraenkt(self):
        n = {"photo": [{"file_id": "b%d" % i, "file_size": 1000 - i}
                       for i in range(20)]}
        self.assertEqual(len(s._bilder(n)), s.BILD_GRUPPE_MAX)

    def test_dokument_zaehlt_als_bild(self):
        n = {"document": {"file_id": "doc1", "file_name": "plan.pdf"},
             "photo": [{"file_id": "p1", "file_size": 900}]}
        self.assertIn("doc1", s._bilder(n))

    def test_kein_medium_keine_bilder(self):
        self.assertEqual(s._bilder({"sticker": {"file_id": "s"}}), [])


class _Attrappe:
    """Zwei Telegram-Rufe: getFile und der Datei-Download."""

    def __init__(self, tmp):
        self.tmp = tmp
        self.aufrufe = []

    def ruf(self, methode, daten=None, zeit=None):
        self.aufrufe.append((methode, daten))
        if methode == "getFile":
            # Telegram kapselt alles in "result" - so antwortet _ruf().
            return {"result": {"file_path": "photos/file_1.jpg"}}
        return []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class BilderHolenTest(unittest.TestCase):
    """Der Download laeuft gegen eine Attrappe - nie gegen Telegram."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.attrappe = _Attrappe(self.tmp)
        self.alt = s.BILDER_PFAD
        s.BILDER_PFAD = os.path.join(self.tmp, "bilder")

    def tearDown(self):
        s.BILDER_PFAD = self.alt

    def test_laden_legt_datei_an_und_liefert_pfad(self):
        class _Antwort:
            """Ein urlopen-Ergebnis:/context manager + read()."""

            def __init__(self, inhalt=b"jpegbytes"):
                self.inhalt = inhalt

            def read(self):
                return self.inhalt

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        alt_ruf, s._ruf = s._ruf, self.attrappe.ruf
        alt_url = s.urllib.request.urlopen
        s.urllib.request.urlopen = lambda *a, **k: _Antwort()
        alt_tok = s.token
        s.token = lambda: "123:ABC"
        try:
            pfade = s._bilder_holen(
                {"photo": [{"file_id": "p1", "file_size": 500}]}, "chat7")
        finally:
            s._ruf, s.urllib.request.urlopen, s.token = alt_ruf, alt_url, alt_tok
        self.assertEqual(len(pfade), 1, "kein Pfad zurueck")
        self.assertTrue(os.path.exists(pfade[0]))
        with open(pfade[0], "rb") as f:
            self.assertEqual(f.read(), b"jpegbytes")
        self.assertEqual(self.attrappe.aufrufe[0][0], "getFile")

    def test_fehlgeschlagener_download_liefert_leere_liste(self):
        """Kein Netz heisst kein Absturz: die Liste ist leer, der Bot lebt."""
        alt_ruf, s._ruf = s._ruf, self.attrappe.ruf
        alt_url = s.urllib.request.urlopen
        alt_tok = s.token

        def _kaputt(*a, **k):
            raise OSError("kein Netz")

        s.urllib.request.urlopen = _kaputt
        s.token = lambda: "123:ABC"
        try:
            pfade = s._bilder_holen(
                {"photo": [{"file_id": "p1", "file_size": 500}]}, "chat7")
        finally:
            s._ruf, s.urllib.request.urlopen, s.token = alt_ruf, alt_url, alt_tok
        self.assertEqual(pfade, [])


class MitBildernTest(unittest.TestCase):

    def test_ohne_bilder_bleibt_der_auftrag_woertlich(self):
        self.assertEqual(s._mit_bildern("mach was", []), "mach was")

    def test_pfad_steht_im_auftrag(self):
        """Ohne Pfad kann der Bot das Bild nicht SEHEN - nur die Zahl lesen."""
        r = s._mit_bildern("leg den Teppich hin", ["C:/tmp/a.jpg",
                                                  "C:/tmp/b.jpg"])
        self.assertIn("C:/tmp/a.jpg", r)
        self.assertIn("C:/tmp/b.jpg", r)
        self.assertIn("leg den Teppich hin", r)


class PollschleifeTest(unittest.TestCase):
    """Die eigentliche Regel: eine Caption darf NICHT verworfen werden.

    Geprueft wird die Quelltextstelle - der Fehler war ein `continue` vor dem
    Log, eine Nachricht ohne Eintrag sieht im Protokoll wie Ruhe aus.
    """

    def _schleife(self):
        quelle = Path(s.__file__).read_text(encoding="utf-8")
        start = quelle.index("for n in nachrichten:")
        return quelle[start:start + 1600]

    def test_kein_verwurf_mehr_nach_caption(self):
        block = self._schleife()
        self.assertIn("_bild_text(nachricht)", block)
        self.assertNotIn('.get("text")', block)
        # Das alte Wegwerfen: `if chat is None or text is None: continue`
        self.assertNotIn("text is None", block)

    def test_bilder_werden_durchgereicht(self):
        self.assertIn("_mit_bildern(text, bilder)", self._schleife())

    def test_bild_ohne_unterschrift_wird_nicht_verworfen(self):
        """`(Bild ohne Unterschrift)` - der Bot sieht es und meldet es."""
        block = self._schleife()
        self.assertIn("(Bild ohne Unterschrift)", block)


class BotNamenTest(unittest.TestCase):

    def test_openmontage_ist_ein_bot(self):
        """Genau der Auftrag, der durchging: /bot openmontage ..."""
        self.assertIn("openmontage", s.bot_namen())


if __name__ == "__main__":
    unittest.main()