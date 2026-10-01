"""Transportfehler bei OKX/Kraken: einmal wiederholen statt alarmieren.

Anlass (01.10.2026): Max sah die Zeile
`OKX-Transportfehler 1/6: <urlopen error [WinError 10054] ...>` und las sie als
Ausfall. Sie ist eine WARNUNG: der erste von bis zu sechs Versuchen ist an einem
zurueckgesetzten TCP-Verbindung gescheitert, der naechste gelingt. Gemessen am
selben Tag: OKX antwortete signiert in 0,2 s, der Dauerlauf hatte in seinem
eigenen Log NULL Fehler und NULL Timeouts, die Meldung stand siebenmal in zwei
Tagen in den Rand-Logs (dauerlauf-kind.err.log 1x, handelszentrale-fehler.log 6x).

Geprueft wird hier die REGEL (wiederholen, fachliche Fehler nicht) und die
Meldung selbst - ein Text, der wie ein Ausfall klingt, kostet Vertrauen.
"""

import io
import os
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
# Die eigene Fassung ZULETZT einfuegen: insert(0, ...) draengt sich nach vorn,
# die zuletzt eingefuegte gewinnt (Lehre vom 16.09.2026).
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(HANDEL / "scanner"))

import okx                                                        # noqa: E402

assert str(okx.__file__).startswith(str(HANDEL / "scanner")), okx.__file__


class WiederholungTest(unittest.TestCase):
    def setUp(self):
        self.schlaf = mock.patch.object(okx.time, "sleep")
        self.schlaf.start()
        self.addCleanup(self.schlaf.stop)

    def test_nach_zwei_fehler_kommt_die_antwort(self):
        aufrufe = []

        def roh(*a, **kw):
            aufrufe.append(1)
            if len(aufrufe) < 3:
                raise ConnectionResetError("[WinError 10054] Verbindung geschlossen")
            return [{"ok": 1}]

        with mock.patch.object(okx, "_roh", roh), redirect_stderr(io.StringIO()) as err:
            ergebnis = okx._mit_wiederholung("/api/v5/x")
        self.assertEqual(ergebnis, [{"ok": 1}])
        self.assertEqual(3, len(aufrufe), "zwei Fehlversuche, dann Erfolg")
        self.assertIn("1/%d" % okx.MAX_FEHLER, err.getvalue())
        self.assertIn("wird wiederholt", err.getvalue())

    def test_nach_sechs_fehlern_wird_geworfen(self):
        aufrufe = []

        def roh(*a, **kw):
            aufrufe.append(1)
            raise ConnectionResetError("Verbindung geschlossen")

        with mock.patch.object(okx, "_roh", roh), redirect_stderr(io.StringIO()):
            with self.assertRaises(ConnectionResetError):
                okx._mit_wiederholung("/api/v5/x")
        self.assertEqual(okx.MAX_FEHLER, len(aufrufe))

    def test_fachlicher_fehler_wird_nicht_wiederholt(self):
        """OKX 50119 ist kein Netzproblem - Wiederholen wuerde nur Zeit kosten."""
        aufrufe = []

        def roh(*a, **kw):
            aufrufe.append(1)
            raise okx.OKXFehler("OKX 50119: API key doesn't exist")

        with mock.patch.object(okx, "_roh", roh), redirect_stderr(io.StringIO()):
            with self.assertRaises(okx.OKXFehler):
                okx._mit_wiederholung("/api/v5/x")
        self.assertEqual(1, len(aufrufe), "fachliche Fehler nur EINMAL versuchen")


class MeldungTest(unittest.TestCase):
    """Alle vier Wiederholer sagen, dass sie wiederholen."""

    STELLEN = ("scanner/okx.py", "xperp/okxf.py", "mosaic/okx_spot.py",
               "kraken/kraken.py")

    def test_jede_meldung_nennt_die_wiederholung(self):
        for rel in self.STELLEN:
            text = (HANDEL / rel).read_text(encoding="utf-8")
            i = text.find("Transportfehler %d/%d")
            self.assertGreater(i, 0, "%s: Meldung nicht gefunden" % rel)
            zeile = text[i:i + 220]
            self.assertIn("wird wiederholt", zeile,
                          "%s: Meldung klingt nach Ausfall" % rel)

    def test_alle_vier_zaehlen_bis_sechs(self):
        for rel in self.STELLEN:
            text = (HANDEL / rel).read_text(encoding="utf-8")
            self.assertIn("MAX_FEHLER", text, rel)
            self.assertRegex(text, r"MAX_FEHLER\s*=\s*6", rel)


if __name__ == "__main__":
    unittest.main()