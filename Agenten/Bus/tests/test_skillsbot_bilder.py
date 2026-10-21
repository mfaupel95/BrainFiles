"""Bilder und Bildunterschriften (SkillsBot).

Anlass (03.10.2026): Max schickte `/bot openmontage mit dem Muster im 2. Bild
den Boden im 1. Bild bedecken` als BILDUNTERSCHRIFT. Die Pollschleife las nur
`message.text`, `message.caption` blieb `None`, und `continue` verwarf die
Nachricht OHNE Log-Eintrag - der Auftrag war weg und der Bot sah harmlos aus.
Zweiter Teil desselben Fehlers: als die Bilder dann doch ankamen, lief der
Auftrag OHNE sie, weil der Ladefehler in einem leeren `except` verschwand.

Geprueft wird die REGEL, nicht der eine Fall: eine Bildunterschrift ist ein
Auftrag, die groesste Bildfassung kommt an, der Agent bekommt den Pfad zu SEHEN,
und jeder Ladefehler nennt seinen Grund. Die Netzpfade (getFile/Download)
laufen gegen Attrappen, nie gegen Telegram.
"""

import os
import sys
import tempfile
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

    def test_nur_die_groesste_stufe_je_bild(self):
        """Telegram liefert 4-5 Stufen DESSELBEN Bildes in einer photo-Liste.

        Wer alle nimmt, laedt dieselbe Datei fuenfmal und nennt sie fuenf
        Bilder - gemessen am 03.10.2026, als Bild 1 fuenfmal in der Ablage lag.
        """
        n = {"photo": [{"file_id": "klein", "file_size": 100},
                       {"file_id": "gross", "file_size": 9000},
                       {"file_id": "mitte", "file_size": 800},
                       {"file_id": "winzig", "file_size": 12}]}
        self.assertEqual(s._bilder(n), ["gross"])

    def test_ohne_bild_leere_liste(self):
        self.assertEqual(s._bilder({"text": "/lage"}), [])

    def test_dokument_zaehlt_als_bild(self):
        """Ein Dokument ist ein Bild - aber gibt es auch ein Foto, gewinnt das."""
        self.assertEqual(
            s._bilder({"document": {"file_id": "doc1", "file_name": "plan.pdf"}}),
            ["doc1"])
        n = {"document": {"file_id": "doc1", "file_name": "plan.pdf"},
             "photo": [{"file_id": "p1", "file_size": 900}]}
        self.assertEqual(s._bilder(n), ["p1"])

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
            # So antwortet _ruf(): es gibt "result" bereits entpackt zurueck.
            # Wer hier ein {"result": ...} liefert, prueft den falschen Vertrag -
            # genau dieser Fehler liess den Auftrag ohne Bild laufen.
            return {"file_id": daten["file_id"],
                    "file_path": "photos/file_1.jpg",
                    "file_size": 500}
        return []


class _Antwort:
    """Ein urlopen-Ergebnis: context manager + read()."""

    def __init__(self, inhalt=b"jpegbytes"):
        self.inhalt = inhalt

    def read(self):
        return self.inhalt

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
        alt_ruf, s._ruf = s._ruf, self.attrappe.ruf
        alt_url = s.urllib.request.urlopen
        alt_tok = s.token
        s.urllib.request.urlopen = lambda *a, **k: _Antwort()
        s.token = lambda: "123:ABC"
        try:
            pfad, grund = s._bilder_holen(
                {"photo": [{"file_id": "p1", "file_size": 500}]}, "chat7")
        finally:
            s._ruf = alt_ruf
            s.urllib.request.urlopen = alt_url
            s.token = alt_tok
        self.assertTrue(pfad, "kein Pfad zurueck")
        self.assertEqual(grund, "", "unnoetiger Fehlgrund: %s" % grund)
        self.assertTrue(os.path.exists(pfad))
        with open(pfad, "rb") as f:
            self.assertEqual(f.read(), b"jpegbytes")
        self.assertEqual(self.attrappe.aufrufe[0][0], "getFile")

    def test_fehlgeschlagener_download_nennt_den_grund(self):
        """Kein Netz heisst kein Absturz - aber der Grund MUSS sichtbar sein.

        Das ist der zweite Teil des Fehlers: vorher kam "Betrachte das Bild"
        und dann lief ein Auftrag ohne Bild, ohne jede Spur im Protokoll.
        """
        alt_ruf, s._ruf = s._ruf, self.attrappe.ruf
        alt_url = s.urllib.request.urlopen
        alt_tok = s.token

        def _kaputt(*a, **k):
            raise OSError("kein Netz")

        s.urllib.request.urlopen = _kaputt
        s.token = lambda: "123:ABC"
        try:
            pfad, grund = s._bilder_holen(
                {"photo": [{"file_id": "p1", "file_size": 500}]}, "chat7")
        finally:
            s._ruf = alt_ruf
            s.urllib.request.urlopen = alt_url
            s.token = alt_tok
        self.assertEqual(pfad, "")
        self.assertIn("kein Netz", grund)

    def test_ohne_bilder_kein_fehlgrund(self):
        self.assertEqual(s._bilder_holen({}, "chat7"), ("", ""))


