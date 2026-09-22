"""Was der Dauerlauf MELDET, ist die Wirkung - nicht die Anfrage.

ANLASS (Befund Max, 22.09.2026): Im Log stand

    22.09. 12:04:00  kraken (live) ok

waehrend kraken in Wahrheit Papier handelte: `handel_erlaubt` stand auf false,
und die Spur selbst schrieb "--live angefordert, aber gesperrt: wachen.json
handel_erlaubt=false -> es wird Papier gehandelt". Das Freigabefenster war
offen, und der Dauerlauf leitet die Meldung allein daraus ab
(`modus = "--live" if f.offen() ...`). Dieselbe Verwechslung wie bei
"still/papier" im Tagesbericht: die Zeile beschrieb die Absicht, nicht das
Ergebnis.

Die Tests halten die Regel jetzt fest:
  * --live + handel_erlaubt=false  -> gemeldet wird (papier)
  * --live + handel_erlaubt=true   -> gemeldet wird (live)
  * --papier                       -> bleibt (papier), unabhaengig von der Datei
  * wachen.json fehlt/unlesbar     -> die Anfrage bleibt stehen (nichts geraten)

Der AUFRUF bleibt ausdruecklich der angeforderte Modus - eine Spur im
Live-Zweig raeumt z.B. ihr Buch anders auf. Geaendert wird nur die Meldung.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
sys.path.insert(0, str(HANDEL))

import dauerlauf                                                 # noqa: E402


class Meldungsmodus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ordner = self.tmp.name
        # _lade_wachen_sicher protokolliert Fehler - protokoll() schreibt in
        # die ECHTE dauerlauf.log. Ein Test darf dort nichts hinterlassen.
        self.pr = patch.object(dauerlauf, "protokoll", lambda *a, **k: None)
        self.pr.start()
        self.addCleanup(self.pr.stop)

    def _wachen(self, inhalt):
        with open(os.path.join(self.ordner, "wachen.json"), "w",
                  encoding="utf-8") as f:
            f.write(inhalt if isinstance(inhalt, str)
                    else json.dumps(inhalt))

    def test_live_ohne_erlaubnis_wird_als_papier_gemeldet(self):
        self._wachen({"handel_erlaubt": False})
        self.assertEqual(dauerlauf._meldungsmodus("--live", self.ordner),
                         "--papier")

    def test_live_mit_erlaubnis_bleibt_live(self):
        self._wachen({"handel_erlaubt": True})
        self.assertEqual(dauerlauf._meldungsmodus("--live", self.ordner),
                         "--live")

    def test_papier_bleibt_papier(self):
        self._wachen({"handel_erlaubt": True})
        self.assertEqual(dauerlauf._meldungsmodus("--papier", self.ordner),
                         "--papier")

    def test_fehlende_datei_laesst_die_anfrage_stehen(self):
        # Nichts geraten: ohne lesbare wachen.json bleibt die Meldung, was
        # angefordert wurde.
        self.assertEqual(dauerlauf._meldungsmodus("--live", self.ordner),
                         "--live")

    def test_feld_fehlt_gilt_nicht_als_verbot(self):
        self._wachen({"max_offene_positionen": 4})
        self.assertEqual(dauerlauf._meldungsmodus("--live", self.ordner),
                         "--live")

    def test_kaputte_datei_laesst_die_anfrage_stehen(self):
        self._wachen("{kaputt")
        self.assertEqual(dauerlauf._meldungsmodus("--live", self.ordner),
                         "--live")


if __name__ == "__main__":
    unittest.main()