class BildfensterTest(unittest.TestCase):
    """"Muster im 2. Bild, Boden im 1." - beide muessen beim Agenten ankommen."""

    def setUp(self):
        self.alt = s.BILDER_PFAD
        s.BILDER_PFAD = os.path.join(tempfile.mkdtemp(), "bilder")

    def tearDown(self):
        s.BILDER_PFAD = self.alt

    def _lege(self, nummer):
        ziel = os.path.join(s.BILDER_PFAD, "chat7")
        os.makedirs(ziel, exist_ok=True)
        pfad = os.path.join(ziel, "bild%d.jpg" % nummer)
        with open(pfad, "wb") as f:
            f.write(b"x")
        return pfad

    def test_fenster_liefert_alle_bilder_in_reihenfolge(self):
        self._lege(1)
        self._lege(2)
        pfade = s._fenster_bilder("chat7")
        self.assertEqual([os.path.basename(p) for p in pfade],
                         ["bild1.jpg", "bild2.jpg"])

    def test_fenster_ohne_bilder(self):
        self.assertEqual(s._fenster_bilder("gibtesnicht"), [])

    def test_nummer_aus_dem_dateinamen(self):
        self.assertEqual(s._bild_nummer("C:/x/bild7.jpg"), 7)
        self.assertEqual(s._bild_nummer("C:/x/quatsch.txt"), 0)


class MitBildernTest(unittest.TestCase):

    def test_ohne_bilder_bleibt_der_auftrag_woertlich(self):
        self.assertEqual(s._mit_bildern("mach was", []), "mach was")

    def test_pfad_steht_im_auftrag(self):
        """Ohne Pfad kann der Bot das Bild nicht SEHEN - nur die Zahl lesen."""
        r = s._mit_bildern("leg den Teppich hin",
                           ["C:/tmp/a.jpg", "C:/tmp/b.jpg"])
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
        return quelle[start:start + 1700]

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

    def test_das_ganze_fenster_geht_raus(self):
        """Nur das neue Bild waere zu wenig: der Auftrag nennt Bild 1 UND 2.

        Seit der Bilder-Regel vom 14.10.2026 waehlt `_bilder_fuer_auftrag` aus,
        was mitgeht - `_fenster_bilder` direkt anzusprechen klebte am
        04.10.2026 Fliesenbilder an einen reinen Textauftrag. Die Eigenschaft
        bleibt: verweist der Auftrag auf ein Bild, kommt das GANZE Fenster mit.
        """
        self.assertIn("_bilder_fuer_auftrag(nachricht, text, cache_key)",
                      self._schleife())
        alt = s.BILDER_PFAD
        s.BILDER_PFAD = os.path.join(tempfile.mkdtemp(), "bilder")
        try:
            ziel = os.path.join(s.BILDER_PFAD, "chat7")
            os.makedirs(ziel)
            for nummer in (1, 2):
                with open(os.path.join(ziel, "bild%d.jpg" % nummer), "wb") as f:
                    f.write(b"x")
            nachricht = {"photo": [{"file_id": "p2", "file_size": 900}]}
            pfade = s._bilder_fuer_auftrag(nachricht, "Muster im 2. Bild",
                                           "chat7")
        finally:
            s.BILDER_PFAD = alt
        self.assertEqual([os.path.basename(p) for p in pfade],
                         ["bild1.jpg", "bild2.jpg"])

    def test_bildfehler_landet_im_protokoll(self):
        """Ein Ladefehler darf nicht spurlos verschwinden."""
        block = self._schleife()
        self.assertIn("bild_fehler", block)
        self.assertIn('"bildfehler"', block)


class BotNamenTest(unittest.TestCase):

    def test_openmontage_ist_ein_bot(self):
        """Genau der Auftrag, der durchging: /bot openmontage ..."""
        self.assertIn("openmontage", s.bot_namen())


if __name__ == "__main__":
    unittest.main()
